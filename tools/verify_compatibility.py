"""Check each packaged adapter against real Minecraft class/member signatures."""

import json
import re
import struct
import sys
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from prepare_versions import fetch  # noqa: E402


class Reader:
    def __init__(self, data):
        self.data, self.position = data, 0

    def integer(self, size):
        result = int.from_bytes(self.data[self.position:self.position + size], "big")
        self.position += size
        return result

    def take(self, size):
        result = self.data[self.position:self.position + size]
        self.position += size
        return result


def parse(data):
    reader = Reader(data)
    assert reader.integer(4) == 0xCAFEBABE
    reader.take(4)
    pool = [None] * reader.integer(2)
    position = 1
    while position < len(pool):
        tag = reader.integer(1)
        if tag == 1:
            pool[position] = (tag, reader.take(reader.integer(2)).decode("utf-8", errors="replace"))
        elif tag in (7, 8, 16, 19, 20):
            pool[position] = (tag, reader.integer(2))
        elif tag in (9, 10, 11, 12, 17, 18):
            pool[position] = (tag, reader.integer(2), reader.integer(2))
        elif tag in (3, 4):
            pool[position] = (tag, reader.take(4))
        elif tag in (5, 6):
            pool[position] = (tag, reader.take(8))
            position += 1
        elif tag == 15:
            pool[position] = (tag, reader.integer(1), reader.integer(2))
        else:
            raise ValueError(tag)
        position += 1

    def utf(index):
        return pool[index][1]

    def clazz(index):
        return utf(pool[index][1]) if index else None

    reader.take(2)
    name, parent = clazz(reader.integer(2)), clazz(reader.integer(2))
    interfaces = [clazz(reader.integer(2)) for _ in range(reader.integer(2))]
    members = {}
    for kind in ("fields", "methods"):
        members[kind] = set()
        for _ in range(reader.integer(2)):
            reader.take(2)
            members[kind].add((utf(reader.integer(2)), utf(reader.integer(2))))
            for _ in range(reader.integer(2)):
                reader.take(2)
                reader.take(reader.integer(4))
    references = []
    for entry in pool:
        if entry and entry[0] in (9, 10, 11):
            member = pool[entry[2]]
            references.append(("fields" if entry[0] == 9 else "methods", clazz(entry[1]), utf(member[1]), utf(member[2])))
    return {"name": name, "parent": parent, "interfaces": interfaces, "references": references,
            "strings": [item[1] for item in pool if item and item[0] == 1], **members}


class Game:
    def __init__(self, paths, mappings=None):
        self.archives = [zipfile.ZipFile(path) for path in paths]
        self.cache = {}
        self.classes = {}
        self.members = {}
        self.reverse = {}
        if mappings:
            owner = None
            for line in mappings.splitlines()[1:]:
                parts = line.split("\t")
                if parts[0] == "c":
                    owner = parts[1]
                    self.classes[parts[1]] = parts[2]
                    self.reverse[parts[2]] = parts[1]
                elif len(parts) >= 5 and parts[1] in ("m", "f"):
                    self.members[(owner, parts[1], parts[3], parts[2])] = parts[4]

    def descriptor(self, value):
        return re.sub(r"L([^;]+);", lambda match: "L" + self.classes.get(match[1], match[1]) + ";", value)

    def get(self, name):
        if name in self.cache:
            return self.cache[name]
        entry = self.reverse.get(name, name) + ".class"
        result = None
        for archive in self.archives:
            if entry in archive.namelist():
                result = parse(archive.read(entry))
                original = result["name"]
                result["name"] = self.classes.get(original, original)
                result["parent"] = self.classes.get(result["parent"], result["parent"])
                result["interfaces"] = [self.classes.get(item, item) for item in result["interfaces"]]
                for kind, tag in (("fields", "f"), ("methods", "m")):
                    result[kind] = {(self.members.get((original, tag, method, descriptor), method), self.descriptor(descriptor)) for method, descriptor in result[kind]}
                break
        self.cache[name] = result
        return result


def cached_game(version):
    root = Path.home() / ".gradle/caches/fabric-loom/minecraftMaven/net/minecraft"
    candidates = []
    for family in ("minecraft-merged-deobf", "minecraft-merged-intermediary", "minecraft-clientonly-intermediary", "minecraft-common-intermediary"):
        for directory in (root / family).glob(version + "*"):
            if directory.name == version or directory.name.startswith(version + "-"):
                candidates.extend(path for path in directory.glob("*.jar") if "sources" not in path.name)
    if candidates:
        return Game(candidates)
    metadata = json.loads((ROOT / ".tools" / f"minecraft-{version}.json").read_text())
    path = fetch(metadata["downloads"]["client"]["url"], ROOT / ".tools" / f"minecraft-{version}-client.jar")
    if version.startswith("26."):
        return Game([path])
    mapping = fetch(f"https://maven.fabricmc.net/net/fabricmc/intermediary/{version}/intermediary-{version}-v2.jar", ROOT / ".tools" / f"intermediary-{version}.jar")
    with zipfile.ZipFile(mapping) as archive:
        return Game([path], archive.read("mappings/mappings.tiny").decode())


def verify(game, mod, prefix):
    checked, errors = 0, []

    def get(name):
        return mod.get(name) or game.get(name)

    def exists(owner, kind, name, descriptor, visited=None):
        visited = visited or set()
        if owner in visited or not owner:
            return False
        visited.add(owner)
        node = get(owner)
        if node is None:
            return owner == "java/lang/Object" and (name, descriptor) in {
                ("getClass", "()Ljava/lang/Class;"), ("toString", "()Ljava/lang/String;"),
                ("hashCode", "()I"), ("equals", "(Ljava/lang/Object;)Z"),
            }
        if (name, descriptor) in node[kind]:
            return True
        if name == "<init>":
            return False
        return any(exists(parent, kind, name, descriptor, visited) for parent in [node["parent"], *node["interfaces"]])

    for name, node in mod.items():
        if not name.startswith(prefix) and not name.startswith(prefix.replace("/compat/", "/mixin/")):
            continue
        if node["parent"] and node["parent"].startswith("net/minecraft/") and not game.get(node["parent"]):
            errors.append("Missing superclass " + node["parent"])
        for kind, owner, member, descriptor in node["references"]:
            if not owner.startswith(("net/minecraft/", "fr/bagyette/aternauto/compat/", "fr/bagyette/aternauto/mixin/", "fr/bagyette/aternauto/forge/")):
                continue
            checked += 1
            if not exists(owner, kind, member, descriptor):
                errors.append(f"{name}: {owner}.{member}{descriptor}")
        if name.endswith("/ConnectionMixin"):
            target = "net/minecraft/client/gui/screens/ConnectScreen" if "v26_" in name else "net/minecraft/class_412"
            for selector in node["strings"]:
                if selector.startswith(("method_36877(", "startConnecting(")):
                    member, descriptor = selector.split("(", 1)
                    if not exists(target, "methods", member, "(" + descriptor):
                        errors.append("Missing mixin target: " + selector)
            for member, descriptor in node["fields"]:
                if member == "field_2412" and not exists(target, "fields", member, descriptor):
                    errors.append("Missing parent shadow")
    if errors:
        raise RuntimeError("\n".join(errors))
    return checked


if __name__ == "__main__":
    destination = ROOT / "releases/1"
    report = {}
    with zipfile.ZipFile(destination / "AternAuto-1-fabric-multiversion.jar") as archive:
        mod = {name[:-6]: parse(archive.read(name)) for name in archive.namelist() if name.endswith(".class")}
        index = json.loads(archive.read("aternauto-adapters.json"))
        for version, adapter in index.items():
            prefix = "fr/bagyette/aternauto/compat/" + adapter["package"] + "/"
            count = verify(cached_game(version), mod, prefix)
            report["fabric-" + version] = {"memberReferencesChecked": count, "result": "passed"}
            print("Fabric", version, "checked", count, "references")
    with zipfile.ZipFile(destination / "AternAuto-1-forge-1.8.9-1.12.2.jar") as archive:
        mod = {name[:-6]: parse(archive.read(name)) for name in archive.namelist() if name.endswith(".class")}
        for version in ("1.8.9", "1.12.2"):
            game = Game([ROOT / ".tools" / f"minecraft-{version}-srg.jar"])
            count = verify(game, mod, "fr/bagyette/aternauto/forge/")
            report["forge-" + version] = {"memberReferencesChecked": count, "result": "passed"}
            print("Forge", version, "checked", count, "references")
    (destination / "compatibility-checks.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    with zipfile.ZipFile(destination / "AternAuto-1.zip", "w", compression=zipfile.ZIP_DEFLATED) as output:
        for name in ("AternAuto-1-fabric-multiversion.jar", "AternAuto-1-forge-1.8.9-1.12.2.jar",
                     "LICENSE", "README.md", "SHA256SUMS.txt", "compatibility-checks.json"):
            output.write(destination / name, arcname=name)
        if (destination / "runtime-checks.json").exists():
            output.write(destination / "runtime-checks.json", arcname="runtime-checks.json")

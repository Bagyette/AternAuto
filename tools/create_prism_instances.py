"""Create clean AternAuto test instances using Prism's native server-join setting."""

import concurrent.futures
import configparser
import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import urllib.request
import uuid

ROOT = Path(__file__).resolve().parents[1]
PRISM = Path(os.environ["APPDATA"]) / "PrismLauncher"
INSTANCES = PRISM / "instances"
SERVER = "leserveursurvie.aternos.me"
GROUP = "AternAuto"
FABRIC = ["26.3", "26.2", "26.1.2", "26.1.1", "26.1", "1.21.11", "1.21.10", "1.21.9",
          "1.21.1", "1.20.1", "1.19.4", "1.18.2", "1.16.5", "1.14.4"]
SPECS = [(version, "Fabric") for version in FABRIC] + [("1.12.2", "Forge"), ("1.8.9", "Forge")]
JAVA = {
    25: PRISM / "java/java-runtime-epsilon",
    21: PRISM / "java/java-runtime-delta",
    17: PRISM / "java/java-runtime-gamma",
    8: Path("C:/Program Files/Eclipse Adoptium/jdk-8.0.504.1-hotspot"),
}


def metadata(uid, version):
    with urllib.request.urlopen(f"https://meta.prismlauncher.org/v1/{uid}/{version}.json", timeout=30) as response:
        return json.load(response)


def component(uid, version, info, dependency=False):
    result = {"uid": uid, "version": version, "cachedName": info.get("name", uid), "cachedVersion": version}
    if dependency:
        result["dependencyOnly"] = True
    if info.get("requires"):
        result["cachedRequires"] = info["requires"]
    if info.get("volatile"):
        result["cachedVolatile"] = True
    return result


def prepare(spec):
    version, loader = spec
    name = f"AternAuto {version} {loader}"
    destination = INSTANCES / name
    if destination.exists():
        raise RuntimeError("Instance already exists; refusing to overwrite: " + name)
    game = metadata("net.minecraft", version)
    java_major = 25 if version.startswith("26.") else 21 if version.startswith("1.21.") else 17 if version in ("1.20.1", "1.19.4", "1.18.2") else 8
    java_home = JAVA[java_major]
    java_executable = java_home / "bin/javaw.exe"
    if not java_executable.is_file():
        raise RuntimeError("Java runtime missing: " + str(java_executable))
    release = (java_home / "release").read_text(encoding="utf-8")
    java_version = re.search(r'^JAVA_VERSION="([^"]+)"', release, re.MULTILINE)[1]
    components = []
    for requirement in game.get("requires", []):
        uid = requirement["uid"]
        dependency_version = requirement.get("equals") or requirement.get("suggests")
        components.append(component(uid, dependency_version, metadata(uid, dependency_version), True))
    components.append(component("net.minecraft", version, game))
    if loader == "Fabric":
        components.append(component("net.fabricmc.intermediary", version, metadata("net.fabricmc.intermediary", version), True))
        components.append(component("net.fabricmc.fabric-loader", "0.19.5", metadata("net.fabricmc.fabric-loader", "0.19.5")))
        mod = ROOT / "releases/1/AternAuto-1-fabric-multiversion.jar"
    else:
        forge_version = "14.23.5.2860" if version == "1.12.2" else "11.15.1.2318"
        components.append(component("net.minecraftforge", forge_version, metadata("net.minecraftforge", forge_version)))
        mod = ROOT / "releases/1/AternAuto-1-forge-1.8.9-1.12.2.jar"
    if not mod.is_file():
        raise RuntimeError("Mod JAR missing: " + str(mod))
    cfg = {
        "ConfigVersion": "1.3", "InstanceType": "OneSix", "name": name, "iconKey": "grass",
        "uuid": uuid.uuid4().hex, "OverrideJavaLocation": "true", "AutomaticJava": "false",
        "JavaPath": java_executable.as_posix(), "JavaVersion": java_version,
        "JavaArchitecture": "64", "JavaRealArchitecture": "amd64",
        "OverrideMemory": "true", "MinMemAlloc": "512" if java_major == 8 else "1024",
        "MaxMemAlloc": "2048" if java_major == 8 else "4096", "PermGen": "128",
        "JoinServerOnLaunch": "true", "JoinServerOnLaunchAddress": SERVER,
        "UseAccountForInstance": "false", "OverrideCommands": "false",
        "notes": "AternAuto 1 - connexion automatique native Prism au serveur de survie.",
    }
    return destination, cfg, {"formatVersion": 1, "components": components}, mod


def main():
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as executor:
        prepared = list(executor.map(prepare, SPECS))
    # Preflight every version before creating anything. Preserve all existing group entries.
    groups_path = INSTANCES / "instgroups.json"
    original_groups = groups_path.read_bytes() if groups_path.exists() else None
    groups = json.loads(original_groups) if original_groups else {"formatVersion": "1", "groups": {}}
    if GROUP in groups["groups"]:
        raise RuntimeError("Group already exists; refusing to overwrite: " + GROUP)
    backup = ROOT / ".tools/prism-backups" / datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    backup.mkdir(parents=True, exist_ok=False)
    if original_groups:
        (backup / "instgroups.json").write_bytes(original_groups)
    report = []
    for destination, cfg, pack, mod in prepared:
        mods = destination / "minecraft/mods"
        mods.mkdir(parents=True, exist_ok=False)
        (destination / "instance.cfg").write_text("[General]\n" + "".join(key + "=" + value + "\n" for key, value in cfg.items()), encoding="utf-8")
        (destination / "mmc-pack.json").write_text(json.dumps(pack, indent=2), encoding="utf-8")
        installed_mod = mods / mod.name
        shutil.copy2(mod, installed_mod)
        parser = configparser.ConfigParser(interpolation=None)
        parser.read(destination / "instance.cfg", encoding="utf-8")
        assert parser["General"].getboolean("JoinServerOnLaunch")
        assert parser["General"]["JoinServerOnLaunchAddress"] == SERVER
        assert hashlib.sha256(installed_mod.read_bytes()).digest() == hashlib.sha256(mod.read_bytes()).digest()
        report.append({"instance": destination.name, "path": str(destination), "java": cfg["JavaVersion"], "mod": mod.name})
    groups["groups"][GROUP] = {"hidden": False, "instances": [entry[0].name for entry in prepared]}
    temporary = groups_path.with_suffix(".json.aternauto.tmp")
    temporary.write_text(json.dumps(groups, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(groups_path)
    (backup / "created-instances.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({"created": len(report), "group": GROUP, "server": SERVER, "backup": str(backup)}, indent=2))


if __name__ == "__main__":
    main()

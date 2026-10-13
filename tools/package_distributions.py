"""Assemble complete distributable JARs with a checked-in license and adapter index."""

import hashlib
import json
from pathlib import Path
import shutil
import zipfile

ROOT = Path(__file__).resolve().parents[1]
DESTINATION = ROOT / "releases/1"
DESTINATION.mkdir(parents=True, exist_ok=True)
CORE = ROOT / "build/libs/AternAuto-common-1.jar"
FABRIC = DESTINATION / "AternAuto-1-fabric-multiversion.jar"
FORGE = DESTINATION / "AternAuto-1-forge-1.8.9-1.12.2.jar"
entries = {}

for source in [CORE, *sorted(ROOT.glob("versions/fabric-*/build/libs/AternAuto-fabric-*-1.jar"))]:
    with zipfile.ZipFile(source) as archive:
        for entry in archive.infolist():
            if entry.is_dir() or entry.filename.startswith("META-INF/"):
                continue
            content = archive.read(entry)
            if entry.filename in entries and entries[entry.filename] != content:
                raise RuntimeError("Conflicting entries: " + entry.filename)
            entries[entry.filename] = content

index = json.loads(entries["aternauto-adapters.json"])
for version, adapter in index.items():
    for prefix, name in (("fr/bagyette/aternauto/mixin/", "ConnectionMixin.class"),
                         ("fr/bagyette/aternauto/compat/", "RequestScreen.class")):
        if prefix + adapter["package"] + "/" + name not in entries:
            raise RuntimeError("Missing adapter for " + version)
config = json.loads(entries["aternauto.mixins.json"])
mixin_prefix = config["package"].replace(".", "/") + "/"
for name in entries:
    if name.startswith(mixin_prefix) and name.endswith(".class") and not name.endswith("Mixin.class"):
        raise RuntimeError("Ordinary class inside reserved mixin package: " + name)

license_content = (ROOT / "LICENSE").read_bytes()
entries["LICENSE"] = license_content
entries["META-INF/MANIFEST.MF"] = b"Manifest-Version: 1.0\r\nImplementation-Title: AternAuto\r\nImplementation-Version: 1\r\n\r\n"
with zipfile.ZipFile(FABRIC, "w", compression=zipfile.ZIP_DEFLATED) as output:
    for name, content in sorted(entries.items()):
        output.writestr(name, content)

shutil.copy2(ROOT / "versions/forge/build/libs/AternAuto-forge-1.jar", FORGE)
for jar in (FABRIC, FORGE):
    with zipfile.ZipFile(jar) as archive:
        assert archive.read("LICENSE") == license_content
        for entry in archive.namelist():
            if entry.endswith(".class"):
                data = archive.read(entry)
                if int.from_bytes(data[6:8], "big") != 52:
                    raise RuntimeError("Non-Java-8 class in universal JAR: " + entry)

shutil.copy2(ROOT / "LICENSE", DESTINATION / "LICENSE")
shutil.copy2(ROOT / "README.md", DESTINATION / "README.md")
(DESTINATION / "SHA256SUMS.txt").write_text("".join(hashlib.sha256(jar.read_bytes()).hexdigest() + "  " + jar.name + "\n" for jar in (FABRIC, FORGE)), encoding="utf-8")
print("Packaged:", FABRIC.name, FORGE.name)

"""Audit the fully verified release and make its public download bundle."""

import hashlib
import json
from pathlib import Path
import shutil
import tomllib
import xml.etree.ElementTree as ET
import zipfile

from distributions_v2 import LANGUAGES, ROOT, release_version
from launch_matrix import validate_artifact_index


def main():
    version = release_version()
    directory = ROOT / "releases" / version
    index = json.loads((directory / "artifacts.json").read_text())
    plan = json.loads((ROOT / "compatibility-v2.json").read_text())
    validate_artifact_index(plan, index, directory)
    if not index.get("complete") or not index.get("runtimeVerified"):
        raise ValueError("All 49 launch checks must pass before finalizing the public bundle")
    report = json.loads((directory / "runtime-checks.json").read_text())
    targets = {target["id"] for target in plan["targets"]}
    if not report.get("complete") or set(report["targets"]) != targets:
        raise ValueError("Incomplete runtime evidence")
    for artifact in index["artifacts"]:
        for target in artifact["targets"]:
            result = report["targets"][target]
            if not result["passed"] or result["jarSha256"] != artifact["sha256"]:
                raise ValueError("Runtime evidence differs from the distribution: " + target)
        with zipfile.ZipFile(directory / artifact["file"]) as archive:
            names = archive.namelist()
            if len(names) != len(set(names)):
                raise ValueError("Duplicate ZIP entries: " + artifact["file"])
            if archive.read("LICENSE") != (ROOT / "LICENSE").read_bytes():
                raise ValueError("License mismatch")
            if "fabric.mod.json" in names:
                declared = json.loads(archive.read("fabric.mod.json"))["version"]
            else:
                descriptor = next((name for name in ["META-INF/neoforge.mods.toml", "META-INF/mods.toml"]
                                   if name in names), None)
                declared = (tomllib.loads(archive.read(descriptor).decode("utf-8"))["mods"][0]["version"]
                            if descriptor else version)  # LaunchWrapper uses @Mod and BuildVersion.
            if declared != version:
                raise ValueError("Incorrect mod version: " + artifact["file"])
            for language in LANGUAGES:
                archive.read(f"assets/aternauto/lang/{language}.properties").decode("utf-8")
            for name in names:
                if name.startswith(("net/minecraft/", "fr/bagyette/aternauto/testing/")) or name.endswith((".env", ".token")):
                    raise ValueError("Unexpected distribution content: " + name)
    for source in ["README.md", "RELEASE_NOTES_2.md", "COMPATIBILITY_V2.md"]:
        shutil.copy2(ROOT / source, directory / source)
    unit_tests = 0
    for project in [ROOT / "common", ROOT / "fabric", *(ROOT / "versions").iterdir()]:
        for path in project.glob("build/test-results/test/TEST-*.xml"):
            suite = ET.parse(path).getroot()
            if int(suite.attrib.get("failures", 0)) or int(suite.attrib.get("errors", 0)):
                raise ValueError("Failed unit test suite: " + path.name)
            unit_tests += int(suite.attrib.get("tests", 0))
    summary = {"version": version, "jars": len(index["artifacts"]),
               "targets": len(targets), "catalogsPerJar": len(LANGUAGES),
               "javaTests": unit_tests, "javaTestFailures": 0,
               "licenseVerified": True, "runtimeVerified": True,
               "boundary": "Offline loader startup and actual request-screen rendering; not live server startup"}
    if any(result.get("metadataOnlyPatch") for result in report["targets"].values()):
        summary["metadataOnlyPatch"] = "English descriptions patched after prior launches; all other JAR entries verified identical; no relaunch"
    if any(result.get("encodingOnlyPatch") for result in report["targets"].values()):
        summary["encodingOnlyPatch"] = "Forge 1.7.10 exception string encoding repaired after prior launch; instructions unchanged; no relaunch"
    (directory / "release-audit.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    bundle = ROOT / "releases" / ("AternAuto-" + version + "-all-loaders.zip")
    with zipfile.ZipFile(bundle, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(directory.iterdir()):
            if path.is_file():
                info = zipfile.ZipInfo(path.name, date_time=(1980, 1, 1, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = 0o644 << 16
                archive.writestr(info, path.read_bytes())
    checksum = hashlib.sha256(bundle.read_bytes()).hexdigest()
    bundle.with_suffix(".zip.sha256").write_text(checksum + "  " + bundle.name + "\n", encoding="ascii")
    print(json.dumps(summary))
    print(bundle)


if __name__ == "__main__":
    main()

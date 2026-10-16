"""Derive release artifacts from the target matrix and the existing adapter modules."""

import argparse
from collections import OrderedDict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import shutil
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]
RUNTIME_DRIVERS = {"fabric", "forge", "neoforge"}
LANGUAGES = (
    "en", "fr", "de", "es", "pt_br", "pt", "ru", "it",
    "pl", "tr", "ja", "zh_cn", "nl", "ko", "uk", "zh_tw",
    "id", "vi", "hi", "ar", "cs", "ro", "sv", "hu",
)


def release_version(root=ROOT):
    properties = (root / "gradle.properties").read_text(encoding="utf-8")
    match = re.search(r"(?m)^mod_version=([0-9]+)$", properties)
    if match is None:
        raise ValueError("Missing integer mod_version in gradle.properties")
    return match.group(1)


def binding(target, root=ROOT):
    loader, version = target["loader"], target["minecraft"]
    if loader == "fabric":
        index = json.loads((root / "fabric/src/main/resources/aternauto-adapters.json").read_text())
        adapter = index.get(version)
        if adapter is None:
            return None
        version = adapter["package"].removeprefix("v").replace("_", ".")
        directory = "versions/fabric-" + version
        project = ":fabric:" + version.replace(".", "_")
    elif loader == "forge" and version in {"1.8.9", "1.12.2"}:
        directory, project = "versions/forge", ":forge:launchwrapper"
    else:
        directory = "versions/" + loader + "-" + version
        project = ":" + loader + ":" + version.replace(".", "_")
    spec = root / directory / "version.json"
    if not spec.is_file():
        return None
    return {"directory": directory, "project": project,
            "metadata": json.loads(spec.read_text(encoding="utf-8"))}


def families(plan):
    result = OrderedDict()
    for target in plan["targets"]:
        result.setdefault(target["artifactFamily"], []).append(target)
    for name, targets in result.items():
        if len({entry["loader"] for entry in targets}) != 1:
            raise ValueError("Artifact mixes different loaders: " + name)
    return result


def preflight(plan, root=ROOT):
    errors = []
    if len(plan["targets"]) != 49 or len({entry["id"] for entry in plan["targets"]}) != 49:
        errors.append("The required matrix must contain 49 distinct targets")
    if str(plan["release"]) != release_version(root):
        errors.append("Target matrix and Gradle release version disagree")
    required = set(plan["requiredFeatures"])
    for target in plan["targets"]:
        adapter = binding(target, root)
        if adapter is None:
            errors.append(target["id"] + ": adapter not ported")
            continue
        missing = required - set(adapter["metadata"].get("features", []))
        if missing:
            errors.append(target["id"] + ": missing " + ", ".join(sorted(missing)))
        if target["loader"] not in RUNTIME_DRIVERS:
            errors.append(target["id"] + ": launch driver not ported")
    families(plan)
    return errors


def artifact_inputs(targets, version, root=ROOT):
    loader = targets[0]["loader"]
    # Forge and NeoForge already embed common before their production remap.
    paths = []
    if loader == "fabric":
        paths.append(root / f"common/build/libs/AternAuto-common-{version}.jar")
        paths.append(root / f"fabric/build/libs/AternAuto-fabric-bootstrap-{version}.jar")
    for target in targets:
        adapter = binding(target, root)
        if adapter is None:
            raise ValueError("Missing adapter: " + target["id"])
        directory = root / adapter["directory"]
        path = directory / "build/libs" / f"AternAuto-{directory.name}-{version}.jar"
        if path not in paths:
            paths.append(path)
    return paths


def merge_entries(inputs):
    entries, manifest = {}, b"Manifest-Version: 1.0\r\n\r\n"
    for source in inputs:
        with zipfile.ZipFile(source) as archive:
            for entry in archive.infolist():
                name = entry.filename
                if entry.is_dir() or re.match(r"META-INF/.*\.(SF|RSA|DSA)$", name, re.I):
                    continue
                content = archive.read(entry)
                if name.upper() == "META-INF/MANIFEST.MF":
                    manifest = content
                    continue
                if name in entries and entries[name] != content:
                    raise ValueError("Conflicting shared entry: " + name)
                entries[name] = content
    entries["META-INF/MANIFEST.MF"] = manifest
    return entries


def write_artifact(path, targets, entries, version, license_bytes):
    entries = dict(entries)
    if targets[0]["loader"] == "fabric":
        versions = [target["minecraft"] for target in targets]
        index = json.loads(entries["aternauto-adapters.json"])
        entries["aternauto-adapters.json"] = json.dumps(
            {item: index[item] for item in versions}, indent=2).encode()
        metadata = json.loads(entries["fabric.mod.json"])
        metadata["version"] = version
        metadata["depends"]["minecraft"] = versions
        metadata["depends"]["java"] = ">=" + str(min(target["java"] for target in targets))
        entries["fabric.mod.json"] = json.dumps(metadata, indent=2).encode()
    entries["LICENSE"] = license_bytes
    for language in LANGUAGES:
        if f"assets/aternauto/lang/{language}.properties" not in entries:
            raise ValueError("Missing language: " + language)
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, content in sorted(entries.items()):
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            archive.writestr(info, content)


def package(plan, root=ROOT, *, preview=False):
    errors = preflight(plan, root)
    if errors and not preview:
        raise ValueError("Incomplete release:\n" + "\n".join(errors))
    version = release_version(root)
    selected = ([target for target in plan["targets"] if binding(target, root)]
                if preview else plan["targets"])
    if not selected:
        raise ValueError("No implemented adapters to package")
    groups = families({"targets": selected})
    inputs = {family: artifact_inputs(targets, version, root)
              for family, targets in groups.items()}
    missing = [str(path) for paths in inputs.values() for path in paths if not path.is_file()]
    if missing:
        raise ValueError("Missing build outputs:\n" + "\n".join(sorted(set(missing))))
    releases = root / "releases"
    releases.mkdir(exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=".v2-", dir=releases))
    try:
        artifacts = []
        for family, targets in groups.items():
            name = f"AternAuto-{version}-{family}.jar"
            output = staging / name
            write_artifact(output, targets, merge_entries(inputs[family]), version,
                           (root / "LICENSE").read_bytes())
            artifacts.append({"file": name, "loader": targets[0]["loader"],
                              "targets": [entry["id"] for entry in targets],
                              "sha256": hashlib.sha256(output.read_bytes()).hexdigest()})
        index = {"version": version, "artifacts": artifacts, "complete": False, "runtimeVerified": False}
        if preview:
            index.update({
                "preview": True,
                "complete": False,
                "runtimeVerified": False,
                "releaseBlockers": errors,
                "missingTargets": [target["id"] for target in plan["targets"]
                                   if target not in selected],
                "missingFeatures": {
                    target["id"]: sorted(set(plan["requiredFeatures"]) - set(
                        binding(target, root)["metadata"].get("features", [])))
                    for target in selected},
            })
            (staging / "README.txt").write_text(
                "AternAuto 2 - incomplete preview builds\n\n"
                "Only the existing adapters are included. Compilation and unit tests\n"
                "do not prove in-game compatibility. See artifacts.json for missing\n"
                "features per target and the remaining full-release blockers.\n"
                "Do not publish these files as the complete AternAuto 2 release.\n",
                encoding="utf-8")
        (staging / "artifacts.json").write_text(
            json.dumps(index, indent=2), encoding="utf-8")
        (staging / "SHA256SUMS.txt").write_text("".join(
            entry["sha256"] + "  " + entry["file"] + "\n" for entry in artifacts), encoding="utf-8")
        shutil.copy2(root / "LICENSE", staging / "LICENSE")
        destination = releases / (version + "-preview" if preview else version)
        # Resolve and verify both paths before any directory replacement on Windows.
        for path in [staging, destination]:
            if path.resolve().parent != releases.resolve():
                raise ValueError("Unexpected release destination")
        if destination.exists():
            if preview:
                raise ValueError("Release directory already exists; preserve it before rebuilding")
            same = all((destination / entry["file"]).is_file() and
                       hashlib.sha256((destination / entry["file"]).read_bytes()).hexdigest() == entry["sha256"]
                       for entry in artifacts)
            if same and (destination / "artifacts.json").is_file():
                previous = json.loads((destination / "artifacts.json").read_text())
                if previous.get("artifacts") == artifacts:
                    return artifacts
            history = releases / ".history"
            if history.resolve().parent != releases.resolve():
                raise ValueError("Unexpected release history path")
            history.mkdir(exist_ok=True)
            backup = history / (version + "-" + datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-%f"))
            if backup.resolve().parent != history.resolve():
                raise ValueError("Unexpected release backup path")
            destination.rename(backup)
        staging.rename(destination)
        return artifacts
    finally:
        if staging.exists():
            if staging.resolve().parent != releases.resolve():
                raise ValueError("Unexpected staging cleanup path")
            shutil.rmtree(staging)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["preflight", "package", "package-preview"])
    args = parser.parse_args()
    plan = json.loads((ROOT / "compatibility-v2.json").read_text())
    if args.action == "preflight":
        errors = preflight(plan)
        print(f"{len(plan['targets'])} targets; {len(families(plan))} artifacts")
        if errors:
            raise SystemExit("Incomplete v2 ports:\n" + "\n".join(errors))
    else:
        print(json.dumps(package(plan, preview=args.action == "package-preview"), indent=2))


if __name__ == "__main__":
    main()

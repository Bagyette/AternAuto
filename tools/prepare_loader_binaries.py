"""Prepare official binary-only compile inputs; never decompile Minecraft sources."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / ".tools"
LIBRARIES = TOOLS / "loader-binaries/libraries"


def download(url, path, sha1=None):
    if path.is_file() and (sha1 is None or hashlib.sha1(path.read_bytes()).hexdigest() == sha1):
        return path
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".download")
    try:
        request = urllib.request.Request(url, headers={"User-Agent": "Gradle/9.5.1"})
        with urllib.request.urlopen(request, timeout=60) as response:
            temporary.write_bytes(response.read())
        if sha1 and hashlib.sha1(temporary.read_bytes()).hexdigest() != sha1:
            raise ValueError("Checksum mismatch: " + path.name)
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)
    return path


def library(item):
    artifact = item.get("downloads", {}).get("artifact", {})
    url = artifact.get("url")
    if not url:
        return None  # Installer-generated outputs are not vanilla compile inputs.
    return download(url, LIBRARIES / artifact["path"], artifact.get("sha1"))


def renamer_paths(profile):
    processor = next((entry for entry in profile["processors"] if "RenamingTool" in entry["jar"]), None)
    if processor is None:
        reference = download(
            "https://maven.minecraftforge.net/net/minecraftforge/forge/1.21.11-61.2.4/forge-1.21.11-61.2.4-installer.jar",
            TOOLS / "loader-mdks/forge-1.21.11-installer.jar")
        with zipfile.ZipFile(reference) as archive:
            profile = json.loads(archive.read("install_profile.json"))
        processor = next(entry for entry in profile["processors"] if "RenamingTool" in entry["jar"])
    required = set(processor["classpath"] + [processor["jar"]])
    paths = [library(item) for item in profile["libraries"] if item["name"] in required]
    if len(paths) != len(required) or any(path is None for path in paths):
        raise ValueError("Missing official renamer dependencies")
    return paths


def named_minecraft(version, profile, installer):
    metadata = json.loads((TOOLS / ("minecraft-" + version + ".json")).read_text())
    client = metadata["downloads"]["client"]
    raw = TOOLS / "gradle-home/caches/fabric-loom" / version / "minecraft-client.jar"
    if not raw.is_file() or hashlib.sha1(raw.read_bytes()).hexdigest() != client["sha1"]:
        raw = download(client["url"], TOOLS / "mojmap" / version / "raw-client.jar", client["sha1"])
    if version.startswith("26."):
        return raw, metadata
    if version == "1.14.4":
        output = TOOLS / "srg" / version / "client.jar"
        if not output.is_file():
            output.parent.mkdir(parents=True, exist_ok=True)
            archive_path = download(
                "https://maven.minecraftforge.net/de/oceanlabs/mcp/mcp_config/1.14.4-20190829.143755/mcp_config-1.14.4-20190829.143755.zip",
                TOOLS / "mcp-1.14.4-20190829.143755-config.zip")
            with zipfile.ZipFile(archive_path) as archive:
                entry = next(name for name in archive.namelist() if name.endswith("joined.tsrg"))
                mappings = output.parent / "mappings.tsrg"
                mappings.write_bytes(archive.read(entry))
            java = Path(os.environ["JAVA_HOME"]) / "bin/java.exe"
            temporary = output.with_suffix(".building.jar")
            try:
                with (output.parent / "remap.log").open("w", encoding="utf-8") as log:
                    subprocess.run([str(java), "-Xmx512m", "-jar", str(TOOLS / "special-source.jar"),
                                    "-i", str(raw), "-o", str(temporary), "-m", str(mappings)],
                                   cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, check=True)
                temporary.replace(output)
            finally:
                temporary.unlink(missing_ok=True)
        return output, metadata
    output = TOOLS / "mojmap" / version / "client.jar"
    if output.is_file():
        return output, metadata
    maps = metadata["downloads"]["client_mappings"]
    mappings = download(maps["url"], output.parent / "client.txt", maps["sha1"])
    paths = renamer_paths(profile)
    java = Path(os.environ["JAVA_HOME"]) / "bin/java.exe"
    temporary = output.with_suffix(".building.jar")
    log = output.parent / "remap.log"
    try:
        with log.open("w", encoding="utf-8") as stream:
            subprocess.run(
                [str(java), "-Xmx1024m", "-XX:ActiveProcessorCount=2", "-cp",
                 os.pathsep.join(map(str, paths)), "net.minecraftforge.fart.Main",
                 "--input", str(raw), "--output", str(temporary), "--names", str(mappings),
                 "--ann-fix", "--ids-fix", "--src-fix", "--record-fix", "--strip-sigs",
                 "--reverse", "--threads", "2"], cwd=ROOT, check=True,
                stdout=stream, stderr=subprocess.STDOUT)
        with zipfile.ZipFile(temporary) as archive:
            archive.getinfo("net/minecraft/client/Minecraft.class")
        temporary.replace(output)
    finally:
        temporary.unlink(missing_ok=True)
    return output, metadata


def production_mappings(metadata, directory):
    version = metadata["id"]
    official = metadata["downloads"]["client_mappings"]
    mojang = download(official["url"], directory / "mojang.txt", official["sha1"])
    mcp_zip = download(
        "https://maven.minecraftforge.net/de/oceanlabs/mcp/mcp_config/1.16.5-20210115.111550/mcp_config-1.16.5-20210115.111550.zip",
        directory / "mcp.zip")
    mcp = directory / "joined.tsrg"
    with zipfile.ZipFile(mcp_zip) as archive:
        name = next(name for name in archive.namelist() if name.endswith("joined.tsrg"))
        mcp.write_bytes(archive.read(name))
    utils = download(
        "https://maven.minecraftforge.net/net/minecraftforge/srgutils/0.6.8/srgutils-0.6.8.jar",
        LIBRARIES / "net/minecraftforge/srgutils/0.6.8/srgutils-0.6.8.jar")
    output = directory / "mojang-to-srg.srg"
    java = Path(os.environ["JAVA_HOME"]) / "bin/java.exe"
    source = ROOT / "tools/mappings/src/fr/bagyette/aternauto/testing/mappings/ComposeMappings.java"
    subprocess.run([str(java), "-Xmx128m", "-cp", str(utils), str(source),
                    str(mojang), str(mcp), str(output)], cwd=ROOT, check=True)
    return output


def prepare(target):
    version, coordinate = target["minecraft"], target["loaderVersion"]
    installer = TOOLS / "loader-mdks" / (target["id"] + "-installer.jar")
    download(f"https://maven.minecraftforge.net/net/minecraftforge/forge/{coordinate}/"
             f"forge-{coordinate}-installer.jar", installer)
    with zipfile.ZipFile(installer) as archive:
        profile = json.loads(archive.read("install_profile.json"))
        runtime = json.loads(archive.read("version.json"))
    minecraft, metadata = named_minecraft(version, profile, installer)
    inputs = [minecraft]
    if version in {"1.14.4", "1.16.5"}:
        inputs.append(download(
            f"https://maven.minecraftforge.net/net/minecraftforge/forge/{coordinate}/forge-{coordinate}-universal.jar",
            LIBRARIES / "net/minecraftforge/forge" / coordinate / ("forge-" + coordinate + "-universal.jar")))
    for item in metadata["libraries"] + runtime["libraries"]:
        path = library(item)
        if path is None:
            artifact = item.get("downloads", {}).get("artifact", {})
            relative = artifact.get("path")
            with zipfile.ZipFile(installer) as archive:
                entry = "maven/" + relative if relative else ""
                if entry in archive.namelist():
                    content = archive.read(entry)
                    if artifact.get("sha1") and hashlib.sha1(content).hexdigest() != artifact["sha1"]:
                        raise ValueError("Embedded artifact checksum mismatch: " + relative)
                    path = LIBRARIES / relative
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_bytes(content)
        if path is not None and path not in inputs:
            inputs.append(path)
    directory = TOOLS / "loader-binaries" / target["id"]
    directory.mkdir(parents=True, exist_ok=True)
    manifest = {"target": target["id"], "minecraft": str(minecraft),
                "minecraftVanillaSha1": metadata["downloads"]["client"]["sha1"],
                "classpath": list(map(str, inputs)), "runtime": runtime,
                "installer": str(installer), "decompiledSources": False}
    if version == "1.16.5":
        manifest["productionMappings"] = str(production_mappings(metadata, directory))
    (directory / "compile-inputs.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print("Verified binary compile inputs:", target["id"], len(inputs), "libraries", flush=True)


def remap_mod(target, source, output, mixin_mappings):
    for path in [source, output, mixin_mappings]:
        if not path.resolve().is_relative_to(ROOT):
            raise ValueError("Remap paths must stay inside the workspace")
    manifest = json.loads((TOOLS / "loader-binaries" / target["id"] / "compile-inputs.json").read_text())
    with zipfile.ZipFile(manifest["installer"]) as archive:
        profile = json.loads(archive.read("install_profile.json"))
    paths = renamer_paths(profile)
    mappings = output.parent / "production-combined.srg"
    mappings.parent.mkdir(parents=True, exist_ok=True)
    mappings.write_text(Path(manifest["productionMappings"]).read_text() + "\n" +
                        mixin_mappings.read_text(), encoding="utf-8")
    java = Path(os.environ["JAVA_HOME"]) / "bin/java.exe"
    args = [str(java), "-Xmx512m", "-XX:ActiveProcessorCount=2", "-cp",
            os.pathsep.join(map(str, paths)), "net.minecraftforge.fart.Main", "--input", str(source),
            "--output", str(output), "--names", str(mappings), "--threads", "2", "--strip-sigs"]
    for path in manifest["classpath"]:
        args.extend(["--lib", path])
    with output.with_suffix(".remap.log").open("w", encoding="utf-8") as log:
        subprocess.run(args, cwd=ROOT, check=True, stdout=log, stderr=subprocess.STDOUT)
    with zipfile.ZipFile(output) as archive:
        archive.getinfo("aternauto.loader.refmap.json")
    print("Production SRG remap:", output, flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("target")
    parser.add_argument("--remap-input", type=Path)
    parser.add_argument("--remap-output", type=Path)
    parser.add_argument("--mixin-mappings", type=Path)
    args = parser.parse_args()
    plan = json.loads((ROOT / "compatibility-v2.json").read_text())
    target = next(item for item in plan["targets"] if item["id"] == args.target)
    if target["loader"] != "forge":
        raise ValueError("Binary compile preparation currently supports Forge only")
    if args.remap_input:
        if args.remap_output is None or args.mixin_mappings is None:
            parser.error("Production remapping requires output and Mixin mappings")
        remap_mod(target, args.remap_input, args.remap_output, args.mixin_mappings)
    else:
        prepare(target)

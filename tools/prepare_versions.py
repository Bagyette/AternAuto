"""Fetch pinned version metadata and tools for the AternAuto compatibility build."""

import concurrent.futures
import json
from pathlib import Path
import subprocess
import urllib.error
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / ".tools"
TOOLS.mkdir(exist_ok=True)
VERSIONS = list(dict.fromkeys(target["minecraft"] for target in json.loads(
    (ROOT / "compatibility-v2.json").read_text(encoding="utf-8"))["targets"]))


def fetch(url, destination):
    if not destination.exists():
        try:
            with urllib.request.urlopen(url, timeout=90) as response:
                destination.write_bytes(response.read())
        except urllib.error.HTTPError as error:
            if error.code != 403:
                raise
            command = "Invoke-WebRequest -Uri '" + url.replace("'", "''") + "' -OutFile '" + str(destination).replace("'", "''") + "'"
            subprocess.run(["powershell.exe", "-NoProfile", "-Command", command], check=True)
    return destination


def load(url):
    with urllib.request.urlopen(url, timeout=30) as response:
        return json.load(response)


urls = {}


def prepare(version):
    metadata = load(urls[version])
    (TOOLS / f"minecraft-{version}.json").write_text(json.dumps(metadata), encoding="utf-8")
    yarn = None
    if version.startswith("1.") and version not in ("1.7.10", "1.8.9", "1.12.2"):
        yarn = load(f"https://meta.fabricmc.net/v2/versions/yarn/{version}")[0]["version"]
        url = f"https://maven.fabricmc.net/net/fabricmc/yarn/{yarn}/yarn-{yarn}-v2.jar"
        path = fetch(url, TOOLS / f"yarn-{version}.jar")
        with zipfile.ZipFile(path) as archive:
            (TOOLS / f"yarn-{version}.tiny").write_bytes(archive.read("mappings/mappings.tiny"))
    if version in ("1.7.10", "1.8.9", "1.12.2"):
        fetch(metadata["downloads"]["client"]["url"], TOOLS / f"minecraft-{version}-client.jar")
        fetch(f"https://maven.minecraftforge.net/de/oceanlabs/mcp/mcp/{version}/mcp-{version}-srg.zip", TOOLS / f"mcp-{version}-srg.zip")
    return {"minecraft": version, "yarn": yarn, "java": metadata.get("javaVersion", {}).get("majorVersion", 8)}


def main():
    global urls
    manifest = load("https://piston-meta.mojang.com/mc/game/version_manifest_v2.json")
    urls = {entry["id"]: entry["url"] for entry in manifest["versions"]}
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as executor:
        versions = list(executor.map(prepare, VERSIONS))
    (TOOLS / "versions.json").write_text(json.dumps(versions, indent=2), encoding="utf-8")
    print(json.dumps(versions, indent=2))
    fetch("https://repo.maven.apache.org/maven2/net/md-5/SpecialSource/1.11.6/SpecialSource-1.11.6-shaded.jar", TOOLS / "special-source.jar")
    fetch("https://repo.maven.apache.org/maven2/com/google/googlejavaformat/google-java-format/1.28.0/google-java-format-1.28.0-all-deps.jar", TOOLS / "google-java-format.jar")
    for version, forge in [("1.7.10", "10.13.4.1614-1.7.10"), ("1.8.9", "11.15.1.2318-1.8.9"), ("1.12.2", "14.23.5.2860")]:
        coordinate = f"{version}-{forge}"
        forge_path = fetch(f"https://maven.minecraftforge.net/net/minecraftforge/forge/{coordinate}/forge-{coordinate}-universal.jar", TOOLS / f"forge-{version}.jar")
        mappings = TOOLS / f"mcp-{version}.srg"
        with zipfile.ZipFile(TOOLS / f"mcp-{version}-srg.zip") as archive:
            mappings.write_bytes(archive.read("joined.srg"))
        for source, target in [(TOOLS / f"minecraft-{version}-client.jar", TOOLS / f"minecraft-{version}-srg.jar"), (forge_path, TOOLS / f"forge-{version}-srg.jar")]:
            if not target.exists():
                subprocess.run(["java", "-jar", str(TOOLS / "special-source.jar"), "-i", str(source), "-o", str(target), "-m", str(mappings)], check=True)
    fetch("https://libraries.minecraft.net/net/minecraft/launchwrapper/1.12/launchwrapper-1.12.jar", TOOLS / "launchwrapper.jar")
    fetch("https://repo.maven.apache.org/maven2/org/ow2/asm/asm-all/5.0.3/asm-all-5.0.3.jar", TOOLS / "asm-all.jar")


if __name__ == "__main__":
    main()

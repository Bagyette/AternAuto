"""Record requested v2 targets and verify upstream loader availability, without building."""

import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import urllib.request
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
VERSIONS = [
    "1.7.10", "1.8.9", "1.12.2", "1.14.4", "1.16.5", "1.18.2",
    "1.19.2", "1.19.4", "1.20.1", "1.21.1", "1.21.4", "1.21.8",
    "1.21.9", "1.21.10", "1.21.11", "26.1", "26.1.1", "26.1.2",
    "26.2", "26.3",
]
SOURCES = {
    "forge": "https://maven.minecraftforge.net/net/minecraftforge/forge/maven-metadata.xml",
    "neoforge": "https://maven.neoforged.net/releases/net/neoforged/neoforge/maven-metadata.xml",
    "neoforge-legacy": "https://maven.neoforged.net/releases/net/neoforged/forge/maven-metadata.xml",
    "fabric-game": "https://meta.fabricmc.net/v2/versions/game",
    "fabric-loader": "https://meta.fabricmc.net/v2/versions/loader",
}
FEATURES = ["autostart", "single-reset-retry-35-ticks", "confirmed-start-counter",
            "twenty-four-languages-and-regional-fallbacks", "credits", "license",
            "cancellable-single-flight-request", "connect-without-startup",
            "classified-errors", "opt-in-discord-issue-report", "nonblocking-counter",
            "persistent-instance-user-agent"]


def fetch(item):
    name, url = item
    with urllib.request.urlopen(url, timeout=30) as response:
        content = response.read()
    if name.startswith("fabric-"):
        return name, json.loads(content)
    document = ET.fromstring(content)
    return name, [entry.text for entry in document.findall("./versioning/versions/version")]


def latest(candidates):
    if not candidates:
        return None
    stable = [value for value in candidates
              if not re.search(r"alpha|beta|snapshot|rc", value, re.IGNORECASE)]
    return max(stable or candidates,
               key=lambda value: tuple(int(part) for part in re.findall(r"\d+", value)))


def java_version(version):
    if version.startswith("26."):
        return 25
    if version.startswith("1.21."):
        return 21
    if version in {"1.18.2", "1.19.2", "1.19.4", "1.20.1"}:
        return 17
    return 8


def artifact_family(loader, version):
    if loader == "fabric":
        if version in {"1.14.4", "1.16.5"}:
            return "fabric-legacy"
        return "fabric-26" if version.startswith("26.") else "fabric-modern"
    if loader == "forge" and version in {"1.8.9", "1.12.2"}:
        return "forge-launchwrapper"
    # Separate artifacts initially; grouping is allowed only after API validation.
    return loader + "-" + version


def build_plan(upstream):
    targets = []
    fabric_games = {entry["version"] for entry in upstream["fabric-game"]}
    fabric_loader = next(entry["version"] for entry in upstream["fabric-loader"]
                         if entry.get("stable"))
    for index, version in enumerate(VERSIONS):
        for loader in ("fabric", "forge", "neoforge"):
            if (loader == "fabric" and index < 3) or (loader == "neoforge" and index < 8):
                continue
            artifact = loader
            if loader == "fabric":
                loader_version = fabric_loader if version in fabric_games else None
            elif loader == "forge":
                loader_version = latest([entry for entry in upstream[loader]
                                         if entry.startswith(version + "-")])
            elif version == "1.20.1":
                artifact = "neoforge-legacy"
                loader_version = latest([entry for entry in upstream[artifact]
                                         if entry.startswith(version + "-")])
            else:
                prefix = "26.1.0." if version == "26.1" else (
                    version + "." if version.startswith("26.") else version[2:] + ".")
                loader_version = latest([entry for entry in upstream[loader]
                                         if entry.startswith(prefix) and "snapshot" not in entry])
            targets.append({
                "id": loader + "-" + version,
                "minecraft": version,
                "loader": loader,
                "loaderVersion": loader_version,
                "upstream": artifact,
                "java": java_version(version),
                "artifactFamily": artifact_family(loader, version),
                "loaderAvailable": loader_version is not None,
                "loaderPrerelease": bool(loader_version and re.search(
                    r"alpha|beta|snapshot|rc", loader_version, re.IGNORECASE)),
                "implementation": "work-in-progress" if loader == "fabric"
                and version == "1.21.11" else "pending-port",
                "validated": False,
            })
    assert len(targets) == 49
    assert len({target["id"] for target in targets}) == 49
    return {
        "release": "2", "buildAllowed": False,
        "checkedAt": datetime.now(timezone.utc).isoformat(),
        "requiredFeatures": FEATURES,
        "sources": SOURCES, "targets": targets,
    }


def markdown(plan):
    rows = ["# AternAuto 2 compatibility targets", "",
            "All 49 requested combinations are mandatory, including every plus sign",
            "in the supplied table. Loader availability is not mod compatibility.", "",
            "No v2 target is validated yet. Compilation remains deferred.", "",
            "| Minecraft | Fabric | Forge | NeoForge | Java |",
            "| --- | --- | --- | --- | --- |"]
    for version in VERSIONS:
        cells = []
        for loader in ("fabric", "forge", "neoforge"):
            target = next((entry for entry in plan["targets"]
                           if entry["id"] == loader + "-" + version), None)
            if target is None:
                cells.append("—")
            elif target["loaderVersion"] is None:
                cells.append("Target; loader not found")
            else:
                cells.append("Target (" + target["loaderVersion"] + ")")
        rows.append("| " + " | ".join([version, *cells, str(java_version(version))]) + " |")
    rows.extend(["", "## Artifact plan", "",
                 "Families are provisional until real class signatures and loader APIs are checked.",
                 "An artifact is not published unless every claimed target is validated.", ""])
    families = {}
    for target in plan["targets"]:
        families.setdefault(target["artifactFamily"], []).append(target["minecraft"])
    for family, versions in families.items():
        rows.append("- `" + family + "`: " + ", ".join(versions) + ".")
    rows.extend(["", "Forge 1.7.10 has its own FML generation. NeoForge 1.20.1 uses the",
                 "older `net.neoforged:forge` artifact, not the modern NeoForge artifact.",
                 "The initial plan deliberately separates other Forge/NeoForge versions.",
                 "Shared artifacts can replace them after validation, without changing the targets.",
                 "", "Every target must include autostart, exactly one reset retry after 35 client",
                 "ticks, confirmed-start telemetry, all 24 language catalogs and regional fallbacks,",
                 "the requested credit, and the license. Server-version compatibility remains",
                 "a separate requirement; the client mod does not translate Minecraft protocols.", ""])
    return "\n".join(rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cached", action="store_true",
                        help="Use the existing .tools/compatibility-v2 upstream snapshot")
    args = parser.parse_args()
    if args.cached:
        directory = ROOT / ".tools/compatibility-v2"
        upstream = {}
        for name in SOURCES:
            if name.startswith("fabric-"):
                upstream[name] = json.loads((directory / (name + ".json")).read_text())
            else:
                upstream[name] = [entry.text for entry in ET.parse(
                    directory / (name + ".xml")).findall("./versioning/versions/version")]
    else:
        with ThreadPoolExecutor(max_workers=5) as pool:
            upstream = dict(pool.map(fetch, SOURCES.items()))
    plan = build_plan(upstream)
    (ROOT / "compatibility-v2.json").write_text(
        json.dumps(plan, indent=2) + "\n", encoding="utf-8")
    (ROOT / "COMPATIBILITY_V2.md").write_text(markdown(plan), encoding="utf-8")
    print("Targets:", len(plan["targets"]))
    print("Upstream loader found:", sum(target["loaderAvailable"] for target in plan["targets"]))
    print("Validated mod targets: 0. No build was run.")


if __name__ == "__main__":
    main()

import argparse
import hashlib
import importlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import urllib.request
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parent))
from assets import prepare as prepare_assets
import harness
importlib.reload(harness)  # Each dynamically loaded driver uses fresh test helpers.
from harness import mixin_harness, render_method

ROOT = Path(__file__).resolve().parents[2]
PRISM = Path(os.environ["APPDATA"]) / "PrismLauncher"
HERE = ROOT / ".tools/runtime-smoke-v2"
HARNESS = ROOT / "build/runtime-smoke/classes"


def metadata(uid, version):
    cache = PRISM / "meta" / uid / (version + ".json")
    if cache.exists():
        return json.loads(cache.read_text(encoding="utf-8"))
    with urllib.request.urlopen(f"https://meta.prismlauncher.org/v1/{uid}/{version}.json") as response:
        return json.load(response)


def allowed(library):
    if "rules" not in library:
        return True
    result = False
    for rule in library["rules"]:
        platform = rule.get("os", {})
        if platform.get("name", "windows") != "windows":
            continue
        if platform.get("arch", "amd64") not in ("amd64", "x86_64"):
            continue
        result = rule["action"] == "allow"
    return result


def artifact(library):
    coordinate = library["name"].split("@", 1)[0].split(":")
    group, name, version = coordinate[:3]
    classifier = "-" + coordinate[3] if len(coordinate) > 3 else ""
    relative = group.replace(".", "/") + f"/{name}/{version}/{name}-{version}{classifier}.jar"
    target = PRISM / "libraries" / relative
    if not target.exists():
        target = ROOT / ".tools/runtime-libraries" / relative
    if not target.exists():
        url = library.get("downloads", {}).get("artifact", {}).get("url") or library.get("url", "https://libraries.minecraft.net/").rstrip("/") + "/" + relative
        target.parent.mkdir(parents=True, exist_ok=True)
        with urllib.request.urlopen(url, timeout=30) as response:
            target.write_bytes(response.read())
    return target


def run(version, mod_jar, directory_root=None):
    mod_jar = Path(mod_jar).resolve()
    if not mod_jar.is_file():
        raise ValueError("Packaged mod missing: " + str(mod_jar))
    if not (HARNESS / "fr/bagyette/aternauto/testing/smoke/SmokeClient.class").is_file():
        raise ValueError("Compile the smoke harness before launching")
    modern = version.startswith("26.")
    game = metadata("net.minecraft", version)
    components = [metadata(requirement["uid"], requirement.get("equals") or requirement["suggests"]) for requirement in game.get("requires", [])]
    components += [game, metadata("net.fabricmc.intermediary", version), metadata("net.fabricmc.fabric-loader", "0.19.5")]
    libraries = {}
    for component in components:
        for library in component.get("libraries", []):
            if not allowed(library):
                continue
            parts = library["name"].split(":")
            key = tuple(parts[:2] + parts[3:])
            libraries[key] = library
    classpath = [artifact(library) for library in libraries.values()]
    for library in libraries.values():
        classifier = library.get("natives", {}).get("windows")
        if classifier:
            classifier = classifier.replace("${arch}", "64")
            native = dict(library)
            native["name"] += ":" + classifier
            native["downloads"] = {"artifact": library.get("downloads", {}).get("classifiers", {}).get(classifier, {})}
            classpath.append(artifact(native))
    classpath.append(artifact(game["mainJar"]))
    directory = Path(directory_root) if directory_root is not None else HERE / version
    if not directory.resolve().is_relative_to(ROOT.resolve()):
        raise ValueError("Runtime workspace must stay inside the project")
    mods = directory / "mods"
    mods.mkdir(parents=True, exist_ok=True)
    shutil.copy2(mod_jar, mods / mod_jar.name)
    index = json.loads((ROOT / "fabric/src/main/resources/aternauto-adapters.json").read_text())
    screen = "fr.bagyette.aternauto.fabric.compat." + index[version]["package"] + ".RequestScreen"
    onboarding = "net.minecraft.client.gui.screens.AccessibilityOnboardingScreen"
    frame = "extractRenderState"
    window_class = "com.mojang.blaze3d.platform.Window"
    if not modern:
        mapping = ROOT / ".tools" / ("yarn-" + version + ".tiny")
        owner = None
        onboarding = "none"
        frame = None
        for line in mapping.read_text().splitlines():
            parts = line.split("\t")
            if parts[0] == "c":
                owner = parts[-1]
                if owner.endswith("/AccessibilityOnboardingScreen"):
                    onboarding = parts[-2].replace("/", ".")
                if owner.endswith("/client/util/Window"):
                    window_class = parts[-2].replace("/", ".")
            elif owner == "net/minecraft/client/gui/screen/Screen" and line.startswith("\tm\t") and parts[-1] == "render":
                frame = parts[-2]
        frame = render_method(mod_jar, screen).split("(")[0]
    mixin_harness(directory, mod_jar, screen, "fabric",
                  "net.minecraft.client.Minecraft" if modern else "net.minecraft.class_310",
                  "tick" if modern else "method_1574", window_class, classpath,
                  onboarding, frame, "sdl" if version == "26.3" else "glfw-static" if modern else None)
    assets, asset_id, virtual = prepare_assets(version, PRISM)
    temporary = directory / "tmp"
    temporary.mkdir(exist_ok=True)
    options = directory / "options.txt"
    options.write_text("soundCategory_master:0.0\nsound:0.0\nmusic:0.0\n", encoding="utf-8")
    result = directory / "result.txt"
    if result.exists():
        result.unlink()
    major = 25 if modern else 21 if version.startswith("1.21") else 8 if version in ("1.14.4", "1.16.5") else 17
    runtime = {25: "java-runtime-epsilon", 21: "java-runtime-delta", 17: "java-runtime-gamma"}.get(major)
    java = PRISM / "java" / runtime / "bin/java.exe" if runtime else Path(os.environ.get("ATERNAUTO_JAVA8", "C:/Program Files/Eclipse Adoptium/jdk-8.0.504.1-hotspot")) / "bin/java.exe"
    args = ["-Xms128M", "-Xmx800M", "-XX:ActiveProcessorCount=2",
            "-Djdk.net.unixdomain.tmpdir=" + str(ROOT / ".tools/sockets"),
            "-Djava.io.tmpdir=" + str(temporary),
            "-Dsmoke.screen=" + screen, "-Dsmoke.connect=" + ("net.minecraft.client.gui.screens.ConnectScreen" if modern else "net.minecraft.class_412"),
            "-Dsmoke.disconnect=" + ("net.minecraft.client.gui.screens.DisconnectedScreen" if modern else "net.minecraft.class_419"),
            "-Dsmoke.modern=" + str(modern).lower(), "-Dsmoke.onboarding=" + onboarding,
            "-Dsmoke.stop=" + ("stop" if modern else "method_1592"),
            "-Dsmoke.result=" + str(result), "-cp", os.pathsep.join(map(str, classpath)), "net.fabricmc.loader.impl.launch.knot.KnotClient",
            "--username", "AternAutoTest", "--version", version, "--gameDir", str(directory), "--assetsDir", str(assets),
            "--assetIndex", asset_id, "--uuid", "11111111222233334444555555555555", "--accessToken", "0",
            "--userType", "msa", "--width", "854", "--height", "480"]
    if version == "1.16.5":
        args[:0] = ["-Dsmoke.manualConnect=true", "-Dsmoke.setScreen=method_1507"]
    quick_play = modern or version.startswith("1.21.") or version == "1.20.1"
    args += ["--quickPlayMultiplayer", "smoke.aternos.me"] if quick_play else ["--server", "smoke.aternos.me", "--port", "25565"]
    args_file = directory / "java-args.txt"
    args_file.write_text("\n".join('"' + item.replace("\\", "\\\\").replace('"', '\\"') + '"' for item in args), encoding="utf-8")
    with (directory / "console.log").open("w", encoding="utf-8") as log:
        command = [str(java), *args] if major == 8 else [str(java), "@" + str(args_file)]
        environment = dict(os.environ)
        environment["_JAVA_OPTIONS"] = "-Xms128m -Xmx800m -XX:ActiveProcessorCount=2"
        process = subprocess.Popen(command, cwd=directory, stdout=log, stderr=subprocess.STDOUT,
                                   env=environment, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        try:
            code = process.wait(timeout=70)
        except subprocess.TimeoutExpired:
            process.terminate()
            process.wait(timeout=10)
            code = -1
    status = result.read_text().strip() if result.exists() else "NO_RESULT"
    print(version, "exit", code, status, flush=True)
    return {"version": version, "exit": code, "result": status,
            "jarSha256": hashlib.sha256((mods / mod_jar.name).read_bytes()).hexdigest(),
            "marker": "ATERN_SMOKE_PASS" in (directory / "console.log").read_text(encoding="utf-8", errors="replace"),
            "secondaryMonitor": "ATERN_SMOKE_WINDOW_1080P" in (directory / "console.log").read_text(encoding="utf-8", errors="replace")}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("version")
    parser.add_argument("--jar", type=Path, required=True)
    args = parser.parse_args()
    result = run(args.version, args.jar)
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result["exit"] == 0 and result["result"] == "REQUEST_SCREEN_RENDERED" and result["marker"] else 1)

"""Launch exact Forge/NeoForge distributions with isolated offline test credentials."""

import hashlib
import importlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import urllib.error
import zipfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from prepare_loader_binaries import download
from assets import prepare as prepare_assets
import harness
importlib.reload(harness)  # Each dynamically loaded driver uses fresh test helpers.
from harness import legacy_harness, mixin_harness, render_method

PRISM = Path(os.environ["APPDATA"]) / "PrismLauncher"
INSTALLATION = ROOT / ".tools/runtime-installation"


def java_runtime(version):
    major = 25 if version.startswith("26.") else 21 if version.startswith("1.21.") else (
        17 if version in {"1.18.2", "1.19.2", "1.19.4", "1.20.1"} else 8)
    if major == 8:
        home = Path(os.environ.get("ATERNAUTO_JAVA8", "C:/Program Files/Eclipse Adoptium/jdk-8.0.504.1-hotspot"))
    else:
        home = PRISM / "java" / {17: "java-runtime-gamma", 21: "java-runtime-delta", 25: "java-runtime-epsilon"}[major]
    java = home / "bin/java.exe"
    if not java.is_file():
        raise ValueError("Missing Java " + str(major) + " for " + version)
    return java, major


def installer_metadata(target):
    version = target["loaderVersion"]
    if target["loader"] == "forge":
        repository, group, artifact = "https://maven.minecraftforge.net", "net/minecraftforge", "forge"
    elif target["upstream"] == "neoforge-legacy":
        repository, group, artifact = "https://maven.neoforged.net/releases", "net/neoforged", "forge"
    else:
        repository, group, artifact = "https://maven.neoforged.net/releases", "net/neoforged", "neoforge"
    installer = download(f"{repository}/{group}/{artifact}/{version}/{artifact}-{version}-installer.jar",
                         ROOT / ".tools/loader-mdks" / (target["id"] + "-installer.jar"))
    with zipfile.ZipFile(installer) as archive:
        profile = json.loads(archive.read("install_profile.json"))
        runtime = json.loads(archive.read("version.json")) if "version.json" in archive.namelist() else profile["versionInfo"]
    return installer, profile, runtime


def permitted(item):
    if "rules" not in item:
        return True
    result = False
    for rule in item["rules"]:
        system = rule.get("os", {})
        if system.get("name", "windows") != "windows" or system.get("arch", "amd64") not in {"amd64", "x86_64"}:
            continue
        if any(bool(value) for value in rule.get("features", {}).values()):
            continue
        result = rule["action"] == "allow"
    return result


def artifact_path(item):
    coordinate = item["name"].split("@", 1)[0].split(":")
    group, artifact, version = coordinate[:3]
    classifier = "-" + coordinate[3] if len(coordinate) > 3 else ""
    return group.replace(".", "/") + f"/{artifact}/{version}/{artifact}-{version}{classifier}.jar"


def shared_library(item, installer):
    artifact = item.get("downloads", {}).get("artifact", {})
    relative = artifact.get("path") or artifact_path(item)
    destination = INSTALLATION / "libraries" / relative
    checksum = artifact.get("sha1")
    if destination.is_file() and (checksum is None or hashlib.sha1(destination.read_bytes()).hexdigest() == checksum):
        return destination
    cached = ROOT / ".tools/loader-binaries/libraries" / relative
    if cached.is_file() and (checksum is None or hashlib.sha1(cached.read_bytes()).hexdigest() == checksum):
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.exists():
            destination.unlink()
        os.link(cached, destination)
        return destination
    with zipfile.ZipFile(installer) as archive:
        entry = "maven/" + relative
        if entry in archive.namelist():
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(archive.read(entry))
            return destination
    url = artifact.get("url")
    if url == "":
        raise ValueError("Installer did not generate " + relative)
    if not url:
        repository = item.get("url", "https://libraries.minecraft.net/")
        repository = repository.replace("http://files.minecraftforge.net/maven/", "https://maven.minecraftforge.net/")
        url = repository.rstrip("/") + "/" + relative
    try:
        return download(url, destination, checksum)
    except urllib.error.HTTPError as error:
        raise ValueError("Library download failed: " + url + " (HTTP " + str(error.code) + ")") from error


def wait_process(process, timeout):
    try:
        return process.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        process.wait(timeout=10)
        return -1


def install(target):
    version = target["minecraft"]
    installer, profile, runtime = installer_metadata(target)
    game = json.loads((ROOT / ".tools" / ("minecraft-" + version + ".json")).read_text())
    base = INSTALLATION / "versions" / version
    base.mkdir(parents=True, exist_ok=True)
    (base / (version + ".json")).write_text(json.dumps(game), encoding="utf-8")
    client = game["downloads"]["client"]
    download(client["url"], base / (version + ".jar"), client["sha1"])
    profiles = INSTALLATION / "launcher_profiles.json"
    if not profiles.exists():
        profiles.write_text('{"profiles":{},"settings":{}}', encoding="utf-8")
    marker = INSTALLATION / "installed" / (target["id"] + ".json")
    installed = INSTALLATION / "versions" / runtime["id"] / (runtime["id"] + ".json")
    digest = hashlib.sha256(installer.read_bytes()).hexdigest()
    if not marker.is_file() or not installed.is_file() or json.loads(marker.read_text()).get("installerSha256") != digest:
        if "install" in profile:
            # LaunchWrapper installers predate the headless client CLI. Their
            # client install consists of the embedded universal JAR and profile.
            entry = profile["install"]
            destination = INSTALLATION / "libraries" / artifact_path({"name": entry["path"]})
            destination.parent.mkdir(parents=True, exist_ok=True)
            with zipfile.ZipFile(installer) as archive:
                destination.write_bytes(archive.read(entry["filePath"]))
            installed.parent.mkdir(parents=True, exist_ok=True)
            installed.write_text(json.dumps(runtime), encoding="utf-8")
            marker.parent.mkdir(parents=True, exist_ok=True)
            marker.write_text(json.dumps({"installerSha256": digest}), encoding="utf-8")
            return game, runtime, installer
        # Seed immutable libraries already downloaded for compilation, avoiding duplicate downloads.
        for item in game.get("libraries", []) + runtime.get("libraries", []) + profile.get("libraries", []):
            try:
                if permitted(item):
                    shared_library(item, installer)
            except (ValueError, urllib.error.HTTPError):
                pass  # These are the installer's generated, not downloaded, outputs.
        java, _ = java_runtime(version)
        with (INSTALLATION / (target["id"] + "-install.log")).open("w", encoding="utf-8") as log:
            process = subprocess.Popen([str(java), "-Xmx1024m", "-Djava.awt.headless=true", "-jar", str(installer),
                                        "--installClient", str(INSTALLATION)], cwd=INSTALLATION,
                                       stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT,
                                       creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            code = wait_process(process, 180)
        if code != 0 or not installed.is_file():
            raise ValueError("Loader installation failed; see " + str(INSTALLATION / (target["id"] + "-install.log")))
        marker.parent.mkdir(parents=True, exist_ok=True)
        marker.write_text(json.dumps({"installerSha256": digest}), encoding="utf-8")
    return game, runtime, installer


def arguments(values, variables):
    result = []
    for value in values:
        if isinstance(value, dict):
            if not permitted(value):
                continue
            value = value["value"]
        for token in value if isinstance(value, list) else [value]:
            token = re.sub(r"\$\{([^}]+)}", lambda match: variables[match[1]], token)
            result.append(token)
    return result


def runtime_tick(mod):
    with zipfile.ZipFile(mod) as archive:
        if "aternauto.loader.refmap.json" in archive.namelist():
            refmap = json.loads(archive.read("aternauto.loader.refmap.json"))
            for name, methods in refmap.get("mappings", {}).items():
                if name.endswith("RetryClientMixin") and "tick" in methods:
                    value = methods["tick"]
                    return value.split(";", 1)[1] if value.startswith("L") else value
    return "tick"


def runtime_stop(target):
    version = target["minecraft"]
    if version in {"1.7.10", "1.8.9", "1.12.2", "1.14.4", "1.16.5"}:
        return "func_71400_g"
    if version.startswith(("1.21.", "26.")):
        return "stop"
    path = ROOT / "versions" / target["id"] / "build/moddev/artifacts/namedToIntermediate.tsrg"
    owner = None
    for line in path.read_text().splitlines():
        parts = line.split()
        if not line.startswith("\t"):
            owner = parts[0]
        elif owner == "net/minecraft/client/Minecraft" and parts[:2] == ["stop", "()V"]:
            return parts[2]
    raise ValueError("Missing exact runtime Minecraft stop mapping")


def onboarding_class(game, version):
    name = "net.minecraft.client.gui.screens.AccessibilityOnboardingScreen"
    if version.startswith("26."):
        jar = INSTALLATION / "versions" / version / (version + ".jar")
        with zipfile.ZipFile(jar) as archive:
            return name if name.replace(".", "/") + ".class" in archive.namelist() else None
    artifact = game["downloads"].get("client_mappings")
    if artifact is None:
        return None
    path = download(artifact["url"], ROOT / ".tools/runtime-mappings" / (version + ".txt"), artifact["sha1"])
    return name if re.search(r"(?m)^" + re.escape(name) + r" -> ", path.read_text(encoding="utf-8")) else None


def window_factory(target, window):
    entry = window.replace(".", "/") + ".class"
    candidates = []
    for group, artifact in [("net/minecraftforge", "forge"), ("net/neoforged", "forge"),
                            ("net/neoforged", "neoforge"), ("net/neoforged", "minecraft-client-patched")]:
        candidates.extend((INSTALLATION / "libraries" / group / artifact / target["loaderVersion"]).glob("*.jar"))
    candidates.append(INSTALLATION / "versions" / target["minecraft"] / (target["minecraft"] + ".jar"))
    for candidate in candidates:
        with zipfile.ZipFile(candidate) as archive:
            if entry not in archive.namelist():
                continue
            content = archive.read(entry)
            if b"org/lwjgl/sdl/SDLVideo" in content:
                return "sdl-static" if b"createWindowStatic" in content else "sdl"
            if b"createGlfwWindow" in content and b"glfwCreateWindow" in content:
                return "glfw-static"
            for owner in ["net/minecraftforge/fml/loading/ImmediateWindowHandler",
                          "net/neoforged/fml/loading/ImmediateWindowHandler",
                          "net/minecraftforge/fml/loading/progress/EarlyProgressVisualization"]:
                if owner.encode() in content:
                    return owner
            if b"glfwCreateWindow" in content:
                return None
    raise ValueError("Cannot locate the exact patched window factory for " + target["id"])


def run(target, mod_jar, directory):
    version, loader = target["minecraft"], target["loader"]
    directory = Path(directory).resolve()
    if not directory.is_relative_to(ROOT):
        raise ValueError("Client test directory must stay inside the workspace")
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "options.txt").write_text("soundCategory_master:0.0\nsound:0.0\nmusic:0.0\n", encoding="utf-8")
    config = directory / "config"
    config.mkdir(exist_ok=True)
    (config / "fml.toml").write_text(
        "earlyWindowControl=false\nmaxThreads=2\nversionCheck=false\ndisableConfigWatcher=true\n",
        encoding="utf-8")
    game, runtime, installer = install(target)
    selected = {}
    for item in game["libraries"] + runtime["libraries"]:
        if permitted(item):
            parts = item["name"].split(":")
            selected[tuple(parts[:2] + parts[3:])] = item
    classpath = [shared_library(item, installer) for item in selected.values()
                 if not item.get("natives") or item.get("downloads", {}).get("artifact")]
    vanilla = INSTALLATION / "versions" / version / (version + ".jar")
    launch_jar = INSTALLATION / "versions" / runtime["id"] / (runtime["id"] + ".jar")
    launch_jar.parent.mkdir(parents=True, exist_ok=True)
    if not launch_jar.exists():
        os.link(vanilla, launch_jar)
    # Match the vanilla launcher's inherited-JAR filename. Older ModLauncher
    # versions exclude this exact filename from their transforming module layer.
    classpath.append(launch_jar)
    natives = directory / "natives"
    natives.mkdir(exist_ok=True)
    for item in selected.values():
        classifier = item.get("natives", {}).get("windows")
        if classifier:
            classifier = classifier.replace("${arch}", "64")
            native = dict(item)
            native["name"] = item["name"] + ":" + classifier
            native["downloads"] = {"artifact": item.get("downloads", {}).get("classifiers", {}).get(classifier, {})}
            classpath.append(shared_library(native, installer))
    for library in classpath:
        with zipfile.ZipFile(library) as archive:
            for name in archive.namelist():
                if name.lower().endswith(".dll"):
                    (natives / Path(name).name).write_bytes(archive.read(name))
    mods = directory / "mods"
    mods.mkdir(exist_ok=True)
    copied = mods / Path(mod_jar).name
    shutil.copy2(mod_jar, copied)
    suffix = "v" + version.replace(".", "_")
    legacy = version in {"1.7.10", "1.8.9", "1.12.2"}
    screen = ("fr.bagyette.aternauto.forge.legacy1710.RequestScreen" if version == "1.7.10" else
              "fr.bagyette.aternauto.forge.RequestScreen" if legacy else
              f"fr.bagyette.aternauto.{loader}.compat.{suffix}.RequestScreen")
    window = "net.minecraft.client.MainWindow" if version in {"1.14.4", "1.16.5"} else "com.mojang.blaze3d.platform.Window"
    tick = runtime_tick(mod_jar)
    harness_classpath = list(classpath)
    if version in {"1.14.4", "1.16.5"}:
        harness_classpath.extend((INSTALLATION / "libraries/net/minecraftforge/forge" /
                                  target["loaderVersion"]).glob("*-universal.jar"))
    for group in ["net/minecraftforge", "net/neoforged"]:
        for artifact in ["javafmllanguage", "fmlcore", "fmlloader", "loader"]:
            harness_classpath.extend((INSTALLATION / "libraries" / group / artifact).glob(
                target["loaderVersion"] + "/*.jar"))
    if legacy or version == "1.14.4":
        legacy_harness(directory, version, harness_classpath, screen)
    else:
        harness_loader = "forge" if version == "1.20.1" else loader
        mixin_harness(directory, mod_jar, screen, harness_loader, "net.minecraft.client.Minecraft", tick,
                      window, harness_classpath, onboarding_class(game, version), render_method(mod_jar, screen).split("(")[0],
                      window_factory(target, window), version)
    assets, asset_id, virtual = prepare_assets(version, PRISM)
    result = directory / "result.txt"
    result.unlink(missing_ok=True)
    temporary = directory / "tmp"
    temporary.mkdir(exist_ok=True)
    variables = {"auth_player_name": "AternAutoTest", "version_name": runtime["id"],
                 "game_directory": str(directory), "assets_root": str(assets), "assets_index_name": asset_id,
                 "auth_uuid": "11111111222233334444555555555555", "auth_access_token": "0",
                 "clientid": "0", "auth_xuid": "0", "user_type": "mojang" if legacy else "msa", "user_properties": "{}",
                 "version_type": "release", "natives_directory": str(natives),
                 "launcher_name": "AternAutoCheck", "launcher_version": "1",
                 "classpath": os.pathsep.join(map(str, classpath)),
                 "library_directory": str(INSTALLATION / "libraries"), "classpath_separator": os.pathsep}
    jvm = arguments(game.get("arguments", {}).get("jvm", []), variables)
    jvm += arguments(runtime.get("arguments", {}).get("jvm", []), variables)
    if "-cp" not in jvm and "-classpath" not in jvm:
        jvm += ["-cp", variables["classpath"]]
    game_args = arguments(game.get("arguments", {}).get("game", []), variables)
    if runtime.get("minecraftArguments"):
        game_args = arguments(runtime["minecraftArguments"].split(), variables)
    else:
        game_args += arguments(runtime.get("arguments", {}).get("game", []), variables)
    game_args += ["--width", "854", "--height", "480"]
    manual_connect = version in {"1.7.10", "1.8.9", "1.12.2", "1.14.4", "1.16.5"}
    if not manual_connect:
        game_args += ["--quickPlayMultiplayer", "smoke.aternos.me"] if version.startswith(("1.21.", "26.")) or version == "1.20.1" else ["--server", "smoke.aternos.me", "--port", "25565"]
    java, major = java_runtime(version)
    command = [str(java), "-Xms128m", "-Xmx800m", "-XX:ActiveProcessorCount=2",
               "-Dfml.earlyprogresswindow=false",
               "-Djava.io.tmpdir=" + str(temporary), "-Djava.library.path=" + str(natives),
               "-Djdk.net.unixdomain.tmpdir=" + str(ROOT / ".tools/sockets"),
               "-Dsmoke.screen=" + screen, "-Dsmoke.connect=" + ("net.minecraft.client.multiplayer.GuiConnecting" if legacy else "net.minecraft.client.gui.screen.ConnectingScreen" if version in {"1.14.4", "1.16.5"} else "net.minecraft.client.gui.screens.ConnectScreen"),
               "-Dsmoke.result=" + str(result), *jvm, runtime["mainClass"], *game_args]
    command.insert(1, "-Dsmoke.disconnect=" + ("net.minecraft.client.gui.GuiDisconnected" if legacy else
                   "net.minecraft.client.gui.screen.DisconnectedScreen" if version in {"1.14.4", "1.16.5"} else
                   "net.minecraft.client.gui.screens.DisconnectedScreen"))
    command.insert(1, "-Dsmoke.stop=" + runtime_stop(target))
    if not legacy:
        command.insert(1, "-Djava.awt.headless=true")
    if manual_connect:
        command[1:1] = ["-Dsmoke.manualConnect=true", "-Dsmoke.setScreen=func_147108_a"]
    if major >= 9:
        argument_file = directory / "java-args.txt"
        argument_file.write_text("\n".join('"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'
                                           for value in command[1:]), encoding="utf-8")
        command = [str(java), "@" + str(argument_file)]
    environment = dict(os.environ)
    environment["_JAVA_OPTIONS"] = "-Xms128m -Xmx800m -XX:ActiveProcessorCount=2"
    with (directory / "console.log").open("w", encoding="utf-8") as log:
        process = subprocess.Popen(command, cwd=directory, stdout=log, stderr=subprocess.STDOUT,
                                   env=environment, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        code = wait_process(process, 120)
    status = result.read_text().strip() if result.is_file() else "NO_RESULT"
    console = (directory / "console.log").read_text(encoding="utf-8", errors="replace")
    return {"version": version, "exit": code, "result": status,
            "jarSha256": hashlib.sha256(copied.read_bytes()).hexdigest(),
            "marker": "ATERN_SMOKE_PASS" in console, "secondaryMonitor": "ATERN_SMOKE_WINDOW_1080P" in console}

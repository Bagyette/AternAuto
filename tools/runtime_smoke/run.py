import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[2]
PRISM = Path(os.environ["APPDATA"]) / "PrismLauncher"
HERE = ROOT / ".tools/runtime-smoke"


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
        url = library.get("downloads", {}).get("artifact", {}).get("url") or library.get("url", "https://libraries.minecraft.net/").rstrip("/") + "/" + relative
        target.parent.mkdir(parents=True, exist_ok=True)
        with urllib.request.urlopen(url, timeout=30) as response:
            target.write_bytes(response.read())
    return target


def run(version):
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
    directory = HERE / version
    mods = directory / "mods"
    mods.mkdir(parents=True, exist_ok=True)
    shutil.copy2(ROOT / "releases/1/AternAuto-1-fabric-multiversion.jar", mods)
    with zipfile.ZipFile(mods / "runtime-smoke.jar", "w") as archive:
        for path in (HERE / "classes").rglob("*.class"):
            archive.write(path, arcname=path.relative_to(HERE / "classes").as_posix())
        archive.writestr("fabric.mod.json", json.dumps({"schemaVersion": 1, "id": "aternauto_runtime_smoke", "version": "1", "environment": "client", "entrypoints": {"client": ["smoke.SmokeClient"]}, "mixins": ["smoke.mixins.json"]}))
        archive.writestr("smoke.mixins.json", json.dumps({"required": True, "package": "smoke.mixin", "compatibilityLevel": "JAVA_8", "client": ["ModernTickMixin" if modern else "LegacyTickMixin"]}))
    index = json.loads((ROOT / "src/main/resources/aternauto-adapters.json").read_text())
    screen = "fr.bagyette.aternauto.compat." + index[version]["package"] + ".RequestScreen"
    onboarding = "net.minecraft.client.gui.screens.AccessibilityOnboardingScreen"
    if not modern:
        mapping = (ROOT / ".tools" / f"yarn-{version}.tiny")
        if not mapping.exists() and version == "1.21.10":
            mapping = ROOT / ".tools/yarn-1.21.9.tiny"
        matches = [line.split("\t")[1].replace("/", ".") for line in mapping.read_text().splitlines() if line.startswith("c\t") and line.endswith("/AccessibilityOnboardingScreen")]
        onboarding = matches[0] if matches else "none"
    if onboarding != "none":
        source = directory / "OnboardFrameMixin.java"
        render = "extractRenderState" if modern else "method_25394"
        source.write_text('package smoke.mixin;\n'
            'import smoke.SmokeClient;\n'
            'import org.spongepowered.asm.mixin.Mixin;\n'
            'import org.spongepowered.asm.mixin.injection.At;\n'
            'import org.spongepowered.asm.mixin.injection.Inject;\n'
            'import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;\n'
            f'@Mixin(targets = "{onboarding}", remap = false)\n'
            'public abstract class OnboardFrameMixin {\n'
            f'  @Inject(method = "{render}", at = @At("TAIL"), remap = false)\n'
            '  private void continueDuringFrame(CallbackInfo callback) {\n'
            '    SmokeClient.continueScreen(this);\n'
            '  }\n}\n', encoding="utf-8")
        compile_path = [HERE / "classes"] + [path for path in classpath if "fabric-loader-" in path.name or "sponge-mixin-" in path.name]
        subprocess.run(["javac", "--release", "8", "-proc:none", "-cp", os.pathsep.join(map(str, compile_path)), "-d", str(directory / "smoke-classes"), str(source)], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        with zipfile.ZipFile(mods / "runtime-smoke.jar") as archive:
            contents = {name: archive.read(name) for name in archive.namelist() if name != "fabric.mod.json"}
        contents["smoke/mixin/OnboardFrameMixin.class"] = (directory / "smoke-classes/smoke/mixin/OnboardFrameMixin.class").read_bytes()
        contents["smoke.frame.mixins.json"] = json.dumps({"required": True, "package": "smoke.mixin", "compatibilityLevel": "JAVA_8", "client": ["OnboardFrameMixin"]}).encode()
        contents["fabric.mod.json"] = json.dumps({"schemaVersion": 1, "id": "aternauto_runtime_smoke", "version": "1", "environment": "client", "entrypoints": {"client": ["smoke.SmokeClient"]}, "mixins": ["smoke.mixins.json", "smoke.frame.mixins.json"]}).encode()
        with zipfile.ZipFile(mods / "runtime-smoke.jar", "w") as archive:
            for name, content in contents.items():
                archive.writestr(name, content)
    options = directory / "options.txt"
    if options.exists():
        options.unlink()
    result = directory / "result.txt"
    if result.exists():
        result.unlink()
    major = 25 if modern else 21 if version.startswith("1.21") else 17
    runtime = {25: "java-runtime-epsilon", 21: "java-runtime-delta", 17: "java-runtime-gamma"}[major]
    java = PRISM / "java" / runtime / "bin/java.exe"
    args = ["-Xms512M", "-Xmx800M", "-Djdk.net.unixdomain.tmpdir=C:/Windows/Temp",
            "-Dsmoke.screen=" + screen, "-Dsmoke.connect=" + ("net.minecraft.client.gui.screens.ConnectScreen" if modern else "net.minecraft.class_412"),
            "-Dsmoke.modern=" + str(modern).lower(), "-Dsmoke.onboarding=" + onboarding,
            "-Dsmoke.result=" + str(result), "-cp", os.pathsep.join(map(str, classpath)), "net.fabricmc.loader.impl.launch.knot.KnotClient",
            "--username", "AternAutoTest", "--version", version, "--gameDir", str(directory), "--assetsDir", str(PRISM / "assets"),
            "--assetIndex", game["assetIndex"]["id"], "--uuid", "11111111222233334444555555555555", "--accessToken", "0",
            "--userType", "msa", "--width", "854", "--height", "480"]
    args += ["--quickPlayMultiplayer", "leserveursurvie.aternos.me"] if modern or version not in ("1.18.2", "1.19.4") else ["--server", "leserveursurvie.aternos.me", "--port", "25565"]
    args_file = directory / "java-args.txt"
    args_file.write_text("\n".join('"' + item.replace("\\", "\\\\").replace('"', '\\"') + '"' for item in args), encoding="utf-8")
    with (directory / "console.log").open("w", encoding="utf-8") as log:
        process = subprocess.Popen([str(java), "@" + str(args_file)], cwd=directory, stdout=log, stderr=subprocess.STDOUT)
        try:
            code = process.wait(timeout=70)
        except subprocess.TimeoutExpired:
            process.terminate()
            process.wait(timeout=10)
            code = -1
    status = result.read_text().strip() if result.exists() else "NO_RESULT"
    print(version, "exit", code, status, flush=True)
    return {"version": version, "exit": code, "result": status}


if __name__ == "__main__":
    versions = sys.argv[1:] or ["1.19.4", "1.20.1"]
    report = []
    for version in versions:
        try:
            report.append(run(version))
        except Exception as error:
            print(version, repr(error), flush=True)
            report.append({"version": version, "error": str(error)})
    (HERE / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")

"""Generate a separate test mod; never modify the distribution being verified."""

import json
import os
from pathlib import Path
import re
import struct
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parents[2]
CLASSES = ROOT / "build/runtime-smoke/classes"
PACKAGE = "fr.bagyette.aternauto.testing.smoke"


def compile_sources(java_home, classpath, output, sources, directory):
    args = ["--release", "8", "-proc:none", "-cp", classpath, "-d", str(output), *map(str, sources)]
    argument_file = directory / "harness-javac.args"
    argument_file.write_text("\n".join('"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'
                                       for value in args), encoding="utf-8")
    with (directory / "harness-compile.log").open("w", encoding="utf-8") as log:
        subprocess.run([str(java_home / "bin/javac.exe"), "@" + str(argument_file)],
                       check=True, stdout=log, stderr=subprocess.STDOUT, cwd=ROOT)


def render_method(mod, screen):
    with zipfile.ZipFile(mod) as archive:
        content = archive.read(screen.replace(".", "/") + ".class")
    offset = 8

    def number(size):
        nonlocal offset
        value = int.from_bytes(content[offset:offset + size], "big")
        offset += size
        return value

    count = number(2)
    pool = {}
    index = 1
    sizes = {3: 4, 4: 4, 5: 8, 6: 8, 7: 2, 8: 2, 9: 4, 10: 4, 11: 4,
             12: 4, 15: 3, 16: 2, 17: 4, 18: 4, 19: 2, 20: 2}
    while index < count:
        tag = number(1)
        if tag == 1:
            length = number(2)
            pool[index] = content[offset:offset + length].decode("utf-8", errors="replace")
            offset += length
        else:
            offset += sizes[tag]
        index += 2 if tag in {5, 6} else 1
    offset += 6
    interfaces = number(2)
    offset += interfaces * 2

    def members():
        nonlocal offset
        result = []
        for _ in range(number(2)):
            number(2)
            name, descriptor = pool[number(2)], pool[number(2)]
            result.append((name, descriptor))
            for _ in range(number(2)):
                number(2)
                length = number(4)
                offset += length
        return result

    members()  # fields
    candidates = [(name, desc) for name, desc in members()
                  if re.fullmatch(r"\((?:L[^;]+;)?IIF\)V", desc)]
    if len(candidates) != 1:
        raise ValueError("Cannot identify the actual compiled screen render method: " + screen)
    return "".join(candidates[0])


def mixin_harness(directory, mod, screen, loader, minecraft_class, tick, window_class,
                  classpath, onboarding=None, onboarding_render=None, window_factory=None, minecraft_version=None):
    source = directory / "harness-src"
    source.mkdir(parents=True, exist_ok=True)
    output = directory / "harness-classes"
    output.mkdir(exist_ok=True)
    sources = []
    mixins = []

    def write(name, text):
        path = source / (name + ".java")
        path.write_text(text, encoding="utf-8")
        sources.append(path)
        mixins.append(name)

    imports = f"""package {PACKAGE}.mixin;
import {PACKAGE}.SmokeChecks;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.Redirect;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;
"""
    write("ScreenFrameMixin", imports + f"""
@Mixin(targets = "{screen}", remap = false)
public abstract class ScreenFrameMixin {{
  @Inject(method = "{render_method(mod, screen)}", at = @At("TAIL"), remap = false)
  private void rendered(CallbackInfo ci) {{ SmokeChecks.rendered(this); }}
}}
""")
    write("ClientTickMixin", imports + f"""
@Mixin(targets = "{minecraft_class}", remap = false)
public abstract class ClientTickMixin {{
  @Inject(method = "{tick}", at = @At("TAIL"), remap = false)
  private void tick(CallbackInfo ci) {{ SmokeChecks.tick(this); }}
}}
""")
    if window_factory in {"sdl", "sdl-static"}:
        sdl_method = "createWindowStatic" if window_factory == "sdl-static" else "createWindow"
        sdl_static = "static " if window_factory == "sdl-static" else ""
        create = """
  @Redirect(method = "SDL_METHOD", at = @At(value = "INVOKE",
      target = "Lcom/mojang/renderpearl/api/device/GpuBackend;createWindow(Ljava/lang/String;IIJ)J"), remap = false)
  private SDL_STATIClong create(@org.spongepowered.asm.mixin.injection.Coerce Object backend,
      String title, int width, int height, long flags) {
    return SmokeChecks.createSdlWindow(backend, title, width, height, flags);
  }
""".replace("SDL_METHOD", sdl_method).replace("SDL_STATIC", sdl_static)
    elif window_factory == "glfw-static":
        create = """
  @Redirect(method = "createGlfwWindow", at = @At(value = "INVOKE",
      target = "Lorg/lwjgl/glfw/GLFW;glfwCreateWindow(IILjava/lang/CharSequence;JJ)J"), remap = false)
  private static long create(int width, int height, CharSequence title, long monitor, long share) {
    return SmokeChecks.createWindow(width, height, title, monitor, share);
  }
"""
    elif window_factory:
        handoff = window_factory.endswith("EarlyProgressVisualization")
        factory_method = "handOffWindow" if handoff else "setupMinecraftWindow"
        receiver = "@org.spongepowered.asm.mixin.injection.Coerce Object provider, " if handoff else ""
        create = f"""
  @Redirect(method = "<init>", at = @At(value = "INVOKE",
      target = "L{window_factory};{factory_method}(Ljava/util/function/IntSupplier;Ljava/util/function/IntSupplier;Ljava/util/function/Supplier;Ljava/util/function/LongSupplier;)J"), remap = false)
  private long create({receiver}java.util.function.IntSupplier width, java.util.function.IntSupplier height,
      java.util.function.Supplier<String> title, java.util.function.LongSupplier monitor) {{
    return SmokeChecks.createWindow(width.getAsInt(), height.getAsInt(), title.get(), monitor.getAsLong(), 0L);
  }}
"""
    else:
        create = """
  @Redirect(method = "<init>", at = @At(value = "INVOKE",
      target = "Lorg/lwjgl/glfw/GLFW;glfwCreateWindow(IILjava/lang/CharSequence;JJ)J"), remap = false)
  private long create(int width, int height, CharSequence title, long monitor, long share) {
    return SmokeChecks.createWindow(width, height, title, monitor, share);
  }
"""
    write("WindowPositionMixin", imports + f"""
@Mixin(targets = "{window_class}", remap = false)
public abstract class WindowPositionMixin {{
{create}
  @Inject(method = "<init>*", at = @At("TAIL"), remap = false)
  private void place(CallbackInfo ci) {{ SmokeChecks.placeWindow(); }}
}}
""")
    if onboarding and onboarding != "none":
        write("OnboardFrameMixin", imports + f"""
@Mixin(targets = "{onboarding}", remap = false)
public abstract class OnboardFrameMixin {{
  @Inject(method = "{onboarding_render}", at = @At("TAIL"), remap = false)
  private void proceed(CallbackInfo ci) {{ SmokeChecks.continueScreen(this); }}
}}
""")
    if loader != "fabric":
        annotation = "net.minecraftforge.fml.common.Mod" if loader == "forge" else "net.neoforged.fml.common.Mod"
        path = source / "HarnessMod.java"
        path.write_text(f"package {PACKAGE};\nimport {annotation};\n"
                        '@Mod("aternauto_runtime_smoke")\npublic final class HarnessMod {}\n', encoding="utf-8")
        sources.append(path)
    java_home = Path(os.environ.get("JAVA_HOME", str(ROOT / ".tools/jdk25/jdk-25.0.4.1+1")))
    cp = os.pathsep.join(map(str, [CLASSES, *classpath]))
    compile_sources(java_home, cp, output, sources, directory)
    path = directory / "mods/runtime-smoke.jar"
    path.parent.mkdir(exist_ok=True)
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
        for compiled in output.rglob("*.class"):
            archive.write(compiled, compiled.relative_to(output).as_posix())
        for name in ["SmokeChecks.class"] + (["SmokeClient.class"] if loader == "fabric" else []):
            archive.write(CLASSES / Path(PACKAGE.replace(".", "/")) / name,
                          PACKAGE.replace(".", "/") + "/" + name)
        archive.writestr("smoke.mixins.json", json.dumps({
            "required": True, "minVersion": "0.8", "package": PACKAGE + ".mixin", "compatibilityLevel": "JAVA_8",
            "client": mixins, "injectors": {"defaultRequire": 1}}))
        if loader == "fabric":
            archive.writestr("fabric.mod.json", json.dumps({
                "schemaVersion": 1, "id": "aternauto_runtime_smoke", "version": "1", "environment": "client",
                "entrypoints": {"client": [PACKAGE + ".SmokeClient"]}, "mixins": ["smoke.mixins.json"]}))
        else:
            with zipfile.ZipFile(mod) as distribution:
                pack_metadata = json.loads(distribution.read("pack.mcmeta"))
            pack_metadata["pack"]["description"] = "Isolated AternAuto launch checks"
            archive.writestr("pack.mcmeta", json.dumps(pack_metadata))
            name = "META-INF/neoforge.mods.toml" if loader == "neoforge" else "META-INF/mods.toml"
            dependency = ('type="required"\n' if loader == "neoforge" else 'mandatory=true\n')
            archive.writestr(name, 'modLoader="javafml"\nloaderVersion="[1,)"\nlicense="All Rights Reserved"\n'
                              '[[mods]]\nmodId="aternauto_runtime_smoke"\nversion="1"\ndisplayName="AternAuto test harness"\n'
                              '[[mixins]]\nconfig="smoke.mixins.json"\n'
                              '[[dependencies.aternauto_runtime_smoke]]\nmodId="minecraft"\n' + dependency +
                              'versionRange="[' + str(minecraft_version) + ']"\nordering="NONE"\nside="CLIENT"\n')
            archive.writestr("META-INF/MANIFEST.MF", "Manifest-Version: 1.0\r\nMixinConfigs: smoke.mixins.json\r\n\r\n")
    return path


def legacy_harness(directory, version, classpath, screen):
    source = directory / "harness-src"
    source.mkdir(parents=True, exist_ok=True)
    output = directory / "harness-classes"
    output.mkdir(exist_ok=True)
    old = version in {"1.7.10", "1.8.9", "1.12.2"}
    fml = "cpw.mods.fml" if version == "1.7.10" else "net.minecraftforge.fml"
    files = {"HarnessMod.java": (
        f"package {PACKAGE};\nimport {fml}.common.Mod;\n" +
        ('@Mod(modid="aternauto_runtime_smoke", name="AternAuto test harness", version="1")\n'
         if old else '@Mod("aternauto_runtime_smoke")\n') +
        "public final class HarnessMod {}\n")}
    if old:
        files["LegacyLoadingPlugin.java"] = f"""package {PACKAGE};
import java.util.Map;
import {fml}.relauncher.IFMLLoadingPlugin;
@IFMLLoadingPlugin.Name("AternAuto runtime check")
@IFMLLoadingPlugin.SortingIndex(1002)
@IFMLLoadingPlugin.TransformerExclusions({{"{PACKAGE}"}})
public final class LegacyLoadingPlugin implements IFMLLoadingPlugin {{
  public String[] getASMTransformerClass() {{ return new String[] {{"{PACKAGE}.LegacyTransformer"}}; }}
  public String getModContainerClass() {{ return null; }}
  public String getSetupClass() {{ return null; }}
  public String getAccessTransformerClass() {{ return null; }}
  public void injectData(Map<String, Object> data) {{ SmokeChecks.placeLegacyWindow(); }}
}}
"""
        files["LegacyTransformer.java"] = f"""package {PACKAGE};
import net.minecraft.launchwrapper.IClassTransformer;
public final class LegacyTransformer implements IClassTransformer {{
  public byte[] transform(String name, String transformed, byte[] bytes) {{
    return SmokeTransformer.transform(transformed, bytes);
  }}
}}
"""
    paths = []
    for name, text in files.items():
        path = source / name
        path.write_text(text, encoding="utf-8")
        paths.append(path)
    java_home = Path(os.environ.get("JAVA_HOME", str(ROOT / ".tools/jdk25/jdk-25.0.4.1+1")))
    compile_sources(java_home, os.pathsep.join(map(str, [CLASSES, *classpath])), output, paths, directory)
    path = directory / "mods/runtime-smoke.jar"
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("pack.mcmeta", json.dumps({"pack": {
            "pack_format": 1 if old else 4, "description": "Isolated AternAuto launch checks"}}))
        for compiled in output.rglob("*.class"):
            archive.write(compiled, compiled.relative_to(output).as_posix())
        for name in ["SmokeChecks.class", "SmokeTransformer.class"]:
            archive.write(CLASSES / Path(PACKAGE.replace(".", "/")) / name,
                          PACKAGE.replace(".", "/") + "/" + name)
        if old:
            archive.writestr("META-INF/MANIFEST.MF", "Manifest-Version: 1.0\r\n"
                              f"FMLCorePlugin: {PACKAGE}.LegacyLoadingPlugin\r\n"
                              "FMLCorePluginContainsFMLMod: true\r\n\r\n")
        else:
            archive.writestr("META-INF/mods.toml", 'modLoader="javafml"\nloaderVersion="[1,)"\n'
                              'license="All Rights Reserved"\n[[mods]]\nmodId="aternauto_runtime_smoke"\n'
                              'version="1"\ndisplayName="AternAuto test harness"\n'
                              '[[dependencies.aternauto_runtime_smoke]]\nmodId="minecraft"\nmandatory=true\n'
                              'versionRange="[' + version + ']"\nordering="NONE"\nside="CLIENT"\n')
            archive.writestr("META-INF/coremods.json", json.dumps({"aternauto_test": "smoke-coremod.js"}))
            archive.writestr("smoke-coremod.js", coremod_script(screen))
    return path


def coremod_script(screen):
    checks = PACKAGE.replace(".", "/") + "/SmokeChecks"
    return """function initializeCoreMod() {
  var O = Java.type('org.objectweb.asm.Opcodes');
  var InsnList = Java.type('org.objectweb.asm.tree.InsnList');
  var VarInsnNode = Java.type('org.objectweb.asm.tree.VarInsnNode');
  var MethodInsnNode = Java.type('org.objectweb.asm.tree.MethodInsnNode');
  function probe(node, methodName, descriptor, callback) {
    var found = 0;
    Java.from(node.methods).forEach(function(method) {
      if (method.name !== methodName || method.desc !== descriptor) return;
      found++;
      var instruction = method.instructions.getFirst();
      while (instruction !== null) {
        var next = instruction.getNext();
        if (instruction.getOpcode() === O.RETURN) {
          var tail = new InsnList();
          tail.add(new VarInsnNode(O.ALOAD, 0));
          tail.add(new MethodInsnNode(O.INVOKESTATIC, 'CHECKS', callback, '(Ljava/lang/Object;)V', false));
          method.instructions.insertBefore(instruction, tail);
        }
        instruction = next;
      }
      method.maxStack = Math.max(method.maxStack, 1);
    });
    if (found !== 1) throw 'Missing probe method: ' + methodName;
    return node;
  }
  return {
    smoke_tick: {
      target: { type: 'CLASS', name: 'net.minecraft.client.Minecraft' },
      transformer: function(node) { return probe(node, 'func_71407_l', '()V', 'tick'); }
    },
    smoke_frame: {
      target: { type: 'CLASS', name: 'SCREEN' },
      transformer: function(node) { return probe(node, 'render', '(IIF)V', 'rendered'); }
    },
    smoke_window: {
      target: { type: 'CLASS', name: 'net.minecraft.client.MainWindow' },
      transformer: function(node) {
        var creates = 0;
        Java.from(node.methods).forEach(function(method) {
          if (method.name !== '<init>') return;
          var instruction = method.instructions.getFirst();
          while (instruction !== null) {
            var next = instruction.getNext();
            if (instruction.getOpcode() === O.INVOKESTATIC && instruction.owner === 'org/lwjgl/glfw/GLFW' && instruction.name === 'glfwCreateWindow') {
              instruction.owner = 'CHECKS';
              instruction.name = 'createWindow';
              creates++;
            }
            if (instruction.getOpcode() === O.RETURN) {
              method.instructions.insertBefore(instruction, new MethodInsnNode(O.INVOKESTATIC, 'CHECKS', 'placeWindow', '()V', false));
            }
            instruction = next;
          }
        });
        if (creates !== 1) throw 'Missing GLFW window creation';
        return node;
      }
    }
  };
}
""".replace("CHECKS", checks).replace("SCREEN", screen)

"""Generate typed Fabric bridges around the single shared connection lifecycle."""

import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]


def generate(version):
    directory = ROOT / "versions" / ("fabric-" + version)
    suffix = "v" + version.replace(".", "_")
    compat = "fr.bagyette.aternauto.fabric.compat." + suffix
    mixin = "fr.bagyette.aternauto.fabric.mixin." + suffix
    modern = version.startswith("26.")
    split_gui = version in {"26.2", "26.3"}
    legacy = version in {"1.14.4", "1.16.5"}
    record_reason = modern or version.startswith("1.21.")
    client = "Minecraft" if modern else "MinecraftClient"
    screen_package = "net.minecraft.client.gui.screens" if modern else "net.minecraft.client.gui.screen"
    if modern:
        connection_package = screen_package
    else:
        mappings = (ROOT / ".tools" / ("yarn-" + version + ".tiny")).read_text()
        connection_class = next(line.split("\t")[-1] for line in mappings.splitlines()
                                if line.startswith("c\t") and line.endswith("/ConnectScreen"))
        connection_package = connection_class.rsplit("/", 1)[0].replace("/", ".")
    text_type = "Component" if modern else "Text"
    text_import = "net.minecraft.network.chat.Component" if modern else "net.minecraft.text.Text"
    details = "DisconnectionDetails" if modern else "DisconnectionInfo"
    field = "details" if modern else "info" if record_reason else "reason"
    accessor_type = details if record_reason else text_type
    client_instance = client + ".getInstance()"
    current = ".gui.screen()" if split_gui else ".screen" if modern else ".currentScreen"
    setter = ".gui.setScreen" if split_gui else ".openScreen" if legacy else ".setScreen"
    world = "level" if modern else "world"
    reason = "aternauto$getReason()" + (".reason()" if record_reason else "") + ".getString()"

    def write(package, name, source):
        path = directory / "src/main/java" / Path(package.replace(".", "/")) / (name + ".java")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("package " + package + ";\n\n" + source, encoding="utf-8")

    write(compat, "RetryConnection", f"""import fr.bagyette.aternauto.common.ConnectionFlow;
import {mixin}.DisconnectedScreenMixin;
import net.minecraft.client.{client};
import {screen_package}.Screen;
import {screen_package}.DisconnectedScreen;
import {connection_package}.ConnectScreen;

/** Typed Minecraft bridge; the retry and reporting policy lives in common. */
public final class RetryConnection {{
  private static final ConnectionFlow<Screen> FLOW = new ConnectionFlow<>(
      () -> {client_instance}{current},
      () -> {client_instance}.{world} != null,
      screen -> screen instanceof ConnectScreen,
      screen -> screen instanceof DisconnectedScreen
          ? ((DisconnectedScreenMixin) screen).{reason} : null);

  private RetryConnection() {{}}

  public static void begin(String host, int port, Runnable connect) {{ FLOW.begin(host, port, connect); }}
  public static void clear() {{ FLOW.clear(); }}
  public static boolean interceptScreen(Screen next) {{ return FLOW.intercept(next); }}
  public static void tick() {{ FLOW.tick(); }}
  public static boolean canReport(Screen screen) {{ return FLOW.report(screen) != null; }}
  public static void openReport(Screen screen) {{
    ConnectionFlow.Target target = FLOW.report(screen);
    if (target != null) {{
      {client_instance}{setter}(RequestScreen.forFailure(screen, target.host, target.port, target.failure));
    }}
  }}
}}
""")
    reason_import = f"import net.minecraft.network.{details};" if record_reason else f"import {text_import};"
    write(mixin, "DisconnectedScreenMixin", f"""import {screen_package}.DisconnectedScreen;
{reason_import}
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.gen.Accessor;

@Mixin(DisconnectedScreen.class)
public interface DisconnectedScreenMixin {{
  @Accessor("{field}")
  {accessor_type} aternauto$getReason();
}}
""")
    write(mixin, "RetryClientMixin", f"""import {compat}.RetryConnection;
import net.minecraft.client.{client};
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

@Mixin({client}.class)
public abstract class RetryClientMixin {{
  @Inject(method = "tick", at = @At("HEAD"))
  private void tickRetry(CallbackInfo ci) {{ RetryConnection.tick(); }}
}}
""")
    target_import = "net.minecraft.client.gui.Gui" if split_gui else "net.minecraft.client." + client
    target_class = "Gui" if split_gui else client
    method = "openScreen" if legacy else "setScreen"
    write(mixin, "ScreenChangeMixin", f"""import {compat}.RetryConnection;
import {target_import};
import {screen_package}.Screen;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

@Mixin({target_class}.class)
public abstract class ScreenChangeMixin {{
  @Inject(method = "{method}", at = @At("HEAD"), cancellable = true)
  private void interceptScreen(Screen screen, CallbackInfo ci) {{
    if (RetryConnection.interceptScreen(screen)) {{ ci.cancel(); }}
  }}
}}
""")
    label = 'messages.text("report.button")'
    button_type = "Button" if modern else "ButtonWidget"
    button_import = "net.minecraft.client.gui.components.Button" if modern else "net.minecraft.client.gui.widget.ButtonWidget"
    if version == "1.14.4":
        button = f"addButton(new ButtonWidget(width / 2 - 100, height - 28, 200, 20, {label}, button -> RetryConnection.openReport(screen)))"
    elif version in {"1.16.5", "1.18.2", "1.19.2"}:
        construct = "new LiteralText" if version != "1.19.2" else "Text.literal"
        adder = "addButton" if legacy else "addDrawableChild"
        button = f"{adder}(new ButtonWidget(width / 2 - 100, height - 28, 200, 20, {construct}({label}), button -> RetryConnection.openReport(screen)))"
    else:
        adder = "addRenderableWidget" if modern else "addDrawableChild"
        bounds = "bounds" if modern else "dimensions"
        button = f"{adder}({button_type}.builder({text_type}.literal({label}), button -> RetryConnection.openReport(screen)).{bounds}(width / 2 - 100, height - 28, 200, 20).build())"
    literal_import = "import net.minecraft.text.LiteralText;" if version in {"1.16.5", "1.18.2"} else ""
    language = "languageCode" if modern else "language"
    write(mixin, "ReportDisconnectedMixin", f"""import fr.bagyette.aternauto.common.Messages;
import {compat}.RetryConnection;
import net.minecraft.client.{client};
import {screen_package}.Screen;
import {screen_package}.DisconnectedScreen;
import {button_import};
import {text_import};
{literal_import}
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

@Mixin(DisconnectedScreen.class)
public abstract class ReportDisconnectedMixin extends Screen {{
  protected ReportDisconnectedMixin({text_type} title) {{ super(title); }}

  @Inject(method = "init", at = @At("TAIL"))
  private void addReportButton(CallbackInfo ci) {{
    Screen screen = this;
    if (RetryConnection.canReport(screen)) {{
      Messages messages = new Messages({client_instance}.options.{language});
      {button};
    }}
  }}
}}
""")
    screen_path = directory / "src/main/java" / Path(compat.replace(".", "/")) / "RequestScreen.java"
    source = screen_path.read_text(encoding="utf-8")
    if "static RequestScreen forFailure" not in source:
        insertion = """  public static RequestScreen forFailure(Screen parent, String host, int port, FailureKind failure) {
    RequestScreen screen = new RequestScreen(parent, host, port, () -> {});
    screen.connectionFailure = failure;
    return screen;
  }

"""
        source = source.replace("  @Override\n  protected void init()", insertion + "  @Override\n  protected void init()")
    source = re.sub(r"    resumed = true;\n    if \(task != null\) \{\n      task.cancel\(\);\n    }\n    ConnectGuard.run\(connect\);",
                    """    resumed = true;
    if (task != null && task.accepted()) {
      RetryConnection.begin(host, port, connect);
    } else {
      if (task != null) { task.cancel(); }
      ConnectGuard.run(connect);
    }""", source)
    screen_path.write_text(source, encoding="utf-8")
    connection_path = directory / "src/main/java" / Path(mixin.replace(".", "/")) / "ConnectionMixin.java"
    source = connection_path.read_text(encoding="utf-8")
    source = re.sub(r"import net\.minecraft\.client\.gui\.screen(?:\.multiplayer)?\.ConnectScreen;",
                    f"import {connection_package}.ConnectScreen;", source)
    if f"import {compat}.RetryConnection;" not in source:
        source = source.replace(f"import {compat}.RequestScreen;", f"import {compat}.RequestScreen;\nimport {compat}.RetryConnection;")
    # Reset any earlier attempt for a new manually requested connection, never for its retry.
    if "RetryConnection.clear();" not in source:
        source = re.sub(r"(CallbackInfo ci\) \{)\n", r"\1\n    if (!ConnectGuard.bypassed()) { RetryConnection.clear(); }\n", source)
    connection_path.write_text(source, encoding="utf-8")
    spec_path = directory / "version.json"
    spec = json.loads(spec_path.read_text())
    required = json.loads((ROOT / "compatibility-v2.json").read_text())["requiredFeatures"]
    spec["features"] = required
    spec_path.write_text(json.dumps(spec, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    for directory in sorted((ROOT / "versions").glob("fabric-*")):
        generate(directory.name.removeprefix("fabric-"))

"""Generate the small, typed Minecraft adapters from the inspected API families."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
metadata = json.loads((ROOT / ".tools/versions.json").read_text())
by_version = {item["minecraft"]: item for item in metadata}
base_package = "fr.bagyette.aternauto.compat"
index = {}


def write(project, package, name, source):
    path = ROOT / "versions" / project / "src/main/java" / Path(package.replace(".", "/")) / (name + ".java")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source, encoding="utf-8")


for version in ["1.14.4", "1.16.5", "1.18.2", "1.19.4", "1.20.1", "1.21.1", "1.21.9", "1.21.11", "26.1", "26.2", "26.3"]:
    project = "fabric-" + version
    folder = ROOT / "versions" / project
    folder.mkdir(parents=True, exist_ok=True)
    spec = {**by_version[version], "loader": "fabric"}
    (folder / "version.json").write_text(json.dumps(spec, indent=2), encoding="utf-8")
    suffix = "v" + version.replace(".", "_")
    package = base_package + "." + suffix
    legacy = version in ("1.14.4", "1.16.5")
    supported = [version]
    if version == "26.1":
        supported += ["26.1.1", "26.1.2"]
    if version == "1.21.9":
        supported += ["1.21.10"]
    for supported_version in supported:
        index[supported_version] = {"package": suffix, "legacy": legacy}

    modern = version.startswith("26.")
    if modern:
        imports = """import net.minecraft.client.Minecraft;
import net.minecraft.client.User;
import net.minecraft.client.gui.GuiGraphics;
import net.minecraft.client.gui.components.Button;
import net.minecraft.client.gui.screens.Screen;
import net.minecraft.network.chat.Component;"""
        client = "Minecraft.getInstance()"
        session = "User session = client.getUser();"
        session_id = "session.getProfileId()"
        username = "session.getName()"
        text = lambda value: f'Component.literal("{value}")'
        button = lambda value, action, offset: f'addRenderableWidget(Button.builder({text(value)}, button -> {action}).bounds(width / 2 - 100, height / 2 + {offset}, 200, 20).build())'
        button_type = "Button"
        client_type = "Minecraft"
        screen_field = "screen"
        set_screen = "setScreen"
        font = "font"
        close_method = "onClose"
        render_signature = "GuiGraphics graphics, int mouseX, int mouseY, float delta"
        render_args = "graphics, mouseX, mouseY, delta"
        draw_center = lambda value, y: f'graphics.drawCenteredString(font, {value}, width / 2, {y}, 0xFFFFFFFF);'
        draw_credit = 'graphics.drawString(font, RequestTask.CREDIT, 4, height - 12, 0xFFAAAAAA);'
        render_background = "renderBackground(graphics, mouseX, mouseY, delta);"
    else:
        draw_context = version not in ("1.14.4", "1.16.5", "1.18.2", "1.19.4")
        matrix = version in ("1.16.5", "1.18.2", "1.19.4")
        session_package = "net.minecraft.client.session" if version.startswith("1.21") else "net.minecraft.client.util"
        imports = f"""import net.minecraft.client.MinecraftClient;
import {session_package}.Session;
import net.minecraft.client.gui.screen.Screen;
import net.minecraft.client.gui.widget.ButtonWidget;
import net.minecraft.text.Text;"""
        if version in ("1.14.4", "1.16.5", "1.18.2"):
            imports += "\nimport net.minecraft.text.LiteralText;"
        if matrix:
            imports += "\nimport net.minecraft.client.util.math.MatrixStack;"
        if draw_context:
            imports += "\nimport net.minecraft.client.gui.DrawContext;"
        client = "MinecraftClient.getInstance()"
        session = "Session session = client.getSession();"
        session_id = "session.getUuidOrNull()" if version not in ("1.14.4", "1.16.5", "1.18.2") else "SessionIds.parse(session.getUuid())"
        username = "session.getUsername()"
        text = lambda value: f'new LiteralText("{value}")' if version in ("1.14.4", "1.16.5", "1.18.2") else f'Text.literal("{value}")'
        adder = "addButton" if legacy else "addDrawableChild"
        if version in ("1.14.4", "1.16.5", "1.18.2"):
            button = lambda value, action, offset: f'{adder}(new ButtonWidget(width / 2 - 100, height / 2 + {offset}, 200, 20, ' + (f'"{value}"' if version == "1.14.4" else text(value)) + f', button -> {action}))'
        else:
            button = lambda value, action, offset: f'{adder}(ButtonWidget.builder({text(value)}, button -> {action}).dimensions(width / 2 - 100, height / 2 + {offset}, 200, 20).build())'
        button_type = "ButtonWidget"
        client_type = "MinecraftClient"
        screen_field = "currentScreen"
        set_screen = "openScreen" if legacy else "setScreen"
        font = "textRenderer"
        close_method = "onClose" if version == "1.16.5" else "close"
        render_signature = ("DrawContext graphics, " if draw_context else "MatrixStack matrices, " if matrix else "") + "int mouseX, int mouseY, float delta"
        render_args = ("graphics, " if draw_context else "matrices, " if matrix else "") + "mouseX, mouseY, delta"
        draw_center = lambda value, y: (f'graphics.drawCenteredTextWithShadow(textRenderer, {value}, width / 2, {y}, 0xFFFFFFFF);' if draw_context else f'drawCenteredText(matrices, textRenderer, {value}, width / 2, {y}, 0xFFFFFFFF);' if matrix else f'drawCenteredString(textRenderer, {value}, width / 2, {y}, 0xFFFFFFFF);')
        draw_credit = ('graphics.drawTextWithShadow(textRenderer, RequestTask.CREDIT, 4, height - 12, 0xFFAAAAAA);' if draw_context else 'drawStringWithShadow(matrices, textRenderer, RequestTask.CREDIT, 4, height - 12, 0xFFAAAAAA);' if matrix else 'drawString(textRenderer, RequestTask.CREDIT, 4, height - 12, 0xFFAAAAAA);')
        render_background = "renderBackground(graphics, mouseX, mouseY, delta);" if version.startswith("1.21") else "renderBackground(graphics);" if draw_context else "renderBackground(matrices);" if matrix else "renderBackground(0);"

    close_override = f"@Override public void {close_method}() {{ cancel(); }}"
    removed_override = "@Override public void removed() { if (task != null) { task.cancel(); } }"
    if version == "1.14.4":
        close_override = """@Override public boolean keyPressed(int key, int scanCode, int modifiers) {
  if (key == 256) { cancel(); return true; }
  return super.keyPressed(key, scanCode, modifiers);
}"""
        removed_override = "@Override public void removed() { if (task != null) { task.cancel(); } }"

    screen = f"""package {package};

import fr.autoaternos.ConnectGuard;
import fr.autoaternos.RequestTask;
import fr.autoaternos.SessionIds;
{imports}

/** Minecraft {version} adapter for the shared AternAuto request state. */
public final class RequestScreen extends Screen {{
  private final Screen parent;
  private final String host;
  private final Runnable connect;
  private RequestTask task;
  private {button_type} continueButton;
  private boolean resumed;

  public RequestScreen(Screen parent, String host, Runnable connect) {{
    super({text('AternAuto')});
    this.parent = parent;
    this.host = host;
    this.connect = connect;
  }}

  @Override protected void init() {{
    {button('Annuler', 'cancel()', 45)};
    continueButton = {button('Se connecter quand même', 'resume()', 20)};
    continueButton.visible = task != null && task.complete() && !task.accepted();
    if (task != null) {{ return; }}
    {client_type} client = {client};
    {session}
    task = new RequestTask(host, {session_id}, {username}, session.getAccessToken());
    task.start();
  }}

  @Override public void tick() {{
    if (task == null || !task.complete() || resumed) {{ return; }}
    if (task.accepted()) {{ resume(); }} else {{ continueButton.visible = true; }}
  }}

  private void resume() {{
    if (resumed) {{ return; }}
    resumed = true;
    ConnectGuard.run(connect);
  }}

  private void cancel() {{
    if (task != null) {{ task.cancel(); }}
    {client}.{set_screen}(parent);
  }}

  {close_override}
  {removed_override}

  @Override public void render({render_signature}) {{
    {render_background}
    super.render({render_args});
    {draw_center('"AternAuto"', 'height / 2 - 45')}
    String status = task == null ? "Vérification du compte Minecraft…" : task.status();
    int lineY = height / 2 - 20;
    for (String line : RequestTask.wrap(status, width - 40, {font}::{'width' if modern else 'getWidth'})) {{
      {draw_center('line', 'lineY')}
      lineY += 10;
    }}
    {draw_credit}
  }}
}}
"""
    language_code = "Minecraft.getInstance().options.languageCode" if modern else "MinecraftClient.getInstance().options.language"
    screen = screen.replace("import fr.autoaternos.RequestTask;", "import fr.autoaternos.RequestTask;\nimport fr.autoaternos.Messages;")
    screen = screen.replace("  private final Runnable connect;", "  private final Runnable connect;\n  private final Messages messages;")
    screen = screen.replace("    this.connect = connect;", "    this.connect = connect;\n    this.messages = new Messages(" + language_code + ");")
    screen = screen.replace('"Annuler"', 'messages.text("button.cancel")')
    screen = screen.replace('"Se connecter quand même"', 'messages.text("button.connect_anyway")')
    screen = screen.replace('"Vérification du compte Minecraft…"', 'messages.text("status.verifying")')
    screen = screen.replace("session.getAccessToken());", "session.getAccessToken(), messages);")
    if modern:
        screen = screen.replace("GuiGraphics", "GuiGraphicsExtractor")
        screen = screen.replace("void render(", "void extractRenderState(")
        screen = screen.replace("super.render(", "super.extractRenderState(")
        screen = screen.replace("renderBackground(", "extractBackground(")
        screen = screen.replace("drawCenteredString(", "centeredText(")
        screen = screen.replace("drawString(", "text(")
        screen = screen.replace(".setScreen(", "." + ("setScreen" if version == "26.1" else "gui.setScreen") + "(")
        screen = screen.replace("    extractBackground(graphics, mouseX, mouseY, delta);\n", "")
    if version in ("1.21.9", "1.21.11"):
        screen = screen.replace("    renderBackground(graphics, mouseX, mouseY, delta);\n", "")
    if version == "1.14.4":
        screen = screen.replace("textRenderer", "font").replace("font::getWidth", "font::getStringWidth")
    if version == "1.19.4":
        screen = screen.replace("drawCenteredText(", "drawCenteredTextWithShadow(")
        screen = screen.replace("drawStringWithShadow(", "drawTextWithShadow(")
    write(project, package, "RequestScreen", screen)

    if modern:
        connection_imports = """import net.minecraft.client.Minecraft;
import net.minecraft.client.gui.screens.ConnectScreen;
import net.minecraft.client.gui.screens.Screen;
import net.minecraft.client.multiplayer.ServerData;
import net.minecraft.client.multiplayer.TransferState;
import net.minecraft.client.multiplayer.resolver.ServerAddress;"""
        signature = "Screen parent, Minecraft client, ServerAddress address, ServerData serverData, boolean quickPlay, TransferState transfer, CallbackInfo ci"
        method = "startConnecting"
        condition = "ConnectGuard.bypassed() || transfer != null || !DawnApi.isSupportedHost(address.getHost())"
        connect = "ConnectScreen.startConnecting(parent, client, address, serverData, quickPlay, transfer)"
        host = "address.getHost()"
    elif not legacy:
        connect_screen = "net.minecraft.client.gui.screen.multiplayer.ConnectScreen" if version.startswith("1.21") else "net.minecraft.client.gui.screen.ConnectScreen"
        connection_imports = f"""import net.minecraft.client.MinecraftClient;
import {connect_screen};
import net.minecraft.client.gui.screen.Screen;
import net.minecraft.client.network.ServerAddress;
import net.minecraft.client.network.ServerInfo;"""
        args = "parent, client, address, serverData"
        signature = "Screen parent, MinecraftClient client, ServerAddress address, ServerInfo serverData"
        condition = "ConnectGuard.bypassed() || !DawnApi.isSupportedHost(address.getAddress())"
        if version not in ("1.18.2", "1.19.4"):
            args += ", quickPlay"
            signature += ", boolean quickPlay"
        if version.startswith("1.21"):
            connection_imports += "\nimport net.minecraft.client.network.CookieStorage;"
            signature += ", CookieStorage transfer"
            args += ", transfer"
            condition = "transfer != null || " + condition
        signature += ", CallbackInfo ci"
        method = "connect"
        connect = "ConnectScreen.connect(" + args + ")"
        host = "address.getAddress()"
    if not legacy:
        write(project, package, "ConnectionMixin", f"""package {package};
import fr.autoaternos.ConnectGuard;
import fr.autoaternos.DawnApi;
{connection_imports}
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

@Mixin(ConnectScreen.class)
public abstract class ConnectionMixin {{
  @Inject(method = "{method}(L{'net/minecraft/client/gui/screens/Screen;Lnet/minecraft/client/Minecraft;Lnet/minecraft/client/multiplayer/resolver/ServerAddress;Lnet/minecraft/client/multiplayer/ServerData;ZLnet/minecraft/client/multiplayer/TransferState;' if modern else 'net/minecraft/client/gui/screen/Screen;Lnet/minecraft/client/MinecraftClient;Lnet/minecraft/client/network/ServerAddress;Lnet/minecraft/client/network/ServerInfo;' + ('' if version in ('1.18.2','1.19.4') else 'Z') + ('Lnet/minecraft/client/network/CookieStorage;' if version.startswith('1.21') else '')})V", at = @At("HEAD"), cancellable = true)
  private static void intercept({signature}) {{
    if ({condition}) {{ return; }}
    ci.cancel();
    client.{'gui.setScreen' if modern and version != '26.1' else 'setScreen'}(new RequestScreen(parent, {host}, () -> {connect}));
  }}
}}
""")
    else:
        write(project, package, "ConnectionMixin", f"""package {package};
import fr.autoaternos.ConnectGuard;
import fr.autoaternos.DawnApi;
import net.minecraft.client.MinecraftClient;
import net.minecraft.client.gui.screen.ConnectScreen;
import net.minecraft.client.gui.screen.Screen;
import org.spongepowered.asm.mixin.Final;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Shadow;
import org.spongepowered.asm.mixin.gen.Invoker;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

@Mixin(ConnectScreen.class)
public abstract class ConnectionMixin {{
  @Shadow @Final private Screen parent;
  @Invoker("connect") public abstract void invokeConnect(String host, int port);

  @Inject(method = "connect", at = @At("HEAD"), cancellable = true)
  private void intercept(String host, int port, CallbackInfo ci) {{
    if (ConnectGuard.bypassed() || !DawnApi.isSupportedHost(host)) {{ return; }}
    Screen original = (Screen) (Object) this;
    PendingConnection.defer(original, new RequestScreen(parent, host, () -> {{
      MinecraftClient.getInstance().openScreen(original);
      invokeConnect(host, port);
    }}));
    ci.cancel();
  }}
}}
""")
        write(project, package, "PendingConnection", f"""package {package};
import net.minecraft.client.MinecraftClient;
import net.minecraft.client.gui.screen.Screen;

/** Waits until the constructor's caller has opened the original connection screen. */
public final class PendingConnection {{
  private static Screen original;
  private static Screen replacement;
  private PendingConnection() {{}}
  public static void defer(Screen screen, Screen requestScreen) {{ original = screen; replacement = requestScreen; }}
  public static void tick() {{
    Screen requestScreen = replacement;
    Screen connectionScreen = original;
    replacement = null;
    original = null;
    MinecraftClient client = MinecraftClient.getInstance();
    if (requestScreen != null && client.currentScreen == connectionScreen) {{ client.openScreen(requestScreen); }}
  }}
}}
""")
        write(project, package, "ClientTickMixin", f"""package {package};
import net.minecraft.client.MinecraftClient;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;
@Mixin(MinecraftClient.class)
public abstract class ClientTickMixin {{
  @Inject(method = "tick", at = @At("HEAD"))
  private void interceptTick(CallbackInfo ci) {{ PendingConnection.tick(); }}
}}
""")

(ROOT / "versions/forge").mkdir(parents=True, exist_ok=True)
(ROOT / "versions/forge/version.json").write_text(json.dumps({"loader": "forge", "minecraft": "1.8.9", "java": 8}), encoding="utf-8")
resources = ROOT / "src/main/resources"
(resources / "aternauto-adapters.json").write_text(json.dumps(index, indent=2), encoding="utf-8")
(resources / "auto_aternos_start.mixins.json").unlink(missing_ok=True)
(resources / "aternauto.mixins.json").write_text(json.dumps({"required": True, "package": base_package, "plugin": "fr.autoaternos.AdapterPlugin", "compatibilityLevel": "JAVA_8", "client": [], "injectors": {"defaultRequire": 1}}, indent=2), encoding="utf-8")
(resources / "fabric.mod.json").write_text(json.dumps({"schemaVersion": 1, "id": "aternauto", "version": "1", "name": "AternAuto", "authors": ["Bagyette0"], "description": "Démarrage Aternos lors de la connexion, via le protocole Dawn.", "environment": "client", "mixins": ["aternauto.mixins.json"], "depends": {"fabricloader": ">=0.16.14", "minecraft": sorted(index), "java": ">=8"}, "breaks": {"dawn": "*", "feather": "*", "auto_aternos_start": "*"}}, ensure_ascii=False, indent=2), encoding="utf-8")

# Only annotated mixin classes belong under the mixin configuration's package.
# Ordinary screens and helpers must remain outside it or Knot rejects their loading.
for folder in (ROOT / "versions").glob("fabric-*/src/main/java"):
    for path in list(folder.rglob("*Mixin.java")):
        source = path.read_text(encoding="utf-8")
        old_package = source.split("package ", 1)[1].split(";", 1)[0]
        if ".compat." not in old_package:
            continue
        new_package = old_package.replace(".compat.", ".mixin.")
        source = source.replace("package " + old_package + ";", "package " + new_package + ";")
        helper = "PendingConnection" if path.name == "ClientTickMixin.java" else "RequestScreen"
        source = source.replace("import fr.autoaternos.ConnectGuard;", "import " + old_package + "." + helper + ";\nimport fr.autoaternos.ConnectGuard;") if path.name != "ClientTickMixin.java" else source.replace("import net.minecraft.client.MinecraftClient;", "import " + old_package + ".PendingConnection;\nimport net.minecraft.client.MinecraftClient;")
        if path.name == "ConnectionMixin.java" and "PendingConnection.defer" in source:
            source = source.replace("import fr.autoaternos.ConnectGuard;", "import " + old_package + ".PendingConnection;\nimport fr.autoaternos.ConnectGuard;")
        destination = folder / Path(new_package.replace(".", "/")) / path.name
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(source, encoding="utf-8")
        path.unlink()
(resources / "aternauto.mixins.json").write_text(json.dumps({"required": True, "package": "fr.bagyette.aternauto.mixin", "plugin": "fr.autoaternos.AdapterPlugin", "compatibilityLevel": "JAVA_8", "client": [], "injectors": {"defaultRequire": 1}}, indent=2), encoding="utf-8")
print("Generated", len(index), "Fabric version bindings with", len(set(item['package'] for item in index.values())), "adapters.")

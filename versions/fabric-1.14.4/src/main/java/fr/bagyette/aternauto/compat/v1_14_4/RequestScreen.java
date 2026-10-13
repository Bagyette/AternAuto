package fr.bagyette.aternauto.compat.v1_14_4;

import fr.autoaternos.ConnectGuard;
import fr.autoaternos.Messages;
import fr.autoaternos.RequestTask;
import fr.autoaternos.SessionIds;
import net.minecraft.client.MinecraftClient;
import net.minecraft.client.gui.screen.Screen;
import net.minecraft.client.gui.widget.ButtonWidget;
import net.minecraft.client.util.Session;
import net.minecraft.text.LiteralText;

/** Minecraft 1.14.4 adapter for the shared AternAuto request state. */
public final class RequestScreen extends Screen {
  private final Screen parent;
  private final String host;
  private final Runnable connect;
  private final Messages messages;
  private RequestTask task;
  private ButtonWidget continueButton;
  private boolean resumed;

  public RequestScreen(Screen parent, String host, Runnable connect) {
    super(new LiteralText("AternAuto"));
    this.parent = parent;
    this.host = host;
    this.connect = connect;
    this.messages = new Messages(MinecraftClient.getInstance().options.language);
  }

  @Override
  protected void init() {
    addButton(
        new ButtonWidget(
            width / 2 - 100,
            height / 2 + 45,
            200,
            20,
            messages.text("button.cancel"),
            button -> cancel()));
    continueButton =
        addButton(
            new ButtonWidget(
                width / 2 - 100,
                height / 2 + 20,
                200,
                20,
                messages.text("button.connect_anyway"),
                button -> resume()));
    continueButton.visible = task != null && task.complete() && !task.accepted();
    if (task != null) {
      return;
    }
    MinecraftClient client = MinecraftClient.getInstance();
    Session session = client.getSession();
    task =
        new RequestTask(
            host,
            SessionIds.parse(session.getUuid()),
            session.getUsername(),
            session.getAccessToken(),
            messages);
    task.start();
  }

  @Override
  public void tick() {
    if (task == null || !task.complete() || resumed) {
      return;
    }
    if (task.accepted()) {
      resume();
    } else {
      continueButton.visible = true;
    }
  }

  private void resume() {
    if (resumed) {
      return;
    }
    resumed = true;
    ConnectGuard.run(connect);
  }

  private void cancel() {
    if (task != null) {
      task.cancel();
    }
    MinecraftClient.getInstance().openScreen(parent);
  }

  @Override
  public boolean keyPressed(int key, int scanCode, int modifiers) {
    if (key == 256) {
      cancel();
      return true;
    }
    return super.keyPressed(key, scanCode, modifiers);
  }

  @Override
  public void removed() {
    if (task != null) {
      task.cancel();
    }
  }

  @Override
  public void render(int mouseX, int mouseY, float delta) {
    renderBackground(0);
    super.render(mouseX, mouseY, delta);
    drawCenteredString(font, "AternAuto", width / 2, height / 2 - 45, 0xFFFFFFFF);
    String status = task == null ? messages.text("status.verifying") : task.status();
    int lineY = height / 2 - 20;
    for (String line : RequestTask.wrap(status, width - 40, font::getStringWidth)) {
      drawCenteredString(font, line, width / 2, lineY, 0xFFFFFFFF);
      lineY += 10;
    }
    drawString(font, RequestTask.CREDIT, 4, height - 12, 0xFFAAAAAA);
  }
}

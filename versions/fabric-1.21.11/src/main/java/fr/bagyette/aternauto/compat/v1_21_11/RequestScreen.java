package fr.bagyette.aternauto.compat.v1_21_11;

import fr.autoaternos.ConnectGuard;
import fr.autoaternos.Messages;
import fr.autoaternos.RequestTask;
import net.minecraft.client.MinecraftClient;
import net.minecraft.client.gui.DrawContext;
import net.minecraft.client.gui.screen.Screen;
import net.minecraft.client.gui.widget.ButtonWidget;
import net.minecraft.client.session.Session;
import net.minecraft.text.Text;

/** Minecraft 1.21.11 adapter for the shared AternAuto request state. */
public final class RequestScreen extends Screen {
  private final Screen parent;
  private final String host;
  private final Runnable connect;
  private final Messages messages;
  private RequestTask task;
  private ButtonWidget continueButton;
  private boolean resumed;

  public RequestScreen(Screen parent, String host, Runnable connect) {
    super(Text.literal("AternAuto"));
    this.parent = parent;
    this.host = host;
    this.connect = connect;
    this.messages = new Messages(MinecraftClient.getInstance().options.language);
  }

  @Override
  protected void init() {
    addDrawableChild(
        ButtonWidget.builder(Text.literal(messages.text("button.cancel")), button -> cancel())
            .dimensions(width / 2 - 100, height / 2 + 45, 200, 20)
            .build());
    continueButton =
        addDrawableChild(
            ButtonWidget.builder(
                    Text.literal(messages.text("button.connect_anyway")), button -> resume())
                .dimensions(width / 2 - 100, height / 2 + 20, 200, 20)
                .build());
    continueButton.visible = task != null && task.complete() && !task.accepted();
    if (task != null) {
      return;
    }
    MinecraftClient client = MinecraftClient.getInstance();
    Session session = client.getSession();
    task =
        new RequestTask(
            host,
            session.getUuidOrNull(),
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
    MinecraftClient.getInstance().setScreen(parent);
  }

  @Override
  public void close() {
    cancel();
  }

  @Override
  public void removed() {
    if (task != null) {
      task.cancel();
    }
  }

  @Override
  public void render(DrawContext graphics, int mouseX, int mouseY, float delta) {
    super.render(graphics, mouseX, mouseY, delta);
    graphics.drawCenteredTextWithShadow(
        textRenderer, "AternAuto", width / 2, height / 2 - 45, 0xFFFFFFFF);
    String status = task == null ? messages.text("status.verifying") : task.status();
    int lineY = height / 2 - 20;
    for (String line : RequestTask.wrap(status, width - 40, textRenderer::getWidth)) {
      graphics.drawCenteredTextWithShadow(textRenderer, line, width / 2, lineY, 0xFFFFFFFF);
      lineY += 10;
    }
    graphics.drawTextWithShadow(textRenderer, RequestTask.CREDIT, 4, height - 12, 0xFFAAAAAA);
  }
}

package fr.bagyette.aternauto.compat.v26_1;

import fr.autoaternos.ConnectGuard;
import fr.autoaternos.Messages;
import fr.autoaternos.RequestTask;
import net.minecraft.client.Minecraft;
import net.minecraft.client.User;
import net.minecraft.client.gui.GuiGraphicsExtractor;
import net.minecraft.client.gui.components.Button;
import net.minecraft.client.gui.screens.Screen;
import net.minecraft.network.chat.Component;

/** Minecraft 26.1 adapter for the shared AternAuto request state. */
public final class RequestScreen extends Screen {
  private final Screen parent;
  private final String host;
  private final Runnable connect;
  private final Messages messages;
  private RequestTask task;
  private Button continueButton;
  private boolean resumed;

  public RequestScreen(Screen parent, String host, Runnable connect) {
    super(Component.literal("AternAuto"));
    this.parent = parent;
    this.host = host;
    this.connect = connect;
    this.messages = new Messages(Minecraft.getInstance().options.languageCode);
  }

  @Override
  protected void init() {
    addRenderableWidget(
        Button.builder(Component.literal(messages.text("button.cancel")), button -> cancel())
            .bounds(width / 2 - 100, height / 2 + 45, 200, 20)
            .build());
    continueButton =
        addRenderableWidget(
            Button.builder(
                    Component.literal(messages.text("button.connect_anyway")), button -> resume())
                .bounds(width / 2 - 100, height / 2 + 20, 200, 20)
                .build());
    continueButton.visible = task != null && task.complete() && !task.accepted();
    if (task != null) {
      return;
    }
    Minecraft client = Minecraft.getInstance();
    User session = client.getUser();
    task =
        new RequestTask(
            host, session.getProfileId(), session.getName(), session.getAccessToken(), messages);
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
    Minecraft.getInstance().setScreen(parent);
  }

  @Override
  public void onClose() {
    cancel();
  }

  @Override
  public void removed() {
    if (task != null) {
      task.cancel();
    }
  }

  @Override
  public void extractRenderState(
      GuiGraphicsExtractor graphics, int mouseX, int mouseY, float delta) {
    super.extractRenderState(graphics, mouseX, mouseY, delta);
    graphics.centeredText(font, "AternAuto", width / 2, height / 2 - 45, 0xFFFFFFFF);
    String status = task == null ? messages.text("status.verifying") : task.status();
    int lineY = height / 2 - 20;
    for (String line : RequestTask.wrap(status, width - 40, font::width)) {
      graphics.centeredText(font, line, width / 2, lineY, 0xFFFFFFFF);
      lineY += 10;
    }
    graphics.text(font, RequestTask.CREDIT, 4, height - 12, 0xFFAAAAAA);
  }
}

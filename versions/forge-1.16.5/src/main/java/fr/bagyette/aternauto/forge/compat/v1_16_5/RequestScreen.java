package fr.bagyette.aternauto.forge.compat.v1_16_5;

import com.mojang.blaze3d.vertex.PoseStack;
import fr.bagyette.aternauto.common.ConnectGuard;
import fr.bagyette.aternauto.common.FailureKind;
import fr.bagyette.aternauto.common.Messages;
import fr.bagyette.aternauto.common.ReportPrompt;
import fr.bagyette.aternauto.common.RequestTask;
import net.minecraft.client.Minecraft;
import net.minecraft.client.User;
import net.minecraft.client.gui.components.Button;
import net.minecraft.client.gui.screens.Screen;
import net.minecraft.network.chat.TextComponent;

/** Minecraft 1.16.5 adapter for the shared AternAuto request state. */
public final class RequestScreen extends Screen {
  private final Screen parent;
  private final String host;
  private final int port;
  private final ReportPrompt report;
  private FailureKind connectionFailure;
  private final Runnable connect;
  private final Messages messages;
  private RequestTask task;
  private Button continueButton;
  private Button reportButton;
  private boolean resumed;

  public RequestScreen(Screen parent, String host, int port, Runnable connect) {
    super(new TextComponent("AternAuto"));
    this.parent = parent;
    this.host = host;
    this.port = port;
    this.connect = connect;
    this.messages = new Messages(Minecraft.getInstance().options.languageCode);
    this.report =
        new ReportPrompt(
            messages,
            () ->
                LoaderReports.capture(host, port, failure(), task == null ? 0 : task.httpStatus()));
  }

  public static RequestScreen forFailure(
      Screen parent, String host, int port, FailureKind failure) {
    RequestScreen screen = new RequestScreen(parent, host, port, () -> {});
    screen.connectionFailure = failure;
    return screen;
  }

  @Override
  protected void init() {
    addButton(
        new Button(
            width / 2 - 100,
            height - 33,
            200,
            20,
            new TextComponent(messages.text("button.cancel")),
            button -> cancel()));
    continueButton =
        addButton(
            new Button(
                width / 2 - 100,
                height - 58,
                200,
                20,
                new TextComponent(messages.text("button.connect_anyway")),
                button -> resume()));
    continueButton.visible = true;
    reportButton =
        addButton(
            new Button(
                width / 2 - 100,
                height - 83,
                200,
                20,
                new TextComponent(report.label()),
                button -> report.click()));
    updateButtons();
    if (task != null || connectionFailure != null) {
      return;
    }
    Minecraft client = Minecraft.getInstance();
    User session = client.getUser();
    task =
        new RequestTask(
            host,
            session.getGameProfile().getId(),
            session.getName(),
            session.getAccessToken(),
            messages);
    task.start();
  }

  @Override
  public void tick() {
    updateButtons();
    if (task == null || !task.complete() || resumed) {
      return;
    }
    if (task.accepted()) {
      resume();
    } else {
      updateButtons();
    }
  }

  private FailureKind failure() {
    return connectionFailure != null ? connectionFailure : task == null ? null : task.failure();
  }

  private void updateButtons() {
    FailureKind failure = failure();
    reportButton.visible = failure != null && failure.reportable();
    reportButton.active = report.actionable();
    reportButton.setMessage(new TextComponent(report.label()));
    continueButton.visible = connectionFailure == null && !report.opened();
  }

  private void resume() {
    if (resumed) {
      return;
    }
    resumed = true;
    if (task != null && task.accepted()) {
      RetryConnection.begin(host, port, connect);
    } else {
      if (task != null) {
        task.cancel();
      }
      ConnectGuard.run(connect);
    }
  }

  private void cancel() {
    resumed = true;
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
    resumed = true;
    if (task != null) {
      task.cancel();
    }
  }

  @Override
  public void render(PoseStack matrices, int mouseX, int mouseY, float delta) {
    renderBackground(matrices);
    super.render(matrices, mouseX, mouseY, delta);
    drawCenteredString(matrices, font, "AternAuto", width / 2, 28, 0xFFFFFFFF);
    String status =
        report.opened()
            ? report.status()
            : connectionFailure != null
                ? connectionFailure.message(messages, 0)
                : task == null ? messages.text("status.verifying") : task.status();
    int lineY = 54;
    for (String line :
        (report.opened()
            ? report.lines(width - 40, font::width, (height - 145) / 10)
            : RequestTask.wrap(status, width - 40, font::width))) {
      drawCenteredString(matrices, font, line, width / 2, lineY, 0xFFFFFFFF);
      lineY += 10;
    }
    drawString(matrices, font, RequestTask.CREDIT, 4, height - 12, 0xFFAAAAAA);
  }
}

package fr.bagyette.aternauto.fabric.compat.v1_21_9;

import fr.bagyette.aternauto.common.ConnectGuard;
import fr.bagyette.aternauto.common.FailureKind;
import fr.bagyette.aternauto.common.Messages;
import fr.bagyette.aternauto.common.ReportPrompt;
import fr.bagyette.aternauto.common.RequestTask;
import fr.bagyette.aternauto.fabric.FabricReports;
import net.minecraft.client.MinecraftClient;
import net.minecraft.client.gui.DrawContext;
import net.minecraft.client.gui.screen.Screen;
import net.minecraft.client.gui.widget.ButtonWidget;
import net.minecraft.client.session.Session;
import net.minecraft.text.Text;

/** Minecraft 1.21.9 adapter for the shared AternAuto request state. */
public final class RequestScreen extends Screen {
  private final Screen parent;
  private final String host;
  private final int port;
  private final ReportPrompt report;
  private FailureKind connectionFailure;
  private final Runnable connect;
  private final Messages messages;
  private RequestTask task;
  private ButtonWidget continueButton;
  private ButtonWidget reportButton;
  private boolean resumed;

  public RequestScreen(Screen parent, String host, int port, Runnable connect) {
    super(Text.literal("AternAuto"));
    this.parent = parent;
    this.host = host;
    this.port = port;
    this.connect = connect;
    this.messages = new Messages(MinecraftClient.getInstance().options.language);
    this.report =
        new ReportPrompt(
            messages,
            () ->
                FabricReports.capture(host, port, failure(), task == null ? 0 : task.httpStatus()));
  }

  public static RequestScreen forFailure(
      Screen parent, String host, int port, FailureKind failure) {
    RequestScreen screen = new RequestScreen(parent, host, port, () -> {});
    screen.connectionFailure = failure;
    return screen;
  }

  @Override
  protected void init() {
    addDrawableChild(
        ButtonWidget.builder(Text.literal(messages.text("button.cancel")), button -> cancel())
            .dimensions(width / 2 - 100, height - 33, 200, 20)
            .build());
    continueButton =
        addDrawableChild(
            ButtonWidget.builder(
                    Text.literal(messages.text("button.connect_anyway")), button -> resume())
                .dimensions(width / 2 - 100, height - 58, 200, 20)
                .build());
    continueButton.visible = true;
    reportButton =
        addDrawableChild(
            ButtonWidget.builder(Text.literal(report.label()), button -> report.click())
                .dimensions(width / 2 - 100, height - 83, 200, 20)
                .build());
    updateButtons();
    if (task != null || connectionFailure != null) {
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
    reportButton.setMessage(Text.literal(report.label()));
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
    MinecraftClient.getInstance().setScreen(parent);
  }

  @Override
  public void close() {
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
  public void render(DrawContext graphics, int mouseX, int mouseY, float delta) {
    super.render(graphics, mouseX, mouseY, delta);
    graphics.drawCenteredTextWithShadow(textRenderer, "AternAuto", width / 2, 28, 0xFFFFFFFF);
    String status =
        report.opened()
            ? report.status()
            : connectionFailure != null
                ? connectionFailure.message(messages, 0)
                : task == null ? messages.text("status.verifying") : task.status();
    int lineY = 54;
    for (String line :
        (report.opened()
            ? report.lines(width - 40, textRenderer::getWidth, (height - 145) / 10)
            : RequestTask.wrap(status, width - 40, textRenderer::getWidth))) {
      graphics.drawCenteredTextWithShadow(textRenderer, line, width / 2, lineY, 0xFFFFFFFF);
      lineY += 10;
    }
    graphics.drawTextWithShadow(textRenderer, RequestTask.CREDIT, 4, height - 12, 0xFFAAAAAA);
  }
}

package fr.bagyette.aternauto.forge.legacy1710;

import fr.bagyette.aternauto.common.ConnectGuard;
import fr.bagyette.aternauto.common.FailureKind;
import fr.bagyette.aternauto.common.Messages;
import fr.bagyette.aternauto.common.ReportPrompt;
import fr.bagyette.aternauto.common.RequestTask;
import net.minecraft.client.Minecraft;
import net.minecraft.client.gui.GuiButton;
import net.minecraft.client.gui.GuiScreen;
import net.minecraft.util.Session;

/** Forge 1.8.9/1.12.2 screen using the SRG API shared by both versions. */
public final class RequestScreen extends GuiScreen {
  private final GuiScreen parent;
  private final String host;
  private final int port;
  private final ReportPrompt report;
  private FailureKind connectionFailure;
  private final Runnable connect;
  private final Messages messages;
  private RequestTask task;
  private GuiButton continueButton;
  private GuiButton reportButton;
  private boolean resumed;

  public RequestScreen(GuiScreen parent, String host, int port, Runnable connect) {
    this.parent = parent;
    this.host = host;
    this.port = port;
    this.connect = connect;
    this.messages = new Messages(Minecraft.func_71410_x().field_71474_y.field_74363_ab);
    this.report =
        new ReportPrompt(
            messages,
            () ->
                ForgeReports.capture(host, port, failure(), task == null ? 0 : task.httpStatus()));
  }

  public static RequestScreen forFailure(
      GuiScreen parent, String host, int port, FailureKind failure) {
    RequestScreen screen = new RequestScreen(parent, host, port, () -> {});
    screen.connectionFailure = failure;
    return screen;
  }

  @Override
  public void func_73866_w_() {
    field_146292_n.clear();
    field_146292_n.add(
        new GuiButton(
            0,
            field_146294_l / 2 - 100,
            field_146295_m - 33,
            200,
            20,
            messages.text("button.cancel")));
    continueButton =
        new GuiButton(
            1,
            field_146294_l / 2 - 100,
            field_146295_m - 58,
            200,
            20,
            messages.text("button.connect_anyway"));
    continueButton.field_146125_m = true;
    field_146292_n.add(continueButton);
    reportButton =
        new GuiButton(2, field_146294_l / 2 - 100, field_146295_m - 83, 200, 20, report.label());
    field_146292_n.add(reportButton);
    updateButtons();
    if (task != null || connectionFailure != null) {
      return;
    }
    Session session = Minecraft.func_71410_x().func_110432_I();
    task =
        new RequestTask(
            host,
            session.func_148256_e().getId(),
            session.func_111285_a(),
            session.func_148254_d(),
            messages);
    task.start();
  }

  @Override
  public void func_73876_c() {
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

  @Override
  protected void func_146284_a(GuiButton button) {
    if (button.field_146127_k == 0) {
      cancel();
    } else if (button.field_146127_k == 2) {
      report.click();
    } else {
      resume();
    }
  }

  @Override
  protected void func_73869_a(char typedChar, int keyCode) {
    if (keyCode == 1) {
      cancel();
    }
  }

  @Override
  public void func_146281_b() {
    resumed = true;
    if (task != null) {
      task.cancel();
    }
  }

  private FailureKind failure() {
    return connectionFailure != null ? connectionFailure : task == null ? null : task.failure();
  }

  private void updateButtons() {
    FailureKind failure = failure();
    reportButton.field_146125_m = failure != null && failure.reportable();
    reportButton.field_146124_l = report.actionable();
    reportButton.field_146126_j = report.label();
    continueButton.field_146125_m = connectionFailure == null && !report.opened();
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
    Minecraft.func_71410_x().func_147108_a(parent);
  }

  @Override
  public void func_73863_a(int mouseX, int mouseY, float delta) {
    func_146276_q_();
    super.func_73863_a(mouseX, mouseY, delta);
    func_73732_a(field_146289_q, "AternAuto", field_146294_l / 2, 28, 0xFFFFFFFF);
    String status =
        report.opened()
            ? report.status()
            : connectionFailure != null
                ? connectionFailure.message(messages, 0)
                : task == null ? messages.text("status.verifying") : task.status();
    int lineY = 54;
    for (String line :
        (report.opened()
            ? report.lines(
                field_146294_l - 40, field_146289_q::func_78256_a, (field_146295_m - 145) / 10)
            : RequestTask.wrap(status, field_146294_l - 40, field_146289_q::func_78256_a))) {
      func_73732_a(field_146289_q, line, field_146294_l / 2, lineY, 0xFFFFFFFF);
      lineY += 10;
    }
    func_73731_b(field_146289_q, RequestTask.CREDIT, 4, field_146295_m - 12, 0xFFAAAAAA);
  }
}

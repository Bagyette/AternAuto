package fr.bagyette.aternauto.forge;

import fr.autoaternos.ConnectGuard;
import fr.autoaternos.Messages;
import fr.autoaternos.RequestTask;
import net.minecraft.client.Minecraft;
import net.minecraft.client.gui.GuiButton;
import net.minecraft.client.gui.GuiScreen;
import net.minecraft.util.Session;

/** Forge 1.8.9/1.12.2 screen using the SRG API shared by both versions. */
public final class RequestScreen extends GuiScreen {
  private final GuiScreen parent;
  private final String host;
  private final Runnable connect;
  private final Messages messages;
  private RequestTask task;
  private GuiButton continueButton;
  private boolean resumed;

  public RequestScreen(GuiScreen parent, String host, Runnable connect) {
    this.parent = parent;
    this.host = host;
    this.connect = connect;
    this.messages = new Messages(Minecraft.func_71410_x().field_71474_y.field_74363_ab);
  }

  @Override
  public void func_73866_w_() {
    field_146292_n.clear();
    field_146292_n.add(
        new GuiButton(
            0,
            field_146294_l / 2 - 100,
            field_146295_m / 2 + 45,
            200,
            20,
            messages.text("button.cancel")));
    continueButton =
        new GuiButton(
            1,
            field_146294_l / 2 - 100,
            field_146295_m / 2 + 20,
            200,
            20,
            messages.text("button.connect_anyway"));
    continueButton.field_146125_m = task != null && task.complete() && !task.accepted();
    field_146292_n.add(continueButton);
    if (task != null) {
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
    if (task == null || !task.complete() || resumed) {
      return;
    }
    if (task.accepted()) {
      resume();
    } else {
      continueButton.field_146125_m = true;
    }
  }

  @Override
  protected void func_146284_a(GuiButton button) {
    if (button.field_146127_k == 0) {
      cancel();
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
    if (task != null) {
      task.cancel();
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
    Minecraft.func_71410_x().func_147108_a(parent);
  }

  @Override
  public void func_73863_a(int mouseX, int mouseY, float delta) {
    func_146276_q_();
    super.func_73863_a(mouseX, mouseY, delta);
    func_73732_a(
        field_146289_q, "AternAuto", field_146294_l / 2, field_146295_m / 2 - 45, 0xFFFFFFFF);
    String status = task == null ? messages.text("status.verifying") : task.status();
    int lineY = field_146295_m / 2 - 20;
    for (String line :
        RequestTask.wrap(status, field_146294_l - 40, field_146289_q::func_78256_a)) {
      func_73732_a(field_146289_q, line, field_146294_l / 2, lineY, 0xFFFFFFFF);
      lineY += 10;
    }
    func_73731_b(field_146289_q, RequestTask.CREDIT, 4, field_146295_m - 12, 0xFFAAAAAA);
  }
}

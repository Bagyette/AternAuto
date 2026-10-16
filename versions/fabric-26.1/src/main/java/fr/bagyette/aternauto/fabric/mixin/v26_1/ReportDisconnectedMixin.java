package fr.bagyette.aternauto.fabric.mixin.v26_1;

import fr.bagyette.aternauto.common.Messages;
import fr.bagyette.aternauto.fabric.compat.v26_1.RetryConnection;
import net.minecraft.client.Minecraft;
import net.minecraft.client.gui.components.Button;
import net.minecraft.client.gui.screens.DisconnectedScreen;
import net.minecraft.client.gui.screens.Screen;
import net.minecraft.network.chat.Component;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

@Mixin(DisconnectedScreen.class)
public abstract class ReportDisconnectedMixin extends Screen {
  protected ReportDisconnectedMixin(Component title) {
    super(title);
  }

  @Inject(method = "init", at = @At("TAIL"))
  private void addReportButton(CallbackInfo ci) {
    Screen screen = this;
    if (RetryConnection.canReport(screen)) {
      Messages messages = new Messages(Minecraft.getInstance().options.languageCode);
      addRenderableWidget(
          Button.builder(
                  Component.literal(messages.text("report.button")),
                  button -> RetryConnection.openReport(screen))
              .bounds(width / 2 - 100, height - 28, 200, 20)
              .build());
    }
  }
}

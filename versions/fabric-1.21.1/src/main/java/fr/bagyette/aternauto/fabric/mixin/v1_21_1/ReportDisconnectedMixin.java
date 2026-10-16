package fr.bagyette.aternauto.fabric.mixin.v1_21_1;

import fr.bagyette.aternauto.common.Messages;
import fr.bagyette.aternauto.fabric.compat.v1_21_1.RetryConnection;
import net.minecraft.client.MinecraftClient;
import net.minecraft.client.gui.screen.DisconnectedScreen;
import net.minecraft.client.gui.screen.Screen;
import net.minecraft.client.gui.widget.ButtonWidget;
import net.minecraft.text.Text;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

@Mixin(DisconnectedScreen.class)
public abstract class ReportDisconnectedMixin extends Screen {
  protected ReportDisconnectedMixin(Text title) {
    super(title);
  }

  @Inject(method = "init", at = @At("TAIL"))
  private void addReportButton(CallbackInfo ci) {
    Screen screen = this;
    if (RetryConnection.canReport(screen)) {
      Messages messages = new Messages(MinecraftClient.getInstance().options.language);
      addDrawableChild(
          ButtonWidget.builder(
                  Text.literal(messages.text("report.button")),
                  button -> RetryConnection.openReport(screen))
              .dimensions(width / 2 - 100, height - 28, 200, 20)
              .build());
    }
  }
}

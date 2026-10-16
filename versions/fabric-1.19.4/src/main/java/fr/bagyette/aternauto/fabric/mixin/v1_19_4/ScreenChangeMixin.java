package fr.bagyette.aternauto.fabric.mixin.v1_19_4;

import fr.bagyette.aternauto.fabric.compat.v1_19_4.RetryConnection;
import net.minecraft.client.MinecraftClient;
import net.minecraft.client.gui.screen.Screen;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

@Mixin(MinecraftClient.class)
public abstract class ScreenChangeMixin {
  @Inject(method = "setScreen", at = @At("HEAD"), cancellable = true)
  private void interceptScreen(Screen screen, CallbackInfo ci) {
    if (RetryConnection.interceptScreen(screen)) {
      ci.cancel();
    }
  }
}

package fr.bagyette.aternauto.forge.mixin.v1_21_4;

import fr.bagyette.aternauto.forge.compat.v1_21_4.RetryConnection;
import net.minecraft.client.Minecraft;
import net.minecraft.client.gui.screens.Screen;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

@Mixin(Minecraft.class)
public abstract class ScreenChangeMixin {
  @Inject(method = "setScreen", at = @At("HEAD"), cancellable = true)
  private void interceptScreen(Screen screen, CallbackInfo ci) {
    if (RetryConnection.interceptScreen(screen)) {
      ci.cancel();
    }
  }
}

package fr.bagyette.aternauto.forge.mixin.v26_2;

import fr.bagyette.aternauto.forge.compat.v26_2.RetryConnection;
import net.minecraft.client.gui.Gui;
import net.minecraft.client.gui.screens.Screen;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

@Mixin(Gui.class)
public abstract class ScreenChangeMixin {
  @Inject(method = "setScreen", at = @At("HEAD"), cancellable = true)
  private void interceptScreen(Screen screen, CallbackInfo ci) {
    if (RetryConnection.interceptScreen(screen)) {
      ci.cancel();
    }
  }
}

package fr.bagyette.aternauto.testing.smoke.mixin;

import fr.bagyette.aternauto.testing.smoke.SmokeClient;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

@Mixin(targets = "net.minecraft.class_310", remap = false)
public abstract class LegacyTickMixin {
  @Inject(method = "method_1574", at = @At("HEAD"), remap = false)
  private void smokeTick(CallbackInfo callback) {
    SmokeClient.tick(this);
  }
}

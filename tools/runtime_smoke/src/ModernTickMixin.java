package smoke.mixin;

import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;
import smoke.SmokeClient;

@Mixin(targets = "net.minecraft.client.Minecraft", remap = false)
public abstract class ModernTickMixin {
  @Inject(method = "tick", at = @At("HEAD"), remap = false)
  private void smokeTick(CallbackInfo callback) {
    SmokeClient.tick(this);
  }
}

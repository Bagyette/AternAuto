package fr.bagyette.aternauto.fabric.mixin.v26_2;

import fr.bagyette.aternauto.fabric.compat.v26_2.RetryConnection;
import net.minecraft.client.Minecraft;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

@Mixin(Minecraft.class)
public abstract class RetryClientMixin {
  @Inject(method = "tick", at = @At("HEAD"))
  private void tickRetry(CallbackInfo ci) {
    RetryConnection.tick();
  }
}

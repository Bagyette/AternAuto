package fr.bagyette.aternauto.neoforge.mixin.v1_21_9;

import fr.bagyette.aternauto.neoforge.compat.v1_21_9.RetryConnection;
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

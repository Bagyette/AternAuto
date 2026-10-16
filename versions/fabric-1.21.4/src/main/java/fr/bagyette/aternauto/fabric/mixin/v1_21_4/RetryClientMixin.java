package fr.bagyette.aternauto.fabric.mixin.v1_21_4;

import fr.bagyette.aternauto.fabric.compat.v1_21_4.RetryConnection;
import net.minecraft.client.MinecraftClient;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

@Mixin(MinecraftClient.class)
public abstract class RetryClientMixin {
  @Inject(method = "tick", at = @At("HEAD"))
  private void tickRetry(CallbackInfo ci) {
    RetryConnection.tick();
  }
}

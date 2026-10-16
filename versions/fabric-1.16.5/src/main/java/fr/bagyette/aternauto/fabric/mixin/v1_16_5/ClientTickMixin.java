package fr.bagyette.aternauto.fabric.mixin.v1_16_5;

import fr.bagyette.aternauto.fabric.compat.v1_16_5.PendingConnection;
import net.minecraft.client.MinecraftClient;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

@Mixin(MinecraftClient.class)
public abstract class ClientTickMixin {
  @Inject(method = "tick", at = @At("HEAD"))
  private void interceptTick(CallbackInfo ci) {
    PendingConnection.tick();
  }
}

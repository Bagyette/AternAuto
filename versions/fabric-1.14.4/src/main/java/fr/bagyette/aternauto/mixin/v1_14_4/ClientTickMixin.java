package fr.bagyette.aternauto.mixin.v1_14_4;

import fr.bagyette.aternauto.compat.v1_14_4.PendingConnection;
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

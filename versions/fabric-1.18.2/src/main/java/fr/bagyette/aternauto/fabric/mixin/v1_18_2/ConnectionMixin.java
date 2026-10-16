package fr.bagyette.aternauto.fabric.mixin.v1_18_2;

import fr.bagyette.aternauto.common.ConnectGuard;
import fr.bagyette.aternauto.common.DawnApi;
import fr.bagyette.aternauto.fabric.compat.v1_18_2.RequestScreen;
import fr.bagyette.aternauto.fabric.compat.v1_18_2.RetryConnection;
import net.minecraft.client.MinecraftClient;
import net.minecraft.client.gui.screen.ConnectScreen;
import net.minecraft.client.gui.screen.Screen;
import net.minecraft.client.network.ServerAddress;
import net.minecraft.client.network.ServerInfo;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

@Mixin(ConnectScreen.class)
public abstract class ConnectionMixin {
  @Inject(
      method =
          "connect(Lnet/minecraft/client/gui/screen/Screen;Lnet/minecraft/client/MinecraftClient;Lnet/minecraft/client/network/ServerAddress;Lnet/minecraft/client/network/ServerInfo;)V",
      at = @At("HEAD"),
      cancellable = true)
  private static void intercept(
      Screen parent,
      MinecraftClient client,
      ServerAddress address,
      ServerInfo serverData,
      CallbackInfo ci) {
    if (!ConnectGuard.bypassed()) {
      RetryConnection.clear();
    }
    if (ConnectGuard.bypassed() || !DawnApi.isSupportedHost(address.getAddress())) {
      return;
    }
    ci.cancel();
    client.setScreen(
        new RequestScreen(
            parent,
            address.getAddress(),
            address.getPort(),
            () -> {
              // Leave the failed screen before vanilla checks for an active connection.
              client.setScreen(parent);
              ConnectScreen.connect(parent, client, address, serverData);
            }));
  }
}

package fr.bagyette.aternauto.forge.mixin.v1_21_1;

import fr.bagyette.aternauto.common.ConnectGuard;
import fr.bagyette.aternauto.common.DawnApi;
import fr.bagyette.aternauto.forge.compat.v1_21_1.RequestScreen;
import fr.bagyette.aternauto.forge.compat.v1_21_1.RetryConnection;
import net.minecraft.client.Minecraft;
import net.minecraft.client.gui.screens.ConnectScreen;
import net.minecraft.client.gui.screens.Screen;
import net.minecraft.client.multiplayer.ServerData;
import net.minecraft.client.multiplayer.TransferState;
import net.minecraft.client.multiplayer.resolver.ServerAddress;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

@Mixin(ConnectScreen.class)
public abstract class ConnectionMixin {
  @Inject(
      method =
          "startConnecting(Lnet/minecraft/client/gui/screens/Screen;Lnet/minecraft/client/Minecraft;Lnet/minecraft/client/multiplayer/resolver/ServerAddress;Lnet/minecraft/client/multiplayer/ServerData;ZLnet/minecraft/client/multiplayer/TransferState;)V",
      at = @At("HEAD"),
      cancellable = true)
  private static void intercept(
      Screen parent,
      Minecraft client,
      ServerAddress address,
      ServerData serverData,
      boolean quickPlay,
      TransferState transfer,
      CallbackInfo ci) {
    if (!ConnectGuard.bypassed()) {
      RetryConnection.clear();
    }
    if (transfer != null
        || ConnectGuard.bypassed()
        || !DawnApi.isSupportedHost(address.getHost())) {
      return;
    }
    ci.cancel();
    client.setScreen(
        new RequestScreen(
            parent,
            address.getHost(),
            address.getPort(),
            () ->
                ConnectScreen.startConnecting(
                    parent, client, address, serverData, quickPlay, transfer)));
  }
}

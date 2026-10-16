package fr.bagyette.aternauto.forge.mixin.v1_16_5;

import fr.bagyette.aternauto.common.ConnectGuard;
import fr.bagyette.aternauto.common.DawnApi;
import fr.bagyette.aternauto.forge.compat.v1_16_5.PendingConnection;
import fr.bagyette.aternauto.forge.compat.v1_16_5.RequestScreen;
import fr.bagyette.aternauto.forge.compat.v1_16_5.RetryConnection;
import net.minecraft.client.Minecraft;
import net.minecraft.client.gui.screens.ConnectScreen;
import net.minecraft.client.gui.screens.Screen;
import org.spongepowered.asm.mixin.Final;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Shadow;
import org.spongepowered.asm.mixin.gen.Invoker;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

@Mixin(ConnectScreen.class)
public abstract class ConnectionMixin {
  @Shadow @Final private Screen parent;

  @Invoker("connect")
  public abstract void invokeConnect(String host, int port);

  @Inject(method = "connect(Ljava/lang/String;I)V", at = @At("HEAD"), cancellable = true)
  private void intercept(String host, int port, CallbackInfo ci) {
    if (!ConnectGuard.bypassed()) {
      RetryConnection.clear();
    }
    if (ConnectGuard.bypassed() || !DawnApi.isSupportedHost(host)) {
      return;
    }
    Screen original = (Screen) (Object) this;
    PendingConnection.defer(
        original,
        new RequestScreen(
            parent,
            host,
            port,
            () -> {
              Minecraft.getInstance().setScreen(original);
              invokeConnect(host, port);
            }));
    ci.cancel();
  }
}

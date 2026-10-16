package fr.bagyette.aternauto.fabric.compat.v1_21_9;

import fr.bagyette.aternauto.common.ConnectionFlow;
import fr.bagyette.aternauto.fabric.mixin.v1_21_9.DisconnectedScreenMixin;
import net.minecraft.client.MinecraftClient;
import net.minecraft.client.gui.screen.DisconnectedScreen;
import net.minecraft.client.gui.screen.Screen;
import net.minecraft.client.gui.screen.multiplayer.ConnectScreen;

/** Typed Minecraft bridge; the retry and reporting policy lives in common. */
public final class RetryConnection {
  private static final ConnectionFlow<Screen> FLOW =
      new ConnectionFlow<>(
          () -> MinecraftClient.getInstance().currentScreen,
          () -> MinecraftClient.getInstance().world != null,
          screen -> screen instanceof ConnectScreen,
          screen ->
              screen instanceof DisconnectedScreen
                  ? ((DisconnectedScreenMixin) screen).aternauto$getReason().reason().getString()
                  : null);

  private RetryConnection() {}

  public static void begin(String host, int port, Runnable connect) {
    FLOW.begin(host, port, connect);
  }

  public static void clear() {
    FLOW.clear();
  }

  public static boolean interceptScreen(Screen next) {
    return FLOW.intercept(next);
  }

  public static void tick() {
    FLOW.tick();
  }

  public static boolean canReport(Screen screen) {
    return FLOW.report(screen) != null;
  }

  public static void openReport(Screen screen) {
    ConnectionFlow.Target target = FLOW.report(screen);
    if (target != null) {
      MinecraftClient.getInstance()
          .setScreen(RequestScreen.forFailure(screen, target.host, target.port, target.failure));
    }
  }
}

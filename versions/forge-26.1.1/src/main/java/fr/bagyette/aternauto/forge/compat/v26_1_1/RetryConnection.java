package fr.bagyette.aternauto.forge.compat.v26_1_1;

import fr.bagyette.aternauto.common.ConnectionFlow;
import fr.bagyette.aternauto.forge.mixin.v26_1_1.DisconnectedScreenMixin;
import net.minecraft.client.Minecraft;
import net.minecraft.client.gui.screens.ConnectScreen;
import net.minecraft.client.gui.screens.DisconnectedScreen;
import net.minecraft.client.gui.screens.Screen;

/** Typed Minecraft bridge; the retry and reporting policy lives in common. */
public final class RetryConnection {
  private static final ConnectionFlow<Screen> FLOW =
      new ConnectionFlow<>(
          () -> Minecraft.getInstance().screen,
          () -> Minecraft.getInstance().level != null,
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
      Minecraft.getInstance()
          .setScreen(RequestScreen.forFailure(screen, target.host, target.port, target.failure));
    }
  }
}

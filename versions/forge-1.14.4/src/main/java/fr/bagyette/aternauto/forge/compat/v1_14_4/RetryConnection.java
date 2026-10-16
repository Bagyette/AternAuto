package fr.bagyette.aternauto.forge.compat.v1_14_4;

import fr.bagyette.aternauto.common.ConnectionFlow;
import java.lang.reflect.Field;
import net.minecraft.client.Minecraft;
import net.minecraft.client.gui.screen.ConnectingScreen;
import net.minecraft.client.gui.screen.DisconnectedScreen;
import net.minecraft.client.gui.screen.Screen;

/** Shared legacy Forge bridge without linking to version-specific text interfaces. */
public final class RetryConnection {
  private static final ConnectionFlow<Screen> FLOW =
      new ConnectionFlow<>(
          () -> Minecraft.func_71410_x().field_71462_r,
          () -> Minecraft.func_71410_x().field_71441_e != null,
          screen -> screen instanceof ConnectingScreen,
          RetryConnection::reason);

  private RetryConnection() {}

  public static void begin(String host, int port, Runnable connect) {
    FLOW.begin(host, port, connect);
  }

  public static void clear() {
    FLOW.clear();
  }

  public static boolean intercept(Screen screen) {
    return FLOW.intercept(screen);
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
      Minecraft.func_71410_x()
          .func_147108_a(
              RequestScreen.forFailure(screen, target.host, target.port, target.failure));
    }
  }

  private static String reason(Screen screen) {
    if (!(screen instanceof DisconnectedScreen)) {
      return null;
    }
    try {
      Field field = DisconnectedScreen.class.getDeclaredField("field_146304_f");
      field.setAccessible(true);
      Object text = field.get(screen);
      return ((net.minecraft.util.text.ITextComponent) text).getString();
    } catch (ReflectiveOperationException error) {
      throw new IllegalStateException("AternAuto: incompatible disconnect text API", error);
    }
  }
}

package fr.bagyette.aternauto.forge.legacy1710;

import fr.bagyette.aternauto.common.ConnectionFlow;
import java.lang.reflect.Field;
import net.minecraft.client.Minecraft;
import net.minecraft.client.gui.GuiDisconnected;
import net.minecraft.client.gui.GuiScreen;
import net.minecraft.client.multiplayer.GuiConnecting;

/** Shared legacy Forge bridge without linking to version-specific text interfaces. */
public final class RetryConnection {
  private static final ConnectionFlow<GuiScreen> FLOW =
      new ConnectionFlow<>(
          () -> Minecraft.func_71410_x().field_71462_r,
          () -> Minecraft.func_71410_x().field_71441_e != null,
          screen -> screen instanceof GuiConnecting,
          RetryConnection::reason);

  private RetryConnection() {}

  public static void begin(String host, int port, Runnable connect) {
    FLOW.begin(host, port, connect);
  }

  public static void clear() {
    FLOW.clear();
  }

  public static boolean intercept(GuiScreen screen) {
    return FLOW.intercept(screen);
  }

  public static void tick() {
    FLOW.tick();
  }

  public static boolean canReport(GuiScreen screen) {
    return FLOW.report(screen) != null;
  }

  public static void openReport(GuiScreen screen) {
    ConnectionFlow.Target target = FLOW.report(screen);
    if (target != null) {
      Minecraft.func_71410_x()
          .func_147108_a(
              RequestScreen.forFailure(screen, target.host, target.port, target.failure));
    }
  }

  private static String reason(GuiScreen screen) {
    if (!(screen instanceof GuiDisconnected)) {
      return null;
    }
    try {
      Field field = GuiDisconnected.class.getDeclaredField("field_146304_f");
      field.setAccessible(true);
      Object text = field.get(screen);
      return (String) text.getClass().getMethod("func_150260_c").invoke(text);
    } catch (ReflectiveOperationException error) {
      throw new IllegalStateException("AternAuto: incompatible disconnect text API", error);
    }
  }
}

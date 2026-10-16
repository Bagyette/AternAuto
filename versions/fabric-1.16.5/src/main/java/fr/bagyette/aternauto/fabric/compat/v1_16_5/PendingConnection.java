package fr.bagyette.aternauto.fabric.compat.v1_16_5;

import net.minecraft.client.MinecraftClient;
import net.minecraft.client.gui.screen.Screen;

/** Waits until the constructor's caller has opened the original connection screen. */
public final class PendingConnection {
  private static Screen original;
  private static Screen replacement;

  private PendingConnection() {}

  public static void defer(Screen screen, Screen requestScreen) {
    original = screen;
    replacement = requestScreen;
  }

  public static void tick() {
    Screen requestScreen = replacement;
    Screen connectionScreen = original;
    replacement = null;
    original = null;
    MinecraftClient client = MinecraftClient.getInstance();
    if (requestScreen != null && client.currentScreen == connectionScreen) {
      client.openScreen(requestScreen);
    }
  }
}

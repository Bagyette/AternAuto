package fr.bagyette.aternauto.forge.compat.v1_16_5;

import net.minecraft.client.Minecraft;
import net.minecraft.client.gui.screens.Screen;

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
    Minecraft client = Minecraft.getInstance();
    if (requestScreen != null && client.screen == connectionScreen) {
      client.setScreen(requestScreen);
    }
  }
}

package fr.bagyette.aternauto.testing.smoke;

import net.fabricmc.api.ClientModInitializer;

/** Fabric entry point for the loader-independent rendered-screen checks. */
public final class SmokeClient implements ClientModInitializer {
  @Override
  public void onInitializeClient() {
    SmokeChecks.initialize();
  }

  public static void tick(Object client) {
    SmokeChecks.tick(client);
  }

  public static void continueScreen(Object screen) {
    SmokeChecks.continueScreen(screen);
  }
}

package fr.bagyette.aternauto.forge;

import fr.autoaternos.ConnectGuard;
import fr.autoaternos.DawnApi;
import java.lang.reflect.Field;
import java.lang.reflect.Method;
import java.util.IdentityHashMap;
import java.util.Map;
import net.minecraft.client.Minecraft;
import net.minecraft.client.gui.GuiScreen;
import net.minecraftforge.client.event.GuiOpenEvent;
import net.minecraftforge.fml.common.eventhandler.SubscribeEvent;

/** Bridges Forge's two GuiOpenEvent APIs without linking to one version's accessor. */
public final class ForgeHooks {
  private static final Map<Object, Pending> PENDING = new IdentityHashMap<>();

  public static boolean defer(Object original, String host, int port) {
    if (ConnectGuard.bypassed() || !DawnApi.isSupportedHost(host)) {
      return false;
    }
    synchronized (PENDING) {
      // The entry is consumed by the immediately following GuiOpenEvent.
      PENDING.clear();
      PENDING.put(original, new Pending(host, port));
    }
    return true;
  }

  @SubscribeEvent
  public void onGuiOpen(GuiOpenEvent event) {
    try {
      GuiScreen original = getGui(event);
      Pending pending;
      synchronized (PENDING) {
        pending = PENDING.remove(original);
      }
      if (pending == null) {
        return;
      }
      Field parentField = original.getClass().getDeclaredField("field_146374_i");
      parentField.setAccessible(true);
      GuiScreen parent = (GuiScreen) parentField.get(original);
      Method connect =
          original.getClass().getDeclaredMethod("func_146367_a", String.class, int.class);
      connect.setAccessible(true);
      GuiScreen replacement =
          new RequestScreen(
              parent,
              pending.host,
              () -> {
                Minecraft.func_71410_x().func_147108_a(original);
                try {
                  connect.invoke(original, pending.host, pending.port);
                } catch (ReflectiveOperationException e) {
                  throw new IllegalStateException(
                      "AternAuto: impossible de reprendre la connexion Forge", e);
                }
              });
      setGui(event, replacement);
    } catch (ReflectiveOperationException e) {
      throw new IllegalStateException("AternAuto: API d'écran Forge incompatible", e);
    }
  }

  private static GuiScreen getGui(GuiOpenEvent event) throws ReflectiveOperationException {
    try {
      return (GuiScreen) event.getClass().getMethod("getGui").invoke(event);
    } catch (NoSuchMethodException e) {
      return (GuiScreen) event.getClass().getField("gui").get(event);
    }
  }

  private static void setGui(GuiOpenEvent event, GuiScreen screen)
      throws ReflectiveOperationException {
    try {
      event.getClass().getMethod("setGui", GuiScreen.class).invoke(event, screen);
    } catch (NoSuchMethodException e) {
      event.getClass().getField("gui").set(event, screen);
    }
  }

  private static final class Pending {
    final String host;
    final int port;

    Pending(String host, int port) {
      this.host = host;
      this.port = port;
    }
  }
}

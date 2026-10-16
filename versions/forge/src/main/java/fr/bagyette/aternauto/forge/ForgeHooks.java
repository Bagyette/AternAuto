package fr.bagyette.aternauto.forge;

import fr.bagyette.aternauto.common.ConnectGuard;
import fr.bagyette.aternauto.common.DawnApi;
import fr.bagyette.aternauto.common.Messages;
import java.lang.reflect.Field;
import java.lang.reflect.Method;
import java.util.IdentityHashMap;
import java.util.List;
import java.util.Map;
import java.util.WeakHashMap;
import net.minecraft.client.Minecraft;
import net.minecraft.client.gui.GuiButton;
import net.minecraft.client.gui.GuiScreen;
import net.minecraftforge.client.event.GuiOpenEvent;
import net.minecraftforge.client.event.GuiScreenEvent;
import net.minecraftforge.fml.common.eventhandler.SubscribeEvent;
import net.minecraftforge.fml.common.gameevent.TickEvent;

/** Bridges Forge's two GuiOpenEvent APIs without linking to one version's accessor. */
public final class ForgeHooks {
  private static final Map<Object, Pending> PENDING = new IdentityHashMap<>();
  private final Map<GuiButton, GuiScreen> reportButtons = new WeakHashMap<>();

  public static boolean defer(Object original, String host, int port) {
    if (ConnectGuard.bypassed() || !DawnApi.isSupportedHost(host)) {
      return false;
    }
    RetryConnection.clear();
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
        if (RetryConnection.intercept(original)) {
          event.setCanceled(true);
        }
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
              pending.port,
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

  @SubscribeEvent
  public void onTick(TickEvent.ClientTickEvent event) {
    if (event.phase == TickEvent.Phase.END) {
      RetryConnection.tick();
    }
  }

  @SubscribeEvent
  public void onGuiInitialized(GuiScreenEvent.InitGuiEvent.Post event) {
    try {
      GuiScreen screen = (GuiScreen) member(event, "getGui", "gui");
      if (!RetryConnection.canReport(screen)) {
        return;
      }
      @SuppressWarnings("unchecked")
      List<GuiButton> buttons = (List<GuiButton>) member(event, "getButtonList", "buttonList");
      int id = 10000;
      for (GuiButton button : buttons) {
        id = Math.max(id, button.field_146127_k + 1);
      }
      Messages messages = new Messages(Minecraft.func_71410_x().field_71474_y.field_74363_ab);
      GuiButton button =
          new GuiButton(
              id,
              screen.field_146294_l / 2 - 100,
              screen.field_146295_m - 28,
              200,
              20,
              messages.text("report.button"));
      buttons.add(button);
      reportButtons.put(button, screen);
    } catch (ReflectiveOperationException error) {
      throw new IllegalStateException("AternAuto: incompatible Forge GUI event", error);
    }
  }

  @SubscribeEvent
  public void onButton(GuiScreenEvent.ActionPerformedEvent.Pre event) {
    try {
      GuiButton button = (GuiButton) member(event, "getButton", "button");
      GuiScreen screen = reportButtons.get(button);
      if (screen != null) {
        event.setCanceled(true);
        RetryConnection.openReport(screen);
      }
    } catch (ReflectiveOperationException error) {
      throw new IllegalStateException("AternAuto: incompatible Forge button event", error);
    }
  }

  private static Object member(Object event, String getter, String field)
      throws ReflectiveOperationException {
    try {
      return event.getClass().getMethod(getter).invoke(event);
    } catch (NoSuchMethodException error) {
      return event.getClass().getField(field).get(event);
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

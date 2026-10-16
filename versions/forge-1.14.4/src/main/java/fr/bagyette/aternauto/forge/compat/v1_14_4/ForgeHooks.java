package fr.bagyette.aternauto.forge.compat.v1_14_4;

import fr.bagyette.aternauto.common.ConnectGuard;
import fr.bagyette.aternauto.common.DawnApi;
import fr.bagyette.aternauto.common.Messages;
import java.lang.reflect.Field;
import java.lang.reflect.Method;
import java.util.IdentityHashMap;
import java.util.Map;
import net.minecraft.client.Minecraft;
import net.minecraft.client.gui.screen.Screen;
import net.minecraft.client.gui.widget.button.Button;
import net.minecraftforge.client.event.GuiOpenEvent;
import net.minecraftforge.client.event.GuiScreenEvent;
import net.minecraftforge.event.TickEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;

/** Native Forge events and coremod hook for the generation preceding bundled Mixin. */
public final class ForgeHooks {
  private static final Map<Object, Pending> PENDING = new IdentityHashMap<>();

  public static boolean defer(Object screen, String host, int port) {
    if (ConnectGuard.bypassed() || !DawnApi.isSupportedHost(host)) {
      return false;
    }
    RetryConnection.clear();
    synchronized (PENDING) {
      PENDING.clear();
      PENDING.put(screen, new Pending(host, port));
    }
    return true;
  }

  @SubscribeEvent
  public void open(GuiOpenEvent event) {
    Screen original = event.getGui();
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
    try {
      Field field = original.getClass().getDeclaredField("field_146374_i");
      field.setAccessible(true);
      Screen parent = (Screen) field.get(original);
      Method connect =
          original.getClass().getDeclaredMethod("func_146367_a", String.class, int.class);
      connect.setAccessible(true);
      event.setGui(
          new RequestScreen(
              parent,
              pending.host,
              pending.port,
              () -> {
                Minecraft.func_71410_x().func_147108_a(original);
                try {
                  connect.invoke(original, pending.host, pending.port);
                } catch (ReflectiveOperationException error) {
                  throw new IllegalStateException(
                      "AternAuto: incompatible Forge connection API", error);
                }
              }));
    } catch (ReflectiveOperationException error) {
      throw new IllegalStateException("AternAuto: incompatible Forge connection screen", error);
    }
  }

  @SubscribeEvent
  public void tick(TickEvent.ClientTickEvent event) {
    if (event.phase == TickEvent.Phase.END) {
      RetryConnection.tick();
    }
  }

  @SubscribeEvent
  public void initialized(GuiScreenEvent.InitGuiEvent.Post event) {
    Screen screen = event.getGui();
    if (RetryConnection.canReport(screen)) {
      Messages messages = new Messages(Minecraft.func_71410_x().field_71474_y.field_74363_ab);
      event.addWidget(
          new Button(
              screen.width / 2 - 100,
              screen.height - 28,
              200,
              20,
              messages.text("report.button"),
              button -> RetryConnection.openReport(screen)));
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

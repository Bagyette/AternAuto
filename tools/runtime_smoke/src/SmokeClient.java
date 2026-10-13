package smoke;

import java.lang.reflect.Method;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Paths;
import net.fabricmc.api.ClientModInitializer;

public final class SmokeClient implements ClientModInitializer {
  private static int stableFrames;
  private static boolean continued;

  @Override
  public void onInitializeClient() {
    try {
      ClassLoader loader = getClass().getClassLoader();
      Class.forName(System.getProperty("smoke.screen"), false, loader);
      Class.forName(System.getProperty("smoke.connect"), false, loader);
      System.out.println("ATERN_SMOKE_CLASSES_LOADED");
    } catch (Throwable error) {
      fail(error);
    }
  }

  public static void tick(Object minecraft) {
    try {
      Object overlay;
      if (System.getProperty("smoke.modern").equals("true")) {
        try {
          overlay = minecraft.getClass().getMethod("getOverlay").invoke(minecraft);
        } catch (NoSuchMethodException error) {
          Object gui = minecraft.getClass().getField("gui").get(minecraft);
          overlay = gui.getClass().getMethod("overlay").invoke(gui);
        }
      } else {
        overlay = minecraft.getClass().getMethod("method_18506").invoke(minecraft);
      }
      if (overlay != null) {
        return;
      }
      Object screen;
      if (System.getProperty("smoke.modern").equals("true")) {
        try {
          screen = minecraft.getClass().getField("screen").get(minecraft);
        } catch (NoSuchFieldException error) {
          Object gui = minecraft.getClass().getField("gui").get(minecraft);
          screen = gui.getClass().getMethod("screen").invoke(gui);
        }
      } else {
        screen = minecraft.getClass().getField("field_1755").get(minecraft);
      }
      if (screen == null) {
        return;
      }
      String name = screen.getClass().getName();
      if (name.equals(System.getProperty("smoke.screen"))) {
        if (++stableFrames >= 15) {
          Files.write(
              Paths.get(System.getProperty("smoke.result")),
              "REQUEST_SCREEN_RENDERED\n".getBytes(StandardCharsets.UTF_8));
          System.out.println("ATERN_SMOKE_PASS");
          String stop = System.getProperty("smoke.modern").equals("true") ? "stop" : "method_1592";
          minecraft.getClass().getMethod(stop).invoke(minecraft);
        }
      }
    } catch (Throwable error) {
      fail(error);
    }
  }

  public static void continueScreen(Object screen) {
    if (continued) {
      return;
    }
    continued = true;
    try {
      String close = System.getProperty("smoke.modern").equals("true") ? "onClose" : "method_25419";
      Method method;
      try {
        method = screen.getClass().getDeclaredMethod("close");
      } catch (NoSuchMethodException error) {
        method = screen.getClass().getMethod(close);
      }
      method.setAccessible(true);
      method.invoke(screen);
      System.out.println("ATERN_SMOKE_CONTINUE");
    } catch (Throwable error) {
      fail(error);
    }
  }

  private static void fail(Throwable error) {
    error.printStackTrace();
    try {
      Files.write(
          Paths.get(System.getProperty("smoke.result")),
          ("FAIL: " + error + "\n").getBytes(StandardCharsets.UTF_8));
    } catch (Exception ignored) {
    }
    System.exit(3);
  }
}

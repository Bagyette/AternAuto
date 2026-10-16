package fr.bagyette.aternauto.testing.smoke;

import java.awt.GraphicsDevice;
import java.awt.GraphicsEnvironment;
import java.awt.Rectangle;
import java.lang.reflect.Method;
import java.nio.ByteBuffer;
import java.nio.ByteOrder;
import java.nio.IntBuffer;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Paths;

/** Loader-independent checks; only the separate test harness calls these methods. */
public final class SmokeChecks {
  private static int frames;
  private static boolean initialized;
  private static boolean continued;
  private static boolean stopping;
  private static long window;
  private static String previousScreen;
  private static boolean manualConnection;
  private static boolean sdl;
  private static int networkAttempts;
  private static int retryTicks;
  private static Object retryScreen;

  private SmokeChecks() {}

  public static void initialize() {
    if (initialized) {
      return;
    }
    initialized = true;
    try {
      ClassLoader loader = SmokeChecks.class.getClassLoader();
      Class.forName(System.getProperty("smoke.screen"), false, loader);
      Class.forName(System.getProperty("smoke.connect"), false, loader);
      String disconnected = System.getProperty("smoke.disconnect");
      if (disconnected != null) {
        Class.forName(disconnected, false, loader);
      }
      System.out.println("ATERN_SMOKE_CLASSES_LOADED");
    } catch (Throwable error) {
      fail(error);
    }
  }

  public static void tick(Object client) {
    initialize();
    try {
      for (java.lang.reflect.Field field : client.getClass().getDeclaredFields()) {
        String fieldType = field.getType().getName();
        if (!fieldType.endsWith(".Screen")
            && !fieldType.endsWith(".GuiScreen")
            && !fieldType.endsWith(".class_437")) {
          continue;
        }
        field.setAccessible(true);
        Object screen = field.get(client);
        String name = screen == null ? "none" : screen.getClass().getName();
        if (!name.equals(previousScreen)) {
          previousScreen = name;
          System.out.println("ATERN_SMOKE_SCREEN " + name);
          if (name.endsWith("LoadingErrorScreen")) {
            for (java.lang.reflect.Field detail : screen.getClass().getDeclaredFields()) {
              if (java.util.Collection.class.isAssignableFrom(detail.getType())) {
                detail.setAccessible(true);
                System.out.println(
                    "ATERN_SMOKE_LOADING " + detail.getName() + "=" + detail.get(screen));
                if (detail.getName().equals("modLoadErrors")
                    && !((java.util.Collection<?>) detail.get(screen)).isEmpty()) {
                  fail(new IllegalStateException("Loader reported mod loading errors"));
                }
              }
            }
          }
        }
        if (Boolean.getBoolean("smoke.manualConnect")
            && !manualConnection
            && (name.endsWith(".TitleScreen")
                || name.endsWith(".MainMenuScreen")
                || name.endsWith(".GuiMainMenu")
                || name.endsWith(".class_442"))) {
          manualConnection = true;
          Class<?> connection = Class.forName(System.getProperty("smoke.connect"));
          for (java.lang.reflect.Constructor<?> constructor : connection.getConstructors()) {
            Class<?>[] parameters = constructor.getParameterTypes();
            if (parameters.length == 4
                && parameters[2] == String.class
                && parameters[3] == int.class) {
              Object connecting =
                  constructor.newInstance(screen, client, "smoke.aternos.me", 25565);
              client
                  .getClass()
                  .getMethod(System.getProperty("smoke.setScreen"), parameters[0])
                  .invoke(client, connecting);
              System.out.println("ATERN_SMOKE_MANUAL_CONNECT");
              break;
            }
          }
        }
      }
    } catch (ReflectiveOperationException error) {
      fail(error);
    }
    if (Boolean.getBoolean("smoke.retry")) {
      retryTick(client);
      return;
    }
    if (frames >= 15 && !stopping) {
      stopping = true;
      try {
        client.getClass().getMethod(System.getProperty("smoke.stop", "stop")).invoke(client);
        Files.write(
            Paths.get(System.getProperty("smoke.result")),
            "REQUEST_SCREEN_RENDERED\n".getBytes(StandardCharsets.UTF_8));
        System.out.println("ATERN_SMOKE_PASS renderedFrames=" + frames);
      } catch (Throwable error) {
        fail(error);
      }
    }
  }

  /** Blocks real networking in the regression probe, after vanilla's connection guard. */
  public static void networkAttempt() {
    networkAttempts++;
  }

  private static void retryTick(Object client) {
    if (frames < 15 || stopping) {
      return;
    }
    try {
      java.lang.reflect.Field current = client.getClass().getField("field_1755");
      if (retryScreen == null) {
        Object request = current.get(client);
        java.lang.reflect.Field callback = request.getClass().getDeclaredField("connect");
        callback.setAccessible(true);
        Class<?> adapter =
            Class.forName("fr.bagyette.aternauto.fabric.compat.v1_21_11.RetryConnection");
        adapter
            .getMethod("begin", String.class, int.class, Runnable.class)
            .invoke(null, "smoke.aternos.me", 25565, callback.get(request));
        if (networkAttempts != 1) {
          throw new IllegalStateException("Initial vanilla connection was not reached");
        }
        retryScreen = current.get(client);
        java.lang.reflect.Field flowField = adapter.getDeclaredField("FLOW");
        flowField.setAccessible(true);
        Object flow = flowField.get(null);
        java.lang.reflect.Field activeField = flow.getClass().getDeclaredField("active");
        activeField.setAccessible(true);
        Object active = activeField.get(flow);
        java.lang.reflect.Field retryField = active.getClass().getDeclaredField("retry");
        retryField.setAccessible(true);
        Object retry = retryField.get(active);
        boolean scheduled =
            (Boolean)
                retry
                    .getClass()
                    .getMethod("schedule", String.class)
                    .invoke(
                        retry, "Internal Exception: java.net.SocketException: Connection reset");
        if (!scheduled) {
          throw new IllegalStateException("Reset retry was not scheduled");
        }
        System.out.println("ATERN_RETRY_SCHEDULED");
        return;
      }
      retryTicks++;
      if (retryTicks < 35) {
        if (networkAttempts != 1 || current.get(client) != retryScreen) {
          throw new IllegalStateException("Reconnected before the 35-tick delay");
        }
        return;
      }
      if (networkAttempts != 2 || current.get(client) == retryScreen) {
        throw new IllegalStateException(
            "Vanilla refused the second connection: " + networkAttempts);
      }
      stopping = true;
      client.getClass().getMethod(System.getProperty("smoke.stop")).invoke(client);
      Files.write(
          Paths.get(System.getProperty("smoke.result")),
          "RESET_RETRY_PASSED\n".getBytes(StandardCharsets.UTF_8));
      System.out.println("ATERN_SMOKE_PASS resetRetryTicks=" + retryTicks + " connections=2");
    } catch (Throwable error) {
      fail(error);
    }
  }

  /** Called after the actual request screen render method returns successfully. */
  public static void rendered(Object screen) {
    initialize();
    if (!screen.getClass().getName().equals(System.getProperty("smoke.screen"))) {
      return;
    }
    frames++;
  }

  public static void continueScreen(Object screen) {
    if (continued) {
      return;
    }
    continued = true;
    try {
      Method method = null;
      for (String name :
          new String[] {"close", "onClose", "method_25419", "func_231175_as_", "m_7379_"}) {
        try {
          method = screen.getClass().getMethod(name);
          break;
        } catch (NoSuchMethodException ignored) {
          // Each generation exposes a different mapped Screen close method.
        }
      }
      if (method == null) {
        throw new NoSuchMethodException("No onboarding close method");
      }
      method.setAccessible(true);
      method.invoke(screen);
      System.out.println("ATERN_SMOKE_CONTINUE");
    } catch (Throwable error) {
      fail(error);
    }
  }

  /** Keeps the first monitor untouched even while a game creates its initial window. */
  public static long createWindow(
      int width, int height, CharSequence title, long monitor, long share) {
    try {
      Class<?> glfw = Class.forName("org.lwjgl.glfw.GLFW");
      Method hint = glfw.getMethod("glfwWindowHint", int.class, int.class);
      hint.invoke(null, glfw.getField("GLFW_VISIBLE").getInt(null), 0);
      hint.invoke(null, glfw.getField("GLFW_FOCUSED").getInt(null), 0);
      try {
        hint.invoke(null, glfw.getField("GLFW_FOCUS_ON_SHOW").getInt(null), 0);
      } catch (NoSuchFieldException ignored) {
        // GLFW versions preceding this hint still create the window hidden.
      }
      window =
          (Long)
              glfw.getMethod(
                      "glfwCreateWindow",
                      int.class,
                      int.class,
                      CharSequence.class,
                      long.class,
                      long.class)
                  .invoke(null, width, height, title, monitor, share);
      return window;
    } catch (Throwable error) {
      fail(error);
      return 0;
    }
  }

  public static void placeWindow() {
    if (window == 0) {
      return;
    }
    if (sdl) {
      placeSdlWindow();
      return;
    }
    try {
      Class<?> glfw = Class.forName("org.lwjgl.glfw.GLFW");
      Object monitors = glfw.getMethod("glfwGetMonitors").invoke(null);
      int count = (Integer) monitors.getClass().getMethod("limit").invoke(monitors);
      for (int index = 0; index < count; index++) {
        long monitor =
            (Long) monitors.getClass().getMethod("get", int.class).invoke(monitors, index);
        Object mode = glfw.getMethod("glfwGetVideoMode", long.class).invoke(null, monitor);
        int width = (Integer) mode.getClass().getMethod("width").invoke(mode);
        int height = (Integer) mode.getClass().getMethod("height").invoke(mode);
        if (width != 1920 || height != 1080) {
          continue;
        }
        IntBuffer x = ByteBuffer.allocateDirect(4).order(ByteOrder.nativeOrder()).asIntBuffer();
        IntBuffer y = ByteBuffer.allocateDirect(4).order(ByteOrder.nativeOrder()).asIntBuffer();
        glfw.getMethod("glfwGetMonitorPos", long.class, IntBuffer.class, IntBuffer.class)
            .invoke(null, monitor, x, y);
        glfw.getMethod("glfwSetWindowPos", long.class, int.class, int.class)
            .invoke(null, window, x.get(0) + 32, y.get(0) + 32);
        glfw.getMethod("glfwShowWindow", long.class).invoke(null, window);
        System.out.println("ATERN_SMOKE_WINDOW_1080P");
        return;
      }
      throw new IllegalStateException(
          "No 1920x1080 monitor found; refusing primary-screen placement");
    } catch (Throwable error) {
      fail(error);
    }
  }

  /** SDL windows replace GLFW in Minecraft 26.3. */
  public static long createSdlWindow(
      Object backend, String title, int width, int height, long flags) {
    try {
      sdl = true;
      Class<?> video = Class.forName("org.lwjgl.sdl.SDLVideo");
      long hidden = video.getField("SDL_WINDOW_HIDDEN").getLong(null);
      long unfocusable = video.getField("SDL_WINDOW_NOT_FOCUSABLE").getLong(null);
      Class<?> gpuBackend = Class.forName("com.mojang.renderpearl.api.device.GpuBackend");
      window =
          (Long)
              gpuBackend
                  .getMethod("createWindow", String.class, int.class, int.class, long.class)
                  .invoke(backend, title, width, height, flags | hidden | unfocusable);
      return window;
    } catch (Throwable error) {
      fail(error);
      return 0;
    }
  }

  private static void placeSdlWindow() {
    try {
      Class<?> video = Class.forName("org.lwjgl.sdl.SDLVideo");
      IntBuffer displays = (IntBuffer) video.getMethod("SDL_GetDisplays").invoke(null);
      try {
        for (int index = 0; index < displays.limit(); index++) {
          int display = displays.get(index);
          Object mode =
              video.getMethod("SDL_GetCurrentDisplayMode", int.class).invoke(null, display);
          int width = (Integer) mode.getClass().getMethod("w").invoke(mode);
          int height = (Integer) mode.getClass().getMethod("h").invoke(mode);
          if (width != 1920 || height != 1080) {
            continue;
          }
          Class<?> rectangle = Class.forName("org.lwjgl.sdl.SDL_Rect");
          Object bounds = rectangle.getMethod("calloc").invoke(null);
          try {
            boolean found =
                (Boolean)
                    video
                        .getMethod("SDL_GetDisplayBounds", int.class, rectangle)
                        .invoke(null, display, bounds);
            if (!found) {
              throw new IllegalStateException("SDL display bounds unavailable");
            }
            int x = (Integer) rectangle.getMethod("x").invoke(bounds);
            int y = (Integer) rectangle.getMethod("y").invoke(bounds);
            boolean positioned =
                (Boolean)
                    video
                        .getMethod("SDL_SetWindowPosition", long.class, int.class, int.class)
                        .invoke(null, window, x + 32, y + 32);
            if (!positioned) {
              throw new IllegalStateException("SDL window positioning failed");
            }
            video.getMethod("SDL_ShowWindow", long.class).invoke(null, window);
            System.out.println("ATERN_SMOKE_WINDOW_1080P");
            return;
          } finally {
            rectangle.getMethod("free").invoke(bounds);
          }
        }
      } finally {
        Class.forName("org.lwjgl.sdl.SDLStdinc")
            .getMethod("SDL_free", IntBuffer.class)
            .invoke(null, displays);
      }
      throw new IllegalStateException("No 1920x1080 SDL display found");
    } catch (Throwable error) {
      fail(error);
    }
  }

  public static void placeLegacyWindow() {
    try {
      for (GraphicsDevice device :
          GraphicsEnvironment.getLocalGraphicsEnvironment().getScreenDevices()) {
        if (device.getDisplayMode().getWidth() != 1920
            || device.getDisplayMode().getHeight() != 1080) {
          continue;
        }
        Rectangle bounds = device.getDefaultConfiguration().getBounds();
        Class.forName("org.lwjgl.opengl.Display")
            .getMethod("setLocation", int.class, int.class)
            .invoke(null, bounds.x + 32, bounds.y + 32);
        System.out.println("ATERN_SMOKE_WINDOW_1080P");
        return;
      }
      throw new IllegalStateException("No 1920x1080 monitor found");
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
      // The console still records the original failure if the result cannot be written.
    }
    System.exit(3);
  }
}

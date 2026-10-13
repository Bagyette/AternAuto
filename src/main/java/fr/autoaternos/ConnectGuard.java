package fr.autoaternos;

public final class ConnectGuard {
  private static final ThreadLocal<Boolean> BYPASS = ThreadLocal.withInitial(() -> false);

  private ConnectGuard() {}

  public static boolean bypassed() {
    return BYPASS.get();
  }

  public static void run(Runnable action) {
    boolean previous = BYPASS.get();
    BYPASS.set(true);
    try {
      action.run();
    } finally {
      BYPASS.set(previous);
    }
  }
}

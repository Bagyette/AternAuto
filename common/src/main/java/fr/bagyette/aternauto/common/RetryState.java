package fr.bagyette.aternauto.common;

/** One connection-reset retry, counted in client ticks rather than wall-clock time. */
public final class RetryState {
  public static final String CONNECTION_RESET =
      "Internal Exception: java.net.SocketException: Connection reset";
  private boolean used;
  private int remaining = -1;

  public boolean schedule(String reason) {
    if (used || !CONNECTION_RESET.equals(reason)) {
      return false;
    }
    used = true;
    remaining = 35;
    return true;
  }

  public boolean tick() {
    if (remaining <= 0) {
      return false;
    }
    return --remaining == 0;
  }
}

package fr.bagyette.aternauto.common;

import java.util.Map;
import java.util.WeakHashMap;
import java.util.function.BooleanSupplier;
import java.util.function.Function;
import java.util.function.Predicate;
import java.util.function.Supplier;

/** Client-thread connection lifetime, shared by every Minecraft and loader adapter. */
public final class ConnectionFlow<S> {
  private final Supplier<S> currentScreen;
  private final BooleanSupplier inWorld;
  private final Predicate<S> connecting;
  private final Function<S, String> disconnectReason;
  private final Map<S, Target> reports = new WeakHashMap<>();
  private Attempt<S> active;

  public ConnectionFlow(
      Supplier<S> currentScreen,
      BooleanSupplier inWorld,
      Predicate<S> connecting,
      Function<S, String> disconnectReason) {
    this.currentScreen = currentScreen;
    this.inWorld = inWorld;
    this.connecting = connecting;
    this.disconnectReason = disconnectReason;
  }

  public void begin(String host, int port, Runnable connect) {
    active = new Attempt<>(host, port, connect);
    try {
      ConnectGuard.run(connect);
    } catch (RuntimeException error) {
      active = null;
      throw error;
    }
  }

  public void clear() {
    active = null;
  }

  /** Suppresses only the first exact reset failure after a successful startup request. */
  public boolean intercept(S next) {
    if (active == null) {
      return false;
    }
    if (ConnectGuard.bypassed()) {
      if (connecting.test(next)) {
        active.screen = next;
      }
      return false;
    }
    if (currentScreen.get() == active.screen && active.screen != null) {
      String reason = disconnectReason.apply(next);
      if (reason != null) {
        if (active.retry.schedule(reason)) {
          return true;
        }
        FailureKind failure = FailureKind.connection(reason);
        if (failure != null) {
          reports.put(next, new Target(active.host, active.port, failure));
        }
      }
    }
    active = null;
    return false;
  }

  public Target report(S screen) {
    return reports.get(screen);
  }

  public void tick() {
    if (active == null) {
      return;
    }
    if (inWorld.getAsBoolean() || currentScreen.get() != active.screen) {
      active = null;
      return;
    }
    if (active.retry.tick()) {
      try {
        ConnectGuard.run(active.connect);
      } catch (RuntimeException error) {
        active = null;
        throw error;
      }
    }
  }

  /** Non-sensitive connection context retained only for an optional report. */
  public static final class Target {
    public final String host;
    public final int port;
    public final FailureKind failure;

    private Target(String host, int port, FailureKind failure) {
      this.host = host;
      this.port = port;
      this.failure = failure;
    }
  }

  private static final class Attempt<S> {
    final String host;
    final int port;
    final Runnable connect;
    final RetryState retry = new RetryState();
    S screen;

    Attempt(String host, int port, Runnable connect) {
      this.host = host;
      this.port = port;
      this.connect = connect;
    }
  }
}

package fr.bagyette.aternauto.common;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.util.concurrent.atomic.AtomicBoolean;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.concurrent.atomic.AtomicReference;
import org.junit.jupiter.api.Test;

class ConnectionFlowTest {
  private static final String RESET =
      "Internal Exception: java.net.SocketException: Connection reset";
  private final AtomicReference<TestScreen> current = new AtomicReference<>();
  private final AtomicBoolean inWorld = new AtomicBoolean();
  private final AtomicInteger connections = new AtomicInteger();
  private final ConnectionFlow<TestScreen> flow =
      new ConnectionFlow<>(
          current::get, inWorld::get, screen -> screen.connecting, screen -> screen.reason);
  private final Runnable connect =
      () -> {
        connections.incrementAndGet();
        TestScreen screen = new TestScreen(true, null);
        assertFalse(flow.intercept(screen));
        current.set(screen);
      };

  @Test
  void firstResetIsHiddenForExactly35TicksThenSecondFailureIsReported() {
    flow.begin("example.aternos.me", 25566, connect);
    TestScreen first = new TestScreen(false, RESET);
    assertTrue(flow.intercept(first));
    for (int tick = 0; tick < 34; tick++) {
      flow.tick();
    }
    assertEquals(1, connections.get());
    flow.tick();
    assertEquals(2, connections.get());
    TestScreen second = new TestScreen(false, RESET);
    assertFalse(flow.intercept(second));
    ConnectionFlow.Target target = flow.report(second);
    assertEquals("example.aternos.me", target.host);
    assertEquals(25566, target.port);
    assertEquals(FailureKind.CONNECTION_RESET, target.failure);
    for (int tick = 0; tick < 100; tick++) {
      flow.tick();
    }
    assertEquals(2, connections.get());
    assertNull(flow.report(first));
  }

  @Test
  void cancellingTheScreenDuringTheWaitPreventsReconnection() {
    flow.begin("example.aternos.me", 25565, connect);
    assertTrue(flow.intercept(new TestScreen(false, RESET)));
    TestScreen menu = new TestScreen(false, null);
    assertFalse(flow.intercept(menu));
    current.set(menu);
    for (int tick = 0; tick < 50; tick++) {
      flow.tick();
    }
    assertEquals(1, connections.get());
  }

  @Test
  void worldEntryCancelsThePendingRetry() {
    flow.begin("example.aternos.me", 25565, connect);
    assertTrue(flow.intercept(new TestScreen(false, RESET)));
    inWorld.set(true);
    for (int tick = 0; tick < 50; tick++) {
      flow.tick();
    }
    assertEquals(1, connections.get());
  }

  @Test
  void unrelatedKickIsShownWithoutRetryOrReport() {
    flow.begin("example.aternos.me", 25565, connect);
    TestScreen kicked = new TestScreen(false, "The server owner has disconnected you");
    assertFalse(flow.intercept(kicked));
    assertNull(flow.report(kicked));
    flow.tick();
    assertEquals(1, connections.get());
  }

  private static final class TestScreen {
    final boolean connecting;
    final String reason;

    TestScreen(boolean connecting, String reason) {
      this.connecting = connecting;
      this.reason = reason;
    }
  }
}

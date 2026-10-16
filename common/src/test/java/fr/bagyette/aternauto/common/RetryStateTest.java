package fr.bagyette.aternauto.common;

import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import org.junit.jupiter.api.Test;

class RetryStateTest {
  @Test
  void retriesOnExactlyTheThirtyFifthTickAndNeverAgain() {
    RetryState state = new RetryState();
    assertTrue(state.schedule(RetryState.CONNECTION_RESET));
    for (int i = 0; i < 34; i++) {
      assertFalse(state.tick());
    }
    assertTrue(state.tick());
    assertFalse(state.tick());
    assertFalse(state.schedule(RetryState.CONNECTION_RESET));
  }

  @Test
  void unrelatedErrorsDoNotConsumeTheRetry() {
    RetryState state = new RetryState();
    assertFalse(state.schedule("Connection timed out"));
    assertFalse(state.schedule("java.net.SocketException: Connection reset"));
    assertFalse(state.tick());
    assertTrue(state.schedule(RetryState.CONNECTION_RESET));
  }
}

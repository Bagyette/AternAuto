package fr.bagyette.aternauto.common;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicInteger;
import org.junit.jupiter.api.Test;

class RequestTaskTest {
  private static void awaitFinished(RequestTask task) throws Exception {
    long deadline = System.nanoTime() + TimeUnit.SECONDS.toNanos(3);
    while ((!task.complete() || RequestTask.running()) && System.nanoTime() < deadline) {
      Thread.sleep(1);
    }
    assertTrue(task.complete());
    assertFalse(RequestTask.running());
  }

  @Test
  void repeatedStartsAndASecondScreenNeverDuplicateTheRequest() throws Exception {
    AtomicInteger calls = new AtomicInteger();
    CountDownLatch entered = new CountDownLatch(1);
    CountDownLatch release = new CountDownLatch(1);
    RequestTask first =
        new RequestTask(
            new Messages("en"),
            (progress, cancelled) -> {
              calls.incrementAndGet();
              entered.countDown();
              release.await();
              return false;
            },
            () -> {});
    first.start();
    assertTrue(entered.await(2, TimeUnit.SECONDS));
    try {
      first.start();
      RequestTask second =
          new RequestTask(
              new Messages("fr"),
              (progress, cancelled) -> {
                calls.incrementAndGet();
                return true;
              },
              () -> {});
      second.start();
      assertTrue(second.complete());
      assertEquals(FailureKind.BUSY, second.failure());
      assertEquals(1, calls.get());
    } finally {
      release.countDown();
      awaitFinished(first);
    }
  }

  @Test
  void cancellationSuppressesLateAcceptanceEvenWhenTheTransportIgnoresInterrupts()
      throws Exception {
    CountDownLatch entered = new CountDownLatch(1);
    CountDownLatch release = new CountDownLatch(1);
    RequestTask task =
        new RequestTask(
            new Messages("en"),
            (progress, cancelled) -> {
              entered.countDown();
              while (true) {
                try {
                  release.await();
                  break;
                } catch (InterruptedException ignored) {
                  // Models an HTTP operation that completes after cancellation.
                }
              }
              return true;
            },
            () -> {});
    task.start();
    assertTrue(entered.await(2, TimeUnit.SECONDS));
    task.cancel();
    release.countDown();
    awaitFinished(task);
    assertFalse(task.accepted());
    assertEquals(null, task.failure());
  }

  @Test
  void counterFailureCannotFailAnAcceptedStartup() throws Exception {
    RequestTask task =
        new RequestTask(
            new Messages("en"),
            (progress, cancelled) -> true,
            () -> {
              throw new IllegalStateException("counter offline");
            });
    task.start();
    awaitFinished(task);
    assertTrue(task.accepted());
    assertEquals(null, task.failure());
  }
}

package fr.bagyette.aternauto.common;

import java.io.IOException;
import java.util.ArrayList;
import java.util.List;
import java.util.UUID;
import java.util.concurrent.FutureTask;
import java.util.concurrent.atomic.AtomicReference;
import java.util.function.BooleanSupplier;
import java.util.function.Consumer;
import java.util.function.ToIntFunction;

/** Background request state shared by every Minecraft adapter. */
public final class RequestTask {
  public static final String CREDIT = "AternAuto made by Bagyette0 (bagyette.fr on discord)";
  private volatile String status;
  private volatile boolean cancelled;
  private volatile boolean complete;
  private volatile boolean accepted;
  private volatile FailureKind failure;
  private volatile int httpStatus;
  private boolean started;
  private static final AtomicReference<RequestTask> ACTIVE = new AtomicReference<>();
  private final FutureTask<Void> future;
  private final Messages messages;

  interface Startup {
    boolean run(Consumer<String> progress, BooleanSupplier cancelled)
        throws IOException, InterruptedException;
  }

  public RequestTask(String host, UUID profileId, String username, String accessToken) {
    this(host, profileId, username, accessToken, new Messages("fr"));
  }

  public RequestTask(
      String host, UUID profileId, String username, String accessToken, Messages messages) {
    this(
        messages,
        (progress, cancelled) ->
            new DawnApi(messages)
                .start(host, profileId, username, accessToken, progress, cancelled),
        () -> StartTelemetry.send(BuildVersion.VERSION));
  }

  RequestTask(Messages messages, Startup startup, Runnable telemetry) {
    this.messages = messages;
    status = messages.text("status.verifying");
    future =
        new FutureTask<>(
            () -> {
              try {
                boolean newStart =
                    startup.run(
                        message -> {
                          if (!cancelled) {
                            status = message;
                          }
                        },
                        () -> cancelled);
                if (newStart) {
                  try {
                    telemetry.run();
                  } catch (RuntimeException ignored) {
                    // An unavailable counter cannot turn a successful start into a failure.
                  }
                }
                if (!cancelled) {
                  accepted = true;
                  status = messages.text("status.accepted");
                }
              } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
              } catch (DawnFailure e) {
                failure = e.kind();
                httpStatus = e.httpStatus();
                status = e.getMessage();
              } catch (IOException e) {
                failure = FailureKind.NETWORK;
                status = failure.message(messages, 0);
              } catch (RuntimeException e) {
                failure = FailureKind.UNEXPECTED;
                status = messages.text("error.failed");
              } finally {
                complete = true;
              }
              return null;
            });
  }

  public synchronized void start() {
    if (started || cancelled) {
      return;
    }
    started = true;
    if (!ACTIVE.compareAndSet(null, this)) {
      failure = FailureKind.BUSY;
      status = failure.message(messages, 0);
      complete = true;
      return;
    }
    Thread worker =
        new Thread(
            () -> {
              try {
                future.run();
              } finally {
                ACTIVE.compareAndSet(this, null);
              }
            },
            "AternAuto");
    worker.setDaemon(true);
    try {
      worker.start();
    } catch (RuntimeException e) {
      ACTIVE.compareAndSet(this, null);
      throw e;
    }
  }

  public synchronized void cancel() {
    cancelled = true;
    future.cancel(true);
  }

  public String status() {
    return status;
  }

  public boolean complete() {
    return complete;
  }

  public boolean accepted() {
    return accepted && !cancelled;
  }

  public FailureKind failure() {
    return cancelled ? null : failure;
  }

  public int httpStatus() {
    return httpStatus;
  }

  static boolean running() {
    return ACTIVE.get() != null;
  }

  public static List<String> wrap(String text, int width, ToIntFunction<String> measure) {
    List<String> lines = new ArrayList<>();
    String line = "";
    for (String word : text.split(" ")) {
      int limit = Math.max(100, width);
      if (measure.applyAsInt(word) > limit) {
        if (!line.isEmpty()) {
          lines.add(line);
          line = "";
        }
        for (int offset = 0; offset < word.length(); ) {
          int end = offset + Character.charCount(word.codePointAt(offset));
          while (end < word.length()) {
            int next = end + Character.charCount(word.codePointAt(end));
            if (measure.applyAsInt(word.substring(offset, next)) > limit) {
              break;
            }
            end = next;
          }
          lines.add(word.substring(offset, end));
          offset = end;
        }
        continue;
      }
      String candidate = line.isEmpty() ? word : line + " " + word;
      if (!line.isEmpty() && measure.applyAsInt(candidate) > Math.max(100, width)) {
        lines.add(line);
        line = word;
      } else {
        line = candidate;
      }
    }
    if (!line.isEmpty()) {
      lines.add(line);
    }
    return lines;
  }
}

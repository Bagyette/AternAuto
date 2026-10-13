package fr.autoaternos;

import java.io.IOException;
import java.util.ArrayList;
import java.util.List;
import java.util.UUID;
import java.util.concurrent.FutureTask;
import java.util.function.ToIntFunction;

/** Background request state shared by every Minecraft adapter. */
public final class RequestTask {
  public static final String CREDIT = "AternAuto made by Bagyette0 (bagyette.fr on discord)";
  private volatile String status;
  private volatile boolean cancelled;
  private volatile boolean complete;
  private volatile boolean accepted;
  private final FutureTask<Void> future;

  public RequestTask(String host, UUID profileId, String username, String accessToken) {
    this(host, profileId, username, accessToken, new Messages("fr"));
  }

  public RequestTask(
      String host, UUID profileId, String username, String accessToken, Messages messages) {
    status = messages.text("status.verifying");
    future =
        new FutureTask<>(
            () -> {
              try {
                new DawnApi(messages)
                    .start(
                        host,
                        profileId,
                        username,
                        accessToken,
                        message -> status = message,
                        () -> cancelled);
                accepted = true;
                status = messages.text("status.accepted");
              } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
              } catch (IOException e) {
                status = e.getMessage();
              } catch (RuntimeException e) {
                status = messages.text("error.failed");
              } finally {
                complete = true;
              }
              return null;
            });
  }

  public void start() {
    Thread worker = new Thread(future, "AternAuto");
    worker.setDaemon(true);
    worker.start();
  }

  public void cancel() {
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
    return accepted;
  }

  public static List<String> wrap(String text, int width, ToIntFunction<String> measure) {
    List<String> lines = new ArrayList<>();
    String line = "";
    for (String word : text.split(" ")) {
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

package fr.bagyette.aternauto.common;

import java.util.function.Supplier;

/** Two-click report consent and one background submission, retained across screen resizes. */
public final class ReportPrompt {
  private enum State {
    CLOSED,
    PREVIEW,
    SENDING,
    SENT,
    FAILED
  }

  private final Messages messages;
  private final Supplier<IssueReport> snapshot;
  private final java.util.function.Consumer<IssueReport> sender;
  private volatile State state = State.CLOSED;
  private IssueReport report;
  private int previewPage;
  private int previewPages = 1;
  private boolean previewReady;

  public ReportPrompt(Messages messages, Supplier<IssueReport> snapshot) {
    this(
        messages,
        snapshot,
        report -> {
          try {
            report.send();
          } catch (Exception e) {
            throw new IllegalStateException("Report not delivered");
          }
        });
  }

  ReportPrompt(
      Messages messages,
      Supplier<IssueReport> snapshot,
      java.util.function.Consumer<IssueReport> sender) {
    this.messages = messages;
    this.snapshot = snapshot;
    this.sender = sender;
  }

  public boolean opened() {
    return state != State.CLOSED;
  }

  public boolean actionable() {
    return state == State.CLOSED || state == State.PREVIEW;
  }

  public String label() {
    return messages.text(
        state == State.PREVIEW
            ? previewPage + 1 < previewPages ? "report.next" : "report.send"
            : "report.button");
  }

  public java.util.List<String> lines(
      int width, java.util.function.ToIntFunction<String> measure, int availableLines) {
    java.util.List<String> all = RequestTask.wrap(status(), width, measure);
    int size = Math.max(1, availableLines);
    if (state == State.PREVIEW) {
      previewPages = Math.max(1, (all.size() + size - 1) / size);
      previewPage = Math.min(previewPage, previewPages - 1);
      previewReady = true;
      int start = previewPage * size;
      return all.subList(start, Math.min(start + size, all.size()));
    }
    return all;
  }

  public String status() {
    switch (state) {
      case PREVIEW:
        return report.notice(messages);
      case SENDING:
        return messages.text("report.sending");
      case SENT:
        return messages.text("report.sent")
            + (report.receipt().isEmpty() ? "" : " #" + report.receipt());
      case FAILED:
        return messages.text("report.failed");
      default:
        return "";
    }
  }

  public synchronized void click() {
    if (state == State.CLOSED) {
      try {
        report = snapshot.get();
        state = State.PREVIEW;
      } catch (RuntimeException e) {
        state = State.FAILED;
      }
      return;
    }
    if (state != State.PREVIEW) {
      return;
    }
    if (!previewReady) {
      return;
    }
    if (previewPage + 1 < previewPages) {
      previewPage++;
      previewReady = false;
      return;
    }
    state = State.SENDING;
    Thread worker =
        new Thread(
            () -> {
              try {
                sender.accept(report);
                state = State.SENT;
              } catch (RuntimeException e) {
                state = State.FAILED;
              }
            },
            "AternAuto issue report");
    worker.setDaemon(true);
    try {
      worker.start();
    } catch (RuntimeException e) {
      state = State.FAILED;
    }
  }
}

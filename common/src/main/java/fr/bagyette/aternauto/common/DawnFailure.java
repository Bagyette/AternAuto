package fr.bagyette.aternauto.common;

import java.io.IOException;

/** A classified failure with no raw response body, URL or credentials. */
public final class DawnFailure extends IOException {
  private final FailureKind kind;
  private final int httpStatus;

  DawnFailure(FailureKind kind, Messages messages) {
    this(kind, 0, messages);
  }

  DawnFailure(FailureKind kind, int httpStatus, Messages messages) {
    super(kind.message(messages, httpStatus));
    this.kind = kind;
    this.httpStatus = httpStatus;
  }

  public FailureKind kind() {
    return kind;
  }

  public int httpStatus() {
    return httpStatus;
  }
}

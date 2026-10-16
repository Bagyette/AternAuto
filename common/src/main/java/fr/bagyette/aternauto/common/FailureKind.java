package fr.bagyette.aternauto.common;

/** Stable error identifiers; reports never contain exception messages or account data. */
public enum FailureKind {
  HOST("error.host", false),
  ACCOUNT("error.account", false),
  SESSION("error.session", false),
  PERMISSION("error.permission", false),
  RATE_LIMIT("error.rate_limit", false),
  BUSY("error.busy", false),
  NETWORK("error.network", true),
  TIMEOUT("error.timeout", true),
  TLS("error.tls", true),
  HTTP_ERROR("error.http", true),
  INVALID_RESPONSE("error.response", true),
  MISSING_TOKEN("error.token", true),
  UNEXPECTED("error.failed", true),
  CONNECTION_RESET("error.connection_reset", true),
  CONNECTION_TIMEOUT("error.connection_timeout", true);

  private final String key;
  private final boolean reportable;

  FailureKind(String key, boolean reportable) {
    this.key = key;
    this.reportable = reportable;
  }

  public String message(Messages messages, int httpStatus) {
    return this == HTTP_ERROR ? messages.text(key, httpStatus) : messages.text(key);
  }

  public boolean reportable() {
    return reportable;
  }

  public static FailureKind connection(String reason) {
    if (RetryState.CONNECTION_RESET.equals(reason)) {
      return CONNECTION_RESET;
    }
    if ("Connection timed out".equals(reason)
        || "Internal Exception: io.netty.handler.timeout.ReadTimeoutException".equals(reason)) {
      return CONNECTION_TIMEOUT;
    }
    return null;
  }
}

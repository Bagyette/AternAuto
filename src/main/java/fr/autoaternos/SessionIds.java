package fr.autoaternos;

import java.util.UUID;

/** Handles the dashed and compact session identifiers used by older launchers. */
public final class SessionIds {
  private SessionIds() {}

  public static UUID parse(String value) {
    if (value == null) {
      return null;
    }
    String compact = value.replace("-", "");
    if (!compact.matches("[0-9a-fA-F]{32}")) {
      return null;
    }
    return UUID.fromString(
        compact.substring(0, 8)
            + "-"
            + compact.substring(8, 12)
            + "-"
            + compact.substring(12, 16)
            + "-"
            + compact.substring(16, 20)
            + "-"
            + compact.substring(20));
  }
}

package fr.bagyette.aternauto.common;

import com.google.gson.GsonBuilder;
import com.google.gson.JsonArray;
import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import com.google.gson.JsonPrimitive;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.nio.file.StandardCopyOption;
import java.time.Instant;
import java.util.LinkedHashSet;
import java.util.Locale;
import java.util.Map;
import java.util.Set;

/** Explicitly enabled local diagnostics; never sends the journal over the network. */
public final class ConnectionDiagnostics {
  private static final boolean ENABLED = Boolean.getBoolean("aternauto.diagnostics");
  private static final Set<String> SECRETS = new LinkedHashSet<>();
  private static final JsonArray EVENTS = new JsonArray();
  private static final Path LOG = Paths.get("logs", "aternauto-dawn-diagnostics.json");

  private ConnectionDiagnostics() {}

  public static synchronized void protect(String... values) {
    if (!ENABLED) {
      return;
    }
    for (String value : values) {
      if (value != null && value.length() >= 3) {
        SECRETS.add(value);
      }
    }
  }

  public static synchronized void response(String path, int status, String body) {
    if (!ENABLED) {
      return;
    }
    JsonObject event = new JsonObject();
    event.addProperty("at", Instant.now().toString());
    event.addProperty(
        "stage", path.endsWith("/aternos/auto-start") ? "auto-start" : "authentication");
    event.addProperty("httpStatus", status);
    if (path.endsWith("/aternos/auto-start")) {
      try {
        event.add("response", sanitize(new JsonParser().parse(body)));
      } catch (RuntimeException e) {
        event.addProperty("response", clean(body));
      }
    }
    EVENTS.add(event);
    try {
      Files.createDirectories(LOG.getParent());
      Path temporary = LOG.resolveSibling(LOG.getFileName() + ".tmp");
      Files.write(
          temporary,
          new GsonBuilder()
              .setPrettyPrinting()
              .create()
              .toJson(EVENTS)
              .getBytes(StandardCharsets.UTF_8));
      Files.move(temporary, LOG, StandardCopyOption.REPLACE_EXISTING);
    } catch (IOException ignored) {
      // A diagnostic failure must not change connection behavior.
    }
  }

  private static JsonElement sanitize(JsonElement value) {
    if (value.isJsonObject()) {
      JsonObject result = new JsonObject();
      for (Map.Entry<String, JsonElement> entry : value.getAsJsonObject().entrySet()) {
        String key = entry.getKey().toLowerCase(Locale.ROOT);
        if (key.matches(
            ".*(token|authorization|password|username|uuid|profile|address|hostname|ip).*")) {
          result.addProperty(entry.getKey(), "[redacted]");
        } else {
          result.add(entry.getKey(), sanitize(entry.getValue()));
        }
      }
      return result;
    }
    if (value.isJsonArray()) {
      JsonArray result = new JsonArray();
      for (JsonElement item : value.getAsJsonArray()) {
        result.add(sanitize(item));
      }
      return result;
    }
    if (value.isJsonPrimitive() && value.getAsJsonPrimitive().isString()) {
      return new JsonPrimitive(clean(value.getAsString()));
    }
    return value;
  }

  private static String clean(String value) {
    String result = value;
    for (String secret : SECRETS) {
      result = result.replace(secret, "[redacted]");
    }
    return result
        .replaceAll("(?i)[a-z0-9._-]+\\.(aternos|exaroton)\\.me", "[server]")
        .replaceAll("(?i)Bearer\\s+\\S+", "Bearer [redacted]")
        .replaceAll("[A-Za-z0-9_-]{16,}\\.[A-Za-z0-9_-]{16,}\\.[A-Za-z0-9_-]+", "[token]");
  }
}

package fr.bagyette.aternauto.common;

import com.google.gson.JsonObject;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URI;
import java.nio.charset.StandardCharsets;

/** Best-effort, anonymous counter: no identifier, server address or Minecraft credential. */
public final class StartTelemetry {
  private static final URI ENDPOINT = URI.create("https://aa.bagyette.fr/ping");
  private static final String DIGITS = "MTFKARPLSB";

  private StartTelemetry() {}

  public static void send(String version) {
    Thread worker =
        new Thread(
            () -> {
              HttpURLConnection connection = null;
              try {
                connection = (HttpURLConnection) ENDPOINT.toURL().openConnection();
                connection.setConnectTimeout(3000);
                connection.setReadTimeout(3000);
                connection.setInstanceFollowRedirects(false);
                connection.setRequestMethod("POST");
                connection.setRequestProperty("Content-Type", "application/json; charset=utf-8");
                connection.setRequestProperty("User-Agent", "AternAuto/" + version);
                byte[] body = payload(version, System.currentTimeMillis() / 1000);
                connection.setDoOutput(true);
                connection.setFixedLengthStreamingMode(body.length);
                try (OutputStream output = connection.getOutputStream()) {
                  output.write(body);
                }
                // No retry: a lost reply must not count the same start twice.
                if (connection.getResponseCode() == HttpURLConnection.HTTP_NO_CONTENT) {
                  try (InputStream input = connection.getInputStream()) {
                    // Closing the response releases the connection without buffering its body.
                  }
                }
              } catch (Exception ignored) {
                // Statistics must never affect gameplay or expose credentials in a log.
              } finally {
                if (connection != null) {
                  connection.disconnect();
                }
              }
            },
            "AternAuto statistics");
    worker.setDaemon(true);
    worker.start();
  }

  static byte[] payload(String version, long timestamp) {
    StringBuilder key = new StringBuilder();
    for (char digit : Long.toString(timestamp).toCharArray()) {
      key.append(DIGITS.charAt(digit - '0'));
    }
    JsonObject json = new JsonObject();
    json.addProperty("version", version);
    json.addProperty("k", key.toString());
    return json.toString().getBytes(StandardCharsets.UTF_8);
  }
}

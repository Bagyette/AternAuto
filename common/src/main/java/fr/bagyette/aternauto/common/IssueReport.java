package fr.bagyette.aternauto.common;

import com.google.gson.JsonArray;
import com.google.gson.JsonObject;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URI;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.Collections;
import java.util.Comparator;
import java.util.List;
import java.util.Locale;

/** Explicitly submitted environment snapshot; no credentials, full logs or JAR contents. */
public final class IssueReport {
  private static final URI ENDPOINT = URI.create("https://aa.bagyette.fr/issue/dscwh/");
  private final JsonObject body = new JsonObject();
  private final int modCount;
  private volatile String receipt = "";

  public static final class Mod {
    final String name;
    final String version;

    public Mod(String name, String version) {
      this.name = clean(name, 128);
      this.version = clean(version, 128);
    }
  }

  public IssueReport(
      String minecraft,
      String loader,
      String loaderVersion,
      List<Mod> mods,
      String server,
      int port,
      FailureKind error,
      int httpStatus) {
    if (error == null || !error.reportable()) {
      throw new IllegalArgumentException("Not a reportable error");
    }
    body.addProperty("version", BuildVersion.VERSION);
    body.addProperty("minecraft", clean(minecraft, 80));
    body.addProperty("loader", loader);
    body.addProperty("loaderVersion", clean(loaderVersion, 80));
    body.addProperty("java", clean(System.getProperty("java.version", "Unknown"), 80));
    String os = System.getProperty("os.name", "").toLowerCase(Locale.ROOT);
    body.addProperty(
        "os",
        os.startsWith("windows")
            ? "Windows"
            : os.contains("mac") ? "macOS" : os.contains("linux") ? "Linux" : "Other");
    body.addProperty("server", clean(server, 253));
    body.addProperty("port", port);
    body.addProperty("error", error.name());
    body.addProperty("httpStatus", httpStatus);
    body.addProperty("userAgent", ClientUserAgent.current());
    body.addProperty("consent", true);
    List<Mod> sorted = new ArrayList<>(mods);
    Collections.sort(sorted, Comparator.comparing(mod -> mod.name));
    if (sorted.size() > 2000) {
      throw new IllegalArgumentException("Too many mods to report");
    }
    JsonArray entries = new JsonArray();
    for (Mod mod : sorted) {
      JsonObject entry = new JsonObject();
      entry.addProperty("name", mod.name);
      entry.addProperty("version", mod.version);
      entries.add(entry);
    }
    modCount = sorted.size();
    body.add("mods", entries);
  }

  public String notice(Messages messages) {
    return messages.text(
            "report.notice",
            body.get("server").getAsString(),
            body.get("port").getAsInt(),
            modCount)
        + " "
        + body.get("minecraft").getAsString()
        + " / "
        + body.get("loader").getAsString()
        + " "
        + body.get("loaderVersion").getAsString()
        + " / Java "
        + body.get("java").getAsString()
        + " / "
        + body.get("os").getAsString()
        + " / "
        + body.get("error").getAsString()
        + " / User-Agent: "
        + body.get("userAgent").getAsString()
        + " — aa.bagyette.fr/privacy";
  }

  String receipt() {
    return receipt;
  }

  byte[] payload() {
    return body.toString().getBytes(StandardCharsets.UTF_8);
  }

  void send() throws Exception {
    HttpURLConnection connection = (HttpURLConnection) ENDPOINT.toURL().openConnection();
    try {
      connection.setConnectTimeout(5000);
      connection.setReadTimeout(10000);
      connection.setInstanceFollowRedirects(false);
      connection.setRequestMethod("POST");
      connection.setRequestProperty("Content-Type", "application/json; charset=utf-8");
      connection.setRequestProperty("User-Agent", "AternAuto/" + BuildVersion.VERSION);
      byte[] bytes = payload();
      connection.setDoOutput(true);
      connection.setFixedLengthStreamingMode(bytes.length);
      try (OutputStream output = connection.getOutputStream()) {
        output.write(bytes);
      }
      if (connection.getResponseCode() != 201) {
        throw new java.io.IOException("Report not delivered");
      }
      try (java.io.InputStream input = connection.getInputStream()) {
        // The relay confirms Discord delivery before returning HTTP 201.
        java.io.ByteArrayOutputStream response = new java.io.ByteArrayOutputStream();
        byte[] buffer = new byte[256];
        int count;
        while ((count = input.read(buffer)) != -1) {
          if (response.size() + count > 1024) {
            throw new java.io.IOException("Invalid report receipt");
          }
          response.write(buffer, 0, count);
        }
        String id =
            new com.google.gson.JsonParser()
                .parse(new String(response.toByteArray(), StandardCharsets.UTF_8))
                .getAsJsonObject()
                .get("reportId")
                .getAsString();
        if (!id.matches("[a-f0-9]{12}")) {
          throw new java.io.IOException("Invalid report receipt");
        }
        receipt = id;
      }
    } finally {
      connection.disconnect();
    }
  }

  private static String clean(String value, int limit) {
    if (value == null || value.trim().isEmpty()) {
      return "Unknown";
    }
    String result = value.replaceAll("[\\p{Cntrl}\\p{Cf}]", " ").trim();
    return result.isEmpty() ? "Unknown" : result.substring(0, Math.min(limit, result.length()));
  }
}

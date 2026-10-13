package fr.autoaternos;

import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URI;
import java.net.URLEncoder;
import java.nio.charset.StandardCharsets;
import java.util.Locale;
import java.util.UUID;
import java.util.function.BooleanSupplier;
import java.util.function.Consumer;

/** Independent implementation of the small protocol observed in Dawn stable/901fe54e. */
public final class DawnApi {
  private static final URI BASE = URI.create("https://api.dawn.gg/v2/");
  private static final URI MOJANG_JOIN =
      URI.create("https://sessionserver.mojang.com/session/minecraft/join");
  private final Transport transport;
  private final URI base;
  private final URI mojangJoin;
  private final Messages messages;

  public DawnApi() {
    this(new HttpTransport(), BASE, MOJANG_JOIN);
  }

  public DawnApi(Messages messages) {
    this(new HttpTransport(), BASE, MOJANG_JOIN, messages);
  }

  DawnApi(URI base, URI mojangJoin) {
    this(new HttpTransport(), base, mojangJoin);
  }

  // Injectable only for local protocol tests. Production endpoints are fixed HTTPS URLs.
  DawnApi(Transport transport, URI base, URI mojangJoin) {
    this(transport, base, mojangJoin, new Messages("fr"));
  }

  private DawnApi(Transport transport, URI base, URI mojangJoin, Messages messages) {
    this.transport = transport;
    this.base = base;
    this.mojangJoin = mojangJoin;
    this.messages = messages;
  }

  public static boolean isSupportedHost(String host) {
    String normalized = host.toLowerCase(Locale.ROOT);
    return normalized.endsWith(".aternos.me") || normalized.endsWith(".exaroton.me");
  }

  public void start(
      String host,
      UUID profileId,
      String username,
      String minecraftToken,
      Consumer<String> progress,
      BooleanSupplier cancelled)
      throws IOException, InterruptedException {
    if (!isSupportedHost(host)) {
      throw new IOException(messages.text("error.host"));
    }
    if (profileId == null
        || username == null
        || username.trim().isEmpty()
        || minecraftToken == null
        || minecraftToken.trim().isEmpty()
        || minecraftToken.equals("0")) {
      throw new IOException(messages.text("error.account"));
    }
    checkCancelled(cancelled);
    progress.accept(messages.text("status.verifying"));
    String challenge =
        field(json(request("GET", base.resolve("minecraft/server-id"), null, null)), "token");

    checkCancelled(cancelled);
    JsonObject join = new JsonObject();
    join.addProperty("accessToken", minecraftToken);
    join.addProperty("selectedProfile", profileId.toString().replace("-", ""));
    join.addProperty("serverId", challenge);
    request("POST", mojangJoin, join.toString(), null);

    checkCancelled(cancelled);
    // Only the challenge goes to Dawn; the Minecraft access token goes to Mojang only.
    URI verify =
        base.resolve("minecraft/has-joined/" + encode(username) + "?token=" + encode(challenge));
    String dawnToken = field(json(request("GET", verify, null, null)), "token");

    checkCancelled(cancelled);
    progress.accept(messages.text("status.requesting"));
    JsonObject payload = new JsonObject();
    payload.addProperty("serverAddress", host.toLowerCase(Locale.ROOT));
    request("POST", base.resolve("aternos/auto-start"), payload.toString(), "Bearer " + dawnToken);
  }

  private String request(String method, URI uri, String body, String authorization)
      throws IOException, InterruptedException {
    Reply reply;
    try {
      reply = transport.send(method, uri, body, authorization);
    } catch (IOException e) {
      throw new IOException(messages.text("error.network"));
    }
    if (reply.status < 200 || reply.status >= 300) {
      String message;
      switch (reply.status) {
        case 401:
          message = messages.text("error.session");
          break;
        case 403:
          message = messages.text("error.permission");
          break;
        case 429:
          message = messages.text("error.rate_limit");
          break;
        default:
          message = messages.text("error.http", reply.status);
      }
      // Do not include response bodies, URLs, usernames or tokens in exceptions/logs.
      throw new IOException(message);
    }
    return reply.body;
  }

  private JsonObject json(String body) throws IOException {
    try {
      return new JsonParser().parse(body).getAsJsonObject();
    } catch (RuntimeException e) {
      throw new IOException(messages.text("error.response"));
    }
  }

  private String field(JsonObject json, String key) throws IOException {
    try {
      String value = json.get(key).getAsString();
      if (!value.trim().isEmpty() && !value.contains("\r") && !value.contains("\n")) {
        return value;
      }
    } catch (RuntimeException ignored) {
      // Missing and malformed fields use the same message below.
    }
    throw new IOException(messages.text("error.token"));
  }

  private static String encode(String value) {
    try {
      return URLEncoder.encode(value, "UTF-8");
    } catch (java.io.UnsupportedEncodingException e) {
      throw new AssertionError(e);
    }
  }

  private static void checkCancelled(BooleanSupplier cancelled) throws InterruptedException {
    if (cancelled.getAsBoolean() || Thread.currentThread().isInterrupted()) {
      throw new InterruptedException("Annulé");
    }
  }

  static final class Reply {
    final int status;
    final String body;

    Reply(int status, String body) {
      this.status = status;
      this.body = body;
    }
  }

  @FunctionalInterface
  interface Transport {
    Reply send(String method, URI uri, String body, String authorization)
        throws IOException, InterruptedException;
  }

  private static final class HttpTransport implements Transport {
    public Reply send(String method, URI uri, String body, String authorization)
        throws IOException, InterruptedException {
      HttpURLConnection connection = (HttpURLConnection) uri.toURL().openConnection();
      try {
        connection.setConnectTimeout(10000);
        connection.setReadTimeout(15000);
        connection.setInstanceFollowRedirects(false);
        connection.setRequestMethod(method);
        connection.setRequestProperty("User-Agent", "DawnClient/1.0.0");
        if (authorization != null) {
          connection.setRequestProperty("Authorization", authorization);
        }
        if (body != null) {
          connection.setRequestProperty("Content-Type", "application/json");
          connection.setDoOutput(true);
          byte[] encoded = body.getBytes(StandardCharsets.UTF_8);
          connection.setFixedLengthStreamingMode(encoded.length);
          try (OutputStream output = connection.getOutputStream()) {
            output.write(encoded);
          }
        }
        int status = connection.getResponseCode();
        if (status < 200 || status >= 300) {
          return new Reply(status, "");
        }
        try (InputStream input = connection.getInputStream();
            ByteArrayOutputStream output = new ByteArrayOutputStream()) {
          byte[] buffer = new byte[4096];
          int length;
          while ((length = input.read(buffer)) != -1) {
            if (Thread.currentThread().isInterrupted()) {
              throw new InterruptedException("Annulé");
            }
            if (output.size() + length > 1048576) {
              throw new IOException("Response too large");
            }
            output.write(buffer, 0, length);
          }
          return new Reply(status, new String(output.toByteArray(), StandardCharsets.UTF_8));
        }
      } finally {
        connection.disconnect();
      }
    }
  }
}

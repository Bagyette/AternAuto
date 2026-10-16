package fr.bagyette.aternauto.common;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.sun.net.httpserver.HttpServer;
import java.io.IOException;
import java.net.InetSocketAddress;
import java.net.URI;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.List;
import java.util.UUID;
import org.junit.jupiter.api.Test;

class TransportTest {
  @Test
  void realTransportUsesJsonAndSendsEachSecretOnlyToItsIntendedEndpoint() throws Exception {
    HttpServer server = HttpServer.create(new InetSocketAddress("127.0.0.1", 0), 0);
    List<String> calls = new ArrayList<>();
    List<String> agents = new ArrayList<>();
    server.createContext(
        "/",
        exchange -> {
          String path = exchange.getRequestURI().getPath();
          String body =
              new String(exchange.getRequestBody().readAllBytes(), StandardCharsets.UTF_8);
          String auth = exchange.getRequestHeaders().getFirst("Authorization");
          calls.add(path + "|" + body + "|" + auth);
          String agent = exchange.getRequestHeaders().getFirst("User-Agent");
          agents.add(agent);
          assertTrue(
              agent.matches("[A-Za-z]+/" + java.util.regex.Pattern.quote(BuildVersion.VERSION)));
          if (exchange.getRequestMethod().equals("POST")) {
            assertEquals("application/json", exchange.getRequestHeaders().getFirst("Content-Type"));
          }
          String response =
              path.endsWith("server-id")
                  ? "{\"token\":\"challenge\"}"
                  : path.contains("has-joined") ? "{\"token\":\"dawn-secret\"}" : "";
          byte[] bytes = response.getBytes(StandardCharsets.UTF_8);
          exchange.sendResponseHeaders(
              bytes.length == 0 ? 204 : 200, bytes.length == 0 ? -1 : bytes.length);
          if (bytes.length > 0) {
            exchange.getResponseBody().write(bytes);
          }
          exchange.close();
        });
    server.start();
    try {
      URI base = URI.create("http://127.0.0.1:" + server.getAddress().getPort() + "/");
      new DawnApi(base, base.resolve("mojang-join"))
          .start(
              "server.aternos.me",
              UUID.randomUUID(),
              "Player",
              "minecraft-secret",
              ignored -> {},
              () -> false);
      assertEquals(4, calls.size());
      assertEquals(1, new java.util.HashSet<>(agents).size());
      assertTrue(calls.get(1).contains("minecraft-secret"));
      assertTrue(calls.get(3).endsWith("Bearer dawn-secret"));
      for (int index : new int[] {0, 2, 3}) {
        assertFalse(calls.get(index).contains("minecraft-secret"));
      }
    } finally {
      server.stop(0);
    }
  }

  @Test
  void redirectIsRejectedInsteadOfFollowingIt() throws Exception {
    HttpServer server = HttpServer.create(new InetSocketAddress("127.0.0.1", 0), 0);
    List<String> calls = new ArrayList<>();
    server.createContext(
        "/",
        exchange -> {
          calls.add(exchange.getRequestURI().getPath());
          exchange.getResponseHeaders().add("Location", "/unexpected");
          exchange.sendResponseHeaders(302, -1);
          exchange.close();
        });
    server.start();
    try {
      URI base = URI.create("http://127.0.0.1:" + server.getAddress().getPort() + "/");
      assertThrows(
          IOException.class,
          () ->
              new DawnApi(base, base.resolve("join"))
                  .start(
                      "server.aternos.me",
                      UUID.randomUUID(),
                      "Player",
                      "secret",
                      ignored -> {},
                      () -> false));
      assertEquals(1, calls.size());
    } finally {
      server.stop(0);
    }
  }
}

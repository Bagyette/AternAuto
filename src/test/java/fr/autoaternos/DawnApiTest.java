package fr.autoaternos;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.junit.jupiter.api.Assertions.fail;

import com.google.gson.JsonParser;
import java.io.IOException;
import java.net.URI;
import java.util.ArrayList;
import java.util.List;
import java.util.UUID;
import java.util.concurrent.atomic.AtomicBoolean;
import org.junit.jupiter.api.Test;

class DawnApiTest {
  private static final URI BASE = URI.create("https://api.example.test/v2/");
  private static final URI JOIN = URI.create("https://mojang.example.test/join");
  private static final UUID ID = UUID.fromString("11111111-2222-3333-4444-555555555555");

  record Call(String method, URI uri, String body, String authorization) {}

  @Test
  void performsMinecraftProofBeforeStartAndNeverSendsMinecraftTokenToDawn() throws Exception {
    List<Call> calls = new ArrayList<>();
    List<String> progress = new ArrayList<>();
    DawnApi api =
        new DawnApi(
            (method, uri, body, auth) -> {
              calls.add(new Call(method, uri, body, auth));
              return switch (calls.size()) {
                case 1 -> new DawnApi.Reply(200, "{\"token\":\"challenge\"}");
                case 2 -> new DawnApi.Reply(204, "");
                case 3 -> new DawnApi.Reply(200, "{\"token\":\"dawn-jwt\"}");
                default -> new DawnApi.Reply(204, "");
              };
            },
            BASE,
            JOIN);
    api.start("MyServer.aternos.me", ID, "Player", "minecraft-secret", progress::add, () -> false);
    assertEquals(4, calls.size());
    assertEquals(BASE.resolve("minecraft/server-id"), calls.get(0).uri);
    assertEquals(JOIN, calls.get(1).uri);
    var join = (new JsonParser()).parse(calls.get(1).body).getAsJsonObject();
    assertEquals("minecraft-secret", join.get("accessToken").getAsString());
    assertEquals("11111111222233334444555555555555", join.get("selectedProfile").getAsString());
    assertEquals("challenge", join.get("serverId").getAsString());
    assertEquals(BASE.resolve("minecraft/has-joined/Player?token=challenge"), calls.get(2).uri);
    Call start = calls.get(3);
    assertEquals("POST", start.method);
    assertEquals(BASE.resolve("aternos/auto-start"), start.uri);
    assertEquals("Bearer dawn-jwt", start.authorization);
    assertEquals(
        "myserver.aternos.me",
        (new JsonParser()).parse(start.body).getAsJsonObject().get("serverAddress").getAsString());
    for (int i : new int[] {0, 2, 3}) {
      assertFalse(calls.get(i).toString().contains("minecraft-secret"));
    }
    assertEquals(2, progress.size());
  }

  @Test
  void rejectsUnrelatedHostsAndOfflineAccountsBeforeAnyNetworkRequest() {
    DawnApi api =
        new DawnApi(
            (method, uri, body, auth) -> {
              fail("Unexpected network request");
              return null;
            },
            BASE,
            JOIN);
    for (String host :
        new String[] {
          "example.org", "server.aternos.me.evil.test", "fakeaternos.me", "aternos.me"
        }) {
      assertFalse(DawnApi.isSupportedHost(host));
      assertThrows(
          IOException.class,
          () -> api.start(host, ID, "Player", "valid", ignored -> {}, () -> false));
    }
    assertTrue(DawnApi.isSupportedHost("SERVER.ATERNOS.ME"));
    assertTrue(DawnApi.isSupportedHost("server.exaroton.me"));
    assertThrows(
        IOException.class,
        () -> api.start("server.aternos.me", ID, "Player", "0", ignored -> {}, () -> false));
  }

  @Test
  void authenticationFailureDoesNotSendStartRequestOrExposeResponseBody() {
    List<URI> calls = new ArrayList<>();
    DawnApi api =
        new DawnApi(
            (method, uri, body, auth) -> {
              calls.add(uri);
              return calls.size() == 1
                  ? new DawnApi.Reply(200, "{\"token\":\"challenge\"}")
                  : new DawnApi.Reply(403, "SECRET_BODY");
            },
            BASE,
            JOIN);
    IOException error =
        assertThrows(
            IOException.class,
            () ->
                api.start("server.aternos.me", ID, "Player", "secret", ignored -> {}, () -> false));
    assertEquals(2, calls.size());
    assertFalse(error.getMessage().contains("SECRET_BODY"));
    assertFalse(calls.contains(BASE.resolve("aternos/auto-start")));
  }

  @Test
  void cancellationAfterChallengeStopsBeforeSessionProofAndStart() {
    AtomicBoolean cancelled = new AtomicBoolean();
    List<URI> calls = new ArrayList<>();
    DawnApi api =
        new DawnApi(
            (method, uri, body, auth) -> {
              calls.add(uri);
              cancelled.set(true);
              return new DawnApi.Reply(200, "{\"token\":\"challenge\"}");
            },
            BASE,
            JOIN);
    assertThrows(
        InterruptedException.class,
        () ->
            api.start("server.aternos.me", ID, "Player", "secret", ignored -> {}, cancelled::get));
    assertEquals(1, calls.size());
  }

  @Test
  void malformedChallengeStopsWithoutProof() {
    List<URI> calls = new ArrayList<>();
    DawnApi api =
        new DawnApi(
            (method, uri, body, auth) -> {
              calls.add(uri);
              return new DawnApi.Reply(200, "{\"unexpected\":true}");
            },
            BASE,
            JOIN);
    assertThrows(
        IOException.class,
        () -> api.start("server.aternos.me", ID, "Player", "secret", ignored -> {}, () -> false));
    assertEquals(1, calls.size());
  }

  @Test
  void permissionDenialAndRateLimitAreReportedWithoutRetrying() {
    for (int denied : new int[] {403, 429, 500}) {
      List<URI> calls = new ArrayList<>();
      DawnApi api =
          new DawnApi(
              (method, uri, body, auth) -> {
                calls.add(uri);
                return switch (calls.size()) {
                  case 1 -> new DawnApi.Reply(200, "{\"token\":\"challenge\"}");
                  case 2 -> new DawnApi.Reply(204, "");
                  case 3 -> new DawnApi.Reply(200, "{\"token\":\"dawn-jwt\"}");
                  default -> new DawnApi.Reply(denied, "SECRET_BODY");
                };
              },
              BASE,
              JOIN);
      IOException error =
          assertThrows(
              IOException.class,
              () ->
                  api.start(
                      "server.aternos.me", ID, "Player", "secret", ignored -> {}, () -> false));
      assertFalse(error.getMessage().contains("SECRET_BODY"));
      assertEquals(4, calls.size());
    }
  }

  @Test
  void guardResetsEvenWhenConnectionFails() {
    assertFalse(ConnectGuard.bypassed());
    assertThrows(
        IllegalStateException.class,
        () ->
            ConnectGuard.run(
                () -> {
                  assertTrue(ConnectGuard.bypassed());
                  throw new IllegalStateException("failed");
                }));
    assertFalse(ConnectGuard.bypassed());
  }
}

package fr.bagyette.aternauto.common;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import java.nio.charset.StandardCharsets;
import java.util.List;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicInteger;
import org.junit.jupiter.api.Test;

class ReportPromptTest {
  private static IssueReport report() {
    return new IssueReport(
        "1.21.11",
        "Fabric",
        "0.19.5",
        List.of(new IssueReport.Mod("Other mod", "1.2.3")),
        "example.aternos.me",
        25566,
        FailureKind.NETWORK,
        0);
  }

  @Test
  void neverSendsBeforeConfirmationAndDoesNotResendAfterRepeatedClicks() throws Exception {
    AtomicInteger calls = new AtomicInteger();
    CountDownLatch delivered = new CountDownLatch(1);
    ReportPrompt prompt =
        new ReportPrompt(
            new Messages("en"),
            ReportPromptTest::report,
            body -> {
              calls.incrementAndGet();
              delivered.countDown();
            });
    assertFalse(prompt.opened());
    prompt.click();
    assertEquals(0, calls.get());
    prompt.click(); // A rapid second click before the consent text rendered does nothing.
    assertEquals(0, calls.get());
    prompt.lines(10000, String::length, 100);
    prompt.click();
    prompt.click();
    assertTrue(delivered.await(2, TimeUnit.SECONDS));
    prompt.click();
    assertEquals(1, calls.get());
  }

  @Test
  void smallScreensShowEveryConsentPageBeforeSending() {
    AtomicInteger calls = new AtomicInteger();
    ReportPrompt prompt =
        new ReportPrompt(
            new Messages("fr_ca"), ReportPromptTest::report, body -> calls.incrementAndGet());
    prompt.click();
    assertEquals(1, prompt.lines(100, String::length, 1).size());
    assertEquals("Suite des informations", prompt.label());
    prompt.click();
    assertEquals(0, calls.get());
    assertTrue(prompt.lines(100, String::length, 1).get(0).length() <= 100);
  }

  @Test
  void payloadHasOnlyTheAgreedFieldsIncludingServerPortAndModVersions() {
    JsonObject body =
        new JsonParser()
            .parse(new String(report().payload(), StandardCharsets.UTF_8))
            .getAsJsonObject();
    assertEquals(13, body.entrySet().size());
    assertEquals(ClientUserAgent.current(), body.get("userAgent").getAsString());
    assertTrue(body.get("consent").getAsBoolean());
    assertEquals("example.aternos.me", body.get("server").getAsString());
    assertEquals(25566, body.get("port").getAsInt());
    assertEquals(
        "1.2.3", body.getAsJsonArray("mods").get(0).getAsJsonObject().get("version").getAsString());
    for (String key : List.of("username", "uuid", "accessToken", "log", "path", "jars")) {
      assertFalse(body.has(key));
    }
  }

  @Test
  void expectedUserErrorsAndArbitraryKickMessagesAreNotReportable() {
    assertFalse(FailureKind.PERMISSION.reportable());
    assertFalse(FailureKind.SESSION.reportable());
    assertEquals(null, FailureKind.connection("Kicked Player123 from private.example"));
    assertEquals(FailureKind.CONNECTION_RESET, FailureKind.connection(RetryState.CONNECTION_RESET));
  }
}

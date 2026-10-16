package fr.bagyette.aternauto.common;

import static org.junit.jupiter.api.Assertions.assertEquals;

import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import java.nio.charset.StandardCharsets;
import org.junit.jupiter.api.Test;

class StartTelemetryTest {
  @Test
  void payloadContainsOnlyVersionAndMappedUnixSeconds() {
    String payload = new String(StartTelemetry.payload("2", 1234567890L), StandardCharsets.UTF_8);
    JsonObject json = new JsonParser().parse(payload).getAsJsonObject();
    assertEquals(2, json.entrySet().size());
    assertEquals("2", json.get("version").getAsString());
    assertEquals("TFKARPLSBM", json.get("k").getAsString());
  }
}

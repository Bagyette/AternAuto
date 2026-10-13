package fr.autoaternos;

import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import org.junit.jupiter.api.Test;

class MixinLayoutTest {
  @Test
  void screensAndHelpersAreOutsideMixinsReservedPackage() throws Exception {
    JsonObject config;
    try (InputStreamReader reader =
        new InputStreamReader(
            getClass().getResourceAsStream("/aternauto.mixins.json"), StandardCharsets.UTF_8)) {
      config = new JsonParser().parse(reader).getAsJsonObject();
    }
    String reserved = "package " + config.get("package").getAsString() + ".";
    Path versions = Path.of(System.getProperty("aternauto.workspace"), "versions");
    try (var sources = Files.walk(versions)) {
      for (Path source :
          sources
              .filter(path -> path.toString().endsWith(".java") && path.toString().contains("src"))
              .toList()) {
        String text = Files.readString(source);
        if (source.getFileName().toString().endsWith("Mixin.java")) {
          assertTrue(text.startsWith(reserved), source.toString());
        } else {
          assertFalse(text.startsWith(reserved), source.toString());
        }
      }
    }
  }
}

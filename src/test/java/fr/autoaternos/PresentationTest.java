package fr.autoaternos;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.util.UUID;
import org.junit.jupiter.api.Test;

class PresentationTest {
  @Test
  void handlesBothOldSessionUuidFormatsAndMissingProfiles() {
    UUID id = UUID.fromString("11111111-2222-3333-4444-555555555555");
    assertEquals(id, SessionIds.parse(id.toString()));
    assertEquals(id, SessionIds.parse("11111111222233334444555555555555"));
    assertNull(SessionIds.parse("offline"));
    assertNull(SessionIds.parse(null));
  }

  @Test
  void wrapsLongStatusMessagesWithoutLosingWords() {
    String text = "Démarrage refusé : permission manquante ou auto-start désactivé côté serveur.";
    var lines = RequestTask.wrap(text, 100, value -> value.length() * 6);
    assertTrue(lines.size() > 1);
    assertEquals(text, String.join(" ", lines));
  }
}

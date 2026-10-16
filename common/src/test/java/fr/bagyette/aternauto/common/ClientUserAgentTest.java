package fr.bagyette.aternauto.common;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Comparator;
import java.util.concurrent.atomic.AtomicInteger;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

class ClientUserAgentTest {
  private Path temporary;

  @BeforeEach
  void createInstance() throws Exception {
    Path workspace = Path.of(System.getProperty("aternauto.workspace"));
    temporary = Files.createTempDirectory(workspace.resolve(".tools"), "user-agent-test-");
  }

  @AfterEach
  void removeInstance() throws Exception {
    try (var paths = Files.walk(temporary)) {
      for (Path path : paths.sorted(Comparator.reverseOrder()).toList()) {
        Files.delete(path);
      }
    }
  }

  @Test
  void persistsOnlyANumberAndReusesItAcrossNewClientInstances() throws Exception {
    Path config = temporary.resolve("config/aternauto");
    AtomicInteger choices = new AtomicInteger();
    ClientUserAgent first =
        new ClientUserAgent(
            config,
            () -> {
              choices.incrementAndGet();
              return 30;
            });
    assertEquals("ServerWakeHelper/" + BuildVersion.VERSION, first.value());
    assertEquals(first.value(), first.value());
    assertEquals(1, choices.get());
    assertEquals("30\n", Files.readString(config.resolve("uatu")));
    ClientUserAgent afterRestart =
        new ClientUserAgent(
            config,
            () -> {
              throw new AssertionError("A persisted selection must not be randomized again");
            });
    assertEquals(first.value(), afterRestart.value());
  }

  @Test
  void repairsCorruptAndOutOfRangeValues() throws Exception {
    Path config = temporary.resolve("config/aternauto");
    Files.createDirectories(config);
    for (String invalid : new String[] {"invalid", "0", "31", "-1", "999999999999999999999999"}) {
      Files.writeString(config.resolve("uatu"), invalid, StandardCharsets.UTF_8);
      assertEquals("AA/" + BuildVersion.VERSION, new ClientUserAgent(config, () -> 2).value());
      assertEquals("2\n", Files.readString(config.resolve("uatu")));
    }
  }

  @Test
  void independentInstancesKeepTheirOwnChoiceAndWriteFailureDoesNotBreakConnections()
      throws Exception {
    ClientUserAgent first = new ClientUserAgent(temporary.resolve("one"), () -> 1);
    ClientUserAgent second = new ClientUserAgent(temporary.resolve("two"), () -> 4);
    assertEquals("AternAuto/" + BuildVersion.VERSION, first.value());
    assertEquals("AAuto/" + BuildVersion.VERSION, second.value());
    Path notADirectory = temporary.resolve("blocked");
    Files.writeString(notADirectory, "file");
    AtomicInteger choices = new AtomicInteger();
    ClientUserAgent blocked =
        new ClientUserAgent(
            notADirectory,
            () -> {
              choices.incrementAndGet();
              return 3;
            });
    assertEquals("AternA/" + BuildVersion.VERSION, blocked.value());
    assertEquals(blocked.value(), blocked.value());
    assertTrue(choices.get() >= 1);
  }
}

package fr.bagyette.aternauto.common;

import java.io.IOException;
import java.nio.channels.FileChannel;
import java.nio.channels.FileLock;
import java.nio.charset.StandardCharsets;
import java.nio.file.AtomicMoveNotSupportedException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardCopyOption;
import java.nio.file.StandardOpenOption;
import java.util.concurrent.ThreadLocalRandom;
import java.util.function.IntSupplier;

/** One random name per instance, persisted as a small integer without player identifiers. */
public final class ClientUserAgent {
  // Stored numbers are one-based. Append new names; do not reorder existing entries.
  private static final String[] NAMES = {
    "AternAuto",
    "AA",
    "AternA",
    "AAuto",
    "AternAutoClient",
    "AAClient",
    "AternAClient",
    "AAutoClient",
    "MinecraftStartupClient",
    "ServerStartupHelper",
    "MinecraftConnectionClient",
    "GameServerWakeClient",
    "AternAutoHelper",
    "AAHelper",
    "AternAHelper",
    "AAutoHelper",
    "AternAutoConnect",
    "AAConnect",
    "AternAConnect",
    "AAutoConnect",
    "AternAutoStartup",
    "AAStartup",
    "AternAStartup",
    "AAutoStartup",
    "MinecraftServerStarter",
    "MinecraftWakeClient",
    "ServerConnectionHelper",
    "GameServerStartupClient",
    "MinecraftJoinHelper",
    "ServerWakeHelper"
  };
  private static ClientUserAgent instance =
      new ClientUserAgent(null, ClientUserAgent::randomChoice);
  private final Path directory;
  private final IntSupplier choose;
  private int selection;

  ClientUserAgent(Path directory, IntSupplier choose) {
    this.directory = directory;
    this.choose = choose;
  }

  /** Called by the loader with this instance's actual config/aternauto directory. */
  public static synchronized void configure(Path directory) {
    instance =
        new ClientUserAgent(directory.toAbsolutePath().normalize(), ClientUserAgent::randomChoice);
  }

  static synchronized String current() {
    return instance.value();
  }

  synchronized String value() {
    if (selection == 0) {
      selection = loadSelection();
    }
    return NAMES[selection - 1] + "/" + BuildVersion.VERSION;
  }

  private int loadSelection() {
    if (directory != null) {
      Path file = directory.resolve("uatu");
      int existing = readSelection(file);
      if (existing != 0) {
        return existing;
      }
      try {
        Files.createDirectories(directory);
        try (FileChannel channel =
                FileChannel.open(
                    directory.resolve("user-agent.lock"),
                    StandardOpenOption.CREATE,
                    StandardOpenOption.WRITE);
            FileLock lock = channel.lock()) {
          int saved = readSelection(file);
          if (saved != 0) {
            return saved;
          }
          int selected = choose.getAsInt();
          Path temporary = Files.createTempFile(directory, "user-agent-", ".tmp");
          try {
            Files.write(
                temporary, (Integer.toString(selected) + "\n").getBytes(StandardCharsets.UTF_8));
            try {
              Files.move(
                  temporary,
                  file,
                  StandardCopyOption.ATOMIC_MOVE,
                  StandardCopyOption.REPLACE_EXISTING);
            } catch (AtomicMoveNotSupportedException ignored) {
              Files.move(temporary, file, StandardCopyOption.REPLACE_EXISTING);
            }
          } finally {
            Files.deleteIfExists(temporary);
          }
          return selected;
        }
      } catch (IOException
          | SecurityException
          | java.nio.channels.OverlappingFileLockException ignored) {
        // A read-only instance can still connect; keep one choice for this process.
      }
    }
    return choose.getAsInt();
  }

  private static int readSelection(Path file) {
    try {
      if (Files.isRegularFile(file) && Files.size(file) <= 16) {
        int saved =
            Integer.parseInt(new String(Files.readAllBytes(file), StandardCharsets.UTF_8).trim());
        return saved >= 1 && saved <= NAMES.length ? saved : 0;
      }
    } catch (IOException | SecurityException | NumberFormatException ignored) {
      // An absent or invalid value is replaced with a random selection.
    }
    return 0;
  }

  private static int randomChoice() {
    return ThreadLocalRandom.current().nextInt(1, NAMES.length + 1);
  }
}

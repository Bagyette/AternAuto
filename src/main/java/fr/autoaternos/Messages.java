package fr.autoaternos;

import java.io.IOException;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import java.util.Locale;
import java.util.Properties;

/** Translations selected by Minecraft's language, with regional and English fallbacks. */
public final class Messages {
  private final Properties english = load("en");
  private final Properties translated;

  public Messages(String languageCode) {
    translated = load(resolve(languageCode));
  }

  public String text(String key, Object... arguments) {
    String pattern = translated.getProperty(key, english.getProperty(key, key));
    return arguments.length == 0 ? pattern : String.format(Locale.ROOT, pattern, arguments);
  }

  private static String resolve(String languageCode) {
    String code =
        languageCode == null ? "" : languageCode.toLowerCase(Locale.ROOT).replace('-', '_');
    if (code.equals("pt_br") || code.startsWith("pt_br_")) {
      return "pt_br";
    }
    String language = code.split("_", 2)[0];
    switch (language) {
      case "fr":
      case "de":
      case "es":
      case "pt":
      case "ru":
      case "it":
        return language;
      default:
        return "en";
    }
  }

  private static Properties load(String language) {
    Properties result = new Properties();
    try (InputStream input =
        Messages.class.getResourceAsStream("/assets/aternauto/lang/" + language + ".properties")) {
      if (input != null) {
        result.load(new InputStreamReader(input, StandardCharsets.UTF_8));
      }
    } catch (IOException ignored) {
      // A missing or unreadable translation falls back to the English catalog.
    }
    return result;
  }
}

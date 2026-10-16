package fr.bagyette.aternauto.common;

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

  static String resolve(String languageCode) {
    String code =
        languageCode == null ? "" : languageCode.toLowerCase(Locale.ROOT).replace('-', '_');
    String[] parts = code.split("_");
    String language = parts.length == 0 ? "" : parts[0];
    if (language.equals("zh")) {
      // An explicit script takes precedence over a region (for example zh-Hans-HK).
      for (String part : parts) {
        if (part.equals("hant")) {
          return "zh_tw";
        }
        if (part.equals("hans")) {
          return "zh_cn";
        }
      }
      for (String part : parts) {
        if (part.equals("tw") || part.equals("hk") || part.equals("mo")) {
          return "zh_tw";
        }
      }
      return "zh_cn";
    }
    if (language.equals("pt")) {
      for (String part : parts) {
        if (part.equals("br")) {
          return "pt_br";
        }
      }
      return "pt";
    }
    if (language.equals("in")) {
      return "id";
    }
    switch (language) {
      case "fr":
      case "de":
      case "es":
      case "pt":
      case "ru":
      case "it":
      case "pl":
      case "tr":
      case "ja":
      case "nl":
      case "ko":
      case "uk":
      case "id":
      case "vi":
      case "hi":
      case "ar":
      case "cs":
      case "ro":
      case "sv":
      case "hu":
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

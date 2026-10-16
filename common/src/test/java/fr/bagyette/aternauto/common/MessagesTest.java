package fr.bagyette.aternauto.common;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.util.List;
import org.junit.jupiter.api.Test;

class MessagesTest {
  @Test
  void regionalVariantsKeepTheirLanguageRatherThanFallingBackToEnglish() {
    String[][] cases = {
      {"fr_ca", "fr"}, {"FR-FR", "fr"}, {"en_au", "en"}, {"en_gb", "en"},
      {"de_at", "de"}, {"es_mx", "es"}, {"pt_br", "pt_br"}, {"pt-Latn-BR", "pt_br"},
      {"pt_pt", "pt"}, {"pt_ao", "pt"}, {"ru_ru", "ru"}, {"it_ch", "it"},
      {"pl_pl", "pl"}, {"tr_tr", "tr"}, {"ja_jp", "ja"}, {"nl_be", "nl"},
      {"ko_kr", "ko"}, {"uk_ua", "uk"}, {"id_id", "id"}, {"in_id", "id"},
      {"vi_vn", "vi"}, {"hi_in", "hi"}, {"ar_sa", "ar"}, {"ar_eg", "ar"},
      {"cs_cz", "cs"}, {"ro_md", "ro"}, {"sv_fi", "sv"}, {"hu_hu", "hu"},
      {"unknown", "en"}, {"", "en"}, {null, "en"}
    };
    for (String[] entry : cases) {
      assertEquals(entry[1], Messages.resolve(entry[0]), String.valueOf(entry[0]));
    }
  }

  @Test
  void chineseScriptTakesPrecedenceAndTraditionalRegionsNeverBecomeSimplified() {
    for (String code : List.of("zh_tw", "zh_hk", "zh_mo", "zh-Hant", "zh-Hant-CN")) {
      assertEquals("zh_tw", Messages.resolve(code), code);
    }
    for (String code : List.of("zh", "zh_cn", "zh_sg", "zh-Hans", "zh-Hans-HK")) {
      assertEquals("zh_cn", Messages.resolve(code), code);
    }
  }

  @Test
  void allCatalogsLoadAndFormatTheRealReportNotice() {
    for (String language :
        List.of(
            "en", "fr", "de", "es", "pt_br", "pt", "ru", "it", "pl", "tr", "ja", "zh_cn", "nl",
            "ko", "uk", "zh_tw", "id", "vi", "hi", "ar", "cs", "ro", "sv", "hu")) {
      Messages messages = new Messages(language);
      String notice = messages.text("report.notice", "example.aternos.me", 25566, 42);
      assertTrue(notice.contains("example.aternos.me"), language);
      assertTrue(notice.contains("25566"), language);
      assertTrue(notice.contains("42"), language);
      assertTrue(notice.contains("User-Agent"), language);
      assertTrue(messages.text("error.http", 503).contains("503"), language);
      assertFalse(messages.text("button.cancel").equals("button.cancel"), language);
    }
    assertEquals("Hủy", new Messages("vi_vn").text("button.cancel"));
    assertEquals("إلغاء", new Messages("ar_sa").text("button.cancel"));
    assertEquals("取消", new Messages("zh_hk").text("button.cancel"));
  }
}

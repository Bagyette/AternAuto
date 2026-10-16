"""Validate real UTF-8 catalogs and formatting contracts without compiling the mod."""

from pathlib import Path
import re
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
from distributions_v2 import LANGUAGES, write_artifact

EXPECTED = {"en", "fr", "de", "es", "pt_br", "pt", "ru", "it",
            "pl", "tr", "ja", "zh_cn", "nl", "ko", "uk", "zh_tw",
            "id", "vi", "hi", "ar", "cs", "ro", "sv", "hu"}
DIRECTORY = ROOT / "common/src/main/resources/assets/aternauto/lang"


def catalog(path):
    result = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line or line.startswith("#"):
            continue
        key, value = line.split("=", 1)
        if key in result:
            raise ValueError("Duplicate key: " + key)
        if not value.strip() or "\ufffd" in value or "\\u" in value:
            raise ValueError("Empty or invalid translation: " + key)
        result[key] = value
    return result


class LanguageCatalogTest(unittest.TestCase):
    def test_all_24_catalogs_are_required_by_the_packager(self):
        self.assertEqual(24, len(LANGUAGES))
        self.assertEqual(EXPECTED, set(LANGUAGES))
        self.assertEqual(EXPECTED, {path.stem for path in DIRECTORY.glob("*.properties")})

    def test_every_catalog_has_all_keys_and_preserves_formatter_arguments(self):
        english = catalog(DIRECTORY / "en.properties")
        for language in LANGUAGES:
            translated = catalog(DIRECTORY / (language + ".properties"))
            self.assertEqual(set(english), set(translated), language)
            for key, value in translated.items():
                placeholders = sorted(re.findall(r"%(?:[0-9]+\$)?[sd]", value))
                self.assertEqual(sorted(re.findall(r"%(?:[0-9]+\$)?[sd]", english[key])),
                                 placeholders, language + ":" + key)
                self.assertNotIn("%", re.sub(r"%(?:[0-9]+\$)?[sd]", "", value), language + ":" + key)
            self.assertIn("User-Agent", translated["report.notice"], language)
            self.assertIn("Discord", translated["report.notice"], language)
            if language != "en":
                self.assertNotEqual(english["report.notice"], translated["report.notice"], language)

    def test_packaging_rejects_an_artifact_missing_a_new_language(self):
        entries = {f"assets/aternauto/lang/{language}.properties": b"test=value"
                   for language in LANGUAGES if language != "zh_tw"}
        with tempfile.TemporaryDirectory(dir=ROOT / ".tools") as temporary:
            with self.assertRaisesRegex(ValueError, "Missing language: zh_tw"):
                write_artifact(Path(temporary) / "fixture.zip", [{"loader": "forge"}],
                               entries, "2", b"license")


if __name__ == "__main__":
    unittest.main()

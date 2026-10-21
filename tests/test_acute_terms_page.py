from pathlib import Path
import shutil
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from apply_overlay import ACUTE_PRIVACY_URL, ACUTE_SOURCE_URL, OverlayError, patch_acute_terms_page

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = Path(__file__).parent / "fixtures/firefox-158.0/TermsOfServiceOnboardingPage.kt"


class AcuteTermsPageTests(unittest.TestCase):
    def transformed(self, source: str) -> str:
        with tempfile.TemporaryDirectory() as directory:
            page = Path(directory) / "TermsOfServiceOnboardingPage.kt"
            page.write_text(source, encoding="utf-8")
            patch_acute_terms_page(page)
            return page.read_text(encoding="utf-8")

    def body(self, text: str) -> str:
        return text[text.index("private fun BodyText("):text.index("private fun BodyLinkText(")]

    def test_mozilla_terms_and_diagnostic_lines_are_replaced(self):
        body = self.body(self.transformed(FIXTURE.read_text(encoding="utf-8")))
        for upstream in ("lineOneText", "lineTwoText", "lineThreeText", "onManagePrivacyPreferencesLinkClicked"):
            self.assertNotIn(upstream, body)
        self.assertIn(f'url = "{ACUTE_SOURCE_URL}"', body)
        self.assertIn(f'url = "{ACUTE_PRIVACY_URL}"', body)
        self.assertIn("R.string.acute_onboarding_source_line", body)
        self.assertIn("R.string.acute_onboarding_privacy_line", body)

    def test_rest_of_the_page_is_untouched(self):
        original = FIXTURE.read_text(encoding="utf-8")
        text = self.transformed(original)
        before = original[:original.index("private fun BodyText(")]
        after = original[original.index("\n@Composable\nprivate fun BodyLinkText("):]
        self.assertTrue(text.startswith(before))
        self.assertTrue(text.endswith(after))

    def test_fails_closed_when_upstream_page_changes(self):
        source = FIXTURE.read_text(encoding="utf-8").replace(
            "eventHandler.onManagePrivacyPreferencesLinkClicked()", "eventHandler.onSomethingElse()")
        with self.assertRaisesRegex(OverlayError, "Unexpected terms page body"):
            self.transformed(source)

    def test_copy_is_accurate_for_acute(self):
        strings = ET.parse(ROOT / "overlay/res/values/acute_onboarding_strings.xml").getroot()
        copy = {node.get("name"): node.text for node in strings}
        self.assertIn("%1$s", copy["acute_onboarding_source_line"])
        self.assertIn("%1$s", copy["acute_onboarding_privacy_line"])
        joined = " ".join(copy.values())
        self.assertNotIn("Firefox", joined)
        self.assertNotIn("Terms of Use", joined)
        self.assertNotIn("sends", joined)

    def test_links_point_at_documents_in_this_repository(self):
        for url in (ACUTE_SOURCE_URL, ACUTE_PRIVACY_URL):
            self.assertTrue(url.startswith("https://github.com/iiankehn/acute-web-android/blob/main/docs/"))
            self.assertTrue((ROOT / "docs" / url.rsplit("/", 1)[1]).is_file(), url)


if __name__ == "__main__":
    unittest.main()

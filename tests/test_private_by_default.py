from pathlib import Path
import re
import shutil
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from apply_overlay import (
    OverlayError,
    patch_private_by_default,
    patch_private_by_default_onboarding,
    patch_private_by_default_summary,
)

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = Path(__file__).parent / "fixtures/firefox-158.0"
ANDROID = "{http://schemas.android.com/apk/res/android}"
SETTINGS = '''    var shouldUseHttpsOnly by
        booleanPreference(
            appContext.getPreferenceKey(R.string.pref_key_https_only),
            default = false,
        )

    var shouldEnableGlobalPrivacyControl by
        booleanPreference(
            appContext.getPreferenceKey(R.string.pref_key_privacy_enable_global_privacy_control),
            false,
        )

    val useStandardTrackingProtection by
        booleanPreference(
            appContext.getPreferenceKey(R.string.pref_key_tracking_protection_standard_option),
            true,
        )

    val useStrictTrackingProtection by
        booleanPreference(
            appContext.getPreferenceKey(R.string.pref_key_tracking_protection_strict_default),
            false,
        )
'''
FRAGMENT = '''class OnboardingFragment {
    private val pagesToDisplay by lazy {
        allOnboardingPages
            .distinctBy { it.type }
            .toMutableStateList()
    }
}
'''


class PrivateByDefaultTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)

    def test_defaults_change_in_code_and_preference_screen(self):
        settings = self.root / "Settings.kt"
        settings.write_text(SETTINGS, encoding="utf-8")
        screen = self.root / "tracking_protection_preferences.xml"
        shutil.copy(FIXTURES / "tracking_protection_preferences.xml", screen)
        patch_private_by_default(settings, screen)
        text = settings.read_text(encoding="utf-8")
        self.assertIn("pref_key_https_only),\n            default = true,", text)
        self.assertIn("global_privacy_control),\n            true,", text)
        self.assertIn("standard_option),\n            false,", text)
        self.assertIn("strict_default),\n            true,", text)
        defaults = {node.get(ANDROID + "key"): node.get(ANDROID + "defaultValue")
                    for node in ET.parse(screen).getroot().iter()}
        self.assertEqual(defaults["@string/pref_key_tracking_protection_standard_option"], "false")
        self.assertEqual(defaults["@string/pref_key_tracking_protection_strict_default"], "true")
        self.assertEqual(defaults["@string/pref_key_privacy_enable_global_privacy_control"], "true")
        # The master switch stays on and the strict allow-list baseline stays enabled.
        self.assertEqual(defaults["@string/pref_key_tracking_protection"], "true")
        self.assertEqual(defaults["@string/pref_key_tracking_protection_strict_allow_list_baseline"], "true")

    def test_defaults_fail_closed_when_upstream_changes(self):
        settings = self.root / "Settings.kt"
        settings.write_text(SETTINGS.replace("default = false,", "default = true,", 1), encoding="utf-8")
        screen = self.root / "tracking_protection_preferences.xml"
        shutil.copy(FIXTURES / "tracking_protection_preferences.xml", screen)
        with self.assertRaisesRegex(OverlayError, "HTTPS-Only default"):
            patch_private_by_default(settings, screen)

    def test_privacy_settings_lead_with_the_summary(self):
        preferences = self.root / "preferences.xml"
        shutil.copy(FIXTURES / "preferences.xml", preferences)
        # apply() runs this after regrouping; the category header it anchors on is unchanged by it.
        patch_private_by_default_summary(preferences)
        root = ET.parse(preferences).getroot()
        privacy = next(c for c in root
                       if c.get(ANDROID + "key") == "@string/pref_key_privacy_security_category")
        first = list(privacy)[0]
        self.assertEqual(first.get(ANDROID + "key"), "acute_private_by_default")
        self.assertEqual(first.get(ANDROID + "selectable"), "false")

    def test_onboarding_adds_an_announcement_page_without_opt_out(self):
        onboarding = self.root / "onboarding"
        (onboarding / "view").mkdir(parents=True)
        for name in ("OnboardingPageUiData.kt", "OnboardingMapper.kt", "OnboardingScreen.kt"):
            shutil.copy(FIXTURES / name, onboarding / "view" / name)
        shutil.copy(FIXTURES / "OnboardingTelemetryRecorder.kt", onboarding / "OnboardingTelemetryRecorder.kt")
        (onboarding / "OnboardingFragment.kt").write_text(FRAGMENT, encoding="utf-8")
        patch_private_by_default_onboarding(onboarding)

        types = (onboarding / "view/OnboardingPageUiData.kt").read_text(encoding="utf-8")
        self.assertIn('PRIVATE_BY_DEFAULT(telemetryId = "private_by_default"),', types)
        # Every exhaustive when over page types handles the new page.
        for name in ("view/OnboardingMapper.kt", "view/OnboardingScreen.kt", "OnboardingTelemetryRecorder.kt"):
            text = (onboarding / name).read_text(encoding="utf-8")
            self.assertIn("OnboardingPageUiData.Type.PRIVATE_BY_DEFAULT", text, name)
        screen = (onboarding / "view/OnboardingScreen.kt").read_text(encoding="utf-8")
        self.assertIn("onPrivateByDefaultContinueClick = scrollToNextPageOrDismiss,", screen)
        self.assertEqual(screen.count("onPrivateByDefaultContinueClick"), 4)
        fragment = (onboarding / "OnboardingFragment.kt").read_text(encoding="utf-8")
        self.assertIn(".withPrivateByDefaultPage()\n            .toMutableStateList()", fragment)
        page = fragment[fragment.index("OnboardingPageUiData("):fragment.index("val index")]
        self.assertNotIn("secondaryButtonLabel", page)

    def test_copy_promises_only_what_the_defaults_do(self):
        strings = ET.parse(ROOT / "overlay/res/values/acute_privacy_strings.xml").getroot()
        copy = {node.get("name"): node.text for node in strings}
        for name in ("acute_private_by_default_onboarding_description", "acute_private_by_default_settings_summary"):
            self.assertIn("shield in the address bar", copy[name])
            self.assertNotRegex(copy[name], re.compile(r"\ball\b|complete|guarantee", re.IGNORECASE))
        for brand in ("Firefox", "Mozilla"):
            self.assertNotIn(brand, "".join(copy.values()))

    def test_whats_new_is_shown_once_and_only_after_updates(self):
        updater = (ROOT / "overlay/kotlin/GitHubUpdateProvider.kt").read_text(encoding="utf-8")
        self.assertIn("if (info.firstInstallTime == info.lastUpdateTime) return false", updater)
        seen = updater.index("prefs.edit().putString(KEY_WHATS_NEW_SEEN, WHATS_NEW_ID).apply()")
        self.assertLess(seen, updater.index("AlertDialog.Builder(activity)\n            .setTitle(\"Private by default\")"))
        # Dev never checks GitHub releases even though it now registers for the notice.
        self.assertIn('updatesEnabled = !app.packageName.endsWith(".dev")', updater)
        self.assertIn("if (!updatesEnabled) return\n        if (!checkInProgress", updater)


if __name__ == "__main__":
    unittest.main()

from pathlib import Path
import sys
import unittest
import xml.etree.ElementTree as ET

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from verify_apk_manifest import DENIED_COMPONENTS, verify
import test_overlay
from apply_overlay import apply


class CompiledManifestTests(unittest.TestCase):
    def test_disabled_reporting_does_not_require_an_upload_service(self):
        for channel in ("stable", "beta", "dev"):
            with self.subTest(channel=channel):
                temp, root = test_overlay.OverlayTests().make_checkout()
                self.addCleanup(temp.cleanup)
                apply(root, channel=channel)
                analytics = (root / "mobile/android/fenix/app/src/main/java/org/mozilla/fenix/components/Analytics.kt").read_text()
                self.assertIn("            enabled = false,", analytics)
                self.assertIn("services = emptyList(),", analytics)
                self.assertIn("telemetryServices = emptyList(),", analytics)
                crash = (root / "mobile/android/android-components/components/lib/crash/src/main/java/mozilla/components/lib/crash/CrashReporter.kt").read_text()
                self.assertIn("require(!enabled || services.isNotEmpty() || telemetryServices.isNotEmpty())", crash)
                self.assertIn('"No crash reporter services defined"', crash)

    def test_firefox_158_renamed_wordmark_is_branded(self):
        temp, root = test_overlay.OverlayTests().make_checkout()
        self.addCleanup(temp.cleanup)
        ui = root / "mobile/android/fenix/app/src/main/java/org/mozilla/fenix/home/ui"
        (ui / "Wordmark.kt").rename(ui / "WordmarkAndLogo.kt")
        apply(root, channel="dev")
        self.assertIn('text = "Acute"', (ui / "WordmarkAndLogo.kt").read_text())

    def test_clean_dump_preserves_non_attribution_providers(self):
        verify('E: manifest (line=1)\n  E: application (line=2)\n'
               '    E: provider (line=3)\n'
               '      A: android:name="com.google.firebase.provider.FirebaseInitProvider"')

    def test_dependency_attribution_components_are_rejected(self):
        for name in DENIED_COMPONENTS:
            with self.subTest(name=name), self.assertRaisesRegex(ValueError, "attribution"):
                verify(f'E: manifest (line=1)\n  E: application (line=2)\n    A: android:name="{name}"')

    def test_empty_wrong_and_truncated_dump_fail_closed(self):
        for text in ("", "package: name=example", "E: manifest (line=1)", "<manifest><application/></manifest>"):
            with self.subTest(text=text), self.assertRaises(ValueError):
                verify(text)

    def test_every_channel_removes_dependency_provider_at_merge_time(self):
        android = "{http://schemas.android.com/apk/res/android}"
        tools = "{http://schemas.android.com/tools}"
        for channel in ("stable", "beta", "dev"):
            with self.subTest(channel=channel):
                temp, root = test_overlay.OverlayTests().make_checkout()
                self.addCleanup(temp.cleanup)
                apply(root, channel=channel)
                app = ET.parse(root / "mobile/android/fenix/app/src/main/AndroidManifest.xml").getroot().find("application")
                providers = [p for p in app.findall("provider") if p.get(android + "name") == DENIED_COMPONENTS[0]]
                self.assertEqual(len(providers), 1)
                self.assertEqual(providers[0].get(tools + "node"), "remove")
                updater = next(p for p in app.findall("provider") if p.get(android + "name").endswith("GitHubUpdateProvider"))
                self.assertEqual(updater.get(android + "exported"), "false")

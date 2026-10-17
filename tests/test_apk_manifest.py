from pathlib import Path
import sys
import unittest
import xml.etree.ElementTree as ET

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from verify_apk_manifest import DENIED_COMPONENTS, verify
import test_overlay
from apply_overlay import apply


CLEAN_MANIFEST = '''E: manifest (line=1)
  A: package="com.acuteweb.browser.dev" (Raw: "com.acuteweb.browser.dev")
  E: application (line=2)
    A: android:allowBackup(0x01010280)=(type 0x12)0x0
    E: provider (line=3)
      A: android:name(0x01010003)="org.mozilla.fenix.acute.GitHubUpdateProvider"
      A: android:exported(0x01010010)=(type 0x12)0x0
      A: android:authorities(0x01010018)="com.acuteweb.browser.dev.acute-updates"
    E: provider (line=4)
      A: android:name(0x01010003)="com.google.firebase.provider.FirebaseInitProvider"
'''


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
        for package in ("com.acuteweb.browser", "com.acuteweb.browser.beta", "com.acuteweb.browser.dev", "com.acuteweb.browser.debug"):
            with self.subTest(package=package):
                verify(CLEAN_MANIFEST.replace("com.acuteweb.browser.dev", package))

    def test_clipboard_keeps_uri_grants_without_exporting_data(self):
        clipboard = '''    E: provider (line=5)
      A: android:name="org.mozilla.gecko.GeckoClipboardContentProvider"
      A: android:authorities="com.acuteweb.browser.dev.clipboard"
      A: android:exported(0x01010010)=(type 0x12)0x0
      A: android:grantUriPermissions(0x0101001b)=(type 0x12)0xffffffff
'''
        verify(CLEAN_MANIFEST + clipboard)
        for changed in (clipboard.replace('0x12)0x0', '0x12)0xffffffff'),
                        clipboard.replace('com.acuteweb.browser.dev.clipboard', 'com.acuteweb.browser.clipboard')):
            with self.assertRaisesRegex(ValueError, 'clipboard'):
                verify(CLEAN_MANIFEST + changed)

    def test_shared_uid_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'UID'):
            verify(CLEAN_MANIFEST.replace('  E: application', '  A: android:sharedUserId="shared"\n  E: application'))

    def test_backup_and_updater_boundaries_fail_closed(self):
        mutations = (
            ('android:allowBackup(0x01010280)=(type 0x12)0x0', 'android:allowBackup(0x01010280)=(type 0x12)0xffffffff'),
            ('    A: android:allowBackup(0x01010280)=(type 0x12)0x0\n', ''),
            ('android:exported(0x01010010)=(type 0x12)0x0', 'android:exported(0x01010010)=(type 0x12)0x1'),
            ('      A: android:exported(0x01010010)=(type 0x12)0x0\n', ''),
            ('com.acuteweb.browser.dev.acute-updates', 'com.acuteweb.browser.acute-updates'),
            ('GitHubUpdateProvider', 'MissingProvider'),
            ('    E: provider (line=4)', '      A: android:grantUriPermissions(0x0101001b)=(type 0x12)0xffffffff\n    E: provider (line=4)'),
            ('    E: provider (line=4)', '      E: grant-uri-permission (line=4)\n    E: provider (line=5)'),
            ('  E: application (line=2)', '  E: application (line=2)\n  E: application (line=2)'),
        )
        for old, new in mutations:
            with self.subTest(mutation=new), self.assertRaises(ValueError):
                verify(CLEAN_MANIFEST.replace(old, new))

    def test_child_metadata_cannot_supply_missing_application_policy(self):
        text = CLEAN_MANIFEST.replace('    A: android:allowBackup(0x01010280)=(type 0x12)0x0\n', '')
        text += '      E: meta-data (line=5)\n        A: android:allowBackup(0x01010280)=(type 0x12)0x0\n'
        with self.assertRaisesRegex(ValueError, 'backups'):
            verify(text)

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

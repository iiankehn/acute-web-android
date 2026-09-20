from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class ProjectTests(unittest.TestCase):
    def test_updater_uses_selected_public_repository(self):
        updater = (ROOT / "overlay/kotlin/GitHubUpdateProvider.kt").read_text()
        self.assertIn("iiankehn/acute-web-android/releases/latest", updater)
        self.assertIn("universal", updater)
        self.assertIn("requestUpdateCheck()", updater)
        self.assertIn('uri.host == "github.com"', updater)
        self.assertIn("KEY_REMIND_AFTER", updater)

    def test_core_branding_assets_are_packaged(self):
        self.assertTrue((ROOT / "overlay/res/drawable-nodpi/acute_brand_mark.png").is_file())
        foreground = (ROOT / "overlay/res/drawable/acute_launcher_foreground.xml").read_text()
        self.assertIn("@drawable/acute_brand_mark", foreground)
        overlay = (ROOT / "scripts/apply_overlay.py").read_text()
        self.assertIn('text = "Acute"', overlay)
        self.assertIn('text = "by CORE"', overlay)
        self.assertIn("#0072BC", overlay)

    def test_release_workflow_requires_signing_key(self):
        workflow = (ROOT / ".github/workflows/build-android.yml").read_text()
        self.assertIn("ACUTE_KEYSTORE_B64 is required for releases", workflow)
        self.assertIn("gh release create", workflow)

    def test_tablet_smoke_follows_every_build(self):
        workflow = (ROOT / ".github/workflows/build-android.yml").read_text()
        self.assertIn("tablet-smoke:", workflow)
        self.assertIn("profile: pixel_tablet", workflow)
        self.assertIn("android-emulator-runner@a421e43855164a8197daf9d8d40fe71c6996bb0d", workflow)
        self.assertIn("scripts/tablet_smoke.sh", workflow)
        self.assertIn("needs: [build, tablet-smoke]", workflow)
        self.assertIn("ACUTE_PACKAGE_NAME: ${{ needs.build.outputs.package }}", workflow)

    def test_tablet_profiles_cover_large_screens(self):
        script = (ROOT / "scripts/tablet_smoke.sh").read_text()
        for profile in ("compact-tablet", "standard-tablet", "large-tablet"):
            self.assertIn(profile, script)
        self.assertIn("KEYCODE_TAB", script)

    def test_no_play_store_dependency(self):
        readme = (ROOT / "README.md").read_text().lower()
        self.assertIn("sideloadable apk", readme)
        self.assertNotIn("play store listing", readme)


if __name__ == "__main__":
    unittest.main()

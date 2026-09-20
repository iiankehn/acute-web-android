from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class ProjectTests(unittest.TestCase):
    def test_updater_uses_selected_public_repository(self):
        updater = (ROOT / "overlay/kotlin/GitHubUpdateProvider.kt").read_text()
        self.assertIn("iiankehn/acute-web-android/releases/latest", updater)
        self.assertIn("universal", updater)

    def test_release_workflow_requires_signing_key(self):
        workflow = (ROOT / ".github/workflows/build-android.yml").read_text()
        self.assertIn("ACUTE_KEYSTORE_B64 is required for releases", workflow)
        self.assertIn("gh release create", workflow)

    def test_release_contains_arm64_firefox_engine(self):
        workflow = (ROOT / ".github/workflows/build-android.yml").read_text()
        self.assertIn("--target=aarch64-linux-android", workflow)
        self.assertIn("lib/arm64-v8a/libmozglue.so", workflow)
        self.assertIn("lib/arm64-v8a/libxul.so", workflow)
        self.assertIn("needs: [build, abi-check]", workflow)

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

from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]


class ProjectTests(unittest.TestCase):
    def test_updater_uses_selected_public_repository(self):
        updater = (ROOT / "overlay/kotlin/GitHubUpdateProvider.kt").read_text()
        self.assertIn("iiankehn/acute-web-android/releases/latest", updater)
        self.assertIn("arm64-v8a.apk", updater)
        self.assertIn("requestUpdateCheck()", updater)
        self.assertIn('uri.host == "github.com"', updater)
        self.assertIn("KEY_REMIND_AFTER", updater)
        self.assertIn("KEY_LAST_ATTEMPT", updater)
        self.assertIn("MAX_RESPONSE_BYTES", updater)
        self.assertIn("ActivityNotFoundException", updater)

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
        self.assertIn("Sign with isolated release credentials", workflow)
        self.assertIn("Build without release secrets", workflow)
        self.assertIn("persist-credentials: false", workflow)
        self.assertIn("refusing to replace published files", workflow)
        self.assertIn("gh release create", workflow)

    def test_release_verification_uses_available_android_tools(self):
        workflow = (ROOT / ".github/workflows/build-android.yml").read_text()
        self.assertIn('"$build_tools/aapt2" dump permissions', workflow)
        self.assertNotIn("apkanalyzer manifest permissions", workflow)
        self.assertIn("certificate_digest()", workflow)
        self.assertIn("certificate SHA-256 digest:", workflow)
        self.assertIn('test -n "$current_digest"', workflow)

    def test_release_contains_arm64_firefox_engine(self):
        workflow = (ROOT / ".github/workflows/build-android.yml").read_text()
        self.assertIn("--target=aarch64-linux-android", workflow)
        self.assertIn("lib/arm64-v8a/libmozglue.so", workflow)
        self.assertIn("lib/arm64-v8a/libxul.so", workflow)
        self.assertIn("Android 12 launch smoke test", workflow)
        self.assertIn("needs: [build, smoke-test]", workflow)

    def test_release_inputs_are_pinned_and_attested(self):
        workflow = (ROOT / ".github/workflows/build-android.yml").read_text()
        self.assertIn("4452e9a17a29f762c5af6326f45c000dcf3117bb", workflow)
        self.assertNotIn("uses: actions/checkout@v", workflow)
        self.assertNotIn("uses: actions/setup-java@v", workflow)
        self.assertIn("attest-build-provenance@96b4a1ef", workflow)
        self.assertIn("sha256sum", workflow)
        self.assertIn("0.4.0-beta.dev.${GITHUB_RUN_NUMBER}", workflow)
        self.assertIn("com.acuteweb.browser.beta", workflow)
        self.assertIn("--prerelease", workflow)

    def test_unneeded_upstream_permissions_are_removed(self):
        overlay = (ROOT / "scripts/apply_overlay.py").read_text()
        self.assertIn("com.adjust.preinstall.READ_PERMISSION", overlay)
        self.assertIn("android.permission.REQUEST_DELETE_PACKAGES", overlay)

    def test_tablet_profiles_cover_large_screens(self):
        script = (ROOT / "scripts/tablet_smoke.sh").read_text()
        for profile in ("compact-tablet", "standard-tablet", "large-tablet"):
            self.assertIn(profile, script)
        self.assertIn("KEYCODE_TAB", script)

    def test_no_play_store_dependency(self):
        readme = (ROOT / "README.md").read_text().lower()
        self.assertRegex(readme, r"sideloadable\s+apk")
        self.assertNotIn("play store listing", readme)


if __name__ == "__main__":
    unittest.main()

from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]


class ProjectTests(unittest.TestCase):
    def test_updater_uses_selected_public_repository(self):
        updater = (ROOT / "overlay/kotlin/GitHubUpdateProvider.kt").read_text()
        self.assertIn("iiankehn/acute-web-android/releases?per_page=20", updater)
        self.assertIn("arm64-v8a.apk", updater)
        self.assertIn('BuildConfig.BUILD_TYPE == "beta"', updater)
        self.assertIn("candidate.optBoolean(\"prerelease\") == IS_BETA", updater)
        self.assertIn("BETA_VERSION", updater)
        self.assertIn("requestUpdateCheck()", updater)
        self.assertIn('uri.host == "github.com"', updater)
        self.assertIn("KEY_REMIND_AFTER", updater)
        self.assertIn("KEY_LAST_ATTEMPT", updater)
        self.assertIn("MAX_RESPONSE_BYTES", updater)
        self.assertIn("ActivityNotFoundException", updater)

    def test_core_branding_assets_are_packaged(self):
        self.assertTrue((ROOT / "overlay/res/drawable-nodpi/acute_brand_mark.png").is_file())
        self.assertTrue((ROOT / "overlay/res/drawable-nodpi/acute_brand_monochrome.png").is_file())
        foreground = (ROOT / "overlay/res/drawable/acute_launcher_foreground.xml").read_text()
        self.assertIn("@drawable/acute_brand_mark", foreground)
        background = (ROOT / "overlay/res/drawable/acute_launcher_background.xml").read_text()
        self.assertIn("@android:color/transparent", background)
        themed = (ROOT / "overlay/res/mipmap-anydpi-v33/ic_launcher.xml").read_text()
        self.assertIn("<monochrome", themed)
        self.assertIn("@drawable/acute_launcher_monochrome", themed)
        legacy = (ROOT / "overlay/res/mipmap-anydpi/ic_launcher.xml").read_text()
        self.assertIn("@drawable/acute_brand_mark", legacy)
        self.assertNotIn("pathData", legacy)
        overlay = (ROOT / "scripts/apply_overlay.py").read_text()
        self.assertIn('text = "Acute"', overlay)
        self.assertIn('text = "by CORE"', overlay)
        self.assertIn("#0072BC", overlay)

    def test_midnight_pages_is_local_and_conservative(self):
        extension = ROOT / "overlay/assets/extensions/acute-midnight"
        manifest = (extension / "manifest.json").read_text()
        script = (extension / "midnight.js").read_text()
        popup = (extension / "popup.js").read_text()
        self.assertIn('"<all_urls>"', manifest)
        self.assertNotIn("http://", script)
        self.assertNotIn("https://", script)
        self.assertIn("inIncognitoContext", script)
        self.assertIn("application/pdf", script)
        self.assertIn("checkout", script)
        self.assertIn("color-scheme", script)
        for mode in ("off", "automatic", "always"):
            self.assertIn(mode, popup)
        self.assertIn("disabledHosts", popup)
        self.assertIn("textContent = host", popup)

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
        self.assertIn("0.5.0-rc.dev.${GITHUB_RUN_NUMBER}", workflow)
        self.assertIn("com.acuteweb.browser.beta", workflow)
        self.assertIn("--prerelease", workflow)

    def test_core_glass_dark_theme_tokens_are_packaged(self):
        tokens = (ROOT / "overlay/res/values/acute_core_glass.xml").read_text()
        theme = (ROOT / "scripts/apply_overlay.py").read_text()
        for color in (
            "acute_glass_canvas",
            "acute_glass_surface",
            "acute_glass_surface_selected",
            "acute_glass_outline",
            "acute_glass_blue",
        ):
            self.assertIn(f'name="{color}"', tokens)
        self.assertIn("#FF0072BC", tokens)
        self.assertIn('"fx_mobile_surface": "@color/acute_glass_surface"', theme)
        self.assertIn(
            '"fx_mobile_surface_container_selected": "@color/acute_glass_surface_selected"',
            theme,
        )
        self.assertIn('"fx_mobile_primary": "@color/acute_glass_blue_soft"', theme)

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

    def test_acute_privacy_notice_is_present(self):
        privacy = (ROOT / "docs/PRIVACY.md").read_text()
        self.assertIn("collecting telemetry", privacy)
        self.assertIn("Mozilla's open-source Gecko engine", privacy)


if __name__ == "__main__":
    unittest.main()

from pathlib import Path
import hashlib
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
        self.assertIn('uri.path == expectedPath', updater)
        self.assertIn('assetSize in 1..MAX_APK_BYTES', updater)
        self.assertIn('pageUri.path != expectedPagePath', updater)
        self.assertIn("KEY_REMIND_AFTER", updater)
        self.assertIn("KEY_LAST_ATTEMPT", updater)
        self.assertIn("MAX_RESPONSE_BYTES", updater)
        self.assertIn("ActivityNotFoundException", updater)
        incomplete_index = updater.index("val completeApkUrl = apkUrl ?: return")
        success_index = updater.index("prefs.edit().putLong(KEY_LAST_SUCCESS, now).apply()")
        self.assertLess(incomplete_index, success_index)
        self.assertIn("private const val RETRY_INTERVAL_MS = 15L * 60 * 1000", updater)

    def test_core_branding_assets_are_packaged(self):
        self.assertTrue((ROOT / "overlay/res/drawable-nodpi/acute_brand_mark.png").is_file())
        self.assertTrue((ROOT / "overlay/res/drawable-nodpi/acute_brand_monochrome.png").is_file())
        foreground = (ROOT / "overlay/res/drawable/acute_launcher_foreground.xml").read_text()
        self.assertIn("@drawable/acute_brand_mark", foreground)
        background = (ROOT / "overlay/res/drawable/acute_launcher_background.xml").read_text()
        self.assertIn("#071827", background)
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

    def test_clear_glass_branding_matches_canonical_android_assets(self):
        stable_hash = "832be7ecb30d8abc1bab6956ee572e80eb9ca5cfd59bf9dcfcd2536ae5b185af"
        beta_hash = "327505ed63137dd7f3eb015af6c31a9f1f71f51b1007a3e23d846db111032034"
        stable_assets = (
            ROOT / "overlay/res/drawable-nodpi/acute_brand_mark.png",
            ROOT / "docs/acute-mark.png",
        )
        for asset in stable_assets:
            self.assertEqual(hashlib.sha256(asset.read_bytes()).hexdigest(), stable_hash)
        beta_asset = ROOT / "overlay/beta-res/drawable-nodpi/acute_brand_mark_beta.png"
        self.assertEqual(hashlib.sha256(beta_asset.read_bytes()).hexdigest(), beta_hash)

    def test_android_branding_has_no_ios_dependency(self):
        tracked_text = (
            (ROOT / "README.md").read_text()
            + (ROOT / "scripts/apply_overlay.py").read_text()
            + (ROOT / ".github/workflows/build-android.yml").read_text()
            + (ROOT / "docs/index.html").read_text()
        ).lower()
        self.assertNotIn("acute-web-ios", tracked_text)
        self.assertNotIn("acutewebicon-clear.png", tracked_text)
        self.assertNotIn("acutewebbetaicon-clear.png", tracked_text)
        self.assertFalse((ROOT / ".github/workflows/sync-branding.yml").exists())

    def test_beta_launcher_badge_is_channel_specific(self):
        beta = ROOT / "overlay/beta-res"
        foreground = (beta / "drawable/acute_beta_launcher_foreground.xml").read_text()
        self.assertIn("@drawable/acute_brand_mark_beta", foreground)
        themed = (beta / "mipmap-anydpi-v33/ic_launcher.xml").read_text()
        self.assertIn("@drawable/acute_beta_launcher_foreground", themed)
        self.assertIn("@drawable/acute_beta_launcher_monochrome", themed)
        stable = (ROOT / "overlay/res/mipmap-anydpi-v33/ic_launcher.xml").read_text()
        self.assertNotIn("acute_beta", stable)

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
        validate = (ROOT / ".github/workflows/validate.yml").read_text()
        self.assertIn("Audit Acute source and release controls", workflow)
        self.assertIn("run: make audit", workflow)
        self.assertIn("needs: audit", workflow)
        self.assertIn("Sign with isolated release credentials", workflow)
        self.assertIn("Build without release secrets", workflow)
        self.assertIn("github.event_name == 'push'", workflow)
        self.assertNotIn("needs.smoke-test.result == 'success'", workflow)
        self.assertIn("ACUTE_BUILD_NUMBER: ${{ github.run_number }}", workflow)
        self.assertIn("persist-credentials: false", workflow)
        self.assertIn("refusing to replace published files", workflow)
        self.assertIn("gh release create", workflow)
        self.assertIn("Publish release links to GitHub Pages", workflow)
        self.assertIn("scripts/update_site_release.py", workflow)
        self.assertIn("git push origin HEAD:main", workflow)
        self.assertNotIn("branches: [main, beta]", validate)

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
        self.assertNotIn("x86_64-linux-android", workflow)
        self.assertNotIn("smoke-x86_64", workflow)
        self.assertIn("needs: build", workflow)

    def test_android_build_bounds_gradle_resources(self):
        workflow = (ROOT / ".github/workflows/build-android.yml").read_text()
        self.assertEqual(workflow.count("Bound Gradle memory and configure swap"), 1)
        self.assertEqual(workflow.count("--max-workers=2"), 1)
        self.assertEqual(workflow.count("--no-parallel"), 1)
        self.assertEqual(workflow.count("-Xmx4g -Xms1g"), 1)
        self.assertEqual(workflow.count("MaxMetaspaceSize=2g"), 1)

    def test_release_inputs_are_pinned_and_attested(self):
        workflow = (ROOT / ".github/workflows/build-android.yml").read_text()
        self.assertIn("4452e9a17a29f762c5af6326f45c000dcf3117bb", workflow)
        self.assertNotIn("uses: actions/checkout@v", workflow)
        self.assertNotIn("uses: actions/setup-java@v", workflow)
        self.assertIn("attest-build-provenance@4d101475", workflow)
        self.assertIn("sha256sum", workflow)
        self.assertIn("version=1.0.1-beta.1", workflow)
        self.assertIn("1.0.1-dev.${GITHUB_RUN_NUMBER}", workflow)
        self.assertIn("ACUTE_VERSION_NAME: ${{ steps.version.outputs.version }}", workflow)
        self.assertNotIn("0.2.1-smoke.", workflow)
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
        self.assertIn("#B81B1E23", tokens)
        self.assertIn("#739FCBE8", tokens)
        self.assertIn('"fx_mobile_surface": "@color/acute_glass_surface"', theme)
        self.assertIn(
            '"fx_mobile_surface_container_selected": "@color/acute_glass_surface_selected"',
            theme,
        )
        self.assertIn('"fx_mobile_primary": "@color/acute_glass_blue_soft"', theme)
        self.assertIn("patch_core_glass_toolbar", theme)
        self.assertIn("patch_core_glass_address_bar", theme)
        self.assertIn("patch_core_glass_compositor", theme)
        self.assertIn("Brush.verticalGradient", theme)
        self.assertIn("Color(0xC2383D46)", theme)
        self.assertIn("Color(0x997AC6EA)", theme)
        self.assertIn("val acuteGlassTopOverlayHeight = 0", theme)
        self.assertIn("engineViewParent.translationY = 0f", theme)
        self.assertIn("toolbar.collapse()", theme)
        self.assertIn("Config.generateFennecVersionCode(abi) + acuteBuildNumber", theme)

    def test_unneeded_upstream_permissions_are_removed(self):
        overlay = (ROOT / "scripts/apply_overlay.py").read_text()
        self.assertIn("com.adjust.preinstall.READ_PERMISSION", overlay)
        self.assertIn("com.google.android.gms.permission.AD_ID", overlay)
        self.assertIn("android.permission.QUERY_ALL_PACKAGES", overlay)
        self.assertIn("android.permission.REQUEST_DELETE_PACKAGES", overlay)
        self.assertIn("android.permission.REQUEST_INSTALL_PACKAGES", overlay)

    def test_updater_and_manifest_are_release_safe(self):
        updater = (ROOT / "overlay/kotlin/GitHubUpdateProvider.kt").read_text()
        overlay = (ROOT / "scripts/apply_overlay.py").read_text()
        self.assertNotIn("android.util.Log", updater)
        self.assertNotIn("Log.", updater)
        self.assertIn('android:authorities="${applicationId}.acute-updates"', overlay)
        self.assertIn('android:exported="false"', overlay)
        for unsafe in (
            'android:debuggable="true"',
            'android:testOnly="true"',
            'android:usesCleartextTraffic="true"',
        ):
            self.assertNotIn(unsafe, overlay)

    def test_tablet_profiles_cover_large_screens(self):
        script = (ROOT / "scripts/tablet_smoke.sh").read_text()
        for profile in ("compact-phone", "compact-tablet", "standard-tablet", "large-tablet"):
            self.assertIn(profile, script)
        self.assertIn("capture_diagnostics", script)
        self.assertIn("https://en.wikipedia.org/wiki/Web_browser", script)
        self.assertIn("android.intent.action.VIEW", script)
        self.assertNotIn("KEYCODE_TAB", script)

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

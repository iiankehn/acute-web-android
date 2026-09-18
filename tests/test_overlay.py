from pathlib import Path
import tempfile
import unittest
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from apply_overlay import apply, OverlayError  # noqa: E402


GRADLE = '''import com.android.build.api.variant.FilterConfiguration
android {
    defaultConfig {
        applicationId "org.mozilla"
    }
    def releaseTemplate = {
        signingConfig = signingConfigs.debug
    }
    buildTypes {
        debug {
            applicationIdSuffix ".fenix.debug"
        }
        beta releaseTemplate >> {
            applicationIdSuffix ".firefox_beta"
            manifestPlaceholders.putAll([
                    "sharedUserId": "org.mozilla.firefox.sharedID",
            ])
        }
        release releaseTemplate >> {
            applicationIdSuffix ".firefox"
            manifestPlaceholders.putAll([
                    "sharedUserId": "org.mozilla.firefox.sharedID",
            ])
        }
    }
    splits {
        abi {
            if (gradle.mozconfig.substs.MOZILLA_OFFICIAL || System.getenv("MOZ_BUILD_CONFIG_LINT") == "1") {
                universalApk true
            }
        }
    }
}
androidComponents {
    onVariants(selector().all()) { variant ->
        def buildType = variant.buildType
        if (buildType in ['nightly', 'beta', 'release', 'benchmark']) {
            variant.outputs.each { output ->
                output.versionName.set("test")
            }
        }
    }
}
android.defaultConfig.with {
    buildConfigField 'boolean', 'CRASH_REPORTING', 'true'
    buildConfigField 'boolean', 'TELEMETRY', 'true'
}
'''

MANIFEST = '''<manifest xmlns:android="http://schemas.android.com/apk/res/android">
    <application
        android:label="@string/app_name">
        <activity android:name=".HomeActivity" android:resizeableActivity="true" />
    </application>
</manifest>
'''

CHANNEL_MANIFEST = '''<manifest xmlns:android="http://schemas.android.com/apk/res/android"
    android:sharedUserId="${sharedUserId}">
</manifest>
'''

SETTINGS = '''package org.mozilla.fenix.utils
class Settings(private val appContext: Context) {
    var shouldUseExpandedToolbar by
        booleanPreference(
            key = appContext.getPreferenceKey(R.string.pref_key_toolbar_expanded),
            default = { FxNimbus.features.defaultExpandedToolbar.value().enabled },
            persistDefaultIfNotExists = true,
        )

    var isTabStripEnabled by
        booleanPreference(
            appContext.getPreferenceKey(R.string.pref_key_tab_strip_show),
            default =
                FxNimbus.features.tabStrip.value().enabled &&
                    (isTabStripEligible(appContext) || FxNimbus.features.tabStrip.value().allowOnAllDevices),
        )
}
'''

DESKTOP_MODE = '''class DefaultDesktopModeRepository(private val context: Context) {
    internal val defaultDesktopMode by lazy {
        context.isLargeScreenSize()
    }
}
'''


class OverlayTests(unittest.TestCase):
    def make_checkout(self):
        temp = tempfile.TemporaryDirectory()
        root = Path(temp.name)
        (root / "mach").write_text("#!/bin/sh\n")
        app = root / "mobile/android/fenix/app"
        (app / "src/main/res/values").mkdir(parents=True)
        (app / "src/main/java/org/mozilla/fenix/utils").mkdir(parents=True)
        (app / "src/main/java/org/mozilla/fenix/browser/desktopmode").mkdir(parents=True)
        (app / "src/release").mkdir(parents=True)
        (app / "src/beta").mkdir(parents=True)
        (app / "build.gradle").write_text(GRADLE)
        (app / "src/main/AndroidManifest.xml").write_text(MANIFEST)
        (app / "src/release/AndroidManifest.xml").write_text(CHANNEL_MANIFEST)
        (app / "src/beta/AndroidManifest.xml").write_text(CHANNEL_MANIFEST)
        (app / "src/main/java/org/mozilla/fenix/utils/Settings.kt").write_text(SETTINGS)
        (app / "src/main/java/org/mozilla/fenix/browser/desktopmode/DesktopModeRepository.kt").write_text(
            DESKTOP_MODE)
        (app / "src/main/res/values/static_strings.xml").write_text(
            '<resources><string name="app_name">Firefox Fenix</string></resources>')
        (app / "src/main/res/values/strings.xml").write_text(
            '<resources><string name="welcome">Welcome to Mozilla Firefox</string></resources>')
        return temp, root

    def test_applies_branding_privacy_updater_and_signing(self):
        temp, root = self.make_checkout()
        self.addCleanup(temp.cleanup)
        apply(root)
        app = root / "mobile/android/fenix/app"
        gradle = (app / "build.gradle").read_text()
        manifest = (app / "src/main/AndroidManifest.xml").read_text()
        strings = (app / "src/main/res/values/strings.xml").read_text()
        static_strings = (app / "src/main/res/values/static_strings.xml").read_text()
        self.assertIn('applicationId "com.acuteweb.browser"', gradle)
        self.assertNotIn("org.mozilla.firefox.sharedID", gradle)
        self.assertNotIn("sharedUserId", (app / "src/release/AndroidManifest.xml").read_text())
        self.assertNotIn("'TELEMETRY', 'true'", gradle)
        self.assertIn("ACUTE_KEYSTORE_PATH", gradle)
        self.assertIn("ACUTE_VERSION_NAME", gradle)
        self.assertIn("GitHubUpdateProvider", manifest)
        self.assertIn("android.hardware.touchscreen", manifest)
        tablet_settings = (app / "src/main/java/org/mozilla/fenix/utils/Settings.kt").read_text()
        self.assertIn("Acute Web: tablets always start with the top tab strip", tablet_settings)
        self.assertIn("appContext.isLargeScreenSize()", tablet_settings)
        self.assertIn("Welcome to Acute Web", strings)
        self.assertIn('name="app_name">Acute Web<', static_strings)
        self.assertTrue((app / "src/main/java/org/mozilla/fenix/acute/GitHubUpdateProvider.kt").is_file())
        self.assertTrue((root / ".acute-web-android-overlay").is_file())

    def test_refuses_second_application(self):
        temp, root = self.make_checkout()
        self.addCleanup(temp.cleanup)
        apply(root)
        with self.assertRaises(OverlayError):
            apply(root)

    def test_requires_firefox_checkout(self):
        with tempfile.TemporaryDirectory() as name:
            with self.assertRaises(OverlayError):
                apply(Path(name))


if __name__ == "__main__":
    unittest.main()

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
    <!-- Needed to get distribution information from partners.
    This is NOT required for the adjust plugin. -->
    <uses-permission android:name="com.adjust.preinstall.READ_PERMISSION"/>

    <!-- Needed to prompt the user directly for app uninstallation as part of an
    'uninstall survey' experiment. This is ONLY used to uninstall the Firefox application -->
    <uses-permission android:name="android.permission.REQUEST_DELETE_PACKAGES" tools:node="replace" />

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

WORDMARK = '''import androidx.compose.foundation.Image
import androidx.compose.foundation.layout.height
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.ColorFilter
import androidx.compose.ui.res.dimensionResource
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.unit.dp

@Composable
internal fun WordmarkText(color: Color?) {
    Image(
        modifier =
            Modifier.semantics {
                    testTagsAsResourceId = true
                    testTag = HOMEPAGE_WORDMARK_TEXT
                }
                .height(dimensionResource(R.dimen.wordmark_text_height)),
        painter = painterResource(getAttr(R.attr.fenixWordmarkText)),
        colorFilter = color?.let { ColorFilter.tint(it) },
        contentDescription = stringResource(R.string.app_name),
    )
}
'''

COLORS = '''<resources>
<color name="fx_mobile_primary">@color/novaViolet70</color>
<color name="fx_mobile_primary_container">@color/novaViolet20</color>
<color name="fx_mobile_tertiary">@color/novaViolet50</color>
<color name="fx_mobile_splashscreen_background">#FCF3EE</color>
<color name="fx_mobile_private_primary">@color/novaViolet20</color>
<color name="fx_mobile_private_primary_container">@color/novaViolet60</color>
<color name="fx_mobile_private_background">@color/novaVioletDesaturated90</color>
<color name="fx_mobile_private_surface">@color/novaVioletDesaturated90</color>
<color name="fx_mobile_private_surface_variant">@color/novaVioletDesaturated80</color>
</resources>'''

CUSTOMIZATION = '''<androidx.preference.PreferenceScreen>
    <androidx.preference.PreferenceCategory
        android:layout="@layout/preference_cat_style"
        android:title="@string/preferences_app_icon"
        android:key="@string/pref_key_customization_category_app_icon"
        app:allowDividerBelow="false"
        app:iconSpaceReserved="false">
        <org.mozilla.fenix.iconpicker.ui.AppIconPreference
            android:key="@string/pref_key_app_icon" />
    </androidx.preference.PreferenceCategory>

</androidx.preference.PreferenceScreen>'''


class OverlayTests(unittest.TestCase):
    def make_checkout(self):
        temp = tempfile.TemporaryDirectory()
        root = Path(temp.name)
        (root / "mach").write_text("#!/bin/sh\n")
        app = root / "mobile/android/fenix/app"
        (app / "src/main/res/values").mkdir(parents=True)
        (app / "src/main/java/org/mozilla/fenix/utils").mkdir(parents=True)
        (app / "src/main/java/org/mozilla/fenix/browser/desktopmode").mkdir(parents=True)
        (app / "src/main/java/org/mozilla/fenix/home/ui").mkdir(parents=True)
        (app / "src/main/res/xml").mkdir(parents=True)
        (app / "src/release").mkdir(parents=True)
        (app / "src/beta").mkdir(parents=True)
        (app / "build.gradle").write_text(GRADLE)
        (app / "src/main/AndroidManifest.xml").write_text(MANIFEST)
        (app / "src/release/AndroidManifest.xml").write_text(CHANNEL_MANIFEST)
        (app / "src/beta/AndroidManifest.xml").write_text(CHANNEL_MANIFEST)
        (app / "src/main/java/org/mozilla/fenix/utils/Settings.kt").write_text(SETTINGS)
        (app / "src/main/java/org/mozilla/fenix/browser/desktopmode/DesktopModeRepository.kt").write_text(
            DESKTOP_MODE)
        (app / "src/main/java/org/mozilla/fenix/home/ui/Wordmark.kt").write_text(WORDMARK)
        (app / "src/main/res/values/colors.xml").write_text(COLORS)
        (app / "src/main/res/xml/customization_preferences.xml").write_text(CUSTOMIZATION)
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
        self.assertNotIn("ACUTE_KEYSTORE_PATH", gradle)
        self.assertIn("ACUTE_VERSION_NAME", gradle)
        self.assertIn("GitHubUpdateProvider", manifest)
        self.assertIn("android.hardware.touchscreen", manifest)
        self.assertNotIn("com.adjust.preinstall.READ_PERMISSION", manifest)
        self.assertNotIn("android.permission.REQUEST_DELETE_PACKAGES", manifest)
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

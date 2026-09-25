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
    var crashReportChoice by
        stringPreference(
            appContext.getPreferenceKey(R.string.pref_key_crash_reporting_choice),
            default = CrashReportOption.Ask.toString(),
        )

    var isMarketingTelemetryEnabled by
        booleanPreference(
            appContext.getPreferenceKey(R.string.pref_key_marketing_telemetry),
            default = false,
        )

    var shouldUseDarkTheme by
        booleanPreference(
            appContext.getPreferenceKey(R.string.pref_key_dark_theme),
            default = false,
        )

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

ONBOARDING = '''class OnboardingFragment {
    private val pagesToDisplay by lazy {
        allOnboardingPages
            .filterNot {
                it.type == OnboardingPageUiData.Type.MARKETING_DATA &&
                    !requireComponents.settings.shouldShowMarketingOnboarding
            }
            .distinctBy { it.type }
            .toMutableStateList()
    }

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        addMarketingFeature.set(
            feature =
                MarketingPageAdditionSupport(
                    prefKey = requireContext().getString(R.string.pref_key_should_show_marketing_onboarding),
                    pagesToDisplay = pagesToDisplay,
                    marketingPage = marketingPage,
                    settings = requireComponents.settings,
                    lifecycleOwner = viewLifecycleOwner,
                ),
            owner = this,
            view = view,
        )
        super.onViewCreated(view, savedInstanceState)
    }
}
'''

PREFERENCES = '''<PreferenceScreen xmlns:android="http://schemas.android.com/apk/res/android"
    xmlns:app="http://schemas.android.com/apk/res-auto">
        <androidx.preference.Preference
            android:key="@string/pref_key_data_choices"
            app:iconSpaceReserved="false"
            android:title="@string/preferences_data_collection" />
</PreferenceScreen>
'''

SEARCH_PROVIDERS = '''import org.mozilla.fenix.settings.datachoices.DataChoicesSearchProvider

class SettingsSearchProviders {
    val providers = listOf(
        DataChoicesSearchProvider,
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

CORE = '''class Core {
    val store = BrowserStore().apply {
                // Install the "icons" WebExtension to automatically load icons for every visited website.
                icons.install(engine, this)
    }
}'''


class OverlayTests(unittest.TestCase):
    def make_checkout(self):
        temp = tempfile.TemporaryDirectory()
        root = Path(temp.name)
        (root / "mach").write_text("#!/bin/sh\n")
        app = root / "mobile/android/fenix/app"
        (app / "src/main/res/values").mkdir(parents=True)
        (app / "src/main/res/values-es").mkdir(parents=True)
        (app / "src/main/java/org/mozilla/fenix/utils").mkdir(parents=True)
        (app / "src/main/java/org/mozilla/fenix/browser/desktopmode").mkdir(parents=True)
        (app / "src/main/java/org/mozilla/fenix/onboarding").mkdir(parents=True)
        (app / "src/main/java/org/mozilla/fenix/components").mkdir(parents=True)
        (app / "src/main/java/org/mozilla/fenix/home/ui").mkdir(parents=True)
        (app / "src/main/res/xml").mkdir(parents=True)
        (app / "src/release").mkdir(parents=True)
        (app / "src/beta").mkdir(parents=True)
        (app / "src/release/res/values").mkdir(parents=True)
        (app / "src/beta/res/values").mkdir(parents=True)
        (app / "build.gradle").write_text(GRADLE)
        (app / "src/main/AndroidManifest.xml").write_text(MANIFEST)
        (app / "src/release/AndroidManifest.xml").write_text(CHANNEL_MANIFEST)
        (app / "src/beta/AndroidManifest.xml").write_text(CHANNEL_MANIFEST)
        (app / "src/main/java/org/mozilla/fenix/utils/Settings.kt").write_text(SETTINGS)
        (app / "src/main/java/org/mozilla/fenix/onboarding/OnboardingFragment.kt").write_text(
            ONBOARDING)
        (app / "src/main/java/org/mozilla/fenix/components/SettingsSearchProviders.kt").write_text(
            SEARCH_PROVIDERS)
        (app / "src/main/java/org/mozilla/fenix/components/Core.kt").write_text(CORE)
        (app / "src/main/java/org/mozilla/fenix/browser/desktopmode/DesktopModeRepository.kt").write_text(
            DESKTOP_MODE)
        (app / "src/main/java/org/mozilla/fenix/home/ui/Wordmark.kt").write_text(WORDMARK)
        (app / "src/main/res/values/colors.xml").write_text(COLORS)
        (app / "src/main/res/xml/customization_preferences.xml").write_text(CUSTOMIZATION)
        (app / "src/main/res/xml/preferences.xml").write_text(PREFERENCES)
        (app / "src/main/res/values/static_strings.xml").write_text(
            '<resources><string name="app_name">Firefox Fenix</string></resources>')
        (app / "src/release/res/values/static_strings.xml").write_text(
            '<resources><string name="app_name">Firefox</string></resources>')
        (app / "src/beta/res/values/static_strings.xml").write_text(
            '<resources><string name="app_name">Firefox Beta</string></resources>')
        (app / "src/main/res/values/strings.xml").write_text(
            '<resources>'
            '<string name="about_content">%1$s is produced by Mozilla.</string>'
            '<string name="welcome">Welcome to Mozilla Firefox</string>'
            '<string name="marketing">Tell a partner that you’re a Firefox user.</string>'
            '<string name="onboarding_term_of_service_line_one_link_text_2">Firefox Terms of Use</string>'
            '<string name="sync_connect_device_dialog">Sign in to Firefox on another device.</string>'
            '</resources>')
        (app / "src/main/res/values-es/strings.xml").write_text(
            '<resources><string name="welcome">Bienvenido a Firefox</string></resources>')
        return temp, root

    def test_midnight_pages_is_beta_only(self):
        temp, root = self.make_checkout()
        self.addCleanup(temp.cleanup)
        apply(root, channel="beta")
        app = root / "mobile/android/fenix/app"
        core = (app / "src/main/java/org/mozilla/fenix/components/Core.kt").read_text()
        self.assertIn("midnight-pages@acuteweb.core", core)
        self.assertTrue(
            (app / "src/main/assets/extensions/acute-midnight/manifest.json").is_file()
        )
        self.assertTrue(
            (app / "src/main/assets/extensions/acute-midnight/midnight.js").is_file()
        )
        self.assertTrue(
            (app / "src/main/assets/extensions/acute-midnight/popup.html").is_file()
        )

        stable_temp, stable_root = self.make_checkout()
        self.addCleanup(stable_temp.cleanup)
        apply(stable_root, channel="stable")
        stable_core = (
            stable_root / "mobile/android/fenix/app/src/main/java/org/mozilla/fenix/components/Core.kt"
        ).read_text()
        self.assertNotIn("midnight-pages@acuteweb.core", stable_core)

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
        self.assertIn('applicationIdSuffix ".beta"', gradle)
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
        self.assertIn("isMarketingTelemetryEnabled: Boolean", tablet_settings)
        self.assertIn("get() = false", tablet_settings)
        self.assertIn("crashReportChoice: String", tablet_settings)
        self.assertIn("CrashReportOption.Never", tablet_settings)
        self.assertIn("Acute Web starts in dark mode", tablet_settings)
        self.assertIn("pref_key_dark_theme),\n            default = true", tablet_settings)
        onboarding = (app / "src/main/java/org/mozilla/fenix/onboarding/OnboardingFragment.kt").read_text()
        self.assertIn("never displays Mozilla marketing", onboarding)
        self.assertNotIn("MarketingPageAdditionSupport(", onboarding)
        preferences = (app / "src/main/res/xml/preferences.xml").read_text()
        self.assertIn('android:key="acute_report_issue"', preferences)
        self.assertNotIn("pref_key_data_choices", preferences)
        providers = (app / "src/main/java/org/mozilla/fenix/components/SettingsSearchProviders.kt").read_text()
        self.assertNotIn("DataChoicesSearchProvider", providers)
        reporting_strings = (app / "src/main/res/values/acute_reporting_strings.xml").read_text()
        self.assertIn("issues/new/choose", reporting_strings)
        self.assertIn("Welcome to Acute Web", strings)
        self.assertIn("you’re an Acute Web user", strings)
        self.assertIn("developed by CORE using Mozilla’s open-source Gecko engine", strings)
        self.assertIn("Firefox Terms of Use", strings)
        self.assertIn("Sign in to Firefox on another device", strings)
        self.assertIn(
            "Bienvenido a Acute Web",
            (app / "src/main/res/values-es/strings.xml").read_text(),
        )
        self.assertIn('name="app_name">Acute Web<', static_strings)
        self.assertIn(
            'name="app_name">Acute Web<',
            (app / "src/release/res/values/static_strings.xml").read_text(),
        )
        self.assertIn(
            'name="app_name">Acute Web<',
            (app / "src/beta/res/values/static_strings.xml").read_text(),
        )
        self.assertTrue((app / "src/main/java/org/mozilla/fenix/acute/GitHubUpdateProvider.kt").is_file())
        self.assertTrue((root / ".acute-web-android-overlay").is_file())

    def test_beta_channel_has_separate_identity(self):
        temp, root = self.make_checkout()
        self.addCleanup(temp.cleanup)
        apply(root, channel="beta")
        app = root / "mobile/android/fenix/app"
        self.assertIn(
            'name="app_name">Acute Beta<',
            (app / "src/beta/res/values/static_strings.xml").read_text(),
        )
        self.assertIn(
            'name="app_name">Acute Web<',
            (app / "src/release/res/values/static_strings.xml").read_text(),
        )
        self.assertEqual(
            (root / ".acute-web-android-overlay").read_text(),
            "Acute Web Android overlay applied (beta)\n",
        )

    def test_rejects_unknown_channel(self):
        temp, root = self.make_checkout()
        self.addCleanup(temp.cleanup)
        with self.assertRaises(OverlayError):
            apply(root, channel="nightly")

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

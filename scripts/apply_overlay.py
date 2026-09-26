#!/usr/bin/env python3
"""Apply the Acute Web Android overlay to a Mozilla Firefox checkout."""

from __future__ import annotations

import argparse
import re
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MARKER = ".acute-web-android-overlay"


class OverlayError(RuntimeError):
    pass


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise OverlayError(f"Expected exactly one {label}; found {count}")
    return text.replace(old, new, 1)


UPSTREAM_DISCLOSURE_RESOURCE_PARTS = (
    "account",
    "fxa_",
    "privacy_notice",
    "sync_",
    "synced_tabs",
    "term_of_service",
    "tou_",
)


MIDNIGHT_COLOR_OVERRIDES = {
    "fx_mobile_primary": "@color/acute_glass_blue_soft",
    "fx_mobile_on_primary": "@color/acute_glass_canvas",
    "fx_mobile_primary_container": "@color/acute_glass_blue_container",
    "fx_mobile_on_primary_container": "@color/acute_glass_text",
    "fx_mobile_secondary": "@color/acute_glass_text_muted",
    "fx_mobile_on_secondary": "@color/acute_glass_canvas",
    "fx_mobile_secondary_container": "@color/acute_glass_surface_high",
    "fx_mobile_on_secondary_container": "@color/acute_glass_text",
    "fx_mobile_tertiary": "@color/acute_glass_blue_soft",
    "fx_mobile_on_tertiary": "@color/acute_glass_canvas",
    "fx_mobile_tertiary_container": "@color/acute_glass_blue_container",
    "fx_mobile_on_tertiary_container": "@color/acute_glass_text",
    "fx_mobile_background": "@color/acute_glass_canvas",
    "fx_mobile_on_background": "@color/acute_glass_text",
    "fx_mobile_surface": "@color/acute_glass_surface",
    "fx_mobile_on_surface": "@color/acute_glass_text",
    "fx_mobile_surface_variant": "@color/acute_glass_surface_high",
    "fx_mobile_on_surface_variant": "@color/acute_glass_text_muted",
    "fx_mobile_surface_bright": "@color/acute_glass_surface_high",
    "fx_mobile_surface_dim": "@color/acute_glass_canvas",
    "fx_mobile_surface_container": "@color/acute_glass_surface",
    "fx_mobile_surface_container_high": "@color/acute_glass_surface_high",
    "fx_mobile_surface_container_highest": "@color/acute_glass_surface_high",
    "fx_mobile_surface_container_low": "@color/acute_glass_surface_low",
    "fx_mobile_surface_container_lowest": "@color/acute_glass_canvas",
    "fx_mobile_surface_container_selected": "@color/acute_glass_surface_selected",
    "fx_mobile_outline": "@color/acute_glass_outline",
}


def patch_midnight_palette(path: Path) -> None:
    """Replace upstream night colors in place so Android sees one definition."""
    text = path.read_text(encoding="utf-8")
    for name, value in MIDNIGHT_COLOR_OVERRIDES.items():
        color = re.compile(
            rf'(<color\b[^>]*\bname="{re.escape(name)}"[^>]*>).*?(</color>)',
            flags=re.DOTALL,
        )
        text, count = color.subn(
            lambda match: f"{match.group(1)}{value}{match.group(2)}",
            text,
            count=1,
        )
        if count != 1:
            raise OverlayError(f"Could not locate night color {name} in {path}")
    path.write_text(text, encoding="utf-8")


def replace_product_branding(xml: str) -> str:
    """Rename the product while preserving truthful upstream disclosures."""
    string = re.compile(
        r'(<string\b[^>]*\bname="([^"]+)"[^>]*>)(.*?)(</string>)',
        flags=re.DOTALL,
    )

    def update(match: re.Match[str]) -> str:
        name = match.group(2)
        value = match.group(3)
        protected = any(part in name for part in UPSTREAM_DISCLOSURE_RESOURCE_PARTS)
        protected = protected or "client=firefox" in value.lower()
        if protected:
            return match.group(0)
        value = value.replace("Mozilla Firefox", "Acute Web")
        value = value.replace("Firefox", "Acute Web")
        value = value.replace("a Acute Web user", "an Acute Web user")
        return f"{match.group(1)}{value}{match.group(4)}"

    return string.sub(update, xml)


def patch_product_branding(fenix: Path) -> None:
    """Patch user-facing product names in every bundled locale."""
    resource_root = fenix / "app/src/main/res"
    for path in sorted(resource_root.glob("values*/strings.xml")):
        text = path.read_text(encoding="utf-8")
        path.write_text(replace_product_branding(text), encoding="utf-8")

    english = resource_root / "values/strings.xml"
    text = english.read_text(encoding="utf-8")
    about = re.compile(
        r'(<string\b[^>]*\bname="about_content"[^>]*>)(.*?)(</string>)',
        flags=re.DOTALL,
    )
    text, count = about.subn(
        r"\1%1$s is developed by CORE using Mozilla’s open-source Gecko engine.\3",
        text,
        count=1,
    )
    if count != 1:
        raise OverlayError("Could not locate the About product attribution")
    english.write_text(text, encoding="utf-8")


def patch_app_labels(fenix: Path, channel: str) -> None:
    """Give Stable and Beta distinct, user-visible launcher labels."""
    static_files = sorted((fenix / "app/src").glob("*/res/values*/static_strings.xml"))
    if not static_files:
        raise OverlayError("Could not locate any channel static_strings.xml files")

    app_name = re.compile(
        r'(<string\b[^>]*\bname="app_name"[^>]*>)(.*?)(</string>)',
        flags=re.DOTALL,
    )
    for path in static_files:
        text = path.read_text(encoding="utf-8")
        label = "Acute Beta" if channel == "beta" and "/beta/" in path.as_posix() else "Acute Web"
        updated, count = app_name.subn(rf"\1{label}\3", text, count=1)
        if count != 1:
            raise OverlayError(f"Could not locate app_name in {path}")
        path.write_text(updated, encoding="utf-8")


def patch_gradle(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    text = replace_once(text, 'applicationId "org.mozilla"',
                        'applicationId "com.acuteweb.browser"', "application ID")
    text = replace_once(text, 'applicationIdSuffix ".fenix.debug"',
                        'applicationIdSuffix ".debug"', "debug application suffix")
    text = replace_once(text, 'applicationIdSuffix ".firefox_beta"',
                        'applicationIdSuffix ".beta"', "beta application suffix")
    text = replace_once(text, 'applicationIdSuffix ".firefox"',
                        '// Acute Web uses the base application ID for releases.',
                        "release application suffix")

    # Acute must not share Firefox's Linux UID or data sandbox.
    text = re.sub(
        r'^\s*"sharedUserId": "org\.mozilla\.firefox\.sharedID",\n',
        "",
        text,
        flags=re.MULTILINE,
    )

    # Disable product telemetry/crash upload flags in every build type. The
    # exact declarations are intentionally checked so upstream changes surface.
    telemetry_patterns = [
        ('buildConfigField "boolean", "TELEMETRY", "true"',
         'buildConfigField "boolean", "TELEMETRY", "false"'),
        ("buildConfigField 'boolean', 'TELEMETRY', 'true'",
         "buildConfigField 'boolean', 'TELEMETRY', 'false'"),
    ]
    crash_patterns = [
        ('buildConfigField "boolean", "CRASH_REPORTING", "true"',
         'buildConfigField "boolean", "CRASH_REPORTING", "false"'),
        ("buildConfigField 'boolean', 'CRASH_REPORTING', 'true'",
         "buildConfigField 'boolean', 'CRASH_REPORTING', 'false'"),
    ]
    if not any(old in text for old, _ in telemetry_patterns) or not any(old in text for old, _ in crash_patterns):
        raise OverlayError("Could not locate Fenix telemetry build flags")
    for old, new in telemetry_patterns + crash_patterns:
        text = text.replace(old, new)

    # Produce one updater-friendly universal APK in addition to ABI APKs.
    universal_pattern = re.compile(
        r"(splits\s*\{\s*abi\s*\{.*?)(if\s*\([^\n]*MOZILLA_OFFICIAL[^\n]*\)\s*\{\s*)"
        r"(universalApk\s+true\s*\})",
        re.DOTALL,
    )
    match = universal_pattern.search(text)
    if match:
        text = text[:match.start()] + match.group(1) + "universalApk true\n" + text[match.end():]

    # Acute's Git tag is the app version seen by the updater. Keep Mozilla's
    # version-code generator because its values are monotonic and ABI-aware.
    version_gate = "        if (buildType in ['nightly', 'beta', 'release', 'benchmark']) {\n"
    version_override = """        def acuteVersion = System.getenv("ACUTE_VERSION_NAME")
        if (acuteVersion) {
            variant.outputs.each { output ->
                def abi = output.filters.find { it.filterType == FilterConfiguration.FilterType.ABI }?.identifier ?: "universal"
                output.versionName.set(acuteVersion)
                output.versionCode.set(Config.generateFennecVersionCode(abi))
            }
        } else if (buildType in ['nightly', 'beta', 'release', 'benchmark']) {
"""
    text = replace_once(text, version_gate, version_override, "versioning gate")

    path.write_text(text, encoding="utf-8")


def patch_dark_theme_default(path: Path) -> None:
    """Lock Acute's application chrome to Midnight mode."""
    text = path.read_text(encoding="utf-8")
    light = '''    var shouldUseLightTheme by
        booleanPreference(
            appContext.getPreferenceKey(R.string.pref_key_light_theme),
            default = false,
        )
'''
    light_locked = '''    // Acute 0.5 has one application theme: Midnight.
    var shouldUseLightTheme: Boolean
        get() = false
        set(value) = Unit
'''
    text = replace_once(text, light, light_locked, "light theme preference")

    dark = '''    var shouldUseDarkTheme by
        booleanPreference(
            appContext.getPreferenceKey(R.string.pref_key_dark_theme),
            default = false,
        )
'''
    dark_locked = '''    // Keep Android resources and Compose surfaces in Midnight mode.
    var shouldUseDarkTheme: Boolean
        get() = true
        set(value) = Unit
'''
    text = replace_once(text, dark, dark_locked, "dark theme preference")

    oled = '''    var shouldUseOledTheme by
        booleanPreference(
            appContext.getPreferenceKey(R.string.pref_key_oled_theme),
            default = false,
        )
'''
    oled_locked = '''    var shouldUseOledTheme: Boolean
        get() = false
        set(value) = Unit
'''
    text = replace_once(text, oled, oled_locked, "OLED theme preference")

    follow = '''    var shouldFollowDeviceTheme by
        booleanPreference(
            appContext.getPreferenceKey(R.string.pref_key_follow_device_theme),
            default = false,
        )
'''
    follow_locked = '''    var shouldFollowDeviceTheme: Boolean
        get() = false
        set(value) = Unit
'''
    text = replace_once(text, follow, follow_locked, "follow-device theme preference")

    auto = '''    val shouldUseAutoBatteryTheme by
        booleanPreference(
            appContext.getPreferenceKey(R.string.pref_key_auto_battery_theme),
            default = false,
        )
'''
    auto_locked = '''    val shouldUseAutoBatteryTheme: Boolean
        get() = false
'''
    text = replace_once(text, auto, auto_locked, "automatic battery theme preference")
    path.write_text(text, encoding="utf-8")


def patch_manifest(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    # Acute does not use Mozilla partner attribution or the Firefox uninstall
    # survey. Removing these inherited permissions reduces package visibility
    # and uninstall capabilities without affecting normal browsing or updates.
    adjust_permission = '''    <!-- Needed to get distribution information from partners.
    This is NOT required for the adjust plugin. -->
    <uses-permission android:name="com.adjust.preinstall.READ_PERMISSION"/>

'''
    delete_permission = '''    <!-- Needed to prompt the user directly for app uninstallation as part of an
    'uninstall survey' experiment. This is ONLY used to uninstall the Firefox application -->
    <uses-permission android:name="android.permission.REQUEST_DELETE_PACKAGES" tools:node="replace" />

'''
    text = replace_once(text, adjust_permission, "", "partner attribution permission")
    text = replace_once(text, delete_permission, "", "uninstall survey permission")
    chromeos_feature = """    <!-- Acute Web: support keyboard/mouse-first ChromeOS and tablet devices. -->
    <uses-feature
        android:name="android.hardware.touchscreen"
        android:required="false" />

"""
    text = replace_once(text, "    <application\n", chromeos_feature + "    <application\n",
                        "application opening tag")
    provider = """
        <!-- Acute Web: non-exported GitHub Releases update checker. -->
        <provider
            android:name="org.mozilla.fenix.acute.GitHubUpdateProvider"
            android:authorities="${applicationId}.acute-updates"
            android:exported="false"
            android:initOrder="100" />
"""
    text = replace_once(text, "    </application>", provider + "    </application>",
                        "application closing tag")
    path.write_text(text, encoding="utf-8")


def patch_tablet_defaults(path: Path) -> None:
    """Make Fenix's large-screen UI deterministic for Acute tablet installs."""
    text = path.read_text(encoding="utf-8")
    expanded_old = "            default = { FxNimbus.features.defaultExpandedToolbar.value().enabled },\n"
    expanded_new = """            // Acute Web: show the desktop-like expanded toolbar on physical tablets.
            default = {
                appContext.isLargeScreenSize() ||
                    FxNimbus.features.defaultExpandedToolbar.value().enabled
            },
"""
    text = replace_once(text, expanded_old, expanded_new, "expanded-toolbar default")

    tab_strip_old = """            default =
                FxNimbus.features.tabStrip.value().enabled &&
                    (isTabStripEligible(appContext) || FxNimbus.features.tabStrip.value().allowOnAllDevices),
"""
    tab_strip_new = """            // Acute Web: tablets always start with the top tab strip. The user can
            // still disable it, and upstream's foldable exclusion remains respected.
            default =
                isTabStripEligible(appContext) ||
                    (FxNimbus.features.tabStrip.value().enabled &&
                        FxNimbus.features.tabStrip.value().allowOnAllDevices),
"""
    text = replace_once(text, tab_strip_old, tab_strip_new, "tablet tab-strip default")
    path.write_text(text, encoding="utf-8")


def patch_marketing_policy(settings: Path, onboarding: Path) -> None:
    """Disable Mozilla marketing collection and remove its onboarding page."""
    settings_text = settings.read_text(encoding="utf-8")
    preference = '''    var isMarketingTelemetryEnabled by
        booleanPreference(
            appContext.getPreferenceKey(R.string.pref_key_marketing_telemetry),
            default = false,
        )
'''
    enforced = '''    // Acute Web does not collect or share marketing attribution data.
    var isMarketingTelemetryEnabled: Boolean
        get() = false
        set(value) = Unit
'''
    settings_text = replace_once(
        settings_text, preference, enforced, "marketing telemetry preference"
    )
    settings.write_text(settings_text, encoding="utf-8")

    onboarding_text = onboarding.read_text(encoding="utf-8")
    conditional_filter = '''            .filterNot {
                it.type == OnboardingPageUiData.Type.MARKETING_DATA &&
                    !requireComponents.settings.shouldShowMarketingOnboarding
            }
'''
    unconditional_filter = '''            // Acute Web never displays Mozilla marketing consent or promotion pages.
            .filterNot { it.type == OnboardingPageUiData.Type.MARKETING_DATA }
'''
    onboarding_text = replace_once(
        onboarding_text, conditional_filter, unconditional_filter, "marketing page filter"
    )
    feature_start = '''        addMarketingFeature.set(
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
'''
    onboarding_text = replace_once(
        onboarding_text, feature_start, "", "dynamic marketing page registration"
    )
    onboarding.write_text(onboarding_text, encoding="utf-8")


def patch_user_reporting(settings: Path, preferences: Path, search_providers: Path) -> None:
    """Remove upload controls and direct voluntary bug reports to GitHub."""
    settings_text = settings.read_text(encoding="utf-8")
    crash_choice = '''    var crashReportChoice by
        stringPreference(
            appContext.getPreferenceKey(R.string.pref_key_crash_reporting_choice),
            default = CrashReportOption.Ask.toString(),
        )
'''
    disabled_choice = '''    // Acute Web keeps crash details local; users can report issues on GitHub.
    var crashReportChoice: String
        get() = CrashReportOption.Never.toString()
        set(value) = Unit
'''
    settings_text = replace_once(
        settings_text, crash_choice, disabled_choice, "crash report upload preference"
    )
    settings.write_text(settings_text, encoding="utf-8")

    preference_text = preferences.read_text(encoding="utf-8")
    data_choices = '''        <androidx.preference.Preference
            android:key="@string/pref_key_data_choices"
            app:iconSpaceReserved="false"
            android:title="@string/preferences_data_collection" />
'''
    issue_link = '''        <androidx.preference.Preference
            android:key="acute_report_issue"
            app:iconSpaceReserved="false"
            android:title="@string/acute_report_issue_title"
            android:summary="@string/acute_report_issue_summary">
            <intent
                android:action="android.intent.action.VIEW"
                android:data="@string/acute_issues_url" />
        </androidx.preference.Preference>
'''
    preference_text = replace_once(
        preference_text, data_choices, issue_link, "data collection settings entry"
    )
    preferences.write_text(preference_text, encoding="utf-8")

    providers_text = search_providers.read_text(encoding="utf-8")
    providers_text = replace_once(
        providers_text,
        "import org.mozilla.fenix.settings.datachoices.DataChoicesSearchProvider\n",
        "",
        "data choices search import",
    )
    providers_text = replace_once(
        providers_text,
        "        DataChoicesSearchProvider,\n",
        "",
        "data choices search provider",
    )
    search_providers.write_text(providers_text, encoding="utf-8")


def patch_branding_ui(fenix: Path) -> None:
    """Apply Acute's CORE identity to prominent browser surfaces."""
    wordmark = fenix / "app/src/main/java/org/mozilla/fenix/home/ui/Wordmark.kt"
    text = wordmark.read_text(encoding="utf-8")
    text = replace_once(text, "import androidx.compose.foundation.layout.height\n",
                        "import androidx.compose.foundation.layout.Column\nimport androidx.compose.foundation.layout.height\n",
                        "wordmark Column import")
    text = replace_once(text, "import androidx.compose.material3.MaterialTheme\n" if "import androidx.compose.material3.MaterialTheme\n" in text else "import androidx.compose.runtime.Composable\n",
                        "import androidx.compose.material3.MaterialTheme\nimport androidx.compose.material3.Text\nimport androidx.compose.runtime.Composable\n",
                        "wordmark Material imports")
    text = replace_once(text, "import androidx.compose.ui.unit.dp\n",
                        "import androidx.compose.ui.text.font.FontWeight\nimport androidx.compose.ui.unit.dp\nimport androidx.compose.ui.unit.sp\n",
                        "wordmark typography imports")
    for unused_import in (
        "import androidx.compose.ui.graphics.ColorFilter\n",
        "import androidx.compose.ui.res.dimensionResource\n",
        "import androidx.compose.ui.res.stringResource\n",
    ):
        text = replace_once(text, unused_import, "", f"unused wordmark import {unused_import.strip()}")
    old_wordmark = '''    Image(
        modifier =
            Modifier.semantics {
                    testTagsAsResourceId = true
                    testTag = HOMEPAGE_WORDMARK_TEXT
                }
                .height(dimensionResource(R.dimen.wordmark_text_height)),
        painter = painterResource(getAttr(R.attr.fenixWordmarkText)),
        colorFilter = color?.let { ColorFilter.tint(it) },
        contentDescription = stringResource(R.string.app_name),
    )'''
    new_wordmark = '''    Column(
        modifier = Modifier.semantics {
            testTagsAsResourceId = true
            testTag = HOMEPAGE_WORDMARK_TEXT
        },
    ) {
        Text(
            text = "Acute",
            color = color ?: MaterialTheme.colorScheme.onSurface,
            fontSize = 24.sp,
            fontWeight = FontWeight.Bold,
            lineHeight = 24.sp,
        )
        Text(
            text = "by CORE",
            color = Color(0xFF0072BC),
            fontSize = 10.sp,
            fontWeight = FontWeight.SemiBold,
            lineHeight = 10.sp,
        )
    }'''
    text = replace_once(text, old_wordmark, new_wordmark, "home wordmark")
    wordmark.write_text(text, encoding="utf-8")

    colors = fenix / "app/src/main/res/values/colors.xml"
    color_text = colors.read_text(encoding="utf-8")
    replacements = {
        '<color name="fx_mobile_primary">@color/novaViolet70</color>':
            '<color name="fx_mobile_primary">#0072BC</color>',
        '<color name="fx_mobile_primary_container">@color/novaViolet20</color>':
            '<color name="fx_mobile_primary_container">#D8EEFC</color>',
        '<color name="fx_mobile_tertiary">@color/novaViolet50</color>':
            '<color name="fx_mobile_tertiary">#0072BC</color>',
        '<color name="fx_mobile_splashscreen_background">#FCF3EE</color>':
            '<color name="fx_mobile_splashscreen_background">#F4F9FC</color>',
        '<color name="fx_mobile_private_primary">@color/novaViolet20</color>':
            '<color name="fx_mobile_private_primary">#44C7F4</color>',
        '<color name="fx_mobile_private_primary_container">@color/novaViolet60</color>':
            '<color name="fx_mobile_private_primary_container">#005A94</color>',
        '<color name="fx_mobile_private_background">@color/novaVioletDesaturated90</color>':
            '<color name="fx_mobile_private_background">#071827</color>',
        '<color name="fx_mobile_private_surface">@color/novaVioletDesaturated90</color>':
            '<color name="fx_mobile_private_surface">#071827</color>',
        '<color name="fx_mobile_private_surface_variant">@color/novaVioletDesaturated80</color>':
            '<color name="fx_mobile_private_surface_variant">#0D2A40</color>',
    }
    for old, new in replacements.items():
        color_text = replace_once(color_text, old, new, f"brand color {old}")
    colors.write_text(color_text, encoding="utf-8")

    # Replace every prominent Firefox logo reference with Acute's own mark.
    # The About-page disclosure remains truthful text; trademarks are not
    # needed to satisfy the source license.
    styles = fenix / "app/src/main/res/values/styles.xml"
    style_text = styles.read_text(encoding="utf-8")
    for old in (
        "@drawable/ic_logo_wordmark_normal",
        "@drawable/ic_logo_wordmark_private",
        "@drawable/ic_wordmark_logo",
    ):
        if old not in style_text:
            raise OverlayError(f"Could not locate inherited branding asset {old}")
        style_text = style_text.replace(old, "@drawable/acute_brand_mark")
    style_text = style_text.replace(
        '<item name="accent">@color/accent_normal_theme</item>',
        '<item name="accent">@color/fx_mobile_primary</item>',
    )
    style_text = style_text.replace(
        '<item name="accentBright">@color/photonViolet70</item>',
        '<item name="accentBright">@color/fx_mobile_primary</item>',
    )
    styles.write_text(style_text, encoding="utf-8")

    preferences = fenix / "app/src/main/res/xml/customization_preferences.xml"
    pref_text = preferences.read_text(encoding="utf-8")
    theme_category = '''    <androidx.preference.PreferenceCategory
        android:layout="@layout/preference_cat_style"
        android:title="@string/preferences_theme"
        app:iconSpaceReserved="false">
        <org.mozilla.fenix.settings.RadioButtonPreference
            android:defaultValue="@bool/underAPI28"
            android:key="@string/pref_key_light_theme"
            android:title="@string/preference_light_theme" />

        <org.mozilla.fenix.settings.RadioButtonPreference
            android:defaultValue="false"
            android:key="@string/pref_key_dark_theme"
            android:title="@string/preference_dark_theme" />

        <org.mozilla.fenix.settings.RadioButtonPreference
            android:defaultValue="false"
            android:key="@string/pref_key_oled_theme"
            android:title="@string/preference_oled_theme"
            android:visible="false" />

        <org.mozilla.fenix.settings.RadioButtonPreference
            android:defaultValue="false"
            android:key="@string/pref_key_auto_battery_theme"
            android:title="@string/preference_auto_battery_theme"
            app:isPreferenceVisible="@bool/underAPI28" />

        <org.mozilla.fenix.settings.RadioButtonPreference
            android:defaultValue="@bool/API28"
            android:key="@string/pref_key_follow_device_theme"
            android:title="@string/preference_follow_device_theme"
            app:isPreferenceVisible="@bool/API28" />
    </androidx.preference.PreferenceCategory>

'''
    pref_text = replace_once(pref_text, theme_category, "", "application theme settings")
    icon_picker = '''    <androidx.preference.PreferenceCategory
        android:layout="@layout/preference_cat_style"
        android:title="@string/preferences_app_icon"
        android:key="@string/pref_key_customization_category_app_icon"
        app:allowDividerBelow="false"
        app:iconSpaceReserved="false">
        <org.mozilla.fenix.iconpicker.ui.AppIconPreference
            android:key="@string/pref_key_app_icon" />
    </androidx.preference.PreferenceCategory>

'''
    pref_text = replace_once(pref_text, icon_picker, "", "alternate app icon picker")
    preferences.write_text(pref_text, encoding="utf-8")

    customization = fenix / "app/src/main/java/org/mozilla/fenix/settings/CustomizationFragment.kt"
    customization_text = customization.read_text(encoding="utf-8")
    theme_setup = '''        bindFollowDeviceTheme()
        bindDarkTheme()
        bindDarkestTheme()
        bindLightTheme()
        bindAutoBatteryTheme()
        setupRadioGroups()
'''
    customization_text = replace_once(
        customization_text,
        theme_setup,
        "        // Acute's browser UI is permanently rendered with the Midnight theme.\n",
        "customization theme bindings",
    )
    customization.write_text(customization_text, encoding="utf-8")


def patch_home_content_policy(settings: Path) -> None:
    """Remove inherited sponsored tiles and Mozilla editorial feeds."""
    text = settings.read_text(encoding="utf-8")
    stories = '''    @Suppress("DEPRECATION")
    var showPocketRecommendationsFeature by
        lazyFeatureFlagBooleanPreference(
            appContext.getPreferenceKey(R.string.pref_key_pocket_homescreen_recommendations),
            featureFlag = ContentRecommendationsFeatureHelper.isContentRecommendationsFeatureEnabled(appContext),
            defaultValue = { homescreenSections[HomeScreenSection.POCKET] == true },
        )
'''
    stories_off = '''    // Acute Web does not ship Mozilla's editorial or sponsored content feed.
    var showPocketRecommendationsFeature: Boolean
        get() = false
        set(value) = Unit
'''
    text = replace_once(text, stories, stories_off, "home stories preference")

    sponsored_tiles = '''    var showContileFeature by
        booleanPreference(
            key = appContext.getPreferenceKey(R.string.pref_key_enable_contile),
            default = true,
        )
'''
    sponsored_tiles_off = '''    // Acute Web does not request or display sponsored shortcut tiles.
    var showContileFeature: Boolean
        get() = false
        set(value) = Unit
'''
    text = replace_once(text, sponsored_tiles, sponsored_tiles_off, "sponsored shortcut preference")

    wallpaper_old = '''            default =
                if (enableHomepageEdgeToEdgeBackgroundFeature) {
                    Wallpaper.EdgeToEdge.name
                } else {
                    Wallpaper.Default.name
                },
'''
    wallpaper_new = '''            // Acute's black/grey interface is the default instead of Firefox artwork.
            default = Wallpaper.Default.name,
'''
    text = replace_once(text, wallpaper_old, wallpaper_new, "home wallpaper default")
    settings.write_text(text, encoding="utf-8")


def patch_about_page(path: Path) -> None:
    """Keep license disclosures while routing product links to Acute resources."""
    text = path.read_text(encoding="utf-8")
    old_list = '''        val context = requireContext()

        return listOf(
            AboutPageItem(
                AboutItem.ExternalLink(
                    WHATS_NEW,
                    SupportUtils.WHATS_NEW_URL,
                ),
                // Note: Fenix only has release notes for 'Release' versions, NOT 'Beta' & 'Nightly'.
                getString(R.string.about_whats_new, getString(R.string.firefox)),
            ),
            AboutPageItem(
                AboutItem.ExternalLink(
                    SUPPORT,
                    SupportUtils.getSumoURLForTopic(context, SupportUtils.SumoTopic.HELP),
                ),
                getString(R.string.about_support),
            ),
            AboutPageItem(
                AboutItem.Crashes,
                getString(R.string.about_crashes),
            ),
            AboutPageItem(
                AboutItem.ExternalLink(
                    PRIVACY_NOTICE,
                    SupportUtils.getMozillaPageUrl(SupportUtils.MozillaPage.PRIVACY_NOTICE),
                ),
                getString(R.string.about_privacy_notice),
            ),
            AboutPageItem(
                AboutItem.ExternalLink(
                    RIGHTS,
                    SupportUtils.getSumoURLForTopic(context, SupportUtils.SumoTopic.YOUR_RIGHTS),
                ),
                getString(R.string.about_know_your_rights),
            ),
'''
    new_list = '''        return listOf(
            AboutPageItem(
                AboutItem.ExternalLink(WHATS_NEW, ACUTE_RELEASES_URL),
                getString(R.string.about_whats_new, appName),
            ),
            AboutPageItem(
                AboutItem.ExternalLink(SUPPORT, ACUTE_ISSUES_URL),
                getString(R.string.about_support),
            ),
            AboutPageItem(
                AboutItem.ExternalLink(PRIVACY_NOTICE, ACUTE_PRIVACY_URL),
                getString(R.string.about_privacy_notice),
            ),
            AboutPageItem(
                AboutItem.ExternalLink(RIGHTS, ACUTE_LICENSE_URL),
                getString(R.string.about_know_your_rights),
            ),
'''
    text = replace_once(text, old_list, new_list, "About product links")
    old_event = '''                    WHATS_NEW -> {
                        WhatsNew.userViewedWhatsNew(requireContext())
                        Events.whatsNewTapped.record(Events.WhatsNewTappedExtra(source = "ABOUT"))
                    }
'''
    text = replace_once(text, old_event, "                    WHATS_NEW -> {}\n", "What's New telemetry")
    text = replace_once(
        text,
        '        private const val ABOUT_LICENSE_URL = "about:license"\n',
        '''        private const val ABOUT_LICENSE_URL = "about:license"
        private const val ACUTE_RELEASES_URL = "https://github.com/iiankehn/acute-web-android/releases"
        private const val ACUTE_ISSUES_URL = "https://github.com/iiankehn/acute-web-android/issues"
        private const val ACUTE_PRIVACY_URL =
            "https://github.com/iiankehn/acute-web-android/blob/main/docs/PRIVACY.md"
        private const val ACUTE_LICENSE_URL =
            "https://github.com/iiankehn/acute-web-android/blob/main/LICENSE"
''',
        "About Acute URLs",
    )
    path.write_text(text, encoding="utf-8")


def patch_midnight_pages(core: Path, channel: str) -> None:
    """Install Acute's local page-darkening engine in Beta builds only."""
    if channel != "beta":
        return
    text = core.read_text(encoding="utf-8")
    anchor = '''                // Install the "icons" WebExtension to automatically load icons for every visited website.
                icons.install(engine, this)
'''
    install = '''                // Acute Beta: install the local-only Midnight Pages renderer. It does not
                // contact a service or expose browsing data outside GeckoView.
                engine.installBuiltInWebExtension(
                    id = "midnight-pages@acuteweb.core",
                    url = "resource://android/assets/extensions/acute-midnight/",
                )

'''
    text = replace_once(text, anchor, anchor + install, "Midnight Pages extension hook")
    core.write_text(text, encoding="utf-8")


def validate_tablet_upstream(manifest: Path, desktop_mode: Path) -> None:
    """Fail fast if upstream removes the tablet behaviors Acute depends on."""
    manifest_text = manifest.read_text(encoding="utf-8")
    if 'android:name=".HomeActivity"' not in manifest_text or 'android:resizeableActivity="true"' not in manifest_text:
        raise OverlayError("Fenix HomeActivity is no longer explicitly resizable")
    desktop_text = desktop_mode.read_text(encoding="utf-8")
    if "context.isLargeScreenSize()" not in desktop_text:
        raise OverlayError("Fenix no longer defaults physical tablets to desktop browsing mode")


def patch_shared_uid_manifest(path: Path) -> None:
    """Remove Firefox's channel-specific shared UID from Acute variants."""
    text = path.read_text(encoding="utf-8")
    updated, count = re.subn(
        r'\s+android:sharedUserId="\$\{sharedUserId\}"', "", text, count=1
    )
    if count != 1:
        raise OverlayError(f"Could not locate sharedUserId in {path}")
    path.write_text(updated, encoding="utf-8")


def copy_overlay(fenix: Path) -> None:
    java_target = fenix / "app/src/main/java/org/mozilla/fenix/acute"
    java_target.mkdir(parents=True, exist_ok=True)
    shutil.copy2(ROOT / "overlay/kotlin/GitHubUpdateProvider.kt",
                 java_target / "GitHubUpdateProvider.kt")

    source_res = ROOT / "overlay/res"
    resource_targets = [fenix / "app/src/main/res"]
    for channel in ("debug", "nightly", "beta", "release"):
        channel_res = fenix / f"app/src/{channel}/res"
        if channel_res.is_dir():
            resource_targets.append(channel_res)
    for target_res in resource_targets:
        for source in source_res.rglob("*"):
            if source.is_file():
                relative = source.relative_to(source_res)
                destination = target_res / relative
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, destination)

    source_assets = ROOT / "overlay/assets"
    target_assets = fenix / "app/src/main/assets"
    if source_assets.is_dir():
        for source in source_assets.rglob("*"):
            if source.is_file():
                destination = target_assets / source.relative_to(source_assets)
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, destination)


def apply(checkout: Path, channel: str = "stable") -> None:
    if channel not in {"stable", "beta"}:
        raise OverlayError(f"Unsupported Acute channel: {channel}")
    checkout = checkout.resolve()
    if not (checkout / "mach").is_file():
        raise OverlayError(f"Not a Firefox checkout: {checkout}")
    fenix = checkout / "mobile/android/fenix"
    gradle = fenix / "app/build.gradle"
    manifest = fenix / "app/src/main/AndroidManifest.xml"
    release_manifest = fenix / "app/src/release/AndroidManifest.xml"
    beta_manifest = fenix / "app/src/beta/AndroidManifest.xml"
    settings = fenix / "app/src/main/java/org/mozilla/fenix/utils/Settings.kt"
    onboarding = fenix / "app/src/main/java/org/mozilla/fenix/onboarding/OnboardingFragment.kt"
    preferences = fenix / "app/src/main/res/xml/preferences.xml"
    search_providers = fenix / "app/src/main/java/org/mozilla/fenix/components/SettingsSearchProviders.kt"
    desktop_mode = fenix / "app/src/main/java/org/mozilla/fenix/browser/desktopmode/DesktopModeRepository.kt"
    core = fenix / "app/src/main/java/org/mozilla/fenix/components/Core.kt"
    about = fenix / "app/src/main/java/org/mozilla/fenix/settings/about/AboutFragment.kt"
    customization = fenix / "app/src/main/java/org/mozilla/fenix/settings/CustomizationFragment.kt"
    values = fenix / "app/src/main/res/values"
    night_colors = fenix / "app/src/main/res/values-night/colors.xml"
    required = [gradle, manifest, release_manifest, beta_manifest, settings, onboarding,
                preferences, search_providers, desktop_mode, core, about, customization,
                values / "static_strings.xml", values / "strings.xml", night_colors]
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        raise OverlayError("Missing expected Fenix files: " + ", ".join(missing))
    if (checkout / MARKER).exists():
        raise OverlayError("Overlay is already applied; start from a clean Firefox checkout")

    patch_gradle(gradle)
    validate_tablet_upstream(manifest, desktop_mode)
    patch_manifest(manifest)
    patch_tablet_defaults(settings)
    patch_dark_theme_default(settings)
    patch_midnight_palette(night_colors)
    patch_marketing_policy(settings, onboarding)
    patch_user_reporting(settings, preferences, search_providers)
    patch_branding_ui(fenix)
    patch_home_content_policy(settings)
    patch_about_page(about)
    patch_midnight_pages(core, channel)
    patch_shared_uid_manifest(release_manifest)
    patch_shared_uid_manifest(beta_manifest)
    patch_app_labels(fenix, channel)
    static_strings = values / "static_strings.xml"
    static_strings.write_text(
        replace_product_branding(static_strings.read_text(encoding="utf-8")), encoding="utf-8"
    )
    patch_product_branding(fenix)
    copy_overlay(fenix)
    (checkout / MARKER).write_text(
        f"Acute Web Android overlay applied ({channel})\n", encoding="utf-8"
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("firefox_checkout", type=Path)
    parser.add_argument(
        "--channel",
        choices=("stable", "beta"),
        default="stable",
        help="Acute release channel to configure (default: stable)",
    )
    args = parser.parse_args()
    try:
        apply(args.firefox_checkout, channel=args.channel)
    except OverlayError as error:
        parser.error(str(error))
    print(f"Applied Acute Web Android overlay to {args.firefox_checkout.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

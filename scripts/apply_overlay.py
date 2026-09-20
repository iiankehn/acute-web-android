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


def replace_text_nodes(xml: str) -> str:
    """Replace visible English branding without touching resource identifiers."""
    def update(match: re.Match[str]) -> str:
        text = match.group(1)
        text = text.replace("Mozilla Firefox", "Acute Web")
        text = text.replace("Firefox", "Acute Web")
        return f">{text}<"

    return re.sub(r">([^<]+)<", update, xml)


def patch_gradle(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    text = replace_once(text, 'applicationId "org.mozilla"',
                        'applicationId "com.acuteweb.browser"', "application ID")
    text = replace_once(text, 'applicationIdSuffix ".fenix.debug"',
                        'applicationIdSuffix ".debug"', "debug application suffix")
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

    build_types = "    buildTypes {\n"
    signing = """    signingConfigs {
        acuteRelease {
            def acuteKeystore = System.getenv("ACUTE_KEYSTORE_PATH")
            if (acuteKeystore) {
                storeFile file(acuteKeystore)
                storePassword System.getenv("ACUTE_KEYSTORE_PASSWORD")
                keyAlias System.getenv("ACUTE_KEY_ALIAS")
                keyPassword System.getenv("ACUTE_KEY_PASSWORD")
            }
        }
    }

    buildTypes {
"""
    if build_types not in text:
        raise OverlayError("Could not locate the Android buildTypes block")
    text = text.replace(build_types, signing, 1)

    release_open = "        release releaseTemplate >> {\n"
    release_signed = """        release releaseTemplate >> {
            if (System.getenv("ACUTE_KEYSTORE_PATH")) {
                signingConfig signingConfigs.acuteRelease
            }
"""
    text = replace_once(text, release_open, release_signed, "release build type")

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


def patch_manifest(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
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

    preferences = fenix / "app/src/main/res/xml/customization_preferences.xml"
    pref_text = preferences.read_text(encoding="utf-8")
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


def apply(checkout: Path) -> None:
    checkout = checkout.resolve()
    if not (checkout / "mach").is_file():
        raise OverlayError(f"Not a Firefox checkout: {checkout}")
    fenix = checkout / "mobile/android/fenix"
    gradle = fenix / "app/build.gradle"
    manifest = fenix / "app/src/main/AndroidManifest.xml"
    release_manifest = fenix / "app/src/release/AndroidManifest.xml"
    beta_manifest = fenix / "app/src/beta/AndroidManifest.xml"
    settings = fenix / "app/src/main/java/org/mozilla/fenix/utils/Settings.kt"
    desktop_mode = fenix / "app/src/main/java/org/mozilla/fenix/browser/desktopmode/DesktopModeRepository.kt"
    values = fenix / "app/src/main/res/values"
    required = [gradle, manifest, release_manifest, beta_manifest, settings, desktop_mode,
                values / "static_strings.xml", values / "strings.xml"]
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        raise OverlayError("Missing expected Fenix files: " + ", ".join(missing))
    if (checkout / MARKER).exists():
        raise OverlayError("Overlay is already applied; start from a clean Firefox checkout")

    patch_gradle(gradle)
    validate_tablet_upstream(manifest, desktop_mode)
    patch_manifest(manifest)
    patch_tablet_defaults(settings)
    patch_branding_ui(fenix)
    patch_shared_uid_manifest(release_manifest)
    patch_shared_uid_manifest(beta_manifest)
    static_strings = values / "static_strings.xml"
    static_text = static_strings.read_text(encoding="utf-8")
    static_text = static_text.replace(">Firefox Fenix<", ">Acute Web<")
    static_strings.write_text(replace_text_nodes(static_text), encoding="utf-8")
    for path in (values / "strings.xml",):
        path.write_text(replace_text_nodes(path.read_text(encoding="utf-8")), encoding="utf-8")
    copy_overlay(fenix)
    (checkout / MARKER).write_text("Acute Web Android overlay applied\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("firefox_checkout", type=Path)
    args = parser.parse_args()
    try:
        apply(args.firefox_checkout)
    except OverlayError as error:
        parser.error(str(error))
    print(f"Applied Acute Web Android overlay to {args.firefox_checkout.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

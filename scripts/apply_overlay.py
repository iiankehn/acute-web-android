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
    "pair_instructions",
    "sign_in_instructions",
)


MIDNIGHT_COLOR_OVERRIDES = {
    "fx_mobile_primary": "@color/acute_native_blue_soft",
    "fx_mobile_on_primary": "@color/acute_native_canvas",
    "fx_mobile_primary_container": "@color/acute_native_blue_container",
    "fx_mobile_on_primary_container": "@color/acute_native_text",
    "fx_mobile_secondary": "@color/acute_native_text_muted",
    "fx_mobile_on_secondary": "@color/acute_native_canvas",
    "fx_mobile_secondary_container": "@color/acute_native_surface_high",
    "fx_mobile_on_secondary_container": "@color/acute_native_text",
    "fx_mobile_tertiary": "@color/acute_native_blue_soft",
    "fx_mobile_on_tertiary": "@color/acute_native_canvas",
    "fx_mobile_tertiary_container": "@color/acute_native_blue_container",
    "fx_mobile_on_tertiary_container": "@color/acute_native_text",
    "fx_mobile_background": "@color/acute_native_canvas",
    "fx_mobile_on_background": "@color/acute_native_text",
    "fx_mobile_surface": "@color/acute_native_surface",
    "fx_mobile_on_surface": "@color/acute_native_text",
    "fx_mobile_surface_variant": "@color/acute_native_surface_high",
    "fx_mobile_on_surface_variant": "@color/acute_native_text_muted",
    "fx_mobile_surface_bright": "@color/acute_native_surface_high",
    "fx_mobile_surface_dim": "@color/acute_native_canvas",
    "fx_mobile_surface_container": "@color/acute_native_surface",
    "fx_mobile_surface_container_high": "@color/acute_native_surface_high",
    "fx_mobile_surface_container_highest": "@color/acute_native_surface_high",
    "fx_mobile_surface_container_low": "@color/acute_native_surface_low",
    "fx_mobile_surface_container_lowest": "@color/acute_native_canvas",
    "fx_mobile_surface_container_selected": "@color/acute_native_surface_selected",
    "fx_mobile_outline": "@color/acute_native_outline",
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


def patch_native_address_bar(display_path: Path, edit_path: Path) -> None:
    """Opaque Material capsules retain the upstream origin, security and editing behavior."""
    for path in (display_path, edit_path):
        text = path.read_text(encoding="utf-8")
        text = replace_once(text, "import androidx.compose.foundation.background\n",
                            "import androidx.compose.foundation.background\nimport androidx.compose.foundation.border\n",
                            "native address border import")
        anchor = "                                shape = CircleShape,\n                            )\n" if path == display_path else "                        .background(color = MaterialTheme.colorScheme.surfaceContainerHighest),\n"
        replacement = anchor + "                            .border(1.dp, MaterialTheme.colorScheme.outline, CircleShape)\n" if path == display_path else "                        .background(color = MaterialTheme.colorScheme.surfaceContainerHighest)\n                        .border(1.dp, MaterialTheme.colorScheme.outline, CircleShape),\n"
        text = replace_once(text, anchor, replacement, "opaque native address capsule")
        path.write_text(text, encoding="utf-8")


def patch_native_navigation(path: Path) -> None:
    """Keep navigation in the address row using maintained Fenix actions and history state."""
    text = path.read_text(encoding="utf-8")
    start = text.index("    private fun buildStartBrowserActions(): List<Action> {")
    end = text.index("    /**", start)
    text = text[:start] + """    private fun buildStartBrowserActions(): List<Action> {
        return listOf(
                ToolbarActionConfig(ToolbarAction.Back) { true },
                ToolbarActionConfig(ToolbarAction.Forward) { browserStore.state.selectedTab?.content?.canGoForward == true },
                ToolbarActionConfig(ToolbarAction.RefreshOrStop) { isWideScreen() },
            )
            .filter { config -> config.isVisible() }
            .map { config -> buildAction(config.action, Source.AddressBar.BrowserStart) }
    }

""" + text[end:]
    start = text.index("    private suspend fun buildEndBrowserActions(): List<Action> {")
    end = text.index("    /**", start)
    text = text[:start] + """    private suspend fun buildEndBrowserActions(): List<Action> {
        return listOf(ToolbarAction.TabCounter, ToolbarAction.Menu).map { action ->
            buildAction(toolbarAction = action, source = Source.AddressBar.BrowserEnd)
        }
    }

""" + text[end:]
    start = text.index("    private suspend fun buildNavigationActions(): List<Action> {")
    end = text.index("    private suspend fun updateNavigationActions", start)
    text = text[:start] + """    // Acute uses one navigation row; the inherited secondary navbar is not rendered.
    private suspend fun buildNavigationActions(): List<Action> = emptyList()

""" + text[end:]
    path.write_text(text, encoding="utf-8")


def patch_native_menu(path: Path) -> None:
    """Group existing commands without replacing their permission, storage or session handlers."""
    text = path.read_text(encoding="utf-8")
    text = replace_once(text, "import androidx.compose.material3.MaterialTheme\n",
                        "import androidx.compose.material3.MaterialTheme\nimport androidx.compose.material3.Text\n",
                        "native menu heading import")
    text = replace_once(text, "import androidx.compose.ui.semantics.semantics\n",
                        "import androidx.compose.ui.semantics.semantics\nimport androidx.compose.ui.semantics.heading\n",
                        "native menu accessibility heading import")
    start = text.index("    MenuFrame(", text.index("fun MainMenu("))
    end = text.index("\n@Composable\nprivate fun QuitMenuGroup", start)
    text = text[:start] + """    MenuFrame(
        contentModifier = Modifier.padding(horizontal = 8.dp, vertical = 8.dp),
        scrollState = scrollState,
        header = {},
        footer = {},
    ) {
        if (accessPoint != MenuAccessPoint.Home) {
            AcuteMenuHeading(R.string.acute_menu_navigation)
            MenuGroup {
                MenuNavigation(
                    isSiteLoading = isSiteLoading,
                    isExtensionsExpanded = isExtensionsExpanded,
                    isMoreMenuExpanded = isMoreMenuExpanded,
                    onBackButtonClick = onBackButtonClick,
                    onForwardButtonClick = onForwardButtonClick,
                    onRefreshButtonClick = onRefreshButtonClick,
                    onStopButtonClick = onStopButtonClick,
                    onShareButtonClick = onShareButtonClick,
                    goBackState = if (canGoBack) MenuItemState.ENABLED else MenuItemState.DISABLED,
                    goForwardState = if (canGoForward) MenuItemState.ENABLED else MenuItemState.DISABLED,
                )
            }
        }
        if (accessPoint == MenuAccessPoint.Browser) {
            AcuteMenuHeading(R.string.acute_menu_page)
            ToolsAndActionsMenuGroup(
                isBookmarked = isBookmarked,
                isDesktopMode = isDesktopMode,
                isPdf = isPdf,
                isExtensionsProcessDisabled = isExtensionsProcessDisabled,
                isExtensionsExpanded = isExtensionsExpanded,
                isMoreMenuHighlighted = isMoreMenuHighlighted,
                moreMenuExpanded = isMoreMenuExpanded,
                webExtensionMenuCount = webExtensionMenuCount,
                isAllWebExtensionsDisabled = isAllWebExtensionsDisabled,
                onExtensionsMenuClick = onExtensionsMenuClick,
                onBookmarkPageMenuClick = onBookmarkPageMenuClick,
                onEditBookmarkButtonClick = onEditBookmarkButtonClick,
                onSwitchToDesktopSiteMenuClick = onSwitchToDesktopSiteMenuClick,
                onFindInPageMenuClick = onFindInPageMenuClick,
                onMoreMenuClick = onMoreMenuClick,
                extensionsMenuItemDescription = extensionsMenuItemDescription,
                moreSettingsSubmenu = moreSettingsSubmenu,
                extensionSubmenu = extensionSubmenu,
            )
        }
        if (isReaderViewActive && accessPoint != MenuAccessPoint.Home) {
            MenuGroup {
                MenuItem(
                    label = stringResource(R.string.browser_menu_customize_reader_view_2),
                    beforeIconPainter = painterResource(iconsR.drawable.mozac_ic_tool_24),
                    onClick = onCustomizeReaderViewMenuClick,
                )
            }
        }
        AcuteMenuHeading(R.string.acute_menu_library)
        if (accessPoint == MenuAccessPoint.Browser) {
            MenuGroup {
                AcuteBookmarkMenuItem(
                    isBookmarked = isBookmarked,
                    onBookmarkPageMenuClick = onBookmarkPageMenuClick,
                    onEditBookmarkButtonClick = onEditBookmarkButtonClick,
                )
            }
        }
        LibraryMenuGroup(
            isDownloadHighlighted = isDownloadHighlighted,
            onBookmarksMenuClick = onBookmarksMenuClick,
            onHistoryMenuClick = onHistoryMenuClick,
            onDownloadsMenuClick = onDownloadsMenuClick,
            onPasswordsMenuClick = onPasswordsMenuClick,
        )
        if (showIPProtection) {
            AcuteMenuHeading(R.string.acute_menu_privacy)
            MenuGroup {
                IPProtectionMenuItem(
                    state = ipProtectionMenuState,
                    onToggle = onIPProtectionClick,
                    onNavigate = onIPProtectionNavigate,
                )
            }
        }
        if (accessPoint == MenuAccessPoint.Home || accessPoint == MenuAccessPoint.Browser) {
            AcuteMenuHeading(R.string.acute_menu_extensions)
            MenuGroup {
                ExtensionsMenuItem(
                    inCustomTab = false,
                    isExtensionsProcessDisabled = isExtensionsProcessDisabled,
                    isExtensionsExpanded = isExtensionsExpanded,
                    isAllWebExtensionsDisabled = isAllWebExtensionsDisabled,
                    webExtensionMenuCount = webExtensionMenuCount,
                    extensionsMenuItemDescription = extensionsMenuItemDescription,
                    onExtensionsMenuClick = onExtensionsMenuClick,
                    extensionSubmenu = extensionSubmenu,
                )
            }
        }
        AcuteMenuHeading(R.string.acute_menu_settings)
        MenuGroup {
            MozillaAccountMenuItem(account = account, accountState = accountState, onClick = onMozillaAccountButtonClick)
            if (accessPoint == MenuAccessPoint.Home) {
                MenuItem(
                    label = stringResource(R.string.browser_menu_customize_homepage),
                    beforeIconPainter = painterResource(iconsR.drawable.mozac_ic_home_24),
                    onClick = onCustomizeHomepageButtonClick,
                )
            }
            MenuItem(
                label = stringResource(R.string.browser_menu_settings),
                beforeIconPainter = painterResource(iconsR.drawable.mozac_ic_settings_24),
                onClick = onSettingsButtonClick,
            )
        }
        if (showQuitMenu) QuitMenuGroup(onQuitMenuClick = onQuitMenuClick)
    }
}

@Composable
private fun AcuteMenuHeading(label: Int) {
    Text(
        text = stringResource(label),
        style = MaterialTheme.typography.labelLarge,
        color = MaterialTheme.colorScheme.onSurfaceVariant,
        modifier = Modifier.padding(start = 12.dp, top = 12.dp, bottom = 8.dp).semantics { heading() },
    )
}
""" + text[end:]
    # Move the existing bookmark state/action block into Library without
    # replacing its maintained add/edit handlers or applying it to custom tabs.
    start = text.index("private fun ToolsAndActionsMenuGroup(")
    end = text.index("@Composable\nprivate fun MoreMenuButtonGroup", start)
    section = text[start:end]
    bookmark_start = section.index("        if (isBookmarked) {")
    bookmark_end = section.index("        MenuItem(\n            label = stringResource(id = R.string.browser_menu_find_in_page)", bookmark_start)
    bookmark_body = section[bookmark_start:bookmark_end]
    section = replace_once(section, bookmark_body, "", "bookmark action moves to Library")
    # Put extension access in its dedicated group, retaining the existing submenu implementation.
    match = """        ExtensionsMenuItem(
            inCustomTab = false,
            isExtensionsProcessDisabled = isExtensionsProcessDisabled,
            isExtensionsExpanded = isExtensionsExpanded,
            isAllWebExtensionsDisabled = isAllWebExtensionsDisabled,
            webExtensionMenuCount = webExtensionMenuCount,
            extensionsMenuItemDescription = extensionsMenuItemDescription,
            onExtensionsMenuClick = onExtensionsMenuClick,
            extensionSubmenu = extensionSubmenu,
        )

"""
    section = replace_once(section, match, "", "page-group extension duplication")
    text = text[:start] + section + text[end:]
    text += '''
@Composable
private fun AcuteBookmarkMenuItem(
    isBookmarked: Boolean,
    onBookmarkPageMenuClick: () -> Unit,
    onEditBookmarkButtonClick: () -> Unit,
) {
''' + bookmark_body + "}\n"
    for old, new in (
        ('''            iconRes = iconsR.drawable.mozac_ic_history_24,
            labelRes = R.string.library_history,
            shape = leftShape,
            index = 0,
            onClick = onHistoryMenuClick,''',
         '''            iconRes = iconsR.drawable.mozac_ic_bookmark_tray_fill_24,
            labelRes = R.string.library_bookmarks,
            shape = leftShape,
            index = 0,
            onClick = onBookmarksMenuClick,'''),
        ('''            iconRes = iconsR.drawable.mozac_ic_bookmark_tray_fill_24,
            labelRes = R.string.library_bookmarks,
            shape = middleShape,
            index = 1,
            onClick = onBookmarksMenuClick,''',
         '''            iconRes = iconsR.drawable.mozac_ic_history_24,
            labelRes = R.string.library_history,
            shape = middleShape,
            index = 1,
            onClick = onHistoryMenuClick,'''),
    ):
        text = replace_once(text, old, new, "consistent Library action order")
    path.write_text(text, encoding="utf-8")


def replace_product_branding(xml: str) -> str:
    """Rename the product while preserving truthful upstream disclosures."""
    acute_resource_values = {
        "preferences_rate": "Visit the Acute Web project",
        "preferences_show_sponsored_suggestions_summary": "Recommendations are disabled in Acute Web",
        "customize_toggle_contile": "Recommendations",
    }
    string = re.compile(
        r'(<string\b[^>]*\bname="([^"]+)"[^>]*>)(.*?)(</string>)',
        flags=re.DOTALL,
    )

    def update(match: re.Match[str]) -> str:
        name = match.group(2)
        value = match.group(3)
        if name in acute_resource_values:
            return f"{match.group(1)}{acute_resource_values[name]}{match.group(4)}"
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
    string_files = sorted(resource_root.glob("values*/strings.xml"))
    string_files += sorted(resource_root.glob("values*/static_strings.xml"))
    for path in string_files:
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


def validate_product_identity(fenix: Path) -> None:
    """Fail if obvious upstream consumer branding survives the Acute overlay."""
    resource_root = fenix / "app/src/main/res"
    prohibited = (
        "Rate on Google Play",
        "Try the Firefox search widget",
        "Add Firefox widget",
        "Find out why millions love Firefox",
        "Notifications help you stay safer with Firefox",
        "make Firefox your own",
        "Notifications for tabs received from other Firefox devices",
        "firefox.com/pair",
        "Firefox Suggest",
        "Firefox privacy notice",
        "millions love Firefox",
        "stay safer with Firefox",
        "Firefox search widget",
        "Add Firefox widget",
        "make Firefox your own",
        "Try Mozilla VPN",
        "Get Mozilla VPN",
        "Pocket recommendations",
        "Sponsored shortcuts",
        "Sponsored suggestions",
    )
    allowed_name_parts = UPSTREAM_DISCLOSURE_RESOURCE_PARTS + (
        "license",
        "mozilla",
        "gecko",
    )
    violations: list[str] = []
    string = re.compile(
        r'<string\b[^>]*\bname="([^"]+)"[^>]*>(.*?)</string>',
        flags=re.DOTALL,
    )
    string_files = sorted(resource_root.glob("values*/strings.xml"))
    string_files += sorted(resource_root.glob("values*/static_strings.xml"))
    for path in string_files:
        text = path.read_text(encoding="utf-8")
        for match in string.finditer(text):
            name, value = match.group(1), match.group(2)
            if any(part in name.lower() for part in allowed_name_parts):
                continue
            compact = re.sub(r"\s+", " ", value)
            for phrase in prohibited:
                if phrase.lower() in compact.lower():
                    violations.append(f"{path}: {name}: {phrase}")
    code_roots = (
        fenix / "app/src/main/java",
        fenix / "app/src/main/kotlin",
    )
    code_extensions = {".kt", ".java"}
    # Source code legitimately contains upstream feature identifiers and comments
    # even when those surfaces are disabled. Only inspect quoted literals here;
    # Android resources below remain subject to the stricter full-text scan.
    quoted_literal = re.compile(r'(?s)(?:"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\')')
    for root in code_roots:
        if not root.exists():
            continue
        for path in sorted(p for p in root.rglob("*") if p.suffix in code_extensions):
            source = path.read_text(encoding="utf-8")
            # Ignore KDoc/block/line comments: quoted product names in documentation
            # are not runtime UI. Resource-backed UI remains covered by the XML scan.
            source_without_comments = re.sub(r"/\*.*?\*/", "", source, flags=re.DOTALL)
            source_without_comments = re.sub(r"//[^\n]*", "", source_without_comments)
            literals = " ".join(
                match.group(0) for match in quoted_literal.finditer(source_without_comments)
            )
            compact = re.sub(r"\s+", " ", literals)
            for phrase in prohibited:
                if phrase.lower() in compact.lower():
                    violations.append(f"{path}: {phrase}")
    xml_roots = (
        resource_root / "xml",
        resource_root / "layout",
        resource_root / "menu",
        resource_root / "navigation",
    )
    for root in xml_roots:
        if not root.exists():
            continue
        for path in sorted(root.rglob("*.xml")):
            compact = re.sub(r"\s+", " ", path.read_text(encoding="utf-8"))
            for phrase in prohibited:
                if phrase.lower() in compact.lower():
                    violations.append(f"{path}: {phrase}")
    if violations:
        raise OverlayError(
            "Product-facing upstream branding survived the Acute overlay:\\n"
            + "\\n".join(violations)
        )


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
        label = "Acute Dev" if channel == "dev" else "Acute Beta" if channel == "beta" and "/beta/" in path.as_posix() else "Acute Web"
        updated, count = app_name.subn(rf"\1{label}\3", text, count=1)
        if count != 1:
            raise OverlayError(f"Could not locate app_name in {path}")
        path.write_text(updated, encoding="utf-8")


def patch_gradle(path: Path, channel: str = "stable") -> None:
    text = path.read_text(encoding="utf-8")
    text = replace_once(text, "\nandroid {\n", '''
// A single Gecko artifact build supplies only one complete native ABI.
// Partial ABIs from Maven dependencies must never influence Android's ABI selection.
def acuteTargetAbi = System.getenv("ACUTE_TARGET_ABI")
if (!(acuteTargetAbi in ["arm64-v8a", "x86_64"])) {
    throw new GradleException("Set ACUTE_TARGET_ABI to the ABI of the Gecko artifact build")
}
android {
    packaging.jniLibs.excludes += ["armeabi", "armeabi-v7a", "arm64-v8a", "x86", "x86_64", "mips", "mips64"]
        .findAll { it != acuteTargetAbi }.collect { "**/${it}/*.so" }
''', "single native architecture packaging")
    text = replace_once(text, 'applicationId "org.mozilla"',
                        'applicationId "com.acuteweb.browser"', "application ID")
    text = replace_once(text, 'applicationIdSuffix ".fenix.debug"',
                        'applicationIdSuffix ".debug"', "debug application suffix")
    text = replace_once(text, 'applicationIdSuffix ".firefox_beta"',
                        'applicationIdSuffix ".beta"', "beta application suffix")
    text = replace_once(text, 'applicationIdSuffix ".firefox"',
                        '// Acute Web uses the base application ID for releases.',
                        "release application suffix")

    if channel == "dev":
        text = replace_once(text, 'applicationId "com.acuteweb.browser"',
                            'applicationId "com.acuteweb.browser.dev"', "isolated Dev package")

    text = replace_once(text, "        minSdk config.minSdkVersion", "        minSdk 31", "Android 12 minimum SDK")

    # Artifact mozconfigs may enable debugging even for the release Gradle variant.
    # Acute's signed candidates must not inherit those development-only overrides.
    debug_override = """        if (gradle.hasProperty("localProperties.debuggable") ||
            gradle.mozconfig.substs.MOZ_ANDROID_DEBUGGABLE) {
            debuggable true
        }
"""
    text = replace_once(text, debug_override, "        debuggable false\n", "non-debuggable release template")

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
    text = replace_once(
        text, 'include "armeabi-v7a", "arm64-v8a", "x86_64"',
        'include acuteTargetAbi', "single native architecture splits",
    )
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
        def acuteBuildNumber = System.getenv("ACUTE_BUILD_NUMBER")?.toInteger() ?: 0
        if (acuteVersion) {
            variant.outputs.each { output ->
                def abi = output.filters.find { it.filterType == FilterConfiguration.FilterType.ABI }?.identifier ?: "universal"
                output.versionName.set(acuteVersion)
                output.versionCode.set(Config.generateFennecVersionCode(abi) + acuteBuildNumber)
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
    light_locked = '''    // Acute has one application theme: Midnight.
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


def patch_runtime_privacy(settings_path: Path, analytics_path: Path) -> None:
    """Disable upload consent even for profiles with old or overridden preferences."""
    text = settings_path.read_text(encoding="utf-8")
    for name in ("isTelemetryEnabled", "isDailyUsagePingEnabled", "isExperimentationEnabled", "isRolloutsEnabled"):
        pattern = re.compile(rf"    var {name} by\n        booleanPreference\(.*?\n        \)\n", re.DOTALL)
        replacement = f"    // Acute does not participate in telemetry or remote experiments.\n    var {name}: Boolean\n        get() = false\n        set(value) = Unit\n"
        text, count = pattern.subn(lambda _: replacement, text)
        if count != 1:
            raise OverlayError(f"Could not locate runtime privacy preference: {name}")
    settings_path.write_text(text, encoding="utf-8")

    text = analytics_path.read_text(encoding="utf-8")
    text = replace_once(text, "            services = services,", "            services = emptyList(),", "local-only crash services")
    start = text.index("            telemetryServices =")
    end = text.index("            shouldPrompt =", start)
    text = text[:start] + "            telemetryServices = emptyList(),\n" + text[end:]
    text = replace_once(text, "            enabled = true,", "            enabled = false,", "disabled crash reporting")
    text = replace_once(text, "private fun isSentryEnabled() = !BuildConfig.SENTRY_TOKEN.isNullOrEmpty()",
                        "private fun isSentryEnabled() = false", "disabled Sentry initialization")
    # Do not construct attribution/usage SDK services even though the controller is a no-op.
    start = text.index("            listOf(", text.index("MetricController.create("))
    end = text.index("            isDataTelemetryEnabled =", start)
    text = text[:start] + "            emptyList(),\n" + text[end:]
    analytics_path.write_text(text, encoding="utf-8")


def patch_disabled_crash_constructor(path: Path) -> None:
    """Permit an explicit disabled reporter without constructing an upload service."""
    text = path.read_text(encoding="utf-8")
    text = replace_once(
        text, "require(services.isNotEmpty() || telemetryServices.isNotEmpty())",
        "require(!enabled || services.isNotEmpty() || telemetryServices.isNotEmpty())",
        "disabled crash reporter constructor guard",
    )
    path.write_text(text, encoding="utf-8")


def patch_manifest(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    # Acute does not use Mozilla partner attribution, advertising identifiers,
    # package-wide discovery, Firefox's uninstall survey, or direct package
    # installation. Updates are downloaded in the user's browser and handed to
    # Android's normal installer, so REQUEST_INSTALL_PACKAGES is unnecessary.
    adjust_permission = '''    <!-- Needed to get distribution information from partners.
    This is NOT required for the adjust plugin. -->
    <uses-permission android:name="com.adjust.preinstall.READ_PERMISSION"/>

'''
    ad_id_permission = '''    <!-- Needed for Google Play policy https://support.google.com/googleplay/android-developer/answer/6048248 -->
    <uses-permission android:name="com.google.android.gms.permission.AD_ID"/>

'''
    query_all_packages_permission = '''    <!-- Needed to interact with all apps installed on a device -->
    <uses-permission android:name="android.permission.QUERY_ALL_PACKAGES"
        tools:ignore="QueryAllPackagesPermission" />

'''
    delete_permission = '''    <!-- Needed to prompt the user directly for app uninstallation as part of an
    'uninstall survey' experiment. This is ONLY used to uninstall the Firefox application -->
    <uses-permission android:name="android.permission.REQUEST_DELETE_PACKAGES" tools:node="replace" />

'''
    install_permission = '''    <uses-permission-sdk-23 android:name="android.permission.REQUEST_INSTALL_PACKAGES" />

'''
    # Attribution broadcasts are unnecessary when marketing telemetry is disabled.
    receiver = re.compile(r'        <receiver\s+android:name="com\.adjust\.sdk\.AdjustPreinstallReferrerReceiver".*?</receiver>\n', re.DOTALL)
    text, count = receiver.subn("", text)
    if count != 1:
        raise OverlayError("Could not locate the upstream attribution receiver")
    text = replace_once(text, adjust_permission, "", "partner attribution permission")
    text = text.replace(ad_id_permission, "")
    if "com.google.android.gms.permission.AD_ID" in text:
        raise OverlayError("Could not remove advertising ID permission")
    text = replace_once(text, query_all_packages_permission, "", "all-packages query permission")
    text = replace_once(text, delete_permission, "", "uninstall survey permission")
    text = replace_once(text, install_permission, "", "package installation permission")
    removed_permissions = (
        "com.adjust.preinstall.READ_PERMISSION",
        "com.google.android.gms.permission.AD_ID",
        "android.permission.QUERY_ALL_PACKAGES",
        "android.permission.REQUEST_DELETE_PACKAGES",
        "android.permission.REQUEST_INSTALL_PACKAGES",
    )
    for permission in removed_permissions:
        if permission in text:
            raise OverlayError(f"Could not remove inherited permission: {permission}")
    # Explicit merger removals also suppress declarations contributed by dependency AARs.
    removal_markers = "    <!-- Acute: block unwanted permissions from dependency manifests. -->\n"
    for permission in removed_permissions:
        for tag in ("uses-permission", "uses-permission-sdk-23"):
            removal_markers += f'    <{tag} android:name="{permission}" tools:node="remove" />\n'
    text = replace_once(text, "    <application\n", removal_markers + "\n    <application\n", "permission merger-removal markers")
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
    provider += '        <receiver android:name="com.adjust.sdk.AdjustPreinstallReferrerReceiver" tools:node="remove" />\n'
    # This dependency provider runs before Application.onCreate, independently
    # of the disabled MetricController service list. Acute does not use attribution.
    provider += '        <provider android:name="com.adjust.sdk.SystemLifecycleContentProvider" tools:node="remove" />\n'
    # Glean's dependency exports this diagnostic command activity even in release builds.
    provider += '        <activity android:name="mozilla.telemetry.glean.debug.GleanDebugActivity" tools:node="remove" />\n'
    text = replace_once(text, "    </application>", provider + "    </application>",
                        "application closing tag")
    path.write_text(text, encoding="utf-8")


def patch_tablet_defaults(path: Path) -> None:
    """Make Fenix's large-screen UI deterministic for Acute tablet installs."""
    text = path.read_text(encoding="utf-8")
    expanded_old = "            default = { FxNimbus.features.defaultExpandedToolbar.value().enabled },\n"
    expanded_block = """    var shouldUseExpandedToolbar by
        booleanPreference(
            key = appContext.getPreferenceKey(R.string.pref_key_toolbar_expanded),
            default = { FxNimbus.features.defaultExpandedToolbar.value().enabled },
            persistDefaultIfNotExists = true,
        )
"""
    text = replace_once(text, expanded_block, """    // Acute 2.0 uses a single native navigation row on every window size.
    var shouldUseExpandedToolbar: Boolean
        get() = false
        set(value) = Unit
""", "single-row toolbar policy")

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


def patch_desktop_shortcuts(path: Path) -> None:
    """Add laptop-class shortcuts through Fenix's existing browser use cases."""
    text = path.read_text(encoding="utf-8")
    text = replace_once(
        text,
        "import org.mozilla.fenix.ext.setNavigationIcon\n",
        "import org.mozilla.fenix.ext.setNavigationIcon\n"
        "import org.mozilla.fenix.utils.isLargeScreenSize\n",
        "desktop shortcut screen-size import",
    )

    # Firefox 158 already imports this generated class; older sources do not.
    directions_import = "import org.mozilla.fenix.browser.BrowserFragmentDirections\n"
    if directions_import not in text:
        text = replace_once(text, "import org.mozilla.fenix.ext.setNavigationIcon\n",
                            directions_import + "import org.mozilla.fenix.ext.setNavigationIcon\n",
                            "desktop shortcut navigation import")

    touch_anchor = '''    override fun dispatchTouchEvent(ev: MotionEvent?): Boolean {
'''
    shortcut_handler = '''    /** Handle conventional browser shortcuts on tablet and laptop-class layouts. */
    private fun handleAcuteDesktopShortcut(event: KeyEvent): Boolean {
        val primaryModifier = event.isCtrlPressed || event.isMetaPressed
        val state = components.core.store.state
        val selectedTab = state.selectedTab

        if (primaryModifier && !event.isAltPressed) {
            when (event.keyCode) {
                KeyEvent.KEYCODE_L -> {
                    selectedTab ?: return false
                    navHost.navController.navigate(
                        BrowserFragmentDirections.actionGlobalHome(
                            focusOnAddressBar = true,
                            sessionToStartSearchFor = selectedTab.id,
                        )
                    )
                    return true
                }

                KeyEvent.KEYCODE_T -> {
                    if (event.isShiftPressed) {
                        components.useCases.tabsUseCases.undo()
                    } else {
                        components.useCases.fenixBrowserUseCases.addNewHomepageTab(
                            private = browsingModeManager.mode.isPrivate,
                        )
                    }
                    openToBrowser(BrowserDirection.FromGlobal)
                    return true
                }

                KeyEvent.KEYCODE_W -> {
                    selectedTab ?: return false
                    components.useCases.tabsUseCases.removeTab(selectedTab.id)
                    return true
                }

                KeyEvent.KEYCODE_TAB,
                KeyEvent.KEYCODE_PAGE_UP,
                KeyEvent.KEYCODE_PAGE_DOWN,
                -> {
                    selectedTab ?: return false
                    val tabs = state.getNormalOrPrivateTabs(private = selectedTab.content.private)
                    if (tabs.size < 2) return true
                    val currentIndex = tabs.indexOfFirst { it.id == selectedTab.id }
                    if (currentIndex < 0) return false
                    val moveBackward =
                        event.isShiftPressed || event.keyCode == KeyEvent.KEYCODE_PAGE_UP
                    val offset = if (moveBackward) tabs.size - 1 else 1
                    val nextTab = tabs[(currentIndex + offset) % tabs.size]
                    components.useCases.tabsUseCases.selectTab(nextTab.id)
                    openToBrowser(BrowserDirection.FromGlobal)
                    return true
                }

                KeyEvent.KEYCODE_R -> {
                    selectedTab ?: return false
                    components.useCases.sessionUseCases.reload()
                    return true
                }
            }
        }

        if (!primaryModifier && event.isAltPressed) {
            when (event.keyCode) {
                KeyEvent.KEYCODE_DPAD_LEFT -> {
                    components.useCases.sessionUseCases.goBack()
                    return true
                }

                KeyEvent.KEYCODE_DPAD_RIGHT -> {
                    components.useCases.sessionUseCases.goForward()
                    return true
                }
            }
        }

        if (!primaryModifier && !event.isAltPressed && event.keyCode == KeyEvent.KEYCODE_F5) {
            selectedTab ?: return false
            components.useCases.sessionUseCases.reload()
            return true
        }

        if (!primaryModifier && !event.isAltPressed && event.keyCode == KeyEvent.KEYCODE_F6) {
            selectedTab ?: return false
            navHost.navController.navigate(
                BrowserFragmentDirections.actionGlobalHome(
                    focusOnAddressBar = true,
                    sessionToStartSearchFor = selectedTab.id,
                )
            )
            return true
        }

        return false
    }

    override fun dispatchGenericMotionEvent(event: MotionEvent): Boolean {
        if (isLargeScreenSize() && event.action == MotionEvent.ACTION_BUTTON_PRESS) {
            when (event.actionButton) {
                MotionEvent.BUTTON_BACK -> {
                    components.useCases.sessionUseCases.goBack()
                    return true
                }

                MotionEvent.BUTTON_FORWARD -> {
                    components.useCases.sessionUseCases.goForward()
                    return true
                }
            }
        }
        return super.dispatchGenericMotionEvent(event)
    }

'''
    text = replace_once(
        text,
        touch_anchor,
        shortcut_handler + touch_anchor,
        "desktop shortcut handler",
    )
    key_return = '''        return super.dispatchKeyEvent(event)
    }

    final override fun onKeyDown'''
    key_return_with_shortcuts = '''        if (
            event.action == KeyEvent.ACTION_DOWN &&
                event.repeatCount == 0 &&
                isLargeScreenSize() &&
                handleAcuteDesktopShortcut(event)
        ) {
            return true
        }
        return super.dispatchKeyEvent(event)
    }

    final override fun onKeyDown'''
    text = replace_once(
        text,
        key_return,
        key_return_with_shortcuts,
        "desktop shortcut dispatch",
    )
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
    # Firefox 158 colocates the wordmark and logo; retain historical fixture
    # compatibility but never silently choose between two upstream definitions.
    home_ui = fenix / "app/src/main/java/org/mozilla/fenix/home/ui"
    wordmarks = [home_ui / name for name in ("Wordmark.kt", "WordmarkAndLogo.kt") if (home_ui / name).is_file()]
    if len(wordmarks) != 1:
        raise OverlayError("Expected one upstream wordmark implementation")
    wordmark = wordmarks[0]
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
    customization_text = replace_once(
        customization_text, "            isVisible = isTallWindow() && !isWideWindow()\n",
        "            isVisible = false // Acute owns the fixed single-row layout.\n",
        "fixed native toolbar layout setting",
    )
    customization_text = replace_once(
        customization_text, "        category.apply {\n            removeAll()\n",
        "        category.apply {\n            isVisible = false // Primary actions have stable positions.\n            removeAll()\n",
        "fixed native toolbar shortcut setting",
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
    """Show Acute's package version and build number, retaining license links."""
    text = path.read_text(encoding="utf-8")
    old_header = '''                val versionCode = PackageInfoCompat.getLongVersionCode(packageInfo).toString()
                val maybeFenixVcsHash = if (BuildConfig.VCS_HASH.isNotBlank()) ", ${BuildConfig.VCS_HASH}" else ""
                val maybeGecko = getString(R.string.gecko_view_abbreviation)
                val geckoVersion = GeckoViewBuildConfig.MOZ_APP_VERSION + "-" + GeckoViewBuildConfig.MOZ_APP_BUILDID
                val appServicesAbbreviation = getString(R.string.app_services_abbreviation)
                val appServicesVersion = mozilla.components.Build.APPLICATION_SERVICES_VERSION
                val operatingSystemAbbrevation = "OS"
                val operatingSystemVersion = "Android ${Build.VERSION.RELEASE}"

                String.format(
                    "%s (Build #%s)%s\\n%s: %s\\n%s: %s\\n%s: %s",
                    packageInfo.versionName,
                    versionCode,
                    maybeFenixVcsHash,
                    maybeGecko,
                    geckoVersion,
                    appServicesAbbreviation,
                    appServicesVersion,
                    operatingSystemAbbrevation,
                    operatingSystemVersion,
                )
'''
    new_header = '''                val versionCode = PackageInfoCompat.getLongVersionCode(packageInfo)
                "${packageInfo.versionName} (Build #$versionCode)"
'''
    text = replace_once(text, old_header, new_header, "About version and build")
    text = replace_once(
        text,
        '''        val buildDate = BuildConfig.BUILD_DATE

        binding.aboutText.text = aboutText
        binding.aboutContent.text = content
        binding.buildDate.text = buildDate
''',
        '''        binding.aboutText.text = aboutText
        binding.aboutContent.text = content
        binding.buildDate.visibility = View.GONE
''',
        "About build date",
    )
    for unused_import in (
        "import android.os.Build\n",
        "import org.mozilla.fenix.BuildConfig\n",
        "import org.mozilla.geckoview.BuildConfig as GeckoViewBuildConfig\n",
    ):
        text = replace_once(text, unused_import, "", f"unused {unused_import.strip()}")
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


def copy_overlay(fenix: Path, channel: str) -> None:
    java_target = fenix / "app/src/main/java/org/mozilla/fenix/acute"
    java_target.mkdir(parents=True, exist_ok=True)
    shutil.copy2(ROOT / "overlay/kotlin/GitHubUpdateProvider.kt",
                 java_target / "GitHubUpdateProvider.kt")

    source_res = ROOT / "overlay/res"
    resource_targets = [fenix / "app/src/main/res"]
    for build_type in ("debug", "nightly", "beta", "release"):
        channel_res = fenix / f"app/src/{build_type}/res"
        if channel_res.is_dir():
            resource_targets.append(channel_res)
    for target_res in resource_targets:
        for source in source_res.rglob("*"):
            if source.is_file():
                relative = source.relative_to(source_res)
                destination = target_res / relative
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, destination)

    # Beta has an intentionally distinct launcher icon. Keep these overrides
    # outside the common resource tree so they can never leak into Stable.
    if channel == "beta":
        beta_res = ROOT / "overlay/beta-res"
        target_res = fenix / "app/src/beta/res"
        for source in beta_res.rglob("*"):
            if source.is_file():
                destination = target_res / source.relative_to(beta_res)
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
    if channel not in {"stable", "beta", "dev"}:
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
    home_activity = fenix / "app/src/main/java/org/mozilla/fenix/HomeActivity.kt"
    browser_toolbar = (
        fenix
        / "app/src/main/java/org/mozilla/fenix/components/toolbar/BrowserToolbarComposable.kt"
    )
    compose_toolbar = (
        checkout
        / "mobile/android/android-components/components/compose/browser-toolbar/src/main/java"
        / "mozilla/components/compose/browser/toolbar"
    )
    display_toolbar = compose_toolbar / "ui/FullDisplayToolbar.kt"
    edit_toolbar = compose_toolbar / "BrowserEditToolbar.kt"
    toolbar_surface = compose_toolbar / "BrowserToolbar.kt"
    toolbar_middleware = fenix / "app/src/main/java/org/mozilla/fenix/components/toolbar/BrowserToolbarMiddleware.kt"
    analytics = fenix / "app/src/main/java/org/mozilla/fenix/components/Analytics.kt"
    crash_reporter = checkout / "mobile/android/android-components/components/lib/crash/src/main/java/mozilla/components/lib/crash/CrashReporter.kt"
    main_menu = fenix / "app/src/main/java/org/mozilla/fenix/components/menu/compose/MainMenu.kt"
    browser_fragment = fenix / "app/src/main/java/org/mozilla/fenix/browser/BaseBrowserFragment.kt"
    clipping_behavior = (
        checkout
        / "mobile/android/android-components/components/ui/widgets/src/main/java/mozilla/components/ui/widgets/behavior/EngineViewClippingBehavior.kt"
    )
    toolbar_behavior = (
        checkout
        / "mobile/android/android-components/components/feature/toolbar/src/main/java/mozilla/components/feature/toolbar/ToolbarBehaviorController.kt"
    )
    onboarding = fenix / "app/src/main/java/org/mozilla/fenix/onboarding/OnboardingFragment.kt"
    preferences = fenix / "app/src/main/res/xml/preferences.xml"
    search_providers = fenix / "app/src/main/java/org/mozilla/fenix/components/SettingsSearchProviders.kt"
    desktop_mode = fenix / "app/src/main/java/org/mozilla/fenix/browser/desktopmode/DesktopModeRepository.kt"
    core = fenix / "app/src/main/java/org/mozilla/fenix/components/Core.kt"
    about = fenix / "app/src/main/java/org/mozilla/fenix/settings/about/AboutFragment.kt"
    customization = fenix / "app/src/main/java/org/mozilla/fenix/settings/CustomizationFragment.kt"
    values = fenix / "app/src/main/res/values"
    night_colors = fenix / "app/src/main/res/values-night/colors.xml"
    required = [gradle, manifest, release_manifest, beta_manifest, settings, home_activity, browser_toolbar, toolbar_middleware, main_menu, analytics, crash_reporter,
                display_toolbar, edit_toolbar, toolbar_surface, browser_fragment,
                clipping_behavior, toolbar_behavior, onboarding,
                preferences, search_providers, desktop_mode, core, about, customization,
                values / "static_strings.xml", values / "strings.xml", night_colors]
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        raise OverlayError("Missing expected Fenix files: " + ", ".join(missing))
    if (checkout / MARKER).exists():
        raise OverlayError("Overlay is already applied; start from a clean Firefox checkout")

    patch_gradle(gradle, channel)
    validate_tablet_upstream(manifest, desktop_mode)
    patch_manifest(manifest)
    patch_tablet_defaults(settings)
    patch_desktop_shortcuts(home_activity)
    patch_dark_theme_default(settings)
    patch_midnight_palette(night_colors)
    patch_native_address_bar(display_toolbar, edit_toolbar)
    patch_native_navigation(toolbar_middleware)
    patch_native_menu(main_menu)
    patch_runtime_privacy(settings, analytics)
    patch_disabled_crash_constructor(crash_reporter)
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
    copy_overlay(fenix, channel)
    validate_product_identity(fenix)
    (checkout / MARKER).write_text(
        f"Acute Web Android overlay applied ({channel})\n", encoding="utf-8"
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("firefox_checkout", type=Path)
    parser.add_argument(
        "--channel",
        choices=("stable", "beta", "dev"),
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

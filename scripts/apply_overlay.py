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


def patch_menu_navigation_scroll(path: Path) -> None:
    """Drop the navigation row's own vertical scroll now that it sits in the scrolling menu body.

    Upstream renders MenuNavigation in the fixed menu header, where its Row may scroll on its
    own. patch_native_menu moves it into MenuFrame's verticalScroll content, and Compose throws
    "Vertically scrollable component was measured with an infinity maximum height" for a
    scroll nested inside another, crashing whenever the menu opens on a web page.
    """
    text = path.read_text(encoding="utf-8")
    text = replace_once(text, "                .verticalScroll(rememberScrollState())\n", "",
                        "menu navigation row vertical scroll")
    text = replace_once(text, "import androidx.compose.foundation.verticalScroll\n", "",
                        "menu navigation verticalScroll import")
    scroll_state_import = "import androidx.compose.foundation.rememberScrollState\n"
    if text.count("rememberScrollState") == 1:
        text = replace_once(text, scroll_state_import, "", "menu navigation rememberScrollState import")
    path.write_text(text, encoding="utf-8")


def patch_private_by_default(settings: Path, tracking_protection: Path) -> None:
    """Default every profile to Strict tracking protection, HTTPS-Only mode and Global Privacy Control.

    Only defaults change: a choice a user already saved in Settings is kept. Gecko continues to
    exempt loopback and private-network IP addresses from HTTPS-Only upgrades.
    """
    text = settings.read_text(encoding="utf-8")
    for old, new, label in (
        ('''            appContext.getPreferenceKey(R.string.pref_key_https_only),
            default = false,''',
         '''            appContext.getPreferenceKey(R.string.pref_key_https_only),
            default = true,''',
         "HTTPS-Only default"),
        ('''            appContext.getPreferenceKey(R.string.pref_key_privacy_enable_global_privacy_control),
            false,''',
         '''            appContext.getPreferenceKey(R.string.pref_key_privacy_enable_global_privacy_control),
            true,''',
         "Global Privacy Control default"),
        ('''            appContext.getPreferenceKey(R.string.pref_key_tracking_protection_standard_option),
            true,''',
         '''            appContext.getPreferenceKey(R.string.pref_key_tracking_protection_standard_option),
            false,''',
         "Standard tracking protection default"),
        ('''    val useStrictTrackingProtection by
        booleanPreference(
            appContext.getPreferenceKey(R.string.pref_key_tracking_protection_strict_default),
            false,''',
         '''    val useStrictTrackingProtection by
        booleanPreference(
            appContext.getPreferenceKey(R.string.pref_key_tracking_protection_strict_default),
            true,''',
         "Strict tracking protection default"),
    ):
        text = replace_once(text, old, new, label)
    settings.write_text(text, encoding="utf-8")

    # The preference screen declares its own defaults; keep them identical to Settings.kt.
    xml = tracking_protection.read_text(encoding="utf-8")
    for old, new, label in (
        ('''        android:defaultValue="true"
        android:dependency="@string/pref_key_tracking_protection"
        android:key="@string/pref_key_tracking_protection_standard_option"''',
         '''        android:defaultValue="false"
        android:dependency="@string/pref_key_tracking_protection"
        android:key="@string/pref_key_tracking_protection_standard_option"''',
         "Standard tracking protection screen default"),
        ('''        android:defaultValue="false"
        android:dependency="@string/pref_key_tracking_protection"
        android:key="@string/pref_key_tracking_protection_strict_default"''',
         '''        android:defaultValue="true"
        android:dependency="@string/pref_key_tracking_protection"
        android:key="@string/pref_key_tracking_protection_strict_default"''',
         "Strict tracking protection screen default"),
        ('''        android:defaultValue="false"
        android:key="@string/pref_key_privacy_enable_global_privacy_control"''',
         '''        android:defaultValue="true"
        android:key="@string/pref_key_privacy_enable_global_privacy_control"''',
         "Global Privacy Control screen default"),
        # Upstream labels Standard as the default; in Acute it is Strict.
        ('android:title="@string/preference_enhanced_tracking_protection_standard_default_1" />',
         'android:title="@string/tracking_protection_standard" />',
         "Standard tracking protection title"),
        ('android:title="@string/preference_enhanced_tracking_protection_strict" />',
         'android:title="@string/acute_tracking_protection_strict_default" />',
         "Strict tracking protection title"),
    ):
        xml = replace_once(xml, old, new, label)
    tracking_protection.write_text(xml, encoding="utf-8")


def patch_private_by_default_summary(preferences: Path) -> None:
    """Explain the privacy defaults at the top of Settings › Privacy and security."""
    text = preferences.read_text(encoding="utf-8")
    category = '''        android:key="@string/pref_key_privacy_security_category"
        android:layout="@layout/preference_category_no_icon_style">
'''
    summary = category + '''        <androidx.preference.Preference
            android:key="acute_private_by_default"
            android:selectable="false"
            app:iconSpaceReserved="false"
            android:title="@string/acute_private_by_default_title"
            android:summary="@string/acute_private_by_default_settings_summary" />
'''
    text = replace_once(text, category, summary, "Privacy and security category")
    preferences.write_text(text, encoding="utf-8")


ACUTE_SOURCE_URL = "https://github.com/iiankehn/acute-web-android/blob/main/docs/SOURCE_AND_LICENSE.md"
ACUTE_PRIVACY_URL = "https://github.com/iiankehn/acute-web-android/blob/main/docs/PRIVACY.md"


def patch_acute_terms_page(path: Path) -> None:
    """Replace the welcome page's Mozilla terms, privacy notice and diagnostic-data lines.

    The upstream lines describe Firefox: Mozilla's Terms of Use, Mozilla's privacy notice and
    diagnostic data sent to Mozilla. None of that is true of Acute, so the page states Acute's
    own licensing and no-telemetry facts and links to Acute's documents instead.
    """
    text = path.read_text(encoding="utf-8")
    start = text.index("private fun BodyText(")
    body_start = text.index("    with(termsOfService) {\n", start)
    body_end = text.index("\n}\n\n@Composable\nprivate fun BodyLinkText(", body_start)
    upstream = text[body_start:body_end]
    for marker in ("onTermsOfServiceLinkClicked", "onPrivacyNoticeLinkClicked", "onManagePrivacyPreferencesLinkClicked"):
        if upstream.count(marker) != 1:
            raise OverlayError(f"Unexpected terms page body: {marker}")
    acute = f'''    // Acute states its own licensing and privacy facts instead of Mozilla's terms,
    // privacy notice and diagnostic-data disclosure, which describe Firefox.
    with(termsOfService) {{
        Column(modifier = Modifier.padding(horizontal = FirefoxTheme.layout.space.static100)) {{
            val sourceLinkText = stringResource(R.string.acute_onboarding_source_link_text)
            BodyLinkText(
                stringResource(R.string.acute_onboarding_source_line).updateFirstPlaceholder(sourceLinkText),
                LinkTextState(
                    text = sourceLinkText,
                    url = "{ACUTE_SOURCE_URL}",
                    onClick = eventHandler::onTermsOfServiceLinkClicked,
                ),
            )

            val privacyLinkText = stringResource(R.string.acute_onboarding_privacy_link_text)
            BodyLinkText(
                stringResource(R.string.acute_onboarding_privacy_line).updateFirstPlaceholder(privacyLinkText),
                LinkTextState(
                    text = privacyLinkText,
                    url = "{ACUTE_PRIVACY_URL}",
                    onClick = eventHandler::onPrivacyNoticeLinkClicked,
                ),
            )
        }}
    }}'''
    text = text[:body_start] + acute + text[body_end:]
    path.write_text(text, encoding="utf-8")


def patch_private_by_default_onboarding(onboarding: Path) -> None:
    """Add a first-run page announcing the privacy defaults; it has no opt-out control."""
    view = onboarding / "view"

    path = view / "OnboardingPageUiData.kt"
    text = path.read_text(encoding="utf-8")
    text = replace_once(text, '''        MARKETING_DATA(telemetryId = "marketing_data"),
''', '''        MARKETING_DATA(telemetryId = "marketing_data"),
        PRIVATE_BY_DEFAULT(telemetryId = "private_by_default"),
''', "onboarding page types")
    path.write_text(text, encoding="utf-8")

    path = view / "OnboardingMapper.kt"
    text = path.read_text(encoding="utf-8")
    text = replace_once(text, '''    onMarketingDataContinueClick: () -> Unit = {},
): OnboardingPageState =''', '''    onMarketingDataContinueClick: () -> Unit = {},
    onPrivateByDefaultContinueClick: () -> Unit = {},
): OnboardingPageState =''', "onboarding page state mapper parameters")
    text = replace_once(text, '''                onPositiveButtonClick = onMarketingDataContinueClick,
                onNegativeButtonClick = {}, // No negative button option for marketing data.
                isSmallDevice = isSmallDevice,
            )
    }
''', '''                onPositiveButtonClick = onMarketingDataContinueClick,
                onNegativeButtonClick = {}, // No negative button option for marketing data.
                isSmallDevice = isSmallDevice,
            )

        OnboardingPageUiData.Type.PRIVATE_BY_DEFAULT ->
            createOnboardingPageState(
                onboardingPageUiData = onboardingPageUiData,
                onPositiveButtonClick = onPrivateByDefaultContinueClick,
                onNegativeButtonClick = {}, // Acute's privacy defaults are announced, not offered.
                isSmallDevice = isSmallDevice,
            )
    }
''', "onboarding page state mapping")
    path.write_text(text, encoding="utf-8")

    path = view / "OnboardingScreen.kt"
    text = path.read_text(encoding="utf-8")
    text = replace_once(text, '''        onAgreeAndConfirmTermsOfService = {
            termsOfServiceEventHandler.onAcceptTermsButtonClicked()
            scrollToNextPageOrDismiss()
        },
''', '''        onAgreeAndConfirmTermsOfService = {
            termsOfServiceEventHandler.onAcceptTermsButtonClicked()
            scrollToNextPageOrDismiss()
        },
        onPrivateByDefaultContinueClick = scrollToNextPageOrDismiss,
''', "onboarding content callbacks")
    content_start = text.index("private fun OnboardingContent(")
    signature_end = text.index(") {", content_start)
    signature = text[content_start:signature_end]
    if "    onAgreeAndConfirmTermsOfService: () -> Unit,\n" not in signature:
        raise OverlayError("Expected exactly one onboarding content terms callback")
    text = (text[:content_start]
            + signature.replace("    onAgreeAndConfirmTermsOfService: () -> Unit,\n",
                                "    onAgreeAndConfirmTermsOfService: () -> Unit,\n"
                                "    onPrivateByDefaultContinueClick: () -> Unit = {},\n", 1)
            + text[signature_end:])
    text = replace_once(text, '''                        onTermsOfServiceButtonClick = onAgreeAndConfirmTermsOfService,
                        isSmallDevice = layout.isSmall,
''', '''                        onTermsOfServiceButtonClick = onAgreeAndConfirmTermsOfService,
                        onPrivateByDefaultContinueClick = onPrivateByDefaultContinueClick,
                        isSmallDevice = layout.isSmall,
''', "onboarding page state callbacks")
    text = replace_once(text, '''        OnboardingPageUiData.Type.NOTIFICATION_PERMISSION -> OnboardingPage(state)
''', '''        OnboardingPageUiData.Type.NOTIFICATION_PERMISSION,
        OnboardingPageUiData.Type.PRIVATE_BY_DEFAULT -> OnboardingPage(state)
''', "onboarding page rendering")
    path.write_text(text, encoding="utf-8")

    path = onboarding / "OnboardingTelemetryRecorder.kt"
    text = path.read_text(encoding="utf-8")
    impression = text.index("        when (pageType) {")
    end = text.index("\n        }\n    }\n", impression)
    text = text[:end] + '''

            // Acute does not record telemetry for its own onboarding page.
            OnboardingPageUiData.Type.PRIVATE_BY_DEFAULT -> Unit''' + text[end:]
    path.write_text(text, encoding="utf-8")

    path = onboarding / "OnboardingFragment.kt"
    text = path.read_text(encoding="utf-8")
    text = replace_once(text, '''            .distinctBy { it.type }
            .toMutableStateList()
    }
''', '''            .distinctBy { it.type }
            .withPrivateByDefaultPage()
            .toMutableStateList()
    }

    // Shown right after the terms page (or first), so every new profile learns the defaults.
    private fun List<OnboardingPageUiData>.withPrivateByDefaultPage(): List<OnboardingPageUiData> {
        val page =
            OnboardingPageUiData(
                type = OnboardingPageUiData.Type.PRIVATE_BY_DEFAULT,
                imageRes = R.drawable.ic_onboarding_welcome,
                title = getString(R.string.acute_private_by_default_title),
                description = getString(R.string.acute_private_by_default_onboarding_description),
                primaryButtonLabel = getString(R.string.acute_private_by_default_continue),
            )
        val index = indexOfFirst { it.type == OnboardingPageUiData.Type.TERMS_OF_SERVICE } + 1
        return toMutableList().apply { add(index, page) }
    }
''', "onboarding pages to display")
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




def patch_glean_startup(path: Path) -> None:
    """Keep startup and onboarding callers compatible without initializing Glean."""
    text = path.read_text(encoding="utf-8")
    original = '''    logger.debug("Initializing Glean (uploadEnabled=$isTelemetryUploadEnabled})")

    // for performance reasons, this is only available in Nightly or Debug builds
    val customEndpoint =
        if (Config.channel.isNightlyOrDebug) {
            // for testing, if custom glean server url is set in the secret menu, use it to initialize Glean
            getCustomGleanServerUrlIfAvailable(applicationContext)
        } else {
            null
        }

    val configuration =
        Configuration(
            channel = BuildConfig.BUILD_TYPE,
            httpClient =
                ConceptFetchHttpUploader(
                    lazy(LazyThreadSafetyMode.NONE) { client },
                    supportsOhttp = true,
                ),
            enableEventTimestamps = FxNimbus.features.glean.value().enableEventTimestamps,
            delayPingLifetimeIo = FxNimbus.features.glean.value().delayPingLifetimeIo,
            pingLifetimeThreshold = FxNimbus.features.glean.value().pingLifetimeThreshold,
            pingLifetimeMaxTime = FxNimbus.features.glean.value().pingLifetimeMaxTime,
        )

    // Since Glean v63.0.0, custom pings need to be registered prior to Glean init
    // in order to ensure they are enabled and able to collect data.
    // See https://bugzilla.mozilla.org/1934931 for more information.
    Glean.registerPings(Pings)

    // Set the metric configuration from Nimbus.
    Glean.applyServerKnobsConfig(FxNimbus.features.glean.value().gleanMetricConfiguration.toJSONObject().toString())

    Glean.initialize(
        applicationContext = applicationContext,
        configuration = configuration.setCustomEndpointIfAvailable(customEndpoint),
        uploadEnabled = isTelemetryUploadEnabled,
        buildInfo = GleanBuildInfo.buildInfo,
    )

    // Re-apply any debug view tag persisted from a previous run so it survives the restart (Nightly/Debug only).
    DefaultGleanDebugToolsStorage.restorePersistedDebugViewTag(applicationContext.components.settings)
}'''
    text = replace_once(text, original,
                        "    // Acute never initializes the telemetry backend. No upload client or pings.\n}",
                        "disabled Glean initialization")
    # The implementation no longer needs SDK/configuration imports.
    text = "\n".join(line for line in text.split("\n")
                     if not line.startswith("import ") or line in {
                         "import android.content.Context",
                         "import mozilla.components.concept.fetch.Client",
                         "import mozilla.components.support.base.log.logger.Logger",
                     })
    path.write_text(text, encoding="utf-8")

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
    provider += '        <activity android:name="org.mozilla.fenix.acute.ReportIssueActivity" android:exported="false" />\n'
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
    # Continuous onboarding re-prompts existing profiles on days 2-7: the system default-browser
    # role request, a Firefox Sync sign-in card and a Mozilla VPN (IP Protection) prompt.
    continuous = '''    var continuousOnboardingFeatureEnabled by
        booleanPreference(
            key = appContext.getPreferenceKey(R.string.pref_key_continuous_onboarding_enabled),
            default = { FxNimbus.features.continuousOnboarding.value().enabled },
        )
'''
    no_continuous = '''    // Acute Web does not re-prompt existing users with engagement or promotion cards.
    var continuousOnboardingFeatureEnabled: Boolean
        get() = false
        set(value) = Unit
'''
    settings_text = replace_once(
        settings_text, continuous, no_continuous, "continuous onboarding preference"
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


def patch_user_reporting(settings: Path, preferences: Path, search_providers: Path, channel: str) -> None:
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
                android:targetPackage="ACUTE_REPORT_PACKAGE"
                android:targetClass="org.mozilla.fenix.acute.ReportIssueActivity" />
        </androidx.preference.Preference>
'''
    preference_text = replace_once(
        preference_text, data_choices, issue_link.replace("ACUTE_REPORT_PACKAGE",
            "com.acuteweb.browser" + ("" if channel == "stable" else "." + channel)), "data collection settings entry"
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
                getString(R.string.acute_report_issue_title),
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
    text = replace_once(
        text, "    private fun openLinkInNormalTab(url: String) {\n",
        "    private fun openLinkInNormalTab(url: String) {\n"
        "        if (url == ACUTE_ISSUES_URL) {\n"
        "            startActivity(android.content.Intent(requireContext(), org.mozilla.fenix.acute.ReportIssueActivity::class.java))\n"
        "            return\n"
        "        }\n",
        "About local issue review",
    )
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


# Settings groups, in display order: (title, category key, preference keys).
# Every preference upstream shows below the account rows must be placed in
# exactly one group, so an upstream addition or removal fails the overlay
# instead of silently disappearing from Settings.
SETTINGS_GROUPS = (
    ("@string/preferences_category_general", None, (
        "@string/pref_key_make_default_browser",
        "@string/pref_key_search_settings",
        "@string/pref_key_language",
        "@string/pref_key_translation",
        "@string/pref_key_page_summaries",
        "@string/pref_key_ai_controls",
        "@string/pref_key_import_bookmarks",
    )),
    ("@string/acute_settings_category_appearance", None, (
        "@string/pref_key_customize",
        "@string/pref_key_home",
        "@string/pref_key_tabs",
        "@string/pref_key_accessibility",
    )),
    ("@string/preferences_category_privacy_security", "@string/pref_key_privacy_security_category", (
        "@string/pref_key_private_browsing",
        "@string/pref_key_tracking_protection_settings",
        "@string/pref_key_https_only_settings",
        "@string/pref_key_doh_settings",
        "@string/pref_key_ip_protection_settings",
        "@string/pref_key_site_permissions",
        "@string/pref_key_notifications",
    )),
    ("@string/acute_settings_category_passwords", None, (
        "@string/pref_key_passwords",
        "@string/pref_key_email_masks",
        "@string/pref_key_credit_cards",
    )),
    ("@string/acute_settings_category_browsing_data", None, (
        "@string/pref_key_delete_browsing_data",
        "@string/pref_key_delete_browsing_data_on_quit_preference",
    )),
    ("@string/acute_settings_category_downloads_links", None, (
        "@string/pref_key_downloads",
        "@string/pref_key_open_links_in_apps",
        "@string/pref_key_link_sharing",
    )),
    ("@string/acute_settings_category_extensions", None, (
        "@string/pref_key_addons",
        "@string/pref_key_install_local_addon",
        "@string/pref_key_override_amo_collection",
    )),
    ("@string/preferences_category_advanced", "@string/pref_key_advanced", (
        "@string/pref_key_firefox_labs",
        "@string/pref_key_remote_improvements",
        "@string/pref_key_remote_debugging",
        "@string/pref_key_enable_gecko_logs",
        "@string/pref_key_local_network_access",
        "@string/pref_key_leakcanary",
    )),
    ("@string/preferences_category_about", None, (
        "@string/pref_key_about",
        "acute_report_issue",
        "@string/pref_key_rate",
        "@string/pref_key_debug_settings",
        "@string/pref_key_nimbus_experiments",
        "@string/pref_key_start_profiler",
    )),
)
SETTINGS_ENTRY = re.compile(
    r"^        <([\w.]+)\b[^>]*?(?:/>|>.*?^        </\1>)\n", re.MULTILINE | re.DOTALL
)


def patch_settings_categories(path: Path) -> None:
    """Regroup the main Settings list into focused categories without dropping entries."""
    text = path.read_text(encoding="utf-8")
    general = (
        "    <androidx.preference.PreferenceCategory\n"
        '        android:title="@string/preferences_category_general"'
    )
    start = text.find(general)
    end = text.rfind("</androidx.preference.PreferenceScreen>")
    if start < 0 or end < start or text.count(general) != 1:
        raise OverlayError("Missing expected Fenix anchor: settings category layout")
    region = text[start:end]
    entries = {}
    for match in SETTINGS_ENTRY.finditer(region):
        key = re.search(r'android:key="([^"]+)"', match.group(0))
        if key is None or key.group(1) in entries:
            raise OverlayError("Settings entry without a unique key")
        entries[key.group(1)] = match.group(0)
    remainder = SETTINGS_ENTRY.sub("", region)
    remainder = re.sub(r"^    </?(?:androidx\.preference\.)?PreferenceCategory\b[^>]*>\n", "",
                       remainder, flags=re.MULTILINE)
    if remainder.strip():
        raise OverlayError("Unexpected content in Settings categories: " + remainder.strip()[:80])
    placed = [key for _, _, keys in SETTINGS_GROUPS for key in keys]
    if sorted(placed) != sorted(entries):
        missing = sorted(set(entries) - set(placed))
        absent = sorted(set(placed) - set(entries))
        raise OverlayError(f"Settings entries changed upstream; unplaced {missing}, absent {absent}")
    groups = []
    for title, category_key, keys in SETTINGS_GROUPS:
        key_attribute = f'\n        android:key="{category_key}"' if category_key else ""
        groups.append(
            "    <androidx.preference.PreferenceCategory\n"
            f'        android:title="{title}"{key_attribute}\n'
            '        android:layout="@layout/preference_category_no_icon_style">\n'
            + "\n".join(entries[key] for key in keys)
            + "    </androidx.preference.PreferenceCategory>\n"
        )
    path.write_text(text[:start] + "\n".join(groups) + text[end:], encoding="utf-8")


# Compose's painterResource accepts only vector XML or raster files, so a
# <bitmap> XML wrapper around the Acute mark throws when drawn. Upstream draws
# these images with painterResource; each becomes a raster copy of the mark.
COMPOSE_BRAND_RASTERS = (
    "ic_firefox",
    "expressive_firefox",
    "ic_onboarding_welcome",
    "nova_onboarding_marketing",
    "nova_onboarding_notifications",
    "nova_onboarding_sync",
    "nova_onboarding_sync_qr",
    "nova_onboarding_tou",
    "nova_onboarding_tou_2",
)


def patch_onboarding_artwork(fenix: Path) -> None:
    """Replace upstream mascot artwork with the Acute mark in Compose-safe forms."""
    mark = ROOT / "overlay/res/drawable-nodpi/acute_brand_mark_transparent.png"
    source_sets = [fenix / f"app/src/{name}/res" for name in ("main", "debug", "nightly", "beta", "release")]
    for name in COMPOSE_BRAND_RASTERS:
        if not (fenix / f"app/src/main/res/drawable/{name}.xml").is_file():
            raise OverlayError(f"Missing expected Fenix drawable: {name}")
        for res in source_sets:
            (res / f"drawable/{name}.xml").unlink(missing_ok=True)
        raster = fenix / f"app/src/main/res/drawable-nodpi/{name}.png"
        raster.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(mark, raster)
    # Selected toolbar-position art shows the mascot. The option also shows a
    # checkmark, so the unselected device art serves both states.
    drawable = fenix / "app/src/main/res/drawable"
    for position in ("top", "bottom"):
        active = drawable / f"nova_onboarding_toolbar_{position}_active.xml"
        inactive = drawable / f"nova_onboarding_toolbar_{position}_inactive.xml"
        if not active.is_file() or not inactive.is_file():
            raise OverlayError(f"Missing expected Fenix drawable: {position} toolbar onboarding art")
        shutil.copy2(inactive, active)


# Fox and Kit mascot illustrations in settings screens and empty states. Each
# is drawn with painterResource, so it becomes a raster: Acute's own artwork from
# overlay/artwork/<name>.png when present, otherwise a copy of the Acute mark.
ARTWORK = ROOT / "overlay/artwork"


def artwork(name: str) -> Path:
    custom = ARTWORK / f"{name}.png"
    return custom if custom.is_file() else ROOT / "overlay/res/drawable-nodpi/acute_brand_mark_transparent.png"


MASCOT_ARTWORK = (
    "drawable/fox_ai_on_state.xml",
    "drawable/fox_exclamation_alert.xml",
    "drawable/illustration_fox_box_inside_light.xml",
    "drawable/ic_kit_bookmarks_empty_state.xml",
    "drawable/ic_kit_heart.xml",
    "drawable/ic_kit_plug_error.xml",
    "drawable/ic_kit_shield_off_state.xml",
    "drawable/ic_kit_shield_on_state.xml",
    "drawable/kit_devices_sync.xml",
    "drawable/kit_devices_sync_error.xml",
    "drawable/kit_expressive_full.xml",
    "drawable/kit_head_protection_blocker_banner.xml",
    "drawable/kit_plug_error.xml",
    "drawable/kit_search_error.xml",
    "drawable-nodpi/firefox_as_default_banner_illustration.xml",
    "drawable-nodpi/kit_sleeping_under_laptop.webp",
)


def patch_mascot_artwork(fenix: Path) -> None:
    """Replace upstream mascot illustrations with Acute artwork."""
    res = fenix / "app/src/main/res"
    for relative in MASCOT_ARTWORK:
        upstream = res / relative
        if not upstream.is_file():
            raise OverlayError(f"Missing expected Fenix drawable: {relative}")
        name = upstream.stem
        for existing in (fenix / "app/src").glob(f"*/res/drawable*/{name}.*"):
            existing.unlink()
        raster = res / f"drawable-nodpi/{name}.png"
        raster.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(artwork(name), raster)


def patch_compose_accents(path: Path) -> None:
    """Give Compose screens Acute's blue instead of the Acorn violet accents."""
    text = path.read_text(encoding="utf-8")
    text = replace_once(text, "import androidx.compose.runtime.ReadOnlyComposable\n",
                        "import androidx.compose.runtime.ReadOnlyComposable\nimport androidx.compose.ui.graphics.Color\n",
                        "Compose theme Color import")
    text = replace_once(text, "            Theme.Private -> acornPrivateColorScheme()\n        }\n",
                        "            Theme.Private -> acornPrivateColorScheme()\n        }.withAcuteAccents(theme)\n",
                        "Compose theme color scheme")
    text = replace_once(text, "            Theme.Private -> privateColorPalette\n        }\n",
                        "            Theme.Private -> privateColorPalette\n        }.withAcuteAccents(theme)\n",
                        "Compose theme palette")
    text = replace_once(text, "            Theme.Private -> privateAcornGradientScheme\n        }\n",
                        "            Theme.Private -> privateAcornGradientScheme\n        }.withAcuteGradients()\n",
                        "Compose theme gradients")
    text = replace_once(text, "import mozilla.components.compose.base.theme.AcornColors\n",
                        "import mozilla.components.compose.base.theme.AcornColors\n"
                        "import mozilla.components.compose.base.theme.AcornGradient\n", "Compose gradient import")
    text = replace_once(text, "import mozilla.components.compose.base.theme.AcornTheme\n",
                        "import mozilla.components.compose.base.theme.AcornGradientType\n"
                        "import mozilla.components.compose.base.theme.AcornTheme\n", "Compose gradient type import")
    text = replace_once(text, "import mozilla.components.compose.base.theme.privateColorPalette\n",
                        "import mozilla.components.compose.base.theme.privateColorPalette\n"
                        "import mozilla.components.compose.base.utils.ColorStop\n", "Compose color stop import")
    text = text.rstrip("\n") + '''

// Matches Acute's native palette (acute_native_theme.xml and the brand colors).
private fun ColorScheme.withAcuteAccents(theme: Theme): ColorScheme =
    when (theme) {
        Theme.Light ->
            copy(
                primary = Color(0xFF0072BC),
                onPrimary = Color.White,
                primaryContainer = Color(0xFFD8EEFC),
                onPrimaryContainer = Color(0xFF00243D),
                inversePrimary = Color(0xFF8ABDDD),
                secondaryContainer = Color(0xFFD8EEFC),
                onSecondaryContainer = Color(0xFF00243D),
                tertiary = Color(0xFF0072BC),
                onTertiary = Color.White,
                tertiaryContainer = Color(0xFFD8EEFC),
                onTertiaryContainer = Color(0xFF00243D),
            )
        Theme.Private ->
            darkAccents().copy(
                background = Color(0xFF071827),
                surface = Color(0xFF071827),
                surfaceVariant = Color(0xFF0D2A40),
                surfaceTint = Color(0xFF1E3A52),
                outlineVariant = Color(0xFF1E3A52),
                secondaryContainer = Color(0xFF0D2A40),
                surfaceBright = Color(0xFF0D2A40),
                surfaceDim = Color(0xFF030C14),
                surfaceContainer = Color(0xFF071827),
                surfaceContainerHigh = Color(0xFF0A2133),
                surfaceContainerHighest = Color(0xFF0D2A40),
                surfaceContainerLow = Color(0xFF05121D),
                surfaceContainerLowest = Color(0xFF030C14),
            )
        else -> darkAccents()
    }

private fun ColorScheme.darkAccents(): ColorScheme =
    copy(
        primary = Color(0xFF8ABDDD),
        onPrimary = Color(0xFF101216),
        primaryContainer = Color(0xFF223B50),
        onPrimaryContainer = Color(0xFFF4F8FB),
        inversePrimary = Color(0xFF0072BC),
        secondaryContainer = Color(0xFF282D35),
        onSecondaryContainer = Color(0xFFF4F8FB),
        tertiary = Color(0xFF8ABDDD),
        onTertiary = Color(0xFF101216),
        tertiaryContainer = Color(0xFF223B50),
        onTertiaryContainer = Color(0xFFF4F8FB),
    )

// The private-mode mask and the selected-tab outline otherwise stay violet.
private fun AcornColors.withAcuteAccents(theme: Theme): AcornColors =
    if (theme == Theme.Private) {
        copy(
            iconPrivate = Color(0xFF0072BC),
            surfaceDimVariant = Color(0xFF0A2133),
            surfaceContainerSelected = Color(0xFF253E52),
        )
    } else {
        copy(iconPrivate = Color(0xFF0072BC))
    }

private val acuteAccentGradient =
    AcornGradient(
        type = AcornGradientType.Linear(angleInDegrees = 96f),
        colorStops = listOf(ColorStop(0f, Color(0xFF8ABDDD)), ColorStop(0.71f, Color(0xFF0072BC))),
    )

private fun AcornGradientScheme.withAcuteGradients(): AcornGradientScheme =
    copy(
        cfr =
            AcornGradient(
                type = AcornGradientType.Linear(angleInDegrees = 135f),
                colorStops = listOf(ColorStop(0f, Color(0xFF005A94)), ColorStop(1f, Color(0xFF0072BC))),
            ),
        accent = acuteAccentGradient,
        accentSubtle =
            AcornGradient(
                type = AcornGradientType.Linear(angleInDegrees = 96f),
                colorStops = listOf(ColorStop(0.4f, Color(0x400072BC)), ColorStop(1f, Color(0x408ABDDD))),
            ),
        tabOutline = acuteAccentGradient,
        privacyMask =
            AcornGradient(
                type = AcornGradientType.Vertical,
                colorStops = listOf(ColorStop(0f, Color(0xFF8ABDDD)), ColorStop(1f, Color.White)),
            ),
    )
'''
    path.write_text(text, encoding="utf-8")


# View-based private surfaces and the private-mode mask icon. Acute's private
# primary and surface colors are set in patch_branding_ui.
PRIVATE_COLOR_OVERRIDES = {
    "fx_mobile_icon_private": "#FF0072BC",
    "fx_mobile_private_icon_private": "#FF0072BC",
    "fx_mobile_private_primary_inverse": "#FF0072BC",
    "fx_mobile_private_secondary_container": "#FF0D2A40",
    "fx_mobile_private_tertiary": "#FF8ABDDD",
    "fx_mobile_private_tertiary_container": "#FF071827",
    "fx_mobile_private_outline_variant": "#FF1E3A52",
    "fx_mobile_private_sheet_outline": "#FF071827",
    "fx_mobile_private_surface_bright": "#FF0D2A40",
    "fx_mobile_private_surface_dim": "#FF030C14",
    "fx_mobile_private_surface_container": "#FF071827",
    "fx_mobile_private_surface_container_high": "#FF0A2133",
    "fx_mobile_private_surface_container_highest": "#FF0D2A40",
    "fx_mobile_private_surface_container_low": "#FF05121D",
    "fx_mobile_private_surface_container_lowest": "#FF030C14",
    "fx_mobile_private_surface_container_selected": "#FF253E52",
}


def patch_color_overrides(path: Path, overrides: dict[str, str]) -> None:
    text = path.read_text(encoding="utf-8")
    for name, value in overrides.items():
        color = re.compile(rf'(<color\b[^>]*\bname="{re.escape(name)}"[^>]*>).*?(</color>)', flags=re.DOTALL)
        text, count = color.subn(lambda match: f"{match.group(1)}{value}{match.group(2)}", text, count=1)
        if count != 1:
            raise OverlayError(f"Could not locate color {name} in {path}")
    path.write_text(text, encoding="utf-8")


def patch_private_colors(res: Path) -> None:
    """Give private browsing Acute's blues instead of the Nova violets."""
    patch_color_overrides(res / "values/colors.xml", PRIVATE_COLOR_OVERRIDES)
    patch_color_overrides(res / "values-night/colors.xml", {"fx_mobile_icon_private": "#FF0072BC"})
    mask = res / "color/private_mode_mask_gradient.xml"
    text = mask.read_text(encoding="utf-8") if mask.is_file() else ""
    text = replace_once(text, 'android:startColor="@color/novaViolet20"', 'android:startColor="#FF8ABDDD"',
                        "private mask gradient")
    mask.write_text(text, encoding="utf-8")


# English copy that names the wrong product, speaks in Mozilla's voice, or does
# not fit its screen. Firefox sync still pairs through desktop Firefox and a
# Mozilla account, so those instructions keep saying so.
ACUTE_ENGLISH_COPY = {
    "sign_in_instructions":
        "<![CDATA[Sync uses a Mozilla account. On your computer, open Firefox and go to "
        "<b>https://firefox.com/pair</b>]]>",
    "sign_in_create_account_text":
        "<![CDATA[No account? <u>Create a Mozilla account</u> to sync between devices.]]>",
    "preference_enhanced_tracking_protection": "Tracking Protection",
    "preference_enhanced_tracking_protection_summary":
        "Blocks trackers that follow you across sites, including cross-site cookies.",
    "preferences_downloads_2": "Downloads",
}


def patch_english_copy(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    for name, value in ACUTE_ENGLISH_COPY.items():
        string = re.compile(rf'(<string\b[^>]*\bname="{re.escape(name)}"[^>]*>).*?(</string>)', flags=re.DOTALL)
        text, count = string.subn(lambda match: f"{match.group(1)}{value}{match.group(2)}", text, count=1)
        if count != 1:
            raise OverlayError(f"Could not locate English string {name}")
    path.write_text(text, encoding="utf-8")


def patch_tracking_protection_banner(path: Path) -> None:
    """Drop the Firefox illustration so the explanation uses the full banner width."""
    text = path.read_text(encoding="utf-8")
    text = replace_once(text, 'android:background="#FF0250BB"',
                        'android:background="@color/acute_native_blue_container"', "ETP banner background")
    image = re.search(r"\n    <ImageView\b.*?/>\n", text, flags=re.DOTALL)
    if image is None or "@drawable/ic_etp_artwork" not in image.group(0):
        raise OverlayError("Missing expected Fenix anchor: ETP banner artwork")
    text = text.replace(image.group(0), "\n", 1).replace(">\n\n\n", ">\n\n", 1)
    guideline = re.search(r"\n    <androidx\.constraintlayout\.widget\.Guideline\b.*?/>\n", text, flags=re.DOTALL)
    if guideline is None:
        raise OverlayError("Missing expected Fenix anchor: ETP banner guideline")
    text = text.replace(guideline.group(0), "\n", 1).replace("\n\n</androidx", "\n</androidx", 1)
    end = 'app:layout_constraintEnd_toStartOf="@id/guideline"'
    if text.count(end) != 2:
        raise OverlayError("Missing expected Fenix anchor: ETP banner text width")
    text = text.replace(end, 'android:layout_marginEnd="16dp"\n        app:layout_constraintEnd_toEndOf="parent"')
    text = replace_once(text, 'android:textColor="@color/photonLightGrey05"',
                        'android:textColor="@color/acute_native_text"', "ETP banner text color")
    text = replace_once(text, 'android:textColor="@color/photonLightGrey30"',
                        'android:textColor="@color/acute_native_blue_soft"', "ETP banner link color")
    path.write_text(text, encoding="utf-8")


def patch_delete_data_counts(path: Path) -> None:
    """Count open tabs and history entries with plurals ("1 tab", not "1 tabs")."""
    text = path.read_text(encoding="utf-8")
    for old, plural, count in (
        ("R.string.preferences_delete_browsing_data_tabs_subtitle", "acute_delete_data_tabs", "openTabs"),
        ("R.string.preferences_delete_browsing_data_browsing_data_subtitle", "acute_delete_data_addresses",
         "historyCount"),
    ):
        call = re.search(rf"resources\.getString\(\s*{re.escape(old)},\s*{count},\s*\)", text)
        if call is None:
            raise OverlayError(f"Missing expected Fenix anchor: {old}")
        text = text.replace(call.group(0), f"resources.getQuantityString(R.plurals.{plural}, {count}, {count})", 1)
    path.write_text(text, encoding="utf-8")


def patch_privacy_report_default(settings: Path) -> None:
    """The tab manager's tracker card sits below the last tab, mid-screen; keep it opt-in."""
    text = settings.read_text(encoding="utf-8")
    text = replace_once(
        text,
        "            appContext.getPreferenceKey(R.string.pref_key_privacy_report_tab_manager),\n"
        "            default = true,\n",
        "            appContext.getPreferenceKey(R.string.pref_key_privacy_report_tab_manager),\n"
        "            default = false,\n",
        "tab manager privacy report default",
    )
    settings.write_text(text, encoding="utf-8")


# Upstream error-page image (without ".svg") -> Acute artwork in overlay/artwork.
# The padlock covers both certificate errors and the HTTPS-Only warning; the
# HTTPS-Only page is the one that offers to continue over HTTP.
ERROR_PAGE_ARTWORK = {
    "mozac_error_unplugged": "acute_connection_failed.png",
    "mozac_error_eye_roll": "acute_connection_failed.png",
    "mozac_error_asleep": "acute_connection_failed.png",
    "mozac_error_hourglass": "acute_connection_failed.png",
    "mozac_error_confused": "acute_page_not_found.png",
    "mozac_error_question_file": "acute_page_not_found.png",
    "mozac_error_no_internet": "acute_offline.png",
    "mozac_error_no_internet_connection": "acute_offline.png",
    "mozac_error_surprised": "acute_tab_crashed.png",
    "mozac_error_shred_file": "acute_tab_crashed.png",
    "mozac_error_inspect": "acute_tab_crashed.png",
}
ERROR_PAGE_LOCK = ("acute_not_encrypted.png", "acute_certificate_error.png")
ERROR_PAGE_DEFAULT = "acute_connection_failed.png"
TAB_CRASHED_ARTWORK = "acute_tab_crashed"
ERROR_PAGE_COLORS = {
    "--primary-button-color: #312a65;": "--primary-button-color: #0072bc;",
    "--secondary-button-text-color: #20123a;": "--secondary-button-text-color: #00243d;",
    "--primary-color: #3e2976;": "--primary-color: #0072bc;",
    "--header-color: #312a65;": "--header-color: #00243d;",
    "--primary-button-color: #7542e5;": "--primary-button-color: #0072bc;",
    "--secondary-button-text-color: #312a65;": "--secondary-button-text-color: #00243d;",
    "--primary-color: #cdb7ff;": "--primary-color: #8abddd;",
}


def error_page_image_script() -> str:
    images = "".join(f'    {name}: "{image}",\n' for name, image in ERROR_PAGE_ARTWORK.items())
    return f"""
// Acute artwork for each kind of error page.
function acuteErrorImage(queryMap) {{
  const name = queryMap.image.replace(/\\.svg$/, "");
  if (name === "mozac_error_lock") {{
    return queryMap.showContinueHttp === "true" ? "{ERROR_PAGE_LOCK[0]}" : "{ERROR_PAGE_LOCK[1]}";
  }}
  const images = {{
{images}  }};
  return images[name] || "{ERROR_PAGE_DEFAULT}";
}}
"""


def patch_error_pages(assets: Path) -> None:
    """Show Acute artwork and blue buttons on Fenix's error pages."""
    for script in ("lowMediumErrorPages.js", "highRiskErrorPages.js"):
        path = assets / script
        text = path.read_text(encoding="utf-8") if path.is_file() else ""
        text = replace_once(text, 'errorImage.src = "resource://android/assets/" + queryMap.image;',
                            'errorImage.src = "resource://android/assets/" + acuteErrorImage(queryMap);',
                            f"error page image in {script}")
        path.write_text(text.rstrip("\n") + "\n" + error_page_image_script(), encoding="utf-8")
    shared = assets / "shared_error_style.css"
    text = shared.read_text(encoding="utf-8") if shared.is_file() else ""
    if "#errorPageContainer" not in text:
        raise OverlayError("Missing expected Fenix anchor: shared error page style")
    shared.write_text(text.rstrip("\n") + "\n\n#errorImage {\n  display: block;\n  width: 100%;\n"
                      "  max-width: 320px;\n  height: auto;\n  margin: 0 auto;\n}\n", encoding="utf-8")
    styles = assets / "low_and_medium_risk_error_style.css"
    text = styles.read_text(encoding="utf-8") if styles.is_file() else ""
    for old, new in ERROR_PAGE_COLORS.items():
        text = replace_once(text, old, new, f"error page color {old}")
    styles.write_text(text, encoding="utf-8")
    for image in {*ERROR_PAGE_ARTWORK.values(), *ERROR_PAGE_LOCK, ERROR_PAGE_DEFAULT}:
        source = ARTWORK / image
        if not source.is_file():
            raise OverlayError(f"Missing Acute artwork: overlay/artwork/{image}")
        shutil.copy2(source, assets / image)


def patch_tab_crashed_artwork(fenix: Path) -> None:
    """The crashed-tab screen shows Acute's artwork instead of Firefox's."""
    layout = fenix / "app/src/main/res/layout/view_crash_reporter.xml"
    text = layout.read_text(encoding="utf-8") if layout.is_file() else ""
    text = replace_once(text, 'app:srcCompat="@drawable/fenix_error_1"',
                        f'app:srcCompat="@drawable/{TAB_CRASHED_ARTWORK}"', "crashed tab artwork")
    layout.write_text(text, encoding="utf-8")
    source = ARTWORK / f"{TAB_CRASHED_ARTWORK}.png"
    if not source.is_file():
        raise OverlayError(f"Missing Acute artwork: overlay/artwork/{source.name}")
    raster = fenix / f"app/src/main/res/drawable-nodpi/{TAB_CRASHED_ARTWORK}.png"
    raster.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, raster)


def copy_overlay(fenix: Path, channel: str) -> None:
    java_target = fenix / "app/src/main/java/org/mozilla/fenix/acute"
    java_target.mkdir(parents=True, exist_ok=True)
    shutil.copy2(ROOT / "overlay/kotlin/GitHubUpdateProvider.kt",
                 java_target / "GitHubUpdateProvider.kt")

    for name in ("LocalCrashReports.kt", "ReportIssueActivity.kt"):
        shutil.copy2(ROOT / "overlay/kotlin" / name, java_target / name)
    shutil.copy2(ROOT / "overlay/java/CrashReportSanitizer.java", java_target / "CrashReportSanitizer.java")

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
    tracking_protection = fenix / "app/src/main/res/xml/tracking_protection_preferences.xml"
    onboarding_views = [onboarding.parent / "view" / name for name in (
        "OnboardingPageUiData.kt", "OnboardingMapper.kt", "OnboardingScreen.kt",
        "TermsOfServiceOnboardingPage.kt")]
    onboarding_telemetry = onboarding.with_name("OnboardingTelemetryRecorder.kt")
    search_providers = fenix / "app/src/main/java/org/mozilla/fenix/components/SettingsSearchProviders.kt"
    desktop_mode = fenix / "app/src/main/java/org/mozilla/fenix/browser/desktopmode/DesktopModeRepository.kt"
    core = fenix / "app/src/main/java/org/mozilla/fenix/components/Core.kt"
    about = fenix / "app/src/main/java/org/mozilla/fenix/settings/about/AboutFragment.kt"
    customization = fenix / "app/src/main/java/org/mozilla/fenix/settings/CustomizationFragment.kt"
    values = fenix / "app/src/main/res/values"
    night_colors = fenix / "app/src/main/res/values-night/colors.xml"
    compose_theme = fenix / "app/src/main/java/org/mozilla/fenix/theme/FirefoxTheme.kt"
    delete_data = fenix / "app/src/main/java/org/mozilla/fenix/settings/deletebrowsingdata/DeleteBrowsingDataFragment.kt"
    etp_banner = fenix / "app/src/main/res/layout/tracking_protection_learn_more_preference.xml"
    required = [gradle, manifest, release_manifest, beta_manifest, settings, home_activity, browser_toolbar, toolbar_middleware, main_menu, analytics, crash_reporter,
                display_toolbar, edit_toolbar, toolbar_surface, browser_fragment,
                clipping_behavior, toolbar_behavior, onboarding, *onboarding_views, onboarding_telemetry,
                preferences, tracking_protection, search_providers, desktop_mode, core, about, customization,
                values / "static_strings.xml", values / "strings.xml", night_colors,
                compose_theme, delete_data, etp_banner]
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
    patch_menu_navigation_scroll(main_menu.with_name("MenuNavigation.kt"))
    patch_runtime_privacy(settings, analytics)
    patch_glean_startup(analytics.with_name("GleanHelper.kt"))
    patch_private_by_default(settings, tracking_protection)
    patch_disabled_crash_constructor(crash_reporter)
    patch_marketing_policy(settings, onboarding)
    patch_private_by_default_onboarding(onboarding.parent)
    patch_acute_terms_page(onboarding.parent / "view/TermsOfServiceOnboardingPage.kt")
    patch_user_reporting(settings, preferences, search_providers, channel)
    patch_settings_categories(preferences)
    patch_private_by_default_summary(preferences)
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
    patch_english_copy(values / "strings.xml")
    patch_compose_accents(compose_theme)
    patch_private_colors(fenix / "app/src/main/res")
    patch_tracking_protection_banner(etp_banner)
    patch_delete_data_counts(delete_data)
    patch_privacy_report_default(settings)
    patch_error_pages(fenix / "app/src/main/assets")
    patch_tab_crashed_artwork(fenix)
    copy_overlay(fenix, channel)
    patch_onboarding_artwork(fenix)
    patch_mascot_artwork(fenix)
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

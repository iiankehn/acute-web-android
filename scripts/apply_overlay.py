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


def replace_span_once(
    text: str,
    start: str,
    end: str,
    replacement: str,
    label: str,
) -> str:
    """Replace one fail-closed span while retaining its end anchor."""
    start_count = text.count(start)
    end_count = text.count(end)
    if start_count != 1 or end_count != 1:
        raise OverlayError(
            f"Expected one {label} span; found start={start_count}, end={end_count}"
        )
    prefix, remainder = text.split(start, 1)
    _, suffix = remainder.split(end, 1)
    return prefix + replacement + end + suffix


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
    "fx_mobile_primary": "@color/acute_glass_light",
    "fx_mobile_on_primary": "@color/acute_glass_canvas",
    "fx_mobile_primary_container": "@color/acute_glass_surface_selected",
    "fx_mobile_on_primary_container": "@color/acute_glass_text",
    "fx_mobile_secondary": "@color/acute_glass_text_muted",
    "fx_mobile_on_secondary": "@color/acute_glass_canvas",
    "fx_mobile_secondary_container": "@color/acute_glass_surface_high",
    "fx_mobile_on_secondary_container": "@color/acute_glass_text",
    "fx_mobile_tertiary": "@color/acute_glass_light",
    "fx_mobile_on_tertiary": "@color/acute_glass_canvas",
    "fx_mobile_tertiary_container": "@color/acute_glass_surface_selected",
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


# Acute Workspaces deliberately uses Firefox's maintained, local tab-group
# store. Resource identifiers stay upstream-compatible while the user-facing
# model is consistently named and described as a workspace.
WORKSPACE_STRING_OVERRIDES = {
    "browser_menu_add_to_tab_group": "Add to workspace",
    "preferences_tab_groups_feature": "Enable Workspaces",
    "create_tab_group_content_description": "Create workspace",
    "tab_manager_multiselect_menu_item_add_to_tab_group": "Add to workspace",
    "tab_group_onboarding_item_title": "Create a workspace",
    "tab_group_onboarding_grid_item_description":
        "Drag one tab onto another to create a workspace.",
    "tab_group_onboarding_list_item_description":
        "Select multiple tabs to create a workspace.",
    "tab_group_onboarding_item_dismiss_content_description":
        "Dismiss workspace introduction",
    "tab_manager_empty_tab_groups_page_header": "Build your first workspace",
    "tab_manager_empty_tab_groups_page_description":
        "Select related tabs to keep them together and ready when you return.",
    "create_tab_group_title": "Create workspace",
    "edit_tab_group_title": "Edit workspace",
    "edit_tab_group_bottom_sheet_grabber_content_description":
        "New workspace, collapse drag handle",
    "create_tab_group_form_default_name": "Workspace %d",
    "add_to_tab_group_title": "Add to workspace",
    "add_to_tab_group_bottom_sheet_grabber_content_description":
        "Add to a workspace, collapse drag handle",
    "add_to_new_tab_group_content_description": "Add to new workspace",
    "add_to_new_tab_group_title": "New workspace",
    "tab_group_sheet_dismiss_description": "View workspace, collapse drag handle",
    "delete_tab_group_confirmation_dialog_title": "Delete workspace?",
    "delete_tab_group_confirmation_dialog_body":
        "This permanently deletes the workspace.",
    "delete_tab_group_confirmation_dialog_confirm": "Delete workspace",
    "close_tab_and_delete_group_confirmation_dialog_title":
        "Close tab and delete workspace?",
    "close_tab_and_delete_group_confirmation_dialog_body":
        "This permanently deletes the workspace.",
    "close_tab_and_delete_group_confirmation_dialog_confirm": "Delete workspace",
    "tab_group_three_dot_menu_close": "Suspend",
    "tab_group_three_dot_menu_ungroup": "Dissolve",
    "ungroup_tab_group_confirmation_dialog_title": "Dissolve workspace?",
    "ungroup_tab_group_confirmation_dialog_body":
        "The tabs will remain open on this device, but the workspace will be deleted.",
    "ungroup_tab_group_confirmation_dialog_confirm": "Dissolve",
    "collections_migration_homepage_banner_title": "Workspaces",
    "collections_migration_homepage_card_message":
        "Keep related tabs together and return to them later.",
    "collections_migration_homepage_card_link": "Open workspaces",
}


WORKSPACE_PLURAL_OVERRIDES = {
    "tabs_header_tab_group_counter_title": (
        "%1$d workspace open. Tap to switch tabs.",
        "%1$d workspaces open. Tap to switch tabs.",
    ),
    "add_to_exiting_tab_group_content_description": (
        "Add to %1$s workspace, %2$d tab, color %3$s",
        "Add to %1$s workspace, %2$d tabs, color %3$s",
    ),
    "expanded_tab_group_header_description": (
        "%1$s workspace with %2$d tab, color %3$s",
        "%1$s workspace with %2$d tabs, color %3$s",
    ),
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


def patch_core_glass_toolbar(path: Path) -> None:
    """Give the browser toolbar a visibly layered CORE Glass treatment."""
    text = path.read_text(encoding="utf-8")
    text = replace_once(
        text,
        "import androidx.compose.foundation.background\n",
        "import androidx.compose.foundation.background\n"
        "import androidx.compose.ui.draw.drawWithContent\n",
        "toolbar glass draw import",
    )
    text = replace_once(
        text,
        "import androidx.compose.ui.graphics.Color\n",
        "import androidx.compose.ui.geometry.Offset\n"
        "import androidx.compose.ui.graphics.Brush\n"
        "import androidx.compose.ui.graphics.Color\n",
        "toolbar glass graphics imports",
    )
    text = replace_once(
        text,
        "import androidx.compose.ui.Modifier\n",
        "import androidx.compose.ui.Modifier\n"
        "import androidx.compose.ui.platform.LocalConfiguration\n",
        "toolbar large-screen configuration import",
    )
    theme_open = "                    MaterialTheme(colorScheme = colorScheme) {\n"
    glass_open = '''                    MaterialTheme(colorScheme = colorScheme) {
                        // CORE Glass uses a translucent charcoal stack over a subtle
                        // ambient-light reflection. The child surfaces retain their own alpha,
                        // so the address field and selected tabs read as separate layers.
                        val acuteLargeScreen =
                            LocalConfiguration.current.smallestScreenWidthDp >= 600
                        val acuteGlassColors =
                            if (acuteLargeScreen) {
                                listOf(
                                    Color(0xE025282D),
                                    Color(0xD01B1D21),
                                    Color(0xC0121417),
                                )
                            } else {
                                listOf(
                                    Color(0xB316181C),
                                    Color(0xA60F1114),
                                    Color(0x99090B0D),
                                )
                            }
                        val acuteCoreGlassModifier =
                            Modifier
                                .fillMaxWidth()
                                .wrapContentHeight()
                                .background(
                                    Brush.verticalGradient(
                                        colors = acuteGlassColors
                                    )
                                )
                                .drawWithContent {
                                    drawContent()
                                    drawLine(
                                        color = Color(0x66F1F2F4),
                                        start = Offset(0f, size.height - 1f),
                                        end = Offset(size.width, size.height - 1f),
                                        strokeWidth = 1f,
                                    )
                                }
'''
    text = replace_once(text, theme_open, glass_open, "toolbar glass theme wrapper")
    column = "Column(modifier = Modifier.fillMaxWidth().wrapContentHeight())"
    count = text.count(column)
    if count != 2:
        raise OverlayError(f"Expected two browser toolbar columns; found {count}")
    text = text.replace(column, "Column(modifier = acuteCoreGlassModifier)")
    path.write_text(text, encoding="utf-8")


def patch_core_glass_compositor(
    toolbar_path: Path,
    browser_fragment_path: Path,
    clipping_behavior_path: Path,
    toolbar_behavior_path: Path,
) -> None:
    """Render Gecko below phone glass while keeping large-screen chrome fixed."""
    toolbar = toolbar_path.read_text(encoding="utf-8")
    toolbar = replace_once(
        toolbar,
        "    val backgroundColor = MaterialTheme.colorScheme.surface\n",
        "    // CORE Glass is composited over Gecko content by Fenix.\n"
        "    val backgroundColor = Color.Transparent\n",
        "transparent browser toolbar surface",
    )
    toolbar_path.write_text(toolbar, encoding="utf-8")

    fragment = browser_fragment_path.read_text(encoding="utf-8")
    fragment = replace_once(
        fragment,
        "import org.mozilla.fenix.utils.allowUndo\n",
        "import org.mozilla.fenix.utils.allowUndo\n"
        "import org.mozilla.fenix.utils.isLargeScreenSize\n",
        "large-screen toolbar import",
    )
    original = '''        if (isToolbarDynamic(context) && webAppToolbarShouldBeVisible) {
            getEngineView().setDynamicToolbarMaxHeight(topToolbarHeight + bottomToolbarHeight)

            (getSwipeRefreshLayout().layoutParams as CoordinatorLayout.LayoutParams).behavior =
                EngineViewClippingBehavior(
                    context = context,
                    attrs = null,
                    engineViewParent = getSwipeRefreshLayout(),
                    topToolbarHeight = topToolbarHeight,
                    bottomToolbarHeight = bottomToolbarHeight,
                )
        } else {
'''
    replacement = '''        // CORE Glass requires live page pixels below the top toolbar. Keeping the
        // Gecko viewport at y=0 also lets the translucent Compose layers blend with
        // the page instead of an opaque parent surface. Because the top toolbar is
        // overlaid, only a bottom toolbar may reduce the web content viewport.
        val acuteGlassTopOverlayHeight = 0

        if (isToolbarDynamic(context) && !context.isLargeScreenSize() && webAppToolbarShouldBeVisible) {
            getEngineView().setDynamicToolbarMaxHeight(bottomToolbarHeight)

            (getSwipeRefreshLayout().layoutParams as CoordinatorLayout.LayoutParams).behavior =
                EngineViewClippingBehavior(
                    context = context,
                    attrs = null,
                    engineViewParent = getSwipeRefreshLayout(),
                    topToolbarHeight = topToolbarHeight,
                    bottomToolbarHeight = bottomToolbarHeight,
                )
        } else {
'''
    fragment = replace_once(fragment, original, replacement, "Gecko toolbar overlay geometry")
    fragment = replace_once(
        fragment,
        "            swipeRefreshParams.topMargin = topToolbarHeight\n",
        "            // Laptop/tablet chrome remains visible and reserves layout space.\n"
        "            // Phones retain the page-backed CORE Glass overlay.\n"
        "            swipeRefreshParams.topMargin =\n"
        "                if (context.isLargeScreenSize()) topToolbarHeight else acuteGlassTopOverlayHeight\n",
        "adaptive Gecko toolbar margin",
    )
    browser_fragment_path.write_text(fragment, encoding="utf-8")

    clipping = clipping_behavior_path.read_text(encoding="utf-8")
    clipping = replace_once(
        clipping,
        "                engineViewParent.translationY = recentTopToolbarTranslation + topToolbarHeight\n",
        "                // CORE Glass keeps live page pixels below the translucent toolbar.\n"
        "                // The toolbar still receives the real height for nested-scroll behavior.\n"
        "                engineViewParent.translationY = 0f\n",
        "glass engine overlay translation",
    )
    clipping = replace_once(
        clipping,
        "    private val dynamicToolbarMaxHeight = topToolbarHeight + bottomToolbarHeight\n",
        "    // The translucent top toolbar overlays Gecko and must not shrink CSS viewport units.\n"
        "    private val dynamicToolbarMaxHeight = bottomToolbarHeight\n",
        "glass dynamic viewport height",
    )
    clipping = replace_once(
        clipping,
        "            val contentBottomClipping = (recentTopToolbarTranslation - recentBottomToolbarTranslation).roundToInt()\n",
        "            // Top-toolbar movement is visual-only for CORE Glass. Only the bottom\n"
        "            // toolbar changes the web content viewport and vertical clipping.\n"
        "            val contentBottomClipping = (-recentBottomToolbarTranslation).roundToInt()\n",
        "glass viewport clipping",
    )
    clipping_behavior_path.write_text(clipping, encoding="utf-8")

    toolbar_behavior = toolbar_behavior_path.read_text(encoding="utf-8")
    toolbar_behavior = replace_once(
        toolbar_behavior,
        '''                        } else if (!state.content.loading) {
                            enableScrolling()
                        }
''',
        '''                        } else if (!state.content.loading) {
                            enableScrolling()
                            // Acute reveals the top of each page after loading. Scrolling
                            // upward restores the toolbar through the standard behavior.
                            toolbar.collapse()
                        }
''',
        "collapse glass toolbar after page load",
    )
    toolbar_behavior_path.write_text(toolbar_behavior, encoding="utf-8")


def patch_core_glass_address_bar(display_path: Path, edit_path: Path) -> None:
    """Style the address pill itself instead of relying on ambient theme colors."""
    display = display_path.read_text(encoding="utf-8")
    display = replace_once(
        display,
        "import androidx.compose.foundation.background\n",
        "import androidx.compose.foundation.background\nimport androidx.compose.foundation.border\n",
        "display address bar border import",
    )
    display = replace_once(
        display,
        "import androidx.compose.ui.graphics.Color\n",
        "import androidx.compose.ui.graphics.Brush\nimport androidx.compose.ui.graphics.Color\n",
        "display address bar brush import",
    )
    display_fill = '''                            .background(
                                color = MaterialTheme.colorScheme.surfaceContainerHighest,
                                shape = CircleShape,
                            )
'''
    glass_fill = '''                            .background(
                                brush =
                                    Brush.horizontalGradient(
                                        colors =
                                            listOf(
                                                Color(0xD034373C),
                                                Color(0xBC24272B),
                                                Color(0xC02B2E33),
                                            )
                                    ),
                                shape = CircleShape,
                            )
                            .border(
                                width = 1.dp,
                                brush =
                                    Brush.horizontalGradient(
                                        colors = listOf(Color(0x99F1F2F4), Color(0x33F1F2F4))
                                    ),
                                shape = CircleShape,
                            )
'''
    display = replace_once(display, display_fill, glass_fill, "display address bar fill")
    display_path.write_text(display, encoding="utf-8")

    edit = edit_path.read_text(encoding="utf-8")
    edit = replace_once(
        edit,
        "import androidx.compose.foundation.background\n",
        "import androidx.compose.foundation.background\nimport androidx.compose.foundation.border\n",
        "edit address bar border import",
    )
    edit = replace_once(
        edit,
        "import androidx.compose.ui.graphics.Color\n",
        "import androidx.compose.ui.graphics.Brush\nimport androidx.compose.ui.graphics.Color\n",
        "edit address bar brush import",
    )
    edit_fill = '''                        .clip(shape = CircleShape)
                        .background(color = MaterialTheme.colorScheme.surfaceContainerHighest),
'''
    edit_glass_fill = '''                        .clip(shape = CircleShape)
                        .background(
                            brush =
                                Brush.horizontalGradient(
                                    colors =
                                        listOf(
                                            Color(0xD034373C),
                                            Color(0xBC24272B),
                                            Color(0xC02B2E33),
                                        )
                                )
                        )
                        .border(
                            width = 1.dp,
                            brush =
                                Brush.horizontalGradient(
                                    colors = listOf(Color(0x99F1F2F4), Color(0x33F1F2F4))
                                ),
                            shape = CircleShape,
                        ),
'''
    edit = replace_once(edit, edit_fill, edit_glass_fill, "edit address bar fill")
    edit_path.write_text(edit, encoding="utf-8")


def replace_product_branding(xml: str) -> str:
    """Rename the product while preserving truthful upstream disclosures."""
    acute_resource_values = {
        "preferences_rate": "Visit the Acute Web project",
        "preferences_show_sponsored_suggestions_summary": "Recommendations are disabled in Acute Web",
        "customize_toggle_contile": "Recommendations",
        "pair_instructions_2": "Sync pairing is not available in Acute Web",
        "sign_in_instructions": "Sync pairing is not available in Acute Web",
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


def patch_adaptive_menu(main_menu_path: Path, menu_dialog_path: Path) -> None:
    """Make common actions stable and use a context-style panel on large screens."""
    main = main_menu_path.read_text(encoding="utf-8")

    banner = '''        if (accessPoint == MenuAccessPoint.Home && showBanner) {
            MenuBanner(
                onDismiss = {
                    onBannerDismiss()
                },
                onClick = {
                    onBannerClick()
                },
            )
        }

'''
    main = replace_once(main, banner, "", "menu promotion banner")

    ip_offer = '''        if (showIPProtection) {
            MenuGroup {
                IPProtectionMenuItem(
                    state = ipProtectionMenuState,
                    onToggle = onIPProtectionClick,
                    onNavigate = onIPProtectionNavigate,
                )
            }
        }

'''
    main = replace_once(main, ip_offer, "", "menu IP protection offer")

    account = '''            MozillaAccountMenuItem(
                account = account,
                accountState = accountState,
                onClick = onMozillaAccountButtonClick,
            )

'''
    main = replace_once(main, account, "", "menu account promotion")

    library = '''        LibraryMenuGroup(
            isDownloadHighlighted = isDownloadHighlighted,
            onBookmarksMenuClick = onBookmarksMenuClick,
            onHistoryMenuClick = onHistoryMenuClick,
            onDownloadsMenuClick = onDownloadsMenuClick,
            onPasswordsMenuClick = onPasswordsMenuClick,
        )

'''
    main = replace_once(main, library, "", "existing library menu position")
    home_extensions = '''        if (accessPoint == MenuAccessPoint.Home) {
            MenuGroup {
                ExtensionsMenuItem(
'''
    main = replace_once(
        main,
        home_extensions,
        '''        // Acute's fixed library actions never move when page context changes.
''' + library + home_extensions,
        "fixed menu action insertion",
    )
    main_menu_path.write_text(main, encoding="utf-8")

    dialog = menu_dialog_path.read_text(encoding="utf-8")
    dialog = replace_once(
        dialog,
        "import org.mozilla.fenix.utils.exitSubmenu\n",
        "import org.mozilla.fenix.utils.exitSubmenu\n"
        "import org.mozilla.fenix.utils.isLargeScreenSize\n",
        "large-screen menu import",
    )
    sheet = '''menuHandleState =
                    MenuHandleState(
                        contentDescription = handlebarContentDescription,
                        useDarkBackground =
                            !settings.shouldUseBottomToolbar &&
                                !settings.shouldUseExpandedToolbar &&
                                (isExtensionsExpanded || isMoreMenuExpanded) &&
                                args.accesspoint == MenuAccessPoint.Browser,
                    ),
                snackbarHostState = snackbarHostState,
                cornerShape =
                    MaterialTheme.shapes.extraLarge.copy(
                        bottomStart = CornerSize(0.dp),
                        bottomEnd = CornerSize(0.dp),
                    ),
'''
    adaptive_sheet = '''menuHandleState =
                    MenuHandleState(
                        contentDescription = handlebarContentDescription,
                        useDarkBackground =
                            !settings.shouldUseBottomToolbar &&
                                !settings.shouldUseExpandedToolbar &&
                                (isExtensionsExpanded || isMoreMenuExpanded) &&
                                args.accesspoint == MenuAccessPoint.Browser,
                        // Large screens present a floating context panel, not a draggable sheet.
                        visible = !context.isLargeScreenSize(),
                    ),
                snackbarHostState = snackbarHostState,
                cornerShape =
                    if (context.isLargeScreenSize()) {
                        MaterialTheme.shapes.extraLarge
                    } else {
                        MaterialTheme.shapes.extraLarge.copy(
                            bottomStart = CornerSize(0.dp),
                            bottomEnd = CornerSize(0.dp),
                        )
                    },
'''
    dialog = replace_once(dialog, sheet, adaptive_sheet, "adaptive menu surface")
    menu_dialog_path.write_text(dialog, encoding="utf-8")


def patch_capture_export_actions(
    main_menu_path: Path,
    menu_dialog_path: Path,
    more_settings_path: Path,
) -> None:
    """Promote Gecko's maintained document export actions into the page menu."""
    main = main_menu_path.read_text(encoding="utf-8")

    main = replace_once(
        main,
        '''    onShareButtonClick: () -> Unit,
    extensionsMenuItemDescription: String?,
    moreSettingsSubmenu: @Composable () -> Unit,
    extensionSubmenu: @Composable () -> Unit,
) {''',
        '''    onShareButtonClick: () -> Unit,
    extensionsMenuItemDescription: String?,
    moreSettingsSubmenu: @Composable () -> Unit,
    extensionSubmenu: @Composable () -> Unit,
    onSaveAsPDFMenuClick: () -> Unit = {},
    onPrintMenuClick: () -> Unit = {},
    isAndroidAutomotiveAvailable: Boolean = false,
) {''',
        "capture callbacks on main menu",
    )
    main = replace_once(
        main,
        '''                moreSettingsSubmenu = moreSettingsSubmenu,
                extensionSubmenu = extensionSubmenu,
            )''',
        '''                moreSettingsSubmenu = moreSettingsSubmenu,
                extensionSubmenu = extensionSubmenu,
                onSaveAsPDFMenuClick = onSaveAsPDFMenuClick,
                onPrintMenuClick = onPrintMenuClick,
                isAndroidAutomotiveAvailable = isAndroidAutomotiveAvailable,
            )''',
        "capture callbacks into tools menu",
    )
    main = replace_once(
        main,
        '''    moreSettingsSubmenu: @Composable () -> Unit,
    extensionSubmenu: @Composable () -> Unit,
) {
    MenuGroup {''',
        '''    moreSettingsSubmenu: @Composable () -> Unit,
    extensionSubmenu: @Composable () -> Unit,
    onSaveAsPDFMenuClick: () -> Unit,
    onPrintMenuClick: () -> Unit,
    isAndroidAutomotiveAvailable: Boolean,
) {
    MenuGroup {''',
        "capture callbacks on tools menu",
    )
    find_in_page = '''        MenuItem(
            label = stringResource(id = R.string.browser_menu_find_in_page),
            beforeIconPainter = painterResource(id = iconsR.drawable.mozac_ic_search_24),
            onClick = onFindInPageMenuClick,
        )
'''
    capture_actions = find_in_page + '''
        // Acute keeps dependable document capture one tap away. Both actions use
        // Gecko's maintained page pipeline rather than an Acute-specific renderer.
        MenuItem(
            label = stringResource(id = R.string.browser_menu_save_as_pdf_2),
            beforeIconPainter = painterResource(id = iconsR.drawable.mozac_ic_save_file_24),
            onClick = onSaveAsPDFMenuClick,
        )

        if (!isAndroidAutomotiveAvailable) {
            MenuItem(
                label = stringResource(id = R.string.browser_menu_print_2),
                beforeIconPainter = painterResource(id = iconsR.drawable.mozac_ic_print_24),
                onClick = onPrintMenuClick,
            )
        }
'''
    main = replace_once(main, find_in_page, capture_actions, "primary capture actions")
    main_menu_path.write_text(main, encoding="utf-8")

    dialog = menu_dialog_path.read_text(encoding="utf-8")
    dialog = replace_once(
        dialog,
        '''                                moreSettingsSubmenu = {''',
        '''                                // Document capture is promoted into Acute's first-level page actions.
                                onSaveAsPDFMenuClick = {
                                    saveToPdfUseCase()
                                    dismiss()
                                },
                                onPrintMenuClick = {
                                    printContentUseCase()
                                    dismiss()
                                },
                                isAndroidAutomotiveAvailable = context.isAndroidAutomotiveAvailable(),
                                moreSettingsSubmenu = {''',
        "capture handlers on main menu",
    )
    dialog = replace_once(
        dialog,
        '''                                        isAndroidAutomotiveAvailable = context.isAndroidAutomotiveAvailable(),
                                        summarizationMenuState = summarizationMenuState,''',
        '''                                        isAndroidAutomotiveAvailable = context.isAndroidAutomotiveAvailable(),
                                        showCaptureActions = false,
                                        summarizationMenuState = summarizationMenuState,''',
        "hide duplicate capture submenu actions",
    )
    menu_dialog_path.write_text(dialog, encoding="utf-8")

    more = more_settings_path.read_text(encoding="utf-8")
    more = replace_once(
        more,
        '''    isAndroidAutomotiveAvailable: Boolean,
    summarizationMenuState: SummarizationMenuState,''',
        '''    isAndroidAutomotiveAvailable: Boolean,
    showCaptureActions: Boolean = true,
    summarizationMenuState: SummarizationMenuState,''',
        "capture submenu visibility parameter",
    )
    more = replace_once(
        more,
        '''        SaveAsPdfMenuItem(onSaveAsPDFMenuClick = onSaveAsPDFMenuClick)
        PrintMenuItem(
            isAndroidAutomotiveAvailable = isAndroidAutomotiveAvailable,
            onPrintMenuClick = onPrintMenuClick,
        )''',
        '''        if (showCaptureActions) {
            SaveAsPdfMenuItem(onSaveAsPDFMenuClick = onSaveAsPDFMenuClick)
            PrintMenuItem(
                isAndroidAutomotiveAvailable = isAndroidAutomotiveAvailable,
                onPrintMenuClick = onPrintMenuClick,
            )
        }''',
        "conditional capture submenu actions",
    )
    more_settings_path.write_text(more, encoding="utf-8")


def patch_home_dashboard(path: Path) -> None:
    """Turn the inherited Firefox feed into Acute's local-first dashboard."""
    text = path.read_text(encoding="utf-8")

    header_start = '''            if (state is HomepageState.Normal) {
'''
    content_start = '''            if (state.firstFrameDrawn) {
'''
    acute_header = '''            // Acute owns the homepage hierarchy. Experimental news controls,
            // promotional banners and remote messaging are never rendered.
            HomepageHeader(
                browsingMode = state.browsingMode,
                browsingModeChanged = browsingModeChanged,
            )

'''
    text = replace_span_once(
        text,
        header_start,
        content_start,
        acute_header,
        "Acute homepage header",
    )

    animated_feed_start = '''                            LaunchedEffect(showLongfoxAnimation) {
'''
    shortcuts_start = '''                            if (topSiteState != null) {
'''
    text = replace_span_once(
        text,
        animated_feed_start,
        shortcuts_start,
        '''                            // Acute's dashboard begins with user-owned shortcuts.
''',
        "inherited homepage animation and feed entry point",
    )

    inherited_cards_start = '''                            if (showPrivacyReport) {
'''
    bookmarks_start = '''                            if (bookmarks != null) {
'''
    local_activity = '''                            // Resume is local-only. Synced-tab, setup,
                            // promotional and telemetry-backed cards are intentionally omitted.
                            if (recentTabs != null) {
                                RecentTabsSection(
                                    interactor = interactor,
                                    recentTabs = recentTabs,
                                    reducedTopSpacing = false,
                                )
                            }

'''
    text = replace_span_once(
        text,
        inherited_cards_start,
        bookmarks_start,
        local_activity,
        "inherited homepage cards",
    )

    remote_feed_start = '''                            if (pocketState != null) {
'''
    dialogs_start = '''                            when (shortcutsDialogState) {
'''
    local_shortcuts = '''                            Spacer(Modifier.height(bottomPadding.dp))

                            // Adding a shortcut never fetches a remote popular-sites list.
                            val popularSites = emptyList<PopularSite>()

'''
    text = replace_span_once(
        text,
        remote_feed_start,
        dialogs_start,
        local_shortcuts,
        "remote homepage feed",
    )

    path.write_text(text, encoding="utf-8")


def patch_large_screen_dashboard(path: Path) -> None:
    """Use an expanded two-column local dashboard when the window is wide enough."""
    text = path.read_text(encoding="utf-8")
    text = replace_once(
        text,
        "import androidx.compose.foundation.layout.Column\n",
        "import androidx.compose.foundation.layout.Column\n"
        "import androidx.compose.foundation.layout.Row\n",
        "dashboard row import",
    )
    text = replace_once(
        text,
        "import androidx.compose.foundation.layout.fillMaxSize\n",
        "import androidx.compose.foundation.layout.fillMaxSize\n"
        "import androidx.compose.foundation.layout.fillMaxWidth\n",
        "dashboard width import",
    )
    stacked_sections = '''                            if (bookmarks != null) {
                                BookmarksSection(
                                    bookmarks = bookmarks,
                                    interactor = interactor,
                                )
                            }

                            if (recentlyVisited != null) {
                                RecentlyVisitedSection(
                                    recentVisits = recentlyVisited,
                                    interactor = interactor,
                                )
                            }

                            CollectionsSection(
                                collectionsState = collectionsState,
                                interactor = interactor,
                                onCollectionsMigrationCardAction = onCollectionsMigrationCardAction,
                            )
'''
    adaptive_sections = '''                            // Expanded Android windows use their width for a real
                            // dashboard. Compact tablets and split windows retain phone flow.
                            val acuteExpandedDashboard = maxWidth >= 840.dp
                            if (acuteExpandedDashboard && (bookmarks != null || recentlyVisited != null)) {
                                Row(modifier = Modifier.fillMaxWidth()) {
                                    Column(modifier = Modifier.weight(1f)) {
                                        if (bookmarks != null) {
                                            BookmarksSection(
                                                bookmarks = bookmarks,
                                                interactor = interactor,
                                            )
                                        }

                                        if (recentlyVisited != null) {
                                            RecentlyVisitedSection(
                                                recentVisits = recentlyVisited,
                                                interactor = interactor,
                                            )
                                        }
                                    }

                                    Box(modifier = Modifier.weight(1f)) {
                                        CollectionsSection(
                                            collectionsState = collectionsState,
                                            interactor = interactor,
                                            onCollectionsMigrationCardAction =
                                                onCollectionsMigrationCardAction,
                                        )
                                    }
                                }
                            } else {
                                if (bookmarks != null) {
                                    BookmarksSection(
                                        bookmarks = bookmarks,
                                        interactor = interactor,
                                    )
                                }

                                if (recentlyVisited != null) {
                                    RecentlyVisitedSection(
                                        recentVisits = recentlyVisited,
                                        interactor = interactor,
                                    )
                                }

                                CollectionsSection(
                                    collectionsState = collectionsState,
                                    interactor = interactor,
                                    onCollectionsMigrationCardAction =
                                        onCollectionsMigrationCardAction,
                                )
                            }
'''
    text = replace_once(
        text,
        stacked_sections,
        adaptive_sections,
        "adaptive dashboard sections",
    )
    path.write_text(text, encoding="utf-8")


def patch_workspaces(homepage_path: Path, strings_path: Path, settings_path: Path) -> None:
    """Expose the maintained local tab-group model as Acute Workspaces."""
    homepage = homepage_path.read_text(encoding="utf-8")
    old_section = '''    when (collectionsState) {
        is CollectionsState.Content -> {
            CollectionsSectionContent {
                Collections(
                    collections = collectionsState.collections,
                    expandedCollections = collectionsState.expandedCollections,
                    showAddTabToCollection = collectionsState.showSaveTabsToCollection,
                    interactor = interactor,
                )
            }
        }

        CollectionsState.MigrationCard -> {
            CollectionsSectionContent {
                CollectionsMigrationPromoCard(onClick = { onCollectionsMigrationCardAction(ViewTabGroupsClicked) })
            }
        }

        CollectionsState.Gone -> {} // no-op. Nothing is shown where there are no collections.
    }
'''
    workspace_section = '''    // Acute Workspaces is backed by the maintained local tab-group store. The
    // dashboard entry remains available even before the first workspace exists.
    CollectionsSectionContent {
        CollectionsMigrationPromoCard(
            onClick = { onCollectionsMigrationCardAction(ViewTabGroupsClicked) },
        )
    }
'''
    homepage = replace_once(
        homepage,
        old_section,
        workspace_section,
        "workspace dashboard section",
    )
    homepage_path.write_text(homepage, encoding="utf-8")

    strings = strings_path.read_text(encoding="utf-8")
    for name, value in WORKSPACE_STRING_OVERRIDES.items():
        pattern = re.compile(
            rf'(<string\b[^>]*\bname="{re.escape(name)}"[^>]*>).*?(</string>)',
            flags=re.DOTALL,
        )
        strings, count = pattern.subn(
            lambda match, replacement=value: (
                f"{match.group(1)}{replacement}{match.group(2)}"
            ),
            strings,
            count=1,
        )
        if count != 1:
            raise OverlayError(f"Could not locate workspace string {name} in {strings_path}")

    for name, (one, other) in WORKSPACE_PLURAL_OVERRIDES.items():
        pattern = re.compile(
            rf'(<plurals\b[^>]*\bname="{re.escape(name)}"[^>]*>).*?(</plurals>)',
            flags=re.DOTALL,
        )
        replacement = (
            "\n      "
            f'<item quantity="one">{one}</item>\n'
            "      "
            f'<item quantity="other">{other}</item>\n    '
        )
        strings, count = pattern.subn(
            lambda match, body=replacement: f"{match.group(1)}{body}{match.group(2)}",
            strings,
            count=1,
        )
        if count != 1:
            raise OverlayError(f"Could not locate workspace plurals {name} in {strings_path}")

    strings_path.write_text(strings, encoding="utf-8")

    settings = settings_path.read_text(encoding="utf-8")
    settings = replace_once(
        settings,
        "            default = { DefaultTabManagementFeatureHelper.tabGroupsEnabled },\n",
        "            // Acute Workspaces is a first-class, local dashboard feature.\n"
        "            default = { true },\n",
        "workspace default",
    )
    settings = replace_once(
        settings,
        "            default = { DefaultTabManagementFeatureHelper.showTabGroupsInMenu },\n",
        "            // Keep the contextual Add to workspace command discoverable.\n"
        "            default = { true },\n",
        "workspace menu default",
    )
    settings_path.write_text(settings, encoding="utf-8")


def patch_workspace_suspension(middleware_path: Path, fragment_path: Path) -> None:
    """Release Gecko sessions when a workspace is closed, preserving restorable state."""
    middleware = middleware_path.read_text(encoding="utf-8")
    middleware = replace_once(
        middleware,
        "    private val mainScope: CoroutineScope = CoroutineScope(Dispatchers.Main),\n"
        ") : Middleware<TabsTrayState, TabsTrayAction> {\n",
        "    private val mainScope: CoroutineScope = CoroutineScope(Dispatchers.Main),\n"
        "    // Acute Workspaces releases Gecko resources without deleting tab state.\n"
        "    private val suspendTab: (String) -> Unit = {},\n"
        ") : Middleware<TabsTrayState, TabsTrayAction> {\n",
        "workspace suspension callback",
    )
    old_close = '''            is TabGroupAction.CloseTabGroupClicked -> {
                scope.launch {
                    tabGroupRepository.closeTabGroup(tabGroupId = action.group.id)
                }
            }
'''
    suspended_close = '''            is TabGroupAction.CloseTabGroupClicked -> {
                scope.launch {
                    // Persisted tab/group records remain intact. Suspending only unlinks and
                    // closes each live Gecko engine; selecting a tab recreates and restores it.
                    action.group.tabs.forEach { tab -> suspendTab(tab.id) }
                    tabGroupRepository.closeTabGroup(tabGroupId = action.group.id)
                }
            }
'''
    middleware = replace_once(
        middleware,
        old_close,
        suspended_close,
        "workspace close behavior",
    )
    middleware_path.write_text(middleware, encoding="utf-8")

    fragment = fragment_path.read_text(encoding="utf-8")
    fragment = replace_once(
        fragment,
        "import mozilla.components.browser.state.selector.privateTabs\n",
        "import mozilla.components.browser.state.action.EngineAction\n"
        "import mozilla.components.browser.state.selector.privateTabs\n",
        "workspace suspension engine action import",
    )
    fragment = replace_once(
        fragment,
        "                            fenixBrowserUseCases = requireComponents.useCases.fenixBrowserUseCases,\n"
        "                            mainScope = lifecycleScope,\n",
        "                            fenixBrowserUseCases = requireComponents.useCases.fenixBrowserUseCases,\n"
        "                            mainScope = lifecycleScope,\n"
        "                            suspendTab = { tabId ->\n"
        "                                requireComponents.core.store.dispatch(\n"
        "                                    EngineAction.SuspendEngineSessionAction(tabId),\n"
        "                                )\n"
        "                            },\n",
        "workspace suspension dispatch",
    )
    fragment_path.write_text(fragment, encoding="utf-8")


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


def patch_site_display(core: Path) -> None:
    """Install Acute's local per-site appearance and accessibility controls."""
    text = core.read_text(encoding="utf-8")
    anchor = '''                // Install the "icons" WebExtension to automatically load icons for every visited website.
                icons.install(engine, this)
'''
    install = '''                // Acute Site Display keeps per-domain appearance, text-size and motion
                // preferences locally. It does not contact a service or expose browsing data.
                engine.installBuiltInWebExtension(
                    id = "midnight-pages@acuteweb.core",
                    url = "resource://android/assets/extensions/acute-midnight/",
                )

'''
    text = replace_once(text, anchor, anchor + install, "Site Display extension hook")
    core.write_text(text, encoding="utf-8")


def patch_saved_sessions(core: Path) -> None:
    """Install Acute's local window-snapshot and restore feature."""
    text = core.read_text(encoding="utf-8")
    anchor = '''                // Install the "icons" WebExtension to automatically load icons for every visited website.
                icons.install(engine, this)
'''
    install = '''                // Saved Sessions stores named URL snapshots locally and restores them through
                // Gecko's maintained WebExtension tabs API. Private and internal tabs are excluded.
                engine.installBuiltInWebExtension(
                    id = "saved-sessions@acuteweb.core",
                    url = "resource://android/assets/extensions/acute-sessions/",
                )

'''
    text = replace_once(text, anchor, anchor + install, "Saved Sessions extension hook")
    core.write_text(text, encoding="utf-8")


def patch_page_notes(core: Path) -> None:
    """Install Acute's local page-addressed notes feature."""
    text = core.read_text(encoding="utf-8")
    anchor = '''                // Install the "icons" WebExtension to automatically load icons for every visited website.
                icons.install(engine, this)
'''
    install = '''                // Page Notes keeps bounded notes associated with normal web addresses in
                // extension-local storage. Private and internal pages are excluded.
                engine.installBuiltInWebExtension(
                    id = "page-notes@acuteweb.core",
                    url = "resource://android/assets/extensions/acute-notes/",
                )

'''
    text = replace_once(text, anchor, anchor + install, "Page Notes extension hook")
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
    home_activity = fenix / "app/src/main/java/org/mozilla/fenix/HomeActivity.kt"
    homepage = fenix / "app/src/main/java/org/mozilla/fenix/home/ui/Homepage.kt"
    main_menu = fenix / "app/src/main/java/org/mozilla/fenix/components/menu/compose/MainMenu.kt"
    menu_dialog = fenix / "app/src/main/java/org/mozilla/fenix/components/menu/MenuDialogFragment.kt"
    more_settings = (
        fenix
        / "app/src/main/java/org/mozilla/fenix/components/menu/compose/MoreSettingsSubmenu.kt"
    )
    tab_storage_middleware = (
        fenix
        / "app/src/main/java/org/mozilla/fenix/tabstray/redux/middleware/TabStorageMiddleware.kt"
    )
    tab_management_fragment = (
        fenix
        / "app/src/main/java/org/mozilla/fenix/tabstray/ui/TabManagementFragment.kt"
    )
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
    required = [gradle, manifest, release_manifest, beta_manifest, settings, home_activity, homepage, main_menu, menu_dialog, more_settings,
                tab_storage_middleware, tab_management_fragment, browser_toolbar,
                display_toolbar, edit_toolbar, toolbar_surface, browser_fragment,
                clipping_behavior, toolbar_behavior, onboarding,
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
    patch_desktop_shortcuts(home_activity)
    patch_dark_theme_default(settings)
    patch_midnight_palette(night_colors)
    patch_core_glass_toolbar(browser_toolbar)
    patch_core_glass_address_bar(display_toolbar, edit_toolbar)
    patch_core_glass_compositor(
        toolbar_surface,
        browser_fragment,
        clipping_behavior,
        toolbar_behavior,
    )
    patch_marketing_policy(settings, onboarding)
    patch_user_reporting(settings, preferences, search_providers)
    patch_branding_ui(fenix)
    patch_home_content_policy(settings)
    patch_home_dashboard(homepage)
    patch_large_screen_dashboard(homepage)
    patch_workspaces(homepage, values / "strings.xml", settings)
    patch_workspace_suspension(tab_storage_middleware, tab_management_fragment)
    patch_adaptive_menu(main_menu, menu_dialog)
    patch_capture_export_actions(main_menu, menu_dialog, more_settings)
    patch_about_page(about)
    patch_site_display(core)
    patch_saved_sessions(core)
    patch_page_notes(core)
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

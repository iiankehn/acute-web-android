#!/usr/bin/env python3
"""Check the complete overlay against real files from the immutable Firefox pin.

This is source compatibility validation, not an Android compilation or device test.
Only the files consumed by the overlay are downloaded; no Gecko build is started.
"""

from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import tomllib

from apply_overlay import (COMPOSE_BRAND_RASTERS, ERROR_PAGE_ARTWORK, ERROR_PAGE_LOCK, MASCOT_ARTWORK, ROOT,
                           SETTINGS_GROUPS, TAB_CRASHED_ARTWORK, apply)


FENIX_FILES = (
    "app/build.gradle",
    "app/src/main/AndroidManifest.xml",
    "app/src/release/AndroidManifest.xml",
    "app/src/beta/AndroidManifest.xml",
    "app/src/main/res/values/strings.xml",
    "app/src/main/res/values/static_strings.xml",
    "app/src/release/res/values/static_strings.xml",
    "app/src/beta/res/values/static_strings.xml",
    "app/src/main/res/values/colors.xml",
    "app/src/main/res/values-night/colors.xml",
    "app/src/main/res/color/private_mode_mask_gradient.xml",
    "app/src/main/res/values/styles.xml",
    "app/src/main/res/xml/preferences.xml",
    "app/src/main/res/xml/tracking_protection_preferences.xml",
    "app/src/main/res/xml/customization_preferences.xml",
    "app/src/main/res/layout/tracking_protection_learn_more_preference.xml",
    "app/src/main/res/layout/view_crash_reporter.xml",
    *(f"app/src/main/assets/{name}" for name in (
        "lowMediumErrorPages.js", "highRiskErrorPages.js", "shared_error_style.css",
        "low_and_medium_risk_error_style.css")),
    *(f"app/src/main/res/{path}" for path in MASCOT_ARTWORK),
    *(f"app/src/main/res/drawable/{name}.xml" for name in COMPOSE_BRAND_RASTERS),
    *(f"app/src/{source}/res/drawable/ic_firefox.xml" for source in ("beta", "debug", "nightly")),
    *(f"app/src/main/res/drawable/nova_onboarding_toolbar_{position}_{state}.xml"
      for position in ("top", "bottom") for state in ("active", "inactive")),
)
FENIX_KOTLIN = (
    "utils/Settings.kt",
    "HomeActivity.kt",
    "home/ui/Homepage.kt",
    "home/ui/WordmarkAndLogo.kt",
    "components/menu/compose/MainMenu.kt",
    "components/menu/compose/MenuNavigation.kt",
    "components/menu/MenuDialogFragment.kt",
    "components/menu/compose/MoreSettingsSubmenu.kt",
    "tabstray/redux/middleware/TabStorageMiddleware.kt",
    "tabstray/ui/TabManagementFragment.kt",
    "components/toolbar/BrowserToolbarComposable.kt",
    "components/toolbar/BrowserToolbarMiddleware.kt",
    "browser/BaseBrowserFragment.kt",
    "browser/BrowserFragment.kt",
    "browser/NativeShareSheetContextMenuCandidate.kt",
    "browser/desktopmode/DesktopModeRepository.kt",
    "onboarding/OnboardingFragment.kt",
    "onboarding/OnboardingTelemetryRecorder.kt",
    "onboarding/view/OnboardingPageUiData.kt",
    "onboarding/view/OnboardingMapper.kt",
    "onboarding/view/OnboardingScreen.kt",
    "onboarding/view/TermsOfServiceOnboardingPage.kt",
    "components/SettingsSearchProviders.kt",
    "components/Core.kt",
    "components/Analytics.kt",
    "components/GleanHelper.kt",
    "settings/about/AboutFragment.kt",
    "settings/CustomizationFragment.kt",
    "settings/deletebrowsingdata/DeleteBrowsingDataFragment.kt",
    "theme/FirefoxTheme.kt",
)
COMPONENT_FILES = (
    "lib/crash/src/main/java/mozilla/components/lib/crash/CrashReporter.kt",
    "compose/browser-toolbar/src/main/java/mozilla/components/compose/browser/toolbar/ui/FullDisplayToolbar.kt",
    "compose/browser-toolbar/src/main/java/mozilla/components/compose/browser/toolbar/BrowserEditToolbar.kt",
    "compose/browser-toolbar/src/main/java/mozilla/components/compose/browser/toolbar/BrowserToolbar.kt",
    "ui/widgets/src/main/java/mozilla/components/ui/widgets/behavior/EngineViewClippingBehavior.kt",
    "feature/toolbar/src/main/java/mozilla/components/feature/toolbar/ToolbarBehaviorController.kt",
    "feature/contextmenu/src/main/java/mozilla/components/feature/contextmenu/ContextMenuCandidate.kt",
)


# MainMenu parameters Acute deliberately stops reading. The default-browser
# promotion banner is not shown, and the grouped navigation section no longer
# moves with toolbar position. Every other upstream menu input must stay wired.
INTENTIONALLY_UNUSED_MENU_INPUTS = frozenset({
    "showBanner", "onBannerClick", "onBannerDismiss",
    "isBottomToolbar", "isExpandedToolbarEnabled",
})


def validate_menu_continuity(original: str, transformed: str) -> None:
    """Fail when regrouping the main menu drops an upstream action or label."""
    def main_menu(text: str) -> tuple[list[str], str]:
        start = text.index("fun MainMenu(")
        signature_end = text.index(") {", start)
        body_end = text.index("\n@Composable", signature_end)
        parameters = re.findall(r"^\s+(\w+): ", text[start:signature_end], re.MULTILINE)
        return parameters, text[signature_end:body_end]

    parameters, original_body = main_menu(original)
    transformed_parameters, transformed_body = main_menu(transformed)
    assert transformed_parameters == parameters, "MainMenu signature changed"
    used = lambda name, body: re.search(rf"\b{name}\b", body) is not None
    dropped = sorted(
        name for name in parameters
        if used(name, original_body) and not used(name, transformed_body)
        and name not in INTENTIONALLY_UNUSED_MENU_INPUTS
    )
    assert not dropped, "Main menu no longer uses upstream inputs: " + ", ".join(dropped)
    wiring = lambda text: set(re.findall(r"\b(on\w+) = (on\w+)\b", text))
    missing_wiring = sorted(wiring(original) - wiring(transformed))
    assert not missing_wiring, f"Main menu handlers are no longer wired: {missing_wiring}"
    strings = lambda text: set(re.findall(r"R\.string\.(\w+)", text))
    missing_labels = sorted(strings(original) - strings(transformed))
    assert not missing_labels, f"Main menu labels disappeared: {missing_labels}"


def validate_settings_and_artwork(source: Path, checkout: Path) -> None:
    """Settings keep every upstream entry; Compose-drawn brand art is raster-only."""
    import xml.etree.ElementTree as ET
    android = "{http://schemas.android.com/apk/res/android}"
    relative = "mobile/android/fenix/app/src/main/res/xml/preferences.xml"
    def keys(root):
        return sorted(e.get(android + "key") for e in root.iter() if e.get(android + "key"))
    original = ET.parse(source / relative).getroot()
    transformed = ET.parse(checkout / relative).getroot()
    expected = keys(original)
    expected.remove("@string/pref_key_data_choices")
    expected.append("acute_report_issue")
    expected.append("acute_private_by_default")
    assert keys(transformed) == sorted(expected), "Settings entries were lost or duplicated"
    titles = [c.get(android + "title") for c in transformed if c.tag.endswith("PreferenceCategory")]
    assert titles[1:] == [title for title, _, _ in SETTINGS_GROUPS], titles
    res = checkout / "mobile/android/fenix/app/src"
    for name in COMPOSE_BRAND_RASTERS:
        assert (res / f"main/res/drawable-nodpi/{name}.png").is_file(), name
        assert not list(res.glob(f"*/res/drawable*/{name}.xml")), name
    for relative in MASCOT_ARTWORK:
        name = Path(relative).stem
        assert [p.name for p in res.glob(f"*/res/drawable*/{name}.*")] == [f"{name}.png"], name
    assets = res / "main/assets"
    for image in {*ERROR_PAGE_ARTWORK.values(), *ERROR_PAGE_LOCK}:
        assert (assets / image).is_file(), image
    for script in ("lowMediumErrorPages.js", "highRiskErrorPages.js"):
        assert "acuteErrorImage(queryMap);" in (assets / script).read_text(encoding="utf-8"), script
    crash_layout = (res / "main/res/layout/view_crash_reporter.xml").read_text(encoding="utf-8")
    assert f"@drawable/{TAB_CRASHED_ARTWORK}" in crash_layout
    assert (res / f"main/res/drawable-nodpi/{TAB_CRASHED_ARTWORK}.png").is_file()
    drawable = res / "main/res/drawable"
    for position in ("top", "bottom"):
        assert (drawable / f"nova_onboarding_toolbar_{position}_active.xml").read_bytes() == (
            drawable / f"nova_onboarding_toolbar_{position}_inactive.xml").read_bytes()


def validate_output(source: Path, checkout: Path, channel: str) -> None:
    """Validate security and viewport invariants on real transformed upstream files."""
    import xml.etree.ElementTree as ET
    app = checkout / "mobile/android/fenix/app"
    gradle = (app / "build.gradle").read_text()
    package = "com.acuteweb.browser.dev" if channel == "dev" else "com.acuteweb.browser"
    assert f'applicationId "{package}"' in gradle
    assert "minSdk 31" in gradle
    release_template = gradle.split("def releaseTemplate = {", 1)[1].split("    buildTypes {", 1)[0]
    assert "debuggable false" in release_template
    assert "MOZ_ANDROID_DEBUGGABLE" not in release_template
    assert "'TELEMETRY', 'true'" not in gradle
    assert "'CRASH_REPORTING', 'true'" not in gradle
    manifest = ET.parse(app / "src/main/AndroidManifest.xml").getroot()
    android = "{http://schemas.android.com/apk/res/android}"
    application = manifest.find("application")
    assert application.get(android + "allowBackup") == "false"
    tools = "{http://schemas.android.com/tools}"
    for provider in application.findall("provider"):
        if provider.get(tools + "node") == "remove":
            assert provider.get(android + "name") == "com.adjust.sdk.SystemLifecycleContentProvider"
            continue
        assert provider.get(android + "exported") == "false"
        assert provider.get(android + "authorities", "").startswith("${applicationId}.")
    from verify_apk_badging import DENIED_PERMISSIONS
    for tag in ("uses-permission", "uses-permission-sdk-23"):
        for name in DENIED_PERMISSIONS:
            markers = [p for p in manifest.findall(tag) if p.get(android + "name") == name]
            assert len(markers) == 1 and markers[0].get(tools + "node") == "remove"
    receiver = [r for r in application.findall("receiver") if r.get(android + "name") == "com.adjust.sdk.AdjustPreinstallReferrerReceiver"]
    assert len(receiver) == 1 and receiver[0].get(tools + "node") == "remove"
    removed_providers = [p for p in application.findall("provider") if p.get(android + "name") == "com.adjust.sdk.SystemLifecycleContentProvider"]
    assert len(removed_providers) == 1 and removed_providers[0].get(tools + "node") == "remove"
    debug_activities = [a for a in application.findall("activity") if a.get(android + "name") == "mozilla.telemetry.glean.debug.GleanDebugActivity"]
    assert len(debug_activities) == 1 and debug_activities[0].get(tools + "node") == "remove"
    code = app / "src/main/java/org/mozilla/fenix"
    menu = "components/menu/compose/MainMenu.kt"
    validate_menu_continuity(
        (source / "mobile/android/fenix/app/src/main/java/org/mozilla/fenix" / menu).read_text(),
        (code / menu).read_text(),
    )
    # MenuNavigation renders inside MenuFrame's scrolling body; a second
    # vertical scroll there crashes the menu on every web page.
    assert "verticalScroll" not in (code / "components/menu/compose/MenuNavigation.kt").read_text()
    validate_private_by_default(app, code)
    terms = (code / "onboarding/view/TermsOfServiceOnboardingPage.kt").read_text()
    body = terms[terms.index("private fun BodyText("):terms.index("private fun BodyLinkText(")]
    assert "onManagePrivacyPreferencesLinkClicked" not in body
    assert "lineOneText" not in body and "lineThreeText" not in body
    assert "R.string.acute_onboarding_privacy_line" in body
    validate_settings_and_artwork(source, checkout)
    reports = [a for a in application.findall("activity")
               if a.get(android + "name") == "org.mozilla.fenix.acute.ReportIssueActivity"]
    assert len(reports) == 1 and reports[0].get(android + "exported") == "false"
    issue = ET.parse(app / "src/main/res/xml/preferences.xml").getroot()
    entry = next(p for p in issue.iter() if p.get(android + "key") == "acute_report_issue")
    intent = entry.find("intent")
    expected_package = "com.acuteweb.browser" + ("" if channel == "stable" else "." + channel)
    assert intent.get(android + "targetPackage") == expected_package
    assert intent.get(android + "targetClass") == "org.mozilla.fenix.acute.ReportIssueActivity"
    assert "ReportIssueActivity::class.java" in (code / "settings/about/AboutFragment.kt").read_text()

    home = (code / "HomeActivity.kt").read_text()
    assert home.count("import org.mozilla.fenix.browser.BrowserFragmentDirections\n") == 1
    # Exact source anchors can apply successfully while introducing Kotlin
    # compiler errors. Catch duplicate imports in every transformed source.
    for kotlin in checkout.rglob("*.kt"):
        imports = re.findall(r"^import .+$", kotlin.read_text(), re.MULTILINE)
        assert len(imports) == len(set(imports)), f"Duplicate imports: {kotlin}"
    assert home.count("BrowserFragmentDirections.actionGlobalHome(") >= 2
    settings = (code / "utils/Settings.kt").read_text()
    assert "    var continuousOnboardingFeatureEnabled: Boolean\n        get() = false\n" in settings
    for name in ("isTelemetryEnabled", "isDailyUsagePingEnabled", "isExperimentationEnabled", "isRolloutsEnabled"):
        assert f"var {name}: Boolean\n        get() = false" in settings
    analytics = (code / "components/Analytics.kt").read_text()
    assert "services = emptyList()," in analytics
    assert "telemetryServices = emptyList()," in analytics
    assert "            enabled = false," in analytics
    glean = (code / "components/GleanHelper.kt").read_text()
    assert "Glean.initialize(" not in glean
    assert "ConceptFetchHttpUploader(" not in glean
    assert "Glean.registerPings(" not in glean
    crash = (checkout / "mobile/android/android-components/components/lib/crash/src/main/java/mozilla/components/lib/crash/CrashReporter.kt").read_text()
    assert "require(!enabled || services.isNotEmpty() || telemetryServices.isNotEmpty())" in crash
    for relative in (
        "mobile/android/fenix/app/src/main/java/org/mozilla/fenix/browser/BaseBrowserFragment.kt",
        "mobile/android/fenix/app/src/main/java/org/mozilla/fenix/components/toolbar/BrowserToolbarComposable.kt",
        "mobile/android/android-components/components/compose/browser-toolbar/src/main/java/mozilla/components/compose/browser/toolbar/BrowserToolbar.kt",
        "mobile/android/android-components/components/ui/widgets/src/main/java/mozilla/components/ui/widgets/behavior/EngineViewClippingBehavior.kt",
        "mobile/android/android-components/components/feature/toolbar/src/main/java/mozilla/components/feature/toolbar/ToolbarBehaviorController.kt",
    ):
        assert (source / relative).read_bytes() == (checkout / relative).read_bytes(), relative
    for xml in app.rglob("*.xml"):
        ET.parse(xml)


def validate_private_by_default(app: Path, code: Path) -> None:
    """Strict, HTTPS-Only and GPC defaults agree in code and XML, and onboarding announces them."""
    import xml.etree.ElementTree as ET
    settings = (code / "utils/Settings.kt").read_text()
    for key, default in (
        ("pref_key_https_only", "default = true"),
        ("pref_key_privacy_enable_global_privacy_control", "true"),
        ("pref_key_tracking_protection_standard_option", "false"),
        ("pref_key_tracking_protection_strict_default", "true"),
    ):
        assert f"R.string.{key}),\n            {default}," in settings, key
    xml = ET.parse(app / "src/main/res/xml/tracking_protection_preferences.xml").getroot()
    android = "{http://schemas.android.com/apk/res/android}"
    defaults = {node.get(android + "key"): node.get(android + "defaultValue") for node in xml.iter()}
    assert defaults["@string/pref_key_tracking_protection_standard_option"] == "false"
    assert defaults["@string/pref_key_tracking_protection_strict_default"] == "true"
    assert defaults["@string/pref_key_privacy_enable_global_privacy_control"] == "true"
    titles = {node.get(android + "key"): node.get(android + "title") for node in xml.iter()}
    assert titles["@string/pref_key_tracking_protection_standard_option"] == "@string/tracking_protection_standard"
    assert titles["@string/pref_key_tracking_protection_strict_default"] == "@string/acute_tracking_protection_strict_default"
    preferences = (app / "src/main/res/xml/preferences.xml").read_text()
    assert preferences.count('android:key="acute_private_by_default"') == 1
    fragment = (code / "onboarding/OnboardingFragment.kt").read_text()
    assert ".withPrivateByDefaultPage()" in fragment
    screen = (code / "onboarding/view/OnboardingScreen.kt").read_text()
    assert screen.count("onPrivateByDefaultContinueClick") == 4


def fetch_source(source: Path, repository: str, ref: str, paths: list[str]) -> None:
    """Fetch one immutable sparse Git snapshot instead of many raw-file requests."""
    if not re.fullmatch(r"[0-9a-f]{40}", ref):
        raise ValueError("Upstream validation requires an immutable Firefox commit")
    subprocess.run(["git", "init", "--quiet", str(source)], check=True)
    def git(*arguments, **kwargs):
        return subprocess.run(["git", "-C", str(source), *arguments], check=True, timeout=300, **kwargs)
    git("remote", "add", "origin", repository)
    git("config", "core.sparseCheckout", "true")
    sparse = source / ".git/info/sparse-checkout"
    sparse.write_text("".join("/" + path + "\n" for path in paths))
    git("fetch", "--quiet", "--depth=1", "--filter=blob:none", "origin", ref)
    fetched = git("rev-parse", "FETCH_HEAD", capture_output=True, text=True).stdout.strip()
    if fetched != ref:
        raise ValueError("Fetched Firefox commit does not match the immutable pin")
    git("checkout", "--quiet", "--detach", "FETCH_HEAD")
    missing = [path for path in paths if not (source / path).is_file()]
    if missing:
        raise ValueError("Sparse upstream snapshot is incomplete: " + ", ".join(missing))


def main() -> int:
    config = tomllib.loads((ROOT / "acute-android.toml").read_text())
    ref = config["upstream"]["ref"]
    if not re.fullmatch(r"[0-9a-f]{40}", ref):
        raise ValueError("Upstream validation requires an immutable Firefox commit")
    paths = ["mach"]
    paths += ["mobile/android/fenix/" + path for path in FENIX_FILES]
    paths += [
        "mobile/android/fenix/app/src/main/java/org/mozilla/fenix/" + path
        for path in FENIX_KOTLIN
    ]
    paths += [
        "mobile/android/android-components/components/" + path
        for path in COMPONENT_FILES
    ]
    with tempfile.TemporaryDirectory(prefix="acute-upstream-") as directory:
        root = Path(directory)
        source = root / "source"

        fetch_source(source, config["upstream"]["repository"], ref, paths)
        for channel in ("stable", "beta", "dev"):
            checkout = root / channel
            shutil.copytree(source, checkout, ignore=shutil.ignore_patterns(".git"))
            apply(checkout, channel=channel)
            validate_output(source, checkout, channel)
            print(f"Complete {channel} overlay matches Firefox {ref}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

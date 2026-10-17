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

from apply_overlay import ROOT, apply


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
    "app/src/main/res/values/styles.xml",
    "app/src/main/res/xml/preferences.xml",
    "app/src/main/res/xml/customization_preferences.xml",
)
FENIX_KOTLIN = (
    "utils/Settings.kt",
    "HomeActivity.kt",
    "home/ui/Homepage.kt",
    "home/ui/WordmarkAndLogo.kt",
    "components/menu/compose/MainMenu.kt",
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
    "components/SettingsSearchProviders.kt",
    "components/Core.kt",
    "components/Analytics.kt",
    "settings/about/AboutFragment.kt",
    "settings/CustomizationFragment.kt",
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
    home = (code / "HomeActivity.kt").read_text()
    assert home.count("import org.mozilla.fenix.browser.BrowserFragmentDirections\n") == 1
    # Exact source anchors can apply successfully while introducing Kotlin
    # compiler errors. Catch duplicate imports in every transformed source.
    for kotlin in checkout.rglob("*.kt"):
        imports = re.findall(r"^import .+$", kotlin.read_text(), re.MULTILINE)
        assert len(imports) == len(set(imports)), f"Duplicate imports: {kotlin}"
    assert home.count("BrowserFragmentDirections.actionGlobalHome(") >= 2
    settings = (code / "utils/Settings.kt").read_text()
    for name in ("isTelemetryEnabled", "isDailyUsagePingEnabled", "isExperimentationEnabled", "isRolloutsEnabled"):
        assert f"var {name}: Boolean\n        get() = false" in settings
    analytics = (code / "components/Analytics.kt").read_text()
    assert "services = emptyList()," in analytics
    assert "telemetryServices = emptyList()," in analytics
    assert "            enabled = false," in analytics
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

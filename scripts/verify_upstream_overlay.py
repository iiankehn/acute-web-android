#!/usr/bin/env python3
"""Check the complete overlay against real files from the immutable Firefox pin.

This is source compatibility validation, not an Android compilation or device test.
Only the files consumed by the overlay are downloaded; no Gecko build is started.
"""

from concurrent.futures import ThreadPoolExecutor
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
    "home/ui/Wordmark.kt",
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
    assert "'TELEMETRY', 'true'" not in gradle
    assert "'CRASH_REPORTING', 'true'" not in gradle
    assert "AdjustPreinstallReferrerReceiver" not in (app / "src/main/AndroidManifest.xml").read_text()
    manifest = ET.parse(app / "src/main/AndroidManifest.xml").getroot()
    android = "{http://schemas.android.com/apk/res/android}"
    application = manifest.find("application")
    assert application.get(android + "allowBackup") == "false"
    for provider in application.findall("provider"):
        assert provider.get(android + "exported") == "false"
        assert provider.get(android + "authorities", "").startswith("${applicationId}.")
    for permission in manifest.findall("uses-permission") + manifest.findall("uses-permission-sdk-23"):
        assert permission.get(android + "name") not in {
            "com.adjust.preinstall.READ_PERMISSION", "com.google.android.gms.permission.AD_ID",
            "android.permission.QUERY_ALL_PACKAGES", "android.permission.REQUEST_DELETE_PACKAGES",
            "android.permission.REQUEST_INSTALL_PACKAGES",
        }
    code = app / "src/main/java/org/mozilla/fenix"
    settings = (code / "utils/Settings.kt").read_text()
    for name in ("isTelemetryEnabled", "isDailyUsagePingEnabled", "isExperimentationEnabled", "isRolloutsEnabled"):
        assert f"var {name}: Boolean\n        get() = false" in settings
    analytics = (code / "components/Analytics.kt").read_text()
    assert "services = emptyList()," in analytics
    assert "telemetryServices = emptyList()," in analytics
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

        def fetch(path: str) -> None:
            destination = source / path
            destination.parent.mkdir(parents=True, exist_ok=True)
            url = f"https://raw.githubusercontent.com/mozilla-firefox/firefox/{ref}/{path}"
            subprocess.run(
                ["curl", "--fail", "--silent", "--show-error", "--location",
                 "--retry", "2", "--max-time", "60", url, "--output", str(destination)],
                check=True,
            )

        with ThreadPoolExecutor(max_workers=8) as pool:
            list(pool.map(fetch, paths))
        for channel in ("stable", "beta", "dev"):
            checkout = root / channel
            shutil.copytree(source, checkout)
            apply(checkout, channel=channel)
            validate_output(source, checkout, channel)
            print(f"Complete {channel} overlay matches Firefox {ref}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

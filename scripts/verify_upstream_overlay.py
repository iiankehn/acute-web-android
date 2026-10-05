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
    "browser/BaseBrowserFragment.kt",
    "browser/BrowserFragment.kt",
    "browser/NativeShareSheetContextMenuCandidate.kt",
    "browser/desktopmode/DesktopModeRepository.kt",
    "onboarding/OnboardingFragment.kt",
    "components/SettingsSearchProviders.kt",
    "components/Core.kt",
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
        for channel in ("stable", "beta"):
            checkout = root / channel
            shutil.copytree(source, checkout)
            apply(checkout, channel=channel)
            print(f"Complete {channel} overlay matches Firefox {ref}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

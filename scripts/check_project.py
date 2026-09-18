#!/usr/bin/env python3
"""Fast repository checks which do not require a Firefox checkout."""

from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
REQUIRED = [
    ".github/workflows/build-android.yml",
    ".github/workflows/validate.yml",
    "acute-android.toml",
    "overlay/kotlin/GitHubUpdateProvider.kt",
    "scripts/apply_overlay.py",
    "docs/SIGNING.md",
    "docs/TABLET_SUPPORT.md",
    "scripts/tablet_smoke.sh",
]


def main() -> int:
    missing = [name for name in REQUIRED if not (ROOT / name).is_file()]
    if missing:
        print("Missing required files: " + ", ".join(missing), file=sys.stderr)
        return 1
    updater = (ROOT / "overlay/kotlin/GitHubUpdateProvider.kt").read_text()
    expected = "https://api.github.com/repos/iiankehn/acute-web-android/releases/latest"
    if expected not in updater:
        print("Updater repository URL is incorrect", file=sys.stderr)
        return 1
    if "REQUEST_INSTALL_PACKAGES" in (ROOT / "scripts/apply_overlay.py").read_text():
        print("Overlay must not request silent package installation", file=sys.stderr)
        return 1
    overlay = (ROOT / "scripts/apply_overlay.py").read_text()
    for requirement in ("patch_tablet_defaults", "android.hardware.touchscreen", "validate_tablet_upstream"):
        if requirement not in overlay:
            print(f"Missing tablet requirement: {requirement}", file=sys.stderr)
            return 1
    print("Project checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

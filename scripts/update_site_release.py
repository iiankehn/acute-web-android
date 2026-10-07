#!/usr/bin/env python3
"""Update the static Acute website from a trusted GitHub release event."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from urllib.parse import urlparse


REPOSITORY = "iiankehn/acute-web-android"
STABLE_TAG = re.compile(r"^v(?P<version>\d+\.\d+\.\d+)$")
BETA_TAG = re.compile(r"^v(?P<version>\d+\.\d+\.\d+-beta\.\d+)$")


def replace_marked_href(html: str, channel: str, url: str) -> str:
    pattern = re.compile(
        rf'(<a\b(?=[^>]*\bdata-release-link="{channel}")[^>]*\bhref=")[^"]*(")'
    )
    updated, count = pattern.subn(rf"\g<1>{url}\g<2>", html)
    if count == 0:
        raise ValueError(f"No {channel} release links were found in the website")
    return updated


def replace_marked_text(html: str, marker: str, value: str) -> str:
    pattern = re.compile(
        rf'(<(?P<tag>[a-z0-9]+)\b(?=[^>]*\bdata-release-version="{marker}")[^>]*>).*?(</(?P=tag)>)',
        re.IGNORECASE | re.DOTALL,
    )
    updated, count = pattern.subn(rf"\g<1>{value}\g<3>", html)
    if count == 0:
        raise ValueError(f"No {marker} version labels were found in the website")
    return updated


def release_details(payload: dict) -> tuple[str, str, str, str]:
    release = payload.get("release") or {}
    repository = (payload.get("repository") or {}).get("full_name")
    if repository != REPOSITORY:
        raise ValueError(f"Unexpected repository: {repository!r}")

    if release.get("draft"):
        raise ValueError("Draft releases cannot update the public website")

    tag = release.get("tag_name", "")
    prerelease = bool(release.get("prerelease"))
    match = (BETA_TAG if prerelease else STABLE_TAG).fullmatch(tag)
    if not match:
        kind = "Beta" if prerelease else "Stable"
        raise ValueError(f"{kind} release tag has an invalid format: {tag!r}")

    version = match.group("version")
    channel = "beta" if prerelease else "stable"
    expected_name = f"acute-web-{version}-arm64-v8a.apk"
    candidates = [asset for asset in release.get("assets", []) if asset.get("name") == expected_name]
    if len(candidates) != 1:
        raise ValueError(f"Release must contain exactly one {expected_name}")

    asset = candidates[0]
    if not isinstance(asset.get("size"), int) or asset["size"] <= 0:
        raise ValueError(f"Release asset {expected_name} is empty")

    download_url = asset.get("browser_download_url", "")
    parsed = urlparse(download_url)
    expected_path = f"/{REPOSITORY}/releases/download/{tag}/{expected_name}"
    if parsed.scheme != "https" or parsed.netloc != "github.com" or parsed.path != expected_path:
        raise ValueError("Release APK download URL is not an official Acute GitHub asset")

    return channel, version, tag, download_url


def update_site(payload: dict, html_path: Path) -> bool:
    channel, version, _tag, download_url = release_details(payload)
    html = html_path.read_text(encoding="utf-8")
    original_html = html
    if channel == "beta" and 'data-release-link="beta"' not in html:
        # Show a beta option only after an actual signed beta is published.
        slot = "<!-- beta-release:start --><!-- beta-release:end -->"
        if slot not in html:
            raise ValueError("No beta release slot was found in the website")
        html = html.replace(slot, (
            '<!-- beta-release:start --><p class="beta-release">'
            f'<a data-release-link="beta" href="{download_url}">Try Acute Beta '
            f'<span data-release-version="beta">{version}</span></a>'
            ' · Early access; may be unstable.</p><!-- beta-release:end -->'
        ))
    updated = replace_marked_href(html, channel, download_url)
    updated = replace_marked_text(updated, channel, version)

    if channel == "stable":
        major_minor = ".".join(version.split(".")[:2])
        updated = replace_marked_text(updated, "stable-short", major_minor)

    if updated == original_html:
        return False
    html_path.write_text(updated, encoding="utf-8")
    return True


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--event", type=Path, required=True)
    parser.add_argument("--html", type=Path, default=Path("docs/index.html"))
    args = parser.parse_args()

    payload = json.loads(args.event.read_text(encoding="utf-8"))
    changed = update_site(payload, args.html)
    print("Website release metadata updated." if changed else "Website already matches this release.")


if __name__ == "__main__":
    main()

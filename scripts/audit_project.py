#!/usr/bin/env python3
"""Fail-closed security and release-readiness checks for Acute-owned source."""

from __future__ import annotations

import json
from pathlib import Path
import re
import sys
import tomllib
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = ROOT / ".github/workflows"


def fail(message: str) -> None:
    print(f"AUDIT FAILURE: {message}", file=sys.stderr)
    raise SystemExit(1)


def tracked_files(*suffixes: str):
    excluded = {".git", "__pycache__"}
    for path in ROOT.rglob("*"):
        if path.is_file() and not excluded.intersection(path.parts):
            if not suffixes or path.suffix in suffixes:
                yield path


def validate_structured_files() -> None:
    for path in tracked_files(".json"):
        try:
            json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as error:
            fail(f"invalid JSON in {path.relative_to(ROOT)}: {error}")
    for path in tracked_files(".xml"):
        try:
            ET.parse(path)
        except (OSError, ET.ParseError) as error:
            fail(f"invalid XML in {path.relative_to(ROOT)}: {error}")


def validate_configuration() -> None:
    config = tomllib.loads((ROOT / "acute-android.toml").read_text(encoding="utf-8"))
    stable = config["channels"]["stable"]["application_id"]
    beta = config["channels"]["beta"]["application_id"]
    if stable == beta:
        fail("Stable and Beta application IDs must remain distinct")

    workflow = (WORKFLOWS / "build-android.yml").read_text(encoding="utf-8")
    website = (ROOT / "docs/index.html").read_text(encoding="utf-8")
    candidate = config["release"]["candidate"]
    upstream_ref = config["upstream"]["ref"]
    if workflow.count(upstream_ref) < 2:
        fail("workflow and project configuration disagree on the Firefox pin")
    for target in ("aarch64-linux-android", "x86_64-linux-android"):
        if target not in workflow:
            fail(f"missing native Android build target: {target}")
    for abi in ("arm64-v8a", "x86_64"):
        if f"abi: {abi}" not in workflow:
            fail(f"missing native Android ABI: {abi}")
    for library in ("libmozglue.so", "libxul.so"):
        if f'grep -qx "lib/$ABI/{library}"' not in workflow:
            fail(f"workflow does not verify Gecko library: {library}")
    if "needs: audit" not in workflow:
        fail("APK build is not gated by the repository audit")
    if 'ACUTE_TARGET_ABI: ${{ matrix.abi }}' not in workflow:
        fail("APK packaging is not constrained to the Gecko artifact ABI")
    if 'python3 acute-overlay/scripts/verify_apk_native.py "$apk" "$ABI"' not in workflow:
        fail("APK build does not reject partial foreign native architectures")
    if f"version={candidate}" not in workflow:
        fail("workflow and project configuration disagree on the release candidate")
    # The website may hide Beta downloads until a Beta is published. A build
    # candidate is not a published release and must not gate Stable fixes.
    if 'data-release-version="beta"' in website and not re.search(
        r'data-release-version="beta">\d+\.\d+\.\d+-beta\.\d+', website
    ):
        fail("website Beta version metadata is malformed")


def validate_action_pinning() -> None:
    action = re.compile(r"^\s*uses:\s*([^\s#]+)", re.MULTILINE)
    immutable = re.compile(r"^[^@]+@[0-9a-f]{40}$")
    for path in WORKFLOWS.glob("*.yml"):
        for reference in action.findall(path.read_text(encoding="utf-8")):
            if not immutable.fullmatch(reference):
                fail(f"mutable action reference in {path.relative_to(ROOT)}: {reference}")


def validate_security_invariants() -> None:
    overlay = (ROOT / "scripts/apply_overlay.py").read_text(encoding="utf-8")
    updater = (ROOT / "overlay/kotlin/GitHubUpdateProvider.kt").read_text(encoding="utf-8")
    required = (
        'android:authorities="${applicationId}.acute-updates"',
        'android:exported="false"',
        'applicationId "com.acuteweb.browser"',
        'applicationIdSuffix ".beta"',
    )
    for marker in required:
        if marker not in overlay:
            fail(f"missing Android isolation invariant: {marker}")
    if 'uri.scheme == "https"' not in updater or 'uri.host == "github.com"' not in updater:
        fail("updater download origin is not constrained to HTTPS GitHub URLs")

    forbidden_flags = ("android:debuggable=\"true\"", "android:testOnly=\"true\"",
                       "android:usesCleartextTraffic=\"true\"")
    forbidden_endpoints = ("http://localhost", "http://127.0.0.1", "http://10.0.2.2")
    secret_markers = ("-----BEGIN PRIVATE KEY-----", "-----BEGIN ENCRYPTED PRIVATE KEY-----")
    for path in tracked_files(".py", ".kt", ".kts", ".gradle", ".xml", ".yml", ".yaml", ".toml"):
        if path == Path(__file__) or "tests" in path.parts:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for marker in (*forbidden_flags, *forbidden_endpoints, *secret_markers):
            if marker in text:
                fail(f"forbidden release marker in {path.relative_to(ROOT)}: {marker}")


def main() -> int:
    validate_structured_files()
    validate_configuration()
    validate_action_pinning()
    validate_security_invariants()
    print("Security and release-readiness audit passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

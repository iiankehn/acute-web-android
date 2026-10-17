#!/usr/bin/env python3
"""Check backup and updater boundaries in the dependency-merged APK manifest.

This is a targeted merger regression gate, not a general manifest security audit.
"""

import argparse
from pathlib import Path
import re

DENIED_COMPONENTS = (
    "com.adjust.sdk.SystemLifecycleContentProvider",
    "com.adjust.sdk.AdjustPreinstallReferrerReceiver",
)


def elements(text):
    """Read direct attributes without confusing child metadata with its parent."""
    stack = []
    result = []
    for line in text.splitlines():
        match = re.match(r"^(\s*)E: ([\w.-]+)(?:\s|$)", line)
        if match:
            depth = len(match[1])
            while stack and stack[-1][0] >= depth:
                stack.pop()
            node = {"tag": match[2], "attrs": {}, "children": []}
            if stack:
                stack[-1][1]["children"].append(node)
            else:
                result.append(node)
            stack.append((depth, node))
            continue
        match = re.match(r"^(\s*)A: ([\w:.-]+)(?:\(0x[0-9a-fA-F]+\))?=(.*)$", line)
        if match and stack:
            if len(match[1]) <= stack[-1][0]:
                raise ValueError("Malformed compiled manifest attribute indentation")
            attrs = stack[-1][1]["attrs"]
            if match[2] in attrs:
                raise ValueError("Duplicate compiled manifest attribute")
            attrs[match[2]] = match[3].strip()
    return result


def string_value(value):
    match = re.fullmatch(r'"([^"\n]*)"(?:\s+\(Raw: "[^"\n]*"\))?', value or "")
    return match[1] if match else None


def is_false(value):
    return bool(re.fullmatch(r"\(type 0x12\)0x0+", value or ""))


def verify(text):
    for element in ("manifest", "application"):
        if not re.search(rf"^\s*E: {element}(?:\s|$)", text, re.MULTILINE):
            raise ValueError(f"Missing compiled {element} element; expected aapt2 dump xmltree output")
    found = [name for name in DENIED_COMPONENTS if name in text]
    if found:
        raise ValueError("Prohibited attribution components: " + ", ".join(found))
    roots = elements(text)
    if len(roots) != 1 or roots[0]["tag"] != "manifest":
        raise ValueError("Expected one compiled manifest root")
    manifest = roots[0]
    if "android:sharedUserId" in manifest["attrs"]:
        raise ValueError("Compiled manifest must not share another application's UID")
    package = string_value(manifest["attrs"].get("package"))
    if package not in {"com.acuteweb.browser", "com.acuteweb.browser.beta", "com.acuteweb.browser.dev", "com.acuteweb.browser.debug"}:
        raise ValueError("Unrecognized compiled manifest package")
    apps = [node for node in manifest["children"] if node["tag"] == "application"]
    if len(apps) != 1:
        raise ValueError("Expected one compiled application")
    app = apps[0]
    if not is_false(app["attrs"].get("android:allowBackup")):
        raise ValueError("Compiled application must explicitly disable backups")
    updaters = [node for node in app["children"] if node["tag"] == "provider" and
                string_value(node["attrs"].get("android:name")) == "org.mozilla.fenix.acute.GitHubUpdateProvider"]
    if len(updaters) != 1:
        raise ValueError("Expected one compiled updater provider")
    provider = updaters[0]
    attrs = provider["attrs"]
    if not is_false(attrs.get("android:exported")):
        raise ValueError("Compiled updater provider must explicitly disable exported access")
    if string_value(attrs.get("android:authorities")) != package + ".acute-updates":
        raise ValueError("Compiled updater authority must match the application package")
    if ("android:grantUriPermissions" in attrs and not is_false(attrs["android:grantUriPermissions"])) or any(
        node["tag"] == "grant-uri-permission" for node in provider["children"]
    ):
        raise ValueError("Compiled updater provider must not grant URI access")
    for provider in app["children"]:
        attrs = provider["attrs"]
        if provider["tag"] == "provider" and string_value(attrs.get("android:name")) == "org.mozilla.gecko.GeckoClipboardContentProvider":
            if not is_false(attrs.get("android:exported")):
                raise ValueError("Compiled clipboard provider must disable exported access; URI grants remain supported")
            if string_value(attrs.get("android:authorities")) != package + ".clipboard":
                raise ValueError("Compiled clipboard authority must match the application package")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest_dump", type=Path)
    args = parser.parse_args()
    try:
        verify(args.manifest_dump.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        parser.exit(1, f"Compiled manifest verification failed: {error}\n")
    print("Compiled manifest passed attribution, backup and updater access checks")


if __name__ == "__main__":
    main()

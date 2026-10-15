#!/usr/bin/env python3
"""Check unwanted attribution startup components in a compiled AAPT2 manifest dump.

This is a targeted merger regression gate, not a general manifest security audit.
"""

import argparse
from pathlib import Path
import re

DENIED_COMPONENTS = (
    "com.adjust.sdk.SystemLifecycleContentProvider",
    "com.adjust.sdk.AdjustPreinstallReferrerReceiver",
)


def verify(text):
    for element in ("manifest", "application"):
        if not re.search(rf"^\s*E: {element}(?:\s|$)", text, re.MULTILINE):
            raise ValueError(f"Missing compiled {element} element; expected aapt2 dump xmltree output")
    found = [name for name in DENIED_COMPONENTS if name in text]
    if found:
        raise ValueError("Prohibited attribution components: " + ", ".join(found))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest_dump", type=Path)
    args = parser.parse_args()
    try:
        verify(args.manifest_dump.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        parser.exit(1, f"Compiled manifest verification failed: {error}\n")
    print("Compiled manifest contains no prohibited attribution startup components")


if __name__ == "__main__":
    main()

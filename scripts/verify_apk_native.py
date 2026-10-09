#!/usr/bin/env python3
"""Reject mixed, incomplete, or incorrectly labelled native APK architectures."""

import argparse
import struct
import zipfile


MACHINES = {"arm64-v8a": 183, "x86_64": 62}
REQUIRED = {"libmozglue.so", "libxul.so", "libmegazord.so", "libjnidispatch.so"}


def verify(apk, abi):
    if abi not in MACHINES:
        raise ValueError(f"Unsupported ABI: {abi}")
    with zipfile.ZipFile(apk) as archive:
        libraries = [item for item in archive.infolist()
                     if item.filename.startswith("lib/") and item.filename.endswith(".so")]
        found = set()
        for item in libraries:
            parts = item.filename.split("/")
            if len(parts) != 3 or parts[1] != abi:
                raise ValueError(f"Foreign or malformed native library: {item.filename}")
            with archive.open(item) as stream:
                header = stream.read(20)
            if (len(header) != 20 or header[:6] != b"\x7fELF\x02\x01"
                    or struct.unpack_from("<H", header, 18)[0] != MACHINES[abi]):
                raise ValueError(f"Wrong ELF architecture: {item.filename}")
            if parts[2] in found:
                raise ValueError(f"Duplicate native library: {item.filename}")
            found.add(parts[2])
        missing = REQUIRED - found
        if missing:
            raise ValueError(f"Missing {abi} runtime libraries: {', '.join(sorted(missing))}")
    return len(found)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("apk")
    parser.add_argument("abi", choices=MACHINES)
    args = parser.parse_args()
    try:
        count = verify(args.apk, args.abi)
    except (ValueError, OSError, zipfile.BadZipFile) as error:
        parser.exit(1, f"Native APK verification failed: {error}\n")
    print(f"Verified {count} native libraries: {args.abi} only")


if __name__ == "__main__":
    main()

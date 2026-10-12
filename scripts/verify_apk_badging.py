#!/usr/bin/env python3
"""Validate actual AAPT2 badging across old/new SDK labels before APK signing."""
import argparse
from pathlib import Path
import re

DENIED_PERMISSIONS = {
    'com.adjust.preinstall.READ_PERMISSION', 'com.google.android.gms.permission.AD_ID',
    'android.permission.QUERY_ALL_PACKAGES', 'android.permission.REQUEST_DELETE_PACKAGES',
    'android.permission.REQUEST_INSTALL_PACKAGES',
}


def minimum_sdk(text):
    values = re.findall(r"^(?:sdkVersion|minSdkVersion):'([0-9]+)'$", text, re.MULTILINE)
    if not values or len(set(values)) != 1:
        raise ValueError('Missing or contradictory APK minimum SDK metadata')
    return int(values[0])


def verify(text, package, version, abi, allow_debug=False):
    packages = re.findall(r"^package: name='([^']+)'[^\n]*versionName='([^']+)'", text, re.MULTILINE)
    if packages != [(package, version)]:
        raise ValueError('APK package/version does not match selected build inputs')
    sdk = minimum_sdk(text)
    if sdk != 31:
        raise ValueError(f'APK minimum SDK is {sdk}; Android 12 (31) is required')
    if not allow_debug and re.search(r'^application-debuggable(?:\s|$)', text, re.MULTILINE):
        raise ValueError('Release APK is debuggable; refusing signing')
    native = re.findall(r'^native-code:\s*(.*)$', text, re.MULTILINE)
    if len(native) != 1 or re.findall(r"'([^']+)'", native[0]) != [abi]:
        raise ValueError('APK native architectures do not match the selected ABI')
    permissions = set(re.findall(r"^uses-permission(?:-sdk-[0-9]+)?: name='([^']+)'", text, re.MULTILINE))
    forbidden = sorted(permissions & DENIED_PERMISSIONS)
    if forbidden:
        raise ValueError('Prohibited permissions survived manifest merging: ' + ', '.join(forbidden))
    return sdk


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('badging', type=Path)
    parser.add_argument('package')
    parser.add_argument('version')
    parser.add_argument('abi', choices=('arm64-v8a', 'x86_64'))
    parser.add_argument('--allow-debug', action='store_true')
    args = parser.parse_args()
    try:
        sdk = verify(args.badging.read_text(), args.package, args.version, args.abi, args.allow_debug)
    except (ValueError, OSError) as error:
        parser.exit(1, f'APK verification failed: {error}\n')
    print(f'Verified APK identity, Android API {sdk}, {args.abi}, debug policy and merged permissions')

if __name__ == '__main__':
    main()

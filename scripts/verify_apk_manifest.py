#!/usr/bin/env python3
"""Audit aapt2's compiled manifest dump, including dependency-merged components."""
import argparse
import json
from pathlib import Path
import re
import xml.etree.ElementTree as ET

DENIED_PERMISSIONS = {
    'com.adjust.preinstall.READ_PERMISSION', 'com.google.android.gms.permission.AD_ID',
    'android.permission.QUERY_ALL_PACKAGES', 'android.permission.REQUEST_DELETE_PACKAGES',
    'android.permission.REQUEST_INSTALL_PACKAGES',
}


def parse_dump(text):
    stack = []
    root = None
    for line in text.splitlines():
        element = re.match(r'^(\s*)E: ([\w-]+)(?:\s|$)', line)
        if element:
            indent, name = len(element[1]), element[2]
            while stack and stack[-1][0] >= indent:
                stack.pop()
            node = ET.Element(name)
            if stack:
                stack[-1][1].append(node)
            elif root is None:
                root = node
            else:
                raise ValueError('Multiple manifest roots')
            stack.append((indent, node))
            continue
        attribute = re.match(r'^\s*A: ([\w:]+)(?:\([^)]*\))?=(.*)$', line)
        if attribute:
            if not stack:
                raise ValueError('Attribute outside manifest element')
            name, value = attribute.groups()
            value = value.strip()
            string = re.match(r'^"([^"]*)"', value)
            number = re.fullmatch(r'\(type 0x([0-9a-f]+)\)0x([0-9a-f]+)', value)
            if string:
                value = string[1]
            elif number:
                kind, numeric = int(number[1], 16), int(number[2], 16)
                value = str(bool(numeric)).lower() if kind == 0x12 else str(numeric)
            # Leave references/unknown values intact so mandatory invariants fail closed.
            stack[-1][1].set(name, value)
    if root is None or root.tag != 'manifest':
        raise ValueError('No compiled Android manifest found')
    return root


def verify(text, package):
    root = parse_dump(text)
    if root.get('package') != package:
        raise ValueError('APK package differs from expected channel')
    if root.get('android:sharedUserId') is not None:
        raise ValueError('Shared Android UID is forbidden')
    sdk = root.find('uses-sdk')
    if sdk is None or sdk.get('android:minSdkVersion') != '31':
        raise ValueError('APK must enforce the Android 12 minimum')
    app = root.find('application')
    if app is None or app.get('android:allowBackup') != 'false':
        raise ValueError('APK must disable profile backups')
    for flag in ('debuggable', 'testOnly', 'usesCleartextTraffic'):
        if app.get('android:' + flag, 'false') != 'false':
            raise ValueError('Unsafe or unresolved application flag: ' + flag)
    permissions = [p.get('android:name') for tag in ('uses-permission', 'uses-permission-sdk-23') for p in root.findall(tag)]
    if None in permissions or DENIED_PERMISSIONS.intersection(permissions):
        raise ValueError('Unresolved or prohibited merged permission')
    providers = app.findall('provider')
    updater = []
    for provider in providers:
        if provider.get('android:exported', 'false') != 'false':
            raise ValueError('Exported provider: ' + str(provider.get('android:name')))
        authority = provider.get('android:authorities', '')
        if not authority or any(not item.startswith(package + '.') for item in authority.split(';')):
            raise ValueError('Provider authority is not channel isolated: ' + authority)
        if provider.get('android:name') == 'org.mozilla.fenix.acute.GitHubUpdateProvider':
            updater.append(provider)
    if len(updater) != 1 or updater[0].get('android:authorities') != package + '.acute-updates':
        raise ValueError('Missing or malformed isolated update provider')
    exported = [dict(tag=node.tag, **node.attrib) for node in app if node.tag in ('activity', 'activity-alias', 'service', 'receiver') and node.get('android:exported') == 'true']
    return dict(package=package, min_sdk=31, backups=False, permissions=sorted(permissions),
                providers=[dict(p.attrib) for p in providers], exported_components=exported)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('dump', type=Path)
    parser.add_argument('package')
    parser.add_argument('--report', type=Path)
    args = parser.parse_args()
    try:
        report = verify(args.dump.read_text(), args.package)
    except (ValueError, OSError) as error:
        parser.exit(1, f'APK manifest verification failed: {error}\n')
    if args.report:
        args.report.write_text(json.dumps(report, indent=2) + '\n')
    print(f"Verified merged manifest: {args.package}, Android 12+, isolated providers, no backups")

if __name__ == '__main__':
    main()

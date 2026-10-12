from pathlib import Path
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from verify_apk_badging import DENIED_PERMISSIONS, minimum_sdk, verify

FIXTURES = Path(__file__).parent / 'fixtures/aapt2'
PACKAGE = 'com.acuteweb.browser.dev'
VERSION = '2.0.0-dev.90'

class ApkBadgingTests(unittest.TestCase):
    def test_actual_build90_output_uses_new_sdk_label_and_exposes_merger_permissions(self):
        for abi in ('arm64-v8a', 'x86_64'):
            text = (FIXTURES / f'build90-{abi}.txt').read_text()
            self.assertEqual(minimum_sdk(text), 31)
            with self.assertRaisesRegex(ValueError, 'Prohibited permissions'):
                verify(text, PACKAGE, VERSION, abi)
            filtered = '\n'.join(line for line in text.splitlines() if not any(name in line for name in DENIED_PERMISSIONS))
            self.assertEqual(verify(filtered, PACKAGE, VERSION, abi), 31)
            self.assertEqual(verify(filtered.replace('minSdkVersion:', 'sdkVersion:'), PACKAGE, VERSION, abi), 31)

    def test_rejects_wrong_or_missing_sdk_and_conflicting_metadata(self):
        for text in ('targetSdkVersion:\'31\'', "minSdkVersion:'30'", "minSdkVersion:'31'\nsdkVersion:'30'"):
            with self.assertRaises(ValueError):
                if text == "minSdkVersion:'30'":
                    original = self.good().replace("minSdkVersion:'31'", text)
                    verify(original, PACKAGE, VERSION, 'arm64-v8a')
                else:
                    minimum_sdk(text)

    def good(self):
        text = (FIXTURES / 'build90-arm64-v8a.txt').read_text()
        return '\n'.join(line for line in text.splitlines() if not any(name in line for name in DENIED_PERMISSIONS))

    def test_rejects_debug_wrong_identity_and_mixed_architectures(self):
        for text in (self.good() + '\napplication-debuggable', self.good().replace(PACKAGE, 'other.app'),
                     self.good().replace("native-code: 'arm64-v8a'", "native-code: 'arm64-v8a' 'x86_64'")):
            with self.assertRaises(ValueError):
                verify(text, PACKAGE, VERSION, 'arm64-v8a')

    def test_library_permissions_are_blocked_for_both_manifest_tag_types(self):
        for permission in DENIED_PERMISSIONS:
            for tag in ('uses-permission', 'uses-permission-sdk-23'):
                with self.subTest(permission=permission, tag=tag), self.assertRaisesRegex(ValueError, 'permissions'):
                    verify(self.good() + f"\n{tag}: name='{permission}'", PACKAGE, VERSION, 'arm64-v8a')

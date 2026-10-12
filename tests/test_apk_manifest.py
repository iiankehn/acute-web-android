from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from verify_apk_manifest import verify

PACKAGE = 'com.acuteweb.browser.dev'
DUMP = '''N: android=http://schemas.android.com/apk/res/android
  E: manifest (line=1)
    A: package="com.acuteweb.browser.dev" (Raw: "com.acuteweb.browser.dev")
    E: uses-sdk (line=2)
      A: android:minSdkVersion(0x0101020c)=(type 0x10)0x1f
    E: uses-permission (line=3)
      A: android:name(0x01010003)="android.permission.INTERNET"
    E: application (line=4)
      A: android:allowBackup(0x01010280)=(type 0x12)0x0
      E: provider (line=5)
        A: android:name(0x01010003)="org.mozilla.fenix.acute.GitHubUpdateProvider"
        A: android:authorities(0x01010018)="com.acuteweb.browser.dev.acute-updates"
        A: android:exported(0x01010010)=(type 0x12)0x0
      E: service (line=6)
        A: android:name(0x01010003)="org.mozilla.fenix.autofill.AutofillService"
        A: android:exported(0x01010010)=(type 0x12)0xffffffff
        A: android:permission(0x01010006)="android.permission.BIND_AUTOFILL_SERVICE"
'''

class ApkManifestTests(unittest.TestCase):
    def test_merged_manifest_inventory_keeps_protected_autofill(self):
        report = verify(DUMP, PACKAGE)
        self.assertEqual(len(report['providers']), 1)
        self.assertEqual(report['exported_components'][0]['android:permission'], 'android.permission.BIND_AUTOFILL_SERVICE')
        self.assertEqual(report['permissions'], ['android.permission.INTERNET'])

    def test_rejects_dependency_merged_exported_provider(self):
        dump = DUMP.replace('      E: service', '      E: provider (line=8)\n        A: android:name="bad.Provider"\n        A: android:exported=(type 0x12)0xffffffff\n        A: android:authorities="com.acuteweb.browser.dev.bad"\n      E: service')
        with self.assertRaisesRegex(ValueError, 'Exported provider'):
            verify(dump, PACKAGE)

    def test_rejects_backup_debug_uid_and_old_sdk(self):
        for old, new in (
            ('allowBackup(0x01010280)=(type 0x12)0x0', 'allowBackup(0x01010280)=(type 0x12)0xffffffff'),
            ('    E: uses-sdk', '    A: android:sharedUserId="firefox"\n    E: uses-sdk'),
            ('(type 0x10)0x1f', '(type 0x10)0x1a'),
            ('      E: provider', '      A: android:debuggable=(type 0x12)0xffffffff\n      E: provider'),
        ):
            with self.subTest(new=new), self.assertRaises(ValueError):
                verify(DUMP.replace(old, new), PACKAGE)

    def test_rejects_permission_restored_by_library_merge(self):
        with self.assertRaises(ValueError):
            verify(DUMP.replace('android.permission.INTERNET', 'android.permission.REQUEST_INSTALL_PACKAGES'), PACKAGE)

    def test_rejects_cross_channel_authority_and_unknown_boolean(self):
        for dump in (DUMP.replace(PACKAGE + '.acute-updates', 'com.acuteweb.browser.acute-updates'),
                     DUMP.replace('allowBackup(0x01010280)=(type 0x12)0x0', 'allowBackup(0x01010280)=@0x7f010001')):
            with self.assertRaises(ValueError):
                verify(dump, PACKAGE)

    def test_rejects_empty_missing_updater_and_wrong_channel(self):
        for dump, package in (('', PACKAGE), (DUMP.replace('GitHubUpdateProvider', 'OtherProvider'), PACKAGE), (DUMP, 'com.acuteweb.browser')):
            with self.assertRaises(ValueError):
                verify(dump, package)

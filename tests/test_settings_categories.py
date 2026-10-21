from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from apply_overlay import OverlayError, patch_settings_categories

FIXTURE = Path(__file__).parent / "fixtures/firefox-158.0/preferences.xml"
DATA_CHOICES = '''        <androidx.preference.Preference
            android:key="@string/pref_key_data_choices"
            app:iconSpaceReserved="false"
            android:title="@string/preferences_data_collection" />
'''
REPORT_ISSUE = '''        <androidx.preference.Preference
            android:key="acute_report_issue"
            app:iconSpaceReserved="false"
            android:title="@string/acute_report_issue_title">
            <intent android:action="android.intent.action.VIEW" />
        </androidx.preference.Preference>
'''


class SettingsCategoryTests(unittest.TestCase):
    def regroup(self, text: str) -> str:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "preferences.xml"
            path.write_text(text)
            patch_settings_categories(path)
            return path.read_text()

    def test_keeps_every_entry_once(self):
        original = FIXTURE.read_text().replace(DATA_CHOICES, REPORT_ISSUE)
        regrouped = self.regroup(original)
        self.assertEqual(regrouped.count(REPORT_ISSUE), 1)
        keys = lambda text: sorted(line.strip() for line in text.splitlines() if "android:key=" in line)
        self.assertEqual(keys(regrouped), keys(original))

    def test_rejects_new_upstream_entry(self):
        added = FIXTURE.read_text().replace(DATA_CHOICES, REPORT_ISSUE + DATA_CHOICES.replace(
            "pref_key_data_choices", "pref_key_new_upstream_setting"))
        with self.assertRaisesRegex(OverlayError, "pref_key_new_upstream_setting"):
            self.regroup(added)


if __name__ == "__main__":
    unittest.main()

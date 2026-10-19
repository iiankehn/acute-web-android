from pathlib import Path
import shutil
import sys
import tempfile
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from apply_overlay import patch_native_menu
from verify_upstream_overlay import validate_menu_continuity

FIXTURE = Path(__file__).parent / "fixtures/firefox-157.0.1/MainMenu.kt"


class MenuContinuityTests(unittest.TestCase):
    def transformed(self) -> str:
        with tempfile.TemporaryDirectory() as directory:
            menu = Path(directory) / "MainMenu.kt"
            shutil.copy(FIXTURE, menu)
            patch_native_menu(menu)
            return menu.read_text()

    def test_grouped_menu_keeps_every_upstream_action(self):
        validate_menu_continuity(FIXTURE.read_text(), self.transformed())

    def test_rejects_dropped_handler(self):
        transformed = self.transformed().replace(
            "onClick = onSettingsButtonClick", "onClick = {}"
        )
        with self.assertRaisesRegex(AssertionError, "onSettingsButtonClick"):
            validate_menu_continuity(FIXTURE.read_text(), transformed)

    def test_rejects_dropped_handler_wiring(self):
        transformed = self.transformed().replace(
            "onQuitMenuClick = onQuitMenuClick", "onQuitMenuClick = {}"
        )
        with self.assertRaisesRegex(AssertionError, "onQuitMenuClick"):
            validate_menu_continuity(FIXTURE.read_text(), transformed)


if __name__ == "__main__":
    unittest.main()

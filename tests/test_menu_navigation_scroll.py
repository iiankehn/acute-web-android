from pathlib import Path
import shutil
import sys
import tempfile
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from apply_overlay import OverlayError, patch_menu_navigation_scroll

FIXTURE = Path(__file__).parent / "fixtures/firefox-158.0/MenuNavigation.kt"


class MenuNavigationScrollTests(unittest.TestCase):
    def transformed(self, source: str) -> str:
        with tempfile.TemporaryDirectory() as directory:
            navigation = Path(directory) / "MenuNavigation.kt"
            navigation.write_text(source, encoding="utf-8")
            patch_menu_navigation_scroll(navigation)
            return navigation.read_text(encoding="utf-8")

    def test_removes_nested_vertical_scroll(self):
        text = self.transformed(FIXTURE.read_text(encoding="utf-8"))
        self.assertNotIn("verticalScroll", text)
        self.assertNotIn("rememberScrollState", text)
        self.assertIn(".padding(horizontal = 4.dp, vertical = 12.dp)\n                .semantics(", text)

    def test_keeps_every_navigation_action(self):
        text = self.transformed(FIXTURE.read_text(encoding="utf-8"))
        for handler in ("onBackButtonClick", "onForwardButtonClick", "onRefreshButtonClick",
                        "onStopButtonClick", "onShareButtonClick"):
            self.assertEqual(FIXTURE.read_text(encoding="utf-8").count(handler), text.count(handler), handler)

    def test_fails_when_upstream_drops_the_scroll(self):
        source = FIXTURE.read_text(encoding="utf-8").replace(
            "                .verticalScroll(rememberScrollState())\n", ""
        )
        with self.assertRaisesRegex(OverlayError, "menu navigation row vertical scroll"):
            self.transformed(source)


if __name__ == "__main__":
    unittest.main()

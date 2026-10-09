import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOKENS = (ROOT / "overlay/kotlin/AcuteThemeTokens.kt").read_text()


def luminance(hex_color):
    channels = [int(hex_color[index:index + 2], 16) / 255 for index in (2, 4, 6)]
    linear = [value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4
              for value in channels]
    return sum(value * weight for value, weight in zip(linear, (0.2126, 0.7152, 0.0722)))


class ThemeTokenTests(unittest.TestCase):
    def test_normal_text_contrast_on_structural_surfaces(self):
        colors = dict(re.findall(r'val (\w+) = Color\(0x([A-Fa-f0-9]{8})\)', TOKENS))
        for foreground in ("text", "muted", "light"):
            for background in ("canvas", "surface", "raised", "selected"):
                with self.subTest(foreground=foreground, background=background):
                    light, dark = sorted((luminance(colors[foreground]), luminance(colors[background])), reverse=True)
                    self.assertGreaterEqual((light + 0.05) / (dark + 0.05), 4.5)

    def test_structural_gradients_are_neutral_and_semantic_roles_are_retained(self):
        self.assertIn("acornDarkColorScheme().copy(", TOKENS)
        self.assertIn("darkColorPalette.copy(", TOKENS)
        self.assertNotIn("error =", TOKENS)
        self.assertNotIn("warning =", TOKENS)
        self.assertNotIn("success =", TOKENS)
        self.assertIn("tabOutline = gradient(light, outline)", TOKENS)
        self.assertIn("privacyMask = gradient(muted, light)", TOKENS)
        self.assertNotIn("NovaColors", TOKENS)
        self.assertNotIn("dynamicDarkColorScheme", TOKENS)

from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from apply_overlay import OverlayError, patch_marketing_policy

SETTINGS = '''    var isMarketingTelemetryEnabled by
        booleanPreference(
            appContext.getPreferenceKey(R.string.pref_key_marketing_telemetry),
            default = false,
        )

    /** Indicates if the continuous onboarding feature is enabled. */
    var continuousOnboardingFeatureEnabled by
        booleanPreference(
            key = appContext.getPreferenceKey(R.string.pref_key_continuous_onboarding_enabled),
            default = { FxNimbus.features.continuousOnboarding.value().enabled },
        )
'''
ONBOARDING = '''            .filterNot {
                it.type == OnboardingPageUiData.Type.MARKETING_DATA &&
                    !requireComponents.settings.shouldShowMarketingOnboarding
            }
        addMarketingFeature.set(
            feature =
                MarketingPageAdditionSupport(
                    prefKey = requireContext().getString(R.string.pref_key_should_show_marketing_onboarding),
                    pagesToDisplay = pagesToDisplay,
                    marketingPage = marketingPage,
                    settings = requireComponents.settings,
                    lifecycleOwner = viewLifecycleOwner,
                ),
            owner = this,
            view = view,
        )
'''


class ContinuousOnboardingTests(unittest.TestCase):
    def apply(self, settings_text: str) -> str:
        with tempfile.TemporaryDirectory() as directory:
            settings = Path(directory) / "Settings.kt"
            onboarding = Path(directory) / "OnboardingFragment.kt"
            settings.write_text(settings_text, encoding="utf-8")
            onboarding.write_text(ONBOARDING, encoding="utf-8")
            patch_marketing_policy(settings, onboarding)
            return settings.read_text(encoding="utf-8")

    def test_continuous_onboarding_is_always_off(self):
        text = self.apply(SETTINGS)
        self.assertIn(
            "    var continuousOnboardingFeatureEnabled: Boolean\n        get() = false\n        set(value) = Unit\n",
            text,
        )
        # Neither a saved preference nor a Nimbus default can turn it back on.
        self.assertNotIn("pref_key_continuous_onboarding_enabled", text)
        self.assertNotIn("FxNimbus.features.continuousOnboarding", text)

    def test_fails_closed_when_upstream_changes_the_preference(self):
        changed = SETTINGS.replace("default = { FxNimbus", "default = { false || FxNimbus")
        with self.assertRaisesRegex(OverlayError, "continuous onboarding preference"):
            self.apply(changed)


if __name__ == "__main__":
    unittest.main()

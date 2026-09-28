from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from scripts.update_site_release import update_site


ROOT = Path(__file__).resolve().parents[1]


def release_event(tag, prerelease, size=100):
    version = tag.removeprefix("v")
    filename = f"acute-web-{version}-arm64-v8a.apk"
    return {
        "repository": {"full_name": "iiankehn/acute-web-android"},
        "release": {
            "tag_name": tag,
            "draft": False,
            "prerelease": prerelease,
            "assets": [
                {
                    "name": filename,
                    "size": size,
                    "browser_download_url": (
                        f"https://github.com/iiankehn/acute-web-android/releases/download/{tag}/{filename}"
                    ),
                }
            ],
        },
    }


class SiteReleaseTests(unittest.TestCase):
    def update_copy(self, event):
        temp = TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        html = Path(temp.name) / "index.html"
        html.write_text((ROOT / "docs/index.html").read_text(), encoding="utf-8")
        self.assertTrue(update_site(event, html))
        return html.read_text(encoding="utf-8")

    def test_stable_release_updates_all_stable_links_and_labels(self):
        updated = self.update_copy(release_event("v0.5.0", prerelease=False))
        self.assertIn("acute-web-0.5.0-arm64-v8a.apk", updated)
        self.assertIn('data-release-version="stable">0.5.0', updated)
        self.assertIn('data-release-version="stable-short">0.5', updated)

    def test_beta_release_updates_beta_only(self):
        original = (ROOT / "docs/index.html").read_text(encoding="utf-8")
        stable_links = [
            line.strip()
            for line in original.splitlines()
            if 'data-release-link="stable"' in line
        ]
        updated = self.update_copy(release_event("v0.5.0-beta.1", prerelease=True))
        self.assertIn("acute-web-0.5.0-beta.1-arm64-v8a.apk", updated)
        self.assertIn('data-release-version="beta">0.5.0-beta.1', updated)
        for stable_link in stable_links:
            self.assertIn(stable_link, updated)

    def test_rejects_empty_or_unexpected_assets(self):
        with TemporaryDirectory() as temp:
            html = Path(temp) / "index.html"
            html.write_text((ROOT / "docs/index.html").read_text(), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "empty"):
                update_site(release_event("v0.5.0", prerelease=False, size=0), html)

    def test_rejects_channel_tag_mismatch(self):
        with TemporaryDirectory() as temp:
            html = Path(temp) / "index.html"
            html.write_text((ROOT / "docs/index.html").read_text(), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "invalid format"):
                update_site(release_event("v0.5.0-beta.1", prerelease=False), html)


if __name__ == "__main__":
    unittest.main()

# Source availability and license compliance

Acute Web is an independent browser developed by CORE from Mozilla's
open-source Firefox for Android and Gecko code. Acute is distributed under the
Mozilla Public License 2.0 (MPL-2.0), and the source needed to reproduce each
published build remains publicly accessible.

## Public source channels

| Product channel | Acute source | Android application ID |
|---|---|---|
| Stable | [`main`](https://github.com/iiankehn/acute-web-android/tree/main) | `com.acuteweb.browser` |
| Beta | [`beta`](https://github.com/iiankehn/acute-web-android/tree/beta) | `com.acuteweb.browser.beta` |
| 2.0 Dev | [`dev`](https://github.com/iiankehn/acute-web-android/tree/dev) | `com.acuteweb.browser.dev` |

GitHub opens the repository on `main` because Stable is the default channel.
The `beta` branch is independently browsable, cloneable, and downloadable from
the branch selector or the direct link above.

## How Acute source maps to a binary

This repository stores Acute's product source as an auditable overlay rather
than duplicating Mozilla's complete source tree. A build is defined by:

1. the Acute commit or release tag;
2. the full Mozilla commit recorded in `acute-android.toml` and the build workflow;
3. `scripts/apply_overlay.py`, which applies the reviewed Acute modifications;
4. the resources, bundled components, tests, and automation in this repository.

The workflow fetches the exact Mozilla commit, applies the Acute overlay, runs
validation, and builds the APK. Published releases include build-input metadata
and provenance so a binary can be traced to those inputs.

The currently pinned upstream source revision is:

[`mozilla-firefox/firefox@08d23041955657e661eef22c8fdc967735300233`](https://github.com/mozilla-firefox/firefox/tree/08d23041955657e661eef22c8fdc967735300233) (Firefox for Android 158.0.2, tag `FIREFOX-ANDROID_158_0_2_RELEASE`)

This is the Android 2.0 development pin. Historical Stable/Beta releases retain
the revision in their own tag's configuration and build-input report.

## Licensing and notices

- Acute source code in this repository is provided under MPL-2.0.
- Files copied or modified from Mozilla retain their original notices.
- Required license and attribution information remains available in the app
  and repository.
- Firefox and Mozilla are trademarks of the Mozilla Foundation. Acute Web is
  not endorsed by or affiliated with Mozilla.
- The Acute Web and CORE names and original artwork identify this project; the
  MPL does not grant trademark rights.

The license notice and link to its complete terms are in [`LICENSE`](../LICENSE). Product-specific
changes are summarized in [`MODIFICATIONS.md`](MODIFICATIONS.md).

## Obtaining source for a release

Open a release's associated tag to browse its exact Acute source. To reproduce
it locally, clone that tag and the pinned Mozilla revision:

```bash
git clone --branch <release-tag> https://github.com/iiankehn/acute-web-android.git
git clone https://github.com/mozilla-firefox/firefox.git
cd firefox
git checkout <upstream-commit-from-the-selected-Acute-tag>
../acute-web-android/scripts/apply_overlay.py . --channel stable
```

For a Beta build, clone the `beta` branch and pass `--channel beta`. Build
2.0 development from `dev` with `--channel dev`. Build prerequisites and release procedures are documented in
[`GITHUB_SETUP.md`](GITHUB_SETUP.md) and [`UPSTREAM.md`](UPSTREAM.md).

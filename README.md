# Acute Web for Android

Acute Web is a Firefox/GeckoView-based Android browser distributed as a
sideloadable APK. This repository is a small, auditable branding and release
overlay for Mozilla's Firefox for Android (Fenix) source tree.

The first version inherits Fenix's tabs, combined search/address bar,
bookmarks and history, downloads, private browsing, password manager, and
compatible WebExtension support. Acute's own telemetry and crash-upload build
flags are disabled by the overlay.

## What this repository does

- applies the Acute Web name, application ID, and launcher artwork;
- keeps the Gecko rendering engine and the Fenix browser UI;
- removes Firefox's shared Android user ID so Acute installs independently;
- adds an in-app update check against this repository's GitHub Releases;
- enables Fenix's top tab strip, expanded toolbar, and desktop-site default on
  physical tablets while preserving user overrides;
- supports resizable/split-screen windows and keyboard/mouse-first ChromeOS
  devices, with automated large-screen launch and rotation smoke tests;
- builds debug APKs on demand and signed release APKs for `v*` tags.

It intentionally does **not** contain a vendored copy of Firefox. GitHub
Actions checks out a reviewed, pinned Mozilla commit, applies this overlay,
and builds it without exposing the Acute release key to upstream build code.

## Local build

Linux is the supported build host (including WSL 2 on Windows). A first build
is large and can take a while.

```bash
git clone https://github.com/mozilla-firefox/firefox.git
git clone https://github.com/iiankehn/acute-web-android.git
cd firefox
python3 ./mach bootstrap --application-choice mobile_android_artifact_mode --no-interactive
../acute-web-android/scripts/apply_overlay.py .
./mach gradle fenix:assembleDebug
```

The APK is written below the Firefox object directory under
`gradle/build/mobile/android/fenix/app/outputs/apk/debug/`.

## GitHub builds and releases

1. Push this repository to `iiankehn/acute-web-android` as a public repo.
2. Run **Build Android APK** from the Actions tab for a test APK.
3. Complete [docs/SIGNING.md](docs/SIGNING.md) once.
4. Push a semantic version tag such as `v0.1.0` to publish a signed GitHub
   Release. The installed app checks the latest release at most once every six
   hours and uses a one-hour retry delay after network failures.

See [docs/GITHUB_SETUP.md](docs/GITHUB_SETUP.md) for exact setup commands and
[docs/UPSTREAM.md](docs/UPSTREAM.md) for maintaining the Firefox base. Tablet
behavior and its current limitations are documented in
[docs/TABLET_SUPPORT.md](docs/TABLET_SUPPORT.md).

## Important status

This is an initial engineering scaffold. The overlay and updater have fixture
tests, but the full Android APK must be compiled by the included GitHub Actions
workflow or on a Linux development machine. Before distributing it broadly,
test browsing, private mode, downloads, saved logins, extensions, upgrades,
and Android lifecycle behavior on physical devices.

Firefox is a trademark of the Mozilla Foundation. Acute Web is an independent
project and is not endorsed by Mozilla.

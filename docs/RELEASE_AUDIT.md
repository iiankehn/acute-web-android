# Release audit and acceptance gates

Acute Web uses a fail-closed pipeline for Android builds.
No Stable or Beta APK is published merely because it compiles.
Pull requests targeting Dev run the audit and unsigned APK builds. Signing is
restricted to trusted pushes; pull requests do not receive release credentials.

## Automated audit

Every Beta push and release tag must pass these checks before the native builds
start:

- all Acute Python regression tests, overlay fixtures, and JavaScript behavioral tests;
- compilation of Acute Python build and release tooling;
- JSON and Android XML parsing;
- Stable/Beta application-ID isolation;
- non-exported update-provider configuration;
- HTTPS and GitHub-origin restrictions in the update checker;
- absence of release-dangerous Android debug, test-only, and cleartext flags;
- absence of private-key material and local development endpoints;
- immutable 40-character GitHub Action references;
- agreement between project metadata, the workflow, and the pinned Firefox
  source commit;
- explicit ARM64 and x86_64 native build targets and package verification;
- compiled-manifest backup, shared-UID, updater and clipboard-provider access checks.

The APK pipeline then verifies the expected Gecko libraries for each ABI,
minimized permissions, release signature, signer continuity with earlier
releases, checksums, immutable build inputs, and GitHub provenance attestation.
Signing secrets are available only to the isolated signing jobs after both
unprivileged builds succeed.

## Dependency policy

The Acute overlay has no third-party Python package dependency. Its local
Midnight Pages extension makes no external service request. GitHub Actions are
pinned to reviewed commit hashes, and the complete Mozilla source input is
pinned to one full commit recorded in `acute-android.toml`, the workflow, and
each release's `build-inputs-<ABI>.txt`.

Mozilla security advisories and upstream source changes must be reviewed before
moving that pin. Acute prefers an ESR-style maintenance cadence, but a different
Firefox/Gecko line is not adopted by name alone: Android source compatibility,
GeckoView behavior, the overlay, and both native builds must all pass on Beta
first.

## Smoke tests

`scripts/android_smoke.py` drives an installed build over adb: launch and first
run, an HTTPS page, the main menu on that page (opened and scrolled), Settings ›
Privacy and security › HTTPS-Only Mode, the HTTPS-Only warning for an HTTP-only
site, and a final check that Acute is still running with no crash recorded.

Every APK build runs it on two x86_64 emulators (a phone on Android 12 and a
tablet on Android 15) through `.github/workflows/android-smoke.yml`, and keeps
screenshots, screen dumps and logs as artifacts. A pull request that only
changes the smoke test runs it against the latest Dev build.

To run the same checks on a phone connected over USB:

```bash
python3 scripts/android_smoke.py --package com.acuteweb.browser.dev
```

Add `--fresh` to test first run as well; it erases that app's profile. The
script checks that Acute is in front before every tap and stops if another app
takes over the screen.

## Physical-device acceptance

ARM64 and x86_64 are separate supported native architectures.
Before promotion to Stable, the signed candidates are checked for correct ABI
packaging and the ARM64 candidate is tested on supported physical devices for:

- install-over update and profile preservation;
- launch, navigation, address-bar interaction, and toolbar collapse/restore;
- tabs, private browsing, bookmarks/history, downloads, passwords, and
  compatible extensions;
- rotation, split screen, phone and large-screen layouts;
- update notification and handoff to Android's package installer;
- opaque native-chrome contrast, touch targets, and page-content accessibility.

Failures block promotion. For the current 2.0 source audit, dependency findings,
and physical-device gates, see [the Beta audit](BETA_2_0_AUDIT.md).

## Historical reviews

The [1.0 upstream decision](archive/RELEASE_1_0_UPSTREAM_REVIEW.md) is retained
for provenance. It does not describe the current Firefox pin.

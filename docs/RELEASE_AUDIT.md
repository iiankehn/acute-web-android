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
- explicit ARM64 and x86_64 native build targets and package verification.
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
each release's `build-inputs.txt`.

Mozilla security advisories and upstream source changes must be reviewed before
moving that pin. Acute prefers an ESR-style maintenance cadence, but a different
Firefox/Gecko line is not adopted by name alone: Android source compatibility,
GeckoView behavior, the overlay, and both native builds must all pass on Beta
first.

## Physical-device acceptance

Version 1.1 adds x86_64 as a supported native architecture alongside ARM64.
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

## 1.0 upstream review

The 1.0 candidate retains Firefox commit
`4452e9a17a29f762c5af6326f45c000dcf3117bb`, reviewed on September 28, 2026.
That input was eight days behind Mozilla's development head and had already
passed Acute's complete ARM64 build, signing-continuity checks, and physical
0.7 acceptance testing. Moving to the contemporary development head would
have introduced roughly 2,200 additional commits, including AndroidX, Gradle,
Android build-system, and Gecko changes, immediately before the final release.
The larger upstream refresh is therefore a post-1.0 Beta task and must pass the
same fail-closed audit and device-acceptance gates before later promotion.

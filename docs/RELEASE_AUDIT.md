# Release audit and acceptance gates

Acute Web uses one sequential, fail-closed pipeline for pre-1.0 Android builds.
No Stable or Beta APK is published merely because it compiles.
Pull requests also run the same audit without launching an APK build.

## Automated audit

Every Beta push and release tag must pass these checks before the ARM64 build
starts:

- all Acute Python regression tests and overlay fixtures;
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
- ARM64-only workflow enforcement through 1.0.

The APK pipeline then verifies the expected ARM64 Gecko libraries, minimized
permissions, release signature, signer continuity with earlier releases,
checksum, immutable build inputs, and GitHub provenance attestation. Signing
secrets are available only to the isolated signing job after the unprivileged
build succeeds.

## Dependency policy

The Acute overlay has no third-party Python package dependency. Its local
Midnight Pages extension makes no external service request. GitHub Actions are
pinned to reviewed commit hashes, and the complete Mozilla source input is
pinned to one full commit recorded in `acute-android.toml`, the workflow, and
each release's `build-inputs.txt`.

Mozilla security advisories and upstream source changes must be reviewed before
moving that pin. Acute prefers an ESR-style maintenance cadence, but a different
Firefox/Gecko line is not adopted by name alone: Android source compatibility,
GeckoView behavior, the overlay, and the complete ARM64 build must all pass on
Beta first.

## Physical-device acceptance

GitHub's hosted Android emulator path is x86_64, which is intentionally outside
Acute's ARM64-only target through 1.0. It is not used as a substitute for the
supported architecture. Before promotion to Stable, the signed ARM64 candidate
is tested on supported physical devices for:

- install-over update and profile preservation;
- launch, navigation, address-bar interaction, and toolbar collapse/restore;
- tabs, private browsing, bookmarks/history, downloads, passwords, and
  compatible extensions;
- rotation, split screen, phone and large-screen layouts;
- update notification and handoff to Android's package installer;
- CORE Glass contrast, touch targets, and page-content accessibility.

Failures block promotion. Versions 0.8 and 0.9 are cut only when a verified
issue requires a corrective candidate; otherwise the audited Beta proceeds
toward 1.0 without ceremonial releases.

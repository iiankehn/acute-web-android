# Acute release channels

Acute Web uses two release channels and an isolated Dev channel with separate Git branches and Android
application identities.

| Channel | Branch | Application ID | Version format |
|---|---|---|---|
| Stable | `main` | `com.acuteweb.browser` | `vMAJOR.MINOR.PATCH` |
| Beta | `beta` | `com.acuteweb.browser.beta` | `vMAJOR.MINOR.PATCH-beta.NUMBER` |
| Dev | `dev` | `com.acuteweb.browser.dev` | `2.0.0-dev.NUMBER` CI artifacts |

Browse the public channel sources directly:

- [Stable source (`main`)](https://github.com/iiankehn/acute-web-android/tree/main)
- [Beta source (`beta`)](https://github.com/iiankehn/acute-web-android/tree/beta)
- [Stable and Beta downloads](https://github.com/iiankehn/acute-web-android/releases)

Acute Beta installs alongside Acute Stable and uses a separate Android profile.
Testing Beta therefore does not replace or modify a user's Stable installation.

## Promotion policy

Every change moves through the channels in one direction: **Dev → Beta → Stable**.

1. **Dev.** Changes land on `dev` through pull requests. Each push builds signed
   Dev-package APKs as CI artifacts for device testing. Dev builds never publish
   releases or update the website, and the Dev updater is disabled.
2. **Beta.** Once a Dev build has been tested on a device, `dev` is promoted to
   `beta` and tagged `vMAJOR.MINOR.PATCH-beta.NUMBER` to publish a prerelease.
3. **Stable.** When a Beta has been tested and the feature set is locked in, `beta`
   is promoted to `main` and tagged `vMAJOR.MINOR.PATCH`. A feature reaches `main`
   only after its tests pass, its branding and documentation are complete, and it
   survives phone, tablet, upgrade, and update-channel testing.

Fixes always start on `dev`, including fixes for problems found in Beta or Stable.

Android 2.0 replaces the CORE Glass interface with native Android controls; the
Glass-based Beta line is preserved at `archive/pre-native-2026-10-12-beta`.
Open acceptance gates are tracked in [the 2.0 Beta audit](BETA_2_0_AUDIT.md).

Stable releases use tags such as `v1.1.0`. Beta releases use tags such as
`v1.1.0-beta.1` and are published as GitHub prereleases.

## Website publication

After the release job publishes its assets, the website job validates the
release tag, channel, non-empty signed ARM64 APK, and official GitHub asset URL
before changing the website. The x86_64 package is published alongside it;
Stable releases update Stable version labels and download buttons, while
prereleases update the Beta card and Beta download buttons.
The resulting commit to `main` triggers the existing GitHub Pages deployment.

## Upstream policy

Both channels use a reviewed, pinned commit from Mozilla's Stable source line.
Acute does not automatically follow Beta or Nightly upstream code. The pinned
revision changes only after review and compatibility testing, or when a browser-
engine security update requires it.

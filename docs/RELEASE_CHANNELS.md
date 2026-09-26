# Acute release channels

Acute Web uses two release channels with separate Git branches and Android
application identities.

| Channel | Branch | Application ID | Version format |
|---|---|---|---|
| Stable | `main` | `com.acuteweb.browser` | `vMAJOR.MINOR.PATCH` |
| Beta | `beta` | `com.acuteweb.browser.beta` | `vMAJOR.MINOR.PATCH-beta.NUMBER` |

Browse the public channel sources directly:

- [Stable source (`main`)](https://github.com/iiankehn/acute-web-android/tree/main)
- [Beta source (`beta`)](https://github.com/iiankehn/acute-web-android/tree/beta)
- [Stable and Beta downloads](https://github.com/iiankehn/acute-web-android/releases)

Acute Beta installs alongside Acute Stable and uses a separate Android profile.
Testing Beta therefore does not replace or modify a user's Stable installation.

## Promotion policy

New features are developed and tested on `beta`. A feature is promoted to
`main` only after its tests pass, its user-facing branding and documentation are
complete, and it survives phone, tablet, upgrade, and update-channel testing.

The 0.5 series is the current Beta and release-candidate train. Its work
includes the Midnight-only application interface, standardized assets, CORE
Glass surfaces, tab organization, a large-screen tab bar, Read Aloud, and
stability work required for eventual Stable promotion.

Stable releases use tags such as `v0.5.0`. Beta releases use tags such as
`v0.5.0-beta.1` and are published as GitHub prereleases.

## Website publication

After the release job publishes its assets, the website job validates the
release tag, channel, non-empty signed ARM64 APK, and official GitHub asset URL
before changing the website. Stable releases update Stable version labels and
download buttons; prereleases update the Beta card and Beta download buttons.
The resulting commit to `main` triggers the existing GitHub Pages deployment.

## Upstream policy

Both channels use a reviewed, pinned commit from Mozilla's Stable source line.
Acute does not automatically follow Beta or Nightly upstream code. The pinned
revision changes only after review and compatibility testing, or when a browser-
engine security update requires it.

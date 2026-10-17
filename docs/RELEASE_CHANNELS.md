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

Android 2.0 experiments are reviewed and tested on `dev` before a Beta candidate. Dev builds do not publish releases or update the public download website. Its release updater is disabled. A feature is promoted to
`main` only after its tests pass, its user-facing branding and documentation are
complete, and it survives phone, tablet, upgrade, and update-channel testing.

The 2.0 development candidate retains native x86_64 support alongside ARM64,
including architecture-aware update selection and separately verified signed
packages. The native Android UI/security work on Dev supersedes the older
Glass-based Beta implementation. Promotion depends on the open gates in
[the 2.0 Beta audit](BETA_2_0_AUDIT.md).

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

# Acute release channels

Acute Web uses two release channels with separate Git branches and Android
application identities.

| Channel | Branch | Application ID | Version format |
|---|---|---|---|
| Stable | `main` | `com.acuteweb.browser` | `vMAJOR.MINOR.PATCH` |
| Beta | `beta` | `com.acuteweb.browser.beta` | `vMAJOR.MINOR.PATCH-beta.NUMBER` |

Acute Beta installs alongside Acute Stable and uses a separate Android profile.
Testing Beta therefore does not replace or modify a user's Stable installation.

## Promotion policy

New features are developed and tested on `beta`. A feature is promoted to
`main` only after its tests pass, its user-facing branding and documentation are
complete, and it survives phone, tablet, upgrade, and update-channel testing.

The 0.4 series is the current Beta feature train. Its planned work includes the
dark-first interface, standardized assets, tab groups, a large-screen tab bar,
and on-device Read Aloud. The following 0.5 series is the planned release-
candidate and Stable promotion line.

Stable releases use tags such as `v0.5.0`. Beta releases use tags such as
`v0.4.0-beta.1` and are published as GitHub prereleases.

## Upstream policy

Both channels use a reviewed, pinned commit from Mozilla's Stable source line.
Acute does not automatically follow Beta or Nightly upstream code. The pinned
revision changes only after review and compatibility testing, or when a browser-
engine security update requires it.

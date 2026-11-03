# Acute Web modifications

This document summarizes the material changes CORE applies to the pinned
Firefox for Android source used by Acute Web. The implementation is defined by
the public overlay, resources, tests, and workflow in this repository.

## Product identity

- Acute Web and Acute Beta use independent Android package identities.
- Acute names, launcher assets, About content, support links, and release
  information replace upstream product-facing branding. Acute Beta adds a
  dedicated `BETA` launcher badge across adaptive, legacy, round, and themed
  icon treatments so it remains visibly distinct from Stable.
- Mozilla and Gecko references are retained where needed for accurate engine,
  copyright, license, and attribution disclosures.

## Privacy and distribution

- Product telemetry, marketing telemetry, crash uploading, and diagnostic
  reporting are disabled in Acute builds.
- Unneeded Adjust preinstallation and package-deletion permissions are removed.
- Sponsored home content and marketing onboarding screens are disabled.
- Continuous onboarding is disabled, so existing users are not re-prompted on later
  days with the default-browser request, a sync sign-in card or a VPN promotion.
  Setting Acute as the default browser stays available in Settings.
- Strict tracking protection, HTTPS-Only mode and Global Privacy Control are the
  default for every profile; saved user choices are kept. First-run onboarding,
  a one-time notice after updating, and Settings › Privacy and security explain
  these defaults.
- Signed ARM64 and x86_64 APKs are distributed through GitHub rather than an application
  store.
- The in-app updater checks the matching Stable or Beta GitHub release channel
  and hands installation to Android's protected package installer.

## Interface and accessibility

- Application chrome uses Acute's Midnight interface and CORE blue accents.
- The 2.0 development source removes CORE Glass in favor of opaque native Android
  surfaces. Older Beta tags retain their historical implementation.
- Toolbar scrolling and viewport handling retain upstream behavior; Acute no
  longer forces toolbar collapse after page loading.
- Launcher assets support circular, rounded-rectangle, square, and monochrome
  adaptive-icon treatments.
- Upstream accessibility semantics and Android text scaling remain release
  requirements.

## Phones, tablets, and productivity

- Large screens receive tablet-oriented layout defaults, desktop-site behavior,
  split-screen support, and keyboard/mouse-compatible controls.
- Beta development includes a large-screen tab strip, tab organization, Read
  Aloud, and Midnight Pages controls for sites without a suitable dark theme.

## Build and release engineering

- Mozilla source is pinned to a reviewed full commit instead of a moving branch.
- Overlay application fails closed when audited upstream patterns no longer match.
- Builds verify ARM64 and x86_64 Gecko libraries, minimized permissions, signing
  continuity, checksums, build inputs, and provenance.
- Stable and Beta use separate branches and application IDs. Signed builds use
  increasing Android version codes so updates preserve user data.

## Upstream components intentionally retained

Acute continues to rely on Gecko, Android Components, and Firefox for Android
features such as standards-compliant rendering, sandboxing, tabs, bookmarks,
history, downloads, private browsing, saved passwords, and compatible
extensions. Those foundations retain their original licenses and notices.

For the exact source relationship and reproduction instructions, see
[`SOURCE_AND_LICENSE.md`](SOURCE_AND_LICENSE.md).

## Beta 3 telemetry startup hardening

- Disable Fenix Glean initialization at its shared helper so startup and
  onboarding cannot start that backend through the helper, even for existing
  profiles. Runtime network validation remains pending.

## Beta 3 local crash review

- Retain one bounded Java/Kotlin main-process crash in private, backup-excluded
  storage. Record version, Android version, model, exception types and stack
  symbols/line numbers; omit exception messages, filenames, thread names and
  suppressed exceptions. Preserve Android termination behavior.
- Settings and About › Report an issue open a local review flow. Including the
  last crash is opt-in, the full draft is editable, and GitHub receives text
  only after the tester presses Open GitHub draft. Delete local crash removes
  the retained record. No new permissions or exported entry points.
- Native engine/tab crashes are not captured by this handler. Physical-device
  forced-crash, storage-failure and draft-opening validation remain pending.

## Beta 3 push log privacy

- Remove Firebase registration tokens and message channel IDs from upstream
  push logs. Retain push transport and callbacks while the Firebase/Web Push
  privacy review continues. No runtime traffic result is claimed.

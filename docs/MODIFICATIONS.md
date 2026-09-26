# Acute Web modifications

This document summarizes the material changes CORE applies to the pinned
Firefox for Android source used by Acute Web. The implementation is defined by
the public overlay, resources, tests, and workflow in this repository.

## Product identity

- Acute Web and Acute Beta use independent Android package identities.
- Acute names, launcher assets, About content, support links, and release
  information replace upstream product-facing branding.
- Mozilla and Gecko references are retained where needed for accurate engine,
  copyright, license, and attribution disclosures.

## Privacy and distribution

- Product telemetry, marketing telemetry, crash uploading, and diagnostic
  reporting are disabled in Acute builds.
- Unneeded Adjust preinstallation and package-deletion permissions are removed.
- Sponsored home content and marketing onboarding screens are disabled.
- Signed ARM64 APKs are distributed through GitHub rather than an application
  store.
- The in-app updater checks the matching Stable or Beta GitHub release channel
  and hands installation to Android's protected package installer.

## Interface and accessibility

- Application chrome uses Acute's Midnight interface and CORE blue accents.
- Beta contains the CORE Glass work, including layered translucent surfaces and
  page-aware toolbar composition.
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
- Builds verify ARM64 Gecko libraries, minimized permissions, signing
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

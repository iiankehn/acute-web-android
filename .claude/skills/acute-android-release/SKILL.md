---
name: acute-android-release
description: Prepare and verify an Acute Web for Android Beta or Stable release — version tags, beta-to-main promotion, signed APK checks, and the automatic acute.iiankehn.com website update. Use when asked to release, tag, promote or ship Acute Web on Android.
---

# Release Acute Web for Android

Read `docs/RELEASE_CHANNELS.md` and `docs/RELEASE_AUDIT.md` first; they are authoritative.

## Choose the channel

| Channel | Source branch | Tag | App ID |
|---|---|---|---|
| Beta | `beta` | `vX.Y.Z-beta.N` (GitHub prerelease) | `com.acuteweb.browser.beta` |
| Stable | `main` | `vX.Y.Z` | `com.acuteweb.browser` |

Find the latest tags with `git ls-remote --tags origin`. Version numbers only
increase; signed builds need increasing version codes.

## Before tagging

1. `make audit` passes on the exact commit to be tagged.
2. For Stable, `beta` is merged into `main` through a PR, and the user confirms
   phone, tablet, upgrade-in-place and update-channel testing happened.
   Do not assert this yourself.
3. Branding and user docs (`README.md`, `docs/MODIFICATIONS.md`) describe the release.
4. Draft release notes: user-visible changes, known issues (honestly), supported
   ABIs (ARM64, x86_64).

## Tag

Tagging publishes signed APKs to the public. **Always confirm with the user
before pushing a tag.** Then push the tag; the **Build Android APK** workflow
runs audit → per-ABI unsigned builds → isolated signing with signer continuity
check → immutable GitHub Release with provenance.

## Verify after the workflow

- The release has signed ARM64 and x86_64 APKs plus checksums, and is a prerelease
  only for Beta.
- The website job committed "Update website for vX.Y.Z" to `main`, and the
  links in `docs/index.html` (`data-release-link` / `data-release-version`)
  point at the new assets.
- If a step fails, fix forward with a new version. Never replace published assets.

## Afterwards

Follow `../brain/playbooks/ship-a-release.md` for the CORE Dev article and
other sites, then update `../brain/projects/acute-web.md` status.

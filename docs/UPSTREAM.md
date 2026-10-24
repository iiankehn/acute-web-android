# Upstream maintenance

Acute Web uses Mozilla's open-source Gecko engine and Firefox for Android code
as its upstream foundation. The release workflow and `acute-android.toml` pin a
reviewed, full-length Mozilla commit. Stable tag builds always use that exact
revision.

Manual test builds may accept a different full commit for compatibility
evaluation. Those jobs never receive Acute's production signing secrets and
cannot publish a stable release.

## Updating the upstream revision

For every proposed upstream update:

1. review Mozilla security advisories and release notes;
2. compare changes affecting Gradle configuration, Android manifests, product
   resources, Gecko integration, telemetry, crash reporting, and update APIs;
3. apply the Acute overlay and resolve any fail-closed patch assertions;
4. run the overlay regression suite and a complete GitHub APK build;
5. inspect both ABI packages, signing, permissions, and build-provenance reports;
6. exercise navigation, tabs, private browsing, downloads, saved passwords,
   bookmarks/history, extensions, rotation, and Android lifecycle behavior;
7. install the candidate over the current production release and confirm that
   the signing identity and stored profile remain intact;
8. publish only after physical-device acceptance testing passes.

## Support-channel policy

Acute adopts upstream security fixes deliberately rather than tracking an
unreviewed development tip. The pin follows Mozilla's Firefox for Android
stable releases on this cadence:

- **Every Beta starts by moving the pin** to the newest Firefox for Android
  stable release (a `FIREFOX-ANDROID_*_RELEASE` tag), before other work lands.
- **Out of cycle:** move the pin as soon as Mozilla publishes a security
  advisory that affects Firefox for Android, without waiting for the next Beta.
- Never pin a Beta, Nightly or untagged commit.

Each pin move lands on `dev` through a pull request and must pass the
repository audit, the pinned-upstream overlay check, both native builds, package
verification and signing-continuity checks before it is promoted. The exact
immutable commit remains the source of truth for every Acute build.

## Overlay policy

The overlay is expected to fail when an upstream source layout no longer
matches an audited patch pattern. A failed patch is a review checkpoint, not a
reason to loosen assertions or silently skip a product change.

When adapting to an upstream change:

- understand the upstream behavior before changing the patch;
- update the implementation and its fixtures together;
- preserve Acute branding, privacy choices, and update behavior;
- retain accurate Mozilla, Gecko, copyright, and license disclosures;
- document any user-visible behavior change in the release notes.

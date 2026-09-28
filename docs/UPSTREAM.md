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
5. inspect the ARM64 package, signing, permissions, and build-provenance reports;
6. exercise navigation, tabs, private browsing, downloads, saved passwords,
   bookmarks/history, extensions, rotation, and Android lifecycle behavior;
7. install the candidate over the current production release and confirm that
   the signing identity and stored profile remain intact;
8. publish only after physical-device acceptance testing passes.

## Support-channel policy

Acute adopts upstream security fixes deliberately rather than tracking an
unreviewed development tip. Before 1.0, each proposed Firefox/Gecko update is
tested on Beta and must pass the repository audit, the complete ARM64 build,
package verification, signing-continuity checks, and physical-device acceptance.
An ESR-style maintenance cadence is preferred where the Android source and
GeckoView compatibility can be verified; the exact immutable commit remains the
source of truth for every Acute build.

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

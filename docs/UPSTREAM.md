# Maintaining the Firefox base

The release workflow and `acute-android.toml` pin a reviewed, full Firefox
commit. Tag builds always use that commit. Manual test builds accept another
full commit for compatibility evaluation, but never receive release secrets.

For each upstream update:

1. build the overlay against the proposed Firefox ref;
2. review changes to Fenix's Gradle file, manifest, branding resources, and
   update-sensitive Android APIs;
3. run the overlay tests and a complete GitHub APK build;
4. inspect the tablet smoke screenshots and exercise tabs, navigation, private browsing, downloads, passwords,
   bookmarks/history, extensions, and upgrade installation on devices;
5. audit Mozilla security advisories and release notes;
6. tag the Acute release only after device tests pass.

The overlay fails on unexpected upstream source layouts rather than silently
shipping an incomplete rebrand. When that happens, update its exact patch
patterns and fixtures together.

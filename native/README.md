# Acute native GeckoView — Dev

Independent Android application on `dev`, with GeckoView providing rendering
and native session state. Preserved Fenix code/checkpoints are documented in
[the migration baseline](../docs/NATIVE_MIGRATION.md).

Current batch: `2.0.0-dev.4`, normal/private tabs, encrypted normal-session
restoration, rotation continuity, reload recovery and native tab controls.
Private tabs are never written to the archive. Existing Stable/Beta profiles
are not read or migrated.

Build with Java 17 and SDK 37.0 / Build Tools 36.0.0:

```sh
cd native
./gradlew :browser-core:test :app:lintDebug :app:assembleDebug :app:assembleDebugAndroidTest
```

On a disposable Android 12+ emulator, `./run-device-tests.sh` runs actual Gecko
privacy/restoration tests and a process-death acceptance sequence. The native
workflow runs them on Android 12 x86_64 before uploading the candidate. Physical
ARM64 and Waydroid/adaptive input acceptance remain required.

Prototype package: `com.acuteweb.browser.dev`. Production release publication
and Stable/Beta migration remain disabled. Signing continuity for Dev upgrades
is a separate channel gate; never uninstall Stable/Beta for a Dev preview.

CI session/privacy acceptance passed in run 38203694137 (five runtime tests and
two force-stop stages). Signed Dev push artifacts use the existing certificate,
checked against v0.2.0. Initial debug previews require a one-time **Dev-only**
reinstall to switch signers; this removes the Dev test profile. Later signed
candidates can update in place. Use `acute-dev-signed`, not the debug artifact,
for that channel. No public release is published by the native workflow.

Dev.3 adds Mozilla Places-backed normal history and bookmarks. The Library menu
shows the 100 latest bookmarks/visits; tap to open and hold for edit/delete.
Saving a bookmarked URL updates its title without creating another duplicate.
Private mode hides the normal library, never records visits and never queries
normal visited-link status. Places uses its maintained schema in this Dev
profile only; it is app-private, not encrypted by this integration.

The Dev.3 follow-up passed CI run 38206717768: 18 core tests, 12 Android runtime
tests, and both force-stop stages. Corrupt Places files are checked read-only
before opening so upstream automatic recreation cannot discard them. Native
link actions retain URL encoding and optionally remove known tracking names.
Dev.4 adds validated Android HTTP/HTTPS link intake into fresh normal tabs;
its Android acceptance and signing passed in CI run 38208036301 (13 runtime tests
and both force-stop stages).

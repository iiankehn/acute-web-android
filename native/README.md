# Acute native GeckoView — Dev

Independent Android application on `dev`, with GeckoView providing rendering
and native session state. Preserved Fenix code/checkpoints are documented in
[the migration baseline](../docs/NATIVE_MIGRATION.md).

Current batch: `2.0.0-dev.2`, normal/private tabs, encrypted normal-session
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

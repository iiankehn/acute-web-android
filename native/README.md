# Acute native GeckoView — Dev

Independent Android application on `dev`, with GeckoView providing rendering
and native session state. Preserved Fenix code/checkpoints are documented in
[the migration baseline](../docs/NATIVE_MIGRATION.md).

Current batch: `2.0.0-dev.7`, normal/private tabs, encrypted normal-session
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

Dev.5 adds authenticated Gecko response-stream downloads using Android's
Create Document picker. Choose Save on the download prompt, then choose a file.
Downloads this session shows progress; tap an active transfer to cancel or a
completed one to open it. One transfer is accepted at a time, with a 2 GB limit
and a two-minute picker deadline. Private saves explicitly warn that the file
will remain on disk. Closing all private tabs cancels private transfers and
clears their in-memory records, while preserving files explicitly exported.

Transfer metadata is process memory only. Process death interrupts downloads;
background completion/resume is not guaranteed. Failed/cancelled transfers can
leave partial selected files; Acute does not delete user-selected documents.
No new storage/notification permissions or persistent URI grants are added.
Dev.5 acceptance and signing passed in CI run 38213421174: 22 core tests,
19 Android runtime tests and both force-stop stages. The signed candidate is
available in that run's `acute-dev-signed` artifact. Physical file-picker,
ARM64 and Waydroid acceptance remain outstanding.

Dev.6 adds first-level Save as PDF and Print page actions. Gecko generates the
complete PDF document; PDF saves use the existing explicit Save/document-picker
flow and session download controls. Print opens Android's print service and is
hidden on Automotive or devices without printing support. Private printing
requires separate explicit consent before copying the document to temporary
app cache and Android's print spooler. Print services may retain exported data.

Print copies are limited to 64 MiB, are removed on print completion/cancellation,
and leftover owned copies are cleared at the next app start. Paper options use
the already generated PDF layout rather than reflowing Gecko. Generation is
cancelled when switching pages, rotating or backgrounding; late streams are
closed. No screenshot stitching, permission additions or persistent document
index is introduced. Dev.6 Android acceptance/signing is pending CI.

Dev.7 adds manual normal background-tab suspension from the tab list and Tabs
menu. Gecko state capture completes before closing a session; selecting the tab
restores it. Private/active tabs and current transfers are excluded. Failed or
oversized capture leaves the tab running. Named workspaces and automatic
memory-pressure policies remain later work. This batch also finishes Dev.6
print cancellation acceptance and adds confirmed archive recovery plus actual
normal/private popup checks. See NATIVE_MIGRATION.md for validation status.

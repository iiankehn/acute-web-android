# Local crash review validation

Status: implementation under review; no physical-device result recorded.
Use the isolated Dev package, not a daily-use profile. The collector handles
main-process Java/Kotlin uncaught exceptions only. Native/tab crashes, ANRs
and force-stop are not crash-record tests.

1. Install the tested Dev APK and launch it once.
2. With adb connected, use `adb shell am crash com.acuteweb.browser.dev` to
   request an Android test crash. This deliberately terminates Dev; it does
   not erase its profile. Record the APK version and Android/device details.
3. Relaunch Dev. Open About › Report an issue, verify Include last crash is
   available and unchecked. Select it, then Review issue draft.
4. Confirm version, Android version, model and useful stack frames are present.
   Confirm messages, paths, URLs, account data and page contents are absent.
5. Cancel. Confirm no browser navigation or network request was made by the
   report flow. Repeat, edit the draft and press Open GitHub draft. Verify
   GitHub shows the reviewed text without submitting an issue.
6. Delete local crash. Reopen the flow and confirm no record is offered.
   Repeat after app restart. Check a second crash replaces the first.
7. Check rotation/back/cancel, large text, no browser handler and oversized
   drafts. Rotation can reset the local editor; it must never send the draft.
8. Confirm normal browsing, private browsing and Android crash termination
   behavior remain intact. Exercise storage failure where a controlled test
   environment permits it; no success claim until it is observed.

The local behavioral sanitizer suite requires a Java 17+ runtime with the
`jdk.compiler` module (in addition to the existing Python and Node tools).
Run `make audit`; APK compilation and emulator smoke run in GitHub Actions.

## Automated review-flow coverage

The standard emulator smoke sequence now opens Settings › Report an issue,
checks that Include last crash is unchecked, opens the preview, checks that
unchecked crash details are absent and cancels back to Settings. It never
presses Open GitHub draft or includes a saved crash. The foreground guard stays
active before each tap. This exercises the review UI on both CI profiles;
it does not establish forced-crash capture, deletion or network-capture results.

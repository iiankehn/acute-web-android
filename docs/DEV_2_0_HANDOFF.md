# Android 2.0 reviewed-source handoff

## October 17 Beta audit continuation

Current Dev base `93995d8f1954d7bd48ba8aaef841c4755c8e8a5f` passed Build 94 on
both architectures, including signing. Local follow-up patches are on
`fix/2.0-beta-hardening`; they have not been built into a new APK.

See [BETA_2_0_AUDIT.md](BETA_2_0_AUDIT.md) for repository-wide source findings,
patches, dependency evidence, validation limits and physical-device acceptance.
The 712-package OSV source inventory produced three vulnerability matches and
three unmaintained notices. Vulnerability applicability/native artifact fixes
remain open. Do not describe the dependency review as clean or Beta as ready.
The Firefox 158 clipboard provider already disables exported access while
allowing URI grants; the prior exported-provider concern is superseded by the
current source inspection and must still receive compiled/device verification.

## October 15 continuation

Dev `ead6dba25401fbea42d2842c967408df097ed73c` completed Build 91 successfully:
both ABIs compiled, passed APK policy checks, and produced signed artifacts with
signer continuity. Public release/website jobs correctly did not run.
Run: https://github.com/iiankehn/acute-web-android/actions/runs/38306153873

The compiled x86_64 manifest review found an unused Adjust lifecycle provider
contributed by an AAR. The follow-up removes that provider with a manifest-merger
rule and adds a targeted compiled-manifest gate before unsigned artifact upload
and signing. This is not evidence of actual tracking traffic; runtime egress
testing is still outstanding. Keep Firebase/web-push and browser entry points.
Do not promote this follow-up before source/upstream checks pass; its resulting
APK must then prove the provider is absent. Stable/Beta/archives remain untouched.

The same continuation targets Firefox Android 158.0 release commit
`3c71aeacdb296402e41fb2084b13e797d1770642` (verified release tag and Android
version file). It adapts the wordmark's rename to `WordmarkAndLogo.kt` and checks
all transformed sources. The prior empty crash-reporting service configuration
would violate upstream's constructor requirement; reporting is now explicitly
disabled and the guard accepts empty lists only when disabled, while preserving
the requirement for enabled reporters. Compilation and on-device launch of this
new checkpoint still need verification. Do not treat Build 91 as runtime acceptance.

Next acceptance: launch both signed Dev variants, phone/tablet Back/Forward and
menu behavior, install-over/profile preservation, runtime traffic verification,
clipboard provider URI access review, and transitive dependency scanning. The
independent GeckoView migration and CORE Glass remain out of scope.

## Earlier reviewed-source checkpoint

Repository: `iiankehn/acute-web-android`. Review branch:
`wip/android-2.0-native-ui-2026-10-12`; promotion target: `dev`.
Stable and Beta refs and `archive/native-geckoview-2026-10-12` must remain unchanged.

The original WIP below has been reviewed and repaired. The audit-script error, stale Glass fixtures,
missing menu handlers and runtime privacy gaps are fixed. Android 12 is enforced. Restored vital lint
and added real upstream/output invariants plus metadata shell execution tests. 47 regressions pass.
See [DEV_2_0_SECURITY_AUDIT.md](DEV_2_0_SECURITY_AUDIT.md) for evidence, scope and remaining gates.

Next: validate the final immutable upstream check, promote the reviewed source to Dev, and inspect
both GitHub build/signing results. A source pass is not an accepted APK. Device checks, traffic
verification and a transitive dependency scan remain pending. No public release is requested.
The large-screen tab strip remains separate; do not claim a merged tablet capsule row.

---

## Original checkpoint (historical; superseded status)

# Fresh Acute Android 2.0 — unfinished handoff

Checkpoint branch: `wip/android-2.0-native-ui-2026-10-12`.
Repository: `iiankehn/acute-web-android`.
Base commit: `bf182a139f668749e4441a27759a0ed3fef1bf9a`.
This checkpoint is WIP and must not be treated as an accepted APK or release.
The `dev` branch still points to the stable baseline; this checkpoint has not
been promoted into Dev. Stable/Beta are unchanged.

## Current user direction

Start fresh on the established Fenix-based codebase, with Dev representing 2.0.
Remove CORE Glass. Make Android chrome feel native while retaining Acute/CORE
branding and the canonical artwork. Improve navigation using inspiration from
Acute iOS: Back always visible, Forward when available, capsule address controls
and grouped More actions. Use Android components and maintained Fenix handlers.
Perform a complete security/dependency/build audit and apply needed updates.
Android 12+ and ARM64/x86_64 remain the intended device targets.

The independent GeckoView application migration is paused and archived in
`archive/native-geckoview-2026-10-12`. Do not resume it or import its unfinished
extension manager into this fresh 2.0 work unless the user changes direction.
That archive contains all native history, unpushed work and its own handoff note.

## Changes preserved in this checkpoint

- Replace translucent Glass tokens with opaque `acute_native_theme.xml` colors.
- Remove custom Glass compositing, viewport clipping and forced post-load toolbar
  collapse. Keep the upstream opaque toolbar and normal viewport behavior.
- Outline opaque address capsules without replacing upstream origin/security UI.
- Use existing Fenix Back/Forward actions in the main address row. Forward is
  conditional; wide windows retain Refresh/Stop. Phone Refresh/Stop remains in
  the menu. Remove the separate expanded navigation row and hide its obsolete
  layout/shortcut settings. Large-screen tab-strip merging is not implemented.
- Group existing menu handlers under Navigation, Page, Library, Extensions and
  Settings/account headings. Keep existing Sync/password/extension integrations.
- Propose Firefox Android 157.0.1 release source pin
  `0c469c2352451630bc69fc328c9f0c589c6c534d`, replacing the September 19 pin.
  Mozilla's October 6 release notes explicitly list a security fix:
  https://www.firefox.com/en-US/firefox/android/157.0.1/releasenotes/
  https://www.mozilla.org/en-US/security/advisories/mfsa2026-104/
- Restore a Fenix Dev package `com.acuteweb.browser.dev`, label Acute Dev and
  `2.0.0-dev.NUMBER` CI artifacts. Proposed pipeline signs isolated Dev artifacts
  with existing credentials but does not publish Dev releases. Verify this fully
  before promotion. Future Beta candidate metadata is 2.0.0-beta.1.
- Disable the release updater in Dev. Reject updater credentials, query/fragment,
  nonstandard ports and noncanonical encoded paths; disable API redirects.
- Add failure-path cleanup for signing material, package/debuggable checks before
  signing, and an immutable-source overlay compatibility command.

## Actual validation so far

Python syntax compilation and `git diff --check` passed. The updated Dev overlay
successfully applied to downloaded real files from the 157.0.1 release pin,
including the toolbar, menu and English resources. This checks source-pattern
compatibility, not Kotlin compilation, all locales, APK execution or device UX.

The complete regression suite was NOT run after these edits. Existing test
fixtures/assertions still describe the old Glass theme and previous channel/pin
and must be updated meaningfully. No new APK build has been started for this
checkpoint. The new security/pipeline checks are not yet proven by CI. The audit
is incomplete; do not claim that the app is security-certified or fully updated.

## Next steps

1. Review the WIP diff, correct any UI/pipeline mistakes and update fixtures/tests.
   The new overlay requires BrowserToolbarMiddleware.kt and MainMenu.kt fixtures;
   customization fixtures need the current toolbar layout/shortcut setup.
2. Run `make audit` and `make upstream-check`; verify all three channel packages,
   labels, privacy flags and preserved viewport behavior against real upstream.
3. Complete the security review, including dependency/runtime telemetry controls,
   permission/exported-component boundaries, update validation, signing continuity,
   current upstream advisories and build/lint coverage. Verify the Android 12+
   baseline and retain the fixed single-ABI packaging on both architectures.
4. Only after source checks pass, move the reviewed changes into Dev and run the
   full Fenix APK build/signing checks. Test phone/tablet navigation, resizing,
   private browsing, saved data and install-over behavior. No public release was
   requested by this handoff.

## Conversation logistics

The user reported a VPN used for Acute iOS testing and suspects it contributed to
chat interruptions; that cause was not verified. They requested a fresh Work chat
because this thread had become unwieldy. Give concise progress updates during
work and do not present pending checks as complete.

Resume by checking out this WIP branch, reading this note and reviewing its diff
against the base commit. Preserve the archived migration and live release refs.

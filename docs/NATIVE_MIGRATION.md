# Independent GeckoView migration — working baseline

Decision: keep Kotlin, GeckoView, Android platform APIs and useful maintained
Mozilla libraries. Acute owns the application UI and feature integration.
Fenix is a reference implementation, not the new application's build input.
This document supersedes the overlay-first implementation direction, not the
product requirements, in ACUTE_2_0.md. No public 2.0 beta is authorized by this work.

## Preserved code and rollback

Public checkpoint branches created before native implementation:

| Branch | Exact commit |
|---|---|
| archive/pre-native-2026-10-12-main | bf182a139f668749e4441a27759a0ed3fef1bf9a |
| archive/pre-native-2026-10-12-beta | 3047668e8761d434168c0875f617400ab57455c2 |
| archive/pre-native-2026-10-12-2.0 | b046c07d693cad59a56afae51e4edc45779b9d92 |

These retain full Git ancestry. Treat checkpoint branches as read-only; no
repository branch-protection rule has been configured by this change. Original
main, beta, and feature/2.0-foundation are not advanced by the migration.
The existing overlays, resources, extensions, tests and release pipeline remain
in this branch as well. Their pinned Mozilla source remains reproducible using
the existing upstream instructions. No upstream source is vendored here.

To revisit the old implementation without rewriting a live branch:

```sh
git fetch origin
git switch -c recovery/old-2.0 b046c07d693cad59a56afae51e4edc45779b9d92
```

Source rollback is separate from installed-data rollback. Android normally
rejects lower version codes; reverting a binary also requires compatible data
schemas and the original signer. Never promise an APK downgrade from these
source checkpoints. Migration must preserve old stores and avoid destructive
schema changes until upgrade and recovery tests pass.

## Initial repository findings

The repository is an overlay/build controller, not a standalone Fenix checkout.
`scripts/apply_overlay.py` rewrites upstream Kotlin, XML and Gradle inputs.
Workspaces, suspension, dashboard, menus, PDF/Print, privacy configuration and
branding are coupled to upstream implementation details. Engine packaging uses
Firefox artifact builds per ABI, with a separate signing job and signer checks.
`main` contains newer Waydroid/native verification fixes absent from the older
2.0 foundation. Those must be reconciled explicitly before promotion.

## Ownership boundaries and first slice

- `native/browser-core`: engine-neutral product interfaces and tested navigation
  policy; no Android, Gecko or Fenix imports.
- `native/app`: Android application and native platform controls; Gecko types
  confined to the runtime/adapter and view host.
- GeckoView stable `157.0.20261005135250`: exact Maven coordinate, confirmed in
  Mozilla Maven metadata and source JAR on 2026-10-12. This is a prototype pin,
  not a certified replacement for the current security-reviewed upstream pin.
  Its Maven POM records Mozilla release source revision
  `737ec77d798755890b062aab541a90d6c75afd19`.
- Gradle distribution 9.3.1 (wrapper bootstrap 8.13) with distribution checksum; AGP 9.1.1 with built-in Kotlin and Kotlin 2.4.20,
  Java 17, compile SDK 37 / target SDK 35, Android 12+ minimum.
- Universal development APK includes ARM64 and x86_64. CI verifies native entries.
- Source files remain MPL-2.0. The Gradle wrapper retains its Apache-2.0
  notices; GeckoView and reused artwork retain their existing upstream notices.
  Complete dependency notice/source mapping is a release acceptance requirement.

This first slice provides navigation/search, back/forward/reload, engine status,
validated URL-only recreation, window/IME insets and native accessible controls.
Permissions are denied until the app-owned permission flow is implemented.
Privileged schemes and external intent navigation are denied. New windows
are supported by the subsequent session batch described below. No telemetry or crash-upload SDK/handler is integrated.
Gecko network defaults, Safe Browsing, remote settings and extension traffic
still need an explicit privacy/network audit; no zero-network claim is made.
CORE Glass here is an opaque neutral capsule foundation; translucency and
adaptive component polish are still pending. No single-tab prototype behavior
is counted as tab/session feature parity.

Prototype package is `com.acuteweb.browser.dev`, with backup disabled.
Local/PR previews are debug signed; accepted Dev pushes use the existing isolated
release-signing job, without publishing a GitHub release. It cannot update stable or beta, and does not read their data.
This is deliberate while migration is unproven. Final stable/beta packages and
production signing identity must be retained at promotion. Reuse the existing
isolated signing flow; do not introduce release secrets into prototype CI.

## Feature parity inventory

| Existing capability / implementation | Planned reuse or extraction | Acceptance gate |
|---|---|---|
| Gecko rendering and navigation | GeckoView supported APIs via adapter | TLS errors, redirects, web compatibility, content-process crash |
| Tabs, private mode, workspaces and suspension / Fenix + local group store | Evaluate browser-state and maintained engine-session middleware before selecting a store | Normal/private isolation, process death, suspend/restore, bounded memory |
| Bookmarks and history / Mozilla storage | Evaluate Android Components storage + Application Services; retain schema | Counts, metadata, CRUD and restart after upgrade |
| Passwords / Mozilla login store | Reuse maintained encrypted storage and autofill integrations | Keystore/schema compatibility, no plaintext export, locked device |
| Firefox accounts and Sync | Reuse maintained account/sync libraries selectively | Existing account, token handling, sync conflict and sign-out |
| Extensions and permissions | GeckoView WebExtension controller + compatible maintained manager | Install/update/revoke, private access, popup, content permissions |
| Notes, Saved Sessions, Site Display / built-in extensions | Keep extension sources and data formats; audit host API requirements | Existing extension storage survives, private exclusions, failure recovery |
| Downloads and file handling | Evaluate maintained download component; Android storage APIs | Authenticated downloads, filename sanitization, cancellation, scoped storage |
| PDF and Print | Gecko document APIs and Android PrintManager | Long pages, protected documents, memory and URI grants |
| CORE Glass, dashboard, menus, keyboard/mouse | Acute-owned native Android UI components | Phone/tablet/desktop sizing, resizing, accessibility, focus, page reachability |
| GitHub updater | Extract version/ABI/channel logic from existing provider | Same signer, higher version code, correct ABI and channel |
| Privacy configuration | Port reviewed settings individually, no Fenix defaults assumed | Network/permission audit, tracking tests and no telemetry uploads |

Data store paths, schemas, versioning and encryption still require inspecting
the pinned full Mozilla source and a real installed profile. Names above describe
known implementation ownership, not verified migration mappings. Do not copy a
profile wholesale or delete legacy stores. Establish read-only inspection,
compatibility adapters, transactional import, failure recovery and upgrade
fixtures before allowing an in-place native update.

## Order of subsequent implementation

1. Obtain passing independent compilation/lint and on-device engine launch.
2. Inspect maintained Mozilla component dependency graphs and actual data stores;
   choose reusable tab/state, storage, account, extension and download components.
3. Implement session lifecycle, restoration and private-mode boundaries before
   adding dashboard and workspace behaviors.
4. Migrate feature services and native UI incrementally with parity checks.
5. Verify package/signer/version continuity and transactional data migration.
6. Test engine upgrades, ARM64/x86_64 including Waydroid, accessibility and input;
   only then prepare a public beta.

Measure independent build duration, dependency graph size, engine upgrade impact,
crash/restoration failures and feature acceptance against the preserved build.
A green build alone does not establish feature parity or migration safety.

## Foundation validation (2026-10-12)

Local Java 17 / SDK 37.0 build passed `:browser-core:test`, `:app:lintDebug`
and `:app:assembleDebug`. All 3 navigation policy tests passed. Android lint
reported 0 errors and 5 warnings (target/tool versions, launcher shape and localization). The APK contains only
ARM64 and x86_64 libraries; ELF class and machine identifiers were verified for
libxul and libmozglue in both ABIs. The existing 45 Python regression tests,
10 extension behavioral tests, project checks and security/release audit passed.
Physical-device foundation launch was subsequently confirmed by the user.
Broader native UI acceptance, network audit and migration testing remain outstanding. These results do not certify a public beta.

## Session/privacy batch — 2.0.0-dev.2

The user confirmed a successful physical-device launch of the foundation on
2026-10-12 UTC (2026-10-11 local). CI run 38199131060 passed before that check.
This records launch acceptance, not certification of the subsequent features.

Implementation now adds normal/private tab selection, bounded tab creation
(32 normal, 16 private), lazy restored sessions, background deactivation,
process-owned sessions across Activity recreation, and reload recovery after
Gecko content-process crash/kill. Gecko's own `SessionState` supplies navigation
history and restorable document state; Acute does not implement another history
engine. New-window navigation inherits its parent mode and rejects background
requests and non-gesture popup loads. Gecko receives an unopened child session
as required by the pinned API.

Normal tab snapshots use Kotlin Serialization JSON 1.11.0, authenticated AES-GCM
with a non-exportable Android Keystore key, and Android AtomicFile replacement
in noBackupFilesDir. File I/O is serialized off the main thread. A failed read
keeps the existing archive intact and disables replacement; failed writes retain
the previous committed archive and can retry. Input/version/size/duplicate-ID
validation is fail-closed. Unsupported/oversized Gecko snapshots fall back to
loading the recorded web URL. Saved state is bounded to 256 Ki characters per
tab and 12 MiB per archive. Abrupt termination before the next durable write
can lose the newest unsaved change; no synchronous-force-stop guarantee is made.

Private tab metadata and Gecko state stay in process memory. Private sessions
use Gecko private mode and a separate randomly generated session context; all
private tabs in one window share that context. Closing the last private tab
clears it and the next private window receives a fresh context. Closing the app
closes private tabs; ordinary backgrounding/rotation preserves the live private
window. Android bundles and backups never receive browser view state. Private
windows/dialogs enable FLAG_SECURE. Switching tabs discards the old Gecko
surface/autofill hierarchy; protection stays until a normal frame is drawn.
This is private browsing, not an anonymity or zero-network promise.

Native UI adds tab count/chooser, clear private-mode labeling, grouped page/tab/
privacy menu actions, large-window tab capsules at 600dp, and Ctrl+L/T/W/Tab and
Ctrl+Shift+P. The launcher is singleTask: multi-window *resizing* is supported,
but independent simultaneous Acute windows are deferred.

### Component decision

The browser-state 157.0 Maven POM was inspected. Its transitive graph includes
concept-fetch/awesomebar/engine/storage, lib-state, support modules, Compose and
coroutines. For this limited integration, importing it would expand the app's
state/dependency surface without replacing Gecko's supported state persistence.
This batch therefore reuses Gecko/Android primitives and the maintained Kotlin
serializer. Android Components storage, Sync, extensions and download libraries
remain candidates for their corresponding feature services; they are not
rejected wholesale.

### Acceptance coverage

Core tests exercise normal/private selection, private-data exclusion, closed-tab
restoration, snapshot bounds, stale-document invalidation, authenticated
encryption, fresh nonces and tamper/wrong-key rejection. Android instrumentation
uses a local offline fixture with the actual Gecko engine, Android Keystore and
AtomicFile. It checks normal/private cookies, private-window context isolation,
Gecko history restoration, rotation/session identity and screenshot protection.
Two additional instrumentation stages are separated by `am force-stop` to
verify restoration in a newly started app process. These test runs are gates in
the Dev workflow, not claims of passing before execution.

Stable/Beta profile migration, bookmarks/history services, downloads, passwords,
Sync, extensions and workspaces remain outstanding. This batch does not import
or modify stable/beta data stores or archive checkpoints.

Local batch validation: 14 core tests, 45 preserved Python tests and 10
extension tests passed; application and instrumentation APKs compiled, lint
reported no errors, and both ELF/ABI packages were checked. A reproduced stale
instrumentation symbol-cache collision was removed by clean compilation; the
small native project disables Kotlin incremental compilation for reliability.
Android runtime/process-death acceptance passed in CI run 38203694137:
all five Android tests plus both force-stop stages succeeded. The initial
process-death harness failed because Gradle uninstalled the test APKs; explicit
reinstallation fixed the harness, followed by a full successful rerun.

## Dev signing continuity

Accepted pushes now build an unsigned release variant and pass it to an isolated
signing job. Only that job receives the existing `release-signing` environment
credentials; PRs/manual runs do not sign. The job validates the separate Dev
package ID, build version code, non-debuggable variant and exact merged
permission allowlist before signing, then compares the certificate with v0.2.0
before uploading. There is no release publishing job in this workflow.

The initial dev.1/dev.2 debug previews cannot be updated by the production signer.
Switching requires uninstalling **Acute Dev only**, losing its test profile, then
installing the signed Dev candidate. Stable/Beta must remain installed and their
data is untouched. Subsequent signed Dev builds retain their signer and monotonic
workflow version codes. Real installed-profile upgrade/Keystore acceptance still
requires device testing; certificate checks alone do not establish data parity.

The merged APK also contains Gecko's normal network-state, wake-lock and audio
settings permissions and AndroidX's app-local signature permission. It is not an
INTERNET-only merged manifest. None are runtime camera, microphone, location or
storage grants. The signing gate rejects any unexpected permission change.

## Library batch — 2.0.0-dev.3

The browser-storage-sync 157.0 source and Maven dependency graph were inspected.
It wraps Application Services Places, adds account/sync concepts, WorkManager,
remote tabs and autocomplete concepts. The narrow local integration uses
`org.mozilla.appservices:places:157.0.1` and its public generated native binding
directly, behind `PlacesStore`. It retains Mozilla's Rust database schema and
CRUD/visit APIs; no replacement SQLite schema or custom history engine is built.
The exact pin and native acceptance tests are the upgrade contract for this
boundary. Full-megazord and JNA are its native dependencies, packaged for both
supported ABIs. Glean's Android artifacts are explicitly excluded from Gradle
configurations; neither Glean, account nor Sync initialization is performed.
The native megazord still contains other crates, so this is not a claim that
every telemetry-related symbol has been removed from native binaries.

Normal top-level successful Gecko visits are persisted through HistoryDelegate,
including redirect flags; title updates use Places observations. Normal visited
link queries run off-main. Private mode is rejected at the storage boundary:
no visits/titles/bookmarks are written and visited-link queries return all false
without opening the database. The native Library menu is hidden in private
mode and any open library dialog closes on a private-mode transition.

Native controls support bookmark save/upsert/title and URL edit/delete, opening
bookmarks/history, per-URL visit deletion and clearing normal history while
retaining bookmarks and open tabs. Lists explicitly show the most recent 100;
folder management, full-library search/pagination and richer accessibility/UI
polish remain later parity work. Writes disable the Save button until completion;
failures retain the editor and show a storage error. Background history failures
also surface in the normal-mode status.

Places lives at Dev noBackupFilesDir/places.sqlite; SQLite manages transactions
and its schema. The store is app-private and excluded from backups, but is not
encrypted by this batch. It never opens an existing Stable/Beta profile. Failure
to open a database prevents subsequent writes without deleting/recreating it.
Stable/Beta transactional import and existing schema/Sync metadata mapping remain
unverified and are not enabled.

New Android tests cover bookmark CRUD/upsert/stable IDs after reopening, private
write/query rejection, history clearing without bookmark loss, corrupted-file
preservation and actual Gecko normal/private visit callbacks. Force-stop stages
also check normal Places history/bookmarks after process replacement. Runtime
acceptance for this batch is pending the next CI run.

### Corruption gate found by runtime acceptance

Run 38205229678 passed compilation, lint, dependency exclusion and all four
native ABI entries, but failed the corruption-preservation test: Places'
constructor automatically recreated a damaged database instead of throwing.
The adapter now inspects existing files read-only with SQLite `quick_check`
before handing them to Places, with an explicit no-op Android corruption
handler to avoid the platform's default file deletion. Failed inspection keeps
the original file and blocks later writes. This is an integrity inspection,
not a replacement schema or storage engine. Its compatibility with this pinned
Places schema is exercised by database reopen and process-death tests.

The follow-up also ports the existing conservative clean-link policy and native
link context actions (open in current-mode tab, copy, share, optional clean copy).
Normal library dialogs and link dialogs are dismissed when their owning tab or
Activity changes. Private dialogs enable screenshot protection; Android 13+
clipboard entries from private mode suppress previews. Copy/share are explicit
user exports to Android's clipboard/share sheet, with no background request.
Downloads remain pending feature work; an ignored Gecko external response now
closes its body stream and reports unsupported download handling rather than
leaking the connection. New tests cover URL byte preservation, link scheme
validation and external stream closure.

The corruption/context follow-up passed build job 114671710238 in CI run
38206717768: 18 core tests, all 12 Android tests, and both force-stop stages.
Both corrupt-file preservation cases passed, as did Places reopen compatibility,
actual Gecko visits, private exclusions, archive restoration and adapter stream
closure. Lint and all four native libraries for both ABIs passed. The isolated
signing job also passed and uploaded the certificate-verified Dev.3 candidate.

## Android link intake — 2.0.0-dev.4

The Dev launcher now advertises HTTP/HTTPS VIEW/BROWSABLE handling. Incoming
links are validated before engine use and queued until session restoration has
finished. Every external link opens a fresh normal tab; it does not replace or
reuse a private session. The consumed Intent data is cleared so rotation cannot
open duplicate tabs. Unsupported schemes/credentials and oversized links are
rejected, and the existing tab limit applies. Android acceptance tests deliver
an actual VIEW Intent while private mode is active, check the normal session
boundary, and verify rotation does not duplicate the link.

The initial Dev.4 Android run passed link delivery/private isolation, but
ActivityScenario could not follow the resumed Activity after the NEW_TASK
handoff and timed out on recreation. The test now launches the real app task,
observes Android lifecycle transitions directly, requires singleTask to reuse
the same Activity, and checks recreation against the newly resumed Activity.
The privacy and duplicate-tab assertions remain intact.

## Accepted Dev.4 checkpoint

CI run 38208036301 passed build and isolated signing jobs for commit
634e2ffc33ac91ceed0b5c02c5641e8f6248b484. Acceptance includes 18 core tests,
all 13 Android runtime tests, both cross-process force-stop stages, 45 preserved
Python tests and 10 extension tests. Lint, permission boundary, telemetry artifact
exclusion, ARM64/x86_64 native entries, non-debuggable release packaging and
certificate continuity all passed. The real-task test verified reuse of the
same singleTask Activity, preservation of the private session until explicitly
closed, normal external-link handling, and no duplicate tabs after recreation.

Separate inspection of Places/JNA source AARs verified ELF64 machine identifiers
183 (ARM64) / 62 (x86_64) and 16 KiB PT_LOAD alignment. This is a binary check,
not physical ARM64, Waydroid or 16 KiB-runtime certification. Extended physical
UI/input/privacy checks and Stable/Beta migration remain outstanding.

Original main, beta, feature/2.0-foundation and all three pre-native checkpoint
refs were rechecked and still match the preserved hashes above. The tested Dev
candidate does not modify those sources or installed Stable/Beta profiles.

## Download batch — 2.0.0-dev.5

The owned flow consumes Gecko ContentDelegate.onExternalResponse's existing
InputStream, preserving the authenticated browser request without refetching
it through another HTTP client. Gecko's pinned stream source was inspected:
its underlying channel remains suspended until reads resume it. The app uses
Android ACTION_CREATE_DOCUMENT, CATEGORY_OPENABLE and ContentResolver's
cancellable descriptor API; no broad storage or notification permission is
introduced. The system picker creates a new document rather than overwriting
an existing document, as documented in Android's Storage Access Framework:
https://developer.android.com/training/data-storage/shared/documents-files

`DownloadPolicy` supplies bounded filename/MIME validation and fixed-buffer
stream copying, cancellation, declared-length/truncation checks and a 2 GiB
limit. Encoded responses do not use encoded Content-Length as a decoded-byte
length. `DownloadController` owns one stream/picker/transfer at a time, off-main
file I/O, throttled progress, resource closure, a two-minute pending deadline,
and at most 20 records per browsing mode. Picker ownership survives Activity
recreation in process memory and prevents an expired/cancelled picker result
from being applied to another request. Closing the Activity abandons its picker;
closing the last private tab cancels private transfers and removes their records.

Native UI asks for Save before launching the picker, warns before exporting a
private file, and presents mode-filtered session downloads with cancel/open
controls. Private prompts/lists enable FLAG_SECURE. Download filenames, URIs,
metadata and bytes are never added to session archives, Android bundles, Places
or backups. The explicitly chosen output document persists outside the profile,
even after private-window close. Partial documents are retained on failure or
cancellation; existing user documents are never automatically deleted.

This is a foreground/session transfer flow, not an Android DownloadManager or
foreground-service implementation. Process death loses transfer metadata and
interrupts active writes; there is no resumable or guaranteed background
completion claim. Blob/data downloads, HTTP range resume, dashboard persistence
and long-term download indexing remain future work. Only supported HTTP(S),
status-200 responses with bodies enter this flow. No public beta is published.

Core tests cover filename/MIME validation, bounded memory/reads, stream closure,
cancellation/write failure and truncated/oversized responses. Android fixtures
use unique app-owned MediaStore destinations on the disposable emulator. Tests
cover actual cookie-authenticated Gecko bytes with exactly one HTTP request,
stale-picker rejection, truncated/unwritable destinations, explicit private
export preservation, active private-transfer cancellation, and private prompt
consent/rotation/close lifecycle.

## Accepted Dev.5 checkpoint

CI run 38213421174 passed build and isolated signing jobs for commit
803704104d590228957bfafe3bbfae9497dc4724. All 22 core tests, 19 Android runtime
tests, both cross-process force-stop stages, 45 preserved Python tests and
10 extension tests passed. Lint, dependency exclusion, both native architectures,
the permission boundary and certificate continuity passed. Signed artifact:
https://github.com/iiankehn/acute-web-android/actions/runs/38213421174/artifacts/11731385134

The first runtime run exposed a fixture error: inserting a MediaStore entry
does not create its bytes until a writer opens it. The stale-picker test now
writes known original bytes before rejecting the stale result and verifies those
bytes remain unchanged. All assertions and other download tests passed in the
full rerun. No production logic changed for this fixture correction.

This acceptance uses actual Gecko authenticated responses, real scoped-storage
IPC and native prompt lifecycle on Android 12 x86_64. It does not certify a
physical device's system file-picker/provider flow, ARM64, Waydroid, resumable
background transfers or Stable/Beta migration. The source checkpoints and
original application profiles remain untouched.

## Document export and printing — 2.0.0-dev.6

The pinned GeckoSession source was reviewed before integration. `saveAsPdf()`
uses Gecko's document print machinery for HTML and the PDF.js saver for original
PDF bytes. Acute does not render pages or stitch viewport images. Save as PDF
hands the generated stream to the existing bounded download/document-picker
flow, preserving its private-export warning, lifecycle and cancellation rules.

Print uses the public Android PrintManager/PrintDocumentAdapter APIs. Only an
explicit Print action creates a temporary app-private cached PDF. Private-mode
printing first requires a FLAG_SECURE consent prompt disclosing the app cache,
system spooler and possible print-service retention. The adapter inspects page
count using PdfRenderer but never renders document bytes for printing; it copies
the full Gecko PDF to the spooler and reports ALL_PAGES, leaving selection to
Android. It does not reflow the source after paper-option changes.

Temporary print copies have a 64 MiB bound, fixed-buffer off-main I/O, resource
closure and cancellation checks. Finishing/cancelling a print removes its owned
copy; process-death leftovers are deleted only from Acute's dedicated print-cache
directory at the next app start. Export to the print service is explicit and
does not imply that system/printer copies can be deleted by Acute. Other cache
files, user documents, session archives and Places are unaffected.

Document generation is bound to the current Activity/tab/URI. Switching pages,
rotation, backgrounding or closing invalidates it and closes late streams. Gecko
does not expose a generation-abort handle here; a cancelled generation can
finish internally before its returned stream is closed. Print is hidden on
Automotive and devices without Android printing support. Web-triggered automatic
printing is not wired into this app-owned flow.

Instrumentation covers a real three-page Gecko export with the last page's
visible marker below the viewport, byte-exact descriptor writes, cancelled and
malformed streams, temporary-file cleanup, private-print consent and Android's
actual print-dialog cancellation. CI acceptance/signing remains pending.

## Dev.6 recovery and navigation follow-up

The original Dev.6 run 38215582046 compiled and passed 24 of 25 Android runtime
checks, but timed out waiting for print-adapter cleanup after a single Back
press. The acceptance test now waits between Back transitions and exits the
actual spooler UI, allowing for keyboard/expanded-option dismissal first. It
still requires Android to call onFinish and remove the cached file; the test
does not manually finish the adapter to satisfy the assertion.

Reviewed ZIP fixes were incorporated selectively. Host/port input supports
web hosts, localhost and bracketed IPv6; port bounds apply to explicit URLs as
well as guessed addresses. Exactly about:blank is accepted for Gecko loads and
new windows; privileged schemes and the existing popup gesture gate remain.
A real Gecko touch-input test exercises normal/private blank popups.

Unreadable archives now have an explicit confirmed recovery action. Atomic
replacement writes the current normal snapshot before enabling persistence;
a failed replacement retains the original archive and the recovery action.
AtomicFile's logged rename failure is checked explicitly. Tests cover corrupt
archive recovery and failed replacement followed by retry. Acceptance for this
follow-up run 38219390271 passed print and recovery checks; its new popup
fixture could not locate Gecko content through accessibility. The next run uses
a real touch gesture in a fixed-layout fixture without weakening popup assertions.

## Native background-tab suspension — 2.0.0-dev.7

This is the first native suspension slice for the workspace roadmap. Normal
background tabs may be suspended individually from the tab list or together
from the Tabs menu. Their Gecko sessions close only after an asynchronous Gecko
state callback supplies a bounded snapshot. The tab metadata remains available;
selection creates a fresh session and restores Gecko navigation state.

Selected and private tabs are excluded, as are tabs while a download/document
transfer is pending or active. Selecting or closing a tab cancels its pending
suspension. A five-second timeout, changed location, failed capture or oversized
snapshot keeps the session open. No timer blindly closes a session after flush.
No new persistent format or private-tab disk storage is introduced. Restored
normal tabs remain lazy until selected, using the existing encrypted archive.

Runtime acceptance covers actual session closure, backward history after
selection, cancellation by selection and private exclusion. Cross-process
force-stop acceptance also preserves and lazily reopens a suspended tab.
Named workspaces, grouping UI, automatic memory-pressure policies and complete
form/scroll acceptance remain subsequent work. CI/signing acceptance is pending.

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
Privileged schemes and external intent navigation are denied; new windows are
not yet supported. No telemetry or crash-upload SDK/handler is integrated.
Gecko network defaults, Safe Browsing, remote settings and extension traffic
still need an explicit privacy/network audit; no zero-network claim is made.
CORE Glass here is an opaque neutral capsule foundation; translucency and
adaptive component polish are still pending. No single-tab prototype behavior
is counted as tab/session feature parity.

Prototype package is `com.acuteweb.browser.dev`, debug signed, with
backup disabled. It cannot update stable or beta, and does not read their data.
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
On-device launch, native UI acceptance, network audit and migration testing
remain outstanding. These results do not certify a public beta.

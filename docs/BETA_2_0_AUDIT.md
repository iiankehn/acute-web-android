# Android 2.0 Beta preparation audit — October 17, 2026

Reviewed base: Dev `93995d8f1954d7bd48ba8aaef841c4755c8e8a5f`.
Working branch: `fix/2.0-beta-hardening`. This review adds local patches; it is
not acceptance of a new APK or authorization to publish a release.

## Coverage and limits

The repository-wide source pass covers Acute's overlay transformations,
Kotlin update provider, bundled extension scripts and resources, APK verifiers,
source packaging, upstream fetcher, build/signing/publishing workflows, tests,
and product/build documentation. Artwork is retained; this was not a redesign.

The immutable Firefox input remains
`3c71aeacdb296402e41fb2084b13e797d1770642` (Android 158.0). Mozilla's
[Android release notes](https://www.firefox.com/en-US/firefox/android/158.0/releasenotes/)
and [security advisory](https://www.mozilla.org/en-US/security/advisories/mfsa2026-106/)
were checked against the October 17 release state. No later Android security
release was found in that check. This does not establish that every upstream
dependency is free of known issues.

The complete Mozilla source tree is not vendored here and has not received a
line-by-line security review in this pass. Real overlay-consumed upstream files,
the Rust lockfile, Maven catalog, and selected advisory/provider source were
inspected. Resolved Android dependencies, native binary reachability, runtime
traffic, and physical-device behavior remain separate acceptance work.

## Findings patched in this branch

| Area | Gap | Change |
|---|---|---|
| Signing policy | Negated `grep` checks do not trigger Bash `-e` reliably on a match | Explicit failure paths for debuggable APKs and prohibited permissions, including read errors; shell execution regressions |
| Compiled manifest | Attribution check did not verify backup and app-isolation boundaries | Require disabled backups, no shared UID, one private package-scoped updater without URI grants; check clipboard access if present |
| Exported diagnostics | The actual Build 95 manifest contains Glean's public debug-command activity | Remove `GleanDebugActivity` at manifest merge time and reject its presence in compiled APKs; no claim of observed traffic |
| Signed evidence | Successful artifacts omitted the compiled manifest | Compare unsigned/signed manifest dumps and retain signed manifest reports, without executing repository source in the signing job |
| Dependency evidence | Actual Android runtime graph absent from artifacts | Add bounded Gradle runtime dependency export and retain it with the Rust lockfile per ABI; this step still needs CI execution |
| Action pins | Direct `- uses:` steps escaped the pin-audit regex | Cover both named steps and direct action steps |
| Source packaging | Recursive bundle could include untracked local files and follow links | Package Git-tracked files only, exclude credential/build files, reject unsafe links and missing sources, publish archives atomically |
| Website links | URL validation accepted query/fragment suffixes before HTML insertion | Require an exact canonical asset URL and ASCII semantic-version digits |
| Stable update discovery | Twenty mixed-channel releases could hide the Stable update | Use GitHub's dedicated latest-release endpoint for Stable and retain the separate Beta array response |
| Extension privacy | Popup could show a private tab's hostname and store a per-site preference | Block private contexts/tabs before reading local settings or rendering site controls |
| Extension reliability | Failed/racing storage writes could misrepresent saved preferences | Disable controls until loaded, serialize writes, restore saved state on failure, distinguish reload failures, validate malformed settings |
| Extension upgrades | Modified built-in scripts need a distinct package version | Bump Midnight Pages to `0.1.1` |
| Sync copy | Branding falsely described retained Sync pairing as unavailable | Preserve upstream Mozilla Sync sign-in/pairing instructions and service attribution |
| Documentation | Mixed old pins, Glass behavior, Android 8 support and automatic smoke-test claims | Correct development-source instructions and distinguish manual device tests from CI evidence |

The pinned Gecko clipboard manifest already sets `exported=false` with
`grantUriPermissions=true`. Its implementation serves committed in-memory
clipboard sessions, not arbitrary filesystem paths. The old exported-provider
concern is superseded by this source check; real cross-app copy/paste and URI
permission tests remain required. Source:
[Gecko manifest template](https://github.com/mozilla-firefox/firefox/blob/3c71aeacdb296402e41fb2084b13e797d1770642/mobile/android/geckoview/src/main/AndroidManifest_overlay.jinja),
[provider implementation](https://github.com/mozilla-firefox/firefox/blob/3c71aeacdb296402e41fb2084b13e797d1770642/mobile/android/geckoview/src/main/java/org/mozilla/gecko/GeckoClipboardContentProvider.java).

## Dependency findings: triage remains open

The [OSV API](https://google.github.io/osv.dev/api/) was queried for **712 distinct
package versions**: 557 crates.io entries in the upstream lockfile and 155
explicit Maven catalog versions. There were six matching packages, all Rust.
No match among those 155 Maven catalog entries establishes neither complete
Maven coverage nor a clean resolved Android dependency graph.

371 inventory inputs were explicitly omitted: local/Git/non-crates.io Rust
sources and Maven catalog entries without an explicit supported version.
Gradle plugin versions, dependencies selected through BOMs, transitive Maven
resolution, C/C++ libraries and binary provenance require additional review.

| Package | Advisory | Assessment and next action |
|---|---|---|
| `smallbitvec 2.5.1` | [GHSA-97wc-2hqc-cjgr](https://osv.dev/vulnerability/GHSA-97wc-2hqc-cjgr) | Capacity-overflow calculation is present. Examined Style/dogear creation sites use allocated container lengths, constant size 1 or incremental pushes; no arbitrary page-supplied capacity was found. Binary parity and complete reachability/risk disposition remain open. |
| `serde_with 3.12.0` | [GHSA-7gcf-g7xr-8hxj](https://osv.dev/vulnerability/GHSA-7gcf-g7xr-8hxj) | `KeyValueMap` underflow expressions are present in the dependency. The sole direct reverse dependency in this lockfile is `qlog`; all 12 pinned qlog source files were inspected and use `skip_serializing_none`, not `KeyValueMap`. Source evidence indicates the affected API is not used through that consumer. Preserve the match and confirm consumed binary/source parity. |
| `ringbuf 0.2.8` | [RUSTSEC-2026-0293](https://osv.dev/vulnerability/RUSTSEC-2026-0293) | Lockfile reverse dependencies are CoreAudio/Pulse backends. Pinned `toolkit/moz.configure` defaults Android to AAudio/OpenSL, rejects PulseAudio on Android and restricts AudioUnit to Darwin. `gkrust-features.mozbuild` enables these optional Rust backends only under their corresponding flags. Source evidence excludes them from the standard Android configuration; confirm artifact configuration/provenance. |
| `bincode 1.3.3` | [RUSTSEC-2025-0141](https://osv.dev/vulnerability/RUSTSEC-2025-0141) | Unmaintained notice; track upstream migration, not a demonstrated runtime exploit. |
| `paste 1.0.11` | [RUSTSEC-2024-0436](https://osv.dev/vulnerability/RUSTSEC-2024-0436) | Unmaintained notice; track upstream replacement and build exposure. |
| `unsafe-libyaml 0.2.11` | [RUSTSEC-2024-0449](https://osv.dev/vulnerability/RUSTSEC-2024-0449) | Unmaintained notice; establish build/runtime inclusion and upstream replacement. |

These matches are not silently suppressed or marked patched. The current
workflow uses **Gecko artifact mode**: modifying vendored Rust after downloading
Gecko does not repair the compiled engine in the APK. A required native fix
must come from a verified fixed upstream artifact or a full, tested Gecko source
build. Blind version changes to the lockfile are not a binary security patch.

Source-triage evidence at the same immutable pin:

- [Android audio backend guards](https://github.com/mozilla-firefox/firefox/blob/3c71aeacdb296402e41fb2084b13e797d1770642/toolkit/moz.configure),
  [Rust feature selection](https://github.com/mozilla-firefox/firefox/blob/3c71aeacdb296402e41fb2084b13e797d1770642/toolkit/library/rust/gkrust-features.mozbuild).
- [qlog source](https://github.com/mozilla-firefox/firefox/tree/3c71aeacdb296402e41fb2084b13e797d1770642/third_party/rust/qlog/src).
- [Style declarations](https://github.com/mozilla-firefox/firefox/blob/3c71aeacdb296402e41fb2084b13e797d1770642/servo/components/style/properties/declaration_block.rs),
  [Style selector/scoping callers](https://github.com/mozilla-firefox/firefox/blob/3c71aeacdb296402e41fb2084b13e797d1770642/servo/components/style/stylist.rs),
  [dogear container lengths](https://github.com/mozilla-firefox/firefox/blob/3c71aeacdb296402e41fb2084b13e797d1770642/third_party/rust/dogear/src/tree.rs).

Reproduce the source-metadata scan with Python 3.12+ and network access:

```bash
python3 scripts/audit_dependencies.py /path/to/pinned-firefox --output dependency-audit.json
```

Exit 0 means no matches for the inventoried subset, 2 means advisory triage is
required, and 1 means the scan failed. The JSON records source SHA-256 hashes,
all queries and matches, omitted inputs, scope and generation time. Partial or
paginated results fail instead of being reported clean.

## Validation

- Existing Dev build 94 at the reviewed base passed both ABI builds, signing
  and CI checks: [run 38999177956](https://github.com/iiankehn/acute-web-android/actions/runs/38999177956).
  That run predates these patches.
- [Draft PR #7](https://github.com/iiankehn/acute-web-android/pull/7) started
  [Build 95](https://github.com/iiankehn/acute-web-android/actions/runs/39054971557).
  Its Linux audit passed all 81 Python tests, eight JavaScript tests and all
  channel overlays. Both APKs compiled, exported runtime dependencies and passed
  ABI/permission checks. The new manifest parser rejected AAPT2's current
  namespace/Boolean syntax even though the actual dumps show backups disabled.
  Both original ABI manifest dumps passed the corrected backup/provider parser
  locally; an exact Build 95 excerpt is now a regression fixture. Further review
  found the exported Glean debug activity in those dumps, which the new policy
  deliberately rejects. The current PR run must verify its removal as well as
  the fix and the subsequent Stable updater/unsigned manifest retention changes.
  Superseded PR runs now cancel when a replacement starts.

The exported diagnostic activity was compared with
[Glean 70.2.0 source](https://github.com/mozilla/glean/blob/v70.2.0/glean-core/android/src/main/java/mozilla/telemetry/glean/debug/GleanDebugActivity.kt).
It accepts log-ping, debug-tag and submit-ping commands from other applications.
The pinned Fenix `GleanHelper.kt` still initializes normal upload consent from
Acute's forced-false telemetry setting. Removing the unused debug activity is
additional attack-surface reduction, not evidence that disabled uploads were
bypassed or that telemetry was observed. Firebase/web-push components remain.
- Complete Stable, Beta and Dev overlays applied successfully to real files
  from the immutable Firefox pin after the source changes in this branch.
- Repository checks, security/release audit, Python compilation and diff
  whitespace checks pass locally.
- 74 Python tests passed in the Windows-compatible selection; three tests were
  skipped (two Bash execution tests and one privileged symlink test). Four
  pre-existing Bash/local-Git test methods were excluded after their Windows
  environment failures were confirmed. All eight JavaScript tests passed.
- JavaScript behavioral tests execute the actual extension scripts with mocked
  browser/DOM APIs. They do not certify Android extension installation or UI.
- Windows cannot execute the existing Bash workflow-metadata tests or the local
  Git-transport fixture here. New shell tests require Linux/Bash; symlink tests
  require OS permission. The full Linux suite remains a required CI check.
- New compiled-manifest rules and dependency-export/signing steps still need
  execution against freshly built ARM64/x86_64 APKs. No APK was rebuilt locally.

## Beta acceptance work still required

1. Resolve or document evidence-based platform/risk dispositions for the three
   vulnerability matches; track the three maintenance notices separately.
2. Run full Linux CI, then review new per-ABI manifests, resolved runtime
   dependency reports, native libraries, signatures and signer continuity.
3. Install the signed matching-channel candidate over its prior installation;
   retain history, bookmarks, passwords, tabs, extensions and preferences.
   Dev and Beta have separate profiles; installing Beta does not migrate Dev.
4. On a physical Android 12+ device, test launch, navigation, address editing,
   Back/Forward state, downloads, native controls, focus, text scaling, rotation
   and narrow split windows. Test process death and tab/private-mode restoration.
5. Exercise Midnight Pages upgrade from 0.1.0, failed/repeated preference writes,
   private-mode exclusion, internal/PDF/payment-page exclusions and reload errors.
6. Test browser entry points, Custom Tabs/shares, file/clipboard URI grants,
   saved passwords/autofill, Mozilla Sync sign-in/pairing and compatible addons.
7. Capture startup/idle/browsing egress and distinguish required security,
   browsing, Sync and push traffic from prohibited diagnostics/attribution.
   Firebase/web push is preserved; no runtime-egress acceptance is claimed.
8. Test the Beta updater and Android installation handoff with the correct
   signing identity. Dev's updater remains disabled.

Open native dependency findings, failed CI, or device regressions prevent this
branch from being called release-ready. No Stable/Beta ref, tag, published APK,
website or production profile has been changed by this local audit.

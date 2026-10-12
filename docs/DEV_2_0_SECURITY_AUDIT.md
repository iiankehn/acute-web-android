# Android 2.0 source security review — October 12, 2026

Scope: the Fenix overlay, updater, manifests, immutable upstream input and build/signing pipeline.
The independent GeckoView migration remains archived. This source review is not APK/device acceptance
and is not a certification that every transitive upstream dependency is vulnerability-free.

## Review findings and changes

- CORE Glass compositing, viewport clipping modifications and forced page-load toolbar collapse are removed.
  The real upstream viewport, toolbar surface and scrolling implementation remain byte-for-byte unchanged.
  Display/edit address capsules use opaque Material colors. Origin/security handlers remain upstream code.
- Back remains in the main navigation row; Forward follows selected-tab history; Refresh/Stop appears in
  wide windows and remains in the phone menu. Existing history/security/session handlers are retained.
  Menu groups preserve Reader View customization, IP protection, passwords, extensions, Sync and Quit.
  Category labels expose Android accessibility heading semantics. The tablet tab strip remains separate;
  merging the strip into address capsules is a future UI step.
- Enforce `minSdk 31` (Android 12), verified in APK badging before signing. ARM64 and x86_64 remain separate
  complete Gecko packages; the native-library verifier rejects incomplete foreign architectures.
- Build flags alone did not enforce runtime consent. Telemetry, daily usage, experiments and remote rollouts
  now return false regardless of saved preferences. Marketing consent and crash-report choice stay locked off.
  CrashReporter receives empty crash/telemetry service lists; Sentry initialization is disabled. MetricController
  receives an empty service list, avoiding construction of Adjust/install-referrer/usage SDK services.
  The unused exported Adjust attribution receiver is removed. Local crash recovery remains available.
- Backups remain disabled. Manifest providers remain non-exported with application-ID-scoped authorities;
  the updater provider grants no external access. Browser/Custom Tab/share/PWA entry points keep maintained
  upstream handlers. Autofill requires `BIND_AUTOFILL_SERVICE`; QA tooling requires `DUMP`. No new exported
  component or permission is introduced. Final dependency-merged manifests still need APK review.
- Dev uses an isolated application ID/label and signed release-variant CI artifacts; its updater exits before
  registering callbacks or scheduling network checks. No Dev public-release or website publication is enabled.
- Updater metadata requests reject redirects; APK/page URLs require HTTPS, exact GitHub host and canonical
  encoded repository paths, no credentials/query/fragment, and only default/443 ports. Response/APK size,
  channel, version and ABI checks remain enforced. Android's installer performs signature enforcement.
- Signing remains isolated from untrusted source builds. The cleanup trap is installed before decoding the
  keystore and `umask 077` protects partial writes. Package identity, non-debuggable status, architecture,
  signer continuity, permission reports and checksums remain gates. Removed the old vital-lint skip:
  acceptance on an old Firefox pin does not validate the new source.
- Fixed an undefined workflow variable in the audit gate and replaced obsolete Glass test expectations.
  Actual metadata shell execution tests cover Dev/Beta/release routing and malformed inputs.

## Upstream and dependencies

The immutable Firefox Android 157.0.1 release source is
`0c469c2352451630bc69fc328c9f0c589c6c534d`. Mozilla's latest Android release notes
and Firefox advisory index were checked on October 12 and list 157.0.1. The October 6
release includes MFSA 2026-104 / CVE-2026-106016 (File Handling mitigation bypass).

Primary sources:
- https://www.firefox.com/en-US/firefox/android/157.0.1/releasenotes/
- https://www.mozilla.org/en-US/security/advisories/mfsa2026-104/
- https://www.mozilla.org/en-US/security/known-vulnerabilities/firefox/

Dependency versions are supplied by the same upstream commit rather than independently mixed:
AGP 9.4.0, Kotlin 2.4.20, Compose BOM 2026.08.00, Glean 68.0.1, protobuf 4.36.1,
OkHttp 5.5.0, Sentry 8.55.0 and Adjust 5.8.0 in `gradle/libs.versions.toml`.
The Fenix Gradle wrapper pins Gradle 9.7.1 with a SHA-256 checksum and URL validation.
Acute adds no Python package dependency. Its local Midnight Pages extension has no remote
service request and skips private pages. GitHub Actions remain pinned to full commit hashes.
A follow-up inventory scan completed 709 OSV version queries and found three vulnerability records
and three maintenance notices. See [dependency findings](DEV_2_0_DEPENDENCY_FINDINGS.md).
Release acceptance is blocked pending triage/remediation. Resolved-transitive Maven coverage and
actual APK merged-manifest review remain pending.

## Validation and remaining acceptance gates

47 repository regressions, Python compilation and source security checks pass locally.
The upstream checker applies all three channel overlays to immutable real Fenix/Android Components
files and checks isolation, consent, manifests and unchanged viewport source. This is source validation,
not Kotlin compilation or physical-device testing.

Dev advancement is permitted only after these source checks pass. The subsequent GitHub build must
complete for both ABIs, including Kotlin/resource compilation, restored vital lint, APK verification,
signing and signer continuity. Then test phone/tablet navigation, Forward state changes, resizing,
private-tab isolation, saved data, install-over and profile preservation. No Stable/Beta promotion or
public release is authorized by this checkpoint. Runtime traffic verification remains pending.

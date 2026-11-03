# Acute Web Android — continuation

## Verified import baseline

- Repository: iiankehn/acute-web-android; active branch: dev.
- Observed head: 1311ea06ea9ce7ce9527ca5704411895fd99198a.
- Published prerelease: v2.0.0-beta.2; Beta 3 is in preparation.
- Build Android APK #145 and Validate overlay #155 passed on that exact head.
- Open PR #25 targets main; its development-branch wording and sibling brain dependencies need review before merge. Open PR #21 targets dev and needs review/disposition.
- Read docs/BETA_3_SCOPE.md, docs/BETA_2_0_AUDIT.md, docs/RELEASE_CHANNELS.md, docs/UPSTREAM.md and acute-android.toml before implementation.

## Resume here

Start with local-only crash records and a tester-reviewed GitHub issue draft, plus preventing Glean startup and gathering runtime network evidence. Review/sanitize diagnostics before a URL or issue draft is opened; no automatic uploads. Then close dependency and device audit findings, investigate GeckoView homelab exceptions and finish privacy disclosures/Firebase decisions. Reconcile the newer website on main before promotion so dev/beta cannot overwrite it. Keep brand-2-assets out of Beta 3. Prove the updater on the actual Beta 3 candidate last; Beta-to-Stable is a distinct package/channel handoff and must not be assumed to be an install-over update.

Keep Fenix/Gecko overlays, native Material UI, Android 12+, ARM64 and x86_64. CORE Glass and the independent GeckoView migration remain shelved. Flow: dev → beta → main. Overlay replacements fail closed with fixtures/regression coverage; read pinned upstream source. Preserve signing and release safeguards. The verified beta-label workflow uses BETA_CANDIDATE with a comment that it matches release.candidate: check both values together rather than assume automatic TOML parsing. Do not rerun completed upstream/smoke work without a new reason; recheck its current evidence first.

Start the next chat with: “Continue Acute Web Android from docs/CONTINUATION_HANDOFF.md on dev. Inspect current repository state and Beta 3 gates first, then continue crash-reporting/privacy work. Work only on Android.”

## Continuation contract

This file imports the supplied Claude handoff for separate project chats. The attachment is a historical snapshot, not proof that pending work has been completed. Re-fetch branch heads, open PRs, CI and the referenced gate documents before changing code. Work on this platform only unless the owner explicitly requests cross-platform work. Do not publish a release or push a version tag without the owner's approval. No application changes or gate completions are made by this documentation import.

## Original Claude handoff (preserved verbatim)

# Acute Web — handoff (iOS + Android), week of Oct 19–25, 2026

Prepared Oct 26, 2026 from the git history, PRs, CI runs and docs of
`iiankehn/acute-web-ios` and `iiankehn/acute-web-android`. Everything below is
what the repositories show; device results are only stated where a commit or doc
records them.

**Product:** Acute Web by CORE, "The web, in focus." A privacy-first browser.
Branding is "Acute Web" / "Acute Web by CORE"; the clear-glass cat-fox is the
product mark. No telemetry, analytics, crash uploads or marketing on either
platform.

---

## 1. Snapshot

| | iOS / iPadOS | Android |
|---|---|---|
| Repo | `iiankehn/acute-web-ios` | `iiankehn/acute-web-android` |
| Tech | Native SwiftUI shell on WebKit, no third-party runtime deps, XcodeGen (`project.yml`) | Not a fork: `scripts/apply_overlay.py` patches a pinned Firefox for Android (Fenix/Gecko) checkout in CI; `overlay/` holds resources + Kotlin |
| Current release | **0.5.0 sideload beta**, tag `v0.5.0` on `main` @ `5fc2bb7` (published by manual Build run #139, green) | **2.0.0-beta.2** released Oct 21; **Beta 3** in progress on `dev` (`release.candidate = "2.0.0-beta.3"`) |
| Active branch | `main` | `dev` (flow is Dev → Beta → Stable) |
| Distribution | Unsigned IPA on GitHub pre-releases; users sign with a free Apple account (AltStore/Sideloadly/Xcode). No App Store/TestFlight (no paid dev account) | Signed APKs (ARM64 + x86_64) on GitHub Releases; in-app updater checks GitHub releases. Not on Google Play |
| Min OS | iOS 18 declared, **only iOS 27 tested** | Android 12+ |
| CI state | `main` green (run #139). Open PR #15 green | `dev` green (Build Android APK #145 incl. emulator smoke tests) |
| Open PRs | #15 Claude Code project memory + skills | #25 Claude Code memory + skills (targets `main`); #21 cloud-session Android SDK setup (targets `dev`) |
| Open issues | none | none |

---

## 2. iOS — what happened this week (PRs #7–#14, all merged to `main`)

### #7 Audit hardening (Oct 21)
Source audit of interface, usability, completeness, security and privacy, fixed in one batch:
- **Privacy:** app-switcher cover whenever *any* private tab exists; Site Privacy changes in private tabs stay in memory; all private tabs share one non-persistent `WKWebsiteDataStore`, released with the last one.
- **Downloads:** ask first; only from the visible tab in the active window (hidden frames can't start them); progress, size, completion notice, retry/resume, background-time request.
- **Security:** indicator uses `hasOnlySecureContent`; plain HTTP shows "Not Secure"; website dialogs limited per tab and blockable until navigation; HTTPS connection failures may retry over HTTP after a warning (never for certificate errors).
- **Tracker blocking:** now covers media, fonts, pings, embedded tracker frames; rule-compilation failure shown in Settings.
- **Browsing:** HTTP auth prompts, `window.open` with opener + `window.close`, always-allow camera/mic per site, queued permission prompts, Site Settings list (www-insensitive), back/forward history menus, pull to refresh, local address suggestions, select-all on focus, capsule close buttons, Cmd-G, Cmd-1…9, editable favorites, bookmark folders + HTML import/export, clear-history prompt when history saving is turned off.
- **Correctness:** WebKit policy interruptions (102/204) no longer show error pages; typing in the address field isn't overwritten; restored background tabs load on first select; reclaimed tabs reload.
- **Release:** iPad multiple windows (shared library, per-window tabs), `ITSAppUsesNonExemptEncryption = NO`, string catalog, injected test defaults, CI no longer retries failed tests.

### #8 iPhone Duo + Library sidebar (Oct 22)
- Layout chosen from size classes and the system's vertical-bar edge (`BrowserChromeMode`), never device model.
- Side rail (Back, Forward, New Tab, Tabs, More) where iOS puts bars vertically, clear of the outer camera; controls avoid the fold; tabletop posture uses a control deck below the fold (`FoldLayout`).
- Wide-window sidebar is now a **Library** (Bookmarks, History, Downloads) on iPad and open Duo; tabs stay in the nav bar unless Settings › Tabs › *Show tabs in sidebar*.
- CI moved to Xcode 27.1 on GitHub's Xcode 27 preview image. iPhone/iPad run on **iOS 27.0** simulator (27.1 runtime only supports iPhone Duo); separate iPhone Duo job installs 27.1.
- iOS 27 quirk: **the More menu's first row ignores taps** in every UI run. Workaround: tab actions (New Tab, New Private Tab, Show All Tabs, Reopen Closed Tab) moved to the top of More under a **"Tabs" section heading** that occupies the dead row. Whether real taps are affected needs a check on a real iOS 27 iPhone.
- WebKit waits raised (30 s for web-view mounts, 60 s for cold page loads) because WebContent processes launch slowly on fresh iOS 27 simulators.

### #9 0.5 release prep (Oct 23)
- `MARKETING_VERSION` 0.5.0; `RELEASE-NOTES.md` explains sideload-only install (free account, 7-day re-sign, Developer Mode, trust certificate) and ships inside the artifact.
- Address error alert no longer publishes state during a view update; release validation now **fails** on that SwiftUI warning.
- Layout UI tests (renamed from Duo tests) check portrait + landscape and also run on iPad, including Show tabs in sidebar.
- All interface orientations declared; validation fails on iOS's orientation warning.
- Skip simulator diagnostics collection (was adding 10 min to failed runs); Node 24 upload action.
- Decision recorded: **no iPhone Duo device available** → Duo ships on simulator evidence + tester reports.

### #10 Coverage + tagged releases (Oct 23)
- Pushing tag `vX.Y.Z` matching `MARKETING_VERSION` publishes a GitHub pre-release (unsigned IPA, `SHA256SUMS.txt`, `build.json`, notes) after every job passes.
- `AcuteWebAppearanceUITests`: Xcode accessibility audits of start page, Settings, tab overview and Library in light and dark mode; largest accessibility text size check. Debug-only `-acuteUITestDarkMode` launch arg (kept out of Release by validation).
- Fixed audit findings: readable secondary text colour, scalable favorite icons, stacked tab-overview counts, inline search-engine list at accessibility sizes, scrollable Library empty states, tab badge large-content viewer.
- **iOS 18 CI job tried and dropped**: Xcode 27.1 (xcodebuild and `xcodes`) can't download any iOS 18 runtime. Docs say iOS 18–26 untested, at tester's own risk.

### #11 Large-text toolbar + manual publish (Oct 23)
- Navigation row and side rail stop growing at the largest *standard* text size (like system bars); long-press shows the large content viewer; address prompt shortens to "Search" at accessibility sizes. Test asserts no nav-row controls overlap.
- Running the Build workflow by hand on `main` publishes the release and creates tag `v` + `MARKETING_VERSION`.
- Near-pass contrast warnings are logged, real contrast failures still fail.

### #12–#14 CI stabilisation (Oct 23)
- #12: layout tests wait for a real on-screen frame after rotation; dialog-broker queue wait 10 s.
- #13: the two required unit-test passes now run as **separate xcodebuild invocations on a freshly restarted simulator** (second pass kept stalling in WebKit).
- #14: interface tests start on a freshly booted simulator too. After this, release run #139 went green and `v0.5.0` was published.

### Still open on iOS (from `docs/BETA-READINESS.md`)
- Device validation: VoiceOver, Voice Control, Increase Contrast, Reduce Motion, real iPad interactions (Split View, pointer, keyboard), browsing matrix (IPv6-only, logins, uploads, media), plain-HTTP behaviour without an ATS exception, More-menu first-row taps on a real iOS 27 iPhone.
- iPhone Duo: no device; revisit on tester reports.
- iOS 18–26: untested.
- App Store / TestFlight: not pursued (needs paid membership); listing/review metadata not prepared.
- Scope is **frozen** for 0.5 hardening: no Android parity, new engines, accounts or extension systems.

---

## 3. Android — what happened this week (PRs #12–#24)

Branches: `main` = Stable (and the GitHub Pages website), `beta` = Beta prereleases, `dev` = where all changes land. App IDs `com.acuteweb.browser`, `.beta`, `.dev` install side by side. Tags: Stable `vX.Y.Z`, Beta `vX.Y.Z-beta.N`; the RC will ship as a Beta tag labelled "Release candidate".

### Leading into Beta 2 (Oct 18–21)
- **#9/#10/#11 website:** Beta download button beside the main one, release-notes row, stricter release URL validation; Dev brought in line with main.
- **Settings regrouped** into General, Appearance, Privacy & security, Passwords and autofill, Browsing data, Downloads and links, Extensions, Advanced, About (overlay fails if upstream adds/removes a setting). First-run artwork rebranded.
- Release lint heap raised (Gradle 6 GiB, Kotlin daemon 4 GiB); main-menu continuity verifier.
- **#12 Menu crash fix:** opening the main menu on any web page crashed (nested `verticalScroll` in `MenuNavigation`). This crash shipped in Beta 1.
- **#13 Private by default:** Strict tracking protection, HTTPS-Only, Global Privacy Control for every profile (saved user choices kept); "Private by default" first-run page; one-time notice for updated profiles; docs/website updated. Gecko already exempts loopback/private IPs from HTTPS-Only.
- **#14 Privacy polish:** Strict labelled as default; notice no longer appears over onboarding after clearing app data.
- **#15 Welcome page:** replaced Firefox terms/diagnostic-data lines with Acute's own (FOSS on Gecko; no telemetry, diagnostics or crash reports).
- **#16 Continuous onboarding off** (default-browser, Sync, Mozilla VPN prompts on days 2–7).
- **#18** promoted `dev` → `beta`; **v2.0.0-beta.2** released Oct 21, website auto-updated.
- **#17** `docs/BETA_3_SCOPE.md` defined (see §4).

### Beta 3 work so far (Oct 24–25, merged to `dev`)
- **#19 Firefox pin → Android 158.0.2** (`08d23041955657e661eef22c8fdc967735300233`), security fixes MFSA 2026-111/116. All overlays applied unchanged. Cadence recorded in `UPSTREAM.md`: move the pin at the start of every Beta, out-of-cycle for Android security advisories. Pin lives in three places (`acute-android.toml`, `PINNED_FIREFOX_REF`, workflow-dispatch default) — change together.
- **#20 Emulator smoke tests:** `scripts/android_smoke.py` over adb (launch, first run, HTTPS page, main menu on a page — the Beta 1 crash, Settings › Privacy and security › HTTPS-Only, HTTPS-Only warning on `httpforever.com`, crash check). Confirms Acute is in front before every tap, so safe on a tester's phone. `android-smoke.yml` runs Android 12 phone + Android 15 tablet emulators on every APK build. UTF-8 output fix for Windows.
- **#22 Pixel 3 XL device-test fixes (Build 128):** Firefox/Kit mascots replaced with Acute artwork (`overlay/artwork/<name>.png`, falls back to the Acute mark); Acorn violet → Acute blue in Compose; Sync copy says "Mozilla account"; Tracking Protection copy; pluralisation fixes; tracker card in tab manager now opt-in; "Download Settings" → "Downloads"; six Acute page-state illustrations for error pages and the crashed tab.
- **#23 Remaining violet removed** (Dev 141 re-test): tab outline gradient, private-mode mask, screen-lock banner, view-based private surfaces → Acute blues.
- **#24 Beta version labelling:** untagged `beta` pushes use `release.candidate` from `acute-android.toml` (now `2.0.0-beta.3`); a Beta tag that doesn't match the candidate fails before building.

### Also on Oct 25
- **Website** (`main`, committed directly by Iian): new frosted cobalt-and-amber site with Features, Privacy and Help pages, custom domain kept (acute.iiankehn.com), release-updater hooks preserved. Pages deploy green.
- **Branch `claude/brand-2-assets` (no PR yet):** traced vectors for the simplified 2.0 fox (royal blue `#1D53E5`, pale blue-white, navy; 108×108 adaptive-icon viewBox) and the approved Lexend Bold wordmark/lockups (spacing option F) with `build_wordmark.py`. **Not used in the app; Beta 3 keeps the current identity.**

---

## 4. Android Beta 3 — remaining work (from `docs/BETA_3_SCOPE.md`)

Theme: stability and trust. Ships when exit gates pass, not on a date. Path: Beta 3 → RC (as a Beta tag) → Stable 2.0.

**RC exit gates**
1. No known crashers, with in-app crash reporting shipped.
2. Every item in `docs/BETA_2_0_AUDIT.md` resolved or formally risk-accepted.
3. Updater proven on a real device: Beta → Beta and Beta → Stable, signer continuity.
4. Network capture supports every privacy claim (incl. "no telemetry, diagnostics or crash reports").

| # | Workstream | Status |
|---|---|---|
| 1 | Upstream pin to newest Firefox stable | **Done** (158.0.2) |
| 2 | Local-only crash reports; About › Report an issue › "Include last crash" opens a pre-filled GitHub issue the tester reviews first | Not started |
| 3 | Stop Glean starting at all (upstream `startGlean` on welcome accept); network captures; destinations listed in PRIVACY.md; decide Firebase/web push | Not started |
| 4 | Close audit: `smallbitvec` GHSA-97wc-2hqc-cjgr, `ringbuf` RUSTSEC-2026-0293 + one more native dep finding; device checks (nav, downloads, rotation, split screen, text scaling, process death, tab restore); entry points (external links, Custom Tabs, share, file/clipboard URIs, passwords, Sync, add-ons); Midnight Pages upgrade/exclusions | Not started |
| 5 | Test automation: CI emulator smoke | **Done** (phone A12 + tablet A15). Pixel adb script exists (same script). Windows `unittest` run: UTF-8 fixed; full Windows pass not confirmed |
| 6 | Updater: verify Beta 2 → Beta 3 on Pixel; Beta → Stable handoff; fix beta branch version label | Label fix **done** (#24); device verification pending (do last, on the real Beta 3) |
| 7 | Homelab: remember "Continue to HTTP site" per site; treat `*.local/.lan/.home.arpa/.internal` like private IPs — investigate GeckoView permission APIs first | Not started |
| 8 | Small features (each with tests, no new permissions) | — |

Suggested order: (upstream ✔) → (tests ✔) → crash reporting + privacy proof in parallel → audit, homelab, small features → updater proof on the actual Beta 3.

---

## 5. Things to watch / inconsistencies

1. **Website will conflict on promotion.** The new site (`features.html`, `help.html`, `privacy.html`, new `index.html`/`styles.css`) went straight onto Android `main`. `dev` and `beta` still have the old site. When `beta` is promoted to `main` (and when the release job rewrites `docs/index.html` via `scripts/update_site_release.py`), make sure the new site isn't overwritten and the `data-release-link` / `data-release-version` hooks still match what the script expects. Consider porting the site to `dev` first.
2. **Android PR #25's CLAUDE.md is out of date**: it says "`main` = Stable, `beta` = active development" and that PR targets `main`. The real flow is `dev` → `beta` → `main`, with fixes always starting on `dev`. Fix the text (and probably retarget) before merging.
3. Both memory PRs (#15 iOS, #25 Android) import `@../brain/CORE.md` and reference `../brain/learnings/ci.md`, `../brain/projects/acute-web.md`, `../brain/playbooks/ship-a-release.md` from an `iiankehn/brain` repo that must be cloned beside each repo.
4. PR #21 (Android SDK SessionStart hook for cloud sessions) is still open against `dev`.
5. iOS CI round trips take ~30–55 min; Android APK builds ~40 min. Neither platform builds in a Linux cloud container (Swift / Fenix), so CI is the test run. Android `make audit` (Python 3.12) runs anywhere in seconds; iOS `python3 -m unittest discover -s scripts -p 'test_*.py'` likewise.
6. Brand 2.0 assets exist on a branch only; don't ship them in Beta 3.

---

## 6. Working rules both repos follow

- Commit messages: plain imperative sentence, no prefix (e.g. "Restart the simulator before the browser interface tests").
- Never relax assertions, skip/disable tests, or add retries to get CI green; make tests deterministic. iOS unit tests must pass twice.
- Claim only evidence that exists: CI ≠ device validation ≠ App Review. Say plainly what's untested (iOS 18–26, iPhone Duo device, physical iPad).
- **iOS:** layout follows size classes and system bar edge, never device model; Liquid Glass (iOS 26+) on controls/navigation only, with material fallbacks; private tabs never reach history, sessions, recent sites or closed-tab recovery; any required-reason API use goes into `PrivacyInfo.xcprivacy` **and** `EXPECTED_REASONS` in `scripts/validate_release.py`.
- **Android:** every upstream patch uses `replace_once` and fails closed (`OverlayError`) with a fixture + test in `tests/test_overlay.py`; read upstream at the pinned commit only; GitHub Actions pinned to full SHAs; Firefox/Mozilla names only in accurate legal/engine disclosures; never commit APKs, keystores, credentials or Mozilla source; update `docs/MODIFICATIONS.md` for user-visible changes.
- Releases: confirm with the owner before pushing any tag (tags publish to the public). Fix forward with a new version; never replace published assets.

## 7. Key files

**iOS:** `project.yml` (version), `AcuteWeb/{Browser,Model,Views,Commands}` (`BrowserStore`, `BrowserTab`, `PermissionBroker`, `BrowserChromeMode`, `FoldLayout`), `AcuteWeb/PrivacyInfo.xcprivacy`, `AcuteWebTests/`, `AcuteWebUITests/` (`AcuteWebLayoutUITests`, `AcuteWebAppearanceUITests`), `scripts/validate_release.py`, `scripts/select_simulator.py`, `.github/workflows/build.yml`, `docs/BETA-READINESS.md`, `docs/ARCHITECTURE.md`, `RELEASE-NOTES.md`.

**Android:** `acute-android.toml`, `scripts/apply_overlay.py`, `scripts/verify_upstream_overlay.py`, `scripts/android_smoke.py`, `scripts/update_site_release.py`, `overlay/` (incl. `overlay/artwork/`, `overlay/beta-res/`, `GitHubUpdateProvider.kt`, Midnight extension), `tests/`, `.github/workflows/{build-android,android-smoke,validate}.yml`, `docs/BETA_3_SCOPE.md`, `docs/BETA_2_0_AUDIT.md`, `docs/RELEASE_CHANNELS.md`, `docs/UPSTREAM.md`, `docs/PRIVACY.md`, `docs/MODIFICATIONS.md`.

## 8. Suggested next steps

**Android (Beta 3):** start crash reporting (WS2) and Glean/no-start + network capture (WS3); work through `BETA_2_0_AUDIT.md`; investigate homelab HTTPS-Only exceptions; reconcile the website between `main` and `dev`; fix and merge #25; merge or close #21; then build Beta 3, device-test on the Pixel 3 XL, and prove the Beta 2 → Beta 3 update.

**iOS (0.5.x):** collect tester feedback on v0.5.0 (especially iPhone Duo and the More-menu first row on real iOS 27); run the remaining device checks in `BETA-READINESS.md`; merge #15; keep scope frozen until the 0.5 gates are met.

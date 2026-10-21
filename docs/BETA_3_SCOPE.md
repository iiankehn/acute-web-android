# Acute Web 2.0 Beta 3 — scope

Beta 3 is the **final Beta before the 2.0 release candidate**. Its purpose is
**stability and trust**: everything that has to be true before Acute can ask
people to rely on it daily. There is no deadline; Beta 3 ships when its exit
gates pass.

This document records the scope agreed on October 21, 2026. Changes to it go
through a pull request like any other change.

## Decisions

| Question | Decision |
|---|---|
| Theme | Stability and trust |
| Size | Large; ships when the exit gates pass, not on a date |
| Feature policy | Small features allowed, each with tests |
| Upstream Firefox | Move the pin to the newest Firefox stable **every Beta** |
| Crash reporting | Must-have |
| Privacy claims | Prove them, don't just document them |
| Homelab follow-ups | In scope |
| Device coverage | Pixel 3 XL by hand; CI emulators for phone, tablet and Android 15/16 |
| Windows test run | Fix it, so local runs are trustworthy |
| How the RC ships | As a Beta tag (`v2.0.0-beta.N`) labeled "Release candidate"; no new tag format |

## Starting point

Beta 3 builds on everything in `dev` for Beta 2: the menu crash fix,
private-by-default (Strict tracking protection, HTTPS-Only, Global Privacy
Control) and its announcements, the Settings categories, the Acute welcome
page, and continuous onboarding turned off.

## Exit gates for the release candidate

Beta 3 can become the RC only when all four hold:

1. **No known crashers.** Zero open crash bugs, with in-app crash reporting
   shipped and available to testers.
2. **Audit items closed.** Every open item in
   [BETA_2_0_AUDIT.md](BETA_2_0_AUDIT.md) has a resolution or a written,
   evidence-based risk acceptance.
3. **Updater proven.** Beta → Beta and Beta → Stable in-app updates verified on a
   real device, with signer continuity.
4. **Privacy claims verified.** A network capture supports every privacy
   statement Acute makes, including the welcome page's "Acute doesn't collect
   telemetry, diagnostics or crash reports."

## Workstreams

Each item lists what "done" means. Items marked **Gate** are needed for an exit
gate.

### 1. Upstream: Firefox every Beta

- Move `PINNED_FIREFOX_REF` to the newest Firefox stable release, re-verify
  every overlay anchor, and fix those that moved. **Gate (all)**
- Write the cadence down in [UPSTREAM.md](UPSTREAM.md): each Beta starts by
  moving the pin; an out-of-cycle move happens for Mozilla security advisories
  that affect Android.
- Done: `verify_upstream_overlay.py` passes on the new pin, CI builds both ABIs,
  and the device smoke checks (workstream 5) pass.

### 2. Crash reporting without uploads

Today a crash needs adb and a USB cable to diagnose, and Beta 1 shipped with a
crash that took an hour to find. **Gate 1**

- Keep the most recent crashes on the device only: version, Android version,
  device model, and the stack trace. No URLs, page content or account data.
- About › Report an issue offers "Include last crash", which opens a pre-filled
  GitHub issue. The tester sees the full text before anything leaves the
  device.
- Nothing is sent automatically, so this stays consistent with "Acute doesn't
  collect crash reports."
- Done: a forced test crash on the Pixel shows up in a pre-filled issue; tests
  cover what is and isn't recorded.

### 3. Prove the privacy claims

**Gate 4**

- Stop the telemetry engine (Glean) from starting at all. Upstream starts it
  when the welcome page is accepted (`startGlean`), even though Acute disables
  uploads.
- Capture network traffic for startup, idle, browsing, first run and update
  checks. List every destination with its purpose in
  [PRIVACY.md](PRIVACY.md): the GitHub update check, Sync only when signed in,
  safe-browsing lists, and so on.
- Decide on Firebase/web push (kept today): keep it with documented behavior,
  or remove it.
- Done: a capture report in the repository; no traffic contradicts the welcome
  page; PRIVACY.md matches the capture.

### 4. Close the audit

**Gate 2.** From [BETA_2_0_AUDIT.md](BETA_2_0_AUDIT.md):

- Resolve or formally accept the three native dependency findings, including
  `smallbitvec` (GHSA-97wc-2hqc-cjgr) and `ringbuf` (RUSTSEC-2026-0293), with
  evidence.
- Device checks: navigation, Back/Forward, downloads, rotation, split screen,
  text scaling, process death, and restoring tabs and private tabs.
- Entry points: links opened from other apps, Custom Tabs, sharing, file and
  clipboard URIs, saved passwords and autofill, Sync sign-in and pairing,
  compatible add-ons.
- Midnight Pages: upgrade from 0.1.0, failed or repeated preference writes,
  private-mode exclusion, and internal, PDF and payment-page exclusions.

### 5. Test automation

**Gate 1** and protects every later change.

- **CI emulator smoke tests** (x86_64) on every PR, with phone and tablet
  profiles on Android 12 and Android 15/16: launch, first run, the menu on a
  web page (the Beta 1 crash), Settings › Privacy and security, and the
  HTTPS-Only page for an HTTP site.
- **Device smoke script** for the Pixel over adb that runs the same checks. It
  checks the app is in front before every tap, since testers may be using the
  phone.
- **Windows test run:** fix the environment errors (encoding, missing tools) so
  `python -m unittest discover -s tests` passes locally on Windows as well as
  Linux.

### 6. Updater and release pipeline

**Gate 3.**

- Verify Beta 2 → Beta 3 in-app update on the Pixel: the dialog appears, the
  download is the signed APK, and it installs over the old version with data
  kept.
- Verify the Beta → Stable handoff.
- Fix Beta branch builds: `build-android.yml` hard-codes `version=2.0.0-beta.1`
  for pushes to `beta`. After Beta 2 ships, branch builds would still report
  Beta 1 and the updater would offer Beta 2 to newer builds. Derive the version
  from the latest Beta tag instead.

### 7. Homelab

- Remember "Continue to HTTP site" per site across restarts, with a list in
  Settings to remove sites. Mozilla's prebuilt engine can't be modified, so this
  has to use GeckoView's permission APIs from Acute's code. Investigate first.
- Treat local names (`*.local`, `*.lan`, `*.home.arpa`, `*.internal`) like
  private IP addresses, which Gecko already exempts. Same constraint.
- Done: a `nas.lan`-style device opens after one "Continue" and still opens after
  restarting Acute. If an item proves impossible without engine changes, record
  that here and keep the current documented behavior.

### 8. Small features

Allowed if each one comes with tests, needs no new permissions, and doesn't
weaken an exit gate. Propose them in their own pull request that references this
scope.

## Out of scope for 2.0

- New tag formats such as `-rc.N` (the RC ships as a Beta tag).
- Changing the release channels or signing setup.
- Large new features (redesigns, new sync providers, store distribution).

## Suggested order

1. **Upstream move** first, so every later check runs against the Firefox that
   will ship.
2. **Test automation** next, so the remaining work is protected as it lands.
3. **Crash reporting** and **privacy proof** in parallel; both touch startup and
   need the smoke tests.
4. **Audit closure**, **homelab** and **small features**.
5. **Updater proof** last, on the actual Beta 3 release.

## Risks and open questions

- **Upstream moves can break overlay anchors.** The overlay fails closed, so a
  move may need several fixes before anything builds.
- **CI emulator time and cost.** Phone, tablet and two Android versions on every
  PR may be slow; a nightly run for the full matrix may be needed.
- **Firebase/web push.** Removing it may affect push-based web features.
- **Persistent HTTPS-Only exceptions** may not be possible without engine
  changes; workstream 7 starts with an investigation.
- **Crash reports can contain sensitive data** in stack traces; the
  "nothing leaves without review" rule is non-negotiable.

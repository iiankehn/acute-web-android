# Paused native GeckoView experiment — 2026-10-12

Archive branch: `archive/native-geckoview-2026-10-12`.
The native migration is paused at the user's request. It has not achieved feature
parity or production migration acceptance. This branch preserves the full native
commit ancestry and the unfinished extension integration that was still local.
Do not treat the proposed `2.0.0-dev.8` version as a tested release.

## Checkpoints

- Last pushed native commit before archiving:
  `7be89bd2b44d4a562b98b08a79ad406af00177bd`.
- Last accepted native checkpoint before the document/suspension follow-ups:
  `803704104d590228957bfafe3bbfae9497dc4724` (Dev.5).
- Stable baseline used to reset the reusable `dev` branch:
  `bf182a139f668749e4441a27759a0ed3fef1bf9a`.
- Beta and the three `archive/pre-native-2026-10-12-*` branches remain unchanged.

## Preserved work

Native foundation, normal/private tabs, encrypted session restoration, Places
history/bookmarks, Android link handling, authenticated scoped-storage downloads,
PDF/printing integration, confirmed unreadable-archive recovery, host/port and
blank-popup changes, and background-tab suspension with runtime fixtures.
The preserved overlay code, resources, extension sources and legacy build
pipeline remain present as well.

The archive commit additionally captures unfinished ExtensionManager/ExtensionUi
wiring, the existing local feature assets as an Android asset source, extension
actions/permissions/tab delegates and the proposed Dev.8 build label. This WIP
was not compiled or runtime-tested and is not an accepted feature-parity batch.
In particular, live Gecko tabs versus suspended native tabs still need a defined
bridge for complete Saved Sessions behavior.

## Validation and open gates

Dev.6 initially compiled but failed print-cancellation runtime acceptance. The
follow-up passed print/recovery checks but its new popup fixture timed out.
Subsequent suspension acceptance exposed restoration timing, which the last
pushed commit attempts to correct. Latest validation run at archive preparation:
https://github.com/iiankehn/acute-web-android/actions/runs/38222318738
The run was still active during archive preparation and subsequently completed
with a failure conclusion. Dev.6/Dev.7 runtime acceptance remains unfinished.
Inspect that run's diagnostics before resuming; do not infer acceptance from this
archive commit.

Local project checks, the 45 Python tests, 10 extension tests and release/security
audit passed before pausing. Full migration, workspaces, extension host parity,
passwords/Sync, updater, adaptive UI, privacy/network audit, installed-profile
compatibility and physical-device/Waydroid acceptance remain unfinished. No
Stable/Beta profile import or public native release was enabled.

## Resume without replacing a live channel

```sh
git fetch origin
git switch -c experiment/native-resume origin/archive/native-geckoview-2026-10-12
```

Start by reading this note, NATIVE_MIGRATION.md and the latest run diagnostics.
Repair and validate the archived WIP before choosing whether to resume the
migration. The `dev` branch is reset to the stable source baseline for unrelated
future experiments; the archived native history remains recoverable here.


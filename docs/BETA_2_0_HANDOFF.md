# Acute Web 2.0 first-beta build handoff

Candidate: `2.0.0-beta.1`.
Source PR: <https://github.com/iiankehn/acute-web-android/pull/2>.
Target branch: `beta`. Stable `main` must not be promoted or changed by this handoff.

## Integrated implementation

- Shared neutral Material/Acorn Compose tokens and gradients, a native Workspaces
  action card without migration artwork or the obsolete Collections heading,
  and a shared homepage/browser glass modifier. Added after device testing
  exposed inherited Compose styling that the XML palette checks did not cover.
- Neutral smoked CORE Glass with white edge light and a persisted opaque-toolbar
  accessibility option in Customization (restart required).
- Feed-free local home foundation and responsive two-column layout at 840dp+.
- Stable library menu ordering, contextual page actions, and rounded large-screen
  menu treatment using the maintained Firefox presentation.
- Workspaces on the local tab-group backend, including Gecko-session suspension.
- First-level Gecko Save as PDF and Android Print.
- Per-site appearance, text scale, and reduced-motion preferences.
- Bounded local Saved Sessions and Page Notes, private/internal-page exclusions,
  failed-write recovery, initial-load protection, and duplicate-tap prevention.
- Maintained link context actions with share-before-download ordering and clean
  link copying when recognized campaign parameters are present.
- Existing ARM64/x86_64 build, signing, architecture-aware update, and telemetry
  controls retained.

## Verification completed before handoff

- 45 Python regression tests.
- 10 behavioral tests executing the actual Notes/Sessions scripts against mocked
  browser and DOM APIs (not an on-device WebExtension certification).
- Project/security/release audit.
- Complete overlay application against actual consumed source files from Firefox
  commit `4452e9a17a29f762c5af6326f45c000dcf3117bb`, for both Stable and Beta.

CI repeats the local suite and exact-source compatibility check before native
builds. The compatibility check downloads only overlay-consumed source files;
it does not compile Android or Gecko.

## Build-stage instructions

1. Merge the tested PR into `beta` to start one two-ABI candidate build.
2. Keep version `2.0.0-beta.1` and package `com.acuteweb.browser.beta`.
3. Require both native builds, ABI checks, signing, and signer continuity.
4. Use the signed branch artifacts for testing. Do not replace published assets.
5. Tag `v2.0.0-beta.1` only when approved for public prerelease publication;
   a tag starts a separate release build. Branch builds do not publish a release.

## Beta acceptance still required

- Install over the current Beta without uninstalling; retain profiles and local
  preferences. Stable and Beta must remain separately installable.
- Phone and large-screen navigation, rotation, narrow split-window resizing,
  keyboard/mouse controls, private-mode isolation, and visible focus.
- Restart with transparency reduction enabled; confirm opaque readable toolbars,
  address-field contrast, page-top reachability, and normal collapse/restore.
- Create/suspend/reopen workspaces; kill and relaunch the process; verify tab
  restoration and measure memory on supported devices.
- Open built-in feature actions on Android; save/restore/delete sessions and notes,
  and test storage failures. Verify PDF/Print with long and protected documents.
- Clean-link copying with duplicate query parameters, percent encoding, unknown
  functional parameters, and fragments.

## Product targets not represented as completed

The first beta has a local dashboard foundation, not the full configurable
module system. Module drag-reordering/collapse controls and native dashboard
cards for Saved Sessions, Notes, and Downloads remain open. Notes and Sessions
currently live in built-in extension actions.

The desktop command palette and fully toolbar-anchored floating main menu remain
open; rounded large-screen sheet styling is not equivalent to an anchored popup.
In-app side-by-side split browsing is not implemented. It remains subject to the
2.0 stability gate; Android OS split-screen support is already retained.
Workspace localization and physical accessibility/restoration certification
remain open before Stable. These are not silently marked done by beta readiness.

Privacy expansion, cloud handoff, Reading Shelf, offline pages, read-aloud queues,
and full-page PNG capture remain explicitly deferred as previously agreed.

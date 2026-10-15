# Acute cross-platform UI contract — draft 0.1

Reviewed October 15, 2026. Principles approved in discussion; the detailed mappings
below are implementation proposals, not completed UI changes or a feature-parity claim.

## Scope and evidence

Acute should be recognizable across iOS/iPadOS and Android while using native
controls, accessibility, input behavior and system integrations. Retain Fenix on
Android and WebKit on iOS. Android CORE Glass removal and the archived independent
GeckoView experiment are not reopened by this contract. Cloud handoff remains deferred.

Source snapshots reviewed:

- Android Dev `3bddbc24089eee57f03972a857655ffea0aa9d08`:
  [navigation, menus and theme policy](../scripts/apply_overlay.py),
  [opaque theme tokens](../overlay/res/values/acute_native_theme.xml),
  [menu labels](../overlay/res/values/acute_navigation_strings.xml),
  [current handoff](DEV_2_0_HANDOFF.md).
- iOS main `4b24698eba49c574799aeeba37032c31888b2c27`:
  [toolbar](https://github.com/iiankehn/acute-web-ios/blob/4b24698eba49c574799aeeba37032c31888b2c27/AcuteWeb/Views/BrowserToolbar.swift),
  [tab capsule](https://github.com/iiankehn/acute-web-ios/blob/4b24698eba49c574799aeeba37032c31888b2c27/AcuteWeb/Views/NavigationTabCapsule.swift),
  [start page](https://github.com/iiankehn/acute-web-ios/blob/4b24698eba49c574799aeeba37032c31888b2c27/AcuteWeb/Views/StartPage.swift),
  [root layout](https://github.com/iiankehn/acute-web-ios/blob/4b24698eba49c574799aeeba37032c31888b2c27/AcuteWeb/Views/BrowserRootView.swift),
  [keyboard/menu commands](https://github.com/iiankehn/acute-web-ios/blob/4b24698eba49c574799aeeba37032c31888b2c27/AcuteWeb/Commands/BrowserCommands.swift),
  [materials](https://github.com/iiankehn/acute-web-ios/blob/4b24698eba49c574799aeeba37032c31888b2c27/AcuteWeb/Views/AcuteGlass.swift).
- iOS accessibility PR #5 was open at review time, head
  `0cfcf4e619266dbb12eac25dbb30afb92682b8cd`. Its unmerged changes and visual
  acceptance are not treated as main's implemented state. Coordinate future work
  with that branch rather than replacing its accessibility fixes.

This was a source comparison, not a paired screenshot/device review. An old
Android Beta screenshot is not evidence of the current no-Glass Dev appearance.

## What already aligns, and what does not

| Area | iOS source | Android Dev source | Contract direction |
|---|---|---|---|
| Back / Forward | Back stays present, disabled without history; Forward appears when available | Back configured always visible; Forward follows selected-tab history | Preserve both behaviors, including disabled and private states |
| Address and tabs | Selected tab is an editable capsule; other tabs are horizontally scrolling capsules in the same row | Opaque address capsule; large-screen tab strip is still separate | Match hierarchy and interaction meanings, not force identical row geometry |
| Reload / Stop | Visible inside the selected capsule, including loading progress | In the main row for wide screens; phone access remains in More | Review consistent direct exposure on phones without sacrificing origin legibility |
| Tabs / More | Direct buttons; Tabs can yield space on narrow/editing layouts, with Show All Tabs in More | Tab counter and menu at the end of the address row | Stable trailing destinations; every collapsed action retains an accessible route |
| Menu organization | Tab Management, Page Tools, Saved Content, Privacy, then Settings | Navigation, Page, Library, Extensions, Settings and account; site-protection tools remain supported | Align shared labels and order; retain platform-only capabilities |
| Start page | Search, optional Bookmarks/Favorites/This Session, separate private state | Fenix homepage retained; editorial/sponsored sections disabled | Common search-first hierarchy; do not claim the earlier Beta dashboard exists here |
| Large screens | Top capsule row, regular-width iPad sidebar and native commands | Separate tab strip, width-sensitive actions and native Android menus | Equivalent tasks and hierarchy, with different native presentations |
| Materials / themes | Apple glass/material compatibility paths, Reduce Transparency fallback, light/dark system surfaces | Opaque native Android surfaces, dark UI policy | Intentional difference; do not add Android glass or force iOS dark-only |
| Accent | sRGB approximately `#0072BC` in AccentColor | `#0072BC` native brand accent plus accessible light accent token | Base accent already aligns; review usage and contrast, not a speculative new palette |

## Shared interaction rules

1. Back is discoverable without opening More. Forward is conditional. System Back
   on Android and native iOS gestures remain platform behaviors, not substitutes
   for the visible browser controls.
2. Address editing is a deliberate, discoverable action. Page titles never replace
   access to the actual address. Preserve maintained origin/security controls,
   long-host handling, connection warnings and accessible security information.
3. Loading, Stop, Reload and failure/retry states use the same meanings and labels.
   Before exposing new controls, test the narrowest supported window and largest
   text sizes. Do not hide Back or cover the address to achieve pixel parity.
4. Tab selection, New Tab, New Private Tab, Show All Tabs, Close Tab and Reopen
   Closed Tab should be recognizable shared concepts wherever implemented.
   Private state must be explicit in text/accessibility, not conveyed only by color.
5. More contains grouped actions, not an unstructured sheet of every capability.
   Native menus, Android panels and iPad menu-bar commands may expose the same
   task differently. Do not introduce a desktop-style menu bar on Android to mimic iPad.
6. Font scaling, focus order, keyboard/pointer operation, safe areas, rotation and
   resizing take precedence over matching fixed sizes. Native icon families can
   differ; their meanings and accessible names should not.
7. System sharing, permissions, file pickers, text selection and autofill remain
   native. Do not remove working Android extensions, passwords, Sync or other
   capabilities simply because iOS lacks the same implementation.

## Candidate common vocabulary and menu mapping

Exact wording/order is proposed for the first alignment batch, not silently applied
by this document. Map every existing handler before moving or renaming an action.

| Proposed destination | Existing labels to reconcile | Contents / constraint |
|---|---|---|
| Tabs | iOS Tab Management; Android tab actions/navigation grouping | New/Private/Show All/Close/Reopen where supported; keep visible Back/Forward outside More |
| Page | iOS Page Tools; Android Page | Reload/Stop, Find on Page, page display/zoom, desktop/mobile site and sharing, as supported |
| Library | iOS Saved Content; Android Library | Bookmarks, History, Downloads; preserve Android password access |
| Privacy | iOS Privacy; Android existing site/protection controls | Existing site information/protections only; this is not authorization for new privacy features |
| Extensions | Android-only destination | Present only where supported; no inactive iOS placeholder |
| Settings | iOS Settings; Android Settings and account | Shared settings names where meanings match; retain Android account/Sync access |

The iPad menu bar may retain a Navigate menu for keyboard-oriented commands.
Do not add duplicate top-level phone menu groups solely to match that menu bar.
Keep visible labels, accessibility labels, empty-state instructions and help text
in sync when renaming a destination; e.g. iOS currently tells users to open Saved Content.

## Start-page contract

- Primary sequence: recognizable Acute branding, search, user-owned shortcuts or
  bookmarks, then recent activity where available. No editorial or sponsored feed.
- Use a consistent distinction between a saved Bookmark, a Favorite/shortcut and
  recent activity. iOS's This Session is session-scoped; renaming it must not imply
  persistent history or cross-device synchronization.
- Keep empty states useful and private-mode content separate. No normal-tab
  activity or saved session should appear in a private dashboard through a layout change.
- Match module purpose and hierarchy before matching card geometry. Do not add
  Workspaces/Notes/Sessions placeholders or restore old Beta features as part of styling.

## Delivery and acceptance

1. Capture paired, build-identified screenshots before UI changes: normal start
   page, loaded page, loading/error state, private mode, tabs, More and Library.
   Include a narrow phone and a wide tablet/window. Use the same public test page
   and data fixtures; exclude personal data. Include default and accessibility text.
2. First implementation batch: common terminology/menu mapping plus updated
   accessibility/help strings. Review a before/after handler inventory so nothing
   working disappears. Keep all unavailable platform-only commands absent.
3. Second batch: phone control hierarchy and Reload/Stop discoverability. Preserve
   editable address space, origin/security affordances and direct Back access.
4. Third batch: start-page hierarchy and large-screen behavior. Tablet capsule-row
   merging is a separate design decision, not a prerequisite for browser identity.
5. Add per-platform interaction tests and reviewed screenshot baselines for these
   states. Compare against each platform's own accepted rendering, not one shared
   pixel-perfect baseline. Source-string tests alone are not visual acceptance.
6. Test iOS light/dark and Reduce Transparency; test Android's supported dark UI.
   Verify private/regular transitions, history state, long URLs, loading, keyboard,
   rotation, resizing and safe areas on the actual new builds.

No layout/runtime change, engine migration, feature expansion, release promotion
or handoff/sync implementation is authorized merely by accepting this contract.

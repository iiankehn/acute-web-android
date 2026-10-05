# Acute Web 2.0 product specification

Acute Web 2.0 is the clarity and usefulness release. It builds on the ARM64 and
x86_64 foundation shipped in 1.1 while giving Acute an interface and workflow
model that are independent of Firefox's consumer product design.

## Product principles

- Local-first: user-facing organizational data remains on the device.
- Predictable: common commands stay in stable positions.
- Adaptive: phones, tablets, foldables and Android computers receive layouts
  appropriate to their available space and input devices.
- Calm: no news feed, sponsored content, remote recommendations or promotional
  cards.
- Honest: existing privacy protections remain enforced without introducing
  unimplemented anonymity or synchronization claims.

## Visual system

CORE Glass becomes a neutral smoked-glass system. Application chrome uses
near-black, charcoal and slate surfaces. Depth is communicated with soft white
edge light, controlled opacity, fine outlines, shadows and elevation rather
than blue tinting.

The canonical product artwork may retain its own brand colors. Blue is not used
as an application-chrome structural, selected-state or navigation color.

Glass opacity must adapt to readability. Reduced-transparency and reduced-motion
paths are required before release.

## Home dashboard

The Firefox news/recommendation surface is replaced by an Acute-owned, local
dashboard. Search remains primary. Optional modules provide:

- user-selected shortcuts;
- active workspaces and saved sessions;
- recent downloads;
- locally stored page notes;
- resume and recently closed actions.

Modules are reorderable, collapsible and removable. Private browsing never
shows normal-session history, workspaces or recent content. Phone layouts use a
clean vertical flow; large screens use the additional width for a dashboard
rather than stretched phone cards.

## Navigation and menus

The inherited long bottom sheet is replaced by a hybrid menu:

- a fixed primary section for common browser actions;
- a contextual section for actions supported by the current page;
- anchored floating presentation on larger screens;
- touch-appropriate compact presentation on phones;
- keyboard navigation, visible shortcuts and a command palette where a hardware
  keyboard is present.

Dynamic commands must not reorder the fixed primary section.

## User-facing capabilities

The 2.0 design target includes:

- tab workspaces with suspension and crash-safe restoration;
- saved browsing sessions;
- local page notes;
- improved link context actions;
- full-document PDF capture and printing;
- per-site display preferences;
- task-focused local home dashboard;
- split browsing on large screens when it can be delivered without destabilizing
  Gecko lifecycle or session restoration.

### Workspaces foundation

The first implementation slice uses Gecko/Fenix's maintained local tab-group
store rather than the deprecated Collections backend. Workspaces are enabled by
default, remain on the device, survive process restoration, and are reachable
from a permanent home-dashboard module as well as the contextual page menu.
Create, edit, add-tab, dissolve and delete flows use Acute's workspace language.

Suspending a workspace keeps its local tab and group records but releases each
live Gecko engine session. Gecko's native session-state restoration recreates a
tab only when the user returns to it, reducing background memory use without a
second Acute-specific cache or session format.

At 840dp and wider, the local dashboard becomes a two-column layout: bookmarks
and recent activity remain together on the left while Workspaces receives a
dedicated right column. Narrow windows, compact tablets and split-screen modes
retain the single-column phone flow. The decision follows current window width
rather than a fixed device category so resizing remains predictable.

Workspace terminology still requires localization before the 2.0 release
candidate; unsupported translations currently retain upstream tab-group wording
rather than receiving machine-translated copy.

### Document capture and export

Save as PDF and Print are promoted from Firefox's secondary overflow into
Acute's first-level page actions. Both commands use Gecko's maintained
document-generation path, so long pages are rendered as complete documents
instead of stitched viewport bitmaps. Print stays hidden on Android Automotive,
matching the upstream platform guard, and duplicate overflow entries are
suppressed in Acute's menu.

Firefox Android does not expose a maintained full-page PNG capture feature at
the pinned 2.0 base revision. Full-page PNG capture remains deferred rather
than shipping an Acute-only renderer with different layout, memory and restore
behavior from Gecko. Android's normal visible-screen screenshot remains
available at the operating-system level.

### Per-site display preferences

Acute Site Display stores page appearance, text scale, and reduced-motion
choices by hostname in extension-local storage. A website can inherit the
global automatic appearance rule, remain original, or always use the local
dark-page treatment. Text scaling offers bounded presets from 90% through 150%,
and reduced motion suppresses page animation, transitions, and smooth scrolling.

These preferences run in normal browsing only, skip PDFs and sensitive payment
paths, make no network request, and are installed in both Stable and Beta. The
old Midnight Pages disabled-site list is migrated locally when a user changes a
site preference.

### Saved sessions

Saved Sessions creates an explicit, named snapshot of the current window's
normal HTTP and HTTPS tabs. Snapshots can be reopened or deleted from the
built-in extension action and remain separate from live Workspaces. They use
extension-local storage and Gecko's maintained tabs API; no account, remote
service, or deprecated Collections backend is involved.

Private tabs and internal browser pages are never captured. A snapshot is
bounded to 100 tabs and the device retains at most 50 snapshots, preventing a
damaged or unexpectedly large window from producing unbounded local storage or
restore work.

### Local page notes

Page Notes attaches a bounded plain-text note to the current page's canonical
HTTP or HTTPS address. Notes can be edited from that page, reopened from a list
of recent notes, or deleted. Fragment identifiers are removed before matching
so navigating within one document does not create duplicate notes.

Notes remain in extension-local storage, are limited to 5,000 characters each,
and are capped at 500 entries. Private tabs and internal browser pages cannot
create notes, and all rendered titles and excerpts use text-only DOM APIs.

Split browsing may move to 2.1 if it fails the stability gate. It must not delay
the rest of 2.0.

## Explicitly deferred

The following are not part of 2.0:

- new cloud accounts or synchronization infrastructure;
- desktop handoff;
- password or authenticated-session transfer;
- a proprietary search engine;
- a full native replacement for mature content-blocking extensions;
- expanded privacy marketing or anonymity claims;
- Reading Shelf, offline-page storage, and read-aloud queues.

## Release gates

2.0 must preserve the 1.1 ARM64 and x86_64 packages, architecture-aware updater,
privacy/telemetry policy, signing continuity and phone behavior. The final
candidate must pass phone, tablet and laptop-class layout testing, upgrade
testing, process-death restoration, reduced-transparency accessibility checks,
and memory testing with suspended workspaces.

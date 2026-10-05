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
- Reading Shelf and offline pages;
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
- Reading Shelf with offline and read-aloud queues;
- local page notes;
- improved link context actions;
- full-page capture and save-as-PDF;
- per-site display preferences;
- task-focused local home dashboard;
- split browsing on large screens when it can be delivered without destabilizing
  Gecko lifecycle or session restoration.

Split browsing may move to 2.1 if it fails the stability gate. It must not delay
the rest of 2.0.

## Explicitly deferred

The following are not part of 2.0:

- new cloud accounts or synchronization infrastructure;
- desktop handoff;
- password or authenticated-session transfer;
- a proprietary search engine;
- a full native replacement for mature content-blocking extensions;
- expanded privacy marketing or anonymity claims.

## Release gates

2.0 must preserve the 1.1 ARM64 and x86_64 packages, architecture-aware updater,
privacy/telemetry policy, signing continuity and phone behavior. The final
candidate must pass phone, tablet and laptop-class layout testing, upgrade
testing, process-death restoration, reduced-transparency accessibility checks,
and memory testing with suspended workspaces.

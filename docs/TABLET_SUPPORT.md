# Tablet and large-screen support

Acute Web treats devices with a physical smallest width of at least 600 dp as
tablets, matching Fenix's current large-screen threshold.

## Enabled by default on tablets

- A persistent tab strip at the top of the browser. Users can turn it off or
  move it to the bottom in customization settings.
- The expanded browser toolbar, which uses the available width for more direct
  actions.
- Desktop browsing mode for newly opened tabs. Users can change the default or
  switch individual sites back to mobile mode.
- Resizable windows, rotation, Android split screen, and picture-in-picture as
  provided by the upstream Fenix activities.
- Installation on keyboard/mouse-first ChromeOS hardware that does not report a
  touchscreen.

Fenix currently excludes hinged foldable devices from the tab strip while its
foldable layouts are being improved. Acute keeps that safety check instead of
forcing a tablet layout across a hinge.

## Automated checks

Every Android build is followed by an emulator smoke test at three effective
large-screen configurations:

| Profile | Resolution | Density | Approximate smallest width |
|---|---:|---:|---:|
| Compact tablet | 1200 × 1920 | 240 dpi | 800 dp |
| Standard tablet | 1600 × 2560 | 320 dpi | 800 dp |
| Large tablet | 1848 × 2960 | 320 dpi | 924 dp |

For each profile the test installs Acute Web, launches it in portrait and
landscape, sends keyboard navigation input, checks that the process remains
alive, and captures screenshots as workflow artifacts.

## Device acceptance checklist

Before publishing the first APK, test at least one physical tablet with a
hardware keyboard or trackpad:

- onboarding and first-run consent screens in both orientations;
- opening, selecting, closing, and restoring tabs from the tab strip;
- combined search/address bar and text selection with keyboard and mouse;
- bookmarks, history, downloads, saved passwords, and extension panels;
- private browsing and switching between normal/private modes;
- desktop/mobile site switching and page zoom;
- split-screen resize from narrow phone-like width to full tablet width;
- video fullscreen and picture-in-picture;
- installing a signed update over an earlier signed APK.

The automated workflow is a crash/layout smoke test, not a substitute for this
physical-device acceptance pass.


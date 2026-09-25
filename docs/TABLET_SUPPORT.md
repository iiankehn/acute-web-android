# Tablet and large-screen support

Acute Web supports Android tablets, foldables, resizable windows, and
keyboard/mouse-first ChromeOS devices. Devices with a physical smallest width
of at least 600 dp use the tablet experience.

## Tablet behavior

On qualifying devices, Acute enables:

- a persistent tab strip, configurable in customization settings;
- an expanded toolbar that uses the available width for direct actions;
- desktop browsing mode for newly opened tabs, with per-site and default
  overrides;
- rotation and Android split-screen resizing;
- picture-in-picture where supported by Android and the website;
- installation on ChromeOS hardware that does not report a touchscreen.

Hinged foldables retain the upstream safety checks for layouts that cross a
physical hinge. Acute does not force the tablet tab strip where the layout
cannot be presented safely.

## Automated coverage

Every Android build runs launch and rotation smoke tests at three large-screen
configurations:

| Profile | Resolution | Density | Approximate smallest width |
|---|---:|---:|---:|
| Compact tablet | 1200 × 1920 | 240 dpi | 800 dp |
| Standard tablet | 1600 × 2560 | 320 dpi | 800 dp |
| Large tablet | 1848 × 2960 | 320 dpi | 924 dp |

For each profile, the workflow installs Acute, launches it in portrait and
landscape, sends keyboard navigation input, checks that the process remains
alive, and stores screenshots as build artifacts.

## Device acceptance checklist

Automated smoke tests do not replace physical-device testing. Before a stable
release, verify at least one tablet in both orientations:

- first launch and permission prompts;
- opening, selecting, closing, and restoring tabs;
- the unified search/address bar and text selection;
- bookmarks, history, downloads, saved passwords, and extension panels;
- private browsing and normal/private mode switching;
- desktop/mobile site switching and page zoom;
- split-screen resizing from narrow to full width;
- hardware keyboard and pointer navigation;
- video fullscreen and picture-in-picture;
- installation over the previous signed Acute release.

Report device-specific problems through
[GitHub Issues](https://github.com/iiankehn/acute-web-android/issues).

# Tablet and large-screen support

Acute Web supports Android tablets, resizable windows, and keyboard/mouse-first
ChromeOS devices. Devices with a physical smallest width of at least 600 dp use
the tablet experience. Foldables can run Acute through Android's normal
resizable layouts, but purpose-built posture and hinge-aware behavior remains a
future validation target.

## Tablet behavior

On qualifying devices, Acute enables:

- a persistent tab strip, configurable in customization settings;
- a single address/navigation row with direct actions on wide layouts;
- fixed browser chrome that remains visible instead of collapsing like the
  phone toolbar;
- desktop browsing mode for newly opened tabs, with per-site and default
  overrides;
- rotation and Android split-screen resizing;
- picture-in-picture where supported by Android and the website;
- installation on ChromeOS hardware that does not report a touchscreen;
- mouse back/forward buttons mapped to browser history navigation;
- opaque Midnight surfaces with native controls on phones and wide layouts.

## Keyboard shortcuts

Tablet and laptop-class layouts support conventional browser controls:

| Shortcut | Action |
|---|---|
| Ctrl/Command + L or F6 | Focus the address bar |
| Ctrl/Command + T | Open a new tab |
| Ctrl/Command + W | Close the selected tab |
| Ctrl/Command + Shift + T | Restore the most recently closed tabs |
| Ctrl/Command + Tab / Page Down | Select the next tab |
| Ctrl/Command + Shift + Tab / Page Up | Select the previous tab |
| Ctrl/Command + R or F5 | Reload the selected tab |
| Alt + Left / Right | Navigate backward or forward |

## Automated coverage

The optional `scripts/tablet_smoke.sh` helper covers these large-screen
configurations, plus a compact-phone profile. The current APK workflow does
not run an emulator or this script automatically.

| Profile | Resolution | Density | Approximate smallest width |
|---|---:|---:|---:|
| Compact tablet | 1200 × 1920 | 240 dpi | 800 dp |
| Standard tablet | 1600 × 2560 | 320 dpi | 800 dp |
| Large tablet | 1848 × 2960 | 320 dpi | 924 dp |
| Laptop landscape | 1920 × 1080 | 160 dpi | 1080 dp |

For each profile, the helper installs Acute, launches it in portrait and
landscape, checks that the process remains alive, and stores screenshots in the
requested output folder. Keyboard behavior and interactive controls still need
manual testing. Use a dedicated test device or emulator: the helper changes
display size/density and rotation settings.

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

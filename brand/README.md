# Acute brand assets (2.0 identity, in progress)

Not used by the app yet. The 2.0 palette and artwork land together once the
whole set is complete and tested; Beta 3 keeps the current identity.

## Decisions

| Item | Decision |
|---|---|
| Primary accent | Royal blue `#1D53E5` |
| Small icons (launcher, themed, notification) | Simplified fox face: `acute_fox_color.svg`, `acute_fox_mono.svg` |
| Large branding (website, covers) | Detailed frosted fox with flame tail |
| "by CORE" | Secondary attribution on the start page, About page and website; not part of every logo |
| Error-page illustrations | Stay flat and restrained; palette moves to the new identity |
| Wordmark | Lowercase "acute web", built from a properly licensed font as vector lettering, conventional flat-topped t |

## Files

| File | What it is |
|---|---|
| `acute_fox_color.svg` | Simplified fox, three flat colors: `#1D53E5`, `#E8EFFD`, `#142341`. 108 × 108 viewBox (Android adaptive-icon units) |
| `acute_fox_mono.svg` | One-color silhouette for themed and notification icons; white, recolored by Android |
| `source/` | The approved raster concepts the vectors were traced from |
| `tools/trace_fox.py` | Re-traces the sources (`python3 trace_fox.py color|mono <source> <out.svg>`; needs `pip install potracer pillow numpy`) |
| `tools/icon_sizes_preview.py` | Renders a mark at launcher, themed and status-bar sizes (`<color.png> <out.png> [<silhouette.png>]`; needs pillow) |

The transparent silhouette from the first concept round had background-removal
damage and was discarded; the silhouette is traced from the white-on-navy
version instead.

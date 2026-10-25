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
| Wordmark | Lowercase "acute web" in Lexend Bold 700 (SIL Open Font License), letter spacing −0.04 em within words only, word gap 75% of the font's space, kerning on; built as vector outlines |
| Lockup | Simplified fox left of the wordmark at the reviewed proportions (fox at 12,16; lettering at x 145, baseline 105, 100-unit em; 140-unit height) |
| Launcher background | Charcoal `#15191F` proposed, navy `#142341` compared; not decided |

## Files

| File | What it is |
|---|---|
| `acute_fox_color.svg` | Simplified fox, three flat colors: `#1D53E5`, `#E8EFFD`, `#142341`. 108 × 108 viewBox (Android adaptive-icon units) |
| `acute_fox_mono.svg` | One-color silhouette for themed and notification icons; white, recolored by Android |
| `wordmark/acute-web-lockup-{dark,light}.svg` | Fox + wordmark. `dark` has white letters (`#F2F4F7`) for dark backgrounds; `light` has navy letters (`#142341`) for light backgrounds. PNGs are 4× renders |
| `wordmark/acute-web-wordmark-{dark,light}.svg` | Lettering alone, same colors |
| `fonts/Lexend[wght].ttf`, `fonts/OFL-Lexend.txt` | Lexend variable font from google/fonts (`ofl/lexend`) and its license |
| `source/` | The approved raster concepts the vectors were traced from |
| `tools/trace_fox.py` | Re-traces the sources (`python3 trace_fox.py color|mono <source> <out.svg>`; needs `pip install potracer pillow numpy`) |
| `tools/build_wordmark.py` | Reproducible build of the approved wordmark and lockups (`python3 brand/tools/build_wordmark.py`; needs `pip install fonttools uharfbuzz cairosvg`) |
| `tools/lexend_spacing_study.py` | The eight-option spacing study (A–H) the approved option F was chosen from; kept for reference |
| `tools/icon_sizes_preview.py` | Renders a mark at launcher, themed and status-bar sizes (`<color.png> <out.png> [<silhouette.png>]`; needs pillow) |

The transparent silhouette from the first concept round had background-removal
damage and was discarded; the silhouette is traced from the white-on-navy
version instead.

"""Build the approved acute web wordmark and lockups (spacing option F).

Adapted from lexend_spacing_study.py, which produced the eight reviewed
options; this keeps its outline pipeline and builds only the approved one.
Run from the repository root: python3 brand/tools/build_wordmark.py
Needs fontTools, uharfbuzz and cairosvg (pip install fonttools uharfbuzz cairosvg).
"""
from io import BytesIO
from pathlib import Path
import xml.etree.ElementTree as ET

import cairosvg
import uharfbuzz as hb
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import instantiateVariableFont

BRAND = Path(__file__).resolve().parents[1]
TEXT = "acute web"
WEIGHT = 700            # Lexend Bold
TRACKING_EM = -0.04     # between letters within a word only
WORD_GAP = 0.75         # multiplier on the font's own space
COLORS = {"dark": "#F2F4F7", "light": "#142341"}  # white letters for dark backgrounds, navy for light

font = instantiateVariableFont(TTFont(BRAND / "fonts/Lexend[wght].ttf"), {"wght": WEIGHT}, inplace=False)
static = BytesIO(); font.save(static)
upem = font["head"].unitsPerEm
hbfont = hb.Font(hb.Face(static.getvalue())); hbfont.scale = (upem, upem)
glyphs, order = font.getGlyphSet(), font.getGlyphOrder()
buf = hb.Buffer(); buf.add_str(TEXT); buf.guess_segment_properties()
hb.shape(hbfont, buf, {"kern": True, "liga": False})
infos, positions = buf.glyph_infos, buf.glyph_positions
fox = ET.parse(BRAND / "acute_fox_color.svg").getroot()
fox_body = "".join(ET.tostring(e, encoding="unicode").replace("ns0:", "").replace(' xmlns:ns0="http://www.w3.org/2000/svg"', "") for e in fox)


def letters(origin_x, baseline, scale):
    """Glyph paths for TEXT and the advance width in font units."""
    x, parts = 0, []
    for i, (info, pos) in enumerate(zip(infos, positions)):
        if TEXT[info.cluster] == " ":
            x += pos.x_advance * WORD_GAP
            continue
        pen = SVGPathPen(glyphs); glyphs[order[info.codepoint]].draw(pen)
        parts.append(f'<path transform="translate({origin_x + (x + pos.x_offset) * scale:.4f} '
                     f'{baseline - pos.y_offset * scale:.4f}) scale({scale:.8f} {-scale:.8f})" d="{pen.getCommands()}"/>')
        x += pos.x_advance
        if i + 1 < len(infos) and TEXT[infos[i + 1].cluster] != " ":
            x += TRACKING_EM * upem
    return "".join(parts), x


def lockup(color):
    # Same geometry as the reviewed study: fox at (12, 16), text at x=145, baseline 105, 100 px em.
    scale = 100 / upem
    paths, advance = letters(145, 105, scale)
    width = 145 + advance * scale + 14
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width:.4f} 140"><title>acute web</title>'
            f'<g transform="translate(12 16)">{fox_body}</g><g fill="{color}">{paths}</g></svg>\n'), width, 140


def wordmark(color):
    # Tight box around the lettering: ascender (b) to baseline, no fox.
    scale = 100 / upem
    paths, advance = letters(0, 76, scale)
    width = advance * scale
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width:.4f} 78"><title>acute web</title>'
            f'<g fill="{color}">{paths}</g></svg>\n'), width, 78


out = BRAND / "wordmark"
out.mkdir(exist_ok=True)
for kind, build in (("lockup", lockup), ("wordmark", wordmark)):
    for theme, color in COLORS.items():
        svg, width, height = build(color)
        stem = out / f"acute-web-{kind}-{theme}"
        stem.with_suffix(".svg").write_text(svg)
        png = cairosvg.svg2png(bytestring=svg.encode(), output_width=round(width * 4), output_height=round(height * 4))
        stem.with_suffix(".png").write_bytes(png)
        print(f"{stem.name}: {width:.1f} x {height} units")

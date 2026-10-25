"""Render a mark the way Android shows launcher, themed and notification icons."""
import sys
from PIL import Image, ImageDraw, ImageFilter, ImageFont

src, out = sys.argv[1], sys.argv[2]
def load(path):
    im = Image.open(path).convert("RGBA")
    return im.crop(im.getchannel("A").point(lambda a: 255 if a > 16 else 0).getbbox())
mark = load(src)
shape = load(sys.argv[3]) if len(sys.argv) > 3 else mark
BG, TILE, TEXT = (16, 18, 22), (0, 114, 188), (220, 226, 232)

def fit(im, box):
    im = im.copy(); im.thumbnail((box, box), Image.LANCZOS); return im

def adaptive(px, shape, fill):
    # Adaptive icons: 108 dp canvas, 72 dp visible, logo in the 66 dp safe zone.
    canvas = Image.new("RGBA", (px, px), fill)
    logo = fit(mark, int(px * 66 / 72))
    canvas.alpha_composite(logo, ((px - logo.width) // 2, (px - logo.height) // 2))
    mask = Image.new("L", (px, px), 0)
    d = ImageDraw.Draw(mask)
    if shape == "circle": d.ellipse((0, 0, px - 1, px - 1), fill=255)
    else: d.rounded_rectangle((0, 0, px - 1, px - 1), radius=int(px * 0.3), fill=255)
    canvas.putalpha(mask); return canvas

def silhouette(px, fg, bg):
    alpha = fit(shape, int(px * 66 / 72)).getchannel("A").point(lambda a: 255 if a > 96 else 0)
    canvas = Image.new("RGBA", (px, px), bg + (255,))
    solid = Image.new("RGBA", alpha.size, fg + (255,)); solid.putalpha(alpha)
    canvas.alpha_composite(solid, ((px - alpha.width) // 2, (px - alpha.height) // 2))
    mask = Image.new("L", (px, px), 0); ImageDraw.Draw(mask).ellipse((0, 0, px - 1, px - 1), fill=255)
    canvas.putalpha(mask); return canvas

def notification(px):
    alpha = fit(shape, px).getchannel("A").point(lambda a: 255 if a > 96 else 0)
    solid = Image.new("RGBA", alpha.size, (255, 255, 255, 255)); solid.putalpha(alpha); return solid

rows = [
    ("Launcher, circle (48 / 72 / 144 px)", [adaptive(s, "circle", TILE) for s in (48, 72, 144)]),
    ("Launcher, squircle on dark tile", [adaptive(s, "squircle", (34, 40, 50)) for s in (48, 72, 144)]),
    ("Themed icon (one-color silhouette)", [silhouette(s, (198, 224, 247), (30, 52, 74)) for s in (48, 72, 144)]),
    ("Notification / status bar (24 / 36 / 48 px)", [notification(s) for s in (24, 36, 48)]),
]
W, rowh = 760, 200
sheet = Image.new("RGB", (W, 40 + rowh * len(rows)), BG)
d = ImageDraw.Draw(sheet)
try: font = ImageFont.truetype("DejaVuSans.ttf", 18)
except OSError: font = ImageFont.load_default()
d.text((20, 10), "Small-size test: " + src.split("/")[-1], fill=TEXT, font=font)
for i, (label, icons) in enumerate(rows):
    y = 40 + i * rowh
    d.text((20, y + 8), label, fill=TEXT, font=font)
    x = 20
    for icon in icons:
        sheet.paste(icon, (x, y + 40 + (144 - icon.height) // 2), icon); x += icon.width + 60
sheet.save(out)

"""Trace flat raster art into SVG layers with potrace (potracer)."""
import sys
import numpy as np
import potrace
from PIL import Image, ImageFilter

def mask_image(mask, grow=0):
    # Light smoothing removes generation noise without moving edges. Upper
    # layers grow slightly so no hairline of the layer below shows at seams.
    im = Image.fromarray((mask * 255).astype("uint8")).filter(ImageFilter.MedianFilter(5))
    if grow:
        im = im.filter(ImageFilter.MaxFilter(2 * grow + 1))
    return np.asarray(im) > 127

def path_data(mask, scale):
    # potrace traces dark pixels, so the shape is passed as the dark part.
    curves = potrace.Bitmap(~mask).trace(turdsize=40, turnpolicy=potrace.POTRACE_TURNPOLICY_MINORITY,
                                        alphamax=1.0, opticurve=True, opttolerance=0.2)
    f = lambda p: f"{p.x * scale:.1f} {p.y * scale:.1f}"
    parts = []
    for curve in curves:
        parts.append(f"M{f(curve.start_point)}")
        for seg in curve.segments:
            if seg.is_corner:
                parts.append(f"L{f(seg.c)}L{f(seg.end_point)}")
            else:
                parts.append(f"C{f(seg.c1)} {f(seg.c2)} {f(seg.end_point)}")
        parts.append("Z")
    return "".join(parts), len(curves)

def svg(layers, size, scale):
    view = size * scale
    body = []
    for color, mask in layers:
        d, n = path_data(mask, scale)
        body.append(f'  <path fill="{color}" fill-rule="evenodd" d="{d}"/>')
        print(f"{color}: {n} curves", file=sys.stderr)
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {view:g} {view:g}">\n'
            + "\n".join(body) + "\n</svg>\n")

if __name__ == "__main__":
    mode, src, out = sys.argv[1:4]
    im = Image.open(src)
    size = im.size[0]
    scale = 108 / size  # viewBox in Android adaptive-icon units (108 x 108 dp)
    if mode == "color":
        a = np.asarray(im.convert("RGBA")).astype(int)
        inside = mask_image(a[..., 3] > 128)
        palette = np.array([[0x1D, 0x53, 0xE5], [0xE8, 0xEF, 0xFD], [0x14, 0x23, 0x41]])
        nearest = np.argmin(((a[..., None, :3] - palette) ** 2).sum(-1), axis=-1)
        layers = [("#1D53E5", inside),
                  ("#E8EFFD", mask_image((nearest == 1) & inside, grow=1) & inside),
                  ("#142341", mask_image((nearest == 2) & inside, grow=1) & inside)]
    else:
        lum = np.asarray(im.convert("L"))
        layers = [("#FFFFFF", mask_image(lum > 160))]
    open(out, "w").write(svg(layers, size, scale))

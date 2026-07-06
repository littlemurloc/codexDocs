from __future__ import annotations

import json
import math
import random
import shutil
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont, ImageOps


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "assets" / "ui" / "export" / "basic-ui-kits-sanguo-v01"
OUT = BASE / "extracted-controls-v11-reference-mirror"
PNG = OUT / "transparent"
S = 4


def c(hex_color: str, a: int = 255) -> tuple[int, int, int, int]:
    hex_color = hex_color.lstrip("#")
    return (
        int(hex_color[0:2], 16),
        int(hex_color[2:4], 16),
        int(hex_color[4:6], 16),
        a,
    )


INK = c("#231c14")
GOLD_D = c("#6b4c24")
GOLD = c("#b78a42")
GOLD_L = c("#ecd28b")
PAPER = c("#e3dac8")
PAPER_L = c("#f3ecdd")
PAPER_D = c("#b8aa91")
JADE = c("#203b34")
JADE_L = c("#365a4f")
RED = c("#743326")
RED_L = c("#9d4d35")
GRAY = c("#77756f")
GRAY_L = c("#aaa89f")


def sb(box):
    return tuple(int(round(v * S)) for v in box)


def sp(points):
    return [(int(round(x * S)), int(round(y * S))) for x, y in points]


def new(size, fill=(0, 0, 0, 0)):
    return Image.new("RGBA", (size[0] * S, size[1] * S), fill)


def down(im):
    return im.resize((im.width // S, im.height // S), Image.Resampling.LANCZOS)


def line(d, pts, fill, w=1):
    d.line(sp(pts), fill=fill, width=max(1, int(w * S)), joint="curve")


def poly(d, pts, fill, outline=None, w=1):
    pts2 = sp(pts)
    d.polygon(pts2, fill=fill)
    if outline:
        d.line(pts2 + [pts2[0]], fill=outline, width=max(1, int(w * S)), joint="curve")


def rr(d, box, r, fill, outline=None, w=1):
    d.rounded_rectangle(sb(box), radius=int(r * S), fill=fill, outline=outline, width=max(1, int(w * S)))


def ellipse(d, box, fill, outline=None, w=1):
    d.ellipse(sb(box), fill=fill, outline=outline, width=max(1, int(w * S)))


def diamond(d, cx, cy, r, fill, outline=INK, w=1.5):
    poly(d, [(cx, cy - r), (cx + r, cy), (cx, cy + r), (cx - r, cy)], fill, outline, w)


def gradient(size, top, bottom, noise=0, seed=0):
    w, h = size[0] * S, size[1] * S
    im = Image.new("RGBA", (w, h))
    pix = im.load()
    rnd = random.Random(seed)
    for y in range(h):
        t = y / max(1, h - 1)
        r = int(top[0] * (1 - t) + bottom[0] * t)
        g = int(top[1] * (1 - t) + bottom[1] * t)
        b = int(top[2] * (1 - t) + bottom[2] * t)
        a = int(top[3] * (1 - t) + bottom[3] * t)
        for x in range(w):
            n = rnd.randint(-noise, noise) if noise else 0
            pix[x, y] = (max(0, min(255, r + n)), max(0, min(255, g + n)), max(0, min(255, b + n)), a)
    return im


def paper(size, seed=0, dark=False):
    base = c("#d4cab7") if dark else PAPER
    hi = c("#f5eedf") if not dark else c("#e0d5be")
    w, h = size[0] * S, size[1] * S
    rnd = random.Random(seed)
    data = bytes(rnd.randrange(255) for _ in range(w * h))
    noise = Image.frombytes("L", (w, h), data).filter(ImageFilter.GaussianBlur(1.3 * S))
    im = ImageOps.colorize(noise, black=base[:3], white=hi[:3]).convert("RGBA")
    im.putalpha(255)
    return im


def shadow(size, mask, offset=(0, 5), blur=5, alpha=96):
    im = new(size)
    off = ImageChops.offset(mask, int(offset[0] * S), int(offset[1] * S))
    off = off.filter(ImageFilter.GaussianBlur(blur * S)).point(lambda p: min(alpha, p))
    im.putalpha(off)
    return im


def mask_poly(size, pts):
    mask = Image.new("L", (size[0] * S, size[1] * S), 0)
    ImageDraw.Draw(mask).polygon(sp(pts), fill=255)
    return mask


def mask_rr(size, box, r=0):
    mask = Image.new("L", (size[0] * S, size[1] * S), 0)
    ImageDraw.Draw(mask).rounded_rectangle(sb(box), radius=int(r * S), fill=255)
    return mask


def masked_tex(dst, tex, mask):
    tmp = Image.new("RGBA", dst.size, (0, 0, 0, 0))
    tmp.alpha_composite(tex)
    tmp.putalpha(ImageChops.multiply(tmp.getchannel("A"), mask))
    dst.alpha_composite(tmp)


def cleanup_alpha(im):
    im = im.convert("RGBA")
    a = im.getchannel("A").point(lambda p: 0 if p < 18 else p)
    im.putalpha(a)
    return im


def save(name, im, nine=None, kind="control"):
    PNG.mkdir(parents=True, exist_ok=True)
    im = cleanup_alpha(im)
    path = PNG / f"{name}.png"
    im.save(path, optimize=True)
    RECORDS.append(
        {
            "name": name,
            "file": f"transparent/{name}.png",
            "size": [im.width, im.height],
            "nine_slice": nine,
            "kind": kind,
        }
    )
    return im


def oct_pts(box, cut=22):
    x0, y0, x1, y1 = box
    return [(x0 + cut, y0), (x1 - cut, y0), (x1, y0 + cut), (x1, y1 - cut), (x1 - cut, y1), (x0 + cut, y1), (x0, y1 - cut), (x0, y0 + cut)]


def corner_knot(d, x, y, sx, sy, scale=1.0):
    a = 18 * scale
    b = 8 * scale
    line(d, [(x, y + sy * a), (x, y), (x + sx * a, y)], GOLD_L, 2)
    line(d, [(x + sx * b, y + sy * a), (x + sx * b, y + sy * b), (x + sx * a, y + sy * b)], GOLD_D, 1.2)
    line(d, [(x + sx * 2, y + sy * (a - 5)), (x + sx * (a - 5), y + sy * 2)], GOLD, 1)
    diamond(d, x + sx * (a + 5), y + sy * (a + 5), 4 * scale, GOLD, INK, 1)


def metal_oct_frame(im, box, fill_tex, cut=24, inner=True, disabled=False):
    size = (im.width // S, im.height // S)
    d = ImageDraw.Draw(im)
    pts = oct_pts(box, cut)
    mask = mask_poly(size, pts)
    im.alpha_composite(shadow(size, mask, offset=(0, 5), blur=5, alpha=120))
    masked_tex(im, fill_tex, mask)
    colors = [(INK, 5.5), (GOLD_L if not disabled else c("#b8b5aa"), 3.4), (GOLD_D if not disabled else c("#6f6e68"), 1.7)]
    for col, wid in colors:
        poly(d, pts, None, col, wid)
    if inner:
        pts2 = oct_pts((box[0] + 10, box[1] + 10, box[2] - 10, box[3] - 10), max(8, cut - 10))
        poly(d, pts2, None, GOLD if not disabled else c("#85837c"), 1.5)
    for sx, sy, x, y in [(1, 1, box[0] + 9, box[1] + 9), (-1, 1, box[2] - 9, box[1] + 9), (1, -1, box[0] + 9, box[3] - 9), (-1, -1, box[2] - 9, box[3] - 9)]:
        corner_knot(d, x, y, sx, sy, 0.75)


def button(name, mode):
    size = (300, 92)
    im = new(size)
    if mode == "primary":
        tex = gradient(size, c("#31564b"), c("#172d29"), noise=10, seed=10)
        disabled = False
    elif mode == "secondary":
        tex = paper(size, seed=11)
        disabled = False
    else:
        tex = gradient(size, c("#aaa8a0"), c("#6b6a65"), noise=5, seed=12)
        disabled = True
    metal_oct_frame(im, (12, 18, 288, 76), tex, cut=22, disabled=disabled)
    d = ImageDraw.Draw(im)
    if mode == "primary":
        diamond(d, 150, 17, 12, JADE_L, INK, 2)
    diamond(d, 38, 47, 6, GOLD_L if not disabled else GRAY_L, INK, 1)
    diamond(d, 262, 47, 6, GOLD_L if not disabled else GRAY_L, INK, 1)
    save(name, down(im), [38, 24, 38, 24])


def icon_circle(name, symbol):
    size = (82, 82)
    im = new(size)
    d = ImageDraw.Draw(im)
    mask = Image.new("L", im.size, 0)
    ImageDraw.Draw(mask).ellipse(sb((9, 9, 73, 73)), fill=255)
    im.alpha_composite(shadow(size, mask, offset=(0, 4), blur=4, alpha=120))
    ellipse(d, (9, 9, 73, 73), c("#1e302d"), INK, 4)
    ellipse(d, (14, 14, 68, 68), c("#33423b"), GOLD_L, 3)
    ellipse(d, (21, 21, 61, 61), c("#26332f"), GOLD_D, 1)
    if symbol == "plus":
        line(d, [(29, 41), (53, 41)], GOLD_L, 5)
        line(d, [(41, 29), (41, 53)], GOLD_L, 5)
    elif symbol == "minus":
        line(d, [(29, 41), (53, 41)], GOLD_L, 5)
    elif symbol == "question":
        # Symbol only, retained as a pictogram matching the reference icon group.
        line(d, [(34, 33), (37, 27), (47, 27), (51, 32), (49, 39), (42, 43), (42, 48)], GOLD_L, 4)
        ellipse(d, (38, 55, 46, 63), GOLD_L)
    elif symbol == "gear":
        for i in range(8):
            a = math.tau * i / 8
            x = 41 + math.cos(a) * 20
            y = 41 + math.sin(a) * 20
            ellipse(d, (x - 4, y - 4, x + 4, y + 4), GOLD_L)
        ellipse(d, (25, 25, 57, 57), None, GOLD_L, 5)
        ellipse(d, (36, 36, 46, 46), c("#26332f"))
    save(name, down(im), None)


def title_badge(size=(270, 64), side_tabs=True):
    im = new(size)
    d = ImageDraw.Draw(im)
    w, h = size
    pts = [(22, 8), (w - 22, 8), (w - 6, h / 2), (w - 22, h - 8), (22, h - 8), (6, h / 2)]
    mask = mask_poly(size, pts)
    im.alpha_composite(shadow(size, mask, offset=(0, 4), blur=4, alpha=110))
    masked_tex(im, gradient(size, c("#314b43"), c("#1b302b"), noise=8, seed=20), mask)
    poly(d, pts, None, INK, 4)
    poly(d, [(28, 14), (w - 28, 14), (w - 14, h / 2), (w - 28, h - 14), (28, h - 14), (14, h / 2)], None, GOLD_L, 2)
    if side_tabs:
        for x in (18, w - 18):
            diamond(d, x, h / 2, 5, GOLD, INK, 1)
            line(d, [(x - 9 if x > w / 2 else x + 9, h / 2 - 16), (x - 9 if x > w / 2 else x + 9, h / 2 + 16)], GOLD_D, 1)
    return im


def mountains(d, box, alpha=58):
    x0, y0, x1, y1 = box
    rnd = random.Random(38)
    tone1 = c("#ddd6c7")
    tone2 = c("#d2cbbc")
    for band, col in enumerate([tone1, tone2]):
        base = y1 - 16 - band * 12
        pts = [(x0, y1), (x0, base)]
        for x in range(int(x0), int(x1) + 1, 28):
            pts.append((x, base - rnd.randint(6, 38) - band * 8))
        pts.append((x1, y1))
        poly(d, pts, col)
    for i in range(4):
        yy = y1 - 18 - i * 5
        line(d, [(x0 + 20 + i * 18, yy), (x0 + 80 + i * 22, yy - 9), (x0 + 150 + i * 25, yy - 3)], c("#b8b1a4"), 0.8)


def clouds(d, box, alpha=42):
    x0, y0, x1, y1 = box
    col = c("#c9c2b3")
    for cx, cy, r in [(x1 - 110, y0 + 55, 24), (x1 - 80, y0 + 48, 17), (x1 - 65, y0 + 66, 22)]:
        ellipse(d, (cx - r, cy - r / 2, cx + r, cy + r / 2), None, col, 1)
    line(d, [(x1 - 150, y0 + 70), (x1 - 40, y0 + 70)], col, 1)


def frame_panel(name, size, modal=False):
    im = new(size)
    d = ImageDraw.Draw(im)
    w, h = size
    box = (14, 22, w - 14, h - 14)
    rr_mask = mask_rr(size, box, 2)
    im.alpha_composite(shadow(size, rr_mask, offset=(0, 5), blur=5, alpha=100))
    masked_tex(im, paper(size, seed=30), rr_mask)
    rr(d, box, 2, None, INK, 4)
    rr(d, (20, 28, w - 20, h - 20), 2, None, GOLD_L, 2.5)
    rr(d, (28, 36, w - 28, h - 28), 1, None, GOLD_D, 1.3)
    corner_knot(d, 30, 38, 1, 1, 1.2)
    corner_knot(d, w - 30, 38, -1, 1, 1.2)
    corner_knot(d, 30, h - 30, 1, -1, 1.2)
    corner_knot(d, w - 30, h - 30, -1, -1, 1.2)
    mountains(d, (40, h - 105, w - 42, h - 30), 48)
    clouds(d, (36, 38, w - 36, h - 36), 36)
    badge = title_badge((260 if not modal else 220, 58))
    im.alpha_composite(badge, ((w - badge.width // S) // 2 * S, 6 * S))
    if modal:
        small1 = control_button((116, 50), primary=True)
        small2 = control_button((116, 50), primary=False)
        im.alpha_composite(small1, (50 * S, (h - 70) * S))
        im.alpha_composite(small2, ((w - 166) * S, (h - 70) * S))
        diamond(d, w / 2, h - 12, 12, GOLD_L, INK, 2)
    save(name, down(im), [44, 54, 44, 42])


def control_button(size, primary=True):
    im = new(size)
    tex = gradient(size, c("#31564b"), c("#172d29"), noise=5, seed=41) if primary else paper(size, seed=42)
    metal_oct_frame(im, (5, 6, size[0] - 5, size[1] - 6), tex, cut=13, inner=True)
    return im


def title_bar():
    size = (560, 70)
    im = new(size)
    d = ImageDraw.Draw(im)
    w, h = size
    pts = [(28, 10), (w - 28, 10), (w - 7, h / 2), (w - 28, h - 10), (28, h - 10), (7, h / 2)]
    mask = mask_poly(size, pts)
    im.alpha_composite(shadow(size, mask, offset=(0, 4), blur=4, alpha=100))
    masked_tex(im, gradient(size, c("#314b43"), c("#1a302b"), noise=8, seed=50), mask)
    poly(d, pts, None, INK, 4)
    poly(d, [(36, 16), (w - 36, 16), (w - 16, h / 2), (w - 36, h - 16), (36, h - 16), (16, h / 2)], None, GOLD_L, 2)
    for x, sx in [(22, 1), (w - 22, -1)]:
        diamond(d, x, h / 2, 13, c("#2a3d37"), INK, 2)
        corner_knot(d, x + sx * 7, h / 2 - 16, sx, 1, 0.65)
        corner_knot(d, x + sx * 7, h / 2 + 16, sx, -1, 0.65)
    save("title_bar_blank", down(im), [52, 20, 52, 20])


def tabs():
    size = (510, 68)
    im = new(size)
    d = ImageDraw.Draw(im)
    x = 0
    widths = [135, 125, 125, 125]
    for i, wid in enumerate(widths):
        pts = [(x + 16, 12), (x + wid - 10, 12), (x + wid, 24), (x + wid, 58), (x, 58), (x, 24)]
        mask = mask_poly(size, pts)
        tex = gradient(size, c("#31564b"), c("#1b312c"), noise=6, seed=61) if i == 0 else paper(size, seed=62 + i)
        masked_tex(im, tex, mask)
        poly(d, pts, None, INK, 3)
        poly(d, [(x + 23, 19), (x + wid - 16, 19), (x + wid - 7, 28), (x + wid - 7, 51), (x + 7, 51), (x + 7, 28)], None, GOLD_L if i == 0 else GOLD_D, 1.3)
        x += wid - 4
    save("tabs_strip_blank", down(im), [42, 18, 42, 18])


def list_row():
    size = (560, 95)
    im = new(size)
    d = ImageDraw.Draw(im)
    box = (8, 10, 552, 86)
    rr_mask = mask_rr(size, box, 4)
    im.alpha_composite(shadow(size, rr_mask, offset=(0, 4), blur=3, alpha=80))
    masked_tex(im, paper(size, seed=70), rr_mask)
    rr(d, box, 4, None, INK, 3)
    rr(d, (14, 16, 546, 80), 2, None, GOLD_L, 2)
    rr(d, (22, 22, 105, 74), 2, None, GOLD_D, 1.4)
    rr(d, (29, 27, 92, 69), 1, JADE, GOLD_L, 1)
    mountains(d, (150, 45, 455, 78), 34)
    line(d, [(520, 35), (534, 48), (520, 62)], GOLD_L, 3)
    save("list_row_blank", down(im), [112, 24, 44, 24])


def input_box():
    size = (560, 72)
    im = new(size)
    d = ImageDraw.Draw(im)
    box = (8, 9, 552, 62)
    rr_mask = mask_rr(size, box, 3)
    im.alpha_composite(shadow(size, rr_mask, offset=(0, 4), blur=3, alpha=80))
    masked_tex(im, paper(size, seed=80), rr_mask)
    rr(d, box, 3, None, INK, 3)
    rr(d, (15, 16, 545, 55), 2, None, GOLD_L, 2)
    diamond(d, 523, 36, 11, c("#e4dcc8"), INK, 1.8)
    diamond(d, 523, 36, 5, GOLD, INK, 1)
    save("input_box_blank", down(im), [44, 22, 44, 22])


def checkbox(name, checked=False):
    size = (44, 44)
    im = new(size)
    d = ImageDraw.Draw(im)
    rr(d, (8, 8, 36, 36), 1, c("#2f3932") if checked else c("#6a6458"), INK, 3)
    rr(d, (12, 12, 32, 32), 1, None, GOLD_L, 1.4)
    if checked:
        line(d, [(15, 23), (21, 29), (31, 15)], GOLD_L, 4)
    save(name, down(im), None)


def toggle(name, on=False):
    size = (118, 42)
    im = new(size)
    d = ImageDraw.Draw(im)
    box = (8, 7, 110, 35)
    rr_mask = mask_rr(size, box, 15)
    masked_tex(im, gradient(size, c("#31564b"), c("#172d29"), noise=5, seed=91) if on else gradient(size, c("#746c5f"), c("#3b3832"), noise=4, seed=92), rr_mask)
    rr(d, box, 15, None, INK, 3)
    rr(d, (13, 12, 105, 30), 10, None, GOLD_D, 1)
    cx = 92 if on else 26
    ellipse(d, (cx - 17, 4, cx + 17, 38), c("#d7c28a"), INK, 2)
    ellipse(d, (cx - 12, 9, cx + 12, 33), c("#b69a5a"), GOLD_L, 1)
    save(name, down(im), [28, 14, 28, 14])


def progress_bar():
    size = (615, 60)
    im = new(size)
    d = ImageDraw.Draw(im)
    pts = oct_pts((8, 12, 607, 48), 24)
    mask = mask_poly(size, pts)
    im.alpha_composite(shadow(size, mask, offset=(0, 4), blur=4, alpha=95))
    masked_tex(im, gradient(size, c("#4b4035"), c("#24211e"), noise=5, seed=101), mask)
    fill_mask = mask_poly(size, oct_pts((10, 14, 390, 46), 20))
    masked_tex(im, gradient(size, c("#376052"), c("#1e3c34"), noise=8, seed=102), fill_mask)
    poly(d, pts, None, INK, 4)
    poly(d, oct_pts((16, 18, 599, 42), 17), None, GOLD_L, 1.8)
    for x, sx in [(22, 1), (593, -1)]:
        corner_knot(d, x, 30, sx, 1, 0.55)
        corner_knot(d, x, 30, sx, -1, 0.55)
    save("progress_bar_65_blank", down(im), [40, 18, 40, 18])


def tooltip():
    size = (305, 145)
    im = new(size)
    d = ImageDraw.Draw(im)
    box = (8, 8, 297, 124)
    rr_mask = mask_rr(size, box, 3)
    im.alpha_composite(shadow(size, rr_mask, offset=(0, 4), blur=4, alpha=100))
    masked_tex(im, gradient(size, c("#243831"), c("#13231f"), noise=7, seed=111), rr_mask)
    rr(d, box, 3, None, INK, 3)
    rr(d, (14, 14, 291, 118), 2, None, GOLD_L, 1.7)
    poly(d, [(140, 124), (160, 124), (150, 137)], c("#17231f"), INK, 2)
    clouds(d, (160, 72, 285, 120), 44)
    save("tooltip_panel_blank", down(im), [34, 34, 34, 48])


def notification():
    size = (710, 95)
    im = new(size)
    d = ImageDraw.Draw(im)
    body = (68, 18, 698, 75)
    rr_mask = mask_rr(size, body, 3)
    im.alpha_composite(shadow(size, rr_mask, offset=(0, 4), blur=4, alpha=90))
    masked_tex(im, paper(size, seed=121), rr_mask)
    rr(d, body, 3, None, INK, 3)
    rr(d, (76, 26, 690, 67), 2, None, GOLD_L, 1.8)
    left_pts = [(18, 17), (90, 17), (100, 28), (100, 74), (18, 74), (8, 60), (8, 31)]
    left_mask = mask_poly(size, left_pts)
    masked_tex(im, gradient(size, RED_L, RED, noise=9, seed=122), left_mask)
    poly(d, left_pts, None, INK, 3)
    poly(d, [(27, 25), (84, 25), (91, 32), (91, 66), (26, 66), (18, 57), (18, 35)], None, GOLD_L, 1.5)
    mountains(d, (410, 35, 620, 70), 45)
    diamond(d, 665, 47, 15, c("#40362b"), INK, 2)
    diamond(d, 665, 47, 7, GOLD_L, INK, 1)
    save("notification_banner_blank", down(im), [92, 25, 45, 25])


def close_button():
    size = (92, 92)
    im = new(size)
    d = ImageDraw.Draw(im)
    pts = [(46, 7), (85, 46), (46, 85), (7, 46)]
    mask = mask_poly(size, pts)
    im.alpha_composite(shadow(size, mask, offset=(0, 4), blur=4, alpha=110))
    masked_tex(im, gradient(size, c("#8d3f2d"), c("#4b2019"), noise=7, seed=131), mask)
    poly(d, pts, None, INK, 4)
    poly(d, [(46, 16), (76, 46), (46, 76), (16, 46)], None, GOLD_L, 2)
    line(d, [(32, 32), (60, 60)], GOLD_L, 5)
    line(d, [(60, 32), (32, 60)], GOLD_L, 5)
    save("close_button_diamond", down(im), None)


def panel_bg(name, variant):
    size = (285, 210)
    im = new(size)
    d = ImageDraw.Draw(im)
    dark = variant == "dragon_dark"
    seed_map = {"mountain": 141, "compass": 142, "dragon_dark": 143, "emblem": 144}
    masked_tex(im, gradient(size, JADE_L, JADE, noise=10, seed=140) if dark else paper(size, seed=seed_map[variant]), Image.new("L", im.size, 255))
    rr(d, (5, 5, 280, 205), 1, None, INK, 3)
    rr(d, (10, 10, 275, 200), 1, None, GOLD_L, 1.5)
    if variant == "mountain":
        mountains(d, (20, 80, 265, 195), 54)
        clouds(d, (35, 25, 250, 100), 42)
    elif variant == "compass":
        for r in [30, 48, 67, 86]:
            ellipse(d, (142 - r, 105 - r, 142 + r, 105 + r), None, c("#817865", 60), 1)
        for a in range(0, 360, 30):
            x = 142 + math.cos(math.radians(a)) * 86
            y = 105 + math.sin(math.radians(a)) * 86
            line(d, [(142, 105), (x, y)], c("#817865", 35), 1)
        ellipse(d, (130, 93, 154, 117), c("#283a36"), INK, 2)
        ellipse(d, (136, 99, 148, 111), GOLD_L)
    elif variant == "dragon_dark":
        for r in [34, 54, 78]:
            ellipse(d, (175 - r * 1.4, 105 - r, 175 + r * 1.4, 105 + r), None, c("#c29e58", 45), 2)
        line(d, [(100, 125), (145, 80), (190, 105), (230, 58)], c("#c29e58", 50), 3)
        clouds(d, (20, 30, 150, 160), 46)
    else:
        mountains(d, (18, 65, 266, 195), 50)
        ellipse(d, (115, 78, 170, 133), c("#314b43"), GOLD_L, 3)
        for a, col in [(0, RED), (90, JADE_L), (180, c("#275e7d")), (270, c("#6e5521"))]:
            x = 142 + math.cos(math.radians(a)) * 78
            y = 105 + math.sin(math.radians(a)) * 78
            diamond(d, x, y, 13, col, INK, 2)
        diamond(d, 142, 105, 34, c("#2b453e"), GOLD_L, 2)
    for sx, sy, x, y in [(1, 1, 18, 18), (-1, 1, 267, 18), (1, -1, 18, 192), (-1, -1, 267, 192)]:
        corner_knot(d, x, y, sx, sy, 0.9)
    save(name, down(im), [26, 26, 26, 26], "background")


def dot(name, top, bottom):
    size = (52, 52)
    im = new(size)
    d = ImageDraw.Draw(im)
    ellipse(d, (4, 4, 48, 48), GOLD_L, INK, 2.5)
    ellipse(d, (8, 8, 44, 44), GOLD, GOLD_D, 1.4)
    mask = Image.new("L", im.size, 0)
    ImageDraw.Draw(mask).ellipse(sb((12, 12, 40, 40)), fill=255)
    masked_tex(im, gradient(size, top, bottom, noise=3, seed=170), mask)
    ellipse(d, (18, 13, 28, 23), c("#ffffff", 100))
    save(name, down(im), None)


def scrollbar():
    size = (555, 54)
    im = new(size)
    d = ImageDraw.Draw(im)
    pts = oct_pts((22, 16, 533, 38), 15)
    mask = mask_poly(size, pts)
    im.alpha_composite(shadow(size, mask, offset=(0, 4), blur=4, alpha=90))
    masked_tex(im, gradient(size, c("#4c453b"), c("#292622"), noise=4, seed=180), mask)
    poly(d, pts, None, INK, 3)
    poly(d, oct_pts((30, 20, 525, 34), 10), None, GOLD_L, 1.4)
    for x, sx in [(19, -1), (536, 1)]:
        poly(d, [(x, 27), (x + sx * 16, 12), (x + sx * 16, 42)], c("#8a6a38"), INK, 2)
        line(d, [(x + sx * 3, 27), (x + sx * 14, 18), (x + sx * 14, 36), (x + sx * 3, 27)], GOLD_L, 1.2)
    knob = title_badge((112, 44), side_tabs=False)
    im.alpha_composite(knob, ((size[0] // 2 - 56) * S, 5 * S))
    d = ImageDraw.Draw(im)
    for dx in [-8, 0, 8]:
        line(d, [(size[0] / 2 + dx, 20), (size[0] / 2 + dx, 34)], GOLD_L, 1.5)
    for dy in [23, 31]:
        line(d, [(size[0] / 2 - 12, dy), (size[0] / 2 + 12, dy)], GOLD_L, 1.5)
    save("scrollbar_horizontal", down(im), [44, 18, 44, 18])


def sheet_preview():
    size = (1200, 1536)
    sheet = Image.new("RGBA", size, c("#eee7d8"))
    d = ImageDraw.Draw(sheet)
    masked_tex(sheet, paper(size, seed=300), Image.new("L", (size[0] * S, size[1] * S), 255))
    def paste(name, xy, scale=1.0):
        im = Image.open(PNG / f"{name}.png").convert("RGBA")
        if scale != 1:
            im = im.resize((int(im.width * scale), int(im.height * scale)), Image.Resampling.LANCZOS)
        sheet.alpha_composite(im, xy)
    paste("button_primary_blank", (30, 70))
    paste("button_secondary_blank", (30, 210))
    paste("button_disabled_blank", (30, 350))
    for i, n in enumerate(["icon_button_plus", "icon_button_minus", "icon_button_question", "icon_button_gear"]):
        paste(n, (315 + i * 95, 68))
    paste("large_window_frame_blank", (295, 180))
    paste("modal_popup_frame_blank", (720, 180))
    paste("title_bar_blank", (28, 535))
    paste("tabs_strip_blank", (535, 540))
    paste("list_row_blank", (30, 660))
    paste("input_box_blank", (535, 670))
    paste("checkbox_empty", (45, 787))
    paste("checkbox_checked", (45, 825))
    paste("toggle_off", (265, 788))
    paste("toggle_on", (265, 830))
    paste("progress_bar_65_blank", (455, 790))
    paste("tooltip_panel_blank", (45, 925))
    paste("notification_banner_blank", (380, 940))
    paste("close_button_diamond", (875, 1075))
    for i, n in enumerate(["panel_bg_mountain", "panel_bg_compass", "panel_bg_dragon_dark", "panel_bg_emblem"]):
        paste(n, (28 + i * 250, 1160), 0.86)
    for i, n in enumerate(["status_dot_gold", "status_dot_blue", "status_dot_red", "status_dot_green", "status_dot_gray"]):
        paste(n, (33 + i * 60, 1430))
    paste("scrollbar_horizontal", (510, 1428))
    # Silent separators only; no text labels.
    for y in [500, 760, 900, 1110, 1395]:
        line(d, [(25, y), (size[0] - 25, y)], c("#b9ae9b"), 1)
    sheet.convert("RGB").save(OUT / "preview_reference_mirror_no_text.png", quality=95)


def alpha_report():
    out = []
    for path in sorted(PNG.glob("*.png")):
        im = Image.open(path).convert("RGBA")
        box = im.getchannel("A").getbbox()
        if box:
            out.append({"file": str(path.relative_to(OUT)).replace("\\", "/"), "size": [im.width, im.height], "alpha_bbox": box})
    (OUT / "alpha_report.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")


def main():
    if OUT.exists():
        shutil.rmtree(OUT)
    PNG.mkdir(parents=True, exist_ok=True)
    button("button_primary_blank", "primary")
    button("button_secondary_blank", "secondary")
    button("button_disabled_blank", "disabled")
    icon_circle("icon_button_plus", "plus")
    icon_circle("icon_button_minus", "minus")
    icon_circle("icon_button_question", "question")
    icon_circle("icon_button_gear", "gear")
    frame_panel("large_window_frame_blank", (430, 300), modal=False)
    frame_panel("modal_popup_frame_blank", (285, 300), modal=True)
    title_bar()
    tabs()
    list_row()
    input_box()
    checkbox("checkbox_empty", False)
    checkbox("checkbox_checked", True)
    toggle("toggle_off", False)
    toggle("toggle_on", True)
    progress_bar()
    tooltip()
    notification()
    close_button()
    panel_bg("panel_bg_mountain", "mountain")
    panel_bg("panel_bg_compass", "compass")
    panel_bg("panel_bg_dragon_dark", "dragon_dark")
    panel_bg("panel_bg_emblem", "emblem")
    dot("status_dot_gold", c("#ffd56e"), c("#a16c1f"))
    dot("status_dot_blue", c("#58b9ff"), c("#13498b"))
    dot("status_dot_red", c("#f16a55"), c("#8a251d"))
    dot("status_dot_green", c("#55c982"), c("#1f7042"))
    dot("status_dot_gray", c("#66675f"), c("#30322f"))
    scrollbar()
    manifest = {
        "version": "v11-reference-mirror",
        "note": "Redrawn from the provided reference sheet. No baked UI text is included in the exported controls.",
        "asset_count": len(RECORDS),
        "assets": RECORDS,
    }
    (OUT / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    (OUT / "README.md").write_text(
        "# Reference Mirror UI Controls v11\n\n"
        "按参考图重新绘制的三国风基础 UI 控件。单个控件资源均过滤掉文字，预留程序叠字空间。\n\n"
        "- `transparent/`: 透明 PNG 切片\n"
        "- `preview_reference_mirror_no_text.png`: 无文字整套预览\n"
        "- `manifest.json`: 尺寸与九宫格建议\n",
        encoding="utf-8",
    )
    alpha_report()
    sheet_preview()
    print(json.dumps({"output": str(OUT), "assets": len(RECORDS)}, ensure_ascii=False))


RECORDS = []


if __name__ == "__main__":
    main()

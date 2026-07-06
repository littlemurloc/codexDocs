from __future__ import annotations

import json
import math
import os
import random
import shutil
import stat
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont, ImageOps


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "assets" / "ui" / "export" / "basic-ui-kits-sanguo-v01"
OUT = BASE / "extracted-controls-v07-production-clean"
S = 4


def assert_safe_path(path: Path) -> None:
    root = ROOT.resolve()
    resolved = path.resolve()
    if root != resolved and root not in resolved.parents:
        raise RuntimeError(f"Refusing to write outside workspace: {resolved}")


def rgba(hex_color: str, a: int = 255) -> tuple[int, int, int, int]:
    hex_color = hex_color.lstrip("#")
    return (
        int(hex_color[0:2], 16),
        int(hex_color[2:4], 16),
        int(hex_color[4:6], 16),
        a,
    )


def scale_box(box):
    return tuple(int(round(v * S)) for v in box)


def scale_pts(points):
    return [(int(round(x * S)), int(round(y * S))) for x, y in points]


def new(size, color=(0, 0, 0, 0)):
    return Image.new("RGBA", (size[0] * S, size[1] * S), color)


def down(im: Image.Image) -> Image.Image:
    return im.resize((im.size[0] // S, im.size[1] // S), Image.Resampling.LANCZOS)


def layer(im: Image.Image, src: Image.Image) -> None:
    im.alpha_composite(src)


def draw_rr(draw, box, radius, fill, outline=None, width=1):
    draw.rounded_rectangle(
        scale_box(box),
        radius=int(radius * S),
        fill=fill,
        outline=outline,
        width=max(1, int(width * S)),
    )


def draw_el(draw, box, fill, outline=None, width=1):
    draw.ellipse(scale_box(box), fill=fill, outline=outline, width=max(1, int(width * S)))


def draw_poly(draw, points, fill, outline=None, width=1):
    pts = scale_pts(points)
    draw.polygon(pts, fill=fill)
    if outline:
        draw.line(pts + [pts[0]], fill=outline, width=max(1, int(width * S)), joint="curve")


def draw_line(draw, points, fill, width=1):
    draw.line(scale_pts(points), fill=fill, width=max(1, int(width * S)), joint="curve")


def text(draw, xy, value, fill, size=22, anchor="mm"):
    try:
        font = ImageFont.truetype("arial.ttf", size * S)
    except OSError:
        font = ImageFont.load_default(size * S)
    draw.text((xy[0] * S, xy[1] * S), value, fill=fill, font=font, anchor=anchor)


def vertical_gradient(size, top, bottom, seed=0, noise=10):
    w, h = size[0] * S, size[1] * S
    img = Image.new("RGBA", (w, h))
    pix = img.load()
    rnd = random.Random(seed)
    for y in range(h):
        t = y / max(1, h - 1)
        r = int(top[0] * (1 - t) + bottom[0] * t)
        g = int(top[1] * (1 - t) + bottom[1] * t)
        b = int(top[2] * (1 - t) + bottom[2] * t)
        a = int(top[3] * (1 - t) + bottom[3] * t)
        for x in range(w):
            n = rnd.randint(-noise, noise) if noise else 0
            pix[x, y] = (
                max(0, min(255, r + n)),
                max(0, min(255, g + n)),
                max(0, min(255, b + n)),
                a,
            )
    return img.filter(ImageFilter.GaussianBlur(0.18 * S))


def paper_texture(size, base, tint, seed=0, strength=22):
    w, h = size[0] * S, size[1] * S
    rnd = random.Random(seed)
    data = bytearray()
    for _ in range(w * h):
        data.append(rnd.randrange(255))
    noise = Image.frombytes("L", (w, h), bytes(data)).filter(ImageFilter.GaussianBlur(1.1 * S))
    colored = ImageOps.colorize(noise, black=base[:3], white=tint[:3]).convert("RGBA")
    alpha = Image.new("L", (w, h), 255)
    colored.putalpha(alpha)
    return colored


def shadow(size, box, radius=18, alpha=95, offset=(0, 8), blur=10, polygon=None):
    im = new(size)
    mask = Image.new("L", im.size, 0)
    d = ImageDraw.Draw(mask)
    if polygon:
        d.polygon(scale_pts([(x + offset[0], y + offset[1]) for x, y in polygon]), fill=alpha)
    else:
        b = (box[0] + offset[0], box[1] + offset[1], box[2] + offset[0], box[3] + offset[1])
        d.rounded_rectangle(scale_box(b), radius=int(radius * S), fill=alpha)
    mask = mask.filter(ImageFilter.GaussianBlur(blur * S))
    im.putalpha(mask)
    return im


def paste_masked(dst, src, mask, xy=(0, 0)):
    tmp = Image.new("RGBA", dst.size, (0, 0, 0, 0))
    tmp.alpha_composite(src, (xy[0] * S, xy[1] * S))
    tmp.putalpha(ImageChops.multiply(tmp.getchannel("A"), mask))
    dst.alpha_composite(tmp)


def oct_mask(size, box, cut=22, radius=0):
    mask = Image.new("L", (size[0] * S, size[1] * S), 0)
    d = ImageDraw.Draw(mask)
    x0, y0, x1, y1 = box
    pts = [
        (x0 + cut, y0),
        (x1 - cut, y0),
        (x1, y0 + cut),
        (x1, y1 - cut),
        (x1 - cut, y1),
        (x0 + cut, y1),
        (x0, y1 - cut),
        (x0, y0 + cut),
    ]
    d.polygon(scale_pts(pts), fill=255)
    if radius > 0:
        mask = mask.filter(ImageFilter.GaussianBlur(radius * S))
        mask = mask.point(lambda p: 255 if p > 120 else 0)
    return mask


def inset(box, n):
    return (box[0] + n, box[1] + n, box[2] - n, box[3] - n)


def diamond(draw, cx, cy, r, fill, outline, width=2):
    pts = [(cx, cy - r), (cx + r, cy), (cx, cy + r), (cx - r, cy)]
    draw_poly(draw, pts, fill, outline, width)


def corner_marks(draw, box, pal, heavy=False):
    x0, y0, x1, y1 = box
    gold = pal["gold"]
    dark = pal["dark"]
    for sx, sy in [(1, 1), (-1, 1), (1, -1), (-1, -1)]:
        cx = x0 if sx == 1 else x1
        cy = y0 if sy == 1 else y1
        lx = cx + sx * (22 if heavy else 16)
        ly = cy + sy * (22 if heavy else 16)
        draw_line(draw, [(cx + sx * 7, cy), (lx, cy), (lx, cy + sy * 9)], gold, 2.2 if heavy else 1.5)
        draw_line(draw, [(cx, cy + sy * 7), (cx, ly), (cx + sx * 9, ly)], dark, 1.1)


def border_panel(size, box, pal, fill_kind="paper", heavy=False, seed=0, hollow=False):
    im = new(size)
    d = ImageDraw.Draw(im)
    layer(im, shadow(size, box, radius=16 if not heavy else 20, alpha=72, offset=(0, 5), blur=7))
    if not hollow:
        inner_tex = (
            paper_texture(size, pal["paper"], pal["paper_hi"], seed=seed)
            if fill_kind == "paper"
            else vertical_gradient(size, pal["panel_hi"], pal["panel_lo"], seed=seed, noise=6)
        )
        mask = Image.new("L", im.size, 0)
        md = ImageDraw.Draw(mask)
        md.rounded_rectangle(scale_box(box), radius=(10 if not heavy else 14) * S, fill=255)
        paste_masked(im, inner_tex, mask)
    draw_rr(d, box, 10 if not heavy else 14, None, pal["dark"], 3.5 if heavy else 2.6)
    draw_rr(d, inset(box, 5), 8 if not heavy else 11, None, pal["gold_hi"], 2.2 if heavy else 1.4)
    draw_rr(d, inset(box, 12), 5 if not heavy else 7, None, pal["line"], 1.1)
    corner_marks(d, inset(box, 14), pal, heavy=heavy)
    return im


def carved_panel(size, box, pal, fill_kind="paper", seed=0, heavy=False):
    im = border_panel(size, box, pal, fill_kind=fill_kind, seed=seed, heavy=heavy)
    d = ImageDraw.Draw(im)
    x0, y0, x1, y1 = box
    for y in (y0 + 22, y1 - 22):
        draw_line(d, [(x0 + 52, y), (x1 - 52, y)], pal["line_soft"], 1)
        diamond(d, (x0 + x1) / 2, y, 5, pal["gold"], pal["dark"], 1)
    return im


def button_asset(size, pal, mode="primary"):
    w, h = size
    im = new(size)
    if mode == "disabled":
        top, bottom, line = pal["disabled_hi"], pal["disabled_lo"], pal["disabled_line"]
    elif mode == "danger":
        top, bottom, line = pal["red_hi"], pal["red_lo"], pal["red_line"]
    elif mode == "secondary":
        top, bottom, line = pal["paper_hi"], pal["paper"], pal["line"]
    else:
        top, bottom, line = pal["panel_hi"], pal["panel_lo"], pal["green_line"]
    box = (12, 12, w - 12, h - 12)
    pts = [
        (box[0] + 36, box[1]),
        (box[2] - 36, box[1]),
        (box[2] - 4, box[1] + 22),
        (box[2], box[3] - 22),
        (box[2] - 36, box[3]),
        (box[0] + 36, box[3]),
        (box[0], box[3] - 22),
        (box[0] + 4, box[1] + 22),
    ]
    layer(im, shadow(size, box, alpha=80, offset=(0, 6), blur=8, polygon=pts))
    mask = oct_mask(size, box, cut=30)
    paste_masked(im, vertical_gradient(size, top, bottom, seed=10), mask)
    d = ImageDraw.Draw(im)
    draw_poly(d, pts, None, pal["dark"], 3)
    draw_poly(d, [(x + (1 if x < w / 2 else -1) * 7, y + (1 if y < h / 2 else -1) * 7) for x, y in pts], None, pal["gold_hi"], 1.8)
    draw_line(d, [(50, 24), (w - 50, 24)], pal["shine"], 1.1)
    draw_line(d, [(50, h - 24), (w - 50, h - 24)], line, 1.1)
    diamond(d, 35, h / 2, 9, pal["gold"], pal["dark"], 1.4)
    diamond(d, w - 35, h / 2, 9, pal["gold"], pal["dark"], 1.4)
    return down(im)


def icon_symbol(draw, name, cx, cy, pal):
    fg = pal["icon"]
    dark = pal["dark"]
    if name == "close":
        draw_line(draw, [(cx - 17, cy - 17), (cx + 17, cy + 17)], fg, 5)
        draw_line(draw, [(cx + 17, cy - 17), (cx - 17, cy + 17)], fg, 5)
    elif name == "plus":
        draw_line(draw, [(cx - 20, cy), (cx + 20, cy)], fg, 5)
        draw_line(draw, [(cx, cy - 20), (cx, cy + 20)], fg, 5)
    elif name == "minus":
        draw_line(draw, [(cx - 21, cy), (cx + 21, cy)], fg, 5)
    elif name == "arrow":
        draw_line(draw, [(cx - 15, cy), (cx + 18, cy)], fg, 5)
        draw_poly(draw, [(cx + 22, cy), (cx + 6, cy - 13), (cx + 6, cy + 13)], fg)
    elif name == "gear":
        for i in range(8):
            a = math.pi * i / 4
            x = cx + math.cos(a) * 23
            y = cy + math.sin(a) * 23
            draw_el(draw, (x - 4, y - 4, x + 4, y + 4), fg)
        draw_el(draw, (cx - 18, cy - 18, cx + 18, cy + 18), None, fg, 5)
        draw_el(draw, (cx - 6, cy - 6, cx + 6, cy + 6), dark)
    elif name == "sword":
        draw_line(draw, [(cx - 20, cy + 21), (cx + 18, cy - 17)], fg, 5)
        draw_poly(draw, [(cx + 18, cy - 17), (cx + 25, cy - 28), (cx + 22, cy - 13)], fg)
        draw_line(draw, [(cx - 25, cy + 8), (cx - 7, cy + 26)], pal["gold"], 4)
    elif name == "flag":
        draw_line(draw, [(cx - 18, cy - 24), (cx - 18, cy + 25)], fg, 4)
        draw_poly(draw, [(cx - 15, cy - 22), (cx + 22, cy - 14), (cx - 15, cy - 2)], pal["red_hi"], pal["dark"], 2)
    elif name == "helmet":
        draw_el(draw, (cx - 25, cy - 20, cx + 25, cy + 24), pal["gold"], dark, 3)
        draw_rr(draw, (cx - 19, cy - 2, cx + 19, cy + 23), 5, pal["panel_lo"], dark, 2)
        draw_line(draw, [(cx, cy - 26), (cx, cy - 4)], pal["red_hi"], 5)
    elif name == "scroll":
        draw_rr(draw, (cx - 24, cy - 18, cx + 24, cy + 18), 5, pal["paper_hi"], dark, 3)
        draw_el(draw, (cx - 30, cy - 20, cx - 18, cy + 20), pal["gold"], dark, 2)
        draw_el(draw, (cx + 18, cy - 20, cx + 30, cy + 20), pal["gold"], dark, 2)
    elif name == "coin":
        draw_el(draw, (cx - 24, cy - 24, cx + 24, cy + 24), pal["gold_hi"], dark, 3)
        diamond(draw, cx, cy, 11, pal["paper"], dark, 2)
    elif name == "mail":
        draw_rr(draw, (cx - 27, cy - 18, cx + 27, cy + 18), 4, pal["paper_hi"], dark, 3)
        draw_line(draw, [(cx - 25, cy - 16), (cx, cy + 4), (cx + 25, cy - 16)], dark, 2)
    elif name == "chest":
        draw_rr(draw, (cx - 27, cy - 15, cx + 27, cy + 24), 5, pal["red_lo"], dark, 3)
        draw_rr(draw, (cx - 25, cy - 27, cx + 25, cy - 5), 9, pal["gold"], dark, 3)
        draw_rr(draw, (cx - 7, cy - 3, cx + 7, cy + 12), 2, pal["gold_hi"], dark, 1)


def icon_button(size, pal, symbol=None, variant="diamond"):
    w, h = size
    im = new(size)
    d = ImageDraw.Draw(im)
    cx, cy = w / 2, h / 2
    layer(im, shadow(size, (10, 10, w - 10, h - 10), alpha=70, offset=(0, 5), blur=7))
    if variant == "round":
        draw_el(d, (12, 12, w - 12, h - 12), pal["panel_lo"], pal["dark"], 3)
        draw_el(d, (20, 20, w - 20, h - 20), pal["panel_hi"], pal["gold_hi"], 2)
    elif variant == "square":
        draw_rr(d, (12, 12, w - 12, h - 12), 12, pal["panel_lo"], pal["dark"], 3)
        draw_rr(d, (20, 20, w - 20, h - 20), 8, pal["panel_hi"], pal["gold_hi"], 2)
    else:
        pts = [(cx, 8), (w - 8, cy), (cx, h - 8), (8, cy)]
        draw_poly(d, pts, pal["panel_lo"], pal["dark"], 3)
        draw_poly(d, [(cx, 18), (w - 18, cy), (cx, h - 18), (18, cy)], pal["panel_hi"], pal["gold_hi"], 2)
    if symbol:
        icon_symbol(d, symbol, cx, cy, pal)
    return down(im)


def window_asset(size, pal, style="A"):
    w, h = size
    im = carved_panel(size, (24, 24, w - 24, h - 24), pal, "paper", seed=24, heavy=style == "B")
    d = ImageDraw.Draw(im)
    title_h = 86 if style == "A" else 94
    tb = title_bar_asset((w - 112, title_h), pal)
    im.alpha_composite(tb.resize(((w - 112) * S, title_h * S), Image.Resampling.LANCZOS), (56 * S, 46 * S))
    for x in (56, w - 56):
        diamond(d, x, 46 + title_h / 2, 12, pal["gold_hi"], pal["dark"], 2)
    inner = (62, 150, w - 62, h - 62)
    draw_rr(d, inner, 8, None, pal["line"], 1.5)
    for off in (0, 16, 32):
        draw_line(d, [(inner[0] + 24, inner[1] + 40 + off), (inner[2] - 24, inner[1] + 40 + off)], pal["line_soft"], 1)
    return down(im)


def modal_asset(size, pal, style="A"):
    w, h = size
    im = carved_panel(size, (18, 18, w - 18, h - 18), pal, "paper", seed=54, heavy=style == "B")
    d = ImageDraw.Draw(im)
    draw_rr(d, (54, 76, w - 54, h - 68), 8, None, pal["line_soft"], 1.4)
    diamond(d, w / 2, 55, 13, pal["gold_hi"], pal["dark"], 2)
    return down(im)


def panel_asset(size, pal, kind="paper", style="A"):
    return down(carved_panel(size, (18, 18, size[0] - 18, size[1] - 26), pal, kind, seed=70, heavy=style == "B"))


def title_bar_asset(size, pal):
    w, h = size
    im = new(size)
    d = ImageDraw.Draw(im)
    box = (8, 8, w - 8, h - 8)
    pts = [(box[0] + 24, box[1]), (box[2] - 24, box[1]), (box[2], h / 2), (box[2] - 24, box[3]), (box[0] + 24, box[3]), (box[0], h / 2)]
    layer(im, shadow(size, box, alpha=70, offset=(0, 4), blur=5, polygon=pts))
    mask = oct_mask(size, box, cut=24)
    paste_masked(im, vertical_gradient(size, pal["panel_hi"], pal["panel_lo"], seed=77, noise=5), mask)
    draw_poly(d, pts, None, pal["dark"], 2.6)
    draw_poly(d, [(x + (4 if x < w / 2 else -4), y + (4 if y < h / 2 else -4)) for x, y in pts], None, pal["gold_hi"], 1.6)
    return down(im)


def tab_asset(size, pal, active=True):
    w, h = size
    im = new(size)
    d = ImageDraw.Draw(im)
    box = (8, 10, w - 8, h - 10)
    fill_top = pal["panel_hi"] if active else pal["paper_hi"]
    fill_bot = pal["panel_lo"] if active else pal["paper"]
    mask = oct_mask(size, box, cut=18)
    paste_masked(im, vertical_gradient(size, fill_top, fill_bot, seed=81), mask)
    draw_poly(d, [(box[0] + 20, box[1]), (box[2] - 20, box[1]), (box[2], box[1] + 18), (box[2], box[3]), (box[0], box[3]), (box[0], box[1] + 18)], None, pal["dark"], 2.2)
    draw_line(d, [(28, h - 13), (w - 28, h - 13)], pal["gold_hi"] if active else pal["line_soft"], 1.4)
    return down(im)


def list_row_asset(size, pal):
    w, h = size
    im = new(size)
    d = ImageDraw.Draw(im)
    draw_rr(d, (8, 8, w - 8, h - 8), 7, pal["paper"], pal["line"], 1.6)
    draw_line(d, [(28, h - 16), (w - 28, h - 16)], pal["line_soft"], 1)
    diamond(d, 24, h / 2, 5, pal["gold"], pal["dark"], 1)
    return down(im)


def input_asset(size, pal):
    w, h = size
    im = new(size)
    d = ImageDraw.Draw(im)
    draw_rr(d, (8, 8, w - 8, h - 8), 8, pal["paper_shadow"], pal["dark"], 2.2)
    draw_rr(d, (16, 16, w - 16, h - 16), 5, pal["paper_hi"], pal["line_soft"], 1.2)
    return down(im)


def checkbox_asset(size, pal, checked=False):
    w, h = size
    im = new(size)
    d = ImageDraw.Draw(im)
    box = (8, 8, w - 8, h - 8)
    draw_rr(d, box, 7, pal["paper_hi"], pal["dark"], 2.8)
    draw_rr(d, inset(box, 8), 4, pal["paper"], pal["gold_hi"], 1.4)
    if checked:
        draw_line(d, [(22, h / 2), (w / 2 - 4, h - 22), (w - 20, 20)], pal["green_line"], 5)
    return down(im)


def toggle_asset(size, pal, on=False):
    w, h = size
    im = new(size)
    d = ImageDraw.Draw(im)
    fill1 = pal["panel_hi"] if on else pal["disabled_hi"]
    fill2 = pal["panel_lo"] if on else pal["disabled_lo"]
    box = (8, 10, w - 8, h - 10)
    mask = Image.new("L", im.size, 0)
    md = ImageDraw.Draw(mask)
    md.rounded_rectangle(scale_box(box), radius=int(24 * S), fill=255)
    paste_masked(im, vertical_gradient(size, fill1, fill2, seed=94), mask)
    draw_rr(d, box, 24, None, pal["dark"], 2)
    r = h / 2 - 14
    cx = w - h / 2 if on else h / 2
    draw_el(d, (cx - r, h / 2 - r, cx + r, h / 2 + r), pal["gold_hi"], pal["dark"], 2)
    return down(im)


def progress_asset(size, pal, value=0.65):
    w, h = size
    im = new(size)
    d = ImageDraw.Draw(im)
    box = (10, 12, w - 10, h - 12)
    draw_rr(d, box, 16, pal["paper_shadow"], pal["dark"], 2.4)
    inner = inset(box, 8)
    draw_rr(d, inner, 11, pal["line_soft"], None, 1)
    if value > 0:
        fill = (inner[0], inner[1], inner[0] + (inner[2] - inner[0]) * value, inner[3])
        draw_rr(d, fill, 10, pal["panel_hi"], pal["green_line"], 1.2)
        draw_line(d, [(fill[0] + 12, fill[1] + 7), (fill[2] - 12, fill[1] + 7)], pal["shine"], 1.1)
    return down(im)


def scrollbar_asset(size, pal):
    w, h = size
    im = new(size)
    d = ImageDraw.Draw(im)
    draw_rr(d, (8, h / 2 - 9, w - 8, h / 2 + 9), 9, pal["paper_shadow"], pal["dark"], 1.8)
    draw_rr(d, (w * 0.28, h / 2 - 17, w * 0.64, h / 2 + 17), 15, pal["panel_hi"], pal["gold_hi"], 2)
    return down(im)


def tooltip_asset(size, pal):
    w, h = size
    im = carved_panel(size, (10, 10, w - 10, h - 24), pal, "paper", seed=111, heavy=False)
    d = ImageDraw.Draw(im)
    draw_poly(d, [(w / 2 - 16, h - 25), (w / 2 + 16, h - 25), (w / 2, h - 7)], pal["paper"], pal["dark"], 2)
    return down(im)


def banner_asset(size, pal):
    w, h = size
    im = new(size)
    d = ImageDraw.Draw(im)
    pts = [(18, 10), (w - 18, 10), (w - 8, h / 2), (w - 18, h - 10), (18, h - 10), (8, h / 2)]
    layer(im, shadow(size, (8, 10, w - 8, h - 10), alpha=70, offset=(0, 5), blur=7, polygon=pts))
    mask = oct_mask(size, (8, 10, w - 8, h - 10), cut=16)
    paste_masked(im, vertical_gradient(size, pal["red_hi"], pal["red_lo"], seed=120, noise=6), mask)
    draw_poly(d, pts, None, pal["dark"], 2.5)
    draw_line(d, [(42, 26), (w - 42, 26)], pal["gold_hi"], 1.4)
    return down(im)


def divider_asset(size, pal):
    w, h = size
    im = new(size)
    d = ImageDraw.Draw(im)
    y = h / 2
    draw_line(d, [(28, y), (w / 2 - 28, y)], pal["line_soft"], 1.4)
    draw_line(d, [(w / 2 + 28, y), (w - 28, y)], pal["line_soft"], 1.4)
    diamond(d, w / 2, y, 12, pal["gold_hi"], pal["dark"], 2)
    diamond(d, w / 2, y, 5, pal["panel_hi"], pal["dark"], 1)
    return down(im)


def status_dot(size, pal, color):
    color_map = {
        "blue": (rgba("#67a8ff"), rgba("#163b72")),
        "green": (rgba("#66d57e"), rgba("#184c2b")),
        "red": (rgba("#f05d53"), rgba("#681a18")),
        "gold": (rgba("#ffd46b"), rgba("#835719")),
        "gray": (rgba("#c9c4b8"), rgba("#5d5a52")),
    }
    w, h = size
    im = new(size)
    d = ImageDraw.Draw(im)
    top, bot = color_map[color]
    draw_el(d, (10, 10, w - 10, h - 10), pal["gold_hi"], pal["dark"], 2.2)
    mask = Image.new("L", im.size, 0)
    md = ImageDraw.Draw(mask)
    md.ellipse(scale_box((18, 18, w - 18, h - 18)), fill=255)
    paste_masked(im, vertical_gradient(size, top, bot, seed=130, noise=5), mask)
    draw_el(d, (25, 21, 38, 34), rgba("#ffffff", 110))
    return down(im)


def panel_bg_asset(size, pal, variant="mountains"):
    w, h = size
    im = new(size)
    d = ImageDraw.Draw(im)
    if variant == "dark_dragon":
        paste_masked(im, vertical_gradient(size, pal["panel_hi"], pal["panel_lo"], seed=141, noise=7), Image.new("L", (w * S, h * S), 255))
        for r in range(38, 172, 23):
            draw_el(d, (w / 2 - r * 1.45, h / 2 - r * 0.75, w / 2 + r * 1.45, h / 2 + r * 0.75), None, rgba("#d0b36a", 32), 4)
        draw_line(d, [(80, h - 70), (160, h - 115), (250, h - 96), (350, h - 150), (w - 80, h - 88)], rgba("#d0b36a", 48), 5)
    elif variant == "plain":
        layer(im, paper_texture(size, pal["paper"], pal["paper_hi"], seed=151, strength=18))
    else:
        layer(im, paper_texture(size, pal["paper"], pal["paper_hi"], seed=152, strength=20))
        for i, col in enumerate([rgba("#7f8c83", 56), rgba("#53645e", 46), rgba("#9b8c73", 42)]):
            base = h - 40 - i * 35
            pts = [(0, h), (0, base)]
            for x in range(0, w + 60, 60):
                pts.append((x, base - random.Random(i * 100 + x).randint(8, 60)))
            pts += [(w, h)]
            draw_poly(d, pts, col)
    draw_rr(d, (7, 7, w - 7, h - 7), 7, None, pal["line"], 1.2)
    return down(im)


PALE = {
    "paper": rgba("#dad2bf"),
    "paper_hi": rgba("#f1ead9"),
    "paper_shadow": rgba("#bfb39b"),
    "panel_hi": rgba("#315348"),
    "panel_lo": rgba("#172b28"),
    "dark": rgba("#3a332a"),
    "line": rgba("#87795d"),
    "line_soft": rgba("#a99c84", 150),
    "gold": rgba("#b89655"),
    "gold_hi": rgba("#e3c57e"),
    "shine": rgba("#fff2b5", 105),
    "green_line": rgba("#74b58d"),
    "red_hi": rgba("#8f3c32"),
    "red_lo": rgba("#4a1d1b"),
    "red_line": rgba("#dda470"),
    "disabled_hi": rgba("#9c978d"),
    "disabled_lo": rgba("#69655f"),
    "disabled_line": rgba("#aaa394"),
    "icon": rgba("#f3e4b5"),
}

BRONZE = {
    "paper": rgba("#b8a78a"),
    "paper_hi": rgba("#ded0b0"),
    "paper_shadow": rgba("#8d7d66"),
    "panel_hi": rgba("#365549"),
    "panel_lo": rgba("#15231f"),
    "dark": rgba("#221d18"),
    "line": rgba("#6e5840"),
    "line_soft": rgba("#9f8561", 145),
    "gold": rgba("#ae7e3d"),
    "gold_hi": rgba("#dfb76b"),
    "shine": rgba("#fff1aa", 90),
    "green_line": rgba("#4db189"),
    "red_hi": rgba("#8a2f24"),
    "red_lo": rgba("#33120f"),
    "red_line": rgba("#d7a062"),
    "disabled_hi": rgba("#756b5f"),
    "disabled_lo": rgba("#464039"),
    "disabled_line": rgba("#8f8373"),
    "icon": rgba("#f2d792"),
}


def save_asset(path: Path, image: Image.Image):
    path.parent.mkdir(parents=True, exist_ok=True)
    if image.mode != "RGBA":
        image = image.convert("RGBA")
    alpha = image.getchannel("A").point(lambda p: 0 if p < 36 else p)
    image = image.copy()
    image.putalpha(alpha)
    image.save(path, optimize=True)


def build_set(key: str, pal: dict, style: str):
    folder = OUT / key
    trans = folder / "transparent"
    trans.mkdir(parents=True, exist_ok=True)
    records = []

    def put(name, im, nine=None, note=""):
        path = trans / f"{name}.png"
        save_asset(path, im)
        records.append(
            {
                "file": f"transparent/{name}.png",
                "size": [im.width, im.height],
                "nine_slice": nine,
                "note": note,
            }
        )

    for mode in ["primary", "secondary", "danger", "disabled"]:
        put(f"button_{mode}", button_asset((400, 104), pal, mode), [54, 30, 54, 30])

    icon_names = ["blank", "close", "plus", "minus", "arrow", "gear", "sword", "flag", "helmet", "scroll", "coin", "mail", "chest"]
    for name in icon_names:
        symbol = None if name == "blank" else name
        put(f"icon_button_{name}", icon_button((104, 104), pal, symbol), None)

    put("window_frame_large", window_asset((840, 560), pal, style), [80, 150, 80, 80])
    put("modal_popup", modal_asset((620, 400), pal, style), [64, 80, 64, 64])
    put("panel_plain", panel_asset((540, 320), pal, "paper", style), [48, 48, 48, 48])
    put("panel_dark", panel_asset((540, 320), pal, "dark", style), [48, 48, 48, 48])
    put("title_bar", title_bar_asset((560, 86), pal), [50, 20, 50, 20])
    put("tab_active", tab_asset((180, 78), pal, True), [36, 24, 36, 16])
    put("tab_inactive", tab_asset((180, 78), pal, False), [36, 24, 36, 16])
    put("list_row", list_row_asset((520, 72), pal), [36, 20, 36, 20])
    put("input_box", input_asset((440, 82), pal), [34, 24, 34, 24])
    put("checkbox_empty", checkbox_asset((72, 72), pal, False), None)
    put("checkbox_checked", checkbox_asset((72, 72), pal, True), None)
    put("toggle_off", toggle_asset((144, 70), pal, False), [38, 22, 38, 22])
    put("toggle_on", toggle_asset((144, 70), pal, True), [38, 22, 38, 22])
    put("progress_bar_65", progress_asset((460, 64), pal, 0.65), [42, 20, 42, 20])
    put("progress_bar_empty", progress_asset((460, 64), pal, 0), [42, 20, 42, 20])
    put("scrollbar_horizontal", scrollbar_asset((420, 64), pal), [40, 18, 40, 18])
    put("tooltip_panel", tooltip_asset((360, 180), pal), [42, 42, 42, 58])
    put("notification_banner", banner_asset((520, 92), pal), [54, 24, 54, 24])
    put("close_button_diamond", icon_button((92, 92), pal, "close", "diamond"), None)
    put("close_button_square", icon_button((92, 92), pal, "close", "square"), None)
    put("close_button_round", icon_button((92, 92), pal, "close", "round"), None)
    put("divider_ornament", divider_asset((520, 58), pal), [160, 20, 160, 20])
    for color in ["blue", "green", "red", "gold", "gray"]:
        put(f"status_dot_{color}", status_dot((58, 58), pal, color), None)
    for variant in ["mountains", "dark_dragon", "plain"]:
        put(f"panel_bg_{variant}", panel_bg_asset((520, 300), pal, variant), [32, 32, 32, 32])

    manifest = {
        "set": key,
        "style": "A clean strategy" if style == "A" else "B bronze command",
        "production_notes": [
            "All controls are redrawn clean assets, not cropped from text-bearing concept images.",
            "PNG files use transparent padding around outer edges.",
            "No baked UI text is included in individual control assets.",
            "Nine-slice values are suggestions: [left, top, right, bottom].",
        ],
        "assets": records,
    }
    (folder / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    make_preview(folder / f"preview_{key}_production_clean.png", records, trans, key)
    return records


def make_preview(path: Path, records, trans: Path, title: str):
    cols = 5
    tile_w, tile_h = 300, 214
    gap_x, gap_y = 20, 24
    rows = math.ceil(len(records) / cols)
    bg_w = 56 * 2 + cols * tile_w + (cols - 1) * gap_x
    bg_h = 90 + rows * tile_h + (rows - 1) * gap_y + 56
    bg = Image.new("RGBA", (bg_w, bg_h), rgba("#ebe4d5"))
    d = ImageDraw.Draw(bg)
    text(d, (bg_w / 2, 48), title, rgba("#44392d"), 24)
    x, y = 56, 90
    row_h = 0
    for i, rec in enumerate(records):
        im = Image.open(trans / Path(rec["file"]).name).convert("RGBA")
        scale = min(1.0, 260 / im.width, 160 / im.height)
        thumb = im.resize((int(im.width * scale), int(im.height * scale)), Image.Resampling.LANCZOS)
        tile = Image.new("RGBA", (tile_w, tile_h), rgba("#f6f1e7"))
        td = ImageDraw.Draw(tile)
        td.rounded_rectangle((0, 0, tile_w - 1, tile_h - 1), radius=10, fill=rgba("#f6f1e7"), outline=rgba("#b8aa90"))
        tile.alpha_composite(thumb, ((tile_w - thumb.width) // 2, 18 + (150 - thumb.height) // 2))
        label = Path(rec["file"]).stem[:28]
        try:
            font = ImageFont.truetype("arial.ttf", 16)
        except OSError:
            font = ImageFont.load_default()
        td.text((tile_w / 2, 188), label, fill=rgba("#5b5043"), font=font, anchor="mm")
        bg.alpha_composite(tile, (x, y))
        x += tile_w + gap_x
        row_h = max(row_h, 214)
        if x + tile_w > bg.width - 56:
            x = 56
            y += row_h + gap_y
            row_h = 0
    bg.convert("RGB").save(path, quality=94)


def combined_preview():
    a = Image.open(OUT / "A_clean_strategy" / "preview_A_clean_strategy_production_clean.png").convert("RGB")
    b = Image.open(OUT / "B_bronze_command" / "preview_B_bronze_command_production_clean.png").convert("RGB")
    scale = min(0.34, 900 / a.width)
    aw = int(a.width * scale)
    ah = int(a.height * scale)
    bw = int(b.width * scale)
    bh = int(b.height * scale)
    canvas = Image.new("RGB", (max(aw, bw) * 2 + 72, max(ah, bh) + 64), rgba("#e9e0ce")[:3])
    canvas.paste(a.resize((aw, ah), Image.Resampling.LANCZOS), (24, 32))
    canvas.paste(b.resize((bw, bh), Image.Resampling.LANCZOS), (aw + 48, 32))
    canvas.save(OUT / "preview_production_clean_A_B.png", quality=94)


def write_root_docs(a_records, b_records):
    readme = """# 三国基础 UI 控件拆分 v07

这一版是重新绘制的干净控件资源，不再从带文字的氛围图里硬裁剪，也没有用色块覆盖原图文字。

## 使用建议

- `A_clean_strategy/transparent`：偏浅色策略界面，适合常规窗口、弹窗、列表、按钮。
- `B_bronze_command/transparent`：偏青铜军令质感，适合战斗、确认、奖励、强化等更重的界面。
- 单个 PNG 均保留透明安全边，边缘装饰没有贴边裁损。
- 控件本体不包含写死文本；文字建议由程序层叠加。
- `manifest.json` 中的 `nine_slice` 是九宫格缩放参考值，单位为像素。

## 预览

- `preview_production_clean_A_B.png`：A/B 两套总览。
- 每套目录内也有各自的 `preview_*_production_clean.png`。
"""
    (OUT / "README.md").write_text(readme, encoding="utf-8")
    root_manifest = {
        "version": "v07-production-clean",
        "source_concepts": [
            "ui_kit_A_clean_strategy.png",
            "ui_kit_B_bronze_command.png",
        ],
        "sets": {
            "A_clean_strategy": {
                "asset_count": len(a_records),
                "path": "A_clean_strategy/transparent",
            },
            "B_bronze_command": {
                "asset_count": len(b_records),
                "path": "B_bronze_command/transparent",
            },
        },
        "notes": [
            "Redrawn clean controls.",
            "No baked text in individual PNG controls.",
            "Transparent outer padding preserved.",
            "Do not use v01-v04 extracted-control folders for production.",
        ],
    }
    (OUT / "manifest.json").write_text(json.dumps(root_manifest, ensure_ascii=False, indent=2), encoding="utf-8")


def alpha_report():
    report = []
    for png in OUT.glob("*/*/*.png"):
        im = Image.open(png).convert("RGBA")
        bbox = im.getchannel("A").getbbox()
        if not bbox:
            report.append({"file": str(png.relative_to(OUT)), "error": "empty alpha"})
            continue
        left, top, right, bottom = bbox
        margins = [left, top, im.width - right, im.height - bottom]
        report.append(
            {
                "file": str(png.relative_to(OUT)).replace("\\", "/"),
                "size": [im.width, im.height],
                "alpha_margins": margins,
            }
        )
    (OUT / "alpha_margins_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")


def main():
    assert_safe_path(OUT)
    if OUT.exists():
        def retry_writable(func, path, exc_info):
            try:
                os.chmod(path, stat.S_IWRITE)
                func(path)
            except Exception as err:
                raise err

        shutil.rmtree(OUT, onexc=retry_writable)
    OUT.mkdir(parents=True)
    a_records = build_set("A_clean_strategy", PALE, "A")
    b_records = build_set("B_bronze_command", BRONZE, "B")
    combined_preview()
    write_root_docs(a_records, b_records)
    alpha_report()
    print(json.dumps({"output": str(OUT), "A": len(a_records), "B": len(b_records)}, ensure_ascii=False))


if __name__ == "__main__":
    main()

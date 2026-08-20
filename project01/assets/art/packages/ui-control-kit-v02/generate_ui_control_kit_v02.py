from __future__ import annotations

import json
import math
import random
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont


ROOT = Path(__file__).resolve().parent
random.seed(20260820)


@dataclass(frozen=True)
class Style:
    key: str
    name: str
    usage: str
    silhouette: str
    bg: tuple[int, int, int, int]
    bg2: tuple[int, int, int, int]
    stroke: tuple[int, int, int, int]
    stroke2: tuple[int, int, int, int]
    accent: tuple[int, int, int, int]
    accent2: tuple[int, int, int, int]
    shadow: tuple[int, int, int, int]


STYLES = [
    Style(
        key="01_porcelain_map",
        name="清瓷地图框",
        usage="常规窗口、地图、阵容、关卡基础界面",
        silhouette="porcelain",
        bg=(246, 241, 229, 232),
        bg2=(221, 213, 196, 226),
        stroke=(91, 76, 52, 150),
        stroke2=(255, 253, 246, 118),
        accent=(181, 137, 61, 225),
        accent2=(75, 128, 112, 215),
        shadow=(70, 54, 32, 68),
    ),
    Style(
        key="02_command_seal",
        name="朱印令牌框",
        usage="军令市场、奖励、购买确认、Set 融合",
        silhouette="seal",
        bg=(241, 222, 190, 232),
        bg2=(216, 181, 135, 226),
        stroke=(118, 48, 38, 185),
        stroke2=(255, 237, 203, 115),
        accent=(177, 58, 45, 236),
        accent2=(184, 136, 61, 226),
        shadow=(91, 39, 23, 85),
    ),
    Style(
        key="03_ink_brush",
        name="墨刷浮层框",
        usage="技能释放、短提示、战斗高压浮层",
        silhouette="brush",
        bg=(28, 33, 33, 224),
        bg2=(13, 17, 18, 218),
        stroke=(214, 198, 168, 118),
        stroke2=(95, 121, 120, 78),
        accent=(196, 67, 51, 232),
        accent2=(83, 134, 126, 220),
        shadow=(0, 0, 0, 132),
    ),
    Style(
        key="04_bronze_plate",
        name="玄铁铜铆框",
        usage="装备、Boss、危险确认、精英战斗面板",
        silhouette="armor",
        bg=(67, 58, 48, 235),
        bg2=(35, 32, 29, 232),
        stroke=(204, 136, 61, 180),
        stroke2=(236, 205, 146, 84),
        accent=(185, 82, 43, 232),
        accent2=(191, 150, 83, 230),
        shadow=(0, 0, 0, 140),
    ),
    Style(
        key="05_dossier_paper",
        name="军务档案夹",
        usage="图鉴、规则说明、战报、单卡详情",
        silhouette="dossier",
        bg=(235, 232, 218, 232),
        bg2=(202, 198, 183, 224),
        stroke=(69, 70, 65, 162),
        stroke2=(255, 255, 248, 96),
        accent=(88, 89, 82, 225),
        accent2=(169, 58, 48, 210),
        shadow=(52, 48, 40, 66),
    ),
    Style(
        key="06_jade_bi",
        name="青玉璧环框",
        usage="成长、羁绊、增益、可用状态",
        silhouette="jade",
        bg=(219, 236, 226, 226),
        bg2=(166, 202, 188, 222),
        stroke=(45, 109, 94, 170),
        stroke2=(245, 255, 249, 104),
        accent=(47, 135, 112, 230),
        accent2=(186, 141, 65, 220),
        shadow=(31, 70, 58, 72),
    ),
]


def mix(a, b, t):
    return tuple(round(a[i] + (b[i] - a[i]) * t) for i in range(len(a)))


def gradient(size, top, bottom):
    w, h = size
    img = Image.new("RGBA", size)
    px = img.load()
    for y in range(h):
        t = y / max(1, h - 1)
        c = mix(top, bottom, t)
        for x in range(w):
            px[x, y] = c
    return img


def polygon_for(style: Style, size: tuple[int, int], kind: str) -> list[tuple[int, int]]:
    w, h = size
    if style.silhouette == "seal":
        s = max(12, min(w, h) // 10)
        return [(s, 0), (w - s, 0), (w, s), (w, h - s), (w - s, h), (s, h), (0, h - s), (0, s)]
    if style.silhouette in {"armor", "brush"}:
        s = max(18, min(w, h) // 7)
        return [(s, 0), (w - s, 0), (w, s), (w, h - s), (w - s, h), (s, h), (0, h - s), (0, s)]
    if style.silhouette == "dossier":
        tab = min(120, w // 4)
        return [(0, 18), (tab, 18), (tab + 18, 0), (w, 0), (w, h), (0, h)]
    if style.silhouette == "jade":
        s = max(34, min(w, h) // 4)
        return [(s, 0), (w - s, 0), (w, h // 2), (w - s, h), (s, h), (0, h // 2)]
    return [(0, 0), (w, 0), (w, h), (0, h)]


def alpha_mask(style: Style, size: tuple[int, int], radius: int, kind: str) -> Image.Image:
    w, h = size
    mask = Image.new("L", size, 0)
    d = ImageDraw.Draw(mask)
    if style.silhouette == "porcelain":
        d.rounded_rectangle((0, 0, w - 1, h - 1), radius=radius, fill=255)
    elif style.silhouette == "brush":
        pts = polygon_for(style, size, kind)
        jittered = []
        for x, y in pts:
            jittered.append((x + random.randint(-4, 4), y + random.randint(-3, 3)))
        d.polygon(jittered, fill=255)
        for _ in range(12):
            x = random.randint(0, w - 1)
            y = random.choice([random.randint(0, 12), random.randint(h - 13, h - 1)])
            d.ellipse((x - 10, y - 4, x + 26, y + 4), fill=255)
        mask = mask.filter(ImageFilter.GaussianBlur(0.35))
    else:
        d.polygon(polygon_for(style, size, kind), fill=255)
    return mask


def apply_mask(img: Image.Image, mask: Image.Image) -> Image.Image:
    out = img.copy()
    out.putalpha(Image.composite(out.getchannel("A"), Image.new("L", img.size, 0), mask))
    return out


def shadowed(body: Image.Image, color) -> Image.Image:
    out = Image.new("RGBA", body.size, (0, 0, 0, 0))
    alpha = body.getchannel("A").filter(ImageFilter.GaussianBlur(12))
    sh = Image.new("RGBA", body.size, color)
    sh.putalpha(alpha.point(lambda p: int(p * color[3] / 255)))
    out.alpha_composite(sh, (0, 5))
    out.alpha_composite(body)
    return out


def draw_border(d: ImageDraw.ImageDraw, style: Style, size, radius, kind):
    w, h = size
    if style.silhouette == "porcelain":
        d.rounded_rectangle((1, 1, w - 2, h - 2), radius=radius, outline=style.stroke, width=3)
        d.rounded_rectangle((12, 12, w - 13, h - 13), radius=max(1, radius - 8), outline=style.stroke2, width=1)
    else:
        pts = polygon_for(style, size, kind)
        d.line(pts + [pts[0]], fill=style.stroke, width=3)
        inset = 12
        inner = polygon_for(style, (w - inset * 2, h - inset * 2), kind)
        inner = [(x + inset, y + inset) for x, y in inner]
        d.line(inner + [inner[0]], fill=style.stroke2, width=1)


def draw_corner_language(d: ImageDraw.ImageDraw, style: Style, size, kind):
    w, h = size
    m = 22
    if style.silhouette == "seal":
        for x, y, sx, sy in [(m, m, 1, 1), (w - m, m, -1, 1), (m, h - m, 1, -1), (w - m, h - m, -1, -1)]:
            d.rectangle((x - 5, y - 5, x + 5, y + 5), fill=style.accent)
            d.line((x, y, x + sx * 42, y), fill=style.accent, width=2)
            d.line((x, y, x, y + sy * 42), fill=style.accent, width=2)
    elif style.silhouette == "armor":
        for x, y, sx, sy in [(22, 22, 1, 1), (w - 22, 22, -1, 1), (22, h - 22, 1, -1), (w - 22, h - 22, -1, -1)]:
            d.line((x, y + sy * 34, x + sx * 34, y), fill=style.accent2, width=3)
            d.ellipse((x + sx * 22 - 5, y + sy * 22 - 5, x + sx * 22 + 5, y + sy * 22 + 5), fill=style.accent)
    elif style.silhouette == "dossier":
        for x, y in [(18, h - 18), (w - 18, 18), (w - 18, h - 18)]:
            d.rectangle((x - 3, y - 3, x + 3, y + 3), fill=style.accent2)
        d.line((18, 20, 108, 20), fill=style.accent, width=2)
    elif style.silhouette == "jade":
        for x, y in [(24, 24), (w - 24, 24), (24, h - 24), (w - 24, h - 24)]:
            d.ellipse((x - 7, y - 7, x + 7, y + 7), fill=style.accent2)
            d.ellipse((x - 3, y - 3, x + 3, y + 3), fill=style.bg)
    elif style.silhouette == "brush":
        d.line((26, 22, w - 26, 22), fill=(*style.accent[:3], 120), width=2)
        d.line((34, h - 24, w // 2, h - 24), fill=(*style.accent2[:3], 120), width=2)
    else:
        for x, y, sx, sy in [(20, 20, 1, 1), (w - 20, 20, -1, 1), (20, h - 20, 1, -1), (w - 20, h - 20, -1, -1)]:
            d.line((x, y, x + sx * 38, y), fill=style.accent, width=2)
            d.line((x, y, x, y + sy * 38), fill=style.accent, width=2)


def add_texture(d: ImageDraw.ImageDraw, style: Style, size, kind):
    w, h = size
    if style.silhouette in {"porcelain", "seal", "dossier"}:
        for y in range(32, h - 28, 28):
            d.line((34, y, w - 34, y), fill=(*style.stroke[:3], 18), width=1)
    if style.silhouette == "route":
        pass
    if style.silhouette == "armor":
        for x in range(70, w, 82):
            d.line((x, 20, x, h - 20), fill=(*style.stroke2[:3], 22), width=1)
    if style.silhouette == "jade":
        for r in range(0, min(w, h), 34):
            d.arc((w // 2 - r, h // 2 - r, w // 2 + r, h // 2 + r), 205, 335, fill=(*style.accent[:3], 22), width=1)


def panel(style: Style, size, kind):
    radius = 18 if kind == "window" else 12
    base = gradient(size, style.bg, style.bg2)
    mask = alpha_mask(style, size, radius, kind)
    body = apply_mask(base, mask)
    img = shadowed(body, style.shadow)
    d = ImageDraw.Draw(img)
    draw_border(d, style, size, radius, kind)
    draw_corner_language(d, style, size, kind)
    add_texture(d, style, size, kind)
    w, h = size
    if kind == "base":
        d.line((54, h // 2, w - 54, h // 2), fill=(*style.stroke[:3], 60), width=1)
    if kind == "headbar":
        if style.silhouette == "dossier":
            d.rectangle((0, 0, min(130, w // 4), h), fill=(*style.accent[:3], 32))
        elif style.silhouette == "brush":
            d.line((42, h - 18, w - 42, h - 18), fill=style.accent, width=4)
        else:
            d.line((58, h - 18, w - 58, h - 18), fill=style.accent, width=2)
            d.ellipse((w // 2 - 5, h - 23, w // 2 + 5, h - 13), fill=style.accent2)
    return img


def disabled(img: Image.Image) -> Image.Image:
    gray = img.convert("LA").convert("RGBA")
    alpha = img.getchannel("A").point(lambda p: int(p * 0.66))
    overlay = Image.new("RGBA", img.size, (120, 120, 116, 120))
    out = Image.alpha_composite(gray, overlay)
    out.putalpha(alpha)
    return out


def button_rect(style: Style, state="normal", size=(340, 96)):
    if style.silhouette in {"armor", "brush", "jade", "seal"}:
        img = panel(style, size, "button")
    elif style.silhouette == "dossier":
        img = panel(style, size, "button")
    else:
        img = panel(style, size, "button")
    d = ImageDraw.Draw(img)
    w, h = size
    if style.silhouette == "seal":
        d.rectangle((18, 18, w - 18, h - 18), outline=(*style.accent[:3], 120), width=2)
    elif style.silhouette == "armor":
        d.line((20, 18, 52, 50), fill=style.stroke2, width=2)
        d.line((w - 20, 18, w - 52, 50), fill=style.stroke2, width=2)
    elif style.silhouette == "jade":
        d.arc((24, 16, h - 16, h + 44), 200, 295, fill=style.stroke2, width=2)
        d.arc((w - h - 44, 16, w - 24, h + 44), 245, 340, fill=style.stroke2, width=2)
    elif style.silhouette == "brush":
        d.line((28, 26, w - 40, h - 26), fill=(*style.accent[:3], 60), width=5)
    else:
        d.line((40, h - 22, w - 40, h - 22), fill=style.accent, width=2)
    return disabled(img) if state == "disabled" else img


def button_tab(style: Style, state="normal", size=(260, 84)):
    # Tabs use stronger silhouettes than normal panels.
    img = Image.new("RGBA", size, (0, 0, 0, 0))
    w, h = size
    d = ImageDraw.Draw(img)
    if style.silhouette == "dossier":
        pts = [(0, h), (0, 18), (44, 18), (58, 4), (w, 4), (w - 18, h)]
    elif style.silhouette == "jade":
        pts = [(36, 4), (w - 36, 4), (w, h // 2), (w - 36, h - 4), (36, h - 4), (0, h // 2)]
    elif style.silhouette in {"armor", "brush"}:
        pts = [(24, 4), (w - 24, 4), (w - 4, h // 2), (w - 24, h - 4), (24, h - 4), (4, h // 2)]
    elif style.silhouette == "seal":
        pts = [(18, 2), (w - 18, 2), (w, 20), (w - 14, h - 4), (14, h - 4), (0, 20)]
    else:
        pts = [(16, 4), (w - 16, 4), (w - 4, h // 2), (w - 20, h - 6), (20, h - 6), (4, h // 2)]
    fill = gradient(size, style.bg, style.bg2)
    mask = Image.new("L", size, 0)
    ImageDraw.Draw(mask).polygon(pts, fill=255)
    fill.putalpha(mask)
    img.alpha_composite(fill)
    d.line(pts + [pts[0]], fill=style.stroke, width=2)
    d.line((48, h - 20, w - 48, h - 20), fill=style.accent, width=2)
    return disabled(img) if state == "disabled" else img


def button_circle(style: Style, state="normal", size=(132, 132)):
    w, h = size
    img = Image.new("RGBA", size, (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    if style.silhouette == "seal":
        pts = [(w // 2, 4), (w - 18, 18), (w - 4, h // 2), (w - 18, h - 18), (w // 2, h - 4), (18, h - 18), (4, h // 2), (18, 18)]
        d.polygon(pts, fill=style.bg2)
        d.line(pts + [pts[0]], fill=style.stroke, width=3)
    elif style.silhouette == "armor":
        pts = [(32, 4), (w - 32, 4), (w - 4, 32), (w - 4, h - 32), (w - 32, h - 4), (32, h - 4), (4, h - 32), (4, 32)]
        d.polygon(pts, fill=style.bg2)
        d.line(pts + [pts[0]], fill=style.stroke, width=3)
    else:
        d.ellipse((6, 6, w - 7, h - 7), fill=style.bg2, outline=style.stroke, width=3)
    d.ellipse((24, 24, w - 25, h - 25), outline=style.stroke2, width=2)
    d.ellipse((44, 44, w - 45, h - 45), fill=(*style.accent[:3], 58), outline=style.accent, width=2)
    d.line((w // 2, 24, w // 2, 42), fill=style.accent, width=2)
    d.line((w // 2, h - 24, w // 2, h - 42), fill=style.accent, width=2)
    d.line((24, h // 2, 42, h // 2), fill=style.accent, width=2)
    d.line((w - 24, h // 2, w - 42, h // 2), fill=style.accent, width=2)
    return disabled(img) if state == "disabled" else img


def save(img, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path)
    return {"path": path.relative_to(ROOT).as_posix(), "size": list(img.size)}


def nine_resize(img: Image.Image, target, inset):
    l, t, r, b = inset["left"], inset["top"], inset["right"], inset["bottom"]
    w, h = img.size
    tw, th = target
    out = Image.new("RGBA", target, (0, 0, 0, 0))
    sx = [0, l, w - r, w]
    sy = [0, t, h - b, h]
    dx = [0, l, tw - r, tw]
    dy = [0, t, th - b, th]
    for yi in range(3):
        for xi in range(3):
            part = img.crop((sx[xi], sy[yi], sx[xi + 1], sy[yi + 1]))
            dw, dh = dx[xi + 1] - dx[xi], dy[yi + 1] - dy[yi]
            if part.size != (dw, dh):
                part = part.resize((dw, dh), Image.Resampling.LANCZOS)
            out.alpha_composite(part, (dx[xi], dy[yi]))
    return out


def checker_rgba(img):
    bg = Image.new("RGBA", img.size, (245, 242, 234, 255))
    d = ImageDraw.Draw(bg)
    for y in range(0, img.height, 16):
        for x in range(0, img.width, 16):
            if (x // 16 + y // 16) % 2:
                d.rectangle((x, y, x + 15, y + 15), fill=(218, 211, 197, 255))
    bg.alpha_composite(img)
    return bg


def contact_sheet(records):
    cols = 3
    cell = (380, 224)
    rows = math.ceil(len(records) / cols)
    sheet = Image.new("RGB", (cols * cell[0], rows * cell[1]), (231, 224, 211))
    d = ImageDraw.Draw(sheet)
    font = ImageFont.load_default()
    for i, rec in enumerate(records):
        x, y = (i % cols) * cell[0], (i // cols) * cell[1]
        d.rectangle((x, y, x + cell[0] - 1, y + cell[1] - 1), outline=(181, 168, 143))
        img = Image.open(ROOT / rec["path"]).convert("RGBA")
        scale = min((cell[0] - 42) / img.width, (cell[1] - 58) / img.height, 1)
        pv = img.resize((int(img.width * scale), int(img.height * scale)), Image.Resampling.LANCZOS)
        pv = checker_rgba(pv)
        sheet.paste(pv.convert("RGB"), (x + (cell[0] - pv.width) // 2, y + 34 + (cell[1] - 64 - pv.height) // 2))
        d.text((x + 12, y + 10), rec["label"], fill=(32, 30, 26), font=font)
    sheet.save(ROOT / "preview_contact_sheet.png")


def stretch_sheet(manifest):
    rows = []
    for set_key, set_data in manifest["sets"].items():
        for asset_key, target in [
            ("window_panel", (940, 350)),
            ("baseplate_panel", (900, 150)),
            ("headbar_panel", (940, 86)),
            ("button_rect_normal", (540, 96)),
            ("button_tab_normal", (440, 84)),
        ]:
            rec = set_data["assets"][asset_key]
            img = Image.open(ROOT / rec["path"]).convert("RGBA")
            rows.append((f"{set_key}/{asset_key}", nine_resize(img, target, rec["nine_slice"])))
    row_h = 390
    sheet = Image.new("RGB", (1100, row_h * len(rows)), (231, 224, 211))
    d = ImageDraw.Draw(sheet)
    font = ImageFont.load_default()
    for i, (label, img) in enumerate(rows):
        y = i * row_h
        d.rectangle((0, y, 1099, y + row_h - 1), outline=(181, 168, 143))
        d.text((12, y + 12), label, fill=(32, 30, 26), font=font)
        pv = checker_rgba(img)
        sheet.paste(pv.convert("RGB"), (130, y + (row_h - pv.height) // 2))
    sheet.save(ROOT / "preview_9slice_stretch_test.png")


def main():
    manifest = {
        "name": "三国斗阵 UI 控件资源包 v02",
        "status": "appearance-variant draft controls; different silhouettes and ornament systems; pending art review",
        "nine_slice_note": "Insets are pixels from left/top/right/bottom. Decorations are kept in fixed corners/edges where possible.",
        "sets": {},
    }
    records = []
    for style in STYLES:
        out_dir = ROOT / style.key
        assets = {}
        items = [
            ("window_panel", panel(style, (720, 460), "window"), {"left": 96, "top": 92, "right": 96, "bottom": 92}),
            ("baseplate_panel", panel(style, (660, 190), "base"), {"left": 96, "top": 64, "right": 96, "bottom": 64}),
            ("headbar_panel", panel(style, (740, 104), "headbar"), {"left": 124, "top": 36, "right": 124, "bottom": 36}),
        ]
        for name, img, nine in items:
            rec = save(img, out_dir / f"{name}.png")
            assets[name] = {**rec, "scale_mode": "nine_slice", "nine_slice": nine}
            records.append({"path": rec["path"], "label": f"{style.key}/{name}"})

        button_items = [
            ("button_rect", button_rect, {"left": 58, "top": 30, "right": 58, "bottom": 30}, "nine_slice"),
            ("button_circle", button_circle, None, "fixed_uniform"),
            ("button_tab", button_tab, {"left": 62, "top": 28, "right": 62, "bottom": 28}, "nine_slice"),
        ]
        for base, fn, nine, scale_mode in button_items:
            for state in ["normal", "disabled"]:
                img = fn(style, state=state)
                rec = save(img, out_dir / f"{base}_{state}.png")
                item = {**rec, "state": state, "scale_mode": scale_mode}
                if nine:
                    item["nine_slice"] = nine
                assets[f"{base}_{state}"] = item
                records.append({"path": rec["path"], "label": f"{style.key}/{base}_{state}"})

        manifest["sets"][style.key] = {
            "display_name": style.name,
            "usage_note": style.usage,
            "silhouette": style.silhouette,
            "assets": assets,
        }

    (ROOT / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    contact_sheet(records)
    stretch_sheet(manifest)


if __name__ == "__main__":
    main()

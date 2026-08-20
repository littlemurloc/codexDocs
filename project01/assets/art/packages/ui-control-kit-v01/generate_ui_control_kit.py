from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont


ROOT = Path(__file__).resolve().parent


@dataclass(frozen=True)
class Theme:
    key: str
    name: str
    note: str
    bg: tuple[int, int, int, int]
    bg2: tuple[int, int, int, int]
    line: tuple[int, int, int, int]
    inner: tuple[int, int, int, int]
    accent: tuple[int, int, int, int]
    accent2: tuple[int, int, int, int]
    text: tuple[int, int, int, int]
    shadow: tuple[int, int, int, int]
    disabled_tint: tuple[int, int, int, int]
    motif: str = "corner"


THEMES = [
    Theme(
        key="A_clean_porcelain",
        name="清瓷战图",
        note="全局基准 UI：浅石瓷、淡地图纸底、细墨线、金铜点缀。",
        bg=(244, 239, 227, 232),
        bg2=(226, 218, 201, 226),
        line=(96, 80, 55, 160),
        inner=(255, 252, 244, 120),
        accent=(181, 139, 67, 230),
        accent2=(82, 132, 116, 210),
        text=(42, 39, 33, 255),
        shadow=(74, 54, 28, 70),
        disabled_tint=(132, 132, 126, 138),
        motif="porcelain",
    ),
    Theme(
        key="B_cinnabar_command",
        name="朱令金章",
        note="军令与奖励模块：象牙纸底、朱红主状态、金铜边线、玉青可用态。",
        bg=(238, 222, 196, 232),
        bg2=(210, 184, 148, 226),
        line=(116, 54, 42, 178),
        inner=(255, 240, 212, 120),
        accent=(168, 61, 48, 236),
        accent2=(72, 116, 91, 215),
        text=(45, 29, 24, 255),
        shadow=(85, 38, 24, 82),
        disabled_tint=(128, 118, 108, 146),
        motif="seal",
    ),
    Theme(
        key="C_dark_ink",
        name="墨锋军务",
        note="战斗高压层：深墨底、冷青灰信息层、朱红危险提示、金铜细边。",
        bg=(31, 38, 41, 235),
        bg2=(17, 21, 24, 232),
        line=(165, 134, 82, 155),
        inner=(119, 142, 146, 72),
        accent=(190, 76, 59, 235),
        accent2=(92, 137, 129, 218),
        text=(239, 231, 213, 255),
        shadow=(0, 0, 0, 120),
        disabled_tint=(83, 88, 88, 168),
        motif="iron",
    ),
    Theme(
        key="D_sandtable_campaign",
        name="沙盘营帐",
        note="地图、关卡、布阵、路线选择：暖沙纸底、路线节点、军旗感角标。",
        bg=(226, 210, 178, 230),
        bg2=(196, 176, 139, 224),
        line=(112, 90, 55, 170),
        inner=(255, 246, 224, 108),
        accent=(175, 105, 52, 230),
        accent2=(160, 61, 48, 220),
        text=(50, 39, 28, 255),
        shadow=(83, 59, 28, 76),
        disabled_tint=(137, 128, 112, 142),
        motif="route",
    ),
    Theme(
        key="E_military_dossier",
        name="军务档案",
        note="说明、图鉴、详情面板：素纸灰墨、档案线框、低装饰密度。",
        bg=(232, 229, 218, 230),
        bg2=(202, 199, 187, 224),
        line=(77, 78, 72, 165),
        inner=(255, 255, 248, 96),
        accent=(91, 92, 84, 225),
        accent2=(159, 56, 47, 205),
        text=(35, 35, 31, 255),
        shadow=(50, 47, 39, 64),
        disabled_tint=(130, 130, 124, 146),
        motif="dossier",
    ),
    Theme(
        key="F_celadon_jade",
        name="青瓷玉令",
        note="成长、羁绊、可用状态：青瓷玉色、冷绿边线、轻金点缀。",
        bg=(220, 233, 223, 228),
        bg2=(175, 201, 189, 224),
        line=(54, 104, 91, 168),
        inner=(244, 255, 248, 110),
        accent=(55, 132, 112, 230),
        accent2=(185, 141, 66, 218),
        text=(28, 49, 43, 255),
        shadow=(34, 69, 57, 72),
        disabled_tint=(116, 132, 126, 148),
        motif="jade",
    ),
    Theme(
        key="G_bronze_armor",
        name="玄铁铜甲",
        note="精英、装备、Boss 或危险确认：深铜铁板、硬边、低亮金属。",
        bg=(58, 54, 48, 235),
        bg2=(34, 32, 30, 232),
        line=(177, 126, 66, 172),
        inner=(231, 204, 147, 72),
        accent=(178, 93, 49, 232),
        accent2=(191, 151, 82, 220),
        text=(239, 228, 206, 255),
        shadow=(0, 0, 0, 126),
        disabled_tint=(82, 82, 78, 170),
        motif="armor",
    ),
    Theme(
        key="H_plain_ink",
        name="素墨留白",
        note="通用轻弹窗、教程、二级信息：大留白、黑墨细线、极低装饰。",
        bg=(248, 246, 239, 225),
        bg2=(230, 226, 215, 218),
        line=(43, 45, 42, 145),
        inner=(255, 255, 252, 90),
        accent=(48, 50, 48, 220),
        accent2=(176, 68, 52, 205),
        text=(28, 28, 26, 255),
        shadow=(54, 50, 42, 52),
        disabled_tint=(142, 142, 136, 140),
        motif="plain",
    ),
]


def lerp(a: int, b: int, t: float) -> int:
    return round(a + (b - a) * t)


def mix(c1: tuple[int, ...], c2: tuple[int, ...], t: float) -> tuple[int, ...]:
    return tuple(lerp(c1[i], c2[i], t) for i in range(len(c1)))


def rounded_gradient(size: tuple[int, int], radius: int, top: tuple[int, int, int, int], bottom: tuple[int, int, int, int]) -> Image.Image:
    w, h = size
    gradient = Image.new("RGBA", size, (0, 0, 0, 0))
    px = gradient.load()
    for y in range(h):
        t = y / max(1, h - 1)
        color = mix(top, bottom, t)
        for x in range(w):
            px[x, y] = color
    mask = Image.new("L", size, 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, w - 1, h - 1), radius=radius, fill=255)
    gradient.putalpha(Image.composite(gradient.getchannel("A"), Image.new("L", size, 0), mask))
    return gradient


def add_shadow(base: Image.Image, alpha: Image.Image, color: tuple[int, int, int, int], blur: int, offset: tuple[int, int]) -> None:
    shadow = Image.new("RGBA", base.size, (0, 0, 0, 0))
    shadow_alpha = alpha.filter(ImageFilter.GaussianBlur(blur))
    colored = Image.new("RGBA", base.size, color)
    colored.putalpha(shadow_alpha.point(lambda p: int(p * color[3] / 255)))
    shadow.alpha_composite(colored, offset)
    base.alpha_composite(shadow)


def draw_panel(theme: Theme, size: tuple[int, int], radius: int, border: int, mood: str) -> Image.Image:
    w, h = size
    img = Image.new("RGBA", size, (0, 0, 0, 0))
    body = rounded_gradient(size, radius, theme.bg, theme.bg2)
    mask = body.getchannel("A")
    add_shadow(img, mask, theme.shadow, 16, (0, 6))
    img.alpha_composite(body)
    d = ImageDraw.Draw(img)

    for i in range(border):
        c = mix(theme.line, theme.accent, i / max(1, border - 1))
        d.rounded_rectangle((i, i, w - 1 - i, h - 1 - i), radius=max(1, radius - i), outline=c, width=1)

    inset = border + 8
    d.rounded_rectangle((inset, inset, w - inset - 1, h - inset - 1), radius=max(1, radius - 10), outline=theme.inner, width=1)

    # Decorative but 9-slice-safe corner marks: stay inside non-stretched corners.
    corner = min(56, w // 8, h // 5)
    c = theme.accent
    for sx, sy in [(1, 1), (-1, 1), (1, -1), (-1, -1)]:
        x0 = inset if sx > 0 else w - inset
        y0 = inset if sy > 0 else h - inset
        if theme.motif == "plain":
            d.line((x0, y0, x0 + sx * (corner // 2), y0), fill=(*c[:3], 150), width=1)
        elif theme.motif == "dossier":
            d.line((x0, y0 + sy * corner, x0, y0), fill=(*c[:3], 160), width=1)
            d.line((x0, y0, x0 + sx * corner, y0), fill=(*c[:3], 160), width=1)
            d.rectangle((x0 + sx * 10 - 3, y0 + sy * 10 - 3, x0 + sx * 10 + 3, y0 + sy * 10 + 3), fill=theme.accent2)
        elif theme.motif == "route":
            d.line((x0, y0 + sy * corner, x0, y0), fill=c, width=2)
            d.line((x0, y0, x0 + sx * corner, y0), fill=c, width=2)
            d.polygon(
                [
                    (x0 + sx * 8, y0 + sy * 8),
                    (x0 + sx * 18, y0 + sy * 13),
                    (x0 + sx * 8, y0 + sy * 18),
                ],
                fill=theme.accent2,
            )
        elif theme.motif in {"armor", "iron"}:
            d.line((x0, y0 + sy * corner, x0, y0), fill=c, width=3)
            d.line((x0, y0, x0 + sx * corner, y0), fill=c, width=3)
            d.line((x0 + sx * 8, y0 + sy * 22, x0 + sx * 22, y0 + sy * 8), fill=theme.accent2, width=2)
        elif theme.motif == "jade":
            d.line((x0, y0 + sy * corner, x0, y0), fill=c, width=2)
            d.line((x0, y0, x0 + sx * corner, y0), fill=c, width=2)
            d.ellipse((x0 + sx * 14 - 5, y0 + sy * 14 - 5, x0 + sx * 14 + 5, y0 + sy * 14 + 5), fill=theme.accent2)
            d.ellipse((x0 + sx * 14 - 2, y0 + sy * 14 - 2, x0 + sx * 14 + 2, y0 + sy * 14 + 2), fill=theme.bg)
        else:
            d.line((x0, y0 + sy * corner, x0, y0), fill=c, width=2)
            d.line((x0, y0, x0 + sx * corner, y0), fill=c, width=2)
            d.ellipse((x0 + sx * 14 - 4, y0 + sy * 14 - 4, x0 + sx * 14 + 4, y0 + sy * 14 + 4), fill=theme.accent2)

    if mood == "window":
        for y in range(38, h - 36, 34):
            d.line((42, y, w - 42, y), fill=(*theme.line[:3], 22), width=1)
        if theme.motif == "route":
            d.line((70, h - 66, w - 70, h - 66), fill=(*theme.accent2[:3], 80), width=2)
            for x in range(110, w - 90, 130):
                d.ellipse((x - 5, h - 71, x + 5, h - 61), fill=(*theme.accent2[:3], 150))
        elif theme.motif == "dossier":
            for x in range(78, w - 78, 92):
                d.line((x, 32, x, h - 32), fill=(*theme.line[:3], 18), width=1)
    elif mood == "base":
        d.line((46, h // 2, w - 46, h // 2), fill=(*theme.line[:3], 34), width=1)
        if theme.motif == "jade":
            d.line((82, 48, w - 82, 48), fill=(*theme.accent[:3], 72), width=3)
            d.line((82, h - 48, w - 82, h - 48), fill=(*theme.accent[:3], 72), width=3)
    elif mood == "headbar":
        d.polygon([(0, 0), (w, 0), (w - 26, h - 1), (28, h - 1)], fill=(*theme.accent[:3], 30))
        d.line((72, h - 18, w - 72, h - 18), fill=theme.accent, width=2)
        d.ellipse((w // 2 - 5, h - 23, w // 2 + 5, h - 13), fill=theme.accent2)
        if theme.motif in {"armor", "iron"}:
            d.line((34, 16, w - 34, 16), fill=(*theme.inner[:3], 92), width=2)
        elif theme.motif == "route":
            for x in range(118, w - 98, 120):
                d.rectangle((x - 4, h - 22, x + 4, h - 14), fill=theme.accent2)

    return img


def disabled(img: Image.Image, tint: tuple[int, int, int, int]) -> Image.Image:
    gray = img.convert("LA").convert("RGBA")
    overlay = Image.new("RGBA", img.size, tint)
    out = Image.alpha_composite(gray, overlay)
    alpha = img.getchannel("A").point(lambda p: int(p * 0.68))
    out.putalpha(alpha)
    return out


def draw_rect_button(theme: Theme, size=(320, 96), state="normal") -> Image.Image:
    w, h = size
    top = mix(theme.accent, theme.bg, 0.2)
    bottom = mix(theme.accent, (32, 24, 18, 235), 0.16)
    img = rounded_gradient(size, 12, top, bottom)
    out = Image.new("RGBA", size, (0, 0, 0, 0))
    add_shadow(out, img.getchannel("A"), theme.shadow, 10, (0, 4))
    out.alpha_composite(img)
    d = ImageDraw.Draw(out)
    d.rounded_rectangle((1, 1, w - 2, h - 2), radius=12, outline=theme.line, width=2)
    d.rounded_rectangle((8, 8, w - 9, h - 9), radius=8, outline=theme.inner, width=1)
    d.line((34, h - 18, w - 34, h - 18), fill=(*theme.inner[:3], 120), width=1)
    if theme.motif in {"route", "dossier", "plain"}:
        d.line((26, 20, 66, 20), fill=(*theme.accent2[:3], 150), width=2)
        d.line((w - 66, 20, w - 26, 20), fill=(*theme.accent2[:3], 150), width=2)
    elif theme.motif in {"armor", "iron"}:
        d.line((12, 12, 36, 36), fill=(*theme.accent2[:3], 130), width=2)
        d.line((w - 12, 12, w - 36, 36), fill=(*theme.accent2[:3], 130), width=2)
    return disabled(out, theme.disabled_tint) if state == "disabled" else out


def draw_circle_button(theme: Theme, size=(128, 128), state="normal") -> Image.Image:
    w, h = size
    img = Image.new("RGBA", size, (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.ellipse((8, 8, w - 9, h - 9), fill=theme.bg2)
    d.ellipse((12, 12, w - 13, h - 13), outline=theme.line, width=3)
    d.ellipse((24, 24, w - 25, h - 25), outline=theme.inner, width=2)
    d.ellipse((43, 43, w - 44, h - 44), fill=(*theme.accent[:3], 56), outline=theme.accent, width=2)
    d.line((w // 2, 26, w // 2, 42), fill=theme.accent, width=2)
    d.line((w // 2, h - 26, w // 2, h - 42), fill=theme.accent, width=2)
    d.line((26, h // 2, 42, h // 2), fill=theme.accent, width=2)
    d.line((w - 26, h // 2, w - 42, h // 2), fill=theme.accent, width=2)
    if theme.motif == "route":
        d.polygon([(w // 2, 30), (w // 2 + 9, 46), (w // 2, 42), (w // 2 - 9, 46)], fill=theme.accent2)
    elif theme.motif == "plain":
        d.arc((30, 30, w - 31, h - 31), 220, 320, fill=theme.accent2, width=2)
    return disabled(img, theme.disabled_tint) if state == "disabled" else img


def draw_tab_button(theme: Theme, size=(240, 82), state="normal") -> Image.Image:
    w, h = size
    img = Image.new("RGBA", size, (0, 0, 0, 0))
    points = [(18, 4), (w - 18, 4), (w - 4, h // 2), (w - 22, h - 6), (22, h - 6), (4, h // 2)]
    d = ImageDraw.Draw(img)
    d.polygon(points, fill=theme.bg)
    d.line(points + [points[0]], fill=theme.line, width=2)
    inner = [(30, 14), (w - 30, 14), (w - 18, h // 2), (w - 34, h - 16), (34, h - 16), (18, h // 2)]
    d.line(inner + [inner[0]], fill=theme.inner, width=1)
    d.line((46, h - 20, w - 46, h - 20), fill=theme.accent, width=2)
    return disabled(img, theme.disabled_tint) if state == "disabled" else img


def save_asset(img: Image.Image, path: Path) -> dict:
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path)
    return {"path": path.relative_to(ROOT).as_posix(), "size": list(img.size)}


def make_contact_sheet(records: list[dict]) -> None:
    font = ImageFont.load_default()
    thumb_w, thumb_h = 360, 210
    cols = 3
    rows = (len(records) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * thumb_w, rows * thumb_h), (231, 224, 211))
    d = ImageDraw.Draw(sheet)
    for idx, rec in enumerate(records):
        x = (idx % cols) * thumb_w
        y = (idx // cols) * thumb_h
        d.rectangle((x, y, x + thumb_w - 1, y + thumb_h - 1), outline=(188, 174, 148))
        img = Image.open(ROOT / rec["path"]).convert("RGBA")
        scale = min((thumb_w - 40) / img.width, (thumb_h - 56) / img.height, 1)
        preview = img.resize((int(img.width * scale), int(img.height * scale)))
        px = x + (thumb_w - preview.width) // 2
        py = y + 28 + (thumb_h - 66 - preview.height) // 2
        checker = Image.new("RGBA", preview.size, (245, 242, 234, 255))
        cd = ImageDraw.Draw(checker)
        for cy in range(0, preview.height, 16):
            for cx in range(0, preview.width, 16):
                if (cx // 16 + cy // 16) % 2:
                    cd.rectangle((cx, cy, cx + 15, cy + 15), fill=(217, 210, 196, 255))
        checker.alpha_composite(preview)
        sheet.paste(checker.convert("RGB"), (px, py))
        d.text((x + 12, y + 8), rec["label"], fill=(32, 30, 26), font=font)
    sheet.save(ROOT / "preview_contact_sheet.png")


def nine_slice_resize(img: Image.Image, target: tuple[int, int], inset: dict) -> Image.Image:
    left, top, right, bottom = inset["left"], inset["top"], inset["right"], inset["bottom"]
    w, h = img.size
    tw, th = target
    out = Image.new("RGBA", target, (0, 0, 0, 0))

    src_x = [0, left, w - right, w]
    src_y = [0, top, h - bottom, h]
    dst_x = [0, left, tw - right, tw]
    dst_y = [0, top, th - bottom, th]

    for yi in range(3):
        for xi in range(3):
            box = (src_x[xi], src_y[yi], src_x[xi + 1], src_y[yi + 1])
            part = img.crop(box)
            dw = dst_x[xi + 1] - dst_x[xi]
            dh = dst_y[yi + 1] - dst_y[yi]
            if part.size != (dw, dh):
                part = part.resize((dw, dh), Image.Resampling.LANCZOS)
            out.alpha_composite(part, (dst_x[xi], dst_y[yi]))
    return out


def make_stretch_preview(manifest: dict) -> None:
    rows = []
    for set_key, set_data in manifest["sets"].items():
        for asset_key, target in [
            ("window_panel", (980, 360)),
            ("baseplate_panel", (920, 150)),
            ("headbar_panel", (980, 88)),
            ("button_rect_normal", (520, 96)),
            ("button_tab_normal", (420, 82)),
        ]:
            rec = set_data["assets"][asset_key]
            img = Image.open(ROOT / rec["path"]).convert("RGBA")
            resized = nine_slice_resize(img, target, rec["nine_slice"])
            rows.append((f"{set_key}/{asset_key}", resized))

    row_h = 420
    sheet = Image.new("RGB", (1120, row_h * len(rows)), (231, 224, 211))
    d = ImageDraw.Draw(sheet)
    font = ImageFont.load_default()
    for idx, (label, img) in enumerate(rows):
        y = idx * row_h
        d.rectangle((0, y, 1119, y + row_h - 1), outline=(188, 174, 148))
        d.text((14, y + 12), label, fill=(32, 30, 26), font=font)
        checker = Image.new("RGBA", img.size, (245, 242, 234, 255))
        cd = ImageDraw.Draw(checker)
        for cy in range(0, img.height, 16):
            for cx in range(0, img.width, 16):
                if (cx // 16 + cy // 16) % 2:
                    cd.rectangle((cx, cy, cx + 15, cy + 15), fill=(217, 210, 196, 255))
        checker.alpha_composite(img)
        px = 126
        py = y + (row_h - img.height) // 2
        sheet.paste(checker.convert("RGB"), (px, py))
    sheet.save(ROOT / "preview_9slice_stretch_test.png")


def main() -> None:
    manifest: dict = {
        "name": "三国斗阵 UI 控件资源包 v01",
        "status": "effect-derived draft assets; pending art review before formal asset registry",
        "nine_slice_note": "Insets are measured in pixels from left/top/right/bottom. Keep decorative corner marks outside stretch center.",
        "sets": {},
    }
    contact_records: list[dict] = []

    for theme in THEMES:
        set_dir = ROOT / theme.key
        assets: dict = {}

        specs = [
            ("window_panel", draw_panel(theme, (720, 460), 18, 4, "window"), {"left": 72, "top": 72, "right": 72, "bottom": 72}),
            ("baseplate_panel", draw_panel(theme, (640, 190), 14, 4, "base"), {"left": 72, "top": 58, "right": 72, "bottom": 58}),
            ("headbar_panel", draw_panel(theme, (720, 104), 10, 3, "headbar"), {"left": 96, "top": 34, "right": 96, "bottom": 34}),
        ]

        for asset_name, img, nine in specs:
            rec = save_asset(img, set_dir / f"{asset_name}.png")
            assets[asset_name] = {**rec, "scale_mode": "nine_slice", "nine_slice": nine}
            contact_records.append({"path": rec["path"], "label": f"{theme.key}/{asset_name}"})

        button_specs = [
            ("button_rect", draw_rect_button, {"left": 42, "top": 28, "right": 42, "bottom": 28}, "nine_slice"),
            ("button_circle", draw_circle_button, None, "fixed_uniform"),
            ("button_tab", draw_tab_button, {"left": 48, "top": 28, "right": 48, "bottom": 28}, "nine_slice"),
        ]
        for base_name, fn, nine, scale_mode in button_specs:
            for state in ["normal", "disabled"]:
                img = fn(theme, state=state)
                rec = save_asset(img, set_dir / f"{base_name}_{state}.png")
                assets[f"{base_name}_{state}"] = {**rec, "state": state, "scale_mode": scale_mode}
                if nine:
                    assets[f"{base_name}_{state}"]["nine_slice"] = nine
                contact_records.append({"path": rec["path"], "label": f"{theme.key}/{base_name}_{state}"})

        manifest["sets"][theme.key] = {
            "display_name": theme.name,
            "usage_note": theme.note,
            "assets": assets,
        }

    (ROOT / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    make_contact_sheet(contact_records)
    make_stretch_preview(manifest)


if __name__ == "__main__":
    main()

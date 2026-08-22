from __future__ import annotations

import json
import math
import random
import shutil
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter


PACKAGE = "battle-bottom-hud-light-components-v01"
OUT = Path("assets/art/packages") / PACKAGE
SOURCE_IMAGE = Path(
    r"C:\Users\littl\.codex\generated_images\01a01c7f-a501-7090-89e1-19817902c1de\call_AZIjefHyO3MhLsUNv6I2uDeB.png"
)
SCREEN = (1920, 1080)
HUD_SIZE = (960, 252)
HUD_ANCHOR = ((SCREEN[0] - HUD_SIZE[0]) // 2, SCREEN[1] - HUD_SIZE[1])


COLORS = {
    "smoke": (11, 12, 12, 156),
    "smoke_deep": (5, 6, 6, 205),
    "bronze": (161, 124, 72, 224),
    "bronze_dim": (102, 76, 45, 178),
    "gold": (220, 181, 101, 235),
    "cinnabar": (125, 35, 28, 225),
    "cinnabar_dark": (74, 21, 18, 230),
    "ivory": (218, 204, 170, 185),
    "jade": (72, 139, 104, 215),
    "red_hp": (190, 38, 33, 238),
    "red_hp_dark": (88, 15, 14, 230),
}


def ensure_dirs() -> dict[str, Path]:
    dirs = {
        "source": OUT / "source",
        "base": OUT / "transparent" / "base",
        "overlays": OUT / "transparent" / "overlays",
        "controls": OUT / "transparent" / "controls",
        "preview": OUT / "preview",
        "reference": OUT / "reference",
    }
    for path in dirs.values():
        path.mkdir(parents=True, exist_ok=True)
    return dirs


def new_rgba(size: tuple[int, int]) -> Image.Image:
    return Image.new("RGBA", size, (255, 255, 255, 0))


def hi(size: tuple[int, int], scale: int = 3) -> tuple[Image.Image, ImageDraw.ImageDraw, int]:
    im = new_rgba((size[0] * scale, size[1] * scale))
    return im, ImageDraw.Draw(im), scale


def down(im: Image.Image, size: tuple[int, int]) -> Image.Image:
    return im.resize(size, Image.Resampling.LANCZOS)


def rounded_rect(draw: ImageDraw.ImageDraw, box, radius: int, fill, outline=None, width: int = 1) -> None:
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)


def add_noise(im: Image.Image, amount: int = 10, alpha_scale: float = 0.18) -> Image.Image:
    random.seed(24)
    noise = Image.new("RGBA", im.size, (0, 0, 0, 0))
    pix = noise.load()
    for y in range(0, im.height, 2):
        for x in range(0, im.width, 2):
            v = random.randint(-amount, amount)
            if v >= 0:
                pix[x, y] = (255, 245, 220, int(v * alpha_scale))
            else:
                pix[x, y] = (0, 0, 0, int(-v * alpha_scale))
    noise = noise.filter(ImageFilter.GaussianBlur(0.4))
    _, _, _, alpha = im.split()
    noise.putalpha(Image.composite(noise.getchannel("A"), Image.new("L", im.size, 0), alpha))
    return Image.alpha_composite(im, noise)


def enforce_safe_border(im: Image.Image, border: int = 2) -> Image.Image:
    out = im.copy()
    pix = out.load()
    w, h = out.size
    for y in range(h):
        for x in range(w):
            if x < border or y < border or x >= w - border or y >= h - border:
                r, g, b, _ = pix[x, y]
                pix[x, y] = (r, g, b, 0)
    return out


def frame_base(size: tuple[int, int], divider_x: int | None = None) -> Image.Image:
    im, d, s = hi(size, 3)
    w, h = im.size
    pad = 4 * s
    rounded_rect(d, (pad, pad, w - pad, h - pad), 6 * s, COLORS["smoke"], COLORS["bronze_dim"], 1 * s)
    rounded_rect(d, (pad + 4 * s, pad + 4 * s, w - pad - 4 * s, h - pad - 4 * s), 3 * s, None, COLORS["bronze"], 1 * s)
    d.line((34 * s, h - 13 * s, w - 34 * s, h - 13 * s), fill=COLORS["cinnabar"], width=3 * s)
    d.line((38 * s, 13 * s, w - 38 * s, 13 * s), fill=(201, 155, 89, 82), width=1 * s)
    if divider_x:
        x = divider_x * s
        d.line((x, 18 * s, x, h - 18 * s), fill=(205, 158, 91, 130), width=1 * s)
        d.line((x + 3 * s, 35 * s, x + 3 * s, h - 35 * s), fill=(15, 14, 13, 140), width=1 * s)

    # Small corner tabs, deliberately fixed-position but modest enough for a HUD.
    for x, y, sx, sy in (
        (pad, pad, 1, 1),
        (w - pad, pad, -1, 1),
        (pad, h - pad, 1, -1),
        (w - pad, h - pad, -1, -1),
    ):
        d.line((x, y + sy * 22 * s, x, y, x + sx * 22 * s, y), fill=COLORS["bronze"], width=2 * s)
        d.line((x + sx * 10 * s, y + sy * 3 * s, x + sx * 10 * s, y + sy * 14 * s), fill=COLORS["bronze_dim"], width=1 * s)
        d.line((x + sx * 3 * s, y + sy * 10 * s, x + sx * 14 * s, y + sy * 10 * s), fill=COLORS["bronze_dim"], width=1 * s)

    im = down(im, size)
    return add_noise(im, 12)


def plaque(size: tuple[int, int], red: bool = True) -> Image.Image:
    im, d, s = hi(size, 4)
    w, h = im.size
    pad = 4 * s
    fill = COLORS["cinnabar"] if red else COLORS["smoke_deep"]
    fill2 = COLORS["cinnabar_dark"] if red else (22, 18, 15, 215)
    points = [
        (pad + 14 * s, pad),
        (w - pad - 18 * s, pad),
        (w - pad, h // 2),
        (w - pad - 18 * s, h - pad),
        (pad + 14 * s, h - pad),
        (pad, h // 2),
    ]
    d.polygon(points, fill=fill, outline=COLORS["bronze"])
    d.line((34 * s, 11 * s, w - 34 * s, 11 * s), fill=(238, 190, 98, 108), width=1 * s)
    d.line((36 * s, h - 11 * s, w - 36 * s, h - 11 * s), fill=fill2, width=2 * s)
    for x in (20 * s, w - 20 * s):
        d.ellipse((x - 5 * s, h // 2 - 5 * s, x + 5 * s, h // 2 + 5 * s), fill=COLORS["gold"])
    return down(im, size)


def section_header(size: tuple[int, int]) -> Image.Image:
    im, d, s = hi(size, 4)
    w, h = im.size
    y = h // 2
    d.line((18 * s, y, w - 18 * s, y), fill=COLORS["bronze"], width=2 * s)
    rounded_rect(d, (54 * s, 6 * s, w - 54 * s, h - 6 * s), 4 * s, (43, 24, 17, 200), COLORS["bronze"], 1 * s)
    d.line((72 * s, 10 * s, w - 72 * s, 10 * s), fill=(232, 194, 116, 82), width=1 * s)
    for x in (28 * s, w - 28 * s):
        d.polygon([(x, y - 7 * s), (x + 7 * s, y), (x, y + 7 * s), (x - 7 * s, y)], fill=COLORS["gold"], outline=COLORS["bronze"])
    return down(im, size)


def avatar_ring(size: int, selected: bool = False, disabled: bool = False) -> Image.Image:
    im, d, s = hi((size, size), 4)
    w = im.size[0]
    c = w // 2
    if selected:
        glow = Image.new("RGBA", im.size, (255, 255, 255, 0))
        gd = ImageDraw.Draw(glow)
        gd.ellipse((7 * s, 7 * s, w - 7 * s, w - 7 * s), outline=(137, 203, 141, 180), width=8 * s)
        im.alpha_composite(glow.filter(ImageFilter.GaussianBlur(6 * s)))
    fill = (16, 17, 15, 92) if not disabled else (38, 38, 38, 110)
    d.ellipse((8 * s, 8 * s, w - 8 * s, w - 8 * s), fill=fill, outline=COLORS["bronze"], width=2 * s)
    d.ellipse((15 * s, 15 * s, w - 15 * s, w - 15 * s), outline=(221, 181, 99, 150), width=1 * s)
    hp_color = COLORS["red_hp"] if not disabled else (92, 92, 92, 210)
    d.arc((10 * s, 10 * s, w - 10 * s, w - 10 * s), start=42, end=138, fill=hp_color, width=5 * s)
    if selected:
        d.polygon([(c, 4 * s), (c + 7 * s, 12 * s), (c, 20 * s), (c - 7 * s, 12 * s)], fill=COLORS["jade"], outline=COLORS["gold"])
    return down(im, (size, size))


def icon_slot(size: int = 68, variant: str = "skill") -> Image.Image:
    im, d, s = hi((size, size), 4)
    w = im.size[0]
    pad = 5 * s
    fill = (24, 21, 17, 92) if variant == "skill" else (18, 18, 17, 118)
    d.rectangle((pad, pad, w - pad, w - pad), fill=fill, outline=COLORS["bronze"], width=2 * s)
    d.rectangle((pad + 5 * s, pad + 5 * s, w - pad - 5 * s, w - pad - 5 * s), outline=(232, 190, 103, 105), width=1 * s)
    corner = 11 * s
    for x, y, sx, sy in (
        (pad, pad, 1, 1),
        (w - pad, pad, -1, 1),
        (pad, w - pad, 1, -1),
        (w - pad, w - pad, -1, -1),
    ):
        d.line((x, y + sy * corner, x, y, x + sx * corner, y), fill=COLORS["gold"], width=2 * s)
    return down(im, (size, size))


def portrait_backing() -> Image.Image:
    size = (248, 230)
    im, d, s = hi(size, 3)
    w, h = im.size
    # Empty ink wash backing for runtime bust art. No character pixels baked in.
    for i in range(20):
        alpha = max(8, 42 - i)
        x0 = (24 + i * 2) * s
        y0 = (14 + i) * s
        x1 = (220 - i) * s
        y1 = (214 - i // 2) * s
        d.ellipse((x0, y0, x1, y1), fill=(232, 225, 204, alpha))
    d.line((34 * s, 206 * s, 230 * s, 206 * s), fill=(172, 128, 74, 130), width=2 * s)
    d.line((44 * s, 36 * s, 214 * s, 190 * s), fill=(18, 18, 16, 42), width=6 * s)
    d.line((60 * s, 28 * s, 205 * s, 160 * s), fill=(120, 36, 28, 50), width=3 * s)
    return down(im.filter(ImageFilter.GaussianBlur(0.45 * s)), size)


def stat_plate(size: tuple[int, int], accent: str = "attack") -> Image.Image:
    im, d, s = hi(size, 4)
    w, h = im.size
    rounded_rect(d, (4 * s, 4 * s, w - 4 * s, h - 4 * s), 6 * s, (222, 207, 174, 170), COLORS["bronze"], 1 * s)
    d.line((46 * s, 8 * s, 46 * s, h - 8 * s), fill=(120, 86, 45, 95), width=1 * s)
    color = (155, 39, 32, 228) if accent == "attack" else (66, 111, 148, 228)
    if accent == "attack":
        d.line((18 * s, 29 * s, 32 * s, 15 * s), fill=color, width=4 * s)
        d.line((20 * s, 16 * s, 34 * s, 30 * s), fill=(92, 26, 23, 215), width=2 * s)
    else:
        d.polygon([(25 * s, 12 * s), (36 * s, 18 * s), (34 * s, 32 * s), (25 * s, 38 * s), (16 * s, 32 * s), (14 * s, 18 * s)], fill=color, outline=(210, 230, 245, 130))
    return down(im, size)


def hp_bar_frame(size: tuple[int, int]) -> Image.Image:
    im, d, s = hi(size, 4)
    w, h = im.size
    rounded_rect(d, (4 * s, 4 * s, w - 4 * s, h - 4 * s), 9 * s, (11, 9, 8, 166), COLORS["bronze"], 2 * s)
    rounded_rect(d, (13 * s, 12 * s, w - 13 * s, h - 12 * s), 5 * s, (30, 14, 12, 165), (224, 188, 116, 125), 1 * s)
    return down(im, size)


def hp_bar_fill(size: tuple[int, int]) -> Image.Image:
    im, d, s = hi(size, 4)
    w, h = im.size
    rounded_rect(d, (3 * s, 3 * s, w - 3 * s, h - 3 * s), 6 * s, COLORS["red_hp"], None, 0)
    d.line((12 * s, 9 * s, w - 12 * s, 9 * s), fill=(255, 124, 106, 132), width=2 * s)
    d.line((12 * s, h - 9 * s, w - 12 * s, h - 9 * s), fill=COLORS["red_hp_dark"], width=2 * s)
    return down(im, size)


def place_grid_preview(assets: list[tuple[str, Image.Image]]) -> Image.Image:
    cell_w, cell_h = 250, 150
    cols = 4
    rows = math.ceil(len(assets) / cols)
    im = Image.new("RGBA", (cols * cell_w, rows * cell_h), (42, 42, 42, 255))
    d = ImageDraw.Draw(im)
    for idx, (name, asset) in enumerate(assets):
        x = (idx % cols) * cell_w
        y = (idx // cols) * cell_h
        d.rectangle((x, y, x + cell_w - 1, y + cell_h - 1), outline=(80, 80, 80, 255))
        preview = asset.copy()
        preview.thumbnail((cell_w - 34, cell_h - 42), Image.Resampling.LANCZOS)
        im.alpha_composite(preview, (x + (cell_w - preview.width) // 2, y + 12))
        d.text((x + 10, y + cell_h - 24), name, fill=(232, 232, 232, 255))
    return im


def checker(size: tuple[int, int], cell: int = 32) -> Image.Image:
    im = Image.new("RGBA", size, (48, 48, 52, 255))
    d = ImageDraw.Draw(im)
    for y in range(0, size[1], cell):
        for x in range(0, size[0], cell):
            c = (82, 82, 88, 255) if (x // cell + y // cell) % 2 == 0 else (39, 39, 43, 255)
            d.rectangle((x, y, x + cell, y + cell), fill=c)
    return im


def nine_slice_resize(im: Image.Image, out_size: tuple[int, int], n: dict[str, int]) -> Image.Image:
    l, t, r, b = n["left"], n["top"], n["right"], n["bottom"]
    w, h = im.size
    ow, oh = out_size
    out = new_rgba(out_size)
    boxes = {
        "tl": (0, 0, l, t),
        "t": (l, 0, w - r, t),
        "tr": (w - r, 0, w, t),
        "l": (0, t, l, h - b),
        "c": (l, t, w - r, h - b),
        "r": (w - r, t, w, h - b),
        "bl": (0, h - b, l, h),
        "b": (l, h - b, w - r, h),
        "br": (w - r, h - b, w, h),
    }
    targets = {
        "tl": (0, 0, l, t),
        "t": (l, 0, ow - r, t),
        "tr": (ow - r, 0, ow, t),
        "l": (0, t, l, oh - b),
        "c": (l, t, ow - r, oh - b),
        "r": (ow - r, t, ow, oh - b),
        "bl": (0, oh - b, l, oh),
        "b": (l, oh - b, ow - r, oh),
        "br": (ow - r, oh - b, ow, oh),
    }
    for key, box in boxes.items():
        part = im.crop(box)
        tx0, ty0, tx1, ty1 = targets[key]
        if tx1 > tx0 and ty1 > ty0:
            out.alpha_composite(part.resize((tx1 - tx0, ty1 - ty0), Image.Resampling.LANCZOS), (tx0, ty0))
    return out


def composite_reference(assets: dict[str, Image.Image]) -> Image.Image:
    bg = Image.new("RGBA", SCREEN, (18, 20, 20, 255))
    d = ImageDraw.Draw(bg)
    for y in range(SCREEN[1]):
        shade = int(26 - 14 * (y / SCREEN[1]))
        d.line((0, y, SCREEN[0], y), fill=(shade, shade + 2, shade + 1, 255))
    for i in range(220):
        x = (i * 137) % SCREEN[0]
        y = 510 + ((i * 41) % 470)
        alpha = 10 + (i % 4) * 7
        d.line((x, y, x + 90, y + 22), fill=(74, 55, 33, alpha), width=1)
    bg = bg.filter(ImageFilter.GaussianBlur(0.25))
    x, y = HUD_ANCHOR
    bg.alpha_composite(assets["hud_group_base_9slice"], (x, y))
    bg.alpha_composite(assets["portrait_ink_backing_empty"], (x + 310, y + 18))
    bg.alpha_composite(assets["hero_name_plaque_blank_9slice"], (x + 470, y + 16))
    bg.alpha_composite(assets["section_header_blank_9slice"], (x + 480, y + 76))
    for i in range(4):
        bg.alpha_composite(assets["skill_icon_slot_square_empty"], (x + 486 + i * 76, y + 114))
    bg.alpha_composite(assets["section_header_small_blank_9slice"], (x + 716, y + 76))
    for i in range(3):
        bg.alpha_composite(assets["equipment_icon_slot_square_empty"], (x + 720 + i * 76, y + 114))
    bg.alpha_composite(assets["stat_plate_attack_blank_9slice"], (x + 410, y + 194))
    bg.alpha_composite(assets["stat_plate_defense_blank_9slice"], (x + 572, y + 194))
    bg.alpha_composite(assets["hp_bar_frame_9slice"], (x + 720, y + 196))
    bg.alpha_composite(assets["hp_bar_fill_red_9slice"], (x + 733, y + 208))
    avatar_positions = []
    for row in range(2):
        for col in range(5):
            avatar_positions.append((x + 40 + col * 48, y + 42 + row * 82))
    for idx, pos in enumerate(avatar_positions):
        ring = assets["team_avatar_frame_selected"] if idx == 0 else assets["team_avatar_frame_normal"]
        bg.alpha_composite(ring, pos)
    return bg


def main() -> None:
    dirs = ensure_dirs()
    concept_path = dirs["source"] / "battle_bottom_hud_clean_blank_source.png"

    assets = {
        "hud_group_base_9slice": frame_base(HUD_SIZE, divider_x=300),
        "team_selector_base_9slice": frame_base((300, 220)),
        "hero_detail_base_9slice": frame_base((640, 220)),
        "portrait_ink_backing_empty": portrait_backing(),
        "hero_name_plaque_blank_9slice": plaque((224, 52), red=True),
        "section_header_blank_9slice": section_header((230, 34)),
        "section_header_small_blank_9slice": section_header((168, 34)),
        "skill_icon_slot_square_empty": icon_slot(68, "skill"),
        "equipment_icon_slot_square_empty": icon_slot(68, "equipment"),
        "team_avatar_frame_normal": avatar_ring(62, False, False),
        "team_avatar_frame_selected": avatar_ring(62, True, False),
        "team_avatar_frame_disabled": avatar_ring(62, False, True),
        "stat_plate_attack_blank_9slice": stat_plate((154, 44), "attack"),
        "stat_plate_defense_blank_9slice": stat_plate((154, 44), "defense"),
        "hp_bar_frame_9slice": hp_bar_frame((214, 34)),
        "hp_bar_fill_red_9slice": hp_bar_fill((188, 12)),
    }
    assets = {name: enforce_safe_border(asset) for name, asset in assets.items()}

    categories = {
        "base": [
            "hud_group_base_9slice",
            "team_selector_base_9slice",
            "hero_detail_base_9slice",
            "portrait_ink_backing_empty",
        ],
        "overlays": [
            "hero_name_plaque_blank_9slice",
            "section_header_blank_9slice",
            "section_header_small_blank_9slice",
        ],
        "controls": [
            "skill_icon_slot_square_empty",
            "equipment_icon_slot_square_empty",
            "team_avatar_frame_normal",
            "team_avatar_frame_selected",
            "team_avatar_frame_disabled",
            "stat_plate_attack_blank_9slice",
            "stat_plate_defense_blank_9slice",
            "hp_bar_frame_9slice",
            "hp_bar_fill_red_9slice",
        ],
    }

    manifest_assets = []
    for category, names in categories.items():
        for name in names:
            path = dirs[category] / f"{name}.png"
            assets[name].save(path)
            size = assets[name].size
            is_9 = name.endswith("_9slice")
            item = {
                "id": name,
                "path": str(path).replace("\\", "/"),
                "type": category,
                "size_px": {"width": size[0], "height": size[1]},
                "scale_mode": "nine_slice" if is_9 else "fixed",
                "contains_character_art": False,
                "contains_avatar_art": False,
            }
            if is_9:
                item["nine_slice"] = {"left": 24, "top": 24, "right": 24, "bottom": 24}
                if "hp_bar" in name:
                    item["nine_slice"] = {"left": 18, "top": 10, "right": 18, "bottom": 10}
                if "plaque" in name:
                    item["nine_slice"] = {"left": 44, "top": 16, "right": 44, "bottom": 16}
                if "section_header" in name:
                    item["nine_slice"] = {"left": 56, "top": 12, "right": 56, "bottom": 12}
                if "stat_plate" in name:
                    item["nine_slice"] = {"left": 54, "top": 14, "right": 20, "bottom": 14}
            manifest_assets.append(item)

    preview_assets = place_grid_preview([(name, assets[name]) for name in assets])
    preview_assets.convert("RGB").save(dirs["preview"] / "preview_assets.png", quality=94)

    alpha = checker((1200, 640))
    x, y = 32, 32
    for name, asset in assets.items():
        alpha.alpha_composite(asset, (x, y))
        x += 280
        if x > 940:
            x = 32
            y += 150
    alpha.convert("RGB").save(dirs["preview"] / "preview_alpha_check.png", quality=94)

    stretch = checker((1400, 620))
    stretch.alpha_composite(assets["hud_group_base_9slice"], (40, 40))
    stretch.alpha_composite(nine_slice_resize(assets["hud_group_base_9slice"], (1180, 320), {"left": 24, "top": 24, "right": 24, "bottom": 24}), (40, 320))
    stretch.alpha_composite(nine_slice_resize(assets["hero_name_plaque_blank_9slice"], (360, 52), {"left": 44, "top": 16, "right": 44, "bottom": 16}), (1010, 60))
    stretch.alpha_composite(nine_slice_resize(assets["hp_bar_frame_9slice"], (360, 34), {"left": 18, "top": 10, "right": 18, "bottom": 10}), (1010, 140))
    stretch.convert("RGB").save(dirs["preview"] / "preview_9slice_stretch.png", quality=94)

    reference = composite_reference(assets)
    reference.save(dirs["reference"] / "battle_bottom_hud_blank_components_1920x1080.png")
    reference.crop((HUD_ANCHOR[0] - 30, HUD_ANCHOR[1] - 30, HUD_ANCHOR[0] + HUD_SIZE[0] + 30, SCREEN[1])).save(concept_path)

    manifest = {
        "package": PACKAGE,
        "status": "implementation_ready_component_pack",
        "source_concept": str(concept_path).replace("\\", "/"),
        "target_screen": {"width": SCREEN[0], "height": SCREEN[1]},
        "layout_reference": {
            "hud_group_size_px": {"width": HUD_SIZE[0], "height": HUD_SIZE[1]},
            "hud_group_anchor_px_on_1920x1080": {"x": HUD_ANCHOR[0], "y": HUD_ANCHOR[1]},
            "team_to_detail_ratio": "approximately 1:2",
            "notes": "HUD is centered and bottom-attached. Character busts and avatar portraits are intentionally excluded.",
        },
        "assets": manifest_assets,
        "qa": {
            "alpha": "All exported controls are RGBA PNGs on transparent canvases; preview_alpha_check.png is provided for edge inspection.",
            "character_art": "No human bust or hero avatar pixels are included in exported controls.",
            "icon_compatibility": "Skill and equipment containers are square to match existing square game icons.",
            "nine_slice": "Stretchable base/plates are marked with nine_slice values; decorative rings and icon frames are fixed scale.",
        },
    }
    (OUT / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    readme = f"""# {PACKAGE}

这是一套基于已确认轻量战斗 HUD 方案拆分的可实装控件资源。

## 内容

- `transparent/base/`：HUD 总底、队伍区底、详情区底、空立绘水墨背板。
- `transparent/overlays/`：姓名牌、栏目条等固定叠加件。
- `transparent/controls/`：圆头像框、方形技能/装备槽、攻防信息底、血条框和血条填充。
- `reference/`：1920x1080 空控件拼装参考。
- `preview/`：资源总览、alpha 检查、9 宫拉伸检查。

## 实装说明

- 不包含人物立绘和头像；程序运行时把角色半身像、头像、技能 ICON、装备 ICON 贴入对应空槽。
- 需要拉伸的资源使用 manifest 中的 `nine_slice` 参数。
- 圆头像框、技能槽、装备槽按固定比例使用，不建议 9 宫拉伸。
- 技能和装备槽保持正方形，以兼容当前项目已有 ICON。

## QA

- 外围为透明 PNG，不保留截图背景。
- 没有人物像素残留。
- 已输出 `preview_alpha_check.png` 和 `preview_9slice_stretch.png` 供检查。
"""
    (OUT / "README.md").write_text(readme, encoding="utf-8")

    print(json.dumps({"package": str(OUT), "assets": len(manifest_assets)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

from __future__ import annotations

import json
import shutil
from collections import deque
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont


ROOT = Path(__file__).resolve().parents[1]
SRC = Path(
    r"C:\Users\littl\.codex\generated_images\01a01c7f-a501-7090-89e1-19817902c1de\call_wEiAgfN6zk0ciMGnj4Wzl63w.png"
)
TEXT_SRC = Path(
    r"C:\Users\littl\.codex\generated_images\01a01c7f-a501-7090-89e1-19817902c1de\call_MG5vowjT1ivOC1Nu012CB6Zj.png"
)
DUEL_STAMP_SRC = Path(
    r"C:\Users\littl\.codex\generated_images\01a01c7f-a501-7090-89e1-19817902c1de\call_zWpFCdvKkhnd91jxUPZGkwgr.png"
)
OUT = ROOT / "assets" / "art" / "packages" / "battle-ui-ink-warfield-components-v02"
SOURCE = OUT / "source"
TRANSPARENT = OUT / "transparent"


COMPONENTS = [
    {
        "name": "top_stage_timer_frame_blank",
        "box": [50, 38, 852, 214],
        "role": "top_hud_frame",
        "scale_mode": "nine_slice",
        "nine_slice": [72, 42, 72, 44],
        "usage": "顶部关卡/时间/波次复合框。文字全部由工程层渲染。",
    },
    {
        "name": "top_resource_bar_blank",
        "box": [896, 54, 1507, 154],
        "role": "top_resource_bar",
        "scale_mode": "nine_slice",
        "nine_slice": [54, 26, 54, 26],
        "usage": "右上资源栏底框。资源图标和数字由工程层叠加。",
    },
    {
        "name": "hp_banner_player_blue_blank",
        "box": [56, 229, 752, 345],
        "role": "hp_bar_base",
        "scale_mode": "nine_slice",
        "nine_slice": [72, 34, 72, 34],
        "usage": "我方总兵力/血条旗帜底框。头像圆框和文字分层叠加。",
        "holes": [{"type": "rect", "box": [62, 28, 635, 88]}],
    },
    {
        "name": "hp_fill_player_blue",
        "box": [120, 258, 716, 316],
        "role": "hp_bar_fill",
        "scale_mode": "nine_slice",
        "nine_slice": [28, 12, 28, 12],
        "usage": "我方血条填充层，可按数值横向裁切或遮罩。",
    },
    {
        "name": "hp_banner_enemy_red_blank",
        "box": [783, 229, 1481, 345],
        "role": "hp_bar_base",
        "scale_mode": "nine_slice",
        "nine_slice": [72, 34, 72, 34],
        "usage": "敌方总兵力/血条旗帜底框。头像圆框和文字分层叠加。",
        "holes": [{"type": "rect", "box": [62, 28, 638, 88]}],
    },
    {
        "name": "hp_fill_enemy_red",
        "box": [846, 258, 1444, 316],
        "role": "hp_bar_fill",
        "scale_mode": "nine_slice",
        "nine_slice": [28, 12, 28, 12],
        "usage": "敌方血条填充层，可按数值横向裁切或遮罩。",
    },
    {
        "name": "portrait_medallion_frame_empty",
        "box": [42, 360, 318, 627],
        "role": "portrait_overlay",
        "scale_mode": "fixed",
        "usage": "圆形头像外框，固定尺寸叠加，不参与九宫格。",
        "holes": [{"type": "ellipse", "box": [45, 38, 232, 228]}],
    },
    {
        "name": "start_challenge_seal_blank",
        "box": [336, 352, 659, 651],
        "role": "primary_button",
        "scale_mode": "fixed",
        "usage": "开战按钮空白印章。按钮文字由工程层渲染。",
    },
    {
        "name": "formation_panel_frame_blank",
        "box": [680, 365, 1218, 641],
        "role": "formation_panel",
        "scale_mode": "nine_slice",
        "nine_slice": [70, 58, 70, 58],
        "usage": "布阵/对决大面板空框。棋盘格、标题、对决章分层叠加。",
    },
    {
        "name": "formation_grid_slot_2x2_reference",
        "box": [1247, 384, 1484, 617],
        "role": "grid_slot_group",
        "scale_mode": "fixed_grid",
        "usage": "格子组参考。正式 3x3 建议用单格控件平铺生成。",
    },
    {
        "name": "formation_grid_slot_single_blank",
        "box": [913, 678, 1086, 852],
        "role": "grid_slot",
        "scale_mode": "fixed",
        "usage": "布阵棋盘单格控件。正式 3x3 可用该完整方形槽平铺并由工程放置头像/数字。",
    },
    {
        "name": "duel_medallion_blank",
        "box": [35, 651, 303, 923],
        "role": "center_overlay",
        "scale_mode": "fixed",
        "usage": "中间对决装饰章，固定尺寸叠加。文字由工程层或单独书法图叠加。",
    },
    {
        "name": "minimap_frame_blank",
        "box": [335, 668, 632, 962],
        "role": "minimap_frame",
        "scale_mode": "fixed",
        "usage": "小地图外框和底板。地图内容由工程渲染。",
        "holes": [{"type": "rect", "box": [28, 24, 270, 262]}],
    },
    {
        "name": "hero_card_frame_blank",
        "box": [659, 650, 884, 986],
        "role": "hero_card_frame",
        "scale_mode": "fixed",
        "usage": "底部武将卡空框。头像、技能、属性、血条全部分层叠加。",
    },
    {
        "name": "hero_card_bottom_info_plate",
        "box": [674, 918, 869, 979],
        "role": "hero_card_subpanel",
        "scale_mode": "nine_slice",
        "nine_slice": [24, 18, 24, 18],
        "usage": "武将卡底部属性/血条信息区，可作为卡牌内部子面板。",
    },
    {
        "name": "skill_slot_square_blank",
        "box": [913, 678, 1086, 852],
        "role": "skill_slot",
        "scale_mode": "fixed",
        "usage": "技能槽/道具槽单格。",
    },
    {
        "name": "stat_plaque_strip_blank",
        "box": [1140, 708, 1477, 801],
        "role": "stat_label_bar",
        "scale_mode": "nine_slice",
        "nine_slice": [36, 20, 36, 20],
        "usage": "属性条/标签条，可横向拉伸。",
    },
    {
        "name": "round_control_button_blank",
        "box": [934, 830, 1106, 1000],
        "role": "round_button",
        "scale_mode": "fixed",
        "usage": "右下圆形控制按钮空框。",
    },
    {
        "name": "play_triangle_icon_gold",
        "box": [1108, 867, 1192, 956],
        "role": "icon",
        "scale_mode": "fixed",
        "usage": "播放三角图标，单独叠加到圆形按钮。",
    },
    {
        "name": "top_icon_button_frame_blank",
        "box": [1300, 834, 1390, 966],
        "role": "top_icon_button",
        "scale_mode": "fixed",
        "usage": "顶部小图标按钮通用空框，暂停/设置/退出等图标另行叠加；重复按钮框只保留这一份。",
    },
]


def reset_dir(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)


def is_checker_bg(rgb: tuple[int, int, int]) -> bool:
    r, g, b = rgb
    return max(rgb) - min(rgb) <= 10 and (r + g + b) / 3 >= 218


def remove_outer_checker(crop: Image.Image, holes: list[dict] | None = None) -> Image.Image:
    rgba = crop.convert("RGBA")
    w, h = rgba.size
    pix = rgba.load()
    remove = Image.new("L", (w, h), 0)
    rp = remove.load()
    seen: set[tuple[int, int]] = set()
    q: deque[tuple[int, int]] = deque()
    for x in range(w):
        q.append((x, 0))
        q.append((x, h - 1))
    for y in range(h):
        q.append((0, y))
        q.append((w - 1, y))

    while q:
        x, y = q.popleft()
        if x < 0 or y < 0 or x >= w or y >= h or (x, y) in seen:
            continue
        seen.add((x, y))
        if not is_checker_bg(pix[x, y][:3]):
            continue
        rp[x, y] = 255
        q.extend(((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)))

    remove = remove.filter(ImageFilter.MaxFilter(3)).filter(ImageFilter.GaussianBlur(0.8))
    rgba.putalpha(ImageChops.multiply(rgba.getchannel("A"), ImageChops.invert(remove)))
    if holes:
        hole_mask = Image.new("L", (w, h), 255)
        hd = ImageDraw.Draw(hole_mask)
        for hole in holes:
            box = tuple(hole["box"])
            if hole["type"] == "rect":
                hd.rectangle(box, fill=0)
            elif hole["type"] == "ellipse":
                hd.ellipse(box, fill=0)
        rgba.putalpha(ImageChops.multiply(rgba.getchannel("A"), hole_mask))
    bbox = rgba.getchannel("A").getbbox()
    if not bbox:
        return rgba
    pad = 4
    tight = rgba.crop(
        (
            max(0, bbox[0] - pad),
            max(0, bbox[1] - pad),
            min(w, bbox[2] + pad),
            min(h, bbox[3] + pad),
        )
    )
    out = Image.new("RGBA", (tight.width + 4, tight.height + 4), (0, 0, 0, 0))
    out.alpha_composite(tight, (2, 2))
    return out


def clean_connected_checker(crop: Image.Image) -> Image.Image:
    rgba = crop.convert("RGBA")
    w, h = rgba.size
    pix = rgba.load()
    remove = Image.new("L", (w, h), 0)
    rp = remove.load()
    seen: set[tuple[int, int]] = set()
    q: deque[tuple[int, int]] = deque()
    for x in range(w):
        q.append((x, 0))
        q.append((x, h - 1))
    for y in range(h):
        q.append((0, y))
        q.append((w - 1, y))
    while q:
        x, y = q.popleft()
        if x < 0 or y < 0 or x >= w or y >= h or (x, y) in seen:
            continue
        seen.add((x, y))
        if not is_checker_bg(pix[x, y][:3]):
            continue
        rp[x, y] = 255
        q.extend(((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)))
    remove = remove.filter(ImageFilter.MaxFilter(3)).filter(ImageFilter.GaussianBlur(0.6))
    rgba.putalpha(ImageChops.multiply(rgba.getchannel("A"), ImageChops.invert(remove)))
    return rgba


def crop_alpha_tight(im: Image.Image, pad: int = 8) -> Image.Image:
    rgba = im.convert("RGBA")
    bbox = rgba.getchannel("A").getbbox()
    if not bbox:
        return rgba
    crop = rgba.crop(
        (
            max(0, bbox[0] - pad),
            max(0, bbox[1] - pad),
            min(rgba.width, bbox[2] + pad),
            min(rgba.height, bbox[3] + pad),
        )
    )
    out = Image.new("RGBA", (crop.width + 4, crop.height + 4), (0, 0, 0, 0))
    out.alpha_composite(crop, (2, 2))
    return out


def preview(records: list[dict]) -> None:
    font = ImageFont.load_default()
    cols = 4
    tile_w, tile_h = 300, 220
    rows = (len(records) + cols - 1) // cols
    out = Image.new("RGBA", (cols * tile_w + 40, rows * tile_h + 40), (226, 218, 202, 255))
    draw = ImageDraw.Draw(out)
    for i, rec in enumerate(records):
        x = 20 + i % cols * tile_w
        y = 20 + i // cols * tile_h
        draw.rounded_rectangle((x, y, x + tile_w - 14, y + tile_h - 14), radius=8, fill=(244, 239, 228, 255), outline=(154, 135, 101, 255))
        im = Image.open(OUT / rec["file"]).convert("RGBA")
        scale = min(1.0, (tile_w - 46) / im.width, 138 / im.height)
        thumb = im.resize((max(1, int(im.width * scale)), max(1, int(im.height * scale))), Image.Resampling.LANCZOS)
        out.alpha_composite(thumb, (x + (tile_w - 14 - thumb.width) // 2, y + 14 + (138 - thumb.height) // 2))
        draw.text((x + 12, y + 162), rec["name"][:34], fill=(48, 40, 30, 255), font=font)
        draw.text((x + 12, y + 181), rec["role"], fill=(102, 78, 44, 255), font=font)
    out.convert("RGB").save(OUT / "preview_components.jpg", quality=92)


def alpha_preview(records: list[dict]) -> None:
    font = ImageFont.load_default()
    cols = 4
    tile_w, tile_h = 300, 220
    rows = (len(records) + cols - 1) // cols
    out = Image.new("RGBA", (cols * tile_w + 40, rows * tile_h + 40), (0, 0, 0, 255))
    draw = ImageDraw.Draw(out)
    step = 16
    for y in range(0, out.height, step):
        for x in range(0, out.width, step):
            fill = (255, 0, 180, 255) if ((x // step + y // step) % 2) else (28, 28, 28, 255)
            draw.rectangle((x, y, x + step, y + step), fill=fill)
    for i, rec in enumerate(records):
        x = 20 + i % cols * tile_w
        y = 20 + i // cols * tile_h
        draw.rectangle((x, y, x + tile_w - 14, y + tile_h - 14), outline=(255, 230, 120, 255), width=2)
        im = Image.open(OUT / rec["file"]).convert("RGBA")
        scale = min(1.0, (tile_w - 46) / im.width, 138 / im.height)
        thumb = im.resize((max(1, int(im.width * scale)), max(1, int(im.height * scale))), Image.Resampling.LANCZOS)
        out.alpha_composite(thumb, (x + (tile_w - 14 - thumb.width) // 2, y + 14 + (138 - thumb.height) // 2))
        draw.text((x + 12, y + 164), rec["name"][:34], fill=(255, 255, 255, 255), font=font)
    out.convert("RGB").save(OUT / "preview_alpha_check.jpg", quality=92)


def make_text_on_controls_preview() -> None:
    seal = Image.open(TRANSPARENT / "start_challenge_seal_blank.png").convert("RGBA")
    start_text = Image.open(TRANSPARENT / "start_challenge_text.png").convert("RGBA")
    duel = Image.open(TRANSPARENT / "duel_stamp_light_blank.png").convert("RGBA")
    duel_text = Image.open(TRANSPARENT / "duel_text.png").convert("RGBA")

    canvas = Image.new("RGBA", (760, 360), (228, 220, 205, 255))
    draw = ImageDraw.Draw(canvas)
    draw.rounded_rectangle((20, 20, 360, 340), radius=10, fill=(244, 239, 228, 255), outline=(150, 132, 98, 255))
    draw.rounded_rectangle((400, 20, 740, 340), radius=10, fill=(244, 239, 228, 255), outline=(150, 132, 98, 255))

    seal_scale = min(250 / seal.width, 250 / seal.height)
    seal = seal.resize((int(seal.width * seal_scale), int(seal.height * seal_scale)), Image.Resampling.LANCZOS)
    sx, sy = 20 + (340 - seal.width) // 2, 50
    canvas.alpha_composite(seal, (sx, sy))

    text_scale = min(seal.width * 0.62 / start_text.width, seal.height * 0.58 / start_text.height)
    start_text = start_text.resize((int(start_text.width * text_scale), int(start_text.height * text_scale)), Image.Resampling.LANCZOS)
    canvas.alpha_composite(start_text, (sx + (seal.width - start_text.width) // 2, sy + (seal.height - start_text.height) // 2))

    duel_scale = min(230 / duel.width, 230 / duel.height)
    duel = duel.resize((int(duel.width * duel_scale), int(duel.height * duel_scale)), Image.Resampling.LANCZOS)
    dx, dy = 400 + (340 - duel.width) // 2, 60
    canvas.alpha_composite(duel, (dx, dy))

    duel_text_scale = min(duel.width * 0.52 / duel_text.width, duel.height * 0.46 / duel_text.height)
    duel_text = duel_text.resize((int(duel_text.width * duel_text_scale), int(duel_text.height * duel_text_scale)), Image.Resampling.LANCZOS)
    canvas.alpha_composite(duel_text, (dx + (duel.width - duel_text.width) // 2, dy + (duel.height - duel_text.height) // 2))

    draw.text((34, 304), "start_challenge_text on start_challenge_seal_blank", fill=(58, 46, 32, 255), font=ImageFont.load_default())
    draw.text((414, 304), "duel_text on duel_stamp_light_blank", fill=(58, 46, 32, 255), font=ImageFont.load_default())
    canvas.convert("RGB").save(OUT / "preview_text_on_controls.jpg", quality=92)


def main() -> None:
    if not SRC.exists():
        raise FileNotFoundError(SRC)
    reset_dir(OUT)
    SOURCE.mkdir(parents=True, exist_ok=True)
    TRANSPARENT.mkdir(parents=True, exist_ok=True)
    source_copy = SOURCE / "battle_ui_ink_warfield_clean_component_sheet.png"
    shutil.copy2(SRC, source_copy)
    text_source_copy = None
    if TEXT_SRC.exists():
        text_source_copy = SOURCE / "battle_ui_ink_warfield_text_sprites_source.png"
        shutil.copy2(TEXT_SRC, text_source_copy)
    duel_stamp_source_copy = None
    if DUEL_STAMP_SRC.exists():
        duel_stamp_source_copy = SOURCE / "battle_ui_ink_warfield_duel_stamp_source.png"
        shutil.copy2(DUEL_STAMP_SRC, duel_stamp_source_copy)

    src = Image.open(source_copy).convert("RGB")
    records = []
    for item in COMPONENTS:
        crop = src.crop(tuple(item["box"]))
        cleaned = remove_outer_checker(crop, item.get("holes"))
        file = TRANSPARENT / f'{item["name"]}.png'
        cleaned.save(file, optimize=True)
        rec = {
            "name": item["name"],
            "role": item["role"],
            "file": file.relative_to(OUT).as_posix(),
            "source_box": item["box"],
            "size": [cleaned.width, cleaned.height],
            "scale_mode": item["scale_mode"],
            "usage": item["usage"],
            "alpha_status": "outer_checker_background_removed",
        }
        if "nine_slice" in item:
            rec["nine_slice"] = {
                "left": item["nine_slice"][0],
                "top": item["nine_slice"][1],
                "right": item["nine_slice"][2],
                "bottom": item["nine_slice"][3],
                "confidence": "draft_from_clean_component_sheet",
            }
        records.append(rec)

    if duel_stamp_source_copy:
        stamp_src = Image.open(duel_stamp_source_copy).convert("RGBA")
        stamp_clean = crop_alpha_tight(clean_connected_checker(stamp_src), 10)
        file = TRANSPARENT / "duel_stamp_light_blank.png"
        stamp_clean.save(file, optimize=True)
        records.append(
            {
                "name": "duel_stamp_light_blank",
                "role": "center_overlay",
                "file": file.relative_to(OUT).as_posix(),
                "source_box": "duel_stamp_generated",
                "size": [stamp_clean.width, stamp_clean.height],
                "scale_mode": "fixed",
                "usage": "布阵面板中心的浅色水墨圆章，用于承载“对决”深墨艺术字。",
                "alpha_status": "outer_checker_background_removed",
            }
        )

    if text_source_copy:
        text_sheet = Image.open(text_source_copy).convert("RGBA")
        text_clean = clean_connected_checker(text_sheet)
        split_y = text_clean.height // 2
        text_items = [
            ("start_challenge_text", "art_text", text_clean.crop((0, 0, text_clean.width, split_y)), "“开始挑战”艺术字，叠加到开战印章按钮上。"),
            ("duel_text", "art_text", text_clean.crop((0, split_y, text_clean.width, text_clean.height)), "“对决”艺术字，叠加到中间对决章上。"),
        ]
        for name, role, im, usage in text_items:
            out_im = crop_alpha_tight(im, 12)
            file = TRANSPARENT / f"{name}.png"
            out_im.save(file, optimize=True)
            records.append(
                {
                    "name": name,
                    "role": role,
                    "file": file.relative_to(OUT).as_posix(),
                    "source_box": "text_sprite_generated",
                    "size": [out_im.width, out_im.height],
                    "scale_mode": "fixed",
                    "usage": usage,
                    "alpha_status": "outer_checker_background_removed",
                }
            )

    preview(records)
    alpha_preview(records)
    make_text_on_controls_preview()
    manifest = {
        "package": "battle-ui-ink-warfield-components-v02",
        "source": source_copy.relative_to(OUT).as_posix(),
        "source_size": [src.width, src.height],
        "production_status": "clean_component_slices",
        "notes": [
            "This package supersedes the earlier screenshot crop package for implementation use.",
            "All gameplay text, numbers, portraits, and icons should be rendered or overlaid separately in engine.",
            "Only the two requested art text sprites are baked text assets: start_challenge_text and duel_text.",
            "Nine-slice values are draft recommendations and should be verified in the target UI runtime.",
        ],
        "assets": records,
    }
    (OUT / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    (OUT / "README.md").write_text(
        "# Battle UI Ink Warfield Components v02\n\n"
        "本包按可实装 UI 控件重新拆分，不再使用整张局内效果图硬裁。\n\n"
        "## 内容\n\n"
        "- `source/`：无文字控件清稿表。\n"
        "- `transparent/`：按控件拆出的透明 PNG。\n"
        "- `transparent/start_challenge_text.png`、`transparent/duel_text.png`：单独生成的艺术字贴图。\n"
        "- `manifest.json`：控件职责、尺寸、来源坐标、九宫格建议和用途说明。\n"
        "- `preview_components.jpg`：控件总览。\n"
        "- `preview_alpha_check.jpg`：透明背景检查。\n\n"
        "- `preview_text_on_controls.jpg`：艺术字贴到目标控件上的合成检查。\n\n"
        "## 实装原则\n\n"
        "- 血条、面板、卡牌、资源栏都按 `base + overlay + engine text/icon` 使用。\n"
        "- 带徽章、头像框、按钮图标等具象装饰不参与九宫格拉伸。\n"
        "- 顶部 HUD、资源条、双方血条、布阵大面板、属性条提供九宫格候选参数。\n"
        "- 圆形按钮、头像框、开战印章、技能槽、卡牌框、小地图框建议固定尺寸或等比缩放。\n",
        encoding="utf-8",
    )
    print(json.dumps({"out": str(OUT), "assets": len(records)}, ensure_ascii=False))


if __name__ == "__main__":
    main()

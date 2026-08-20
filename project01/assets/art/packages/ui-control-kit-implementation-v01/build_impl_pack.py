from __future__ import annotations

import json
import shutil
from collections import deque
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont


ROOT = Path(__file__).resolve().parent
SOURCE_ROOT = ROOT.parent / "ui-control-kit-clean-layer-sample-v01"


@dataclass(frozen=True)
class Style:
    key: str
    name: str
    source: str
    tint: str


STYLES = [
    Style("01_porcelain_map", "清瓷地图框", "porcelain_map_clean_layers_v02_recommended.png", "porcelain"),
    Style("02_cinnabar_seal", "朱印令牌框", "cinnabar_seal_clean_layers_v01.png", "red"),
    Style("03_ink_brush", "墨刷浮层框", "ink_brush_clean_layers_v01.png", "ink"),
    Style("04_bronze_armor", "玄铁铜铆框", "bronze_armor_clean_layers_v01.png", "metal"),
    Style("05_dossier_paper", "军务档案夹", "dossier_paper_clean_layers_v01.png", "paper"),
    Style("06_jade_bi", "青玉璧环框", "jade_bi_clean_layers_v01.png", "jade"),
]


BASE_KEYS = [
    "window",
    "baseplate",
    "headbar",
    "button_rect_normal",
    "button_rect_disabled",
    "button_circle_normal",
    "button_circle_disabled",
    "button_tab_normal",
    "button_tab_disabled",
]

BASE_SLOTS = {
    "window": (0, 70, 500, 410),
    "baseplate": (485, 70, 775, 410),
    "headbar": (760, 70, 1245, 270),
    "button_rect_normal": (760, 260, 960, 405),
    "button_rect_disabled": (930, 260, 1140, 405),
    "button_circle_normal": (1120, 240, 1210, 395),
    "button_circle_disabled": (1190, 240, 1305, 395),
    "button_tab_normal": (1265, 115, 1536, 280),
    "button_tab_disabled": (1265, 250, 1536, 410),
}

STYLE_SLOT_OVERRIDES = {
    "05_dossier_paper": {
        "button_tab_normal": (1245, 250, 1405, 410),
        "button_tab_disabled": (1375, 250, 1536, 410),
    },
    "06_jade_bi": {
        "button_tab_normal": (1245, 250, 1405, 410),
        "button_tab_disabled": (1375, 250, 1536, 410),
    },
}

MANUAL_BASE_BOXES = {
    "01_porcelain_map": {
        "window": (17, 95, 490, 367),
        "baseplate": (494, 157, 757, 367),
        "headbar": (773, 177, 1158, 255),
        "button_rect_normal": (773, 292, 930, 365),
        "button_rect_disabled": (950, 292, 1110, 365),
        "button_circle_normal": (1135, 280, 1198, 363),
        "button_circle_disabled": (1214, 280, 1278, 363),
        "button_tab_normal": (1280, 169, 1516, 263),
        "button_tab_disabled": (1290, 286, 1515, 366),
    },
    "02_cinnabar_seal": {
        "window": (17, 95, 490, 373),
        "baseplate": (491, 157, 758, 373),
        "headbar": (771, 177, 1159, 256),
        "button_rect_normal": (771, 292, 930, 368),
        "button_rect_disabled": (950, 292, 1110, 368),
        "button_circle_normal": (1135, 280, 1198, 368),
        "button_circle_disabled": (1214, 280, 1278, 368),
        "button_tab_normal": (1278, 171, 1512, 263),
        "button_tab_disabled": (1290, 286, 1512, 369),
    },
    "03_ink_brush": {
        "window": (31, 102, 508, 392),
        "baseplate": (560, 113, 783, 392),
        "headbar": (805, 157, 1175, 278),
        "button_rect_normal": (805, 285, 965, 391),
        "button_rect_disabled": (975, 285, 1124, 383),
        "button_circle_normal": (1130, 260, 1208, 384),
        "button_circle_disabled": (1210, 260, 1284, 384),
        "button_tab_normal": (1280, 177, 1503, 279),
        "button_tab_disabled": (1292, 295, 1508, 382),
    },
    "04_bronze_armor": {
        "window": (31, 92, 508, 411),
        "baseplate": (565, 92, 783, 411),
        "headbar": (825, 126, 1205, 278),
        "button_rect_normal": (825, 285, 970, 398),
        "button_rect_disabled": (980, 285, 1124, 383),
        "button_circle_normal": (1130, 260, 1208, 383),
        "button_circle_disabled": (1210, 260, 1284, 383),
        "button_tab_normal": (1272, 177, 1494, 277),
        "button_tab_disabled": (1290, 295, 1497, 383),
    },
    "05_dossier_paper": {
        "window": (35, 75, 558, 408),
        "baseplate": (585, 75, 800, 408),
        "headbar": (825, 136, 1197, 278),
        "button_rect_normal": (808, 292, 935, 368),
        "button_rect_disabled": (948, 292, 1072, 368),
        "button_circle_normal": (1074, 282, 1148, 370),
        "button_circle_disabled": (1156, 282, 1230, 370),
        "button_tab_normal": (1272, 286, 1392, 380),
        "button_tab_disabled": (1392, 286, 1504, 380),
    },
    "06_jade_bi": {
        "window": (38, 77, 558, 408),
        "baseplate": (585, 77, 800, 409),
        "headbar": (825, 139, 1197, 278),
        "button_rect_normal": (808, 292, 935, 370),
        "button_rect_disabled": (948, 292, 1072, 370),
        "button_circle_normal": (1074, 282, 1148, 372),
        "button_circle_disabled": (1156, 282, 1230, 372),
        "button_tab_normal": (1272, 286, 1392, 382),
        "button_tab_disabled": (1392, 286, 1504, 382),
    },
}


NINE = {
    "window": {"left": 88, "top": 58, "right": 88, "bottom": 58},
    "baseplate": {"left": 64, "top": 48, "right": 64, "bottom": 48},
    "headbar": {"left": 86, "top": 22, "right": 86, "bottom": 22},
    "button_rect_normal": {"left": 42, "top": 18, "right": 42, "bottom": 18},
    "button_rect_disabled": {"left": 42, "top": 18, "right": 42, "bottom": 18},
    "button_tab_normal": {"left": 52, "top": 24, "right": 52, "bottom": 24},
    "button_tab_disabled": {"left": 52, "top": 24, "right": 52, "bottom": 24},
}


def object_mask(img: Image.Image) -> np.ndarray:
    arr = np.asarray(img.convert("RGB"), dtype=np.int16)
    mn = arr.min(axis=2)
    mx = arr.max(axis=2)
    sat = mx - mn
    # The clean sheets use a very light checkerboard. This catches UI material,
    # edges, shadows, and low-saturation paper without turning the whole board on.
    mask = (mn < 232) | (sat > 18)
    return mask


def components(mask: np.ndarray, min_area: int = 80) -> list[tuple[int, int, int, int, int]]:
    h, w = mask.shape
    seen = np.zeros_like(mask, dtype=bool)
    out: list[tuple[int, int, int, int, int]] = []
    for y in range(h):
        xs = np.where(mask[y] & ~seen[y])[0]
        for x0 in xs:
            if seen[y, x0] or not mask[y, x0]:
                continue
            q = deque([(x0, y)])
            seen[y, x0] = True
            x1 = x2 = x0
            y1 = y2 = y
            area = 0
            while q:
                x, yy = q.popleft()
                area += 1
                x1 = min(x1, x)
                x2 = max(x2, x)
                y1 = min(y1, yy)
                y2 = max(y2, yy)
                for nx, ny in ((x + 1, yy), (x - 1, yy), (x, yy + 1), (x, yy - 1)):
                    if 0 <= nx < w and 0 <= ny < h and mask[ny, nx] and not seen[ny, nx]:
                        seen[ny, nx] = True
                        q.append((nx, ny))
            if area >= min_area:
                out.append((x1, y1, x2 + 1, y2 + 1, area))
    return out


def merge_boxes(boxes: list[tuple[int, int, int, int, int]], gap: int = 18) -> list[tuple[int, int, int, int, int]]:
    merged: list[tuple[int, int, int, int, int]] = []
    for box in sorted(boxes, key=lambda b: (b[1], b[0])):
        x1, y1, x2, y2, area = box
        placed = False
        for i, old in enumerate(merged):
            ox1, oy1, ox2, oy2, oa = old
            if x1 <= ox2 + gap and x2 >= ox1 - gap and y1 <= oy2 + gap and y2 >= oy1 - gap:
                merged[i] = (min(x1, ox1), min(y1, oy1), max(x2, ox2), max(y2, oy2), area + oa)
                placed = True
                break
        if not placed:
            merged.append(box)
    if len(merged) == len(boxes):
        return merged
    return merge_boxes(merged, gap=gap)


def pad_box(box: tuple[int, int, int, int, int], w: int, h: int, pad: int = 10) -> tuple[int, int, int, int]:
    x1, y1, x2, y2, _ = box
    return max(0, x1 - pad), max(0, y1 - pad), min(w, x2 + pad), min(h, y2 + pad)


def detect_row_objects(img: Image.Image, y1: int, y2: int, min_area: int = 220) -> list[tuple[int, int, int, int]]:
    crop = img.crop((0, y1, img.width, y2))
    mask = object_mask(crop)
    # Light dilation connects shadows and fine rims into one object.
    pil_mask = Image.fromarray((mask * 255).astype("uint8")).filter(ImageFilter.MaxFilter(7))
    comps = components(np.asarray(pil_mask) > 0, min_area=min_area)
    merged = merge_boxes(comps, gap=18)
    boxes = [pad_box((x1, yy1 + y1, x2, yy2 + y1, area), img.width, img.height, 8) for x1, yy1, x2, yy2, area in merged]
    boxes = [b for b in boxes if (b[2] - b[0]) > 20 and (b[3] - b[1]) > 20]
    return sorted((tuple(int(v) for v in b) for b in boxes), key=lambda b: b[0])


def content_box_in_slot(img: Image.Image, slot: tuple[int, int, int, int], pad: int = 8) -> tuple[int, int, int, int]:
    x1, y1, x2, y2 = slot
    crop = img.crop(slot)
    mask = object_mask(crop)
    pil_mask = Image.fromarray((mask * 255).astype("uint8")).filter(ImageFilter.MaxFilter(3))
    comps = components(np.asarray(pil_mask) > 0, min_area=120)
    if not comps:
        raise RuntimeError(f"empty slot: {slot}")
    bx1 = min(c[0] for c in comps)
    by1 = min(c[1] for c in comps)
    bx2 = max(c[2] for c in comps)
    by2 = max(c[3] for c in comps)
    return (
        max(0, int(x1 + bx1 - pad)),
        max(0, int(y1 + by1 - pad)),
        min(img.width, int(x1 + bx2 + pad)),
        min(img.height, int(y1 + by2 + pad)),
    )


def tighten_box(img: Image.Image, box: tuple[int, int, int, int], pad: int = 4) -> tuple[int, int, int, int]:
    x1, y1, x2, y2 = box
    crop = img.crop(box)
    mask = object_mask(crop)
    pil_mask = Image.fromarray((mask * 255).astype("uint8")).filter(ImageFilter.MaxFilter(3))
    comps = components(np.asarray(pil_mask) > 0, min_area=80)
    if not comps:
        return box
    bx1 = min(c[0] for c in comps)
    by1 = min(c[1] for c in comps)
    bx2 = max(c[2] for c in comps)
    by2 = max(c[3] for c in comps)
    return (
        max(0, int(x1 + bx1 - pad)),
        max(0, int(y1 + by1 - pad)),
        min(img.width, int(x1 + bx2 + pad)),
        min(img.height, int(y1 + by2 + pad)),
    )


def shape_alpha(size: tuple[int, int], key: str, style: Style) -> Image.Image:
    w, h = size
    mask = Image.new("L", size, 0)
    d = ImageDraw.Draw(mask)
    if "circle" in key:
        d.ellipse((3, 3, w - 4, h - 4), fill=255)
    elif "tab" in key:
        if style.tint in {"paper", "jade", "porcelain"}:
            d.rounded_rectangle((2, 4, w - 3, h - 3), radius=8, fill=255)
            d.rectangle((18, 2, w - 19, h - 3), fill=255)
        else:
            cut = max(14, min(28, h // 2))
            d.polygon([(cut, 2), (w - cut, 2), (w - 3, h // 2), (w - cut, h - 3), (cut, h - 3), (2, h // 2)], fill=255)
    else:
        if style.tint in {"red", "ink", "metal"}:
            cut = max(10, min(34, min(w, h) // 5))
            d.polygon([(cut, 2), (w - cut, 2), (w - 3, cut), (w - 3, h - cut), (w - cut, h - 3), (cut, h - 3), (2, h - cut), (2, cut)], fill=255)
        else:
            d.rounded_rectangle((2, 2, w - 3, h - 3), radius=8, fill=255)
    return ImageChops.lighter(mask.filter(ImageFilter.GaussianBlur(2)), mask.filter(ImageFilter.MaxFilter(3)))


def with_base_alpha(img: Image.Image, key: str, style: Style) -> Image.Image:
    out = img.convert("RGBA")
    alpha = filled_content_alpha(img)
    # If a very pale object leaks during flood-fill, fall back to the conservative
    # geometric mask for that control family.
    if alpha.getbbox() is None or (alpha.getbbox()[2] - alpha.getbbox()[0]) < img.width * 0.35:
        alpha = shape_alpha(out.size, key, style)
    out.putalpha(alpha)
    return remove_edge_white_fringe(out)


def filled_content_alpha(img: Image.Image) -> Image.Image:
    mask = object_mask(img)
    hard = Image.fromarray((mask * 255).astype("uint8"), "L")
    hard = hard.filter(ImageFilter.MaxFilter(5))
    solid = np.asarray(hard) > 0
    h, w = solid.shape

    visited = np.zeros_like(solid, dtype=bool)
    q = deque()
    for x in range(w):
        if not solid[0, x]:
            q.append((x, 0))
            visited[0, x] = True
        if not solid[h - 1, x]:
            q.append((x, h - 1))
            visited[h - 1, x] = True
    for y in range(h):
        if not solid[y, 0]:
            q.append((0, y))
            visited[y, 0] = True
        if not solid[y, w - 1]:
            q.append((w - 1, y))
            visited[y, w - 1] = True

    while q:
        x, y = q.popleft()
        for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if 0 <= nx < w and 0 <= ny < h and not solid[ny, nx] and not visited[ny, nx]:
                visited[ny, nx] = True
                q.append((nx, ny))

    filled = solid | ~visited
    alpha = Image.fromarray((filled * 255).astype("uint8"), "L")
    alpha = alpha.filter(ImageFilter.MaxFilter(3)).filter(ImageFilter.GaussianBlur(0.8))
    return alpha


def with_overlay_alpha(img: Image.Image) -> Image.Image:
    rgb = img.convert("RGB")
    arr = np.asarray(rgb, dtype=np.int16)
    h, w, _ = arr.shape

    border = np.concatenate([arr[0, :, :], arr[-1, :, :], arr[:, 0, :], arr[:, -1, :]], axis=0)
    bmn = border.min(axis=1)
    bmx = border.max(axis=1)
    bg_candidates = border[(border.mean(axis=1) > 216) & ((bmx - bmn) < 28)]
    if len(bg_candidates) < 8:
        bg_candidates = border
    # The source sheets use a pale checkerboard, so keep a light and a dark
    # background sample and make pixels transparent when they are close to either.
    brightness = bg_candidates.mean(axis=1)
    light_bg = np.median(bg_candidates[brightness >= np.median(brightness)], axis=0)
    dark_bg = np.median(bg_candidates[brightness < np.median(brightness)], axis=0)

    dist_light = np.sqrt(((arr - light_bg) ** 2).sum(axis=2))
    dist_dark = np.sqrt(((arr - dark_bg) ** 2).sum(axis=2))
    dist = np.minimum(dist_light, dist_dark)
    mn = arr.min(axis=2)
    mx = arr.max(axis=2)
    sat = mx - mn

    alpha_arr = np.clip((dist - 10) * 7, 0, 255)
    strong_object = (mn < 205) | (sat > 34)
    alpha_arr[strong_object] = np.maximum(alpha_arr[strong_object], 230)
    alpha_arr = alpha_arr.astype("uint8")
    alpha = Image.fromarray(alpha_arr, "L").filter(ImageFilter.MaxFilter(3)).filter(ImageFilter.GaussianBlur(0.6))
    out = img.convert("RGBA")
    out.putalpha(alpha)
    out = remove_edge_white_fringe(out)
    return trim_transparent(out, pad=2)


def split_overlay_parts(img: Image.Image, min_area: int = 18) -> list[Image.Image]:
    rgba = img.convert("RGBA")
    alpha = np.asarray(rgba.getchannel("A"))
    mask = alpha > 24
    comps = components(mask, min_area=min_area)
    if not comps:
        return [rgba]

    # Components that are very close are often pieces of one ornament, such as
    # separated shine strokes on a badge. Distant pieces should become separate
    # overlay assets.
    merged = merge_boxes(comps, gap=5)
    parts: list[Image.Image] = []
    for box in sorted(merged, key=lambda b: (b[1], b[0])):
        x1, y1, x2, y2, area = box
        if area < min_area:
            continue
        x1 = max(0, int(x1) - 2)
        y1 = max(0, int(y1) - 2)
        x2 = min(rgba.width, int(x2) + 2)
        y2 = min(rgba.height, int(y2) + 2)
        part = trim_transparent(rgba.crop((x1, y1, x2, y2)), pad=2)
        if part.width >= 4 and part.height >= 4:
            parts.append(part)
    return parts or [rgba]


def remove_edge_white_fringe(img: Image.Image) -> Image.Image:
    rgba = img.convert("RGBA")
    arr = np.asarray(rgba).copy()
    rgb = arr[:, :, :3].astype(np.int16)
    alpha = arr[:, :, 3]
    mn = rgb.min(axis=2)
    mx = rgb.max(axis=2)
    sat = mx - mn
    light_unsat = (mn > 214) & (sat < 34) & (alpha > 0)
    weak_alpha = (alpha > 0) & (alpha < 86)
    passable = light_unsat | weak_alpha | (alpha == 0)

    h, w = alpha.shape
    visited = np.zeros_like(passable, dtype=bool)
    q = deque()
    for x in range(w):
        if passable[0, x]:
            q.append((x, 0))
            visited[0, x] = True
        if passable[h - 1, x]:
            q.append((x, h - 1))
            visited[h - 1, x] = True
    for y in range(h):
        if passable[y, 0]:
            q.append((0, y))
            visited[y, 0] = True
        if passable[y, w - 1]:
            q.append((w - 1, y))
            visited[y, w - 1] = True

    while q:
        x, y = q.popleft()
        for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if 0 <= nx < w and 0 <= ny < h and passable[ny, nx] and not visited[ny, nx]:
                visited[ny, nx] = True
                q.append((nx, ny))

    arr[visited, 3] = 0
    return Image.fromarray(arr, "RGBA")


def repair_generated_tab(img: Image.Image, style: Style, key: str) -> Image.Image:
    return img


def tint_disabled_tab_to_normal(img: Image.Image, style: Style) -> Image.Image:
    rgba = img.convert("RGBA")
    arr = np.asarray(rgba).copy()
    rgb = arr[:, :, :3].astype(np.float32)
    lum = (rgb[:, :, 0] * 0.299 + rgb[:, :, 1] * 0.587 + rgb[:, :, 2] * 0.114) / 255.0
    if style.key == "05_dossier_paper":
        shadow = np.array([118, 102, 78], dtype=np.float32)
        mid = np.array([206, 184, 145], dtype=np.float32)
        high = np.array([244, 233, 207], dtype=np.float32)
    else:
        shadow = np.array([104, 135, 126], dtype=np.float32)
        mid = np.array([183, 213, 196], dtype=np.float32)
        high = np.array([231, 244, 225], dtype=np.float32)
    low_mix = np.clip(lum * 2.0, 0, 1)[:, :, None]
    high_mix = np.clip((lum - 0.5) * 2.0, 0, 1)[:, :, None]
    color = shadow * (1 - low_mix) + mid * low_mix
    color = color * (1 - high_mix) + high * high_mix
    arr[:, :, :3] = np.clip(color, 0, 255).astype(np.uint8)
    return Image.fromarray(arr, "RGBA")


def trim_transparent(img: Image.Image, pad: int = 2) -> Image.Image:
    bbox = img.getchannel("A").getbbox()
    if bbox is None:
        return img
    x1, y1, x2, y2 = bbox
    x1 = max(0, x1 - pad)
    y1 = max(0, y1 - pad)
    x2 = min(img.width, x2 + pad)
    y2 = min(img.height, y2 + pad)
    return img.crop((x1, y1, x2, y2))


def add_transparent_padding(img: Image.Image, pad: int = 2) -> Image.Image:
    if pad <= 0:
        return img
    out = Image.new("RGBA", (img.width + pad * 2, img.height + pad * 2), (0, 0, 0, 0))
    out.alpha_composite(img.convert("RGBA"), (pad, pad))
    return out


def save_asset(img: Image.Image, path: Path) -> dict:
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path)
    return {"path": path.relative_to(ROOT).as_posix(), "size": list(img.size)}


def clamp_nine(size: tuple[int, int], nine: dict | None) -> dict | None:
    if nine is None:
        return None
    w, h = size
    max_x = max(4, (w - 4) // 2)
    max_y = max(4, (h - 4) // 2)
    return {
        "left": min(nine["left"], max_x),
        "top": min(nine["top"], max_y),
        "right": min(nine["right"], max_x),
        "bottom": min(nine["bottom"], max_y),
    }


def make_previews(manifest: dict) -> None:
    previews = []
    for style_key, style_data in manifest["sets"].items():
        for key, data in style_data["controls"].items():
            previews.append((f"{style_key}/{key}", ROOT / data["base"]["path"]))
        for ov in style_data["overlays"]:
            previews.append((f"{style_key}/overlay/{ov['name']}", ROOT / ov["path"]))

    cell_w, cell_h = 260, 132
    cols = 4
    rows = (len(previews) + cols - 1) // cols
    sheet = Image.new("RGB", (cell_w * cols, cell_h * rows), (232, 226, 216))
    d = ImageDraw.Draw(sheet)
    font = ImageFont.load_default()
    for i, (label, path) in enumerate(previews):
        x = (i % cols) * cell_w
        y = (i // cols) * cell_h
        d.rectangle((x, y, x + cell_w - 1, y + cell_h - 1), outline=(180, 170, 150))
        img = Image.open(path).convert("RGBA")
        scale = min((cell_w - 28) / img.width, (cell_h - 42) / img.height, 1)
        pv = img.resize((max(1, int(img.width * scale)), max(1, int(img.height * scale))), Image.Resampling.LANCZOS)
        bg = Image.new("RGBA", pv.size, (246, 244, 238, 255))
        bg.alpha_composite(pv)
        sheet.paste(bg.convert("RGB"), (x + (cell_w - pv.width) // 2, y + 30 + (cell_h - 42 - pv.height) // 2))
        d.text((x + 8, y + 8), label[:34], fill=(35, 31, 26), font=font)
    sheet.save(ROOT / "preview_assets.png")


def make_stretch_preview(manifest: dict) -> None:
    rows = []
    for style_key, style_data in manifest["sets"].items():
        for key in ("window", "headbar", "button_rect_normal", "button_tab_normal"):
            data = style_data["controls"][key]
            if data["scale_mode"] != "nine_slice":
                continue
            src = Image.open(ROOT / data["base"]["path"]).convert("RGBA")
            rows.append((f"{style_key}/{key}", src, data["nine_slice"]))

    cell_w, cell_h = 300, 130
    sheet = Image.new("RGB", (cell_w * 3, cell_h * len(rows)), (232, 226, 216))
    d = ImageDraw.Draw(sheet)
    font = ImageFont.load_default()
    for r, (label, src, nine) in enumerate(rows):
        sizes = [src.size, (int(src.width * 1.45), src.height), (int(src.width * 2.1), int(src.height * 1.25))]
        for c, size in enumerate(sizes):
            x = c * cell_w
            y = r * cell_h
            d.rectangle((x, y, x + cell_w - 1, y + cell_h - 1), outline=(180, 170, 150))
            if c == 0:
                d.text((x + 8, y + 8), label[:34], fill=(35, 31, 26), font=font)
            scaled = nine_slice(src, size, nine)
            bg = Image.new("RGBA", scaled.size, (246, 244, 238, 255))
            bg.alpha_composite(scaled)
            pv = bg.convert("RGB")
            if pv.width > cell_w - 24 or pv.height > cell_h - 36:
                s = min((cell_w - 24) / pv.width, (cell_h - 36) / pv.height)
                pv = pv.resize((int(pv.width * s), int(pv.height * s)), Image.Resampling.LANCZOS)
            sheet.paste(pv, (x + (cell_w - pv.width) // 2, y + 28 + (cell_h - 38 - pv.height) // 2))
    sheet.save(ROOT / "preview_9slice_stretch.png")


def nine_slice(img: Image.Image, size: tuple[int, int], n: dict) -> Image.Image:
    l, t, r, b = n["left"], n["top"], n["right"], n["bottom"]
    w, h = img.size
    nw, nh = size
    out = Image.new("RGBA", size, (0, 0, 0, 0))
    xs = [(0, l, 0, l), (l, w - r, l, nw - r), (w - r, w, nw - r, nw)]
    ys = [(0, t, 0, t), (t, h - b, t, nh - b), (h - b, h, nh - b, nh)]
    for sx1, sx2, dx1, dx2 in xs:
        for sy1, sy2, dy1, dy2 in ys:
            tile = img.crop((sx1, sy1, sx2, sy2))
            target = (max(1, dx2 - dx1), max(1, dy2 - dy1))
            if tile.size != target:
                tile = tile.resize(target, Image.Resampling.LANCZOS)
            out.alpha_composite(tile, (dx1, dy1))
    return out


def build_style(style: Style) -> dict:
    src_path = SOURCE_ROOT / style.source
    img = Image.open(src_path).convert("RGB")
    style_dir = ROOT / style.key
    if style_dir.exists():
        shutil.rmtree(style_dir)
    (style_dir / "source").mkdir(parents=True, exist_ok=True)
    img.save(style_dir / "source" / style.source)

    controls = {}
    for key in BASE_KEYS:
        box = MANUAL_BASE_BOXES.get(style.key, {}).get(key)
        source_key = key
        repaired_note = None
        if style.key in {"05_dossier_paper", "06_jade_bi"} and key == "button_tab_normal":
            source_key = "button_tab_disabled"
            box = MANUAL_BASE_BOXES[style.key][source_key]
            repaired_note = "normal tab rebuilt from complete disabled tab silhouette and re-tinted for implementation"
        if box is None:
            slot = STYLE_SLOT_OVERRIDES.get(style.key, {}).get(key, BASE_SLOTS[key])
            box = content_box_in_slot(img, slot)
        box = tighten_box(img, box, pad=3)
        crop = img.crop(box)
        rgba = with_base_alpha(crop, key, style)
        if repaired_note:
            rgba = tint_disabled_tab_to_normal(rgba, style)
        rgba = trim_transparent(rgba, pad=1)
        rgba = add_transparent_padding(rgba, pad=2)
        out_name = "base_9slice.png" if key in NINE else "base_fixed.png"
        rec = save_asset(rgba, style_dir / key / out_name)
        nine = clamp_nine(rgba.size, NINE.get(key))
        controls[key] = {
            "source_box": list(box),
            "base": rec,
            "scale_mode": "nine_slice" if key in NINE else "fixed_uniform",
            "nine_slice": nine,
        }
        if repaired_note:
            controls[key]["repair_note"] = repaired_note
            controls[key]["source_control"] = source_key

    overlay_boxes = detect_row_objects(img, 420, 650, min_area=160)
    overlays = []
    overlay_index = 1
    for parent_i, box in enumerate(overlay_boxes, 1):
        crop = img.crop(box)
        rgba = with_overlay_alpha(crop)
        parts = split_overlay_parts(rgba)
        for part_i, part in enumerate(parts, 1):
            name = f"overlay_{overlay_index:03d}"
            rec = save_asset(part, style_dir / "overlays" / f"{name}.png")
            overlays.append(
                {
                    "name": name,
                    "source_box": list(box),
                    "source_overlay_group": f"overlay_group_{parent_i:02d}",
                    "group_part_index": part_i,
                    **rec,
                }
            )
            overlay_index += 1

    return {
        "display_name": style.name,
        "source_sheet": f"{style.key}/source/{style.source}",
        "controls": controls,
        "overlays": overlays,
        "notes": "base controls are intended for 9-slice/fixed use; overlays are fixed-position decorative pieces.",
    }


def main() -> None:
    manifest = {
        "name": "三国项目 UI 控件可实装资源包 v01",
        "status": "implementation draft from approved clean layer sheets",
        "method": "清稿第一排切 base，第二排切 overlay；base 使用 shape alpha，overlay 使用浅背景遮罩透明化。",
        "sets": {},
    }
    for style in STYLES:
        manifest["sets"][style.key] = build_style(style)

    (ROOT / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    make_previews(manifest)
    make_stretch_preview(manifest)


if __name__ == "__main__":
    main()

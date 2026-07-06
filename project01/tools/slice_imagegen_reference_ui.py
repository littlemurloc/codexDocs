from __future__ import annotations

import json
from collections import deque
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "assets" / "ui" / "export" / "basic-ui-kits-sanguo-v01" / "extracted-controls-v12-imagegen-reference-redraw"
SRC = OUT / "source_reference_redraw_no_text.png"
PNG = OUT / "transparent"


BOXES = [
    ("button_primary_blank", (34, 52, 302, 162), [38, 28, 38, 28]),
    ("button_secondary_blank", (38, 205, 284, 300), [38, 28, 38, 28]),
    ("button_disabled_blank", (32, 374, 292, 470), [38, 24, 38, 24]),
    ("icon_button_plus", (332, 62, 426, 154), None),
    ("icon_button_minus", (448, 62, 542, 154), None),
    ("icon_button_question", (540, 48, 670, 170), None),
    ("icon_button_gear", (660, 50, 800, 166), None),
    ("large_window_frame_blank", (300, 178, 708, 542), [52, 58, 52, 52]),
    ("modal_popup_frame_blank", (716, 178, 1005, 542), [44, 58, 44, 52]),
    ("title_bar_blank", (35, 575, 506, 650), [54, 24, 54, 24]),
    ("tabs_strip_blank", (528, 590, 1002, 650), [42, 18, 42, 18]),
    ("list_row_blank", (36, 688, 500, 792), [112, 28, 46, 28]),
    ("input_box_blank", (532, 698, 1000, 780), [44, 24, 44, 24]),
    ("checkbox_empty", (48, 840, 88, 884), None),
    ("checkbox_checked", (48, 890, 90, 936), None),
    ("toggle_off", (228, 828, 384, 892), [32, 14, 32, 14]),
    ("toggle_on", (228, 880, 384, 944), [32, 14, 32, 14]),
    ("progress_bar_65_blank", (452, 850, 1002, 910), [42, 18, 42, 18]),
    ("tooltip_panel_blank", (45, 940, 350, 1106), [36, 36, 36, 55]),
    ("notification_banner_blank", (374, 996, 1000, 1090), [88, 26, 44, 26]),
    ("close_button_diamond", (842, 1088, 962, 1210), None),
    ("panel_bg_mountain", (29, 1193, 267, 1421), [24, 24, 24, 24]),
    ("panel_bg_compass", (278, 1193, 505, 1419), [24, 24, 24, 24]),
    ("panel_bg_dragon_dark", (514, 1193, 742, 1419), [24, 24, 24, 24]),
    ("panel_bg_emblem", (755, 1194, 1006, 1438), [24, 24, 24, 24]),
    ("status_dot_gold", (31, 1447, 81, 1497), None),
    ("status_dot_blue", (94, 1446, 143, 1498), None),
    ("status_dot_red", (156, 1446, 206, 1498), None),
    ("status_dot_green", (219, 1447, 268, 1497), None),
    ("status_dot_gray", (281, 1447, 331, 1497), None),
    ("scrollbar_horizontal", (462, 1444, 1012, 1520), [42, 16, 42, 16]),
]

KEEP_LARGEST_ONLY = {
    "close_button_diamond",
    "toggle_off",
    "toggle_on",
    "scrollbar_horizontal",
    "icon_button_question",
}


def median_bg(im: Image.Image) -> tuple[int, int, int]:
    w, h = im.size
    samples = []
    for x in range(w):
        samples.append(im.getpixel((x, 0))[:3])
        samples.append(im.getpixel((x, h - 1))[:3])
    for y in range(h):
        samples.append(im.getpixel((0, y))[:3])
        samples.append(im.getpixel((w - 1, y))[:3])
    samples.sort()
    return samples[len(samples) // 2]


def dist(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1]) + abs(a[2] - b[2])


def remove_outer_bg(crop: Image.Image, threshold=30) -> Image.Image:
    crop = crop.convert("RGBA")
    w, h = crop.size
    bg = median_bg(crop)
    bg_mask = Image.new("L", (w, h), 0)
    seen = set()
    q = deque()
    for x in range(w):
        q.append((x, 0))
        q.append((x, h - 1))
    for y in range(h):
        q.append((0, y))
        q.append((w - 1, y))
    pix = crop.load()
    mp = bg_mask.load()
    while q:
        x, y = q.popleft()
        if x < 0 or y < 0 or x >= w or y >= h or (x, y) in seen:
            continue
        seen.add((x, y))
        if dist(pix[x, y][:3], bg) > threshold:
            continue
        mp[x, y] = 255
        q.extend(((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)))

    # Expand the detected outer paper slightly so parchment texture halos disappear,
    # but keep a soft transition around the object shadow.
    hard = bg_mask.filter(ImageFilter.MaxFilter(5))
    soft = hard.filter(ImageFilter.GaussianBlur(1.2))
    alpha = ImageChops.invert(soft)
    current_alpha = crop.getchannel("A")
    crop.putalpha(ImageChops.multiply(current_alpha, alpha))

    bbox = crop.getchannel("A").getbbox()
    if not bbox:
        return crop
    pad = 4
    left = max(0, bbox[0] - pad)
    top = max(0, bbox[1] - pad)
    right = min(w, bbox[2] + pad)
    bottom = min(h, bbox[3] + pad)
    return crop.crop((left, top, right, bottom))


def keep_largest_alpha_component(im: Image.Image) -> Image.Image:
    im = im.convert("RGBA")
    alpha = im.getchannel("A")
    w, h = im.size
    pix = alpha.load()
    seen = set()
    best = []
    for y in range(h):
        for x in range(w):
            if (x, y) in seen or pix[x, y] <= 24:
                continue
            q = deque([(x, y)])
            seen.add((x, y))
            pts = []
            while q:
                cx, cy = q.popleft()
                pts.append((cx, cy))
                for nx, ny in ((cx + 1, cy), (cx - 1, cy), (cx, cy + 1), (cx, cy - 1)):
                    if 0 <= nx < w and 0 <= ny < h and (nx, ny) not in seen and pix[nx, ny] > 24:
                        seen.add((nx, ny))
                        q.append((nx, ny))
            if len(pts) > len(best):
                best = pts

    if not best:
        return im
    keep = Image.new("L", (w, h), 0)
    kp = keep.load()
    for x, y in best:
        kp[x, y] = 255
    keep = keep.filter(ImageFilter.MaxFilter(5)).filter(ImageFilter.GaussianBlur(0.8))
    im.putalpha(ImageChops.multiply(alpha, keep))
    bbox = im.getchannel("A").getbbox()
    if not bbox:
        return im
    pad = 4
    return im.crop((max(0, bbox[0] - pad), max(0, bbox[1] - pad), min(w, bbox[2] + pad), min(h, bbox[3] + pad)))


def add_transparent_padding(im: Image.Image, pad=8) -> Image.Image:
    out = Image.new("RGBA", (im.width + pad * 2, im.height + pad * 2), (0, 0, 0, 0))
    out.alpha_composite(im.convert("RGBA"), (pad, pad))
    return out


def build_preview(records):
    thumbs = []
    for rec in records:
        im = Image.open(OUT / rec["file"]).convert("RGBA")
        scale = min(1.0, 210 / im.width, 140 / im.height)
        thumb = im.resize((int(im.width * scale), int(im.height * scale)), Image.Resampling.LANCZOS)
        thumbs.append((rec["name"], thumb))
    cols = 4
    tile_w, tile_h = 270, 190
    rows = (len(thumbs) + cols - 1) // cols
    preview = Image.new("RGBA", (cols * tile_w + 40, rows * tile_h + 40), (239, 232, 218, 255))
    d = ImageDraw.Draw(preview)
    for i, (name, thumb) in enumerate(thumbs):
        x = 20 + (i % cols) * tile_w
        y = 20 + (i // cols) * tile_h
        d.rounded_rectangle((x, y, x + tile_w - 14, y + tile_h - 14), radius=8, fill=(248, 244, 236, 255), outline=(190, 176, 150, 255))
        preview.alpha_composite(thumb, (x + (tile_w - 14 - thumb.width) // 2, y + 16 + (132 - thumb.height) // 2))
        d.text((x + 12, y + tile_h - 36), name[:32], fill=(80, 72, 60, 255))
    preview.convert("RGB").save(OUT / "preview_sliced_transparent_assets.png", quality=94)


def main():
    PNG.mkdir(parents=True, exist_ok=True)
    src = Image.open(SRC).convert("RGBA")
    records = []
    for name, box, nine in BOXES:
        crop = src.crop(box)
        if name.startswith("panel_bg_"):
            out = crop.convert("RGBA")
        else:
            out = remove_outer_bg(crop)
            if name in KEEP_LARGEST_ONLY:
                out = keep_largest_alpha_component(out)
            out = add_transparent_padding(out, 8)
        path = PNG / f"{name}.png"
        out.save(path, optimize=True)
        records.append(
            {
                "name": name,
                "file": f"transparent/{name}.png",
                "source_box": list(box),
                "size": [out.width, out.height],
                "nine_slice": nine,
            }
        )
    (OUT / "manifest.json").write_text(json.dumps({"version": "v12-imagegen-reference-redraw", "assets": records}, ensure_ascii=False, indent=2), encoding="utf-8")
    (OUT / "README.md").write_text(
        "# v12 imagegen reference redraw\n\n"
        "基于参考图重新生成的无文字整图，并切分为透明 PNG 控件。`source_box` 为整图切片坐标，`nine_slice` 为建议九宫格参数。\n",
        encoding="utf-8",
    )
    build_preview(records)
    print(json.dumps({"out": str(OUT), "assets": len(records)}, ensure_ascii=False))


if __name__ == "__main__":
    main()

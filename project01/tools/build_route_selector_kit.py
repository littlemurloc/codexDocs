"""Crop approved route-selector source sheets into reusable UI components."""

from __future__ import annotations

import json
from pathlib import Path

from PIL import Image, ImageDraw


ROOT = Path(r"D:\codex\project01\assets\ui\command-cards\v01\route-selector-kit-v01")
TMP = ROOT / "tmp"
OUT = ROOT / "transparent"
PREVIEW = ROOT / "preview"
PADDING = 16

SOURCES = {
    "header": TMP / "route_selector_header_source.png",
    "lane": TMP / "route_selector_lane_source.png",
    "row": TMP / "route_selector_row_source.png",
    "indicator": TMP / "route_selector_indicator_source.png",
}

# Coordinates describe only the approved source-sheet layout. No artwork is drawn here.
ASSETS = [
    ("command_header_frame", "header", (38, 243, 600, 646), "nine_slice", (48, 48, 48, 48)),
    ("command_point_badge", "header", (679, 389, 1195, 503), "nine_slice", (24, 16, 24, 16)),
    ("target_mode_badge", "header", (48, 816, 590, 930), "nine_slice", (24, 16, 24, 16)),
    ("lane_connector_triplet", "header", (692, 856, 1175, 897), "fixed", None),
    ("lane_panel_base", "lane", (63, 44, 593, 582), "nine_slice", (32, 108, 32, 32)),
    ("lane_panel_selected_outline", "lane", (656, 43, 1215, 583), "overlay", None),
    ("lane_panel_disabled_wash", "lane", (63, 654, 593, 1191), "overlay", None),
    ("lane_invalid_reason_strip", "lane", (636, 857, 1208, 966), "nine_slice", (20, 12, 20, 12)),
    ("squad_row_bg", "row", (121, 90, 1411, 294), "nine_slice", (32, 24, 32, 24)),
    ("squad_portrait_frame", "row", (249, 345, 573, 665), "fixed", None),
    ("troop_chip_frame", "row", (718, 425, 1273, 584), "nine_slice", (20, 18, 20, 18)),
    ("hp_bar_track", "row", (229, 734, 1307, 778), "nine_slice", (14, 8, 14, 8)),
    ("hp_bar_fill_neutral", "row", (453, 849, 1079, 908), "nine_slice", (4, 4, 4, 4)),
    ("final_target_reticle", "indicator", (80, 96, 455, 485), "fixed", None),
    ("final_target_ribbon", "indicator", (577, 102, 679, 479), "fixed", None),
    ("target_mode_auto_lock_icon", "indicator", (845, 148, 1137, 440), "fixed", None),
    ("target_mode_lane_all_icon", "indicator", (130, 645, 385, 898), "fixed", None),
    ("troop_icon_melee", "indicator", (497, 646, 750, 901), "fixed", None),
    ("troop_icon_ranged", "indicator", (864, 646, 1121, 901), "fixed", None),
    ("release_hint_divider", "indicator", (160, 1064, 1093, 1113), "fixed", None),
]


def crop_component(image: Image.Image, box: tuple[int, int, int, int]) -> Image.Image:
    x0, y0, x1, y1 = box
    margin = 24
    crop = image.crop((max(0, x0 - margin), max(0, y0 - margin), min(image.width, x1 + margin), min(image.height, y1 + margin)))
    bbox = crop.getchannel("A").getbbox()
    if bbox is None:
        raise ValueError("No visible pixels in source crop")
    crop = crop.crop(bbox)
    canvas = Image.new("RGBA", (crop.width + PADDING * 2, crop.height + PADDING * 2), (0, 0, 0, 0))
    canvas.alpha_composite(crop, (PADDING, PADDING))
    return canvas


def outer_edge_alpha(image: Image.Image) -> int:
    alpha = image.getchannel("A")
    edges = [
        *alpha.crop((0, 0, image.width, 1)).get_flattened_data(),
        *alpha.crop((0, image.height - 1, image.width, image.height)).get_flattened_data(),
        *alpha.crop((0, 0, 1, image.height)).get_flattened_data(),
        *alpha.crop((image.width - 1, 0, image.width, image.height)).get_flattened_data(),
    ]
    return max(edges)


def checkerboard(width: int, height: int, cell: int = 20) -> Image.Image:
    result = Image.new("RGB", (width, height), (210, 210, 210))
    draw = ImageDraw.Draw(result)
    for y in range(0, height, cell):
        for x in range(0, width, cell):
            if (x // cell + y // cell) % 2:
                draw.rectangle((x, y, x + cell - 1, y + cell - 1), fill=(246, 246, 246))
    return result


def make_preview(files: list[Path]) -> None:
    columns, cell_w, cell_h, gap = 4, 300, 220, 20
    rows = (len(files) + columns - 1) // columns
    preview = checkerboard(columns * cell_w + (columns + 1) * gap, rows * cell_h + (rows + 1) * gap)
    for index, path in enumerate(files):
        asset = Image.open(path).convert("RGBA")
        asset.thumbnail((cell_w - 20, cell_h - 20), Image.Resampling.LANCZOS)
        col, row = index % columns, index // columns
        x = gap + col * (cell_w + gap) + (cell_w - asset.width) // 2
        y = gap + row * (cell_h + gap) + (cell_h - asset.height) // 2
        preview.paste(asset, (x, y), asset)
    preview.save(PREVIEW / "preview_alpha_checker.png")


def validate_special_centers(asset_id: str, image: Image.Image) -> bool | None:
    if asset_id not in {"squad_portrait_frame", "lane_panel_selected_outline", "final_target_reticle"}:
        return None
    alpha = image.getchannel("A")
    center = alpha.getpixel((image.width // 2, image.height // 2))
    return center == 0


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    PREVIEW.mkdir(parents=True, exist_ok=True)
    source_images = {key: Image.open(path).convert("RGBA") for key, path in SOURCES.items()}
    report = []
    files = []
    for asset_id, source_key, box, behavior, insets in ASSETS:
        asset = crop_component(source_images[source_key], box)
        output = OUT / f"{asset_id}.png"
        asset.save(output)
        pixels = asset.get_flattened_data()
        magenta = sum(1 for r, g, b, a in pixels if a > 32 and r > 180 and b > 180 and g < 90)
        item = {
            "id": asset_id,
            "file": output.name,
            "size": {"width": asset.width, "height": asset.height},
            "mode": asset.mode,
            "behavior": behavior,
            "nine_slice_insets": insets,
            "edge_alpha_zero": outer_edge_alpha(asset) == 0,
            "magenta_pixels_over_alpha_32": magenta,
            "transparent_center": validate_special_centers(asset_id, asset),
        }
        if not item["edge_alpha_zero"] or magenta:
            raise ValueError(f"Alpha validation failed for {asset_id}")
        if item["transparent_center"] is False:
            raise ValueError(f"Expected transparent center for {asset_id}")
        report.append(item)
        files.append(output)
    make_preview(files)
    (ROOT / "manifest.json").write_text(json.dumps({"version": "v01", "assets": report}, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()

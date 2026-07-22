"""Package approved market status-band art without changing its design."""

from __future__ import annotations

import json
from pathlib import Path

from PIL import Image, ImageDraw


ROOT = Path(r"D:\codex\project01\assets\ui\command-cards\v01\market-selection-kit-v01\status-bands-final-v01")
TMP = ROOT / "tmp"
OUT = ROOT / "transparent"
PREVIEW = ROOT / "preview"
CANVAS = (512, 128)
PADDING = 10

ASSETS = [
    ("status_band_discount", "Discount status band", "Dynamic discount text area"),
    ("status_band_set_fusion", "Set fusion status band", "Dynamic fusion text area"),
    ("status_band_insufficient", "Insufficient funds status band", "Dynamic insufficient-funds text area"),
]


def alpha_bbox(image: Image.Image) -> tuple[int, int, int, int]:
    bbox = image.getchannel("A").getbbox()
    if bbox is None:
        raise ValueError("Image has no visible pixels")
    return bbox


def fit_asset(source_path: Path, output_path: Path) -> dict[str, object]:
    image = Image.open(source_path).convert("RGBA")
    image = image.crop(alpha_bbox(image))
    max_w, max_h = CANVAS[0] - PADDING * 2, CANVAS[1] - PADDING * 2
    scale = min(max_w / image.width, max_h / image.height)
    size = (max(1, round(image.width * scale)), max(1, round(image.height * scale)))
    image = image.resize(size, Image.Resampling.LANCZOS)
    canvas = Image.new("RGBA", CANVAS, (0, 0, 0, 0))
    pos = ((CANVAS[0] - image.width) // 2, (CANVAS[1] - image.height) // 2)
    canvas.alpha_composite(image, pos)
    canvas.save(output_path)

    alpha = canvas.getchannel("A")
    pixels = list(canvas.get_flattened_data())
    opaque = [pixel for pixel in pixels if pixel[3] > 32]
    magenta = sum(1 for r, g, b, a in opaque if r > 180 and b > 180 and g < 90)
    edge = [*alpha.crop((0, 0, CANVAS[0], 1)).get_flattened_data(), *alpha.crop((0, CANVAS[1] - 1, CANVAS[0], CANVAS[1])).get_flattened_data(), *alpha.crop((0, 0, 1, CANVAS[1])).get_flattened_data(), *alpha.crop((CANVAS[0] - 1, 0, CANVAS[0], CANVAS[1])).get_flattened_data()]
    return {
        "file": output_path.name,
        "size": {"width": CANVAS[0], "height": CANVAS[1]},
        "mode": canvas.mode,
        "edge_alpha_zero": max(edge) == 0,
        "magenta_pixels_over_alpha_32": magenta,
    }


def checkerboard(width: int, height: int, cell: int = 16) -> Image.Image:
    image = Image.new("RGB", (width, height), (208, 208, 208))
    draw = ImageDraw.Draw(image)
    for y in range(0, height, cell):
        for x in range(0, width, cell):
            if (x // cell + y // cell) % 2:
                draw.rectangle((x, y, x + cell - 1, y + cell - 1), fill=(245, 245, 245))
    return image


def make_preview() -> None:
    gap, label_h = 16, 0
    width = CANVAS[0] + 32
    height = 3 * CANVAS[1] + 4 * gap + label_h
    preview = checkerboard(width, height)
    for index, (asset_id, _, _) in enumerate(ASSETS):
        asset = Image.open(OUT / f"{asset_id}.png").convert("RGBA")
        preview.paste(asset, (16, gap + index * (CANVAS[1] + gap)), asset)
    preview.save(PREVIEW / "preview_status_bands_alpha_checker.png")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    PREVIEW.mkdir(parents=True, exist_ok=True)
    report = []
    for asset_id, label, dynamic_area in ASSETS:
        report.append({"id": asset_id, "label": label, "dynamic_area": dynamic_area, **fit_asset(TMP / f"{asset_id}.png", OUT / f"{asset_id}.png")})
    make_preview()
    (ROOT / "manifest.json").write_text(json.dumps({"version": "v01", "assets": report}, ensure_ascii=False, indent=2), encoding="utf-8")
    failures = [item for item in report if not item["edge_alpha_zero"] or item["magenta_pixels_over_alpha_32"]]
    if failures:
        raise SystemExit(f"Validation failed: {failures}")


if __name__ == "__main__":
    main()

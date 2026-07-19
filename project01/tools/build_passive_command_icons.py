from __future__ import annotations

import json
from collections import deque
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageDraw


ROOT = Path(r"D:\codex\project01\assets\ui\command-cards\v01")
CONCEPTS = ROOT / "passive-concepts-v02"
SOURCE_DIR = ROOT / "source"
TRANSPARENT_DIR = ROOT / "transparent"
PREVIEW_DIR = ROOT / "preview"
SIZE = 512
PLACED = 390
OFFSET = (SIZE - PLACED) // 2


@dataclass(frozen=True)
class IconSpec:
    command_card_id: str
    display_name: str
    source_name: str
    box: tuple[int, int, int, int]


def grid_4x2(filename: str, ids: list[tuple[str, str]]) -> list[IconSpec]:
    xs = [12, 454, 898, 1340]
    ys = [12, 454]
    boxes = [(x, y, x + 430, y + 430) for y in ys for x in xs]
    return [IconSpec(command_id, name, filename, box) for (command_id, name), box in zip(ids, boxes)]


def grid_3x2(filename: str, ids: list[tuple[str, str]]) -> list[IconSpec]:
    xs = [12, 524, 1036]
    ys = [12, 524]
    boxes = [(x, y, x + 488, y + 488) for y in ys for x in xs]
    return [IconSpec(command_id, name, filename, box) for (command_id, name), box in zip(ids, boxes)]


SPECS = [
    *grid_4x2(
        "palette_calibration_A_martial_sets.png",
        [
            ("cmd_break_spearhead", "\u950b\u77e2\u519b\u7565"),
            ("cmd_break_war_drum", "\u6218\u9f13\u519b\u7565"),
            ("cmd_tiger_iron_armor", "\u94c1\u7532\u519b\u7565"),
            ("cmd_tiger_shield_line", "\u76fe\u5217\u519b\u7565"),
            ("cmd_tiger_hold_fast", "\u6b7b\u5b88\u519b\u7565"),
            ("cmd_tiger_hold_formation", "\u56fa\u9635\u519b\u7565"),
            ("cmd_flying_good_mount", "\u826f\u9a6c\u519b\u7565"),
            ("cmd_flying_flank_assault", "\u4fa7\u51fb\u519b\u7565"),
        ],
    ),
    *grid_3x2(
        "overview_B_fire_chain_ambush_palette_v02.png",
        [
            ("cmd_fire_oil", "\u706b\u6cb9\u519b\u7565"),
            ("cmd_fire_wind", "\u98ce\u52a9\u519b\u7565"),
            ("cmd_chain_bind_boats", "\u7f1a\u821f\u519b\u7565"),
            ("cmd_chain_cut_rope", "\u65ad\u7d22\u519b\u7565"),
            ("cmd_ambush_scout", "\u8033\u76ee\u519b\u7565"),
            ("cmd_ambush_cut_supply", "\u65ad\u7cae\u519b\u7565"),
        ],
    ),
    *grid_4x2(
        "overview_C_tuntian_recruitment_palette_v02.png",
        [
            ("cmd_farm_reclaim", "\u5c6f\u57a6\u519b\u7565"),
            ("cmd_farm_thrift", "\u8282\u7528\u519b\u7565"),
            ("cmd_farm_spoils", "\u7f34\u83b7\u519b\u7565"),
            ("cmd_farm_prosperity", "\u5bcc\u56fd\u519b\u7565"),
            ("cmd_recruit_enlist", "\u52df\u5352\u519b\u7565"),
            ("cmd_recruit_train", "\u7ec3\u5352\u519b\u7565"),
            ("cmd_recruit_formation", "\u6210\u9635\u519b\u7565"),
            ("cmd_recruit_elite_force", "\u7cbe\u5175\u5f3a\u519b"),
        ],
    ),
    *grid_4x2(
        "overview_D_workshop_independent_palette_v02.png",
        [
            ("cmd_armory_forging", "\u7cbe\u953b\u519b\u7565"),
            ("cmd_armory_armor", "\u7532\u80c4\u519b\u7565"),
            ("cmd_armory_calibration", "\u6821\u51c6\u519b\u7565"),
            ("cmd_armory_masterwork", "\u767e\u5de5\u519b\u7565"),
            ("cmd_independent_vitality", "\u4f53\u9b44\u519b\u7565"),
            ("cmd_independent_vigor", "\u9510\u6c14\u519b\u7565"),
            ("cmd_independent_march", "\u884c\u519b\u519b\u7565"),
            ("cmd_independent_preserve", "\u4fdd\u5168\u519b\u7565"),
        ],
    ),
]


def is_paper(pixel: tuple[int, int, int, int]) -> bool:
    r, g, b, _ = pixel
    return r > 190 and g > 170 and b > 130 and max(r, g, b) - min(r, g, b) < 100


def clear_connected_paper(image: Image.Image) -> Image.Image:
    """Remove only ivory gutter pixels connected to the crop edge."""
    rgba = image.convert("RGBA")
    width, height = rgba.size
    pixels = rgba.load()
    cleared = set()
    queue: deque[tuple[int, int]] = deque()

    for x in range(width):
        queue.extend(((x, 0), (x, height - 1)))
    for y in range(1, height - 1):
        queue.extend(((0, y), (width - 1, y)))

    while queue:
        x, y = queue.popleft()
        if (x, y) in cleared or not is_paper(pixels[x, y]):
            continue
        cleared.add((x, y))
        for nx, ny in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
            if 0 <= nx < width and 0 <= ny < height and (nx, ny) not in cleared:
                queue.append((nx, ny))

    for x, y in cleared:
        r, g, b, _ = pixels[x, y]
        pixels[x, y] = (r, g, b, 0)
    return rgba


def compose_icon(crop: Image.Image, transparent: bool) -> Image.Image:
    icon = clear_connected_paper(crop) if transparent else crop.convert("RGBA")
    icon = icon.resize((PLACED, PLACED), Image.Resampling.LANCZOS)
    canvas = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    canvas.alpha_composite(icon, (OFFSET, OFFSET))
    return canvas


def checkerboard(size: int) -> Image.Image:
    image = Image.new("RGB", (size, size), (222, 222, 222))
    draw = ImageDraw.Draw(image)
    step = 12
    for y in range(0, size, step):
        for x in range(0, size, step):
            if (x // step + y // step) % 2:
                draw.rectangle((x, y, x + step - 1, y + step - 1), fill=(186, 186, 186))
    return image.convert("RGBA")


def make_preview(files: list[Path], tile_size: int, icon_size: int, output: Path) -> None:
    columns = 6
    rows = (len(files) + columns - 1) // columns
    canvas = Image.new("RGBA", (columns * tile_size, rows * tile_size), (238, 232, 216, 255))
    for index, file in enumerate(files):
        x = (index % columns) * tile_size
        y = (index // columns) * tile_size
        tile = checkerboard(tile_size)
        icon = Image.open(file).convert("RGBA").resize((icon_size, icon_size), Image.Resampling.LANCZOS)
        tile.alpha_composite(icon, ((tile_size - icon_size) // 2, (tile_size - icon_size) // 2))
        canvas.alpha_composite(tile, (x, y))
    canvas.save(output)


def main() -> None:
    SOURCE_DIR.mkdir(parents=True, exist_ok=True)
    TRANSPARENT_DIR.mkdir(parents=True, exist_ok=True)
    PREVIEW_DIR.mkdir(parents=True, exist_ok=True)

    source_boards = {spec.source_name: Image.open(CONCEPTS / spec.source_name).convert("RGBA") for spec in SPECS}
    output_files: list[Path] = []
    passive_assets = []
    validations = []

    for spec in SPECS:
        crop = source_boards[spec.source_name].crop(spec.box)
        source_path = SOURCE_DIR / f"{spec.command_card_id}_source.png"
        transparent_path = TRANSPARENT_DIR / f"{spec.command_card_id}.png"
        crop.save(source_path)
        compose_icon(crop, transparent=False).save(SOURCE_DIR / f"{spec.command_card_id}_normalized.png")
        compose_icon(crop, transparent=True).save(transparent_path)

        with Image.open(transparent_path) as image:
            rgba = image.convert("RGBA")
            edge_alpha = max(
                max(rgba.getpixel((x, 0))[3] for x in range(SIZE)),
                max(rgba.getpixel((x, SIZE - 1))[3] for x in range(SIZE)),
                max(rgba.getpixel((0, y))[3] for y in range(SIZE)),
                max(rgba.getpixel((SIZE - 1, y))[3] for y in range(SIZE)),
            )
            assert rgba.size == (SIZE, SIZE)
            assert rgba.mode == "RGBA"
            assert edge_alpha == 0

        output_files.append(transparent_path)
        passive_assets.append(
            {
                "command_card_id": spec.command_card_id,
                "display_name": spec.display_name,
                "file": f"transparent/{spec.command_card_id}.png",
                "source": f"source/{spec.command_card_id}_source.png",
                "dimensions": [SIZE, SIZE],
                "format": "PNG RGBA",
                "safe_edge": "12% transparent margin",
                "production": "approved passive concept v02 crop, alpha cleaned",
            }
        )
        validations.append(
            {
                "file": f"{spec.command_card_id}.png",
                "dimensions": [SIZE, SIZE],
                "mode": "RGBA",
                "edge_alpha_max": 0,
            }
        )

    make_preview(output_files, 128, 104, PREVIEW_DIR / "preview_passive_alpha_checker.png")
    make_preview(output_files, 72, 48, PREVIEW_DIR / "preview_passive_hud_48.png")

    manifest_path = ROOT / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    existing_ids = {asset["command_card_id"] for asset in manifest["assets"]}
    manifest["assets"].extend(asset for asset in passive_assets if asset["command_card_id"] not in existing_ids)
    existing_validation = {entry["file"] for entry in manifest.get("validation", [])}
    manifest.setdefault("validation", []).extend(entry for entry in validations if entry["file"] not in existing_validation)
    manifest["asset_count"] = len(manifest["assets"])
    manifest["status"] = "active and passive command icons exported to transparent masters"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    for board in source_boards.values():
        board.close()


if __name__ == "__main__":
    main()

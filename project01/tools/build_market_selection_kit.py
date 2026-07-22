from __future__ import annotations

import json
from pathlib import Path

from PIL import Image, ImageDraw


ROOT = Path(r"D:\codex\project01\assets\ui\command-cards\v01\market-selection-kit-v01")
TMP = ROOT / "tmp"
OUT = ROOT / "transparent"
PREVIEW = ROOT / "preview"


def trim_and_fit(image: Image.Image, size: tuple[int, int], padding: int) -> Image.Image:
    image = image.convert("RGBA")
    bbox = image.getchannel("A").getbbox()
    if bbox is None:
        raise ValueError("Component has no opaque pixels")
    image = image.crop(bbox)
    max_width = size[0] - padding * 2
    max_height = size[1] - padding * 2
    scale = min(max_width / image.width, max_height / image.height)
    scaled = image.resize((round(image.width * scale), round(image.height * scale)), Image.Resampling.LANCZOS)
    canvas = Image.new("RGBA", size, (0, 0, 0, 0))
    canvas.alpha_composite(scaled, ((size[0] - scaled.width) // 2, (size[1] - scaled.height) // 2))
    return canvas


def checkerboard(size: tuple[int, int], step: int = 12) -> Image.Image:
    image = Image.new("RGBA", size, (224, 224, 224, 255))
    draw = ImageDraw.Draw(image)
    for y in range(0, size[1], step):
        for x in range(0, size[0], step):
            if (x // step + y // step) % 2:
                draw.rectangle((x, y, x + step - 1, y + step - 1), fill=(186, 186, 186, 255))
    return image


def save_component(name: str, image: Image.Image, size: tuple[int, int], padding: int) -> dict:
    output = trim_and_fit(image, size, padding)
    path = OUT / f"{name}.png"
    output.save(path)
    alpha = output.getchannel("A")
    edge_alpha = max(
        alpha.crop((0, 0, output.width, 1)).getextrema()[1],
        alpha.crop((0, output.height - 1, output.width, output.height)).getextrema()[1],
        alpha.crop((0, 0, 1, output.height)).getextrema()[1],
        alpha.crop((output.width - 1, 0, output.width, output.height)).getextrema()[1],
    )
    if edge_alpha != 0:
        raise ValueError(f"{name} touches its outer edge")
    return {"file": f"transparent/{name}.png", "dimensions": list(size), "edge_alpha_max": edge_alpha}


def make_controls_preview(names: list[str]) -> None:
    tile = 180
    canvas = Image.new("RGBA", (tile * 3, tile * 3), (238, 232, 216, 255))
    for index, name in enumerate(names):
        component = Image.open(OUT / f"{name}.png").convert("RGBA")
        preview = checkerboard((tile, tile))
        scale = min(150 / component.width, 130 / component.height)
        component = component.resize((round(component.width * scale), round(component.height * scale)), Image.Resampling.LANCZOS)
        preview.alpha_composite(component, ((tile - component.width) // 2, (tile - component.height) // 2))
        canvas.alpha_composite(preview, ((index % 3) * tile, (index // 3) * tile))
    canvas.save(PREVIEW / "preview_controls_alpha_checker.png")


def make_card_preview() -> None:
    names = ["choice_card_base", "choice_card_selected_outline"]
    tile_size = (320, 480)
    canvas = Image.new("RGBA", (tile_size[0] * 2, tile_size[1]), (238, 232, 216, 255))
    for index, name in enumerate(names):
        component = Image.open(OUT / f"{name}.png").convert("RGBA")
        preview = checkerboard(tile_size, step=16)
        component = component.resize((300, 450), Image.Resampling.LANCZOS)
        preview.alpha_composite(component, (10, 15))
        canvas.alpha_composite(preview, (index * tile_size[0], 0))
    canvas.save(PREVIEW / "preview_card_layers_alpha_checker.png")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    PREVIEW.mkdir(parents=True, exist_ok=True)

    base = Image.open(TMP / "choice_card_base_alpha_full.png")
    outline = Image.open(TMP / "choice_card_selected_outline_alpha_full.png")
    controls = Image.open(TMP / "selection_controls_alpha_full.png")

    validation = []
    validation.append(save_component("choice_card_base", base, (512, 768), 30))
    validation.append(save_component("choice_card_selected_outline", outline, (512, 768), 24))

    cells = {
        "choice_card_set_crest_frame": (0, 0, 418, 418, (128, 128), 8),
        "choice_card_progress_empty": (418, 0, 836, 418, (56, 56), 4),
        "choice_card_progress_lit": (836, 0, 1254, 418, (56, 56), 4),
        "choice_card_type_active": (0, 418, 418, 836, (160, 80), 8),
        "choice_card_type_passive": (418, 418, 836, 836, (160, 80), 8),
        "choice_card_currency_coin": (836, 418, 1254, 836, (72, 72), 6),
        "choice_card_set_advance_cue": (0, 836, 418, 1254, (260, 64), 8),
        "choice_card_confirm_button": (430, 836, 930, 1254, (300, 96), 8),
        "choice_card_close_button": (930, 836, 1254, 1254, (72, 72), 6),
    }
    for name, (left, top, right, bottom, size, padding) in cells.items():
        validation.append(save_component(name, controls.crop((left, top, right, bottom)), size, padding))

    make_card_preview()
    make_controls_preview(list(cells.keys()))

    assets = [
        {
            "name": "choice_card_base",
            "purpose": "Card structure layer. The crest socket and ability-art window are transparent.",
            "z_order": 3,
        },
        {
            "name": "choice_card_selected_outline",
            "purpose": "Selected-state decorative outline. Engine may add its own bloom outside this texture.",
            "z_order": 8,
        },
        {
            "name": "choice_card_set_crest_frame",
            "purpose": "Frame placed over a dynamic Set crest icon.",
            "z_order": 4,
        },
        {
            "name": "choice_card_progress_empty",
            "purpose": "Unlit Set progress pip.",
            "z_order": 5,
        },
        {
            "name": "choice_card_progress_lit",
            "purpose": "Lit Set progress pip.",
            "z_order": 5,
        },
        {
            "name": "choice_card_type_active",
            "purpose": "Active-command marker.",
            "z_order": 5,
        },
        {
            "name": "choice_card_type_passive",
            "purpose": "Passive-doctrine marker.",
            "z_order": 5,
        },
        {
            "name": "choice_card_currency_coin",
            "purpose": "Currency icon placed before dynamic price text.",
            "z_order": 5,
        },
        {
            "name": "choice_card_set_advance_cue",
            "purpose": "Optional blank cue plaque for dynamic Set advancement copy.",
            "z_order": 6,
        },
        {
            "name": "choice_card_confirm_button",
            "purpose": "Blank confirm button; program overlays localized button text.",
            "z_order": 8,
        },
        {
            "name": "choice_card_close_button",
            "purpose": "Optional close button for the selection surface.",
            "z_order": 8,
        },
    ]
    manifest = {
        "package": "market-selection-kit-v01",
        "based_on": "market-selection concept B",
        "assets": assets,
        "validation": validation,
        "composition_order": [
            "dynamic ability illustration",
            "dynamic Set crest icon",
            "choice_card_base",
            "choice_card_set_crest_frame",
            "dynamic title, Set label, description, price and progress text",
            "type marker, progress pips and currency coin",
            "choice_card_set_advance_cue when relevant",
            "choice_card_selected_outline when selected",
        ],
    }
    (ROOT / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()

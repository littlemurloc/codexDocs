from __future__ import annotations

import json
from collections import deque
from pathlib import Path

from PIL import Image


OUT = Path("assets/art/packages/battle-command-popup-cinnabar-v01")
SRC = OUT / "source" / "cinnabar_command_popup_frame_raw.png"
TARGET_SCREEN = (1920, 1080)
TARGET_WIDTH = 1344


def is_checker_background(pixel: tuple[int, int, int, int]) -> bool:
    r, g, b, _ = pixel
    mean = (r + g + b) / 3
    spread = max(r, g, b) - min(r, g, b)
    return mean >= 190 and spread <= 45


def edge_connected_background(im: Image.Image) -> set[tuple[int, int]]:
    width, height = im.size
    seen: set[tuple[int, int]] = set()
    q: deque[tuple[int, int]] = deque()

    def push(x: int, y: int) -> None:
        if (x, y) not in seen and is_checker_background(im.getpixel((x, y))):
            seen.add((x, y))
            q.append((x, y))

    for x in range(width):
        push(x, 0)
        push(x, height - 1)
    for y in range(height):
        push(0, y)
        push(width - 1, y)

    while q:
        x, y = q.popleft()
        for nx, ny in (
            (x + 1, y),
            (x - 1, y),
            (x, y + 1),
            (x, y - 1),
            (x + 1, y + 1),
            (x + 1, y - 1),
            (x - 1, y + 1),
            (x - 1, y - 1),
        ):
            if 0 <= nx < width and 0 <= ny < height:
                push(nx, ny)
    return seen


def clean_alpha(src: Path) -> Image.Image:
    im = Image.open(src).convert("RGBA")
    bg = edge_connected_background(im)
    pix = im.load()
    for x, y in bg:
        pix[x, y] = (255, 255, 255, 0)

    for y in range(im.height):
        for x in range(im.width):
            r, g, b, a = pix[x, y]
            mean = (r + g + b) / 3
            spread = max(r, g, b) - min(r, g, b)
            if a and mean >= 245 and spread <= 20:
                pix[x, y] = (255, 255, 255, 0)

    bbox = im.getbbox()
    if not bbox:
        raise RuntimeError("No non-transparent pixels found after alpha cleanup")

    left, top, right, bottom = bbox
    pad = 8
    left = max(left - pad, 0)
    top = max(top - pad, 0)
    right = min(right + pad, im.width)
    bottom = min(bottom + pad, im.height)
    return im.crop((left, top, right, bottom))


def main() -> None:
    transparent_dir = OUT / "transparent"
    reference_dir = OUT / "reference"
    preview_dir = OUT / "preview"
    for directory in (transparent_dir, reference_dir, preview_dir):
        directory.mkdir(parents=True, exist_ok=True)

    popup = clean_alpha(SRC)
    target_height = round(popup.height * TARGET_WIDTH / popup.width)
    popup = popup.resize((TARGET_WIDTH, target_height), Image.Resampling.LANCZOS)

    transparent_path = transparent_dir / "cinnabar_command_popup_frame_blank.png"
    popup.save(transparent_path)

    canvas = Image.new("RGBA", TARGET_SCREEN, (255, 255, 255, 0))
    anchor = ((TARGET_SCREEN[0] - popup.width) // 2, (TARGET_SCREEN[1] - popup.height) // 2)
    canvas.alpha_composite(popup, anchor)
    reference_path = reference_dir / "cinnabar_command_popup_frame_1920x1080.png"
    canvas.save(reference_path)

    checker = Image.new("RGB", TARGET_SCREEN, (48, 52, 58))
    cell = 32
    for y in range(0, TARGET_SCREEN[1], cell):
        for x in range(0, TARGET_SCREEN[0], cell):
            if (x // cell + y // cell) % 2 == 0:
                checker.paste((76, 80, 88), (x, y, x + cell, y + cell))
    checker_rgba = checker.convert("RGBA")
    checker_rgba.alpha_composite(canvas)
    preview_path = preview_dir / "preview_alpha_on_checker.jpg"
    checker_rgba.convert("RGB").save(preview_path, quality=92)

    manifest = {
        "package": "battle-command-popup-cinnabar-v01",
        "source_image": str(SRC),
        "target_screen": {"width": TARGET_SCREEN[0], "height": TARGET_SCREEN[1]},
        "assets": [
            {
                "id": "cinnabar_command_popup_frame_blank",
                "path": str(transparent_path).replace("\\", "/"),
                "type": "modal_popup_frame",
                "size_px": {"width": popup.width, "height": popup.height},
                "reference_anchor_px_on_1920x1080": {"x": anchor[0], "y": anchor[1]},
                "recommended_scale_usage": "Place at 1344 px width on a 1920x1080 battle screen; center on screen unless layout requires offset.",
                "notes": "Cards and dynamic content are intentionally removed. Title plaque is blank for runtime text/art text layering.",
            },
            {
                "id": "cinnabar_command_popup_frame_1920x1080_reference",
                "path": str(reference_path).replace("\\", "/"),
                "type": "layout_reference_transparent_canvas",
                "size_px": {"width": TARGET_SCREEN[0], "height": TARGET_SCREEN[1]},
            },
        ],
        "nine_slice_notes": {
            "recommended": "Use this as a whole modal frame when possible. If 9-slicing is needed, keep hanging tags/tassels, close button, title plaque, and bottom medallion as overlays rather than stretching them.",
            "stretchable_center": "Ivory parchment interior only.",
            "non_stretch_overlays": [
                "top title plaque",
                "upper-right close button",
                "side hanging command tokens and tassels",
                "gold corner brackets",
                "bottom center medallion",
            ],
        },
    }
    (OUT / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps({
        "transparent": str(transparent_path),
        "reference": str(reference_path),
        "preview": str(preview_path),
        "popup_size": [popup.width, popup.height],
        "anchor": list(anchor),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

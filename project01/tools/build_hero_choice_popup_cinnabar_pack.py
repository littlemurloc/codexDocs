from __future__ import annotations

import json
from collections import deque
from pathlib import Path

from PIL import Image


OUT = Path("assets/art/packages/hero-choice-popup-cinnabar-v01")
SRC_POPUP = OUT / "source" / "hero_choice_popup_raw.png"
SRC_BUTTONS = OUT / "source" / "hero_choice_buttons_raw.png"
TARGET_SCREEN = (1920, 1080)
POPUP_TARGET_WIDTH = 1500


BUTTON_CROPS = {
    "button_confirm_red_blank": (45, 105, 1005, 270),
    "button_cancel_green_blank": (45, 320, 1005, 475),
    "button_neutral_parchment_blank": (45, 520, 1005, 680),
    "button_long_disabled_gray_blank": (45, 720, 1005, 880),
    "button_refresh_round_normal": (1030, 95, 1285, 320),
    "button_refresh_round_disabled": (1030, 685, 1285, 890),
    "text_confirm": (1310, 115, 1565, 265),
    "text_cancel": (1310, 345, 1570, 505),
    "text_refresh": (1300, 605, 1585, 760),
}


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

    neighbors = (
        (1, 0),
        (-1, 0),
        (0, 1),
        (0, -1),
        (1, 1),
        (1, -1),
        (-1, 1),
        (-1, -1),
    )
    while q:
        x, y = q.popleft()
        for dx, dy in neighbors:
            nx, ny = x + dx, y + dy
            if 0 <= nx < width and 0 <= ny < height:
                push(nx, ny)
    return seen


def clean_alpha(
    src: Path,
    protected_rect: tuple[int, int, int, int] | None = None,
    global_neutral_cleanup: bool = True,
) -> Image.Image:
    im = Image.open(src).convert("RGBA")
    pix = im.load()
    for x, y in edge_connected_background(im):
        pix[x, y] = (255, 255, 255, 0)

    for y in range(im.height):
        for x in range(im.width):
            r, g, b, a = pix[x, y]
            mean = (r + g + b) / 3
            spread = max(r, g, b) - min(r, g, b)
            protected = False
            if protected_rect:
                left, top, right, bottom = protected_rect
                protected = left <= x < right and top <= y < bottom
            if (
                a
                and global_neutral_cleanup
                and not protected
                and (is_checker_background((r, g, b, a)) or (mean >= 245 and spread <= 20))
            ):
                pix[x, y] = (255, 255, 255, 0)
    return im


def tight_crop(im: Image.Image, pad: int = 8) -> Image.Image:
    bbox = im.getbbox()
    if not bbox:
        raise RuntimeError("No non-transparent pixels found")
    left, top, right, bottom = bbox
    left = max(left - pad, 0)
    top = max(top - pad, 0)
    right = min(right + pad, im.width)
    bottom = min(bottom + pad, im.height)
    return im.crop((left, top, right, bottom))


def save_scaled_popup(popup: Image.Image, out_path: Path) -> tuple[int, int]:
    popup = tight_crop(popup, pad=8)
    target_height = round(popup.height * POPUP_TARGET_WIDTH / popup.width)
    popup = popup.resize((POPUP_TARGET_WIDTH, target_height), Image.Resampling.LANCZOS)
    popup.save(out_path)
    return popup.size


def make_reference(popup_path: Path, out_path: Path) -> tuple[int, int]:
    popup = Image.open(popup_path).convert("RGBA")
    canvas = Image.new("RGBA", TARGET_SCREEN, (255, 255, 255, 0))
    anchor = ((TARGET_SCREEN[0] - popup.width) // 2, (TARGET_SCREEN[1] - popup.height) // 2)
    canvas.alpha_composite(popup, anchor)
    canvas.save(out_path)
    return anchor


def make_preview(reference_path: Path, out_path: Path) -> None:
    reference = Image.open(reference_path).convert("RGBA")
    bg = Image.new("RGB", TARGET_SCREEN, (48, 52, 58))
    cell = 32
    for y in range(0, TARGET_SCREEN[1], cell):
        for x in range(0, TARGET_SCREEN[0], cell):
            if (x // cell + y // cell) % 2 == 0:
                bg.paste((76, 80, 88), (x, y, x + cell, y + cell))
    preview = bg.convert("RGBA")
    preview.alpha_composite(reference)
    preview.convert("RGB").save(out_path, quality=92)


def main() -> None:
    transparent_dir = OUT / "transparent"
    controls_dir = OUT / "controls"
    text_dir = OUT / "text"
    reference_dir = OUT / "reference"
    preview_dir = OUT / "preview"
    for directory in (transparent_dir, controls_dir, text_dir, reference_dir, preview_dir):
        directory.mkdir(parents=True, exist_ok=True)

    popup_clean = clean_alpha(SRC_POPUP, protected_rect=(115, 120, 1650, 825))
    popup_path = transparent_dir / "hero_choice_popup_frame_blank_zhaoxian.png"
    popup_size = save_scaled_popup(popup_clean, popup_path)

    reference_path = reference_dir / "hero_choice_popup_frame_1920x1080.png"
    anchor = make_reference(popup_path, reference_path)
    preview_path = preview_dir / "preview_alpha_on_checker.jpg"
    make_preview(reference_path, preview_path)

    buttons_clean = clean_alpha(SRC_BUTTONS, global_neutral_cleanup=False)
    assets = [
        {
            "id": "hero_choice_popup_frame_blank_zhaoxian",
            "path": str(popup_path).replace("\\", "/"),
            "type": "modal_popup_frame",
            "size_px": {"width": popup_size[0], "height": popup_size[1]},
            "reference_anchor_px_on_1920x1080": {"x": anchor[0], "y": anchor[1]},
            "notes": "Hero cards and dynamic content are removed. Side plaques use 招贤. Title plaque is blank for runtime title art.",
        },
        {
            "id": "hero_choice_popup_frame_1920x1080_reference",
            "path": str(reference_path).replace("\\", "/"),
            "type": "layout_reference_transparent_canvas",
            "size_px": {"width": TARGET_SCREEN[0], "height": TARGET_SCREEN[1]},
        },
    ]

    for asset_id, box in BUTTON_CROPS.items():
        crop = tight_crop(buttons_clean.crop(box), pad=6)
        if asset_id.startswith("text_"):
            path = text_dir / f"{asset_id}.png"
            asset_type = "button_text_art"
        else:
            path = controls_dir / f"{asset_id}.png"
            asset_type = "button_control"
        crop.save(path)
        assets.append(
            {
                "id": asset_id,
                "path": str(path).replace("\\", "/"),
                "type": asset_type,
                "size_px": {"width": crop.width, "height": crop.height},
            }
        )

    manifest = {
        "package": "hero-choice-popup-cinnabar-v01",
        "source_images": {
            "popup": str(SRC_POPUP).replace("\\", "/"),
            "buttons": str(SRC_BUTTONS).replace("\\", "/"),
        },
        "target_screen": {"width": TARGET_SCREEN[0], "height": TARGET_SCREEN[1]},
        "recommended_usage": {
            "popup_width_on_1920x1080": POPUP_TARGET_WIDTH,
            "popup_anchor_centered": {"x": anchor[0], "y": anchor[1]},
            "title_runtime_text": "选择你的伙伴",
            "side_plaque_text": "招贤",
        },
        "assets": assets,
        "implementation_notes": {
            "layering": "Use popup frame as base, place hero cards and action buttons as separate runtime layers.",
            "nine_slice": "If stretching is required, only stretch the parchment interior and straight rails; keep plaques, tassels, corner brackets, and title plaque as overlays.",
            "button_text": "Button blanks and Chinese text art are separated so states/localization can be swapped.",
        },
    }
    (OUT / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    print(
        json.dumps(
            {
                "popup": str(popup_path),
                "reference": str(reference_path),
                "preview": str(preview_path),
                "assets": len(assets),
                "popup_size": list(popup_size),
                "anchor": list(anchor),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()

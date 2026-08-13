"""Build a bright, temporary Y3 card-merge overlay preview from approved key art."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(r"D:\codex\project01")
GENERATED = Path(r"C:\Users\littl\.codex\generated_images\019f11ac-2fcc-7431-b8fe-6f6101936789")
OUT = ROOT / "tmp/card-merge-mask-y3-preview-v02"
FRAMES = OUT / "png_frames"
HELPER_PATH = Path(r"C:\Users\littl\.codex\skills\.system\imagegen\scripts\remove_chroma_key.py")

SOURCES = [
    "exec-cdfc825f-beca-488e-8245-179979ca3f38.png",
    "exec-eea43fb2-0db0-4ce6-9f49-97ebe10f86b1.png",
    "exec-ab678d60-d179-4b67-bc95-bd77c346a1e1.png",
    "exec-3dee2cd1-7c96-4fe4-a26b-5eb436383603.png",
    "exec-740f38b2-1138-4164-80ee-4a6814909045.png",
    "exec-06956363-3fe1-4814-bc9f-1c135e7393cf.png",
    "exec-9806c84c-d25f-4adf-87e7-527e5a812350.png",
    "exec-7186319e-0e3f-44d1-96fb-56f07c5d7b14.png",
    "exec-ef52e096-6802-4860-a200-04ccec00857b.png",
    "exec-8bb2c1c6-30c5-40e4-9bfc-091b600989dd.png",
    "exec-b89334b0-410e-47a0-bc9b-d30c287556d5.png",
    "exec-ee31d660-fb47-4086-9106-9ef45b7a19ad.png",
    "exec-57e40781-51bc-4193-91bf-5f3d2f531ff4.png",
    "exec-17ccf057-d60b-4000-a6aa-dc483fcb6225.png",
    "exec-acd4e341-79ce-4f18-ab01-89a65bf9b183.png",
    "exec-3f30ad9f-09d9-49ed-ab6c-3aa4438628a7.png",
]


def load_helper():
    spec = importlib.util.spec_from_file_location("remove_chroma_key", HELPER_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load chroma helper: {HELPER_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def process_source(source: Path, helper) -> Image.Image:
    with Image.open(source) as opened:
        image = opened.convert("RGBA").resize((360, 480), Image.Resampling.LANCZOS)
    key = helper._sample_border_key(image, "border")
    helper._apply_alpha_to_image(
        image,
        key=key,
        tolerance=12,
        spill_cleanup=True,
        soft_matte=True,
        transparent_threshold=12,
        opaque_threshold=220,
    )
    image = helper._contract_alpha(image, 1)
    framed = Image.new("RGBA", (384, 512), (0, 0, 0, 0))
    framed.alpha_composite(image, (12, 16))
    return framed


def expand_keyframes(keyframes: list[Image.Image]) -> list[Image.Image]:
    """Use three temporal samples per authored stage for a smooth 16 fps test."""
    result: list[Image.Image] = []
    for index, current in enumerate(keyframes):
        following = keyframes[min(index + 1, len(keyframes) - 1)]
        result.extend((
            current,
            Image.blend(current, following, 1 / 3),
            Image.blend(current, following, 2 / 3),
        ))
    return result


def validate(image: Image.Image, name: str) -> list[int]:
    if image.size != (384, 512) or image.mode != "RGBA":
        raise RuntimeError(f"Unexpected frame format: {name}")
    alpha = image.getchannel("A")
    edges = (
        alpha.crop((0, 0, 384, 1)), alpha.crop((0, 511, 384, 512)),
        alpha.crop((0, 0, 1, 512)), alpha.crop((383, 0, 384, 512)),
    )
    if max(edge.getextrema()[1] for edge in edges) != 0:
        raise RuntimeError(f"Frame touches edge: {name}")
    bbox = alpha.getbbox()
    if bbox is None:
        raise RuntimeError(f"Empty frame: {name}")
    return list(bbox)


def checkerboard(width: int, height: int) -> Image.Image:
    canvas = Image.new("RGBA", (width, height), (0, 0, 0, 255))
    draw = ImageDraw.Draw(canvas)
    for y in range(0, height, 16):
        for x in range(0, width, 16):
            color = (197, 202, 204, 255) if (x // 16 + y // 16) % 2 == 0 else (139, 146, 149, 255)
            draw.rectangle((x, y, x + 15, y + 15), fill=color)
    return canvas


def contact_sheet(frames: list[Image.Image]) -> None:
    columns, tile_w, tile_h, gap, margin = 8, 120, 160, 12, 22
    rows = (len(frames) + columns - 1) // columns
    canvas = checkerboard(margin * 2 + columns * tile_w + (columns - 1) * gap, margin * 2 + rows * tile_h + (rows - 1) * gap)
    draw = ImageDraw.Draw(canvas)
    font = ImageFont.truetype(r"C:\Windows\Fonts\arial.ttf", 16)
    for index, frame in enumerate(frames):
        x = margin + (index % columns) * (tile_w + gap)
        y = margin + (index // columns) * (tile_h + gap)
        canvas.alpha_composite(frame.resize((tile_w, tile_h), Image.Resampling.LANCZOS), (x, y))
        draw.text((x + 3, y + 3), f"{index:03d}", font=font, fill=(248, 244, 232, 255), stroke_width=1, stroke_fill=(35, 36, 34, 255))
    canvas.convert("RGB").save(OUT / "contact_sheet_alpha_checker.png", quality=95)


def alpha_preview(frames: list[Image.Image]) -> None:
    # Checkerboard is preview-only to make alpha visible; it is not part of the Y3 frames.
    sequence = []
    for frame in frames:
        canvas = checkerboard(576, 768)
        canvas.alpha_composite(frame.resize((576, 768), Image.Resampling.LANCZOS), (0, 0))
        sequence.append(canvas.convert("P", palette=Image.Palette.ADAPTIVE))
    sequence[0].save(OUT / "preview_alpha_checker.gif", save_all=True, append_images=sequence[1:], duration=62, loop=0, disposal=2, optimize=False)


def main() -> None:
    if OUT.exists() and any(OUT.rglob("*")):
        raise RuntimeError(f"Output already exists: {OUT}")
    FRAMES.mkdir(parents=True, exist_ok=True)
    helper = load_helper()
    keyframes = [process_source(GENERATED / source, helper) for source in SOURCES]
    frames = expand_keyframes(keyframes)
    entries = []
    for index, frame in enumerate(frames):
        target = FRAMES / f"card_merge_bright_mask_{index:03d}.png"
        target.write_bytes(b"")
        frame.save(target, optimize=True)
        entries.append({"frame": index, "file": target.name, "alpha_bbox": validate(frame, target.name)})
    contact_sheet(frames)
    alpha_preview(frames)
    manifest = {
        "package": "card-merge-mask-y3-preview-v02",
        "temporary_review_only": True,
        "sequence": {"frame_count": 48, "fps": 16, "duration_seconds": 3.0, "frame_size": [384, 512], "format": "RGBA PNG", "recommended_overlay_scale": 1.08},
        "swap_window": {"start_frame": 15, "end_frame": 27, "instruction": "The parchment mask is fully opaque here. Replace the dynamic card during this window."},
        "visual": "Bright ivory parchment and pale antique-gold seal; no backdrop or card artwork in frame resources.",
        "import": "Batch-import png_frames in ascending filename order as a Y3 sequence-frame resource.",
        "frames": entries,
    }
    (OUT / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (OUT / "README.md").write_text(
        "# Card Merge Bright Mask Y3 Preview v02\n\n"
        "临时审核资源。48 帧、16fps、约 3 秒。015-027 为完整亮纸幕遮挡窗口，程序在此期间替换动态卡面。\n"
        "`preview_alpha_checker.gif` 的棋盘格只用于验证透明区域，不属于任何游戏资源。\n",
        encoding="utf-8",
    )
    print(f"Built {len(frames)} preview frames: {OUT}")


if __name__ == "__main__":
    main()

"""Prepare Y3-style preview PNG frames from approved card-merge overlay artwork."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(r"D:\codex\project01")
GENERATED = Path(r"C:\Users\littl\.codex\generated_images\019f11ac-2fcc-7431-b8fe-6f6101936789")
OUT = ROOT / "tmp/card-merge-mask-y3-preview-v01"
FRAMES = OUT / "png_frames"
CHROMA_HELPER = Path(r"C:\Users\littl\.codex\skills\.system\imagegen\scripts\remove_chroma_key.py")

SOURCES = [
    "exec-9ad854c7-f744-4aea-b945-8b0d3385c28d.png",
    "exec-1e1bef83-d33e-4b1f-9133-8ae56176f4a9.png",
    "exec-592bc2d7-0378-4d27-8836-256d0368fa32.png",
    "exec-28258d64-ad12-4590-bb8b-4e5358c74c7f.png",
    "exec-4108d159-bd55-4d09-b797-adb0b5a519b7.png",
    "exec-d8b49581-a161-4508-a81e-c55cda795a12.png",
    "exec-3b4b0eb8-d0e9-43fe-be84-c4e7235abd49.png",
    "exec-920806ba-9589-459c-8cad-4aae859bf220.png",
    "exec-0cc9ed95-b6c2-4553-aced-130a401d7c00.png",
    "exec-7c2ba20e-a9a0-4e0d-8fa3-165f0088c136.png",
    "exec-a4f55c4c-1048-4710-bdb2-bba33950345e.png",
    "exec-5a2d5f6e-a218-4c83-af3c-00f2ef651cd8.png",
]


def load_chroma_helper():
    spec = importlib.util.spec_from_file_location("remove_chroma_key", CHROMA_HELPER)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load chroma-key helper: {CHROMA_HELPER}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def make_alpha(source: Path, helper) -> Image.Image:
    with Image.open(source) as image:
        rgba = image.convert("RGBA").resize((360, 480), Image.Resampling.LANCZOS)
    key = helper._sample_border_key(rgba, "border")
    helper._apply_alpha_to_image(
        rgba,
        key=key,
        tolerance=12,
        spill_cleanup=True,
        soft_matte=True,
        transparent_threshold=12,
        opaque_threshold=220,
    )
    rgba = helper._contract_alpha(rgba, 1)
    framed = Image.new("RGBA", (384, 512), (0, 0, 0, 0))
    framed.alpha_composite(rgba, (12, 16))
    return framed


def ensure_safe_edges(image: Image.Image, name: str) -> tuple[int, int, int, int]:
    alpha = image.getchannel("A")
    edge_max = max(
        alpha.crop((0, 0, 384, 1)).getextrema()[1],
        alpha.crop((0, 511, 384, 512)).getextrema()[1],
        alpha.crop((0, 0, 1, 512)).getextrema()[1],
        alpha.crop((383, 0, 384, 512)).getextrema()[1],
    )
    if edge_max != 0:
        raise RuntimeError(f"Visible pixels touch the frame edge: {name}")
    box = alpha.getbbox()
    if box is None:
        raise RuntimeError(f"Empty frame: {name}")
    return box


def expand_to_three_seconds(keyframes: list[Image.Image]) -> list[Image.Image]:
    """Interpolate approved keyframes only; no additional art is introduced."""
    expanded: list[Image.Image] = []
    for index, current in enumerate(keyframes):
        following = keyframes[min(index + 1, len(keyframes) - 1)]
        for amount in (0.0, 1 / 3, 2 / 3):
            expanded.append(Image.blend(current, following, amount))
    return expanded


def build_contact_sheet(images: list[Image.Image]) -> None:
    columns, rows, tile_w, tile_h, gap, margin = 6, 6, 128, 171, 14, 24
    width = margin * 2 + columns * tile_w + (columns - 1) * gap
    height = margin * 2 + rows * tile_h + (rows - 1) * gap
    sheet = Image.new("RGBA", (width, height), (42, 43, 42, 255))
    draw = ImageDraw.Draw(sheet)
    for y in range(0, height, 16):
        for x in range(0, width, 16):
            color = (193, 198, 201, 255) if (x // 16 + y // 16) % 2 == 0 else (137, 143, 147, 255)
            draw.rectangle((x, y, x + 15, y + 15), fill=color)
    font = ImageFont.truetype(r"C:\Windows\Fonts\arial.ttf", 18)
    for index, image in enumerate(images):
        x = margin + (index % columns) * (tile_w + gap)
        y = margin + (index // columns) * (tile_h + gap)
        thumb = image.resize((tile_w, tile_h), Image.Resampling.LANCZOS)
        sheet.alpha_composite(thumb, (x, y))
        draw.text((x + 4, y + 4), f"{index:03d}", font=font, fill=(250, 245, 230, 255), stroke_width=1, stroke_fill=(27, 28, 27, 255))
    sheet.convert("RGB").save(OUT / "contact_sheet_alpha_checker.png", quality=95)


def build_apng(images: list[Image.Image]) -> None:
    preview_frames = [image.resize((576, 768), Image.Resampling.LANCZOS) for image in images]
    preview_frames[0].save(
        OUT / "preview_card_merge_mask_alpha.png",
        save_all=True,
        append_images=preview_frames[1:],
        duration=83,
        loop=0,
        disposal=2,
        blend=1,
    )


def main() -> None:
    if OUT.exists() and any(OUT.rglob("*")):
        raise RuntimeError(f"Preview output already exists: {OUT}")
    FRAMES.mkdir(parents=True, exist_ok=True)
    helper = load_chroma_helper()
    keyframes: list[Image.Image] = []
    manifest_frames = []
    for index, name in enumerate(SOURCES):
        image = make_alpha(GENERATED / name, helper)
        box = ensure_safe_edges(image, name)
        keyframes.append(image)
    frames = expand_to_three_seconds(keyframes)
    for index, image in enumerate(frames):
        box = ensure_safe_edges(image, f"expanded_{index:03d}")
        target = FRAMES / f"card_merge_mask_{index:03d}.png"
        image.save(target, optimize=True)
        manifest_frames.append({"frame": index, "file": target.name, "alpha_bbox": list(box)})
    build_contact_sheet(frames)
    build_apng(frames)
    manifest = {
        "package": "card-merge-mask-y3-preview-v01",
        "temporary_review_only": True,
        "sequence": {"frame_count": 36, "fps": 12, "duration_seconds": 3.0, "frame_size": [384, 512], "format": "RGBA PNG", "recommended_overlay_scale": 1.08},
        "swap_window": {"start_frame": 12, "end_frame": 22, "instruction": "Hide old card and show the new dynamic card within this fully covered window."},
        "import": "Batch-import png_frames in filename ascending order as a Y3 sequence-frame resource.",
        "frames": manifest_frames,
    }
    (OUT / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (OUT / "README.md").write_text(
        "# Card Merge Mask Y3 Preview v01\n\n"
        "临时审核用序列帧。帧号 012-022 为完整遮挡窗口，程序在此期间替换动态卡面。\n"
        "确认或否决后应清理该目录中的预览资源。\n",
        encoding="utf-8",
    )
    print(f"Built {len(frames)} temporary review frames in {OUT}")


if __name__ == "__main__":
    main()

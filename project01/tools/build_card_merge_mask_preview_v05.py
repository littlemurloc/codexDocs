"""Temporal resample of the originally preferred card-merge artwork.

This is a temporary review builder. It adds no visual design or new artwork:
the 12 original v01 stages are only converted to alpha and continuously
cross-dissolved into a 60-frame, three-second Y3 sequence.
"""

from __future__ import annotations

import importlib.util
import json
import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(r"D:\codex\project01")
GENERATED = Path(r"C:\Users\littl\.codex\generated_images\019f11ac-2fcc-7431-b8fe-6f6101936789")
HELPER_PATH = Path(r"C:\Users\littl\.codex\skills\.system\imagegen\scripts\remove_chroma_key.py")
OUT = ROOT / "tmp/card-merge-mask-y3-preview-v05"
FRAMES = OUT / "png_frames"
SIZE = (384, 512)
FPS = 20
COUNT = 60
SOURCES = (
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
)


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
    framed = Image.new("RGBA", SIZE, (0, 0, 0, 0))
    framed.alpha_composite(image, (12, 16))
    return framed


def smooth(value: float) -> float:
    value = max(0.0, min(1.0, value))
    return value * value * (3.0 - 2.0 * value)


def interpolate(keyframes: list[Image.Image]) -> list[Image.Image]:
    """Map every output time sample over the whole source timeline."""
    result: list[Image.Image] = []
    last = len(keyframes) - 1
    for output_index in range(COUNT):
        position = output_index * last / (COUNT - 1)
        before = min(last, math.floor(position))
        after = min(last, before + 1)
        amount = smooth(position - before)
        result.append(Image.blend(keyframes[before], keyframes[after], amount))
    return result


def validate(image: Image.Image, name: str) -> list[int]:
    alpha = image.getchannel("A")
    edge_alpha = max(
        alpha.crop((0, 0, 384, 1)).getextrema()[1],
        alpha.crop((0, 511, 384, 512)).getextrema()[1],
        alpha.crop((0, 0, 1, 512)).getextrema()[1],
        alpha.crop((383, 0, 384, 512)).getextrema()[1],
    )
    if edge_alpha:
        raise RuntimeError(f"Visible edge pixel: {name}")
    return list(alpha.getbbox() or (0, 0, 0, 0))


def checker(size: tuple[int, int]) -> Image.Image:
    canvas = Image.new("RGBA", size, (0, 0, 0, 255))
    draw = ImageDraw.Draw(canvas)
    for y in range(0, size[1], 16):
        for x in range(0, size[0], 16):
            shade = (201, 206, 208, 255) if (x // 16 + y // 16) % 2 == 0 else (140, 147, 151, 255)
            draw.rectangle((x, y, x + 15, y + 15), fill=shade)
    return canvas


def make_previews(images: list[Image.Image]) -> None:
    preview_frames = []
    for image in images:
        preview = checker((576, 768))
        preview.alpha_composite(image.resize((576, 768), Image.Resampling.LANCZOS))
        preview_frames.append(preview.convert("P", palette=Image.Palette.ADAPTIVE))
    preview_frames[0].save(
        OUT / "preview_alpha_checker.gif",
        save_all=True,
        append_images=preview_frames[1:],
        duration=50,
        loop=1,
        disposal=2,
        optimize=False,
    )

    columns, width, height, gap, margin = 10, 96, 128, 10, 20
    rows = math.ceil(len(images) / columns)
    sheet = checker((margin * 2 + columns * width + (columns - 1) * gap, margin * 2 + rows * height + (rows - 1) * gap))
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.truetype(r"C:\Windows\Fonts\arial.ttf", 12)
    for index, image in enumerate(images):
        x = margin + (index % columns) * (width + gap)
        y = margin + (index // columns) * (height + gap)
        sheet.alpha_composite(image.resize((width, height), Image.Resampling.LANCZOS), (x, y))
        draw.text((x + 3, y + 3), f"{index:03d}", font=font, fill=(250, 248, 240, 255), stroke_width=1, stroke_fill=(24, 25, 24, 255))
    sheet.convert("RGB").save(OUT / "contact_sheet_alpha_checker.png", quality=95)


def main() -> None:
    if OUT.exists():
        raise RuntimeError(f"Output already exists: {OUT}")
    FRAMES.mkdir(parents=True)
    helper = load_helper()
    keyframes = [process_source(GENERATED / source, helper) for source in SOURCES]
    images = interpolate(keyframes)
    manifest_frames = []
    for index, image in enumerate(images):
        target = FRAMES / f"card_merge_mask_{index:03d}.png"
        image.save(target, optimize=True)
        manifest_frames.append({"frame": index, "file": target.name, "alpha_bbox": validate(image, target.name)})
    make_previews(images)
    manifest = {
        "package": "card-merge-mask-y3-preview-v05",
        "temporary_review_only": True,
        "sequence": {"frame_count": COUNT, "fps": FPS, "duration_seconds": 3.0, "frame_size": list(SIZE), "format": "RGBA PNG", "recommended_overlay_scale": 1.08, "playback": "once"},
        "visual_basis": "Same 12 original v01 key artworks; only temporal resampling was changed.",
        "motion": "Every adjacent original stage is continuously blended across five to six output samples; no hard frame hold or independent redraw is used.",
        "swap_window": {"start_frame": 20, "end_frame": 37, "instruction": "Use the original full-coverage portion of the effect to replace the dynamic card."},
        "import": "Batch-import png_frames in ascending filename order as a Y3 sequence-frame resource. Set loop to off / play once.",
        "frames": manifest_frames,
    }
    (OUT / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (OUT / "README.md").write_text(
        "# Card Merge Mask Y3 Preview v05\n\n"
        "临时审核包。保留最早 v01 的原始视觉，仅将时间轴重采样为 60 帧 / 20fps / 3 秒。\n"
        "Y3 请关闭循环并单次播放；GIF 仅播放两次，避免循环边界被误认为动画丢帧。\n",
        encoding="utf-8",
    )
    print(f"Built {COUNT} temporally resampled v01 frames in {OUT}")


if __name__ == "__main__":
    main()

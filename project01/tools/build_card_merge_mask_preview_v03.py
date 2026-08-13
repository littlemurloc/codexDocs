"""Compose a smooth deterministic Y3 preview from one stable art master.

No per-frame artwork is regenerated. Every frame derives from the same master,
so ink fibers, seal geometry and gold flecks move continuously instead of jumping.
"""

from __future__ import annotations

import importlib.util
import json
import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont


ROOT = Path(r"D:\codex\project01")
SOURCE = Path(r"C:\Users\littl\.codex\generated_images\019f11ac-2fcc-7431-b8fe-6f6101936789\exec-f06cdfca-c91b-462e-80fb-8989a5a1c825.png")
HELPER_PATH = Path(r"C:\Users\littl\.codex\skills\.system\imagegen\scripts\remove_chroma_key.py")
OUT = ROOT / "tmp/card-merge-mask-y3-preview-v03"
FRAMES = OUT / "png_frames"
SIZE = (384, 512)
FRAME_COUNT = 60
FPS = 20


def helper_module():
    spec = importlib.util.spec_from_file_location("remove_chroma_key", HELPER_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load chroma helper: {HELPER_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def master_image() -> Image.Image:
    helper = helper_module()
    with Image.open(SOURCE) as opened:
        image = opened.convert("RGBA")
    key = helper._sample_border_key(image, "border")
    helper._apply_alpha_to_image(image, key=key, tolerance=12, spill_cleanup=True, soft_matte=True, transparent_threshold=12, opaque_threshold=220)
    image = helper._contract_alpha(image, 1)
    # Preserve full master and leave a safe border in the final frame canvas.
    image.thumbnail((338, 450), Image.Resampling.LANCZOS)
    return image


def smoothstep(value: float) -> float:
    value = max(0.0, min(1.0, value))
    return value * value * (3.0 - 2.0 * value)


def phase(t: float, start: float, end: float) -> float:
    return smoothstep((t - start) / (end - start))


def paste_scaled(canvas: Image.Image, master: Image.Image, scale: float, alpha: float, rotation: float = 0.0) -> None:
    width = max(1, round(master.width * scale))
    height = max(1, round(master.height * scale))
    layer = master.resize((width, height), Image.Resampling.LANCZOS)
    if rotation:
        layer = layer.rotate(rotation, Image.Resampling.BICUBIC, expand=True)
    alpha_channel = layer.getchannel("A").point(lambda value: round(value * alpha))
    layer.putalpha(alpha_channel)
    canvas.alpha_composite(layer, ((SIZE[0] - layer.width) // 2, (SIZE[1] - layer.height) // 2))


def reveal_mask(opacity: float) -> Image.Image:
    """A hidden cover guarantees the old dynamic layout never shows through."""
    mask = Image.new("RGBA", SIZE, (0, 0, 0, 0))
    draw = ImageDraw.Draw(mask)
    draw.rounded_rectangle((48, 32, 336, 480), radius=12, fill=(30, 25, 20, round(255 * opacity)))
    return mask


def gold_sparkles(t: float, strength: float) -> Image.Image:
    layer = Image.new("RGBA", SIZE, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    particles = ((-0.39, -0.38), (0.32, -0.44), (-0.44, 0.28), (0.37, 0.35), (-0.18, -0.50), (0.14, 0.48), (-0.50, -0.04), (0.52, 0.08))
    for index, (x, y) in enumerate(particles):
        pulse = 0.65 + 0.35 * math.sin(t * 12.0 + index * 1.6)
        radius = max(1, round((1.5 + 2.5 * strength) * pulse))
        cx = round(192 + x * (80 + 110 * strength))
        cy = round(256 + y * (110 + 145 * strength))
        alpha = round(210 * strength * pulse)
        draw.ellipse((cx - radius, cy - radius, cx + radius, cy + radius), fill=(229, 186, 92, alpha))
    return layer


def make_frame(index: int, master: Image.Image) -> Image.Image:
    t = index / (FRAME_COUNT - 1)
    enter = phase(t, 0.0, 0.36)
    exit_ = phase(t, 0.61, 1.0)
    # The mask reaches full coverage before the swap and stays there long enough.
    cover = enter if t < 0.36 else (1.0 if t < 0.61 else 1.0 - exit_)
    canvas = Image.new("RGBA", SIZE, (0, 0, 0, 0))
    canvas.alpha_composite(reveal_mask(cover))
    if t < 0.36:
        scale = 0.20 + 0.80 * enter
        alpha = 0.08 + 0.92 * enter
        rotation = 7.0 * (1.0 - enter)
    elif t < 0.61:
        impact = math.exp(-((t - 0.49) / 0.055) ** 2)
        scale = 1.0 + 0.045 * impact
        alpha = 1.0
        rotation = 0.0
    else:
        scale = 1.0 + 0.16 * exit_
        alpha = 1.0 - exit_
        rotation = -5.0 * exit_
    paste_scaled(canvas, master, scale, alpha, rotation)
    flash = math.exp(-((t - 0.49) / 0.040) ** 2)
    if flash > 0.01:
        glow = Image.new("RGBA", SIZE, (0, 0, 0, 0))
        glow_draw = ImageDraw.Draw(glow)
        radius = round(35 + 72 * flash)
        glow_draw.ellipse((192 - radius, 256 - radius, 192 + radius, 256 + radius), fill=(244, 210, 133, round(135 * flash)))
        glow = glow.filter(ImageFilter.GaussianBlur(10))
        canvas.alpha_composite(glow)
    particle_strength = max(0.0, min(1.0, enter * 0.6 + flash + exit_ * 0.8))
    canvas.alpha_composite(gold_sparkles(t, particle_strength))
    return canvas


def validate(image: Image.Image, name: str) -> list[int]:
    alpha = image.getchannel("A")
    edges = (alpha.crop((0, 0, 384, 1)), alpha.crop((0, 511, 384, 512)), alpha.crop((0, 0, 1, 512)), alpha.crop((383, 0, 384, 512)))
    if image.size != SIZE or image.mode != "RGBA" or max(edge.getextrema()[1] for edge in edges) != 0:
        raise RuntimeError(f"Invalid alpha boundary: {name}")
    return list(alpha.getbbox() or (0, 0, 0, 0))


def checkerboard(width: int, height: int) -> Image.Image:
    image = Image.new("RGBA", (width, height), (0, 0, 0, 255))
    draw = ImageDraw.Draw(image)
    for y in range(0, height, 16):
        for x in range(0, width, 16):
            draw.rectangle((x, y, x + 15, y + 15), fill=(198, 202, 204, 255) if (x // 16 + y // 16) % 2 == 0 else (141, 146, 149, 255))
    return image


def preview(frames: list[Image.Image]) -> None:
    sequence = []
    for frame in frames:
        canvas = checkerboard(576, 768)
        canvas.alpha_composite(frame.resize((576, 768), Image.Resampling.LANCZOS))
        sequence.append(canvas.convert("P", palette=Image.Palette.ADAPTIVE))
    sequence[0].save(OUT / "preview_alpha_checker.gif", save_all=True, append_images=sequence[1:], duration=50, loop=0, disposal=2, optimize=False)
    columns, tile_w, tile_h, margin, gap = 10, 96, 128, 20, 10
    rows = (len(frames) + columns - 1) // columns
    sheet = checkerboard(margin * 2 + columns * tile_w + (columns - 1) * gap, margin * 2 + rows * tile_h + (rows - 1) * gap)
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.truetype(r"C:\Windows\Fonts\arial.ttf", 14)
    for index, frame in enumerate(frames):
        x = margin + (index % columns) * (tile_w + gap)
        y = margin + (index // columns) * (tile_h + gap)
        sheet.alpha_composite(frame.resize((tile_w, tile_h), Image.Resampling.LANCZOS), (x, y))
        draw.text((x + 2, y + 2), f"{index:03d}", font=font, fill=(248, 244, 232, 255), stroke_width=1, stroke_fill=(30, 30, 28, 255))
    sheet.convert("RGB").save(OUT / "contact_sheet_alpha_checker.png", quality=95)


def main() -> None:
    if OUT.exists() and any(OUT.rglob("*")):
        raise RuntimeError(f"Output already exists: {OUT}")
    FRAMES.mkdir(parents=True, exist_ok=True)
    master = master_image()
    frames = [make_frame(index, master) for index in range(FRAME_COUNT)]
    manifest_frames = []
    for index, frame in enumerate(frames):
        target = FRAMES / f"card_merge_ink_mask_{index:03d}.png"
        frame.save(target, optimize=True)
        manifest_frames.append({"frame": index, "file": target.name, "alpha_bbox": validate(frame, target.name)})
    preview(frames)
    manifest = {
        "package": "card-merge-mask-y3-preview-v03",
        "temporary_review_only": True,
        "sequence": {"frame_count": FRAME_COUNT, "fps": FPS, "duration_seconds": 3.0, "frame_size": list(SIZE), "format": "RGBA PNG", "recommended_overlay_scale": 1.08},
        "swap_window": {"start_frame": 22, "end_frame": 35, "instruction": "The hidden opaque card mask is at full coverage. Replace the dynamic card in this window."},
        "motion": "All frames use one master artwork transformed continuously by deterministic curves; no independently regenerated per-frame art.",
        "visual": "Charcoal ink, aged bronze seal and restrained antique-gold dust. Frame resources have transparent backgrounds and no card art.",
        "import": "Batch-import png_frames in ascending filename order as a Y3 sequence-frame resource.",
        "frames": manifest_frames,
    }
    (OUT / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (OUT / "README.md").write_text(
        "# Card Merge Ink Mask Y3 Preview v03\n\n"
        "临时审核资源。60 帧、20fps、3 秒。022-035 为完整遮挡窗口，程序在此期间替换动态卡面。\n"
        "每帧来自同一张稳定母版的连续变换，不使用独立 AI 重绘帧。GIF 棋盘格仅用于检查透明，不是游戏资源。\n",
        encoding="utf-8",
    )
    print(f"Built {len(frames)} smooth preview frames in {OUT}")


if __name__ == "__main__":
    main()

"""Build a smooth, layered card-synthesis preview without card artwork."""

from __future__ import annotations

import importlib.util
import json
import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont


ROOT = Path(r"D:\codex\project01")
GENERATED = Path(r"C:\Users\littl\.codex\generated_images\019f11ac-2fcc-7431-b8fe-6f6101936789")
RING_SOURCE = GENERATED / "exec-923ad5c9-218d-41f6-bd65-583ec9857ddb.png"
BURST_SOURCE = GENERATED / "exec-72772848-37d2-4f08-934a-9ffe4e285191.png"
HELPER_PATH = Path(r"C:\Users\littl\.codex\skills\.system\imagegen\scripts\remove_chroma_key.py")
OUT = ROOT / "tmp/card-merge-mask-y3-preview-v04"
FRAMES = OUT / "png_frames"
SIZE = (384, 512)
FPS = 20
COUNT = 60


def load_helper():
    spec = importlib.util.spec_from_file_location("remove_chroma_key", HELPER_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load chroma helper: {HELPER_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def cutout(path: Path, size: tuple[int, int]):
    helper = load_helper()
    with Image.open(path) as source:
        image = source.convert("RGBA")
    key = helper._sample_border_key(image, "border")
    helper._apply_alpha_to_image(image, key=key, tolerance=12, spill_cleanup=True, soft_matte=True, transparent_threshold=12, opaque_threshold=220)
    image = helper._contract_alpha(image, 1)
    image.thumbnail(size, Image.Resampling.LANCZOS)
    return image


def smooth(value: float) -> float:
    value = max(0.0, min(1.0, value))
    return value * value * (3 - 2 * value)


def ramp(t: float, a: float, b: float) -> float:
    return smooth((t - a) / (b - a))


def composite_scaled(canvas: Image.Image, source: Image.Image, scale: float, alpha: float, angle: float) -> None:
    layer = source.resize((max(1, round(source.width * scale)), max(1, round(source.height * scale))), Image.Resampling.LANCZOS)
    if angle:
        layer = layer.rotate(angle, Image.Resampling.BICUBIC, expand=True)
    layer.putalpha(layer.getchannel("A").point(lambda value: round(value * alpha)))
    canvas.alpha_composite(layer, ((SIZE[0] - layer.width) // 2, (SIZE[1] - layer.height) // 2))


def sparkles(t: float, strength: float) -> Image.Image:
    canvas = Image.new("RGBA", SIZE, (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)
    positions = ((-0.47, -0.32), (0.41, -0.37), (-0.43, 0.29), (0.47, 0.25), (-0.18, -0.51), (0.2, 0.49), (-0.53, 0.03), (0.52, -0.02), (0.0, -0.56), (0.0, 0.55))
    for index, (x, y) in enumerate(positions):
        drift = 0.12 * math.sin(t * 8 + index)
        pulse = 0.65 + 0.35 * math.sin(t * 14 + index * 1.7)
        radius = max(1, round((1.1 + 2.4 * strength) * pulse))
        cx = round(192 + (x + drift * (1 if index % 2 else -1)) * (88 + 85 * strength))
        cy = round(256 + y * (88 + 72 * strength))
        draw.ellipse((cx-radius, cy-radius, cx+radius, cy+radius), fill=(231, 187, 87, round(220 * strength * pulse)))
    return canvas


def flash_cover(opacity: float) -> Image.Image:
    """Only exists for the short swap window, hiding any dynamic card layout change."""
    canvas = Image.new("RGBA", SIZE, (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)
    draw.rounded_rectangle((48, 32, 336, 480), radius=12, fill=(245, 229, 185, round(255 * opacity)))
    return canvas


def make_frame(index: int, ring: Image.Image, burst: Image.Image) -> Image.Image:
    t = index / (COUNT - 1)
    enter = ramp(t, 0.0, 0.32)
    release = ramp(t, 0.40, 1.0)
    flash = math.exp(-((t - 0.365) / 0.055) ** 2)
    # Keep the actual card replacement inside a stable, fully opaque window.
    # Only the two frames on either side fade, so the cover never looks like
    # a hesitant half-transparent card-shaped panel.
    if 19 <= index <= 24:
        swap_cover = 1.0
    elif index == 18 or index == 25:
        swap_cover = 0.55
    elif index == 17 or index == 26:
        swap_cover = 0.18
    else:
        swap_cover = 0.0
    canvas = Image.new("RGBA", SIZE, (0, 0, 0, 0))
    # Ring stays off the card center; it is one stable art layer with continuous motion.
    ring_scale = 0.58 + 0.22 * enter + 0.02 * release
    ring_alpha = 0.12 + 0.88 * enter
    if t > 0.40:
        ring_alpha = max(0.0, 1.0 - release)
    composite_scaled(canvas, ring, ring_scale, ring_alpha, 8.0 - 18.0 * t)
    if swap_cover:
        canvas.alpha_composite(flash_cover(swap_cover))
    burst_alpha = min(1.0, flash * 1.45)
    if burst_alpha > 0.01:
        composite_scaled(canvas, burst, 0.52 + 0.34 * flash, burst_alpha, 0.0)
    canvas.alpha_composite(sparkles(t, min(1.0, 0.35 + enter * 0.65 + flash - release * 0.25)))
    return canvas


def validate(image: Image.Image, name: str) -> list[int]:
    alpha = image.getchannel("A")
    edges = (alpha.crop((0, 0, 384, 1)), alpha.crop((0, 511, 384, 512)), alpha.crop((0, 0, 1, 512)), alpha.crop((383, 0, 384, 512)))
    if max(edge.getextrema()[1] for edge in edges):
        raise RuntimeError(f"Visible edge pixel: {name}")
    return list(alpha.getbbox() or (0, 0, 0, 0))


def checker(size: tuple[int, int]) -> Image.Image:
    canvas = Image.new("RGBA", size, (0, 0, 0, 255))
    draw = ImageDraw.Draw(canvas)
    for y in range(0, size[1], 16):
        for x in range(0, size[0], 16):
            draw.rectangle((x, y, x+15, y+15), fill=(199, 204, 206, 255) if (x//16 + y//16) % 2 == 0 else (140, 146, 149, 255))
    return canvas


def previews(frames: list[Image.Image]) -> None:
    animated = []
    for frame in frames:
        preview = checker((576, 768))
        preview.alpha_composite(frame.resize((576, 768), Image.Resampling.LANCZOS))
        animated.append(preview.convert("P", palette=Image.Palette.ADAPTIVE))
    animated[0].save(OUT / "preview_alpha_checker.gif", save_all=True, append_images=animated[1:], duration=50, loop=0, disposal=2, optimize=False)
    cols, w, h, gap, margin = 10, 96, 128, 10, 20
    rows = (len(frames)+cols-1)//cols
    sheet = checker((margin*2+cols*w+(cols-1)*gap, margin*2+rows*h+(rows-1)*gap))
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.truetype(r"C:\Windows\Fonts\arial.ttf", 14)
    for index, frame in enumerate(frames):
        x = margin+(index%cols)*(w+gap); y=margin+(index//cols)*(h+gap)
        sheet.alpha_composite(frame.resize((w,h),Image.Resampling.LANCZOS),(x,y))
        draw.text((x+2,y+2),f"{index:03d}",font=font,fill=(248,244,232,255),stroke_width=1,stroke_fill=(30,30,28,255))
    sheet.convert("RGB").save(OUT / "contact_sheet_alpha_checker.png", quality=95)


def main():
    if OUT.exists() and any(OUT.rglob("*")):
        raise RuntimeError(f"Output already exists: {OUT}")
    FRAMES.mkdir(parents=True, exist_ok=True)
    ring = cutout(RING_SOURCE, (336, 448))
    burst = cutout(BURST_SOURCE, (310, 412))
    frames = [make_frame(index, ring, burst) for index in range(COUNT)]
    items=[]
    for index, frame in enumerate(frames):
        target=FRAMES/f"card_merge_ink_gold_{index:03d}.png"
        frame.save(target,optimize=True)
        items.append({"frame":index,"file":target.name,"alpha_bbox":validate(frame,target.name)})
    previews(frames)
    manifest={
        "package":"card-merge-mask-y3-preview-v04", "temporary_review_only":True,
        "sequence":{"frame_count":COUNT,"fps":FPS,"duration_seconds":3.0,"frame_size":list(SIZE),"format":"RGBA PNG","recommended_overlay_scale":1.08},
        "swap_window":{"start_frame":19,"end_frame":24,"instruction":"White-gold flash cover is fully opaque. Replace the dynamic card only in this 0.30-second window."},
        "motion":"A single fixed ink-ring and burst artwork are transformed continuously for every frame; no independent AI redraws.",
        "visual":"Ink-gold orbit stays around the card; a bright flash, not a black panel, briefly covers the dynamic-card swap.",
        "import":"Batch-import png_frames in ascending filename order as a Y3 sequence-frame resource.", "frames":items}
    (OUT/"manifest.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    (OUT/"README.md").write_text("# Card Merge Ink Gold Mask Y3 Preview v04\n\n临时审核资源。60 帧、20fps、3 秒。019-024 为白金爆闪完整遮挡窗口，程序在此期间替换动态卡面。\nGIF 中的棋盘格仅用于看透明，不属于游戏资源。\n",encoding="utf-8")
    print(f"Built {COUNT} smooth frames in {OUT}")


if __name__ == "__main__":
    main()

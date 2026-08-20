"""Compose non-archival review previews for the phase-alert resource packages."""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(r"D:\codex\project01")
PREP = ROOT / "assets/art/ui/export/phase-alert-preparation-v01/transparent"
RESULTS = ROOT / "assets/art/ui/export/phase-alert-results-v01/transparent"
OUT = ROOT / "tmp/phase-alert-combined-preview.png"


def visible(image: Image.Image) -> Image.Image:
    rgba = image.convert("RGBA")
    box = rgba.getchannel("A").getbbox()
    return rgba.crop(box) if box else rgba


def place(canvas: Image.Image, source: Path, center: tuple[int, int], size: tuple[int, int]) -> None:
    with Image.open(source) as image:
        layer = visible(image)
    layer.thumbnail(size, Image.Resampling.LANCZOS)
    canvas.alpha_composite(layer, (center[0] - layer.width // 2, center[1] - layer.height // 2))


def panel(canvas: Image.Image, rect: tuple[int, int, int, int], label: str) -> tuple[int, int]:
    x, y, width, height = rect
    draw = ImageDraw.Draw(canvas)
    draw.rounded_rectangle((x, y, x + width, y + height), radius=14, fill=(33, 32, 28, 232), outline=(133, 113, 75, 170), width=2)
    font = ImageFont.truetype(r"C:\Windows\Fonts\msyh.ttc", 24)
    draw.text((x + 24, y + 20), label, font=font, fill=(226, 213, 186, 255))
    return (x + width // 2, y + height // 2 + 12)


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    canvas = Image.new("RGBA", (1920, 1280), (19, 19, 17, 255))
    draw = ImageDraw.Draw(canvas)
    # A quiet neutral battlefield-style review ground; it is not part of any asset package.
    for y in range(canvas.height):
        shade = int(27 + 17 * y / canvas.height)
        draw.line((0, y, canvas.width, y), fill=(shade, shade - 2, shade - 7, 255))

    centers = [
        panel(canvas, (50, 50, 880, 560), "备战阶段"),
        panel(canvas, (990, 50, 880, 560), "战斗开始"),
        panel(canvas, (50, 670, 880, 560), "战斗胜利"),
        panel(canvas, (990, 670, 880, 560), "战斗失败"),
    ]

    for index, title in enumerate(("title_beizhan.png", "title_battle_start.png")):
        cx, cy = centers[index]
        place(canvas, PREP / "ink_exit_trail.png", (cx + 42, cy + 18), (760, 260))
        place(canvas, PREP / "ink_main.png", (cx, cy), (760, 270))
        place(canvas, PREP / "ink_entry_splatter.png", (cx - 286, cy + 54), (192, 192))
        place(canvas, PREP / title, (cx + 24, cy), (590, 205))
        if title == "title_beizhan.png":
            place(canvas, PREP / "seal_vermilion.png", (cx - 280, cy + 64), (92, 112))

    cx, cy = centers[2]
    place(canvas, RESULTS / "victory_gold_ring.png", (cx, cy), (330, 330))
    place(canvas, RESULTS / "title_battle_victory.png", (cx, cy + 8), (590, 270))
    place(canvas, RESULTS / "victory_gold_flecks.png", (cx, cy), (440, 440))

    cx, cy = centers[3]
    place(canvas, RESULTS / "defeat_vermilion_stroke.png", (cx, cy), (135, 365))
    place(canvas, RESULTS / "defeat_fissures_ash.png", (cx, cy + 48), (390, 235))
    place(canvas, RESULTS / "title_battle_defeat.png", (cx, cy + 10), (590, 270))

    canvas.convert("RGB").save(OUT, quality=95)
    print(OUT)


if __name__ == "__main__":
    main()

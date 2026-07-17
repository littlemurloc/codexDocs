from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw


ROOT = Path(r"D:\codex\project01")
PACKAGE = ROOT / "assets" / "ui" / "export" / "skill-icons-medallion-v01"
SOURCE = PACKAGE / "source"
OUT = PACKAGE / "icons_128"
PREVIEW = PACKAGE / "preview"
WORK = ROOT / "tmp" / "skill-icons-medallion-v01-keyed"
PYTHON = Path(r"C:\Users\littl\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe")
KEYER = Path(r"C:\Users\littl\.codex\skills\.system\imagegen\scripts\remove_chroma_key.py")


def checker(size: tuple[int, int], cell: int) -> Image.Image:
    image = Image.new("RGB", size, (49, 53, 52))
    draw = ImageDraw.Draw(image)
    for y in range(0, size[1], cell):
        for x in range(0, size[0], cell):
            if (x // cell + y // cell) % 2 == 0:
                draw.rectangle((x, y, x + cell - 1, y + cell - 1), fill=(86, 90, 88))
    return image


def normalize(keyed: Path, final: Path) -> dict[str, int]:
    image = Image.open(keyed).convert("RGBA")
    bbox = image.getchannel("A").getbbox()
    if not bbox:
        raise RuntimeError(f"Empty alpha: {keyed.name}")
    subject = image.crop(bbox)
    target = 120
    scale = min(target / subject.width, target / subject.height)
    w, h = round(subject.width * scale), round(subject.height * scale)
    subject = subject.resize((w, h), Image.Resampling.LANCZOS)
    master = Image.new("RGBA", (128, 128), (0, 0, 0, 0))
    master.alpha_composite(subject, ((128 - w) // 2, (128 - h) // 2))
    master.save(final, optimize=True)
    return {"bbox_left": bbox[0], "bbox_top": bbox[1], "bbox_right": bbox[2], "bbox_bottom": bbox[3], "placed_width": w, "placed_height": h}


def grid(files: list[Path], out: Path, cell_size: int, checker_cell: int) -> None:
    cols = 8
    rows = (len(files) + cols - 1) // cols
    gap, pad = 8, 8
    canvas = checker((pad * 2 + cols * cell_size + (cols - 1) * gap, pad * 2 + rows * cell_size + (rows - 1) * gap), checker_cell).convert("RGBA")
    for index, file in enumerate(files):
        icon = Image.open(file).convert("RGBA").resize((cell_size, cell_size), Image.Resampling.LANCZOS)
        x = pad + (index % cols) * (cell_size + gap)
        y = pad + (index // cols) * (cell_size + gap)
        canvas.alpha_composite(icon, (x, y))
    canvas.convert("RGB").save(out, optimize=True)


def edge_max(path: Path) -> int:
    alpha = Image.open(path).convert("RGBA").getchannel("A")
    w, h = alpha.size
    pixels = list(alpha.crop((0, 0, w, 1)).getdata())
    pixels += list(alpha.crop((0, h - 1, w, h)).getdata())
    pixels += list(alpha.crop((0, 0, 1, h)).getdata())
    pixels += list(alpha.crop((w - 1, 0, w, h)).getdata())
    return max(pixels)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    PREVIEW.mkdir(parents=True, exist_ok=True)
    WORK.mkdir(parents=True, exist_ok=True)
    sources = sorted(SOURCE.glob("*_source.png"), key=lambda p: p.name)
    if len(sources) != 48:
        raise RuntimeError(f"Expected 48 source images, found {len(sources)}")

    assets = []
    finals = []
    for source in sources:
        stem = source.name.removesuffix("_source.png")
        keyed = WORK / f"{stem}_keyed.png"
        final = OUT / f"{stem}.png"
        if final.exists():
            normalization = {"status": "generated during prior batch pass"}
        else:
            subprocess.run([
                str(PYTHON), str(KEYER), "--input", str(source), "--out", str(keyed),
                "--auto-key", "border", "--soft-matte", "--transparent-threshold", "12",
                "--opaque-threshold", "220", "--despill", "--edge-contract", "1",
            ], check=True)
            normalization = normalize(keyed, final)
        hero, skill = stem.split("_", 1)
        assets.append({
            "hero": hero,
            "skill": skill,
            "file": f"icons_128/{final.name}",
            "source": f"source/{source.name}",
            "dimensions": [128, 128],
            "format": "PNG RGBA",
            "normalization": normalization,
            "edge_alpha_max": edge_max(final),
        })
        finals.append(final)

    grid(finals, PREVIEW / "preview_alpha_checker_128px.png", 128, 16)
    grid(finals, PREVIEW / "preview_actual_48px.png", 48, 6)
    manifest = {"version": "v01", "style": "three-kingdoms jade-and-gold cinematic skill medallions", "asset_count": len(assets), "assets": assets}
    (PACKAGE / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    (PACKAGE / "README.md").write_text(
        "# Hero Skill Icons Medallion V01\n\n"
        "48 张第一批英雄技能图标。最终图为 `128x128` RGBA PNG，使用 `英雄_技能.png` 中文命名。\n\n"
        "- `icons_128/`: 游戏接入资源。\n"
        "- `source/`: 高分辨率洋红底源图，保留以便返工。\n"
        "- `preview/preview_alpha_checker_128px.png`: 透明边缘检查。\n"
        "- `preview/preview_actual_48px.png`: 常态小尺寸可读性检查。\n"
        "- `manifest.json`: 资源映射与尺寸记录。\n",
        encoding="utf-8",
    )
    print(json.dumps({"assets": len(assets), "edge_alpha_max": max(a["edge_alpha_max"] for a in assets)}, ensure_ascii=False))


if __name__ == "__main__":
    main()

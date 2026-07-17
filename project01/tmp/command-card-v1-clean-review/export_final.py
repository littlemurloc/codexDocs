from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw


ROOT = Path(r"D:\codex\project01")
GENERATED = Path(r"C:\Users\littl\.codex\generated_images\019f11ac-2fcc-7431-b8fe-6f6101936789")
PYTHON = Path(r"C:\Users\littl\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe")
CHROMA_HELPER = Path(r"C:\Users\littl\.codex\skills\.system\imagegen\scripts\remove_chroma_key.py")
OUT = ROOT / "assets" / "ui" / "command-cards" / "v01"

ASSETS = [
    ("cmd_break_execute", "斩将令", "exec-37b94b41-88d5-4bae-b22c-f4af7421a2d2.png"),
    ("cmd_break_formation", "破阵令", "exec-f9ac4a3f-6525-4384-a5c6-fb5fee769ced.png"),
    ("cmd_flying_raid", "奇袭令", "exec-1aff653a-015e-4a47-a2cc-e114f115d09d.png"),
    ("cmd_flying_charge", "奔袭令", "exec-c5678aa0-6d16-42fb-a17d-7eeb63600210.png"),
    ("cmd_fire_burn_camp", "焚营令", "exec-049a682a-1646-4ce5-9273-0f5ce189a039.png"),
    ("cmd_fire_attack", "火攻令", "exec-7c6e9c3e-7832-429b-ab40-fe5680895dba.png"),
    ("cmd_chain_link_order", "连环令", "exec-00e375c5-5c53-46f8-960b-5f62dda918b6.png"),
    ("cmd_chain_burn_boats", "焚舟令", "exec-f4f479cb-494e-4800-99a5-03770b43a036.png"),
    ("cmd_ambush_order", "伏兵令", "exec-b26da728-72f4-4131-abce-8097e6cca159.png"),
    ("cmd_ambush_ten_sides", "十面埋伏令", "exec-3c41c94c-a7a0-4362-8590-b1ac68cbb72d.png"),
    ("cmd_independent_inspire", "鼓舞令", "exec-33635b99-7e4f-4429-97d3-e64021659477.png"),
    ("cmd_independent_hold", "固守令", "exec-7f0c8c2e-7c5c-470b-b1a3-ee838c100a96.png"),
]


def checkerboard(size: tuple[int, int], cell: int = 16) -> Image.Image:
    w, h = size
    image = Image.new("RGB", size, (48, 52, 51))
    draw = ImageDraw.Draw(image)
    for y in range(0, h, cell):
        for x in range(0, w, cell):
            if (x // cell + y // cell) % 2 == 0:
                draw.rectangle((x, y, x + cell - 1, y + cell - 1), fill=(82, 87, 85))
    return image


def normalize_to_master(intermediate: Path, output: Path) -> dict[str, int]:
    image = Image.open(intermediate).convert("RGBA")
    alpha = image.getchannel("A")
    bbox = alpha.getbbox()
    if not bbox:
        raise RuntimeError(f"No opaque pixels after key removal: {intermediate}")

    # Preserve the complete framing; fit it into a centered 512px master with a 12% transparent safe edge.
    subject = image.crop(bbox)
    max_content = 512 - 2 * 62
    scale = min(max_content / subject.width, max_content / subject.height)
    target_size = (round(subject.width * scale), round(subject.height * scale))
    subject = subject.resize(target_size, Image.Resampling.LANCZOS)
    master = Image.new("RGBA", (512, 512), (0, 0, 0, 0))
    x = (512 - target_size[0]) // 2
    y = (512 - target_size[1]) // 2
    master.alpha_composite(subject, (x, y))
    master.save(output, optimize=True)
    return {"source_width": image.width, "source_height": image.height, "bbox_left": bbox[0], "bbox_top": bbox[1], "bbox_right": bbox[2], "bbox_bottom": bbox[3], "placed_width": target_size[0], "placed_height": target_size[1]}


def make_grid(files: list[Path], out_path: Path, thumb: int) -> None:
    cols = 4
    rows = (len(files) + cols - 1) // cols
    gap = 16 if thumb > 64 else 8
    pad = gap
    bg = checkerboard((pad * 2 + cols * thumb + (cols - 1) * gap, pad * 2 + rows * thumb + (rows - 1) * gap), max(4, thumb // 8)).convert("RGBA")
    for i, file in enumerate(files):
        icon = Image.open(file).convert("RGBA").resize((thumb, thumb), Image.Resampling.LANCZOS)
        x = pad + (i % cols) * (thumb + gap)
        y = pad + (i // cols) * (thumb + gap)
        bg.alpha_composite(icon, (x, y))
    bg.convert("RGB").save(out_path, optimize=True)


def edge_alpha_max(image_path: Path) -> int:
    alpha = Image.open(image_path).convert("RGBA").getchannel("A")
    w, h = alpha.size
    values = list(alpha.crop((0, 0, w, 1)).getdata())
    values += list(alpha.crop((0, h - 1, w, h)).getdata())
    values += list(alpha.crop((0, 0, 1, h)).getdata())
    values += list(alpha.crop((w - 1, 0, w, h)).getdata())
    return max(values)


def main() -> None:
    source_dir = OUT / "source"
    transparent_dir = OUT / "transparent"
    preview_dir = OUT / "preview"
    work_dir = ROOT / "tmp" / "command-card-v1-final-intermediate"
    for folder in (source_dir, transparent_dir, preview_dir, work_dir):
        folder.mkdir(parents=True, exist_ok=True)

    manifest_assets = []
    final_files = []
    for asset_id, name, generated_name in ASSETS:
        original = GENERATED / generated_name
        source = source_dir / f"{asset_id}_source.png"
        intermediate = work_dir / f"{asset_id}_keyed.png"
        final = transparent_dir / f"{asset_id}.png"
        shutil.copy2(original, source)
        subprocess.run([
            str(PYTHON), str(CHROMA_HELPER),
            "--input", str(source),
            "--out", str(intermediate),
            "--auto-key", "border",
            "--soft-matte",
            "--transparent-threshold", "12",
            "--opaque-threshold", "220",
            "--despill",
            "--edge-contract", "1",
        ], check=True)
        details = normalize_to_master(intermediate, final)
        manifest_assets.append({
            "command_card_id": asset_id,
            "display_name": name,
            "file": f"transparent/{asset_id}.png",
            "source": f"source/{asset_id}_source.png",
            "dimensions": [512, 512],
            "format": "PNG RGBA",
            "safe_edge": "12% transparent margin",
            "normalization": details,
        })
        final_files.append(final)

    make_grid(final_files, preview_dir / "preview_alpha_checker.png", 128)
    make_grid(final_files, preview_dir / "preview_48px.png", 48)
    validation = []
    for file in final_files:
        image = Image.open(file).convert("RGBA")
        validation.append({
            "file": file.name,
            "dimensions": list(image.size),
            "mode": image.mode,
            "edge_alpha_max": edge_alpha_max(file),
        })
    manifest = {
        "package": "command-cards-v01",
        "version": "v01",
        "status": "approved-clean-art exported to transparent masters",
        "asset_count": len(manifest_assets),
        "assets": manifest_assets,
        "validation": validation,
    }
    (OUT / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    (OUT / "README.md").write_text(
        "# Command Card Art V01\n\n"
        "12 张军令卡中央插图资源。所有最终文件为 512x512 RGBA PNG，外缘保留 12% 透明安全区。\n\n"
        "- `source/`: 已确认清稿阶段的原始色键图，保留供溯源。\n"
        "- `transparent/`: 游戏接入用无文字透明主资源。\n"
        "- `preview/preview_alpha_checker.png`: 透明边缘检查。\n"
        "- `preview/preview_48px.png`: 常态小尺寸辨识度检查。\n"
        "- `manifest.json`: 卡牌 ID、文件映射与导出校验。\n",
        encoding="utf-8",
    )
    print(json.dumps({"output": str(OUT), "asset_count": len(final_files), "validation": validation}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

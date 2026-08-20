"""Build approved buff-status icons: chroma removal, resize, alpha QA and preview."""

from __future__ import annotations

import json
import importlib.util
from pathlib import Path

from PIL import Image, ImageDraw


ROOT = Path(r"D:\codex\project01")
GENERATED = Path(r"C:\Users\littl\.codex\generated_images\019f11ac-2fcc-7431-b8fe-6f6101936789")
OUT = ROOT / "assets/art/ui/export/buff-status-icons-v02"
TRANSPARENT = OUT / "transparent"
PREVIEW = OUT / "preview"
REMOVER = Path(r"C:\Users\littl\.codex\skills\.system\imagegen\scripts\remove_chroma_key.py")

ICONS = [
    ("嘲讽", "exec-01dd8828-cc9b-4679-b446-3bc51ea553f5.png", "怒面与声浪"),
    ("沉默", "exec-9bd2b2c2-9c5a-44fa-bdde-38c23223f580.png", "封口面具"),
    ("持续恢复", "exec-18ad5062-b871-4812-a256-e4f441cd841b.png", "药叶、水滴与回环"),
    ("攻击降低", "exec-0bf5f26c-3df9-447f-835b-e4dae4d792b8.png", "残剑与下箭头"),
    ("攻击提升", "exec-87ec44c4-f33b-4f9e-9afd-f46c5e5d9bb7.png", "上扬直剑与上箭头"),
    ("攻速降低", "exec-18348a31-ac4b-45fd-8123-2391700cbb9c.png", "短促枪锋与下箭头"),
    ("攻速提升", "exec-4f68be61-d65c-4eec-a15b-a3abb2a74afa.png", "速度枪锋与上箭头"),
    ("护盾", "exec-f14a74a4-93e3-4e8b-8e44-1b9ce7bfac20.png", "古盾"),
    ("闪避", "exec-adef47b0-7045-4ff7-ab8a-cb1f2dcfa5ed.png", "闪身武人"),
    ("受伤减免", "exec-720651e6-2574-4ffb-aecb-256270707398.png", "承击护盾"),
    ("受伤提升", "exec-be7e7848-fdf8-4513-b399-cb508acd16b3.png", "受击甲胄与上箭头"),
    ("伤害降低", "exec-dbfff208-b6a9-4953-9e2f-dfbe84e0ebe5.png", "弱化斩击与下箭头"),
    ("伤害提升", "exec-6a5f785d-bfe1-45a2-9137-ac78d236dee8.png", "强化斩击与上箭头"),
    ("移速降低", "exec-e3905d5d-075b-4211-9732-bda38895a758.png", "锁链战靴与下箭头"),
    ("移速提升", "exec-5bc3bf36-4a14-4d70-9516-eb3dab3c0004.png", "疾行战靴与上箭头"),
    ("隐身", "exec-46ae9408-6942-4c02-956d-833ce65ba135.png", "淡化武人与闭眼"),
    ("护甲降低", "exec-0734d82a-8b65-4286-93f2-5317a5fcd900.png", "裂甲与下箭头"),
    ("护甲提升", "exec-84a686d0-7124-4f9d-b1b5-7ef96040727e.png", "整甲与上箭头"),
]


def remove_chroma(source: Path, target: Path) -> None:
    # Reuse the imagegen helper's chroma-matte implementation in-process so the
    # batch remains deterministic and does not leave child conversion processes.
    spec = importlib.util.spec_from_file_location("remove_chroma_key", REMOVER)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load chroma helper: {REMOVER}")
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    with Image.open(source) as image:
        rgba = image.convert("RGBA").resize((256, 256), Image.Resampling.LANCZOS)
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
    target.parent.mkdir(parents=True, exist_ok=True)
    rgba.save(target, optimize=True)


def resize_and_validate(path: Path) -> dict[str, object]:
    with Image.open(path) as source:
        visible = source.convert("RGBA")
    # Preserve an explicit transparent safety border even if a source has a soft edge.
    visible.thumbnail((224, 224), Image.Resampling.LANCZOS)
    image = Image.new("RGBA", (256, 256), (0, 0, 0, 0))
    image.alpha_composite(visible, ((256 - visible.width) // 2, (256 - visible.height) // 2))
    image.save(path, optimize=True)
    alpha = image.getchannel("A")
    edges = [alpha.crop((0, 0, 256, 1)), alpha.crop((0, 255, 256, 256)),
             alpha.crop((0, 0, 1, 256)), alpha.crop((255, 0, 256, 256))]
    if any(edge.getextrema()[1] != 0 for edge in edges):
        raise RuntimeError(f"Outer alpha edge is not transparent: {path.name}")
    bbox = alpha.getbbox()
    if bbox is None:
        raise RuntimeError(f"No visible icon pixels: {path.name}")
    return {"file": path.name, "size": [256, 256], "alpha_bbox": list(bbox), "outer_edge_alpha": 0}


def build_checker(paths: list[Path]) -> None:
    columns, rows, tile, gap, margin = 6, 3, 256, 18, 28
    width = margin * 2 + columns * tile + (columns - 1) * gap
    height = margin * 2 + rows * tile + (rows - 1) * gap
    canvas = Image.new("RGBA", (width, height), (35, 38, 42, 255))
    draw = ImageDraw.Draw(canvas)
    light, dark, step = (203, 207, 210, 255), (145, 151, 157, 255), 16
    for y in range(0, height, step):
        for x in range(0, width, step):
            draw.rectangle((x, y, x + step - 1, y + step - 1), fill=light if (x // step + y // step) % 2 == 0 else dark)
    for index, path in enumerate(paths):
        x = margin + (index % columns) * (tile + gap)
        y = margin + (index // columns) * (tile + gap)
        with Image.open(path) as icon:
            canvas.alpha_composite(icon.convert("RGBA"), (x, y))
    canvas.save(PREVIEW / "preview_alpha_checker.png", optimize=True)


def main() -> None:
    if OUT.exists() and any(path.is_file() for path in OUT.rglob("*")):
        raise RuntimeError(f"Output directory already exists: {OUT}")
    TRANSPARENT.mkdir(parents=True)
    PREVIEW.mkdir(parents=True)
    report: list[dict[str, object]] = []
    output_paths: list[Path] = []
    for name, source_name, motif in ICONS:
        source = GENERATED / source_name
        target = TRANSPARENT / f"{name}.png"
        if not source.exists():
            raise FileNotFoundError(source)
        remove_chroma(source, target)
        item = resize_and_validate(target)
        item["name"] = name
        item["motif"] = motif
        report.append(item)
        output_paths.append(target)
    build_checker(output_paths)
    manifest = {
        "package": "buff-status-icons-v02",
        "version": "v02",
        "spec": {"width": 256, "height": 256, "format": "PNG RGBA", "background": "transparent"},
        "style": "ivory-white and pale-silver subject, charcoal contours, no fixed backing plate or text",
        "icons": report,
        "validation": {"count": len(report), "alpha_outer_edge": 0, "chroma_key": "#ff00ff removed"},
    }
    (OUT / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = [
        "# Buff Status Icons v02", "", "18 个单位状态图标，已统一为白银基底的透明 PNG。", "",
        "## 规格", "", "- 每张：`256x256` RGBA PNG", "- 透明背景，四边 alpha 为 0", "- 无文字、无卡牌底板；可直接用于公告板或特效贴图", "",
        "## 文件", "",
    ]
    lines.extend(f"- `{name}.png`：{motif}" for name, _, motif in ICONS)
    lines.extend(["", "`preview/preview_alpha_checker.png` 仅用于透明边缘检查，不作为运行时资源。", ""])
    (OUT / "README.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"Built {len(report)} icons in {OUT}")


if __name__ == "__main__":
    main()

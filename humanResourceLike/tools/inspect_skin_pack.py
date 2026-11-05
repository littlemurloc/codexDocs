#!/usr/bin/env python3
"""看一眼 UI 素材包的结构，重点是 sheets.json 里的 9-slice 边距。

用法：
    python tools/inspect_skin_pack.py <解压后的文件夹>

为什么要有这一步：9-slice 的四个边距写错不会报错，只会让面板被拉伸时圆角变形。
素材包里通常带一份 sheets.json / manifest 来描述它，但字段名各家不同
（slice / border / nine_patch / margins …），所以先打印出来看一眼，再写导入代码。
"""

from __future__ import annotations

import json
import sys
from pathlib import Path


def looks_like_sheet_meta(p: Path) -> bool:
    return p.suffix.lower() == ".json" and p.stat().st_size < 2_000_000


def describe(obj, depth: int = 0, max_items: int = 3):
    """递归打印结构，遇到 list 只展开前几项。"""
    pad = "  " * depth
    if isinstance(obj, dict):
        for k, v in list(obj.items())[:24]:
            if isinstance(v, (dict, list)):
                print(f"{pad}{k}:")
                describe(v, depth + 1, max_items)
            else:
                print(f"{pad}{k} = {v!r}")
        if len(obj) > 24:
            print(f"{pad}... 还有 {len(obj) - 24} 个键")
    elif isinstance(obj, list):
        print(f"{pad}[list] 共 {len(obj)} 项")
        for i, v in enumerate(obj[:max_items]):
            print(f"{pad}  #{i}:")
            describe(v, depth + 2, max_items)
    else:
        print(f"{pad}{obj!r}")


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    root = Path(sys.argv[1]).expanduser().resolve()
    if not root.is_dir():
        print(f"不是文件夹：{root}")
        return 2

    files = [p for p in root.rglob("*") if p.is_file()]
    counts: dict[str, int] = {}
    for p in files:
        counts[p.suffix.lower() or "(无扩展名)"] = counts.get(p.suffix.lower() or "(无扩展名)", 0) + 1

    print(f"根目录：{root}")
    print(f"共 {len(files)} 个文件")
    for ext, n in sorted(counts.items(), key=lambda kv: -kv[1]):
        print(f"  {ext:>10}  × {n}")

    metas = [p for p in files if looks_like_sheet_meta(p)]
    if not metas:
        print("\n没找到 json 描述文件 —— 那就是纯图，需要手工量 9-slice 边距。")
        return 0

    for meta in metas:
        print(f"\n=== {meta.relative_to(root)} ===")
        try:
            data = json.loads(meta.read_text(encoding="utf-8"))
        except Exception as e:  # noqa: BLE001
            print(f"  读不了：{e}")
            continue
        describe(data)

    print("\n提示：真实导入时，把每个部件展开成 (图片路径, 左, 上, 右, 下) 的映射表，")
    print("      在 Godot 里用 StyleBoxTexture.set_texture_margin_all(...) 就能直接用。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

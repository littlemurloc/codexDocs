#!/usr/bin/env python3
"""把 Crisp Kit 采样包切成我们界面能用的尺寸。

为什么要重切：原包是给手机大控件做的 —— input_normal 是 160×48，9-slice 上下边距
加起来 32px；而我们的程序行只有 30px 高，原样用会把整行顶开。
这里的做法是按目标高度等比缩放图片，**并把 slice 边距同比例缩放**，
两者一起缩才不会出现「圆角被拉扁」或「边距比图还大」这两种变形。

输出：
    hrm_godot/assets/ui/crisp/<name>.png
    hrm_godot/assets/ui/crisp/crisp_slices.json   （缩放后的边距，供 Godot 读）

用法：python tools/import_crisp_skin.py
"""

from __future__ import annotations

import json
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "_assets_src" / "CrispKit_Sampler"
OUT = ROOT / "hrm_godot" / "assets" / "ui" / "crisp"

# 目标尺寸（Godot 里的实际像素）。None 表示按 1x 原尺寸、只缩放比例。
# 每个条目：源名 -> (目标高, 可选的强制宽)
PLAN: dict[str, tuple[int, int | None]] = {
    # 程序行里的数值框：行高 30，留 2px 呼吸 -> 26
    "input_normal": (26, None),
    # 数值框右上的两枚步进键：一枚 15 高，两枚叠起来 30 刚好贴合行高
    "button_flat_normal": (13, 17),
    # 滚动条：8~10px 宽的细条，这里给到 12 宽（卡通风格可以略粗一点）
    "progress_track": (12, 12),
    "progress_fill": (12, 12),
    # 底部动作条的主按钮
    "button_medium_normal": (34, 108),
    "button_medium_hover": (34, 108),
    "button_medium_pressed": (34, 108),
    "button_medium_disabled": (34, 108),
}


def main() -> int:
    sheets = json.loads((SRC / "sheets.json").read_text(encoding="utf-8"))
    by_name = {it["name"]: it for it in sheets}
    OUT.mkdir(parents=True, exist_ok=True)

    out_meta: dict[str, dict] = {}
    for name, (target_h, force_w) in PLAN.items():
        if name not in by_name:
            print(f"跳过 {name}：包里没有")
            continue
        it = by_name[name]
        src_png = SRC / it["png_1x"]
        im = Image.open(src_png).convert("RGBA")
        w0, h0 = im.size
        k = target_h / float(h0)
        new_w = force_w if force_w else max(1, round(w0 * k))
        if (new_w, target_h) != (w0, h0):
            im = im.resize((new_w, target_h), Image.LANCZOS)
        im.save(OUT / f"{name}.png")

        sl = it.get("slice_1x")
        if sl:
            # 边距同比例缩放；同时保证两边的边距加起来不超过图宽/图高的一半，
            # 否则 9-slice 会退化成「整张拉伸」，圆角直接糊掉。
            l = max(1, round(sl["left"] * k))
            r = max(1, round(sl["right"] * k))
            t = max(1, round(sl["top"] * k))
            b = max(1, round(sl["bottom"] * k))
            if l + r >= new_w:
                l = r = max(1, new_w // 4)
            if t + b >= target_h:
                t = b = max(1, target_h // 4)
            out_meta[name] = {"w": new_w, "h": target_h, "l": l, "t": t, "r": r, "b": b}
        else:
            out_meta[name] = {"w": new_w, "h": target_h, "l": 0, "t": 0, "r": 0, "b": 0}

        print(f"{name:22s} {w0}x{h0} -> {new_w}x{target_h}  slice={sl} -> {out_meta[name]}")

    (OUT / "crisp_slices.json").write_text(
        json.dumps(out_meta, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(f"\n写入 {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

# -*- coding: utf-8 -*-
"""把城镇素材打成 base64，供布局编辑器离线使用（M64）。

为什么不用相对路径：这个编辑器要能直接双击打开（file://），
也要能被单独发给别人。相对路径在别的目录下就断了，base64 不会。

产出：docs/town_layout_editor_assets.js（window.ASSETS = {...}）
用法：python tools/gen_editor_assets.py
"""
import base64
import io
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "assets", "art", "ui", "town")
OUT = os.path.join(ROOT, "docs", "town_layout_editor_assets.js")

IDS = ["abbey", "tavern", "guild", "smith", "sanitarium", "coach", "wagon", "graveyard"]


def b64(name):
    with open(os.path.join(SRC, name), "rb") as f:
        return "data:image/png;base64," + base64.b64encode(f.read()).decode()


def main():
    parts = ["// 由 tools/gen_editor_assets.py 生成，不要手改。\n", "window.ASSETS = {\n"]
    # 三层背景：编辑器里 far/mid 在建筑下面，near 在建筑上面（可开关）
    parts.append('  bg_far: "%s",\n' % b64("bg_far.png"))
    parts.append('  bg_mid: "%s",\n' % b64("bg_mid.png"))
    parts.append('  bg_near: "%s",\n' % b64("bg_near.png"))
    for i, bid in enumerate(IDS):
        comma = "," if i < len(IDS) - 1 else ""
        parts.append('  %s: "%s"%s\n' % (bid, b64("bld_%s.png" % bid), comma))
    parts.append("};\n")
    data = "".join(parts)
    with io.open(OUT, "w", encoding="utf-8") as f:
        f.write(data)
    print("saved %s  %.2f MB" % (OUT, len(data) / 1024 / 1024))


if __name__ == "__main__":
    main()

# -*- coding: utf-8 -*-
"""把出图方交付的品红底素材切成可用的透明 PNG（M64）。

出图方交的是 1920×1920、品红底（#FF00FF）的 JPG。
JPG 有压缩噪点，所以不能直接按颜色替换，要：
  1. 从四边 BFS「泛洪」出**连通**的品红区域（不能全图扫，否则建筑里的暖色会被吃掉）；
  2. 封闭空洞（栏杆缝、獠牙缝这种四周被围住的品红）单独补一刀；
  3. alpha 腐蚀 1px，去掉 JPG 紫边；
  4. 按内容裁边，统一缩到 PROP_H 高，存 PNG。

用法： python tools/import_town_art.py
"""
import os
import sys
from collections import deque

from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, ".tmp", "town_src")
OUT = os.path.join(ROOT, "assets", "art", "ui", "town")

PROPS = ["abbey", "tavern", "guild", "smith", "sanitarium", "coach",
         "wagon", "graveyard"]
PROP_H = 520          # 存 520 高，近景显示 190 时有 2.7 倍余量
BG_H = 1400           # 底图存 1400 高（目标 1334）


def is_magenta(p):
    r, g, b = p[0], p[1], p[2]
    return r > 150 and b > 150 and g < 120 and (r - g) > 70 and (b - g) > 70


def flood_bg(im):
    """从四边泛洪，标出与画面边界连通的品红像素。"""
    w, h = im.size
    px = im.load()
    seen = bytearray(w * h)
    q = deque()
    for x in range(w):
        for y in (0, h - 1):
            if is_magenta(px[x, y]) and not seen[y * w + x]:
                seen[y * w + x] = 1
                q.append((x, y))
    for y in range(h):
        for x in (0, w - 1):
            if is_magenta(px[x, y]) and not seen[y * w + x]:
                seen[y * w + x] = 1
                q.append((x, y))
    while q:
        x, y = q.popleft()
        for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if 0 <= nx < w and 0 <= ny < h:
                i = ny * w + nx
                if not seen[i] and is_magenta(px[nx, ny]):
                    seen[i] = 1
                    q.append((nx, ny))
    return seen


def main():
    os.makedirs(OUT, exist_ok=True)
    for name in PROPS:
        im = Image.open(os.path.join(SRC, name + ".jpg")).convert("RGB")
        w, h = im.size
        mask = flood_bg(im)
        px = im.load()
        alpha = Image.new("L", (w, h), 255)
        ap = alpha.load()
        for y in range(h):
            base = y * w
            for x in range(w):
                if mask[base + x]:
                    ap[x, y] = 0
        # 封闭空洞：四周都被围住的品红（栏杆/车轮之间的缝），从外面泛洪进不来
        for y in range(1, h - 1):
            for x in range(1, w - 1):
                if ap[x, y] == 255 and is_magenta(px[x, y]):
                    ap[x, y] = 0
        # 腐蚀 1px 去紫边
        small = alpha.filter(__import__("PIL.ImageFilter", fromlist=["MinFilter"]).MinFilter(3))
        alpha = small
        out = im.convert("RGBA")
        out.putalpha(alpha)
        box = out.getbbox()
        if box:
            out = out.crop(box)
        k = PROP_H / out.height
        out = out.resize((max(1, int(out.width * k)), PROP_H), Image.LANCZOS)
        out.save(os.path.join(OUT, "bld_" + name + ".png"), "PNG")
        print("%-12s %s -> %s" % (name, im.size, out.size))

    bg = Image.open(os.path.join(SRC, "bg_scene.jpg")).convert("RGB")
    k = BG_H / bg.height
    bg = bg.resize((int(bg.width * k), BG_H), Image.LANCZOS)
    bg.save(os.path.join(OUT, "bg_town_scene.png"), "PNG")
    print("bg_scene     %s -> %s" % ((1071, 1920), bg.size))

    # 泛洪只能去掉「和边框连通的品红」，边缘抗锯齿处会留下 mag 18~30 的弱残留。
    # 单看很淡，连成线就是一条粉边 —— 必须再过一遍阈值清理。
    import subprocess
    subprocess.run([sys.executable, os.path.join(os.path.dirname(__file__), "clean_magenta.py")],
                   check=False)


if __name__ == "__main__":
    main()

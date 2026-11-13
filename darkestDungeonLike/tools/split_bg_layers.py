# -*- coding: utf-8 -*-
"""把城镇底图按手绘红线切成「远景 / 前景」两层（M64）。

输入：用户在手绘截图里画的红色分界线（红线是隔离墙，不是一条函数曲线 ——
      它在大树那里是往上绕的，按列取 y 表达不了，所以用泛洪）。

输出：
  assets/art/ui/town/bg_far.png   红线以上（天空 / 城堡 / 雾），下方透明
  assets/art/ui/town/bg_near.png  红线以下（地面 / 植被 / 栅栏），上方透明
  docs/HUD_TOWN_LAYERS.png        合成演示：远景 → 一栋建筑 → 前景

用法：
  python tools/split_bg_layers.py --line="C:/.../clipboard-....png"
坐标系：手绘截图是底图缩到 658 宽、从 y=108 起的裁片（用互相关对出来的）。
"""
import os
import sys
from collections import deque

import numpy as np
from PIL import Image, ImageFilter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOWN = os.path.join(ROOT, "assets", "art", "ui", "town")

ANN_W = 658          # 手绘截图里底图的宽
ANN_TOP = 108        # 手绘截图对应底图的起始 y（658 宽坐标系下）
LINE_RGB = (140, 100, 100)   # 红线的判定门槛


def build_near_mask(bg_w, bg_h, ann_path):
    """返回 bg 尺寸下的 bool 蒙版：True = 红线以下（前景）。"""
    ann = Image.open(ann_path).convert("RGB")
    b = np.asarray(ann).astype(int)
    red = ((b[:, :, 0] > LINE_RGB[0]) & (b[:, :, 1] < LINE_RGB[1])
           & (b[:, :, 2] < LINE_RGB[2]) & ((b[:, :, 0] - b[:, :, 1]) > 60))
    ys, xs = np.nonzero(red)     # nonzero 返回 (行, 列)，别再写反

    barrier = np.zeros((bg_h, bg_w), bool)
    k = bg_w / float(ANN_W)
    for y, x in zip(ys, xs):
        by = int((y + ANN_TOP) * k)
        bx = int(x * k)
        if 0 <= by < bg_h and 0 <= bx < bg_w:
            barrier[by, bx] = True

    # 左右两端补到画面边缘，否则泛洪会从缝里绕上去
    lx = int(xs.min() * k)
    ly = int((int(np.median(ys[xs == xs.min()])) + ANN_TOP) * k)
    rx = int(xs.max() * k)
    ry = int((int(np.median(ys[xs == xs.max()])) + ANN_TOP) * k)
    barrier[max(0, ly - 2):ly + 3, :lx + 1] = True
    barrier[max(0, ry - 2):ry + 3, rx:] = True

    # 膨胀，补手绘线的断点（不补会有缝，泛洪顺着缝整片漏过去）
    d = barrier.copy()
    for kk in (-3, -2, -1, 1, 2, 3):
        d |= np.roll(barrier, kk, axis=0)
        d |= np.roll(barrier, kk, axis=1)

    seen = np.zeros((bg_h, bg_w), bool)
    q = deque()
    for x in range(bg_w):
        if not d[bg_h - 1, x]:
            seen[bg_h - 1, x] = True
            q.append((bg_h - 1, x))
    while q:
        y, x = q.popleft()
        for ny, nx in ((y - 1, x), (y, x - 1), (y, x + 1)):
            if 0 <= ny < bg_h and 0 <= nx < bg_w and not seen[ny, nx] and not d[ny, nx]:
                seen[ny, nx] = True
                q.append((ny, nx))
    return seen


def main():
    ann = ""
    for a in sys.argv[1:]:
        if a.startswith("--line="):
            ann = a.split("=", 1)[1].strip('"')
    if not ann or not os.path.exists(ann):
        print("need --line=<手绘截图>")
        return

    bg = Image.open(os.path.join(TOWN, "bg_town_scene.png")).convert("RGB")
    W, H = bg.size
    near = build_near_mask(W, H, ann)

    # 羽化 1px：硬边在游戏里放大后会看到锯齿
    alpha = Image.fromarray((near * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(0.8))
    near_img = bg.convert("RGBA")
    near_img.putalpha(alpha)
    near_img.save(os.path.join(TOWN, "bg_near.png"), "PNG")

    far_alpha = Image.fromarray(((~near) * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(0.8))
    far_img = bg.convert("RGBA")
    far_img.putalpha(far_alpha)
    far_img.save(os.path.join(TOWN, "bg_far.png"), "PNG")

    print("bg_far.png / bg_near.png  %dx%d  前景占比 %.1f%%" %
          (W, H, 100.0 * near.sum() / near.size))

    # 合成演示：远景 → 建筑 → 前景。建筑放 3 栋，故意让它们「压线」，
    # 好看清哪些部分被前景挡掉。
    demo = Image.new("RGBA", (W, H), (0, 0, 0, 255))
    demo.alpha_composite(far_img)
    for bid, x, base, h in (("guild", 150, 760, 260), ("tavern", 470, 820, 280),
                            ("abbey", 360, 700, 170)):
        sp = Image.open(os.path.join(TOWN, "bld_%s.png" % bid)).convert("RGBA")
        k = h / sp.height
        sp = sp.resize((int(sp.width * k), h), Image.LANCZOS)
        demo.alpha_composite(sp, (x, base - h))
    demo.alpha_composite(near_img)
    demo.convert("RGB").save(os.path.join(ROOT, "docs", "HUD_TOWN_LAYERS.png"), "PNG")
    print("docs/HUD_TOWN_LAYERS.png")


if __name__ == "__main__":
    main()

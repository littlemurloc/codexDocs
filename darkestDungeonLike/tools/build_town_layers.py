# -*- coding: utf-8 -*-
"""三层底图入库 + 合成预览（M64 第五轮）。

出图方交了三张 1071×1920：远景（天空/城堡）、中景（地面/路面）、近景（品红底墨线物件）。
这里做三件事：
  1. 把近景的品红抠掉 → 透明；
  2. 三张统一缩到 780×1400 存进 assets/art/ui/town/；
  3. 按布局 JSON 合成一张预览：远景 → 中景 → 建筑 → 近景。

用法：python tools/build_town_layers.py
"""
import os
from collections import deque

import numpy as np

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "assets", "art", "ui", "town")
SRC = os.path.join(ROOT, ".tmp", "town_src")
W, H = 780, 1400

F = "C:/Windows/Fonts/msyh.ttc"
FB = "C:/Windows/Fonts/msyhbd.ttc"


def f(size, bold=False):
    return ImageFont.truetype(FB if bold else F, size)


def key_matte(im):
    """按「洋红含量」出 alpha，并去掉边缘溢色。

    第一版只认亮品红（r>150 且 b>150），结果边缘一圈暗品红（JPEG 抗锯齿混出来的
    120,20,110）全被留下 —— 叠上去是一圈粉边。
    正确做法是算 mag = min(r,b) - g：墨线是中性黑，mag≈0；纯品红 mag≈255。
    边缘像素的 mag 介于两者之间，正好可以当 1-alpha 用，再按比例把 r/b 拉回 g 去溢色。

    **阈值别放宽**：第一版用 `mag / 80`（mag=20 时还有 75% 不透明），
    留下的弱品红单看很淡，但连成线就是一条粉边 —— 城镇屏上那条紫粉色轮廓
    就是这么来的。现在 `mag >= 22` 全透明、8 以下不动，中间线性过渡。
    改完记得跑 `tools/clean_magenta.py` 复核（它也是按同一套阈值判定的）。
    """
    im = im.convert("RGB")
    w, h = im.size
    px = im.load()
    out = Image.new("RGBA", (w, h))
    po = out.load()
    for y in range(h):
        for x in range(w):
            r, g, b = px[x, y]
            mag = min(r, b) - g
            if mag <= 8:
                po[x, y] = (r, g, b, 255)
                continue
            t = min(1.0, (mag - 8) / 14.0)    # 8 以下保留，22 以上全透明
            if t >= 0.985:
                po[x, y] = (0, 0, 0, 0)
                continue
            # 去溢色：把 r/b 朝 g 拉，消掉粉边；alpha 同步降
            nr = int(r * (1 - t) + g * t)
            nb = int(b * (1 - t) + g * t)
            po[x, y] = (nr, g, nb, int(255 * (1 - t)))
    return out


def cut_sky(im):
    """把中景层的「天空区」改成透明。

    出图方交的 bg_mid 是不透明 RGB：上半部是纯黑 + 一层暗渐变，整片把远景盖死了
    （编辑器里只看到两张图，城堡根本没露出来）。
    这里用地形轮廓把上面切开：高频纹理（|图 - 模糊|）在有内容的地方才有值，
    平滑渐变接近 0，所以「每列第一个有纹理的行」就是地形顶。
    """
    a = np.asarray(im.convert("RGB")).astype(float)
    blur = np.asarray(im.convert("RGB").filter(ImageFilter.GaussianBlur(6))).astype(float)
    hp = np.abs(a - blur).mean(2)
    mask = hp > 4
    h, w = mask.shape
    prof = np.full(w, h)
    for x in range(w):
        ys = np.where(mask[:, x])[0]
        if len(ys):
            prof[x] = ys.min()
    # 中值滤波平滑轮廓，避免个别列抖出锯齿
    k = 9
    pad = np.pad(prof, k // 2, mode="edge")
    prof = np.array([int(np.median(pad[i:i + k])) for i in range(w)])

    alpha = np.full((h, w), 255, np.uint8)
    for x in range(w):
        y = int(prof[x])
        alpha[:max(0, y - 2), x] = 0
        for d in range(4):
            if 0 <= y - 2 + d < h:
                alpha[y - 2 + d, x] = int(255 * (d + 1) / 5)
    out = im.convert("RGBA")
    out.putalpha(Image.fromarray(alpha))
    return out


def fit(im):
    return im.resize((W, H), Image.LANCZOS)


def main():
    far = fit(Image.open(os.path.join(SRC, "bg_far_src.jpg")).convert("RGB"))
    mid = fit(cut_sky(Image.open(os.path.join(SRC, "bg_mid_src.jpg"))))
    near = fit(key_matte(Image.open(os.path.join(SRC, "bg_near_src.jpg"))))

    far.save(os.path.join(OUT, "bg_far.png"), "PNG")
    mid.save(os.path.join(OUT, "bg_mid.png"), "PNG")
    near.save(os.path.join(OUT, "bg_near.png"), "PNG")
    print("saved bg_far / bg_mid / bg_near  %dx%d" % (W, H))
    print("near alpha 非零占比 %.1f%%" % (100.0 * sum(
        1 for a in near.getchannel("A").getdata() if a > 40) / (W * H)))


if __name__ == "__main__":
    main()

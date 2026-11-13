# -*- coding: utf-8 -*-
"""生成「三层切分」需求的标注示意图（M64）。

不是最终素材，是给出图方看的**分区说明图**：
  · 青色 = bg_far（天空/城堡/雾）
  · 绿色 = bg_mid（地面/路面/贴地的草）
  · 琥珀 = 立起来的物件，要单独切进 bg_near（带透明）

用法：python tools/gen_layer_zones.py
"""
import os

from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "assets", "art", "ui", "town", "bg_town_scene.png")
OUT = os.path.join(ROOT, "docs", "town_layers_annotated.png")

F = "C:/Windows/Fonts/msyh.ttc"
FB = "C:/Windows/Fonts/msyhbd.ttc"


def f(size, bold=False):
    return ImageFont.truetype(FB if bold else F, size)


def label(d, xy, s, size=15, color=(255, 255, 255), bg=(0, 0, 0, 190), bold=True,
          right=False):
    """right=True 时 xy 是右边界 —— 靠右的物件标签必须往左排，否则出画。"""
    w = d.textlength(s, font=f(size, bold))
    x, y = xy
    if right:
        x = x - w
    d.rounded_rectangle((x - 6, y - 4, x + w + 8, y + size + 6), radius=5, fill=bg)
    d.text((x, y), s, font=f(size, bold), fill=color)


def main():
    im = Image.open(SRC).convert("RGBA")
    W, H = im.size
    over = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(over, "RGBA")

    # 三带的示意区（y 是按这张 780×1400 的底图量的，不是最终画布坐标）
    d.rectangle((0, 0, W, 520), fill=(60, 200, 220, 46))       # far
    d.rectangle((0, 520, W, 780), fill=(240, 180, 60, 58))     # 物件带
    d.rectangle((0, 780, W, H), fill=(90, 210, 120, 40))       # mid 地面

    out = Image.alpha_composite(im, over)
    d = ImageDraw.Draw(out, "RGBA")

    # 分区标签
    label(d, (18, 96), "① bg_far：天空 / 云 / 城堡废墟 / 远山 / 雾", 16, (200, 245, 255))
    label(d, (18, 800), "② bg_mid：路面 / 石板 / 草地 / 贴地的碎石", 16, (200, 255, 210))
    label(d, (18, 528), "③ 这一带里「立起来」的东西 → bg_near（透明底）", 16, (255, 226, 160))

    # 逐个物件打点
    marks = [
        (676, 486, "1", "右侧枯树（整棵，含细枝）", True),
        (62, 430, "2", "左侧枯树", False),
        (348, 648, "3", "街心吊灯", False),
        (170, 706, "4", "左中木箱堆", False),
        (628, 712, "5", "右下木桶堆", True),
        (150, 594, "6", "地平线灌木丛（共 5 丛）", False),
        (500, 664, "7", "栅栏（左右各一段）", False),
    ]
    for x, y, n, txt, right in marks:
        d.ellipse((x - 16, y - 16, x + 16, y + 16), fill=(255, 90, 60, 235),
                  outline=(255, 255, 255, 255), width=2)
        d.text((x, y - 1), n, font=f(17, True), fill=(255, 255, 255), anchor="mm")
        lx = x - 24 if right else x + 24
        label(d, (lx, y - 11), txt, 14, (255, 235, 225), (60, 20, 12, 215), False,
              right=right)

    label(d, (18, H - 40), "红点 = 必须单独切进 bg_near 的物件", 15, (255, 220, 210))

    out.convert("RGB").save(OUT, "PNG")
    print("saved", OUT, out.size)


if __name__ == "__main__":
    main()

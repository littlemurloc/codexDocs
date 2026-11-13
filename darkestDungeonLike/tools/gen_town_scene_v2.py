# -*- coding: utf-8 -*-
"""三层底图 + 布局 JSON 合成预览（M64 第五轮）。

顺序固定：远景 → 中景 → 建筑 → 近景。
建筑夹在 mid 和 near 之间，这就是「遮挡正确」的全部秘密 —— 不用给每栋建筑算层级，
近景层里的树、栅栏、木箱会自然地盖住立在它们后面的建筑。

用法：
  python tools/gen_town_scene_v2.py                       # 用 docs/town_layout.json
  python tools/gen_town_scene_v2.py --layout=xxx.json
"""
import json
import os
import sys

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ART = os.path.join(ROOT, "assets", "art", "ui", "town")
OUT = os.path.join(ROOT, "docs", "HUD_TOWN_SCENE_V2.png")

CW, CH = 750, 1334
F = "C:/Windows/Fonts/msyh.ttc"
FB = "C:/Windows/Fonts/msyhbd.ttc"
NAMES = {"abbey": "修道院", "tavern": "酒馆", "guild": "公会", "smith": "铁匠铺",
         "sanitarium": "疗养院", "coach": "马车", "wagon": "商队", "graveyard": "墓园"}
C_TEXT = (219, 211, 197)
C_GOLD = (214, 168, 74)
C_RED = (198, 60, 48)


def f(size, bold=False):
    return ImageFont.truetype(FB if bold else F, size)


def text(d, xy, s, size=13, color=C_TEXT, bold=False, anchor="la"):
    d.text(xy, s, font=f(size, bold), fill=color, anchor=anchor)


def depth_fx(im, base):
    """越远越接近雾色、越糊 —— 和 v1 同一条规则，只是基线按新底图调过。"""
    # 雾只给「地平线那一排」：底边 660 以下基本是近景，再吃雾就发白。
    # 第一版用 (base-620)/620，737 的墓园被雾压成灰片，和 303 高的公会同屏打架。
    t = max(0.0, min(1.0, (base - 660) / 160.0))
    far = 1.0 - t
    k = 0.34 * far
    if k > 0.02:
        fog = Image.new("RGBA", im.size, (74, 82, 92, 255))
        fog.putalpha(Image.eval(im.getchannel("A"), lambda v: int(v * k)))
        im = Image.alpha_composite(im, fog)
    if far > 0.62:
        im = im.filter(ImageFilter.GaussianBlur(0.7))
    return im


def rim(im, px=2, color=(224, 178, 74)):
    """生成一圈金色描边（返回带描边的合成图）。

    做法：alpha 先膨胀再减去原 alpha，得到**边缘环**；环稍微模糊一下，
    免得出现锯齿。数字建筑元素不能靠画方框 —— 方框是「卡片」，不是「这栋楼可点」。
    """
    from PIL import ImageChops
    a = im.getchannel("A")
    grown = a.filter(ImageFilter.MaxFilter(px * 2 + 1))
    ring = ImageChops.subtract(grown, a).filter(ImageFilter.GaussianBlur(0.8))
    ring = ring.point(lambda v: int(v * 0.9))
    glow = Image.new("RGBA", im.size, color + (255,))
    glow.putalpha(ring)
    out = Image.new("RGBA", im.size, (0, 0, 0, 0))
    out.alpha_composite(glow)
    out.alpha_composite(im)
    return out


def soften_bottom(im, px):
    a = im.getchannel("A")
    w, h = im.size
    grad = Image.new("L", (1, h), 255)
    gp = grad.load()
    for y in range(h - px, h):
        gp[0, y] = int(255 * (h - y) / px)
    grad = grad.resize((w, h))
    im.putalpha(Image.composite(a, Image.new("L", (w, h), 0), grad))
    return im


def main():
    layout = os.path.join(ROOT, "docs", "town_layout.json")
    for a in sys.argv[1:]:
        if a.startswith("--layout="):
            layout = a.split("=", 1)[1]
    items = json.load(open(layout, encoding="utf-8"))["items"]

    def load(name):
        im = Image.open(os.path.join(ART, name)).convert("RGBA")
        return im.resize((CW, CH), Image.LANCZOS)

    canvas = Image.new("RGBA", (CW, CH), (0, 0, 0, 255))
    canvas.alpha_composite(load("bg_far.png"))
    canvas.alpha_composite(load("bg_mid.png"))

    def draw_bld(it):
        sp = Image.open(os.path.join(ART, "bld_%s.png" % it["id"])).convert("RGBA")
        h = it["h"]
        k = h / sp.height
        sp = sp.resize((max(1, int(sp.width * k)), h), Image.LANCZOS)
        if it.get("flipH"):
            from PIL import ImageOps
            sp = ImageOps.mirror(sp)
        sp = depth_fx(sp, it["y"])
        sp = soften_bottom(sp, max(10, int(h * 0.09)))
        sh = Image.new("RGBA", (sp.width + 60, 90), (0, 0, 0, 0))
        sd = ImageDraw.Draw(sh)
        sd.ellipse((30, 26, sp.width + 30, 74), fill=(0, 0, 0, 120))
        sh = sh.filter(ImageFilter.GaussianBlur(9))
        canvas.alpha_composite(sh, (it["x"] - 30, it["y"] - 50))
        sp = rim(sp)
        canvas.alpha_composite(sp, (it["x"], it["y"] - h))

    back = [i for i in items if not i.get("front")]
    front = [i for i in items if i.get("front")]
    for it in sorted(back, key=lambda i: i["y"]):
        draw_bld(it)

    # 近景压在建筑之上 —— 这一行就是「遮挡正确」的来源
    canvas.alpha_composite(load("bg_near.png"))

    # 标了 front 的几栋摆在前景层**前面**（比如故意要让它在树前面）
    for it in sorted(front, key=lambda i: i["y"]):
        draw_bld(it)

    d = ImageDraw.Draw(canvas, "RGBA")
    boxes = []
    for it in items:
        sp = Image.open(os.path.join(ART, "bld_%s.png" % it["id"])).convert("RGBA")
        w = int(it["h"] * sp.width / sp.height)
        boxes.append((it["x"], it["y"] - it["h"], w, it["h"]))

    # UI 占位：牌子和建筑都不能压这几块
    UI = [(0, 80, 750, 92),        # 顶部信息带
          (200, 930, 360, 118),    # 名册条
          (0, 1122, 750, 160),     # 底部 dock
          (10, 190, 56, 210)]      # 左侧竖栏

    def hit(a, b):
        return not (a[0] + a[2] <= b[0] or b[0] + b[2] <= a[0]
                    or a[1] + a[3] <= b[1] or b[1] + b[3] <= a[1])

    def place(i, it, pw):
        """名牌依次试：下方 → 上方 → 建筑内底 → 右侧 → 左侧，取第一个不撞的。

        统一挂底边会有两栋撞车（公会压墓园、疗养院压酒馆），
        而「统一往上挪」又会撞到别的 —— 只能逐个算。
        """
        x, top, w, h = boxes[i]
        # 中心点先夹回画面内：酒馆这种右半出框的建筑，
        # 不夹的话所有候选位置都会越界，牌子会被甩到屏幕中间去（看起来像别人的）。
        cx = min(max(x + w // 2, 8 + pw // 2), 742 - pw // 2)
        cands = [
            (cx - pw // 2, it["y"] + 6),
            (cx - pw // 2, top - 32),
            (cx - pw // 2, it["y"] - 30),
            (x + w + 6, it["y"] - 30),
            (x - pw - 6, it["y"] - 30),
            (cx - pw // 2, it["y"] - h // 2),
        ]
        others = [b for k, b in enumerate(boxes) if k != i]
        for (px, py) in cands:
            r = (px, py, pw, 26)
            if px < 8 or px + pw > 742 or py < 180 or py + 26 > 1116:
                continue
            if any(hit(r, o) for o in others):
                continue
            if any(hit(r, u) for u in UI):
                continue
            return px, py
        return cx - pw // 2, it["y"] - 30

    for i, it in enumerate(items):
        w = boxes[i][2]
        pw = max(84, min(118, int(w * 0.86)))
        px, py = place(i, it, pw)
        d.rounded_rectangle((px, py, px + pw, py + 26), radius=5,
                            fill=(11, 10, 9, 242), outline=(104, 88, 62))
        text(d, (px + pw // 2, py + 14), NAMES.get(it["id"], it["id"]), 14, C_TEXT, False, "mm")
        if it.get("badge"):
            d.ellipse((px + pw - 12, py - 5, px + pw - 2, py + 5), fill=C_RED)

    canvas.convert("RGB").save(OUT, "PNG")
    print("saved", OUT)


if __name__ == "__main__":
    main()

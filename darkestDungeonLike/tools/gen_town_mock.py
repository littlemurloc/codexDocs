# -*- coding: utf-8 -*-
"""城镇 HUD 改版示意图（M64 方案 A）。

用**现有的 8 张建筑立绘**拼一版 750×1334 的城镇首页，验证四件事：
  1. 建筑摆进场景能不能「一屏看完」，不再横向滑动；
  2. 木牌（名字 + 红点）挂在建筑上方读不读得懂；
  3. 名册和关卡搬走之后，首页还缺不缺信息；
  4. 底部 dock + 左侧竖栏 + 右侧挂件这套手游骨架，套在暗色 DD 风格上会不会打架。

产出只用于确认布局思路，所以贴图直接用原尺寸缩放，不重新导资源。
用法： python tools/gen_town_mock.py
"""
import os
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "docs", "HUD_TOWN_SCENE_MOCK.png")

W, H = 750, 1334
SAFE_TOP, SAFE_BOT = 80, 52

C_TEXT = (216, 208, 194)
C_DIM = (150, 143, 132)
C_FAINT = (104, 100, 94)
C_GOLD = (214, 168, 74)
C_RED = (196, 58, 48)
C_OK = (108, 170, 96)
C_PANEL = (10, 11, 12)
C_EDGE = (74, 66, 54)

F = "C:/Windows/Fonts/msyh.ttc"
FB = "C:/Windows/Fonts/msyhbd.ttc"


def f(size, bold=False):
    return ImageFont.truetype(FB if bold else F, size)


def tex(rel, h=None):
    im = Image.open(os.path.join(ROOT, rel)).convert("RGBA")
    if h:
        k = h / im.height
        im = im.resize((max(1, int(im.width * k)), h), Image.LANCZOS)
    return im


def paste_center(canvas, img, x, baseline, alpha=255):
    """x 是左边界，baseline 是图片底边 y。"""
    if alpha < 255:
        a = img.getchannel("A").point(lambda v: v * alpha // 255)
        img = img.copy()
        img.putalpha(a)
    canvas.alpha_composite(img, (int(x), int(baseline - img.height)))


def panel(d, box, fill=(10, 11, 12, 210), edge=C_EDGE, r=10, width=1):
    d.rounded_rectangle(box, radius=r, fill=fill, outline=edge + (255,), width=width)


def text(d, xy, s, size=15, color=C_TEXT, bold=False, anchor="la"):
    d.text(xy, s, font=f(size, bold), fill=color, anchor=anchor)


def bead(d, cx, cy, n=None, r=9):
    d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=C_RED)
    if n:
        text(d, (cx, cy + 1), str(n), 12, (255, 245, 240), True, "mm")


def plaque(canvas, d, cx, top, label, dot=None, w=132, h=32):
    """建筑上方的木牌：深底 + 细边 + 名字，右侧可挂红点。"""
    x0 = cx - w // 2
    panel(d, (x0, top, x0 + w, top + h), (14, 13, 12, 232), (96, 82, 60), 6)
    text(d, (cx, top + h // 2 + 1), label, 15, C_TEXT, False, "mm")
    if dot:
        bead(d, x0 + w - 6, top + 4, dot)


def main():
    # —— 底：现成的城镇背景（已压到 15% 亮度）——
    base = tex("assets/art/ui/skin/bg_town.png", H).convert("RGBA")
    canvas = Image.new("RGBA", (W, H), (0, 0, 0, 255))
    canvas.alpha_composite(base.crop((0, 0, W, H)))

    # 上暗角：顶部信息带下面压一层渐变，让建筑上半不抢字
    veil = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    vd = ImageDraw.Draw(veil)
    for i in range(220):
        a = int(150 * (1 - i / 220.0))
        vd.line((0, SAFE_TOP + i, W, SAFE_TOP + i), fill=(4, 4, 5, a))
    canvas.alpha_composite(veil)

    # —— 场景：后排 4 座（矮、暗）、前排 4 座（高、亮）——
    #
    # 为什么分两排：8 座一字排开在 750 宽里每座只有 94px，谁都不够看；
    # 前后排错落之后，「街上有几处可去」是一眼看完的，不用滑。
    # 后排压暗到 0.75，前排全亮 —— 深度靠亮度和大小拉开，不靠透视。
    d0 = ImageDraw.Draw(canvas)
    far = [
        ("abbey", 24, 150, 190),
        ("tavern", 160, 150, 190),
        ("wagon", 330, 150, 190),
        ("sanitarium", 560, 150, 190),
    ]
    for bid, x, h, alpha in far:
        img = tex("assets/art/ui/buildings/%s.png" % bid, h)
        # 落地影：不给影子的话，半身像看着像贴在画面上的一张贴纸
        d0.ellipse((x + img.width * 0.12, 660 - 9, x + img.width * 0.88, 660 + 9),
                   fill=(0, 0, 0, 110))
        paste_center(canvas, img, x, 660, alpha)

    near = [("smith", 10, 210), ("coach", 231, 210), ("guild", 383, 210), ("graveyard", 581, 210)]
    for bid, x, h in near:
        img = tex("assets/art/ui/buildings/%s.png" % bid, h)
        d0.ellipse((x + img.width * 0.10, 1100 - 11, x + img.width * 0.90, 1100 + 11),
                   fill=(0, 0, 0, 130))
        paste_center(canvas, img, x, 1100)

    d = ImageDraw.Draw(canvas)
    # 木牌：统一贴在每座建筑的头顶上方 26px，两排各一条水平线 ——
    # 上一版按各自的图高算，结果后排（矮）的牌子正好落在前排头顶上。
    for cx, lab, dot in [(82, "修道院", None), (222, "酒馆", None),
                         (420, "商队", 2), (614, "疗养院", 1)]:
        plaque(canvas, d, cx, 482, lab, dot, w=108, h=30)
    for cx, lab, dot in [(115, "铁匠铺", 3), (302, "马车", 1),
                         (477, "公会", None), (651, "墓园", None)]:
        plaque(canvas, d, cx, 862, lab, dot, w=108, h=30)

    # —— 中段待办条 ——
    # 画面正中那块是背景图的暗区（街道阴影），不放东西就是 340px 的黑。
    # 放「这一周该处理的几件事」：它同时解释了右上角那些红点是为什么亮的，
    # 玩家不用把 8 座建筑逐个点开才知道该干嘛。
    panel(d, (62, 676, 688, 752), (10, 10, 11, 224), (72, 64, 52), 12)
    d.line((78, 700, 78, 730), fill=(196, 58, 48, 255), width=3)
    text(d, (94, 688), "这周该处理 2 件事", 15, C_TEXT, True)
    text(d, (94, 716), "2 人压力过百　铁匠铺攒了 3 件能升的", 13, C_DIM)
    text(d, (94, 736), "6 天后任务板重抽，现在这 4 档还能挑", 13, C_FAINT)

    # —— 顶部信息带 ——
    d = ImageDraw.Draw(canvas)
    d.rectangle((0, SAFE_TOP, W, SAFE_TOP + 92), fill=(8, 9, 10, 228))
    d.line((0, SAFE_TOP + 92, W, SAFE_TOP + 92), fill=C_EDGE + (255,), width=1)
    text(d, (22, SAFE_TOP + 14), "城镇 · 第 12 周", 19, C_TEXT, True)
    text(d, (W - 22, SAFE_TOP + 18), "首领讨伐 2 / 4", 13, C_DIM, False, "ra")

    x = 22
    for icon, val, col in [
        ("icon_gold", "7797", C_GOLD),
        ("icon_bust", "12", C_DIM),
        ("icon_portrait", "9", C_DIM),
        ("icon_crest", "7", C_DIM),
        ("icon_deed", "3", C_DIM),
    ]:
        ic = tex("assets/art/ui/skin/atlas/%s.png" % icon, 20)
        canvas.alpha_composite(ic, (int(x), SAFE_TOP + 54))
        tw = d.textlength(val, font=f(15))
        text(d, (x + 24, SAFE_TOP + 55), val, 15, col, True)
        x += 24 + tw + 22
    text(d, (W - 22, SAFE_TOP + 60), "名册 5 · 存活 5 · 最多带 4 人", 13, C_FAINT, False, "ra")

    # —— 左侧功能竖栏 ——
    rail = [("鉴", 1), ("绩", 0), ("设", 0), ("档", 0)]
    ry = 196
    for lab, dot in rail:
        panel(d, (14, ry, 62, ry + 48), (10, 11, 12, 215), (66, 60, 50), 8)
        text(d, (38, ry + 25), lab, 20, C_DIM, False, "mm")
        if dot:
            bead(d, 60, ry + 6, dot)
        ry += 56

    # —— 右侧：本周事件挂件 ——
    panel(d, (638, 196, 736, 414), (22, 17, 10, 225), (150, 112, 48), 10)
    d.line((648, 214, 726, 214), fill=(150, 112, 48, 180), width=1)
    text(d, (687, 232), "本周事件", 15, C_GOLD, True, "mm")
    text(d, (687, 262), "任务板已刷新", 12, C_DIM, False, "mm")
    text(d, (687, 284), "4 档 · 最高 Lv5", 12, C_FAINT, False, "mm")
    d.line((648, 300, 726, 300), fill=(86, 70, 46, 180), width=1)
    text(d, (687, 322), "剩 6 天", 15, C_TEXT, True, "mm")
    text(d, (687, 348), "点开 → 出征", 12, C_FAINT, False, "mm")
    bead(d, 726, 204, 1)

    # —— 底部 dock ——
    d.rectangle((0, 1122, W, 1282), fill=(8, 9, 10, 235))
    d.line((0, 1122, W, 1122), fill=C_EDGE + (255,), width=1)
    items = [("城镇", 94, 26, None, False), ("名册", 281, 26, 1, False),
             ("出征", 469, 36, None, True), ("商店", 656, 26, None, False)]
    for lab, cx, r, dot, hot in items:
        if hot:
            d.ellipse((cx - r - 5, 1156 - r - 5, cx + r + 5, 1156 + r + 5),
                      outline=(150, 112, 48, 200), width=2)
            d.ellipse((cx - r, 1156 - r, cx + r, 1156 + r), fill=(60, 48, 24, 255),
                      outline=(214, 168, 74, 255), width=2)
            text(d, (cx, 1157), "出", 26, C_GOLD, True, "mm")
        else:
            d.ellipse((cx - r, 1156 - r, cx + r, 1156 + r), fill=(20, 21, 22, 255),
                      outline=(70, 64, 54, 255), width=1)
            text(d, (cx, 1157), lab[0], 20, C_DIM, False, "mm")
        text(d, (cx, 1214), lab, 14, C_GOLD if hot else C_DIM, hot, "mm")
        if dot:
            bead(d, cx + r - 2, 1156 - r + 4, dot, 9)

    # —— 安全区 ——
    d.rectangle((0, 0, W, SAFE_TOP), fill=(0, 0, 0, 255))
    d.rectangle((0, H - SAFE_BOT, W, H), fill=(0, 0, 0, 255))

    canvas.convert("RGB").save(OUT, "PNG")
    print("saved", OUT)


if __name__ == "__main__":
    main()

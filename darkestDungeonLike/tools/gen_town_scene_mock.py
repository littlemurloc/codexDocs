# -*- coding: utf-8 -*-
"""城镇场景合成预览（M64）：真实素材版。

和 `gen_town_layout.py` 的区别：那份是程序画的**布局蓝图**（定坐标用），
这一份是**拿交付的真实素材合成**，用来验证 8 个点位在这张底图上站不站得住。

关键校准：交付的底图是一张「路在正中、两侧有围栏和杂物」的街景，
路面比蓝图里的窄，所以两侧建筑的 x 要按图重新排 —— 蓝图坐标只是上下分层的依据。

用法： python tools/gen_town_scene_mock.py
"""
import os

import sys

from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ART = os.path.join(ROOT, "assets", "art", "ui", "town")
OUT = os.path.join(ROOT, "docs", "HUD_TOWN_SCENE_V1.png")

W, H = 750, 1334
SAFE_TOP, SAFE_BOT = 80, 52

C_TEXT = (219, 211, 197)
C_DIM = (150, 143, 132)
C_FAINT = (100, 96, 90)
C_GOLD = (214, 168, 74)
C_RED = (198, 60, 48)
C_EDGE = (84, 74, 58)

F = "C:/Windows/Fonts/msyh.ttc"
FB = "C:/Windows/Fonts/msyhbd.ttc"


def f(size, bold=False):
    return ImageFont.truetype(FB if bold else F, size)


def text(d, xy, s, size=13, color=C_TEXT, bold=False, anchor="la"):
    d.text(xy, s, font=f(size, bold), fill=color, anchor=anchor)


# id, 名字, x, 底边 y, 显示高度, 红点
# 高频的放近层（离拇指近），低频的放远层 —— 位置本身就是频率分层。
#
# 三层基线与高度是**按交付底图校准过的**：
#   · 底图的路面比蓝图里窄，所以近层只能放两侧草地上，不能让建筑压住路面；
#   · 每层之间要留出「木牌 28 + 上下各 8」的净空，否则上一排的牌子会盖住
#     下一排建筑的底边（第一版就是这样：酒馆的牌子落在铁匠铺屋顶上）。
# id, 名字, x, 底边 y, 显示高, 红点
#
# **尺寸跟着深度走**：底边 y 越靠上（越远）就越小、越淡。
# 第一版所有建筑按「层」给固定高（100/120/135/170），结果远近距离差不出来，
# 和背景的路面、围栏一比就显得像贴纸 —— 场景里围栏约 28px 高，
# 一栋房子怎么也得是它的 5~8 倍。
SLOTS = [
    # 深处：压在**地平线附近**（y≈470 以下才有地面，再往上就是天空，会飘）
    ("abbey", "修道院", 196, 500, 118, None, False),
    ("guild", "公会", 410, 505, 124, None, False),
    ("graveyard", "墓园", 60, 545, 130, None, False),
    ("wagon", "商队", 470, 540, 132, 2, False),
    # 中景
    ("sanitarium", "疗养院", 566, 740, 170, 1, False),
    ("tavern", "酒馆", 0, 900, 200, None, False),
    # 近景两角（最近的东西本来就该被画面裁掉一点）
    ("smith", "铁匠铺", -60, 1115, 230, 3, False),
    ("coach", "马车", 552, 1115, 230, 1, False),
]


def soften_bottom(im, px=14):
    """把图片最下面 px 行的 alpha 渐隐到 0。

    出图方交的单体图底边是**直切**的（抠图时按内容框裁掉），
    直接贴到场景里就是一条硬边 —— 看着像剪贴画，不像站在地上。
    """
    a = im.getchannel("A")
    w, h = im.size
    grad = Image.new("L", (1, h), 255)
    gp = grad.load()
    for y in range(h - px, h):
        gp[0, y] = int(255 * (h - y) / px)
    grad = grad.resize((w, h))
    im.putalpha(Image.composite(a, Image.new("L", (w, h), 0), grad))
    return im


def depth_fx(im, base):
    """大气透视：越远的建筑越接近雾色、越糊、对比越低。

    只做「整体压暗」是不够的 —— 远排那几座原本是单独画的，
    自带一套明亮的光照，摆进雾里一眼就是贴上去的剪贴画。
    真正的做法是**往雾色里混**（mix toward fog），浓度按距离走。
    """
    t = max(0.0, min(1.0, (base - 500) / 615.0))       # 0 = 最远，1 = 最近
    far = 1.0 - t
    k = 0.30 * far
    if k > 0.02:
        fog = Image.new("RGBA", im.size, (74, 82, 92, 255))
        fog.putalpha(Image.eval(im.getchannel("A"), lambda v: int(v * k)))
        im = Image.alpha_composite(im, fog)
    if far > 0.6:
        im = im.filter(ImageFilter.GaussianBlur(0.8))
    return im


def prop(name, h):
    im = Image.open(os.path.join(ART, "bld_%s.png" % name)).convert("RGBA")
    k = h / im.height
    return im.resize((max(1, int(im.width * k)), h), Image.LANCZOS)


def load_layout(path):
    """读布局编辑器导出的 JSON。

    编辑器里存的是 {id, x, y(底边), h, flipH, flipV}，和下面 SLOTS 的字段一一对应，
    所以改完布局不用改代码 —— 换个 JSON 就重出图。
    """
    import json
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    out = []
    for it in data.get("items", []):
        out.append((it["id"], NAMES.get(it["id"], it["id"]), int(it["x"]),
                    int(it["y"]), int(it["h"]), 0, bool(it.get("flipH"))))
    return out


NAMES = {"abbey": "修道院", "tavern": "酒馆", "guild": "公会", "smith": "铁匠铺",
         "sanitarium": "疗养院", "coach": "马车", "wagon": "商队", "graveyard": "墓园"}


def main():
    layout_path = ""
    for a in sys.argv[1:]:
        if a.startswith("--layout="):
            layout_path = a.split("=", 1)[1]
    global SLOTS
    if layout_path:
        SLOTS = load_layout(layout_path)
        print("layout:", layout_path, len(SLOTS), "items")

    canvas = Image.new("RGBA", (W, H), (0, 0, 0, 255))

    bg = Image.open(os.path.join(ART, "bg_town_scene.png")).convert("RGB")
    k = W / bg.width
    bg = bg.resize((W, int(bg.height * k)), Image.LANCZOS)
    canvas.paste(bg.crop((0, 0, W, H)), (0, 0))

    # 整体压暗一点：交付图的亮度比游戏内其它屏高，会抢 UI
    canvas = Image.alpha_composite(canvas, Image.new("RGBA", (W, H), (0, 0, 0, 52)))

    d = ImageDraw.Draw(canvas, "RGBA")

    # —— 八个建筑：远 → 近 依次叠 ——
    #
    # 两条「不浮空」的做法，缺一条就会像贴纸：
    #   1. 落影必须是**软**的（高斯模糊），硬椭圆读起来是一块黑盘子；
    #   2. 远层画完之后要压一道**地平线雾**，让它们的下半截沉进雾里 ——
    #      这也是「建筑和场景融合」最省事的一招，不用改素材。
    layers = sorted(SLOTS, key=lambda s: s[3])

    def draw_row(row):
        for bid, name, x, base, h, dot, flip in row:
            im = prop(bid, h)
            depth = (base - 380) / 525.0
            # 软落影
            sh = Image.new("RGBA", (im.width + 60, 90), (0, 0, 0, 0))
            sd = ImageDraw.Draw(sh)
            sd.ellipse((30, 26, im.width + 30, 74), fill=(0, 0, 0, 150))
            sh = sh.filter(ImageFilter.GaussianBlur(9))
            canvas.alpha_composite(sh, (x - 30, base - 50))
            if flip:
                im = ImageOps.mirror(im)
            im = depth_fx(im, base)
            im = soften_bottom(im, max(10, int(im.height * 0.09)))
            a = int(150 + 90 * depth)
            if a < 255:
                al = im.getchannel("A").point(lambda v: v * a // 255)
                im = im.copy()
                im.putalpha(al)
            canvas.alpha_composite(im, (x, base - im.height))
    # 分行从布局里推，别再写死 —— 换 JSON 之后基线全变了，写死会 min() 空集合
    rows = sorted({r[3] for r in layers})
    for base_i, by in enumerate(rows):
        draw_row([r for r in layers if r[3] == by])
        if base_i < len(rows) - 1:
            # 大气透视：这一排画完压一层雾，范围到下一排的顶部为止。
            # 不分层的话，远排和近排的对比度一样，深度就塌了。
            nxt = rows[base_i + 1]
            top = min(r[3] - r[4] for r in layers if r[3] == by) - 10
            haze = Image.new("RGBA", (W, 180), (0, 0, 0, 0))
            hd = ImageDraw.Draw(haze)
            a0 = max(0, 34 - base_i * 11)
            for i in range(180):
                a = int(a0 * (1 - i / 180.0))
                if a > 0:
                    hd.line((0, i, W, i), fill=(120, 126, 134, a))
            canvas.alpha_composite(haze, (0, max(0, top)))

    # —— 顶部信息带 ——
    d.rectangle((0, SAFE_TOP, W, 172), fill=(8, 9, 10, 226))
    d.line((0, 172, W, 172), fill=C_EDGE + (255,), width=1)
    text(d, (22, SAFE_TOP + 14), "城镇 · 第 12 周", 19, C_TEXT, True)
    text(d, (W - 22, SAFE_TOP + 18), "首领讨伐 2 / 4", 13, C_DIM, False, "ra")
    x = 22
    for icon, val, col in (("icon_gold", "7797", C_GOLD), ("icon_bust", "12", C_DIM),
                           ("icon_portrait", "9", C_DIM), ("icon_crest", "7", C_DIM),
                           ("icon_deed", "3", C_DIM)):
        ic = Image.open(os.path.join(ROOT, "assets/art/ui/skin/atlas/%s.png" % icon)).convert("RGBA")
        ic = ic.resize((20, 20), Image.LANCZOS)
        canvas.alpha_composite(ic, (int(x), SAFE_TOP + 54))
        tw = d.textlength(val, font=f(15))
        text(d, (x + 24, SAFE_TOP + 55), val, 15, col, True)
        x += 24 + tw + 22

    # —— 名册：缩小、居中在马路底部（M64 第四轮）——
    #
    # 原来是一整排 5 张 136 宽的卡横贯全屏，把底部两角全占了。
    # 收成 340 宽的紧凑条之后，左下/右下各让出 200 多像素给铁匠铺和马车 ——
    # 「名册是查询，不是操作」，它不需要那么宽。
    rx0, ry0, rw, rh = 212, 960, 336, 98
    d.rounded_rectangle((rx0, ry0, rx0 + rw, ry0 + rh), radius=10,
                        fill=(9, 10, 11, 236), outline=(76, 68, 54))
    d.rectangle((rx0 + 2, 968, rx0 + 5, 986), fill=C_GOLD)
    text(d, (rx0 + 14, 978), "名册 5 人", 15, C_TEXT, True, "lm")
    text(d, (rx0 + 106, 978), "存活 5 · 上限 4", 10, C_DIM, False, "lm")
    for i, hero in enumerate(("crusader", "highwayman", "vestal", "plague_doctor", "hellion")):
        hx = rx0 + 12 + i * 65
        try:
            pf = Image.open(os.path.join(ROOT, "assets/art/units/%s.png" % hero)).convert("RGB")
            pf = pf.resize((54, 54), Image.LANCZOS)
            canvas.paste(pf, (int(hx), 992))
        except Exception:
            d.rectangle((hx, 992, hx + 54, 1046), fill=(30, 31, 34))
        d.rectangle((hx, 992, hx + 54, 1046), outline=(88, 78, 60))

    # —— dock ——
    d.rectangle((0, 1122, W, H), fill=(8, 9, 10, 242))
    d.line((0, 1122, W, 1122), fill=C_EDGE + (255,), width=1)
    for lab, cx, r, hot in (("城镇", 94, 26, False), ("名册", 281, 26, False),
                            ("出征", 469, 34, True), ("商店", 656, 26, False)):
        d.ellipse((cx - r, 1156 - r, cx + r, 1156 + r),
                  fill=(58, 46, 22) if hot else (20, 21, 22),
                  outline=C_GOLD if hot else (70, 64, 54), width=2 if hot else 1)
        text(d, (cx, 1157), lab[0], 20, C_GOLD if hot else C_DIM, hot, "mm")
        text(d, (cx, 1214), lab, 13, C_GOLD if hot else C_DIM, hot, "mm")

    d = ImageDraw.Draw(canvas, "RGBA")

    # —— 木牌 + 红点（挂在建筑的**底部居中**）——
    #
    # 原来挂在屋顶上方，两个毛病：① 远排的牌子飘在空中，看不出属于哪栋；
    # ② 竖着排三层时，上层的牌子正好落在下层屋顶上，像下层的招牌。
    # 挪到建筑底边之后，牌子和它那栋楼永远贴合，也不会跟邻居打架。
    for bid, name, x, base, h, dot, flip in SLOTS:
        im = prop(bid, h)
        cx = x + im.width // 2
        # 牌宽跟着建筑走：比建筑还宽的牌子会左右支棱出去，看着像浮在旁边
        pw = max(84, min(118, int(im.width * 0.86)))
        # 名牌默认贴建筑底边；底边已经沉到 dock 区（1122 以下）时改挂**建筑顶部**，
        # 否则牌子会被底部导航栏盖掉 —— 前景建筑故意「从 UI 后面探出来」是常见做法，
        # 但牌子必须还看得见。
        py = base - 26 if base <= 1096 else base - h + 4
        d.rounded_rectangle((cx - pw // 2, py, cx + pw // 2, py + 26), radius=5,
                            fill=(11, 10, 9, 242), outline=(104, 88, 62))
        text(d, (cx, py + 14), name, 14, C_TEXT, False, "mm")
        if dot:
            d.ellipse((cx + pw // 2 - 12, py - 5, cx + pw // 2 - 2, py + 5), fill=C_RED)
            text(d, (cx + pw // 2 - 7, py), str(dot), 9, (255, 244, 236), True, "mm")

    # —— 安全区 ——
    d.rectangle((0, 0, W, SAFE_TOP), fill=(0, 0, 0, 255))
    d.rectangle((0, H - SAFE_BOT, W, H), fill=(0, 0, 0, 255))

    canvas.convert("RGB").save(OUT, "PNG")
    print("saved", OUT)


if __name__ == "__main__":
    main()

# -*- coding: utf-8 -*-
"""城镇新底图的「8 点布局」示意图（M64）。

这不是最终美术，是**给底图定坐标的蓝图**：
  · 8 个功能点落在哪、各多大、前后怎么分层；
  · 哪些 UI 带占掉哪块，剩给场景的可用区是多少；
  · 「可互动」怎么表现（金边 + 暖光 + 落地影 + 木牌）。

底图本身要另出（见 docs/TOWN_SCENE_BRIEF.md），这版只证明布局站得住。
用法： python tools/gen_town_layout.py
"""
import os
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "docs", "HUD_TOWN_LAYOUT.png")

W, H = 750, 1334
SAFE_TOP, SAFE_BOT = 80, 52

C_TEXT = (216, 208, 194)
C_DIM = (140, 134, 123)
C_FAINT = (92, 89, 84)
C_GOLD = (214, 168, 74)
C_AMBER = (224, 178, 74)
C_RED = (198, 60, 48)
C_EDGE = (86, 76, 60)
C_HOT = (255, 214, 130)

F = "C:/Windows/Fonts/msyh.ttc"
FB = "C:/Windows/Fonts/msyhbd.ttc"


def f(size, bold=False):
    return ImageFont.truetype(FB if bold else F, size)


def text(d, xy, s, size=13, color=C_TEXT, bold=False, anchor="la"):
    d.text(xy, s, font=f(size, bold), fill=color, anchor=anchor)


# 8 个功能点：id, 名字, x, 宽, 高, 基线 y, 层级, 红点
# 层级只决定「画多大、压多暗」——近大远小就是这一屏的深度感来源。
SLOTS = [
    ("abbey", "修道院", 96, 110, 110, 400, "far", None),
    ("graveyard", "墓园", 320, 110, 110, 400, "far", None),
    ("wagon", "商队", 490, 110, 110, 400, "far", 2),
    ("tavern", "酒馆", 10, 140, 145, 600, "mid", None),
    ("sanitarium", "疗养院", 590, 140, 145, 600, "mid", 1),
    ("coach", "马车", 18, 134, 120, 890, "near", 1),
    ("smith", "铁匠铺", 196, 180, 190, 870, "near", 3),
    ("guild", "公会", 560, 182, 190, 870, "near", None),
]

PLAQUE_Y = {"far": 264, "mid": 429, "near": 652}
TIER_ALPHA = {"far": 0.62, "mid": 0.78, "near": 0.95}


def house(d, x, w, h, base, alpha, hot=False):
    """建筑占位：屋身 + 双坡屋顶 + 亮着的窗。只为说明「这一格放一栋房子」。"""
    top = base - h
    roof = int(h * 0.30)
    body_top = top + roof
    tone = (28, 26, 24) if not hot else (40, 34, 26)
    edge = (120, 104, 78) if not hot else C_HOT
    d.polygon([(x - 4, body_top), (x + w // 2, top), (x + w + 4, body_top)],
              fill=(34, 30, 27), outline=edge)
    d.rectangle((x, body_top, x + w, base), fill=tone, outline=edge)
    dw, dh = max(14, w // 5), max(22, int(h * 0.22))
    dx = x + w // 2 - dw // 2
    d.rectangle((dx, base - dh, dx + dw, base), fill=(16, 14, 13), outline=edge)
    for i, wx in enumerate((x + w // 6, x + w - w // 6 - 14)):
        wy = body_top + int(h * 0.16)
        d.rectangle((wx, wy, wx + 14, wy + 16), fill=(120, 86, 34) if not hot else (196, 148, 62))
        d.rectangle((wx, wy, wx + 14, wy + 16), outline=(60, 50, 34))


def wagon(d, x, w, h, base):
    top = base - h
    d.rectangle((x + 8, top + 10, x + w - 8, base - 22), fill=(30, 27, 24),
                outline=(120, 104, 78))
    d.polygon([(x + 8, top + 10), (x + w // 2, top - 14), (x + w - 8, top + 10)],
              fill=(34, 30, 27), outline=(120, 104, 78))
    for cx in (x + 26, x + w - 26):
        d.ellipse((cx - 14, base - 30, cx + 14, base - 2), outline=(130, 112, 82), width=3)
    d.rectangle((x + 24, top + 34, x + w - 24, top + 52), fill=(110, 78, 30))


def yard(d, x, w, h, base):
    top = base - h
    d.line((x, base - 4, x + w, base - 4), fill=(110, 96, 72), width=2)
    for i in range(6):
        px = x + 4 + i * (w - 8) // 5
        d.line((px, base - 4, px, base - 22), fill=(96, 84, 64), width=2)
    for i in range(3):
        sx = x + 12 + i * (w - 34) // 2
        hh = 30 + (i % 2) * 8
        d.rounded_rectangle((sx, base - 16 - hh, sx + 18, base - 16), radius=9,
                            fill=(44, 40, 36), outline=(120, 106, 82))
        d.line((sx + 4, base - 30 - hh // 3, sx + 14, base - 30 - hh // 3),
               fill=(120, 106, 82), width=1)


def slot(canvas, d, s, hot=False, dashed=None):
    bid, name, x, w, h, base, tier, dot = s
    a = TIER_ALPHA[tier]
    # 落地影：没有影子就会像贴在画面上的一张纸
    d.ellipse((x - 6, base - 10, x + w + 6, base + 10), fill=(0, 0, 0, int(150 * a)))
    if bid == "coach":
        wagon(d, x, w, h, base)
    elif bid == "graveyard":
        yard(d, x, w, h, base)
    else:
        house(d, x, w, h, base, a, hot)
    # 可互动：金色描边 + 四角短标（不画满框，满框会像截图里的选中框）
    cx0, cy0, cx1, cy1 = x - 4, base - h - 6, x + w + 4, base + 4
    col = C_HOT if hot else (C_GOLD if tier == "near" else (150, 124, 80))
    d.rectangle((cx0, cy0, cx1, cy1), outline=col, width=2 if hot else 1)
    if hot:
        d.rectangle((cx0 - 3, cy0 - 3, cx1 + 3, cy1 + 3), outline=(255, 214, 130), width=1)
    L = 12
    for px, py, dx, dy in ((cx0, cy0, 1, 1), (cx1, cy0, -1, 1),
                           (cx0, cy1, 1, -1), (cx1, cy1, -1, -1)):
        d.line((px, py, px + dx * L, py), fill=col, width=3 if hot else 2)
        d.line((px, py, px, py + dy * L), fill=col, width=3 if hot else 2)
    # 木牌
    py0 = PLAQUE_Y[tier] if bid != "coach" else base - h - 28
    pw = 106
    px = x + w // 2 - pw // 2
    d.rounded_rectangle((px, py0, px + pw, py0 + 28), radius=5,
                        fill=(13, 12, 11, 240), outline=(96, 82, 60))
    text(d, (px + pw // 2, py0 + 15), name, 14, C_TEXT, False, "mm")
    if dot:
        d.ellipse((px + pw - 12, py0 + 1, px + pw - 2, py0 + 11), fill=C_RED)
        text(d, (px + pw - 7, py0 + 7), str(dot), 9, (255, 244, 236), True, "mm")
    if dashed:
        d.rectangle(dashed, outline=(120, 120, 120), width=1)


def main():
    canvas = Image.new("RGBA", (W, H), (11, 12, 14, 255))
    d = ImageDraw.Draw(canvas, "RGBA")

    # —— 天空 / 远景墙 / 地面 ——
    for y in range(SAFE_TOP, 340):
        k = (y - SAFE_TOP) / 260.0
        d.line((0, y, W, y), fill=(int(16 + 10 * k), int(17 + 10 * k), int(19 + 11 * k)))
    d.rectangle((0, 300, W, 344), fill=(20, 19, 18))

    # 地面与街道（M64 第二版）：
    # 上一版是「把街道中间压黑」，结果画面正中读成一个洞。
    # 反过来才对：**路面比两侧亮**，两侧压暗当作街边的建筑阴影。
    d.rectangle((0, 344, W, 1122), fill=(27, 26, 25))
    d.polygon([(0, 344), (300, 344), (150, 1122), (0, 1122)], fill=(13, 13, 14))
    d.polygon([(W, 344), (470, 344), (630, 1122), (W, 1122)], fill=(13, 13, 14))
    d.polygon([(326, 350), (434, 350), (630, 1122), (150, 1122)], fill=(37, 35, 32))
    # 路面石板缝：越近越疏，给纵深一个刻度
    for i in range(8):
        yy = 380 + int(i * i * 14.5)
        if yy > 1120:
            break
        k = (yy - 350) / 772.0
        x0 = int(326 - 176 * k)
        x1 = int(434 + 196 * k)
        d.line((max(0, x0), yy, min(W, x1), yy), fill=(48, 45, 40, 120), width=1)
    # 街道尽头的一点暖光（三层叠到 ~18%，再叠就成一坨）
    for r, a in ((108, 6), (74, 7), (42, 9)):
        d.ellipse((375 - r, 372 - int(r * 0.40), 375 + r, 372 + int(r * 0.40)),
                  fill=(120, 88, 40, a))

    # —— UI 带（占位，交叠关系必须看得见）——
    d.rectangle((0, SAFE_TOP, W, 172), fill=(9, 10, 11, 232))
    d.line((0, 172, W, 172), fill=C_EDGE + (255,), width=1)
    text(d, (22, 96), "顶部信息带", 15, C_TEXT, True)
    text(d, (22, 120), "周 · 金币 · 传家宝 · 首领进度", 12, C_DIM)
    text(d, (W - 22, 120), "y 80–172", 12, C_FAINT, False, "ra")

    for i, lab in enumerate(("鉴", "绩", "设", "档")):
        yy = 196 + i * 56
        d.rounded_rectangle((14, yy, 62, yy + 48), radius=8, fill=(10, 11, 12, 232),
                            outline=(66, 60, 50))
        text(d, (38, yy + 25), lab, 19, C_DIM, False, "mm")
    text(d, (38, 452), "竖栏", 11, C_FAINT, False, "ma")

    d.rounded_rectangle((638, 196, 736, 414), radius=10, fill=(22, 17, 10, 236),
                        outline=(150, 112, 48))
    text(d, (687, 236), "本周事件", 14, C_GOLD, True, "mm")
    text(d, (687, 268), "挂件区", 11, C_DIM, False, "mm")
    text(d, (687, 300), "y 196–414", 11, C_FAINT, False, "mm")

    # 名册（保留，用户要求高亮）
    d.rectangle((20, 930, W - 20, 958), fill=(9, 10, 11, 226))
    d.rectangle((22, 935, 25, 953), fill=(200, 150, 50))
    text(d, (34, 944), "名册 5 人", 16, C_TEXT, True, "lm")
    text(d, (150, 944), "存活 5 · 出战上限 4 人", 11, C_DIM, False, "lm")
    text(d, (W - 24, 944), "y 930–1102 · 保留", 11, C_FAINT, False, "rm")
    for i in range(5):
        bx = 24 + i * 146
        d.rounded_rectangle((bx, 962, bx + 136, 1102), radius=8, fill=(15, 16, 18, 210),
                            outline=(70, 64, 54))
        text(d, (bx + 68, 1032), "名册卡", 12, C_FAINT, False, "mm")

    # dock
    d.rectangle((0, 1122, W, H), fill=(9, 10, 11, 240))
    d.line((0, 1122, W, 1122), fill=C_EDGE + (255,), width=1)
    for lab, cx, r, hot in (("城镇", 94, 26, False), ("名册", 281, 26, False),
                            ("出征", 469, 34, True), ("商店", 656, 26, False)):
        d.ellipse((cx - r, 1156 - r, cx + r, 1156 + r),
                  fill=(58, 46, 22) if hot else (20, 21, 22),
                  outline=C_GOLD if hot else (70, 64, 54), width=2 if hot else 1)
        text(d, (cx, 1157), lab[0], 20, C_GOLD if hot else C_DIM, hot, "mm")
        text(d, (cx, 1214), lab, 13, C_GOLD if hot else C_DIM, hot, "mm")

    # —— 8 个功能点 ——
    for s in SLOTS:
        slot(canvas, d, s)
    # 悬停态示例：铁匠铺
    slot(canvas, d, SLOTS[6], hot=True)

    # 命中框外扩示意（马车）
    d.rectangle((10, 890 - 120 - 8, 152 + 8, 890 + 8), outline=(110, 110, 110), width=1)

    # 层级标注：写在街道空档里，不压任何建筑
    text(d, (392, 320), "远 · h 110", 11, C_FAINT)
    text(d, (392, 470), "中 · h 145", 11, C_FAINT)
    text(d, (398, 772), "近 · h 190", 11, C_FAINT)
    text(d, (398, 800), "走廊留空 ·", 11, C_FAINT)
    text(d, (398, 818), "透视线汇到这里", 11, C_FAINT)

    # 安全区
    d.rectangle((0, 0, W, SAFE_TOP), fill=(0, 0, 0, 255))
    d.rectangle((0, H - SAFE_BOT, W, H), fill=(0, 0, 0, 255))
    text(d, (24, 40), "安全区 80", 12, (70, 70, 70), False, "lm")

    canvas.convert("RGB").save(OUT, "PNG")
    print("saved", OUT)


if __name__ == "__main__":
    main()

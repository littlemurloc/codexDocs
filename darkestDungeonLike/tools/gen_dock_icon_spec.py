"""生成 dock 图标的需求示意图（M64）。

一张图说清四件事：
  1. 交付画布多大、内容占多少、四周留多少；
  2. 图标在屏幕上**实际只有多大**（这是最容易画错的地方）；
  3. 放进圆环里之后，四周还能剩多少余量；
  4. 现在的 40px 素材放大后糊成什么样（反面教材）。

用法： python tools/gen_dock_icon_spec.py
输出： docs/dock_icons_spec.png
"""

import os

from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ATLAS = os.path.join(ROOT, "assets", "art", "ui", "skin", "atlas")
OUT = os.path.join(ROOT, "docs", "dock_icons_spec.png")

FONT = "C:/Windows/Fonts/msyh.ttc"
FONT_B = "C:/Windows/Fonts/msyhbd.ttc"


def f(sz, bold=False):
    try:
        return ImageFont.truetype(FONT_B if bold else FONT, sz)
    except OSError:
        return ImageFont.load_default()


def icon(name, size):
    im = Image.open(os.path.join(ATLAS, name + ".png")).convert("RGBA")
    im = im.resize((size, size), Image.LANCZOS)
    return im


def tab(canvas, cx, cy, rad, name, active=False, primary=False):
    """模拟游戏里那颗按钮，用来展示「图标放进圆环后的余量」。"""
    d = ImageDraw.Draw(canvas)
    # 注意：RGBA 画布上 `ImageDraw` 的 fill 是**直接写入**，不是混合 ——
    # 想画半透明必须单独起一层再 alpha_composite，否则会盖成一个实心色块。
    if active or primary:
        glow = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
        ImageDraw.Draw(glow).ellipse(
            (cx - rad - rad * 0.32, cy - rad - rad * 0.32,
             cx + rad + rad * 0.32, cy + rad + rad * 0.32),
            fill=(224, 174, 76, 26))
        canvas.alpha_composite(glow)
    d.ellipse((cx - rad, cy - rad, cx + rad, cy + rad), fill=(5, 5, 6, 255))
    d.ellipse((cx - rad + 3, cy - rad + 1, cx + rad - 3, cy + rad - 5),
              fill=(37, 34, 28, 255) if active else (22, 21, 20, 255))
    ring = (160, 125, 61, 255) if active else (
        (102, 84, 43, 255) if primary else (48, 46, 44, 255))
    d.ellipse((cx - rad + 2, cy - rad + 2, cx + rad - 2, cy + rad - 2),
              outline=ring, width=max(1, int(rad * 0.07)))
    isz = int(rad * (1.5 if primary else 1.45))
    canvas.alpha_composite(icon(name, isz), (cx - isz // 2, cy - isz // 2))


W, H = 1280, 730
canvas = Image.new("RGBA", (W, H), (17, 17, 19, 255))
d = ImageDraw.Draw(canvas)

d.text((36, 24), "底部导航图标 · 交付规格", font=f(30, True), fill=(232, 226, 214))
d.text((36, 66), "三颗：城镇 / 出征 / 商店　·　替补现有 40×40 的旧图（放大后糊）",
       font=f(16), fill=(150, 148, 142))

# ── 左：交付画布 ────────────────────────────────────────────────
BX, BY, BS = 40, 120, 420          # 画布示意区
d.text((BX, BY - 26), "1. 交付画布 512 × 512", font=f(19, True), fill=(214, 196, 168))
d.rectangle((BX, BY, BX + BS, BY + BS), fill=(28, 28, 31), outline=(86, 86, 92))
# 内容安全区：四周各留 11%
INSET = int(BS * 0.11)
for x in range(BX + INSET, BX + BS - INSET, 12):
    d.line((x, BY + INSET, x + 6, BY + INSET), fill=(190, 145, 62), width=2)
    d.line((x, BY + BS - INSET, x + 6, BY + BS - INSET), fill=(190, 145, 62), width=2)
for y in range(BY + INSET, BY + BS - INSET, 12):
    d.line((BX + INSET, y, BX + INSET, y + 6), fill=(190, 145, 62), width=2)
    d.line((BX + BS - INSET, y, BX + BS - INSET, y + 6), fill=(190, 145, 62), width=2)
demo = icon("icon_bust", int(BS * 0.56))
canvas.paste(demo, (BX + (BS - demo.width) // 2, BY + (BS - demo.height) // 2), demo)
d.text((BX + BS // 2 - 74, BY + INSET + 8), "内容区 78%", font=f(15), fill=(190, 145, 62))
d.text((BX + 10, BY + BS + 10),
       "四周各留 11% 透明（约 56px）—— 图标要进圆环，不能顶边",
       font=f(15), fill=(150, 148, 142))

# ── 右上：实际显示尺寸 ──────────────────────────────────────────
RX = 540
d.text((RX, BY - 26), "2. 屏幕上实际只有这么大（@750 宽）", font=f(19, True), fill=(214, 196, 168))
sizes = [(44, "icon_bust", "城镇", False), (62, "icon_deed", "出征", True),
         (44, "icon_gold", "商店", False)]
x = RX + 30
for px, name, lab, pri in sizes:
    tab(canvas, x + px // 2, BY + 70, px // 2, name, primary=pri)
    d.text((x, BY + 70 + px // 2 + 8), "%d px" % px, font=f(14, True), fill=(200, 196, 188))
    x += px + 56
d.text((RX + 30, BY + 178),
       "这就是玩家看到的真实大小。细节要在这一步还认得出，才算过关。",
       font=f(15), fill=(150, 148, 142))

# ── 右中：放大 2 倍看余量 ──────────────────────────────────────
Z = 2
ZTOP = BY + 224
d.text((RX, ZTOP), "3. 放大 2 倍：图标与圆环之间要留一圈空", font=f(19, True),
       fill=(214, 196, 168))
cy3 = ZTOP + 78 + 62 * Z // 2
x = RX + 50
for px, name, lab, pri in sizes:
    tab(canvas, x + px * Z // 2, cy3, px * Z // 2, name, primary=pri)
    x += px * Z + 46
d.text((RX + 10, ZTOP + 118 + 62 * Z),
       "图标别顶到环：占圆直径的 65~70% 最舒服，再大就挤成一坨暗色。",
       font=f(15), fill=(150, 148, 142))

# ── 右下：反面教材 ──────────────────────────────────────────────
FTOP = ZTOP + 118 + 62 * Z + 40
d.text((RX, FTOP), "4. 现在的素材是 40px，放大到 44 / 62 就糊", font=f(19, True),
       fill=(214, 196, 168))
d.text((RX + 10, FTOP + 32),
       "金币已经看不出是金币了。所以新图请按 512 交付，不要沿用 40px。",
       font=f(15), fill=(190, 118, 96))
canvas.convert("RGB").save(OUT)
print("wrote", OUT, canvas.size)

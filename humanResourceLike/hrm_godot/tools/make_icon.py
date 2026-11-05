# -*- coding: utf-8 -*-
"""给 H5 版画图标：照 stage.gd 里那只羊画 —— 白云身、深棕脸、黑腿、琥珀星。
一次生成 512 图标，导出时 Godot 自动缩出 favicon 和 splash。"""
from PIL import Image, ImageDraw
import math

S = 512
im = Image.new("RGBA", (S, S), (0, 0, 0, 0))
d = ImageDraw.Draw(im)

INK = (6, 44, 75, 255)        # 深蓝描边（游戏铁律色 #062c4b）
W = 14                        # 描边宽

# ---- 底：垂直渐变 面板蓝 #1470b4 → 深一档 #0e5a96，圆角，深描边 ----
R = 96
top, bot = (20, 112, 180), (14, 90, 150)
grad = Image.new("RGBA", (S, S))
gd = ImageDraw.Draw(grad)
for y in range(S):
    t = y / (S - 1)
    c = tuple(int(top[i] + (bot[i] - top[i]) * t) for i in range(3)) + (255,)
    gd.line([(0, y), (S, y)], fill=c)
mask = Image.new("L", (S, S), 0)
md = ImageDraw.Draw(mask)
md.rounded_rectangle([W, W, S - W, S - W], radius=R, fill=255)
im.paste(grad, (0, 0), mask)
d.rounded_rectangle([W, W, S - W, S - W], radius=R, outline=INK, width=W)

# ---- 星（先画，压在羊身后）----
def star(cx, cy, r, fill, rot=-math.pi / 2):
    pts = []
    for i in range(10):
        rr = r if i % 2 == 0 else r * 0.45
        a = rot + i * math.pi / 5
        pts.append((cx + rr * math.cos(a), cy + rr * math.sin(a)))
    return pts

d.polygon(star(400, 116, 52, (242, 181, 68, 255)), outline=INK, width=8)

# ---- 腿（在身体后面）----
for lx in (185, 235, 300, 345):
    d.line([(lx, 330), (lx, 398)], fill=(26, 26, 26, 255), width=22)
    d.line([(lx, 330), (lx, 398)], fill=(26, 26, 26, 255), width=22)

# ---- 身体：三个圆叠成云朵。先黑放大版再白版，外轮廓自然成描边 ----
def blob(circles, fill, grow):
    for (cx, cy, r) in circles:
        d.ellipse([cx - r - grow, cy - r - grow, cx + r + grow, cy + r + grow], fill=fill)

body = [(178, 268, 82), (256, 236, 100), (322, 268, 82)]
blob(body, INK, 8)          # 描边层
blob(body, (255, 255, 255, 255), 0)

# ---- 脸：深棕椭圆压在身体右缘，带描边；白眼圈黑瞳 ----
d.ellipse([296, 216, 428, 332], fill=INK)
d.ellipse([304, 224, 420, 324], fill=(91, 58, 36, 255))
# 耳朵：脸左上角探出去一小块
d.ellipse([276, 222, 330, 258], fill=(60, 38, 24, 255))
d.ellipse([284, 228, 322, 252], fill=(91, 58, 36, 255))
# 眼睛：白底黑瞳，位置偏脸的左上（朝左看，像在看自己身上）
d.ellipse([330, 248, 362, 280], fill=(255, 255, 255, 255))
d.ellipse([338, 256, 356, 274], fill=(20, 20, 20, 255))

im.save("assets/icon_512.png")
print("saved assets/icon_512.png")

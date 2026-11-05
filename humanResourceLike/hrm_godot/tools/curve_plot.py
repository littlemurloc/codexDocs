# -*- coding: utf-8 -*-
"""把 40 关的难度分画成折线图。改完关卡重跑一遍，就能看出曲线是不是又塌了。

用法（需要 Pillow）：
    python tools/curve_plot.py  _shots/v20/curve.png
"""
import json
import subprocess
import sys

from PIL import Image, ImageDraw, ImageFont

FONT = "C:/Windows/Fonts/msyh.ttc"
W, H = 1320, 620
PAD_L, PAD_R, PAD_T, PAD_B = 74, 40, 92, 76


def font(size):
    try:
        return ImageFont.truetype(FONT, size)
    except Exception:
        return ImageFont.load_default()


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else "_shots/curve.png"
    raw = subprocess.run(
        [sys.executable, "tools/vm_py.py", "--json"],
        capture_output=True, text=True, check=True).stdout
    rows = json.loads(raw)
    xs = [r["id"] for r in rows]
    ys = [r["score"] for r in rows]
    n1 = 20                                    # 教学段 / 进阶段的分界

    im = Image.new("RGB", (W, H), (16, 34, 56))
    d = ImageDraw.Draw(im)
    lo, hi = 10, max(ys) + 6

    def px(i):
        return PAD_L + (W - PAD_L - PAD_R) * (i - 1) / (len(xs) - 1)

    def py(v):
        return H - PAD_B - (H - PAD_T - PAD_B) * (v - lo) / (hi - lo)

    # 网格
    for v in range(20, int(hi) + 1, 10):
        y = py(v)
        d.line([(PAD_L, y), (W - PAD_R, y)], fill=(30, 58, 88))
        d.text((PAD_L - 12, y), str(v), font=font(15), fill=(120, 150, 185), anchor="rm")
    # 分段背景
    d.rectangle([px(1), PAD_T, px(n1), H - PAD_B], fill=(22, 42, 66))
    d.text((px(1) + 8, PAD_T - 26), "1-20  教学段（按指令组织，天然有起伏）",
           font=font(16), fill=(150, 180, 215))
    d.text((px(n1 + 1) + 8, PAD_T - 26), "21-40  进阶段（按任务组织，难度单调上升）",
           font=font(16), fill=(150, 220, 190))

    # 理想线性参考线
    d.line([(px(1), py(ys[0])), (px(len(xs)), py(max(ys)))],
           fill=(70, 96, 128), width=2)
    # 折线：两段分开配色
    for a, b, col in ((0, n1 - 1, (255, 205, 70)), (n1, len(xs) - 1, (110, 220, 160))):
        pts = [(px(xs[i]), py(ys[i])) for i in range(a, b + 1)]
        d.line(pts, fill=col, width=3, joint="curve")
        for p in pts:
            d.ellipse([p[0] - 4, p[1] - 4, p[0] + 4, p[1] + 4], fill=col)

    # 教学段的三处塌陷，点名
    for lv, note in ((14, "第 14 关掉回第 3 关的水平"), (19, "第 19 关掉回第 5 关")):
        i = xs.index(lv)
        y = py(ys[i])
        d.ellipse([px(lv) - 8, y - 8, px(lv) + 8, y + 8], outline=(232, 85, 63), width=2)
        d.text((px(lv) + 12, y + 14), note, font=font(14), fill=(232, 130, 110))

    # 轴标签
    for i in xs:
        if i % 2 == 1 or i in (n1, len(xs)):
            d.text((px(i), H - PAD_B + 14), str(i), font=font(14),
                   fill=(120, 150, 185), anchor="mm")
    d.text((W - PAD_R, H - 22), "关卡", font=font(14), fill=(120, 150, 185), anchor="rm")
    d.text((PAD_L, 20), "难度分 = 参考解步数 + 可选指令数×1.5 + 木牌数×2 + 跳转嵌套×4 + 新概念×6",
           font=font(15), fill=(150, 180, 215))
    im.save(out)
    print("saved", out, im.size)


if __name__ == "__main__":
    main()

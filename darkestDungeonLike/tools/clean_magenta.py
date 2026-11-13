"""清掉已入库 PNG 上的**弱品红残留**（M64）。

背景：品红底素材第一次抠图时只认「明显品红」（`min(r,b) - g` 很大），
边缘和半透明区留下的 `mag` 在 18~30 之间的像素被当成正常内容保留了。
单个像素看不出来，但它们**连成线**就是一条粉边
（城镇屏上酒馆底部那条紫粉色的轮廓就是这么来的）。

判据仍然是 `mag = min(r, b) - g`：
  - 墨线是中性黑，`mag ≈ 0`；
  - 纯品红 `mag ≈ 255`；
  - JPEG 抗锯齿混出来的淡品红落在中间 —— 正是要清的那一档。

    mag <= 8        完全保留
    8 < mag < 22   alpha 线性降到 0，同时把 r/b 往 g 拉（去溢色）
    mag >= 22      全透明

这张图是墨线稿，画面里没有真正的品红内容，所以可以放心清。

用法：
    python tools/clean_magenta.py                 # 清 bg_near + 8 张建筑
    python tools/clean_magenta.py --dry           # 只统计，不写文件
"""

import glob
import os
import sys

import numpy as np
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOWN = os.path.join(ROOT, "assets", "art", "ui", "town")

LO = 8.0    # 这个值以下完全保留
HI = 22.0   # 这个值以上全透明


def clean(path: str, dry: bool = False) -> int:
    im = Image.open(path).convert("RGBA")
    a = np.asarray(im).astype(np.float32)
    r, g, b, al = a[..., 0], a[..., 1], a[..., 2], a[..., 3]
    mag = np.minimum(r, b) - g

    bad_before = int(((mag > 18) & (al > 30)).sum())

    t = np.clip((mag - LO) / (HI - LO), 0.0, 1.0)
    # 去溢色：把 r/b 朝 g 拉；alpha 同步降，两者必须一起做，
    # 只降 alpha 不拉颜色的话，边缘会变成「半透明的粉色」。
    a[..., 0] = r * (1.0 - t) + g * t
    a[..., 2] = b * (1.0 - t) + g * t
    a[..., 3] = al * (1.0 - t)

    out = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8), "RGBA")
    if not dry:
        out.save(path)

    chk = np.asarray(out).astype(np.float32)
    mag2 = np.minimum(chk[..., 0], chk[..., 2]) - chk[..., 1]
    bad_after = int(((mag2 > 18) & (chk[..., 3] > 30)).sum())
    print("%-24s 残留 %6d → %6d" % (os.path.basename(path), bad_before, bad_after))
    return bad_after


def main() -> None:
    dry = "--dry" in sys.argv
    targets = [os.path.join(TOWN, "bg_near.png")]
    targets += sorted(glob.glob(os.path.join(TOWN, "bld_*.png")))
    left = 0
    for p in targets:
        if os.path.exists(p):
            left += clean(p, dry)
    print("总残留：%d" % left)


if __name__ == "__main__":
    main()

"""把 AI 生成的怪物立绘处理成 `assets/art/units/` 能直接用的规格。

## 为什么需要这一步

生成器吐出来的是 1024×1536 的整张图，右下角还带一个水印。
而游戏那边（`UnitArt` / `_draw_unit`）的约定是：

  * 透明背景
  * 人物本体高 **400px**（和英雄同一套缩放比，README §2）
  * 脚底贴画布底边、左右居中

不归一化的话，怪物站在英雄旁边会一会儿偏大一会儿偏小，
而且每只的"脚底线"不一样 —— 看着像浮在空中。

## 用法

    python tools/gen_monster_art.py 输入.png cultist_brawler
    python tools/gen_monster_art.py 输入.png cultist_brawler --keep-watermark
    python tools/gen_monster_art.py 输入.png --inspect

`--inspect` 只打印尺寸和非透明区域的包围盒，不写文件。
"""

import sys
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "assets" / "art" / "units"

# 人物本体高度，与英雄帧一致（README §2：按"脚底到头顶"400 归一）
TARGET_H = 400

# 水印固定在右下角。给一个略大的框，宁可多清一点也不留半截字。
WM_W = 320
WM_H = 120


def despill(arr: np.ndarray) -> np.ndarray:
    """去掉抠图边缘残留的品红（M207）。

    **为什么必须做**：只把"接近底色"的像素 alpha 置 0 是不够的。
    轮廓外那一圈抗锯齿像素是"品红 + 人物色"的混合，颜色距离已经拉开，
    会被当成内容留下 —— 在深色战场上就是一圈**粉边 / 粉块**
    （第一版就是这么翻车的，而且**用品红底检查图看不出来**：品红压在品红上）。

    判据用标准的溢色量 `mag = min(R,B) - G`：
      · 褐色 / 灰绿人物：B 接近 G，mag 是负数或很小 → 不动
      · 品红混出来的边：R 和 B 都远高于 G，mag 极大 → 压回中性
    """
    r = arr[:, :, 0].astype(int)
    g = arr[:, :, 1].astype(int)
    b = arr[:, :, 2].astype(int)
    mag = np.minimum(r, b) - g
    alive = arr[:, :, 3] > 0

    # 1) 强溢出的像素（纯品红边）：直接判成背景
    strong = (mag > 55) & alive
    arr[strong, 3] = 0

    # 2) 弱溢出：把 R / B 压到 G 附近，颜色拉回中性
    weak = (mag > 8) & (arr[:, :, 3] > 0)
    arr[weak, 0] = np.minimum(r[weak], g[weak] + 10).astype(np.uint8)
    arr[weak, 2] = np.minimum(b[weak], g[weak] + 10).astype(np.uint8)

    # 3) 极淡的边缘（alpha < 40）：留着只会是噪点
    arr[arr[:, :, 3] < 40, 3] = 0
    return arr


def cutout_background(im: Image.Image) -> Image.Image:
    """按"与四角底色接近"判背景，整块清掉。

    **不能用 alpha**：生成器对 `transparent` 的处理是**画一层东西**，
    整张图 alpha 全是 255（M205 实测）。

    **也不能写死"亮灰"**：同一个 prompt 两次生成，一次给暖灰（亮度 200），
    一次给深灰（亮度 ~70）—— 写死阈值只在某一次能work（M206 踩到）。

    所以底色**从四个角现取**（各 24×24 的中位数），再按颜色距离判：
    距离 < 42 且「接触画布边缘」或「面积 > 0.4% 画布」的块清掉。

    为什么还要"连通 + 面积"两道：只按颜色清，人物身上同色系的区域
    （灰绿袍子、暗部）会被打出洞。人物内部的小块同色区域不接触边缘、
    面积也小，两条都躲过。
    """
    from scipy import ndimage

    arr = np.array(im.convert("RGBA"))
    rgb = arr[:, :, :3].astype(int)
    h, w = rgb.shape[:2]
    pad = 24
    corners = [rgb[:pad, :pad], rgb[:pad, w - pad:], rgb[h - pad:, :pad], rgb[h - pad:, w - pad:]]
    flat = np.concatenate([c.reshape(-1, 3) for c in corners], axis=0)
    bg_color = np.median(flat, axis=0)
    dist = np.linalg.norm(rgb - bg_color, axis=2)

    # 先判这张图的背景是不是**纯色幕**（M206 定版做法）。
    #
    # 四角颜色的标准差很小 = 背景是一整块纯色（绿幕 / 品红幕）。
    # 这种图可以**直接按颜色距离全清**，不需要连通和面积两道兜底 ——
    # 纯色幕和人物颜色天然拉得开，不存在"帽子被当成背景"的风险。
    # 这也是批量出图应该走的路线：prompt 里要求 solid chroma background。
    spread = float(flat.reshape(-1, 3).std(axis=0).mean())
    if spread < 12.0:
        arr[dist < 50, 3] = 0
        return Image.fromarray(despill(arr))

    bg = dist < 42

    lab, n = ndimage.label(bg)
    if n == 0:
        return im
    sizes = ndimage.sum(bg, lab, index=np.arange(1, n + 1))
    edge_ids = set()
    for strip in (lab[0, :], lab[-1, :], lab[:, 0], lab[:, -1]):
        edge_ids.update(int(v) for v in np.unique(strip) if v != 0)
    big = 0.004 * float(bg.size)
    # 两道门槛，缺一不可（M206 第二版）：
    #   · 接触边缘 **且** 面积 > 1%  —— 真正的背景块一定够大；
    #   · 或者面积 > 3%  —— 被人物包围的大片背景（脚下阴影围出来的）。
    # 只写「接触边缘 或 面积大」，会把人物身上贴着轮廓的小块同色区域一起清掉：
    # 上一版邪教徒的**兜帽顶部**就是这么没的（深灰帽子挨着深灰背景，
    # 从边缘连通、面积又过了 0.4% 的线）。
    total = float(bg.size)
    clear = [i for i in range(1, n + 1)
             if (i in edge_ids and float(sizes[i - 1]) > 0.01 * total)
             or float(sizes[i - 1]) > 0.03 * total]
    if not clear:
        return im
    mask = np.isin(lab, clear)

    # 羽化一圈：硬切会在轮廓外留一条亮边（抗锯齿混出来的）
    mask = ndimage.binary_dilation(mask, iterations=1)
    arr[mask, 3] = 0
    return Image.fromarray(despill(arr))


def strip_watermark(im: Image.Image) -> Image.Image:
    """把右下角那块 alpha 清零。

    水印是半透明白字压在透明背景上，位置固定在右下角。
    只清 alpha、不改颜色：这块本来就没有人物内容（人物居中，脚在底部中央）。
    """
    arr = np.array(im)
    h, w = arr.shape[:2]
    x0 = max(0, w - WM_W)
    y0 = max(0, h - WM_H)
    arr[y0:h, x0:w, 3] = 0
    return Image.fromarray(arr)


def crop_and_scale(im: Image.Image, target_h: int = TARGET_H) -> Image.Image:
    """按非透明内容裁紧，再等比缩放到目标高度。"""
    arr = np.array(im)
    alpha = arr[:, :, 3]
    ys, xs = np.where(alpha > 8)
    if ys.size == 0:
        raise SystemExit("整张图都是透明的 —— 抠图或生成出了问题")
    top, bottom = int(ys.min()), int(ys.max())
    left, right = int(xs.min()), int(xs.max())
    boxed = im.crop((left, top, right + 1, bottom + 1))
    k = target_h / float(boxed.height)
    new_w = max(1, int(round(boxed.width * k)))
    return boxed.resize((new_w, target_h), Image.LANCZOS)


def main() -> None:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    flags = {a for a in sys.argv[1:] if a.startswith("--")}
    if not args:
        raise SystemExit(__doc__)
    src = Path(args[0])
    if not src.exists():
        raise SystemExit(f"找不到 {src}")
    im = Image.open(src).convert("RGBA")

    if "--inspect" in flags:
        arr = np.array(im)
        ys, xs = np.where(arr[:, :, 3] > 8)
        print(f"尺寸 {im.size[0]}×{im.size[1]}")
        print(f"非透明区域 x {xs.min()}–{xs.max()} · y {ys.min()}–{ys.max()}")
        return

    if len(args) < 2:
        raise SystemExit("要给出单位 id，例如 cultist_brawler")
    uid = args[1]
    # 动作帧与目标高度（M210）：`--anim=attack_melee` / `--target-h=170`
    #
    # 不同动作的**目标高度不能一样**：
    #   · combat / attack 是站姿，600→400 按"脚底到头顶"归一；
    #   · dead 是躺倒的一堆，按 400 归一会被放大成一个巨大的骨堆，
    #     视觉上像"站着的尸体缩水版"。实测按站姿的 42%（约 170）最像"躺在地上"。
    anim = "combat"
    target_h = TARGET_H
    for a in sys.argv[1:]:
        if a.startswith("--anim="):
            anim = a.split("=", 1)[1]
        elif a.startswith("--target-h="):
            target_h = int(a.split("=", 1)[1])

    if "--keep-watermark" not in flags:
        im = strip_watermark(im)
    # 生成器给的"透明"其实是画上去的棋盘格，必须自己抠（M205）
    im = cutout_background(im)
    im = crop_and_scale(im, target_h)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    dst = OUT_DIR / f"{uid}_{anim}.png"
    im.save(dst)
    print(f"已写出 {dst.relative_to(ROOT)}  {im.size[0]}×{im.size[1]}")


if __name__ == "__main__":
    main()

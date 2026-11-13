#!/usr/bin/env python
"""把出图方交付的 atlas 切成游戏用的单体图标。

用法：
    python tools/slice_atlas.py <交付目录>

交付目录里应当有 ATLAS_A.png / ATLAS_B.png / ATLAS_C.png（1024×1024）。
切完直接写进 `assets/art/ui/skin/`，命名与代码里的调用一致。

三件事：
  1. 按固定网格切，不依赖出图方是否画准格子线；
  2. 每个切片自动 trim 掉透明边再居中 —— 出图方很难保证每个图标
     在格子里位置完全一致，trim 之后至少视觉上是居中的；
  3. 缩到「显示尺寸 × 2」再存（手机屏是 2 倍密度），过大只会浪费内存。
"""
import os
import sys
from collections import deque

import numpy as np
from PIL import Image, ImageFilter

# 图集定义：编号 → (输出文件名, 显示尺寸)
# 显示尺寸要和 UI_ASSET_BRIEF.md 第 5 节一致
SHEETS = {
    "ATLAS_A": {
        "cols": 4, "rows": 4, "cell": 256,
        "map": {
            "A1":  ("icon_gold", 24),
            "A2":  ("icon_bust", 20),
            "A3":  ("icon_portrait", 20),
            "A4":  ("icon_crest", 20),
            "A5":  ("icon_deed", 20),
            "A6":  ("icon_food", 20),
            "A7":  ("icon_stress", 16),
            "A8":  ("icon_disease", 16),
            "A9":  ("icon_quirk", 16),
            "A10": ("icon_busy", 16),
            "A11": ("rank_apprentice", 28),
            "A12": ("rank_veteran", 28),
            "A13": ("rank_champion", 28),
        },
    },
    "ATLAS_B": {
        "cols": 3, "rows": 3, "cell": 341,
        "map": {
            "B1": ("emblem_empty", 96),
            "B2": ("emblem_blocked", 96),
            "B3": ("emblem_done", 96),
            "B4": ("sigil_weald", 56),
            "B5": ("sigil_crypts", 56),
            "B6": ("sigil_warrens", 56),
            "B7": ("sigil_cove", 56),
            "B8": ("seal_victory", 120),
        },
    },
    "ATLAS_C": {
        "cols": 4, "rows": 4, "cell": 256,
        "map": {
            "C1": ("job_abomination", 24),
            "C2": ("job_antiquarian", 24),
            "C3": ("job_arbalest", 24),
            "C4": ("job_bounty_hunter", 24),
            "C5": ("job_crusader", 24),
            "C6": ("job_grave_robber", 24),
            "C7": ("job_hellion", 24),
            "C8": ("job_highwayman", 24),
            "C9": ("job_houndmaster", 24),
            "C10": ("job_jester", 24),
            "C11": ("job_leper", 24),
            "C12": ("job_man_at_arms", 24),
            "C13": ("job_occultist", 24),
            "C14": ("job_plague_doctor", 24),
            "C15": ("job_vestal", 24),
        },
    },
}

OUT_DIR = os.path.join("assets", "art", "ui", "skin")


def _channel_diff(a, b):
    return max(abs(int(a[i]) - int(b[i])) for i in range(3))


def key_out(cell, key_rgb, tol=40, checker=False, seal_holes=False):
    """把「从四角能连通的底色」抠成透明。

    出图方如果交的是实底（白/黑/品红/棋盘格），整格都是不透明的，
    直接 trim 会把整个格子当内容保留，游戏里就是一个方块。

    三个要点：
      1. **从四角 BFS，不是全局阈值** —— 图标内部可能有和背景同色的区域
         （羊皮纸、骨头、大理石），全局抠会把它挖空。
      2. **逐通道比较，不用 PIL 的 floodfill** —— `ImageDraw.floodfill` 的
         thresh 比的是三通道差之和，棋盘格两档灰（252/220）sum 差 96，
         看起来「差不多」实际过不去，结果只抠掉一个格子。
      3. **棋盘格按「亮度 + 饱和」判定**，不认具体色值：它每格都是无彩灰，
         而大理石半身像是有色调的（饱和 > 20），能分开。
    """
    a = np.asarray(cell.convert("RGBA")).astype(np.int16)
    h, w = a.shape[:2]
    rgb = a[..., :3]
    if checker:
        lum = 0.299 * rgb[..., 0] + 0.587 * rgb[..., 1] + 0.114 * rgb[..., 2]
        sat = rgb.max(axis=2) - rgb.min(axis=2)
        cand = (lum > 196) & (sat <= 16)
    else:
        cand = np.abs(rgb - np.array(key_rgb, dtype=np.int16)).max(axis=2) <= tol

    visited = np.zeros((h, w), bool)
    dq = deque()
    for y, x in ((0, 0), (0, w - 1), (h - 1, 0), (h - 1, w - 1)):
        if cand[y, x] and not visited[y, x]:
            visited[y, x] = True
            dq.append((y, x))
    while dq:
        y, x = dq.popleft()
        if y > 0 and cand[y - 1, x] and not visited[y - 1, x]:
            visited[y - 1, x] = True; dq.append((y - 1, x))
        if y < h - 1 and cand[y + 1, x] and not visited[y + 1, x]:
            visited[y + 1, x] = True; dq.append((y + 1, x))
        if x > 0 and cand[y, x - 1] and not visited[y, x - 1]:
            visited[y, x - 1] = True; dq.append((y, x - 1))
        if x < w - 1 and cand[y, x + 1] and not visited[y, x + 1]:
            visited[y, x + 1] = True; dq.append((y, x + 1))

    if seal_holes:
        # 品红底特有：獠牙之间、墓碑与骨头之间的空隙被图案围住，
        # 从四角 BFS 进不去，会留下一块亮品红。纯品红不可能出现在图标里，
        # 所以把所有「同色但没连到边界」的连通块也一起填掉。
        for y0 in range(h):
            for x0 in range(w):
                if cand[y0, x0] and not visited[y0, x0]:
                    visited[y0, x0] = True
                    dq.append((y0, x0))
                    while dq:
                        y, x = dq.popleft()
                        for ny, nx in ((y - 1, x), (y + 1, x), (y, x - 1), (y, x + 1)):
                            if 0 <= ny < h and 0 <= nx < w and cand[ny, nx] and not visited[ny, nx]:
                                visited[ny, nx] = True
                                dq.append((ny, nx))

    a[visited] = (0, 0, 0, 0)
    # 去边缘残色：jpg 有压缩，抠完边缘会留一圈「品红混黑」的紫边。
    # 把半透明的、颜色仍偏背景的像素直接清掉，比保留一条紫线好看。
    if seal_holes:
        alpha = a[..., 3]
        rgb = a[..., :3]
        close = np.abs(rgb - np.array(key_rgb, dtype=np.int16)).max(axis=2) <= 90
        a[close & (alpha > 0)] = (0, 0, 0, 0)
        # 再削掉边缘 1px：jpg 在「品红 → 黑描边」之间会留一圈紫红过渡，
        # 颜色差得远、阈值清不掉，只能连像素一起削。原图 512px，
        # 缩到 56px 显示时这 1px 本来也不见了。
        im = Image.fromarray(a.astype(np.uint8), "RGBA")
        al = im.getchannel("A").filter(ImageFilter.MinFilter(3))
        im.putalpha(al)
        return im
    return Image.fromarray(a.astype(np.uint8), "RGBA")


def opaque_ratio(im):
    a = im.getchannel("A")
    hist = a.histogram()
    return sum(hist[200:]) / float(im.width * im.height)


def trim(im):
    bb = im.getbbox()
    return im.crop(bb) if bb else None


def slice_sheet(path, spec, out_dir, scale=2, key=None, checker=False, lift=False):
    sheet = Image.open(path).convert("RGBA")
    made, skipped, warned = [], [], []
    # 按图片实际尺寸算格子，不写死 1024 —— 出图方常交 2048。
    # 用浮点除再取整：3 列时 2048/3 除不尽，累加取整会逐格偏移。
    sw, sh = sheet.size
    cw_f, ch_f = sw / float(spec["cols"]), sh / float(spec["rows"])
    for code, (name, show) in spec["map"].items():
        n = int(code[1:]) - 1
        col, row = n % spec["cols"], n // spec["cols"]
        box = (round(col * cw_f), round(row * ch_f),
               round((col + 1) * cw_f), round((row + 1) * ch_f))
        cell = sheet.crop(box)
        if checker:
            cell = key_out(cell, None, checker=True)
        elif key is not None:
            cell = key_out(cell, key, tol=48, seal_holes=True)
        elif opaque_ratio(cell) > 0.97:
            # 97% 以上不透明 = 这格基本是实底，要么没画，要么带了背景色
            warned.append(code)
        body = trim(cell)
        if body is None:
            # 透明空格：出图方没画，跳过而不是写一张空图 ——
            # 空图会被游戏当成「加载到了但没内容」，比缺图更难排查
            skipped.append(code)
            continue
        target = show * scale
        # 等比缩放到目标边长内，再居中贴到透明方画布上
        k = min(target / body.width, target / body.height)
        body = body.resize((max(1, round(body.width * k)),
                            max(1, round(body.height * k))), Image.LANCZOS)
        canvas = Image.new("RGBA", (target, target), (0, 0, 0, 0))
        canvas.alpha_composite(body, ((target - body.width) // 2,
                                      (target - body.height) // 2))
        if lift:
            canvas = lift_silhouette(canvas)
        canvas.save(os.path.join(out_dir, name + ".png"))
        made.append(name)
    return made, skipped, warned


def lift_silhouette(im, lo=8.0, hi=72.0, out_lo=0.46, out_hi=0.92):
    """把纯黑剪影提成「浅色版画」。

    ATLAS_C 交的是纯黑剪影（平均亮度 15、最亮 64），
    直接放到 #14161a 的深色界面上等于隐形。
    这里按亮度重映射到暖白区间：保留内部的明暗起伏，但整体抬到可读。
    """
    a = np.asarray(im.convert("RGBA")).astype(np.float32)
    rgb = a[..., :3]
    lum = 0.299 * rgb[..., 0] + 0.587 * rgb[..., 1] + 0.114 * rgb[..., 2]
    t = np.clip((lum - lo) / max(1.0, hi - lo), 0.0, 1.0)
    v = (out_lo + (out_hi - out_lo) * t) * 255.0
    a[..., 0] = v
    a[..., 1] = v * 0.965
    a[..., 2] = v * 0.895
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8), "RGBA")


def parse_key(arg):
    if not arg:
        return None
    a = arg.lstrip("#")
    if len(a) != 6:
        raise SystemExit("--key 要写成 #RRGGBB")
    return tuple(int(a[i:i + 2], 16) for i in (0, 2, 4))


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    flags = [a for a in sys.argv[1:] if a.startswith("--")]
    src = args[0] if args else os.path.join("docs", "ui_atlas")
    key = None
    checker = False
    lift = False
    for f in flags:
        if f.startswith("--key="):
            key = parse_key(f.split("=", 1)[1])
        elif f == "--checker":
            checker = True
        elif f == "--lift":
            lift = True
    os.makedirs(OUT_DIR, exist_ok=True)
    total, empty, solid = 0, [], []
    for sheet_name, spec in SHEETS.items():
        path = None
        for ext in (".png", ".jpg", ".jpeg", ".webp"):
            cand = os.path.join(src, sheet_name + ext)
            if os.path.exists(cand):
                path = cand
                break
        if path is None:
            print("[跳过] 没有 %s.*" % sheet_name)
            continue
        use_checker = checker
        if not use_checker and key is None:
            use_checker = looks_like_checkerboard(Image.open(path).convert("RGBA"))
            if use_checker:
                print("  （检测到棋盘格假透明，自动按棋盘格抠图）")
        # ATLAS_C 是纯黑剪影，自动提亮
        use_lift = lift or sheet_name == "ATLAS_C"
        made, skipped, warned = slice_sheet(path, spec, OUT_DIR, key=key,
                                            checker=use_checker, lift=use_lift)
        total += len(made)
        empty += skipped
        solid += warned
        print("%s：切出 %d 张%s" % (
            sheet_name, len(made),
            ("，空格 " + "、".join(skipped)) if skipped else ""))
    print("\n共输出 %d 张到 %s" % (total, OUT_DIR))
    if empty:
        print("以下编号是空的（图集里那格透明）：%s" % "、".join(empty))
    if solid:
        print("\n[警告] 这些格子几乎完全不透明，很可能带了底色：%s" % "、".join(solid))
        print("       如果是白/黑/品红底，加参数重跑：--key=#FFFFFF 或 --key=#FF00FF")
    print("提示：新图放进 assets/ 之后要跑一次 "
          "`godot --headless --path . --editor --quit` 才会被导入。")


if __name__ == "__main__":
    main()

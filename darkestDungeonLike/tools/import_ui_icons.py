"""把美术交付的四张多图标合成图切成单个 256×256 透明 PNG。

为什么按「列区间内再做行投影」切，而不是连通域：
  图标内部有碎屑（剑周围的小石、号角的音波线），连通域会被拆成好几块；
  而这四张图都是规整网格，投影切最稳。

trinket 那张第二、三行看起来重复，脚本会把每格的内容哈希打出来 ——
如果真是同一张，就只留前 10 个（后面 5 个是备用的不同变体）。
"""
import hashlib
import os

import numpy as np
from PIL import Image

SRC = ".tmp/icons2_src"
OUT = "assets/art/ui/icons"
SIZE = 256
# 内容占画布的比例。0.97 = 长边几乎贴满，只留 3px 给抗锯齿边。
#
# 原来是 0.80，看着「方格里空一圈」：窄高物体（圣水那种瓶子）按长边等比缩放，
# 长边只到 80%，宽度本来就窄，两头一叠就只剩半个格子。
# 留边距的顾虑是「贴边被裁」—— 但下面已经先按 alpha bbox 裁紧了，
# 再留 3px 就够，不需要 20%。
FILL = 0.97

# 每组：文件名 → 按行优先排列的 (id, 中文名)
GROUPS = {
    "skill": [
        ("skill_melee", "近战"), ("skill_ranged", "远程"), ("skill_heal", "治疗"),
        ("skill_buff", "增益"), ("skill_debuff", "减益"), ("skill_move", "位移"),
    ],
    "supply": [
        ("supply_antivenom", "解毒剂"), ("supply_bandage", "绷带"),
        ("supply_holy_water", "圣水"), ("supply_laudanum", "鸦片酊"),
        ("supply_herbs", "药草"), ("supply_shovel", "铲子"),
        ("supply_skeleton_key", "骷髅钥匙"), ("supply_torch", "火把"),
    ],
    "trinket": [
        ("trk_potion", "药瓶"), ("trk_feather", "羽毛"), ("trk_ring", "戒指"),
        ("trk_pendant", "吊坠"), ("trk_scroll", "书页"),
        ("trk_blade", "兵器"), ("trk_cloth", "衣物"), ("trk_bone", "骨头"),
        ("trk_chest", "容器"), ("trk_relic", "遗物"),
    ],
    "room": [
        ("room_start", "入口"), ("room_goal", "出口"), ("room_battle", "战斗"),
        ("room_boss", "首领"), ("room_curio", "奇物"), ("room_empty", "空房"),
    ],
}


def mag_mask(a):
    """洋红量：墨线是中性色（mag≈0），纯品红 mag≈255。"""
    r, g, b = a[:, :, 0], a[:, :, 1], a[:, :, 2]
    return np.minimum(r, b) - g


def cut_bands(v, thr=3, min_gap=12):
    """返回内容区段列表（跳过首尾空白）。"""
    segs, run = [], None
    for i, x in enumerate(v):
        if x >= thr:
            if run is None:
                run = i
        else:
            if run is not None:
                segs.append((run, i))
                run = None
    if run is not None:
        segs.append((run, len(v)))
    # 合并间隔很小的段（图标内部的缝隙不该被当成两格）
    merged = []
    for s in segs:
        if merged and s[0] - merged[-1][1] < min_gap:
            merged[-1] = (merged[-1][0], s[1])
        else:
            merged.append((s[0], s[1]))
    return merged


def group_rows(cells, tol=120):
    """按**段的起始 y** 归行，行内按 x 排序。

    不能用「中心点 / 常数 再 round」当分组键 —— skill 那张第一行三个的
    中心 y 是 329.5 / 330.5，除 60 四舍五入后正好跨档（5 和 6），
    整行顺序就乱了。而 r0（段起点）不受元素高度影响：
    神龛那种纵向跨两行的元素，r0 也仍然落在它所属的那一行。
    """
    cells = sorted(cells, key=lambda t: (t[1], t[0]))
    rows = []
    for c in cells:
        if rows and c[1] - rows[-1][0][1] <= tol:
            rows[-1].append(c)
        else:
            rows.append([c])
    out = []
    for r in rows:
        out.extend(sorted(r, key=lambda t: t[0]))
    return out


def extract(im, box):
    """从原图裁 box → 去品红 → 裁到内容 bbox → 缩放到 SIZE 的 FILL 内 → 居中。"""
    a = np.asarray(im.crop(box)).astype(int)
    mag = mag_mask(a)
    r, g, b = a[:, :, 0], a[:, :, 1], a[:, :, 2]
    # alpha：mag<=8 全保留，8~22 线性，>=22 全透明
    t = np.clip((mag - 8) / 14.0, 0.0, 1.0)
    alpha = (255 * (1.0 - t)).astype(np.uint8)
    # 去溢色：把 r/b 朝 g 拉
    nr = (r * (1 - t) + g * t).astype(np.uint8)
    nb = (b * (1 - t) + g * t).astype(np.uint8)
    rgba = np.dstack([nr, g.astype(np.uint8), nb, alpha])
    sp = Image.fromarray(rgba, "RGBA")
    bb = sp.getbbox()
    if bb is None:
        return None, "empty"
    sp = sp.crop(bb)
    k = min(SIZE * FILL / sp.width, SIZE * FILL / sp.height)
    sp = sp.resize((max(1, int(sp.width * k)), max(1, int(sp.height * k))), Image.LANCZOS)
    canvas = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    canvas.alpha_composite(sp, ((SIZE - sp.width) // 2, (SIZE - sp.height) // 2))
    return canvas, "ok"


def main():
    os.makedirs(OUT, exist_ok=True)
    report = []
    for name, entries in GROUPS.items():
        im = Image.open(os.path.join(SRC, name + ".jpg")).convert("RGB")
        a = np.asarray(im).astype(int)
        fg = mag_mask(a) <= 40
        cols = cut_bands(fg.sum(axis=0))
        cells = []
        for c0, c1 in cols:
            # 在每列内部单独做行投影，避免「整张图行间距不均匀」导致跨格
            sub = fg[:, c0:c1]
            rows = cut_bands(sub.sum(axis=1))
            for r0, r1 in rows:
                cells.append((c0, r0, c1, r1))
        # 行优先排序（先按段起始 y 归行，再按 x）
        cells = group_rows(cells)
        report.append("== %s 切出 %d 格（期望 %d）" % (name, len(cells), len(entries)))
        for i, box in enumerate(cells):
            icon, st = extract(im, box)
            if i < len(entries):
                iid, cn = entries[i]
            else:
                iid, cn = "%s_extra%d" % (name, i), "多余"
            if icon is None:
                report.append("   %-20s %s" % (iid, st))
                continue
            p = os.path.join(OUT, iid + ".png")
            icon.save(p)
            h = hashlib.md5(np.asarray(icon).tobytes()).hexdigest()[:8]
            report.append("   %-20s %-6s %4d×%-4d bbox=%s hash=%s" % (
                iid, cn, box[2] - box[0], box[3] - box[1], box, h))
    print("\n".join(report))


if __name__ == "__main__":
    main()

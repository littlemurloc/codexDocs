"""把美术交付的 dock 图标（品红底 JPG）处理成 512×512 透明 PNG（M64）。

交付原图是品红底（#FF00FF）的 JPG，内容几乎铺满。处理四步：
  1. 按「洋红含量」出 alpha，并去溢色（和 bg_near 同一套阈值）；
  2. 裁到内容 bbox —— 原图的品红边距不该占掉画布的 11%；
  3. 等比缩放到最大边 410px（512 的 80%，落在需求书的 78~84% 区间）；
  4. 居中贴到 512×512 透明画布。

用法： python tools/import_dock_icons.py
输出： assets/art/ui/town/dock/icon_{town,gate,shop}.png
"""

import os

import numpy as np
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, ".tmp", "dock_src")
OUT = os.path.join(ROOT, "assets", "art", "ui", "town", "dock")

CANVAS = 512
CONTENT = 410          # 512 的 80%
LO, HI = 8.0, 22.0     # mag <= LO 保留；>= HI 全透明；中间线性过渡

FILES = {
    "town": "town.jpg",
    "gate": "gate.jpg",
    "shop": "shop.jpg",
}


def key_matte(im: Image.Image) -> Image.Image:
    """品红底 → 透明。`mag = min(r,b) - g`：墨线中性，mag≈0；纯品红 mag≈255。

    阈值别放宽 —— 8~22 这一段是 JPEG 抗锯齿混出来的淡品红，
    单看不明显，连成线就是一圈粉边。
    """
    a = np.asarray(im.convert("RGB")).astype(np.float32)
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    mag = np.minimum(r, b) - g
    t = np.clip((mag - LO) / (HI - LO), 0.0, 1.0)
    out = np.empty((a.shape[0], a.shape[1], 4), np.uint8)
    out[..., 0] = np.clip(r * (1 - t) + g * t, 0, 255)
    out[..., 1] = np.clip(g, 0, 255)
    out[..., 2] = np.clip(b * (1 - t) + g * t, 0, 255)
    out[..., 3] = np.clip(255.0 * (1.0 - t), 0, 255)
    return Image.fromarray(out, "RGBA")


def place(im: Image.Image, name: str) -> None:
    box = im.getbbox()
    if box:
        im = im.crop(box)
    k = CONTENT / max(im.width, im.height)
    im = im.resize((max(1, int(round(im.width * k))),
                    max(1, int(round(im.height * k)))), Image.LANCZOS)
    canvas = Image.new("RGBA", (CANVAS, CANVAS), (0, 0, 0, 0))
    canvas.alpha_composite(im, ((CANVAS - im.width) // 2, (CANVAS - im.height) // 2))
    path = os.path.join(OUT, "icon_%s.png" % name)
    canvas.save(path, "PNG")
    print("%-6s %s -> %s（内容 %d×%d）" % (name, "src", path, im.width, im.height))


def main() -> None:
    os.makedirs(OUT, exist_ok=True)
    for key, fn in FILES.items():
        p = os.path.join(SRC, fn)
        if not os.path.exists(p):
            print("缺文件：", p)
            continue
        place(key_matte(Image.open(p)), key)


if __name__ == "__main__":
    main()

# 安全区抽取演出 · 军需箱

用 image2 生成的军需箱封存和开封两帧。两张透明 PNG 等比裁放到 512 × 512 画布，共用同一条落地线，时间轴可在同一锚点衔接。

| 素材 | 用途 |
| --- | --- |
| `png/crate_closed.png` | 封条完整，补给演出起始 |
| `png/crate_open.png` | 箱盖掀开，内侧物资显露 |

在深色和品红背景检查了裁切、透明边缘与底部对齐。[透明检查图](preview_alpha_check.png)

`source/` 内有清稿和提示词，`manifest.json` 记录尺寸及源坐标，`y3-icons.json` 记录编辑器导入 ID。编辑器里可在 **美术资源 → 图标 → 玩家自定义** 搜索 `crate_closed` 和 `crate_open`。

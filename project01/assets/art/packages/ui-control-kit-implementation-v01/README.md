# 三国项目 UI 控件可实装资源包 v01

本包基于 `ui-control-kit-clean-layer-sample-v01` 的分层清稿生成，用于工程接入验证。

## 包结构

每套风格目录包含：

- `window/base_9slice.png`
- `baseplate/base_9slice.png`
- `headbar/base_9slice.png`
- `button_rect_normal/base_9slice.png`
- `button_rect_disabled/base_9slice.png`
- `button_circle_normal/base_fixed.png`
- `button_circle_disabled/base_fixed.png`
- `button_tab_normal/base_9slice.png`
- `button_tab_disabled/base_9slice.png`
- `overlays/overlay_*.png`
- `source/*.png`

根目录文件：

- `manifest.json`：每个控件的路径、尺寸、9 宫格 inset、源图裁切框。
- `preview_assets.png`：全部切片资源总览。
- `preview_9slice_stretch.png`：9 宫格拉伸预览。
- `preview_alpha_check.png`：黑/粉高对比透明通道检查图，用于发现背景残留、旁边控件残片和过大留白。
- `build_impl_pack.py`：从清稿重新生成本包的脚本。

## 实装方式

1. 读取 `manifest.json`。
2. 对 `scale_mode = nine_slice` 的控件使用 `nine_slice.left/top/right/bottom` 做 9 宫格。
3. 对 `scale_mode = fixed_uniform` 的圆形按钮只做等比缩放。
4. overlay 固定尺寸叠加，不进入 9 宫格拉伸。
5. 第三排组合预览不进入工程，只用于校验视觉目标。

## 风格目录

| 目录 | 风格 |
| --- | --- |
| `01_porcelain_map/` | 清瓷地图框 |
| `02_cinnabar_seal/` | 朱印令牌框 |
| `03_ink_brush/` | 墨刷浮层框 |
| `04_bronze_armor/` | 玄铁铜铆框 |
| `05_dossier_paper/` | 军务档案夹 |
| `06_jade_bi/` | 青玉璧环框 |

## 注意

这是第一版工程验证包。base 已按固定坐标从清稿切出，overlay 已透明化；如果后续某套风格要进入正式美术资源库，建议美术再输出原生透明 PNG 或 PSD 分层，以替换本包中由清稿自动透明化得到的 PNG。

## QA 记录

本包已做一次全面修正：

- 收紧 base 裁切框，去掉明显多余留白。
- 用 flood-fill 背景识别重算 base alpha，避免白底被保留。
- 重算 overlay alpha，并自动裁掉透明外框。
- 修正清瓷/朱印圆按钮上方残片。
- 修正墨刷/玄铁禁用态控件带到邻居控件的问题。
- 对军务档案与青玉的 `button_tab_normal` 做工程修复：源清稿 normal tab 右侧被相邻控件遮挡，因此用完整 disabled tab 轮廓重映射 normal 材质，`manifest.json` 中已记录 `repair_note`。

本轮追加修正：

- 外围白色描边不是透明的问题已修正：从画布边缘连通进来的近白色低饱和像素统一设为 `alpha = 0`。
- 资源重新加了 2px 真透明安全边，避免边缘高光或角点被裁断。
- 对切割后缺边/缺角风险较高的 normal tab 做了二次完整性处理。
- `preview_alpha_check.png` 已更新为最终透明检查图。

本轮 overlay 拆分修正：

- `overlays/` 内装饰件已从合并图进一步拆成独立可锚定 PNG。
- 四角件、铆钉、小玉钉、连接件、红色划痕、金属尖刺等已按独立连通装饰拆分。
- 兽头、完整玉扣横饰、纸夹、印章框、龙纹、盾徽等本身作为单个装饰使用的元素保留为整体。
- `manifest.json` 中 overlay 数量由 57 个更新为 98 个，并记录 `source_overlay_group` 与 `group_part_index`，方便追溯它们来自清稿中的哪组装饰。

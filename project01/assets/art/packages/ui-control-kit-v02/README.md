# 三国斗阵 UI 控件资源包 v02

这版针对“外观样式变化不够”的问题重做。v02 不再只是换色，而是让每套在轮廓、边框结构、角部语言、材质密度和按钮形态上都有明显差异。

## 套装

| 目录 | 外观语言 | 建议用途 |
| --- | --- | --- |
| `01_porcelain_map/` | 圆角清瓷地图框，轻薄细线 | 全局窗口、地图、阵容、关卡基础界面 |
| `02_command_seal/` | 八角朱印令牌框，方印角钉 | 军令市场、奖励、购买确认、Set 融合 |
| `03_ink_brush/` | 暗墨斜切浮层，刷痕边缘 | 技能释放、短提示、战斗高压浮层 |
| `04_bronze_plate/` | 玄铁铜铆硬边框，铆钉与金属分割 | 装备、Boss、危险确认、精英战斗面板 |
| `05_dossier_paper/` | 军务档案夹，页签切口与档案纸底 | 图鉴、规则说明、战报、单卡详情 |
| `06_jade_bi/` | 青玉璧环框，六边弧形与玉环纹 | 成长、羁绊、增益、可用状态 |

## 每套资源

| 文件 | 类型 | 状态 | 拉伸 |
| --- | --- | --- | --- |
| `window_panel.png` | 窗口类控件 | 常态 | 九宫格 |
| `baseplate_panel.png` | 底板类装饰控件 | 常态 | 九宫格 |
| `headbar_panel.png` | headbar 类装饰控件 | 常态 | 九宫格 |
| `button_rect_normal.png` | 长方形按钮 | 常态 | 九宫格 |
| `button_rect_disabled.png` | 长方形按钮 | 禁止灰态 | 九宫格 |
| `button_circle_normal.png` | 圆形按钮 | 常态 | 等比缩放 |
| `button_circle_disabled.png` | 圆形按钮 | 禁止灰态 | 等比缩放 |
| `button_tab_normal.png` | 切页标签形按钮 | 常态 | 九宫格 |
| `button_tab_disabled.png` | 切页标签形按钮 | 禁止灰态 | 九宫格 |

## 预览

- `preview_contact_sheet.png`：全部 54 个控件总览。
- `preview_9slice_stretch_test.png`：九宫格放大测试图。
- `manifest.json`：尺寸、状态、九宫格参数与建议用途。

## 接入说明

- 九宫格参数见 `manifest.json` 的 `nine_slice` 字段，格式为 `left/top/right/bottom` 像素 inset。
- 圆形按钮建议只做等比缩放，不做九宫格拉伸。
- 所有控件不含文字，文本、数值、图标由工程层叠加。
- 当前仍是审美/工程草案资源，进入正式资源库前建议主美确认外观方向。

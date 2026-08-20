# 三国斗阵 UI 控件资源包 v01

本目录是从本轮 UI 效果图方向中拆出的工程可用控件草案。资源为透明 PNG，配套 `manifest.json` 记录尺寸、状态与九宫格拉伸参数。

## 套装

| 目录 | 风格 | 建议用途 |
| --- | --- | --- |
| `A_clean_porcelain/` | 清瓷战图 | 全局窗口、常规面板、地图/阵容/关卡基础 UI |
| `B_cinnabar_command/` | 朱令金章 | 军令市场、奖励、Set 融合、购买确认 |
| `C_dark_ink/` | 墨锋军务 | 战斗 HUD、Boss 预警、技能/军令释放状态 |
| `D_sandtable_campaign/` | 沙盘营帐 | 关卡地图、布阵、路线选择、战前推演 |
| `E_military_dossier/` | 军务档案 | 图鉴、规则说明、详情面板、战报 |
| `F_celadon_jade/` | 青瓷玉令 | 成长、羁绊、可用/增益状态 |
| `G_bronze_armor/` | 玄铁铜甲 | 装备、精英、Boss、危险确认 |
| `H_plain_ink/` | 素墨留白 | 轻弹窗、教程、二级信息、通用说明 |

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

- `preview_contact_sheet.png`：全部 72 个控件总览。
- `preview_9slice_stretch_test.png`：九宫格放大测试图。

## 接入说明

- 九宫格参数见 `manifest.json` 的 `nine_slice` 字段，格式为 `left/top/right/bottom` 像素 inset。
- 圆形按钮不建议九宫格拉伸，使用等比缩放。
- 所有资源不包含文字，文本、数值、图标由工程层叠加。
- 当前状态为效果图方向拆分出的草案资源，进入正式资源库前仍建议做一次主美/主策审美确认。

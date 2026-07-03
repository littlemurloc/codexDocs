# P0 Processed UI Resources

本目录保存首轮 Y3 原型验收优先使用的 P0 工程占位资源。资源来源于 `assets/ui/export/` 第一轮参考切片，加工目标是去除固定文字、补最低状态、整理复用关系。

## 使用边界

- 当前资源是工程占位级，不是最终美术交付。
- `assets/ui/export/` 保留为原始参考切片，本目录不覆盖原文件。
- 文案、数值、图标、头像建议全部由 Y3 工程层动态渲染。
- 九宫格参数以本 README 的 `建议九宫格边距` 为准，不强制依赖文件名后缀。

## 第一批已处理资源

### Common

| 资源 | 来源 | 状态 | 建议九宫格边距 L/T/R/B | 用途 |
| --- | --- | --- | --- | --- |
| `common/button-primary-red-normal.png` | `export/common/button-red-large.png` | 普通 | 42/22/42/22 | 红色主按钮底。 |
| `common/button-primary-red-pressed.png` | `common/button-primary-red-normal.png` | 按下 | 42/22/42/22 | 红色主按钮按下态。 |
| `common/button-primary-red-disabled.png` | `common/button-primary-red-normal.png` | 禁用 | 42/22/42/22 | 红色主按钮禁用态。 |
| `common/button-primary-red-wide-normal.png` | `export/common/button-red-wide.png` | 普通 | 48/20/48/20 | 红色宽按钮底。 |
| `common/button-primary-red-wide-pressed.png` | `common/button-primary-red-wide-normal.png` | 按下 | 48/20/48/20 | 红色宽按钮按下态。 |
| `common/button-primary-red-wide-disabled.png` | `common/button-primary-red-wide-normal.png` | 禁用 | 48/20/48/20 | 红色宽按钮禁用态。 |
| `common/button-primary-gold-normal.png` | `export/common/button-gold-wide.png` | 普通 | 42/18/42/18 | 金色确认按钮底。 |
| `common/button-primary-gold-pressed.png` | `common/button-primary-gold-normal.png` | 按下 | 42/18/42/18 | 金色确认按钮按下态。 |
| `common/button-primary-gold-disabled.png` | `common/button-primary-gold-normal.png` | 禁用 | 42/18/42/18 | 金色确认按钮禁用态。 |
| `common/info-bar-dark.png` | `export/common/bottom-info-bar-dark.png` | 普通 | 32/16/32/16 | 通用底部信息条。 |

### Battle

| 资源 | 来源 | 状态 | 建议九宫格边距 L/T/R/B | 用途 |
| --- | --- | --- | --- | --- |
| `battle/battle-top-bar.png` | `export/battle/battle-top-bar.png` | 普通 | 24/8/24/8 | 战斗顶部波次/时间/资源栏。 |
| `battle/battle-bottom-bar.png` | `export/battle/battle-bottom-status-bar.png` | 普通 | 32/14/32/14 | 战斗底部状态栏。 |
| `battle/prep-confirm-button-normal.png` | `export/battle/prep-confirm-button.png` | 普通 | 42/18/42/18 | 战备确认按钮。 |
| `battle/prep-confirm-button-pressed.png` | `battle/prep-confirm-button-normal.png` | 按下 | 42/18/42/18 | 战备确认按钮按下态。 |
| `battle/prep-confirm-button-disabled.png` | `battle/prep-confirm-button-normal.png` | 禁用 | 42/18/42/18 | 战备确认按钮禁用态。 |
| `battle/prep-card-normal.png` | `export/battle/prep-card-normal.png` | 普通 | 不建议九宫格 | 战备选择卡普通态无字版。 |
| `battle/prep-card-selected.png` | `export/battle/prep-card-selected.png` | 选中 | 不建议九宫格 | 战备选择卡选中态无字版。 |
| `battle/prep-card-rare.png` | `export/battle/prep-card-rare.png` | 稀有 | 不建议九宫格 | 战备选择卡稀有态无字版。 |
| `battle/prep-card-disabled.png` | `battle/prep-card-normal.png` | 不可选 | 不建议九宫格 | 战备选择卡不可选态。 |
| `battle/unit-card-active.png` | `export/battle/unit-card-active-1.png` | 已上阵 | 不建议九宫格 | 战斗 HUD 我方单位卡。 |
| `battle/unit-card-selected.png` | `battle/unit-card-active.png` | 选中 | 不建议九宫格 | 战斗 HUD 我方单位卡选中态。 |
| `battle/unit-card-empty.png` | `export/battle/unit-card-empty.png` | 空槽 | 不建议九宫格 | 战斗 HUD 空单位槽。 |
| `battle/unit-card-locked.png` | `battle/unit-card-empty.png` | 锁定 | 不建议九宫格 | 战斗 HUD 锁定单位槽。 |
| `battle/prep-preview-panel.png` | `export/battle/prep-left-preview-panel.png` | 普通 | 24/24/24/24 | 战备选择左侧下一波预览面板。 |
| `battle/prep-summary-panel.png` | `export/battle/prep-right-summary-panel.png` | 普通 | 24/24/24/24 | 战备选择右侧本局战备摘要面板。 |

### Lineup

| 资源 | 来源 | 状态 | 建议九宫格边距 L/T/R/B | 用途 |
| --- | --- | --- | --- | --- |
| `lineup/save-lineup-button-normal.png` | `export/lineup/save-lineup-button.png` | 普通 | 42/18/42/18 | 保存阵容按钮。 |
| `lineup/save-lineup-button-pressed.png` | `lineup/save-lineup-button-normal.png` | 按下 | 42/18/42/18 | 保存阵容按钮按下态。 |
| `lineup/save-lineup-button-disabled.png` | `lineup/save-lineup-button-normal.png` | 禁用 | 42/18/42/18 | 保存阵容按钮禁用态。 |
| `lineup/formation-slot-filled.png` | `export/lineup/formation-slot-filled-1.png` | 已上阵 | 不建议九宫格 | 阵容界面已上阵槽位。 |
| `lineup/formation-slot-empty.png` | `export/lineup/formation-slot-empty-1.png` | 空槽 | 不建议九宫格 | 阵容界面空槽位。 |
| `lineup/formation-slot-hover.png` | `lineup/formation-slot-empty.png` | 悬停 | 不建议九宫格 | 拖拽或选择目标槽提示。 |
| `lineup/formation-slot-locked.png` | `lineup/formation-slot-empty.png` | 锁定 | 不建议九宫格 | 未解锁出战槽。 |

### Settlement

| 资源 | 来源 | 状态 | 建议九宫格边距 L/T/R/B | 用途 |
| --- | --- | --- | --- | --- |
| `settlement/confirm-reward-button-normal.png` | `export/settlement/confirm-reward-button.png` | 普通 | 48/20/48/20 | 领取奖励按钮。 |
| `settlement/confirm-reward-button-pressed.png` | `settlement/confirm-reward-button-normal.png` | 按下 | 48/20/48/20 | 领取奖励按钮按下态。 |
| `settlement/confirm-reward-button-disabled.png` | `settlement/confirm-reward-button-normal.png` | 禁用 | 48/20/48/20 | 领取奖励按钮禁用态。 |
| `settlement/retry-button-normal.png` | `export/settlement/retry-button.png` | 普通 | 54/22/54/22 | 再战按钮。 |
| `settlement/retry-button-pressed.png` | `settlement/retry-button-normal.png` | 按下 | 54/22/54/22 | 再战按钮按下态。 |
| `settlement/retry-button-disabled.png` | `settlement/retry-button-normal.png` | 禁用 | 54/22/54/22 | 再战按钮禁用态。 |
| `settlement/adjust-lineup-button-normal.png` | `export/settlement/adjust-lineup-button.png` | 普通 | 42/20/42/20 | 调整阵容按钮。 |
| `settlement/adjust-lineup-button-pressed.png` | `settlement/adjust-lineup-button-normal.png` | 按下 | 42/20/42/20 | 调整阵容按钮按下态。 |
| `settlement/adjust-lineup-button-disabled.png` | `settlement/adjust-lineup-button-normal.png` | 禁用 | 42/20/42/20 | 调整阵容按钮禁用态。 |
| `settlement/reward-card-normal.png` | `export/settlement/reward-card-normal-1.png` | 普通 | 不建议九宫格 | 奖励选择卡普通态无字版。 |
| `settlement/reward-card-selected.png` | `export/settlement/reward-card-selected.png` | 选中 | 不建议九宫格 | 奖励选择卡选中态无字版。 |
| `settlement/reward-card-disabled.png` | `settlement/reward-card-normal.png` | 不可选 | 不建议九宫格 | 奖励选择卡不可选态。 |
| `settlement/reward-summary-panel.png` | `export/settlement/reward-summary-panel.png` | 普通 | 18/18/18/18 | 通关摘要面板无字版。 |
| `settlement/failure-summary-panel.png` | `export/settlement/failure-summary-panel.png` | 普通 | 18/18/18/18 | 失败挑战摘要面板无字版。 |

## 后续批次

1. P0 首轮工程占位资源已覆盖阵容、战斗 HUD、战备选择、通关奖励和失败结算主流程。

## 卡牌资源说明

- 战备卡和奖励卡保留了卡框、选中框、推荐色带、图标圆框、标题槽、标签槽和说明槽。
- 固定文字、固定数值和固定图标已移除，后续应由 Y3 工程文本和图标层填充。
- 当前卡牌仍是矩形 PNG，不是最终透明描边卡。若后续需要精细透明边缘，应在正式美术阶段基于源文件重新导出。

## 单位与槽位资源说明

- 战斗单位卡保留头像区、职业/标签区、生命/能量条、技能槽和装备槽，固定武将图、名称、数值已移除。
- 阵容槽位保留大头像区、名称/职业标签区和基础属性槽，固定武将图、阵营字、等级和属性数值已移除。
- `selected` 和 `hover` 当前使用高亮边框表达，后续正式美术可替换为更细的发光、描边或动效。

## 面板资源说明

- 战备预览面板保留三组敌人条目槽、标签槽和底部推荐应对槽，敌人头像、敌人名称、数量和推荐文字由工程填充。
- 战备摘要面板保留已选能力列表、流派倾向槽和当前队伍头像槽，固定技能图标、武将头像和文本已移除。
- 通关摘要与失败摘要面板保留浅色纸底、标题槽、行图标槽、左/右文本槽和分隔线，波次、时间、阵容、流派、状态等内容由工程填充。

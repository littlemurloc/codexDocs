# Y3 UI Implementation Guide

本说明用于指导 Y3 首轮原型实装时如何使用 P0 UI 资源。资源以 `assets/ui/processed/p0_components/` 为主，`assets/ui/processed/p0/` 只作为快速占位和视觉参考。

## 目录选择

| 目录 | 何时使用 |
| --- | --- |
| `assets/ui/processed/p0_components/` | 正式拼接控件时使用。优先级最高。 |
| `assets/ui/processed/p0/` | 快速搭布局、对照整体比例、按钮整件占位时使用。 |
| `assets/ui/export/` | 回看原始界面切片，不直接作为正式拼接资源。 |
| `assets/ui/icon/` | 后续放技能、装备、奖励、敌人、武将头像等图标资源。 |

## 总原则

1. 外框底图只负责容器，不写死条目内容。
2. 重复内容用组件循环生成，例如摘要行、敌人条目、能力条目、属性项。
3. 文本、数值、头像、图标、血条比例、能量比例都由工程层动态渲染。
4. 状态优先通过替换底图或叠加状态件实现，例如 normal、selected、disabled、locked、hover。
5. `processed/p0` 中的整块卡牌、面板、单位槽位只用于参考，不作为最终控件拆分标准。

## 拼接层级

推荐从下到上按以下层级拼：

| 层级 | 内容 |
| --- | --- |
| 1 | 背景/外框底图，例如 `*-bg-*`、`*-panel-bg`。 |
| 2 | 固定槽位组件，例如头像槽、图标圈、标题槽、标签槽、分隔线。 |
| 3 | 动态图片，例如武将头像、敌人头像、技能图标、装备图标、奖励图标。 |
| 4 | 动态文本和数值，例如名称、说明、稀有度、波次、属性。 |
| 5 | 状态叠加，例如推荐角标、勾选框、选中描边、悬停描边。 |

## 阵容配置

使用组件：

- `lineup/formation-slot-bg-filled.png`
- `lineup/formation-slot-bg-empty.png`
- `lineup/formation-slot-bg-hover.png`
- `lineup/formation-slot-bg-locked.png`
- `lineup/formation-portrait-slot.png`
- `lineup/formation-name-slot.png`
- `lineup/formation-role-slot-red.png`
- `lineup/formation-stat-slot.png`
- `lineup/formation-empty-emblem.png`
- `lineup/formation-empty-text-slot.png`

动态内容：

- 武将头像、名称、职业/定位、等级、生命、攻击、防御。
- 槽位状态：已上阵、空槽、悬停、锁定。

可直接占位：

- 保存阵容按钮可先用 `assets/ui/processed/p0/lineup/save-lineup-button-normal.png` 等三态资源。

## 战斗 HUD

使用组件：

- `battle/unit-card-bg-active.png`
- `battle/unit-card-bg-selected.png`
- `battle/unit-card-bg-empty.png`
- `battle/unit-card-bg-locked.png`
- `battle/unit-portrait-slot.png`
- `battle/unit-name-slot.png`
- `battle/unit-role-slot.png`
- `battle/unit-hp-bar.png`
- `battle/unit-energy-bar.png`
- `battle/unit-skill-slot.png`
- `battle/unit-equipment-slot.png`
- `battle/unit-empty-emblem.png`

动态内容：

- 单位头像、名称、定位标签、血量比例、能量比例、技能图标、装备图标。
- 顶部栏中的波次、时间、倍率、资源等文本。

可直接占位：

- `assets/ui/processed/p0/battle/battle-top-bar.png`
- `assets/ui/processed/p0/battle/battle-bottom-bar.png`

## 战备选择

战备卡使用：

- `battle/prep-card-bg-normal.png`
- `battle/prep-card-bg-selected.png`
- `battle/prep-card-bg-rare.png`
- `battle/prep-card-bg-disabled.png`
- `battle/choice-card-icon-ring-dark.png`
- `battle/choice-card-title-slot.png`
- `battle/choice-card-rarity-slot.png`
- `battle/choice-card-desc-slot.png`
- `battle/choice-card-tag-row-bg.png`
- `battle/choice-card-ribbon-corner.png`

下一波预览使用：

- `battle/prep-preview-panel-bg.png`
- `battle/enemy-portrait-slot.png`
- `battle/enemy-name-slot.png`
- `battle/enemy-count-slot.png`
- `battle/enemy-tag-red.png`
- `battle/response-chip-red.png`
- `battle/response-chip-blue.png`
- `battle/response-chip-green.png`

本局战备摘要使用：

- `battle/prep-summary-panel-bg.png`
- `battle/ability-row-bg.png`
- `battle/ability-icon-slot.png`
- `battle/ability-name-slot.png`
- `battle/section-label-slot.png`
- `battle/team-avatar-slot.png`

动态内容：

- 战备名称、图标、稀有度、说明、适配标签、推荐状态。
- 敌人头像、名称、数量、标签。
- 已选能力列表、流派倾向、当前队伍头像。

可直接占位：

- 战备确认按钮可先用 `assets/ui/processed/p0/battle/prep-confirm-button-normal.png` 等三态资源。

## 通关奖励

奖励卡使用：

- `settlement/reward-card-bg-normal.png`
- `settlement/reward-card-bg-selected.png`
- `settlement/reward-card-bg-disabled.png`
- `settlement/reward-card-icon-ring.png`
- `settlement/reward-card-title-slot.png`
- `settlement/reward-card-type-slot.png`
- `settlement/reward-card-tag-slot.png`
- `settlement/reward-card-desc-slot.png`
- `settlement/reward-card-recommend-ribbon.png`
- `settlement/reward-card-checkmark-box.png`

通关摘要使用：

- `settlement/summary-panel-bg-small.png`
- `settlement/summary-title-slot.png`
- `settlement/summary-row-icon-slot.png`
- `settlement/summary-row-label-slot.png`
- `settlement/summary-row-value-slot.png`
- `settlement/summary-row-separator-small.png`

动态内容：

- 奖励名称、类型、图标、关键词标签、说明、推荐状态、选中状态。
- 通关波次、用时、阵容、流派等摘要数据。

可直接占位：

- 领取奖励按钮可先用 `assets/ui/processed/p0/settlement/confirm-reward-button-normal.png` 等三态资源。

## 失败结算

失败摘要使用：

- `settlement/summary-panel-bg-tall.png`
- `settlement/summary-title-slot.png`
- `settlement/summary-row-icon-slot.png`
- `settlement/summary-row-label-slot.png`
- `settlement/summary-row-value-slot.png`
- `settlement/summary-row-separator-wide.png`

动态内容：

- 失败波次、用时、阵容、状态/失败原因。

可直接占位：

- 再战按钮：`assets/ui/processed/p0/settlement/retry-button-normal.png` 等三态资源。
- 调整阵容按钮：`assets/ui/processed/p0/settlement/adjust-lineup-button-normal.png` 等三态资源。

## 首轮实装顺序建议

1. 先用 `processed/p0` 的整块资源搭出界面位置和大致比例。
2. 再把卡牌、槽位、面板替换为 `p0_components` 组件级拼接。
3. 接入工程动态文本和头像/图标占位。
4. 接入状态切换：选中、禁用、锁定、悬停。
5. 最后对照 `p0-ui-acceptance-checklist.md` 逐项验收。

## 不要做的事

- 不要把摘要面板、战备预览、奖励卡等整块图片直接当最终控件。
- 不要把固定文字烙进图片资源。
- 不要为了某个具体数据生成专用图片，例如固定波次、固定武将名、固定奖励名。
- 不要在首轮原型阶段追求最终透明描边和动效，先保证数据驱动和控件拼接方式正确。

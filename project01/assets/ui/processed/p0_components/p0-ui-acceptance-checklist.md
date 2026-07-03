# P0 UI Resource Acceptance Checklist

本清单用于核对 `assets/ui/processed/p0_components/` 是否足够支撑 Y3 首轮原型界面的正式拼接。`assets/ui/processed/p0/` 保留为整块占位参考，本清单以组件级资源为准。

## 验收结论

| 界面 | 资源状态 | 结论 |
| --- | --- | --- |
| 阵容配置 | 已覆盖槽位底、头像槽、名称槽、职业槽、属性槽、空槽/悬停/锁定状态 | 可进入 Y3 拼接。 |
| 战斗 HUD | 已覆盖单位卡、单位空槽/锁定槽、血条/能量条、技能槽/装备槽、顶部/底部栏占位 | 可进入 Y3 拼接。 |
| 战备选择 | 已覆盖战备卡、左侧下一波预览、右侧本局战备摘要、确认按钮 | 可进入 Y3 拼接。 |
| 通关奖励 | 已覆盖奖励卡、通关摘要面板、领取按钮 | 可进入 Y3 拼接。 |
| 失败结算 | 已覆盖失败摘要面板、再战按钮、调整阵容按钮 | 可进入 Y3 拼接。 |

## 使用规则

| 资源目录 | 用法 |
| --- | --- |
| `assets/ui/processed/p0_components/` | 正式拼控件时优先使用，按外框、槽位、行组件、状态件组合。 |
| `assets/ui/processed/p0/` | 快速布局占位或视觉对照使用，不作为最终拆分标准。 |
| `assets/ui/export/` | 原始参考切片，遇到组件缺失或视觉争议时回看。 |

工程侧应动态提供：文本、数值、头像、图标、当前血量/能量比例、奖励/战备/敌人条目数量。

## 阵容配置

| 控件 | 组件资源 | 状态 |
| --- | --- | --- |
| 已上阵槽位底 | `lineup/formation-slot-bg-filled.png` | 已有 |
| 空槽位底 | `lineup/formation-slot-bg-empty.png` | 已有 |
| 悬停槽位底 | `lineup/formation-slot-bg-hover.png` | 已有 |
| 锁定槽位底 | `lineup/formation-slot-bg-locked.png` | 已有 |
| 武将头像槽 | `lineup/formation-portrait-slot.png` | 已有 |
| 武将名称槽 | `lineup/formation-name-slot.png` | 已有 |
| 职业/定位标签槽 | `lineup/formation-role-slot-red.png` | 已有 |
| 属性项槽 | `lineup/formation-stat-slot.png` | 已有 |
| 空槽徽记 | `lineup/formation-empty-emblem.png` | 已有 |
| 空槽提示槽 | `lineup/formation-empty-text-slot.png` | 已有 |
| 保存阵容按钮 | `processed/p0/lineup/save-lineup-button-normal.png`, `processed/p0/lineup/save-lineup-button-pressed.png`, `processed/p0/lineup/save-lineup-button-disabled.png` | 已有，占位整件可用 |

工程动态内容：

- 出战武将头像、名称、职业/定位文本。
- 等级、生命、攻击、防御等属性文本。
- 槽位状态：空、已占、悬停、锁定。

## 战斗 HUD

| 控件 | 组件资源 | 状态 |
| --- | --- | --- |
| 战斗顶部栏 | `processed/p0/battle/battle-top-bar.png` | 已有，占位整件可用 |
| 战斗底部栏 | `processed/p0/battle/battle-bottom-bar.png` | 已有，占位整件可用 |
| 单位卡底 | `battle/unit-card-bg-active.png` | 已有 |
| 单位卡选中底 | `battle/unit-card-bg-selected.png` | 已有 |
| 单位空槽底 | `battle/unit-card-bg-empty.png` | 已有 |
| 单位锁定槽底 | `battle/unit-card-bg-locked.png` | 已有 |
| 单位头像槽 | `battle/unit-portrait-slot.png` | 已有 |
| 单位名称槽 | `battle/unit-name-slot.png` | 已有 |
| 单位标签槽 | `battle/unit-role-slot.png` | 已有 |
| 生命条 | `battle/unit-hp-bar.png` | 已有 |
| 能量条 | `battle/unit-energy-bar.png` | 已有 |
| 单位卡分隔线 | `battle/unit-card-separator.png` | 已有 |
| 技能槽 | `battle/unit-skill-slot.png` | 已有 |
| 装备槽 | `battle/unit-equipment-slot.png` | 已有 |
| 空槽徽记 | `battle/unit-empty-emblem.png` | 已有 |

工程动态内容：

- 波次、倒计时、资源/倍率等顶部栏文本。
- 单位头像、名称、标签、血量、能量、技能图标、装备图标。
- 单位状态：已上阵、选中、空槽、锁定。

## 战备选择

| 控件 | 组件资源 | 状态 |
| --- | --- | --- |
| 战备卡普通底 | `battle/prep-card-bg-normal.png` | 已有 |
| 战备卡选中底 | `battle/prep-card-bg-selected.png` | 已有 |
| 战备卡稀有底 | `battle/prep-card-bg-rare.png` | 已有 |
| 战备卡不可选底 | `battle/prep-card-bg-disabled.png` | 已有 |
| 战备图标圈 | `battle/choice-card-icon-ring-dark.png` | 已有 |
| 战备标题槽 | `battle/choice-card-title-slot.png` | 已有 |
| 战备稀有度槽 | `battle/choice-card-rarity-slot.png` | 已有 |
| 战备说明槽 | `battle/choice-card-desc-slot.png` | 已有 |
| 战备适配标签行 | `battle/choice-card-tag-row-bg.png` | 已有 |
| 战备卡分隔线 | `battle/choice-card-separator.png` | 已有 |
| 推荐角标 | `battle/choice-card-ribbon-corner.png` | 已有 |
| 下一波预览面板底 | `battle/prep-preview-panel-bg.png` | 已有 |
| 敌人头像槽 | `battle/enemy-portrait-slot.png` | 已有 |
| 敌人名称槽 | `battle/enemy-name-slot.png` | 已有 |
| 敌人数量槽 | `battle/enemy-count-slot.png` | 已有 |
| 敌人标签槽 | `battle/enemy-tag-red.png` | 已有 |
| 推荐应对标签 | `battle/response-chip-red.png`, `battle/response-chip-blue.png`, `battle/response-chip-green.png` | 已有 |
| 本局战备摘要面板底 | `battle/prep-summary-panel-bg.png` | 已有 |
| 已选能力行 | `battle/ability-row-bg.png` | 已有 |
| 已选能力图标槽 | `battle/ability-icon-slot.png` | 已有 |
| 已选能力名称槽 | `battle/ability-name-slot.png` | 已有 |
| 分区标题槽 | `battle/section-label-slot.png` | 已有 |
| 队伍头像槽 | `battle/team-avatar-slot.png` | 已有 |
| 战备确认按钮 | `processed/p0/battle/prep-confirm-button-normal.png`, `processed/p0/battle/prep-confirm-button-pressed.png`, `processed/p0/battle/prep-confirm-button-disabled.png` | 已有，占位整件可用 |

工程动态内容：

- 战备候选数量、名称、稀有度、说明、适配标签、推荐标记。
- 下一波敌人头像、名称、数量、标签。
- 已选战备列表、流派倾向、当前队伍头像。

## 通关奖励

| 控件 | 组件资源 | 状态 |
| --- | --- | --- |
| 奖励卡普通底 | `settlement/reward-card-bg-normal.png` | 已有 |
| 奖励卡选中底 | `settlement/reward-card-bg-selected.png` | 已有 |
| 奖励卡不可选底 | `settlement/reward-card-bg-disabled.png` | 已有 |
| 奖励图标圈 | `settlement/reward-card-icon-ring.png` | 已有 |
| 奖励标题槽 | `settlement/reward-card-title-slot.png` | 已有 |
| 奖励类型槽 | `settlement/reward-card-type-slot.png` | 已有 |
| 奖励标签槽 | `settlement/reward-card-tag-slot.png` | 已有 |
| 奖励说明槽 | `settlement/reward-card-desc-slot.png` | 已有 |
| 奖励卡分隔线 | `settlement/reward-card-separator.png` | 已有 |
| 推荐角标 | `settlement/reward-card-recommend-ribbon.png` | 已有 |
| 勾选框 | `settlement/reward-card-checkmark-box.png` | 已有 |
| 通关摘要外框底 | `settlement/summary-panel-bg-small.png` | 已有 |
| 摘要标题槽 | `settlement/summary-title-slot.png` | 已有 |
| 摘要行图标槽 | `settlement/summary-row-icon-slot.png` | 已有 |
| 摘要行文本槽 | `settlement/summary-row-label-slot.png`, `settlement/summary-row-value-slot.png` | 已有 |
| 摘要分隔线 | `settlement/summary-row-separator-small.png` | 已有 |
| 领取奖励按钮 | `processed/p0/settlement/confirm-reward-button-normal.png`, `processed/p0/settlement/confirm-reward-button-pressed.png`, `processed/p0/settlement/confirm-reward-button-disabled.png` | 已有，占位整件可用 |

工程动态内容：

- 奖励名称、类型、图标、标签、说明、推荐状态、选中状态。
- 通关波次、用时、阵容、流派等摘要内容。

## 失败结算

| 控件 | 组件资源 | 状态 |
| --- | --- | --- |
| 失败摘要外框底 | `settlement/summary-panel-bg-tall.png` | 已有 |
| 摘要标题槽 | `settlement/summary-title-slot.png` | 已有 |
| 摘要行图标槽 | `settlement/summary-row-icon-slot.png` | 已有 |
| 摘要行文本槽 | `settlement/summary-row-label-slot.png`, `settlement/summary-row-value-slot.png` | 已有 |
| 摘要分隔线 | `settlement/summary-row-separator-wide.png` | 已有 |
| 再战按钮 | `processed/p0/settlement/retry-button-normal.png`, `processed/p0/settlement/retry-button-pressed.png`, `processed/p0/settlement/retry-button-disabled.png` | 已有，占位整件可用 |
| 调整阵容按钮 | `processed/p0/settlement/adjust-lineup-button-normal.png`, `processed/p0/settlement/adjust-lineup-button-pressed.png`, `processed/p0/settlement/adjust-lineup-button-disabled.png` | 已有，占位整件可用 |

工程动态内容：

- 失败波次、用时、阵容、状态或失败原因。
- 再战、调整阵容按钮的可点击状态。

## 暂不阻塞项

| 项目 | 原因 |
| --- | --- |
| 最终透明描边高精资源 | 当前组件足够 Y3 原型拼接，正式美术阶段可重导。 |
| 复杂悬停/发光动效 | 首轮原型可用静态状态替代。 |
| 图标全集 | 当前只整理槽位，具体技能/装备/奖励/敌人图标由工程数据或后续美术补齐。 |
| P1/P2 界面资源 | 主流程闭环前暂不阻塞。 |

## 复查通过条件

- 每个主流程界面都有外框底或单控件底图。
- 所有重复条目都能通过组件循环拼接，不再依赖整块固定行数图片。
- 固定文本、数值、头像、图标不写死在组件级资源里。
- 按钮至少具备普通、按下、禁用三态。
- 空槽、选中、锁定等关键状态均有对应资源。

当前结论：P0 UI 资源满足 Y3 首轮原型拼接要求。

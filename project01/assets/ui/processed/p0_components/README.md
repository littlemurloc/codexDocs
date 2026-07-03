# P0 Component-Level UI Resources

本目录保存 P0 UI 的标准组件级拆分资源。它用于替代 `assets/ui/processed/p0/` 中的整块占位面板资源，目标是让 Y3 侧用“外框 + 行组件 + 文本/图标工程层”的方式拼控件。

## 使用边界

- `assets/ui/processed/p0/`：整块工程占位图，适合快速搭界面。
- `assets/ui/processed/p0_components/`：组件级资源，适合正式拼接控件。
- 本目录里的组件尽量不包含固定文字、固定数值、固定头像或固定条目数量。
- 文字、数值、图标、头像建议全部由 Y3 工程层动态渲染。

## Settlement

| 资源 | 用途 | 拼接方式 |
| --- | --- | --- |
| `settlement/summary-panel-bg-small.png` | 通关摘要外框底 | 只做外框和纸底，不包含任何摘要行。 |
| `settlement/summary-panel-bg-tall.png` | 失败摘要外框底 | 只做外框和纸底，不包含任何摘要行。 |
| `settlement/summary-title-slot.png` | 标题底槽 | 可选；标题也可以直接工程文本渲染。 |
| `settlement/summary-row-icon-slot.png` | 行图标底槽 | 每行复用一次，实际图标由工程层放入。 |
| `settlement/summary-row-label-slot.png` | 行左侧文本底槽 | 可选；如果不需要底纹，可只用工程文本。 |
| `settlement/summary-row-value-slot.png` | 行右侧文本底槽 | 可选；如果不需要底纹，可只用工程文本。 |
| `settlement/summary-row-separator-small.png` | 小摘要行分隔线 | 通关摘要面板内复用。 |
| `settlement/summary-row-separator-wide.png` | 宽摘要行分隔线 | 失败摘要面板内复用。 |

建议拼接：

1. 先放 `summary-panel-bg-small.png` 或 `summary-panel-bg-tall.png`。
2. 标题位置放工程文本，必要时垫 `summary-title-slot.png`。
3. 每一行循环放图标、左文本、右文本和分隔线。
4. 行数由工程数据决定，不再烙死在面板图片里。

## Battle

| 资源 | 用途 | 拼接方式 |
| --- | --- | --- |
| `battle/prep-preview-panel-bg.png` | 下一波预览面板外框底 | 只做外框和深色底，不包含敌人条目。 |
| `battle/prep-summary-panel-bg.png` | 本局战备摘要面板外框底 | 只做外框和深色底，不包含技能条目或队伍头像。 |
| `battle/panel-title-slot.png` | 面板标题底槽 | 可选；标题可由工程文本直接渲染。 |
| `battle/panel-separator-wide.png` | 宽分隔线 | 下一波预览面板内使用。 |
| `battle/panel-separator-mid.png` | 中分隔线 | 战备摘要面板内使用。 |
| `battle/enemy-portrait-slot.png` | 敌人头像槽 | 敌人头像由工程层放入。 |
| `battle/enemy-name-slot.png` | 敌人名称底槽 | 敌人名称由工程文本渲染。 |
| `battle/enemy-count-slot.png` | 敌人数量底槽 | 敌人数量由工程文本渲染。 |
| `battle/enemy-tag-red.png` | 敌人标签底槽 | 可用于高护甲、Boss 等标签。 |
| `battle/response-chip-red.png` | 推荐应对标签 | 用于破甲等偏攻击/破防标签。 |
| `battle/response-chip-blue.png` | 推荐应对标签 | 用于突进、控制等偏战术标签。 |
| `battle/response-chip-green.png` | 推荐应对标签 | 用于治疗、续航等偏防守标签。 |
| `battle/ability-row-bg.png` | 已选能力行底 | 每个已选战备能力复用一行。 |
| `battle/ability-icon-slot.png` | 能力图标槽 | 实际技能图标由工程层放入。 |
| `battle/ability-name-slot.png` | 能力名称底槽 | 能力名称由工程文本渲染。 |
| `battle/section-label-slot.png` | 分区标题底槽 | 用于“已选能力”“当前队伍”等小标题。 |
| `battle/team-avatar-slot.png` | 当前队伍头像槽 | 武将头像由工程层放入。 |
| `battle/prep-card-bg-normal.png` | 战备卡普通态外框底 | 只做卡牌底和外框，不包含图标、标题、标签和说明。 |
| `battle/prep-card-bg-selected.png` | 战备卡选中态外框底 | 只做卡牌底、外框和选中描边。 |
| `battle/prep-card-bg-rare.png` | 战备卡稀有态外框底 | 只做稀有配色卡牌底和外框。 |
| `battle/prep-card-bg-disabled.png` | 战备卡不可选外框底 | 只做不可选卡牌底和外框。 |
| `battle/choice-card-icon-ring-dark.png` | 战备/选择卡图标圈 | 实际战备图标由工程层放入。 |
| `battle/choice-card-title-slot.png` | 战备卡标题底槽 | 可选；标题可由工程文本直接渲染。 |
| `battle/choice-card-rarity-slot.png` | 战备卡稀有度底槽 | 可选；稀有度文本由工程层渲染。 |
| `battle/choice-card-desc-slot.png` | 战备卡说明底槽 | 可选；说明文字由工程层渲染。 |
| `battle/choice-card-tag-row-bg.png` | 战备卡适配标签行底 | 标签内容由工程动态拼接。 |
| `battle/choice-card-separator.png` | 战备卡分隔线 | 卡内分区分隔。 |
| `battle/choice-card-ribbon-corner.png` | 战备卡推荐角标底 | 推荐文字由工程层渲染，资源只做色带。 |
| `battle/unit-card-bg-active.png` | 战斗单位卡外框底 | 只做单位卡底和边框，不包含头像、数值、技能槽。 |
| `battle/unit-card-bg-selected.png` | 战斗单位卡选中外框底 | 只做单位卡底、边框和选中描边。 |
| `battle/unit-card-bg-empty.png` | 战斗单位空槽外框底 | 只做空槽卡底和边框。 |
| `battle/unit-card-bg-locked.png` | 战斗单位锁定槽外框底 | 只做锁定卡底和边框。 |
| `battle/unit-portrait-slot.png` | 战斗单位头像槽 | 头像由工程层放入。 |
| `battle/unit-name-slot.png` | 战斗单位名称底槽 | 可选；名称由工程文本渲染。 |
| `battle/unit-role-slot.png` | 战斗单位标签底槽 | 可选；职业/定位由工程文本渲染。 |
| `battle/unit-hp-bar.png` | 战斗单位生命条底 | 数值和当前比例由工程控制。 |
| `battle/unit-energy-bar.png` | 战斗单位能量条底 | 数值和当前比例由工程控制。 |
| `battle/unit-card-separator.png` | 战斗单位卡分隔线 | 卡内技能区上方分隔。 |
| `battle/unit-skill-slot.png` | 战斗单位技能槽 | 技能图标由工程层放入。 |
| `battle/unit-equipment-slot.png` | 战斗单位装备槽 | 装备图标由工程层放入。 |
| `battle/unit-empty-emblem.png` | 战斗单位空槽徽记 | 空槽/锁定槽中部占位标识。 |

建议拼接：

1. 战备预览：`prep-preview-panel-bg` + 标题 + N 个敌人条目组件 + 推荐应对标签。
2. 战备摘要：`prep-summary-panel-bg` + 分区标题 + N 个能力行 + 流派标签 + 队伍头像槽。
3. 战备卡：`prep-card-bg-*` + 图标圈 + 标题/稀有度/说明/标签槽 + 推荐角标。
4. 战斗单位卡：`unit-card-bg-*` + 头像槽 + 名称/标签槽 + 生命/能量条 + 技能/装备槽。
5. 面板和卡牌本体不再承载固定条目数量，条目数量和内容完全由工程数据决定。

## Lineup

| 资源 | 用途 | 拼接方式 |
| --- | --- | --- |
| `lineup/formation-slot-bg-filled.png` | 阵容已上阵槽外框底 | 只做槽位底和边框，不包含武将头像、名称、职业、属性。 |
| `lineup/formation-slot-bg-empty.png` | 阵容空槽外框底 | 只做空槽底和边框。 |
| `lineup/formation-slot-bg-hover.png` | 阵容空槽悬停外框底 | 只做空槽底、边框和悬停描边。 |
| `lineup/formation-slot-bg-locked.png` | 阵容锁定槽外框底 | 只做锁定槽底和边框。 |
| `lineup/formation-portrait-slot.png` | 阵容武将头像槽 | 头像由工程层放入。 |
| `lineup/formation-name-slot.png` | 阵容武将名称底槽 | 可选；名称由工程文本渲染。 |
| `lineup/formation-role-slot-red.png` | 阵容职业/定位标签底槽 | 可用于突击、护盾等定位标签。 |
| `lineup/formation-stat-slot.png` | 阵容属性项底槽 | 生命、攻击、防御等属性由工程文本渲染。 |
| `lineup/formation-empty-emblem.png` | 阵容空槽徽记 | 空槽中部占位标识。 |
| `lineup/formation-empty-text-slot.png` | 阵容空槽提示文本底槽 | 可选；提示文字由工程文本渲染。 |

建议拼接：

1. 已上阵槽：`formation-slot-bg-filled` + 头像槽 + 名称/职业标签 + N 个属性槽。
2. 空槽：`formation-slot-bg-empty` + 空槽徽记 + 提示文本。
3. 悬停/锁定状态只替换外框底或叠加状态描边，不需要重新制作整张槽位图。

## Settlement Cards

| 资源 | 用途 | 拼接方式 |
| --- | --- | --- |
| `settlement/reward-card-bg-normal.png` | 奖励卡普通态外框底 | 只做纸底和外框，不包含图标、标题、标签和说明。 |
| `settlement/reward-card-bg-selected.png` | 奖励卡选中态外框底 | 只做纸底、外框和选中描边。 |
| `settlement/reward-card-bg-disabled.png` | 奖励卡不可选态外框底 | 只做不可选卡牌底和外框。 |
| `settlement/reward-card-icon-ring.png` | 奖励卡图标圈 | 实际奖励图标由工程层放入。 |
| `settlement/reward-card-title-slot.png` | 奖励卡标题底槽 | 可选；标题由工程文本渲染。 |
| `settlement/reward-card-type-slot.png` | 奖励类型标签底槽 | 例如装备、技能强化等类型文本由工程渲染。 |
| `settlement/reward-card-tag-slot.png` | 奖励卡效果标签底槽 | 奖励关键词由工程动态拼接。 |
| `settlement/reward-card-desc-slot.png` | 奖励卡说明底槽 | 说明文字由工程文本渲染。 |
| `settlement/reward-card-separator.png` | 奖励卡分隔线 | 卡内分区分隔。 |
| `settlement/reward-card-recommend-ribbon.png` | 奖励卡推荐角标底 | 推荐文字由工程文本渲染。 |
| `settlement/reward-card-checkmark-box.png` | 奖励卡勾选框 | 选中态右上角勾选标识。 |

建议拼接：

1. 奖励卡：`reward-card-bg-*` + 图标圈 + 标题/类型/标签/说明槽。
2. 选中态额外叠加 `reward-card-checkmark-box`，推荐态叠加 `reward-card-recommend-ribbon`。

## P0 复查结论

| `processed/p0` 资源类型 | 复查处理 |
| --- | --- |
| 按钮、信息条、战斗顶部/底部栏 | 本身就是单控件底图，保留为整件使用。 |
| 战备预览/战备摘要/通关摘要/失败摘要 | 已拆为外框底、行组件、图标槽、文本槽和分隔线。 |
| 战备卡/奖励卡 | 已拆为卡框底、图标圈、标题槽、标签槽、说明槽、角标/勾选组件。 |
| 战斗单位卡 | 已拆为单位卡底、头像槽、名称/标签槽、血条/能量条、技能/装备槽。 |
| 阵容槽位 | 已拆为槽位底、头像槽、名称/职业/属性槽、空槽提示组件。 |

## 预览

- `_contact-sheet-components.png` 用于核对当前组件拆分结果。
- `_contact-sheet-components-extra.png` 用于核对卡牌、单位卡、阵容槽位补拆结果。

# UI Resource Landing Checklist

本清单用于把 `assets/ui/export/` 第一轮切片转成 Y3 落地时可执行的 UI 资源加工队列。当前资源来自完整界面示意图裁切，优先用于控件拼接参考、占位验证和尺寸比例对齐。

## 状态定义

| 状态 | 含义 |
| --- | --- |
| 可占位 | 可直接放入 Y3 做原型占位或布局验证。 |
| 视觉参考 | 只建议作为外观、比例、层级参考，不建议直接作为最终控件。 |
| 需无字版 | 资源内含固定文字或数值，正式控件需去文字，由 Y3 文本层渲染。 |
| 需透明版 | 当前切片带背景或相邻界面内容，正式控件需透明底独立资源。 |
| 需九宫格 | 面板、按钮、长条类资源需要九宫格，避免缩放变形。 |
| 需多状态 | 按钮、卡片、页签、节点需要补普通、选中、悬停、禁用等状态。 |

## 优先级结论

| 优先级 | 范围 | 目标 |
| --- | --- | --- |
| P0 | 战斗 HUD、战备选择、阵容槽位、通用按钮、结算按钮/奖励卡 | 支撑首轮 Y3 原型验收的主流程。 |
| P1 | 武将配置、羁绊、兵书成长节点 | 支撑主要养成和配置界面的可交互原型。 |
| P2 | 主界面地图、大面板背景、完整说明面板 | 作为视觉参考保留，待主流程稳定后再拆正式件。 |

## Common

| 资源 | 尺寸 | 当前用途 | 状态 | 优先级 | 后续处理 |
| --- | --- | --- | --- | --- | --- |
| `common/top-bar-dark.png` | 1672x68 | 深色顶部栏参考 | 视觉参考 / 需无字版 / 需九宫格 | P1 | 拆背景、货币区、标题文本层。 |
| `common/top-bar-light.png` | 1672x74 | 浅色顶部栏参考 | 视觉参考 / 需无字版 / 需九宫格 | P1 | 与深色顶部栏统一九宫格规则。 |
| `common/bottom-info-bar-dark.png` | 1644x80 | 底部信息条参考 | 可占位 / 需无字版 / 需九宫格 | P0 | 保留条底，文本由工程渲染。 |
| `common/button-red-large.png` | 365x86 | 主按钮参考 | 可占位 / 需无字版 / 需九宫格 / 需多状态 | P0 | 制作普通、按下、禁用状态。 |
| `common/button-red-wide.png` | 429x79 | 宽主按钮参考 | 可占位 / 需无字版 / 需九宫格 / 需多状态 | P0 | 与结算确认按钮共用按钮底。 |
| `common/button-gold-wide.png` | 330x72 | 金色确认按钮参考 | 可占位 / 需无字版 / 需九宫格 / 需多状态 | P0 | 与战备确认按钮统一。 |
| `common/button-light-back.png` | 228x74 | 返回按钮参考 | 可占位 / 需无字版 / 需多状态 | P1 | 拆出按钮底和返回图标。 |
| `common/tabs-three-dark-active.png` | 460x50 | 三页签参考 | 视觉参考 / 需无字版 / 需九宫格 / 需多状态 | P1 | 拆单个页签普通/选中状态。 |
| `common/tabs-skill-equipment.png` | 472x51 | 技能/装备页签参考 | 视觉参考 / 需无字版 / 需九宫格 / 需多状态 | P1 | 拆单页签底图。 |

## Battle

| 资源 | 尺寸 | 当前用途 | 状态 | 优先级 | 后续处理 |
| --- | --- | --- | --- | --- | --- |
| `battle/battle-top-bar.png` | 1672x43 | 战斗顶部信息栏 | 可占位 / 需无字版 / 需九宫格 | P0 | 拆时间、波次、资源文本层。 |
| `battle/battle-bottom-status-bar.png` | 1672x75 | 战斗底部状态栏 | 可占位 / 需无字版 / 需九宫格 | P0 | 拆底条和状态图标槽。 |
| `battle/unit-card-active-1.png` | 177x300 | 出战单位竖卡 | 可占位 / 需无字版 / 需透明版 / 需多状态 | P0 | 保留卡底，头像和数值工程挂接。 |
| `battle/unit-card-active-2.png` | 177x300 | 出战单位竖卡变体 | 可占位 / 需无字版 / 需透明版 / 需多状态 | P0 | 与 active-1 统一为同一控件模板。 |
| `battle/unit-card-empty.png` | 176x300 | 空出战槽 | 可占位 / 需透明版 / 需多状态 | P0 | 补可解锁、未解锁状态。 |
| `battle/threat-panel.png` | 199x143 | 威胁提示小面板 | 视觉参考 / 需无字版 / 需九宫格 | P1 | 文本和图标拆层。 |
| `battle/prep-left-preview-panel.png` | 319x497 | 下一波预览面板 | 可占位 / 需无字版 / 需九宫格 | P0 | 敌人图标与文本全部工程化。 |
| `battle/prep-card-normal.png` | 255x500 | 战备卡普通态 | 可占位 / 需无字版 / 需透明版 / 需多状态 | P0 | 正式制作卡框、稀有度条、图标槽。 |
| `battle/prep-card-selected.png` | 263x510 | 战备卡选中态 | 可占位 / 需无字版 / 需透明版 / 需多状态 | P0 | 与普通态保持同模板尺寸。 |
| `battle/prep-card-rare.png` | 254x500 | 战备卡稀有变体 | 可占位 / 需无字版 / 需透明版 / 需多状态 | P0 | 明确稀有度颜色规范。 |
| `battle/prep-right-summary-panel.png` | 324x518 | 本局战备摘要 | 可占位 / 需无字版 / 需九宫格 | P0 | 列表项改为工程动态生成。 |
| `battle/prep-confirm-button.png` | 330x72 | 战备确认按钮 | 可占位 / 需无字版 / 需九宫格 / 需多状态 | P0 | 可与 `common/button-gold-wide.png` 合并。 |

## Lineup

| 资源 | 尺寸 | 当前用途 | 状态 | 优先级 | 后续处理 |
| --- | --- | --- | --- | --- | --- |
| `lineup/role-detail-panel.png` | 372x675 | 左侧武将详情面板 | 视觉参考 / 需无字版 / 需九宫格 | P1 | 拆头像区、属性区、技能区。 |
| `lineup/formation-slot-filled-1.png` | 238x271 | 已上阵槽位 | 可占位 / 需无字版 / 需透明版 / 需多状态 | P0 | 做统一槽位模板，头像独立挂接。 |
| `lineup/formation-slot-filled-2.png` | 238x271 | 已上阵槽位变体 | 可占位 / 需无字版 / 需透明版 / 需多状态 | P0 | 与 filled-1 合并模板。 |
| `lineup/formation-slot-empty-1.png` | 225x269 | 空槽位 | 可占位 / 需透明版 / 需多状态 | P0 | 补锁定、可放入、拖拽悬停态。 |
| `lineup/formation-slot-empty-2.png` | 225x269 | 空槽位变体 | 可占位 / 需透明版 / 需多状态 | P0 | 与 empty-1 合并模板。 |
| `lineup/hero-list-panel.png` | 455x723 | 武将列表面板 | 视觉参考 / 需无字版 / 需九宫格 | P1 | 卡片列表由工程循环生成。 |
| `lineup/bottom-synergy-bar.png` | 860x66 | 底部羁绊摘要 | 可占位 / 需无字版 / 需九宫格 | P1 | 羁绊标签拆成独立小控件。 |
| `lineup/save-lineup-button.png` | 367x70 | 保存阵容按钮 | 可占位 / 需无字版 / 需九宫格 / 需多状态 | P0 | 可复用红色主按钮体系。 |
| `lineup/synergy-list-panel.png` | 450x670 | 羁绊列表面板 | 视觉参考 / 需无字版 / 需九宫格 | P1 | 列表项拆独立资源。 |
| `lineup/synergy-row-active.png` | 420x48 | 羁绊激活行 | 可占位 / 需无字版 / 需九宫格 / 需多状态 | P1 | 补未激活、选中、禁用行。 |
| `lineup/synergy-detail-block.png` | 420x210 | 羁绊详情块 | 视觉参考 / 需无字版 / 需九宫格 | P1 | 文案全部改工程文本。 |
| `lineup/synergy-bottom-tokens.png` | 550x49 | 羁绊标签组 | 视觉参考 / 需透明版 / 需多状态 | P1 | 拆单个标签。 |

## Hero Config

| 资源 | 尺寸 | 当前用途 | 状态 | 优先级 | 后续处理 |
| --- | --- | --- | --- | --- | --- |
| `hero-config/left-hero-grid-panel.png` | 708x751 | 左侧武将选择区 | 视觉参考 / 需无字版 / 需九宫格 | P1 | 列表格子改为独立控件。 |
| `hero-config/hero-tile-selected.png` | 122x130 | 武将头像格选中态 | 可占位 / 需无字版 / 需透明版 / 需多状态 | P1 | 与已有头像素材配合使用。 |
| `hero-config/hero-tile-normal.png` | 103x120 | 武将头像格普通态 | 可占位 / 需无字版 / 需透明版 / 需多状态 | P1 | 补未拥有、可升级提示态。 |
| `hero-config/right-config-panel-skill.png` | 918x760 | 右侧技能配置区 | 视觉参考 / 需无字版 / 需九宫格 | P1 | 拆为摘要、槽位、候选列表、详情面板。 |
| `hero-config/character-summary.png` | 877x168 | 武将摘要区 | 视觉参考 / 需无字版 / 需九宫格 | P1 | 属性文本与头像独立。 |
| `hero-config/skill-slot-card.png` | 205x185 | 技能槽卡 | 可占位 / 需无字版 / 需透明版 / 需多状态 | P1 | 补空槽、已装、选中状态。 |
| `hero-config/skill-candidate-row.png` | 820x120 | 技能候选行 | 可占位 / 需无字版 / 需九宫格 / 需多状态 | P1 | 补普通、选中、不可用状态。 |
| `hero-config/skill-detail-panel.png` | 875x112 | 技能详情面板 | 视觉参考 / 需无字版 / 需九宫格 | P1 | 文本工程渲染。 |
| `hero-config/equipment-slot-card-1.png` | 373x154 | 装备槽卡 | 可占位 / 需无字版 / 需透明版 / 需多状态 | P1 | 与装备图标独立。 |
| `hero-config/equipment-slot-card-2.png` | 373x154 | 装备槽卡变体 | 可占位 / 需无字版 / 需透明版 / 需多状态 | P1 | 与 slot-card-1 合并模板。 |
| `hero-config/equipment-group-panel-1.png` | 273x177 | 装备组面板 | 视觉参考 / 需无字版 / 需九宫格 | P1 | 装备列表项工程生成。 |
| `hero-config/equipment-group-panel-2.png` | 273x177 | 装备组面板变体 | 视觉参考 / 需无字版 / 需九宫格 | P1 | 合并同类面板模板。 |
| `hero-config/equipment-group-panel-3.png` | 273x177 | 装备组面板变体 | 视觉参考 / 需无字版 / 需九宫格 | P1 | 合并同类面板模板。 |
| `hero-config/equipment-detail-panel.png` | 876x96 | 装备详情面板 | 视觉参考 / 需无字版 / 需九宫格 | P1 | 文本工程渲染。 |

## Settlement

| 资源 | 尺寸 | 当前用途 | 状态 | 优先级 | 后续处理 |
| --- | --- | --- | --- | --- | --- |
| `settlement/reward-summary-panel.png` | 255x258 | 通关摘要面板 | 视觉参考 / 需无字版 / 需九宫格 | P0 | 数值与标签工程渲染。 |
| `settlement/reward-card-selected.png` | 330x427 | 奖励卡选中态 | 可占位 / 需无字版 / 需透明版 / 需多状态 | P0 | 与战备卡共享卡牌规范。 |
| `settlement/reward-card-normal-1.png` | 306x424 | 奖励卡普通态 | 可占位 / 需无字版 / 需透明版 / 需多状态 | P0 | 补稀有度和选中边框。 |
| `settlement/reward-card-normal-2.png` | 306x424 | 奖励卡普通态变体 | 可占位 / 需无字版 / 需透明版 / 需多状态 | P0 | 合并奖励卡模板。 |
| `settlement/fixed-reward-panel.png` | 235x225 | 固定奖励面板 | 视觉参考 / 需无字版 / 需九宫格 | P1 | 奖励图标独立。 |
| `settlement/first-clear-unlock-panel.png` | 235x220 | 首通解锁面板 | 视觉参考 / 需无字版 / 需九宫格 | P1 | 解锁物图标独立。 |
| `settlement/confirm-reward-button.png` | 429x79 | 领取奖励按钮 | 可占位 / 需无字版 / 需九宫格 / 需多状态 | P0 | 复用红色宽按钮。 |
| `settlement/record-button.png` | 262x74 | 战报按钮 | 可占位 / 需无字版 / 需九宫格 / 需多状态 | P1 | 补禁用态。 |
| `settlement/failure-summary-panel.png` | 290x393 | 失败摘要面板 | 视觉参考 / 需无字版 / 需九宫格 | P0 | 数值工程渲染。 |
| `settlement/defeat-illustration-panel.png` | 820x436 | 失败插画/战场区 | 视觉参考 | P2 | 后续可替换为独立背景或截图层。 |
| `settlement/failure-gain-panel.png` | 335x205 | 失败获得面板 | 视觉参考 / 需无字版 / 需九宫格 | P1 | 奖励图标独立。 |
| `settlement/failure-suggestion-panel.png` | 335x267 | 失败建议面板 | 视觉参考 / 需无字版 / 需九宫格 | P1 | 文本工程渲染。 |
| `settlement/retry-button.png` | 493x83 | 再战按钮 | 可占位 / 需无字版 / 需九宫格 / 需多状态 | P0 | 复用主按钮体系。 |
| `settlement/adjust-lineup-button.png` | 321x82 | 调整阵容按钮 | 可占位 / 需无字版 / 需九宫格 / 需多状态 | P0 | 复用副按钮体系。 |

## Home

| 资源 | 尺寸 | 当前用途 | 状态 | 优先级 | 后续处理 |
| --- | --- | --- | --- | --- | --- |
| `home/map-background-left.png` | 1242x760 | 地图区域背景 | 可占位 / 视觉参考 | P2 | 后续替换为完整地图底图与节点层。 |
| `home/stage-card-selected.png` | 255x226 | 关卡卡选中态 | 可占位 / 需无字版 / 需透明版 / 需多状态 | P1 | 节点文本、星级、状态分层。 |
| `home/stage-card-normal.png` | 225x206 | 关卡卡普通态 | 可占位 / 需无字版 / 需透明版 / 需多状态 | P1 | 与选中态统一尺寸策略。 |
| `home/stage-card-locked.png` | 225x195 | 关卡卡锁定态 | 可占位 / 需无字版 / 需透明版 / 需多状态 | P1 | 锁图标独立。 |
| `home/stage-card-locked-large.png` | 250x193 | 大锁定关卡卡 | 可占位 / 需无字版 / 需透明版 / 需多状态 | P1 | 判断是否保留大节点规格。 |
| `home/party-summary-panel.png` | 450x317 | 阵容摘要面板 | 视觉参考 / 需无字版 / 需九宫格 | P2 | 与阵容系统控件复用。 |
| `home/stage-info-panel.png` | 407x621 | 关卡详情面板 | 视觉参考 / 需无字版 / 需九宫格 | P2 | 文案、奖励、按钮分层。 |
| `home/bottom-report-bar.png` | 1644x80 | 底部战报条 | 可占位 / 需无字版 / 需九宫格 | P2 | 可复用 common 底条。 |
| `home/nav-buttons-row.png` | 407x76 | 导航按钮组 | 视觉参考 / 需透明版 / 需多状态 | P2 | 拆为单个图标按钮。 |

## Meta

| 资源 | 尺寸 | 当前用途 | 状态 | 优先级 | 后续处理 |
| --- | --- | --- | --- | --- | --- |
| `meta/meta-routes-panel.png` | 1124x712 | 兵书路线总览 | 视觉参考 / 需无字版 | P1 | 路线、节点、卡片拆层。 |
| `meta/route-card-common.png` | 240x160 | 通用路线卡 | 可占位 / 需无字版 / 需透明版 / 需多状态 | P1 | 补选中和禁用状态。 |
| `meta/route-card-prep.png` | 240x160 | 战备路线卡 | 可占位 / 需无字版 / 需透明版 / 需多状态 | P1 | 与路线卡模板统一。 |
| `meta/route-card-reward.png` | 240x160 | 奖励路线卡 | 可占位 / 需无字版 / 需透明版 / 需多状态 | P1 | 与路线卡模板统一。 |
| `meta/route-card-faction.png` | 240x160 | 阵营路线卡 | 可占位 / 需无字版 / 需透明版 / 需多状态 | P1 | 与路线卡模板统一。 |
| `meta/node-selected.png` | 120x130 | 兵书节点选中态 | 可占位 / 需无字版 / 需透明版 / 需多状态 | P1 | 补可升级、已满级、锁定态。 |
| `meta/node-normal.png` | 120x130 | 兵书节点普通态 | 可占位 / 需无字版 / 需透明版 / 需多状态 | P1 | 与选中态统一节点模板。 |
| `meta/node-locked.png` | 120x130 | 兵书节点锁定态 | 可占位 / 需无字版 / 需透明版 / 需多状态 | P1 | 锁图标独立。 |
| `meta/node-detail-panel.png` | 475x704 | 节点详情面板 | 视觉参考 / 需无字版 / 需九宫格 | P1 | 文本、消耗、按钮拆层。 |
| `meta/meta-warning-bar.png` | 641x71 | 提示条 | 可占位 / 需无字版 / 需九宫格 | P1 | 可做通用警告条。 |
| `meta/upgrade-button.png` | 429x69 | 升级按钮 | 可占位 / 需无字版 / 需九宫格 / 需多状态 | P1 | 与主按钮体系统一。 |

## 下一步加工建议

1. 先做 P0 的无字版与九宫格：通用按钮、战备卡、奖励卡、阵容槽位、战斗上下信息栏。
2. 再补 P0 多状态：按钮普通/按下/禁用，卡片普通/选中/不可选，槽位空/已占/锁定。
3. P1 等主流程可跑通后再做：武将配置、羁绊、兵书成长。
4. P2 暂时只保留参考，不投入精切，避免在主流程 UI 还没验证前消耗过多美术加工量。

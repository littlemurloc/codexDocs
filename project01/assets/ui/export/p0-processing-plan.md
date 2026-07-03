# P0 UI Resource Processing Plan

本表用于确认首轮 Y3 原型验收最先需要精加工的 UI 资源。确认后再进入实际图片处理，不在本步骤直接改图。

## 处理目标

P0 资源只服务首轮核心闭环：

1. 阵容配置能摆上阵单位。
2. 战斗界面能展示我方单位、波次信息和状态栏。
3. 战备三选一能完成选择与确认。
4. 结算界面能完成奖励选择、失败重试和调整阵容。

## 输出目录建议

正式加工后的资源建议另存到 `assets/ui/processed/p0/`，不要覆盖 `assets/ui/export/` 第一轮参考切片。

| 目录 | 内容 |
| --- | --- |
| `common/` | 通用按钮、底条、可复用九宫格底图。 |
| `battle/` | 战斗 HUD、单位卡、战备选择卡和战备面板。 |
| `lineup/` | 出战槽位、保存阵容按钮。 |
| `settlement/` | 奖励卡、结算按钮、失败结算关键面板。 |

## P0 合并规则

| 合并组 | 来源资源 | 建议产物 | 说明 |
| --- | --- | --- | --- |
| 红色主按钮 | `common/button-red-large.png`, `common/button-red-wide.png`, `lineup/save-lineup-button.png`, `settlement/confirm-reward-button.png`, `settlement/retry-button.png` | `common/button-primary-red.9.png` + 多状态 | 用同一套九宫格按钮底，尺寸由工程拉伸。 |
| 金色确认按钮 | `common/button-gold-wide.png`, `battle/prep-confirm-button.png` | `common/button-primary-gold.9.png` + 多状态 | 战备确认优先复用。 |
| 阵容/战斗单位卡 | `battle/unit-card-active-1.png`, `battle/unit-card-active-2.png`, `lineup/formation-slot-filled-1.png`, `lineup/formation-slot-filled-2.png` | `unit-slot-filled.png` + 头像/文本工程层 | 战斗竖卡和阵容槽位比例不同，但卡框语言应统一。 |
| 空槽位 | `battle/unit-card-empty.png`, `lineup/formation-slot-empty-1.png`, `lineup/formation-slot-empty-2.png` | `unit-slot-empty.png`, `unit-slot-locked.png` | 补锁定态、可放入态。 |
| 战备/奖励卡 | `battle/prep-card-normal.png`, `battle/prep-card-selected.png`, `battle/prep-card-rare.png`, `settlement/reward-card-normal-1.png`, `settlement/reward-card-normal-2.png`, `settlement/reward-card-selected.png` | `choice-card-normal.png`, `choice-card-selected.png`, `choice-card-rare.png` | 战备卡和奖励卡可共用卡框规范，内容区由工程填充。 |
| 底部信息条 | `common/bottom-info-bar-dark.png`, `battle/battle-bottom-status-bar.png` | `common/info-bar-dark.9.png` | 文本和图标槽工程化。 |

## P0 待加工清单

| 模块 | 资源 | 当前尺寸 | 加工类型 | 建议输出 | 验收标准 |
| --- | --- | --- | --- | --- | --- |
| common | `common/button-red-large.png` | 365x86 | 无字版 / 九宫格 / 多状态 | `common/button-primary-red-normal.9.png` | 无固定文字，可承载不同按钮文案。 |
| common | `common/button-red-wide.png` | 429x79 | 无字版 / 九宫格 / 多状态 | `common/button-primary-red-wide-normal.9.png` | 与主红按钮共用边框风格。 |
| common | `common/button-gold-wide.png` | 330x72 | 无字版 / 九宫格 / 多状态 | `common/button-primary-gold-normal.9.png` | 可作为战备确认按钮底。 |
| common | `common/bottom-info-bar-dark.png` | 1644x80 | 无字版 / 九宫格 | `common/info-bar-dark.9.png` | 可横向缩放，边框不变形。 |
| battle | `battle/battle-top-bar.png` | 1672x43 | 无字版 / 九宫格 | `battle/battle-top-bar.9.png` | 波次、时间、资源数字全部留给工程文本。 |
| battle | `battle/battle-bottom-status-bar.png` | 1672x75 | 无字版 / 九宫格 | `battle/battle-bottom-bar.9.png` | 状态图标槽和文本区可动态填充。 |
| battle | `battle/unit-card-active-1.png` | 177x300 | 无字版 / 透明版 / 多状态 | `battle/unit-card-active.png` | 不含角色名和数值，头像可替换。 |
| battle | `battle/unit-card-empty.png` | 176x300 | 透明版 / 多状态 | `battle/unit-card-empty.png` | 空槽、锁定、可解锁状态清晰。 |
| battle | `battle/prep-left-preview-panel.png` | 319x497 | 无字版 / 九宫格 | `battle/prep-preview-panel.9.png` | 敌人头像、数量、标题可由工程生成。 |
| battle | `battle/prep-card-normal.png` | 255x500 | 无字版 / 透明版 / 多状态 | `battle/prep-card-normal.png` | 卡名、说明、数值、图标全部可替换。 |
| battle | `battle/prep-card-selected.png` | 263x510 | 无字版 / 透明版 / 多状态 | `battle/prep-card-selected.png` | 选中边框明显，卡体尺寸与普通态可对齐。 |
| battle | `battle/prep-card-rare.png` | 254x500 | 无字版 / 透明版 / 多状态 | `battle/prep-card-rare.png` | 稀有度差异主要来自边框/标题条。 |
| battle | `battle/prep-right-summary-panel.png` | 324x518 | 无字版 / 九宫格 | `battle/prep-summary-panel.9.png` | 本局已选战备列表可动态生成。 |
| battle | `battle/prep-confirm-button.png` | 330x72 | 无字版 / 九宫格 / 多状态 | `battle/prep-confirm-button.9.png` | 可直接复用金色确认按钮。 |
| lineup | `lineup/formation-slot-filled-1.png` | 238x271 | 无字版 / 透明版 / 多状态 | `lineup/formation-slot-filled.png` | 武将头像、星级、名称、状态可替换。 |
| lineup | `lineup/formation-slot-empty-1.png` | 225x269 | 透明版 / 多状态 | `lineup/formation-slot-empty.png` | 空槽表达明确，支持拖拽悬停。 |
| lineup | `lineup/save-lineup-button.png` | 367x70 | 无字版 / 九宫格 / 多状态 | `lineup/save-lineup-button.9.png` | 可复用红色主按钮体系。 |
| settlement | `settlement/reward-summary-panel.png` | 255x258 | 无字版 / 九宫格 | `settlement/reward-summary-panel.9.png` | 星级、难度、收益文本动态生成。 |
| settlement | `settlement/reward-card-normal-1.png` | 306x424 | 无字版 / 透明版 / 多状态 | `settlement/reward-card-normal.png` | 与战备卡保持统一卡框语法。 |
| settlement | `settlement/reward-card-selected.png` | 330x427 | 无字版 / 透明版 / 多状态 | `settlement/reward-card-selected.png` | 选中态明确且不依赖固定文字。 |
| settlement | `settlement/confirm-reward-button.png` | 429x79 | 无字版 / 九宫格 / 多状态 | `settlement/confirm-reward-button.9.png` | 复用红色宽按钮体系。 |
| settlement | `settlement/failure-summary-panel.png` | 290x393 | 无字版 / 九宫格 | `settlement/failure-summary-panel.9.png` | 失败数据、存活时间、击败数可动态显示。 |
| settlement | `settlement/retry-button.png` | 493x83 | 无字版 / 九宫格 / 多状态 | `settlement/retry-button.9.png` | 复用主按钮体系，可横向拉伸。 |
| settlement | `settlement/adjust-lineup-button.png` | 321x82 | 无字版 / 九宫格 / 多状态 | `settlement/adjust-lineup-button.9.png` | 可作为副按钮，与主按钮区分明显。 |

## 多状态最低要求

| 控件类型 | 必备状态 | 可后补状态 |
| --- | --- | --- |
| 主按钮 | 普通、按下、禁用 | 悬停、高亮提示 |
| 战备卡/奖励卡 | 普通、选中、不可选 | 稀有、推荐 |
| 单位槽位 | 空、已占、锁定 | 可放入、拖拽悬停 |
| 信息面板 | 普通 | 告警、强调 |

## 暂不处理项

| 资源范围 | 暂缓原因 |
| --- | --- |
| `home/` 全部资源 | 主界面地图对首轮战斗闭环不是阻塞项，先保留参考切片。 |
| `hero-config/` 全部资源 | 武将配置属于 P1，待阵容和战斗主流程控件稳定后再加工。 |
| `lineup/` 羁绊页资源 | 羁绊是重要系统，但不阻塞首轮战斗闭环验收。 |
| `meta/` 全部资源 | 兵书成长属于长期养成界面，先不占用 P0 美术加工量。 |

## 确认点

请重点确认以下 4 点：

1. P0 是否只覆盖阵容、战斗、战备、结算四个主流程。
2. 是否接受将按钮、卡牌、单位槽位做合并复用，减少后续美术和工程负担。
3. 正式加工资源是否另存到 `assets/ui/processed/p0/`，不覆盖参考切片。
4. P1/P2 是否继续暂缓，只保留现有 `assets/ui/export/` 参考资源。

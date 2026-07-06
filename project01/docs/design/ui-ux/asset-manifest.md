# UI 资源清单

本文档用于记录 UI/UX agent 产出的图片、源文件、导出资源和评审状态。主策划默认只读取本清单，不主动打开资源文件。

## 状态定义

- 草图：用于探索方向，未进入评审。
- 待评审：需要项目负责人或主策划确认。
- 已确认：可作为后续界面设计基准。
- 已废弃：保留记录，但不再作为设计依据。

## 资源列表

| 资源路径 | 对应界面 | 状态 | 说明文档 | 用途 | 是否需主策划查看 | 备注 |
| --- | --- | --- | --- | --- | --- | --- |
| `assets/ui/preview/home-map-stage-select-v02.png` | 主界面 / 地图选关入口 | 已确认 | [home-map-stage-select-v02.md](home-map-stage-select-v02.md) | 主界面第二版 UI 概念图，确定现代历史策略 UI、同层级地图选关、关卡信息面板和局外入口规则 | 否 | 作为后续局外界面视觉基准 |
| `assets/ui/preview/lineup-formation-v01.png` | 阵容编成 | 已确认 | [lineup-formation-v01.md](lineup-formation-v01.md) | 局外阵容配置概念图，确定承接主界面调整阵容入口、顶部资源栏一致、2+2 出战槽位和技能装配轻入口 | 否 | 作为后续武将、技能、装备配置界面的衔接基准 |
| `assets/ui/preview/lineup-synergy-v01.png` | 阵容编成 / 羁绊页签 | 已确认 | [lineup-synergy-v01.md](lineup-synergy-v01.md) | 阵容编成同层级羁绊切页，确定全部羁绊列表、阵营与职业分别计算、多羁绊同时生效和选中羁绊详情的展示方式 | 否 | 作为后续羁绊展示和阵容页签结构基准 |
| `assets/ui/preview/hero-config-skill-tab-v01.png` | 武将配置 / 技能页签 | 已确认 | [hero-config-v01.md](hero-config-v01.md) | 整合技能装配和装备配置的武将配置界面，当前图展示技能页签：左侧 24 人头像矩阵，右侧技能/装备页签与技能 4/6 配置内容 | 否 | 作为后续战前武将配置界面视觉基准 |
| `assets/ui/preview/hero-config-equipment-tab-v01.png` | 武将配置 / 装备页签 | 已确认 | [hero-config-v01.md](hero-config-v01.md) | 整合技能装配和装备配置的武将配置界面，当前图展示装备页签：左侧 24 人头像矩阵，右侧技能/装备页签与装备 2/2 配置内容 | 否 | 与技能页签组成同一套武将配置界面基准 |
| `assets/ui/preview/skill-loadout-v04.png` | 技能装配 | 已废弃 | [skill-loadout-v04.md](skill-loadout-v04.md) | 单独技能装配概念图，保留 24 人头像矩阵，右侧改为角色摘要、已携带技能主编辑区、轻量候选技能池和单技能详情 | 否 | 已被武将配置页签方案替代；保留用于追溯减压版技能区来源 |
| `assets/ui/preview/battle-hud-v07.png` | 战斗 HUD | 已确认 | [battle-hud-v07.md](battle-hud-v07.md) | 轻量战斗 HUD 概念图，确定俯视战斗观赏、底部 4 槽竖卡、2 人当前参战和已预留 4 人布局 | 否 | 作为后续局内战斗界面视觉基准 |
| `assets/ui/preview/battle-prep-choice-v04.png` | 波次战备三选一 | 已确认 | [battle-prep-choice-v04.md](battle-prep-choice-v04.md) | 战备暂停界面概念图，确定下一波预览、三选一能力卡和本局战备摘要的结构 | 否 | 作为后续 Roguelike 备战界面视觉基准 |
| `assets/ui/preview/difficulty-clear-reward-v01.png` | 难度通关奖励 3 选 1 | 已确认 | [difficulty-clear-reward-v01.md](difficulty-clear-reward-v01.md) | 难度通关后的奖励选择界面，区分于波次战备，展示通关摘要、3 个奖励候选、固定资源和首通解锁 | 否 | 作为后续通关奖励与结算前流程视觉基准 |
| `assets/ui/preview/challenge-failure-settlement-v03.png` | 挑战失败结算 | 已确认 | [challenge-failure-settlement-v03.md](challenge-failure-settlement-v03.md) | 我方全灭后的失败结算界面，与通关奖励页共享结算框架，中央使用战败静态图，右侧展示少量获得和调整建议 | 否 | 作为失败分支结算视觉基准 |
| `assets/ui/preview/meta-upgrade-v02.png` | 兵书成长 | 已确认 | [meta-upgrade-v02.md](meta-upgrade-v02.md) | 局外兵书弱成长界面，一页展示通用、战备、奖励、阵营四条路线，强调非强前置技能树和弱成长边界 | 否 | 作为局外成长界面视觉基准 |
| `assets/ui/icon/skill-select-v02/` | 技能装配 / 武将头像矩阵 | 草图 | [skill-loadout-v04.md](skill-loadout-v04.md) | 从技能装配中间稿裁切的 24 个武将头像占位素材，含宽裁切与 face-crops 两套 | 否 | 概念素材，不是正式立绘 skill 输出 |
| `assets/ui/processed/p0/` | P0 核心闭环 UI | 已确认 | `assets/ui/export/p0-processing-plan.md` | 首轮 Y3 原型快速占位资源，覆盖阵容、战斗、战备、结算关键整块控件 | 否 | 只作快速布局和整体比例参考，不作为最终组件拆分标准 |
| `assets/ui/processed/p0_components/` | P0 核心闭环 UI | 已确认 | `assets/ui/processed/p0_components/README.md` | 首轮 Y3 原型正式拼接资源，按外框、槽位、行组件、状态件组合控件 | 否 | 阵容、战斗 HUD、战备三选一、通关奖励、失败结算优先使用该目录 |
| `assets/ui/export/basic-ui-kits-sanguo-v01/preview_basic_ui_kits_A-D.png` | 基础 UI 控件探索 | 待评审 | `assets/ui/export/basic-ui-kits-sanguo-v01/manifest.json` | 2026-07-06 基础控件审美方向总览，包含 A/B/C/D 四个概念方向 | 是 | A/C 保留为轻量策略 UI 参考，B 仅作重控件参考，D 暂不作为主方向 |
| `assets/ui/export/basic-ui-kits-sanguo-v01/extracted-controls-v12-imagegen-reference-redraw/` | 基础 UI 控件候选切片 | 待评审 | `assets/ui/export/basic-ui-kits-sanguo-v01/extracted-controls-v12-imagegen-reference-redraw/README.md` | 基于图像生成参考图清稿后的无字透明 PNG 控件候选，含 manifest、透明检查和组合预览 | 是 | 下一步只做审美、透明边缘和九宫格复核；通过前不直接替换 P0 组件 |

## 记录规则

- 资源路径应使用相对路径，例如 `assets/ui/preview/battle-hud-v07.png`。
- 若资源需要主策划评审，将“是否需主策划查看”标记为“是”，并在备注中说明希望评审的问题；未获得审核认可前，不将图片长期保留在 `assets/ui/preview/`。
- 未通过审核的迭代图只作为临时预览，不登记为正式资源；若已经误存，应在最终版确认后清理。
- 已废弃但需要留档的资源必须有明确保留理由；否则默认清理，避免后续误用。
- 同一界面的多个版本建议使用 `v01`、`v02`、`v03` 命名。
- 每张已确认图必须有独立说明文档，否则不能作为后续设计基准引用。
- 基础 UI 控件资源必须先按 [art-asset-generation-workflow.md](art-asset-generation-workflow.md) 完成效果图、清稿和切片阶段判断，再进入正式资源替换。
- 脚本生成物只有在来源图已确认、透明检查通过、manifest 完整且预览图可复核时，才允许从“待评审”改为“已确认”。

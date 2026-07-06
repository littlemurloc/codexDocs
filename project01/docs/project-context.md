# Project Context

本文件是《三国斗阵》的低 token 回溯入口。新对话或新任务开始时，主策划优先读取本文件，再按任务需要读取 `docs/game-design.md` 或具体系统细案。

## 回溯读取顺序

默认顺序：

1. `docs/project-context.md`：读取当前核心结论、边界和低 token 规则。
2. `docs/game-design.md`：需要系统索引或关键决策时读取。
3. 具体系统细案：只读取与当前任务直接相关的文件。
4. `tests/`：只在审核、验收、测试、风险检查任务中读取。

默认不读取：

- `assets/ui/`：UI 图片、源文件、导出资源，除非用户明确要求评审具体资源。UI/UX agent 也默认先读 `asset-manifest.md`，不批量打开资源本体。
- `generate-game-ui-mockups/`：UI 图片生成技能包，除非任务涉及该技能。
- `generate-sanguo-portrait-images/`：三国头像生成技能包，除非任务涉及该技能。
- `tests/`：非审核/验收类任务默认不读。
- `tools/combat-sim/` 与 `tests/combat-sim-validation.md`：普通回溯默认不读、不运行；只有新增或修改英雄技能、装备、关卡波次怪物、战备能力时，才读取规程并跑模拟验证。
- 无关系统细案：例如只讨论关卡时，不默认读取装备、UI、兵书、商业化等全文。

## 项目定位

《三国斗阵》是面向网易 Y3 的单人 PVE 自动推线斗蛐蛐项目。当前项目只做设计案与规划，不由主策划执行工程实装。

当前协作中新增“程序顾问”定位：负责回答 Y3 实现落地咨询、拆解技术工作流、评审实现风险、讨论工具与技能问题；必要时可基于现有设计案制作 Web 版《三国斗阵》参考小项目，但不代替项目负责人执行 Y3 实装。

核心体验：

- 三国幻想题材。
- 单人 PVE 挑战。
- 唯一主路线自动推线。
- 波次后备战抉择，3 选 1 Roguelike 能力成长。
- 每名武将 6 个技能，战前携带 4 个。
- 装备围绕关键词放大角色当前流派。
- 阵营/职业羁绊提供阵容方向。

## 当前关键规则

- 胜负：取消营寨概念，只按队伍全灭判定。敌方全灭则我方胜利，我方全灭则失败。
- 关卡：关卡 N - 难度 1-10 - 敌人波次 N。每个关卡统一 10 个难度。
- 解锁：同关卡难度依次解锁；新关卡难度 1 由上一关指定门槛难度解锁。
- 波次：波次是单个难度里的出怪批次，每个难度的波次数量可自由指定。
- 单局边界：MVP 中一次单局通常对应一次关卡难度挑战。战备能力只在当前挑战内继承，挑战结束后清空。
- 备战：每波结束后暂停，预览下一波敌人，并从 3 个战备能力中选择 1 个。
- 备战权限：波次间默认只允许调整出战顺序；技能装配和装备更换需要特定战备能力或奖励授权。
- 阵型：行军阶段按队伍阵型整体推进，不依赖 Y3 原生阵型接口；高速职业在接敌后通过短突进、换目标和追击体现机动性。
- 商业化：第一版只做单局可携带参战武将数量解锁。默认最多 2 名，付费最多 4 名。

## 内容规模

- 武将：长期目标 24 名完整候选，MVP 优先 16 名。
- 技能：每名武将 6 个技能，战前携带 4 个。
- 装备：MVP 首发 12 件，围绕关键词强化流派。
- 战备能力：首批 30 个。
- 羁绊：4 个阵营羁绊，4 个职业羁绊，采用 2 人/4 人阈值。
- 关卡：首批 4 个关卡，每关 10 个难度。
- 局外兵书：弱幅度成长，不作为硬通关门槛。

## 当前 UI 资源工作状态

- 当前不是进入完整 Y3 工程实装，而是继续 UI 资源整理与首轮 Y3 原型拼接准备。
- `assets/ui/processed/p0/` 是首轮原型快速占位资源，只用于布局比例和整块对照。
- `assets/ui/processed/p0_components/` 是首轮 Y3 原型拼接主资源，阵容、战斗 HUD、战备三选一、通关奖励、失败结算优先使用该目录组件。
- `assets/ui/export/basic-ui-kits-sanguo-v01/` 是 2026-07-06 的基础 UI 控件审美探索；A/C 方向偏轻量策略界面，B 方向可参考战斗、确认、奖励等重控件，D 方向暂不作为主方向。
- `assets/ui/export/basic-ui-kits-sanguo-v01/extracted-controls-v12-imagegen-reference-redraw/` 是基础控件候选切片资源，下一步只做审美、透明边缘和九宫格复核，不直接替换 P0 组件。
- UI 美术资源生产遵守 `docs/design/ui-ux/art-asset-generation-workflow.md`：先效果图确认，再无字清稿，最后工程切片和校验。脚本只用于切片、透明处理、预览、manifest 和验证，不再承担主要美术设计。

## 文档入口

- 总纲与索引：`docs/game-design.md`
- 角色边界：`docs/agents.md`
- 基础规则：`docs/design/general-rules.md`
- 关卡规则：`docs/design/stage-design.md`
- 波次表：`docs/design/stage-wave-table.md`
- 敌人与 Boss：`docs/design/enemy-boss-design.md`
- 武将与技能：`docs/design/hero-skill-design.md`
- 单位数值属性：`docs/design/unit-attribute-design.md`
- 首批基础数值基准：`docs/design/initial-stat-baseline.md`
- 装备：`docs/design/equipment-design.md`
- 战备抉择：`docs/design/battle-prep-choice-design.md`
- 战备能力池：`docs/design/battle-prep-choice-pool.md`
- 奖励：`docs/design/reward-design.md`
- 兵书成长：`docs/design/meta-upgrade-design.md`
- Y3 策划字段：`docs/design/y3-table-field-design.md`
- UI/UX 索引：`docs/design/ui-ux/ui-index.md`
- UI 美术资源流程：`docs/design/ui-ux/art-asset-generation-workflow.md`
- Y3 实装对齐：`docs/y3-implementation-alignment.md`
- Y3 一致性审查：`docs/y3-design-consistency-review.md`
- 战斗模拟验证规程：`tests/combat-sim-validation.md`

## 维护规则

- 本文件只保留当前共识和读取策略，不承载完整细案。
- 当核心规则发生改变时，先更新对应细案，再同步本文件的一句话结论。
- 本文件目标是低 token 回溯，避免扩写成长篇设计文档。
 
## 回溯读取排除规则

- 新对话、项目回溯、资料浏览和全文搜索时，默认跳过 Git 元数据与高噪声目录，包括 `D:\codex` 下任意层级的 `.git/` 目录、当前工作区内任意 `.git/` 目录、缓存目录、临时目录和生成型大体量产物。
- 只有当用户明确要求查看 Git 历史、提交记录、分支、diff、回滚线索或版本追踪时，才读取 `.git` 或运行相关 Git 查询。
- 普通设计讨论、文档索引、项目概览、技能/装备/关卡回溯时，应优先读取 `docs/project-context.md`、`README.md` 和任务直接相关文档，不扫描 `.git`。

## 讨论内容落档规则

- 所有讨论、分析、方案草案和设计建议，默认只在对话中呈现，不直接写入项目文件。
- 需要落档到 `docs/`、`tests/`、`README.md` 或其他项目文件前，必须先把拟写入内容或变更摘要提交给用户审核。
- 只有在用户明确同意落档、保存、写入、更新文档或执行同等含义的指令后，才可以修改项目文件。

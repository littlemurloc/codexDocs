# 三国斗阵 - 设计总纲

本文件只作为项目设计索引和系统大纲，不承载完整细案。新任务优先读取低 token 回溯入口 [project-context.md](project-context.md)，需要系统索引时再读取本文件。具体设计请进入对应系统文档，避免后续回溯时反复加载整份大文档。

## 项目定位

《三国斗阵》是一款面向网易 Y3 制作的单人 PVE 自动战斗斗蛐蛐游戏。玩家在开局确定参战队伍，并为核心角色从 6 个技能中选择 4 个出战技能；战前布局时，玩家把我方队伍摆入左侧 3x3 共 9 个站位格，对抗右侧镜像 3x3 敌方站位。战斗阶段单位按站位行列关系自动选敌、移动和释放技能；玩家也可以在备战阶段关闭部分英雄主动技能的自动释放，让这些技能以 HUD 技能卡牌形式进入手动释放循环。每波战斗结束后进入备战状态，玩家预览下一波敌人，并从 3 个随机战备能力中选择 1 个作为本局持续成长。胜负由队伍全灭判定。

核心体验：

- 阵容构筑：武将阵营、职业、技能装配与出兵顺序。
- 站位布局：上中下 3 路、每路 3 个站位格，站位影响优先选敌和部分英雄被动。
- 战备抉择：波次后预览下一波敌人，从 3 个本局继承能力中选择 1 个。
- 技能构筑：每名角色 6 选 4，并在备战阶段决定主动技能自动释放或进入手动技能卡牌池。
- 装备构筑：装备围绕关键词强化当前流派，而不是只提供泛用属性。
- 关卡挑战：每个关卡统一 10 个难度，每个难度可自由配置波次数量。

## 设计文档索引

| 模块 | 关键词 | 细案文件 |
| --- | --- | --- |
| Project Context | 低 token 回溯入口、当前共识、默认读取策略 | [project-context.md](project-context.md) |
| General Rules | 项目定位、单局循环、3 路 3x3 站位战斗、选敌规则、胜负判定、MVP边界 | [general-rules.md](design/general-rules.md) |
| Stage Design | 关卡1-4、每关10难度、难度解锁、波次定义、敌人类型 | [stage-design.md](design/stage-design.md) |
| Stage Wave Table | 4个关卡、每关10难度、波次数量、波次结构、测试目的 | [stage-wave-table.md](design/stage-wave-table.md) |
| Enemy & Boss Design | 敌人职责、波次压力、精英机制、Boss机制、流派反制 | [enemy-boss-design.md](design/enemy-boss-design.md) |
| Enemy Readability Design | 敌人外观读性、技能前摇、状态提示、Boss阶段表现 | [enemy-readability-design.md](design/enemy-readability-design.md) |
| Hero & Skill Design | 阵营、职业、首批8名武将、6选4技能装配、2人/4人组合 | [hero-skill-design.md](design/hero-skill-design.md) |
| Hero Second Batch | 第二批8名武将、组合补充、阵营职业补位 | [hero-second-batch.md](design/hero-second-batch.md) |
| Hero Third Batch | 第三批8名武将、24人池补位、2人/4人组合扩展 | [hero-third-batch.md](design/hero-third-batch.md) |
| Hero Readability Design | 首批16名武将、职业轮廓、技能前摇、关键词表现、装备联动 | [hero-readability-design.md](design/hero-readability-design.md) |
| Hero Third Readability Design | 第三批8名武将、召唤、突进、切后、减益表现读性 | [hero-third-readability-design.md](design/hero-third-readability-design.md) |
| Unit Attribute Design | 单位数值属性、战斗节奏属性、阵型属性、展示与隐藏规则 | [unit-attribute-design.md](design/unit-attribute-design.md) |
| Initial Stat Baseline | 首批8武将、首批敌人基础数值、模拟验证摘要 | [initial-stat-baseline.md](design/initial-stat-baseline.md) |
| Build Archetypes | 护盾反击、灼烧扩散、流血斩杀、关键词体系 | [build-archetypes.md](design/build-archetypes.md) |
| Equipment Design | 装备原则、MVP首发12件、延后2件、风险控制 | [equipment-design.md](design/equipment-design.md) |
| Equipment Pressure Review | 关卡压力反查、装备覆盖、测试关注、微调建议 | [equipment-pressure-review.md](design/equipment-pressure-review.md) |
| Battle Prep Choice Design | 备战状态、敌人预览、3选1能力、本局继承、能力池维度 | [battle-prep-choice-design.md](design/battle-prep-choice-design.md) |
| Battle Prep Choice Pool | 首批30个战备能力、稀有度、流派覆盖、测试重点 | [battle-prep-choice-pool.md](design/battle-prep-choice-pool.md) |
| Synergy Design | 4个阵营羁绊、4个职业羁绊、2人/4人阈值、风险控制 | [synergy-design.md](design/synergy-design.md) |
| Reward Design | 难度通关奖励、首通解锁、装备/技能奖励、战备重掷、局外资源 | [reward-design.md](design/reward-design.md) |
| Meta Upgrade Design | 兵书节点、资源规则、弱成长上限、2人/4人商业化边界 | [meta-upgrade-design.md](design/meta-upgrade-design.md) |
| Y3 Table Field Design | 策划表字段、跨表引用、落表顺序、测试指标字段 | [y3-table-field-design.md](design/y3-table-field-design.md) |
| Progression & Monetization | 羁绊、局外兵书、商业化、MVP内容量 | [progression-monetization.md](design/progression-monetization.md) |
| UI/UX Index | UI文档入口、界面流程、资源索引、默认不浏览图片资源 | [ui-index.md](design/ui-ux/ui-index.md) |
| Y3 Implementation Alignment | 实装前设计对齐、可落表口径、实装风险、验收标准 | [y3-implementation-alignment.md](y3-implementation-alignment.md) |
| Y3 Design Consistency Review | 实装前一致性审查、已修正口径、后续主策划工作步骤 | [y3-design-consistency-review.md](y3-design-consistency-review.md) |
| Agent Roles | 项目agent角色职责、默认读写范围、越界审批规则 | [agents.md](agents.md) |
| Acceptance Checklist | MVP验收项、规则覆盖、系统完成度 | [acceptance-checklist.md](../tests/acceptance-checklist.md) |
| Design Test Record | 策划验收、封闭测试、数值调优、问题单模板 | [design-test-record-template.md](../tests/design-test-record-template.md) |
| Combat Simulation Validation | 抽象战斗沙盘、触发条件、验证命令、记录规则 | [combat-sim-validation.md](../tests/combat-sim-validation.md) |
| Design Self Review | 当前设计案自检、风险归类、实装验证风险 | [design-self-review.md](../tests/design-self-review.md) |
| Final Design Review | 实装前最终设计自检、系统边界、必测风险 | [final-design-review.md](../tests/final-design-review.md) |

## 当前关键决策

- 题材：三国幻想。
- 模式：单人 PVE，不做首版多人匹配或实时 PVP。
- 战场：上中下 3 路，每方各有 3x3 共 9 个战前站位格。我方在左侧，敌方在右侧镜像摆放。
- 我方站位编号：从左到右、从上到下表示为 `741 / 852 / 963`；敌方按该布局镜像。站位用于战前自由摆放和部分被动触发。
- 选敌：上排优先攻击对方 `147`，中排优先攻击对方 `258`，下排优先攻击对方 `369`；对应格位或对应行无敌方单位时，按次级选敌策略转向其他行。
- 站位被动：部分英雄被动技能受所处格位影响，放入指定格位会触发特定被动效果。
- 主动技能：主动技能默认纯自动释放；备战阶段可关闭已上阵英雄的主动技能自动释放，关闭后这些技能进入 HUD 技能卡牌池由玩家选择释放。
- 技能卡牌池：所有关闭自动释放的可主动释放技能组成卡牌池；当前每轮抽取上限为 4 张，全部使用完后重新抽取。冷却中、系统锁定或死亡英雄所属技能不会被抽取；开启自动释放的英雄技能不进入卡牌池。
- 胜负：取消营寨概念；敌方队伍全灭则我方胜利，我方队伍全灭则失败。
- 关卡：首批 4 个关卡，每个关卡统一 10 个难度。
- 难度解锁：同关卡内按 1 到 10 依次解锁；新关卡难度 1 由上一关指定门槛难度解锁。
- 波次：波次是单个难度内的出怪批次，数量可自由指定。
- 单局边界：MVP 中一次单局通常对应一次关卡难度挑战；战备能力只在当前挑战内继承，挑战结束后清空。
- 武将：已完成 24 名完整武将池候选设计，其中 16 名为 MVP 优先接入候选。
- 技能：每名武将 6 个技能，战前携带 4 个。
- 表现：24 名武将已补充职业轮廓、技能前摇和关键词状态表达。
- 装备：每名核心武将最多 2 件装备；装备强化角色当前战斗风格。
- 战备抉择：每波结束后预览下一波敌人，随机 3 选 1 战备能力；已选能力本局持续继承，首批能力池 30 个。
- 备战权限：波次间默认允许调整站位布局和主动技能自动释放开关；技能装配和装备更换需要特定战备能力或奖励授权。
- 羁绊：MVP 包含 4 个阵营羁绊和 4 个职业羁绊，采用 2 人/4 人阈值。
- 奖励：波次后只给战备抉择，难度通关后展示 3 选 1 奖励并结算局外资源。
- 局外成长：兵书提供低幅稳定性、战备辅助、奖励修正和阵营熟练，不作为通关硬门槛。
- 商业化：第一版只做单局可携带参战武将数量解锁，默认 2 名，付费最多 4 名。
- 战斗模拟：普通设计回溯默认不读取或运行；新增/修改英雄技能、装备、关卡波次怪物或战备能力时，按 [combat-sim-validation.md](../tests/combat-sim-validation.md) 执行抽象战斗验证。

## 下一步设计优先级

1. 先按 [y3-implementation-alignment.md](y3-implementation-alignment.md) 和 [y3-design-consistency-review.md](y3-design-consistency-review.md) 对齐实装口径、风险和验收标准。
2. 进入 Y3 策划落表和原型制作。
3. 首轮原型优先验证 3 路 3x3 站位选敌、站位被动、技能卡牌池、战备 3 选 1、奖励结算和 2 人/4 人差距。

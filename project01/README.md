# 三国斗阵 - 设计案

这是一个面向网易 Y3 游戏引擎制作的单人 PVE 自动推线斗蛐蛐项目设计包。当前内容只覆盖玩法设计、系统规划、版本目标与验收标准，不包含代码、数据表或工程实现方案。

玩法关键词：

- 三国幻想题材。
- 单人 PVE 爬层。
- 唯一主路线自动推线。
- 波次后备战抉择与本局 Roguelike 能力成长。
- 参考《暗黑地牢》的 6 选 4 技能装配。
- 装备围绕关键词放大角色战斗流派。

## 目录

- `docs/game-design.md`: 设计总纲、模块关键词和细案索引。
- `docs/project-context.md`: 低 token 回溯入口、当前共识和默认读取策略。
- `docs/design/general-rules.md`: 基础规则、单局循环、战斗胜负。
- `docs/design/stage-design.md`: 关卡结构、难度解锁、波次定义、敌人类型。
- `docs/design/stage-wave-table.md`: 4 个关卡、每关 10 难度的波次配置骨架。
- `docs/design/enemy-boss-design.md`: 敌人职责、波次压力、精英和 Boss 机制。
- `docs/design/enemy-readability-design.md`: 敌人外观读性、技能前摇、状态提示和 Boss 阶段表现。
- `docs/design/hero-skill-design.md`: 武将、职业、技能装配、首批 8 名武将。
- `docs/design/hero-second-batch.md`: 第二批 8 名武将和组合补充。
- `docs/design/hero-third-batch.md`: 第三批 8 名武将、24 人池补位和组合补充。
- `docs/design/hero-readability-design.md`: 首批 16 名武将的表现读性、技能前摇和关键词状态表达。
- `docs/design/hero-third-readability-design.md`: 第三批 8 名武将的表现读性、技能前摇和召唤/突进规范。
- `docs/design/unit-attribute-design.md`: 单位数值属性、战斗节奏属性、阵型属性和首版暂缓属性。
- `docs/design/initial-stat-baseline.md`: 首批 8 武将与首批敌人的基础数值基准和模拟验证摘要。
- `docs/design/build-archetypes.md`: 核心流派和关键词系统。
- `docs/design/equipment-design.md`: 装备原则、MVP 首发 12 件和延后装备。
- `docs/design/equipment-pressure-review.md`: 关卡压力反查、装备覆盖和微调建议。
- `docs/design/battle-prep-choice-design.md`: 波次后备战状态、下一波敌人预览、3选1战备能力和本局继承成长。
- `docs/design/battle-prep-choice-pool.md`: 首批 30 个战备抉择能力清单。
- `docs/design/synergy-design.md`: 4 个阵营羁绊、4 个职业羁绊、2 人/4 人阈值和风险控制。
- `docs/design/reward-design.md`: 难度通关奖励、首通奖励、装备/技能奖励、战备重掷和局外资源。
- `docs/design/meta-upgrade-design.md`: 兵书局外成长、资源规则、弱成长上限和商业化边界。
- `docs/design/y3-table-field-design.md`: 后续 Y3 策划表字段和落表顺序。
- `docs/design/progression-monetization.md`: 羁绊、局外成长、商业化和 MVP 内容量。
- `docs/design/ui-ux/ui-index.md`: UI/UX 文档入口、资源目录和默认回溯规则。
- `docs/y3-implementation-alignment.md`: Y3 实装前设计对齐清单、可落表口径、实装风险和验收标准。
- `docs/y3-design-consistency-review.md`: Y3 实装前设计一致性审查、已修正口径和后续工作步骤。
- `docs/agents.md`: 项目 agent 角色职责、读写边界和越界审批规则。
- `docs/milestones.md`: 8 周 MVP 里程碑。
- `tests/acceptance-checklist.md`: MVP 验收清单。
- `tests/design-test-record-template.md`: 策划验收、封闭测试和数值调优记录模板。
- `tests/combat-sim-validation.md`: 抽象战斗模拟器的触发条件、验证命令和记录规则。
- `tests/design-self-review.md`: 当前设计案自检验收报告和实装验证风险。
- `tests/final-design-review.md`: 实装前最终设计自检结论、系统边界和必测风险。

## MVP 内容

- 24 名完整武将池候选，其中 16 名为 MVP 优先接入候选。
- 每名武将 6 个技能，战前携带 4 个。
- 24 名武将已按定位、技能池、推荐装配、2 人/4 人组合价值进行设计。
- 24 名武将已补充表现读性、技能前摇和关键词状态表达。
- 每波战斗后进入备战状态，预览下一波敌人，并从 3 个战备能力中选择 1 个。
- 战备能力在当前挑战中持续继承，挑战结束后清空，新局从零开始。
- 首批战备能力池为 30 个，后续根据测试扩展。
- MVP 优先验证护盾反击、灼烧扩散、流血斩杀三条核心流派。
- 关键词驱动的技能、装备、羁绊联动。
- 强化战斗风格的装备体系：MVP 首发 12 件，另有 2 件候选延后观察。
- 阵营与职业羁绊：4 个阵营羁绊、4 个职业羁绊，按 2 人/4 人阈值设计。
- 难度通关奖励：3 选 1 奖励、首通解锁、战备重掷和局外资源产出。
- “关卡 N - 难度 1-10 - 敌人波次 N”的 PVE 挑战结构。
- 首批 4 个关卡：黄巾余烬、汜水先锋、赤壁火势、虎牢压阵。
- 局外兵书成长：12 个首批节点，提供低幅稳定性、战备辅助、奖励修正和阵营熟练。
- 第一版商业化：单局可携带参战武将数量解锁。

## 下一步

1. 先按 `docs/y3-implementation-alignment.md` 和 `docs/y3-design-consistency-review.md` 对齐实装口径、风险和验收标准。
2. 进入 Y3 策划落表和原型制作。
3. 优先验证单线路径战斗、战备 3 选 1、奖励结算和 2 人/4 人差距。
4. 当新增或修改英雄技能、装备、关卡波次怪物、战备能力时，按 `tests/combat-sim-validation.md` 跑抽象战斗验证。
5. 由项目实装阶段自行决定 Y3 工程结构、数据表和代码实现。

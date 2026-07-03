# Final Design Review

本文件记录《三国斗阵》进入 Y3 实装前的最终设计自检。自检范围只覆盖设计文档，不代表数值、UI、战斗手感或工程实现已经通过。

状态说明：本文档为历史终审记录，用于追溯进入 Y3 前的设计闭合判断。当前 Y3 实装对齐、验收用例和后续执行顺序，以 `docs/y3-implementation-alignment.md`、`docs/y3-design-consistency-review.md` 和 `tests/acceptance-checklist.md` 为准。

自检日期：2026-05-18

## 总体结论

当前设计案已经可以进入 Y3 落表和原型制作阶段。

已闭合的核心设计：

- 单人 PVE、唯一主路线、队伍全灭胜负。
- “关卡 N - 难度 1-10 - 波次 N”的关卡结构。
- 每波后备战状态、下一波敌人预览、战备 3 选 1、本局继承。
- 24 名完整武将池候选，每名 6 技能、战前携带 4 技能。
- 24 名武将表现读性、技能前摇和关键词表现规则。
- 12 件 MVP 首发装备和 2 件延后观察装备。
- 8 个羁绊：4 个阵营羁绊、4 个职业羁绊。
- 首批 30 个战备能力。
- 首批 24 个通关奖励条目。
- 首批 12 个兵书局外成长节点。
- 第一版商业化只做单局参战武将数量解锁。

当前不建议继续扩写更多系统。下一步应该进入 Y3 表格拆分、原型战斗、首轮数值验证和 UI 草模。

## 文档索引验收

| 模块 | 文档 | 状态 |
| --- | --- | --- |
| 总纲 | [../docs/game-design.md](../docs/game-design.md) | 通过 |
| 基础规则 | [../docs/design/general-rules.md](../docs/design/general-rules.md) | 通过 |
| 关卡结构 | [../docs/design/stage-design.md](../docs/design/stage-design.md) | 通过 |
| 波次骨架 | [../docs/design/stage-wave-table.md](../docs/design/stage-wave-table.md) | 通过 |
| 敌人与 Boss | [../docs/design/enemy-boss-design.md](../docs/design/enemy-boss-design.md) | 通过 |
| 敌人读性 | [../docs/design/enemy-readability-design.md](../docs/design/enemy-readability-design.md) | 通过 |
| 武将与技能 | [../docs/design/hero-skill-design.md](../docs/design/hero-skill-design.md) | 通过 |
| 第二批武将 | [../docs/design/hero-second-batch.md](../docs/design/hero-second-batch.md) | 通过 |
| 第三批武将 | [../docs/design/hero-third-batch.md](../docs/design/hero-third-batch.md) | 通过 |
| 武将读性 | [../docs/design/hero-readability-design.md](../docs/design/hero-readability-design.md) | 通过 |
| 第三批读性 | [../docs/design/hero-third-readability-design.md](../docs/design/hero-third-readability-design.md) | 通过 |
| 流派 | [../docs/design/build-archetypes.md](../docs/design/build-archetypes.md) | 通过 |
| 装备 | [../docs/design/equipment-design.md](../docs/design/equipment-design.md) | 通过 |
| 装备压力反查 | [../docs/design/equipment-pressure-review.md](../docs/design/equipment-pressure-review.md) | 通过 |
| 战备抉择规则 | [../docs/design/battle-prep-choice-design.md](../docs/design/battle-prep-choice-design.md) | 通过 |
| 战备能力池 | [../docs/design/battle-prep-choice-pool.md](../docs/design/battle-prep-choice-pool.md) | 通过 |
| 羁绊 | [../docs/design/synergy-design.md](../docs/design/synergy-design.md) | 通过 |
| 奖励 | [../docs/design/reward-design.md](../docs/design/reward-design.md) | 通过 |
| 兵书 | [../docs/design/meta-upgrade-design.md](../docs/design/meta-upgrade-design.md) | 通过 |
| 商业化 | [../docs/design/progression-monetization.md](../docs/design/progression-monetization.md) | 通过 |
| 策划表字段 | [../docs/design/y3-table-field-design.md](../docs/design/y3-table-field-design.md) | 通过 |
| 里程碑 | [../docs/milestones.md](../docs/milestones.md) | 通过 |
| 验收清单 | [acceptance-checklist.md](acceptance-checklist.md) | 通过 |
| 测试记录模板 | [design-test-record-template.md](design-test-record-template.md) | 通过 |

## 系统边界验收

| 系统关系 | 结论 | 说明 |
| --- | --- | --- |
| 战备抉择 vs 奖励 | 通过 | 波次后只做战备；难度通关后才给奖励。 |
| 奖励 vs 兵书 | 通过 | 奖励产出局外资源；兵书消耗资源提供弱成长。 |
| 羁绊 vs 技能装配 | 通过 | 羁绊提供队伍方向，不替代 6 选 4。 |
| 装备 vs 技能 | 通过 | 装备放大当前关键词，不独立形成万能强度。 |
| 4 人付费位 vs 战备/奖励 | 通过 | 4 人位不获得专属池或更高稀有度。 |
| 单线路径 vs 突进/切后 | 通过 | 突进和切后只改变短距离表现或目标优先级，不形成分线。 |
| 召唤 vs 同屏上限 | 通过但需实测 | 文档已有召唤数量和表现约束，实际性能需验证。 |
| Boss vs 控制/斩杀 | 通过但需实测 | Boss 不完全免疫流派，但需要防止阶段跳过。 |

## 必测风险

| 优先级 | 风险 | 测试方式 |
| --- | --- | --- |
| P1 | 默认 2 人位是否能完成门槛难度 | 分别测试关卡 1 难度 5、关卡 2 难度 5、关卡 3 难度 7。 |
| P1 | 4 人位是否成为强制通关门票 | 对比 2 人/4 人在同装备、同兵书下的通关率。 |
| P1 | 战备 3 选 1 是否经常出现无效候选 | 记录候选维度、选择率、放弃率和重掷率。 |
| P1 | 单线战斗是否会卡路径或无限索敌 | 用高密度、召唤、切后、Boss 波次专项测试。 |
| P1 | Boss 阶段是否被斩杀或控制异常跳过 | 测试白马镫、断首符、流血斩杀和控制技能。 |
| P2 | 兵书重掷和奖励刷新是否诱导刷池 | 记录备战停留时长和奖励刷新使用率。 |
| P2 | 召唤物是否压垮同屏单位上限 | 测试张角、袁绍、董卓组合。 |
| P2 | 第三批突进/切后读性是否混乱 | 测试马超、甘宁、赵云、张辽混合阵容。 |
| P2 | 高风险装备是否过强 | 优先测试还血护符、风火锦囊、白马镫。 |

## 实装前建议顺序

1. 先落表 `StageConfig`、`DifficultyConfig`、`WaveConfig`，跑通关卡和波次。
2. 接入 8 名最低可测武将、基础技能装配和单线 AI。
3. 接入战备 3 选 1 和下一波预览。
4. 接入 3 条核心流派的装备、羁绊和奖励。
5. 再扩到 16 名 MVP 武将，最后视成本扩到 24 名完整池。
6. 首轮测试只追稳定闭环，不追完整数值平衡。

## 最终结论

设计层面通过。可以进入 Y3 原型阶段。

后续新增内容应以测试结果为依据，不建议在未实装验证前继续扩大武将、装备、战备能力或关卡数量。

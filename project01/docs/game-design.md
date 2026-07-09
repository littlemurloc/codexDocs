# Game Design

《三国斗阵》当前是一款单人 PVE 自动战斗设计案。玩家选择英雄队伍，在 3x3 站位中布阵，战斗中英雄和小兵自动交战；玩家可通过按英雄关闭主动技能自动释放，把关键主动技能转入 HUD 卡牌池进行手动释放。

## 当前核心体验

- 阵容构筑：英雄选择、职业职责、升星解锁、3x3 站位、英雄小队与主动技能自动/手动取舍。
- 战斗核心：3 路 3x3 站位、行优先选敌、队长/小兵目标规则。
- 技能核心：8 英雄各 6 技能，3 主动 + 3 被动，通过升星解锁并自动携带。
- 手动技能：按英雄关闭自动释放后，该英雄所有已解锁主动技能进入公共卡牌池，每轮最多抽 4 张。
- 单局流程：关卡难度挑战、波次战斗、备战、最终奖励、失败结算。

## 当前第一版 8 英雄

- 吕布：压阵无双，威势斩将。
- 张飞：守线嘲讽，守势抗压。
- 吕蒙：侧翼背刺，隐身生存。
- 黄忠：后排蓄势，单点/穿线/斩首。
- 诸葛亮：后排谋略，阵法法术控制。
- 赵云：闪避游龙，突刺救援。
- 刘备：仁德护队，只治疗/护盾队长。
- 夏侯惇：刚烈反击，把承伤转成反斩。

## 当前文档索引

| 模块 | 说明 | 文档 |
| --- | --- | --- |
| 核心规则 | 站位、小队、技能卡牌、波次结算 | [general-rules.md](design/general-rules.md) |
| 英雄技能 | 当前 8 英雄入口 | [hero-skill-design.md](design/hero-skill-design.md) |
| 8 英雄主源 | 已过审技能文本 | [first-batch-8-heroes-latest-skills.md](design/first-batch-8-heroes-latest-skills.md) |
| 技能审查 | 落表注释和规则约束 | [first-batch-8-heroes-skill-implementation-audit.md](design/first-batch-8-heroes-skill-implementation-audit.md) |
| 技能表草案 | 48 技能 Y3 表字段草案 | [first-batch-8-heroes-y3-skill-table-v0.md](design/first-batch-8-heroes-y3-skill-table-v0.md) |
| 表字段 | Y3 落表字段建议 | [y3-table-field-design.md](design/y3-table-field-design.md) |
| UI/UX | UI 文档和资源索引 | [ui-index.md](design/ui-ux/ui-index.md) |
| 验收 | 首轮原型验收 | [acceptance-checklist.md](../tests/acceptance-checklist.md) |

## 当前暂缓

旧版装备、旧版战备 3 选 1、旧版羁绊和旧版 24 人武将池不作为当前系统依据。新版装备、战备和羁绊应等 8 英雄技能定型后重新讨论。

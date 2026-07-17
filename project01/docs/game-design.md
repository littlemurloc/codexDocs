# Game Design

《三国斗阵》当前是一款单人 PVE 自动战斗设计案。玩家选择英雄队伍，在 3x3 站位中布阵，战斗中英雄和小兵自动交战；英雄主动技能稳定自动释放，玩家通过局内军令卡构筑和主动军令参与关键战术时机。

## 当前核心体验

- 阵容构筑：英雄选择、职业职责、升星解锁、3x3 站位与英雄小队。
- 战斗核心：3 路 3x3 站位、行优先选敌、队长/小兵目标规则。
- 技能核心：首批 10 英雄各 6 技能，3 主动 + 3 被动，通过升星解锁并自动携带；已解锁主动技能始终自动释放。
- 玩家参与：备战阶段出现 3 个军令报价，玩家使用本局军资购买军令并可付费刷新。每次备战至多选择 3 张主动军令进入 HUD；普通/精英波有 2 点军令点，Boss 波有 3 点。被动军略在本局剩余波次持续生效，并可通过自动吞噬、自动进阶和 Set 解锁形成高阶组合。
- 单局流程：约 10-12 波、约 15 分钟的关卡挑战，包含波次战斗、备战、最终奖励和失败结算。小兵阵亡跨波次保留损失，只有军略可在备战补员。

## 已确认英雄概览

- 吕布：压阵无双，威势斩将。
- 张飞：守线嘲讽，守势抗压。
- 吕蒙：侧翼背刺，隐身生存。
- 黄忠：后排蓄势，单点/穿线/斩首。
- 诸葛亮：后排谋略，阵法法术控制。
- 赵云：闪避游龙，突刺救援。
- 刘备：仁德护队，只治疗/护盾队长。
- 夏侯惇：刚烈反击，把承伤转成反斩。
- 司马懿：筹谋法术，远程小兵。
- 甘宁：火药突袭，近战小兵。

## 当前文档索引

| 模块 | 说明 | 文档 |
| --- | --- | --- |
| 核心规则 | 站位、小队、自动技能、波次结算 | [general-rules.md](design/general-rules.md) |
| 军令卡系统 | 局内三报价、主动/被动军令、吞噬与 Set 解锁框架 | [tactical-command-card-system-v1.md](design/tactical-command-card-system-v1.md) |
| 军令效果目录 | 首批 9 套 Set、6 张独立军略与逐卡效果 | [tactical-command-card-catalog-v1.md](design/tactical-command-card-catalog-v1.md) |
| 通用军令 V0 | 已体验的固定三卡历史方案 | [tactical-command-v0.md](design/tactical-command-v0.md) |
| 英雄技能 | 当前 10 英雄入口 | [hero-skill-design.md](design/hero-skill-design.md) |
| 10 英雄落表源 | 技能字段、目标与效果载荷 | [first-batch-10-heroes-skill-config-v1.md](design/first-batch-10-heroes-skill-config-v1.md) |
| 表字段 | Y3 落表字段建议 | [y3-table-field-design.md](design/y3-table-field-design.md) |
| UI/UX | UI 文档和资源索引 | [ui-index.md](design/ui-ux/ui-index.md) |
| 验收 | 首轮原型验收 | [acceptance-checklist.md](../tests/acceptance-checklist.md) |

## 当前暂缓

旧版英雄随机技能卡池、固定三张通用军令、旧版独立战备 3 选 1、装备、羁绊和旧版 24 人武将池不作为当前系统依据。备战阶段在 V1.1 中承担军令市场入口；首批卡牌已定，基础军资经济、报价权重与属性公式仍待核算。

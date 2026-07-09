# Project Context

本文档是 project01 的普通回溯入口。后续不同角色 agent 应先读本文件，再按职责读取自己范围内的文档。

## 当前阶段

项目处于“新版第一版 8 英雄技能定型 + Y3 首轮原型准备”阶段，不是完整 Y3 实装阶段。

当前优先事项：

1. 保持 8 英雄技能主源正确。
2. 补齐 Y3 技能落表字段。
3. 验证 3x3 站位、小队规则、自动/手动技能卡牌池。
4. 使用 P0 UI 组件拼接阵容、战斗 HUD、备战、通关奖励和失败结算流程。

## 当前核心玩法口径

- 单人 PVE 自动战斗。
- 我方左侧 3x3 站位：`741 / 852 / 963`。
- 敌方右侧 3x3 站位：`147 / 258 / 369`。
- 前排 = `1/2/3`，中排 = `4/5/6`，后排 = `7/8/9`，侧翼 = `1/4/7` 或 `3/6/9`。
- 每名英雄带小兵队伍，队长等于英雄。
- 玩家队长死亡后小兵溃败，NPC 队长死亡后小兵继续战斗。
- 每名英雄 6 技能，3 主动 + 3 被动，通过升星解锁。
- 英雄进入战斗自动携带所有已解锁技能。
- 自动释放开关按英雄关闭；关闭后该英雄所有已解锁主动技能进入公共技能卡牌池。

## 文档入口

- 核心规则：`docs/design/general-rules.md`
- 英雄技能入口：`docs/design/hero-skill-design.md`
- 8 英雄主源：`docs/design/first-batch-8-heroes-latest-skills.md`
- 技能审查：`docs/design/first-batch-8-heroes-skill-implementation-audit.md`
- 技能落表草案：`docs/design/first-batch-8-heroes-y3-skill-table-v0.md`
- 表字段：`docs/design/y3-table-field-design.md`
- 验收：`tests/acceptance-checklist.md`
- UI 索引：`docs/design/ui-ux/ui-index.md`
- UI 资源 manifest：`docs/design/ui-ux/asset-manifest.md`

## 当前不作为依据的旧系统

- 旧版装备、装备压力反查：历史参考，当前待重做。
- 旧版战备抉择、战备能力池：历史参考，当前待重做。
- 旧版羁绊：历史参考，当前暂不考虑。
- 旧版 24 人英雄池、第二批/第三批、旧读性、旧数值基线：历史参考，不作为当前设计依据。

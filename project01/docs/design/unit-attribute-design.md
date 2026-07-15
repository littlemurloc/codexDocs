# Unit Attribute Design

本文定义当前 MVP 中单位、技能和状态会使用的基础属性口径。旧版装备、战备、羁绊相关属性不作为当前优先项。

当前 P0 技能数值的相对系数、冷却档位和防护档位见 [p0-skill-numeric-baseline-v0.1.md](p0-skill-numeric-baseline-v0.1.md)。

## P0 战斗基础属性

| 属性 | 字段 | 说明 |
| --- | --- | --- |
| 最大生命 | `max_hp` | 治疗、护盾与低生命阈值使用自身最大生命百分比结算。 |
| 攻击 | `attack` | P0 技能伤害统一使用攻击系数；法术 / 物理为伤害标签，不额外要求独立法强属性。 |
| 攻击速度 | `attack_speed` | 普攻频率及攻速增减的基础属性。 |
| 攻击距离 | `attack_range` | 普攻和“当前目标”主动技能的默认距离。 |
| 闪避 | `dodge_pct` | 成功闪避时不受本次伤害，可触发赵云游龙等效果。 |
| 伤害标签 | `damage_tag` | `physical` / `spell` / `true`；P0 暂不拆物理与法术抗性。 |

## 站位属性

| 属性 | 字段 | 说明 |
| --- | --- | --- |
| 战前格位 | `battle_grid_slot` | 我方为 `741 / 852 / 963`，敌方为 `147 / 258 / 369`。 |
| 所在行 | `battle_lane` | top / middle / bottom。 |
| 所在列 | `battle_column` | front / middle / back。 |

## 小队属性

| 属性 | 字段 | 说明 |
| --- | --- | --- |
| 是否队长 | `is_leader` | 英雄或敌方队长。 |
| 所属队长 | `leader_unit_id` | 小兵所属队长。 |
| 小兵数量 | `soldier_count` | 玩家由升星决定，NPC 由配表决定。 |
| 小兵兵种 | `soldier_type` | 当前只确认 melee / ranged。 |
| 队长死亡规则 | `leader_death_rule` | 玩家小兵溃败，NPC 小兵继续战斗。 |

## 技能相关属性

| 属性 | 字段 | 说明 |
| --- | --- | --- |
| 目标单位类型 | `target_unit_type` | leader / soldier / all / self / current_target。 |
| 目标规则 | `target_rule` | 当前目标、生命最低队长、当前一路、当前目标区域等。 |
| 主动释放方式 | `active_cast_mode` | P0 固定为 `auto`；英雄主动技能不进入卡池。 |
| 解锁星级 | `unlock_star_level` | 技能通过几星解锁。 |

## 通用军令相关属性

| 属性 | 字段 | 说明 |
| --- | --- | --- |
| 军令 ID | `tactical_command_id` | 固定三张通用军令卡的配置主键。 |
| 军令目标规则 | `command_target_rule` | 友方队长及其小队、敌方队长或精英及其小队等。 |
| 每波使用上限 | `command_use_limit_per_wave` | 普通/精英波为 1，Boss 波为 2。 |

# Unit Attribute Design

本文定义当前 MVP 中单位、技能和状态会使用的基础属性口径。旧版装备、战备、羁绊相关属性不作为当前优先项。

当前 P0 技能数值的相对系数、冷却档位和防护档位见 [p0-skill-numeric-baseline-v0.1.md](p0-skill-numeric-baseline-v0.1.md)。

## P0 战斗基础属性

| 属性 | 字段 | 说明 |
| --- | --- | --- |
| 最大生命 | `max_hp` | 治疗、护盾与低生命阈值使用自身最大生命百分比结算。 |
| 攻击 | `attack` | P0 技能伤害统一使用攻击系数；法术 / 物理为伤害标签，不额外要求独立法强属性。 |
| 防御 | `defense` | 减伤与无视防御效果使用的基础属性；完整公式与舍入规则待战斗数值核算。 |
| 攻击速度 | `attack_speed` | 普攻频率及攻速增减的基础属性。 |
| 攻击距离 | `attack_range` | 普攻和“当前目标”主动技能的默认距离。 |
| 移动速度 | `move_speed` | 自动移动、追击、后撤与移速增减的基础属性。 |
| 闪避 | `dodge_pct` | 成功闪避时不受本次伤害，可触发赵云游龙等效果。 |
| 暴击 | `crit_pct` | 普攻暴击率；暴击倍率与和其他修正的结算顺序待定。 |
| 伤害标签 | `damage_tag` | `physical` / `spell` / `true`；P0 暂不拆物理与法术抗性。 |

## 军令卡属性扩展边界

军令卡系统 V1 已确认允许被动军略在本局内提供长期属性、经济和成长收益。以下属性是后续卡牌设计可使用的方向，不代表已经确定具体换算或数值。

| 属性层 | 属性 | 建议字段 | 当前状态 |
| --- | --- | --- | --- |
| 二级属性 | 力量、智力、敏捷 | `strength` / `intelligence` / `agility` | 已确认采用；对一级属性的映射待定。 |
| 一级战斗属性 | 攻击、防御、生命、攻速、移速、闪避、暴击等 | 按属性分别配置 | 可作为被动军略收益；完整公式待定。 |
| 局内经济 | 军资及其获取/消费修正 | `run_currency` 等 | 可作为构筑方向；货币规则待定。 |
| 局内成长 | 英雄等级、经验、技能等级 | `hero_level` / `hero_exp` / `skill_level` 等 | 可作为构筑方向；不得绕过升星解锁技能。 |

## 站位属性

| 属性 | 字段 | 说明 |
| --- | --- | --- |
| 战前格位 | `battle_grid_slot` | 我方为 `741 / 852 / 963`，敌方为 `147 / 258 / 369`。 |
| 所在行 | `battle_lane` | top / middle / bottom。 |
| 所在列 | `battle_column` | front / middle / back。 |
| 战前路归属 | `initial_route` | top / middle / bottom。军令选路与跨路效果只读取本字段，不随实时坐标改变。 |

## 小队属性

| 属性 | 字段 | 说明 |
| --- | --- | --- |
| 是否队长 | `is_leader` | 英雄或敌方队长。 |
| 所属队长 | `leader_unit_id` | 小兵所属队长。 |
| 小兵上限 | `soldier_limit` | 玩家由当前升星决定，NPC 由配表决定。 |
| 当前小兵数量 | `current_soldier_count` | 单局运行时数量。小兵阵亡后跨波次保留损失；仅补员效果可增加，且不得超过 `soldier_limit`。 |
| 小兵兵种 | `soldier_type` | 当前只确认 melee / ranged。 |
| 队长死亡规则 | `leader_death_rule` | 玩家小兵溃败，NPC 小兵继续战斗。 |

## 技能相关属性

| 属性 | 字段 | 说明 |
| --- | --- | --- |
| 目标单位类型 | `target_unit_type` | leader / soldier / all / self / current_target。 |
| 目标规则 | `target_rule` | 当前目标、生命最低队长、当前一路、当前目标区域等。 |
| 主动释放方式 | `active_cast_mode` | P0 固定为 `auto`；英雄主动技能不进入卡池。 |
| 解锁星级 | `unlock_star_level` | 技能通过几星解锁。 |

## 军令卡相关属性

| 属性 | 字段 | 说明 |
| --- | --- | --- |
| 军令卡 ID | `command_card_id` | 主动军令或被动军略的配置主键。 |
| 军令卡类型 | `command_card_type` | `active` / `passive`。 |
| Set ID | `command_set_id` | 所属 Set；独立军略为空。 |
| 进阶结果 ID | `fusion_result_id` | 满足组件条件后自动获得的高阶卡或军略。 |
| 解锁 Set | `unlock_set_ids` | 自动结果完成后解锁的二阶 Set 候选。 |
| 报价资格 | `offer_eligibility_rule` | 初始可出现、Set 解锁后可出现等。 |
| 军令目标模式 | `command_target_mode` | 主动军令最多一次手动目标选择；具体目标类型按卡牌定义。 |
| 军令点成本 | `command_point_cost` | 当前第一版主动军令固定为 1。 |
| 每波使用上限 | `uses_per_wave` | 当前第一版主动军令固定为 1。 |
| 预警时间 | `telegraph_seconds` | 军令结算前的目标预警时间。 |
| 军略图鉴状态 | `command_compendium_state` | 被动军略、吞噬后的高阶军略及其查看状态。 |
| Set 完成状态 | `command_set_progress` | 独立记录，不能因被动吞噬而丢失已达成解锁资格。 |
| 主动备战状态 | `prepared_active_command_ids` | 玩家本次备战带入 HUD 的主动军令，最多 3 张。 |
| 本波军令点 | `wave_command_points` | 普通/精英波 2，Boss 波 3，波末清空。 |

# Y3 Table Field Design

本文定义后续在 Y3 中落表时建议使用的策划表字段。当前优先服务新版第一版 8 英雄、3x3 站位、英雄小队、技能升星解锁和技能卡牌池。旧版装备、旧版战备 3 选 1 和旧版羁绊字段不作为当前落表优先级。

当前第一批 8 英雄技能落表草案见 [first-batch-8-heroes-y3-skill-table-v0.md](first-batch-8-heroes-y3-skill-table-v0.md)。

## 表格总览

| 表名 | 用途 | 优先级 |
| --- | --- | --- |
| StageConfig | 关卡主题、解锁关系、展示信息 | 必做 |
| DifficultyConfig | 每关 10 个难度、门槛、奖励组、推荐标签 | 必做 |
| WaveConfig | 单个难度内的敌人波次 | 必做 |
| EnemyGroupConfig | 每波敌方队伍组合 | 必做 |
| EnemyUnitConfig | 敌方队长/小兵基础配置 | 必做 |
| BossConfig | Boss 阶段、技能、弱点窗口 | 必做 |
| HeroConfig | 英雄基础信息、升星、小队和站位 | 必做 |
| HeroSkillConfig | 英雄技能、解锁、目标和卡牌池规则 | 必做 |
| KeywordConfig | 关键词说明和表现 | 必做 |
| EnemyPreviewConfig | 下一波敌人预览信息 | 必做 |
| RewardConfig | 难度通关奖励和局外资源 | 建议 |
| MetaUpgradeConfig | 兵书局外成长 | 建议 |
| MonetizationConfig | 单局参战英雄携带位解锁 | 必做 |
| TestMetricConfig | 测试记录字段 | 建议 |
| EquipmentConfig | 新版装备字段 | 待重做 |
| BattlePrepChoiceConfig | 新版战备字段 | 待重做 |
| SynergyConfig | 新版羁绊字段 | 暂缓 |

## HeroConfig 当前核心字段

| 字段 | 类型建议 | 说明 |
| --- | --- | --- |
| hero_id | string | 英雄 ID。 |
| hero_name | string | 英雄名。 |
| class | string | 猛将、智将、敏将、辅将等。 |
| role_summary | string | 战斗定位。 |
| keyword_tags | string/list | 核心关键词。 |
| star_level | int | 外围英雄升星等级。 |
| unlocked_skill_ids | string/list | 当前升星已解锁技能。 |
| squad_soldier_limit | int | 当前升星可携带小兵数量，上限 8。 |
| soldier_type | string | 当前小兵兵种，MVP 为 melee/ranged。 |
| battle_grid_slot | int/string | 我方战前摆放格位，按 `741 / 852 / 963` 编号。 |
| recommended_grid_slots | string/list | 推荐站位格、行、列或侧翼标签。 |
| active_auto_cast_enabled | bool | 该英雄主动技能是否自动释放。 |

## HeroSkillConfig 当前核心字段

| 字段 | 类型建议 | 说明 |
| --- | --- | --- |
| skill_id | string | 技能 ID。 |
| hero_id | string | 所属英雄。 |
| skill_name | string | 技能名。 |
| skill_type | string | active / passive。 |
| unlock_star_level | int | 该技能通过英雄几星解锁。 |
| target_rule | string | 当前目标、当前一路、目标区域、生命最低队长等。 |
| target_unit_type | string | leader / soldier / all / self / current_target。 |
| cooldown | float | 冷却时间，待补。 |
| cast_range | float | 释放距离，待补。 |
| effect_type | string | 伤害、治疗、护盾、控制、增益、减益等。 |
| effect_value | int/float/string | 主要效果值或描述，待补。 |
| duration | float | 持续时间，待补。 |
| can_enter_card_pool | bool | 已解锁主动技能且所属英雄关闭自动释放后是否可进入卡牌池。 |
| card_lock_rule | string | cooldown / system_lock / hero_dead 等。 |
| position_passive_rule | string | 站位被动触发条件或规则 ID。 |
| ai_priority | string/int | 自动释放优先级。 |
| readability_note | string | 技能表现说明，待补。 |

## MVP 落表顺序

1. StageConfig、DifficultyConfig、WaveConfig。
2. EnemyUnitConfig、EnemyGroupConfig、BossConfig。
3. HeroConfig、HeroSkillConfig、KeywordConfig。
4. EnemyPreviewConfig、RewardConfig、MetaUpgradeConfig。
5. MonetizationConfig、TestMetricConfig。
6. 新版装备、新版战备、新版羁绊等待后续重新设计。

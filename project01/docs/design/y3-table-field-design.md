# Y3 Table Field Design

本文件定义后续在 Y3 中落表时建议使用的策划表字段。它只描述数据结构与字段含义，不包含代码、触发器或工程实现方案。

## 设计原则

- 表格服务调数：字段要让策划能快速调整关卡、波次、技能、装备和奖励。
- 主键稳定：每个表都需要稳定 ID，避免后续改名影响引用。
- 配置可读：名称、描述、标签字段保留给策划和测试人员阅读。
- 数值可拆：基础数值、倍率、奖励、解锁条件尽量拆成独立字段。
- 不过早复杂：MVP 不做过度抽象，先满足 4 关、10 难度、16 武将、12 首发装备。

单位基础属性、战斗节奏属性、阵型属性和首版暂缓属性的统一口径见 [unit-attribute-design.md](unit-attribute-design.md)。首批 8 武将和首批敌人的基础数值基准见 [initial-stat-baseline.md](initial-stat-baseline.md)。本文件中的 HeroConfig、EnemyUnitConfig、HeroSkillConfig、EquipmentConfig 和 KeywordConfig 字段应优先遵守该属性字典。

## 表格总览

| 表名 | 用途 | 优先级 |
| --- | --- | --- |
| StageConfig | 关卡主题、解锁关系、展示信息 | 必做 |
| DifficultyConfig | 每关 10 个难度、门槛、奖励、推荐标签 | 必做 |
| WaveConfig | 单个难度内的出怪波次 | 必做 |
| EnemyGroupConfig | 每波敌人组合 | 必做 |
| EnemyUnitConfig | 敌人单位基础配置 | 必做 |
| BossConfig | Boss 阶段、技能、弱点窗口 | 必做 |
| HeroConfig | 武将基础信息 | 必做 |
| HeroSkillConfig | 武将技能池、自动释放和技能卡牌池规则 | 必做 |
| HeroLoadoutPresetConfig | 推荐技能装配 | 建议 |
| KeywordConfig | 关键词说明和表现 | 必做 |
| EquipmentConfig | 装备基础效果 | 必做 |
| SynergyConfig | 阵营/职业羁绊 | 必做 |
| BattlePrepChoiceConfig | 战备抉择能力池、稀有度、维度、权重 | 必做 |
| EnemyPreviewConfig | 下一波敌人预览信息 | 必做 |
| RewardConfig | 关卡奖励、装备、局外资源 | 建议 |
| MetaUpgradeConfig | 兵书局外成长 | 建议 |
| MonetizationConfig | 单局参战武将携带位解锁 | 必做 |
| TestMetricConfig | 测试记录字段 | 建议 |

## StageConfig

用途：定义关卡本体，不定义具体波次。

| 字段 | 类型建议 | 说明 |
| --- | --- | --- |
| stage_id | string | 稳定关卡 ID，例如 stage_01。 |
| stage_name | string | 关卡名，例如黄巾余烬。 |
| stage_order | int | 关卡顺序。 |
| theme_tag | string | 主题标签，例如新手、破甲、灼烧、终局。 |
| unlock_stage_id | string | 前置关卡 ID，可为空。 |
| unlock_difficulty | int | 前置关卡需通关的难度。 |
| default_unlocked | bool | 是否初始开放。 |
| description | string | 关卡描述。 |
| recommended_build_tags | string/list | 推荐流派标签。 |

首批配置：

- stage_01：黄巾余烬，初始开放。
- stage_02：汜水先锋，关卡 1 难度 5 解锁。
- stage_03：赤壁火势，关卡 2 难度 5 解锁。
- stage_04：虎牢压阵，关卡 3 难度 7 解锁。

## DifficultyConfig

用途：定义每个关卡内固定 10 个难度。

| 字段 | 类型建议 | 说明 |
| --- | --- | --- |
| difficulty_id | string | 稳定难度 ID，例如 stage_01_d05。 |
| stage_id | string | 所属关卡。 |
| difficulty_index | int | 难度编号，1-10。 |
| unlock_previous_difficulty | bool | 是否需要通关同关卡上一难度。 |
| is_stage_unlock_gate | bool | 是否为新关卡解锁门槛。 |
| unlock_target_stage_id | string | 通关后解锁的新关卡，可为空。 |
| wave_count | int | 当前难度波次数量。 |
| rhythm_tag | string | 慢速、标准、密集、压迫、Boss。 |
| test_goal | string | 该难度测试目的。 |
| recommended_build_tags | string/list | 推荐构筑标签。 |
| reward_group_id | string | 奖励组 ID。 |
| enemy_level_multiplier | float | 敌人等级或基础强度倍率。 |
| enemy_hp_multiplier | float | 敌人生命倍率。 |
| enemy_attack_multiplier | float | 敌人攻击倍率。 |
| two_slot_power_hint | int/string | 默认 2 人参战推荐强度提示。 |
| four_slot_power_hint | int/string | 4 人参战推荐强度提示。 |

设计约束：

- 每个关卡都必须有 difficulty_index 1-10。
- 新关卡只解锁难度 1，不自动解锁更高难度。
- wave_count 可以自由指定，不受全局固定波次数限制。

## WaveConfig

用途：定义某难度内每一波。

| 字段 | 类型建议 | 说明 |
| --- | --- | --- |
| wave_id | string | 稳定波次 ID，例如 stage_01_d05_w03。 |
| difficulty_id | string | 所属难度。 |
| wave_index | int | 波次顺序。 |
| enemy_group_id | string | 敌人组合 ID。 |
| spawn_delay | float | 本波开始前延迟。 |
| next_wave_delay | float | 本波后到下一波的间隔。 |
| rhythm_tag | string | 慢速、标准、密集、压迫、Boss。 |
| is_elite_wave | bool | 是否精英波。 |
| is_boss_wave | bool | 是否 Boss 波。 |
| wave_goal | string | 本波测试目的。 |
| max_alive_limit | int | 本波单位存活上限，用于保护同屏单位数量。 |

设计约束：

- 单个难度通关条件是完成该难度所有 WaveConfig。
- Boss 波通常放在最后一波，但表格不强制，方便后续做特殊关卡。
- 同屏单位上限建议按全局 60 控制，单波要留出安全余量。

## EnemyGroupConfig

用途：定义一波中包含哪些敌人。

| 字段 | 类型建议 | 说明 |
| --- | --- | --- |
| enemy_group_id | string | 敌人组 ID。 |
| group_name | string | 敌人组名称。 |
| enemy_01_id | string | 敌人 1 ID。 |
| enemy_01_count | int | 敌人 1 数量。 |
| enemy_01_spawn_pattern | string | 出怪方式，例如同时、分批、间隔。 |
| enemy_02_id | string | 敌人 2 ID。 |
| enemy_02_count | int | 敌人 2 数量。 |
| enemy_02_spawn_pattern | string | 出怪方式。 |
| enemy_03_id | string | 敌人 3 ID，可为空。 |
| enemy_03_count | int | 敌人 3 数量。 |
| enemy_03_spawn_pattern | string | 出怪方式。 |
| group_tags | string/list | 杂兵、远程、破甲、增益、Boss 等标签。 |

MVP 可先支持 3 类敌人槽位。如果后续波次更复杂，再扩展为子表或更多槽位。

## EnemyUnitConfig

用途：定义敌方单位。

| 字段 | 类型建议 | 说明 |
| --- | --- | --- |
| enemy_id | string | 敌人 ID。 |
| enemy_name | string | 敌人名称。 |
| stage_theme | string | 所属主题关卡。 |
| role_tag | string | 杂兵、前排、远程、破甲、控制、增益、精英、Boss。 |
| keyword_tags | string/list | 灼烧、破甲、护盾等关键词。 |
| base_hp | int | 基础生命。 |
| base_attack | int | 基础攻击。 |
| armor | int | 护甲或防御。 |
| attack_range | float | 攻击距离。 |
| move_speed | float | 移动速度。 |
| battle_grid_slot | int/string | 默认敌方格位，1-9；敌方按我方 `741 / 852 / 963` 镜像摆放。 |
| battle_lane | string | 所在路：top、middle、bottom，可由格位推导。 |
| battle_column | string | 所在列：front、middle、back，可由格位推导。 |
| primary_target_slots | string/list | 默认优先攻击的我方格位组。 |
| fallback_target_slots | string/list | 优先组无目标时的次级选敌格位组。 |
| combat_move_speed | float | 接敌后用于短距离调整、追击或突进的战斗移动速度。 |
| attack_interval | float | 攻击间隔。 |
| skill_id_list | string/list | 敌人技能列表。 |
| readability_tag | string | 外观读性标签，对应 enemy-readability-design。 |
| priority_hint | string | 玩家是否应优先处理。 |

## BossConfig

用途：定义 Boss 阶段与机制，不替代 EnemyUnitConfig。

| 字段 | 类型建议 | 说明 |
| --- | --- | --- |
| boss_id | string | Boss ID。 |
| enemy_id | string | 对应敌人单位 ID。 |
| stage_id | string | 所属关卡。 |
| phase_count | int | 阶段数量。 |
| phase_01_hp_threshold | float | 阶段 1 血量区间或进入条件。 |
| phase_01_skill_ids | string/list | 阶段 1 技能。 |
| phase_01_readability | string | 阶段表现说明。 |
| phase_02_hp_threshold | float | 阶段 2 进入条件。 |
| phase_02_skill_ids | string/list | 阶段 2 技能。 |
| phase_02_readability | string | 阶段表现说明。 |
| phase_03_hp_threshold | float | 阶段 3 进入条件。 |
| phase_03_skill_ids | string/list | 阶段 3 技能。 |
| phase_03_readability | string | 阶段表现说明。 |
| weak_window_rule | string | 弱点窗口规则。 |
| anti_skip_rule | string | 防止阶段被跳过的规则说明。 |

## HeroConfig

用途：定义武将基础信息。

| 字段 | 类型建议 | 说明 |
| --- | --- | --- |
| hero_id | string | 武将 ID。 |
| hero_name | string | 武将名。 |
| faction | string | 魏、蜀、吴、群。 |
| class | string | 猛将、智将、敏将、辅将。 |
| role_summary | string | 战斗定位。 |
| selling_point | string | 角色卖点。 |
| keyword_tags | string/list | 核心关键词。 |
| base_hp | int | 基础生命。 |
| base_attack | int | 基础攻击。 |
| base_armor | int | 基础防御。 |
| attack_range | float | 攻击距离。 |
| move_speed | float | 移动速度。 |
| recommended_grid_slots | string/list | 推荐站位格，可填 1-9、上/中/下路或前/中/后列标签。 |
| battle_grid_slot | int/string | 当前战前摆放格位，1-9；我方布局为 `741 / 852 / 963`。 |
| battle_lane | string | 所在路：top、middle、bottom，可由格位推导。 |
| battle_column | string | 所在列：front、middle、back，可由格位推导。 |
| primary_target_slots | string/list | 默认优先攻击的敌方格位组。 |
| fallback_target_slots | string/list | 优先组无目标时的次级选敌格位组。 |
| position_passive_rule_ids | string/list | 站位被动规则 ID，可为空。 |
| combat_move_speed | float | 接敌后用于短距离调整、追击或突进的战斗移动速度。 |
| skill_pool_ids | string/list | 6 个技能 ID。 |
| recommended_equipment_tags | string/list | 适配装备关键词。 |
| two_slot_value | string | 2 人组合价值。 |
| four_slot_value | string | 4 人组合价值。 |

## HeroSkillConfig

用途：定义武将技能池和技能效果。

| 字段 | 类型建议 | 说明 |
| --- | --- | --- |
| skill_id | string | 技能 ID。 |
| hero_id | string | 所属武将。 |
| skill_name | string | 技能名。 |
| keyword_tags | string/list | 技能关键词。 |
| target_rule | string | 目标规则，例如最近、血量最低、后排、范围。 |
| cooldown | float | 冷却时间。 |
| cast_range | float | 释放距离。 |
| effect_type | string | 伤害、治疗、护盾、召唤、控制、增益、减益。 |
| effect_value | int/float | 主要效果值。 |
| duration | float | 持续时间。 |
| max_stack | int | 最大层数，可为空。 |
| is_default_unlocked | bool | 是否默认解锁。 |
| is_active_skill | bool | 是否主动技能。主动技能可自动释放或进入手动技能卡牌池。 |
| default_auto_cast | bool | 默认是否自动释放。玩家可在备战阶段对已上阵英雄调整。 |
| can_enter_card_pool | bool | 关闭自动释放后是否可进入 HUD 技能卡牌池。 |
| card_pool_tags | string/list | 卡牌池分类标签，例如伤害、治疗、控制、爆发。 |
| card_lock_rule | string | 卡牌锁定规则，例如 cooldown、system_lock、hero_dead。 |
| position_passive_rule | string | 站位被动触发条件或规则 ID，可为空。 |
| ai_priority | int | 自动释放优先级。 |
| readability_note | string | 技能前摇或表现说明。 |

设计约束：

- 每名武将必须有 6 个技能。
- 战前最多携带 4 个技能。
- 未携带技能不应在战斗中触发。
- 开启自动释放的技能不进入卡牌池。
- 关闭自动释放的可主动技能进入公共技能卡牌池；当前每轮抽取上限为 4 张。
- 冷却中、系统锁定或死亡英雄所属技能不参与抽取。

## HeroLoadoutPresetConfig

用途：记录推荐装配，便于新手提示、测试和策划验收。

| 字段 | 类型建议 | 说明 |
| --- | --- | --- |
| preset_id | string | 推荐装配 ID。 |
| hero_id | string | 所属武将。 |
| preset_name | string | 装配名称。 |
| skill_01_id | string | 携带技能 1。 |
| skill_02_id | string | 携带技能 2。 |
| skill_03_id | string | 携带技能 3。 |
| skill_04_id | string | 携带技能 4。 |
| build_tags | string/list | 对应流派。 |
| usage_note | string | 使用说明。 |

## KeywordConfig

用途：统一关键词规则、颜色和表现。

| 字段 | 类型建议 | 说明 |
| --- | --- | --- |
| keyword_id | string | 关键词 ID。 |
| keyword_name | string | 关键词名。 |
| category | string | 伤害、控制、防御、资源、召唤等。 |
| effect_summary | string | 规则说明。 |
| stack_rule | string | 叠层规则。 |
| display_color | string | 表现颜色。 |
| icon_note | string | 图标建议。 |
| counterplay_note | string | 反制方式。 |

## EquipmentConfig

用途：定义装备。

| 字段 | 类型建议 | 说明 |
| --- | --- | --- |
| equipment_id | string | 装备 ID。 |
| equipment_name | string | 装备名。 |
| launch_status | string | 首发、延后、废弃。 |
| build_tags | string/list | 护盾反击、灼烧扩散、流血斩杀等。 |
| keyword_tags | string/list | 强化关键词。 |
| suitable_hero_ids | string/list | 适配武将。 |
| core_effect | string | 核心效果描述。 |
| trigger_condition | string | 触发条件。 |
| effect_value | int/float/string | 主要数值或描述。 |
| internal_cooldown | float | 内部冷却，可为空。 |
| risk_note | string | 风险控制。 |
| test_focus | string | 测试关注点。 |

## SynergyConfig

用途：定义阵营和职业羁绊。

| 字段 | 类型建议 | 说明 |
| --- | --- | --- |
| synergy_id | string | 羁绊 ID。 |
| synergy_name | string | 羁绊名。 |
| synergy_type | string | 阵营或职业。 |
| required_tag | string | 魏、蜀、吴、群、猛将等。 |
| threshold_2_effect | string | 2 人阈值效果。 |
| threshold_4_effect | string | 4 人阈值效果。 |
| keyword_tags | string/list | 关联关键词。 |
| supported_hero_ids | string/list | 适配武将 ID。 |
| two_slot_note | string | 默认 2 人位体验说明。 |
| four_slot_note | string | 4 人位扩展体验说明。 |
| prep_choice_interaction_note | string | 与战备抉择的联动说明。 |
| balance_note | string | 风险说明。 |

具体 8 个羁绊见 [synergy-design.md](synergy-design.md)。

## BattlePrepChoiceConfig

用途：定义每波结束后的 3 选 1 战备能力。

| 字段 | 类型建议 | 说明 |
| --- | --- | --- |
| prep_choice_id | string | 战备能力 ID。 |
| prep_choice_name | string | 能力名称。 |
| rarity | string | 普通、稀有、史诗。 |
| dimension_tag | string | 关键词强化、波次针对、开战布置、职业职责、技能联动、装备联动、风险收益、资源修整。 |
| keyword_tags | string/list | 关联关键词，例如灼烧、流血、护盾。 |
| class_tags | string/list | 关联职业，可为空。 |
| trigger_timing | string | 生效时机，例如开战、受击、击杀、Boss弱点窗口。 |
| effect_summary | string | 效果描述。 |
| stack_rule | string | 是否可叠加、可升级或禁止重复。 |
| duration_rule | string | 默认本局持续，可注明只对下一波生效。 |
| risk_cost | string | 风险收益类能力的代价，可为空。 |
| enemy_preview_bias_tags | string/list | 哪类下一波预览会提高出现权重。 |
| build_bias_tags | string/list | 适配流派，例如护盾反击、灼烧扩散、流血斩杀。 |
| weight | int | 随机权重。 |
| max_level | int | 最大等级，可为空。 |
| test_focus | string | 测试关注点。 |

具体能力维度见 [battle-prep-choice-design.md](battle-prep-choice-design.md)，首批 30 个能力见 [battle-prep-choice-pool.md](battle-prep-choice-pool.md)。

## EnemyPreviewConfig

用途：定义备战状态中下一波敌人预览的信息。

| 字段 | 类型建议 | 说明 |
| --- | --- | --- |
| preview_id | string | 预览配置 ID。 |
| wave_id | string | 对应 WaveConfig。 |
| enemy_type_summary | string | 敌人类型摘要。 |
| enemy_count_hint | string | 数量段提示，例如少量、中量、密集。 |
| threat_tags | string/list | 核心威胁标签，例如高护甲、后排火力、灼烧、破甲。 |
| keyword_tags | string/list | 敌方关键词。 |
| rhythm_tag | string | 慢速、标准、密集、压迫、Boss。 |
| recommended_response_tags | string/list | 推荐应对标签，例如范围、单体、续航、控场。 |
| hidden_detail_rule | string | 不展示哪些细节，避免过度剧透。 |

## RewardConfig

用途：定义通关奖励、局外资源或非波次内成长奖励。波次间主要成长由 BattlePrepChoiceConfig 承担。

| 字段 | 类型建议 | 说明 |
| --- | --- | --- |
| reward_group_id | string | 奖励组 ID。 |
| reward_id | string | 奖励条目 ID。 |
| reward_name | string | 奖励名称。 |
| reward_type | string | 装备、技能强化、局外资源、战备重掷次数等。 |
| rarity | string | 普通、稀有、史诗或固定。 |
| reward_weight | int | 权重。 |
| min_difficulty | int | 最低出现难度。 |
| max_difficulty | int | 最高出现难度。 |
| first_clear_only | bool | 是否仅首通出现。 |
| gate_clear_only | bool | 是否仅门槛难度出现。 |
| candidate_rule | string | 是否进入 3 选 1、是否固定结算。 |
| build_tag_bias | string/list | 偏向构筑标签。 |
| unlock_content_id | string | 解锁内容 ID，可为空。 |
| meta_resource_amount | int | 局外资源数量，可为空。 |
| reward_description | string | 展示描述。 |
| risk_note | string | 风险控制说明。 |

具体奖励节奏与首批 24 个奖励见 [reward-design.md](reward-design.md)。

## MetaUpgradeConfig

用途：定义兵书局外成长。

| 字段 | 类型建议 | 说明 |
| --- | --- | --- |
| upgrade_id | string | 兵书升级 ID。 |
| upgrade_name | string | 升级名。 |
| category | string | 初始战备候选质量、战备重掷次数、阵营熟练度、奖励刷新等。 |
| max_level | int | 最大等级。 |
| unlock_condition | string | 解锁条件。 |
| resource_type | string | 消耗资源类型，例如兵书残页、阵营札记、试炼印记。 |
| cost_rule | string | 消耗规则。 |
| effect_per_level | string | 每级效果。 |
| affects_slot_count | bool | 是否受 2 人/4 人参战位影响，MVP 默认 false。 |
| related_faction | string | 关联阵营，可为空。 |
| related_system | string | 关联战备、奖励、通用属性或阵营熟练。 |
| cap_note | string | 上限和风险说明。 |

具体兵书节点见 [meta-upgrade-design.md](meta-upgrade-design.md)。

## MonetizationConfig

用途：定义第一版唯一商业化内容。

| 字段 | 类型建议 | 说明 |
| --- | --- | --- |
| monetization_id | string | 配置 ID。 |
| item_name | string | 商品或解锁项名称。 |
| unlock_type | string | 参战武将携带位。 |
| default_slot_count | int | 默认参战携带位，固定为 2。 |
| paid_extra_slot_count | int | 付费额外携带位，固定为 2。 |
| max_slot_count | int | 最大参战携带位，固定为 4。 |
| excludes | string | 明确不包含武将、技能、装备、关卡通关等。 |
| balance_note | string | 2 人位仍可体验核心玩法。 |

## TestMetricConfig

用途：定义封闭测试需要记录的指标。

| 字段 | 类型建议 | 说明 |
| --- | --- | --- |
| metric_id | string | 指标 ID。 |
| metric_name | string | 指标名。 |
| category | string | 技能、装备、关卡、商业化、局长等。 |
| record_timing | string | 记录时机，例如战斗结束、难度结算、本局结束。 |
| value_type | string | 数字、百分比、文本、枚举。 |
| target_range | string | 目标范围。 |
| warning_rule | string | 异常判断。 |

建议首轮记录：

- 技能携带率。
- 装备选择率。
- 常见 2 人组合。
- 常见 4 人组合。
- 每个难度失败率。
- 平均局长。
- 默认 2 人参战通关率。
- 4 人参战通关率。
- Boss 阶段跳过情况。
- `还血护符` 回复占比。
- `赤焰羽扇` 扩散伤害占比。
- `白马镫` 追加命中贡献。

## 字段命名建议

- ID 使用英文小写加下划线，例如 `stage_01_d05_w03`。
- 展示名称使用中文，例如 `黄巾余烬`。
- 标签字段使用稳定关键词，例如 `burn`、`bleed`、`shield_counter`，也可以在表格中保留中文映射。
- 不把长文本说明塞进 ID。
- 不用名称作为跨表引用，全部用 ID 引用。

## MVP 落表顺序

1. StageConfig、DifficultyConfig、WaveConfig。
2. EnemyUnitConfig、EnemyGroupConfig、BossConfig。
3. HeroConfig、HeroSkillConfig、HeroLoadoutPresetConfig。
4. KeywordConfig、EquipmentConfig、SynergyConfig。
5. BattlePrepChoiceConfig、EnemyPreviewConfig、RewardConfig、MetaUpgradeConfig。
6. MonetizationConfig、TestMetricConfig。

这个顺序能先跑通关卡与战斗压力，再补阵容构筑和长期调优。

# 第一批 8 英雄 Y3 技能落表草案 v0

> 已废弃：本文保留旧字段和历史讨论，包含已取消的英雄随机技能卡池规则，不得作为设计、实现或验收依据。当前请使用 `first-batch-10-heroes-skill-config-v1.md` 与 `tactical-command-card-system-v1.md`。

本文把当前第一批 8 英雄技能整理成接近 `HeroSkillConfig` 的策划表口径。技能玩家文本以 [first-batch-8-heroes-latest-skills.md](first-batch-8-heroes-latest-skills.md) 为主，审查注释见 [first-batch-8-heroes-skill-implementation-audit.md](first-batch-8-heroes-skill-implementation-audit.md)。

## 临时通用规则

- 解锁星级暂按阶段顺序：1 星主动、2 星被动、3 星主动、4 星被动、5 星主动、6 星被动。
- 主动技能默认自动释放，且在该英雄关闭自动释放后进入公共 HUD 技能卡牌池。
- 被动技能不进入卡牌池。
- `target_unit_type = leader` 表示只筛选队长/英雄，不选小兵。
- `target_unit_type = soldier` 表示只影响小兵。
- `target_unit_type = all` 表示队长和小兵都可能受影响。
- `current_lane` 对应敌方上路 `147`、中路 `258`、下路 `369`。
- `current_target_area` 首轮暂指当前目标所在格及其小范围单位。

## 技能表

| hero | skill_id | 技能 | 类型 | 解锁 | target_unit_type | target_rule | can_enter_card_pool | position_rule | ai_priority | 手动价值 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 黄忠 | huangzhong_dingjun_jian | 定军箭 | active | 1 | current_target | current_target_consume_charge_1 | true | - | medium | medium |
| 黄忠 | huangzhong_laogong_wenshou | 老弓稳手 | passive | 2 | self | back_row_charge_loop | false | back_row_789 | - | none |
| 黄忠 | huangzhong_chuanyun_guanzhen | 穿云贯阵 | active | 3 | all | current_lane_path_prefer_leader | true | - | high_when_lane_cluster | high |
| 黄忠 | huangzhong_shouwei_shengong | 守位神弓 | passive | 4 | self | back_row_ranged_reduce_charge_keep | false | back_row_789 | - | none |
| 黄忠 | huangzhong_baibu_chuanyang | 百步穿杨 | active | 5 | leader | lowest_hp_enemy_leader_or_elite | true | - | high_when_charge_or_casting | high |
| 黄忠 | huangzhong_jianzhen_laojiang | 箭阵老将 | passive | 6 | soldier | own_ranged_soldiers | false | - | - | none |
| 刘备 | liubei_rende_yuanhu | 仁德援护 | active | 1 | leader | lowest_hp_ally_leader_heal | true | - | high_when_ally_low | high |
| 刘备 | liubei_kuanren | 宽仁 | passive | 2 | leader | ally_leader_below_40_gain_rende | false | back_row_789 | - | none |
| 刘备 | liubei_tongxin_huwei | 同心护卫 | active | 3 | leader | lowest_hp_ally_leader_shield | true | - | high_when_ally_low | high |
| 刘备 | liubei_renwang_guixin | 仁望归心 | passive | 4 | leader | after_active_lowest_ally_regen | false | - | - | none |
| 刘备 | liubei_taoyuan_zhenjun | 桃园振军 | active | 5 | leader | all_ally_leaders_heal_cleanse | true | - | high_when_multi_ally_low | high |
| 刘备 | liubei_hanshi_yuze | 汉室余泽 | passive | 6 | leader | ally_leader_below_30_shield | false | - | - | none |
| 吕蒙 | lvmeng_baiyi_qianxi | 白衣潜袭 | active | 1 | current_target | current_target_stealth_backstab_check | true | - | medium | high |
| 吕蒙 | lvmeng_ceyi_bufa | 侧翼步法 | passive | 2 | self | flank_attack_speed_backstab_bonus | false | flank_147_or_369 | - | none |
| 吕蒙 | lvmeng_shuangdao_duanying | 双刀断影 | active | 3 | current_target | two_hits_each_backstab_check | true | - | medium | medium |
| 吕蒙 | lvmeng_cangfeng | 藏锋 | passive | 4 | self | stealth_ranged_reduce_flank_extend | false | flank_147_or_369 | - | none |
| 吕蒙 | lvmeng_baiyi_dujiang | 白衣渡江 | active | 5 | leader | lowest_hp_enemy_leader_or_elite_stealth | true | - | high_when_low_hp_leader | high |
| 吕蒙 | lvmeng_shibie_sanri | 士别三日 | passive | 6 | self | after_stealth_damage_reduce | false | - | - | none |
| 赵云 | zhaoyun_longdan_tu | 龙胆突 | active | 1 | current_target | current_target_consume_youlong_1 | true | - | medium | medium |
| 赵云 | zhaoyun_youlong_shenfa | 游龙身法 | passive | 2 | self | dodge_plus_15_gain_youlong | false | - | - | none |
| 赵云 | zhaoyun_qijin_qichu | 七进七出 | active | 3 | all | current_target_area_max_3 | true | - | high_when_youlong_2 | high |
| 赵云 | zhaoyun_baima_qingqi | 白马轻骑 | passive | 4 | self | flank_dodge_8_attack_speed_12 | false | flank_147_or_369 | - | none |
| 赵云 | zhaoyun_changban_huiqiang | 长坂回枪 | active | 5 | leader | lowest_hp_ally_leader_target | true | - | high_when_ally_low | high |
| 赵云 | zhaoyun_yishen_shidan | 一身是胆 | passive | 6 | self | after_consume_youlong_and_full_youlong | false | - | - | none |
| 张飞 | zhangfei_dangyang_nuhou | 当阳怒吼 | active | 1 | current_target | current_target_taunt | true | - | high_when_leader | high |
| 张飞 | zhangfei_shoumen_mengjiang | 守门猛将 | passive | 2 | self | front_row_guard_stack | false | front_row_123 | - | none |
| 张飞 | zhangfei_shemao_henglan | 蛇矛横拦 | active | 3 | all | current_lane_front_max_3_consume_guard_1 | true | - | medium | medium |
| 张飞 | zhangfei_qiangdun_chengqiang | 枪盾成墙 | passive | 4 | soldier | own_soldiers_melee_reduce | false | - | - | none |
| 张飞 | zhangfei_juqiao_sishou | 据桥死守 | active | 5 | current_target | self_shield_taunt_consume_all_guard | true | - | high_when_pressure | high |
| 张飞 | zhangfei_wanfu_mokai | 万夫莫开 | passive | 6 | self | low_hp_gain_3_guard | false | - | - | none |
| 夏侯惇 | xiahoudun_dumu_yingji | 独目迎击 | active | 1 | current_target | current_target_self_shield | true | - | medium | medium |
| 夏侯惇 | xiahoudun_ganglie | 刚烈 | passive | 2 | self_area | melee_hit_stack_counter | false | - | - | none |
| 夏侯惇 | xiahoudun_bashi_nuzhan | 拔矢怒斩 | active | 3 | current_target | gain_2_ganglie_current_target | true | - | medium | medium |
| 夏侯惇 | xiahoudun_dumu_butui | 独目不退 | passive | 4 | self | front_row_knockback_reduce_ganglie_reduce | false | front_row_123 | - | none |
| 夏侯惇 | xiahoudun_liezhen_fanpu | 裂阵反扑 | active | 5 | all | current_lane_front_max_3_consume_all_ganglie | true | - | medium | medium |
| 夏侯惇 | xiahoudun_yishang_huanshi | 以伤换势 | passive | 6 | self | after_counter_next_active_damage | false | - | - | none |
| 吕布 | lvbu_fangtian_yazhen | 方天压阵 | active | 1 | all | current_lane_front_max_3 | true | - | medium | medium |
| 吕布 | lvbu_jixia_wutui | 戟下无退 | passive | 2 | self | front_row_reduce_leader_damage | false | front_row_123 | - | none |
| 吕布 | lvbu_zhenqian_jiaozhan | 阵前叫战 | active | 3 | current_target | prefer_leader_or_elite_taunt_reduce_attack | true | - | high_when_leader | high |
| 吕布 | lvbu_renzhong_lvbu | 人中吕布 | passive | 4 | self | gain_weishi_on_leader_elite_kill | false | - | - | none |
| 吕布 | lvbu_yuanmen_zhanjiang | 辕门斩将 | active | 5 | leader | lowest_hp_enemy_leader_or_elite_consume_weishi | true | - | high_when_weishi | high |
| 吕布 | lvbu_feijiang_yapo | 飞将压迫 | passive | 6 | soldier | current_target_area_soldier_attack_reduce | false | - | - | none |
| 诸葛亮 | zhugeliang_bagua_zhen | 八卦阵 | active | 1 | all | current_target_area_max_4_attack_reduce | true | - | high_when_cluster | high |
| 诸葛亮 | zhugeliang_guanxing | 观星 | passive | 2 | self | back_row_gain_moulue | false | back_row_789 | - | none |
| 诸葛亮 | zhugeliang_jie_dongfeng | 借东风 | active | 3 | all | current_lane_max_5_slow | true | - | high_when_lane_cluster | high |
| 诸葛亮 | zhugeliang_yushan_lunjin | 羽扇纶巾 | passive | 4 | self | back_row_ranged_reduce_moulue_magic_damage | false | back_row_789 | - | none |
| 诸葛亮 | zhugeliang_bazhen_dingjun | 八阵定军 | active | 5 | all | current_target_area_max_4_stun | true | - | high_when_cluster_or_boss_window | high |
| 诸葛亮 | zhugeliang_kongcheng | 空城 | passive | 6 | self | low_hp_shield_gain_moulue | false | - | - | none |

## 字段待补

首轮原型前还需要补充：`cooldown`、`cast_range`、`effect_type`、`effect_value`、`duration`、`internal_cooldown`、`readability_note`、`manual_targeting_rule`。

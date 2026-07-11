# 第一批 10 英雄技能配置 v1

> 状态：机制字段整理中。本文是首批 10 英雄进入程序实现与数值设计前的统一落表入口；旧版 8 英雄 v0 表仅作历史参考。

## 使用约定

- 技能解锁固定为：1 星主动、2 星被动、3 星主动、4 星被动、5 星主动、6 星被动。
- 主动技能默认自动释放；关闭该英雄自动释放后，该英雄所有已解锁主动技能进入公共技能卡牌池。
- 所有“前排 / 后排 / 侧翼”条件只读取本波次战前锁定站位，不受战斗中的移动、追击、击退或绕行影响。
- `数值状态 = 待配置` 表示机制已确认，但伤害、治疗、护盾、冷却、施法距离等尚未确认；程序不得自行补值。
- 当前未定义统一的技能伤害、治疗、护盾与控制抗性基线。本表先锁定字段、目标和触发口径，数值将在下一轮逐英雄审核。
- P0 的统一数值尺度见 [p0-skill-numeric-baseline-v0.1.md](p0-skill-numeric-baseline-v0.1.md)。

## 通用字段

| 字段 | 说明 |
| --- | --- |
| `skill_id` | 程序配置主键；新建后不可随意改名。 |
| `target_rule` | 目标筛选规则；`leader` 只选队长，`soldier` 只选小兵，`all` 可包含两者。 |
| `card_pool` | 主动技能为 `true`，被动为 `false`。 |
| `auto_rule` | 自动释放模式的目标与释放优先级。 |
| `manual_rule` | 关闭英雄自动释放后，卡牌模式允许的目标选择方式。 |
| `effect_payload` | 需要落入配置的伤害、治疗、护盾、状态、层数、次数、持续时间、内置冷却与资源变化。 |

## 黄忠

核心资源：蓄势，最多 3 层；战前锁定后排 `7/8/9` 时，普攻命中获得；受到近战伤害时清空。

| 星级 | skill_id | 类型 | target_rule / card_pool | auto_rule / manual_rule | effect_payload / 数值状态 |
| --- | --- | --- | --- | --- | --- |
| 1 | `huangzhong_dingjun_jian` | 主动 | `current_target` / `true` | 自动攻击当前目标；手动指定敌方当前可选目标 | 消耗 1 层蓄势；单体伤害；攻击速度降低。伤害、减速幅度、持续时间、CD 待配置。 |
| 2 | `huangzhong_laogong_wenshou` | 被动 | `self` / `false` | - | 后排普攻速度提高；普攻获得蓄势。攻速数值待配置。 |
| 3 | `huangzhong_chuanyun_guanzhen` | 主动 | `current_lane_path` / `true` | 自动优先敌人较密集的一路；手动指定敌方一路 | 当前一路穿透伤害；消耗 1 层蓄势强化；命中队长或精英时降低攻击。伤害、攻击降低值、持续时间、CD 待配置。 |
| 4 | `huangzhong_shouwei_shengong` | 被动 | `self` / `false` | - | 后排远程减伤；一段时间未受近战伤害时，下一次主动至少保留 1 层蓄势。减伤、时间阈值待配置。 |
| 5 | `huangzhong_baibu_chuanyang` | 主动 | `lowest_hp_enemy_leader_or_elite` / `true` | 自动选择生命比例最低的敌方队长或精英；手动指定队长或精英 | 消耗全部蓄势；单体高伤；目标施法时打断。基础伤害、每层增幅、CD 待配置。 |
| 6 | `huangzhong_jianzhen_laojiang` | 被动 | `own_ranged_soldiers` / `false` | - | 远程小兵攻速提高；蓄势满层时对敌方小兵增伤。不改变小兵目标。数值待配置。 |

## 刘备

核心资源：仁德，友方队长生命低于 40% 时获得；每名队长 8 秒最多提供 1 层；最多 3 层；波次结束清空。刘备全部主动技能仅作用友方队长。

| 星级 | skill_id | 类型 | target_rule / card_pool | auto_rule / manual_rule | effect_payload / 数值状态 |
| --- | --- | --- | --- | --- | --- |
| 1 | `liubei_rende_yuanhu` | 主动 | `lowest_hp_ally_leader` / `true` | 自动治疗生命比例最低的友方队长；手动指定友方队长 | 治疗；消耗 1 层仁德时提高治疗。治疗量、强化值、CD 待配置。 |
| 2 | `liubei_kuanren` | 被动 | `ally_leader_below_40` / `false` | - | 仁德获取；后排远程减伤。减伤数值待配置。 |
| 3 | `liubei_tongxin_huwei` | 主动 | `lowest_hp_ally_leader` / `true` | 自动保护生命比例最低的友方队长；手动指定友方队长 | 护盾；消耗 1 层仁德时提高护盾。护盾值、强化值、持续时间、CD 待配置。 |
| 4 | `liubei_renwang_guixin` | 被动 | `lowest_hp_ally_leader` / `false` | - | 每次主动后，最低生命比例友方队长获得持续 6 秒恢复；刘备持有仁德时延长。恢复量、延长秒数待配置。 |
| 5 | `liubei_taoyuan_zhenjun` | 主动 | `all_ally_leaders` / `true` | 自动在多名友方队长低血时释放；手动无目标或指定己方阵列 | 治疗全体友方队长并清除 1 个普通减益；消耗全部仁德强化治疗。治疗量、每层增幅、CD 待配置。 |
| 6 | `liubei_hanshi_yuze` | 被动 | `ally_leader_below_30` / `false` | - | 任意友方队长低于 30% 时获得护盾；刘备自身 12 秒 ICD。护盾值、持续时间待配置。 |

## 吕蒙

核心机制：攻击命中时，吕蒙位于目标背后 120 度范围内则为背刺。隐身期间可普攻且不破隐；主动、受伤或持续结束时解除隐身。

| 星级 | skill_id | 类型 | target_rule / card_pool | auto_rule / manual_rule | effect_payload / 数值状态 |
| --- | --- | --- | --- | --- | --- |
| 1 | `lvmeng_baiyi_qianxi` | 主动 | `current_target` / `true` | 自动攻击当前目标；手动指定敌方单位 | 突袭伤害并进入隐身；背刺时提高伤害。伤害、背刺增幅、隐身持续、CD 待配置。 |
| 2 | `lvmeng_ceyi_bufa` | 被动 | `self` / `false` | - | 战前锁定侧翼时提高普攻速度；背刺额外伤害。数值待配置。 |
| 3 | `lvmeng_shuangdao_duanying` | 主动 | `current_target` / `true` | 自动攻击当前目标；手动指定敌方单位 | 固定 2 次斩击，每次独立判定背刺；第二击命中生命低于 50% 的目标时提高伤害。数值、CD 待配置。 |
| 4 | `lvmeng_cangfeng` | 被动 | `self` / `false` | - | 隐身时降低远程伤害；战前锁定侧翼时延长隐身。减伤、延长秒数待配置。 |
| 5 | `lvmeng_baiyi_dujiang` | 主动 | `lowest_hp_enemy_leader_or_elite` / `true` | 自动选择最低生命比例队长或精英；手动指定队长或精英 | 突袭、隐身、背刺强化；目标低于 35% 时进一步提高伤害。各段伤害、隐身、CD 待配置。 |
| 6 | `lvmeng_shibie_sanri` | 被动 | `self` / `false` | - | 脱离隐身后短暂减伤；击败队长或精英时延长。减伤、持续与延长待配置。 |

## 赵云

核心资源：游龙，成功闪避获得 1 层，最多 3 层。`游龙身法` 提供闪避 +15%；侧翼提供闪避 +8%、普攻速度 +12%。

| 星级 | skill_id | 类型 | target_rule / card_pool | auto_rule / manual_rule | effect_payload / 数值状态 |
| --- | --- | --- | --- | --- | --- |
| 1 | `zhaoyun_longdan_tu` | 主动 | `current_target` / `true` | 自动攻击当前目标；手动指定敌方单位 | 突击伤害；消耗 1 层游龙追加 1 次枪影伤害。两段伤害、CD 待配置。 |
| 2 | `zhaoyun_youlong_shenfa` | 被动 | `self` / `false` | - | 闪避 +15%；成功闪避获得游龙。 |
| 3 | `zhaoyun_qijin_qichu` | 主动 | `current_target_area_max_3` / `true` | 自动在目标区域至少有多个敌人时释放；手动指定敌方目标区域 | 最多 3 个敌人各 1 次伤害；消耗 2 层游龙时各 2 次伤害。伤害、CD 待配置。 |
| 4 | `zhaoyun_baima_qingqi` | 被动 | `self` / `false` | - | 战前锁定侧翼：闪避 +8%，普攻速度 +12%。 |
| 5 | `zhaoyun_changban_huiqiang` | 主动 | `lowest_hp_ally_leader_target` / `true` | 自动援护最低生命比例友方队长；手动指定友方队长 | 攻击该友方队长正在攻击的目标；消耗 1 层游龙时为友方队长施加护盾。伤害、护盾、CD 待配置。 |
| 6 | `zhaoyun_yishen_shidan` | 被动 | `self` / `false` | - | 消耗游龙后：闪避 +7%、普攻速度 +15%，持续 4 秒；持有 3 层游龙时普攻速度 +20%。 |

## 张飞

核心资源：守势，受到近战伤害获得；每秒最多 1 层，最多 3 层；每层近战减伤 6%，持续 5 秒并可刷新；被消耗时失去对应减伤。

| 星级 | skill_id | 类型 | target_rule / card_pool | auto_rule / manual_rule | effect_payload / 数值状态 |
| --- | --- | --- | --- | --- | --- |
| 1 | `zhangfei_dangyang_nuhou` | 主动 | `current_target` / `true` | 自动优先队长或精英；手动指定敌方单位 | 单体伤害并嘲讽 3 秒；有守势时嘲讽额外 +1 秒。伤害、CD 待配置。 |
| 2 | `zhangfei_shoumen_mengjiang` | 被动 | `self` / `false` | - | 战前锁定前排：近战减伤 +10%；守势循环。 |
| 3 | `zhangfei_shemao_henglan` | 主动 | `current_lane_front_max_3` / `true` | 自动当前路前方目标较多时释放；手动指定敌方一路 | 当前一路前方最多 3 个敌人：伤害、击退；消耗 1 层守势时降低攻击 3 秒。伤害、攻击降低值、CD 待配置。 |
| 4 | `zhangfei_qiangdun_chengqiang` | 被动 | `own_soldiers` / `false` | - | 小队小兵近战减伤 +10%；持有守势时额外 +8%。 |
| 5 | `zhangfei_juqiao_sishou` | 主动 | `self_and_current_target` / `true` | 自动承压时释放；手动无需目标 | 自身护盾并嘲讽当前目标 3 秒；消耗全部守势，每层提高护盾。护盾值、每层增幅、持续、CD 待配置。 |
| 6 | `zhangfei_wanfu_mokai` | 被动 | `self` / `false` | - | 生命低于 40%：立即获得 3 层守势；12 秒 ICD。 |

## 夏侯惇

核心资源：刚烈，受到近战伤害获得；每秒最多 1 层，最多 4 层。满层自动消耗并反斩当前目标区域；反斩 3 秒 ICD；护盾吸收的近战伤害也计入。

| 星级 | skill_id | 类型 | target_rule / card_pool | auto_rule / manual_rule | effect_payload / 数值状态 |
| --- | --- | --- | --- | --- | --- |
| 1 | `xiahoudun_dumu_yingji` | 主动 | `current_target_and_self` / `true` | 自动攻击当前目标；手动指定敌方单位 | 单体伤害并获得护盾；持有刚烈时提高护盾。伤害、护盾、强化、持续、CD 待配置。 |
| 2 | `xiahoudun_ganglie` | 被动 | `self_area` / `false` | - | 刚烈循环与满层反斩。反斩伤害、区域范围待配置。 |
| 3 | `xiahoudun_bashi_nuzhan` | 主动 | `current_target` / `true` | 自动攻击当前目标；手动指定敌方单位 | 立即获得 2 层刚烈并斩击；本次满层时立刻触发反斩。伤害、CD 待配置。 |
| 4 | `xiahoudun_dumu_butui` | 被动 | `self` / `false` | - | 战前锁定前排：击退效果降低 50%；持有刚烈时近战减伤 +8%。 |
| 5 | `xiahoudun_liezhen_fanpu` | 主动 | `current_lane_front_max_3` / `true` | 自动当前路目标较多时释放；手动指定敌方一路 | 当前一路前方最多 3 个敌人：伤害、击退；每层刚烈提高伤害；释放后消耗全部刚烈。数值、CD 待配置。 |
| 6 | `xiahoudun_yishang_huanshi` | 被动 | `self` / `false` | - | 触发反斩后，下一次主动技能伤害 +20%。 |

## 吕布

核心资源：威势，参与击破敌方队长或精英时获得；参与指目标死亡前 3 秒内造成过伤害；最多 3 层；每层攻击 +6%；波次结束清空。

| 星级 | skill_id | 类型 | target_rule / card_pool | auto_rule / manual_rule | effect_payload / 数值状态 |
| --- | --- | --- | --- | --- | --- |
| 1 | `lvbu_fangtian_yazhen` | 主动 | `current_lane_front_max_3` / `true` | 自动当前路前方目标较多时释放；手动指定敌方一路 | 当前一路前方最多 3 个敌人伤害；每层威势提高伤害。基础、每层、CD 待配置。 |
| 2 | `lvbu_jixia_wutui` | 被动 | `self` / `false` | - | 战前锁定前排：近战减伤 +10%；普攻队长或精英时伤害 +10%。 |
| 3 | `lvbu_zhenqian_jiaozhan` | 主动 | `current_target` / `true` | 自动优先队长或精英；手动指定敌方单位 | 单体伤害；目标为队长或精英时嘲讽 3 秒并降低攻击 3 秒。伤害、攻击降低值、CD 待配置。 |
| 4 | `lvbu_renzhong_lvbu` | 被动 | `self` / `false` | - | 威势循环。 |
| 5 | `lvbu_yuanmen_zhanjiang` | 主动 | `lowest_hp_enemy_leader_or_elite` / `true` | 自动选择最低生命比例队长或精英；手动指定队长或精英 | 突击高伤；消耗全部威势，每层提高伤害。基础、每层、CD 待配置。 |
| 6 | `lvbu_feijiang_yapo` | 被动 | `current_target_area_soldiers` / `false` | - | 持有威势时，当前目标区域敌方小兵攻击降低；满 3 层时提高效果。数值待配置。 |

## 诸葛亮

核心资源：谋略。战前锁定后排 `7/8/9` 时，每 4 秒获得 1 层，最多 3 层；受到近战伤害失去 1 层；战斗移动不清空谋略。

| 星级 | skill_id | 类型 | target_rule / card_pool | auto_rule / manual_rule | effect_payload / 数值状态 |
| --- | --- | --- | --- | --- | --- |
| 1 | `zhugeliang_bagua_zhen` | 主动 | `current_target_area_max_4` / `true` | 自动目标区域单位较多时释放；手动指定敌方目标区域 | 最多 4 个敌人：法术伤害并降低攻击 3 秒；消耗 1 层谋略提高伤害。数值、CD 待配置。 |
| 2 | `zhugeliang_guanxing` | 被动 | `self` / `false` | - | 谋略循环。 |
| 3 | `zhugeliang_jie_dongfeng` | 主动 | `current_lane_max_5` / `true` | 自动当前路目标较多时释放；手动指定敌方一路 | 当前一路最多 5 个敌人法术伤害；消耗 1 层谋略时额外减速 3 秒。伤害、减速、CD 待配置。 |
| 4 | `zhugeliang_yushan_lunjin` | 被动 | `self` / `false` | - | 后排远程减伤 +12%；持有谋略时主动法术伤害 +8%。 |
| 5 | `zhugeliang_bazhen_dingjun` | 主动 | `current_target_area_max_4` / `true` | 自动目标区域单位较多或 Boss 可控时释放；手动指定敌方目标区域 | 最多 4 个敌人：法术伤害并眩晕 1 秒；消耗全部谋略，每层提高伤害。数值、CD 待配置。 |
| 6 | `zhugeliang_kongcheng` | 被动 | `self` / `false` | - | 生命低于 35%：获得护盾并立即获得 1 层谋略；12 秒 ICD。护盾、持续待配置。 |

## 司马懿

核心资源：筹谋。每释放 1 次主动技能获得 1 层，最多 3 层；满层进入“定局”，下一次主动强化并消耗全部筹谋；波次结束清空。

| 星级 | skill_id | 类型 | target_rule / card_pool | auto_rule / manual_rule | effect_payload / 数值状态 |
| --- | --- | --- | --- | --- | --- |
| 1 | `simayi_yingshi` | 主动 | `enemy_leader` / `true` | 自动优先当前高威胁队长；手动指定敌方队长 | 240% 法术伤害；目标 6 秒内受到司马懿伤害 +12%；定局：330%、+18%。CD 待配置。 |
| 2 | `simayi_shenmou_yuanlv` | 被动 | `self` / `false` | - | 释放任意主动获得 1 层筹谋。 |
| 3 | `simayi_fuxin` | 主动 | `enemy_leader` / `true` | 自动优先高输出队长；手动指定敌方队长 | 120% 法术伤害；5 秒伤害 -20%、攻速 -25%；定局：7 秒、伤害 -30%、攻速 -35%。CD 待配置。 |
| 4 | `simayi_yinren_daibian` | 被动 | `self` / `false` | - | 首次低于 45% 最大生命：获得 25% 最大生命护盾，持续 8 秒；每波 1 次。 |
| 5 | `simayi_zhonghujue` | 主动 | `enemy_leader` / `true` | 自动优先已有鹰视或缚心的队长；手动指定敌方队长 | 300% 法术伤害；目标有鹰视或缚心时 450%；定局：420% / 600%。CD 待配置。 |
| 6 | `simayi_jianglue_tongjun` | 被动 | `own_ranged_soldiers` / `false` | - | 进入定局时，小队远程小兵 6 秒内对其自然攻击的敌方队长伤害 +25%；不切换目标。 |

## 甘宁

核心资源：火药。普通攻击命中任意敌方单位 3 次获得 1 层，最多 3 层；满层进入“满膛”，下一次主动强化并消耗全部火药；波次结束清空。

| 星级 | skill_id | 类型 | target_rule / card_pool | auto_rule / manual_rule | effect_payload / 数值状态 |
| --- | --- | --- | --- | --- | --- |
| 1 | `ganning_jinfan_lianchong` | 主动 | `enemy_leader` / `true` | 自动攻击当前高威胁队长；手动指定敌方队长 | 连续 3 次，每次 85% 物理伤害；满膛：5 次，每次 95%。CD 待配置。 |
| 2 | `ganning_huoyao_zhuangtian` | 被动 | `self` / `false` | - | 普攻命中 3 次获得 1 层火药。 |
| 3 | `ganning_zhendan_chongji` | 主动 | `enemy_leader` / `true` | 自动优先高输出队长；手动指定敌方队长 | 180% 物理伤害；5 秒伤害 -20%、攻速 -25%；满膛：250%、7 秒、伤害 -30%、攻速 -35%。CD 待配置。 |
| 4 | `ganning_jinfan_ceji` | 被动 | `self` / `false` | - | 战前锁定侧翼：闪避 +8%，攻速 +15%。 |
| 5 | `ganning_zhanqi_duojiang` | 主动 | `enemy_leader` / `true` | 自动优先低血队长；手动指定敌方队长 | 250% 物理伤害；目标生命低于 35% 时 450%；满膛：阈值 50%、伤害 540%。CD 待配置。 |
| 6 | `ganning_duanbing_jiexian` | 被动 | `own_melee_soldiers` / `false` | - | 主动命中敌方队长后，小队近战小兵 6 秒内对该队长伤害 +25%；不切换目标。 |

## v1 未完成项

以下字段必须在开始程序实装前完成数值审核：

- 所有 30 个主动技能：`cooldown`、`cast_range`、伤害或治疗基数、成长系数、最大有效目标数与无合法目标处理。
- 所有护盾、生命恢复、增伤、减伤、攻速、攻击降低、减速、击退效果：数值、持续时间、叠加和刷新规则。
- 所有区域、一路、路径与“当前目标区域”：统一几何范围与目标排序。
- 所有控制效果：嘲讽、打断、眩晕、击退、隐身、Boss 抗性与免疫优先级。
- 自动释放 AI 的精确阈值与卡牌手动指定规则。

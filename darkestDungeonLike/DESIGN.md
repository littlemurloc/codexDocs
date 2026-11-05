# 暗黑地牢 1 — 数据结构与战斗规则还原文档

> 本文档由 `tools/gen_doc.py` 从游戏安装目录自动生成。
> 所有数值均来自 `D:/Program Files (x86)/Steam/steamapps/common/DarkestDungeon` 的明文配置，
> 标注「推断」的段落是基于行为的合理推测，未在可执行文件中验证。
> **仅供个人研究与学习，数据与美术版权归 Red Hook Studios 所有，不得用于商业用途。**

## 1. 数据完整度

| 系统 | 数量 | 文件 | 备注 |
|---|---|---|---|
| 英雄 | 15 | heroes.json | 每人 7 技能 × 5 级 |
| 怪物变体 | 254 | monsters.json | 101 个家族 |
| 效果定义 | 1215 | effects.json | 技能引用的最小单位 |
| Buff 定义 | 2020 | buffs.json | 数值修正的原子条目 |
| 地图参数 | 44 | dungeons.json | 区域 × 任务类型 × 规模 |
| 遭遇表 | 45 | dungeons.json | 每区 8 张（含 conditional） |
| 掉落表 | 58 | loot.json | 支持表套表嵌套 |
| 饰品 | 490 | trinkets.json |  |
| 怪癖 | 170 | quirks.json |  |
| 物品 | 52 | inventory.json | 金币 / 传家宝 / 宝石 |

原始 DSL 记录 **9496** 条，扫描 `.darkest` 文件 **699** 个，未解析行 **0** 条。

引用完整性校验：所有英雄与怪物技能引用的效果名，共 **0** 条找不到定义（效果定义总数 1189）。该项为 0 说明效果图是完整闭合的。

## 2. 数据模型

### 2.1 站位掩码

技能的作用范围不用坐标，用**数字位串**表示站位集合。这是读懂全部技能配置的关键。

| 字段 | 含义 | 示例 |
|---|---|---|
| `launch` | 技能可以从己方哪些站位发动 | `21` = 己方 1、2 号位 |
| `target` | 可以命中敌方哪些站位 | `12` = 敌方 1、2 号位单体 |
| `target` 带 `~` | 对该集合**全体**生效（AOE） | `~12` = 敌方 1–2 号位全部 |
| `target` 带 `@` | 目标是**友方** | `@1234` = 全体队友 |
| `move` | 施法后自身位移 | `0 1` = 前移 1 格 |

> `~` 与 `@` 的语义为**推断**：依据是 `.target ~12` 只出现在 AOE 技能（如十字军「狂信指控」）上，且该技能带 `-40%` 伤害惩罚，符合 DD1 的 AOE 设计惯例。

### 2.2 英雄字段

| 字段 | 含义 | 说明 |
|---|---|---|
| `resistances` | 八项抗性 | stun / poison / bleed / disease / move / debuff / death_blow / trap |
| `weapon[]` | 武器 5 阶 | `dmg` 是**区间**，`atk`/`crit` 是**加成**（非绝对值） |
| `armour[]` | 护甲 5 阶 | `hp` 是**绝对生命值**，`def` 是闪避率，`prot` 是减伤 |
| `skills[]` | 战斗技能 | 每个技能含 `levels[0..4]` 五级，等级即升级次数 |
| `deaths_door` | 死门状态挂载 | 进入死门 / 死门恢复 / 心脏骤停三组 buff |
| `tags` | 标签 | 供奇物与技能条件判定，如 `religious` 影响祭坛交互 |
| `generation` | 随机生成规则 | 怪癖数量、营地技能数、初始技能数 |

**关键点**：英雄技能的 `dmg` 是**百分比修正**（如 `0%`、`-40%`），最终伤害 = 武器区间 × (1 + dmg 修正)。怪物技能的 `dmg` 则是**绝对区间**（如 `2 4`）。两者同名不同义，移植时必须分开处理。

### 2.3 效果（effect）— 最小执行单元

1215 条效果定义，字段词频前 15 位：

| 字段 | 出现次数 | 作用 |
|---|---|---|
| `name` | 1215 |  |
| `target` | 1215 |  |
| `on_hit` | 1206 |  |
| `on_miss` | 1206 |  |
| `chance` | 1203 |  |
| `curio_result_type` | 949 |  |
| `queue` | 588 |  |
| `duration` | 489 |  |
| `combat_stat_buff` | 427 |  |
| `apply_once` | 211 |  |
| `can_apply_on_death` | 176 |  |
| `damage_low_multiply` | 166 |  |
| `damage_high_multiply` | 166 |  |
| `buff_ids` | 156 |  |
| `defense_rating_add` | 113 |  |

效果是**数据驱动的指令**：`.target` 选目标，`.chance` 判命中，`.on_hit`/`.on_miss` 决定成败分支，`.queue` 决定立即执行还是延后结算，`.buff_ids` 挂载 buff，`.duration` 定时长。

## 3. 战斗数学

以下参数全部来自 `shared/rules.json`，原样引用。

### 3.1 命中

- 命中率上限 **95%**，下限 **0%**（即无下限，可 0%）
- 连续未命中补偿：每次未命中累加 **4%** 命中
- 基础行动值 **8**

### 3.2 伤害与暴击

- 玩家暴击倍率 **1.5×**，怪物暴击倍率 **1.5×**
- 溢出暴击：每点超出上限的暴击提供 **0%** 额外倍率，封顶 **20%**

暴击的压力副作用（这才是 DD1 的压迫感来源）：

| 触发者 | 效果 | 对自身 | 对队友 |
|---|---|---|---|
| 怪物暴击 | 压力伤害 | 100% 概率 +10 | 50% 概率 +5 |
| 玩家暴击 | 压力缓解 | 100% 概率 -3 | 25% 概率 -3 |

- 玩家暴击时喊话概率 **75%**；击杀缓解压力概率 **50%**，数值 **-3**

### 3.3 压力（Stress）与死门

- 空过一回合：**+5** 压力/回合
- 进入死门：自身 **+8**，队友 25% 概率 **+4**
- 死门持续（重复触发）：自身 **+4**，队友 25% 概率 **+2**
- 队友死亡：**50%** 概率 **+12** 压力
- 压力崩溃判定率 **75%**；抵抗成功回落至 **45**
- 怪癖上限：正面 **5** / 负面 **5** / 疾病 **3**；锁定上限各 **3**

### 3.4 光照（Torch）

光照分 5 档，直接改写战斗参数。这是 DD1 最核心的风险/收益旋钮。

| 光照区间 | 压力几率 | 压力伤害 | 怪物伤害 | 怪物暴击 | 金币掉落 | 怪物被惊袭 |
|---|---|---|---|---|---|---|
| ≥ 75 | +0 | +0 | +0 | +0 | +0 | +25 |
| 50 – 75 | +5 | +10 | +0 | +1 | +0 | +15 |
| 25 – 50 | +10 | +20 | +10 | +2 | +10 | +10 |
| 0 – 25 | +25 | +30 | +15 | +3 | +15 | +5 |
| < 0 | +35 | +40 | +25 | +5 | +30 | +0 |

火把消耗：每移动一格，明亮区 **-1**、微光区 **-6**、黑暗区 **-6**。营地休息回复 **+100**，被夜袭 **-100**。

> 注意最后一列：**越黑，怪物越容易被惊袭**（黑暗提供先手优势），但代价是承伤、压力、暴击全面上升。这个矛盾设计是 DD1 数值的精髓。

### 3.5 探索与经济

| 机制 | 参数 | 值 |
|---|---|---|
| 营地 | 技能点总数 | 12 |
| 营地 | 休息点阈值 | 6 |
| 营地 | 最多营地技能 | 3 |
| 惊袭 | 走廊基础概率 | 10% |
| 惊袭 | 已知走廊 | 25% |
| 惊袭 | 上限 | 65% |
| 扎营 | 夜袭基础概率 | 33% |
| 陷阱 | 侦察后解除加成 | 40% |
| 撤退 | 基础成功率 | 70% |
| 撤退 | 每次尝试加成 | 5% |
| 撤退 | 代价 | +20 压力 |
| 侦察 | 基础概率 | 25% |
| 补给 | 食物回血 | 5% |

进食分级（直接影响压力）：

| 档位 | 口粮/人 | 回血 | 压力 |
|---|---|---|---|
| none | 0 | -20% | 15 |
| half | 0.5 | 0% | 0 |
| full | 1 | 10% | 0 |
| feast | 2 | 25% | -10 |

饿肚子（`none`）是 **-20% 生命 + 15 压力**——惩罚远大于战斗失误，这是设计上的强约束。

### 3.6 拖延惩罚（Stall）

DD1 用一套独立规则防止玩家靠治疗刷血：

| 参数 | 值 |
|---|---|
| 队伍人数阈值 | 3 |
| 敌人数阈值 | 2 |
| 失效技能数阈值 | 2 |
| 回合压力效果阈值 | 3 |
| 回合召唤效果阈值 | 4 |
| 回合重置阈值 | 4 |
| 惩罚名 | stall_stress |

## 4. 地牢生成参数

| 区域 | 任务类型 | 规模 | 房间数 | 走廊数 | 网格 | 连通度 | 走廊战斗 | 房间战斗 |
|---|---|---|---|---|---|---|---|---|
| crypts | explore | short | 9 | 10 | 4×3 | 0.9 | 2–4 | 1–3 |
| weald | explore | short | 9 | 10 | 4×4 | 0.85 | 2–4 | 1–3 |
| warrens | explore | short | 9 | 10 | 4×3 | 0.95 | 2–4 | 1–3 |
| cove | explore | short | 9 | 10 | 4×4 | 0.9 | 2–4 | 1–3 |
| crypts | explore | medium | 14 | 15 | 5×4 | 0.9 | 3–4 | 3–4 |
| weald | explore | medium | 14 | 15 | 5×5 | 0.85 | 3–4 | 3–4 |
| warrens | explore | medium | 14 | 15 | 6×3 | 0.95 | 3–4 | 3–4 |
| cove | explore | medium | 14 | 15 | 5×5 | 0.9 | 3–4 | 3–4 |
| crypts | explore | long | 19 | 20 | 5×5 | 0.9 | 7 | 7 |
| weald | explore | long | 19 | 20 | 6×5 | 0.85 | 7 | 7 |
| warrens | explore | long | 19 | 20 | 5×4 | 0.95 | 7 | 7 |
| cove | explore | long | 19 | 20 | 6×5 | 0.9 | 7 | 7 |
| crypts | kill_boss | medium | 11 | 11 | 5×4 | 0.9 | 4–5 | 4–5 |
| weald | kill_boss | medium | 11 | 11 | 6×3 | 0.85 | 4–5 | 4–5 |
| warrens | kill_boss | medium | 11 | 11 | 4×3 | 0.95 | 4–5 | 4–5 |
| cove | kill_boss | medium | 11 | 11 | 6×3 | 0.9 | 4–5 | 4–5 |
| crypts | kill_boss | long | 14 | 11 | 6×3 | 0.9 | 8 | 8 |
| weald | kill_boss | long | 14 | 11 | 6×4 | 0.85 | 8 | 8 |
| warrens | kill_boss | long | 14 | 11 | 4×4 | 0.95 | 8 | 8 |
| cove | kill_boss | long | 14 | 11 | 6×4 | 0.9 | 8 | 8 |
| crypts | cleanse | short | 7 | 8 | 4×3 | 0.9 | 2–4 | 2–4 |
| weald | cleanse | short | 7 | 8 | 5×3 | 0.85 | 2–4 | 2–4 |
| warrens | cleanse | short | 7 | 8 | 3×3 | 0.95 | 2–4 | 2–4 |
| cove | cleanse | short | 7 | 8 | 5×3 | 0.9 | 2–4 | 2–4 |
| crypts | cleanse | medium | 11 | 11 | 5×3 | 0.9 | 4–5 | 4–5 |
| weald | cleanse | medium | 11 | 11 | 6×3 | 0.85 | 4–5 | 4–5 |
| warrens | cleanse | medium | 11 | 11 | 4×4 | 0.95 | 4–5 | 4–5 |
| cove | cleanse | medium | 11 | 11 | 6×3 | 0.9 | 4–5 | 4–5 |
| crypts | cleanse | long | 14 | 15 | 5×4 | 0.9 | 8 | 8 |
| weald | cleanse | long | 14 | 15 | 5×5 | 0.85 | 8 | 8 |
| warrens | cleanse | long | 14 | 15 | 4×4 | 0.95 | 8 | 8 |
| cove | cleanse | long | 14 | 15 | 5×5 | 0.9 | 8 | 8 |
| crypts | gather | medium | 13 | 11 | 5×4 | 0.9 | 4–5 | 4–5 |
| weald | gather | medium | 13 | 11 | 6×4 | 0.85 | 4–5 | 4–5 |
| warrens | gather | medium | 13 | 11 | 5×3 | 0.95 | 4–5 | 4–5 |
| cove | gather | medium | 13 | 11 | 6×4 | 0.9 | 4–5 | 4–5 |
| crypts | activate | medium | 13 | 11 | 5×4 | 0.9 | 4–5 | 4–5 |
| weald | activate | medium | 13 | 11 | 6×4 | 0.85 | 4–5 | 4–5 |
| warrens | activate | medium | 13 | 11 | 5×3 | 0.95 | 4–5 | 4–5 |
| cove | activate | medium | 13 | 11 | 6×4 | 0.9 | 4–5 | 4–5 |
| crypts | inventory_activate | medium | 13 | 11 | 5×4 | 0.9 | 4–5 | 4–5 |
| weald | inventory_activate | medium | 13 | 11 | 6×4 | 0.85 | 4–5 | 4–5 |
| warrens | inventory_activate | medium | 13 | 11 | 5×3 | 0.95 | 4–5 | 4–5 |
| cove | inventory_activate | medium | 13 | 11 | 6×4 | 0.9 | 4–5 | 4–5 |

生成器不是格子迷宫，而是**房间-走廊图**：先按网格撒房间，再按连通度连边，然后按各类 POI 的区间数量往走廊和房间上挂内容（战斗/陷阱/障碍/奇物/饥饿）。

关键参数含义：

- `connectivity` 越高，地图越像一张网，绕路多；越低越像树，死路多
- `min_final_distance` 保证终点房间离起点足够远
- `nudge_span` / `nudge_neighbour_bias` / `nudge_map_centre_bias` 控制地图布局的「自然感」扰动

### 4.1 奇物刷新权重（以 weald 为例）

| 类别 | 权重 | 奇物 |
|---|---|---|
| hall_curios | 10 | discarded_pack |
| hall_curios | 8 | sconce |
| hall_curios | 10 | crate |
| hall_curios | 10 | sack |
| hall_curios | 5 | mummified_remains |
| hall_curios | 8 | old_tree |
| hall_curios | 8 | beast_carcass |
| hall_curios | 5 | cosmic_spiderweb |
| room_curios | 2 | pristine_fountain |
| room_curios | 4 | ancient_coffin |
| room_curios | 3 | travellers_tent |
| room_curios | 1 | eldritch_altar |
| room_treasures | 2 | unlocked_strongbox |
| room_treasures | 3 | locked_strongbox |
| room_treasures | 3 | heirloom_chest |
| traps | 1 | poison_cloud |
| obstacles | 1 | thorny_thicket |
| prison_doors | 1 | weald_door_shovel |
| prison_doors | 1 | weald_door_key |

### 4.2 遭遇表结构

五个主区域（crypts / weald / warrens / cove / darkestdungeon），每区分 5 个难度层；`_shared` 与 `town` 是教学关和共享桶，`conditional_*` 是剧情条件覆盖表。

| 区域 | 层/条件 | hall 条目 | room 条目 | boss | stall |
|---|---|---|---|---|---|
| _shared | 1 | 2 | 0 | 0 | 0 |
| _shared | 2 | 0 | 0 | 0 | 0 |
| _shared | 3 | 2 | 0 | 0 | 0 |
| _shared | 4 | 0 | 0 | 0 | 0 |
| _shared | 5 | 2 | 0 | 0 | 0 |
| _shared | 6 | 2 | 0 | 0 | 0 |
| cove | 1 | 20 | 18 | 2 | 3 |
| cove | 2 | 12 | 19 | 1 | 0 |
| cove | 3 | 27 | 22 | 2 | 4 |
| cove | 4 | 12 | 19 | 1 | 0 |
| cove | 5 | 33 | 29 | 2 | 5 |
| cove | conditional_1 | 2 | 0 | 0 | 0 |
| cove | conditional_3 | 2 | 0 | 0 | 0 |
| cove | conditional_5 | 2 | 0 | 0 | 0 |
| crypts | 1 | 21 | 14 | 2 | 5 |
| crypts | 2 | 17 | 19 | 1 | 0 |
| crypts | 3 | 32 | 26 | 2 | 6 |
| crypts | 4 | 17 | 19 | 1 | 0 |
| crypts | 5 | 38 | 34 | 2 | 6 |
| crypts | conditional_1 | 2 | 0 | 0 | 0 |
| crypts | conditional_3 | 2 | 0 | 0 | 0 |
| crypts | conditional_5 | 2 | 0 | 0 | 0 |
| darkestdungeon | 6 | 1 | 1 | 2 | 2 |
| town | 1 | 21 | 14 | 2 | 5 |
| town | 2 | 17 | 19 | 1 | 0 |
| town | 3 | 32 | 26 | 2 | 6 |
| town | 4 | 17 | 19 | 1 | 0 |
| town | 5 | 30 | 21 | 2 | 5 |
| town | 6 | 1 | 1 | 1 | 4 |
| warrens | 1 | 26 | 11 | 2 | 4 |
| warrens | 2 | 23 | 23 | 1 | 0 |
| warrens | 3 | 35 | 20 | 2 | 5 |
| warrens | 4 | 23 | 23 | 1 | 0 |
| warrens | 5 | 39 | 26 | 2 | 6 |
| warrens | conditional_1 | 2 | 0 | 0 | 0 |
| warrens | conditional_3 | 2 | 0 | 0 | 0 |
| warrens | conditional_5 | 2 | 0 | 0 | 0 |
| weald | 1 | 21 | 13 | 3 | 4 |
| weald | 2 | 12 | 19 | 1 | 0 |
| weald | 3 | 36 | 20 | 3 | 5 |
| weald | 4 | 12 | 19 | 1 | 0 |
| weald | 5 | 37 | 24 | 3 | 6 |
| weald | conditional_1 | 2 | 0 | 0 | 0 |
| weald | conditional_3 | 2 | 0 | 0 | 0 |
| weald | conditional_5 | 2 | 0 | 0 | 0 |

每条遭遇是「概率 + 怪物 id 列表」，例如 weald 第 1 层：

- 权重 0.01 → `brigand_cutthroat_A`
- 权重 1 → `rabid_dog_A + rabid_dog_A + rabid_dog_A`
- 权重 2 → `ectoplasm_A + ectoplasm_A`
- 权重 1 → `fungal_bloat_A + fungal_bloat_A + fungal_artillery_A`

## 5. 英雄速查

| 英雄 | 生命 1→5 | 武器伤害 1→5 | 速度 | 眩晕抗性 | 技能数 | 标签 |
|---|---|---|---|---|---|---|
| abomination | 26 → 46 | 6–11 → 11–20 | 7 | 40% | 7 | light, non-religious, outsiders_bonfire |
| antiquarian | 17 → 29 | 3–5 → 5–9 | 5 | 20% | 7 | light, non-religious, library |
| arbalest | 27 → 47 | 4–8 → 7–14 | 3 | 40% | 7 | heavy, non-religious, training_ring |
| bounty_hunter | 25 → 45 | 5–10 → 8–16 | 5 | 40% | 7 | heavy, non-religious, house_of_the_yellow_hand |
| crusader | 33 → 61 | 6–12 → 10–19 | 1 | 40% | 7 | heavy, religious, altar_of_light |
| grave_robber | 20 → 36 | 4–8 → 7–14 | 8 | 20% | 7 | light, non-religious, house_of_the_yellow_hand |
| hellion | 26 → 46 | 6–12 → 10–19 | 4 | 40% | 7 | non-religious, heavy, outsiders_bonfire |
| highwayman | 23 → 43 | 5–10 → 9–16 | 5 | 30% | 7 | light, non-religious, house_of_the_yellow_hand |
| houndmaster | 21 → 37 | 4–7 → 7–13 | 5 | 40% | 7 | light, non-religious, training_ring |
| jester | 19 → 35 | 4–7 → 7–13 | 7 | 20% | 7 | light, non-religious, theater |
| leper | 35 → 63 | 8–16 → 13–26 | 2 | 60% | 7 | heavy, religious, outsiders_bonfire |
| man_at_arms | 31 → 55 | 5–9 → 8–14 | 3 | 40% | 7 | heavy, non-religious, training_ring |
| occultist | 19 → 35 | 4–7 → 7–13 | 6 | 20% | 7 | light, non-religious, library |
| plague_doctor | 22 → 38 | 4–7 → 7–13 | 7 | 20% | 7 | light, non-religious, library |
| vestal | 24 → 44 | 4–8 → 7–14 | 4 | 30% | 7 | religious, heavy, altar_of_light |

## 6. 怪物速查（按家族聚合）

| 家族 | 变体数 | 生命 | 速度 | 单次伤害 |
|---|---|---|---|---|
| ancestor_big | 1 | 252 | 10 | 0–14 |
| ancestor_flawed | 1 | 29 | 4 | 1–3 |
| ancestor_heart | 1 | 252 | 10 | 0–23 |
| ancestor_nebula | 1 | 999 | 0 | — |
| ancestor_perfect | 1 | 36 | 9 | 2–5 |
| ancestor_pod | 1 | 189 | 2 | 0 |
| ancestor_small | 1 | 5 | 12 | 0 |
| bloated_corpse | 3 | 14–27 | 0–2 | 5–23 |
| brigand_barrel | 1 | 25 | 0 | — |
| brigand_blood | 3 | 35–68 | 1–3 | 1–20 |
| brigand_cannon | 3 | 76–156 | 0–2 | 0–50 |
| brigand_cutthroat | 3 | 12–23 | 3–5 | 2–15 |
| brigand_fuseman | 3 | 8–16 | -20–-18 | 0–3 |
| brigand_fusilier | 3 | 12–23 | 6–8 | 1–7 |
| brigand_hunter | 1 | 25 | 8 | 2–9 |
| brigand_raider | 1 | 25 | 5 | 4–15 |
| brigand_sapper | 1 | 160 | 4 | 0–45 |
| carrion_eater | 3 | 11–21 | 4–6 | 2–7 |
| carrion_eater_big | 3 | 37–72 | 1–3 | 2–20 |
| cauldron_empty | 3 | 100–205 | 0–2 | — |
| cauldron_full | 3 | 14–29 | 0–2 | — |
| cell_battle | 1 | 38 | 6 | 8–17 |
| cell_white | 1 | 25 | 8 | 0–3 |
| collector | 3 | 70–137 | 5–7 | 0–13 |
| collector_battle | 3 | 16–31 | 3–5 | 5–20 |
| collector_protect | 3 | 16–31 | 7–9 | 0–13 |
| collector_shaman | 3 | 16–31 | 5–7 | 0–7 |
| corpse | 4 | 7–14 | 0 | — |
| corpse_large | 4 | 15–30 | 0 | — |
| crone | 3 | 13–25 | 8–10 | 0–5 |
| crow | 4 | 75–154 | 7–9 | 1–18 |
| cultist_brawler | 3 | 15–29 | 5–7 | 2–7 |
| cultist_harpy | 1 | 27 | 9 | 1–3 |
| cultist_orgiastic | 1 | 21 | 9 | 0 |
| cultist_shrouded | 1 | 38 | 7 | 4–14 |
| cultist_warlord | 1 | 32 | 7 | 4–9 |
| cultist_witch | 3 | 13–25 | 7–9 | 1–3 |
| cyst | 1 | 158 | 3 | 8–17 |
| drowned_anchor | 3 | 14–29 | 0–2 | 0 |
| drowned_anchored | 3 | 14–29 | 0–2 | — |
| drowned_captain | 3 | 100–205 | 3–5 | 0–13 |
| drowned_pirate | 3 | 27–53 | 6–8 | 0–3 |
| ectoplasm | 3 | 8–16 | 1–3 | 1–9 |
| ectoplasm_large | 3 | 35–68 | 1–3 | 2–15 |
| errant_flesh_bat | 1 | 25 | 12 | 1–9 |
| errant_flesh_dog | 1 | 34 | 9 | 1–13 |
| fishman_crabby | 3 | 42–82 | 0–2 | 1–13 |
| fishman_harpoon | 3 | 14–27 | 6–8 | 3–17 |
| fishman_shaman | 3 | 12–23 | 10–12 | 0–7 |
| formless_guard | 3 | 25–51 | 1–3 | 2–7 |
| formless_melee | 3 | 25–51 | 5–7 | 6–22 |
| formless_ranged | 3 | 25–51 | 8–10 | 5–17 |
| formless_weak | 3 | 25–51 | 10–12 | 0 |
| fungal_artillery | 3 | 14–27 | 2–4 | 1–3 |
| fungal_bloat | 3 | 19–37 | 0–2 | 2–10 |
| gargoyle | 3 | 7–14 | 8–10 | 1–5 |
| ghoul | 3 | 29–57 | 5–7 | 0–15 |
| hag | 3 | 66–135 | 5–7 | 0–7 |
| jellyfish | 3 | 10–20 | 7–9 | 1–7 |
| madman | 3 | 14–27 | 9–11 | 0–3 |
| maggot | 3 | 6–12 | 3–5 | 2–7 |
| necromancer | 3 | 105–215 | 8–10 | 0–15 |
| nest | 3 | 60–123 | 0 | — |
| octotank | 3 | 25–49 | 0–2 | 0–10 |
| pew_large | 3 | 55–113 | 0–2 | — |
| pew_medium | 3 | 40–82 | 0–2 | — |
| pew_small | 3 | 25–51 | 0–2 | — |
| prophet | 3 | 105–215 | 0–2 | 0–42 |
| rabid_dog | 3 | 10–20 | 8–10 | 1–5 |
| shambler | 4 | 77–174 | 0–3 | 1–3 |
| shambler_tentacle | 4 | 8–18 | 10–13 | 2–9 |
| shuffler | 1 | 162 | 2 | 1–9 |
| siren | 3 | 119–244 | 5–7 | 0–3 |
| skeleton_arbalist | 3 | 15–29 | 5–7 | 2–13 |
| skeleton_bearer | 3 | 22–43 | 5–7 | 0–11 |
| skeleton_captain | 3 | 35–68 | 0–2 | 2–22 |
| skeleton_common | 3 | 8–16 | 1–3 | 2–8 |
| skeleton_courtier | 3 | 10–20 | 8–10 | 2–7 |
| skeleton_defender | 3 | 15–29 | 0–2 | 0–10 |
| skeleton_militia | 3 | 10–20 | 2–4 | 2–14 |
| skeleton_spear | 3 | 15–29 | 3–5 | 2–15 |
| snail_urchin | 3 | 5–10 | -5–-3 | 2–7 |
| spider_spitter | 3 | 7–14 | 4–6 | 1–10 |
| spider_webber | 3 | 7–14 | 5–7 | 1–5 |
| swine_drummer | 3 | 15–29 | 7–9 | 1–2 |
| swine_piglet | 3 | 17–35 | 20–22 | 1–2 |
| swine_prince | 3 | 132–271 | 0–2 | 3–17 |
| swine_reaver | 3 | 21–41 | 3–5 | 2–13 |
| swine_skiver | 3 | 25–49 | 7–9 | 2–18 |
| swine_slasher | 3 | 8–16 | 5–7 | 3–13 |
| swine_wretch | 3 | 12–23 | 8–10 | 1–3 |
| swinetaur | 3 | 45–88 | 0–2 | 0–22 |
| templar_melee | 1 | 137 | 5 | 8–20 |
| templar_melee_mb | 1 | 137 | 5 | 8–26 |
| templar_ranged | 1 | 105 | 6 | 5–17 |
| templar_ranged_mb | 1 | 105 | 6 | 5–26 |
| totem_attack | 1 | 42 | 4 | 4–15 |
| totem_guard | 1 | 42 | 10 | 0 |
| unclean_giant | 3 | 70–137 | 0–2 | 1–37 |
| virago_hateful | 3 | 28–55 | 8–10 | 0–13 |
| virago_shroom | 3 | 16–31 | 1–3 | — |

## 7. 其它内容规模

| 资产 | 数量 | 说明 |
|---|---|---|
| 饰品 | 490 | kickstarter 294，uncommon 44，common 44，rare 33，very_rare 24，very_common 16，ancestral 9，trophy 9 |
| 怪癖 | 170 | 正面 68 / 负面 102 |
| 掉落表 | 58 | 支持 table 嵌套与难度/区域过滤 |
| 任务定义 | 6 | 生成规则 / 剧情任务 / 类型定义 |
| 物品 | 52 | 金币、传家宝、宝石 |

## 8. 无法从数据获得、需要反推的部分

这些逻辑编译在 `Darkest.exe` 里，数据文件只提供参数不提供算法：

| 系统 | 已知 | 缺失 | 反推难度 |
|---|---|---|---|
| 效果结算顺序 | `.queue` 标记了哪些延后 | 延后效果的层内排序规则 | 中 |
| 行动顺序 | `initiative_base` 与速度值 | 速度相同时的 tie-break 规则 | 低 |
| 怪物 AI | `monster_brain` 只给 ID | 技能选择评分函数、目标偏好权重 | 高 |
| 地图生成 | 全部生成参数（44 套） | 从参数到图的具体随机算法 | 中 |
| 奇物交互 | 设计表 CSV（策划草稿） | 运行期判定逻辑 | 中 |
| 压力崩溃 | 触发率与抗性阈值 | 崩溃/美德的具体判定流程 | 中 |

务实做法：不要追求二进制级还原，做**行为等价**——先让数值区间对得上，再用试玩修正排序细节。

## 9. 迁移到 Godot 的落点

| DD1 概念 | 数据来源 | Godot 实现建议 |
|---|---|---|
| 效果（effect） | effects.json | `Effect` Resource + 解释器（命令模式），不写死技能逻辑 |
| Buff | buffs.json | `BuffInstance` 挂在角色身上，按 `duration_type` 在阶段钩子里衰减 |
| 技能 | heroes.json → skills | `Skill` Resource，5 个等级是数组不是 5 个资源 |
| 站位掩码 | `launch` / `target` | 位运算：`mask & (1 << rank)`，天然契合整型 |
| 地牢生成 | dungeons.json → maps | 房间图用 `AStar2D` 不必要，直接邻接表 + DFS 生成 |
| 遭遇表 | encounters | 按权重 roulette 抽样，注意 `stall`/`named` 是特殊桶 |
| 光照 | rules.json → darkness | 纯数据表查表，`light` 值做区段映射 |
| 小镇循环 | quests.json / buildings | 状态机 + 存档用 `ResourceSaver` 存 Dictionary |

架构上最重要的一条：**把战斗逻辑写成不依赖节点的纯类**。DD1 的战斗正确性可以用数据验证（给定种子和输入，输出必须确定），逻辑与节点解耦后可以直接写单元测试，这在移植项目里能省掉大量调试时间。

## 10. 版权说明

本文档与 `data/` 下的数据均派生自受版权保护的游戏内容，仅可用于个人学习、机制分析与技术研究。若要发布任何作品，**规则可以重新实现，数值需要重新平衡，美术与音频必须原创**。

# M19 · 技能组（7 选 4）

> 一句话：`heroes.json` 里写着「每个英雄只能带 4 个技能」，这段数据躺了十九期没人读，
> 于是每个英雄 7 个技能全开、战斗底栏永远是 7 个按钮——原版最核心的 build 取舍从头到尾不存在。

## 1. 起点：又一条「数据在、无人读」

查证过程只有一步：

```bash
python -c "
import json; h=json.load(open('data/heroes.json'))
print([ (x['id'], x.get('skill_selection')) for x in h ][:3])"
```

```
[('abomination', {'can_select_combat_skills': False, 'number_of_selected_combat_skills_max': 7}),
 ('antiquarian', {'can_select_combat_skills': True,  'number_of_selected_combat_skills_max': 4}),
 ('arbalest',    {'can_select_combat_skills': True,  'number_of_selected_combat_skills_max': 4})]
```

15 个英雄里 14 个是 `max=4`，只有憎恶是例外（变身职业，7 个全开）。

`grep -r "skill_selection" src/` 的结果是 **No matches found**。
数据从 M0 就抽好了，代码一次都没读过。

这和 M13「61 份抽卡表在、没人加载」、M14「`heroes.json` 的 generation 段没读」
是同一类问题：**数据层太完整，反而让「什么还没接」不容易被看见**。
区别在于，前两次是内容不可见，这一次是**系统不可见**——
玩家根本不知道「技能可以选」这件事存在过。

## 2. 改了什么

### 规则层（`src/core/`）

| 文件 | 改动 |
|---|---|
| `skill_loadout.gd` | **新增**。技能组判定的共用件：`default_for` / `sanitize` / `max_slots` |
| `dd_db.gd` | 新增 `hero_skill_table()`，把 `skill_selection` 和技能 id 列表摊平成 `{hid: {can_select, max, ids}}` |
| `combatant.gd` | `setup_from_hero(..., selected: Array = [])`；新增静态 `filter_actions()` |
| `battle.gd` | `setup(..., loadout_by_id: Dictionary = {})` |
| `expedition.gd` | 新增 `hero_loadout`，随战斗装配传给 `Battle` |
| `campaign.gd` | roster 每个英雄多一个 `skills` 字段；`equipped_skills` / `set_skills` / `skill_slot_max` / `loadout_map` |

**为什么抽 `SkillLoadout` 而不是写在 `Campaign` 里**：这套判定有两个调用方——
元层（存/读档）和 bench（对照组）。两边各写一份，迟早会在某个边界上分叉，
然后 bench 数字和游戏内表现对不上，而那种不一致最难查（两边都不报错，只是答案不同）。
M15 把怪癖和饰品的判定抽成 `BuffRules` 也是这个理由。

### 默认值：三层都留了「全装」的退路

这是保住旧基线的关键，不能省：

1. `Combatant.setup_from_hero` 的 `selected` 默认空 → 全装（M1~M18 的行为）
2. `Battle.setup` 的 `loadout_by_id` 默认空字典 → 每个英雄都走第 1 条
3. `Expedition.hero_loadout` 默认空 → 走第 2 条

所以 `bench_expedition.gd` **不加参数时行为逐位不变**。要跑新路径才加 `--skills=loadout`。

### 表现层（`src/view/`）

- 城镇多一个「公会」入口（`S_GUILD`）
- 新屏：左侧名册 5 人，右侧 7 个技能卡，点一下切换；满 4 格时**不挤掉别人**，
  直接提示「先点掉一个」——M18 的出战屏用「挤掉最后一个」，被证明会让人以为点了没反应
- 技能卡两行：`✓ 惩击` / `＋ 圣枪`，下面一行是「类型 · 可从 N 位发动 · 目标 · 数值 · 等级」
- 加 `--guild` 启动参数，可以直接停在公会屏截图（同 `--prep`）

## 3. 默认组是本项目补的，不是原版

**原版没有「默认装哪 4 个」这张表**——它硬编码在游戏逻辑里，`.darkest` 数据里抽不出来。
`heroes.json` 只给了「上限 4」和「这个职业的 7 个技能都是什么」。

所以 `data/campaign.json` 里加了一段 `default_skills`，写明这是补的：

| 英雄 | 默认 4 个 | 取舍 |
|---|---|---|
| crusader | smite / stunning_blow / battle_heal / **inspiring_cry** | 输出 + 控制 + 治疗 + 减压，放弃守护（守护由 man_at_arms 演示） |
| highwayman | wicked_slice / pistol_shot / point_blank_shot / grape_shot_blast | 纯输出，含 AOE |
| vestal | judgement / dazzling_light / divine_grace / **gods_illumination** | 治疗 + 控制 + 减压 |
| plague_doctor | noxious_blast / plague_grenade / blinding_gas / battlefield_medicine | 毒 + 控 + 治疗 |
| man_at_arms | crush / defender / retribution / bolster | 坦克 + 守护 + 反击，保住 M10 的演示 |

没写到的英雄回退「技能表前 N 个」。改这段就是改默认 build，不用碰代码。

## 4. 对照数据

同一批路线（`--runs=30`，`standard` 预设，默认队伍 = crusader/highwayman/vestal/plague_doctor），
只切 `--skills`：

| 规格 | 技能 | 完成率 | 团灭率 | 压迫指数 |
|---|---|---|---|---|
| short Lv1 | all（7 个） | 0.967 | 0.033 | 0.287 |
| short Lv1 | loadout（4 个） | **0.900** | 0.100 | 0.547 |
| medium Lv3 | all（7 个） | 0.600 | 0.400 | 1.713 |
| medium Lv3 | loadout（4 个，第一版） | 0.333 | 0.667 | 2.407 |
| medium Lv3 | loadout（4 个，最终版） | **0.400** | 0.600 | 2.317 |

数据在 `bench/m19_{short,med}_{all,loadout,loadoutB}.json`。

**读法**：

- 新手图（short Lv1）只掉 6.7 个百分点，还能玩 —— 4 技能本身不是死路
- 中图（medium Lv3）掉 20 个百分点。但 medium Lv3 对 0 阶队伍本来就偏难
  （M18 已知限制：6 趟 5 团灭），4 技能只是把「偏难」推到「很难」
- 第一版默认组比最终版差 6.7 个百分点，差在**没带减压**：压迫 2.407 → 2.317。
  `inspiring_cry` 少一格，压力就压不住，崩溃连锁

**不能直接用这组数字评价玩家体验**：bench 用的是启发式评分 AI，
它逐动作挑当前分最高的技能，没有「攒着控场」「先奶再打」这类组合概念。
技能池从 7 收到 4，对它来说是「可选项少了 3 个」；对玩家来说是「必须做一次取舍」。
所以 0.400 是**AI 的下限**，不是玩家的上限。

## 5. 踩的坑

**`launch` / `target` 是 int 或 null，不是字符串。**

第一版直接 `str(lv.get("target", ""))` 再逐字符拆，结果：

- `target: null` → `str(null)` 在 Godot 里是 `"<null>"` → 显示成「打 `<、11、1、1、> 位`」
- `target: "@1234"` 的 `@` 是「己方」前缀，`~` 是「全体」前缀，都被当成数字位

修法是先判 `null` → 「自身」，再按前缀分流，最后只抽 1–4 的数字位。
现在的输出是「作用于己方全体」「打敌方 1、2 位」「自身」。

**「鼓舞呐喊」一开始被标成「治疗」**：它有 `heal: [1,1]`，但实际作用是减压。
技能组里最核心的取舍就是「这一格带奶还是带减压」，标错等于把决策做废了。
修法：先认 effect 里的 `stress`，再认 heal。

## 6. 复现

```bash
GODOT="D:/XT/godot/Godot_v4.7.2-stable_win64_console.exe"

# 全量断言（909 项，M19 新增 25 项）
"$GODOT" --headless --path . --script res://tests/run_tests.gd

# 两种技能组对照（同路线，只切开关）
"$GODOT" --headless --path . --script res://tests/bench_expedition.gd -- \
  --runs=30 --size=medium --level=3 --presets=standard --out=bench/m19_med_all.json
"$GODOT" --headless --path . --script res://tests/bench_expedition.gd -- \
  --runs=30 --size=medium --level=3 --presets=standard --skills=loadout \
  --out=bench/m19_med_loadoutB.json

# 三档自检
for s in "short 1" "medium 3" "long 5"; do set -- $s
  "$GODOT" --headless --path . -- --selftest --size=$1 --level=$2 --save=user://m19_$1.json
done

# 公会屏截图
"$GODOT" --path . -- --save=user://m19_guild.json --guild --shot=shots/m19_guild.png --shot-at=2
```

## 7. 没做的

- **技能描述文本**：原版的完整描述在 `.strings` 里，M0 的管线没抽。
  现在这一行是从数值反推的（「近战 · 可从 1、2 位发动 · 打敌方 1、2 位 · 命中 +85%」），
  能读懂「打谁、从哪打、伤害修正多少」，读不懂「它到底有什么特殊效果」。
- **技能解锁**：原版的技能要花钱在公会解锁（`guild` 建筑），现在 7 个默认全部可用。
- **营地技能**：`generation` 里写了 `number_of_class_specific_camping_skills = 2`，
  这块数据还在睡。
- **AI 不会组合技能**：这是 M19 暴露出来的真问题，也是 medium Lv3 掉 20 个点的根因。
  如果以后要拿 bench 数字代表玩家体验，得先做一个「会攒控场、会先奶」的 AI。

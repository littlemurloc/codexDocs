# M15 · 饰品

> 前三期（M13 奇物、M14 怪癖）补的都是「**被动接受**」：碰到什么就长什么。
> 饰品是这个游戏里第一个「**出发前我决定带什么**」的机制。
>
> 它也是最后一块「数据完全闭合、代码只算了个数」的地方：
> `loot_trinkets += (agg.get("trinkets", []) as Array).size()` —— 拿到就扔。

---

## 1. 起点：数据是完整的，代码只数了个数

`data/trinkets.json` 的三条硬指标全部过关：

| 项 | 数字 |
|---|---|
| 饰品 | 490 件 |
| buff 引用 | 1964 条 |
| 不同 buff | 943 个 |
| **指向不存在的 buff** | **0** |
| 未知 `rule_type` | **0** |

抽卡表早就按**稀有度**引用饰品，不按 id：

```json
{"type": "trinket", "data": {"rarity": "very_common"}}
```

10 档稀有度合计 182 件可掉落（去重后 196 件，含只在 specific 表出现的）。294 件
`kickstarter`（众筹支持者专享）从来没被任何表引用——这层筛选在原数据里就是对的，
保留它，别让赞助者礼品从普通宝箱里开出来。

而代码侧：

```gdscript
loot_trinkets += (agg.get("trinkets", []) as Array).size()
```

件数进了结算屏，东西没进游戏。

## 2. 规则层复用：抽出 BuffRules

饰品的 943 个 buff 用的是**和怪癖同一套** `rule_type` 词表，只多 6 种：

| 新规则 | 条数 | 判定依据 |
|---|---:|---|
| `in_rank` | 197 | `rule_data.float` 是 0 基站位号 |
| `at_deaths_door` | 56 | `hp == 0 && at_deaths_door` |
| `attacking_monster_type` | 22 | 目标的 `enemy_types` |
| `actorStatus` | 22 | 自身 `statuses` |
| `skill` | 3 | 技能 id |
| `monsterSize` | 1 | 目标 `size >= float` |

复制一份判定逻辑等于给自己埋一个必然漂移的副本（M13 的 `A` 表、M14 的槽位数字
都是这么出事的）。所以把 `QuirkLib` 里那套判定抽成 `BuffRules`，两边共用：

```
QuirkLib.rule_active()  -> BuffRules.rule_active()
QuirkLib.STAT_COMBAT    -> 保留，供自检
```

重构之后 713 项旧断言一条没变——这是「抽对了」的唯一证据。

### in_rank 的语义是怎么确认的

`rule_data.float` 只有 0 和 3 两种值，而 buff id 自带 `_FRONT` / `_BACKRANK`
后缀。所以它是**0 基站位号**（0=前排、3=后排），不是掩码、不是百分比。

这条如果猜错，197 条 buff 会全部错位——而且不会报错，只会让「只在前排生效」
的饰品在第四位生效。

## 3. 掉落解析：为什么必须用派生 rng

抽卡表的叶子只写稀有度，换成具体 id 要消耗一个随机数。而
`draw_n` 的抽取次数决定后面所有金币/传家宝/宝石的序列——多抽一次，
M13 量到的**全部**掉落基线就整体漂移。

所以走和 `MapGen._derive_seed` 同样的办法：只读 `rng.draw_count` 当盐，
另开一条流。

验证方式是硬的（`tests/test_trinket.gd`）：同一颗种子抽 30 次 A 表，
一次开着饰品解析、一次关掉，比对两条序列的**金币总额与 draw_count**：

```
金币完全一致（4903）
主序列消耗次数一致
```

bench 的完整基线对比更能说明问题——M14 与 M15 的默认基线**逐位一致**，
连 4903.125 这个小数都没动。

## 4. 元层：仓库和装备是两个容器

```
Campaign
├── trinket_store: Array        # 仓库，16 格（inventory.json 的 trinket_store.max_slots）
└── roster[hid].equipped: Array # 每人 2 格（hero_equipped_trinkets.max_slots）
```

**不合成一个列表**，理由是两件事会同时坏掉：

1. 装备中的件不占仓库格。合成之后「仓库满了但人身上还能戴」这个状态表达不出来。
2. 同名上限（`limit`）要按**总量**判。只看仓库会让「仓库两件 + 身上两件」绕过
   `limit=3`。

`owned_trinket_ids()` 就是为第 2 条存在的——它同时扫仓库和所有人身上。

### limit 的真实分布

| limit | 件数 | 含义 |
|---:|---:|---|
| 1 | 330 | 全库唯一 |
| 0 | 159 | 不限量 |
| 3 | 1 | 极少数特例（`dd_trinket`） |

我起先以为「稀有件应该唯一」，测试写完才发现 `swift_cloak` 的 limit 是 0
——**两派都大量存在**，不能凭印象定。

### 装备失败必须能被说出来

`add_trinket` / `equip_trinket` / `unequip_trinket` 都返回 `String`：
成功是 `""`，失败是原因（`limit` / `store_full` / `slots_full` /
`class_mismatch` / `not_in_store` / `no_such_slot`）。

拒绝会累加进 `trinket_refused`。M13/M14 各被「静默失败」拖掉半天工期，
这次一开始就把失败摆出来。

**仓库满时不允许卸装**：那一件会凭空消失。返回 `store_full`，让玩家先腾地方。

## 5. 战斗注入：第三条通道

`Combatant` 原本有两条：`buffs`（战斗内临时）和 `_quirk_active`（怪癖）。
饰品走第三条 `_trinket_active`，判定器同一个（`BuffRules`）。

为什么不塞进 `_quirk_active`：两个问题都要能单独回答——

- 「这人身上几条怪癖在生效」
- 「他戴的两个饰品生效了没有」

合成一条之后，卸一件饰品会把怪癖一起刷掉（`set_quirks` 会重置），
反之亦然。

### 三条通道的顺序

```
hp = base_hp
  → set_quirks()      # 可能乘 base_hp
  → set_trinkets()    # 也可能乘 base_hp
```

顺序换了功能不会错，但血量比例会因舍入差一点——基线会漂。所以写死，
并在注释里说明原因。

### max_hp 的两次乘

`max_hp` 不是「每帧可变」的属性，它改的是 `base_hp` 这个分母。所以：
**注入时一次性乘掉，并同比例缩放当前血量**（否则「戴上 +10% 生命」会顺手把伤治了），
之后 `filter_active` 必须跳过它，否则重复乘。

## 6. 中文名：数据里根本没有

这是本期唯一一处「数据有损」：

`trinkets.json` 的字段只有
`buffs / hero_class_requirements / id / limit / origin_dungeon / price / rarity`
——**没有 name**。`data/_raw/all_records.json` 里也没有 localization 段。
原游戏的饰品显示名没被抽出来。

做法是按 id 词根拼：

```
swift_cloak       → 迅捷 + 斗篷   =「迅捷斗篷」
ancestors_pen     → 先祖 + 笔     =「先祖笔」（of / the 跳过）
crow_wingfeather  → 乌鸦 + 翼羽   =「乌鸦翼羽」
padlock_1         → 挂锁          （数字后缀跳过）
```

英文 id 恰好是「形容词 名词」，与中文同序，拼出来能读。

**只覆盖可掉落的 196 件**（216 个词根，覆盖 100%）。294 件 kickstarter 永远
不出现在游戏里，为它们造译名是浪费。

认不出的 id **整件回退英文**，不做半中半英（「迅捷cloak」比全英文更难读）。
`DdTheme.trinket_name_coverage()` 供断言用：以后换数据包加了新词根，
那条断言会先红，而不是让界面默默变英文。

## 7. 界面

城镇屏右下加「饰品仓库 N/16」入口，进入独立状态：

- 左：4×4 仓库格，点一下选中（金框）
- 右：四个英雄各两个槽，点空格装、点有东西的槽卸
- 空槽的提示随状态变：没选中写「空」，选中了写「装这件」（绿字），阵亡写「已阵亡」

交互只做一个入口 `_toggle_slot()`，三种情况（装 / 卸 / 换）走同一段代码。
两套代码分叉是「装得上但卸不下来」这类 bug 的常见来源。

结算屏加一行「饰品 ×N」并在进不去仓库时报「另有 N 件没能带走」——
只报「掉了 2 件」而实际一件没进，玩家会以为存档坏了。

## 8. 对照实验

口径统一：40 趟 short/Lv3、`--presets=standard`、同种子序列。

### 8.1 干净 A/B：同一批装备，只切开关

| 组 | 完成率 | 压迫 | 死亡 | 崩溃 | 轮数 | 末血 | 末压 |
|---|---:|---:|---:|---:|---:|---:|---:|
| 完全不戴 | 0.875 | 0.698 | 0.72 | 0.75 | 32.8 | 0.603 | 76.2 |
| 戴了但关掉 | 0.875 | 0.698 | 0.72 | 0.75 | 32.8 | 0.603 | 76.2 |
| 戴了且生效 | **0.950** | **0.492** | **0.42** | 0.70 | 32.8 | 0.653 | **63.3** |

第二行与第一行**逐位相同**——证明注入路径本身不改任何东西，
所有差异都来自 buff 生效。这是比「和上一期比」更硬的证据。

### 8.2 随机 / 好 / 坏

| 组 | 完成率 | 压迫 | 死亡 | 轮数 | 末血 |
|---|---:|---:|---:|---:|---:|
| 随机 2 件 | 0.950 | 0.492 | 0.42 | 32.8 | 0.653 |
| 「好」2 件 | 0.900 | 0.610 | 0.68 | 30.1 | 0.669 |
| 「坏」2 件 | 0.875 | 0.740 | 0.70 | 30.7 | 0.567 |

**「好」组不如随机组**，这个反直觉的结果值得写下来：

我的「好坏」判据是拍的（速度/暴击/命中/伤害倍率算正分，受压算负分），
而随机池里恰好有一批「减受压」的件——它们在 8.1 里贡献了 13 点末压差。
换句话说，**我拍的「好」不等于数据里的「强」**。

所以这一张表只能说明「方向能分开」，不能说明「最优配置是哪套」。
真正可信的是 8.1，因为那是同一批装备的开关对照。

## 9. 已知限制

- **自然掉落率很低**：中图约 **1.12 件/趟**（200 趟模拟，每趟 24 抽）。
  短图约 0.6 件/趟，也就是打两趟才看到一件。而 `trinkets.base.starting` 是空数组
  ——**开局一件都没有**。前期会很空，和 M14 的怪癖是同一类问题：
  机制完整，出现率是内容决策。
- **312 条 buff 没有承载**（15.9%）：`hp_heal_percent`、`resolve_check_percent`、
  `stun_chance`、`damage_received_percent`、`activity_side_effect_chance` 等
  属于城镇/营地/决心检定/眩晕概率，本作没有对应系统。
- **27 条规则不可判**（1.4%）：`in_camp` 38 条是主因。
- **没有商店**。`price` 读进来了但没用到——金币目前只有升级一个出口，
  饰品是纯掉落。
  **已被 M16 修订**：现在有城镇商店（6 格货架，按趟刷新），
  也能卖仓库里的件（买价的 10%）。见 [M16_TOWN_ECONOMY.md](M16_TOWN_ECONOMY.md)。
- **饰品不能卖、不能熔**。仓库满了只能丢（计入 `trinkets_dropped`）。
  **已被 M16 修订**：可以卖，`sell_gold_value` 用买价的 10% 折算。
- **`origin_dungeon` 没接**：它标记「这件出自哪座地牢」，本可以先影响掉落池，
  但那会改变 M13 量到的难度梯度，需要单独一期验证。

## 10. 复现

```bash
GODOT="path/to/Godot_v4.7.2-stable_win64_console.exe"

# 全量断言（791 项）
"$GODOT" --headless --path . --script res://tests/run_tests.gd

# 干净 A/B：同装备，开关对照
"$GODOT" --headless --path . --script res://tests/bench_expedition.gd -- \
  --runs=40 --size=short --level=3 --presets=standard --trinkets=2 --trinket-pick=mix
"$GODOT" --headless --path . --script res://tests/bench_expedition.gd -- \
  --runs=40 --size=short --level=3 --presets=standard --trinkets=2 --trinket-pick=mix --no-trinket

# 默认基线（应为 0.875 / 0.698 / 0.72 / 32.775 / 0.6026 / 76.2443 / 4903.125）
"$GODOT" --headless --path . --script res://tests/bench_expedition.gd -- \
  --runs=40 --size=short --level=3 --presets=standard --out=bench/m15_base.json

# 端到端（三档）
"$GODOT" --headless --path . -- --selftest --size=short --level=1
```

对照数据在 `bench/m15_*.json`：

| 文件 | 内容 |
|---|---|
| `m15_base.json` | 默认（没人戴饰品） |
| `m15_ab_off.json` | 戴了但 `--no-trinket` |
| `m15_mix2.json` | 每人 2 件，随机 |
| `m15_best2.json` | 每人 2 件，按我拍的好坏判据挑「好」 |
| `m15_worst2.json` | 同上挑「坏」 |

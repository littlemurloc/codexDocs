# M12 — 召唤

> 59 个召唤效果、35 只怪，从 M0 就在库里。M1~M11 期间 `effect_resolver`
> 一直把它们落到 `unsupported = "summon"` —— 也就是说，收藏家、死灵法师、
> 溺亡船长这些以「叫人来」为核心威胁的敌人，在战斗里等于一群只会平砍的普通怪。
> 这一期把它们接通，并处理接通之后才暴露的三个问题。

---

## 一、数据全貌

| 项 | 数量 | 说明 |
|---|---|---|
| 带 `summon_monsters` 的效果 | 59 条 | 覆盖 35 只怪 |
| 带 `summon_limits` | 22 条 | 其余**没有上限** |
| 带 `summon_ranks` | 13 条 | 落点，见 §2 |
| 带 `summon_can_spawn_loot` | 55 条 | 召唤物掉不掉战利品 |
| 带 `summon_erase_data_on_roll` | 3 条 | 抽走即移除 |
| 带 `summon_does_roll_initiatives` | 9 条 | 本项目未用，见 §6 |

典型条目：

```json
{"name": "Summon Fuseman 1", "target": "performer", "summon_count": 1,
 "summon_monsters": "brigand_fuseman_A", "summon_chances": 1.0,
 "summon_limits": 1, "summon_ranks": 4, "summon_can_spawn_loot": true,
 "on_hit": true, "on_miss": true, "apply_once": true}
```

---

## 二、三个必须先搞对的数据形态

### 2.1 `summon_monsters` 单值时是字符串

```json
"summon_monsters": "brigand_fuseman_A"          // 单值
"summon_monsters": ["a", "b", "c", "d"]         // 多候选
```

单值写成字符串这一点，从 Python 或 GDScript 侧遍历都会把它拆成单字符。
M11 已经在同类问题上踩过一次，所以解析层统一摊平成数组，下游一律不用再判类型。

### 2.2 `summon_limits` / `summon_ranks` / `summon_chances` 是与候选**并行**的数组

```json
"summon_monsters": ["brigand_cutthroat_A", "brigand_fusilier_A"],
"summon_limits":   [1, 1],
"summon_ranks":    [1, 4],
"summon_chances":  [0.5, 0.5]
```

「第二个候选拿第一个候选的上限」这种事不会报错，只会让行为悄悄变成另一个东西，
所以解析层用 `_aligned()` 强制对齐：能取多少取多少，不足的填默认值。

### 2.3 `summon_ranks` 是**位掩码**，不是槽位号

这是这一期最容易搞错的一处。第一版按「1 基槽位」实现，理由是值域恰好是 1~4。
但 `brigand_sapper` 写的是 **12**——按槽位号无解（阵型只有 4 格）。

按位掩码解释全部自洽：

| 数据 | 二进制 | 含义 |
|---|---|---|
| `4` | `0b0100` | 第 3 位 → 3 号位 |
| `12` | `0b1100` | 第 3、4 位 → 3、4 号位 |
| `[1, 4]` | `0b0001`, `0b0100` | 割喉贼 1 号位、火枪手 3 号位 |

最后一行是决定性的：割喉贼是近战、火枪手是远程，位掩码解释给出的站位
（前 / 后）在语义上完全成立；槽位号解释会得到「1 号位 / 4 号位」，
而 4 号位根本不存在于他们能用的阵型里。

**置信度：高。** 依据是这三条数据互相印证，不是猜的。

---

## 三、实现：一个单位怎么被放进去

### 3.1 阵型上限 4 是硬约束，不是设计选择

技能的 `launch` / `target` 是 4 位掩码（`@1234`），第 5 格**永远无法被任何技能
指定为目标**。允许第 5 个敌人存在，等于造一个既打不到人、也不会被打的摆设。
所以 `MAX_SLOTS = 4`。

### 3.2 尸体让位

这是本项目特有的一条。DD1 里尸体不占位，所以「召不出来」只有
「4 个敌人都活着」时成立。这里的尸体一直占着格子（M1 的遗留，从没改过），
如果不让位就会出现：

> 打死了两个，场上还剩 2 个活的和 2 具尸体——却没有空位召唤。

这既比 DD1 严苛，也违反直觉。所以槽位优先级是：

1. 掩码指定的位置，且那里躺着尸体
2. 掩码指定的位置，且正好是下一个空位
3. 任何躺着尸体的格子
4. 阵型还没满 → 往后接

第 3、4 条是**兜底**：数据里的「3 号位」在场上只有 1 个怪时永远不成立，
因为掩码对不上就拒绝召唤，会让大部分召唤永远不触发——那比放错位置糟得多。

尸体会被**替换**，不是挪走：阵型是一条没有空洞的线（`_relayout` 直接把
rank 写成下标），不存在「给尸体换个位置」这回事。

### 3.3 回合调度不用改

`begin_round()` 里 `_order = build_order(all_units(), ...)` 是一次**快照**。
召唤发生在回合中途，新单位不在本轮的 `_order` 里，下一轮重新遍历时自然进入。
这正是「召唤物当轮不动」的语义，不需要任何额外代码。

数据里的 `summon_does_roll_initiatives`（9 条）因此不需要消费——我们天然
每轮重掷先攻。

### 3.4 光照修正要手动补

`set_environment()` 是在开战时把 `initiative_bonus` 一次性写进单位的，
中途加入的单位拿不到那次写入。`build_spec` 里的伤害/命中修正是每击现读 `env`，
所以那部分自动继承，只有先攻要补一行。

---

## 四、AI 估值：没有它，前三节全白做

M11 已经证明过一次：解析通了不等于实现。这一期是同一个剧本。

接通的**第一天**，六只召唤怪的召唤技能实测分数：

| 怪 | 召唤技 | 分数（接通后、加估值前） |
|---|---|---|
| brigand_cannon_A | `cannon_summon` | **0.00** |
| collector_A | `collect_call` | **0.00** |
| cyst_D | `beholder_summon` | 1.00 |
| ectoplasm_A | `summon_slime` | 0.85 |

原因很直接：它们的 `atk = 0`、`dmg = [0, 0]`，`_score` 里没有任何一条给它们加分。
实跑 12 场，召唤次数 **0**。

### 4.1 估值口径

**按被召唤物的血量折算。** 一个敌人值的是「一块要多打掉的血 + 之后每回合多一次攻击」，
而这两项都随血量单调增长，所以用血量做代理：

```
value = 1.5 + hp / 4.0        # hp 12 ≈ 4.5 分，约等于一次平砍
```

不写死一个常数，这样换数值包、换怪时估值自动跟着变。

### 4.2 召唤**不乘命中率**

数据里 59 条召唤效果全是 `on_hit: true, on_miss: true`，也就是命中与否都会召唤。
所以 `summon_bonus` 加在 `bonus *= hit` **之后**。乘命中率会让低命中的召唤者
永远不去召唤，而它实际照样召得出来。

### 4.3 三个分支都要带上它

`_score` 有多条提前 `return`：治疗、守护、纯功能技。任何一条漏了 `summon_bonus`，
那个分支里的召唤技就永远是 0 分。`brigand_sapper` 的 `sapper_guard` 同时带
「守护 + 召唤」，正是这种混合情况——它现在是 `gs + summon_bonus`。

### 4.4 估值必须和实现用同一套判定

`_eval_summon` 里的「能不能召」必须和 `_pick_summon_index` / `summon_slot` 一致。
不一致的后果**不是报错**，而是 AI 反复选一个注定被拒的技能，表现成
「这只怪有技能却在空过」——不读代码查不出来。

---

## 五、上限：一条不得不补的规则

### 5.1 问题

59 条里只有 22 条带 `summon_limits`。剩下的**没有任何上限**，只能靠 4 格兜底。
而 4 格兜底挡不住循环：死一个就让位，于是「打死一个又补一个」。

`ectoplasm_A` 是这个问题的极端形态——它召的是**它自己**：

| 实现 | 轮数 | 召唤/场 |
|---|---|---|
| 无任何上限 | 22.1 | 24.7 |
| 每施法者 4 次 | 16.3 | 11.8 |
| **同种上限 2** | **23.7** | **26.4** |
| **同种 2 + 阵营总量 4** | **9.73** | **3.87** |

第三行值得单独说：只加「同种在场最多 2 个」**反而更糟**。因为同种数量始终卡在
2 个上下震荡——打死一个，剩下那个立刻补回来，阵型长度不再增长，但
「要打掉的总血量」无限延伸。

### 5.2 两条闸

```gdscript
DEFAULT_SUMMON_LIMIT     = 2   # 同一个 monster_id 在场最多几个
MAX_SUMMONED_PER_BATTLE  = 4   # 一个阵营整场累计最多召出几个
```

它们挡的不是同一件事：

- 第一条挡「同一种怪占满阵型」
- 第二条挡「死一个补一个」的震荡循环

**这是补充规则，不是数据。** 取 4 的语义是「召唤最多补充一整支队伍」，
超过这个量只剩重复劳动，不再产生新的战术压力。

**数据优先**：有 `summon_limits` 的用数据的（炮船 = 1，意思是「只能有一门炮灰」），
只有缺失时才退到默认值。反过来做会覆盖掉那些明确写了上限的条目。

### 5.3 这条规则改了什么（30 趟配对）

| 预设 | 完成率（有上限 → 无上限） | 压迫指数 |
|---|---|---|
| lenient | 0.700 → 0.433 | 1.197 → 2.030 |
| standard | 0.533 → 0.367 | 1.903 → 2.343 |
| tight | 0.067 → 0.067 | 3.097 → 3.083 |

上限确实在削弱召唤——不是因为「怪变少了」，而是因为无上限时怪物把回合
大量花在召唤上，战斗被拖长，压力与光照一起烧穿。

---

## 六、顺手修掉的一个健壮性 bug

`effect_resolver.apply` 里原有一行：

```gdscript
var allow: bool = bool(e.get("on_hit", false)) if hit else bool(e.get("on_miss", false))
```

数据里 `on_miss` 有 **3 条是列表**，`on_hit` 全部是 bool。这行代码在两种情况下会炸：

- `bool(null)` → GDScript 4 抛 `Nonexistent 'bool' constructor`
- `Array == bool` → 直接是非法运算

之前没炸，只是因为走到这条路径的技能恰好都写了 true/false。M12 让更多技能
被真正使用后立刻暴露。现在统一走 `_flag(v)`：只有显式 true 才算真。

---

## 七、数据

### 7.1 默认基线：逐位不变

`faithful` 数值包、默认队伍、200 场：

```
轮数 4.0962   终局血量 0.9410   命中 0.8052
暴击 0.0716   溢出 0.1215       压力 19.3123
```

与 M11 **完全相同**。默认那套遭遇（`cultist_brawler` / `cultist_witch`）
里没有一只会召唤的怪，所以 M12 对默认基线是纯增量。

### 7.2 单场：机制确实在工作（60 场）

| 场景 | 轮数（开 → 关） | 终局血量（开 → 关） | 召唤/场 |
|---|---|---|---|
| `necromancer` | 5.45 → 4.08 | 0.718 → 0.736 | 2.12 |
| `drowned_captain` | 6.22 → 5.35 | 0.897 → 0.845 | 1.20 |
| `ectoplasm_split` | **9.73 → 1.97** | **0.700 → 0.944** | 3.87 |
| `cannon_no_summon` | 4.62 → 4.62 | 0.177 → 0.177 | **0.00** |

最后一行是**反对照**：炮船有召唤技，但 `cannon_boom` 的期望伤害是 9–27，
估值远高于召唤一个 5 血炮灰。它一次都不召——这不是没实现，是 AI 判断对了。

`drowned_captain` 那一行反直觉：**召唤之后玩家反而更安全**（0.897 vs 0.845）。
因为 `all_hands` 是纯功能技（伤害为 0），怪物花一回合召唤，就等于少打一次，
而它召来的锚并不强。这条数据本身就说明「召唤不等于变强」。

### 7.3 远征：显著变难（60 趟，medium Lv3，同路线对照）

| 预设 | 完成率（开 → 关） | 差 | 压迫指数（开 → 关） |
|---|---|---|---|
| lenient | 0.750 → 0.883 | **−0.133** | 1.058 → 0.655（+0.403） |
| standard | 0.650 → 0.750 | **−0.100** | 1.637 → 1.328（+0.309） |
| tight | 0.083 → 0.217 | **−0.133** | 3.150 → 2.867（+0.283） |
| brutal | 0.000 → 0.000 | ±0 | 3.280 → 3.315（−0.035） |

压力终值（lenient）：**104.64 vs 75.60**，差近 30 点。终局血量 0.388 vs 0.513。

**方向和 M11 正好相反。** M11 的位移让玩家更轻松（完成率 +0.033），
因为位移的估值把 AI 从「高压力 + 高 DOT」拉到了「高直伤」，而压力会跟你
走到远征结束、直伤打完就没了。召唤没有这个副作用：它直接增加敌军规模。

两个机制放在一起看才有意思：同一套 AI，一个机制让路更好走，另一个让路更难走，
而两者的代码在同一个 `_score` 里。

---

## 八、已知局限

- **`summon_can_spawn_loot` 未消费。** 当前战利品不按怪物数量结算，
  所以这条字段暂时没有影响面。一旦战利品改成按敌人算，它必须接上。
- **`summon_does_roll_initiatives` 未消费。** 见 §3.3，我们的语义天然是
  「下轮重掷」，不需要这个开关。
- **`summon_rank_is_previous_monster_class` 未实现**（4 条）。
  它要求「召唤物站到上一个死者的位置」，和尸体让位规则冲突，暂不处理。
- **`summon_erase_data_on_roll` 只做了 per-action 去重**（3 条），
  不是完整的「从全局候选池移除」。
- **默认上限是我加的规则**（§5），不是数据。它压掉了 ectoplasm 从 22 轮
  到 9.7 轮，但 9.7 仍然远高于基线 4.1——「分裂型怪物」在无数据约束下
  依然偏重。要更接近 DD1，得在数值层给这类怪单独的 `summon_limits`。
- **英雄没有召唤技能**，所以这个机制目前完全是怪物侧。
- **洗位仍无实际效果**（M11 遗留，见 M11 §8）。

---

## 九、怎么跑

```bash
GODOT="D:/XT/godot/Godot_v4.7.2-stable_win64_console.exe"

# 全量断言（含召唤的 45 项新断言）
"$GODOT" --headless --path . --script res://tests/run_tests.gd

# 默认队伍：应当与 M11 逐位相同（4.0962）
"$GODOT" --headless --path . --script res://tests/bench_battle.gd -- \
  --runs=200 --data=balance/faithful --out=bench/m12_faithful.json

# 召唤专项（4 个场景：死灵 / 船长 / 史莱姆 / 炮船反对照）
"$GODOT" --headless --path . --script res://tests/bench_battle.gd -- \
  --runs=60 --data=balance/faithful --out=bench/m12_probe.json

# 对照：关掉召唤（等于 M11 行为）
"$GODOT" --headless --path . --script res://tests/bench_battle.gd -- \
  --runs=60 --data=balance/faithful --no-summon --out=bench/m12_probe_nosummon.json

# 远征：召唤开
"$GODOT" --headless --path . --script res://tests/bench_expedition.gd -- \
  --runs=60 --size=medium --level=3 --data=balance/faithful --out=bench/m12_exp.json

# 远征：关掉召唤（同路线对照）
"$GODOT" --headless --path . --script res://tests/bench_expedition.gd -- \
  --runs=60 --size=medium --level=3 --data=balance/faithful --no-summon \
  --out=bench/m12_exp_nosummon.json

# 远征：关掉默认上限（看「没有闸门会怎样」）
"$GODOT" --headless --path . --script res://tests/bench_expedition.gd -- \
  --runs=30 --size=medium --level=3 --data=balance/faithful --no-summon-limit \
  --out=bench/m12_exp_nolimit.json

# 端到端自检（会打印「SELFTEST 召唤 成功=N 失败=M」）
"$GODOT" --headless --path . -- --selftest --size=medium --level=3 --save=user://t12.json
```

自检里的召唤**只报数不判 PASS**：路上有没有召唤怪由地图决定，不是玩家能选的，
和 M11 的位移同一条规矩。假装它能判 PASS，等于给自己一个永远不会红的绿灯。

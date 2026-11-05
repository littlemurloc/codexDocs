# M11 · 怪物位移：三层断点，一次接通

M9 的「已知局限」里有一句：

> **只有英雄能移动，怪物不会**。数据分析显示没有任何怪物技能带 push/pull，
> 它们的 `move_skill` 也没解析——所以敌人打了这么久，从来没打乱过你的阵型。

**这句话是错的。**

## 一、先纠正一个错误结论

真实数据：

```
552 个怪物技能里，46 个带位移效果，分属 41 只怪物
  push           37 条   Push 1A..3F / Bolo Push / Gargoyle Lash Push ...
  pull           21 条   Pull 1A..3F / Grouper Pull / Reaver Ball ...
  shuffletarget  14 条   Shuffle Target / Shuffle Self / Disorient 1..6
  shuffleparty    6 条   Shuffle Party 1..5
```

`cultist_witch_C` 带着 `Pull 2E` / `Push 2E`，`fishman_crabby_A` 的
`pincer_smack` 是 3–7 伤 + 眩晕 + `Push 3`，`shambler_A` 的 `shambler_howl`
直接洗你全队。这些一直都在。

所以「怪物不会位移」不是数据缺失。真实原因有三层，**每一层单独修都不够**。

## 二、第一层：抗性字段从 M0 就在，没人读

`monsters.json` 的每个怪都有 `move_resist`，`combatant.setup_from_monster`
在 M1 就把它写进了 `resistances`：

```gdscript
var resist_keys: Array = ["stun_resist", "poison_resist", "bleed_resist",
	"debuff_resist", "move_resist", "death_blow_resist"]
```

然后没有任何一处位移逻辑读它。`move_resist` 和 M10 的 `ignore_guard` 一样，
是**解析了但从来没人消费**的字段。

数值分布值得单独说：

| | 范围 | 说明 |
|---|---|---|
| 英雄 | 0.2 ~ 0.4 | 默认队伍：十字军 0.4、强盗 0.3、修女 0.3、瘟疫医生 0.2 |
| 怪物 | 0 ~ 3.4 | 原始值超过 0.95 的在 `resistance()` 里被 clamp，表示「基本推不动」 |

怪物有 4 只 `move_resist = 0`，也有 1 只 10.0、6 只 3.0。也就是说数据里
**位移抗性是有梯度的设计**——有些怪天生推不动。这也侧面证明这机制本来该存在。

### 一个必须写对的细节：`res > 0` 的短路

```gdscript
if e.has("push") or e.has("pull"):
	var move_res: float = t.resistance("move")
	if move_resist_on and move_res > 0.0 and rng.next_float() < move_res:
		out["resisted"] = "move"
		return out
	out["move"] = int(e.get("push", 0)) - int(e.get("pull", 0))
```

`move_res > 0.0` 不是优化，是**正确性**。

不判的话，抗性为 0 的单位也会白消耗一次随机数——逻辑上完全等价（0 永远不抵抗），
但整个 rng 序列错位一格，**所有下游随机全部改变**。表现是「改了个不生效的功能，
基线却变了」，而且查不出来。

这条被单测钉住了（`tests/test_move.gd` 的「抗性 0 时推一次不改变 rng 序列」）。

## 三、第二层：洗位是第三批死代码

`shuffletarget` / `shuffleparty` 落到 `effect_resolver._apply_one` 的兜底分支，
返回空字典。和 M9 的位移、M10 的守护完全同一个形状：

```gdscript
if e.has("shuffletarget") or e.has("shuffleparty"):
	var shuf_res: float = t.resistance("move")
	if move_resist_on and t != attacker and shuf_res > 0.0 and rng.next_float() < shuf_res:
		out["resisted"] = "move"
		return out
	out["shuffle"] = "team" if e.has("shuffleparty") else "target"
	return out
```

两个键的值都是 `null`，只有「有没有」这一个信息：

- `shuffletarget` → 把**这一个单位**随机换到己方另一个槽
- `shuffleparty` → 把**整个阵营**打乱

`t != attacker` 这一条是给 `Shuffle Self` 用的：数据里它的 target 是 `performer`，
怪物自己乱跳。自己抖一下还要过自己的抗性，等于「这只怪有 95% 概率拒绝自己跳」，
显然不是原意。

### 洗位只在活人之间换

尸体仍然占格（M1 的遗留），但洗位要把尸体排除掉：

```gdscript
func _alive_slots(side: String) -> Array:
```

否则打死的怪会在阵型里滑来滑去，看起来像又活了一次。

### 消费顺序有个坑

`apply_effects` 原来是：

```gdscript
var delta: int = int(ev.get("move", 0))
if delta == 0:
	continue      # ← 洗位结果里没有 move 字段，会在这里被静默跳过
```

洗位必须在 `delta == 0` 之前分流。改完是：

```gdscript
var shuf: String = str(ev.get("shuffle", ""))
if shuf == "team":
	for mv2 in shuffle_team(u.side): ...
	continue
if shuf == "target":
	var mv3: Dictionary = shuffle_unit(u)
	...
	continue
var delta: int = int(ev.get("move", 0))
if delta == 0:
	continue
```

## 四、第三层：真正的原因——AI 不认识位移

前两层修完，怪物**依然一次都不推人**。

我对着 `cultist_witch_C` 把三个技能的分数打出来：

```
cultist_pull         vs 修女  score = 5.69
cultist_push         vs 十字军 score = 5.13
cultist_incantation  vs 修女  score = 7.20
```

`_score` 的 effect 估值只认识这五样：

```gdscript
if e.has("stun"):      bonus += 3.0 * success
if e.has("riposte"):   bonus += duration * 0.3 * rmult
if e.has("stress"):    bonus += stress * 0.35 * base_chance
if e.has("dotBleed") / e.has("dotPoison"): ...
```

**push / pull / 洗位一条都没有。** 所以带位移的技能永远输给同伤害但附带压力的技能。
`cultist_incantation` 的 7.20 里有 5.6 分来自 `+20 压力`——数据里的 `stress: 20`。

**这才是「怪物不会推人」的真正原因：不是数据没有，不是解析没有，是 AI 不选。**

修法是给位移估值：

```gdscript
if move_value_enabled and (e.has("push") or e.has("pull")):
	var push_delta: int = int(e.get("push", 0)) - int(e.get("pull", 0))
	var team: Array = party if target.side == Combatant.SIDE_PARTY else enemies
	var land: int = clampi(target.rank + push_delta, 0, team.size() - 1)
	var real_ranks: int = absi(land - target.rank)
	if real_ranks > 0:
		bonus += MOVE_VALUE_PER_RANK * float(real_ranks)
			* (1.0 - target.resistance("move")) * base_chance
```

两个设计点：

1. **按「实际能挪几格」算，不按数据里写的格数。** 一个已经在 4 号位的人被
   push 2 其实纹丝不动，给它记 2 格的分会让 AI 一直去推边角。
2. **乘「推得动」的概率**（`1 - move_resist`）。高抗性目标不值得推。

洗位用固定值 `SHUFFLE_VALUE`，因为它不保证把人送到坏位置——它值的是「打乱」，
不是「安置」。同样要判「活人 ≥ 2」。

## 五、唯一一个不是数据给的数

`MOVE_VALUE_PER_RANK = 1.0` 和 `SHUFFLE_VALUE = 1.5` 都**不来自数据**，
DD1 也没有等价字段。这一点必须说清楚，因为项目其它所有参数都能追到源文件。

依据：一个技能的分差通常在 2~4 分之间（伤害 1.6 + 一个附带效果 1.7~3.6）。
「挪一格」值 1 分，意味着「推 2 格」约等于一个中等技能的一半——这是能自圆其说的
量级，而不是「调到能赢为止」。

它也确实不是「调到能赢」：`cultist_witch_C` 在 1.0 下**仍然不选** push/pull，
因为它的 `+20 压力` 值 5.6 分。这个结果是**对的**，见第六节。

## 六、到底有没有用：单场有效，远征被副作用盖过

### 1. 默认遭遇：一个数都没动

| 指标 | M10 | M11 |
|---|---:|---:|
| 战斗轮数 | 4.0962 | **4.0962** |
| 终局血量 | 0.9410 | **0.9410** |
| 命中率 | 0.8052 | **0.8052** |
| 暴击率 | 0.0716 | **0.0716** |
| 溢出占比 | 0.1215 | **0.1215** |
| 终局压力 | 19.3123 | **19.3123** |

逐位相同。原因很直接：默认那套遭遇（`cultist_brawler` + `cultist_witch`）里
**没有一只怪会真的用位移技能**，而默认队伍四个英雄**一个位移技能都没有**——
所以抗性判定一次都没触发，rng 序列一格都没动。

`M11 是纯增量`，和 M7/M8/M10 同一个形状。

### 2. 换一批带位移的怪：位移真的伤到玩家

`bench_battle` 里新增了 `move_probe` 三组专项遭遇（不进 summary，否则会污染基线对比）：

| 场景 | 位移/场 | 洗位/场 | 被抵抗/场 | 终局血量 |
|---|---:|---:|---:|---:|
| `crabby_push3`（pincer_smack: 3–7 伤 + 眩晕 + push 3） | 2.06 | 0 | 1.49 | **0.580** |
| `shambler_shuffle`（howl: 1 伤 + 10 压力 + 洗全队） | 0 | 13.25 | 2.00 | 0.958 |
| `witch_no_push`（有位移技但 incantation 太强） | 0 | 0 | 0 | 0.982 |

同场景、只关掉位移估值做对照：

| | 完成轮数 | 终局血量 | 位移/场 |
|---|---:|---:|---:|
| 估值开 | 9.82 | **0.580** | 2.06 |
| 估值关 | 11.51 | **0.830** | 0 |

**位移让玩家血量少了 0.25。** 这是 M11 之前完全不存在的一个伤害维度：
螃蟹把 1 号位推到后面，原本在 4 号位躲着的修女 / 瘟疫医生被顶到前面挨打。

### 3. 抗性挡掉了 42% 的位移，但没救回血量

| | 位移/场 | 终局血量 |
|---|---:|---:|
| 抗性开 | 2.06 | 0.580 |
| 抗性关 | 3.42 | 0.601 |

位移次数少了 40%，血量只差 0.02。说明**位移有边际递减**：推两次和推三次，
最后那个阵型已经乱了，再推意义不大。

### 4. 洗位：一次都没落地

`shambler` 每场洗 13.25 次（3 人队，每轮洗一遍还多），但：

- 关不关估值都是 13.25 次——`shambler_howl` 自带 `+10 压力`，本来就会被选中
- 终局血量 0.958，抗性开 / 关**完全相同**

结论：**洗位在这套数值下没有可测效果。** 它把阵型重排，但英雄的技能大多
不依赖精确站位（或者被洗到后面的人会自己走回来），所以「打乱」没有转化成
「更疼」。洗位是一个**为了完整而接通的机制**，不是有效的战术。

### 5. 远征：反直觉的结果——玩家变轻松了

120 趟、medium / Lv3、同路线同种子，只开关位移估值：

| 预设 | 完成率（开 → 关） | 差 | 压迫指数（开 → 关） | 差 |
|---|---:|---:|---:|---:|
| lenient | 0.883 → 0.850 | **+0.033** | 0.706 → 0.807 | **−0.102** |
| standard | 0.767 → 0.733 | **+0.033** | 1.336 → 1.532 | **−0.197** |
| tight | 0.200 → 0.183 | +0.017 | 2.937 → 2.978 | −0.041 |
| brutal | 0.008 → 0.008 | ±0 | 3.321 → 3.328 | −0.007 |

**怪物学会推人之后，玩家反而更容易通关、压力更低。** 60 趟和 120 趟方向完全一致，
四个预设的压迫差单调递减（越难差距越小），不像噪音。

这个结论需要解释，否则看起来像弄反了：

```gdscript
if e.has("push") or e.has("pull"):
	bonus += ...
```

估值只加在**带位移的技能**上。而带位移的技能往往同时是「高直伤」技能
（`pincer_smack` 3–7 伤），它们原本竞争不过的是**低直伤 + 高 DOT** 的技能
（`the_pinch` 1–1 伤 + 流血；`cultist_incantation` +20 压力）。

位移加成把 AI 从 DOT 拉到了直伤，于是：

- 直伤是**一次性的**，打完就没了
- DOT 和压力是**累积的**，会一直跟到远征结束

所以是**副作用**让玩家轻松了，不是位移本身。要验证这一点有个现成的证据：
`witch_no_push` 那组三个开关下结果**完全一致**——估值只在「带位移的技能真的
被选中」时才产生作用，不会外溢到别的技能。

**这说明 `MOVE_VALUE_PER_RANK = 1.0` 这个估值确实会改变 AI 的技能偏好。**
它是有效的，但它的净效果和「让怪物更凶」是两件事——这两件事被同一行代码
绑在一起了。要分开，得给 DOT 和压力的估值也重新校准，那是数值层的事。

## 七、踩到的坑

**1. 探针把字符串 effect 按字符拆了。** `effect` 单值时是字符串不是数组
（README 数据约定第 2 条），我用 Python 遍历时写出了
`['B','l','e','e','d',' ','1']` 这种结果，一度以为数据抽取坏了。

**2. 数组下标不等于单位身份。** 测「末位的人有没有被顶到前面」时先记了
`pd_start = b.party[3].rank`，战斗后读 `b.party[3].rank` —— 这是**两个不同的人**，
阵型一变就对不上。必须 `var pd: Combatant = b.party[3]` 抓住引用。
这和 M10 里 `remove_at + insert` 之后 `enemies[1]` 就是被推的人本身是同一类错。

**3. 忘了把开关拨回来。** 测「抗性越高位移越不值钱」时，上一段为了拿对照分数
把 `move_value_enabled` 设成了 false，忘了恢复，于是两段都算出「不含位移」的分数，
断言成了 `4.693 > 4.693`。**开关是全局可变状态，测试里任何一次拨动都要还回去。**

**4. 洗位被 `delta == 0` 静默吞掉。** 见第三节。洗位结果里没有 `move` 字段，
走原来的 `if delta == 0: continue` 会被直接跳过，而且不报错。

**5. 自检的出手次数不稳定。** 短图连跑三次得到 12 / 58 / 27 次出手，一度以为
是估值改动影响了英雄行为。实际是自检路线本身带随机性（不走固定种子）——
**这个数字不能用来对比两次改动。**

## 八、已知局限

- **英雄一个位移技能都没有。** 15 个英雄里没有一条 push/pull，所以「推怪」
  这件事玩家做不到——位移目前完全是怪物单向的特权。数据里英雄确实有少数
  带位移的技能（比如 `bellow`），但它们不在默认队伍的技能表里。
- **怪物不会主动「调整站位」。** 它们只会被推拉和洗位，不会为了追人而移动。
  `move_skill` 仍然只对英雄解析。
- **洗位没有实际效果**（第 6.4 节）。接通了，但在当前数值下不产生影响。
- **位移估值和 DOT 估值耦合。** 给位移加分会让 AI 从 DOT 转向直伤，
  两者共用同一个 `_score`，目前无法分离（第 6.5 节）。
- **位移不改「谁应该站哪」的判断。** AI 不会因为阵型被打乱而去「重新找位置」，
  只有当前技能放不出来时才会移动。
- **尸体不参与洗位但不让位。** 和 M1/M9 一致。
- ~~**召唤仍然没做**~~ —— **M12 已实现**。`drowned_captain` 的 `all_hands`
  （召唤锚 + pull 3）现在两半都生效，位移那一半的判断为此多了一个变量：
  召唤会改变阵容长度，而 `pull` 的落点依赖阵容长度。见 [M12_SUMMON.md](M12_SUMMON.md)。

## 九、怎么跑

```bash
GODOT="D:/XT/godot/Godot_v4.7.2-stable_win64_console.exe"

# 全量断言（含位移/洗位/估值的 25 项新断言）
"$GODOT" --headless --path . --script res://tests/run_tests.gd

# 默认队伍：应当与 M10 逐位相同（4.0962）
"$GODOT" --headless --path . --script res://tests/bench_battle.gd -- \
  --runs=200 --data=balance/faithful --out=bench/m11_faithful.json

# 对照：关掉位移估值（怪物回到 M10 行为，永不选带位移的技能）
"$GODOT" --headless --path . --script res://tests/bench_battle.gd -- \
  --runs=200 --data=balance/faithful --no-move-value --out=bench/m11_novalue.json

# 对照：关掉位移抗性
"$GODOT" --headless --path . --script res://tests/bench_battle.gd -- \
  --runs=200 --data=balance/faithful --no-move-resist --out=bench/m11_noresist.json

# 远征：120 趟 × 4 预设（单场看不见的副作用在这里）
"$GODOT" --headless --path . --script res://tests/bench_expedition.gd -- \
  --runs=120 --size=medium --level=3 --data=balance/faithful --out=bench/m11_exp120.json

"$GODOT" --headless --path . --script res://tests/bench_expedition.gd -- \
  --runs=120 --size=medium --level=3 --data=balance/faithful --no-move-value \
  --out=bench/m11_exp120_novalue.json

# 端到端：自检会报出整趟里的推拉/洗位/抵抗次数
"$GODOT" --headless --path . -- --selftest --size=medium --level=3
```

三组 `move_probe` 遭遇（`crabby_push3` / `shambler_shuffle` / `witch_no_push`）
不需要单独命令，它们包含在每一次 `bench_battle` 的 `move_probe` 字段里。

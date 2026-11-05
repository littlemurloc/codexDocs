# M10 · 守护与反击：把「替队友挨打」接上

M9 的最后一行写着：

> 守护（替队友挨打）和反击都还没做。它们要等站位真的会动之后才有意义，现在是做它们的时候了。

这一期就是那句话。

## 一、又是两段死代码

和 M9 的位移一样，这两套机制在数据层完整存在，在代码层一字未实现：

```
effects.json    21 条带 `guard` 的效果      14 条带 `riposte` 的效果
              （MAA Guard 1 / HM Guard 1 /  （Hwy Riposte 1..5 /
               Antiq ProtectMe Guard /       MAA Riposte 1..5 /
               Clear Guard Performer ...）   Riposte Example）
combatant.gd    build_actions 解析了 `ignore_guard`，M1 起就在字典里，从没被读
effect_resolver `guard` / `riposte` 落到函数末尾的兜底分支，变成空字典返回
```

后果不是报错，是**沉默**：战争老兵花一个回合点「守护」，队友身上什么都不会发生，
攻击照样打在被守护者身上。玩家会觉得这技能坏了，但日志里一个红字都没有。

## 二、守护：一份必须成对的关系

守护只有一句话：**打向被守护者的敌方单体攻击，改为由守护者承受**。

难点不在重定向，在**状态的形状**。守护天然是双向的：

```
A 在守 B   →   A 需要知道「我在守谁」（回合末要清、要判断距离）
               B 需要知道「谁在守我」（每挨一刀都要查）
```

只记一边，就会出现「A 认为自己在守 B，B 不知道自己被守」——重定向查的正是 B 那一侧，
于是当场失效，而且失效得毫无痕迹。

所以两者放在一组字典里成对增删：

```gdscript
var _guards: Dictionary = {}      # 守护者 uid -> 被守护者 uid
var _guarded: Dictionary = {}     # 被守护者 uid -> 守护者 uid
var _guard_left: Dictionary = {}  # 守护者 uid -> 剩余回合
```

`set_guard` 同时维护两条互斥规则（一个人只能守一个、一个目标只能被一个人守），
另一半永远由它自己清理——调用方不需要知道这两条规则存在。

### 三条例外，每一条都对应一个具体问题

```gdscript
func guard_redirect(actor, action, target) -> Combatant:
	if actor.side == target.side:                  return target   # 1
	if bool(action.get("target_aoe", false)):      return target   # 2
	if bool(action.get("ignore_guard", false)):    return target   # 3
```

1. **友方技能不重定向。** 治疗被守护者，不该治到守护者头上。这一条不写，
   AI 会给残血队友点治疗，结果治的是满血的坦克。

2. **AOE 不重定向。** 这是本项目的取舍，**不是 DD1 原样**。理由：一个守护者替四个人
   吃掉整轮 AOE，等于把守护的收益翻四倍；而且 AI 完全无法预期，前排会突然变成必死位。
   如果将来要做 DD1 那种「AOE 也逐个重定向」，改这一行就够了。

3. **`ignore_guard` 穿透。** 这个字段 `build_actions` 从 M1 就在解析，一直没人读。
   现在它终于有意义了。

### 失效条件有四个，少一个都会出鬼

```gdscript
if g == null or t == null or not g.is_alive() or not t.is_alive() or left <= 0:
	drop_guard_by(g_uid)
```

守护者死了、被守护者死了、有人走了、时间到了。前三个不判，就会出现
「守护者已经阵亡，攻击仍然打在他身上」——一个人不在场却还在挨打。

## 三、反击：姿态不是攻击

`riposte` 授予的是一个**姿态**，真正的还手发生在编排层，因为只有编排层知道
「刚才那一下打中了没有」。

```gdscript
# _resolve_action 的两个出口都要调
if not hit:  ...  _try_riposte(target, actor, false)
else:        ...  _try_riposte(target, actor, true)
```

**未命中也要还手**，这不是 bug：数据里 `riposte_on_miss_chance_add` 也是 1.0，
意思是「他扑空了，正好露出破绽」。

三条实现细节：

- **伤害倍率来自数据，不是常数。** `Hwy Riposte 1` 带 `damage_low_multiply: -0.4`，
  反击伤害 = 武器伤害 × (1 − 0.4) = 60%。等级越高负得越少（4 级 −0.25 → 75%）。
  原样接。
- **不连锁。** `_riposte_depth` 计数，反击过程中不再触发反击。
  现在怪物身上没有任何 riposte，这条防线看起来多余；但只要给怪物接上同类效果，
  没有它就是 A 反击 B、B 反击 A 的栈溢出。
- **反击用虚拟技能。** 它不属于任何英雄的技能表——`dmg_range` 留空走武器伤害，
  效果列表为空，`ignore_guard = true`（反击本身是「被打之后仍然还手」的那一手，
  再被守护重定向一次会变成「守护者替攻击者挨自己人一刀」）。

## 四、一个必须查清的地方：守护为什么只能守自己

`defender` 的数据长这样：

```
{"id": "defender", "atk": 0.0, "dmg": 0.0, "launch": 1234, "target": "@1234", ...}
```

`atk = 0`，没有 `heal`。于是它撞上了这条判断：

```gdscript
# 纯功能技（无攻击无治疗，比如自身增益）：只作用于自己
if float(action.atk) <= 0.0 and float(action.heal) <= 0.0:
	return [actor]
```

目标池永远是 `[自己]`。而**守自己不会产生任何重定向**（`set_guard` 直接拒绝），
所以即使把 guard 解析出来、把关系表建好、把重定向写对，这一整套仍然是空的。

缺的是 `friendly` 这一项——目标字符串里的 `@`：

```gdscript
var pure_self: bool = float(action.atk) <= 0.0 and float(action.heal) <= 0.0 and not friendly
```

这一改还顺带修好了三处同一根因的错：

| 技能 | 归属 | 原来 | 现在 |
|---|---|---|---|
| `defender` / `guard_dog` / `protect_me` | 守护 | 只能守自己 | 能守队友 |
| `command` / `bolster`（`~@1234`） | 战争老兵群体增益 | 只给自己 | 给全队 |
| `emboldening_vapours`（`@1234`） | 瘟疫医生 | 只给自己 | 给任意队友 |

后两个是纯粹的 bug，跟守护无关，只是被同一条判断连坐。

## 五、队伍换了一个人（以及为什么）

守护只长在 `man_at_arms` / `houndmaster` / `antiquarian` 身上，反击只长在
`man_at_arms` / `highwayman` 身上。而原开局队伍是：

```
crusader, highwayman, vestal, plague_doctor
```

一个守护职业都没有。不换人的话，这两套机制要等玩家攒够 60 金去招募才会第一次出现。

所以把**十字军换成战争老兵**：

```json
"roster_start": {"heroes": ["man_at_arms", "highwayman", "vestal", "plague_doctor"]}
```

同样的前排位置，一个人同时带守护（defender）和反击（retribution），
一个位置演示两件事。旧存档读进来会按新名册重建，所以老档不会缺人。

**这是有意的替换，不是"为了好看改数据"**：数据里本来就有这两种职业，
只是初始四人组没抽到。要改回去，把 `data/campaign.json` 的 `roster_start` 改回
`crusader` 即可，代码一行都不用动。

### 代价必须说清楚

换了人，整个游戏的难度基线就变了，而变化的**大部分不是守护**：

| 队伍 | 完成率 lenient | standard | tight | 压迫指数（standard） |
|---|---:|---:|---:|---:|
| 十字军（M9 基线） | 0.867 | **0.783** | 0.283 | 1.303 |
| 战争老兵 + 守护 | 0.717 | **0.567** | 0.300 | 1.943 |
| 战争老兵，关掉守护 | 0.700 | **0.483** | 0.300 | 2.158 |

- 守护本身的贡献：standard 完成率 **+0.084**（0.483 → 0.567），压迫指数 **−0.215**。是正收益。
- 换职业的代价：standard 完成率 **−0.216**（0.783 → 0.567）。

剩下的差额纯粹是「十字军比战争老兵强」：武器伤害 6–12 vs 5–9、生命 33 vs 31。
**守护补不回这个损失。** 而且换别的守护职业只会更差——
`houndmaster` 21 血 4–7 伤、`antiquarian` 17 血 3–5 伤，数据里没有第二个能站前排的守卫。

所以这是一个带代价的选择：**要么开局就能看见守护，要么保持 M9 的难度曲线。**
当前选了前者，因为这两套机制不实际出现一次，就没法知道它到底通没通。
要换回去，改一行 `roster_start`，其余不用动。

## 六、守护到底有没有用

三个层次分开答，因为它们的答案不一样。

### 1. 默认队伍：一个数都没动

| 指标 | M9 | M10 |
|---|---:|---:|
| 战斗轮数 | 4.0962 | **4.0962** |
| 终局血量 | 0.9410 | **0.9410** |
| 命中率 | 0.8052 | **0.8052** |
| 暴击率 | 0.0716 | **0.0716** |
| 溢出占比 | 0.1215 | **0.1215** |
| 终局压力 | 19.3123 | **19.3123** |

十六个指标逐位相同。远征层同样（完成率 0.867 / 0.783 / 0.283 / 0.000，
压迫指数 0.787 / 1.303 / 2.810 / 3.340，与 M9 完全一致）。

**M10 是纯增量**：新增的代码路径默认不触发，所以旧基线一个数都不动。
这正是 M7/M8 的做法，也说明「没变」这件事本身是可验证的。

### 2. 换成带守卫的队伍：只有一种场景会触发

同队伍、同种子，只把 `guard_enabled` 关掉做对照（200 场）：

| 场景 | 守护次数/场 | 实际挡住/场 | 终局血量（开 → 关） |
|---|---:|---:|---|
| tier1（0 阶） | 0.00 | 0.00 | 0.9356 → 0.9356 |
| tier2（2 阶） | 0.00 | 0.00 | 0.9282 → 0.9282 |
| tier3（4 阶） | 0.00 | 0.00 | 0.9012 → 0.9012 |
| **tier3_pressured（4 打 4）** | **0.98** | **0.41** | 0.8843 → 0.8837 |
| gauntlet（连打三场） | 0.00 | 0.00 | 0.8309 → 0.8309 |

前三个场景 AI **一次都没守护**。原因很直接：`_score` 给守护的分数是
`2.0 + (1 − 队友血量比) × 6.0`，满血队友值 2 分，而任何一刀都值 7~9 分。
只有当队友掉到半血以下（>5 分）才可能被选中——而这几个场景里根本没人掉到半血。

`tier3_pressured` 是唯一的硬仗（4 只最高难度怪），于是守护出现了：
每场 0.98 次，其中 0.41 次真的挡到了刀。但单场收益仍然在噪音级：

```
终局血量   0.8843 vs 0.8837   （+0.0006）
战斗轮数   5.0800 vs 5.0600   （+0.02）
终局压力  32.7790 vs 32.5190   （+0.26，反而更高）
```

### 3. 远征：正收益，但要 60 趟才看得见

单场看不见的东西，在一整趟路上会累积。同队伍、同路线、同种子，只开关守护
（weald / medium / Lv3 / 60 趟）：

| 预设 | 守护开 | 守护关 | 差值 |
|---|---:|---:|---:|
| lenient | 0.717 | 0.700 | +0.017 |
| **standard** | **0.567** | **0.483** | **+0.084** |
| tight | 0.300 | 0.300 | ±0 |
| brutal | 0.000 | 0.017 | −0.017 |

压迫指数（standard）**1.943 vs 2.158**，守护把压力降了 0.215。

所以守护**是有用的**，只是它的收益不在「这一刀打在谁身上」，而在
「十步路上少进几次死门」。这和 M3 的结论同一形状：单场看不出的东西，
摊到资源层才显形——只不过这次量级小得多。

### 4. 为什么单场一概看不见

因为守护**不减少总伤害**，它只把伤害从 A 挪到 B。它的全部价值在于
「让本该进死门的人不进死门」——而单场 200 局里：

```
hero_death_rate   0.0000
deaths_door_per_fight  0.0000
```

**没人会死，所以守护没有可拯救的对象。** 这是 M2 那条结论的又一次回响：
资源层是伤害维度的放大器，而 M2/M3 已经把危险度调到了「打得疼但打不死」的区间。
守护是纯粹的**风险管理**工具，它需要一个「管理失败就会真的死人」的环境才有价值。

这不是实现的失败，是数值环境的现状。要让守护有意义，先得有会死人的仗——
那是数值层的事，不是机制层的事。

## 七、踩到的坑

**1. 探针的 `atk = 0` 让它变成功能技。** 测试里构造一个「必中固定伤害」的攻击，
`atk` 给了 0，结果 `_resolve_action` 用 `atk <= 0` 判定「这是纯功能技」，
一刀都不打。所有断言静默失败，而失败信息全是「血量没变」——看起来像守护没生效。

**2. `cutoff_hit = 0` 会连反击一起打死。** 为了稳定复现「攻击未命中」，
把命中上限压到 0；但 `cutoff_hit` 是全局的，**反击本身**也就永远打不中。
断言报「未命中也会触发反击（15 → 15）」，看着像反击没触发，其实反击打了、只是没中。
正确做法是把攻击者的 `acc` 压到负数，只影响那一次攻击。

**3. 怪物没有命中属性。** `monster_base` 里 `acc` 恒为 0，所以怪物的命中率**就是**
技能的 `atk`。探针给 `atk = 0.5` 就意味着每次只有五成概率命中，断言会随机红。
这个事实本身也值得记：怪物打人靠技能自带的 `atk`，不靠面板。

**4. 给反击估值会抬高整条基线。** 第一版给「每回合 2 分」，AI 立刻开始用
`duelist_advance`（伤害只有平砍的 80%），平均轮数从 4.0962 涨到 **4.305**（+5%），
而 `riposte_per_fight` 还是 0——它摆了三回合姿态，一次都没被打中。

现在用 `duration × 0.3 × 反击伤害倍率`，小到不改变任何选择，基线精确回到 4.0962。
**结论是「AI 不该主动为反击牺牲输出」**，这个估值本身就是那个结论的编码。

**5. 换队伍不是对照实验。** 一开始拿「MAA 队伍 vs 十字军队伍」当守护的效果对比，
但换了职业，变的就不只是守护（血量 31 vs 33、技能组、伤害区间全都变了）。
真正的对照必须同队伍 + 开关。

## 八、已知局限

- **怪物不会守护。** 数据里 254 只怪物没有任何一条 guard 效果，所以守护天然是玩家特权。
- **AOE 穿透守护。** 本项目的取舍（见第二节），不是 DD1 原样。
- **反击只有一种形态。** 不分技能、不区分近远，就是用武器平砍一下。
  DD1 里反击走的是每职业各自的 riposte 技能。
- **守护不改变站位。** DD1 里守护者会「挡在前面」，这里位置不动，只有伤害改道。
  只有古物学家的 `protect_me` 因为数据里写了 `swap_source_and_target` 才换位。
- **没做「守护数量上限」之外的策略。** 一个守护者守一个人、一个目标被一个人守，
  这两条是从数据里 `clearguarding` / `clearguarded` 的效果反推的，没有更多规则。
- **AI 几乎不主动用反击。** `riposte_per_fight` 在默认队伍是 0，带守卫的队伍也是 0。
  原因见第七节第 4 条：姿态那回合伤害只有 80%，而 3 回合内被打中的次数不够回本。
  **这个技能目前主要属于玩家**——人能预判「下一轮谁会打我」，AI 不能。
- **换名册让标准难度变难了 0.216。** 见第五节。要回滚只需改 `roster_start` 一行，
  但那样玩家得先攒 60 金招募才能第一次看见守护。
- **死人不让出位置。** 和 M9 一样，尸体仍占格。
- 怪物位移、陷阱主动解除、秘密房间、饰品，仍然没做。

## 九、怎么跑

```bash
GODOT="D:/XT/godot/Godot_v4.7.2-stable_win64_console.exe"

# 全量断言（含守护/反击的 52 项新断言）
"$GODOT" --headless --path . --script res://tests/run_tests.gd

# 默认队伍：应当与 M9 逐位相同
"$GODOT" --headless --path . --script res://tests/bench_battle.gd -- \
  --runs=200 --data=balance/faithful --out=bench/m10_faithful.json

# 带守卫的队伍（守护/反击统计在这里）
"$GODOT" --headless --path . --script res://tests/bench_battle.gd -- \
  --runs=200 --data=balance/faithful \
  --heroes=man_at_arms,highwayman,vestal,plague_doctor \
  --out=bench/m10_faithful_guard.json

# 对照：同队伍，只关掉守护
"$GODOT" --headless --path . --script res://tests/bench_battle.gd -- \
  --runs=200 --data=balance/faithful \
  --heroes=man_at_arms,highwayman,vestal,plague_doctor --no-guard \
  --out=bench/m10_faithful_noguard.json

# 远征：守护开（60 趟 × 4 预设，单场看不见的收益在这里）
"$GODOT" --headless --path . --script res://tests/bench_expedition.gd -- \
  --runs=60 --size=medium --level=3 --data=balance/faithful \
  --heroes=man_at_arms,highwayman,vestal,plague_doctor

# 远征：同队伍，关掉守护（对照）
"$GODOT" --headless --path . --script res://tests/bench_expedition.gd -- \
  --runs=60 --size=medium --level=3 --data=balance/faithful \
  --heroes=man_at_arms,highwayman,vestal,plague_doctor --no-guard

# 端到端（自检会真的点一次「守护」并检查关系是否建立）
"$GODOT" --headless --path . -- --selftest --size=short --level=1

# 看界面：开局第一场战斗自动守护一次后冻住
"$GODOT" --path . -- --auto --fast --show-guard --shot=shots/m10_guard.png --shot-at=14
```

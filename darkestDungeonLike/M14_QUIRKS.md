# M14 · 怪癖与疾病

> 这一期补的是 M13 留下的那 27 个「只解析不落地」分支里最重要的一类。
> 但它不是简单地把 `unsupported` 改成生效——**195 条 buff 引用里有 119 条带条件**，
> 真正的难点是把 15 种 `rule_type` 翻译成可判定的谓词，并且诚实地说清楚
> 哪些判不了。
>
> **第二版修订**：第一版上线后的问题是「原版怪癖出现率是一样的吗？为什么原版正常」——
> 一查，我漏掉了原版的主渠道，还把三个上限数字拍错了。见 §7。

---

## 1. 起点：三个空层

M13 结束时，奇物能抽出 `quirk` / `disease` / `purge` 三类结果，`CurioLib`
把它们解析出来、带上 `quirk: positive` 这样的字段，然后——

| 层 | 现状 |
|---|---|
| `effect_resolver` | 遇到 `disease` 标一句 `unsupported`；遇到 `quirk` 连标都没标，直接掉在地上 |
| `Combatant` | 有完整的 buff 通道（`_sum_add` / `_product_mult` / `resistance`），但没有任何东西往里放怪癖 |
| `Campaign` / `Expedition` | 没有「英雄身上有怪癖」这个概念，`state` 里只有血量、压力、崩溃 |

而 `data/quirks.json` 里躺着 170 个怪癖（23 个是疾病）、195 条 buff 引用。

## 2. 疾病不是独立系统

`quirks.json` 每条都有 `is_disease`，23 条为 true。疾病就是**带疾病标记的怪癖**：

- 同一套槽位语法（正 / 负 / 疾病各一组，上限见 §7.2）
- 同一条 buff 通道
- 同一个清负面规则（`purge` 不清病，`cure` 才清）

差别只有两个：获得途径（接触脏东西而不是战斗结算），以及多一条疾病抗性判定。

单独造一张疾病表会让两者永远不同步——这正是 M13 修过的那类问题（同名表分多份、
`overrides` 没合并）。所以这里一律走同一张表。

## 3. 关键结构：条件才是主体

195 条 buff 引用里只有 76 条是 `always`。其余靠 15 种 `rule_type` 决定
「什么时候生效」：

| rule_type | 条数 | 判定 |
|---|---:|---|
| `always` | 76 | 恒真 |
| `in_dungeon` | 24 | `rule_data.string == 当前地牢` |
| `monsterType` | 20 | 活着的敌人里有这个种 |
| `monster_type_count_min` | 11 | 这个种的数量 ≥ `rule_data.float` |
| `lightabove` | 9 | 光照 **≥** 阈值 |
| `hpbelow` | 9 | 血量比例 **<** 阈值 |
| `firstroundonly` | 8 | 第 1 轮 |
| `rangedonly` | 8 | 本次技能是远程 |
| `lightbelow` | 7 | 光照 **≤** 阈值 |
| `meleeonly` | 6 | 本次技能是近战 |
| `in_camp` | 6 | **判不了**（没有营地系统） |
| `in_activity` | 6 | **判不了**（没有城镇活动） |
| `stress_above` | 3 | 压力 **>** 阈值 |
| `walking_backwards` | 1 | **判不了** |
| `in_corridor` | 1 | **判不了** |

三种阈值口径**不一致**，是原表就这么写的，不是笔误：

- `hpbelow: 0.5` → 比例（半血以下）
- `stress_above: 50` → 绝对压力值
- `lightabove: 75` / `lightbelow: 26` → 绝对光照值

`lightabove` 用 `>=`、`lightbelow` 用 `<=`，于是 27–74 是一段**无判定的灰带**——
亮处、暗处、以及两者之间那片谁都不得罪的区间。这和 DD1 的火把分档语义一致。

判不了的四种一律返回 `false` 并计数，**不猜**。宁可这个怪癖暂时无效，
也不要给一个「看起来生效了」的假实现。

## 4. 落地率

```
总引用 195
├─ 可落地     178  (91.3%)  条件可判 + 有承载
├─ 条件判不了   5  ( 2.6%)  有承载，但依赖营地/活动/走廊方向
├─ 没有承载     3  ( 1.5%)  条件能判，但本作没有对应系统
└─ 两头都没有   9  ( 4.6%)
```

承载通道分四层：

| 通道 | 条数 | 谁消费 |
|---|---:|---|
| 战斗 | 168 | `Combatant._sum_add / _product_mult / _sum_stat / resistance` |
| 远征 | 13 | 侦察概率、食物消耗 |
| 元层 | 2 | 升级折扣 |
| 无 | 12 | 营地治疗、决心检定、城镇活动副作用 |

32 个怪癖**没有任何数值效果**（`curious`、`compulsive` 这类纯奇物标记型），
它们的作用是改奇物标签的触发概率，本作没有那套标签联动。

## 5. 实现

### 5.1 `src/core/quirk_lib.gd`

- 加载 `quirks.json` + `buffs.json`，把 buff id 展开成定义（缺失的单独记 `missing_buffs`，不静默丢）
- `rule_active(buff, ctx)` —— 15 种条件的判定表
- `pick(polarity, rng, owned, want_disease)` —— 按 `random_chance` 加权，排除已持有、排除互斥
- `apply_caps(pos, neg, disease)` —— 槽位上限由规则表灌入（见 §7.2）
- `max_hp_mult(ids)` —— 见下
- `compute_stats()` —— §4 那张表就是它算的

### 5.2 为什么不复用 `buffs` 数组

`Combatant.buffs` 是**战斗内**临时状态：战斗结束要清、同名要刷新持续时间、
死门减益靠 id 反查删除。怪癖是**跨远征**的，生命周期完全不同。

混进去的后果是「清 buff」会顺手把人物性格洗掉。所以分两条通道：
`quirk_pool`（原始定义，带条件）+ `_quirk_active`（按当前语境筛过的子集），
读取数值时两条都算。

### 5.3 刷新时机

条件会随战况变化，所以必须定期重算。三个点：

1. **战斗开始**（`apply_party_state` 之后）
2. **每轮开头**——而且必须在 `build_order` **之前**：行动序按速度算，
   放到排序后刷，`firstroundonly` 的 +4 速度就永远只能影响伤害、不能影响先手
3. **每次行动前**（`_apply_choice`）——`meleeonly` / `rangedonly` 要等技能定了才知道判什么

刷新不消耗 rng（纯查表），随便刷。

### 5.4 `max_hp` 必须在注入时算掉

`combat_stat_multiply / max_hp` 改的是**分母**（`hp_ratio`、治疗上限都依赖 `base_hp`），
做成每帧可变会让「当前血量」失去定义。

九条 max_hp buff 全是 `always`，所以可以安全地在 `set_quirks` 里一次性取乘积，
并**按同比例缩放当前血量**——否则「装上 +10% 生命的怪癖」会顺手把伤治了。

之后每次 `refresh_quirks` 都跳过 max_hp，避免重复乘。

## 6. 两个静默失败

这一期花在查 bug 上的时间比写代码多。两个 bug 都属于「不报错、只是什么都不发生」。

### 6.1 `state` 整份替换把怪癖抹掉

`finish_battle` 用 `capture_party_state()` 的结果**整份替换** `state[hid]`，
而那份快照里没有 `quirks`。

症状：战斗内明明生效（开打时读到了），打完第一场就清零。
**只有打满两场以上才看得出来**，单场测试永远抓不到。

修法：两处都补——`capture_party_state` 带上 `quirks`，
`finish_battle` 在旧值非空时兜底回填。

### 6.2 键不存在导致 append 抛错，而异常被吞

更隐蔽的一层：替换后的行里**根本没有 `quirks` 这个键**，
`state[hid]["quirks"].append(qid)` 直接抛
`Invalid access to property or key 'quirks'`。

在自动流程里这个异常被静默吞掉，表现是：
**奇物明明抽到了 `quirk` 分支、槽位也空着，但什么都没发生。**

定位过程（值得记下来）：

1. bench 量到 5.47 次奇物接触只换来 0.025 条怪癖 → 差 24 倍
2. 加结果类型计数 → 确认 0.325 次/趟是真的抽到了 `quirk` 分支
3. 加拒绝计数（槽位满/重复/未知/池空/无此人）→ 全 0，说明连 `grant_quirk` 都没进去
4. 加分支命中计数 → 命中，`quirk_target` 也不空
5. 打印 `want` → 是 `positive`，正常
6. 打印 `grant_quirk` 三个返回点 → 一个都没打印 → 函数抛异常了
7. 在未过滤的输出里 `grep error` → 找到了

修法：加一个 `_quirk_list(hid)` 入口，键不存在就建，返回**活引用**，
所有写操作走它。

## 7. 原版为什么正常：我漏掉了主渠道

第一版上线后的问题：「原版怪癖出现率是一样的吗？为什么原版正常？」

答案是否定的——**原版不是靠奇物撑起来的**。DD1 的怪癖有三条独立来源，
而且都能在已经抽取出来的数据里找到：

| 渠道 | 数据出处 | 第一版 |
|---|---|---|
| **新英雄自带** | `heroes.json` → `generation.number_of_positive_quirks_min/max`、`..._negative_...`，**15 个英雄全部是 1–2 / 1–2** | **完全没接** |
| 奇物交互 | `curios.json`，约 20 个奇物能触发，占 60 个的三分之一 | 接了（唯一一条） |
| 任务奖惩 | `quests.json` → `party_quirks_to_apply_on_completion / _on_failure` | 未接（本作数据里这两个数组全是空） |

所以原版「正常」的原因很朴素：**每个走进酒馆的英雄本来就不是白纸**。
4 人队开局就有 8–16 条怪癖，怪癖从第一分钟起就在影响战斗和数值。

我们只接奇物，等于把「人物个性」全押在「这趟有没有碰到书架」上——
而一趟真实远征只能碰到 0–1 个奇物。

### 7.1 这条渠道本来就该有

`heroes.json` 的 `generation` 段是给「生成一个新英雄」用的，里面除了怪癖数量，
还有属性随机区间等。我读表时只取了 `resistances` / `skills` / `base`，
`generation` 整段被跳过了。

这已经不只是「沉默死代码」（数据在、没人读），而是**读了一半**——
比完全不读更难发现，因为同一条数据的前半截明明是在用的。

### 7.2 顺带修正两个数字

翻 `rules.json` 时发现槽位上限我拍错了：

| 项 | 我第一版写的 | `rules.json` 实际 | 出处 |
|---|---:|---:|---|
| 正面槽位 | 3 | **5** | `quirks_max_positive` |
| 负面槽位 | 3 | **5** | `quirks_max_negative` |
| 疾病槽位 | 1 | **3** | `quirks_max_diseases` |

另外还有一组**读了但没落点**的参数：

- `quirk_chance_to_lock_negative = 0.25`
- `quirk_negative_locked_after_turn_count = 2`
- `quirks_max_locked_positive = 3` / `quirks_max_locked_negative = 3`

意思是负面怪癖在若干回合后有 25% 概率「锁定」，锁定后不能再被洗掉。
本作没有疗养所/医院，锁定没有落点，所以只把参数读进来备用。
但它解释了一件事：**原版里负面怪癖为什么会「粘住」**——不是数值设计，是锁定机制。

槽位从 3/3 提到 5/5 之后，「怪癖满了」这件事晚来很多，单次奇物的价值上升。
这不是数值偏好，是还原。

### 7.3 修正后的账

| 项 | 第一版 | 修正后 |
|---|---:|---:|
| 新档开局怪癖 | 0 | **8–16 条**（实测 11–13） |
| 奇物来源 | 约 0.05 条/趟 | 约 0.05 条/趟（这条数据没错，它本来就不是主渠道） |
| 正面 / 负面 / 疾病槽 | 3 / 3 / 1 | **5 / 5 / 3**（来自 `rules.json`） |

平衡影响（40 趟 short/Lv3/standard，其余全同）：

| 组 | 完成率 | 压迫指数 | 死亡 | 崩溃 | 轮数 | 末血 |
|---|---:|---:|---:|---:|---:|---:|
| 无怪癖（第一版默认） | 0.875 | 0.698 | 0.72 | 0.75 | 32.8 | 0.603 |
| 1 正 1 负（生成下限） | 0.925 | 0.510 | 0.47 | 0.72 | 32.8 | 0.619 |
| 2 正 2 负（生成上限） | 0.925 | 0.655 | 0.62 | 0.78 | 34.3 | 0.596 |
| 6 正（极端） | 0.975 | 0.325 | 0.23 | 0.68 | 30.1 | 0.692 |
| 6 负（极端） | 0.850 | 0.925 | 0.82 | 1.18 | 34.6 | 0.543 |

自带怪癖**没有把难度打崩**：完成率 0.875 → 0.925，压迫反而降了一点。
原因是随机池里正面比负面更容易凑成有效组合（负面里有大量「判不了」或「无承载」的
纯标记怪癖，见 §4）。这是原版也存在的不对称，不是我们调的。

## 8. 奇物这条渠道的真实数字

修正后在 bench 里注入 6 个走廊奇物：

```
奇物接触      5.47 次/趟
quirk 分支    0.325 次/趟   （10.8%，与权重吻合）
实际获得      0.325 条/趟   （100% 落地，无静默丢弃）
```

折算到真实地图（一趟只碰到 0–1 个奇物）：**约 0.05 条/趟**。

这个数字一直是对的，只是第一版据此得出了错误结论
（「机制完整但玩家看不见」）——真正的问题是**渠道选错了**，不是概率偏低。

## 9. 对照实验：怪癖到底有没有用

同队伍、同种子、同路线，只改「每人挂几条怪癖」。40 趟 short/Lv3/standard：

| 组 | 完成率 | 压迫指数 | 死亡 | 崩溃 | 轮数 | 末血 |
|---|---:|---:|---:|---:|---:|---:|
| 每人 3 条（混合） | 0.900 | 0.615 | 0.57 | 0.80 | 31.9 | 0.604 |
| 每人 6 条（混合） | 0.925 | 0.637 | 0.72 | 0.70 | 32.1 | 0.665 |
| 每人 6 条（**全负面**） | 0.850 | **0.925** | 0.82 | **1.18** | **34.6** | 0.543 |
| 每人 6 条（**全正面**） | **0.975** | **0.325** | **0.23** | 0.68 | 30.1 | 0.692 |

单调、方向正确：

- 全负面：压迫 +0.23、崩溃 +0.43、多打 1.8 轮、末血 −6%
- 全正面：压迫 −0.37、死亡 −0.49、少打 2.7 轮

**bench 基线逐位不变**：bench 默认不塞怪癖（`--quirks=0`），
无怪癖时完成率/压迫/死亡/崩溃/轮数/末血全部与 M13 一致。
改的是**新档默认行为**（开新档会掷开局怪癖），不是测量基线。

## 10. 已知限制

- **4 种条件判不了**（`in_camp` / `in_activity` / `walking_backwards` / `in_corridor`），
  共 13 条 buff，一律不生效并计数。
- **32 个怪癖没有数值效果**（纯奇物标记），本作没有标签联动系统。
- **怪癖标签（`curio_tag`）未接**：21 个怪癖带「碰某类奇物时更容易触发」的字段，
  需要奇物标签匹配，本期没做。
- **负面怪癖锁定未实现**：`rules.json` 里的 25% / 2 回合参数已读入但无落点
  （没有疗养所）。原版靠它让负面怪癖「粘住」。
- **城镇没有医院**：怪癖和疾病只能靠奇物清除，回城不会自动治。`cure` 已实现，
  但没有任何东西调用它——**同一类「实现了但没有入口」**。
- **刷新粒度是「轮开始 + 行动前」**：`hpbelow` 类怪癖在两次刷新之间的血量变化不会
  立刻生效（最坏差一次行动）。
- **食物消耗带一个小数债**：`food_consumption_percent` 是增量（绦虫 +1.0 = 吃两倍），
  但 `stress_faster` 写的是 −1.0，照字面会让饥饿系统失效，所以下限夹到 0.5 倍。
- **开局怪癖会改变手感**：新档默认带 8–16 条，这是相对第一版的行为变化。
  想回到「白纸英雄」：把 `Campaign.start_quirks_enabled` 置 false，
  或在 `campaign.json` 的 `roster_start.quirks` 里给某个人写空数组。

## 11. 复现

```bash
GODOT="D:/XT/godot/Godot_v4.7.2-stable_win64_console.exe"

# 全量断言（713 项）
"$GODOT" --headless --path . --script res://tests/run_tests.gd

# 生成区间怪癖的影响（1 正 1 负 ≈ 生成下限，2 正 2 负 ≈ 上限）
"$GODOT" --headless --path . --script res://tests/bench_expedition.gd -- \
  --runs=40 --size=short --level=3 --presets=standard --quirks=2 --quirk-polarity=alt
"$GODOT" --headless --path . --script res://tests/bench_expedition.gd -- \
  --runs=40 --size=short --level=3 --presets=standard --quirks=4 --quirk-polarity=alt

# 极端对照：全负面 / 全正面（每人 6 条）
"$GODOT" --headless --path . --script res://tests/bench_expedition.gd -- \
  --runs=40 --size=short --level=3 --presets=standard --quirks=6 --quirk-polarity=neg
"$GODOT" --headless --path . --script res://tests/bench_expedition.gd -- \
  --runs=40 --size=short --level=3 --presets=standard --quirks=6 --quirk-polarity=pos

# 奇物 → 怪癖的真实转化率（注入 6 个走廊奇物）
"$GODOT" --headless --path . --script res://tests/bench_expedition.gd -- \
  --runs=40 --size=short --level=3 --presets=standard --hall-curio=6 --out=bench/m14_curio6.json

# 端到端自检：全新档应报「在手 8–16」；
# 怪癖一栏只报数不判 PASS——这一趟能不能再拿到取决于碰到什么奇物
"$GODOT" --headless --path . -- --selftest --size=short --level=1 --save=user://m14_fresh.json
```

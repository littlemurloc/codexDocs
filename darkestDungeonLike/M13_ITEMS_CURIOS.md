# M13 — 道具与奇物

一句话：**这一期修的不是「缺功能」，是「假数据」。**

M5 的战利品是一组手写常数（每场 9–17 金、30% 掉一件传家宝、通关 45+22×场次），
奇物是一枚硬币（65% 拿 12–26 金，否则全队 +9 压力）。而 `data/` 里一直躺着
61 份抽卡表、60 个奇物定义、139 个有权重的分支、46 条道具交互——一行代码都没读。

于是「板条箱」和「邪秽祭坛」在玩家眼里是同一个东西。要记住「铁处女该用绷带」
「邪祭坛该带圣水」是不可能的，因为那些区别**在代码里不存在**。

这一期把它们接上。顺便发现两件比预期严重的事：**整棵抽卡树的根（A 表）
根本没被加载**，以及**经济模型差了一个数量级**。

---

## 一、数据全貌

| 数据 | 规模 | 之前的状态 |
|---|---|---|
| `data/loot.json` | 61 份表变体 / 40 个 id | 没有代码读 |
| `data/curios.json`（本期生成） | 60 个奇物 · 480 个 outcome 行 · 139 个有权重 · 46 条道具交互 | 不存在 |
| `data/dungeons.json .props` | 6 个地牢 · 7 类位置 · 67 个引用 | 读了，注释写「暂未接入」 |
| `data/inventory.json` | 10 种补给（带价格与堆叠上限） | 没有代码读 |
| `data/monsters.json .loot` | 254 只怪，每只带 `{code, count}` | 没有代码读 |

对照的实现量：`src/core/loot.gd`（抽卡树）+ `src/core/curio.gd`（奇物规则）
+ 远征/地图/界面接线。

---

## 二、四个必须先搞对的结构事实

### 2.1 `overrides` 的语义是「覆盖」，不是「另存一份」

`tools/extract.py` 把 `loot/*overrides.loot.json` 原样塞进 `overrides` 字段，
没有合并。而那批文件里有 **A 表和 S 表——恰好是整棵树的根**：

```
A ──50──> C（金币档 25…1000）
  ──38──> G（宝石，250…4500 卖价）
  ──48──> H（传家宝）
  ──28──> S     ──8──> T（饰品）     ──2──> 日志页
```

只读 `loot_tables` 的话，`tables["A"]` 根本不存在。而所有引用 A 的抽取都会
走「缺表 → 什么都不给」分支，**不报错、不警告，只是掉得少**。
这类错误在 40 趟的对照里才会显出差异。

所以合并放在运行时做（`LootTables._add_variant`）：先装 `loot_tables`，
再按文件名顺序让 overrides 覆盖同名同难度的表。

### 2.2 表 id 不是唯一键

`loot_tables` 数组长 58，唯一 id 只有 37。同名的 C/G/T 各有 4 份，H 有 13 份：

| 表 | 变体数 | 维度 |
|---|---|---|
| `C`（金币） | 4 | difficulty 1 / 3 / 5 / 6 |
| `G`（宝石） | 4 | 同上 |
| `T`（饰品） | 4 | 同上 |
| `H`（传家宝） | 13 | 4 地牢 × 3 难度 + 1 份通用 |

它们不是重复数据，是**难度梯度**：

| C 表 | difficulty 1 | 3 | 5 | 6 |
|---|---|---|---|---|
| 期望金币 | **253.4** | 431.4 | 559.2 | 559.2 |
| 条目权重合计 | 22 | 35 | 30 | 30 |

用 `id → entries` 当字典会让最后一份（d6）吃掉全部，**深地牢的经济优势直接消失**。
所以 `tables` 的值是变体数组，抽取时按 `(地牢, 难度)` 选一份：

1. 本地牢 + `difficulty <= 当前` 里取难度最大
2. 没有 → 通用表（`dungeon == ""`）同规则
3. 都没有 → **宁可放宽难度取通用表，也不拿别的地牢的专属表**
   （H 表里是各地牢的传家宝配比，张冠李戴比给少了更糟）

### 2.3 `hallway_curio` 是百分比，不是数量

```
hallway_battle  = [2,4]   [3,4]   [7,8]      ← 数量
hallway_trap    = [1,2]   [3,5]   [5,7]      ← 数量
hallway_curio   = [9,9]   [14,14] [19,19]    ← short/medium/long 线性相关
```

9 条走廊放不下 9 个奇物（走廊容量 cap 只有 4–5）。这是**百分比**：
short 9%、medium 14%、long 19%。

而且项目此前只实现了 `room_curio`，它的配额是 `[0,0]`——**奇物在地图上几乎不存在**。
真正的奇物来源（走廊，9–19%）一行都没写。这是「接线层」的漏洞，不是规则层的。

补上之后：只填空走廊（不动已按 cap 分配的陷阱/饥饿，否则饥饿会被挤死——
M3 的老教训），用派生 rng 抽取，实测 long 图 12 张出 8 个。

### 2.4 设计表是 Excel 排版，标签行本身也是 outcome 行

`curio_design_table.json` 是 958×19 的单元格矩阵（来自策划的 `curio_type_library.csv`）。
60 个奇物各占 16 行，合并单元格导出后只剩左上角有值。

两个坑：

- **col2 是元数据列，col4 是 outcome 列，两者错开一行。**
  `row5` 的 col2 是标签 `REGION FOUND`，col4 却是 outcome `Loot`（权重 3）。
  第一版按标签行 `continue`，直接把每块的两个分支吃掉了——60 个奇物只剩 5 个 outcome。
- **`Nothing` 分支的三个 result 列都填了 `N/A`**，是占位不是结果，要剔掉。

摊平脚本是 `tools/gen_curios.py`，产物 `data/curios.json`（480 个 outcome 行，60×8 槽位齐全）。

---

## 三、奇物交互：并列还是互斥

一个 outcome 内部可能有多个 result。两种语义，判据是**百分比列有没有值**：

| 情况 | 判据 | 例子 |
|---|---|---|
| **清单**（全给） | 所有 result 的 pct 都缺 | `goal_strongbox` 的 Loot：抽 B 表 3 次 **+** T 表 1 次 |
| **选择题**（抽一个） | 任一 result 有 pct | `locked_strongbox` 的 Effect：Blight 1 / Bleed 1 各 50% |

容易搞错的是**互斥时不能用 weight 列当概率**。原表里 Loot 分支的 weight 位
被「抽几次」占用了，跟概率无关。看这一行：

```
shovel → Loot:  Nothing  权重1  50%      A表  权重2  "<- # Draws"
```

按 weight 1:2 分会变成 33/67，而表里写的是 50/50。正确规则是：
**给了百分比的按百分比，没给的平分剩余概率**。实现见 `CurioLib._pick_results`。

---

## 四、道具：第一次真的能「带什么上路」

9 种补给，46 条交互。同一种奇物对不同道具给不同结果：

| 奇物 | 道具 | 结果 |
|---|---|---|
| 上锁的保险箱 | 骷髅钥匙 | 必中：抽 A 表 **3 次** |
| 上锁的保险箱 | 铲子 | 50% 砸空 / 50% 抽 A 表 2 次 |
| 上锁的保险箱 | （空手） | 50% 掉落 / 50% Blight·Bleed 各半 |
| 邪秽祭坛 | 圣水 | 清负面怪癖（`Purge`） |
| 铁处女 | 绷带 | 抽 B 表 2 次 |
| 浅坟 | 铲子 | 抽 CH 表 2 次 + `guilty_conscience` 怪癖 |

补给包在出发时给每样 1 件（`Expedition.DEFAULT_SUPPLY_PACK`），
`preset.supply.start` 可覆盖。拾取到 `supply` 类物品会补进包里。

`shovel` 是个例外：它在 M8 就是独立字段（障碍清除在用），
所以 `supply_count("shovel")` 直接读那个字段，不另存一份镜像——
两处镜像同一份数量只会制造不同步。取用统一走 `supply_count` / `take_supply`。

---

## 五、战斗掉落：逐只怪抽表

`monsters.json` 里 254 只怪都带 loot：

| loot | 怪物数 |
|---|---|
| `A × 1` | 100 |
| `A × 2` | 22 |
| `NONE`（明确不掉） | 17 |
| `C × 1` | 9 |
| `T × 2` | 10 |
| `BLUEPRINT × 1` | 14 |
| 其余 | 82 |

于是「这波怪值多少」不再是一个可以随便改的数字，而是**遭遇表 × 怪物表**的结果：
换一层地牢、换一组怪，产出自己就变了。

旧路径保留为 `loot_table_enabled = false`，走 M5 的 9–17 金常数，
用于复现历史基线。**注意它在 bench 里一直是 0 金**——因为 bench 从来没传过
`loot_cfg`。所以「真表 4903 金 vs 旧常数 0 金」这个对比不是真表让收益涨了 4903，
而是**战利品第一次真的存在**。

---

## 六、经济必须连带重标定

真表一落地，`campaign.json` 的旧价格立刻站不住：

| | 旧 | 真表实测 |
|---|---|---|
| 一趟 short/Lv1 | — | **3498 金** · 9.1 传家宝 |
| 一趟 short/Lv3 | — | 4903 金 · 15.7 传家宝 |
| 一趟 short/Lv5 | — | 6364 金 · 18.7 传家宝 |
| 升满一件装备（4 阶） | 40+90+160+260 = **550 金** | — |
| 招募一名英雄 | **60 金** | — |

也就是说：**打半趟就能把全队升满**。旧价格是 M5 在没有抽卡树时拍的，
从来没跟任何数据对过。

按实测产出重标定（`data/campaign.json`）：

| | 旧 | 新 | 依据 |
|---|---|---|---|
| 招募 | 60 | **1000** | 约 1/3 趟新手图 |
| 升级 1→2 | 40 | **1000** | 约 1/3 趟 |
| 2→3 | 90 | **2200** | |
| 3→4 | 160 | **4800** | |
| 4→5 | 260 | **10000** | 升满一件 ≈ 10 趟新手图 |
| 传家宝（bust/portrait/deed/crest） | 2/3/4/6 | **3/4/6/10** | 一趟 9.1 个 → 全队 ≈ 20 趟 |

回滚方式：把 `campaign.json` 的 `costs` 段换回旧值即可，其余逻辑不依赖具体数字。
测试也从「硬编码 100 金够升级」改成了按 `upgrade_cost()` 读配置——
写死金额的断言会跟着配置一起碎。

---

## 七、数据

### 7.1 地图基线：逐位不变

新增的奇物抽取全部走**派生 rng**（`MapGen._derive_seed`，只读 `rng.draw_count` 当盐，
不消耗主序列）。地图形状、房间内容、走廊配额都是同一条序列出来的，
多抽一个数会让 M7 的全部基线整体漂移。

实测：`test_map` / `test_expedition` 的 559 项旧断言在接入后逐条通过，
房间数、边数、陷阱数、饥饿数均未变化。

### 7.2 产出曲线（30 趟/格，weald，standard）

| 配置 | 金币 | 传家宝 | 宝石 | 战斗 | 完成率 |
|---|---|---|---|---|---|
| short Lv1 | 3498 | 9.1 | 3.1 | 5.3 | 0.967 |
| short Lv3 | 4903 | 15.7 | 2.9 | 5.2 | 0.875 |
| short Lv5 | 6364 | 18.7 | 3.0 | 5.1 | 0.833 |
| medium Lv3 | 5721 | 18.6 | 3.8 | 6.1 | 0.600 |
| long Lv3 | 6047 | 22.3 | 4.3 | 6.9 | 0.033 |

难度越高给越多（Lv1 → Lv5 是 1.8 倍）——这是旧常数给不了的东西：
以前「更难」只意味着更容易死，收益一模一样。

### 7.3 奇物贡献（40 趟 short Lv3，注入 3 个走廊奇物）

| | 有奇物 | 无奇物 |
|---|---|---|
| 金币 | 6382 | 4903 |
| 奇物带来 | **1495（23%）** | — |
| 平均遇到 | 2.73 次/趟 | 0 |
| 用掉道具 | 1.13 次/趟 | 0 |
| 完成率 | 0.875 | 0.875 |
| 压迫指数 | 0.750 | 0.698 |

奇物贡献了约四分之一的收入，且**不降低完成率**——因为它是可选的收益，
不是必经的关卡。

### 7.4 开关对照

```bash
--no-loot-table     走 M5 手写常数（bench 下为 0 金）
--no-curio-table    奇物退回一枚硬币
--hall-curio=N      线性路线注入 N 个奇物（默认 0，不动历史基线）
```

---

## 八、已知局限

诚实列出，这些都是「有数据但没落地」的部分：

1. **落地率 63%**（139 个有权重分支里 87 个可执行）。
   **这一条已被 M14 修订**：`quirk` 15 个、`disease` 9 个、`purge` 3 个现在都已落地
   （共 27 个），算上它们后奇物分支的落地率约 82%。剩下的是：
   - `scouting` 4 个 —— 已解析成 `{hops, target}`，但只有 `all` 语义能映射到 M6 侦察
   - 21 条 `scripted`（见下条）
   详见 [M14_QUIRKS.md](M14_QUIRKS.md)。原文保留，是为了记住当时的边界。
2. **21 条 scripted 效果不猜数值**。`Suit of Armor Shield`、`fish_idol_curse_1`
   这类在表里只有名字、没有数值（实际在游戏脚本里）。一律标 `scripted` 并计数
   （`stats.curio_unsupported`），**不编一个数字**——编出来的数会让后续所有
   对照实验失去意义。道具交互里另有 9 条同类。
3. **`Blight N` / `Bleed N` 的落地是自定的**：没有战斗外 DOT 承载，
   折算成全队 `hp_ratio - N×2%`。方向对（奇物陷阱会掉血），但比例是拍的。
4. **饰品只计数不装备**（`loot_trinkets`）。`trinkets.json` 有完整数据，
   但没有装备位，属于下一期。
   **已被 M15 修订**：现在有仓库（16 格）+ 每人 2 格，掉落直接入库，
   见 [M15_TRINKETS.md](M15_TRINKETS.md)。原文保留，是为了记住当时的边界。
5. **宝石直接折成金币**。没有商店库存，宝石除了卖钱没有别的用途，
   单开一个「宝石袋」只会让结算屏多一行没人看的东西。件数在结算屏有报。
6. **走廊上的奇物没有预览**。走过去才知道是什么——这是 DD1 的行为，
   但 `edges_known`（M8 侦察）本可以让它更可读，本期没接。
7. **`_grant_complete_loot` 仍是旧常数**（45+22×场次）。现在只占总收入约 4%，
   语义上它是「任务报酬」而非掉落，保留是合理的，但如果你想让通关更有分量，
   应该改成按 quest 奖励表抽。

---

## 九、怎么跑

```bash
GODOT="D:/XT/godot/Godot_v4.7.2-stable_win64_console.exe"

# 1. 重新生成奇物数据（改了 curio_design_table.json 之后必跑）
python tools/gen_curios.py

# 2. 全量断言（含 M13 的 93 项新断言，总 583）
"$GODOT" --headless --path . --script res://tests/run_tests.gd

# 3. 产出曲线：尺寸 × 难度
"$GODOT" --headless --path . --script res://tests/bench_expedition.gd -- \
  --runs=30 --size=short --level=1 --presets=standard \
  --out="D:/XT/codex/projectTestCodexDocs/darkestDungeonLike/bench/m13_yield_short_lv1.json"

# 4. 奇物贡献（注入 3 个走廊奇物）
"$GODOT" --headless --path . --script res://tests/bench_expedition.gd -- \
  --runs=40 --size=short --level=3 --presets=standard --hall-curio=3 \
  --out="D:/XT/codex/projectTestCodexDocs/darkestDungeonLike/bench/m13_curio_on_short.json"

# 5. 关掉真表做对照
"$GODOT" --headless --path . --script res://tests/bench_expedition.gd -- \
  --runs=40 --size=short --level=3 --presets=standard --no-loot-table --no-curio-table \
  --out="D:/XT/codex/projectTestCodexDocs/darkestDungeonLike/bench/m13_legacy_short.json"

# 6. 端到端自检（会打印「SELFTEST 战利品 金币=N 传家宝=M」）
"$GODOT" --headless --path . -- --selftest --size=medium --level=3 --save=user://t13.json
```

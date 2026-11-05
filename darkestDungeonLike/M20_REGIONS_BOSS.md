# M20 · 区域与首领

> 一句话：`dungeons.json` 里四个区域的遭遇表、地图参数、奇物池、首领遭遇全是分开的，
> 但代码第 26 行写死了 `var _dungeon: String = "weald"`——另外三个区域、
> 三十条首领数据，从 M7 到 M19 一次都没露过面。

## 1. 起点：一条硬编码挡掉了 4/5 的内容

`expedition_scene.gd:26`：

```gdscript
var _dungeon: String = "weald"
```

`_dungeon` 一共只用在 6 个地方（生成地图、set_location、日志、三处标题）。
改起来不难，难的是发现它——因为游戏**跑得通**，只是你永远在同一个地方打同样的怪。

数据这边的实际情况：

| 数据 | 覆盖 | M19 之前用到 |
|---|---|---|
| `encounters.{region}.{1..5}` | cove / crypts / warrens / weald / darkestdungeon | 只有 weald |
| `maps`（44 条） | 4 区域 × 6 种 quest_type × 3 尺寸 | 只有 weald / explore / 3 档 |
| `props`（奇物池） | 按区域分开 | `CurioLib` 其实早支持按区域取，只是永远收到 `weald` |
| `encounters.*.boss` | 每个区域每级 2–3 组，共 30 条 | **一次都没读过** |

最后一行是这一期的主要工作量：`boss` 这个键从来没被 `map_gen.gd` 查询过——
它只查 `hall` 和 `room`。

## 2. 区域选择

城镇「出发」那行改成一行选择器：`荒野 / 墓穴 / 猪人巢穴 / 海湾`，
右边跟一句该区域的定位（从遭遇表归纳，不是原版文案）：

| 区域 | 定位 | 主要敌人 |
|---|---|---|
| weald 荒野 | 野兽与土匪 · 硬碰硬 | rabid_dog / fungal / cultist |
| crypts 墓穴 | 骷髅与死灵 · 抗性高 | 骷髅系 + necromancer |
| warrens 猪人巢穴 | 肮脏拥挤 · 数量多 | swine / formless |
| cove 海湾 | 鱼人与深海 · 控制多 | fishman / snail_urchin |

切换区域只影响下一次出发，不改难度、不消耗资源。

## 3. 首领任务

### 数据这边已经齐了

```
cove    Lv1: siren_A / drowned_captain_A
crypts  Lv1: necromancer_A / prophet_A
warrens Lv1: swine_prince_A / formless_*_A
weald   Lv1: hag_A / brigand_cannon 群 / crow_A
```

`maps` 里也各有 `kill_boss` 的地图参数（图比 explore 短：
weald medium 11 间房 vs 14 间，`min_final_distance` 3 vs 7）。

### 接法

改动很小，因为 `Expedition.travel` 本来就会把 `rooms[id].step` 压进待结算队列：

1. `MapGen.build(..., quest_type)` → `db.map_for(dungeon, size, quest_type)`
2. `_fill_contents` 末尾：`quest_type == "kill_boss"` 时，给**终点房间**塞一个战斗步
3. `K_BOSS` 房间类型，地图上画红色「王」
4. `Expedition` 记两个字段：`boss_fought`（真的开了那仗）、`boss_killed`（打赢了）

**`boss_fought` 单独记是有原因的**：只报击杀率的话，「没走到终点就团灭」
和「走到终点打输了」会混成一件事，而这是两种完全不同的病。

### 任务判据：不能「跑出去就算完成」

第一版跑出来一条反直觉的结果：`打到=true 击杀=false 结果=complete`——
玩家打到首领、打输了、队伍还没全灭，然后走出地牢，结算屏写「走出地牢」并给完成奖励。

修在 `_end()` 里：

```gdscript
if reason == "complete" and quest_type == "kill_boss" and not boss_killed:
    reason = "incomplete"
```

单独给一个 `incomplete` 而不是并进 `retreat`：
撤退是玩家主动放弃，这个是「到了地方没打下来」，两者的压力惩罚该不一样。
结算屏标题：「首领未死 · 任务未完成」。

## 4. 数据

### 四个区域的探索（短图 Lv1，12 趟，`--skills=loadout`）

| 区域 | 完成率 | 团灭率 | 压迫指数 |
|---|---|---|---|
| weald | 0.917 | 0.083 | 0.375 |
| crypts | 0.917 | 0.083 | 0.442 |
| warrens | 0.917 | 0.083 | 0.358 |
| cove | 1.000 | 0.000 | 0.158 |

完成率几乎一样（短图 Lv1 本来就松），但**压迫指数差了近 3 倍**——
说明遭遇表确实换了一套，不是换了个名字。

### 首领任务（海湾 medium Lv1，10 趟）

| 指标 | 值 |
|---|---|
| 走到终点（打到首领） | 0.900 |
| 击杀首领 | 0.400 |
| 完成（=击杀后离开） | 0.400 |
| 团灭 | 0.500 |

和探索短图对比：**同一批 0 阶队伍，短图 0.917 完成，首领任务 0.400**。
这个落差是对的——首领战是单场定生死，不是多打一场怪。

medium Lv3 的首领任务则 3/3 全部**没走到终点就团灭**，
和 M19 的结论一致（0 阶队伍打 medium Lv3 本身就过不去），不是首领机制的问题。

## 5. 踩的坑

**1. 一个手滑字符，卡了 3 分钟。**

编辑 `_ready` 的分支链时把 `if _auto_start:` 改成了 `el	if _auto_start:`，
`--check-only` 当时没跑（改动后直接去跑自检了）。
Godot 的解析错误信息和正常输出一样打到 stdout，被我的 `grep SELFTEST` 全过滤掉了，
看起来就是「进程跑了三分钟没结果」。真实原因只有一行：

```
SCRIPT ERROR: Parse Error: Expected "else" after ternary operator condition.
   at: GDScript::reload (res://src/view/expedition_scene.gd:212)
```

教训：**改完先 `--check-only`，再跑任何会 grep 的批量任务**。
grep 会把「报错」和「没跑到」变成同一种现象。

**2. 探索地图的终点「有 step」。**

测试写的是 `rooms[goal].has("step") == false`，结果失败——
因为房间结构初始化时**永远带一个空的 `step` 键**。
判的应该是 `.is_empty()`，不是 `has()`。

这和 M13「按标签行 continue 吃掉 outcome 分支」是同一类错误：
把「键存在」和「有内容」当成一回事。

## 6. 复现

```bash
GODOT="D:/XT/godot/Godot_v4.7.2-stable_win64_console.exe"

# 全量断言（922 项，M20 新增 13 项）
"$GODOT" --headless --path . --script res://tests/run_tests.gd

# 四区域探索对照
for d in weald crypts warrens cove; do
  "$GODOT" --headless --path . --script res://tests/bench_expedition.gd -- \
    --runs=12 --size=short --level=1 --presets=standard --skills=loadout --dungeon=$d
done

# 首领任务：打到 / 击杀 分开报
for i in $(seq 1 10); do
  "$GODOT" --headless --path . -- --selftest --dungeon=cove --quest=kill_boss \
    --size=medium --level=1 --save=user://m20_$i.json
done | grep "SELFTEST 首领"

# 截图
"$GODOT" --path . -- --save=user://m20_alive.json --shot=shots/m20_town.png --shot-at=2
"$GODOT" --path . -- --save=user://m20_alive.json --dungeon=cove --quest=kill_boss \
  --size=medium --level=1 --start --reveal --shot=shots/m20_boss_map.png --shot-at=2
```

## 7. 没做的

- **首领只有 medium 一档入口**：`kill_boss` 数据有 medium 和 long，界面只给了 medium。
  long 的首领任务（14 间房走到终点）对 0 阶队伍基本是送死，等装备曲线稳了再开。
- **首领信息不透明**：准备屏不告诉你这趟会遇到谁。原版会在任务卡上写首领名字，
  这里只有一句「终点必有首领」。
- **其他 quest_type 没接**：数据里还有 `cleanse`（12 条）/ `gather` / `activate` /
  `inventory_activate`，每个区域都有。它们需要各自的任务目标（净化几个房间、
  收集几件东西），是比「到终点打一场」复杂得多的机制。
- **至暗之地没接**：`darkestdungeon` 的遭遇表只有 Lv6，地图参数也是 medium 起步，
  而且它的奇物池是 `chance 1` 全给——那是终局内容，不是这一期该开的。

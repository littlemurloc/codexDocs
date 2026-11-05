# M21 · 可读性：名字与出发情报

> 一句话：十九期做下来，玩家打了一整场仗，屏幕上写的是 `Cultist Brawler`；
> 城镇里五个英雄叫 `Crusader / Highwayman / Vestal`；
> 出发前唯一的信息是「中程 · 3 级怪」——不知道对面是疯狗还是骷髅。

## 1. 起点：`display_name = monster_id`

`combatant.gd:136`：

```gdscript
display_name = monster_id
```

表现层其实没读 `display_name`，用的是 `DdTheme.pretty(u.def_id)`——
把 `cultist_brawler_A` 去掉难度后缀、下划线换空格、首字母大写，得到 `Cultist Brawler`。

所以整局游戏里：

| 位置 | 之前 | 现在 |
|---|---|---|
| 战斗单位 | `Cultist Brawler` | 邪教打手 |
| 英雄卡 / 战斗 | `Crusader` | 十字军 |
| 技能按钮 | `Smite` | 惩击（M19 已修） |
| 日志 | `Crusader ← Cultist Brawler 5` | 十字军 ← 邪教打手 5 |
| 传家宝 | `bust 5` | 半身像 5 |
| 结算「永久损失」 | `Vestal` | 修女 |

M19 修了技能名，但**英雄、怪物、传家宝三张表一直是空的**。
这不是「没翻译」，是「没建表」——`pretty()` 是个兜底，用了十九期没人觉得不对。

## 2. 三张表 + 一个统一入口

| 表 | 数量 | 范围 |
|---|---|---|
| `HERO_NAMES` | 15 | 全部英雄（名册只用 5 个，但 M20 之后随时换人） |
| `MONSTER_NAMES` | 61 | 四个区域遭遇池 + 首领池里**真的会出现**的基础怪 |
| `HEIRLOOM_NAMES` | 4 | 表早就有了，只是 UI 一直没用（这次接上） |

`MONSTER_NAMES` 的 key 是**不带难度后缀**的 id：`cultist_brawler_A/B/C` 只是数值不同，
对玩家来说是同一个东西，名字必须一样。查表前先剥 `_A/_B/_C/_D`。

统一入口：

```gdscript
DdTheme.unit_name(id)   # 战斗/日志：先认英雄，再认怪物，都不认识才 fallback
DdTheme.hero_name(id)
DdTheme.monster_name(id)
```

然后 sed 批了 23 处调用点。**这一步不能靠人眼找**：`pretty()` 在场景里有 26 处，
其中 4 处不是单位名（gems 的 key、slot 名、区域列表），批量替换前必须先分类。

## 3. 出发情报

原来难度卡上只有「中程 · 3 级怪 / 7-8 场，补给吃紧」——
玩家知道路有多长，不知道路上是什么。

现在每张卡多一行：

| 卡片 | 情报行 |
|---|---|
| 短途 1 级（荒野） | 主要：食腐兽、疯狗 |
| 中程 3 级（荒野） | 主要：邪教打手、邪教女巫 |
| 长途 5 级（荒野） | 主要：疯狗、巨型章鱼 |
| 首领 3 级（荒野） | 首领：空坩埚、沼泽老妪 |

数据来自新增的 `DdDb.encounter_outline(dungeon, level)`：

- 把 `hall` + `room` 两张表里的 `types` 按**基础 id** 计数，取前 3
- `boss` 行的 `types` 全给（每级只有 2–3 组）
- 排序带二级 key（频次相同时按 id 字典序），**保证同一次调用两次结果一致**，
  否则截图和文档对不上

**只报「可能出现哪几种」，不报「这趟一定是哪只」**：遭遇是随机抽的，
写死一个名字等于撒谎。原版任务卡也只给情报，不给答案。

## 4. 数据

测试里加了一条**全量扫描**：

```gdscript
for 每个区域 → 每级 → hall/room/boss → 每个 type:
    base = 去难度后缀(id)
    if not MONSTER_NAMES.has(base): missing.append(base)
t.eq(missing, [])
```

第一次跑就抓出 3 个漏网的：`shambler`（蹒跚者）、`collector`（收藏家）、
`carrion_eater_large`（大型食腐兽）。

**它们出现在 `conditional_*` 那几张表里**——我手工统计时只看了 `hall` / `room` / `boss`。
人眼统计必然会漏，而漏掉的那几个只会在「这一局恰好遇到它」时露出英文 id。

## 5. 踩的坑

**批量替换前必须分类。**

`DdTheme.pretty` 在 `expedition_scene.gd` 里有 26 处调用，长得几乎一样：

```gdscript
DdTheme.pretty(hid)                              # 英雄 → hero_name
DdTheme.pretty(u.def_id)                         # 英雄或怪 → unit_name
DdTheme.pretty(str(k))                           # 传家宝 → heirloom_name
DdTheme.pretty(str(action.id))                   # 技能 → skill_name（M19 修过）
DdTheme.pretty(str(i))                           # 遭遇的怪 → monster_name
```

一刀切全改成 `unit_name` 会「看起来都对」，但传家宝会去怪物表里查、
技能名会去英雄表里查，然后全部 fallback 成 `Pretty Id`——和改之前一样烂，
只是烂得更隐蔽。

所以做法是：先 `grep -n` 全列出来，按「这个变量是什么类型」分八组，
每组一条 sed，没把握的四处手工改。

## 6. 复现

```bash
GODOT="D:/XT/godot/Godot_v4.7.2-stable_win64_console.exe"

# 全量断言（931 项，M21 新增 9 项：三张表的覆盖率 + 情报摘要稳定性）
"$GODOT" --headless --path . --script res://tests/run_tests.gd

# 截图
"$GODOT" --path . -- --save=user://m21_alive.json --shot=shots/m21_town.png --shot-at=2
"$GODOT" --path . -- --save=user://m21_alive.json --dungeon=cove --size=short --level=1 \
  --auto --fast --shot=shots/m21_battle.png --shot-at=5
```

## 7. 没做的

- **技能描述文本**：M19 说过，这一行仍是从数值反推的
  （「近战 · 可从 1、2 位发动 · 打敌方 1、2 位 · 命中 +85%」），
  原版的完整描述在 `.strings` 里，M0 的管线没抽。
- **怪物的行为情报**：现在只报名字，不报「它会干什么」。
  `monsters.json` 里有它的技能和抗性，但没有「一句话概述」这种数据——
  要报「这只会推人」「这只有高毒抗」，得从技能反推，那是另一期的事。
- **任务类型标签**：`cleanse` / `gather` / `activate` 还没接（M20 提过），
  所以情报里也没法区分「这趟是探索还是净化」。

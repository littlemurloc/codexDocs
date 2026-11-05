# darkestDungeonLike

用 Godot 4 重构一个「机制等价」的暗黑地牢式回合制游戏。

- **M0 数据管线** — 从 DD1 安装目录抽取全部规则数据，产出可查询的 JSON 与自动生成的设计文档
- **M1 战斗核心** — 4 英雄 vs 3 怪物的完整回合结算，规则层纯类、可脱离引擎单测 → 见 [BATTLE_CORE.md](BATTLE_CORE.md)
- **M2 数值生成** — 曲线抽取 → 生成器 → 多套数值包 → 手感测量 → 见 [BALANCE.md](BALANCE.md)
- **M3 资源层** — 光照/口粮/休整/崩溃，把「一场战斗」变成「一段路程」 → 见 [M3_EXPEDITION.md](M3_EXPEDITION.md)
- **M4 可玩循环** — 出发/地图/战斗/结算四屏，鼠标可玩，带端到端自检 → 见 [M4_PLAYABLE.md](M4_PLAYABLE.md)
- **M5 元层** — 战利品/城镇/升级/永久阵亡/存档，两趟之间终于有得失 → 见 [M5_CAMPAIGN.md](M5_CAMPAIGN.md)
- **M6 战前情报** — 光照决定你能提前看见多远，让「休整/点火把/撤退」变成有信息的决策 → 见 [M6_SCOUTING.md](M6_SCOUTING.md)
- **M7 房间图** — 从「一条线」到随机生成的房间/走廊/岔路，玩家开始选路 → 见 [M7_MAP.md](M7_MAP.md)
- **M8 走廊内容** — 陷阱与障碍 + 走廊可见性；侦察链闭合，也修掉了 M7「假分岔」 → 见 [M8_HAZARDS.md](M8_HAZARDS.md)
- **M9 站位** — 位移从死代码变成真的会动，英雄第一次能主动换位 → 见 [M9_MOVEMENT.md](M9_MOVEMENT.md)
- **M10 守护与反击** — 替队友挨打、被打就还手；又是两段数据齐备但从未执行的机制 → 见 [M10_GUARD.md](M10_GUARD.md)
- **M11 怪物位移** — 怪物推拉、洗位、位移抗性；「怪物不会推人」其实有三层原因，不是数据没有 → 见 [M11_MONSTER_MOVE.md](M11_MONSTER_MOVE.md)
- **M12 召唤** — 59 个召唤效果、35 只怪从 `unsupported` 变成真的会叫人来；顺手暴露了「数据没有上限」这一层 → 见 [M12_SUMMON.md](M12_SUMMON.md)
- **M13 道具与奇物** — 61 份抽卡表、60 个奇物、46 条道具交互从「数据在、无人读」接进游戏；顺带发现 A 表根本没被加载、经济差一个数量级 → 见 [M13_ITEMS_CURIOS.md](M13_ITEMS_CURIOS.md)
- **M14 怪癖与疾病** — 170 个怪癖（含 23 个疾病）、195 条 buff 引用、15 种触发条件接进游戏；顺带查出两处「异常被吞、看起来什么都没发生」→ 见 [M14_QUIRKS.md](M14_QUIRKS.md)
- **M15 饰品** — 490 件饰品、1964 条 buff 引用从「拿到就扔」接成仓库 + 每人 2 格 + 战斗生效；规则判定抽成 `BuffRules` 供怪癖与饰品共用 → 见 [M15_TRINKETS.md](M15_TRINKETS.md)
- **M16 城镇经济** — 补给采购 + 饰品商店把 `price` / `purchase_gold_value` / `sell_gold_value` 三组沉睡数据接上；顺带修掉「火把同时有两个数字」的口径分裂 → 见 [M16_TOWN_ECONOMY.md](M16_TOWN_ECONOMY.md)
- **M17 内容密度** — 走廊奇物从 9%/14%/19% 提到 60% 下限，图上奇物 ×3（短图 0.57→3.07）；同时查清「玩家只走 5.5 步，遇到的是图上的 21%」→ 见 [M17_CONTENT_DENSITY.md](M17_CONTENT_DENSITY.md)
- **M18 远征节奏** — 查清「走不完图」的真因是 M10 换人欠的债（战争老兵完成率比十字军低 23 个百分点）；名册扩到 5 人、出战 4 人由玩家选；顺带修掉「逐步驱动没有回合上限」导致的 228 回合死斗 → 见 [M18_EXPEDITION_PACE.md](M18_EXPEDITION_PACE.md)
- **M19 技能组** — `heroes.json` 的 `skill_selection`（每人只能带 4 个）从 M0 就抽好了，十九期没人读；现在每个英雄要真的做取舍，城镇多一个公会用来看技能 → 见 [M19_SKILL_LOADOUT.md](M19_SKILL_LOADOUT.md)
- **M20 区域与首领** — `_dungeon` 写死 `weald` 挡掉了另外三个区域的全部内容；30 条首领遭遇 M7 起一次没被查询过。现在四个区域可选，终点房间会刷首领，任务判据是「首领死了才算完成」 → 见 [M20_REGIONS_BOSS.md](M20_REGIONS_BOSS.md)
- **M21 可读性** — 打完一场仗屏幕上写着 `Cultist Brawler`，城镇里叫 `Crusader`：三张名字表一直是空的，靠 `pretty()` 兜底了十九期。现在英雄/怪物/传家宝全部中文，难度卡多一行「主要：食腐兽、疯狗」 → 见 [M21_READABILITY.md](M21_READABILITY.md)
- **M22 城镇建筑** — 八座建筑原来被压成「英雄卡上两个按钮 + 右下角三个按钮」；疗养院让 M14 起就没人调用的 `cure` 终于有了入口，修道院/酒馆把写死的「回城减 40 压力」变成两档取舍 → 见 [M22_BUILDINGS.md](M22_BUILDINGS.md)
- **M23 周次循环** — 有「趟」没有「周」时，建筑只能是「点了立刻生效」的功能面板；现在一趟 = 一周，进建筑占一周、这一周他不能出征，一周只能办一件事 → 见 [M23_WEEKS.md](M23_WEEKS.md)
- **M24 主动过一周** — M23 的时间只能「打完一趟顺便过」，所以派去疗养院的人不打仗就永远不结束；现在花 50 金可以什么都不做直接过一周（压力 −10、建筑队列前进），代价是没有收入 → 见 [M24_IDLE_WEEK.md](M24_IDLE_WEEK.md)
- **M25 决心等级** — 二十四期以来难度的唯一来源是「玩家愿意挑多难」；补上原版的等级轴：英雄练到 3 级以上就**拒绝再进学徒本**，装备阶也卡在等级上。现在「往高难度走」是唯一出路，而不是可选项 → 见 [M25_RESOLVE.md](M25_RESOLVE.md)
- **M26 任务板** — M25 的锁只负责「不让你往下走」，而城镇那四张难度卡的等级是写死的常量，玩家永远能挑低的那张。现在每周按名册重抽，但留一格给名册里最弱的人 → 见 [M26_BOARD.md](M26_BOARD.md)
- **M27 名册扩容** — 名册从 M0 起就是固定 5 人（`_order` 只在开新档时写过一次），M25/M26 的所有妥协都长在这上面；现在能从马车招新职业，上限 15（= 职业总数） → 见 [M27_ROSTER.md](M27_ROSTER.md)
- **M28 解雇** — M27 让名册能扩到 15 人，但只能加不能减：满了没法换人、练废的人只能一直占位置。现在马车能把人赶走（免费，等级和装备一起归零），按钮要点两次 → 见 [M28_DISMISS.md](M28_DISMISS.md)
- **M29 受压 +25%/级** — M25 的等级惩罚只做了一半（进本白吃 20 压力），那是一次性的，撑过前两场就回本；现在低等级打高级本会全程更疼。两条惩罚的难度贡献几乎相等 → 见 [M29_STRESS_PENALTY.md](M29_STRESS_PENALTY.md)
- **M31 界面分层与设计令牌** — 831 行的主题文件里 770 行是名字表，176 处字号有 9 档，同一个「选中」有三种长相。这一期拆文件、定六档字号、把开发信息收进 `--dev`、统一可点方块，并顺手修掉公会屏名册溢出屏幕、憎恶显示「已装备 0 / 7」、70 个技能名缺失 → 见 [M31_UI_LAYERING.md](M31_UI_LAYERING.md)
- **M32 分区任务板与目标层** — `quests.json` 的 6 种任务、48 个目标从 M0 抽出来就没人读过，任务在代码里只是一个字符串。这一期让任务板长在区域上（四区各一块、每区槽位不同）、把判据抽成 `QuestGoal`、接上「清剿」（清光图上全部战斗，走到出口不算完成）；顺手查出 10 个任务奇物里 **9 个在抽取数据里根本不存在** → 见 [M32_TASK_BOARD.md](M32_TASK_BOARD.md)
- **M33 任务奇物标签化** — 那 9 个不存在的任务奇物不能硬编 id 冒充，只能把目标**降到标签层**（`Worship` / `Food` / `Scrounging`…），在该区域里解析成真实奇物；地图按需额外投放（否则收集任务必然做不完），接上「收集」与「激活」，任务类型从 3 种变 4 种 → 见 [M33_QUEST_CURIOS.md](M33_QUEST_CURIOS.md)
- **世界观** — 已定典：**空腔**。一座城把城名抵押出去换了活路，三百年后另一座城靠在它的抵押物上捞东西活着 → 见 [WORLD.md](WORLD.md)
- **图志** — 十二幅插画 + 注记，可翻阅的设定集图册；画风、构图与十二张清单见 [WORLD_INSERTS.md](WORLD_INSERTS.md) → 见 [ATLAS.html](ATLAS.html)
- **图鉴（正文）** — 城的地面十一个生活区与功能建筑、六族十三行的职业与过往、地下四层的生态与原住民、最终底层磨心 → 见 [CODEX.md](CODEX.md)（排版稿 [CODEX.html](CODEX.html)，由 `tools/gen_codex.py` 生成）

不含任何来自 DD1 的美术或音频资源。

## 工程结构

```
src/core/            规则层（纯 GDScript，不挂节点）
  dd_rng.gd          确定性随机数，用于跨语言逐位对账
  dd_rules.gd        rules.json 的类型化包装（含光照/饥饿/营地常量）
  dd_db.gd           数据索引（唯一的数据入口）
  combatant.gd       战斗单位（含死门/崩溃/美德的跨战斗状态）
  damage_formula.gd  伤害与命中公式（全静态纯函数）
  turn_scheduler.gd  每轮先攻重掷 + 排序
  effect_resolver.gd 效果结算
  battle.gd          回合编排 + 事件广播 + 压力阈值（同步/逐步两套驱动）
  expedition_cfg.gd  资源策略预设（expedition.json）
  route_gen.gd       线性路线（bench 用，口径不变）
  map_gen.gd         房间图生成：撒房间 / 连走廊 / 选端点 / 投内容
  quest_goal.gd      任务目标判定：解析 quests.json / 判进度 / 判完成（元层与自检共用）
  skill_loadout.gd   技能组判定：默认组 / 存档清洗 / 上限（元层与 bench 共用）
  expedition.gd      远征编排：光照/口粮/休整/撤退/状态延续/战利品
  campaign.gd        元层：存档、账、名册、升级、招募、结算
src/view/            表现层（只订阅事件，不含规则）
  expedition_scene   ★ 主场景：城镇 / 地图 / 战斗 / 结算四屏
  main.tscn          M1 战斗切片（保留可单独跑）
  dd_theme.gd        共用色板与文本工具
tests/               测试、战报工具、跨语言基准、两个测量器、端到端自检
tools/               数据抽取与代码生成
data/                抽取出的结构化数据
  expedition.json      资源层策略预设（M3）
  campaign.json        战利品曲线与城镇开销（M5）
```

## 为什么先做数据管线

DD1 的规则、数值、内容全部以明文散落在安装目录里（`.darkest` DSL + JSON + CSV），
逻辑层编译在 `Darkest.exe` 中。把数据层完整抽出，等于拿到一份**可机读的完整设计文档**，
之后写 Godot 逻辑时不必再猜数值。

## 目录结构

```
tools/
  darkest_parser.py     .darkest DSL 解析器（tokenizer + 记录模型）
  extract.py            抽取驱动：解析 → 归一化 → JSON
  gen_doc.py            从 JSON 生成 DESIGN.md
  gen_curves.py         提炼「数值生成器参数」+ 生成 curves.html
  gen_balance.py        ★ 数值包生成器：设计旋钮 → 完整数值目录
  compare_balance.py    ★ 多套数值包的指标对比（单场）
  compare_expedition.py ★ 远征指标对比 + 目标判定（M3）
  ref_impl.py           伤害公式的 Python 参考实现（交叉验证基准）
data/                    ★ DD1 原数值包（参照基线，不要手改）
  expedition.json       ★ 资源层策略预设（lenient/standard/tight/brutal）
balance/
  faithful/             忠实复刻曲线，用于校准生成器
  signature/            自研规格（详见 BALANCE.md）
  signature_v2/         signature 的远征修正版（详见 M3_EXPEDITION.md）
  lethal_probe/         诊断用：检验测量器能否测出危险度
bench/                  各规格的实测指标 JSON + compare.md
  exp_*.json            ★ 远征测量结果（不同数值包 / 不同图长）
  heroes.json           15 名英雄，技能按 id 聚合 5 个等级
  monsters.json         254 个怪物变体（101 家族）
  effects.json          1215 条效果定义（技能执行的最小单元）
  buffs.json            2020 条 buff
  dungeons.json         44 套地图参数 + 45 张遭遇表 + 各区奇物刷新权重
  loot.json             58 张掉落表（支持表套表嵌套）
  trinkets.json         490 件饰品
  quirks.json           170 个怪癖（正/负面）
  quests.json           任务生成规则、剧情任务、类型定义
  inventory.json        52 个物品定义
  curio_props.json      62 条奇物 → 精灵图/音频映射
  curio_design_table.json  奇物交互设计表（策划草稿，未结构化）
  rules.json            战斗数学常量（含 raid_settings）
  balance_curves.json   ★ 数值生成器参数（不是数值表，是生成数值的规则）
  stats.json            计数与校验结果
  _raw/all_records.json 699 个 .darkest 文件的全部原始记录，可回溯任意数值出处
DESIGN.md               自动生成的设计文档
BATTLE_CORE.md          战斗规则：公式顺序 + 假设清单（含置信度分级）
BALANCE.md              ★ 数值生成器与手感测量：signature 规格的设计意图与验证
curves.html             ★ 自包含可视化：平衡空间、成长曲线、难度阶梯
```

## 为什么需要 balance_curves.json

抄数值会作废，抄曲线才能复用。从数据里能验证出的结构性规律：

| 规律 | 证据 |
|---|---|
| 英雄生命是等差数列 | 15/15 英雄全部符合 `基准 + 成长档 × 装备阶`，成长档只有 5 个离散值（+3~+7） |
| 英雄闪避是统一斜率 | 15/15 英雄均为 `基础 + 5% × 装备阶`，无一例外 |
| 技能升级不加伤害 | 387 次逐级比较，伤害修正的差值全部为 0；只加命中 +5%、暴击 +1% |
| 伤害成长藏在效果里 | effect 的 `damage_low_multiply` 每级 +5%（28 组多层伤害效果的中位增量） |
| 怪物变体是难度分层 | A/B/C/D 对应地牢 1/3/5/6 层（从遭遇表反推：1 层 133 处全 A，3 层 193 处全 B） |
| 难度阶梯非等比 | A→B 生命 ×1.415 / 伤害 ×1.500；B→C 生命 ×1.381 / 伤害 ×1.250 |
| 饰品稀有度 = 槽位数 | very_common 2.0 → rare 3.24 → very_rare 3.88，是槽位预算不是强度 |

结论：**101 个怪物设计撑起 254 个变体**，内容量与数值都不是手调的散点，而是参数生成的结果。
你要复刻的是这套生成规则，而不是它的输出。

## 重跑

```bash
GODOT="D:/XT/godot/Godot_v4.7.2-stable_win64_console.exe"

# 数据管线
python tools/extract.py --game "D:/Program Files (x86)/Steam/steamapps/common/DarkestDungeon"
python tools/gen_doc.py
python tools/gen_curves.py

# 战斗核心测试（规则层不依赖引擎场景）
"$GODOT" --headless --path . --script res://tests/run_tests.gd

# 数值包（M2）：--data 要传绝对路径
python tools/gen_balance.py
"$GODOT" --headless --path . --script res://tests/bench_battle.gd -- \
  --runs=200 --data="D:/XT/codex/projectTestCodexDocs/darkestDungeonLike/balance/signature" \
  --out="D:/XT/codex/projectTestCodexDocs/darkestDungeonLike/bench/signature.json"
python tools/compare_balance.py dd1_baseline faithful signature

# 远征（M3）：四档资源 × 60 趟，再看别的数值包
"$GODOT" --headless --path . --script res://tests/bench_expedition.gd -- \
  --runs=60 --size=medium --level=3 \
  --out="D:/XT/codex/projectTestCodexDocs/darkestDungeonLike/bench/exp_data_medium.json"
"$GODOT" --headless --path . --script res://tests/dump_expedition.gd -- --preset=standard --seed=3
python tools/compare_expedition.py

# 可玩循环（M4）：直接开窗口玩，或者跑端到端自检
"$GODOT" --path .
"$GODOT" --headless --path . -- --selftest --size=medium --level=3

# 走廊内容（M8）：三策略对照，看信息到底值不值钱
"$GODOT" --headless --path . --script res://tests/bench_hazards.gd -- --runs=120

# 房间图（M7）：看生成结果 / 批量统计 / 截图整张图
"$GODOT" --headless --path . --script res://tests/dump_map.gd -- --size=medium --seed=3
"$GODOT" --headless --path . --script res://tests/dump_map.gd -- --stats --runs=60
"$GODOT" --path . -- --start --reveal --save=user://m.json

# 元层（M5）：换一份存档玩，不污染主档
"$GODOT" --path . -- --save=user://test.json
"$GODOT" --headless --path . -- --selftest --size=short --level=1 --save=user://t.json

# 守护与反击（M10）：默认队伍不该有任何变化；带守卫才触发
"$GODOT" --headless --path . --script res://tests/bench_battle.gd -- \
  --runs=200 --data=balance/faithful \
  --heroes=man_at_arms,highwayman,vestal,plague_doctor
"$GODOT" --path . -- --auto --fast --show-guard --shot=shots/m10_guard.png --shot-at=14

# 怪物位移（M11）：默认队伍不该变化；带位移的怪在 move_probe 里
"$GODOT" --headless --path . --script res://tests/bench_battle.gd -- \
  --runs=200 --data=balance/faithful
"$GODOT" --headless --path . --script res://tests/bench_expedition.gd -- \
  --runs=120 --size=medium --level=3 --data=balance/faithful

# 召唤（M12）：默认队伍仍不该变化；召唤怪在 summon_probe 里
"$GODOT" --headless --path . --script res://tests/bench_battle.gd -- \
  --runs=60 --data=balance/faithful --out=bench/m12_probe.json
# 同路线关掉召唤，看它到底改了多少
"$GODOT" --headless --path . --script res://tests/bench_expedition.gd -- \
  --runs=60 --size=medium --level=3 --data=balance/faithful --no-summon

# 道具与奇物（M13）：先重新生成奇物数据，再量产出曲线
python tools/gen_curios.py
# 真表产出：难度越高给越多（short Lv1 3498 → Lv5 6364 金/趟）
"$GODOT" --headless --path . --script res://tests/bench_expedition.gd -- \
  --runs=30 --size=short --level=1 --presets=standard --out=bench/m13_yield_short_lv1.json
# 走廊奇物贡献：注入 3 个奇物，与不注入对照（约 +1495 金/趟）
"$GODOT" --headless --path . --script res://tests/bench_expedition.gd -- \
  --runs=40 --size=short --level=3 --presets=standard --hall-curio=3 --out=bench/m13_curio_on_short.json
# 关掉真表回到 M5 手写常数（对照用）
"$GODOT" --headless --path . --script res://tests/bench_expedition.gd -- \
  --runs=40 --size=short --level=3 --presets=standard --no-loot-table --no-curio-table

# 怪癖与疾病（M14）：默认不加怪癖，所以历史和上面逐位一致
"$GODOT" --headless --path . --script res://tests/bench_expedition.gd -- \
  --runs=40 --size=short --level=3 --presets=standard --quirks=0 --out=bench/m14_final_base.json
# 每人 6 条全负面 → 压迫 0.698→0.925、崩溃 0.75→1.18、多打 1.8 轮
"$GODOT" --headless --path . --script res://tests/bench_expedition.gd -- \
  --runs=40 --size=short --level=3 --presets=standard --quirks=6 --quirk-polarity=neg
# 每人 6 条全正面 → 完成率 0.875→0.975、死亡 0.72→0.23
"$GODOT" --headless --path . --script res://tests/bench_expedition.gd -- \
  --runs=40 --size=short --level=3 --presets=standard --quirks=6 --quirk-polarity=pos
# 奇物 → 怪癖的真实转化率（注入 6 个走廊奇物，约 0.325 条/趟）
"$GODOT" --headless --path . --script res://tests/bench_expedition.gd -- \
  --runs=40 --size=short --level=3 --presets=standard --hall-curio=6 --out=bench/m14_curio6.json

# 饰品（M15）：默认没人戴，所以历史和上面逐位一致
"$GODOT" --headless --path . --script res://tests/bench_expedition.gd -- \
  --runs=40 --size=short --level=3 --presets=standard --out=bench/m15_base.json
# 干净 A/B：同一批装备，只切开关。关掉那组必须与不戴逐位相同
"$GODOT" --headless --path . --script res://tests/bench_expedition.gd -- \
  --runs=40 --size=short --level=3 --presets=standard --trinkets=2 --trinket-pick=mix
"$GODOT" --headless --path . --script res://tests/bench_expedition.gd -- \
  --runs=40 --size=short --level=3 --presets=standard --trinkets=2 --trinket-pick=mix --no-trinket
# 完成率 0.875→0.950、压迫 0.698→0.492、死亡 0.72→0.42

# 城镇经济（M16）：补给对照。口粮是主力，火把是小头
for m in base nofood notorch lean rich; do
  "$GODOT" --headless --path . --script res://tests/bench_expedition.gd -- \
    --runs=40 --size=short --level=3 --presets=standard --pack=$m \
    --out=bench/m16_pack_$m.json
done
# 无口粮：死亡 0.72→1.35；无火把：死亡 0.72→0.80；带满与默认逐位相同

# 内容密度（M17）：自检会打印「内容」一行，看玩家实际遇到多少
for i in $(seq 1 10); do
  "$GODOT" --headless --path . -- --selftest --size=medium --level=3 \
    --save=user://m17_$i.json
done
# 图上有 6.67 个奇物，实际遇到 1.40 个（只走 5.5 步）

# 技能组（M19）：默认 all = 每人 7 个（M18 及以前的行为），loadout = 每人 4 个
"$GODOT" --headless --path . --script res://tests/bench_expedition.gd -- \
  --runs=30 --size=medium --level=3 --presets=standard --skills=loadout \
  --out=bench/m19_med_loadoutB.json
# 完成率 all 0.600 → loadout 0.400（AI 不会组合技能，这是它的下限）

# 分区任务板与清剿（M32）：自检会打印「任务」一行，看判据有没有真的生效
"$GODOT" --headless --path . -- --selftest --size=short --level=1 --quest=cleanse \
  --save=user://m32.json
# 清剿 10 趟 9 次完成（自检会绕去没清完的战斗房）；换回 explore 就是 M31 的行为

# 收集 / 激活（M33）：这两类只有 medium 一档图参数，传 short 会出发失败
"$GODOT" --headless --path . -- --selftest --size=medium --level=1 --quest=gather \
  --save=user://m33_g.json
"$GODOT" --headless --path . -- --selftest --size=medium --level=1 \
  --dungeon=crypts --quest=activate --save=user://m33_a.json
# 收集 5 趟 4 次完成（荒野→老树，集齐 3 件）；激活 5 趟 5 次（墓穴→铁处女）
```

`--data=` 接受任意路径，所以换数值不用改一行规则代码。
游戏路径可通过 `--game` 覆盖，输出目录通过 `--out` 覆盖。数据管线仅依赖标准库。
战斗核心的细节、公式顺序与假设清单见 [BATTLE_CORE.md](BATTLE_CORE.md)；
数值生成与手感测量见 [BALANCE.md](BALANCE.md)；
资源层与远征测量见 [M3_EXPEDITION.md](M3_EXPEDITION.md)；
可玩循环与端到端自检见 [M4_PLAYABLE.md](M4_PLAYABLE.md)；
战利品、城镇与存档见 [M5_CAMPAIGN.md](M5_CAMPAIGN.md)；
战前情报见 [M6_SCOUTING.md](M6_SCOUTING.md)；房间图生成见 [M7_MAP.md](M7_MAP.md)；
陷阱、障碍与走廊可见性见 [M8_HAZARDS.md](M8_HAZARDS.md)；
站位与位移见 [M9_MOVEMENT.md](M9_MOVEMENT.md)；
守护与反击见 [M10_GUARD.md](M10_GUARD.md)；
怪物位移与洗位见 [M11_MONSTER_MOVE.md](M11_MONSTER_MOVE.md)；
召唤见 [M12_SUMMON.md](M12_SUMMON.md)；
分区任务板与任务目标见 [M32_TASK_BOARD.md](M32_TASK_BOARD.md)；
任务奇物的标签化见 [M33_QUEST_CURIOS.md](M33_QUEST_CURIOS.md)；
世界观、种族、岗位与终局见 [WORLD.md](WORLD.md)（已定典；两个东方方向归档于 `docs/archive/`）；
设定集插画与画风规范见 [WORLD_INSERTS.md](WORLD_INSERTS.md)，成册图志见 [ATLAS.html](ATLAS.html)；
城的地面、职业、地下四层与磨心见 [CODEX.md](CODEX.md)（阅读版 [CODEX.html](CODEX.html)）。

## 数据约定

理解这些约定能避免后面踩坑：

1. **百分数已转小数**。`atk 85%` 存为 `0.85`。字段本身不记单位，靠语义判断。
2. **单值/多值不固定**。`.target 12` 存为 `12`（标量），`.effect "A" "B"` 存为 `["A","B"]`。
   取值时统一用 `as_list()` 式的兼容写法。
3. **站位掩码是整型**。`launch 21` 存为 `21`，转回字符串即 "21"，表示己方 1、2 号位。
   DD1 站位只有 1–4，无前导零，转整型不会丢信息。
4. **英雄技能的 `dmg` 是修正，怪物的 `dmg` 是绝对值**。同名不同义，移植时必须分开处理：
   英雄 `dmg: 0.0` 表示「武器伤害 × 1.0」，怪物 `dmg: [2, 4]` 表示「直接造成 2–4 点」。
5. **未显式建模的记录原样保留**。英雄的 `extra`、怪物的 `extra`（`life_link`、`shared_health`、
   `shape_shifter` 等 32 种机制）都不是丢失数据，只是没做语义归类。

## 已验证项

- 699 个 `.darkest` 文件解析出 **9496** 条记录，**0** 条未解析行
- 1189 条基础效果定义全部提取；英雄与怪物技能引用的效果名 **0** 条缺失（效果图闭合）
- 15 名英雄各有 7 个技能 × 5 个等级，无缺级
- 抽查十字军数值与源文件逐字段一致（抗性、武器 5 阶、护甲 5 阶、技能 5 级、死门 buff）
- 难度档位映射经遭遇表独立验证：地牢 1–2 层用 A、3–4 层用 B、5 层用 C、6 层用 D
- 条形图坐标经数值校验：最长条右端与绘图区边界误差 0.00px
- 战斗核心 **1210 项断言全绿**（含死门/崩溃/治疗配额/跨战斗状态继承/两套驱动等价/元层账目与存档/侦察视野/地图生成/走廊配额与陷阱/位移与换位/守护与反击/怪物位移/召唤/抽卡树与难度变体/奇物分支与道具交互/怪癖条件判定与槽位/饰品稀有度池与装备/规则判定共用件/商店价格与补给口径/内容密度下限语义/名册与出战选择/回合上限与僵持/技能组上限与存档兼容/首领任务判据/名称覆盖率与情报摘要/建筑价格与状态校验/周次推进与占用/主动休整的成本与副作用/决心等级与双向锁/任务板池子与保底档/名册扩容与招新/解雇与名额释放/受压倍率的三层叠乘/技能名与变身职业语义/分区任务板与旧档迁移/清剿分母固定与完成判据/任务奇物标签解析与地图投放/收集计数与位置去重）
- **只在资源层换参数**，完成率可从 0.867 单调压到 0.000（四个数值包全部满足单调）
- `faithful` 包的远征指标与 DD1 数据包**逐项相同**——生成器在两个尺度上都自洽
- 可玩循环端到端自检在 短/中/长 三种规格下全部通过（地图→战斗→选技能→选目标→结算→入账→存档→读档）

## 已知限制

- 只处理基础游戏，未含 DLC（`445700_musketeer` 火枪手英雄、`1117860_arena_mp` 竞技场）。
  竞技场的 `.darkest` 含花括号语法，与主 DSL 不同，已排除。
- `curio_design_table.json` 是策划草稿表格（单元格坐标式）。M13 用 `tools/gen_curios.py` 把它摊平成 `data/curios.json`（60 个奇物 / 480 个 outcome 行），运行时只读摊平后的版本；草稿矩阵仍原样保留以便追溯。
- 逻辑层（效果结算顺序、行动序 tie-break、怪物 AI 评分、地图生成算法）不在数据里，见 `DESIGN.md` 第 8 节。
- 远征层仍是**线性路线**：没有网格地图、分支、回头。自动 AI 不会撤退、不会集火、
  不用道具，所以绝对难度不代表 DD1 真实表现，只有同 AI 下的相对差异有效。
- 可玩层有城镇/战利品/存档/战前情报/怪癖/饰品，但没有建筑、商店与战斗中撤退；崩溃的失控行为只做了「摆烂」一种。
- 饰品已完整可用（490 件 / 1964 条 buff / 落地率 82.7%），但**开局没有饰品**
  （`trinkets.base.starting` 是空数组），自然掉落约 0.6–1.1 件/趟。
  机制完整，前期偏空（见 [M15_TRINKETS.md](M15_TRINKETS.md) §9）。
- 饰品**没有显示名数据**：`trinkets.json` 与 `_raw` 里都没有，界面上的名字是
  按 id 词根拼的（可掉落 196 件覆盖 100%，其余回退英文）。
- 城镇经济已闭环（补给采购 + 饰品买卖），但**前几趟白嫖补给**：新档金币是 0，
  出发走免费保底包。补给也**不能卖**，买多了就浪费
  （见 [M16_TOWN_ECONOMY.md](M16_TOWN_ECONOMY.md) §8）。
- 内容密度已从 9%/14%/19% 提到 60% 下限（图上奇物 ×3）。M18 修正了 M17 的一个
  结论：那个「只走 5.5 步」是**自检走最短路径**的结果，不代表玩家；加了探索模式
  后也只多走 8%——因为地图的支线都是死胡同，没有可规划的绕路
  （见 [M17_CONTENT_DENSITY.md](M17_CONTENT_DENSITY.md) §6、
  [M18_EXPEDITION_PACE.md](M18_EXPEDITION_PACE.md) §1）。
- 名册 5 人、出战 4 人由玩家在出发准备屏选（M18 起）。但**中图对 0 阶队伍仍偏难**：
  medium Lv3 自检 6 趟里 5 趟团灭，有几趟只打 2 场仗就全灭——符合「先打短图攒装备」
  的设计，但「2 场打死 4 个人」值得单开一期看（见 [M18_EXPEDITION_PACE.md](M18_EXPEDITION_PACE.md) §5）。
- 技能组（M19）：每人只能带 4 个（`heroes.json` 的 `skill_selection`），可以在城镇公会里改。  但**默认那 4 个是本项目补的**——原版把默认组硬编码在逻辑里，数据抽不出来。
  4 技能后 medium Lv3 完成率 0.600→0.400，主要因为 bench 用的启发式 AI 不会组合技能
  （不会攒控场、不会先奶再打），这个数字是 AI 的下限不是玩家的上限
  （见 [M19_SKILL_LOADOUT.md](M19_SKILL_LOADOUT.md) §4）。
  技能描述文本仍未接入，公会里那一行是从数值反推的。
- 区域与首领（M20）：四个区域都能选，终点房间会刷首领，判据是「首领死了才算完成」。
  但**首领只有 medium 一档入口**（数据里 kill_boss 还有 long，那档对 0 阶队伍基本送死），
  且准备屏不告诉你遇到的是谁。0 阶队伍打首领任务（海湾 medium Lv1）击杀率 0.400，
  走到终点的比例是 0.900——落差全在那一场仗上
  （见 [M20_REGIONS_BOSS.md](M20_REGIONS_BOSS.md) §4）。
  另外 `cleanse` 已在 M32 接上，`gather` / `activate` 在 M33 接上；
  `inventory_activate` 和至暗之地仍然没接（前者要道具系统，
  后者那两行地图参数一直没用）。
- 界面（M31）：字号统一到六档、信息收成三档、可点方块共用一个函数。
  **但没有美术**：仍是纯色块 + 文字，背景/图标/动画/音效全无；
  `expedition_scene.gd` 还是 3900 多行一个大文件（只把名字表搬了出去）。
  存档路径这类开发信息收进 `--dev`，默认不显示。
- 可读性（M21）：英雄 / 怪物 / 传家宝已全部中文（15 + 61 + 4 条），
  难度卡会报「主要：食腐兽、疯狗」或「首领：空坩埚、沼泽老妪」。
  但**只报名字，不报行为**——「这只会推人」「这只有高毒抗」这类情报
  要从 `monsters.json` 的技能和抗性反推，还没做；技能描述文本也仍是数值拼出来的。
- 城镇建筑（M22）：八座都能进，疗养院能治病和清怪癖（一次一条）、
  修道院与酒馆是两档减压（40/200 金 与 70/450 金）。
  墓园只读 `roster` 的阵亡计数，没有「谁死在哪一趟」的逐次记录
  （见 [M22_BUILDINGS.md](M22_BUILDINGS.md) §10）。
- 周次（M23）：一趟 = 一周，进建筑占一周（这周不能出征），一周只能办一件事。
  但**还没有「不出发也能过一周」**——只有打完一趟才推进时间，
  所以「跳过一周让压力自然衰减」这条路不存在；`weekly_stress_relief` 默认 0，
  动它要重跑整条续航基线（M16 的 0.72→1.35 全靠回城那 40 点撑着）。
  建筑效果仍是「立即生效 + 占周」，不是原版的「下周回来才生效」
  （见 [M23_WEEKS.md](M23_WEEKS.md) §9）。
- 主动过一周（M24）：花 50 金可以什么都不做直接过一周（压力 −10、建筑队列前进），
  所以「派去疗养院的人不打仗也能回来」了。
  但**休整期间没有任何事件**，也不能「一直休整到某周」；
  而且**难度不随时间上升**——原版「拖得越久敌人越强」这条压力不存在，
  护栏只有「每周 50 金」这一个（见 [M24_IDLE_WEEK.md](M24_IDLE_WEEK.md) §7）。
- 决心等级（M25 + M29）：英雄 1–6 级，完成远征才给经验（撤退/团灭给 0）；
  比任务高 2 级**拒绝参战**，比任务低则进本 +20 压力/级**且全程受压 ×(1+0.25N)**；
  装备阶卡在等级上（`gear ≤ resolve-1`）；阵亡后招募回来是 **Lv1 新人**。
  两条没做：**任务板不按名册加权**（靠锁而不是靠任务池推）、
  **同职业不能多人**（key 是职业 id）。
  另外 `hero_base` 的 `hp_max` 只取了 `armours[lv].hp`，修女 24 血偏低，
  改它要重跑全部战斗基线，先记着（见 [M25_RESOLVE.md](M25_RESOLVE.md) §6）。
- 任务板（M26）：每周按名册等级重抽，四张卡里**固定一格**留给名册最弱的人
  （原版的「保底学徒本」在这里改成「保底最弱的人打得动的档」——
  因为我们只有 5 个固定 ID，全员 5 级时塞学徒本只会得到一张点不动的废卡）。
  两条没做：**尺寸和难度仍绑在槽位上**（原版是三维随机）、
  **任务目标当时只有** `explore` / `kill_boss`（cleanse 在 M32 接上，
  gather/activate 在 M33 接上）。
  「四个区域共用一块板子」已在 M32 解决。
  名册不能扩容是这些妥协的共同根（见 [M26_BOARD.md](M26_BOARD.md) §6）。
- 任务板与任务目标（M32）：四个区域各一块板子（每区槽位不同、保底是**区域级**的），
  `QuestGoal` 负责判据，`cleanse` 已接（清光图上全部战斗，走到出口不算完成）。
  四条限制：**`explore` 的判据仍是「走到出口」**，而不是数据写的「90% 房间」——
  改了会让 M3 以来的 bench 全部作废（路线模式没有房间）；
  **`gather` / `activate` 已在 M33 接上**，`inventory_activate` 仍然没接
  （它要任务物品先进背包，属于道具系统）；
  **bench 量不了清剿**（走路线模式，判据被 `map_mode` 挡住），
  数字全部来自端到端自检、样本 10 趟；清剿的「还差几场」只写在右侧面板一行，
  没探明的支路不计入。
  见 [M32_TASK_BOARD.md](M32_TASK_BOARD.md) §4、§5、§8。
- 任务奇物（M33）：9 个不存在的任务奇物靠**标签**解析成本作真实奇物
  （这张 10 条的表是这一期编的，带理由、有测试钉住，将来拿到真定义应整张删）。
  收集 / 激活已在任务板上，但：**收集到的东西不进背包**（只记计数，不占格子、不能卖）；
  **`inventory_activate` 没接**（要道具系统）；**`activate` 只有墓穴能玩**
  （目标铁处女只属于 Ruins）；**收集/激活只有 medium 一档**
  （`dungeons.json` 里只有一行地图参数，接 short/long 会出发失败）；
  目标奇物**只放 `amount` 个**，没有余量，支路一多会变成绕死路。
  见 [M33_QUEST_CURIOS.md](M33_QUEST_CURIOS.md) §7。
- 名册扩容（M27）：名册上限 15（= 职业总数），马车每周来 2 个新面孔、
  1000 金币招一个（只收金币）。三条没做：**没有解雇**（只能加不能减，
  满了就没法换人）、**一个职业只能有一个人**（key 是职业 id，
  不支持同职业多人）、**候选不按阵容短板加权**（纯随机，原版缺治疗更容易来修女）。
  `hire`（招新）和 `recruit`（复活）并存是过渡设计
  （见 [M27_ROSTER.md](M27_ROSTER.md) §7）。
- 解雇（M28）：免费，等级和装备一起归零；**至少留 1 个活人**（防锁死）、
  忙人不能解雇、死人可以「从墓园移除」。按钮要点两次（自绘 UI 没有弹窗）。
  两条没做：解雇**不退还装备投入**（原版也不退，但我们升级更贵）、
  解雇**不产生叙事反馈**（原版会进墓园/触发城镇事件）
  （见 [M28_DISMISS.md](M28_DISMISS.md) §7）。
- 怪癖与疾病已生效（170 个 / 195 条 buff 引用 / 落地率 91.3%）。
  主要来源是**新英雄自带 1–2 正 + 1–2 负**（`heroes.json` 的 `generation`），
  奇物只贡献约 0.05 条/趟；槽位上限 5/5/3 取自 `rules.json`
  （见 [M14_QUIRKS.md](M14_QUIRKS.md) §7）。
- 怪癖里 `cure` 已实现但**没有任何东西调用它**（城镇没有医院），
  疾病只能靠奇物清除；`curio_tag` 那 21 条标签联动、以及 `rules.json` 里的
  「负面怪癖锁定」（25% / 2 回合）都没接。
- 站位：英雄与怪物都已能位移（怪物有 46 个带位移的技能），守护与反击也已生效；
  但**英雄一个位移技能都没有**，所以「推怪」这件事玩家做不到。
- 召唤：59 个效果、35 只怪已接通，但数据里只有 22 条写了数量上限，
  其余靠本项目补的默认闸（见 [M12_SUMMON.md](M12_SUMMON.md) §5），
  分裂型怪物（ectoplasm）仍然偏重。
- 地图是随机房间图，内容有战斗/奇物/饥饿/陷阱/障碍五类；秘密房间与宝箱未接入，
  走廊长度恒为 1 格，`spacing` 未接，所以一条走廊只放一件事。
- 「看见陷阱就绕」是负期望（多走 2 步的代价大于陷阱伤害），这一层兑现的是
  「为侦察付火把」与「综合使用信息」，详见 [M8_HAZARDS.md](M8_HAZARDS.md)。

## 版权

`data/` 全部内容派生自 Red Hook Studios 的受版权保护作品，**仅供个人学习与机制研究**。
任何公开发布的作品必须重新实现规则、重新平衡数值、使用原创美术与音频。

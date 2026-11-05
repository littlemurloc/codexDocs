"""从抽取出的 JSON 生成可读的设计文档 DESIGN.md。

文档只做两件事：把数据摆清楚，把从数据能推出的公式写下来。
明确区分「数据直接读出」与「行为推断」，避免把猜测当事实。
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

BASE = Path(__file__).parent.parent
DATA = BASE / "data"


def load(name: str):
    p = DATA / name
    if not p.exists():
        return None
    return json.loads(p.read_text(encoding="utf-8"))


def pct(v, digits: int = 1) -> str:
    if v is None:
        return "—"
    if isinstance(v, bool):
        return "是" if v else "否"
    if isinstance(v, (int, float)):
        s = f"{v * 100:.{digits}f}".rstrip("0").rstrip(".")
        return f"{s}%"
    return str(v)


def num(v):
    if v is None:
        return "—"
    if isinstance(v, float) and v.is_integer():
        return str(int(v))
    return str(v)


def rng(v):
    """区间显示：两端相同时折叠成单值。"""
    if isinstance(v, list) and len(v) == 2 and all(isinstance(x, (int, float)) for x in v):
        if v[0] == v[1]:
            return num(v[0])
        return f"{num(v[0])}–{num(v[1])}"
    if isinstance(v, list):
        return " / ".join(num(x) for x in v)
    return num(v)


def span(lo, hi):
    """min/max 折叠显示。"""
    if lo is None and hi is None:
        return "—"
    if lo == hi:
        return num(lo)
    return f"{num(lo)}–{num(hi)}"


def grid(v):
    """网格尺寸用 × 而非破折号，避免和区间混淆。"""
    if isinstance(v, list) and len(v) == 2:
        return f"{num(v[0])}×{num(v[1])}"
    return rng(v)


def table(headers: list[str], rows: list[list], align: str = "") -> str:
    if not rows:
        return "_（无数据）_\n"
    out = ["| " + " | ".join(headers) + " |"]
    out.append("|" + "|".join(["---"] * len(headers)) + "|")
    for r in rows:
        out.append("| " + " | ".join(str(c) for c in r) + " |")
    return "\n".join(out) + "\n"


def main() -> int:
    heroes = load("heroes.json") or []
    monsters = load("monsters.json") or []
    effects = load("effects.json") or []
    buffs = load("buffs.json") or []
    dungeons = load("dungeons.json") or {}
    rules = load("rules.json") or {}
    trinkets = load("trinkets.json") or {}
    quirks = load("quirks.json") or {}
    quests = load("quests.json") or {}
    loot = load("loot.json") or {}
    inventory = load("inventory.json") or []
    stats = load("stats.json") or {}

    R = rules.get("rules", {})
    L: list[str] = []
    a = L.append

    a("# 暗黑地牢 1 — 数据结构与战斗规则还原文档\n")
    a("> 本文档由 `tools/gen_doc.py` 从游戏安装目录自动生成。\n"
      "> 所有数值均来自 `D:/Program Files (x86)/Steam/steamapps/common/DarkestDungeon` 的明文配置，\n"
      "> 标注「推断」的段落是基于行为的合理推测，未在可执行文件中验证。\n"
      "> **仅供个人研究与学习，数据与美术版权归 Red Hook Studios 所有，不得用于商业用途。**\n")

    # ---------------------------------------------------------- 1 总览
    a("## 1. 数据完整度\n")
    p = stats.get("parse", {})
    rows = [
        ["英雄", stats.get("counts", {}).get("heroes", 0), "heroes.json", "每人 7 技能 × 5 级"],
        ["怪物变体", stats.get("counts", {}).get("monsters", 0), "monsters.json",
         f"{stats.get('counts', {}).get('monster_families', 0)} 个家族"],
        ["效果定义", len(effects), "effects.json", "技能引用的最小单位"],
        ["Buff 定义", len(buffs), "buffs.json", "数值修正的原子条目"],
        ["地图参数", stats.get("counts", {}).get("map_configs", 0), "dungeons.json", "区域 × 任务类型 × 规模"],
        ["遭遇表", stats.get("counts", {}).get("encounter_tables", 0), "dungeons.json", "每区 8 张（含 conditional）"],
        ["掉落表", len(loot.get("loot_tables", [])), "loot.json", "支持表套表嵌套"],
        ["饰品", len((trinkets.get("base.entries") or {}).get("entries", [])), "trinkets.json", ""],
        ["怪癖", len(quirks.get("quirks", [])), "quirks.json", ""],
        ["物品", len(inventory), "inventory.json", "金币 / 传家宝 / 宝石"],
    ]
    a(table(["系统", "数量", "文件", "备注"], rows))
    a(f"原始 DSL 记录 **{p.get('total_records', 0)}** 条，扫描 `.darkest` 文件 **{p.get('darkest_files_scanned', 0)}** 个，"
      f"未解析行 **{p.get('orphan_line_count', 0)}** 条。\n")
    rc = stats.get("referential_check", {})
    a(f"引用完整性校验：所有英雄与怪物技能引用的效果名，共 **{rc.get('missing_count', 0)}** 条找不到定义"
      f"（效果定义总数 {rc.get('effect_defs', 0)}）。该项为 0 说明效果图是完整闭合的。\n")

    # ---------------------------------------------------------- 2 数据模型
    a("## 2. 数据模型\n")
    a("### 2.1 站位掩码\n")
    a("技能的作用范围不用坐标，用**数字位串**表示站位集合。这是读懂全部技能配置的关键。\n")
    a(table(["字段", "含义", "示例"], [
        ["`launch`", "技能可以从己方哪些站位发动", "`21` = 己方 1、2 号位"],
        ["`target`", "可以命中敌方哪些站位", "`12` = 敌方 1、2 号位单体"],
        ["`target` 带 `~`", "对该集合**全体**生效（AOE）", "`~12` = 敌方 1–2 号位全部"],
        ["`target` 带 `@`", "目标是**友方**", "`@1234` = 全体队友"],
        ["`move`", "施法后自身位移", "`0 1` = 前移 1 格"],
    ]))
    a("> `~` 与 `@` 的语义为**推断**：依据是 `.target ~12` 只出现在 AOE 技能（如十字军「狂信指控」）上，"
      "且该技能带 `-40%` 伤害惩罚，符合 DD1 的 AOE 设计惯例。\n")

    a("### 2.2 英雄字段\n")
    a(table(["字段", "含义", "说明"], [
        ["`resistances`", "八项抗性", "stun / poison / bleed / disease / move / debuff / death_blow / trap"],
        ["`weapon[]`", "武器 5 阶", "`dmg` 是**区间**，`atk`/`crit` 是**加成**（非绝对值）"],
        ["`armour[]`", "护甲 5 阶", "`hp` 是**绝对生命值**，`def` 是闪避率，`prot` 是减伤"],
        ["`skills[]`", "战斗技能", "每个技能含 `levels[0..4]` 五级，等级即升级次数"],
        ["`deaths_door`", "死门状态挂载", "进入死门 / 死门恢复 / 心脏骤停三组 buff"],
        ["`tags`", "标签", "供奇物与技能条件判定，如 `religious` 影响祭坛交互"],
        ["`generation`", "随机生成规则", "怪癖数量、营地技能数、初始技能数"],
    ]))
    a("**关键点**：英雄技能的 `dmg` 是**百分比修正**（如 `0%`、`-40%`），最终伤害 = 武器区间 × (1 + dmg 修正)。"
      "怪物技能的 `dmg` 则是**绝对区间**（如 `2 4`）。两者同名不同义，移植时必须分开处理。\n")

    a("### 2.3 效果（effect）— 最小执行单元\n")
    a(f"{len(effects)} 条效果定义，字段词频前 15 位：\n")
    keys = Counter()
    for e in effects:
        for k in e:
            keys[k] += 1
    a(table(["字段", "出现次数", "作用"], [
        [f"`{k}`", c, ""] for k, c in keys.most_common(15)
    ]))
    a("效果是**数据驱动的指令**：`.target` 选目标，`.chance` 判命中，`.on_hit`/`.on_miss` 决定成败分支，"
      "`.queue` 决定立即执行还是延后结算，`.buff_ids` 挂载 buff，`.duration` 定时长。\n")

    # ---------------------------------------------------------- 3 战斗数学
    a("## 3. 战斗数学\n")
    a("以下参数全部来自 `shared/rules.json`，原样引用。\n")
    a("### 3.1 命中\n")
    a(f"- 命中率上限 **{pct(R.get('cutoffAlwaysHit'))}**，下限 **{pct(R.get('cutoffAlwaysMiss'))}**（即无下限，可 0%）")
    a(f"- 连续未命中补偿：每次未命中累加 **{pct(R.get('consecutive_miss_reduction_acc_buff'))}** 命中")
    a(f"- 基础行动值 **{num(R.get('initiative_base'))}**\n")

    a("### 3.2 伤害与暴击\n")
    pc = R.get("player_crit_multiplier_table") or [{}]
    mc = R.get("monster_crit_multiplier_table") or [{}]
    a(f"- 玩家暴击倍率 **{num((pc[0] or {}).get('value'))}×**，怪物暴击倍率 **{num((mc[0] or {}).get('value'))}×**")
    a(f"- 溢出暴击：每点超出上限的暴击提供 **{pct(R.get('excessCritMult'))}** 额外倍率，封顶 **{pct(R.get('excessCritMax'))}**\n")

    mcrit = R.get("monster_crit", {})
    pcrit = R.get("player_crit", {})
    a("暴击的压力副作用（这才是 DD1 的压迫感来源）：\n")
    a(table(["触发者", "效果", "对自身", "对队友"], [
        ["怪物暴击", "压力伤害",
         f"{pct(mcrit.get('stress_chance'))} 概率 +{num(mcrit.get('stress_damage'))}",
         f"{pct(mcrit.get('companion_stress_chance'))} 概率 +{num(mcrit.get('companion_stress_damage'))}"],
        ["玩家暴击", "压力缓解",
         f"{pct(pcrit.get('relief_chance'))} 概率 -{num(pcrit.get('stress_relief'))}",
         f"{pct(pcrit.get('companion_relief_chance'))} 概率 -{num(pcrit.get('companion_stress_relief'))}"],
    ]))
    a(f"- 玩家暴击时喊话概率 **{pct(R.get('playerCritBarkChance'))}**"
      f"；击杀缓解压力概率 **{pct(R.get('killing_blow_relief_chance'))}**，数值 **-{num(R.get('killing_blow_stress_relief'))}**\n")

    a("### 3.3 压力（Stress）与死门\n")
    a(f"- 空过一回合：**+{num(R.get('passed_turn_stress_dmg'))}** 压力/回合")
    a(f"- 进入死门：自身 **+{num(R.get('deaths_door_self_stress_dmg'))}**，队友 "
      f"{pct(R.get('deaths_door_companion_stress_chance'))} 概率 **+{num(R.get('deaths_door_companion_stress_dmg'))}**")
    a(f"- 死门持续（重复触发）：自身 **+{num(R.get('deaths_door_self_stress_dmg_repeat'))}**，队友 "
      f"{pct(R.get('deaths_door_companion_stress_chance_repeat'))} 概率 **+{num(R.get('deaths_door_companion_stress_dmg_repeat'))}**")
    a(f"- 队友死亡：**{pct(R.get('death_party_stress_chance'))}** 概率 **+{num(R.get('death_party_stress_damage'))}** 压力")
    a(f"- 压力崩溃判定率 **{pct(R.get('affliction_base_onset_chance'))}**；抵抗成功回落至 **{num(R.get('stress_affliction_resisted'))}**")
    a(f"- 怪癖上限：正面 **{num(R.get('quirks_max_positive'))}** / 负面 **{num(R.get('quirks_max_negative'))}** / "
      f"疾病 **{num(R.get('quirks_max_diseases'))}**；锁定上限各 **{num(R.get('quirks_max_locked_positive'))}**\n")

    a("### 3.4 光照（Torch）\n")
    a("光照分 5 档，直接改写战斗参数。这是 DD1 最核心的风险/收益旋钮。\n")
    dark = (R.get("darkness") or {}).get("range_table") or []
    rows = []
    for band in dark:
        r0 = band.get("range", {})
        v = band.get("value", {})
        lo, hi = r0.get("lower"), r0.get("upper")
        if hi is not None and hi > 1e30:
            label = f"≥ {num(lo)}"
        elif lo is not None and lo < -1e30:
            label = f"< {num(hi)}"
        else:
            label = f"{num(lo)} – {num(hi)}"
        rows.append([
            label,
            f"+{num(v.get('stress_chance_increase'))}",
            f"+{num(v.get('stress_damage_increase'))}",
            f"+{num(v.get('monster_damage_increase'))}",
            f"+{num(v.get('monster_crit_increase'))}",
            f"+{num(v.get('loot_increase_gold'))}",
            f"+{num(v.get('monsters_surprised_increase'))}",
        ])
    a(table(["光照区间", "压力几率", "压力伤害", "怪物伤害", "怪物暴击", "金币掉落", "怪物被惊袭"], rows))
    loss = {x.get("key"): x.get("data") for x in (R.get("tile_light_loss") or [])}
    a(f"火把消耗：每移动一格，明亮区 **-{num(loss.get('clear'))}**、微光区 **-{num(loss.get('dim'))}**、"
      f"黑暗区 **-{num(loss.get('dark'))}**。营地休息回复 **+{num(R.get('camp_restore_torch'))}**，"
      f"被夜袭 **{num(R.get('ambush_torch_reduction'))}**。\n")
    a("> 注意最后一列：**越黑，怪物越容易被惊袭**（黑暗提供先手优势），但代价是承伤、压力、暴击全面上升。"
      "这个矛盾设计是 DD1 数值的精髓。\n")

    a("### 3.5 探索与经济\n")
    a(table(["机制", "参数", "值"], [
        ["营地", "技能点总数", num(R.get("camp_start_camping_points"))],
        ["营地", "休息点阈值", num(R.get("camp_rest_point_threshold"))],
        ["营地", "最多营地技能", num(R.get("max_number_of_camping_skills"))],
        ["惊袭", "走廊基础概率", pct(R.get("surprise_corridor_monsters_base_chance"))],
        ["惊袭", "已知走廊", pct(R.get("surprise_known_corridor_monsters_base_chance"))],
        ["惊袭", "上限", pct(R.get("surprise_max_monsters_surprised_chance"))],
        ["扎营", "夜袭基础概率", pct(R.get("ambush_camping_base_chance"))],
        ["陷阱", "侦察后解除加成", pct(R.get("trap_scout_disarm_bonus"))],
        ["撤退", "基础成功率", pct(R.get("combat_retreat_chance"))],
        ["撤退", "每次尝试加成", pct(R.get("combat_retreat_bonus_chance_per_attempt"))],
        ["撤退", "代价", f"+{num(R.get('combat_retreat_stress'))} 压力"],
        ["侦察", "基础概率", pct(R.get("scouting_chance_base"))],
        ["补给", "食物回血", pct(R.get("provision_hp_heal"))],
    ]))
    meals = R.get("meals_table") or []
    a("进食分级（直接影响压力）：\n")
    a(table(["档位", "口粮/人", "回血", "压力"],
            [[m.get("type"), num(m.get("rations_per")), pct(m.get("healing")), num(m.get("stress"))] for m in meals]))
    a(f"饿肚子（`none`）是 **{pct((meals[0] or {}).get('healing'))} 生命 + {num((meals[0] or {}).get('stress'))} 压力**——"
      "惩罚远大于战斗失误，这是设计上的强约束。\n")

    a("### 3.6 拖延惩罚（Stall）\n")
    a("DD1 用一套独立规则防止玩家靠治疗刷血：\n")
    a(table(["参数", "值"], [
        ["队伍人数阈值", num(R.get("stall_party_size_threshold"))],
        ["敌人数阈值", num(R.get("stall_enemy_size_threshold"))],
        ["失效技能数阈值", num(R.get("stall_number_of_invalidating_skills_threshold"))],
        ["回合压力效果阈值", num(R.get("stall_round_stress_effect_threshold"))],
        ["回合召唤效果阈值", num(R.get("stall_round_summon_effect_threshold"))],
        ["回合重置阈值", num(R.get("stall_round_reset_threshold"))],
        ["惩罚名", R.get("stall_stress_effect_name")],
    ]))

    # ---------------------------------------------------------- 4 地牢
    a("## 4. 地牢生成参数\n")
    maps = dungeons.get("maps", [])
    rows = []
    for m in maps:
        rows.append([
            m.get("dungeon_type"), m.get("quest_type"), m.get("size"),
            m.get("base_room_number"), m.get("base_corridor_number"),
            grid(m.get("gridsize")), num(m.get("connectivity")),
            f"{rng(m.get('hallway_battle'))}",
            f"{rng(m.get('total_room_battles'))}",
        ])
    a(table(["区域", "任务类型", "规模", "房间数", "走廊数", "网格", "连通度", "走廊战斗", "房间战斗"], rows))
    a("生成器不是格子迷宫，而是**房间-走廊图**：先按网格撒房间，再按连通度连边，"
      "然后按各类 POI 的区间数量往走廊和房间上挂内容（战斗/陷阱/障碍/奇物/饥饿）。\n")
    a("关键参数含义：\n")
    a("- `connectivity` 越高，地图越像一张网，绕路多；越低越像树，死路多")
    a("- `min_final_distance` 保证终点房间离起点足够远")
    a("- `nudge_span` / `nudge_neighbour_bias` / `nudge_map_centre_bias` 控制地图布局的「自然感」扰动\n")

    props = dungeons.get("props", {})
    if props:
        a("### 4.1 奇物刷新权重（以 weald 为例）\n")
        w = props.get("weald", {})
        rows = []
        for kind in ("hall_curios", "room_curios", "room_treasures", "traps", "obstacles", "prison_doors"):
            for entry in w.get(kind, [])[:8]:
                rows.append([kind, num(entry.get("chance")), ", ".join(map(str, entry.get("types") or []))])
        a(table(["类别", "权重", "奇物"], rows))

    enc = dungeons.get("encounters", {})
    if enc:
        a("### 4.2 遭遇表结构\n")
        a("五个主区域（crypts / weald / warrens / cove / darkestdungeon），每区分 5 个难度层；"
          "`_shared` 与 `town` 是教学关和共享桶，`conditional_*` 是剧情条件覆盖表。\n")
        rows = []
        for region, tables in enc.items():
            for lvl, t in tables.items():
                rows.append([region, lvl, len(t.get("hall", [])), len(t.get("room", [])),
                             len(t.get("boss", [])), len(t.get("stall", []))])
        a(table(["区域", "层/条件", "hall 条目", "room 条目", "boss", "stall"], rows))
        a("每条遭遇是「概率 + 怪物 id 列表」，例如 weald 第 1 层：\n")
        weald1 = (enc.get("weald") or {}).get("1", {})
        sample = (weald1.get("hall") or [])[:4]
        for s in sample:
            a(f"- 权重 {num(s.get('chance'))} → `{' + '.join(map(str, s.get('types') or []))}`")
        a("")

    # ---------------------------------------------------------- 5 内容清单
    a("## 5. 英雄速查\n")
    rows = []
    for h in heroes:
        w = h.get("weapons") or [{}]
        ar = h.get("armours") or [{}]
        rows.append([
            h.get("id"),
            f"{num((ar[0] or {}).get('hp'))} → {num((ar[-1] or {}).get('hp'))}",
            f"{rng((w[0] or {}).get('dmg'))} → {rng((w[-1] or {}).get('dmg'))}",
            num((w[0] or {}).get("spd")),
            pct((h.get("resistances") or {}).get("stun")),
            len(h.get("skills") or []),
            ", ".join(h.get("tags") or []),
        ])
    a(table(["英雄", "生命 1→5", "武器伤害 1→5", "速度", "眩晕抗性", "技能数", "标签"], rows))

    a("## 6. 怪物速查（按家族聚合）\n")
    fam: dict = {}
    for m in monsters:
        fam.setdefault(m["family"], []).append(m)
    rows = []
    for name, variants in sorted(fam.items()):
        hp = [v["stats"].get("hp") for v in variants if v.get("stats", {}).get("hp") is not None]
        spd = [v["stats"].get("spd") for v in variants if v.get("stats", {}).get("spd") is not None]
        dmg_lo, dmg_hi = None, None
        for v in variants:
            for s in v.get("skills") or []:
                d = s.get("dmg")
                if isinstance(d, list) and len(d) == 2 and all(isinstance(x, (int, float)) for x in d):
                    dmg_lo = d[0] if dmg_lo is None else min(dmg_lo, d[0])
                    dmg_hi = d[1] if dmg_hi is None else max(dmg_hi, d[1])
        rows.append([name, len(variants),
                     span(min(hp), max(hp)) if hp else "—",
                     span(min(spd), max(spd)) if spd else "—",
                     span(dmg_lo, dmg_hi) if dmg_lo is not None else "—"])
    a(table(["家族", "变体数", "生命", "速度", "单次伤害"], rows))

    a("## 7. 其它内容规模\n")
    tr = (trinkets.get("base.entries") or {}).get("entries", [])
    rar = Counter(t.get("rarity") for t in tr)
    qs = (quirks.get("quirks") or [])
    pos = sum(1 for q in qs if q.get("is_positive"))
    a(table(["资产", "数量", "说明"], [
        ["饰品", len(tr), "，".join(f"{k} {v}" for k, v in rar.most_common(8))],
        ["怪癖", len(qs), f"正面 {pos} / 负面 {len(qs) - pos}"],
        ["掉落表", len(loot.get("loot_tables", [])), "支持 table 嵌套与难度/区域过滤"],
        ["任务定义", len(quests), "生成规则 / 剧情任务 / 类型定义"],
        ["物品", len(inventory), "金币、传家宝、宝石"],
    ]))

    # ---------------------------------------------------------- 8 未解
    a("## 8. 无法从数据获得、需要反推的部分\n")
    a("这些逻辑编译在 `Darkest.exe` 里，数据文件只提供参数不提供算法：\n")
    a(table(["系统", "已知", "缺失", "反推难度"], [
        ["效果结算顺序", "`.queue` 标记了哪些延后", "延后效果的层内排序规则", "中"],
        ["行动顺序", "`initiative_base` 与速度值", "速度相同时的 tie-break 规则", "低"],
        ["怪物 AI", "`monster_brain` 只给 ID", "技能选择评分函数、目标偏好权重", "高"],
        ["地图生成", "全部生成参数（44 套）", "从参数到图的具体随机算法", "中"],
        ["奇物交互", "设计表 CSV（策划草稿）", "运行期判定逻辑", "中"],
        ["压力崩溃", "触发率与抗性阈值", "崩溃/美德的具体判定流程", "中"],
    ]))
    a("务实做法：不要追求二进制级还原，做**行为等价**——先让数值区间对得上，再用试玩修正排序细节。\n")

    # ---------------------------------------------------------- 9 Godot
    a("## 9. 迁移到 Godot 的落点\n")
    a(table(["DD1 概念", "数据来源", "Godot 实现建议"], [
        ["效果（effect）", "effects.json", "`Effect` Resource + 解释器（命令模式），不写死技能逻辑"],
        ["Buff", "buffs.json", "`BuffInstance` 挂在角色身上，按 `duration_type` 在阶段钩子里衰减"],
        ["技能", "heroes.json → skills", "`Skill` Resource，5 个等级是数组不是 5 个资源"],
        ["站位掩码", "`launch` / `target`", "位运算：`mask & (1 << rank)`，天然契合整型"],
        ["地牢生成", "dungeons.json → maps", "房间图用 `AStar2D` 不必要，直接邻接表 + DFS 生成"],
        ["遭遇表", "encounters", "按权重 roulette 抽样，注意 `stall`/`named` 是特殊桶"],
        ["光照", "rules.json → darkness", "纯数据表查表，`light` 值做区段映射"],
        ["小镇循环", "quests.json / buildings", "状态机 + 存档用 `ResourceSaver` 存 Dictionary"],
    ]))
    a("架构上最重要的一条：**把战斗逻辑写成不依赖节点的纯类**。"
      "DD1 的战斗正确性可以用数据验证（给定种子和输入，输出必须确定），"
      "逻辑与节点解耦后可以直接写单元测试，这在移植项目里能省掉大量调试时间。\n")

    a("## 10. 版权说明\n")
    a("本文档与 `data/` 下的数据均派生自受版权保护的游戏内容，仅可用于个人学习、"
      "机制分析与技术研究。若要发布任何作品，**规则可以重新实现，数值需要重新平衡，"
      "美术与音频必须原创**。\n")

    out = BASE / "DESIGN.md"
    out.write_text("\n".join(L), encoding="utf-8")
    print(f"已生成 {out} （{len('\n'.join(L))} 字符）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

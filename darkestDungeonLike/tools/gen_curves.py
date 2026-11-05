"""从抽取数据中提炼「数值生成器参数」，而不是数值本身。

这是把 DD1 从「一张数值表」还原成「一套能生成数值的规则」的关键一步：
你不需要抄 490 件饰品的具体数字，你需要的是英雄血量怎么长、怪物难度怎么阶梯、
技能升级加什么、饰品槽位怎么给。

产出：
    data/balance_curves.json   参数集（可直接喂给自己的平衡工具）
    curves.html                自包含可视化（内嵌数据，双击即开）

用法：
    python tools/gen_curves.py
"""

from __future__ import annotations

import json
import math
import re
import statistics as st
from collections import Counter, defaultdict
from pathlib import Path

BASE = Path(__file__).parent.parent
DATA = BASE / "data"


def load(name: str):
    p = DATA / name
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def as_list(v) -> list:
    if v is None:
        return []
    return v if isinstance(v, list) else [v]


def med(v, digits=3):
    return round(st.median(v), digits) if v else None


# ---------------------------------------------------------------- 英雄曲线

def hero_curves(heroes: list[dict]) -> dict:
    per_hero = []
    growth_classes = Counter()
    def_growth = Counter()

    for h in heroes:
        ar = h.get("armours") or []
        wp = h.get("weapons") or []
        if len(ar) < 5 or len(wp) < 5:
            continue
        hp = [a.get("hp") for a in ar]
        dfn = [a.get("def") for a in ar]
        lo = [w.get("dmg", [0, 0])[0] for w in wp]
        hi = [w.get("dmg", [0, 0])[1] for w in wp]

        hp_d = [hp[i + 1] - hp[i] for i in range(4)]
        df_d = [round(dfn[i + 1] - dfn[i], 4) for i in range(4)]
        growth = hp_d[0] if len(set(hp_d)) == 1 else None
        if growth is not None:
            growth_classes[growth] += 1
        if len(set(df_d)) == 1:
            def_growth[df_d[0]] += 1

        # 单次期望伤害：武器均值 × 伤害技能的平均修正
        mods = []
        for s in h.get("skills") or []:
            lv = s["levels"][0] if s.get("levels") else {}
            if lv.get("type") in ("melee", "ranged"):
                d = lv.get("dmg")
                if isinstance(d, (int, float)):
                    mods.append(1.0 + d)
        w_avg = (lo[0] + hi[0]) / 2
        mult = st.mean(mods) if mods else 1.0

        # 闪避折算生命：DEF 是闪避率，等价于把命中率打折
        ehp = hp[0] / (1 - dfn[0]) if dfn[0] and dfn[0] < 1 else hp[0]

        per_hero.append({
            "id": h["id"],
            "hp_base": hp[0],
            "hp_growth": growth,
            "hp_tiers": hp,
            "def_base": dfn[0],
            "def_growth": df_d[0] if len(set(df_d)) == 1 else None,
            "def_tiers": dfn,
            "weapon_low": lo,
            "weapon_high": hi,
            "weapon_l0_avg": round(w_avg, 2),
            "weapon_l4_over_l0": round(((lo[4] + hi[4]) / 2) / w_avg, 3) if w_avg else None,
            "skill_dmg_mult": round(mult, 3),
            "dmg_per_hit_l0": round(w_avg * mult, 2),
            "ehp_l0": round(ehp, 1),
            "tags": h.get("tags") or [],
        })

    hps = [p["hp_base"] for p in per_hero]
    ehp = [p["ehp_l0"] for p in per_hero]
    dmg = [p["dmg_per_hit_l0"] for p in per_hero]
    ratios = [p["weapon_l4_over_l0"] for p in per_hero if p["weapon_l4_over_l0"]]

    return {
        "hp_growth_classes": {str(k): v for k, v in sorted(growth_classes.items())},
        "def_growth_classes": {str(k): v for k, v in sorted(def_growth.items())},
        "hp_base_range": [min(hps), max(hps)],
        "ehp_l0_range": [min(ehp), max(ehp)],
        "dmg_l0_range": [min(dmg), max(dmg)],
        "weapon_l4_over_l0_median": med(ratios),
        "weapon_l4_over_l0_range": [min(ratios), max(ratios)],
        "per_hero": per_hero,
    }


# ---------------------------------------------------------------- 技能成长

def skill_growth(heroes: list[dict], effects: list[dict]) -> dict:
    atk_d, crit_d, dmg_d = Counter(), Counter(), Counter()
    for h in heroes:
        for s in h.get("skills") or []:
            lv = s.get("levels") or []
            for i in range(len(lv) - 1):
                for key, bucket in (("atk", atk_d), ("crit", crit_d), ("dmg", dmg_d)):
                    a, b = lv[i].get(key), lv[i + 1].get(key)
                    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
                        bucket[round(b - a, 4)] += 1

    # 效果分层：按名字末尾数字分组，看伤害加成逐级增量
    pat = re.compile(r"^(.*?)\s*(\d+)$")
    groups: dict = defaultdict(dict)
    for e in effects:
        m = pat.match(str(e.get("name", "")))
        if m:
            groups[m.group(1).strip()][int(m.group(2))] = e

    tier_delta = Counter()
    for _, tiers in groups.items():
        vals = [(k, tiers[k].get("damage_low_multiply")) for k in sorted(tiers)
                if isinstance(tiers[k].get("damage_low_multiply"), (int, float))]
        for i in range(len(vals) - 1):
            tier_delta[round(vals[i + 1][1] - vals[i][1], 4)] += 1

    killer = []
    for name in ("Unholy Killer", "Stun Killer"):
        t = groups.get(name, {})
        killer.append({
            "series": name,
            "tiers": [{"tier": k, "damage_multiply": t[k].get("damage_low_multiply")}
                      for k in sorted(t) if isinstance(t[k].get("damage_low_multiply"), (int, float))],
        })

    return {
        "atk_per_level": atk_d.most_common(3),
        "crit_per_level": crit_d.most_common(3),
        "dmg_modifier_per_level": dmg_d.most_common(3),
        "effect_damage_per_tier": tier_delta.most_common(6),
        "damage_effect_series": killer,
        "note": "英雄伤害成长不在技能修正里（该字段逐级不变），而在 effect 的伤害乘算每级 +5%",
    }


# ---------------------------------------------------------------- 怪物曲线

def monster_curves(monsters: list[dict], dungeons: dict) -> dict:
    fam: dict = defaultdict(dict)
    for m in monsters:
        fam[m["family"]][m["id"][-1]] = m

    ratios: dict = defaultdict(lambda: defaultdict(list))
    families = []
    TIERS = "ABCDE"

    for name, v in fam.items():
        tiers = {k: v[k] for k in TIERS if k in v}
        if not tiers:
            continue
        hps = {k: t["stats"].get("hp") for k, t in tiers.items()}
        present = [k for k in TIERS if k in tiers]

        # 逐档对比：倍率按「A->B / B->C / C->D」分别统计，不合并
        for i in range(len(present) - 1):
            step = f"{present[i]}->{present[i + 1]}"
            ta, tb = tiers[present[i]], tiers[present[i + 1]]
            a, b = hps[present[i]], hps[present[i + 1]]
            if a and b:
                ratios[step]["hp"].append(b / a)
            sa = {s["id"]: s for s in ta.get("skills") or []}
            sb = {s["id"]: s for s in tb.get("skills") or []}
            for sid, s in sa.items():
                if sid in sb:
                    d0, d1 = s.get("dmg"), sb[sid].get("dmg")
                    if (isinstance(d0, list) and isinstance(d1, list)
                            and len(d0) == 2 and len(d1) == 2 and d0[0]):
                        ratios[step]["dmg"].append(d1[0] / d0[0])
            s0, s1 = ta["stats"].get("spd"), tb["stats"].get("spd")
            if isinstance(s0, (int, float)) and isinstance(s1, (int, float)) and s0:
                ratios[step]["spd"].append(s1 / s0)
            for k in ("stun_resist", "poison_resist", "bleed_resist"):
                r0, r1 = ta["stats"].get(k), tb["stats"].get(k)
                if isinstance(r0, (int, float)) and isinstance(r1, (int, float)) and r0:
                    ratios[step]["resist"].append(r1 / r0)

        dmg_lo = dmg_hi = None
        for t in tiers.values():
            for s in t.get("skills") or []:
                d = s.get("dmg")
                if isinstance(d, list) and len(d) == 2 and all(isinstance(x, (int, float)) for x in d):
                    dmg_lo = d[0] if dmg_lo is None else min(dmg_lo, d[0])
                    dmg_hi = d[1] if dmg_hi is None else max(dmg_hi, d[1])

        first = tiers[present[0]]
        families.append({
            "family": name,
            "variants": len(tiers),
            "hp": hps,
            "size": first.get("size"),
            "dmg_low": dmg_lo,
            "dmg_high": dmg_hi,
            "spd": first["stats"].get("spd"),
            "is_boss": max([h for h in hps.values() if h] or [0]) >= 100,
        })

    # 从遭遇表反推「难度档 -> 地牢层」的对应关系
    suffix_by_level: dict = defaultdict(Counter)
    for region, tables in (dungeons.get("encounters") or {}).items():
        for lvl, table in tables.items():
            if not lvl.isdigit():
                continue
            for bucket in table.values():
                for entry in bucket:
                    for t in entry.get("types") or []:
                        if len(t) > 1 and t[-1] in TIERS and t[-2] == "_":
                            suffix_by_level[lvl][t[-1]] += 1
    tier_map = {}
    for lvl, counter in sorted(suffix_by_level.items()):
        if counter:
            tier_map[lvl] = counter.most_common(1)[0][0]

    all_hp = [h for f in families for h in f["hp"].values() if h]
    all_dmg = [f["dmg_high"] for f in families if f["dmg_high"] is not None]
    tier_scaling = {
        step: {k: {"median": med(v), "n": len(v)} for k, v in stats.items() if v}
        for step, stats in sorted(ratios.items())
    }
    headline = tier_scaling.get("A->B") or {}
    return {
        "tier_scaling": tier_scaling,
        "tier_headline": {k: v["median"] for k, v in headline.items()},
        "tier_to_dungeon_level": tier_map,
        "hp_range": [min(all_hp), max(all_hp)],
        "dmg_high_range": [min(all_dmg), max(all_dmg)],
        "families": families,
        "designs_vs_variants": {
            "families": len(families),
            "variants": sum(f["variants"] for f in families),
        },
    }


# ---------------------------------------------------------------- 饰品预算

def trinket_curves(trinkets: dict, buffs: list[dict]) -> dict:
    entries = (trinkets or {}).get("base.entries", {}).get("entries", [])
    bm = {b["id"]: b for b in buffs}
    by_rarity = defaultdict(list)
    for t in entries:
        slots = len(t.get("buffs") or [])
        by_rarity[t.get("rarity")].append(slots)
    order = ["very_common", "common", "uncommon", "rare", "very_rare", "ancestral", "trophy"]
    out = {}
    for r in order:
        v = by_rarity.get(r) or []
        if v:
            out[r] = {"count": len(v), "slots_avg": round(st.mean(v), 2),
                      "slots_range": [min(v), max(v)]}
    return {
        "slots_by_rarity": out,
        "note": "稀有度约等于效果槽位数（2→4），不是强度数字；强度分布在槽位内随机",
        "total": len(entries),
    }


# ---------------------------------------------------------------- SVG 图表

PALETTE = ["#7F77DD", "#1D9E75", "#D85A30", "#D4537E", "#378ADD", "#EF9F27"]


def _esc(s) -> str:
    return (str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def scatter(items, xkey, ykey, xlabel, ylabel, title, w=600, h=380) -> str:
    pad_l, pad_r, pad_t, pad_b = 58, 24, 34, 46
    pw, ph = w - pad_l - pad_r, h - pad_t - pad_b
    xs = [it[xkey] for it in items]
    ys = [it[ykey] for it in items]
    x0, x1 = min(xs), max(xs)
    y0, y1 = min(ys), max(ys)
    x0 -= (x1 - x0) * 0.12 or 1
    x1 += (x1 - x0) * 0.12 or 1
    y0 -= (y1 - y0) * 0.12 or 1
    y1 += (y1 - y0) * 0.12 or 1

    def px(v):
        return pad_l + (v - x0) / (x1 - x0) * pw

    def py(v):
        return pad_t + ph - (v - y0) / (y1 - y0) * ph

    out = [f'<svg viewBox="0 0 {w} {h}" width="100%" role="img" aria-label="{_esc(title)}">']
    out.append(f'<rect x="{pad_l}" y="{pad_t}" width="{pw}" height="{ph}" fill="#191c22"/>')
    # 网格
    for i in range(5):
        yy = pad_t + ph * i / 4
        val = y1 - (y1 - y0) * i / 4
        out.append(f'<line x1="{pad_l}" y1="{yy:.1f}" x2="{pad_l+pw}" y2="{yy:.1f}" stroke="#2a2e35" stroke-width="0.5"/>')
        out.append(f'<text x="{pad_l-8}" y="{yy+3.5:.1f}" font-size="10" fill="#8b8a84" text-anchor="end">{val:.0f}</text>')
    for i in range(5):
        xx = pad_l + pw * i / 4
        val = x0 + (x1 - x0) * i / 4
        out.append(f'<line x1="{xx:.1f}" y1="{pad_t}" x2="{xx:.1f}" y2="{pad_t+ph}" stroke="#2a2e35" stroke-width="0.5"/>')
        out.append(f'<text x="{xx:.1f}" y="{pad_t+ph+16}" font-size="10" fill="#8b8a84" text-anchor="middle">{val:.0f}</text>')

    for i, it in enumerate(items):
        cx, cy = px(it[xkey]), py(it[ykey])
        out.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="5" fill="{PALETTE[i % len(PALETTE)]}" stroke="#14161a" stroke-width="1"/>')
        out.append(f'<text x="{cx:.1f}" y="{cy-9:.1f}" font-size="9.5" fill="#c9c7c1" text-anchor="middle">{i+1}</text>')

    out.append(f'<text x="{pad_l+pw/2}" y="{h-8}" font-size="11" fill="#a8a69f" text-anchor="middle">{_esc(xlabel)}</text>')
    out.append(f'<text x="14" y="{pad_t+ph/2}" font-size="11" fill="#a8a69f" text-anchor="middle" transform="rotate(-90 14 {pad_t+ph/2})">{_esc(ylabel)}</text>')
    out.append("</svg>")
    return "".join(out)


def line_chart(series, xlabels, ylabel, title, w=600, h=340) -> str:
    """series: [{label, values, color}]"""
    pad_l, pad_r, pad_t, pad_b = 58, 90, 30, 44
    pw, ph = w - pad_l - pad_r, h - pad_t - pad_b
    allv = [v for s in series for v in s["values"]]
    y0, y1 = min(allv), max(allv)
    y0 -= (y1 - y0) * 0.08 or 1
    y1 += (y1 - y0) * 0.08 or 1
    n = len(xlabels)

    def px(i):
        return pad_l + (pw * i / max(n - 1, 1))

    def py(v):
        return pad_t + ph - (v - y0) / (y1 - y0) * ph

    out = [f'<svg viewBox="0 0 {w} {h}" width="100%" role="img" aria-label="{_esc(title)}">']
    out.append(f'<rect x="{pad_l}" y="{pad_t}" width="{pw}" height="{ph}" fill="#191c22"/>')
    for i in range(5):
        yy = pad_t + ph * i / 4
        val = y1 - (y1 - y0) * i / 4
        out.append(f'<line x1="{pad_l}" y1="{yy:.1f}" x2="{pad_l+pw}" y2="{yy:.1f}" stroke="#2a2e35" stroke-width="0.5"/>')
        out.append(f'<text x="{pad_l-8}" y="{yy+3.5:.1f}" font-size="10" fill="#8b8a84" text-anchor="end">{val:.0f}</text>')
    for i, lab in enumerate(xlabels):
        out.append(f'<text x="{px(i):.1f}" y="{pad_t+ph+16}" font-size="10" fill="#8b8a84" text-anchor="middle">{_esc(lab)}</text>')
    for s in series:
        pts = " ".join(f"{px(i):.1f},{py(v):.1f}" for i, v in enumerate(s["values"]))
        out.append(f'<polyline points="{pts}" fill="none" stroke="{s["color"]}" stroke-width="{s.get("width",1.4)}" opacity="{s.get("opacity",1)}"/>')
    # 图例
    ly = pad_t + 4
    for s in series:
        if s.get("legend"):
            out.append(f'<line x1="{pad_l+pw+10}" y1="{ly}" x2="{pad_l+pw+24}" y2="{ly}" stroke="{s["color"]}" stroke-width="2"/>')
            out.append(f'<text x="{pad_l+pw+28}" y="{ly+3.5}" font-size="9.5" fill="#a8a69f">{_esc(s["legend"])}</text>')
            ly += 15
    out.append(f'<text x="14" y="{pad_t+ph/2}" font-size="11" fill="#a8a69f" text-anchor="middle" transform="rotate(-90 14 {pad_t+ph/2})">{_esc(ylabel)}</text>')
    out.append("</svg>")
    return "".join(out)


def bar_chart(groups, w=600, h=None) -> str:
    """横向分组条形图：每行一个家族，三档难度并列。长标签也不会挤。"""
    row_h = 30
    pad_l, pad_r, pad_t, pad_b = 128, 86, 26, 34
    ph = len(groups) * row_h
    h = h or (pad_t + ph + pad_b)
    pw = w - pad_l - pad_r
    allv = max(v for g in groups for v in g["values"] if v)
    bh = row_h * 0.62 / 3

    out = [f'<svg viewBox="0 0 {w} {h}" width="100%" role="img" aria-label="怪物难度层生命对比">']
    out.append(f'<rect x="{pad_l}" y="{pad_t}" width="{pw}" height="{ph}" fill="#191c22"/>')
    for i in range(5):
        xx = pad_l + pw * i / 4
        val = allv * i / 4
        out.append(f'<line x1="{xx:.1f}" y1="{pad_t}" x2="{xx:.1f}" y2="{pad_t+ph}" stroke="#2a2e35" stroke-width="0.5"/>')
        out.append(f'<text x="{xx:.1f}" y="{pad_t-8}" font-size="10" fill="#8b8a84" text-anchor="middle">{val:.0f}</text>')
    for gi, g in enumerate(groups):
        ry = pad_t + gi * row_h
        out.append(f'<text x="{pad_l-10}" y="{ry+row_h/2+3:.1f}" font-size="11" fill="#c9c7c1" text-anchor="end">{_esc(g["label"])}</text>')
        for ti, v in enumerate(g["values"]):
            if not v:
                continue
            bw = v / allv * pw
            by = ry + (row_h - bh * 3) / 2 + ti * bh
            out.append(f'<rect x="{pad_l}" y="{by:.1f}" width="{bw:.1f}" height="{bh-1.5:.1f}" fill="{PALETTE[ti]}" rx="1.5"/>')
    ly = pad_t
    for ti, lab in enumerate(["A 低难度", "B 中难度", "C 高难度"]):
        out.append(f'<rect x="{pad_l+pw+12}" y="{ly-6}" width="9" height="9" fill="{PALETTE[ti]}" rx="1.5"/>')
        out.append(f'<text x="{pad_l+pw+25}" y="{ly+2}" font-size="9.5" fill="#a8a69f">{lab}</text>')
        ly += 14
    out.append(f'<text x="14" y="{pad_t+ph/2}" font-size="11" fill="#a8a69f" text-anchor="middle" transform="rotate(-90 14 {pad_t+ph/2})">生命值</text>')
    out.append("</svg>")
    return "".join(out)


# ---------------------------------------------------------------- HTML

def build_html(curves: dict) -> str:
    hc = curves["heroes"]
    mc = curves["monsters"]
    tc = curves["trinkets"]
    sg = curves["skill_growth"]

    heroes = hc["per_hero"]

    # 图 1：英雄平衡空间
    sc = scatter(heroes, "ehp_l0", "dmg_per_hit_l0",
                 "闪避折算生命（初始装备）", "单次期望伤害（初始）", "英雄平衡空间")
    legend_rows = "".join(
        f'<tr><td class="n">{i+1}</td><td>{_esc(h["id"])}</td>'
        f'<td>{h["hp_base"]}</td><td>{h["ehp_l0"]}</td>'
        f'<td>{h["dmg_per_hit_l0"]}</td><td>{h["skill_dmg_mult"]}</td>'
        f'<td>{h["weapon_l4_over_l0"]}</td></tr>'
        for i, h in enumerate(heroes))

    # 图 2：血量成长按档位着色
    classes = defaultdict(list)
    for h in heroes:
        if h["hp_growth"] is not None:
            classes[h["hp_growth"]].append(h)
    series = []
    for ci, (g, hs) in enumerate(sorted(classes.items())):
        for h in hs:
            series.append({"values": h["hp_tiers"], "color": PALETTE[ci % len(PALETTE)],
                           "width": 1.3, "opacity": 0.85})
        series.append({"values": [], "color": PALETTE[ci % len(PALETTE)],
                       "legend": f"+{g} / 阶（{len(hs)} 人）"})
    lc = line_chart([s for s in series if s["values"]] + [s for s in series if not s["values"]],
                    ["装备 1", "装备 2", "装备 3", "装备 4", "装备 5"], "生命值", "生命成长线")

    # 图 3：怪物难度层
    picks = [f for f in mc["families"] if f["variants"] >= 3 and not f["is_boss"]][:10]
    groups = [{"label": f["family"].replace("_", " "), 
               "values": [f["hp"].get("A"), f["hp"].get("B"), f["hp"].get("C")]} for f in picks]
    bc = bar_chart(groups)
    tier_map = mc.get("tier_to_dungeon_level") or {}
    tier_txt = " / ".join(f"{k} 档 → 地牢 {v} 层" for k, v in tier_map.items())
    sc_rows = "".join(
        f'<tr><td>{_esc(step)}</td><td>×{v["hp"]["median"]}</td><td>{v["hp"]["n"]}</td>'
        f'<td>×{v["dmg"]["median"]}</td><td>{v["dmg"]["n"]}</td></tr>'
        for step, v in mc["tier_scaling"].items()
        if "hp" in v and "dmg" in v and v["hp"]["n"] >= 10)

    # 参数卡
    tm = mc["tier_headline"]
    cards = [
        ("首次进阶 A→B", f"生命 ×{tm.get('hp')}", "伤害同时 ×" + str(tm.get("dmg"))),
        ("二次进阶 B→C", f"生命 ×{mc['tier_scaling']['B->C']['hp']['median']}",
         "伤害只 ×" + str(mc["tier_scaling"]["B->C"]["dmg"]["median"])),
        ("英雄武器成长", f"×{hc['weapon_l4_over_l0_median']}", "装备 1 阶 → 5 阶"),
        ("技能命中成长", f"+{sg['atk_per_level'][0][0]*100:.0f}%", "每级，暴击 +1%"),
        ("怪物设计量", str(mc["designs_vs_variants"]["families"]),
         f"撑起 {mc['designs_vs_variants']['variants']} 个变体"),
        ("英雄生命基准", f"{hc['hp_base_range'][0]}–{hc['hp_base_range'][1]}", "只有 5 档成长"),
    ]
    card_html = "".join(
        f'<div class="card"><div class="cl">{_esc(t)}</div>'
        f'<div class="cv">{_esc(v)}</div><div class="cs">{_esc(s)}</div></div>'
        for t, v, s in cards)

    trows = "".join(
        f'<tr><td>{_esc(k)}</td><td>{v["count"]}</td><td>{v["slots_avg"]}</td>'
        f'<td>{v["slots_range"][0]}–{v["slots_range"][1]}</td></tr>'
        for k, v in tc["slots_by_rarity"].items())

    eff_rows = "".join(
        f'<tr><td>+{d*100:.0f}%</td><td>{c}</td></tr>' for d, c in sg["effect_damage_per_tier"][:5])

    return f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>DD1 数值生成器参数</title>
<style>
*{{box-sizing:border-box}}
body{{margin:0;background:#14161a;color:#e8e6e1;font:13px/1.65 -apple-system,"Segoe UI","Microsoft YaHei",sans-serif}}
.wrap{{max-width:1120px;margin:0 auto;padding:32px 24px 64px}}
h1{{font-size:21px;font-weight:500;margin:0 0 6px}}
.sub{{color:#8b8a84;font-size:12.5px;margin-bottom:28px}}
h2{{font-size:15px;font-weight:500;margin:38px 0 4px;padding-top:18px;border-top:1px solid #262a31}}
.h2s{{color:#8b8a84;font-size:12px;margin-bottom:16px}}
.cards{{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:10px;margin:16px 0 8px}}
.card{{background:#1b1e24;border:1px solid #262a31;border-radius:8px;padding:12px 14px}}
.cl{{color:#8b8a84;font-size:11.5px}}.cv{{font-size:20px;font-weight:500;margin:3px 0 1px;color:#e8e6e1}}
.cs{{color:#6f6e69;font-size:11px;line-height:1.4}}
.grid2{{display:grid;grid-template-columns:1fr 300px;gap:24px;align-items:start}}
@media(max-width:880px){{.grid2{{grid-template-columns:1fr}}}}
table{{width:100%;border-collapse:collapse;font-size:12px}}
th{{text-align:left;color:#8b8a84;font-weight:400;border-bottom:1px solid #262a31;padding:6px 8px}}
td{{border-bottom:1px solid #1e2126;padding:5px 8px}}
td.n{{color:#8b8a84;width:22px}}
.note{{background:#1b1e24;border-left:2px solid #378ADD;padding:10px 14px;border-radius:0 6px 6px 0;
color:#a8a69f;font-size:12.5px;margin:14px 0}}
code{{background:#22262d;padding:1px 5px;border-radius:3px;font-size:12px;color:#9FE1CB}}
.foot{{color:#6f6e69;font-size:11.5px;margin-top:36px;border-top:1px solid #262a31;padding-top:14px}}
</style></head><body><div class="wrap">
<h1>DD1 数值生成器参数</h1>
<div class="sub">这页不是数值表，是「生成数值的规则」。抄点会作废，抄线才有用。</div>

<div class="cards">{card_html}</div>

<h2>一、关键倍率</h2>
<div class="h2s">全部为样本中位数，来自 {mc['designs_vs_variants']['families']} 个怪物家族 / {len(heroes)} 名英雄</div>

<div class="note">最重要的发现：<b>难度阶梯不是等比数列</b>。第一次进阶伤害 ×{tm.get('dmg')}，
第二次只剩 ×{mc['tier_scaling']['B->C']['dmg']['median']}；而生命始终稳定在 ×1.4 左右。
也就是说 <b>前期靠伤害暴增制造压迫感，后期靠血量拖长战斗</b>。
如果你把每档都做成等比放大，高难度会变成单纯的数值碾压，失去节奏变化。</div>

<table><tr><th>难度进阶</th><th>生命倍率</th><th>样本</th><th>伤害倍率</th><th>样本</th></tr>{sc_rows}</table>

<h2>二、英雄平衡空间</h2>
<div class="h2s">15 名英雄落在二维空间的分布。横轴是抗打程度，纵轴是输出。编号对应右下表格。</div>
<div class="grid2">
<div>{sc}</div>
<div><table>
<tr><th>#</th><th>英雄</th><th>生命</th><th>折算</th><th>伤害</th><th>修正</th><th>成长</th></tr>
{legend_rows}
</table></div>
</div>
<div class="note">左上角是「脆皮高输出」（盗墓贼、小丑），右下角是「肉盾低输出」（十字军、麻风病人）。
中间留白区说明 DD1 刻意不做「均衡型」英雄——每个英雄都有明确的极端，靠队伍搭配补短板。
这是你设计原创角色时最该继承的结构性决策。</div>

<h2>三、生命成长是等差数列</h2>
<div class="h2s">15 名英雄全部符合 <code>生命 = 基准 + 成长档 × 装备阶</code>，成长档只有 5 个离散值</div>
{lc}
<div class="note">5 条平行线，斜率分别是 +3 / +4 / +5 / +6 / +7。也就是说 75 个数字只需
<b>15 个基准值 + 1 个成长档</b> 就能完全复现。你的游戏只要定这两件事，血量曲线就自动成立。</div>

<h2>四、怪物难度层缩</h2>
<div class="h2s">A / B / C 三档难度下的生命值。同一套怪，三个强度。经验证：{_esc(tier_txt)}</div>
{bc}
<div class="note">{mc['designs_vs_variants']['families']} 个家族共 {mc['designs_vs_variants']['variants']} 个变体。
真实内容量是 <b>{mc['designs_vs_variants']['families']} 个设计</b>（怪物家族数），不是 {mc['designs_vs_variants']['variants']} 个。
变体只是同一设计的难度复制，美术与行为完全复用——这是 DD1 用有限美术撑起长线内容的核心手法。
你的游戏如果做 5 个区域 × 3 层难度，怪物设计量只需要 <b>一个区域 20–25 个</b>就够。</div>

<h2>五、技能升级到底加什么</h2>
<div class="h2s">这是最反直觉的一条</div>
<div class="note">英雄技能的<b>伤害修正逐级不变</b>（387 次比较中 387 次差值为 0）。
技能升级只加命中 <b>+{sg['atk_per_level'][0][0]*100:.0f}%</b> 和暴击 <b>+{sg['crit_per_level'][0][0]*100:.0f}%</b>。
真正的伤害成长藏在效果的伤害乘算里，每级 <b>+5%</b>：</div>
<table><tr><th>效果伤害乘算逐级增量</th><th>出现次数</th></tr>{eff_rows}</table>
<div class="note">所以在你的游戏里，<b>「升级技能」和「升级装备」是两条独立曲线</b>：
技能升级提升的是稳定性（命中/暴击），装备升级提升的是数值上限。两者叠加才是完整的成长感。</div>

<h2>六、饰品槽位预算</h2>
<div class="h2s">稀有度不是强度，是「能挂几个效果」</div>
<table><tr><th>稀有度</th><th>数量</th><th>平均槽位</th><th>槽位范围</th></tr>{trows}</table>
<div class="note">所以做自己的饰品时，先定稀有度 → 得到槽位数 → 在槽位内随机分配强度。
不要反过来「先想一个强力效果再定稀有度」，那样必然崩坏。</div>

<div class="foot">
数据来源：Darkest Dungeon 安装目录明文配置，经 tools/gen_curves.py 统计生成。<br>
仅供个人研究与学习，数值与美术版权归 Red Hook Studios 所有。
</div>
</div></body></html>"""


# ---------------------------------------------------------------- 主流程

def main() -> int:
    heroes = load("heroes.json") or []
    monsters = load("monsters.json") or []
    effects = load("effects.json") or []
    buffs = load("buffs.json") or []
    trinkets = load("trinkets.json") or {}
    rules = (load("rules.json") or {}).get("rules", {})

    curves = {
        "meta": {
            "source": "Darkest Dungeon 明文配置",
            "purpose": "数值生成器参数，不是数值表",
            "license": "仅限个人研究，禁止商用",
        },
        "heroes": hero_curves(heroes),
        "skill_growth": skill_growth(heroes, effects),
        "monsters": monster_curves(monsters, load("dungeons.json") or {}),
        "trinkets": trinket_curves(trinkets, buffs),
        "difficulty": {
            "torch_bands": len((rules.get("darkness") or {}).get("range_table") or []),
            "crit_multiplier": (rules.get("player_crit_multiplier_table") or [{}])[0].get("value"),
            "hit_cap": rules.get("cutoffAlwaysHit"),
            "stress_per_passed_turn": rules.get("passed_turn_stress_dmg"),
            "quirks_max_positive": rules.get("quirks_max_positive"),
            "camp_points": rules.get("camp_start_camping_points"),
        },
    }

    out_json = DATA / "balance_curves.json"
    out_json.write_text(json.dumps(curves, ensure_ascii=False, indent=1), encoding="utf-8")

    html = build_html(curves)
    out_html = BASE / "curves.html"
    out_html.write_text(html, encoding="utf-8")

    print(f"已生成 {out_json}（{out_json.stat().st_size/1024:.0f} KB）")
    print(f"已生成 {out_html}（{out_html.stat().st_size/1024:.0f} KB）")
    hc = curves["heroes"]
    print()
    print("核心参数：")
    print(f"  英雄生命基准        {hc['hp_base_range'][0]} – {hc['hp_base_range'][1]}")
    print(f"  生命成长档          {list(hc['hp_growth_classes'].keys())}（5 档）")
    print(f"  武器 5 阶 / 1 阶    ×{hc['weapon_l4_over_l0_median']}")
    print(f"  怪物 A->B 生命      ×{curves['monsters']['tier_headline']['hp']}")
    print(f"  怪物 A->B 伤害      ×{curves['monsters']['tier_headline']['dmg']}")
    sc = curves["monsters"]["tier_scaling"]
    for step, v in sc.items():
        if "hp" in v and "dmg" in v:
            print(f"    {step}: 生命 ×{v['hp']['median']}  伤害 ×{v['dmg']['median']}")
    print(f"  设计 vs 变体        {curves['monsters']['designs_vs_variants']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

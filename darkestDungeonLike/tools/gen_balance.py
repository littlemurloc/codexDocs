#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""数值包生成器：把「设计目标」变成一整套可加载的数值。

不是把 DD1 的数字乘个系数（那只是换个量纲，手感一点没变），
而是把上一轮抽出的**生成器参数**当作骨架，往里填自己的数值点。

产出两种规格：
  faithful  忠实复刻 DD1 曲线 —— 用来校准：生成结果应当几乎还原原值
  signature 差异化规格        —— 每个旋钮都对应一条设计意图

用法：
  python tools/gen_balance.py                 # 生成两种规格
  python tools/gen_balance.py --only signature

输出到 balance/<规格名>/ ，是一个完整的、DdDb 可直接加载的数据目录。
"""

from __future__ import annotations

import argparse
import copy
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
OUT = ROOT / "balance"

# ---------------------------------------------------------------------------
# 设计规格
#
# 每个旋钮都写了「为什么」。改数值之前先读这段，否则很容易把平衡调成一个
# 看起来不一样、玩起来一样的无效改动。
# ---------------------------------------------------------------------------

SPECS: dict = {
    # ------------------------------------------------------------------
    "faithful": {
        "desc": "忠实复刻 DD1 曲线形状，用于验证生成器本身是否正确",
        "intent": "生成结果应当几乎等于 data/ 里的原值；若对不上，说明抽取的曲线参数有误。",
        "hero": {
            "hp_scale": 1.0,       # 生命基准
            "dmg_scale": 1.0,      # 武器伤害均值
            "dmg_var_scale": 1.0,  # 伤害区间宽度（high-low），保持均值不变
            "crit_rate_scale": 1.0,
        },
        "monster": {
            "hp_scale": 1.0,
            "dmg_scale": 1.0,
        },
        "rules": {
            "crit_mult": 1.5,
            "stress_scale": 1.0,
        },
    },
    # ------------------------------------------------------------------
    "signature": {
        "desc": "自研规格：更长、更稳、爆发更强烈、长线压力更可控",
        "intent": (
            "四条改动各有针对性，不是随手调参：\n"
            "  1. 战斗 3.5 轮 → 约 4.8 轮。DD1 的普通交火偏短，往往一轮集火就结束了，\n"
            "     玩家来不及做第二个决策。拉长怪物生命可以让「控制 → 集火 → 补刀」\n"
            "     这条链路真正跑起来。\n"
            "  2. 伤害方差收窄到 0.62。武器区间 6-12（跨 2 倍）意味着单次攻击的运气权重\n"
            "     过大，一次低伤就可能让整场节奏崩掉。收窄后均值不变，但下限抬高了。\n"
            "  3. 暴击率 ×0.62、倍率 1.85。原配置 0.5 的期望加成 ≈ 新的 0.527，\n"
            "     期望几乎不变，方差却明显变大——「平时平淡、偶尔爆发」的观感更强。\n"
            "  4. 压力 ×0.7。战斗变长 1.4 倍后，若不调低，单场压力会从 11-18 涨到 15-25，\n"
            "     叠加多场远征会失控。压到 0.7 让单场压力回到基线水平，\n"
            "     把压力预算留给「远征长度」而不是「单场战斗」。"
        ),
        "hero": {
            "hp_scale": 1.0,       # 不动：战斗变长，承伤自然增多，危险度靠它上升
            "dmg_scale": 1.0,
            "dmg_var_scale": 0.62,
            "crit_rate_scale": 0.62,
        },
        "monster": {
            "hp_scale": 1.45,      # 目标：轮数 3.46 → 约 4.8
            "dmg_scale": 1.0,      # 不动：危险度靠轮数累积，不靠单次致命
        },
        "rules": {
            # 期望校验：原 crit×(1.5-1)=0.5×crit
            #           新 (0.62×crit)×(1.85-1)=0.527×crit  ≈ 持平
            "crit_mult": 1.85,
            "stress_scale": 0.7,
        },
    },
    # ------------------------------------------------------------------
    # M3 的产物：signature 在远征尺度上被判为「不合格」，这是修正版。
    #
    # 诊断：signature 把怪物生命 ×1.45，战斗从 4.1 轮拉到 5.3 轮。
    # 单场指标（溢出、暴击、压力）全部达标，但一放进远征就崩——
    # 中图 7 场打完的完成率只有 0.33，团灭率 0.67。
    #
    # 原因很直接：战斗长 29%，英雄就多挨 29% 的打，而治疗输出没有变。
    # 「每轮承受 > 每轮治疗」的意思是净掉血，7 场下来必然见底。
    # M2 当时看不到这一点，因为三场连打之后血量反而在涨——
    # 只有把资源层接上、治疗被封、补给有限，这个洞才露出来。
    #
    # 修法：保留「更长」这个设计意图，同时把单位时间伤害压下来。
    # 这不是把数字调软，而是把「时长」与「强度」解耦——
    # 想让玩家做更多决策，不该靠让他多挨打。
    # ------------------------------------------------------------------
    "signature_v2": {
        "desc": "signature 的远征修正版：战斗仍然更长，但单位时间伤害下调",
        "intent": (
            "signature 在单场指标上全绿、在远征指标上崩盘（完成率 0.33）。\n"
            "  原因：战斗长 29% → 多挨 29% 的打，治疗输出不变 → 净掉血。\n"
            "  修正：怪物伤害 ×0.85，保留长战斗，削掉随时间累积的伤害速率。"
        ),
        "hero": {
            "hp_scale": 1.0,
            "dmg_scale": 1.0,
            "dmg_var_scale": 0.62,
            "crit_rate_scale": 0.62,
        },
        "monster": {
            "hp_scale": 1.45,
            "dmg_scale": 0.85,
        },
        "rules": {
            "crit_mult": 1.85,
            "stress_scale": 0.7,
        },
    },
    # ------------------------------------------------------------------
    # 诊断用，不是设计规格：用来回答"测量器到底能不能测出危险度"。
    # 如果连怪物伤害提高 60% 都测不出死亡差异，说明 bench 的危险度维度是坏的，
    # 那上面所有对比都只在「节奏」上有效，在「压迫感」上是盲的。
    "lethal_probe": {
        "desc": "【诊断用，非设计规格】怪物伤害 ×1.6，检验测量器对危险度是否敏感",
        "intent": "灵敏度自检：若此规格下阵亡率仍为 0，说明 bench 测不出危险度差异。",
        "hero": {"hp_scale": 1.0, "dmg_scale": 1.0, "dmg_var_scale": 1.0,
                 "crit_rate_scale": 1.0},
        "monster": {"hp_scale": 1.0, "dmg_scale": 1.6},
        "rules": {"crit_mult": 1.5, "stress_scale": 1.0},
    },
}

# 受 stress_scale 影响的规则键（压力量纲）
STRESS_KEYS: list = [
    "monster_crit.stress_damage",
    "monster_crit.companion_stress_damage",
    "player_crit.stress_relief",
    "player_crit.companion_stress_relief",
    "deaths_door_self_stress_dmg",
    "deaths_door_companion_stress_dmg",
    "deaths_door_self_stress_dmg_repeat",
    "deaths_door_companion_stress_dmg_repeat",
    "passed_turn_stress_dmg",
    "combat_retreat_stress",
    "killing_blow_stress_relief",
]


# ---------------------------------------------------------------------------
# 变换
# ---------------------------------------------------------------------------


def scale_range(lo: float, hi: float, mean_scale: float, var_scale: float) -> tuple:
    """缩放一个伤害区间。

    mean_scale 调整均值，var_scale 调整宽度（1.0 = 不变，<1 = 收窄）。
    两者独立，这样才能做到「整体变强」和「运气影响变小」互不干扰。
    """
    mean = (lo + hi) / 2.0 * mean_scale
    span = (hi - lo) * var_scale
    return (mean - span / 2.0, mean + span / 2.0)


def transform_heroes(heroes: list, spec: dict) -> tuple:
    """返回 (新数据, 变更计数)"""
    h = spec["hero"]
    out = copy.deepcopy(heroes)
    n = 0
    for hero in out:
        for w in hero.get("weapons", []):
            dmg = w.get("dmg")
            if not isinstance(dmg, list) or len(dmg) < 2:
                continue
            lo, hi = float(dmg[0]), float(dmg[1])
            nlo, nhi = scale_range(lo, hi, h["dmg_scale"], h["dmg_var_scale"])
            w["dmg"] = [max(1, int(round(nlo))), max(1, int(round(nhi)))]
            n += 1
            if "crit" in w:
                w["crit"] = round(float(w["crit"]) * h["crit_rate_scale"], 4)
                n += 1
        for a in hero.get("armours", []):
            if "hp" in a:
                a["hp"] = max(1, int(round(float(a["hp"]) * h["hp_scale"])))
                n += 1
    return out, n


def transform_monsters(monsters: list, spec: dict) -> tuple:
    """怪物：只按档位缩放基础数值，技能结构原样保留。"""
    m = spec["monster"]
    out = copy.deepcopy(monsters)
    n = 0
    for mon in out:
        st = mon.get("stats") or {}
        if "hp" in st:
            st["hp"] = max(1, int(round(float(st["hp"]) * m["hp_scale"])))
            n += 1
        if m["dmg_scale"] != 1.0:
            for skill in mon.get("skills", []):
                dmg = skill.get("dmg")
                if isinstance(dmg, list) and len(dmg) >= 2:
                    lo, hi = float(dmg[0]), float(dmg[1])
                    nlo, nhi = scale_range(lo, hi, m["dmg_scale"], 1.0)
                    skill["dmg"] = [max(0, int(round(nlo))), max(1, int(round(nhi)))]
                    n += 2
    return out, n


def transform_effects(effects: list, spec: dict) -> tuple:
    """效果里的压力值也要跟着调。

    只改规则常量是不够的：单场战斗的压力大头来自怪物技能自带的 stress 效果，
    战斗一变长，这部分会等比放大，把规则侧的下调全部吃掉。
    """
    s = spec["rules"]["stress_scale"]
    out = copy.deepcopy(effects)
    n = 0
    if s == 1.0:
        return out, n
    for eff in out:
        v = eff.get("stress")
        # 只缩放加压值；减压另走别的字段，不动它以免把回血翻成伤害
        if isinstance(v, (int, float)) and v > 0:
            eff["stress"] = max(1, int(round(v * s)))
            n += 1
        elif isinstance(v, list) and v and isinstance(v[0], (int, float)) and v[0] > 0:
            eff["stress"] = [max(1, int(round(x * s))) for x in v]
            n += 1
    return out, n


def transform_rules(rules: dict, spec: dict) -> tuple:
    r = spec["rules"]
    out = copy.deepcopy(rules)
    body = out.get("rules", out)
    n = 0

    if r["crit_mult"] != 1.5:
        for key in ("player_crit_multiplier_table", "monster_crit_multiplier_table"):
            tbl = body.get(key)
            if isinstance(tbl, list):
                for row in tbl:
                    if isinstance(row, dict) and "value" in row:
                        row["value"] = r["crit_mult"]
                        n += 1

    if r["stress_scale"] != 1.0:
        for path in STRESS_KEYS:
            parts = path.split(".")
            node = body
            for p in parts[:-1]:
                node = node.get(p) if isinstance(node, dict) else None
                if node is None:
                    break
            if isinstance(node, dict) and parts[-1] in node:
                node[parts[-1]] = round(
                    float(node[parts[-1]]) * r["stress_scale"], 4)
                n += 1
    return out, n


# ---------------------------------------------------------------------------


def load(name: str) -> dict:
    return json.loads((DATA / f"{name}.json").read_text(encoding="utf-8"))


def build(spec_name: str) -> dict:
    spec = SPECS[spec_name]
    dest = OUT / spec_name
    dest.mkdir(parents=True, exist_ok=True)

    changes: dict = {}
    heroes, n = transform_heroes(load("heroes"), spec)
    changes["heroes"] = n
    monsters, n = transform_monsters(load("monsters"), spec)
    changes["monsters"] = n
    rules, n = transform_rules(load("rules"), spec)
    changes["rules"] = n
    effects, n = transform_effects(load("effects"), spec)
    changes["effects"] = n

    files = ["buffs", "trinkets", "quirks", "dungeons", "loot",
             "quests", "inventory", "curio_props", "curio_design_table",
             # 资源层策略不属于「数值」，但必须跟着包走：
             # 每个包都带一份，才能在同一个包里做「只换资源参数」的对照实验。
             "expedition"]
    for f in files:
        src = DATA / f"{f}.json"
        if src.exists():
            (dest / f"{f}.json").write_text(src.read_text(encoding="utf-8"),
                                            encoding="utf-8")

    (dest / "effects.json").write_text(
        json.dumps(effects, ensure_ascii=False), encoding="utf-8")

    (dest / "heroes.json").write_text(
        json.dumps(heroes, ensure_ascii=False), encoding="utf-8")
    (dest / "monsters.json").write_text(
        json.dumps(monsters, ensure_ascii=False), encoding="utf-8")
    (dest / "rules.json").write_text(
        json.dumps(rules, ensure_ascii=False), encoding="utf-8")

    # 规格留档：改了什么、为什么改，比一堆数字有用得多
    (dest / "_spec.json").write_text(json.dumps({
        "name": spec_name,
        "desc": spec["desc"],
        "intent": spec["intent"],
        "knobs": {k: v for k, v in spec.items() if k not in ("desc", "intent")},
        "field_changes": changes,
    }, ensure_ascii=False, indent=1), encoding="utf-8")

    return {"name": spec_name, "changes": changes, "path": str(dest)}


def verify_faithful() -> dict:
    """faithful 规格必须几乎还原原值——这是生成器正确性的自检。"""
    src_h = load("heroes")
    src_m = load("monsters")
    dst_h = json.loads((OUT / "faithful" / "heroes.json").read_text(encoding="utf-8"))
    dst_m = json.loads((OUT / "faithful" / "monsters.json").read_text(encoding="utf-8"))

    diff_h = diff_m = 0
    total_h = total_m = 0
    worst: list = []
    for a, b in zip(src_h, dst_h):
        for wa, wb in zip(a.get("weapons", []), b.get("weapons", [])):
            for k in ("dmg", "crit"):
                if k in wa:
                    total_h += 1
                    if wa[k] != wb.get(k):
                        diff_h += 1
                        if len(worst) < 5:
                            worst.append(("hero.%s.weapon.%s" % (a.get("id"), k), wa[k], wb.get(k)))
        for aa, bb in zip(a.get("armours", []), b.get("armours", [])):
            if "hp" in aa:
                total_h += 1
                if aa["hp"] != bb.get("hp"):
                    diff_h += 1
    for a, b in zip(src_m, dst_m):
        sa, sb = a.get("stats") or {}, b.get("stats") or {}
        if "hp" in sa:
            total_m += 1
            if sa["hp"] != sb.get("hp"):
                diff_m += 1
    return {
        "hero_fields": [total_h, diff_h],
        "monster_hp_fields": [total_m, diff_m],
        "worst": worst,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default="", help="只生成指定规格")
    args = ap.parse_args()

    names = [args.only] if args.only else list(SPECS)
    for n in names:
        if n not in SPECS:
            print("未知规格: %s（可选 %s）" % (n, "/".join(SPECS)))
            return 1
        info = build(n)
        print("  %-10s 变更字段 %s  →  %s" % (n, info["changes"], info["path"]))

    if "faithful" in names or not args.only:
        v = verify_faithful()
        ok = v["hero_fields"][1] == 0 and v["monster_hp_fields"][1] == 0
        print()
        print("  生成器自检（faithful 应还原原值）：")
        print("    英雄数值字段 %d 个，不一致 %d 个" % tuple(v["hero_fields"]))
        print("    怪物生命字段 %d 个，不一致 %d 个" % tuple(v["monster_hp_fields"]))
        if v["worst"]:
            for p, a, b in v["worst"]:
                print("      %s  %s != %s" % (p, a, b))
        print("    结论：%s" % ("生成器正确" if ok else "生成器有偏差，先修再往下走"))
        return 0 if ok else 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

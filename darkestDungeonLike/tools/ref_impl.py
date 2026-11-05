#!/usr/bin/env python3
"""伤害公式的 Python 参考实现 + 交叉验证用例生成器。

为什么要有第二份实现：
    GDScript 那份如果抄错了系数、写反了顺序、或者随机数转录错一位，
    单元测试只要断言写得松就抓不到。用一份独立编写的 Python 实现跑同一批
    输入，逐条比对 hit/crit/damage，能把「两套实现都错得一模一样」以外的
    所有错误都挡住。

两份实现共享的东西只有一件事：随机数算法。这是刻意的——它是唯一无法
"自然"从数据推出的部分，必须逐位对齐才能比较。

用法：
    python tools/ref_impl.py
产出：
    tests/fixtures/cross_validation.json
"""

from __future__ import annotations

import json
import math
from pathlib import Path

MASK32 = 0xFFFFFFFF
DEFAULT_SEED = 0x9E3779B9
HASH_FLOAT = 2654435761
HASH_INT = 2246822519

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "tests" / "fixtures" / "cross_validation.json"


def _mul32(a: int, b: int) -> int:
    """32 位截断乘法，与 GDScript 侧逐位一致。"""
    al = a & 0xFFFF
    ah = (a >> 16) & 0xFFFF
    bl = b & 0xFFFF
    bh = (b >> 16) & 0xFFFF
    return (al * bl + (((ah * bl + al * bh) & 0xFFFF) << 16)) & MASK32


class Rng:
    """xorshift32 + 乘法散列。对应 src/core/dd_rng.gd。"""

    def __init__(self, seed: int) -> None:
        self.state = (seed & MASK32) or DEFAULT_SEED
        self.draws = 0

    def next_u32(self) -> int:
        x = self.state
        x ^= (x << 13) & MASK32
        x ^= x >> 17
        x ^= (x << 5) & MASK32
        self.state = x
        self.draws += 1
        return x

    def next_float(self) -> float:
        return _mul32(self.next_u32(), HASH_FLOAT) / 4294967296.0

    def next_int(self, n: int) -> int:
        if n <= 0:
            return 0
        return _mul32(self.next_u32(), HASH_INT) % n

    def next_int_range(self, lo: int, hi: int) -> int:
        if hi <= lo:
            return lo
        return lo + self.next_int(hi - lo + 1)

    def chance(self, p: float) -> bool:
        if p <= 0.0:
            return False
        if p >= 1.0:
            return True
        return self.next_float() < p


def clamp(v: float, lo: float, hi: float) -> float:
    return min(max(v, lo), hi)


def hit_chance(acc: float, dodge: float, cutoff_miss: float = 0.0, cutoff_hit: float = 0.95) -> float:
    return clamp(acc - dodge, cutoff_miss, cutoff_hit)


def resolve_attack(spec: dict, rng: Rng) -> dict:
    """对应 src/core/damage_formula.gd::resolve_attack。

    运算顺序必须与 GDScript 侧逐行一致，否则浮点结果会出现末位差异。
    """
    acc = float(spec.get("acc", 0.85))
    dodge = float(spec.get("dodge", 0.0))
    chance = hit_chance(acc, dodge, float(spec.get("cutoff_miss", 0.0)), float(spec.get("cutoff_hit", 0.95)))

    if not (rng.next_float() < chance):
        return {"hit": False, "crit": False, "damage": 0, "raw": 0.0, "mult": 1.0, "hit_chance": chance}

    crit_valid = bool(spec.get("crit_valid", True))
    crit_rate = clamp(float(spec.get("crit", 0.0)), 0.0, 1.0)
    crit = crit_valid and (rng.next_float() < crit_rate)

    base_low = float(spec.get("base_low", 0.0))
    base_high = float(spec.get("base_high", base_low))
    t = rng.next_float()
    raw = base_low + (base_high - base_low) * t

    extra = 0.0
    for m in spec.get("mods", []):
        extra += float(m)
    mult = 1.0 + extra

    dmg = raw * mult
    if mult < 0.0:
        mult = 0.0
        dmg = 0.0

    buff_mult = float(spec.get("dmg_mult_buffs", 1.0))
    if buff_mult != 1.0:
        dmg *= buff_mult

    if crit:
        dmg *= float(spec.get("crit_mult", 1.5))

    if not bool(spec.get("ignore_prot", False)):
        prot = clamp(float(spec.get("prot", 0.0)), 0.0, 1.0)
        dmg *= 1.0 - prot
    dmg *= 1.0 + float(spec.get("dmg_taken_mod", 0.0))

    final = math.floor(dmg + 0.5) if dmg > 0.0 else 0

    return {
        "hit": True,
        "crit": crit,
        "damage": int(final),
        "raw": raw,
        "mult": mult,
        "hit_chance": chance,
    }


# ============================================================
# 用例生成
# ============================================================

def build_scenarios(count: int = 120) -> dict:
    gen = Rng(424242)
    scenarios = []

    for i in range(count):
        seed = gen.next_int_range(1, 2_000_000_000)
        base_low = float(gen.next_int_range(2, 20))
        base_high = base_low + float(gen.next_int_range(0, 10))

        n_mods = gen.next_int(4)
        mods = [round(gen.next_float() * 0.6, 3) for _ in range(n_mods)]

        spec = {
            "base_low": base_low,
            "base_high": base_high,
            "acc": round(0.4 + gen.next_float() * 0.8, 4),
            "dodge": round(gen.next_float() * 0.25, 4),
            "crit": round(gen.next_float() * 0.35, 4),
            "crit_mult": 1.5,
            "crit_valid": gen.next_int(5) > 0,
            "prot": round(gen.next_float() * 0.4, 4),
            "mods": mods,
            "dmg_mult_buffs": round(0.7 + gen.next_float() * 0.8, 4),
            "dmg_taken_mod": round(gen.next_float() * 0.5, 4),
            "ignore_prot": gen.next_int(6) == 0,
        }

        expected = resolve_attack(spec, Rng(seed))
        scenarios.append({"index": i, "seed": seed, "spec": spec, "expected": expected})

    return {
        "generated_by": "tools/ref_impl.py",
        "note": "Python 参考实现的输出，供 Godot 侧逐条比对；改动公式后必须重新生成本文件",
        "count": len(scenarios),
        "scenarios": scenarios,
    }


def main() -> None:
    data = build_scenarios()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")

    hits = sum(1 for s in data["scenarios"] if s["expected"]["hit"])
    crits = sum(1 for s in data["scenarios"] if s["expected"]["crit"])
    print(f"生成 {data['count']} 条用例 -> {OUT.relative_to(ROOT)}")
    print(f"  命中 {hits} 条 / 未命中 {data['count'] - hits} 条，其中暴击 {crits} 条")


if __name__ == "__main__":
    main()

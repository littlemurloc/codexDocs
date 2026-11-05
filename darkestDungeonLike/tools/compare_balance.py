#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""对比多套数值包的战斗指标，判断设计目标有没有达成。

用法：
  python tools/compare_balance.py                      # 对比 bench/ 下全部
  python tools/compare_balance.py dd1_baseline signature
  python tools/compare_balance.py --md                 # 输出 markdown 表格
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BENCH = ROOT / "bench"

# 指标说明：展示名、越高越好 / 越低越好 / 中性
METRICS = [
    ("rounds_avg", "战斗轮数", None, "一场交火平均几轮"),
    ("rounds_p90", "轮数 P90", None, "九成战斗不超过的轮数"),
    ("first_kill_round_avg", "首杀轮次", "low", "第一个敌人倒下所需轮数"),
    ("hit_rate", "命中率", None, "攻击命中占比"),
    ("crit_rate", "暴击率", None, "命中中触发暴击的比例"),
    ("overkill_ratio", "溢出伤害占比", "low", "打出去但没进血条的浪费比例"),
    ("damage_to_hp_ratio", "有效伤害/总血量", "high", "接近 1 说明数值刚好够用"),
    ("party_win_rate", "胜率", None, "队伍获胜比例"),
    ("hero_alive_avg", "存活人数", "high", "战斗结束时还站着的人"),
    ("hero_hp_end_ratio", "终局血量占比", "high", "危险度主指标：越低压迫感越强"),
    ("hero_hp_low_water", "最低血量水位", "high", "全队最危险时刻的剩余血量"),
    ("hero_death_rate", "阵亡率", "low", "英雄死亡人次占比"),
    ("deaths_door_per_fight", "死门触发/场", None, "每场进入死门的次数"),
    ("stress_end_avg", "终局压力", None, "结束时候的平均压力值"),
    ("timeout_rate", "超时率", "low", "打到轮数上限还没结束"),
]


def load(name: str) -> dict:
    p = BENCH / f"{name}.json"
    if not p.exists():
        print("找不到 %s" % p)
        sys.exit(1)
    return json.loads(p.read_text(encoding="utf-8"))


def main() -> int:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    md = "--md" in sys.argv
    names = args if args else sorted(
        p.stem for p in BENCH.glob("*.json") if p.stem != "compare")
    if len(names) < 2:
        print("至少需要两套数据才能对比；bench/ 现有：%s" % names)
        return 1

    data = {n: load(n) for n in names}
    scen = sorted(set.intersection(*[set(d["scenarios"]) for d in data.values()]))

    # 连续遭遇是三场合计，口径不同；只在逐场景表里看，不进跨场景平均
    plain = [s for s in scen if not s.startswith("gauntlet")]
    rows: dict = {}
    for key, _label, _dir, _desc in METRICS:
        rows[key] = {}
        for n in names:
            rows[key][n] = {s: data[n]["scenarios"][s].get(key) for s in scen}

    def cell(v) -> str:
        if v is None:
            return "—"
        if isinstance(v, float):
            return "%.3f" % v
        return str(v)

    print()
    print("=" * 78)
    print("数值包对比：" + " vs ".join(names))
    print("=" * 78)

    # 每个场景一张表
    for s in scen:
        print()
        print("【%s】" % s)
        hdr = "%-22s" % "指标" + "".join("%12s" % n for n in names) + "   变化"
        print(hdr)
        print("-" * len(hdr))
        for key, label, _d, _desc in METRICS:
            vals = [rows[key][n][s] for n in names]
            line = "%-22s" % label
            for v in vals:
                line += "%12s" % cell(v)
            if len(vals) >= 2 and isinstance(vals[0], (int, float)) and isinstance(vals[-1], (int, float)):
                if vals[0]:
                    delta = (vals[-1] - vals[0]) / abs(vals[0]) * 100
                    line += "   %+6.1f%%" % delta
            print(line)

    # 跨场景汇总
    print()
    print("-" * 78)
    print("【跨场景平均】")
    hdr = "%-22s" % "指标" + "".join("%12s" % n for n in names) + "   变化"
    print(hdr)
    print("-" * len(hdr))
    summary_rows = []
    for key, label, _d, _desc in METRICS:
        avgs = []
        for n in names:
            vs = [rows[key][n][s] for s in plain
                  if isinstance(rows[key][n].get(s), (int, float))]
            avgs.append(sum(vs) / len(vs) if vs else None)
        line = "%-22s" % label
        for v in avgs:
            line += "%12s" % cell(v)
        if avgs[0] and avgs[-1] is not None:
            line += "   %+6.1f%%" % ((avgs[-1] - avgs[0]) / abs(avgs[0]) * 100)
        print(line)
        summary_rows.append((label, key, avgs))

    # 设计目标达成检查
    print()
    print("-" * 78)
    print("【设计目标检查】")
    goals = [
        ("战斗轮数落在 4.0–5.5", "rounds_avg", 4.0, 5.5),
        ("溢出伤害占比 < 15%", "overkill_ratio", 0.0, 0.15),
        ("有效伤害/总血量 落在 0.9–1.35", "damage_to_hp_ratio", 0.9, 1.35),
        ("阵亡率不高于 15%", "hero_death_rate", 0.0, 0.15),
        ("超时率为 0", "timeout_rate", 0.0, 0.0),
    ]
    all_ok = True
    # 基线包只作参照，不参与目标判定——它本来就不该满足新规格的目标
    judged = names[1:]
    for name, key, lo, hi in goals:
        vals = []
        for n in judged:
            vs = [rows[key][n][s] for s in plain
                  if isinstance(rows[key][n].get(s), (int, float))]
            vals.append(sum(vs) / len(vs) if vs else None)
        checks = ["✓" if (v is not None and lo <= v <= hi) else "✗" for v in vals]
        if any(c == "✗" for c in checks):
            all_ok = False
        print("  %-30s %s   %s" % (
            name, " ".join("%.3f" % v if v is not None else "—" for v in vals), " ".join(checks)))
    print()
    print("  （参照组 %s 不参与判定）" % names[0])

    print()
    print("结论：%s" % ("目标规格 %s 全部达成" % "/".join(judged) if all_ok
                     else "有目标未达成，需要继续调参"))

    if md:
        out = ["| 指标 | " + " | ".join(names) + " |",
               "|" + "---|" * (len(names) + 1)]
        for label, key, avgs in summary_rows:
            out.append("| %s | %s |" % (label, " | ".join(cell(v) for v in avgs)))
        (BENCH / "compare.md").write_text("\n".join(out), encoding="utf-8")
        print("\n已写出 bench/compare.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())

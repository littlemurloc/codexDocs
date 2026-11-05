#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""远征测量的对比与判定。

bench_expedition.gd 只负责「跑并记录」，这个脚本负责「读并下结论」：
它回答两个问题，对应 M3 的两条验收标准——

  1. 资源层是不是真的有用？
     同一套战斗数值，只换资源预设，危险度指标必须单调移动。
     如果 lenient 与 brutal 的指标差不多，说明资源层白做了。

  2. 资源层能不能把「伤害」这个维度重新变成有效维度？
     M2 的结论是：单场战斗里把怪物伤害 ×1.6，结果一点变化都没有。
     在远征尺度上再测一次——如果这次动了，说明「压迫感来自资源」
     这句话被证实；如果还是不动，说明 M3 也没解决问题。

用法：
  python tools/compare_expedition.py                       # 读 bench/exp_*.json
  python tools/compare_expedition.py --preset=standard
"""

from __future__ import annotations

import argparse
import glob
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BENCH = ROOT / "bench"

# 每个预设的设计意图与目标区间。不是「好看的数字」，
# 而是「这个预设应该达到什么手感」——达不到就说明某一层没接上。
GOALS: dict = {
    "lenient": {
        "desc": "补给充足，资源不构成约束",
        "complete_rate": (0.55, 1.00),
        "pressure_index": (0.0, 1.50),
    },
    "standard": {
        "desc": "短途也能感到压力，但大多数人能走出来",
        "complete_rate": (0.50, 0.85),
        "pressure_index": (0.90, 2.40),
    },
    "tight": {
        "desc": "趟数一长就崩，必须靠休整与判断",
        "complete_rate": (0.10, 0.55),
        "pressure_index": (2.00, 3.20),
    },
    "brutal": {
        "desc": "诊断用：确认测量器能测到上限（不是设计目标）",
        "complete_rate": (0.00, 0.20),
        "pressure_index": (2.80, 9.99),
    },
}

# 表格里显示的指标（键, 中文, 格式）
METRICS: list = [
    ("complete_rate", "完成率", ".3f"),
    ("wipe_rate", "团灭率", ".3f"),
    ("death_rate_per_hero_run", "英雄死亡率", ".3f"),
    ("affliction_rate_per_hero_run", "崩溃率", ".3f"),
    ("heart_attack_rate_per_hero_run", "心脏骤停率", ".3f"),
    ("dd_rate_per_hero_run", "死门率", ".3f"),
    ("hp_end", "终局血量", ".3f"),
    ("hp_low_water", "最低血量水位", ".3f"),
    ("stress_end", "终局压力", ".1f"),
    ("light_end", "终局光照", ".1f"),
    ("food_end", "终局口粮", ".2f"),
    ("heals_blocked", "治疗被封/趟", ".1f"),
    ("act_outs", "崩溃摆烂/趟", ".2f"),
    ("pressure_index", "压迫指数", ".3f"),
]


def load(pattern: str) -> list:
    files = sorted(glob.glob(str(ROOT / pattern)))
    out = []
    for f in files:
        try:
            d = json.loads(Path(f).read_text(encoding="utf-8"))
        except Exception:
            continue
        if "presets" not in d:
            continue
        d["_file"] = Path(f).stem
        out.append(d)
    return out


def label(d: dict) -> str:
    """带场景后缀。

    原来 data 包一律标成 data(dd1)，于是 short/Lv1、short/Lv3、medium/Lv3
    三份结果在「伤害灵敏度」表里显示成三行一模一样的名字——
    表能算出来，但读的人分不清哪行是哪份，等于没用。
    """
    data = d.get("data") or ""
    base = "data(dd1)" if not data else Path(data).name
    return f"{base} {d.get('size', '?')}/Lv{d.get('level', '?')}"


def print_preset_table(d: dict) -> None:
    cols = list(d["presets"].keys())
    if not cols:
        return
    print(f"\n### {label(d)}  ·  {d.get('dungeon')}/{d.get('size')} Lv{d.get('level')}"
          f"  ·  {d.get('runs')} 趟/预设  ·  路线 {d.get('route_steps_avg', 0):.1f} 步")
    print("| 指标 | " + " | ".join(cols) + " |")
    print("|---|" + "---:|" * len(cols))
    for key, name, fmt in METRICS:
        cells = []
        for c in cols:
            v = (d["presets"][c] or {}).get(key, 0.0)
            cells.append(format(float(v), fmt))
        print(f"| {name} | " + " | ".join(cells) + " |")


def check_monotonic(d: dict) -> list:
    """资源越紧，压迫指数必须越高。不单调说明某个旋钮方向反了或没接上。"""
    order = [p for p in ["lenient", "standard", "tight", "brutal"] if p in d["presets"]]
    vals = [float(d["presets"][p].get("pressure_index", 0.0)) for p in order]
    problems = []
    for i in range(1, len(vals)):
        if vals[i] < vals[i - 1]:
            problems.append(
                f"{label(d)}: {order[i-1]}({vals[i-1]:.3f}) → {order[i]}({vals[i]:.3f}) 没有上升")
    return problems


def check_goals(d: dict) -> list:
    # 目标区间是按「中图 + 3 级队」定的。短图本来就该更安全、长图本来就该更致命，
    # 拿同一套区间去卡所有场景，只会得到一堆假警报。
    if str(d.get("size", "")) != "medium":
        return []
    problems = []
    for p, g in GOALS.items():
        if p not in d["presets"]:
            continue
        row = d["presets"][p]
        for key in ("complete_rate", "pressure_index"):
            lo, hi = g[key]
            v = float(row.get(key, 0.0))
            if not (lo <= v <= hi):
                problems.append(
                    f"{label(d)}/{p}: {key}={v:.3f} 不在目标区间 [{lo}, {hi}]")
    return problems


def damage_sensitivity(docs: list, preset: str) -> None:
    """固定资源预设，只换战斗数值包——检验伤害维度是否终于有了反应。"""
    rows = []
    for d in docs:
        # 只在同一场景里比：短图和中图的压迫指数本来就不在一个量级，
        # 混进一张表会得出「换数值包让难度降了」这种假结论。
        if str(d.get("size", "")) != "medium":
            continue
        if preset not in d["presets"]:
            continue
        r = d["presets"][preset]
        rows.append((label(d), r))
    if len(rows) < 2:
        return
    print(f"\n### 伤害灵敏度（预设 {preset}）：只换数值包，资源策略完全相同")
    print("| 数值包 | 完成率 | 团灭率 | 英雄死亡率 | 终局血量 | 死门/趟 | 压迫指数 |")
    print("|---|---:|---:|---:|---:|---:|---:|")
    for name, r in rows:
        print("| %s | %.3f | %.3f | %.3f | %.3f | %.2f | %.3f |" % (
            name, r.get("complete_rate", 0), r.get("wipe_rate", 0),
            r.get("death_rate_per_hero_run", 0), r.get("hp_end", 0),
            r.get("dd_entries", 0), r.get("pressure_index", 0)))
    base = rows[0][1].get("pressure_index", 0.0)
    for name, r in rows[1:]:
        cur = r.get("pressure_index", 0.0)
        delta = cur - base
        print(f"- {name} 相对 {rows[0][0]}：压迫指数 {delta:+.3f}"
              f"（{'有响应' if abs(delta) > 0.15 else '无响应'}）")


def to_markdown(docs: list) -> str:
    lines = ["# 远征资源层对比（自动生成）", "", "由 `tools/compare_expedition.py` 生成。", ""]
    for d in docs:
        cols = list(d["presets"].keys())
        if not cols:
            continue
        lines.append(f"## {label(d)} · {d.get('dungeon')}/{d.get('size')} Lv{d.get('level')}")
        lines.append("")
        lines.append("| 指标 | " + " | ".join(cols) + " |")
        lines.append("|---|" + "---:|" * len(cols))
        for key, name, fmt in METRICS:
            cells = [format(float((d["presets"][c] or {}).get(key, 0.0)), fmt) for c in cols]
            lines.append(f"| {name} | " + " | ".join(cells) + " |")
        lines.append("")
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pattern", default="bench/exp_*.json")
    ap.add_argument("--preset", default="standard", help="伤害灵敏度对比用的预设")
    ap.add_argument("--md", default="bench/expedition_compare.md")
    args = ap.parse_args()

    docs = load(args.pattern)
    if not docs:
        print("没有找到远征测量结果，先跑 tests/bench_expedition.gd")
        return 1

    for d in docs:
        print_preset_table(d)

    print("\n## 判定")
    problems: list = []
    for d in docs:
        problems += check_monotonic(d)
    if problems:
        for p in problems:
            print("  ✗ " + p)
    else:
        print("  ✓ 资源越紧，压迫指数单调上升（%d 个包全部通过）" % len(docs))

    goal_problems: list = []
    for d in docs:
        goal_problems += check_goals(d)
    if goal_problems:
        for p in goal_problems:
            print("  · " + p)
    else:
        print("  ✓ 所有预设都落在设计目标区间内")

    damage_sensitivity(docs, args.preset)

    out = ROOT / args.md
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(to_markdown(docs), encoding="utf-8")
    print(f"\n已写入 {out.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

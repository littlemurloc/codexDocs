#!/usr/bin/env python3
"""把策划的奇物设计表摊平成运行期可读的 data/curios.json。

来源是 data/curio_design_table.json（由 curios/curio_type_library.csv 转出）。
那份 CSV 是**排版用**的表格：60 个奇物各占 16 行，合并单元格导成 JSON 后
只剩左上角有值，其余为空串。直接让 GDScript 去读它，等于把「Excel 的行偏移」
写进规则层——换一版策划表就会静默错位。所以先在这里摊平一次。

表格的三列语义（容易看错，记在这里）：
  col2 是**元数据标签列**：紧跟 "ID STRING" / "REGION FOUND" / "FULL CURIO?" /
       "TAGS" 的那一行，col2 才是这些字段的值。它和 col4 的 outcome 列
       **互相错开一行**，所以不能按固定行偏移取，只能按标签取。
  col4 是 **outcome 类型列**：Nothing / Loot / Quirk / Effect / Purge /
       Scouting / Teleport / Disease，连续排下来，权重在 col5。
  col7/col10/col13 是同一 outcome 内的**并列结果**（RESULT 1/2/3），
       每个结果自带值 + 权重 + 百分比。

效果值混了两种东西：
  "Stress 3" / "Blight 1" 这类能直接读出数值；
  "Suit of Armor Shield" / "fish_idol_curse_1" 这类是游戏脚本里的复合效果，
  表里只有名字没有数值。后者一律标成 scripted 并在统计里计数，
  **不猜数值**——猜出来的数字会让后续所有对照实验失去意义。
"""
from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "data" / "curio_design_table.json"
OUT = ROOT / "data" / "curios.json"

OUTCOME_TYPES = {
    "Nothing", "Loot", "Quirk", "Effect",
    "Purge", "Scouting", "Teleport", "Disease",
}
LABELS = {
    "ID STRING": "id",
    "REGION FOUND": "region",
    "FULL CURIO?": "full",
    "TAGS": "tags",
}
# 表格里 "Item Interactions" 之后才是道具交互段；这一段 col4 是道具 id
ITEM_SECTION_MARK = "Item Interactions"

# 通用效果：名字 + 一个数字。匹配不上的一律 scripted。
NUMERIC_EFFECTS = [
    (re.compile(r"^Stress\s+(\d+)$", re.I), "stress"),
    (re.compile(r"^Blight\s+(\d+)$", re.I), "blight"),
    (re.compile(r"^Bleed\s+(\d+)$", re.I), "bleed"),
    (re.compile(r"^Darkness\s+(\d+)$", re.I), "darkness"),
    (re.compile(r"^HealSelf\s+(\d+)$", re.I), "heal_hp"),
    (re.compile(r"^Heal\s+Stress\s+(\d+)$", re.I), "heal_stress"),
]
# "3 - all" / "0 - curios" 之类：揭示 N 跳内的目标
SCOUT_RE = re.compile(r"^(\d+)\s*-\s*(\w+)$", re.I)


def _num(s: str) -> int:
    """表格里的权重/次数是字符串，可能为空或 'N/A'。"""
    s = (s or "").strip()
    if not s or not s.replace(".", "", 1).isdigit():
        return 0
    return int(float(s))


def _pct(s: str) -> float:
    """'75.00%' -> 0.75；空串/箭头说明 -> -1（表示表里没给）。"""
    s = (s or "").strip()
    if not s.endswith("%"):
        return -1.0
    try:
        return float(s[:-1]) / 100.0
    except ValueError:
        return -1.0


def parse_effect(raw: str) -> dict:
    """效果值 -> {kind, value?}。解析不出的标 scripted，保留原文。"""
    s = (raw or "").strip()
    if not s:
        return {}
    for pat, kind in NUMERIC_EFFECTS:
        m = pat.match(s)
        if m:
            return {"kind": kind, "value": int(m.group(1)), "raw": s}
    return {"kind": "scripted", "raw": s}


def parse_scout(raw: str) -> dict:
    m = SCOUT_RE.match((raw or "").strip())
    if not m:
        return {"kind": "scout", "hops": 0, "target": str(raw or "").strip().lower()}
    return {"kind": "scout", "hops": int(m.group(1)), "target": m.group(2).lower()}


def parse_results(row: list[str]) -> list[dict]:
    """把一行里的 RESULT 1/2/3 拆成并列结果列表。"""
    out: list[dict] = []
    for base in (7, 10, 13):
        val = row[base].strip()
        if not val:
            continue
        w = _num(row[base + 1])
        pct = _pct(row[base + 2])
        out.append({"value": val, "weight": w, "pct": pct})
    return out


def build_outcome(otype: str, row: list[str]) -> dict:
    """一个 outcome 行 -> 结构化字典。"""
    raw_results = parse_results(row)
    weight = _num(row[5])
    oc: dict = {
        "type": otype.lower(),
        "weight": weight,
        "chance": _pct(row[6]),
        "note": row[17].strip(),
        "results": [],
    }
    for r in raw_results:
        val = r["value"]
        if otype == "Nothing":
            # "N/A" 在三列 result 里各填了一次，是占位不是结果
            continue
        item: dict = {"weight": r["weight"], "pct": r["pct"], "raw": val}
        if otype == "Loot":
            # 值是 loot 表 id（A/B/CH/TORCHONLY…），权重位放的是抽取次数
            item["kind"] = "loot_table"
            item["table"] = val
            item["draws"] = r["weight"]
        elif otype == "Effect":
            item.update(parse_effect(val))
        elif otype == "Scouting":
            item.update(parse_scout(val))
        elif otype == "Quirk":
            item["kind"] = "quirk"
            item["quirk"] = val
        elif otype == "Disease":
            item["kind"] = "disease"
            item["disease"] = val
        elif otype == "Purge":
            item["kind"] = "purge"
            item["purge"] = val
        elif otype == "Teleport":
            item["kind"] = "teleport"
            item["target"] = val
        elif otype == "Nothing":
            item["kind"] = "nothing"
        else:
            item["kind"] = "unknown"
        oc["results"].append(item)
    return oc


def split_blocks(rows: list[list[str]]) -> list[list[list[str]]]:
    """按 col1 的序号切块。序号是策划的连续编号，比按固定 16 行切更稳。"""
    starts = [i for i, r in enumerate(rows) if r[1].strip().isdigit()]
    starts.append(len(rows))
    return [rows[starts[i]:starts[i + 1]] for i in range(len(starts) - 1)]


def parse_block(block: list[list[str]]) -> dict | None:
    name = block[0][2].strip()
    tier = block[0][4].strip()
    if not name:
        return None

    fields: dict = {"id": "", "region": "", "full": "", "tags": []}
    pending: str | None = None
    outcomes: list[dict] = []
    items: dict[str, list[dict]] = {}
    in_items = False

    for row in block:
        c2 = row[2].strip()
        c3 = row[3].strip()
        c4 = row[4].strip()
        c5 = row[5].strip()

        is_label_row = c2 in LABELS or c2 == ITEM_SECTION_MARK
        # 标签行**本身也是 outcome 行**（"REGION FOUND" 那行的 col4 常常就是 Loot），
        # 所以这里只记 pending，不能用 continue 把它整行跳掉。
        if c2 in LABELS:
            pending = LABELS[c2]
        elif c2 == ITEM_SECTION_MARK:
            in_items = True
            pending = None

        # 标签值先消费：它和 outcome 列错开一行，且同一行 col4 可能正是 outcome 类型
        if pending and c2 and not is_label_row:
            if pending == "tags":
                # TAGS 段：col2 是标签名，col3 是区域限定（"All" 表示不限）
                if c2 and c2 not in ("ALL",) and c4:
                    fields["tags"].append(c2)
            elif not fields[pending]:
                fields[pending] = c2
                pending = None

        if in_items:
            # 道具交互段：col4 = 道具 id，col5 = 结果类型
            if c4 and c4 not in OUTCOME_TYPES and c4 not in ("RESULT TYPES", "ITEM"):
                oc = build_outcome(c5, row)
                oc["note"] = row[17].strip()
                # 道具交互行**没有行级权重**（col5 被 RESULT TYPE 占用，col6 为空）。
                # 每个道具对每个奇物只占一行（已核对：0 组重复），所以权重记 1，
                # 真正的概率分配在行内 result 的百分比列里。
                oc["weight"] = 1
                items.setdefault(c4, []).append(oc)
            continue

        if c4 in OUTCOME_TYPES:
            outcomes.append(build_outcome(c4, row))

    return {
        "id": fields["id"],
        "name": name,
        "tier": tier,
        "region": fields["region"],
        "full": fields["full"].strip().lower() == "yes",
        "tags": fields["tags"],
        "outcomes": [o for o in outcomes],
        "items": items,
    }


def main() -> int:
    rows = json.loads(SRC.read_text(encoding="utf-8"))
    blocks = split_blocks(rows)

    curios: dict[str, dict] = {}
    cid_by_name: dict[str, str] = {}
    dup: list[str] = []
    for blk in blocks:
        c = parse_block(blk)
        if not c:
            continue
        cid = (c.get("id") or "").strip()
        if not cid:
            # 序号块里没有 ID STRING 值，说明这块不是奇物（表尾残留）
            continue
        if cid in curios:
            dup.append(cid)
        curios[cid] = {
            "name": c["name"],
            "tier": c["tier"],
            "region": c["region"],
            "full": c["full"],
            "tags": c["tags"],
            "outcomes": c["outcomes"],
            "items": c["items"],
        }
        cid_by_name[c["name"]] = cid

    # —— 统计：落地率是这一期诚实度的核心指标 ——
    eff_kinds: Counter = Counter()
    occ_types: Counter = Counter()
    item_rows = 0
    item_eff: Counter = Counter()
    for cid, c in curios.items():
        for oc in c["outcomes"]:
            if oc["weight"] > 0:
                occ_types[oc["type"]] += 1
            for r in oc["results"]:
                if r.get("kind") == "scripted":
                    eff_kinds[r["raw"]] += 1
        for it, ocs in c["items"].items():
            item_rows += len(ocs)
            for oc in ocs:
                for r in oc["results"]:
                    if r.get("kind") == "scripted":
                        item_eff[r["raw"]] += 1

    doc = {
        "version": 1,
        "note": (
            "由 tools/gen_curios.py 从 curio_design_table.json 摊平而来，勿手改。"
            "outcomes 的 weight 是该分支的抽取权重（0 = 不出现）；"
            "Loot 分支的 draws 是抽几张 loot 表；"
            "Effect 里 kind=scripted 的是游戏脚本复合效果，表内无数值，运行期计为未支持。"
        ),
        "source": "data/curio_design_table.json",
        "stats": {
            "curios": len(curios),
            "outcome_rows": sum(len(c["outcomes"]) for c in curios.values()),
            "weighted_outcomes": sum(occ_types.values()),
            "item_interaction_rows": item_rows,
            "scripted_effects": sum(eff_kinds.values()) + sum(item_eff.values()),
        },
        "curios": curios,
    }
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")

    print(f"写出 {OUT.relative_to(ROOT)}")
    print(f"  奇物 {len(curios)}  重名/重复 id {len(dup)}")
    print(f"  outcome 行 {doc['stats']['outcome_rows']}（有权重的 {doc['stats']['weighted_outcomes']}）")
    print(f"  道具交互行 {item_rows}")
    print(f"  outcome 类型分布 {occ_types.most_common()}")
    print(f"  scripted 效果 {doc['stats']['scripted_effects']} 条，{len(eff_kinds)} 种：")
    for k, v in eff_kinds.most_common():
        print(f"      {k!r} x{v}")
    if item_eff:
        print("  道具交互里的 scripted：")
        for k, v in item_eff.most_common():
            print(f"      {k!r} x{v}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

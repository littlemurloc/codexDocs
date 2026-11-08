"""Replace invalid hp_cur attribute reads with Y3's native current-HP expression."""

from __future__ import annotations

import json
import sys
from pathlib import Path


RELATIVE = Path("item/134283207.json")


def repair(value, changed):
    if isinstance(value, dict):
        if (value.get("sub_type") == "GET_UNIT_ATTR"
                and len(value.get("args_list", [])) == 3
                and value["args_list"][2].get("args_list") == ["hp_cur"]):
            unit = value["args_list"][0]
            assert unit["arg_type"] == 100006
            value.clear()
            value.update({"arg_type": 100000, "args_list": [unit],
                          "sub_type": "GET_HP_CUR"})
            changed.append(1)
            return
        for child in value.values():
            repair(child, changed)
    elif isinstance(value, list):
        for child in value:
            repair(child, changed)


def stage(source: Path, output: Path):
    data = json.loads((source / RELATIVE).read_text(encoding="utf-8"))
    changed = []
    repair(data, changed)
    if len(changed) != 3:
        raise ValueError(f"expected 3 invalid current-HP reads, got {len(changed)}")
    destination = output / RELATIVE
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(data, ensure_ascii=True, indent=4) + "\n",
                           encoding="utf-8")
    return {"item": 134283207, "current_hp_reads_repaired": len(changed)}


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit("usage: fix_pouch_hp_expression.py MAP3 CANDIDATE_DIR")
    print(stage(Path(sys.argv[1]), Path(sys.argv[2])))

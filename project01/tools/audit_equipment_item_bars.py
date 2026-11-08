"""List item-bar constants in the map3 equipment ECA chain."""

from __future__ import annotations

import json
import sys
from pathlib import Path


KINDS = {
    "UNIT_ADD_ITEM", "UNIT_SLOT_ITEM", "SWITCH_UNIT_ITEM_SLOT_BY_SLOT_ID",
    "SET_UI_COMP_UNIT_EQUIP_SLOT_NEW", "SHIFT_ITEM_NEW",
}


def walk(value):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk(child)


def literal(arg):
    if not isinstance(arg, dict):
        return None
    items = arg.get("args_list", [])
    if arg.get("sub_type") == 1 and len(items) == 1 and isinstance(items[0], int):
        return items[0]
    return None


def main(map_root: Path):
    paths = [
        map_root / "global_trigger/function/new/功能执行/动态创建玩家新队长单位.json",
        *sorted((map_root / "global_trigger/function/new/UI").glob("*装备*.json")),
        *sorted((map_root / "global_trigger/trigger/UI").glob("装备*.json")),
    ]
    for path in paths:
        data = json.loads(path.read_text(encoding="utf-8"))
        for node in walk(data):
            kind = node.get("action_type", node.get("sub_type"))
            if kind not in KINDS:
                continue
            args = node.get("args_list", [])
            print(path.relative_to(map_root).as_posix(), kind,
                  "args=", [literal(arg) for arg in args],
                  "op_arg=", [literal(arg) for arg in node.get("op_arg", [])],
                  "element_id=", node.get("element_id"))


if __name__ == "__main__":
    main(Path(sys.argv[1]))

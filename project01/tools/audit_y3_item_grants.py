"""List map3 ECA item-grant actions and literal object IDs."""

from __future__ import annotations

import json
import sys
from pathlib import Path


def walk(value):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk(child)


def walk_with_context(value, parents=()):
    if isinstance(value, dict):
        yield value, parents
        next_parents = parents
        if "action_type" in value:
            next_parents += (value.get("action_type"),)
        for child in value.values():
            yield from walk_with_context(child, next_parents)
    elif isinstance(value, list):
        for child in value:
            yield from walk_with_context(child, parents)


def main(map_path: Path) -> None:
    for path in (map_path / "global_trigger").rglob("*.json"):
        data = json.loads(path.read_text(encoding="utf-8"))
        for action, parents in walk_with_context(data):
            if not isinstance(action, dict) or action.get("action_type") not in (
                    "UNIT_ADD_ITEM", "UNIT_BUY_ITEM", "CREATE_ITEM", "ADD_ITEM_TO_UNIT"):
                continue
            ids = sorted({value for node in walk(action)
                          if isinstance(node, dict) and "args_list" in node
                          for value in node["args_list"]
                          if isinstance(value, int) and 100000000 <= value <= 200000000})
            labels = sorted({str(item) for node in walk(action)
                             if isinstance(node, dict) and "args_list" in node
                             for item in node["args_list"]
                             if isinstance(item, str) and len(item) < 60})
            print(path.relative_to(map_path).as_posix(), action["action_type"],
                  ids, "parents=", parents[-5:], "labels=", labels[:12])


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: audit_y3_item_grants.py MAP")
    main(Path(sys.argv[1]))

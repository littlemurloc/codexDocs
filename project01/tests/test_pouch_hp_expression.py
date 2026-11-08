"""The pouch must use the same current-HP ECA primitive as native items."""

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


def check(map_path, candidate):
    source = json.loads((map_path / "item/134283207.json").read_text(encoding="utf-8"))
    fixed = json.loads((candidate / "item/134283207.json").read_text(encoding="utf-8"))
    native = json.loads((map_path / "item/134221867.json").read_text(encoding="utf-8"))
    native_reads = [node for node in walk(native) if node.get("sub_type") == "GET_HP_CUR"]
    reads = [node for node in walk(fixed) if node.get("sub_type") == "GET_HP_CUR"]
    assert native_reads and len(reads) == 3
    assert all(node["arg_type"] == native_reads[0]["arg_type"] == 100000
               and len(node["args_list"]) == 1
               and node["args_list"][0]["sub_type"] == "DAMAGE_TARGET_UNIT"
               for node in reads)
    assert sum(node.get("sub_type") == "GET_UNIT_ATTR"
               and any(part.get("args_list") == ["hp_cur"] for part in walk(node))
               for node in walk(source)) == 3
    assert not any(node.get("args_list") == ["hp_cur"] for node in walk(fixed))
    assert source["trigger_dict"].keys() == fixed["trigger_dict"].keys()
    assert [node["element_id"] for node in walk(source) if "element_id" in node] == [
        node["element_id"] for node in walk(fixed) if "element_id" in node]
    print("OK: three current-HP reads use native GET_HP_CUR without changing ECA IDs")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit("usage: test_pouch_hp_expression.py MAP3 CANDIDATE_DIR")
    check(Path(sys.argv[1]), Path(sys.argv[2]))

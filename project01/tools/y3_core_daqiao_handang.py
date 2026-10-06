"""Stage only the evidenced Da Qiao ECA fragment for map3.

This is deliberately not a complete core-loop generator.  The normal-hit
healing branch is staged, but cross-captain cast acquisition and every Han Dang
combat trigger remain absent until their event semantics can be demonstrated.
No shared table, live map, ability, or Lua file is written.
"""

from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path
from typing import Any, Iterator


DAQIAO_UNIT = 134230459
HANDANG_UNIT = 134256942
DAQIAO_ABILITY = 134283907
HANDANG_ABILITY = 134283913
DAQIAO_BUFF = 134283908
HANDANG_BUFF = 134283914
HANDANG_SHIELD_BUFF = 134283916
EMPTY_ABILITY = 134255698

# This function is present in map3 and returns the player's captain group.
CAPTAIN_GROUP_FUNCTION = "6570be50be1a11f1916d7b0e2885c54e"
HIT_TRIGGER = "1418035204"
CAST_TRIGGER = "2011996165"

UNIMPLEMENTED = {
    "daqiao_cast_acquisition": (
        "No same-map generic ET_UNIT_RELEASE_ABILITY modifier instance proves "
        "the caster/ability payload and completed-active-cast semantics for other captains; "
        "one-dew cap and two-second throttling are therefore not staged."
    ),
    "handang_direct_damage": (
        "ET_UNIT_BE_HURT_COMPLETE exists, but the inspected ECA provides no "
        "predicate distinguishing direct hits from periodic or reflected damage; "
        "one-arrow-per-second acquisition is not staged."
    ),
    "handang_retaliation": (
        "Without a proven direct-damage event, the two-arrow/five-second "
        "retaliation, 120% shot, range fallback, and "
        "no-target 8%-max-HP four-second shield cannot be attached safely; "
        "shield Buff 134283916 is reserved but not emitted."
    ),
}


def _read(path: Path) -> Any:
    with path.open(encoding="utf-8") as stream:
        return json.load(stream)


def _nodes(value: Any) -> Iterator[dict[str, Any]]:
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from _nodes(child)
    elif isinstance(value, list):
        for child in value:
            yield from _nodes(child)


def _arg(arg_type: int, sub_type: Any, *values: Any) -> dict[str, Any]:
    return {"arg_type": arg_type, "args_list": list(values), "sub_type": sub_type}


class _Ids:
    def __init__(self) -> None:
        self.value = 1418035204900000

    def next(self) -> int:
        self.value += 1
        return self.value


def _action(ids: _Ids, action_type: str, *values: Any) -> dict[str, Any]:
    return {
        "action_type": action_type,
        "args_list": list(values),
        "bp": False,
        "element_id": ids.next(),
        "enable": True,
    }


def _condition(ids: _Ids, condition_type: str, *values: Any) -> dict[str, Any]:
    return {
        "condition_type": condition_type,
        "args_list": list(values),
        "element_id": ids.next(),
        "enable": True,
    }


def _if(ids: _Ids, conditions: list[dict[str, Any]], actions: list[dict[str, Any]]) -> dict[str, Any]:
    return _action(ids, "IF_THEN_ELSE", _arg(100021, 1, *conditions),
                   _arg(100022, 1, *actions), _arg(100022, 1))


def _float_compare(ids: _Ids, lhs: Any, operator: str, rhs: Any) -> dict[str, Any]:
    return _condition(ids, "FLOAT_COMPARE", lhs, _arg(100015, 1, operator), rhs)


def _unit_compare(ids: _Ids, lhs: Any, operator: str, rhs: Any) -> dict[str, Any]:
    return _condition(ids, "UNIT_COMPARE", lhs, _arg(100035, 1, operator), rhs)


def _modifier() -> dict[str, Any]:
    return _arg(100076, "CUR_MODIFIER")


def _owner() -> dict[str, Any]:
    return _arg(100006, "MODIFIER_OWNER")


def _selected() -> dict[str, Any]:
    return _arg(100006, "FOR_EACH_SELECTED_UNIT")


def _max_hp(unit: dict[str, Any]) -> dict[str, Any]:
    return _arg(100000, "GET_UNIT_ATTR", unit, _arg(100301, 1, "ATTR_RESULT"),
                _arg(100042, 1, "hp_max"))


def _hp_ratio(unit: dict[str, Any]) -> dict[str, Any]:
    return _arg(100000, "ARITHMETIC_OPERATION", _arg(100000, "GET_HP_CUR", unit),
                _arg(100017, 1, "/"), _max_hp(unit))


def _kv_key(name: str) -> dict[str, Any]:
    return _arg(100003, 1, name)


def _unit_kv(name: str) -> dict[str, Any]:
    return _arg(100006, "GET_UNIT_ENTITY_KV", _modifier(), _kv_key(name))


def _float_kv(name: str) -> dict[str, Any]:
    return _arg(100000, "GET_FLOAT_KV", _modifier(), _kv_key(name))


def _captain_group() -> dict[str, Any]:
    return {
        "arg_type": 100026,
        "args_list": [
            _arg(100025, "OWNER_PLAYER", _owner()),
            _arg(100001, 1, False),
            _arg(100003, 1, "所有队长"),
        ],
        "call_rt_index": 0,
        "op_arg": [],
        "op_arg_enable": [],
        "sub_type": CAPTAIN_GROUP_FUNCTION,
    }


def _healing_actions(ids: _Ids) -> list[dict[str, Any]]:
    chosen_key = "daqiao_dew_target"
    ratio_key = "daqiao_dew_min_hp_ratio"
    selected = _selected()
    chosen = _unit_kv(chosen_key)

    reset_target = _action(ids, "SET_ENTITY_KV", _modifier(), _kv_key(chosen_key),
                           _arg(100006, "NONE_UNIT"))
    reset_ratio = _action(ids, "SET_ENTITY_KV", _modifier(), _kv_key(ratio_key),
                          _arg(100000, 1, 1.0))
    choose = _if(ids, [
        _float_compare(ids, _max_hp(selected), ">", _arg(100000, 1, 0.0)),
        _float_compare(ids, _arg(100000, "GET_HP_CUR", selected), ">",
                       _arg(100000, 1, 0.0)),
        _float_compare(ids, _hp_ratio(selected), "<", _float_kv(ratio_key)),
    ], [
        _action(ids, "SET_ENTITY_KV", _modifier(), _kv_key(chosen_key), selected),
        _action(ids, "SET_ENTITY_KV", _modifier(), _kv_key(ratio_key),
                _hp_ratio(selected)),
    ])
    pick = _action(ids, "PICK_UNIT_DO_ACTION", _captain_group(),
                   _arg(100022, 1, choose))

    amount = _arg(100000, "ARITHMETIC_OPERATION", _max_hp(chosen),
                  _arg(100017, 1, "*"), _arg(100000, 1, 0.05))
    cure = _action(ids, "CURE_UNIT", chosen, amount, _arg(100001, 1, True))
    cure["op_arg"] = [_arg(100014, "RELATED_ABILITY", _modifier()),
                      _owner(), None, None, None]
    cure["op_arg_enable"] = [True, True, False, False, False]
    apply = _if(ids, [
        _unit_compare(ids, chosen, "!=", _arg(100006, "NONE_UNIT")),
    ], [
        _action(ids, "SET_BUFF_STACK", _modifier(), _arg(100002, 1, 1)),
        cure,
    ])
    return [reset_target, reset_ratio, pick, apply]


def audit(map_path: Path) -> None:
    """Check only the named map objects and the exact samples used below."""
    map_path = Path(map_path)
    if not map_path.is_dir():
        raise FileNotFoundError(map_path)
    rows = _read(map_path / "tables/单位技能配置表.json")["table_data"]["data"]
    for unit_id in (DAQIAO_UNIT, HANDANG_UNIT):
        matching = [row for row in rows if len(row) >= 10 and row[1] == unit_id]
        if len(matching) != 1 or matching[0][2:10] != [EMPTY_ABILITY] * 8:
            raise ValueError(f"unit {unit_id}: expected eight empty skill slots")
    for object_id in (DAQIAO_ABILITY, DAQIAO_BUFF, HANDANG_ABILITY,
                      HANDANG_BUFF, HANDANG_SHIELD_BUFF):
        for folder in ("ability", "modifier", "editor_table/abilityall",
                       "editor_table/modifierall"):
            if (map_path / folder / f"{object_id}.json").exists():
                raise ValueError(f"reserved ID already occupied: {folder}/{object_id}")

    hit = _read(map_path / "modifier/134248740.json")["trigger_dict"]["1878966277"]
    if not any(node.get("condition_type") == "GET_IS_NORMAL_HIT_FROM_EVENT"
               for node in _nodes(hit["condition"])):
        raise ValueError("normal-hit sample changed")
    if hit["event"][0]["args_list"][1]["args_list"] != ["ET_UNIT_HURT_OTHER"]:
        raise ValueError("normal-hit event sample changed")

    captain_func = _read(map_path / "global_trigger/function/new/参数返回/返回【队长单位组】根据筛选类型名称.json")
    if (captain_func["func_id"] != CAPTAIN_GROUP_FUNCTION
            or "所有队长" not in json.dumps(captain_func, ensure_ascii=False)):
        raise ValueError("captain-group function changed")
    sample = _read(map_path / "ability/134276144.json")
    if not any(node.get("sub_type") == CAPTAIN_GROUP_FUNCTION
               for node in _nodes(sample)):
        raise ValueError("captain-group call sample changed")

    cure_sample = _read(map_path / "ability/134274208.json")
    if not any(node.get("action_type") == "CURE_UNIT"
               for node in _nodes(cure_sample)):
        raise ValueError("cure action sample changed")


def _daqiao_hit_eca(map_path: Path) -> dict[str, Any]:
    eca = copy.deepcopy(_read(map_path / "modifier/134242511.json"))
    hit = eca["trigger_dict"][HIT_TRIGGER]
    eca["trigger_dict"].pop(CAST_TRIGGER)
    eca["local_variable"].pop(CAST_TRIGGER, None)
    eca["trigger_group_info"] = [
        group for group in eca["trigger_group_info"]
        if not (group.get("__tuple__") and group["items"][0] == int(CAST_TRIGGER))
    ]
    eca["trigger_group_info"][0]["key"] = DAQIAO_BUFF
    eca["trigger_group_info"][0]["name"] = str(DAQIAO_BUFF)
    for trigger in eca["trigger_dict"].values():
        trigger["group_id"] = DAQIAO_BUFF

    eca["trigger_dict"]["1485688834"]["action"] = [int(HIT_TRIGGER)]
    loss = eca["trigger_dict"]["594665475"]
    loss["action"] = [node for node in loss["action"]
                      if node["action_type"] == "UNREG_TRIGGER"
                      and "temp触发器" in json.dumps(node, ensure_ascii=False)]
    hit["event"][0]["args_list"][1]["args_list"] = ["ET_UNIT_HURT_OTHER"]
    ids = _Ids()
    hit["condition"] = [
        _condition(ids, "GET_IS_NORMAL_HIT_FROM_EVENT"),
        _float_compare(ids, _arg(100002, "GET_MOD_STACK", _modifier()), ">=",
                       _arg(100002, 1, 2)),
    ]
    hit["action"] = _healing_actions(ids)
    return eca


def _check_candidate(eca: dict[str, Any]) -> None:
    triggers = eca["trigger_dict"]
    if CAST_TRIGGER in triggers or len(triggers) != 4:
        raise AssertionError("unexpected inherited trigger")
    hit = triggers[HIT_TRIGGER]
    if hit["event"][0]["args_list"][1]["args_list"] != ["ET_UNIT_HURT_OTHER"]:
        raise AssertionError("normal-hit event lost")
    types = [node.get("action_type") for node in _nodes(hit["action"])]
    if types.count("CURE_UNIT") != 1 or types.count("SET_BUFF_STACK") != 1:
        raise AssertionError("healing/consumption action missing")
    if not any(node.get("sub_type") == CAPTAIN_GROUP_FUNCTION
               for node in _nodes(hit["action"])):
        raise AssertionError("captain group missing")
    if eca["trigger_dict"]["1485688834"]["action"] != [int(HIT_TRIGGER)]:
        raise AssertionError("normal-hit child not registered")
    if str(134242511) in json.dumps(eca):
        raise AssertionError("template Buff ID survived")
    if CAST_TRIGGER in json.dumps(eca):
        raise AssertionError("template cast trigger survived")


def stage(map_path: Path, out_path: Path) -> dict[str, Any]:
    """Write one partial Buff ECA; never imply both core loops are complete.

    Returns the staged path and explicit missing branches.  Han Dang files and
    both shared-table bindings are intentionally absent.
    """
    map_path = Path(map_path).resolve()
    out_path = Path(out_path).resolve()
    if out_path == map_path or map_path in out_path.parents:
        raise ValueError("out_path must not be inside the read-only map")
    audit(map_path)
    eca = _daqiao_hit_eca(map_path)
    _check_candidate(eca)
    target = out_path / "modifier" / f"{DAQIAO_BUFF}.json"
    if target.exists():
        raise FileExistsError(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(eca, stream, ensure_ascii=True, indent=4)
        stream.write("\n")
    return {"staged": [str(target)], "unimplemented": UNIMPLEMENTED.copy()}


def _self_check(map_path: Path) -> None:
    audit(map_path)
    eca = _daqiao_hit_eca(map_path)
    _check_candidate(eca)
    json.loads(json.dumps(eca))
    print("Static self-check OK: Da Qiao normal-hit healing branch only.")
    for name, reason in UNIMPLEMENTED.items():
        print(f"UNIMPLEMENTED {name}: {reason}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("map_path", type=Path)
    parser.add_argument("out_path", type=Path, nargs="?")
    args = parser.parse_args()
    if args.out_path is None:
        _self_check(args.map_path)
    else:
        print(stage(args.map_path, args.out_path))

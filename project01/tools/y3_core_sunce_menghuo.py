"""Stage evidence-backed, unbound ECA fragments for Sun Ce and Meng Huo.

The current map does not prove either complete loop. ``stage`` therefore writes
only a separately marked Meng Huo death-gain fragment, never a bindable
``modifier/<id>.json`` or a shared table. No Lua or approximate strike is used.
"""

from __future__ import annotations

import argparse
import copy
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator


EMPTY_ABILITY = 134255698
HEROES = {
    134260498: (134283903, 134283904),
    134255426: (134283905, 134283906),
}
RESERVED_RAGE_BUFF = 134283915
CURRENT_MELEE_MINION = 134270627


@dataclass(frozen=True)
class Blocker:
    code: str
    evidence: str
    requirement: str


class EcaSemanticBlocker(RuntimeError):
    """The map evidence cannot support a complete, behaviorally exact ECA."""

    def __init__(self, blockers: list[Blocker]):
        self.blockers = blockers
        super().__init__("\n".join(
            f"{item.code}: {item.evidence}; need {item.requirement}"
            for item in blockers
        ))


def _read_json(path: Path) -> Any:
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


def _events(eca: dict[str, Any], event_type: str) -> list[dict[str, Any]]:
    return [
        trigger
        for trigger in eca["trigger_dict"].values()
        if any(event.get("event_type") == event_type
               for event in trigger.get("event", []))
    ]


def _unit_event(trigger: dict[str, Any], name: str) -> bool:
    return any(
        name in node.get("args_list", [])
        for node in _nodes(trigger.get("event", []))
        if node.get("sub_type") in (1, "GENERIC_UNIT_EVENT")
    )


def _actions(value: Any, action_type: str) -> list[dict[str, Any]]:
    return [node for node in _nodes(value)
            if node.get("action_type") == action_type]


def _one(values: list[Any], label: str) -> Any:
    if len(values) != 1:
        raise ValueError(f"{label}: expected one map instance, got {len(values)}")
    return values[0]


def _soldier_leader_key(map_path: Path) -> str:
    creation = _read_json(map_path / "global_trigger/function/new/功能执行/创建英雄队伍单位.json")
    assignments = [
        action for action in _actions(creation, "SET_ENTITY_KV")
        if len(action.get("args_list", [])) == 3
        and action["args_list"][0].get("sub_type") == 11
        and action["args_list"][2].get("sub_type") == 11
    ]
    return _one(assignments, "soldier-to-leader KV")["args_list"][1]["args_list"][0]


def _check_current_minion(map_path: Path) -> None:
    creation = _read_json(map_path / "global_trigger/function/new/功能执行/动态创建玩家新队长单位.json")
    soldier_types = [
        action["args_list"][2]["args_list"][0]
        for action in _actions(creation, "SET_ENTITY_KV")
        if len(action.get("args_list", [])) == 3
        and action["args_list"][1].get("args_list") == ["队伍小兵类型"]
    ]
    if soldier_types != [CURRENT_MELEE_MINION]:
        raise ValueError(f"current team minion type changed: {soldier_types}")
    soldier = _read_json(map_path / f"editor_table/editorunit/{CURRENT_MELEE_MINION}.json")
    if "刀兵" not in soldier["tags"]["items"]:
        raise ValueError("current minion no longer has the 刀兵 tag")


def _death_fragment(map_path: Path) -> dict[str, Any]:
    """Clone actual modifier registration and death actions, then narrow them."""
    source = _read_json(map_path / "modifier/134224731.json")
    eca = copy.deepcopy(source)
    parent_id, child_id, loss_id = "1485688834", "1418035204", "594665475"
    eca["trigger_dict"] = {key: eca["trigger_dict"][key]
                           for key in (loss_id, child_id, parent_id)}
    eca["local_variable"] = {key: eca["local_variable"][key]
                             for key in (loss_id, child_id, parent_id)}
    eca["trigger_group_info"][0]["group"] = [
        item for item in eca["trigger_group_info"][0]["group"]
        if item["items"][0] in (int(parent_id), int(loss_id))
    ]
    eca["trigger_group_info"][0].update(key=134283906, name="134283906")
    eca["variable_dict"].pop("NEW_TIMER", None)
    for key in list(eca["variable_length_dict"]):
        if key not in eca["variable_dict"].get("DYNAMIC_TRIGGER_INSTANCE", {}):
            eca["variable_length_dict"].pop(key)
    for trigger in eca["trigger_dict"].values():
        trigger["group_id"] = 134283906

    parent = eca["trigger_dict"][parent_id]
    parent["action"] = [int(child_id)]
    loss = eca["trigger_dict"][loss_id]
    loss["action"] = [action for action in loss["action"]
                      if action.get("action_type") == "UNREG_TRIGGER"]
    if len(loss["action"]) != 1:
        raise ValueError("loss-trigger unregistration template changed")

    child = eca["trigger_dict"][child_id]
    child["event"][0]["args_list"][0]["args_list"] = ["ET_UNIT_DIE"]
    leader_key = _soldier_leader_key(map_path)
    ownership_sample = _read_json(map_path / "modifier/134277456.json")
    owner_compare = copy.deepcopy(_one([
        node for node in _nodes(ownership_sample)
        if node.get("condition_type") == "UNIT_COMPARE"
    ], "unit-owner comparison"))
    leader_lookup = _one([
        node for node in _nodes(_read_json(map_path / "modifier/134227930.json"))
        if node.get("sub_type") == "GET_UNIT_ENTITY_KV"
        and node["args_list"][1]["args_list"] == [leader_key]
    ], "soldier leader lookup")
    leader_lookup = copy.deepcopy(leader_lookup)
    leader_lookup["args_list"][0]["sub_type"] = "KILLED_UNIT"
    owner_compare["args_list"][0] = leader_lookup
    owner_compare["element_id"] = 1418035204900001

    type_sample = _read_json(map_path / "modifier/134247641.json")
    type_compare = copy.deepcopy(_one([
        node for node in _nodes(type_sample)
        if node.get("condition_type") == "UNIT_CLASS_COMPARE"
    ], "unit-class comparison"))
    type_compare["args_list"][0]["args_list"][0]["sub_type"] = "KILLED_UNIT"
    type_compare["args_list"][2]["args_list"] = [CURRENT_MELEE_MINION]
    type_compare["element_id"] = 1418035204900002

    stack_sample = _read_json(map_path / "modifier/134220504.json")
    stack_limit = copy.deepcopy(_one([
        node for node in _nodes(stack_sample)
        if node.get("condition_type") == "FLOAT_COMPARE"
        and node.get("args_list", [{}])[0].get("sub_type") == "GET_MOD_STACK"
        and node["args_list"][1].get("args_list") == ["<"]
    ], "stack-limit comparison"))
    stack_limit["args_list"][0]["args_list"] = [
        {"arg_type": 100076, "args_list": [], "sub_type": "CUR_MODIFIER"}
    ]
    stack_limit["args_list"][2]["args_list"] = [4]
    stack_limit["element_id"] = 1418035204900003
    child["condition"] = [owner_compare, type_compare, stack_limit]
    if len(child["action"]) != 1 or child["action"][0].get("action_type") != "ADD_BUFF_STACK":
        raise ValueError("death stack action template changed")
    child["action"][0]["element_id"] = 1418035204900004

    assert {event.get("event_type") for trigger in eca["trigger_dict"].values()
            for event in trigger["event"]} == {
                "OBTAIN_MODIFIER", "LOSS_MODIFIER", "GENERIC_UNIT_EVENT"
            }
    assert [_unit_event(child, "ET_UNIT_DIE"),
            child["action"][0]["args_list"][1]["args_list"] == [1]] == [True, True]
    assert not _actions(eca, "RUN_LOOP_TIMER")
    return eca


def _rage_speed_fragment(map_path: Path) -> dict[str, Any]:
    """Preserve the map's gain/clear attribute lifecycle, changing only 10 to 20."""
    eca = copy.deepcopy(_read_json(map_path / "modifier/134238612.json"))
    eca["trigger_group_info"][0].update(key=RESERVED_RAGE_BUFF,
                                         name=str(RESERVED_RAGE_BUFF))
    for trigger in eca["trigger_dict"].values():
        trigger["group_id"] = RESERVED_RAGE_BUFF
        if trigger["event"][0]["event_type"] == "OBTAIN_MODIFIER":
            attributes = [action for action in trigger["action"]
                          if action.get("action_type") == "ADD_MODIFIER_OWNER_ATTR"
                          and action["args_list"][1]["args_list"] == ["attack_speed"]
                          and action["args_list"][2]["args_list"] == ["ATTR_ALL_RATIO"]]
            speed = _one(attributes, "rage attack-speed ratio")
            if speed["args_list"][3]["args_list"] != [10.0]:
                raise ValueError("rage attribute sample changed")
            speed["args_list"][3]["args_list"] = [20.0]
            trigger["action"] = [speed]
        elif trigger["event"][0]["event_type"] == "LOSS_MODIFIER":
            if [action.get("action_type") for action in trigger["action"]] != [
                "CLEAR_MODIFIER_OWNER_ATTR"
            ]:
                raise ValueError("rage attribute cleanup sample changed")
        else:
            raise ValueError("unexpected rage attribute sample trigger")
    assert len(_actions(eca, "ADD_MODIFIER_OWNER_ATTR")) == 1
    assert len(_actions(eca, "CLEAR_MODIFIER_OWNER_ATTR")) == 1
    return eca


def _write_new_json(path: Path, value: Any) -> None:
    if path.exists():
        if _read_json(path) != value:
            raise FileExistsError(f"refusing to replace an existing staged artifact: {path}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, ensure_ascii=True, indent=2)
        stream.write("\n")


def audit(map_path: Path) -> list[Blocker]:
    """Check targeted map instances without scanning other map or Git content."""
    map_path = Path(map_path)
    skill_table = _read_json(map_path / "tables/单位技能配置表.json")
    rows = skill_table["table_data"]["data"]
    for unit_id, (ability_id, buff_id) in HEROES.items():
        matching = [row for row in rows if len(row) > 6 and row[1] == unit_id]
        if len(matching) != 1:
            raise ValueError(f"unit {unit_id}: expected one skill row, got {len(matching)}")
        if matching[0][2:10] != [EMPTY_ABILITY] * 8:
            raise ValueError(f"unit {unit_id}: skill slots are not all empty")
        for object_id in (ability_id, buff_id):
            for folder in ("ability", "modifier", "editor_table/abilityall",
                           "editor_table/modifierall"):
                target = map_path / folder / f"{object_id}.json"
                if target.exists():
                    raise ValueError(f"reserved object ID is already present: {target}")
    for folder in ("modifier", "editor_table/modifierall"):
        target = map_path / folder / f"{RESERVED_RAGE_BUFF}.json"
        if target.exists():
            raise ValueError(f"rage Buff reservation is already occupied: {target}")
    _check_current_minion(map_path)
    if _soldier_leader_key(map_path) != "所属英雄":
        raise ValueError("soldier ownership KV changed")

    normal_hit = _read_json(map_path / "modifier/134248740.json")
    hit_triggers = [
        trigger for trigger in _events(normal_hit, "SPECIAL_UNIT_EVENT")
        if _unit_event(trigger, "ET_UNIT_HURT_OTHER")
        and any(node.get("condition_type") == "GET_IS_NORMAL_HIT_FROM_EVENT"
                for node in _nodes(trigger.get("condition", [])))
    ]
    if not hit_triggers:
        raise ValueError("normal-hit reference 134248740 changed")

    death_sample = _read_json(map_path / "modifier/134224731.json")
    death_triggers = [
        trigger for trigger in _events(death_sample, "GENERIC_UNIT_EVENT")
        if _unit_event(trigger, "ET_BEFORE_UNIT_DIE")
    ]
    if len(death_triggers) != 1:
        raise ValueError("generic-death reference 134224731 changed")
    death = death_triggers[0]
    death_conditions = {node.get("condition_type")
                        for node in _nodes(death.get("condition", []))}
    if death.get("enabled") is not False or not {"PLAYER_COMPARE", "UNIT_HAS_TAG"} <= death_conditions:
        raise ValueError("generic-death reference no longer matches inspected evidence")
    parent = death_sample["trigger_dict"][str(death["p_trigger_id"])]
    if int(death["trigger_id"]) not in parent["action"]:
        raise ValueError("generic-death subtrigger is no longer parent-registered")
    global_death = _read_json(map_path / "global_trigger/trigger/游戏业务/其他事件02.json")
    death_events = [node for node in _nodes(global_death)
                    if isinstance(node.get("event"), list)
                    and _unit_event(node, "ET_UNIT_DIE")
                    and any(arg.get("sub_type") == "KILLED_UNIT"
                            for arg in _nodes(node))]
    if not death_events:
        raise ValueError("ET_UNIT_DIE / KILLED_UNIT reference changed")

    mover_sample = _read_json(map_path / "ability/134251360.json")
    movers = _actions(mover_sample, "CREATE_STRAIGHT_MOVER")
    if len(movers) != 1 or movers[0]["args_list"][0].get("sub_type") != "ABILITY_OWNER":
        raise ValueError("collision-mover reference 134251360 changed")
    collision = movers[0]["args_list"][9]
    damage = _actions(collision, "APPLY_DAMAGE")
    if len(damage) != 1 or damage[0]["args_list"][2].get("sub_type") != "MOVER_COLLIDE_UNIT":
        raise ValueError("collision-mover reference lost its hit callback")

    cast_sample = _read_json(map_path / "modifier/134242511.json")
    cast_triggers = [
        trigger for trigger in _events(cast_sample, "SPECIAL_UNIT_EVENT")
        if _unit_event(trigger, "ET_UNIT_RELEASE_ABILITY")
    ]
    if len(cast_triggers) != 1:
        raise ValueError("release-ability reference 134242511 changed")

    return [
        Blocker(
            "SUNCE_PATH_STRIKE",
            "ability/134251360 proves unit-mover collision damage and "
            "ability/134275990 proves target-point direction, but a modifier-owned "
            "path strike with unique hits and a three-enemy cap is not established",
            "a modifier-compatible mover callback with explicit hit-set and cap, "
            "or approval to defer the entire strike until editor testing",
        ),
        Blocker(
            "MENGHUO_RAGE_AND_SWEEP",
            "the current fixed 134270627 刀兵 death can be scoped by 所属英雄, "
            "but the 6-second rage modifier, +20% attack speed, 70% secondary "
            "sweep, two-target cap, and self-trigger guard remain unbuilt",
            "a complete same-map rage/sweep ECA composition before binding the Buff",
        ),
        Blocker(
            "FUTURE_ACTIVE_EVENTS",
            "modifier/134242511 and global 其他事件01 use ET_UNIT_RELEASE_ABILITY "
            "for releases, but neither hero has active IDs to allowlist; "
            "Sun Ce's multi-target hit lacks per-cast deduplication",
            "future active ability IDs (or approval to count every non-basic "
            "release), plus a proven per-cast hit identity for Sun Ce",
        ),
    ]


def stage(map_path: Path, out_path: Path) -> dict[str, Any]:
    """Stage only proven, unbound fragments and their explicit status."""
    map_path = Path(map_path).resolve()
    out_path = Path(out_path).resolve()
    if out_path == map_path or map_path in out_path.parents:
        raise ValueError("out_path must not be inside the live map")
    blockers = audit(map_path)
    fragments = {
        Path("partial/modifier/134283906.json"): _death_fragment(map_path),
        Path("partial/modifier/134283915.json"): _rage_speed_fragment(map_path),
    }
    manifest = {
        "status": "partial_unbound_do_not_import_as_complete_loop",
        "fragments": [str(path).replace("\\", "/") for path in fragments],
        "proven_behavior": [
            "ET_UNIT_DIE supplies KILLED_UNIT",
            "KILLED_UNIT.所属英雄 equals MODIFIER_OWNER",
            "KILLED_UNIT unit type is the current fixed 刀兵 134270627",
            "internal modifier stack increments by 1 only while below 4",
            "rage modifier adds 20% all-ratio attack speed and clears it on loss",
        ],
        "not_implemented": [item.code for item in blockers],
        "shared_tables_written": False,
        "live_map_written": False,
    }
    for relative, fragment in fragments.items():
        _write_new_json(out_path / relative, fragment)
    _write_new_json(out_path / "partial/manifest.json", manifest)
    return manifest


def _self_check(map_path: Path) -> None:
    blockers = audit(map_path)
    assert {blocker.code for blocker in blockers} == {
        "SUNCE_PATH_STRIKE", "MENGHUO_RAGE_AND_SWEEP", "FUTURE_ACTIVE_EVENTS"
    }
    assert all(blocker.evidence and blocker.requirement for blocker in blockers)
    assert len(_death_fragment(Path(map_path))["trigger_dict"]) == 3
    assert len(_rage_speed_fragment(Path(map_path))["trigger_dict"]) == 2
    print(f"Static preflight OK; two fragments validated, {len(blockers)} blockers remain.")
    for blocker in blockers:
        print(f"{blocker.code}: {blocker.evidence}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("map_path", type=Path)
    parser.add_argument("out_path", type=Path, nargs="?")
    args = parser.parse_args()
    if args.out_path is None:
        _self_check(args.map_path)
    else:
        print(json.dumps(stage(args.map_path, args.out_path), ensure_ascii=False, indent=2))

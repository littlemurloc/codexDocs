"""Read-only map3 ECA preflight for Zhang He and Zhu Rong.

No modifier candidate is emitted until both complete loops have verified ECA
semantics. ``verified_fragments`` exposes actual map nodes for future editor
work, but fragments must not be presented as working hero modifiers.
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
    134249677: ("张郃", 134283909, 134283910),
    134255270: ("祝融", 134283911, 134283912),
}
SEED_BUFF = 134283917


@dataclass(frozen=True)
class Blocker:
    code: str
    evidence: str
    required_proof: str


class EcaSemanticBlocker(RuntimeError):
    """Exact hero behavior cannot be established from the inspected ECA."""

    def __init__(self, blockers: list[Blocker]):
        self.blockers = blockers
        super().__init__("\n".join(
            f"{b.code}: {b.evidence}; need {b.required_proof}"
            for b in blockers
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


def _actions(value: Any, kind: str) -> list[dict[str, Any]]:
    return [node for node in _nodes(value) if node.get("action_type") == kind]


def _unit_event(trigger: dict[str, Any], name: str) -> bool:
    return any(name in node.get("args_list", [])
               for node in _nodes(trigger.get("event", [])))


def _expect(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _check_ids_and_slots(map_path: Path) -> None:
    rows = _read_json(map_path / "tables/单位技能配置表.json")["table_data"]["data"]
    for unit_id, (name, ability_id, buff_id) in HEROES.items():
        matching = [row for row in rows if len(row) >= 10 and row[1] == unit_id]
        _expect(len(matching) == 1 and matching[0][0] == name,
                f"unit {unit_id}: expected one {name} skill row")
        _expect(matching[0][2:10] == [EMPTY_ABILITY] * 8,
                f"unit {unit_id}: skill slots changed")
        for object_id in (ability_id, buff_id):
            for folder in ("ability", "modifier", "editor_table/abilityall",
                           "editor_table/modifierall"):
                path = map_path / folder / f"{object_id}.json"
                _expect(not path.exists(), f"reserved ID occupied: {path}")
    for folder in ("modifier", "editor_table/modifierall"):
        path = map_path / folder / f"{SEED_BUFF}.json"
        _expect(not path.exists(), f"seed Buff ID occupied: {path}")


def verified_fragments(map_path: Path) -> dict[str, dict[str, Any]]:
    """Return evidenced ECA nodes only; none forms a complete candidate."""
    map_path = Path(map_path)
    _check_ids_and_slots(map_path)

    normal = _read_json(map_path / "modifier/134248740.json")
    hit = normal["trigger_dict"]["1878966277"]
    obtain = normal["trigger_dict"]["1485688834"]
    _expect(hit["event"][0]["event_type"] == "SPECIAL_UNIT_EVENT"
            and _unit_event(hit, "ET_UNIT_HURT_OTHER")
            and any(node.get("condition_type") == "GET_IS_NORMAL_HIT_FROM_EVENT"
                    for node in _nodes(hit["condition"]))
            and hit["trigger_id"] in obtain["action"],
            "normal-hit template 134248740 is no longer registered on obtain")

    command_eca = _read_json(map_path / "modifier/134247354.json")
    cycle = command_eca["trigger_dict"]["1937633284"]
    commands = _actions(cycle["action"], "UNIT_RELEASE_COMMAND")
    _expect(cycle["event"][0]["event_type"] == "MODIFIER_CYCLE_TRIGGER"
            and len(commands) == 1
            and commands[0]["args_list"][0]["sub_type"] == "MODIFIER_OWNER"
            and commands[0]["args_list"][1]["sub_type"] == "UNIT_COMMAND_ATTACK_TARGET",
            "attack-target command template 134247354 changed")

    death_eca = _read_json(map_path / "modifier/134263847.json")
    death = death_eca["trigger_dict"]["1823006723"]
    death_obtain = death_eca["trigger_dict"]["1625518081"]
    _expect(death["event"][0]["event_type"] == "SPECIAL_UNIT_EVENT"
            and _unit_event(death, "ET_BEFORE_UNIT_DIE")
            and death["trigger_id"] in death_obtain["action"]
            and len(_actions(death["action"], "PICK_UNIT_DO_ACTION")) == 1
            and len(_actions(death["action"], "APPLY_DAMAGE")) == 1,
            "registered host-death explosion template 134263847 changed")

    loss_eca = _read_json(map_path / "modifier/134239943.json")
    loss = loss_eca["trigger_dict"]["1233457155"]
    _expect(loss["event"][0]["event_type"] == "LOSS_MODIFIER"
            and len(_actions(loss["action"], "APPLY_DAMAGE")) == 1
            and loss["valid"] is False,
            "unqualified loss-damage example 134239943 changed")

    return {
        "normal_hit": {"source": "modifier/134248740.json",
                       "event": copy.deepcopy(hit["event"]),
                       "condition": copy.deepcopy(hit["condition"])},
        "attack_command": {"source": "modifier/134247354.json",
                           "action": copy.deepcopy(commands[0])},
        "host_death_damage": {"source": "modifier/134263847.json",
                              "event": copy.deepcopy(death["event"]),
                              "action": copy.deepcopy(death["action"])},
        "unqualified_loss_damage": {"source": "modifier/134239943.json",
                                    "event": copy.deepcopy(loss["event"]),
                                    "valid": loss["valid"]},
    }


def audit(map_path: Path) -> list[Blocker]:
    """Validate local evidence and list the still-unproven exact semantics."""
    verified_fragments(map_path)
    return [
        Blocker(
            "ZHANGHE_FRONT_BACK_TARGET",
            "134247354 can command an attack against a supplied unit, but does "
            "not select the front/rear legal enemy in the current target's lane "
            "or prove command timing before the real basic attack",
            "a map3 ECA selection/ordering and attack-timing pattern that changes "
            "the actual basic-attack target, including empty and single-enemy lanes",
        ),
        Blocker(
            "ZHURONG_SEED_LIFECYCLE",
            "134263847 has a registered host-before-death area hit; 134239943 "
            "damages on every LOSS_MODIFIER reason and its trigger is invalid. "
            "Neither proves one explosion only at 5 seconds or host death",
            "a reason-qualified expiration or timer path plus host-death path "
            "with an exactly-once guard and surviving-enemy cap of three",
        ),
        Blocker(
            "ZHURONG_IGNITION_AND_WAVE",
            "the inspected fragments do not jointly establish priority for an "
            "in-range unseeded basic-attack target, one seed per enemy, "
            "explosion-to-Zhu-Rong fire resource, targetless full-stack hold, "
            "or a four-enemy 130% physical same-lane wave without re-ignition",
            "map3 ECA proofs for target selection, seed uniqueness, credited "
            "explosion, pending-full retry, capped lane damage, and recursion guard",
        ),
    ]


def stage(map_path: Path, out_path: Path) -> None:
    """Refuse partial modifier files until both exact loops can be generated."""
    map_path = Path(map_path).resolve()
    out_path = Path(out_path).resolve()
    if out_path == map_path or map_path in out_path.parents:
        raise ValueError("out_path must not be inside the read-only live map")
    blockers = audit(map_path)
    if blockers:
        raise EcaSemanticBlocker(blockers)
    raise AssertionError("stage needs a verified full generator before publishing")


def _self_check(map_path: Path) -> None:
    fragments = verified_fragments(map_path)
    _expect(set(fragments) == {"normal_hit", "attack_command",
                               "host_death_damage", "unqualified_loss_damage"},
            "fragment inventory changed")
    blockers = audit(map_path)
    _expect({b.code for b in blockers} == {
        "ZHANGHE_FRONT_BACK_TARGET", "ZHURONG_SEED_LIFECYCLE",
        "ZHURONG_IGNITION_AND_WAVE"}, "blocker inventory changed")
    _expect(all(b.evidence and b.required_proof for b in blockers),
            "incomplete blocker explanation")
    print(f"Static preflight OK: {len(fragments)} verified fragments; "
          f"{len(blockers)} semantic blockers. No candidate files written.")
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
        stage(args.map_path, args.out_path)

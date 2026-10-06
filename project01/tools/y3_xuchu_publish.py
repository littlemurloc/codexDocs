"""Guarded backup and publish for Xu Chu's remaining five skills in map3."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from y3_xuchu_six import descend, validate_stage


EXISTING = {
    "tables/单位技能配置表.json",
    "tables/技能特有循环机制表.json",
    "tables/技能作用描述表.json",
    "zhlanguage.json",
    "editor/folderinfo/folderinfo_ability_all.json",
    "editor/folderinfo/folderinfo_modifier_all.json",
    "modifier/134283902.json",
}
NEW = {
    *(f"editor_table/abilityall/{number}.json" for number in range(134283918, 134283923)),
    *(f"ability/{number}.json" for number in (134283918, 134283919, 134283920, 134283921)),
    "editor_table/modifierall/134283923.json",
    "modifier/134283923.json",
}
REPAIR = {"ability/134283919.json", "ability/134283920.json",
          "modifier/134283923.json"}


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def preflight(map_path: Path, candidate: Path, backup: Path, mode: str):
    map_path = map_path.resolve()
    candidate = candidate.resolve()
    if map_path.name != "map3" or map_path.parent.parent.name != "ProjectMonster02":
        raise ValueError(f"unexpected map path: {map_path}")
    if candidate == map_path or map_path in candidate.parents:
        raise ValueError("candidate must be outside the live map")
    if not candidate.is_dir():
        raise ValueError(f"candidate missing: {candidate}")
    staged = {path.relative_to(candidate).as_posix(): path
              for path in candidate.rglob("*.json") if path.is_file()}
    if set(staged) != EXISTING | NEW:
        raise ValueError(f"candidate file set mismatch: missing={(EXISTING | NEW) - set(staged)}, extra={set(staged) - (EXISTING | NEW)}")
    for relative, path in staged.items():
        json.loads(path.read_text(encoding="utf-8"))
        target = (map_path / relative).resolve()
        if map_path not in target.parents:
            raise ValueError(f"candidate path escapes map: {relative}")
        if relative in EXISTING and not target.is_file():
            raise ValueError(f"existing map file missing: {relative}")
        if relative in NEW and target.exists():
            raise ValueError(f"new object ID occupied: {relative}")
    validate_stage(map_path, candidate)
    if mode == "backup":
        if backup.exists():
            raise ValueError(f"backup already exists: {backup}")
    else:
        if not backup.is_file():
            raise ValueError(f"backup missing: {backup}")
        with ZipFile(backup) as archive:
            if set(archive.namelist()) != EXISTING:
                raise ValueError("backup file set mismatch")
            for relative in EXISTING:
                if digest(archive.read(relative)) != digest((map_path / relative).read_bytes()):
                    raise ValueError(f"live map drifted after backup: {relative}")
    print(json.dumps({"mode": mode, "existing": sorted(EXISTING),
                      "new": sorted(NEW)}, ensure_ascii=False, indent=2))
    return map_path, staged


def main(map_path: Path, candidate: Path, backup: Path, mode: str):
    if mode.startswith("repair-"):
        repair(map_path, candidate, backup, mode)
        return
    map_path, staged = preflight(map_path, candidate, backup, mode)
    if mode == "backup":
        backup.parent.mkdir(parents=True, exist_ok=True)
        with ZipFile(backup, "x", ZIP_DEFLATED) as archive:
            for relative in sorted(EXISTING):
                archive.write(map_path / relative, relative)
        return
    if mode == "preflight":
        return
    for relative, path in sorted(staged.items()):
        target = map_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = target.with_name(target.name + ".codex-pending")
        if temporary.exists():
            raise ValueError(f"pending file already exists: {temporary}")
        payload = path.read_bytes()
        try:
            temporary.write_bytes(payload)
            os.replace(temporary, target)
        finally:
            if temporary.exists():
                temporary.unlink()
        if digest(target.read_bytes()) != digest(payload):
            raise IOError(f"post-write mismatch: {relative}")


def repair(map_path: Path, candidate: Path, backup: Path, mode: str):
    map_path = map_path.resolve()
    candidate = candidate.resolve()
    if map_path.name != "map3" or map_path.parent.parent.name != "ProjectMonster02":
        raise ValueError(f"unexpected map path: {map_path}")
    if candidate == map_path or map_path in candidate.parents:
        raise ValueError("candidate must be outside live map")
    old = {relative: json.loads((map_path / relative).read_text(encoding="utf-8"))
           for relative in REPAIR}
    new = {relative: json.loads((candidate / relative).read_text(encoding="utf-8"))
           for relative in REPAIR}
    expected = copy.deepcopy(old)
    roar_old = expected["ability/134283919.json"]
    roar_new = new["ability/134283919.json"]
    replacements = {node["element_id"]: node for node in descend(roar_new)
                    if node.get("condition_type") == "UNIT_COMPARE"
                    and node.get("element_id") in (893440004978621, 893440004978622)}
    count = 0
    for node in descend(roar_old):
        if (node.get("condition_type") == "UNIT_HAS_TAG"
                and node.get("element_id") in replacements):
            element_id = node["element_id"]
            node.clear()
            node.update(copy.deepcopy(replacements[element_id]))
            count += 1
    if count != 2 or roar_old != roar_new:
        raise ValueError("roar repair changes more than two minion conditions")
    guard_old = expected["ability/134283920.json"]
    guard_new = new["ability/134283920.json"]
    guard_old["trigger_dict"]["58232837"]["condition"].pop()
    if guard_old != guard_new:
        raise ValueError("guard repair changes more than minion condition")
    speed_old = expected["modifier/134283923.json"]
    speed_new = new["modifier/134283923.json"]
    speed_old["trigger_dict"]["1418035204"]["valid"] = True
    speed_old["trigger_dict"]["1625518081"]["valid"] = True
    speed_old["trigger_group_info"].append(
        {"__tuple__": True, "items": [1418035204, "子触发器"]})
    if speed_old != speed_new:
        raise ValueError("speed Buff repair changes more than subtrigger registration")
    if mode == "repair-backup":
        if backup.exists():
            raise ValueError(f"repair backup already exists: {backup}")
        backup.parent.mkdir(parents=True, exist_ok=True)
        with ZipFile(backup, "x", ZIP_DEFLATED) as archive:
            for relative in sorted(REPAIR):
                archive.write(map_path / relative, relative)
    else:
        if not backup.is_file():
            raise ValueError(f"repair backup missing: {backup}")
        with ZipFile(backup) as archive:
            if set(archive.namelist()) != REPAIR:
                raise ValueError("repair backup file set mismatch")
            for relative in REPAIR:
                if digest(archive.read(relative)) != digest((map_path / relative).read_bytes()):
                    raise ValueError(f"live map drifted after repair backup: {relative}")
    if mode == "repair-apply":
        for relative in sorted(REPAIR):
            target = map_path / relative
            temporary = target.with_name(target.name + ".codex-pending")
            if temporary.exists():
                raise ValueError(f"pending file already exists: {temporary}")
            payload = (candidate / relative).read_bytes()
            try:
                temporary.write_bytes(payload)
                os.replace(temporary, target)
            finally:
                if temporary.exists():
                    temporary.unlink()
            if digest(target.read_bytes()) != digest(payload):
                raise IOError(f"repair post-write mismatch: {relative}")
    print(json.dumps({"mode": mode, "files": sorted(REPAIR)}, ensure_ascii=False))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("map", type=Path)
    parser.add_argument("candidate", type=Path)
    parser.add_argument("backup", type=Path)
    parser.add_argument("mode", choices=("backup", "preflight", "apply",
                                         "repair-backup", "repair-preflight", "repair-apply"))
    options = parser.parse_args()
    main(options.map, options.candidate, options.backup, options.mode)

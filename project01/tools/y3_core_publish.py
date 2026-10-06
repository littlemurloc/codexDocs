"""Publish a reviewed core-loop candidate only if the live map has not drifted.

Run without --apply for a read-only preflight. The backup ZIP must contain the
six shared files from immediately before this batch; newly allocated object IDs
must not exist in the live map.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
from zipfile import ZipFile


SHARED = {
    "tables/单位技能配置表.json",
    "tables/技能特有循环机制表.json",
    "tables/技能作用描述表.json",
    "zhlanguage.json",
    "editor/folderinfo/folderinfo_ability_all.json",
    "editor/folderinfo/folderinfo_modifier_all.json",
}
NEW_PREFIXES = (
    "editor_table/abilityall/",
    "editor_table/modifierall/",
    "modifier/",
    "ability/",
)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def publish(map_path: Path, candidate: Path, backup_zip: Path, apply: bool):
    map_path = map_path.resolve()
    candidate = candidate.resolve()
    if map_path.name != "map3" or not map_path.is_dir():
        raise ValueError(f"not the expected map3 directory: {map_path}")
    if candidate == map_path or map_path in candidate.parents:
        raise ValueError("candidate must be outside the live map")

    staged = sorted(path for path in candidate.rglob("*.json") if path.is_file())
    if not staged:
        raise ValueError("empty candidate")
    relatives = [path.relative_to(candidate).as_posix() for path in staged]
    if not SHARED <= set(relatives):
        raise ValueError("candidate is missing a shared file")
    if any(relative not in SHARED and not relative.startswith(NEW_PREFIXES)
           for relative in relatives):
        raise ValueError("candidate includes an unexpected file")

    with ZipFile(backup_zip) as backup:
        original = {name: backup.read(Path(name).name) for name in SHARED}
    for path, relative in zip(staged, relatives):
        target = (map_path / relative).resolve()
        if map_path not in target.parents:
            raise ValueError(f"path escapes map: {relative}")
        json.loads(path.read_text(encoding="utf-8"))
        if relative in SHARED:
            if not target.is_file() or target.read_bytes() != original[relative]:
                raise ValueError(f"live shared file changed after backup: {relative}")
        elif target.exists():
            raise ValueError(f"new object ID is already occupied: {relative}")

    print(json.dumps({"mode": "apply" if apply else "preflight",
                      "files": relatives}, ensure_ascii=False, indent=2))
    if not apply:
        return

    for path, relative in zip(staged, relatives):
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
        if sha256(target.read_bytes()) != sha256(payload):
            raise IOError(f"post-write mismatch: {relative}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("map", type=Path)
    parser.add_argument("candidate", type=Path)
    parser.add_argument("backup_zip", type=Path)
    parser.add_argument("--apply", action="store_true")
    options = parser.parse_args()
    publish(options.map, options.candidate, options.backup_zip, options.apply)

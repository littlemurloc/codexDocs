"""Move the new Xu Chu ability after existing hero folders, without touching them."""

from __future__ import annotations

import argparse
import copy
import json
import os
from pathlib import Path
from zipfile import ZipFile


def fix(map_path: Path, backup_zip: Path, apply: bool):
    live_path = map_path / "editor/folderinfo/folderinfo_ability_all.json"
    live = json.loads(live_path.read_text(encoding="utf-8"))
    with ZipFile(backup_zip) as backup:
        before = json.loads(backup.read("folderinfo_ability_all.json"))
    new_id = "134283901"
    if new_id in before["d"] or new_id not in live["d"]:
        raise ValueError("unexpected Xu Chu ability folder state")
    new_entry = live["d"][new_id]
    parent_uid = new_entry["items"][0]
    children = [folder for folder in before["f"]
                if folder["items"][0].split("/")[-1] == parent_uid]
    expected = copy.deepcopy(before)
    expected["d"][new_id] = copy.deepcopy(new_entry)
    for folder in expected["f"]:
        if (folder["items"][0].split("/")[-1] == parent_uid
                and folder["items"][1] > 0):
            folder["items"][1] += 1
    if live != expected or new_entry["items"][1] != 1:
        raise ValueError("live folder state has changes beyond editor reordering")
    repaired = copy.deepcopy(before)
    repaired["d"][new_id] = copy.deepcopy(new_entry)
    repaired["d"][new_id]["items"][1] = max(
        folder["items"][1] for folder in children
    ) + 1
    print(f"Xu Chu folder index: 1 -> {repaired['d'][new_id]['items'][1]}")
    if not apply:
        return
    temporary = live_path.with_name(live_path.name + ".codex-pending")
    if temporary.exists():
        raise ValueError(f"pending file already exists: {temporary}")
    try:
        temporary.write_text(json.dumps(repaired, ensure_ascii=True, indent=1) + "\n",
                             encoding="utf-8", newline="\n")
        os.replace(temporary, live_path)
    finally:
        if temporary.exists():
            temporary.unlink()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("map", type=Path)
    parser.add_argument("backup_zip", type=Path)
    parser.add_argument("--apply", action="store_true")
    options = parser.parse_args()
    fix(options.map, options.backup_zip, options.apply)

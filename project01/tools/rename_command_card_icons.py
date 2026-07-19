from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(r"D:\codex\project01\assets\ui\command-cards\v01")

NAMES = {
    "cmd_break_execute": "\u65a9\u5c06\u4ee4",
    "cmd_break_formation": "\u7834\u9635\u4ee4",
    "cmd_flying_raid": "\u5947\u88ad\u4ee4",
    "cmd_flying_charge": "\u5954\u88ad\u4ee4",
    "cmd_fire_burn_camp": "\u711a\u8425\u4ee4",
    "cmd_fire_attack": "\u706b\u653b\u4ee4",
    "cmd_chain_link_order": "\u8fde\u73af\u4ee4",
    "cmd_chain_burn_boats": "\u711a\u821f\u4ee4",
    "cmd_ambush_order": "\u4f0f\u5175\u4ee4",
    "cmd_ambush_ten_sides": "\u5341\u9762\u57cb\u4f0f\u4ee4",
    "cmd_independent_inspire": "\u9f13\u821e\u4ee4",
    "cmd_independent_hold": "\u56fa\u5b88\u4ee4",
    "cmd_break_spearhead": "\u950b\u77e2\u519b\u7565",
    "cmd_break_war_drum": "\u6218\u9f13\u519b\u7565",
    "cmd_tiger_iron_armor": "\u94c1\u7532\u519b\u7565",
    "cmd_tiger_shield_line": "\u76fe\u5217\u519b\u7565",
    "cmd_tiger_hold_fast": "\u6b7b\u5b88\u519b\u7565",
    "cmd_tiger_hold_formation": "\u56fa\u9635\u519b\u7565",
    "cmd_flying_good_mount": "\u826f\u9a6c\u519b\u7565",
    "cmd_flying_flank_assault": "\u4fa7\u51fb\u519b\u7565",
    "cmd_fire_oil": "\u706b\u6cb9\u519b\u7565",
    "cmd_fire_wind": "\u98ce\u52a9\u519b\u7565",
    "cmd_chain_bind_boats": "\u7f1a\u821f\u519b\u7565",
    "cmd_chain_cut_rope": "\u65ad\u7d22\u519b\u7565",
    "cmd_ambush_scout": "\u8033\u76ee\u519b\u7565",
    "cmd_ambush_cut_supply": "\u65ad\u7cae\u519b\u7565",
    "cmd_farm_reclaim": "\u5c6f\u57a6\u519b\u7565",
    "cmd_farm_thrift": "\u8282\u7528\u519b\u7565",
    "cmd_farm_spoils": "\u7f34\u83b7\u519b\u7565",
    "cmd_farm_prosperity": "\u5bcc\u56fd\u519b\u7565",
    "cmd_recruit_enlist": "\u52df\u5352\u519b\u7565",
    "cmd_recruit_train": "\u7ec3\u5352\u519b\u7565",
    "cmd_recruit_formation": "\u6210\u9635\u519b\u7565",
    "cmd_recruit_elite_force": "\u7cbe\u5175\u5f3a\u519b",
    "cmd_armory_forging": "\u7cbe\u953b\u519b\u7565",
    "cmd_armory_armor": "\u7532\u80c4\u519b\u7565",
    "cmd_armory_calibration": "\u6821\u51c6\u519b\u7565",
    "cmd_armory_masterwork": "\u767e\u5de5\u519b\u7565",
    "cmd_independent_vitality": "\u4f53\u9b44\u519b\u7565",
    "cmd_independent_vigor": "\u9510\u6c14\u519b\u7565",
    "cmd_independent_march": "\u884c\u519b\u519b\u7565",
    "cmd_independent_preserve": "\u4fdd\u5168\u519b\u7565",
}


def move_if_present(directory: Path, old_stem: str, new_stem: str) -> None:
    old_path = directory / f"{old_stem}.png"
    new_path = directory / f"{new_stem}.png"
    if old_path.exists():
        if new_path.exists():
            raise FileExistsError(f"Refusing to overwrite {new_path}")
        old_path.rename(new_path)


def main() -> None:
    manifest_path = ROOT / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    for command_id, display_name in NAMES.items():
        move_if_present(ROOT / "transparent", command_id, display_name)
        move_if_present(ROOT / "source", f"{command_id}_source", f"{display_name}_source")
        move_if_present(ROOT / "source", f"{command_id}_normalized", f"{display_name}_normalized")

    for asset in manifest["assets"]:
        command_id = asset["command_card_id"]
        if command_id not in NAMES:
            continue
        display_name = NAMES[command_id]
        asset["display_name"] = display_name
        asset["file"] = f"transparent/{display_name}.png"
        asset["source"] = f"source/{display_name}_source.png"

    for validation in manifest.get("validation", []):
        old_stem = Path(validation["file"]).stem
        if old_stem in NAMES:
            validation["file"] = f"{NAMES[old_stem]}.png"

    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()

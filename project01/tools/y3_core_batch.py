"""Stage the approved second-batch core-loop objects without editing the live map.

This file is intentionally a staging tool. It refuses to publish incomplete ECA.
"""

from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path


HEROES = (
    ("许褚", 134242131, 134283901, 134283902, "踏地生威", "虎势", 3,
     "普攻击中获得1点虎势，最多3点；满3点震地，对当前目标及附近最多3名敌人各造成90%攻击的物理伤害。"),
    ("孙策", 134260498, 134283903, 134283904, "江潮战意", "潮势", 2,
     "接敌或主动命中获得潮势，最多2点；满2点冲斩当前目标及路径上最多3名敌人，各造成110%攻击的物理伤害。"),
    ("孟获", 134255426, 134283905, 134283906, "蛮勇不屈", "蛮勇", 3,
     "本队近战小兵阵亡或成功施放主动时获得蛮勇；满3点狂化6秒，期间攻速提高20%，普攻横扫附近最多2名敌人，造成70%攻击的物理伤害。"),
    ("大乔", 134230459, 134283907, 134283908, "伞上凝露", "凝露", 1,
     "我方队长施放主动后获得1滴凝露；下次普攻击中时若有受伤友方队长，消耗凝露并治疗生命比例最低者5%最大生命。"),
    ("张郃", 134249677, 134283909, 134283910, "兵无常势", "变势", 1,
     "普攻交替射击当前一路最前方与最后方的合法敌人；前阵命中获得1点变势，后阵出手消耗。"),
    ("祝融", 134255270, 134283911, 134283912, "焰起成势", "火势", 3,
     "普攻优先为未带炎种的敌人点火；炎种爆炸获得1点火势，满3点向当前一路最多4名敌人释放130%攻击的物理火浪。"),
    ("韩当", 134256942, 134283913, 134283914, "箭囊备守", "备矢", 2,
     "友方队长受到直接伤害时备箭，最多2枚；满额后援射伤害来源，造成120%攻击的物理伤害，并为受击队长提供8%最大生命的护盾4秒。"),
)


def read_json(path: Path):
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def write_json(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as file:
        json.dump(data, file, ensure_ascii=True, indent=4)
        file.write("\n")


def new_language_key(language: dict, start: int) -> int:
    key = start
    while str(key) in language:
        key += 1
    return key


def patch_unit_skills(table: dict, heroes):
    data = table["table_data"]["data"]
    for name, unit_id, ability_id, *_ in heroes:
        matching = [i for i, row in enumerate(data) if row[:2] == [name, unit_id]]
        if len(matching) != 1:
            raise ValueError(f"unit skill row not unique: {name} ({unit_id})")
        row = data[matching[0]]
        if row[6] != 134255698:
            raise ValueError(f"2-star slot is not empty: {name}: {row[6]}")
        row[6] = ability_id


def patch_cycle_table(table: dict, heroes):
    data = table["table_data"]["data"]
    empty = [i for i, row in enumerate(data) if i >= 2 and row[0] is None]
    if len(empty) < len(heroes):
        raise ValueError("not enough empty core-loop rows")
    for index, (_, _, ability_id, buff_id, *_) in zip(empty, heroes):
        data[index][:5] = [index - 1, buff_id, ability_id, 0, 0]


def patch_description_table(table: dict, heroes):
    data = table["table_data"]["data"]
    ids = {int(row[1]) for row in data[2:] if len(row) > 1 and isinstance(row[1], int)}
    number = max(int(row[0]) for row in data[2:] if row and str(row[0]).isdigit())
    width = len(data[0])
    for _, _, ability_id, _, _, _, _, description in heroes:
        if ability_id in ids:
            raise ValueError(f"description row exists: {ability_id}")
        number += 1
        data.append(([str(number), ability_id, "被动"] + [description] * 11 + [""] * width)[:width])


def arg(kind: int, subtype, *values):
    return {"arg_type": kind, "args_list": list(values), "sub_type": subtype}


def action(kind: str, element_id: int, *values):
    node = {"action_type": kind, "args_list": list(values), "bp": False,
            "element_id": element_id, "enable": True}
    if kind == "IF_THEN_ELSE":
        node["fake_op"] = [2]
    return node


def condition(kind: str, element_id: int, *values):
    return {"condition_type": kind, "args_list": list(values),
            "element_id": element_id, "enable": True}


def find_action(node, kind: str):
    if isinstance(node, dict):
        if node.get("action_type") == kind:
            return node
        for child in node.values():
            found = find_action(child, kind)
            if found is not None:
                return found
    elif isinstance(node, list):
        for child in node:
            found = find_action(child, kind)
            if found is not None:
                return found
    return None


def xuchu_eca(map_path: Path):
    buff_id = 134283902
    eca = read_json(map_path / "modifier/134242511.json")
    hit_id = "1418035204"
    eca["trigger_dict"].pop("2011996165")
    eca["local_variable"].pop("2011996165", None)
    eca["trigger_dict"]["1485688834"]["action"] = [int(hit_id)]
    loss = eca["trigger_dict"]["594665475"]["action"]
    loss[:] = [node for node in loss if node["action_type"] == "UNREG_TRIGGER"][:1]
    eca["trigger_group_info"][0]["key"] = buff_id
    eca["trigger_group_info"][0]["name"] = str(buff_id)
    eca["trigger_group_info"] = [
        group for group in eca["trigger_group_info"]
        if group.get("items", [None])[0] != 2011996165
    ]
    for trigger in eca["trigger_dict"].values():
        trigger["group_id"] = buff_id

    hit = eca["trigger_dict"][hit_id]
    hit["event"][0]["args_list"][1]["args_list"] = ["ET_UNIT_HURT_OTHER"]
    hit["condition"] = [
        condition("GET_IS_NORMAL_HIT_FROM_EVENT", 1418035204900001),
        condition("BOOL_COMPARE", 1418035204900015,
                  arg(100001, "GET_BOOLEAN_KV", arg(100076, "CUR_MODIFIER"),
                      arg(100003, 1, "xuchu_quaking")),
                  arg(100035, 1, "=="), arg(100001, 1, False)),
    ]
    owner = arg(100006, "MODIFIER_OWNER")
    current = arg(100076, "CUR_MODIFIER")
    target = arg(100006, "DAMAGE_TARGET_UNIT")
    stack = arg(100002, "GET_MOD_STACK", current)
    hit["action"] = [action("ADD_BUFF_STACK", 1418035204900002,
                            current, arg(100002, 1, 1))]

    damage_sample = read_json(map_path / "modifier/134225437.json")
    damage = copy.deepcopy(find_action(damage_sample, "APPLY_DAMAGE"))
    if damage is None:
        raise ValueError("damage action template missing")
    damage["args_list"][0] = owner
    damage["args_list"][1] = arg(100014, "RELATED_ABILITY", current)
    damage["args_list"][3] = arg(100064, 1, 0)
    damage["args_list"][4] = arg(100000, "ARITHMETIC_OPERATION",
                                  damage["args_list"][4], arg(100017, 1, "*"),
                                  arg(100000, 1, 0.9))
    damage["element_id"] = 1418035204900003
    primary = copy.deepcopy(damage)
    primary["args_list"][2] = target

    area_sample = read_json(map_path / "ability/134259316.json")
    picked = copy.deepcopy(find_action(area_sample, "PICK_UNIT_DO_ACTION"))
    if picked is None:
        raise ValueError("area action template missing")
    group = picked["args_list"][0]
    group["args_list"][0] = arg(100004, "UNIT_ENTITY_POINT", target)
    group["args_list"][1] = arg(100211, "CONST_CIRCULAR_SHAPE", arg(100000, 1, 260.0))
    group["op_arg"][0] = arg(100027, "PLAYER_ENEMY",
                              arg(100025, "OWNER_PLAYER", owner))
    extra = copy.deepcopy(damage)
    extra["args_list"][2] = arg(100006, "FOR_EACH_SELECTED_UNIT")
    extra["element_id"] = 1418035204900004
    key = arg(100003, 1, "xuchu_quake_count")
    count = arg(100000, "GET_FLOAT_KV", current, key)
    bump = action("SET_ENTITY_KV", 1418035204900005, current, key,
                  arg(100000, "ARITHMETIC_OPERATION", count,
                      arg(100017, 1, "+"), arg(100000, 1, 1.0)))
    count_check = condition("FLOAT_COMPARE", 1418035204900006,
                            count, arg(100015, 1, "<"), arg(100000, 1, 2.0))
    not_primary = condition("UNIT_COMPARE", 1418035204900007,
                            arg(100006, "FOR_EACH_SELECTED_UNIT"),
                            arg(100035, 1, "!="), target)
    add_extra = action("IF_THEN_ELSE", 1418035204900008,
                       arg(100021, 1, count_check), arg(100022, 1, extra, bump),
                       arg(100022, 1))
    pick_other = action("IF_THEN_ELSE", 1418035204900009,
                        arg(100021, 1, not_primary), arg(100022, 1, add_extra),
                        arg(100022, 1))
    picked["args_list"][1] = arg(100022, 1, pick_other)
    picked["element_id"] = 1418035204900010
    reset = action("SET_BUFF_STACK", 1418035204900011,
                   current, arg(100002, 1, 1))
    count_reset = action("SET_ENTITY_KV", 1418035204900012,
                         current, key, arg(100000, 1, 0.0))
    busy_key = arg(100003, 1, "xuchu_quaking")
    busy_on = action("SET_ENTITY_KV", 1418035204900016,
                     current, busy_key, arg(100001, 1, True))
    busy_off = action("SET_ENTITY_KV", 1418035204900017,
                      current, busy_key, arg(100001, 1, False))
    full = condition("FLOAT_COMPARE", 1418035204900013,
                     stack, arg(100015, 1, ">="), arg(100002, 1, 4))
    stomp_ability = read_json(map_path / "ability/134260949.json")
    stomp_fx = copy.deepcopy(find_action(stomp_ability, "CREATE_SFX_ON_POINT_NEW"))
    if stomp_fx is None:
        raise ValueError("stomp effect action template missing")
    stomp_fx["args_list"][0] = arg(100066, 1, 101118)
    stomp_fx["args_list"][1] = arg(100004, "UNIT_ENTITY_POINT", target)
    stomp_fx["element_id"] = 1418035204900018
    quake = action("IF_THEN_ELSE", 1418035204900014,
                   arg(100021, 1, full),
                   arg(100022, 1, busy_on, reset, count_reset, stomp_fx,
                       primary, picked, busy_off),
                   arg(100022, 1))
    hit["action"].append(quake)
    return eca


def patch_folder(map_path: Path, out_path: Path, kind: str, ids: list[int], folder_name: str):
    path = map_path / "editor/folderinfo" / f"folderinfo_{kind}.json"
    data = read_json(path)
    matching = [folder["items"][2] for folder in data["f"]
                if folder["items"][-1] == folder_name]
    if len(matching) != 1:
        raise ValueError(f"folder not unique: {kind}/{folder_name}")
    folder_uid = matching[0]
    used = [entry["items"][1] for entry in data["d"].values()
            if entry["items"][0] == folder_uid]
    used.extend(folder["items"][1] for folder in data["f"]
                if folder["items"][0].split("/")[-1] == folder_uid)
    next_index = max(used, default=0) + 1
    for object_id in ids:
        if str(object_id) in data["d"]:
            raise ValueError(f"folder entry already exists: {object_id}")
        data["d"][str(object_id)] = {"__tuple__": True,
                                      "items": [folder_uid, next_index]}
        next_index += 1
    write_json(out_path / "editor/folderinfo" / path.name, data)


def validate_candidate(out_path: Path, heroes):
    ability_ids = [hero[2] for hero in heroes]
    buff_ids = [hero[3] for hero in heroes]
    if len(set(ability_ids + buff_ids)) != 2 * len(heroes):
        raise ValueError("duplicate object ID")
    for name, unit_id, ability_id, buff_id, *_ in heroes:
        ability = read_json(out_path / "editor_table/abilityall" / f"{ability_id}.json")
        buff = read_json(out_path / "editor_table/modifierall" / f"{buff_id}.json")
        if (ability["key"], buff["key"]) != (ability_id, buff_id):
            raise ValueError(f"object key mismatch: {name}")
        unit = read_json(out_path / "tables/单位技能配置表.json")
        row = next(row for row in unit["table_data"]["data"] if row[:2] == [name, unit_id])
        if row[6] != ability_id:
            raise ValueError(f"2-star slot mismatch: {name}")
    cycle = read_json(out_path / "tables/技能特有循环机制表.json")
    for i, hero in enumerate(heroes, start=19):
        if cycle["table_data"]["data"][i + 1][:3] != [i, hero[3], hero[2]]:
            raise ValueError(f"core-loop table mismatch: {hero[0]}")
    descriptions = read_json(out_path / "tables/技能作用描述表.json")
    for ability_id in ability_ids:
        if sum(row[1] == ability_id for row in descriptions["table_data"]["data"][2:]) != 1:
            raise ValueError(f"description not unique: {ability_id}")
    language = read_json(out_path / "zhlanguage.json")
    for object_id in ability_ids + buff_ids:
        kind = "abilityall" if object_id in ability_ids else "modifierall"
        item = read_json(out_path / "editor_table" / kind / f"{object_id}.json")
        if str(item["name"]) not in language or str(item["description"]) not in language:
            raise ValueError(f"missing translated name/description: {object_id}")
    for kind, ids in (("ability_all", ability_ids), ("modifier_all", buff_ids)):
        folder = read_json(out_path / "editor/folderinfo" / f"folderinfo_{kind}.json")
        if any(str(object_id) not in folder["d"] for object_id in ids):
            raise ValueError(f"folder entry missing: {kind}")
    if any(hero[0] == "许褚" for hero in heroes):
        xuchu = read_json(out_path / "modifier/134283902.json")
        if "134242511" in json.dumps(xuchu, ensure_ascii=False):
            raise ValueError("Xu Chu ECA still references Huang Zhong Buff")
        hit = xuchu["trigger_dict"]["1418035204"]
        if hit["action"][0]["args_list"][1]["args_list"] != [1]:
            raise ValueError("Xu Chu stack increment is not +1")


def stage(map_path: Path, out_path: Path, heroes=HEROES):
    ability_template = read_json(map_path / "editor_table/abilityall/134259316.json")
    buff_template = read_json(map_path / "editor_table/modifierall/134242511.json")
    language = read_json(map_path / "zhlanguage.json")
    tables = {
        name: read_json(map_path / "tables" / f"{name}.json")
        for name in ("单位技能配置表", "技能特有循环机制表", "技能作用描述表")
    }
    patch_unit_skills(tables["单位技能配置表"], heroes)
    patch_cycle_table(tables["技能特有循环机制表"], heroes)
    patch_description_table(tables["技能作用描述表"], heroes)

    language_key = new_language_key(language, 2030000000)
    for name, unit_id, ability_id, buff_id, ability_name, buff_name, count, description in heroes:
        for kind, object_id, template, title, text in (
            ("abilityall", ability_id, ability_template, ability_name, description),
            ("modifierall", buff_id, buff_template, buff_name, f"{name}：{buff_name} 0–{count} 点"),
        ):
            target = map_path / "editor_table" / kind / f"{object_id}.json"
            if target.exists():
                raise ValueError(f"object ID already exists: {target}")
            item = copy.deepcopy(template)
            item["_ref_"] = object_id
            item["key"] = object_id
            item["uid"] = str(object_id)
            item["name"] = language_key
            language[str(language_key)] = title
            language_key += 1
            item["desc"] = language_key
            item["description"] = language_key
            language[str(language_key)] = text
            language_key += 1
            item["suffix"] = name if kind == "modifierall" else "被动"
            icon = read_json(map_path / "editor_table/editorunit" / f"{unit_id}.json")["icon"]
            item["modifier_icon" if kind == "modifierall" else "ability_icon"] = icon
            if kind == "modifierall":
                item["layer_max"] = count + 1
            else:
                item["kv"] = {}
            write_json(out_path / "editor_table" / kind / f"{object_id}.json", item)

    for name, table in tables.items():
        write_json(out_path / "tables" / f"{name}.json", table)
    write_json(out_path / "zhlanguage.json", language)
    patch_folder(map_path, out_path, "ability_all", [hero[2] for hero in heroes], "英雄")
    patch_folder(map_path, out_path, "modifier_all", [hero[3] for hero in heroes],
                 "能力循环机制buff")
    if any(hero[0] == "许褚" for hero in heroes):
        write_json(out_path / "modifier/134283902.json", xuchu_eca(map_path))
    validate_candidate(out_path, heroes)
    # The other six ECA files are deliberately absent; incomplete objects may not be published.


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("map", type=Path)
    parser.add_argument("out", type=Path)
    parser.add_argument("--heroes", default=",".join(hero[0] for hero in HEROES))
    args = parser.parse_args()
    selected_names = args.heroes.split(",")
    heroes = tuple(hero for hero in HEROES if hero[0] in selected_names)
    if len(heroes) != len(selected_names):
        parser.error("--heroes must be a comma-separated list of unique known hero names")
    stage(args.map, args.out, heroes)

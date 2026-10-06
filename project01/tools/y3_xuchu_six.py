"""Stage Xu Chu skills against the currently open map, without publishing them."""

from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path


UNIT_ID = 134242131
EMPTY_ID = 134255698
SKILL_ONE_ID = 134283918
SKILL_THREE_ID = 134283919
SKILL_FOUR_ID = 134283920
SKILL_FIVE_ID = 134283921
SKILL_SIX_ID = 134283922
SPEED_BUFF_ID = 134283923
SHARED = (
    "tables/单位技能配置表.json",
    "tables/技能特有循环机制表.json",
    "tables/技能作用描述表.json",
    "zhlanguage.json",
    "editor/folderinfo/folderinfo_ability_all.json",
    "editor/folderinfo/folderinfo_modifier_all.json",
)


def read(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=True, indent=4) + "\n", encoding="utf-8")


def descend(value):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from descend(child)
    elif isinstance(value, list):
        for child in value:
            yield from descend(child)


def new_language_key(language: dict, start=2030000004):
    while str(start) in language:
        start += 1
    return start


def add_description(table: dict, ability_id: int, tag: str, description: str):
    rows = table["table_data"]["data"]
    if any(len(row) > 1 and row[1] == ability_id for row in rows[2:]):
        raise ValueError(f"description already exists: {ability_id}")
    number = max(int(row[0]) for row in rows[2:] if row and str(row[0]).isdigit()) + 1
    width = len(rows[0])
    rows.append(([str(number), ability_id, tag] + [description] * 11 + [""] * width)[:width])


def add_folder(folder: dict, ability_id: int):
    items = folder["d"]
    if str(ability_id) in items:
        raise ValueError(f"folder ID already exists: {ability_id}")
    entries = [entry["items"] for entry in items.values() if entry.get("__tuple__")]
    parent = items[str(134283901)]["items"][0]
    index = max((index for uid, index in entries if uid == parent), default=0) + 1
    items[str(ability_id)] = {"__tuple__": True, "items": [parent, index]}


def add_buff_folder(folder: dict, buff_id: int):
    items = folder["d"]
    if str(buff_id) in items:
        raise ValueError(f"buff folder ID already exists: {buff_id}")
    parent = items[str(134283902)]["items"][0]
    entries = [entry["items"] for entry in items.values() if entry.get("__tuple__")]
    index = max((index for uid, index in entries if uid == parent), default=0) + 1
    items[str(buff_id)] = {"__tuple__": True, "items": [parent, index]}


def literal(kind: int, value):
    return {"arg_type": kind, "args_list": [value], "sub_type": 1}


def arg(kind: int, subtype, *values):
    return {"arg_type": kind, "args_list": list(values), "sub_type": subtype}


def action(kind: str, element_id: int, *values):
    result = {"action_type": kind, "args_list": list(values), "bp": False,
              "element_id": element_id, "enable": True}
    if kind == "IF_THEN_ELSE":
        result["fake_op"] = [2]
    return result


def condition(kind: str, element_id: int, *values):
    return {"args_list": list(values), "condition_type": kind,
            "element_id": element_id, "enable": True}


def modifier_name_keys(shared: dict, name: str, description: str):
    language = shared["zhlanguage.json"]
    name_key = new_language_key(language)
    description_key = new_language_key(language, name_key + 1)
    language[str(name_key)] = name
    language[str(description_key)] = description
    return name_key, description_key


def bind_skill(shared: dict, ability_id: int, slot: int, tag: str, description: str):
    rows = shared["tables/单位技能配置表.json"]["table_data"]["data"]
    matching = [row for row in rows if row[:2] == ["许褚", UNIT_ID]]
    if len(matching) != 1 or matching[0][slot] != EMPTY_ID:
        raise ValueError(f"Xu Chu slot {slot} is not uniquely empty")
    matching[0][slot] = ability_id
    add_description(shared["tables/技能作用描述表.json"], ability_id, tag, description)
    add_folder(shared["editor/folderinfo/folderinfo_ability_all.json"], ability_id)


def template_ability(map_path: Path, shared: dict, source_id: int, ability_id: int,
                     name: str, description: str, *, passive: bool):
    if any((map_path / subdir / f"{ability_id}.json").exists()
           for subdir in ("ability", "editor_table/abilityall")):
        raise ValueError(f"ability ID is occupied: {ability_id}")
    ability = read(map_path / f"editor_table/abilityall/{source_id}.json")
    name_key, description_key = modifier_name_keys(shared, name, description)
    unit = read(map_path / f"editor_table/editorunit/{UNIT_ID}.json")
    ability.update({"_ref_": ability_id, "key": ability_id, "uid": str(ability_id),
                    "name": name_key, "desc": description_key,
                    "description": description_key,
                    "suffix": "被动" if passive else "主动",
                    "ability_icon": unit["icon"], "ability_max_level": 1})
    eca = read(map_path / f"ability/{source_id}.json")
    for trigger in eca["trigger_dict"].values():
        trigger["group_id"] = ability_id
    for group in eca.get("trigger_group_info", []):
        if group.get("_trigger_group_"):
            group["key"] = ability_id
            group["name"] = str(ability_id)
    return ability, eca


def patch_skill_one(map_path: Path, out_path: Path, shared: dict):
    ability_id = SKILL_ONE_ID
    if any((map_path / subdir / f"{ability_id}.json").exists()
           for subdir in ("ability", "editor_table/abilityall")):
        raise ValueError(f"ability ID is occupied: {ability_id}")

    description = "重击当前目标，造成190%攻击的物理伤害并嘲讽3秒。冷却8秒。"
    ability, eca = template_ability(map_path, shared, 134223225, ability_id,
                                    "虎痴重击", description, passive=False)
    ability["cold_down_time"]["items"] = ["8.0"]
    ability["kv"]["时长"]["value"] = 3.0
    ability["kv"]["额外系数"]["value"] = 1.9

    for node in descend(eca):
        if node.get("action_type") == "SET_ENTITY_KV":
            args = node.get("args_list", [])
            if len(args) == 3 and args[1].get("arg_type") == 100003:
                key = args[1]["args_list"]
                if key == ["时长"]:
                    args[2]["args_list"] = [3.0]
                    args[2]["sub_type"] = 1
                elif key == ["额外系数"]:
                    args[2]["args_list"] = [1.9]
                    args[2]["sub_type"] = 1
    cast = eca["trigger_dict"]["893440004"]
    if [action["action_type"] for action in cast["action"]][-2:] != ["APPLY_DAMAGE", "ADD_MODIFIER"]:
        raise ValueError("Zhang Fei cast template changed")
    duration_check = cast["action"][1]
    if duration_check["action_type"] != "IF_THEN_ELSE":
        raise ValueError("Zhang Fei duration branch changed")
    base_duration = copy.deepcopy(duration_check["args_list"][2]["args_list"][0])
    cast["action"][1] = base_duration
    taunt = cast["action"][-1]
    if taunt["args_list"][1]["args_list"] != [1004]:
        raise ValueError("Zhang Fei taunt template changed")
    old_sfx = next(index for index, item in enumerate(cast["action"])
                   if item["action_type"] == "CREATE_SFX_ON_UNIT_3")
    stomp = read(map_path / "ability/134260949.json")
    new_sfx = copy.deepcopy(next(node for node in descend(stomp)
                                 if node.get("action_type") == "CREATE_SFX_ON_POINT_NEW"))
    new_sfx["args_list"][0] = literal(100066, 101118)
    target = copy.deepcopy(cast["action"][-2]["args_list"][2])
    new_sfx["args_list"][1] = {"arg_type": 100004,
                               "args_list": [target], "sub_type": "UNIT_ENTITY_POINT"}
    new_sfx["element_id"] = 893440004978501
    cast["action"][old_sfx] = new_sfx
    if "134224490" in json.dumps(eca):
        raise ValueError("old Zhang Fei resource reference survived")

    bind_skill(shared, ability_id, 2, "主动", description)
    write(out_path / f"editor_table/abilityall/{ability_id}.json", ability)
    write(out_path / f"ability/{ability_id}.json", eca)


def patch_skill_four(map_path: Path, out_path: Path, shared: dict):
    ability_id = SKILL_FOUR_ID
    description = "本队近战小兵受到的伤害降低8%。"
    ability, eca = template_ability(map_path, shared, 134271608, ability_id,
                                    "虎卫", description, passive=True)
    troop = read(map_path / f"editor_table/editorunit/{UNIT_ID}.json")
    if troop["kv"]["队伍小兵类型"]["value"] != 134236300:
        raise ValueError("Xu Chu troop type changed; reassess melee-minion filter")
    ability["kv"]["伤害减免%"]["value"] = 0.08
    for node in descend(eca):
        if node.get("action_type") == "SET_ENTITY_KV":
            args = node.get("args_list", [])
            if len(args) == 3 and args[1].get("args_list") == ["伤害减免%"]:
                args[2] = literal(100000, 0.08)
    hurt = eca["trigger_dict"]["58232837"]
    if len(hurt["condition"]) != 2 or len(hurt["action"]) != 3:
        raise ValueError("Zhang Fei troop passive template changed")
    owner_condition = hurt["condition"][0]
    hurt["condition"] = [owner_condition]
    hurt["action"] = [hurt["action"][0], hurt["action"][2]]
    if "134224490" in json.dumps(eca):
        raise ValueError("old Zhang Fei resource reference survived")
    bind_skill(shared, ability_id, 7, "被动", description)
    write(out_path / f"editor_table/abilityall/{ability_id}.json", ability)
    write(out_path / f"ability/{ability_id}.json", eca)


def patch_skill_three(map_path: Path, out_path: Path, shared: dict):
    ability_id = SKILL_THREE_ID
    description = "使当前目标及附近最多3名敌人攻击降低20%，持续5秒，并击退其中的小兵。冷却11秒。"
    ability, eca = template_ability(map_path, shared, 134268037, ability_id,
                                    "虎啸断军", description, passive=False)
    ability["cold_down_time"]["items"] = ["11.0"]
    ability["kv"]["降攻系数"]["value"] = 0.2
    ability["kv"]["数量"]["value"] = 3
    for node in descend(eca):
        if node.get("action_type") == "SET_ENTITY_KV":
            args = node.get("args_list", [])
            if len(args) == 3 and args[1].get("args_list") == ["降攻系数"]:
                args[2] = literal(100000, 0.2)

    cast = eca["trigger_dict"]["893440004"]
    old_pick = next(item for item in cast["action"]
                    if item["action_type"] == "PICK_UNIT_DO_ACTION")
    old_debuff = next(node for node in descend(old_pick)
                      if node.get("action_type") == "ADD_MODIFIER")
    old_push = next(node for node in descend(old_pick)
                    if node.get("action_type") == "CALL_TRIGGER_FUNC")
    owner = arg(100006, "ABILITY_OWNER")
    current = arg(100014, "CUR_ABILITY")
    target = arg(100006, "TARGET_UNIT_IN_ABILITY", current)
    selected = arg(100006, "FOR_EACH_SELECTED_UNIT")
    key = literal(100003, "xuchu_roar_count")

    def apply_debuff(victim, suffix):
        result = copy.deepcopy(old_debuff)
        result["args_list"][0] = victim
        result["op_arg"][2] = literal(100000, 5.0)
        result["element_id"] = 893440004978600 + suffix
        return result

    def push_minion(victim, suffix):
        pushed = copy.deepcopy(old_push)
        pushed["args_list"][0]["args_list"][1] = victim
        pushed["args_list"][0]["op_arg"][0] = literal(100002, 120)
        pushed["element_id"] = 893440004978610 + suffix
        troop_owner = arg(100006, "GET_UNIT_ENTITY_KV", victim,
                          literal(100003, "所属英雄"))
        small = condition("UNIT_COMPARE", 893440004978620 + suffix,
                          troop_owner, literal(100035, "!="), arg(100006, "NONE_UNIT"))
        return action("IF_THEN_ELSE", 893440004978630 + suffix,
                      arg(100021, 1, small), arg(100022, 1, pushed), arg(100022, 1))

    pick = copy.deepcopy(old_pick)
    group = pick["args_list"][0]
    group["args_list"][0] = arg(100004, "UNIT_ENTITY_POINT", target)
    group["args_list"][1] = arg(100211, "CONST_CIRCULAR_SHAPE", literal(100000, 260.0))
    group["op_arg"][12] = literal(100002, 20)
    count = arg(100000, "GET_FLOAT_KV", current, key)
    is_extra = condition("UNIT_COMPARE", 893440004978641,
                         selected, literal(100035, "!="), target)
    has_room = condition("FLOAT_COMPARE", 893440004978642,
                         count, literal(100015, "<"), literal(100000, 2.0))
    bump = action("SET_ENTITY_KV", 893440004978643, current, key,
                  arg(100000, "ARITHMETIC_OPERATION", count,
                      literal(100017, "+"), literal(100000, 1.0)))
    add_extra = action("IF_THEN_ELSE", 893440004978644,
                       arg(100021, 1, has_room),
                       arg(100022, 1, apply_debuff(selected, 2),
                           push_minion(selected, 2), bump), arg(100022, 1))
    pick["args_list"][1] = arg(100022, 1,
                                action("IF_THEN_ELSE", 893440004978645,
                                       arg(100021, 1, is_extra),
                                       arg(100022, 1, add_extra), arg(100022, 1)))
    pick["element_id"] = 893440004978646
    effect = copy.deepcopy(next(item for item in cast["action"]
                                if item["action_type"] == "CREATE_SFX_ON_POINT_NEW"))
    effect["args_list"][0] = literal(100066, 101118)
    effect["args_list"][1] = arg(100004, "UNIT_ENTITY_POINT", target)
    effect["element_id"] = 893440004978647
    animation = copy.deepcopy(next(item for item in cast["action"]
                                   if item["action_type"] == "PLAY_ANIMATION"))
    cast["action"] = [cast["action"][0], animation, effect,
                      apply_debuff(target, 1), push_minion(target, 1),
                      action("SET_ENTITY_KV", 893440004978648,
                             current, key, literal(100000, 0.0)), pick]
    if "134224490" in json.dumps(eca):
        raise ValueError("old Zhang Fei resource reference survived")
    bind_skill(shared, ability_id, 3, "主动", description)
    write(out_path / f"editor_table/abilityall/{ability_id}.json", ability)
    write(out_path / f"ability/{ability_id}.json", eca)


def patch_skill_five(map_path: Path, out_path: Path, shared: dict):
    ability_id = SKILL_FIVE_ID
    description = "获得自身最大生命22%的护盾，持续7秒；嘲讽当前目标及附近最多3名敌人3秒。冷却15秒。"
    ability, eca = template_ability(map_path, shared, 134278144, ability_id,
                                    "一夫当关", description, passive=False)
    ability["cold_down_time"]["items"] = ["15.0"]
    cast = eca["trigger_dict"]["893440004"]
    shield = copy.deepcopy(next(item for item in cast["action"]
                                if item["action_type"] == "ADD_MODIFIER"
                                and item["args_list"][1]["args_list"] == [134274812]))
    taunt = copy.deepcopy(next(item for item in cast["action"]
                               if item["action_type"] == "ADD_MODIFIER"
                               and item["args_list"][1]["args_list"] == [1004]))
    owner = arg(100006, "ABILITY_OWNER")
    current = arg(100014, "CUR_ABILITY")
    target = arg(100006, "TARGET_UNIT_IN_ABILITY", current)
    selected = arg(100006, "FOR_EACH_SELECTED_UNIT")
    key = literal(100003, "xuchu_taunt_count")
    max_hp = arg(100000, "GET_UNIT_ATTR", owner,
                 literal(100301, "ATTR_RESULT"), literal(100042, "hp_max"))
    shield_value = arg(100000, "ARITHMETIC_OPERATION", max_hp,
                       literal(100017, "*"), literal(100000, 0.22))
    shield_set = action("SET_ENTITY_KV", 893440004978701,
                        current, literal(100003, "护盾值"), shield_value)
    shield["op_arg"][2] = literal(100000, 7.0)
    shield["op_arg_enable"][2] = True
    shield["element_id"] = 893440004978702

    def apply_taunt(victim, suffix):
        result = copy.deepcopy(taunt)
        result["args_list"][0] = victim
        result["op_arg"][2] = literal(100000, 3.0)
        result["op_arg_enable"][2] = True
        result["element_id"] = 893440004978710 + suffix
        return result

    old_pick = read(map_path / "ability/134268037.json")
    old_pick = next(node for node in descend(old_pick)
                    if node.get("action_type") == "PICK_UNIT_DO_ACTION")
    pick = copy.deepcopy(old_pick)
    group = pick["args_list"][0]
    group["args_list"][0] = arg(100004, "UNIT_ENTITY_POINT", target)
    group["args_list"][1] = arg(100211, "CONST_CIRCULAR_SHAPE", literal(100000, 260.0))
    group["op_arg"][12] = literal(100002, 20)
    count = arg(100000, "GET_FLOAT_KV", current, key)
    is_extra = condition("UNIT_COMPARE", 893440004978721,
                         selected, literal(100035, "!="), target)
    has_room = condition("FLOAT_COMPARE", 893440004978722,
                         count, literal(100015, "<"), literal(100000, 2.0))
    bump = action("SET_ENTITY_KV", 893440004978723, current, key,
                  arg(100000, "ARITHMETIC_OPERATION", count,
                      literal(100017, "+"), literal(100000, 1.0)))
    add_extra = action("IF_THEN_ELSE", 893440004978724,
                       arg(100021, 1, has_room),
                       arg(100022, 1, apply_taunt(selected, 2), bump), arg(100022, 1))
    pick["args_list"][1] = arg(100022, 1,
                                action("IF_THEN_ELSE", 893440004978725,
                                       arg(100021, 1, is_extra),
                                       arg(100022, 1, add_extra), arg(100022, 1)))
    pick["element_id"] = 893440004978726
    sfx = copy.deepcopy(next(item for item in cast["action"]
                             if item["action_type"] == "CREATE_SFX_ON_UNIT_3"))
    sfx["element_id"] = 893440004978727
    animation = copy.deepcopy(next(item for item in cast["action"]
                                   if item["action_type"] == "PLAY_ANIMATION"))
    cast["action"] = [cast["action"][1], shield_set, animation, sfx, shield,
                      apply_taunt(target, 1),
                      action("SET_ENTITY_KV", 893440004978728,
                             current, key, literal(100000, 0.0)), pick]
    if "134224490" in json.dumps(eca):
        raise ValueError("old Zhang Fei resource reference survived")
    bind_skill(shared, ability_id, 4, "主动", description)
    write(out_path / f"editor_table/abilityall/{ability_id}.json", ability)
    write(out_path / f"ability/{ability_id}.json", eca)


def patch_skill_six(map_path: Path, out_path: Path, shared: dict):
    ability_id = SKILL_SIX_ID
    buff_id = SPEED_BUFF_ID
    for subdir in ("editor_table/modifierall", "modifier"):
        if (map_path / subdir / f"{buff_id}.json").exists():
            raise ValueError(f"speed Buff ID is occupied: {buff_id}")
    description = "每次震地后，接下来2次普攻的攻击速度提高30%。"
    ability, _ = template_ability(map_path, shared, 134233053, ability_id,
                                  "连山震", description, passive=True)
    ability["kv"] = {}
    bind_skill(shared, ability_id, 8, "被动", description)
    write(out_path / f"editor_table/abilityall/{ability_id}.json", ability)

    buff = read(map_path / "editor_table/modifierall/134242281.json")
    name_key, description_key = modifier_name_keys(shared, "连山震·疾攻", "许褚：后续2次普攻攻速提高30%。")
    unit = read(map_path / f"editor_table/editorunit/{UNIT_ID}.json")
    buff.update({"_ref_": buff_id, "key": buff_id, "uid": str(buff_id),
                 "name": name_key, "desc": description_key,
                 "description": description_key, "suffix": "许褚",
                 "modifier_icon": unit["icon"], "layer_max": 1})
    buff["kv"] = {}
    add_buff_folder(shared["editor/folderinfo/folderinfo_modifier_all.json"], buff_id)
    write(out_path / f"editor_table/modifierall/{buff_id}.json", buff)

    buff_eca = read(map_path / "modifier/134242281.json")
    for trigger in buff_eca["trigger_dict"].values():
        trigger["group_id"] = buff_id
    gain = buff_eca["trigger_dict"]["1625518081"]
    loss = buff_eca["trigger_dict"]["1726324738"]
    current = arg(100076, "CUR_MODIFIER")
    remaining_key = literal(100003, "xuchu_speed_hits")
    gain["action"].insert(0, action("SET_ENTITY_KV", 1625518081810080,
                                    current, remaining_key, literal(100000, 2.0)))
    attr = next(item for item in gain["action"]
                if item["action_type"] == "ADD_MODIFIER_OWNER_ATTR")
    attr["args_list"][3] = literal(100000, 0.3)
    gain["action"].append(1418035204)
    source = read(map_path / "modifier/134283902.json")
    hit = copy.deepcopy(source["trigger_dict"]["1418035204"])
    hit["group_id"] = buff_id
    hit["p_trigger_id"] = 1625518081
    hit["condition"] = [hit["condition"][0]]
    remaining = arg(100000, "GET_FLOAT_KV", current, remaining_key)
    is_last = condition("FLOAT_COMPARE", 1418035204900090,
                        remaining, literal(100015, "<="), literal(100000, 1.0))
    remove = action("REMOVE_BUFF_INS", 1418035204900091, current)
    decrement = action("SET_ENTITY_KV", 1418035204900092,
                       current, remaining_key,
                       arg(100000, "ARITHMETIC_OPERATION", remaining,
                           literal(100017, "-"), literal(100000, 1.0)))
    hit["action"] = [action("IF_THEN_ELSE", 1418035204900093,
                            arg(100021, 1, is_last), arg(100022, 1, remove),
                            arg(100022, 1, decrement))]
    buff_eca["trigger_dict"]["1418035204"] = hit
    buff_eca["local_variable"]["1418035204"] = {
        "variable_dict": {}, "variable_length_dict": {}}
    buff_eca["trigger_group_info"][0]["key"] = buff_id
    buff_eca["trigger_group_info"][0]["name"] = str(buff_id)
    buff_eca["trigger_group_info"].append(
        {"__tuple__": True, "items": [1418035204, "子触发器"]})
    unreg = copy.deepcopy(source["trigger_dict"]["594665475"]["action"][0])
    unreg["element_id"] = 1726324738810090
    loss["action"].append(unreg)
    write(out_path / f"modifier/{buff_id}.json", buff_eca)

    loop = copy.deepcopy(source)
    full = loop["trigger_dict"]["1418035204"]["action"][1]
    full_actions = full["args_list"][1]["args_list"]
    if full_actions[-1]["action_type"] != "SET_ENTITY_KV":
        raise ValueError("Xu Chu quake tail changed")
    add_speed = copy.deepcopy(next(node for node in descend(
        read(map_path / "modifier/134219544.json"))
        if node.get("action_type") == "ADD_MODIFIER"))
    add_speed["args_list"][0] = arg(100006, "MODIFIER_OWNER")
    add_speed["args_list"][1] = literal(100046, buff_id)
    add_speed["op_arg"][0] = arg(100006, "MODIFIER_OWNER")
    add_speed["op_arg"][1] = arg(100014, "RELATED_ABILITY", current)
    add_speed["op_arg_enable"][2] = False
    add_speed["element_id"] = 1418035204900094
    has_six = condition("CHECK_HAS_ABILITY_TYPE", 1418035204900095,
                        arg(100006, "MODIFIER_OWNER"), literal(100039, ability_id))
    full_actions.append(action("IF_THEN_ELSE", 1418035204900096,
                               arg(100021, 1, has_six),
                               arg(100022, 1, add_speed), arg(100022, 1)))
    speed_instance = arg(100076, "GET_LAST_MODIFIER_INSTANCE",
                         arg(100006, "MODIFIER_OWNER"), literal(100046, buff_id))
    exists = condition("FLOAT_COMPARE", 594665475000091,
                       arg(100002, "GET_MOD_STACK", speed_instance),
                       literal(100015, ">"), literal(100002, 0))
    cleanup = action("IF_THEN_ELSE", 594665475000092,
                     arg(100021, 1, exists),
                     arg(100022, 1,
                         action("REMOVE_BUFF_INS", 594665475000093, speed_instance)),
                     arg(100022, 1))
    loop["trigger_dict"]["594665475"]["action"].insert(0, cleanup)
    write(out_path / "modifier/134283902.json", loop)


def validate_stage(map_path: Path, out_path: Path):
    ids = (SKILL_ONE_ID, 134283901, SKILL_THREE_ID,
           SKILL_FOUR_ID, SKILL_FIVE_ID, SKILL_SIX_ID)
    unit = read(out_path / "tables/单位技能配置表.json")
    rows = unit["table_data"]["data"]
    row = next(row for row in rows if row[:2] == ["许褚", UNIT_ID])
    if tuple(row[index] for index in (2, 6, 3, 7, 4, 8)) != ids:
        raise ValueError(f"Xu Chu skill slots mismatch: {row[:10]}")
    old_rows = read(map_path / "tables/单位技能配置表.json")["table_data"]["data"]
    if len(rows) != len(old_rows) or any(
            current != previous for current, previous in zip(rows, old_rows)
            if current[:2] != ["许褚", UNIT_ID]):
        raise ValueError("unrelated unit skill row changed")
    desc = read(out_path / "tables/技能作用描述表.json")
    old_desc = read(map_path / "tables/技能作用描述表.json")
    if desc["table_data"]["data"][:len(old_desc["table_data"]["data"])] != old_desc["table_data"]["data"]:
        raise ValueError("existing description row changed")
    if read(out_path / "tables/技能特有循环机制表.json") != read(map_path / "tables/技能特有循环机制表.json"):
        raise ValueError("core-loop table changed")
    for ability_id in ids:
        count = sum(line[1] == ability_id for line in desc["table_data"]["data"][2:])
        if count != 1:
            raise ValueError(f"description row count {count} for {ability_id}")
    for ability_id in ids:
        ability = read(out_path / f"editor_table/abilityall/{ability_id}.json") if ability_id != 134283901 else read(map_path / f"editor_table/abilityall/{ability_id}.json")
        if ability["key"] != ability_id or ability["ability_icon"] != 134262300:
            raise ValueError(f"ability ID/icon mismatch: {ability_id}")
    ability_folder = read(out_path / "editor/folderinfo/folderinfo_ability_all.json")["d"]
    old_ability_folder = read(map_path / "editor/folderinfo/folderinfo_ability_all.json")["d"]
    if any(ability_folder.get(key) != value for key, value in old_ability_folder.items()):
        raise ValueError("existing ability folder entry changed")
    parent = ability_folder["134283901"]["items"][0]
    new_indices = [ability_folder[str(ability_id)]["items"][1]
                   for ability_id in ids if ability_id != 134283901]
    if len(set(new_indices)) != len(new_indices) or any(
            ability_folder[str(ability_id)]["items"][0] != parent
            for ability_id in ids if ability_id != 134283901):
        raise ValueError("Xu Chu ability folder entries are not unique siblings")
    buff = read(out_path / f"editor_table/modifierall/{SPEED_BUFF_ID}.json")
    if buff["key"] != SPEED_BUFF_ID or buff["modifier_icon"] != 134262300:
        raise ValueError("speed Buff metadata mismatch")
    old_buff_folder = read(map_path / "editor/folderinfo/folderinfo_modifier_all.json")["d"]
    new_buff_folder = read(out_path / "editor/folderinfo/folderinfo_modifier_all.json")["d"]
    if any(new_buff_folder.get(key) != value for key, value in old_buff_folder.items()):
        raise ValueError("existing Buff folder entry changed")
    old_language = read(map_path / "zhlanguage.json")
    new_language = read(out_path / "zhlanguage.json")
    if any(new_language.get(key) != value for key, value in old_language.items()):
        raise ValueError("existing localization changed")
    for ability_id in (SKILL_ONE_ID, SKILL_THREE_ID, SKILL_FOUR_ID, SKILL_FIVE_ID):
        eca = read(out_path / f"ability/{ability_id}.json")
        if any(trigger["group_id"] != ability_id for trigger in eca["trigger_dict"].values()):
            raise ValueError(f"ECA group mismatch: {ability_id}")
        if "134224490" in json.dumps(eca):
            raise ValueError(f"Zhang Fei resource survived: {ability_id}")
    speed_eca = read(out_path / f"modifier/{SPEED_BUFF_ID}.json")
    if any(trigger["group_id"] != SPEED_BUFF_ID for trigger in speed_eca["trigger_dict"].values()):
        raise ValueError("speed Buff ECA group mismatch")
    if len(speed_eca["trigger_dict"]["1418035204"]["action"]) != 1:
        raise ValueError("speed Buff hit counter is not singular")
    if not any(group.get("items", [None])[0] == 1418035204
               for group in speed_eca["trigger_group_info"]):
        raise ValueError("speed Buff subtrigger missing from group index")
    loop_before = read(map_path / "modifier/134283902.json")
    loop_after = read(out_path / "modifier/134283902.json")
    before_hit = loop_before["trigger_dict"]["1418035204"]["action"][1]
    after_hit = loop_after["trigger_dict"]["1418035204"]["action"][1]
    full_before = before_hit["args_list"][1]["args_list"]
    full_after = after_hit["args_list"][1]["args_list"]
    if full_after[:-1] != full_before or len(full_after) != len(full_before) + 1:
        raise ValueError("Xu Chu quake actions changed beyond 6-star hook")
    before_loss = loop_before["trigger_dict"]["594665475"]["action"]
    after_loss = loop_after["trigger_dict"]["594665475"]["action"]
    if after_loss[1:] != before_loss or len(after_loss) != len(before_loss) + 1:
        raise ValueError("Xu Chu loop loss actions changed beyond 6-star cleanup")
    for key in loop_before["trigger_dict"]:
        if key not in ("1418035204", "594665475") and loop_after["trigger_dict"][key] != loop_before["trigger_dict"][key]:
            raise ValueError(f"unrelated Xu Chu loop trigger changed: {key}")


def repair_staged_minion_conditions(out_path: Path):
    roar_path = out_path / f"ability/{SKILL_THREE_ID}.json"
    roar = read(roar_path)
    repaired = 0
    for node in descend(roar):
        if (node.get("condition_type") == "UNIT_HAS_TAG"
                and len(node.get("args_list", [])) == 2
                and node["args_list"][1].get("args_list") == ["小兵"]):
            victim = copy.deepcopy(node["args_list"][0])
            element_id = node["element_id"]
            node.clear()
            node.update(condition("UNIT_COMPARE", element_id,
                                  arg(100006, "GET_UNIT_ENTITY_KV", victim,
                                      literal(100003, "所属英雄")),
                                  literal(100035, "!="), arg(100006, "NONE_UNIT")))
            repaired += 1
    if repaired != 2:
        raise ValueError(f"expected two roar minion filters, found {repaired}")
    guard_path = out_path / f"ability/{SKILL_FOUR_ID}.json"
    guard = read(guard_path)
    hurt = guard["trigger_dict"]["58232837"]
    if (len(hurt["condition"]) != 2 or
            hurt["condition"][1]["condition_type"] != "UNIT_HAS_TAG" or
            hurt["condition"][1]["args_list"][1]["args_list"] != ["小兵"]):
        raise ValueError("guard minion filter changed unexpectedly")
    hurt["condition"] = [hurt["condition"][0]]
    for relative, key in ((f"ability/{SKILL_ONE_ID}.json", SKILL_ONE_ID),
                          (f"ability/{SKILL_THREE_ID}.json", SKILL_THREE_ID),
                          (f"ability/{SKILL_FOUR_ID}.json", SKILL_FOUR_ID),
                          (f"ability/{SKILL_FIVE_ID}.json", SKILL_FIVE_ID)):
        path = out_path / relative
        eca = roar if key == SKILL_THREE_ID else guard if key == SKILL_FOUR_ID else read(path)
        for group in eca.get("trigger_group_info", []):
            if group.get("_trigger_group_"):
                group["key"] = key
                group["name"] = str(key)
        write(path, eca)
    speed_path = out_path / f"modifier/{SPEED_BUFF_ID}.json"
    speed = read(speed_path)
    speed["trigger_group_info"][0]["key"] = SPEED_BUFF_ID
    speed["trigger_group_info"][0]["name"] = str(SPEED_BUFF_ID)
    if not any(group.get("items", [None])[0] == 1418035204
               for group in speed["trigger_group_info"]):
        speed["trigger_group_info"].append(
            {"__tuple__": True, "items": [1418035204, "子触发器"]})
    write(speed_path, speed)


def stage(map_path: Path, out_path: Path):
    shared = {relative: read(map_path / relative) for relative in SHARED}
    patch_skill_one(map_path, out_path, shared)
    patch_skill_three(map_path, out_path, shared)
    patch_skill_four(map_path, out_path, shared)
    patch_skill_five(map_path, out_path, shared)
    patch_skill_six(map_path, out_path, shared)
    for relative, value in shared.items():
        write(out_path / relative, value)
    validate_stage(map_path, out_path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("map", type=Path)
    parser.add_argument("out", type=Path)
    parser.add_argument("--repair-existing", action="store_true")
    args = parser.parse_args()
    if args.repair_existing:
        repair_staged_minion_conditions(args.out)
    else:
        stage(args.map, args.out)

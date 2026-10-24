"""Read-only P2 middle candidates. Never publishes, reloads or writes a map.

Each build rereads root. P1 modules are deliberately not imported. Native API
evidence: map3 134235502 hit counter, 134243430 ADD_MODIFIER expression,
134255911 IS_ENEMY, existing property-backed modifier contributions.
Conditional damage uses native Modifier snapshots (134259689), source-team
filtering (134227930), and damage listeners, not generic attack attributes.
"""

from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path

CAST = "893440004"
LEVEL = "26066946"
MELEE = ("刀兵", "枪兵", "盾兵", "骑兵")
HIT_COUNT = "P2_ganning_normal_hits"
SHOT_COUNT = "P2_ganning_shots"
PRIMARY = "P2_primary_hit"
EXTRAS = "P2_extra_candidates"
EXTRA_COUNT = "P2_extra_count"
EAGLE_RATIO = "P2_yingshi_ratio"
EAGLE_HANDLE = "P2_yingshi_instance"
EAGLE_TARGET = "P2_yingshi_target"
EAGLE_ENHANCED = "P2_yingshi_enhanced_ratio"
CONDITIONAL_RATIO = "P2_conditional_ratio"
CONDITIONAL_TARGET = "P2_conditional_target"
CONDITIONAL_CORE = "P2_conditional_core"
CONDITIONAL_READY = "P2_conditional_ready"
CONDITIONAL_ACTIVE = "P2_conditional_active"
CONDITIONAL_HANDLE = "P2_conditional_instance"
SOURCE_SUPPORT, TARGET_SUPPORT = 134299015, 134299016
CONDITIONAL_IDS = (134236412, 134263656, 134259902, 134237178)
FOLDERS = "editor/folderinfo/folderinfo_modifier_all.json"


class ReviewError(ValueError):
    pass


def need(ok, message):
    if not ok:
        raise ReviewError(message)


def expr(t, s, *args):
    return {"arg_type": t, "sub_type": s, "args_list": list(args)}


def lit(value, t=100002):
    return expr(t, 1, value)


def value(n):
    need(isinstance(n, dict) and n.get("sub_type") == 1
         and len(n.get("args_list", [])) == 1, "expected primitive literal")
    return n["args_list"][0]


def reviewed_expression(tree):
    need(all(set(n) <= {"arg_type", "sub_type", "args_list", "__tuple__", "items"}
             for n in walk(tree, False)), "unknown metadata on expression to be replaced")


def walk(x, active=True):
    if isinstance(x, dict):
        if active and x.get("enable") is False:
            return
        yield x
        for key, child in x.items():
            if active and key == "op_arg":
                for arg, enabled in zip(child, x.get("op_arg_enable", [])):
                    if enabled is True:
                        yield from walk(arg, active)
            elif key != "op_arg_enable":
                yield from walk(child, active)
    elif isinstance(x, list):
        for child in x:
            yield from walk(child, active)


def one(tree, predicate, label):
    found = [n for n in walk(tree) if predicate(n)]
    need(len(found) == 1, f"{label}: expected one active node, got {len(found)}")
    return found[0]


def action(tree, kind, eid=None):
    return one(tree, lambda n: n.get("action_type") == kind
               and (eid is None or n.get("element_id") == eid), f"{kind}/{eid}")


def isexpr(n, kind):
    return isinstance(n, dict) and n.get("sub_type") == kind


def binary(n, op):
    need(n.get("sub_type") in ("ARITHMETIC_OPERATION", "MATH_OPERATION")
         and len(n.get("args_list", [])) == 3 and value(n["args_list"][1]) == op,
         f"expected native binary {op}")
    return n["args_list"][0], n["args_list"][2]


def math(a, op, b, integer=False):
    return expr(100002 if integer else 100000,
                "MATH_OPERATION" if integer else "ARITHMETIC_OPERATION",
                a, lit(op, 100016 if integer else 100017), b)


def unit(kind):
    return expr(100006, kind)


def kv(key, entity=None):
    return expr(100000, "GET_FLOAT_KV", entity or expr(100014, "CUR_ABILITY"), lit(key, 100003))


def ref(typ, name, scope="local"):
    t, sub = {"INTEGER": (100002, 6), "FLOAT": (100000, 2),
              "UNIT_ENTITY": (100006, 11), "UNIT_GROUP": (100026, 14),
              "MODIFIER_ENTITY": (100076, 11)}[typ]
    return expr(t, sub, [typ, name, scope])


def factory(doc):
    index = max((n.get("element_id", 0) for n in walk(doc, False)), default=0) + 1

    def make(kind, *args, condition=False):
        nonlocal index
        n = {"condition_type" if condition else "action_type": kind,
             "args_list": list(args), "element_id": index, "enable": True}
        if not condition:
            n["bp"] = False
        index += 1
        return n

    return make


def iff(make, conditions, yes, no=()):
    n = make("IF_THEN_ELSE", expr(100021, 1, *conditions),
             expr(100022, 1, *yes), expr(100022, 1, *no))
    n["fake_op"] = []
    return n


def assign(make, typ, name, rhs, scope="local"):
    lhs = ref(typ, name, scope) if typ == "MODIFIER_ENTITY" else expr(100030, 1, [typ, name, scope])
    return make("SET_VARIABLE", lhs, rhs)


def compare(make, a, op, b, kind="FLOAT_COMPARE"):
    return make(kind, a, lit(op, 100035 if kind != "FLOAT_COMPARE" else 100015), b, condition=True)


def declare(doc, typ, name, tid=None):
    if tid is None:
        need(all(name not in v for v in doc["variable_dict"].values()), f"reserved actor local exists: {name}")
        doc["variable_dict"].setdefault(typ, {})[name] = 0
        doc["variable_length_dict"][name] = 0
        doc["variable_group_info"].append({"__tuple__": True, "items": [name, name]})
    else:
        local = doc["local_variable"][tid]
        t = doc["trigger_dict"][tid]
        need(name not in local["variable_length_dict"] and name not in t["var_data"][1],
             f"reserved local exists: {name}")
        local["variable_dict"].setdefault(typ, {})[name] = 0
        local["variable_length_dict"][name] = 0
        t["var_data"][0].setdefault(typ, {})[name] = 0
        t["var_data"][1][name] = 0
        t["var_data"][2].append(name)


def trigger(doc, tid, event):
    t = doc["trigger_dict"][tid]
    need(any(e.get("event_type") == event and e.get("enable") is not False for e in t["event"]),
         f"trigger {tid} event changed")
    if t.get("enabled") is False:
        parent = doc["trigger_dict"].get(str(t.get("p_trigger_id")), {})
        need(parent.get("enabled") is True and t.get("is_conf") is True,
             f"trigger {tid} is disabled, not a registered dynamic template")
        need(any(isinstance(v, int) and v == int(tid)
                 for n in walk(parent.get("action", [])) for v in n.get("args_list", []))
             or int(tid) in parent.get("action", []), f"trigger {tid} missing registration link")
        reg = t.get("sub_trigger_owner_set_var_action", {})
        need(reg.get("enable") is not False and any(
            n.get("sub_type") in ("REG_ABILITY_TRIGGER", "REG_MODIFIER_TRIGGER")
            for n in walk(reg)), f"trigger {tid} registration disabled")
    return t


def level_cases(doc):
    switch = action(trigger(doc, LEVEL, "ABILITY_LEVEL_CHANGED")["action"], "SWITCH")
    cases = switch["args_list"][1]["args_list"]
    need([value(c["args_list"][0]) for c in cases if c.get("enable") is not False]
         == [1, 2, 3, 4, 5], "level branches changed")
    return cases


def check_levels(doc, expected):
    for c in level_cases(doc):
        for key, number in expected.items():
            n = one(c, lambda n: n.get("action_type") == "SET_ENTITY_KV"
                    and value(n["args_list"][1]) == key, f"level KV {key}")
            need(value(n["args_list"][2]) == number, f"review changed level value {key}")


def add_level_kv(doc, make, key, number, integer=False):
    for c in level_cases(doc):
        body = c["args_list"][1]["args_list"]
        need(not any(n.get("action_type") == "SET_ENTITY_KV"
                     and value(n["args_list"][1]) == key for n in walk(body)), f"KV exists: {key}")
        body.insert(0, make("SET_ENTITY_KV", expr(100014, "CUR_ABILITY"), lit(key, 100003),
                            lit(number, 100002 if integer else 100000)))


def property_kv(doc, key, number, integer=False):
    need(key not in doc["kv"], f"property KV exists: {key}")
    doc["kv"][key] = {"annotation": "", "desc": "", "etype": 1 if integer else 2,
                       "key": key, "prop_cls": "PInt" if integer else "PFloat",
                       "remark": "", "show_in_attr": True, "sort": len(doc["kv"]),
                       "type": 2 if integer else 1, "value": number}


def instance(modifier, owner="ABILITY_OWNER"):
    return expr(100076, "GET_LAST_MODIFIER_INSTANCE", unit(owner), lit(modifier, 100046))


def legal(make, selected, body, melee=False, owner=None):
    conditions = [make("IS_UNIT_ALIVE", deepcopy(selected), condition=True),
                  make("BOOL_NOT", expr(100001, "UNIT_HAS_TAG", deepcopy(selected), lit("已死亡", 100003)), condition=True)]
    if owner is not None:
        conditions.append(make("IS_ENEMY", deepcopy(selected), deepcopy(owner), condition=True))
    if melee:
        for tag in ("仆从伙伴", "阵型队长"):
            conditions.append(make("BOOL_NOT", expr(100001, "UNIT_HAS_TAG", deepcopy(selected), lit(tag, 100003)), condition=True))
        conditions.append(make("OR", expr(100021, 1, *[
            make("UNIT_HAS_TAG", deepcopy(selected), lit(tag, 100003), condition=True) for tag in MELEE]), condition=True))
    return iff(make, [make("TYPE_IS_EXIST", deepcopy(selected), condition=True)],
               [iff(make, conditions, body)])


def repair_recipients(doc):
    t = trigger(doc, "1051000836", "GLOBAL_MODIFIER_EVENT" if doc["trigger_dict"]["1051000836"]["event"][0]["event_type"] == "GLOBAL_MODIFIER_EVENT" else "SPECIAL_UNIT_EVENT")
    pick = action(t["action"], "PICK_UNIT_DO_ACTION")
    add = action(pick["args_list"][1], "ADD_MODIFIER")
    need(isexpr(add["args_list"][0], "ABILITY_OWNER"), "soldier recipient already changed")
    make = factory(doc)
    add["args_list"][0]["sub_type"] = "FOR_EACH_SELECTED_UNIT"
    body = pick["args_list"][1]["args_list"]
    old_body = list(body)
    body[:] = [legal(make, unit("FOR_EACH_SELECTED_UNIT"), old_body, melee=True)]
    return "Only the iterated living melee soldiers receive this Buff; owner self-buff, source/ability/duration and pre-existing filters remain unchanged. Existing generic-attack semantics are NOT claimed to implement target-specific damage."


def repair_ganning_core(doc):
    t = trigger(doc, "1418035204", "SPECIAL_UNIT_EVENT")
    event = t["event"][0]
    need(value(event["args_list"][1]) == "ET_UNIT_RELEASE_ABILITY", "core event changed")
    cond = one(t["condition"], lambda n: n.get("condition_type") == "ABILITY_TYPE_COMPARE", "old attack-release condition")
    need(value(cond["args_list"][2]) == 1, "old attack type changed")
    reviewed_expression(cond["args_list"])
    add = action(t["action"], "ADD_BUFF_STACK")
    need(value(add["args_list"][1]) == 1 and isexpr(add["args_list"][0], "CUR_MODIFIER"), "core stack action changed")
    make = factory(doc)
    declare(doc, "INTEGER", HIT_COUNT)
    event["args_list"][1]["args_list"][0] = "ET_UNIT_HURT_OTHER"
    cond["condition_type"], cond["args_list"] = "GET_IS_NORMAL_HIT_FROM_EVENT", []
    t["condition"].append(make("IS_ENEMY", unit("DAMAGE_TARGET_UNIT"), unit("MODIFIER_OWNER"), condition=True))
    counter = ref("INTEGER", HIT_COUNT, "actor")
    body = [assign(make, "INTEGER", HIT_COUNT, expr(100002, "INT_PLUS_ONE", deepcopy(counter)), "actor"),
            iff(make, [compare(make, deepcopy(counter), ">=", lit(3))],
                [assign(make, "INTEGER", HIT_COUNT, lit(0), "actor"), add])]
    t["action"] = [iff(make, [make("TYPE_IS_EXIST", expr(100076, "CUR_MODIFIER"), condition=True)], body)]
    gain = trigger(doc, "1485688834", "OBTAIN_MODIFIER")
    gain["action"].insert(0, assign(make, "INTEGER", HIT_COUNT, lit(0), "actor"))
    return "Count outgoing normal-attack damage hits on enemies; every third hit grants one powder; per-core counter resets on obtain. Miss/release/skill damage do not count."


def repair_burst(doc, prop):
    check_levels(doc, {"伤害系数": 0.85, "伤害提高": 0.95})
    t = trigger(doc, CAST, "ABILITY_SP_END")
    timer = action(t["action"], "RUN_COUNT_TIMER_NO_SAVE")
    need(value(timer["args_list"][1]) == 3, "burst count changed")
    branch = action(t["action"], "IF_THEN_ELSE", 893440004974869)
    make = factory(doc)
    declare(doc, "INTEGER", SHOT_COUNT, CAST)
    for key, count in (("P2_normal_shots", 3), ("P2_enhanced_shots", 5)):
        property_kv(prop, key, count, True)
        add_level_kv(doc, make, key, count, True)
    def count_kv(key):
        return expr(100002, "GET_INTEGER_KV", expr(100014, "CUR_ABILITY"), lit(key, 100003))
    # GET_INTEGER_KV is used by native map3; this is not a float-to-int coercion.
    index = t["action"].index(branch)
    t["action"].insert(index, assign(make, "INTEGER", SHOT_COUNT, count_kv("P2_normal_shots")))
    branch["args_list"][1]["args_list"].insert(0, assign(make, "INTEGER", SHOT_COUNT, count_kv("P2_enhanced_shots")))
    timer["args_list"][1].update(ref("INTEGER", SHOT_COUNT))
    return "Per-cast shot count snapshots 3/5 from level-backed integer KV before powder consumption; existing .85/.95 damage formulas and projectile flow retained."


def repair_caoren_duration(doc):
    check_levels(doc, {"伤害系数": 1.2, "时长": 5.0})
    add = action(trigger(doc, CAST, "ABILITY_SP_END")["action"], "ADD_MODIFIER")
    need(value(add["args_list"][1]) == 134256265 and add["op_arg_enable"][2] is True,
         "Cao Ren debuff or duration option changed")
    duration = add["op_arg"][2]
    need(isexpr(duration, 2), "duration no longer unassigned local")
    reviewed_expression(duration["args_list"])
    duration.update(kv("时长"))
    return "Debuff duration reads this skill's 5s KV (all five levels). There is no separate enhanced duration; resource threshold only enables the debuff."


def repair_dianwei_threshold(doc):
    t = trigger(doc, CAST, "ABILITY_SP_END")
    cond = one(t["action"], lambda n: n.get("condition_type") == "FLOAT_COMPARE"
               and n.get("element_id") == 893440004974059, "Dian Wei threshold")
    need(value(cond["args_list"][1]) == ">" and value(cond["args_list"][2]) == 3,
         "threshold changed")
    cond["args_list"][2]["args_list"][0] = 2
    return "Empowered at internal >2, i.e. visible >=2; unchanged damage payload."


def repair_dianwei_duration(doc):
    t = trigger(doc, "1051000836", "GLOBAL_MODIFIER_EVENT")
    add = action(t["action"], "ADD_BUFF_REMAINING")
    stack = one(add, lambda n: isexpr(n, "GET_MOD_STACK"), "Dian Wei internal stack")
    need(value(stack["args_list"][0]["args_list"][1]) == 134275651, "core lookup changed")
    core = deepcopy(stack["args_list"][0])
    copied = deepcopy(stack)
    stack.update(expr(100000, "I2F", math(copied, "-", lit(1), True)))
    make = factory(doc)
    event_buff = expr(100076, "GET_MODIFIER_FROM_EVENT")
    t["action"] = [iff(make, [make("TYPE_IS_EXIST", event_buff, condition=True)],
        [iff(make, [make("TYPE_IS_EXIST", core, condition=True)], [add])])]
    return "Control duration reduction uses visible=internal-1: 0/10/20/30%; missing core or event Buff skips mutation; existing control/source filters retained."


def repair_extras(doc, maximum):
    t = trigger(doc, CAST, "ABILITY_SP_END")
    pick = one(t["action"], lambda n: n.get("action_type") == "PICK_UNIT_DO_ACTION", "extra AOE iteration")
    query = pick["args_list"][0]
    need(isexpr(query, "UNIT_LIST_IN_SHAPE") and query["op_arg_enable"][0] is True
         and query["op_arg_enable"][12] is True and value(query["op_arg"][12]) == maximum,
         "extra query filters/count changed")
    mover = one(t["action"], lambda n: n.get("action_type") in ("CREATE_STRAIGHT_MOVER", "CREATE_CHASING_MOVER"), "AOE mover")
    callback = mover["args_list"][5]["args_list"]
    main = one(callback, lambda n: n.get("action_type") == "APPLY_DAMAGE"
               and not isexpr(n["args_list"][2], "FOR_EACH_SELECTED_UNIT"), "primary damage")
    need(pick in callback and callback.index(main) < callback.index(pick), "callback order changed")
    make = factory(doc)
    for typ, name in (("UNIT_ENTITY", PRIMARY), ("UNIT_GROUP", EXTRAS), ("INTEGER", EXTRA_COUNT)):
        declare(doc, typ, name, CAST)
    # Preserve all spatial/enemy/source optional arguments; only defer the cap.
    query["op_arg_enable"][12] = False
    snapshot_query = deepcopy(query)
    main_target = deepcopy(main["args_list"][2])
    main["args_list"][2] = ref("UNIT_ENTITY", PRIMARY)
    before = [assign(make, "UNIT_ENTITY", PRIMARY, main_target),
              assign(make, "UNIT_GROUP", EXTRAS, snapshot_query),
              assign(make, "INTEGER", EXTRA_COUNT, lit(0))]
    index = callback.index(main)
    callback[index:index] = before
    pick["args_list"][0] = ref("UNIT_GROUP", EXTRAS)
    body = pick["args_list"][1]["args_list"]
    count = ref("INTEGER", EXTRA_COUNT)
    admitted = iff(make, [compare(make, unit("FOR_EACH_SELECTED_UNIT"), "!=", ref("UNIT_ENTITY", PRIMARY), "UNIT_COMPARE"),
                         compare(make, deepcopy(count), "<", lit(maximum))],
                   [assign(make, "INTEGER", EXTRA_COUNT, expr(100002, "INT_PLUS_ONE", deepcopy(count))), *body])
    body[:] = [legal(make, unit("FOR_EACH_SELECTED_UNIT"), [admitted], owner=unit("ABILITY_OWNER"))]
    return f"Snapshot primary and candidate group before primary damage; exclude original primary; only living legal enemy extras count toward {maximum}. Existing P1 formulas/query flags preserved except deferring the early cap."


def _pairs(pairs):
    result = {}
    for key, val in pairs:
        need(key not in result, f"duplicate JSON key: {key}")
        result[key] = val
    return result


FIXED_ARMOR_CALLERS = {134219157: 10.0, 134237178: 12.0, 134273833: 12.0}


def repair_armor(doc, sun_property):
    gain = trigger(doc, "1625518081", "OBTAIN_MODIFIER")
    original = action(gain["action"], "ADD_MODIFIER_OWNER_ATTR")
    need(value(original["args_list"][1]) == "defense_phy"
         and value(original["args_list"][2]) == "ATTR_ALL_RATIO", "armor contribution changed")
    source = one(original, lambda n: isexpr(n, "RELATED_ABILITY_MODIFIER"), "armor related ability")
    make = factory(doc)
    fixed = deepcopy(original)
    fixed["element_id"] = make("placeholder")["element_id"]
    fixed["args_list"][2]["args_list"][0] = "ATTR_BASE"
    # Explicit fixed/ratio dispatch by reviewed source identity, never by size
    # of the numeric coefficient. Unknown future sources retain original ratio.
    modes = [compare(make, expr(100039, "ABILITY_NAME_OF_ABILITY", deepcopy(source)),
                     "==", lit(aid, 100039), "ABILITY_COMPARE") for aid in FIXED_ARMOR_CALLERS]
    dispatch = iff(make, [make("OR", expr(100021, 1, *modes), condition=True)], [fixed], [original])
    guarded = iff(make, [make("TYPE_IS_EXIST", deepcopy(source), condition=True)], [dispatch])
    gain["action"][gain["action"].index(original)] = guarded
    p = sun_property["kv"]["减甲系数"]
    need(p["prop_cls"] == "PBool" and p["type"] == 3 and p["etype"] == 4
         and p["value"] is False, "Sun Shangxiang property type/default changed")
    p.update(prop_cls="PFloat", etype=2, type=1, value=0.0)
    return "Reviewed source IDs 134219157/134237178/134273833 use fixed ATTR_BASE (-10/-12/-12); other sources retain ATTR_ALL_RATIO. Modifier-owned contribution/clear preserved. Correct Sun Shangxiang coefficient PBool to PFloat. No new support/index."


def repair_eagle(skill, buff, skill_property, buff_property):
    check_levels(skill, {"伤害系数": 2.4, "伤害提高": 0.12})
    t = trigger(skill, CAST, "ABILITY_SP_END")
    branch = action(t["action"], "IF_THEN_ELSE", 893440004974869)
    add = one(t["action"], lambda n: n.get("action_type") == "ADD_MODIFIER"
              and value(n["args_list"][1]) == 134266933, "eagle apply")
    hit = one(t["action"], lambda n: n.get("action_type") == "CREATE_CHASING_MOVER", "eagle projectile")
    callback = hit["args_list"][5]["args_list"]
    need(add in callback and add["op_arg_enable"][:3] == [True, True, True], "eagle add association changed")
    impact = action(callback, "APPLY_DAMAGE")
    need(impact in callback and callback.index(impact) < callback.index(add), "eagle damage/apply order changed")
    make = factory(skill)
    declare(skill, "FLOAT", EAGLE_RATIO, CAST)
    declare(skill, "MODIFIER_ENTITY", EAGLE_HANDLE, CAST)
    declare(skill, "UNIT_ENTITY", EAGLE_TARGET, CAST)
    property_kv(skill_property, EAGLE_ENHANCED, 0.18)
    property_kv(buff_property, EAGLE_RATIO, 0.0)
    add_level_kv(skill, make, EAGLE_ENHANCED, 0.18)
    branch["args_list"][1]["args_list"].insert(0, assign(make, "FLOAT", EAGLE_RATIO, kv(EAGLE_ENHANCED)))
    branch["args_list"][2]["args_list"].insert(0, assign(make, "FLOAT", EAGLE_RATIO, kv("伤害提高")))
    # Damage may kill/remove the target or change the actor's next target.
    # Keep the existing target operand, but capture it before that boundary.
    target_snapshot = assign(make, "UNIT_ENTITY", EAGLE_TARGET, deepcopy(add["args_list"][0]))
    callback.insert(callback.index(impact), target_snapshot)
    add["args_list"][0] = ref("UNIT_ENTITY", EAGLE_TARGET)
    call = expr(100076, "ADD_MODIFIER", *add["args_list"])
    for key in ("op_arg", "op_arg_enable"):
        call[key] = add.pop(key)
    add["action_type"] = "SET_VARIABLE"
    add["args_list"] = [ref("MODIFIER_ENTITY", EAGLE_HANDLE), call]
    handle = ref("MODIFIER_ENTITY", EAGLE_HANDLE)
    write = make("SET_ENTITY_KV", deepcopy(handle), lit(EAGLE_RATIO, 100003), ref("FLOAT", EAGLE_RATIO))
    same_source = compare(make, expr(100006, "GET_BUFF_SOURCE", deepcopy(handle)), "==", unit("ABILITY_OWNER"), "UNIT_COMPARE")
    same_ability = compare(make, expr(100014, "RELATED_ABILITY_MODIFIER", deepcopy(handle)),
                           "==", expr(100014, "CUR_ABILITY"), "ABILITY_ENTITY_COMPARE")
    guarded = iff(make, [make("TYPE_IS_EXIST", deepcopy(handle), condition=True)],
                  [iff(make, [same_source, same_ability], [write])])
    index = callback.index(add)
    callback[index:index + 1] = [legal(make, ref("UNIT_ENTITY", EAGLE_TARGET), [add, guarded])]
    response = trigger(buff, "512499716", "SPECIAL_UNIT_EVENT")
    damage = action(response["action"], "SET_CUR_DAMAGE")
    factor = damage["args_list"][0]["args_list"][2]
    _, old_ratio = binary(factor, "+")
    need(value(old_ratio) == 0.12, "eagle ratio already changed")
    old_ratio.update(kv(EAGLE_RATIO, expr(100076, "CUR_MODIFIER")))
    return "Applying skill snapshots normal .12/enhanced .18 before core consumption (five level branches). Original Buff target is captured before damage; after damage, existence then alive/death-tag checks precede ADD_MODIFIER. Returned handle is separately checked for existence, source unit and exact ability instance before writing its ratio. Buff reads its own snapshot; original source filter/unregister retained."


def _armor_callers(root):
    callers = set()
    # Reverse reference audit, no .git traversal, only actual ADD_MODIFIER sites.
    for folder in ("ability", "modifier", "global_trigger"):
        for directory, dirs, names in os.walk(root / folder):
            dirs[:] = [d for d in dirs if d != ".git"]
            for name in names:
                if not name.endswith(".json"):
                    continue
                path = Path(directory) / name
                raw = path.read_bytes()
                if b"134245346" not in raw:
                    continue
                doc = json.loads(raw, object_pairs_hook=_pairs)
                for n in walk(doc):
                    if n.get("action_type") == "ADD_MODIFIER" or n.get("sub_type") == "ADD_MODIFIER":
                        if len(n.get("args_list", [])) >= 2 and n["args_list"][1].get("args_list") == [134245346]:
                            callers.add(path.relative_to(root).as_posix())
    return callers


def audit_support_ids(root, ids=(134299015, 134299016)):
    """Check local/shared object tables and all map folder indexes, read only."""
    root = Path(root)
    project = root.parents[1]
    conflicts = []
    for mid in ids:
        for mapdir in root.parent.iterdir():
            if not mapdir.is_dir() or mapdir.name == ".git":
                continue
            folders = [mapdir / "modifier", mapdir / "ability"]
            table = mapdir / "editor_table"
            if table.is_dir():
                folders.extend(p for p in table.iterdir() if p.is_dir() and p.name != ".git")
            for folder in folders:
                p = folder / f"{mid}.json"
                if p.exists():
                    conflicts.append(str(p))
    index_roots = [project / "editor_table"]
    index_roots += [m / "editor/folderinfo" for m in root.parent.iterdir()
                    if m.is_dir() and m.name != ".git"]
    for folder in index_roots:
        for directory, dirs, names in os.walk(folder):
            dirs[:] = [d for d in dirs if d != ".git"]
            for name in names:
                if not name.endswith(".json"):
                    continue
                p = Path(directory) / name
                raw = p.read_bytes()
                if any(str(mid).encode() in raw for mid in ids):
                    conflicts.append(str(p))
    return sorted(set(conflicts))


def entity_kv(entity, key, typ=100006, getter="GET_UNIT_ENTITY_KV"):
    return expr(typ, getter, deepcopy(entity), lit(key, 100003))


def leader(make, selected):
    return make("OR", expr(100021, 1, *[
        make("UNIT_HAS_TAG", deepcopy(selected), lit(tag, 100003), condition=True)
        for tag in ("仆从伙伴", "阵型队长")]), condition=True)


def exists_then(make, entities, body):
    # Separate layers deliberately do not assume Boolean short circuiting.
    for entity in reversed(entities):
        body = [iff(make, [make("TYPE_IS_EXIST", deepcopy(entity), condition=True)], body)]
    return body


def conditional_support(template, mid):
    doc = deepcopy(template)
    for n in walk(doc, False):
        if n.get("group_id") == 134266933:
            n["group_id"] = mid
        if n.get("_trigger_group_"):
            n.update(key=mid, name=str(mid))
    make = factory(doc)
    current = expr(100076, "CUR_MODIFIER")
    source = expr(100006, "GET_BUFF_SOURCE", current)
    ability = expr(100014, "RELATED_ABILITY_MODIFIER", current)
    attacker, target = unit("DAMAGE_SOURCE_UNIT"), unit("DAMAGE_TARGET_UNIT")
    core = entity_kv(current, CONDITIONAL_CORE, 100076, "GET_MODIFIER_ENTITY_KV")
    ratio = kv(CONDITIONAL_RATIO, current)
    response = trigger(doc, "512499716", "SPECIAL_UNIT_EVENT")
    response["condition"] = []
    if mid == SOURCE_SUPPORT:
        response["event"][0].update(event_type="GENERIC_UNIT_EVENT",
            args_list=[expr(100008, "GENERIC_UNIT_EVENT", "ET_UNIT_BE_HURT")])
    # Target-side instances preserve independent six-second windows per target.
    common = [compare(make, entity_kv(attacker, "所属英雄"), "==", source, "UNIT_COMPARE"),
              compare(make, expr(100006, "GET_ABILITY_OWNER", ability), "==", source, "UNIT_COMPARE"),
              make("BOOL_COMPARE", entity_kv(ability, CONDITIONAL_ACTIVE, 100001, "GET_BOOLEAN_KV"),
                   lit("==", 100035), lit(True, 100001), condition=True)]
    for tag in ("仆从伙伴", "阵型队长"):
        common.append(make("BOOL_NOT", expr(100001, "UNIT_HAS_TAG", attacker, lit(tag, 100003)), condition=True))
    melee = make("OR", expr(100021, 1, *[
        make("UNIT_HAS_TAG", attacker, lit(tag, 100003), condition=True) for tag in MELEE]), condition=True)
    damage = make("SET_CUR_DAMAGE", math(expr(100000, "HURT_DAMAGE"), "*", math(lit(1.0, 100000), "+", ratio)))
    if mid == SOURCE_SUPPORT:
        sima = exists_then(make, [core], [iff(make, [
            compare(make, core, "==", expr(100076, "GET_LAST_MODIFIER_INSTANCE", source, lit(134232832, 100046)), "MODIFIER_COMPARE"),
            compare(make, expr(100002, "GET_MOD_STACK", core), ">=", expr(100002, "GET_MOD_STACK_MAX", core))], [damage])])
        zhang_damage = deepcopy(damage)
        zhang_damage["element_id"] = make("placeholder")["element_id"]
        effect = [iff(make, [compare(make, expr(100039, "ABILITY_NAME_OF_ABILITY", ability), "==", lit(134236412, 100039), "ABILITY_COMPARE")], sima,
            [iff(make, [compare(make, expr(100039, "ABILITY_NAME_OF_ABILITY", ability), "==", lit(134259902, 100039), "ABILITY_COMPARE"), melee], [zhang_damage])])]
        common += [leader(make, target), compare(make, unit("MODIFIER_OWNER"), "==", source, "UNIT_COMPARE")]
    else:
        effect = [damage]
        common += [melee, compare(make, target, "==", entity_kv(current, CONDITIONAL_TARGET), "UNIT_COMPARE"),
                   compare(make, target, "==", unit("MODIFIER_OWNER"), "UNIT_COMPARE")]
        # Ma Chao marks his exact target, including ordinary soldiers. Gan Ning
        # only marks leaders, and rechecks that classification on each hit.
        common.append(make("OR", expr(100021, 1,
            compare(make, expr(100039, "ABILITY_NAME_OF_ABILITY", ability), "==", lit(134237178, 100039), "ABILITY_COMPARE"),
            make("AND", expr(100021, 1,
                compare(make, expr(100039, "ABILITY_NAME_OF_ABILITY", ability), "==", lit(134263656, 100039), "ABILITY_COMPARE"),
                leader(make, target)), condition=True)), condition=True))
    guarded = [iff(make, common, effect)]
    guarded = exists_then(make, [entity_kv(attacker, "所属英雄")], guarded)
    guarded = [iff(make, [make("HAS_KV_ANY", attacker, lit("所属英雄", 100003), condition=True)], guarded)]
    guarded = [legal(make, target, guarded, owner=source)]
    guarded = [legal(make, attacker, guarded)]
    guarded = [legal(make, source, guarded)]
    response["action"] = exists_then(make, [current], [iff(make, [
        make("BOOL_COMPARE", entity_kv(current, CONDITIONAL_READY, 100001, "GET_BOOLEAN_KV"),
             lit("==", 100035), lit(True, 100001), condition=True)], exists_then(make, [ability, source], guarded))])
    gain = trigger(doc, "1625518081", "OBTAIN_MODIFIER")
    gain["action"] = [make("SET_ENTITY_KV", current, lit(CONDITIONAL_READY, 100003), lit(False, 100001)), 512499716]
    # Keep native per-instance registration and LOSS->UNREG_TRIGGER verbatim.
    doc["variable_dict"] = {"DYNAMIC_TRIGGER_INSTANCE": {"temp触发器": 0}}
    doc["variable_length_dict"] = {"temp触发器": 0}
    doc["variable_group_info"] = [{"__tuple__": True, "items": ["temp触发器", "temp触发器"]}]
    for tid, t in doc["trigger_dict"].items():
        doc["local_variable"][tid] = {"variable_dict": {}, "variable_length_dict": {}}
        t["var_data"] = [{}, {}, []]
    return doc


def apply_conditional(doc, make, tid, add, recipient, mid, ratio, target=None, core=None):
    need(add["op_arg_enable"] == [True, True, True, False, False, False], "conditional add options changed")
    need(value(add["args_list"][1]) == 134243369, "conditional old Buff changed")
    declare(doc, "MODIFIER_ENTITY", CONDITIONAL_HANDLE, tid)
    handle = ref("MODIFIER_ENTITY", CONDITIONAL_HANDLE)
    call = expr(100076, "ADD_MODIFIER", deepcopy(recipient), lit(mid, 100046))
    call["op_arg"] = deepcopy(add["op_arg"])
    call["op_arg_enable"] = list(add["op_arg_enable"])
    if mid == SOURCE_SUPPORT and core is not None:
        # Ding Ju has no arbitrary 6s cutoff. The original core is the gate.
        call["op_arg"][2] = lit(-1.0, 100000)
    writes = [make("SET_ENTITY_KV", handle, lit(CONDITIONAL_READY, 100003), lit(False, 100001)),
              make("SET_ENTITY_KV", handle, lit(CONDITIONAL_RATIO, 100003), ratio)]
    if target is not None:
        writes.append(make("SET_ENTITY_KV", handle, lit(CONDITIONAL_TARGET, 100003), target))
    if core is not None:
        writes.append(make("SET_ENTITY_KV", handle, lit(CONDITIONAL_CORE, 100003), core))
    if mid == SOURCE_SUPPORT:
        first = CONDITIONAL_HANDLE not in doc["variable_dict"].get("MODIFIER_ENTITY", {})
        if first:
            declare(doc, "MODIFIER_ENTITY", CONDITIONAL_HANDLE)
        writes.append(assign(make, "MODIFIER_ENTITY", CONDITIONAL_HANDLE, handle, "actor"))
        saved = ref("MODIFIER_ENTITY", CONDITIONAL_HANDLE, "actor")
        loss = trigger(doc, "225054724", "ABILITY_LOSE")
        cleanup = exists_then(make, [saved], [iff(make, [
            compare(make, expr(100006, "GET_BUFF_SOURCE", saved), "==",
                    expr(100006, "GET_ABILITY_OWNER", expr(100014, "CUR_ABILITY")), "UNIT_COMPARE"),
            compare(make, expr(100014, "RELATED_ABILITY_MODIFIER", saved), "==", expr(100014, "CUR_ABILITY"), "ABILITY_ENTITY_COMPARE")],
            [make("REMOVE_BUFF_INS", saved)])])
        if first:
            loss["action"].extend(cleanup)
    writes.append(make("SET_ENTITY_KV", handle, lit(CONDITIONAL_READY, 100003), lit(True, 100001)))
    check = iff(make, [compare(make, expr(100006, "GET_BUFF_SOURCE", handle), "==", unit("ABILITY_OWNER"), "UNIT_COMPARE"),
        compare(make, expr(100014, "RELATED_ABILITY_MODIFIER", handle), "==", expr(100014, "CUR_ABILITY"), "ABILITY_ENTITY_COMPARE")], writes)
    old = expr(100076, "FOR_EACH_SELECTED_MODIFIER")
    # Native iteration/removal: ability/134255234; class comparison:
    # ability/134222326. Do not infer refresh/stacking semantics from cover enums.
    owned = iff(make, [compare(make, expr(100006, "GET_BUFF_SOURCE", old), "==", unit("ABILITY_OWNER"), "UNIT_COMPARE"),
        compare(make, expr(100014, "RELATED_ABILITY_MODIFIER", old), "==", expr(100014, "CUR_ABILITY"), "ABILITY_ENTITY_COMPARE")],
        [make("REMOVE_BUFF_INS", old)])
    cleanup = make("ITER_MODIFIER_DO", deepcopy(recipient), expr(100022, 1, *exists_then(make, [old], [iff(make, [
        compare(make, expr(100046, "GET_MODIFIER_ENTITY_METATYPE", old), "==", lit(mid, 100046), "MODIFIER_CLASS_COMPARE")], [owned])])))
    after_add = exists_then(make, [handle, expr(100014, "CUR_ABILITY")], [check])
    rebuilt = [assign(make, "MODIFIER_ENTITY", CONDITIONAL_HANDLE, call), *after_add]
    # Removing an old instance executes its LOSS callback before the new add.
    rebuilt = exists_then(make, [expr(100014, "CUR_ABILITY")],
        [legal(make, unit("ABILITY_OWNER"), [legal(make, deepcopy(recipient), rebuilt)])])
    return [cleanup, *rebuilt]


def repair_conditionals(docs, conflicts):
    need(not conflicts, f"conditional support ID audit failed: {conflicts}")
    template = docs["modifier/134266933.json"]
    extra = {}
    for aid in CONDITIONAL_IDS:
        doc = docs[f"ability/{aid}.json"]
        make = factory(doc)
        gain = trigger(doc, "1959489540", "ABILITY_OBTAIN")
        # Both player and NPC leaders can own these passives.
        need(len(gain["condition"]) == 1 and gain["condition"][0]["condition_type"] == "UNIT_HAS_TAG"
             and value(gain["condition"][0]["args_list"][1]) == "仆从伙伴", "conditional gain filter changed")
        gain["condition"] = [leader(make, unit("ABILITY_OWNER"))]
        gain["action"].insert(0, make("SET_ENTITY_KV", expr(100014, "CUR_ABILITY"), lit(CONDITIONAL_ACTIVE, 100003), lit(True, 100001)))
        loss = trigger(doc, "225054724", "ABILITY_LOSE")
        loss["action"].insert(0, make("SET_ENTITY_KV", expr(100014, "CUR_ABILITY"), lit(CONDITIONAL_ACTIVE, 100003), lit(False, 100001)))
        tid = "1984499716" if aid in (134236412, 134263656) else "1051000836"
        t = trigger(doc, tid, "GLOBAL_MODIFIER_EVENT" if aid == 134236412 else "SPECIAL_UNIT_EVENT")
        pick = action(t["action"], "PICK_UNIT_DO_ACTION")
        add = action(pick, "ADD_MODIFIER")
        if aid == 134236412:
            check_levels(doc, {"加攻系数": .25})
            core = expr(100076, "GET_MODIFIER_FROM_EVENT")
            need(len(t["condition"]) == 2 and t["condition"][0]["condition_type"] == "MODIFIER_COMPARE", "Sima original conditions changed")
            conditions = t["condition"]
            t["condition"] = []
            effect = apply_conditional(doc, make, tid, add, unit("ABILITY_OWNER"), SOURCE_SUPPORT, kv("加攻系数"), core=core)
            t["action"] = exists_then(make, [core, instance(134232832)], [iff(make, conditions, effect)])
            # A six-star passive gained while Ding Ju is already active must
            # work immediately, without waiting for another layer-change.
            initial_core = instance(134232832)
            initial = apply_conditional(doc, make, "1959489540", add, unit("ABILITY_OWNER"),
                SOURCE_SUPPORT, kv("加攻系数"), core=initial_core)
            gain["action"].extend(exists_then(make, [initial_core], [iff(make, [
                compare(make, expr(100002, "GET_MOD_STACK", initial_core), ">=", expr(100002, "GET_MOD_STACK_MAX", initial_core))], initial)]))
        elif aid == 134263656:
            check_levels(doc, {"加攻系数": .25})
            need(value(t["event"][0]["args_list"][1]) == "ET_UNIT_RELEASE_ABILITY", "Gan event changed")
            t["event"][0]["args_list"][1] = lit("ET_UNIT_HURT_OTHER", 100007)
            conditions = t["condition"]
            need(len(conditions) == 1 and conditions[0]["condition_type"] == "ABILITY_TYPE_COMPARE"
                 and value(conditions[0]["args_list"][2]) == 3, "Gan active type changed")
            t["condition"] = []
            declare(doc, "UNIT_ENTITY", CONDITIONAL_TARGET, tid)
            target = ref("UNIT_ENTITY", CONDITIONAL_TARGET)
            effect = apply_conditional(doc, make, tid, add, target, TARGET_SUPPORT, kv("加攻系数"), target=target)
            t["action"] = exists_then(make, [expr(100014, "DAMAGE_ABILITY")], [iff(make, conditions, [
                assign(make, "UNIT_ENTITY", CONDITIONAL_TARGET, unit("DAMAGE_TARGET_UNIT")),
                legal(make, target, [iff(make, [leader(make, target)], effect)], owner=unit("ABILITY_OWNER"))])])
        elif aid == 134259902:
            # Trigger on the actual three-point consumption, not the earlier
            # release event (whose ordering relative to cast is engine-owned).
            t["event"][0].update(event_type="GLOBAL_MODIFIER_EVENT", args_list=[lit("ET_MODIFIER_LAYER_CHANGE", 100129)])
            core = expr(100076, "GET_MODIFIER_FROM_EVENT")
            t["condition"] = []
            owner_buff = t["action"][0]
            need(value(owner_buff["args_list"][1]) == 134243369, "Zhang self attack Buff changed")
            effect = apply_conditional(doc, make, tid, add, unit("ABILITY_OWNER"), SOURCE_SUPPORT,
                                       math(kv("加攻系数"), "/", lit(100.0, 100000)))
            t["action"] = exists_then(make, [core, instance(134259689)], [iff(make, [
                compare(make, core, "==", instance(134259689), "MODIFIER_COMPARE"),
                compare(make, expr(100002, "GET_MODIFIER_LAYER_CHANGE_VALUE"), "==", lit(-3)),
                compare(make, expr(100002, "GET_MOD_STACK", core), "==", lit(1))], [owner_buff, *effect])])
            # Preserve the original +15 attack coefficient; repair its stale
            # fifth-level 12, rather than changing the shared attack Buff.
            for case in level_cases(doc):
                setter = one(case, lambda n: n.get("action_type") == "SET_ENTITY_KV" and value(n["args_list"][1]) == "加攻系数", "Zhang attack coefficient")
                need(value(setter["args_list"][2]) in (12.0, 15.0), "Zhang coefficient changed")
                setter["args_list"][2] = lit(15.0, 100000)
        else:
            check_levels(doc, {"减甲系数": 12.0, "加攻系数": 15.0})
            declare(doc, "UNIT_ENTITY", CONDITIONAL_TARGET, tid)
            target = ref("UNIT_ENTITY", CONDITIONAL_TARGET)
            armor = t["action"][0]
            need(value(armor["args_list"][1]) == 134245346, "Ma armor changed")
            armor["args_list"][0] = target
            effect = apply_conditional(doc, make, tid, add, target, TARGET_SUPPORT,
                                       math(kv("加攻系数"), "/", lit(100.0, 100000)), target=target)
            t["action"] = [
                assign(make, "UNIT_ENTITY", CONDITIONAL_TARGET, unit("GET_ABILITY_TARGET_UNIT_FROM_EVENT")),
                legal(make, target, [armor, *effect], owner=unit("ABILITY_OWNER"))]
        # Additions for one conditional caller are local; scalar state is only
        # written on the returned, source/exact-ability-checked instance.
        t["action"] = [legal(make, unit("ABILITY_OWNER"), t["action"])]
    folder, language, tids = (docs[p] for p in (FOLDERS, "zhlanguage.json", "tidindexinfo.json"))
    for mid in (SOURCE_SUPPORT, TARGET_SUPPORT):
        extra[f"modifier/{mid}.json"] = conditional_support(template, mid)
        prop = deepcopy(docs["editor_table/modifierall/134227930.json"])
        prop.update(_ref_=mid, key=mid, uid=str(mid), kv={}, suffix="P2条件增伤", show_on_ui=False,
                    modifier_effect=3 if mid == SOURCE_SUPPORT else 2,
                    modifier_cover_type=1 if mid == SOURCE_SUPPORT else 3,
                    same_origin_cover=True, time_change_of_cover=1)
        for key, text in (("name", "定向增伤·来源" if mid == SOURCE_SUPPORT else "定向增伤·目标"),
                          ("desc", "按来源、所属小队与目标条件提高本次伤害；不提高攻击属性。")):
            index = -2100000000 - (mid - 134000000) * 2 - (key == "desc")
            need(str(index) not in language and str(index) not in tids, f"conditional text ID collision {index}")
            language[str(index)] = text
            tids[str(index)] = {"editor_type": "modifier_all", "index_type": "object_editor", "item_key": mid, "prop_key": key}
            prop[key] = index
            if key == "desc": prop["description"] = index
        extra[f"editor_table/modifierall/{mid}.json"] = prop
        need(str(mid) not in folder["d"], "conditional folder collision")
        parent = folder["d"]["134266933"]["items"][0]
        order = max(v["items"][1] for v in folder["d"].values() if v["items"][0] == parent) + 1
        folder["d"][str(mid)] = {"__tuple__": True, "items": [parent, order]}
    return ("#15 and #18 use real conditional damage. Sima source controller checks living source and original current full core every hit, including new squad members; Gan marks each exact actively damaged enemy leader for 6s. Zhang actual three-point consumption keeps self +15 attack and grants melee vs enemy leaders +15%/6s (elite classification unresolved; leader-only candidate boundary, not approved design removal). Ma keeps -12 physical defense and marks exact target +15%/6s. Before each add, native iteration removes only the same Buff class + source + exact ability on this recipient, explicitly rebuilding one listener/window without relying on cover enums. Returned instance checks existence/source/exact ability before snapshots; LOSS unregisters only itself. Cover property pairs copy native 134266933 (1/True) and 134227930 (3/True); enum meaning, cross-source coexistence and engine event/removal ordering still need editor/combat verification.", extra)


def build(root: Path) -> tuple[dict[str, dict], list[dict]]:
    """Reread latest root, return only candidates and precise pending/review notes."""
    root = Path(root)
    candidates, reports = {}, []

    def group(issue, paths, fix, overlay=False):
        hashes = {}
        try:
            original = {}
            for path in paths:
                raw = (root / path).read_bytes()
                hashes[path] = hashlib.sha256(raw).hexdigest()
                original[path] = json.loads(raw, object_pairs_hook=_pairs)
            docs = {p: deepcopy(candidates.get(p, d) if overlay else d) for p, d in original.items()}
            result = fix(*(docs[p] for p in paths))
            explanation, extra = result if isinstance(result, tuple) else (result, {})
            changed = {p: d for p, d in docs.items() if d != original[p]}
            changed.update(extra)
            for p in extra:
                hashes[p] = None
            need(bool(changed), "no reviewed changes; may already be fixed")
        except (OSError, ValueError, TypeError, KeyError, IndexError, AttributeError) as exc:
            reports.append({"issue": issue, "status": "review_required", "paths": paths,
                            "source_sha256": hashes, "explanation": str(exc)})
        else:
            candidates.update(changed)
            reports.append({"issue": issue, "status": "candidate", "paths": list(changed),
                            "source_sha256": hashes, "explanation": explanation,
                            "validation": "static/offline candidate only; not editor/combat verified"})

    for aid in (134259902, 134226331, 134237178):
        group(f"18/{aid}", [f"ability/{aid}.json"], repair_recipients)
    group("21/core", ["modifier/134278238.json"], repair_ganning_core)
    group("21/burst", ["ability/134235613.json", "editor_table/abilityall/134235613.json"], repair_burst)
    group("26", ["ability/134253524.json"], repair_caoren_duration)
    group("27/threshold", ["ability/134267273.json"], repair_dianwei_threshold)
    group("27/duration", ["ability/134263365.json"], repair_dianwei_duration)
    for aid, maximum in ((134273095, 2), (134256160, 3)):
        group(f"29/{aid}", [f"ability/{aid}.json"], lambda d, m=maximum: repair_extras(d, m))
    def armor_fix(buff, prop, sun, ma, tai):
        callers = _armor_callers(root)
        need({f"ability/{i}.json" for i in FIXED_ARMOR_CALLERS} <= callers, "known armor caller disappeared")
        for d, number in ((sun, 10.0), (ma, 12.0), (tai, 12.0)):
            check_levels(d, {"减甲系数": number})
        return repair_armor(buff, prop) + f" Reverse-audited callers: {sorted(callers)}."
    group("19", ["modifier/134245346.json", "editor_table/abilityall/134219157.json",
                  "ability/134219157.json", "ability/134237178.json", "ability/134273833.json"], armor_fix)
    group("22", ["ability/134230908.json", "modifier/134266933.json",
                  "editor_table/abilityall/134230908.json", "editor_table/modifierall/134266933.json"], repair_eagle)
    conditional_paths = [*(f"ability/{i}.json" for i in CONDITIONAL_IDS),
                         FOLDERS, "zhlanguage.json", "tidindexinfo.json",
                         "modifier/134266933.json", "editor_table/modifierall/134227930.json"]
    def conditional_fix(*documents):
        # Run after recipients/armor; never regenerate those skills from a
        # second independent baseline and overwrite the preceding repairs.
        return repair_conditionals(dict(zip(conditional_paths, documents)), audit_support_ids(root))
    group("15", conditional_paths, conditional_fix, overlay=True)
    if reports[-1]["status"] == "candidate":
        reports[-1].update(allocatedID=[SOURCE_SUPPORT, TARGET_SUPPORT],
                           elite_scope="unresolved classification; leader-only candidate boundary, not approved design removal")
    expected, stale = {}, set()
    for report in reports:
        for path, sha in report.get("source_sha256", {}).items():
            if path in expected and expected[path] != sha:
                stale.add(path)
            expected[path] = sha
    for path, sha in expected.items():
        try:
            changed = ((root / path).exists() if sha is None else
                       hashlib.sha256((root / path).read_bytes()).hexdigest() != sha)
            if changed:
                stale.add(path)
        except OSError:
            stale.add(path)
    for report in reports:
        if report["status"] == "candidate" and stale.intersection(report["source_sha256"]):
            for path in report["paths"]:
                candidates.pop(path, None)
            report.update(status="review_required", explanation="Source changed during build; regenerate this atomic group.",
                          stale_paths=sorted(stale.intersection(report["source_sha256"])))
    return candidates, reports

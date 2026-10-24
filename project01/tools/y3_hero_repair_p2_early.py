"""Read-only P2 early-hero candidates (#17/32/33/34/35/38/46).

build(root) reads current Python JSON on every call; it never writes or reloads.
Evidence: the owned map3 ECAs, native 134218551 (ADD_MODIFIER expression),
134255234 (ITER_MODIFIER_DO), 134222326 (MODIFIER_CLASS_COMPARE), 134249476
(ABILITY_ENTITY_COMPARE), 134220754 (SET_BUFF_REMAINING), 134274812
(SET_BUFF_SHIELD), and the approved first-batch design/numeric documents.
Support evidence: 134230566 (damage listener/registration), 134242511
(ordinary-attack cast type 1), 134228356 (IS_ENEMY), 134277456
(GET_BUFF_SOURCE), and native folder/TID data.
Offline tests model only the explicitly listed AST subset, not engine support.
"""
from __future__ import annotations

from copy import deepcopy as clone
import hashlib
import json
from pathlib import Path

CAST, GAIN, LEVEL, LOSS = "893440004", "1959489540", "26066946", "225054724"
FILES = tuple(f"ability/{i}.json" for i in (
    134278144, 134232470, 134256840, 134280536, 134268037, 134233053,
    134275990, 134236877, 134266460, 134228529, 134221456,
)) + ("modifier/134228469.json",)
RATIO_FILES = {134266460, 134275990, 134228529, 134256840, 134221456}
SNAPSHOT = "P2_early_shield"
SHIELD = "P2_early_shield_instance"
FOUND = "P2_early_owned_found"
PASSIVE_OWNER = "P2_early_passive_owner"
ARCHER = "ability/134236877.json"
SUPPORT = 134286002
SUPPORT_ECA = f"modifier/{SUPPORT}.json"
SUPPORT_PROP = f"editor_table/modifierall/{SUPPORT}.json"
ARCHER_PROP = "editor_table/abilityall/134236877.json"
FOLDERS = "editor/folderinfo/folderinfo_modifier_all.json"
LANG = "zhlanguage.json"
TIDS = "tidindexinfo.json"
BONUS = "对小兵普攻增伤系数"
SOURCE = "P2_hz_original_source"
SOURCE_ABILITY = "P2_hz_original_ability"
ELIGIBLE = "P2_hz_eligible"
TIMER_LIVE = "P2_hz_timer_established"
LISTENER_LIVE = "P2_hz_listener_established"
LOSS_SEEN = "P2_hz_loss_seen"
SUPPORT_GAIN, SUPPORT_LOSS, SUPPORT_HURT = "1980923905", "1930846210", "450277379"
NAME_TID, DESC_TID = -2100286002, -2100286003
SUPPORT_INPUTS = (ARCHER, ARCHER_PROP, FOLDERS, LANG, TIDS,
                  "modifier/134230566.json", "editor_table/modifierall/134243369.json",
                  "editor_table/modifierall/134242511.json")
SOURCE_FILES = tuple(p for p in FILES if p != ARCHER) + SUPPORT_INPUTS
PAYLOAD_FILES = FILES + (SUPPORT_ECA, SUPPORT_PROP, ARCHER_PROP, FOLDERS, LANG, TIDS)
ISSUES = {134278144: [17], 134232470: [17], 134256840: [17, 46],
          134280536: [32], 134268037: [33], 134233053: [34],
          134275990: [35, 46], 134236877: [38], 134266460: [46],
          134228529: [46], 134221456: [46], 134228469: [32]}


class ReviewRequired(ValueError):
    """The root differs from the reviewed native AST."""


def need(ok, message):
    if not ok:
        raise ReviewRequired(message)


def walk(value, active=False):
    if isinstance(value, dict):
        if active and value.get("enable") is False:
            return
        yield value
        for key, child in value.items():
            if active and key == "op_arg":
                for arg, enabled in zip(child, value.get("op_arg_enable", [])):
                    if enabled:
                        yield from walk(arg, active)
            elif key != "op_arg_enable":
                yield from walk(child, active)
    elif isinstance(value, list):
        for child in value:
            yield from walk(child, active)


def ex(kind, subtype, *args):
    return dict(arg_type=kind, sub_type=subtype, args_list=list(args))


def lit(value, kind=100000):
    return ex(kind, 1, value)


def unit(subtype="ABILITY_OWNER"):
    return ex(100006, subtype)


def ability():
    return ex(100014, "CUR_ABILITY")


def kv(key, entity=None, kind=100000, subtype="GET_FLOAT_KV"):
    return ex(kind, subtype, ability() if entity is None else clone(entity), lit(key, 100003))


def lookup(owner, resource):
    return ex(100076, "GET_LAST_MODIFIER_INSTANCE", clone(owner), lit(resource, 100046))


def has(owner, resource):
    return ex(100001, "UNIT_HAS_MODIFIER", clone(owner), lit(resource, 100046))


def math(left, operator, right, integer=False):
    return ex(100002 if integer else 100000,
              "MATH_OPERATION" if integer else "ARITHMETIC_OPERATION",
              clone(left), lit(operator, 100016 if integer else 100017), clone(right))


def hpmax(owner):
    return ex(100000, "GET_UNIT_ATTR", clone(owner), lit("ATTR_RESULT", 100301), lit("hp_max", 100042))


def target():
    return ex(100006, 11, {"__tuple__": True, "items": ["UNIT_ENTITY", "目标单位", "actor"]})


def one(tree, predicate, label):
    found = [n for n in walk(tree, True) if predicate(n)]
    need(len(found) == 1, f"{label}: expected one active node, found {len(found)}")
    return found[0]


def action(tree, kind, eid=None):
    return one(tree, lambda n: n.get("action_type") == kind and
               (eid is None or n.get("element_id") == eid), f"{kind}/{eid}")


def trigger(doc, tid, event=None):
    t = doc["trigger_dict"][tid]
    if event:
        need(any(e.get("event_type") == event and e.get("enable") is not False
                 for e in t["event"]), f"{tid}: expected {event}")
    return t


class Nodes:
    def __init__(self, doc, resource):
        self.doc = doc
        self.used = {n["element_id"] for n in walk(doc) if "element_id" in n}
        self.serial = resource * 10000000 + 9200000

    def node(self, field, kind, *args):
        self.serial += 1
        while self.serial in self.used:
            self.serial += 1
        self.used.add(self.serial)
        n = {field: kind, "args_list": list(args), "element_id": self.serial, "enable": True}
        if field == "action_type":
            n["bp"] = False
        return n

    def a(self, kind, *args):
        return self.node("action_type", kind, *args)

    def c(self, kind, *args):
        return self.node("condition_type", kind, *args)

    def cmp(self, left, op, right, kind="FLOAT_COMPARE"):
        return self.c(kind, clone(left), lit(op, 100015 if kind == "FLOAT_COMPARE" else 100035), clone(right))

    def branch(self, checks, yes, no=()):
        return self.a("IF_THEN_ELSE", ex(100021, 1, *checks), ex(100022, 1, *yes), ex(100022, 1, *no))

    def exists(self, obj, yes):
        need(obj["arg_type"] in (100006, 100014), "unverified existence overload")
        return self.branch([self.c("TYPE_IS_EXIST", clone(obj))], yes)

    def yes(self, expression):
        return self.cmp(expression, "==", lit(True, 100001), "BOOL_COMPARE")

    def set(self, ref, value):
        if ref["arg_type"] in (100000, 100001, 100002, 100014):
            dest = ex(100030, 1, clone(ref["args_list"][0]))
        else:
            dest = clone(ref)
        return self.a("SET_VARIABLE", dest, clone(value))

    def fresh(self, value):
        result = clone(value)
        for node in walk(result):
            if "element_id" in node:
                node["element_id"] = self.node("action_type", "SET_VARIABLE")["element_id"]
        return result

    def actor_unit(self, name):
        need(name not in self.doc["variable_length_dict"], "actor variable collision: " + name)
        self.doc["variable_dict"].setdefault("UNIT_ENTITY", {})[name] = 0
        self.doc["variable_length_dict"][name] = 0
        self.doc["variable_group_info"].append({"__tuple__": True, "items": [name, name]})
        return ex(100006, 11, {"__tuple__": True, "items": ["UNIT_ENTITY", name, "actor"]})

    def var(self, tid, name, kind="FLOAT"):
        types = {"FLOAT": (100000, 2, 0.0), "INTEGER": (100002, 6, 0),
                 "UNIT_ENTITY": (100006, 11, 0), "MODIFIER_ENTITY": (100076, 11, None)}
        typ, subtype, initial = types[kind]
        decl = self.doc["local_variable"][tid]
        t = self.doc["trigger_dict"][tid]
        if name not in decl["variable_length_dict"]:
            decl["variable_dict"].setdefault(kind, {})[name] = initial
            decl["variable_length_dict"][name] = 0
            t["var_data"][0].setdefault(kind, {})[name] = initial
            t["var_data"][1][name] = 0
            t["var_data"][2].append(name)
        else:
            need(name in decl["variable_dict"].get(kind, {}), "variable type collision")
        ref = [kind, name, "local"]
        return ex(typ, subtype, {"__tuple__": True, "items": ref})


def _level_add(doc, n, key, value):
    """Add a new numeric entrance without rewriting any existing level data."""
    switch = action(trigger(doc, LEVEL, "ABILITY_LEVEL_CHANGED")["action"], "SWITCH")
    cases = switch["args_list"][1]["args_list"]
    need([c["args_list"][0]["args_list"][0] for c in cases] == [1, 2, 3, 4, 5], "levels must be 1..5")
    for c in cases:
        body = c["args_list"][1]["args_list"]
        need(not any(x.get("action_type") == "SET_ENTITY_KV" and x["args_list"][1] == lit(key, 100003)
                     for x in walk(body, True)), "numeric entrance already exists: " + key)
        body.insert(0, n.a("SET_ENTITY_KV", ability(), lit(key, 100003), lit(value)))
    trigger(doc, GAIN, "ABILITY_OBTAIN")["action"].insert(
        0, n.a("SET_ENTITY_KV", ability(), lit(key, 100003), lit(value)))


def _created(n, add, ref):
    expr = ex(100076, "ADD_MODIFIER", *clone(add["args_list"]))
    for key in ("op_arg", "op_arg_enable"):
        expr[key] = clone(add[key])
    add["action_type"] = "SET_VARIABLE"
    add["args_list"] = [clone(ref), expr]
    add.pop("op_arg")
    add.pop("op_arg_enable")


def _shield_cast(doc, n, oid):
    cast = trigger(doc, CAST, "ABILITY_SP_END")
    snapshot = n.var(CAST, SNAPSHOT)
    saved = n.var(CAST, SHIELD, "MODIFIER_ENTITY")
    writes = [x for x in walk(cast["action"], True) if x.get("action_type") == "SET_ENTITY_KV"
              and x["args_list"][0] == ability() and x["args_list"][1] == lit("护盾值", 100003)]
    expected = {134278144: [893440004974199, 893440004974202],
                134232470: [893440004974141, 893440004974124],
                134256840: [893440004974141, 893440004974151]}[oid]
    need([x["element_id"] for x in writes] == expected, "shield mutation layout changed")
    boost, restore = writes
    # Rewrite only the boosted calculation; the base KV is never a cast scratchpad.
    boost["action_type"] = "SET_VARIABLE"
    boost["args_list"] = [ex(100030, 1, clone(snapshot["args_list"][0])), clone(boost["args_list"][2])]
    for node in walk(boost["args_list"][1]):
        if node == kv("护盾值"):
            node.clear()
            node.update(clone(snapshot))
    def remove(items):
        if isinstance(items, list):
            items[:] = [x for x in items if x is not restore]
            for x in items:
                remove(x)
        elif isinstance(items, dict):
            for v in items.values():
                remove(v)
    remove(cast["action"])
    if oid == 134278144:
        initial = action(cast["action"], "SET_VARIABLE", 893440004974193)
        # Original named local was the base snapshot; use the unified snapshot.
        old = ex(100000, 2, {"__tuple__": True, "items": ["FLOAT", "初始护盾值", "local"]})
        for x in walk(boost):
            if x == old:
                x.clear()
                x.update(clone(snapshot))
        initial["args_list"] = [ex(100030, 1, clone(snapshot["args_list"][0])), kv("护盾值")]
    else:
        cast["action"].insert(0, n.set(snapshot, kv("护盾值")))
    resource = {134278144: 134224490, 134232470: 134259960, 134256840: 134264323}[oid]
    boost_branch = one(cast["action"], lambda x: x.get("action_type") == "IF_THEN_ELSE" and
                       any(y is boost for y in walk(x)), "shield boost branch")
    # has-buff is an ordered gate before GET_MOD_STACK, not a pretend short circuit.
    index = cast["action"].index(boost_branch)
    cast["action"][index] = n.branch([n.yes(has(unit(), resource))], [boost_branch])
    add = one(cast["action"], lambda x: x.get("action_type") == "ADD_MODIFIER"
              and x["args_list"][1] == lit(134274812, 100046), "shield creation")
    owner = clone(add["args_list"][0])
    _created(n, add, saved)
    at = cast["action"].index(add)
    cast["action"].insert(at + 1, n.branch([n.yes(has(owner, 134274812))], [
        n.branch([n.cmp(saved, "==", lookup(owner, 134274812), "MODIFIER_COMPARE")], [
            n.a("SET_ENTITY_KV", clone(saved), lit("护盾值", 100003), clone(snapshot)),
            n.a("SET_BUFF_SHIELD", clone(saved), clone(snapshot))])]))
    return "Per-cast base/boost snapshot; set only returned shield instance, no base KV writes; existing level values retained."


def _piercing(doc, n):
    _level_add(doc, n, "额外系数", 0.4)
    boosted = action(trigger(doc, CAST)["action"], "SET_VARIABLE", 893440004974076)
    outer = boosted["args_list"][1]
    need(outer.get("sub_type") == "ARITHMETIC_OPERATION" and outer["args_list"][1] == lit("+", 100017), "piercing formula drift")
    product, _, extra = outer["args_list"]
    need(extra == kv("额外系数") and product["args_list"][2] == kv("伤害系数"), "piercing coefficients drift")
    boosted["args_list"][1] = math(product["args_list"][0], "*", math(kv("伤害系数"), "+", extra))
    return "Extra=.40 attack from approved 125%+40% design; preserve current base level values, use attack*(base+extra); collision body untouched."


def _sweep(doc, n):
    cast = trigger(doc, CAST)
    pick = action(cast["action"], "PICK_UNIT_DO_ACTION")
    body = pick["args_list"][1]["args_list"]
    boost = action(body, "IF_THEN_ELSE", 893440004974860)
    clear = action(boost, "ADD_BUFF_STACK")
    debuff = action(boost, "ADD_MODIFIER")
    need(clear["args_list"][1] == lit(-1, 100002), "sweep cost changed")
    flag = n.var(CAST, "P2_early_sweep_boost", "INTEGER")
    first = n.var(CAST, "P2_early_sweep_started", "INTEGER")
    body.remove(boost)
    resource = 134224490
    commit = n.branch([n.cmp(first, "==", lit(0, 100002))], [
        n.set(first, lit(1, 100002)),
        n.branch([n.yes(has(unit(), resource))], [n.branch(clone(boost["args_list"][0]["args_list"]), [
            n.set(flag, lit(1, 100002)), clear])])])
    body.insert(0, commit)
    body.append(n.branch([n.cmp(flag, "==", lit(1, 100002))], [debuff]))
    # Keep native enemy/shape/quantity filters, then validate each victim before cost.
    selected = unit("FOR_EACH_SELECTED_UNIT")
    need(body[1].get("action_type") == "APPLY_DAMAGE", "sweep damage order changed")
    after_damage = body[2:]
    body[2:] = [n.exists(ability(), [n.exists(unit(), [n.exists(selected, [
        n.branch([n.c("IS_UNIT_ALIVE", clone(selected))], after_damage)])])])]
    pick["args_list"][1]["args_list"] = [n.exists(selected, [
        n.branch([n.c("IS_UNIT_ALIVE", clone(selected))], body[:])])]
    at = cast["action"].index(pick)
    cast["action"][at:at] = [n.set(flag, lit(0, 100002)), n.set(first, lit(0, 100002))]
    return "First valid victim consumes once before damage; one cast flag boosts every selected victim (native max-three/enemy filters retained)."


def _owned(n, owner, resource, actions):
    buff = ex(100076, "FOR_EACH_SELECTED_MODIFIER")
    related = ex(100014, "RELATED_ABILITY_MODIFIER", clone(buff))
    return n.a("ITER_MODIFIER_DO", clone(owner), ex(100022, 1,
        n.branch([n.cmp(ex(100046, "GET_MODIFIER_ENTITY_METATYPE", clone(buff)), "==", lit(resource, 100046), "MODIFIER_CLASS_COMPARE")], [
            n.branch([n.cmp(related, "==", ability(), "ABILITY_ENTITY_COMPARE")], actions)])))


def _refresh_owned(n, tid, owner, add, seconds=None, refresh=()):
    resource = add["args_list"][1]["args_list"][0]
    found = n.var(tid, FOUND, "INTEGER")
    payload = [n.set(found, lit(1, 100002)), *refresh]
    if seconds is not None:
        payload.append(n.a("SET_BUFF_REMAINING", ex(100076, "FOR_EACH_SELECTED_MODIFIER"), lit(seconds)))
    absent = n.c("BOOL_NOT", has(owner, resource))
    return [n.set(found, lit(0, 100002)), _owned(n, owner, resource, payload),
            n.branch([n.cmp(found, "==", lit(0, 100002))], [n.branch([absent], [add])])]


def _courage(doc, n):
    t = trigger(doc, "58232837", "GLOBAL_MODIFIER_EVENT")
    need(len(t["action"]) == 2, "courage branches changed")
    saved_owner = n.actor_unit(PASSIVE_OWNER)
    trigger(doc, GAIN)["action"].insert(0, n.set(saved_owner, unit()))
    output = []
    for branch in t["action"]:
        phase, absent = branch["args_list"][0]["args_list"]
        add = branch["args_list"][1]["args_list"][0]
        need(absent.get("condition_type") == "BOOL_NOT" and add.get("action_type") == "ADD_MODIFIER", "courage shape drift")
        resource = add["args_list"][1]["args_list"][0]
        output.append(n.branch([clone(phase)], _refresh_owned(n, "58232837", unit(), add, 4.0)))
        trigger(doc, LOSS)["action"].insert(0, n.exists(saved_owner, [
            _owned(n, saved_owner, resource,
                   [n.a("REMOVE_BUFF_INS", ex(100076, "FOR_EACH_SELECTED_MODIFIER"))])]))
    t["action"] = [n.exists(unit(), output)]
    return "Refresh own associated attack-speed/dodge instances to 4s; never remove/replace foreign instances of the shared resources."


def _ratio(doc, n, oid):
    tid = "58232837" if oid == 134221456 else GAIN
    t = trigger(doc, tid)
    pick = action(t["action"], "PICK_UNIT_DO_ACTION", 1959489540974145)
    select = action(pick, "IF_THEN_ELSE", 1959489540974150)
    compare = one(select, lambda x: x.get("element_id") == 1959489540974200, "HP comparison")
    left, op, right = compare["args_list"]
    need(left == ex(100000, "GET_HP_CUR", unit("FOR_EACH_SELECTED_UNIT")) and
         right == ex(100000, "GET_HP_CUR", target()) and op == lit("<", 100015), "HP operands changed")
    compare["args_list"][0] = math(left, "/", hpmax(unit("FOR_EACH_SELECTED_UNIT")))
    compare["args_list"][2] = math(right, "/", hpmax(target()))
    # The old selection branch is reused, with safe recovery from a stale target.
    fallback = n.fresh(select["args_list"][1]["args_list"])
    existing = select["args_list"][2]["args_list"]
    select["args_list"][2]["args_list"] = [n.branch([n.c("TYPE_IS_EXIST", target())], [
        n.branch([n.c("IS_UNIT_ALIVE", target())], [
            n.branch([n.cmp(hpmax(target()), ">", lit(0.0))], existing, n.fresh(fallback))], n.fresh(fallback))], fallback)]
    body = pick["args_list"][1]["args_list"]
    selected = unit("FOR_EACH_SELECTED_UNIT")
    pick["args_list"][1]["args_list"] = [n.exists(selected, [n.branch([n.c("IS_UNIT_ALIVE", clone(selected))], [
        n.branch([n.cmp(hpmax(selected), ">", lit(0.0))], body[:])])])]
    # Clear the actor result at each fresh search, not at each victim.
    def insert(items):
        if isinstance(items, list):
            for index, item in enumerate(items[:]):
                if item is pick:
                    items.insert(index, n.set(target(), unit("NONE_UNIT")))
                    return True
                if insert(item):
                    return True
        elif isinstance(items, dict):
            for child in items.values():
                if insert(child):
                    return True
        return False
    need(insert(t["action"]), "search container not found")
    return "HP/maxHP selection; ordered existence/alive/maxHP>0 gates, reset stale result; original team/tag/threshold filters retained."


def _rescue(doc, n):
    _level_add(doc, n, "伤害系数", 2.6)
    cast = trigger(doc, CAST)
    mover = action(cast["action"], "CREATE_STRAIGHT_MOVER")
    ally = n.var(CAST, "P2_early_rescue_ally", "UNIT_ENTITY")
    enemy = n.var(CAST, "P2_early_rescue_enemy", "UNIT_ENTITY")
    at = cast["action"].index(mover)
    cast["action"].insert(at, n.set(ally, target()))
    for x in walk(mover):
        if x == target():
            x.clear()
            x.update(clone(ally))
    # Arrival callback is native argument 5; old taunt/collision data stays intact.
    arrival = mover["args_list"][5]["args_list"]
    need(mover["args_list"][5]["arg_type"] == 100022, "mover arrival slot changed")
    shield_branch = action(arrival, "IF_THEN_ELSE", 893440004974815)
    # Split resource presence from its stack read, preserving original cost/shield.
    conds = shield_branch["args_list"][0]["args_list"]
    need(len(conds) == 2, "rescue shield conditions changed")
    shield_branch["args_list"][0]["args_list"] = [conds[1]]
    resource_ref = conds[1]["args_list"][0]["args_list"][0]
    need(resource_ref == kv("能力循环机制", unit(), 100076, "GET_MODIFIER_ENTITY_KV"),
         "rescue resource stack source changed")
    # Presence was checked for this exact core, so do not use a stale generic KV
    # handle for either the stack test or the corresponding one-stack cost.
    conds[1]["args_list"][0]["args_list"][0] = lookup(unit(), 134246678)
    cost = action(shield_branch, "ADD_BUFF_STACK")
    need(cost["args_list"][0] == resource_ref and cost["args_list"][1] == lit(-1, 100002),
         "rescue one-stack cost changed")
    cost["args_list"][0] = lookup(unit(), 134246678)
    shield_at = arrival.index(shield_branch)
    arrival[shield_at] = n.branch([conds[0]], [shield_branch])
    ai = ex(100006, "GET_UNIT_AI_BATTLE_TARGET_UNIT", clone(ally))
    taunt = action(arrival, "IF_THEN_ELSE", 893440004974830)
    taunt_checks = taunt["args_list"][0]["args_list"]
    need([c.get("condition_type") for c in taunt_checks] == ["TYPE_IS_EXIST", "IS_UNIT_ALIVE"], "rescue taunt guards changed")
    taunt["args_list"][0]["args_list"] = [taunt_checks[1]]
    arrival[arrival.index(taunt)] = n.exists(ai, [taunt])
    attack = ex(100000, "GET_UNIT_ATTR", unit(), lit("ATTR_RESULT", 100301), lit("attack_phy", 100042))
    damage = n.a("APPLY_DAMAGE", unit(), ability(), clone(enemy), lit(0, 100064), math(attack, "*", kv("伤害系数")), lit(True, 100001))
    damage["op_arg"] = [lit(True, 100001)] * 3 + [None] * 6
    damage["op_arg_enable"] = [False] * 9
    # Only the allied leader's current enemy, after movement, may receive damage.
    hostile = n.c("BOOL_NOT", ex(100001, "IS_ALLY", unit(), clone(enemy)))
    after_damage = n.exists(ability(), [n.exists(unit(), [n.exists(ally, [
        n.branch([n.c("IS_UNIT_ALIVE", clone(ally))], arrival[:])])])])
    arrival[:] = [n.set(enemy, ai),
                  n.exists(enemy, [n.branch([n.c("IS_UNIT_ALIVE", clone(enemy)), hostile], [damage])]), after_damage]
    mover["args_list"][5]["args_list"] = [n.exists(ability(), [n.exists(unit(), [
        n.exists(ally, [n.branch([n.c("IS_UNIT_ALIVE", clone(ally)),
                                n.yes(ex(100001, "IS_ALLY", unit(), clone(ally)))], arrival[:])])])])]
    at = cast["action"].index(mover)
    cast["action"][at] = n.exists(ally, [n.branch([n.c("IS_UNIT_ALIVE", clone(ally)),
                                                n.yes(ex(100001, "IS_ALLY", unit(), clone(ally)))], [
        n.exists(ai, [n.branch([n.c("IS_UNIT_ALIVE", clone(ai)),
                              n.c("BOOL_NOT", ex(100001, "IS_ALLY", unit(), clone(ai)))], [mover])])])])
    # Do not spend an automatic cast when the lowest-HP ally has no legal enemy.
    gain = trigger(doc, GAIN)
    dispatch = action(gain["action"], "IF_THEN_ELSE", 1959489540974075)
    container = one(gain["action"], lambda x: x.get("arg_type") == 100022 and
                    any(item is dispatch for item in x.get("args_list", [])), "rescue auto dispatch parent")
    current_ai = ex(100006, "GET_UNIT_AI_BATTLE_TARGET_UNIT", target())
    gate = n.exists(target(), [n.branch([n.c("IS_UNIT_ALIVE", target()),
                                        n.yes(ex(100001, "IS_ALLY", unit(), target()))], [
        n.exists(current_ai, [n.branch([n.c("IS_UNIT_ALIVE", clone(current_ai)),
                                       n.c("BOOL_NOT", ex(100001, "IS_ALLY", unit(), clone(current_ai)))], [dispatch])])])])
    container["args_list"][container["args_list"].index(dispatch)] = gate
    return "Arrival damages rescued leader's current valid living enemy at attack*2.6; ally is cast-local; existing shield cost/levels and taunt retained."


def _archers(doc, n):
    gain = trigger(doc, GAIN)
    saved_owner = n.actor_unit(PASSIVE_OWNER)
    _level_add(doc, n, BONUS, 0.18)
    gain["action"].insert(1, n.a("SET_ENTITY_KV", ability(), lit("攻速提升", 100003), lit(15.0)))
    gain["action"].insert(0, n.set(saved_owner, unit()))
    setters = [x for x in walk(trigger(doc, LEVEL)["action"], True)
               if x.get("action_type") == "SET_ENTITY_KV" and x["args_list"][1] == lit("攻速提升", 100003)]
    need([x["args_list"][2] for x in setters] == [lit(float(i)) for i in (5, 10, 15, 20, 25)],
         "archer attack-speed levels changed")
    for setter in setters:
        setter["args_list"][2] = lit(15.0)
    timer = action(gain["action"], "RUN_LOOP_TIMER")
    pick = action(timer, "PICK_UNIT_DO_ACTION")
    full_branch = action(pick, "IF_THEN_ELSE", 1959489540000185)
    add = clone(action(full_branch, "ADD_MODIFIER"))
    need(add["args_list"][1] == lit(134243369, 100046) and add["op_arg_enable"][:2] == [True, True],
         "archer source/ability association changed")
    add["args_list"][1] = lit(SUPPORT, 100046)
    selected = unit("FOR_EACH_SELECTED_UNIT")
    cleanup = [_owned(n, selected, resource, [n.a("REMOVE_BUFF_INS", ex(100076, "FOR_EACH_SELECTED_MODIFIER"))])
               for resource in (134243369, 134254769)]
    body = _refresh_owned(n, GAIN, selected, add)
    pick["args_list"][1]["args_list"] = [n.exists(selected, [
        *cleanup, n.branch(_soldier(n, selected, ranged=True) + [n.c("IS_UNIT_ALIVE", clone(selected)),
            n.yes(ex(100001, "IS_ALLY", unit(), clone(selected)))], body)])]
    refresh = [n.exists(ability(), [n.exists(unit(), [
        n.branch([_leader(n, unit()), n.c("IS_UNIT_ALIVE", unit())], [pick])])])]
    timer["args_list"][3]["args_list"] = refresh
    custom = trigger(doc, "1051000836", "RECEIVE_CUSTOM_EVENT")
    custom["action"] = n.fresh(refresh)
    custom["var_data"] = clone(gain["var_data"])
    doc["local_variable"]["1051000836"] = clone(doc["local_variable"][GAIN])
    gain["condition"] = [_leader(n, unit())]
    # An immediate refresh covers obtain; the native stage listener and 1s timer
    # cover wave changes/reinforcements. Full stacks are checked at damage time.
    gain["action"].extend(n.fresh(refresh))
    loss = trigger(doc, LOSS)
    remove = [_owned(n, selected, resource, [n.a("REMOVE_BUFF_INS", ex(100076, "FOR_EACH_SELECTED_MODIFIER"))])
              for resource in (SUPPORT, 134243369, 134254769)]
    loss["action"].insert(0, n.exists(saved_owner, [n.a("PICK_UNIT_DO_ACTION",
        kv("带领小队", saved_owner, 100026, "GET_UNIT_GROUP_KV"),
        ex(100022, 1, n.exists(selected, remove)))]))
    return "Source-owned ranged soldiers receive 15% attack speed; dedicated Buff checks original source, current squad and 3 visible stacks on each enemy-soldier normal hit for +18% damage; no targeting changes."


def _leader(n, owner):
    return n.c("OR", ex(100021, 1, *(n.c("UNIT_HAS_TAG", clone(owner), lit(tag, 100003))
                                     for tag in ("仆从伙伴", "阵型队长"))))


def _soldier(n, owner, ranged=False):
    checks = [n.c("BOOL_NOT", ex(100001, "UNIT_HAS_TAG", clone(owner), lit(tag, 100003)))
              for tag in ("仆从伙伴", "阵型队长")]
    if ranged:
        checks.append(n.c("UNIT_HAS_TAG", clone(owner), lit("远程普攻", 100003)))
    return checks


def _actor(doc, kind, name, arg_type, initial):
    need(name not in doc["variable_length_dict"], "actor variable collision: " + name)
    doc["variable_dict"].setdefault(kind, {})[name] = initial
    doc["variable_length_dict"][name] = 0
    doc["variable_group_info"].append({"__tuple__": True, "items": [name, name]})
    return ex(arg_type, 2 if kind == "ABILITY" else "VARIABLE",
              {"__tuple__": True, "items": [kind, name, "actor"]})


def _support(native, timer_template):
    doc = clone(native)
    n = Nodes(doc, SUPPORT)
    current = ex(100076, "CUR_MODIFIER")
    owner = unit("MODIFIER_OWNER")
    related = ex(100014, "RELATED_ABILITY_MODIFIER", clone(current))
    source = n.actor_unit(SOURCE)
    skill = _actor(doc, "ABILITY", SOURCE_ABILITY, 100014, None)
    timer_ref = _actor(doc, "NEW_TIMER", "P2_hz_validity_timer", 100181, -1)
    timer_live = _actor(doc, "BOOLEAN", TIMER_LIVE, 100001, False)
    listener_live = _actor(doc, "BOOLEAN", LISTENER_LIVE, 100001, False)
    loss_seen = _actor(doc, "BOOLEAN", LOSS_SEEN, 100001, False)
    for t in doc["trigger_dict"].values():
        t["group_id"] = SUPPORT
    group = doc["trigger_group_info"][0]
    group["key"], group["name"] = SUPPORT, str(SUPPORT)

    def eligibility(tid, yes, no=()):
        flag = n.var(tid, ELIGIBLE, "INTEGER")
        member = unit("FOR_EACH_SELECTED_UNIT")
        check_member = n.a("PICK_UNIT_DO_ACTION", kv("带领小队", source, 100026, "GET_UNIT_GROUP_KV"),
            ex(100022, 1, n.branch([n.cmp(member, "==", owner, "UNIT_COMPARE")],
                                   [n.set(flag, lit(1, 100002))])))
        validate = n.exists(source, [n.exists(skill, [n.exists(owner, [n.branch([
            n.c("IS_UNIT_ALIVE", clone(source)), n.c("IS_UNIT_ALIVE", clone(owner)), _leader(n, source),
            n.cmp(ex(100006, "GET_BUFF_SOURCE", clone(current)), "==", source, "UNIT_COMPARE"),
            n.cmp(related, "==", skill, "ABILITY_ENTITY_COMPARE"),
            n.cmp(ex(100006, "GET_ABILITY_OWNER", clone(skill)), "==", source, "UNIT_COMPARE"),
            n.yes(ex(100001, "IS_ALLY", clone(source), clone(owner))), *_soldier(n, owner, ranged=True)
        ], [check_member])])])])
        return [n.set(flag, lit(0, 100002)), validate,
                n.branch([n.cmp(flag, "==", lit(1, 100002))], yes, no)]

    gain = trigger(doc, SUPPORT_GAIN, "OBTAIN_MODIFIER")
    loss = trigger(doc, SUPPORT_LOSS, "LOSS_MODIFIER")
    hurt = trigger(doc, SUPPORT_HURT, "SPECIAL_UNIT_EVENT")
    need(hurt["event"][0]["args_list"] == [owner, lit("ET_UNIT_HURT_OTHER", 100007)],
         "support outgoing damage event drift")
    remove = lambda: n.a("REMOVE_BUFF_INS", clone(current))
    timer = n.fresh(timer_template)
    timer["args_list"][0] = clone(timer_ref)
    timer["args_list"][3]["args_list"] = eligibility(SUPPORT_GAIN, [], [remove()])
    # A first timer callback may synchronously remove this Buff before RUN_LOOP
    # returns its handle. LOSS records that fact; the continuation deletes the
    # now-established timer instead of re-arming a lost instance.
    after_timer = n.branch([n.yes(loss_seen)], [n.a("DELETE_TIMER", clone(timer_ref))],
                          [n.set(timer_live, lit(True, 100001))])
    gain["action"] = [n.set(source, ex(100006, "GET_BUFF_SOURCE", clone(current))), n.set(skill, related),
        *eligibility(SUPPORT_GAIN, [
            n.a("ADD_MODIFIER_OWNER_ATTR", clone(current), lit("attack_speed", 100042),
                lit("ATTR_ALL_RATIO", 100300), kv("攻速提升", skill)), int(SUPPORT_HURT),
            n.set(listener_live, lit(True, 100001)), timer, after_timer], [remove()])]
    unregister = clone(action(loss["action"], "UNREG_TRIGGER"))
    loss["action"] = [n.set(loss_seen, lit(True, 100001)),
        n.branch([n.yes(listener_live)], [n.set(listener_live, lit(False, 100001)), unregister]),
        n.branch([n.yes(timer_live)], [n.set(timer_live, lit(False, 100001)), n.a("DELETE_TIMER", clone(timer_ref))]),
        n.a("CLEAR_MODIFIER_OWNER_ATTR", clone(current))]
    victim, attacker, damage_ability = unit("DAMAGE_TARGET_UNIT"), unit("DAMAGE_SOURCE_UNIT"), ex(100014, "DAMAGE_ABILITY")
    core = lookup(source, 134242511)
    # Presence is a separate stage before either core stack read. No stale core
    # or full-state snapshot can authorize a later hit after consumption/removal.
    increase = n.a("SET_CUR_DAMAGE", math(ex(100000, "HURT_DAMAGE"), "*", math(lit(1.0), "+", kv(BONUS, skill))))
    damage = n.exists(attacker, [n.exists(victim, [n.exists(damage_ability, [n.branch([
        n.cmp(attacker, "==", owner, "UNIT_COMPARE"), n.c("IS_UNIT_ALIVE", clone(victim)),
        n.c("IS_ENEMY", clone(victim), clone(owner)), *_soldier(n, victim),
        n.cmp(ex(100219, "GET_ABILITY_CAST_TYPE", clone(damage_ability)), "==", lit(1, 100219), "ABILITY_CAST_TYPE_COMPARE")
    ], [n.branch([n.yes(has(source, 134242511))], [n.branch([
        n.cmp(ex(100002, "GET_MOD_STACK", clone(core)), ">=", lit(4, 100002)),
        n.cmp(ex(100002, "GET_MOD_STACK_MAX", clone(core)), "==", lit(4, 100002))], [increase])])])])])])
    hurt["condition"] = []
    hurt["action"] = eligibility(SUPPORT_HURT, [damage], [remove()])
    # Cloned template IDs are replaced, including the native registration node.
    return n.fresh(doc)


def _archer_bundle(root):
    """All-or-nothing resource/registration payload, always read from this root."""
    source, hashes = {}, {}
    for relative in SUPPORT_INPUTS:
        raw = (root / relative).read_bytes()
        source[relative] = json.loads(raw, object_pairs_hook=_unique)
        hashes[relative] = hashlib.sha256(raw).hexdigest()
    need(not (root / SUPPORT_ECA).exists() and not (root / SUPPORT_PROP).exists(), "support resource ID collision")
    need(not any((root / "editor_table").glob(f"*/{SUPPORT}.json")), "support object ID collision")
    folders, language, tids = (clone(source[p]) for p in (FOLDERS, LANG, TIDS))
    need(str(SUPPORT) not in folders["d"], "support folder ID collision")
    for tid in (NAME_TID, DESC_TID):
        need(str(tid) not in language and str(tid) not in tids, "support language TID collision")
    need(source["editor_table/modifierall/134242511.json"]["layer_max"] == 4, "xushi visible/internal stack mapping drift")
    doc = clone(source[ARCHER])
    timer = clone(action(trigger(doc, GAIN)["action"], "RUN_LOOP_TIMER"))
    message = _archers(doc, Nodes(doc, 134236877))
    support = _support(source["modifier/134230566.json"], timer)
    prop = clone(source["editor_table/modifierall/134243369.json"])
    prop.update(_ref_=SUPPORT, key=SUPPORT, uid=str(SUPPORT), name=NAME_TID,
                desc=DESC_TID, description=DESC_TID, suffix="黄忠-远程小兵", influence_rng=0,
                is_influence_self=True, show_on_ui=False, modifier_icon=source[ARCHER_PROP]["ability_icon"])
    ability_prop = clone(source[ARCHER_PROP])
    entry = clone(ability_prop["kv"].pop("加攻系数"))
    entry.update(key=BONUS, value=0.18)
    ability_prop["kv"][BONUS] = entry
    ability_prop["kv"]["攻速提升"]["value"] = 15.0
    description = "小队远程小兵攻速+15%；黄忠持有3层蓄势时，其远程小兵对敌方小兵的普通攻击伤害+18%，不改变攻击目标。"
    language[str(ability_prop["desc"])] = "<html><body><p>" + description + "</p></body></html>"
    language[str(NAME_TID)] = "黄忠-蓄势远程小兵"
    language[str(DESC_TID)] = description
    for tid, field in ((NAME_TID, "name"), (DESC_TID, "desc")):
        tids[str(tid)] = dict(editor_type="modifier_all", index_type="object_editor", item_key=SUPPORT, prop_key=field)
    parent = folders["d"]["134242511"]["items"][0]
    order = max(x["items"][1] for x in folders["d"].values() if x["items"][0] == parent) + 1
    folders["d"][str(SUPPORT)] = {"__tuple__": True, "items": [parent, order]}
    return {ARCHER: doc, SUPPORT_ECA: support, SUPPORT_PROP: prop, ARCHER_PROP: ability_prop,
            FOLDERS: folders, LANG: language, TIDS: tids}, hashes, message


def _regen(doc, n):
    gain = one(doc["trigger_dict"], lambda x: any(e.get("event_type") == "OBTAIN_MODIFIER" for e in x.get("event", [])), "regen gain")
    related = ex(100014, "RELATED_ABILITY_MODIFIER", ex(100076, "CUR_MODIFIER"))
    current = ex(100076, "CUR_MODIFIER")
    setter = n.a("SET_ENTITY_KV", current, lit("每次回血", 100003), kv("每次回血", related))
    gain["action"][0:0] = [n.a("SET_ENTITY_KV", clone(current), lit("每次回血", 100003), lit(0.0)),
                           n.exists(related, [setter])]
    return "Snapshot 每次回血 from actual associated caller 134221456 before starting timer; missing related ability yields zero, never 每次伤害."


def _unique(pairs):
    result = {}
    for key, value in pairs:
        need(key not in result, "duplicate JSON key: " + key)
        result[key] = value
    return result


def build(root: Path) -> tuple[dict[str, dict], list[dict]]:
    """Candidate documents and reports, with hashes for stale-input detection.

    No caches, default live path, publication, or editor calls. Call after the P1
    overlay has been staged into root. review_required files are not candidates.
    """
    candidates, reports = {}, []
    repairs = {134278144: _shield_cast, 134232470: _shield_cast, 134256840: _shield_cast,
               134280536: _piercing, 134268037: _sweep, 134233053: _courage,
               134275990: _rescue, 134236877: _archers, 134228469: _regen}
    for relative in FILES:
        if relative == ARCHER:
            continue
        report = dict(path=relative, file=relative, phase="P2", group="early",
                      issues=ISSUES[int(Path(relative).stem)])
        try:
            raw = (Path(root) / relative).read_bytes()
            report["source_sha256"] = hashlib.sha256(raw).hexdigest()
            original = json.loads(raw, object_pairs_hook=_unique)
            doc = clone(original)
            oid = int(Path(relative).stem)
            n = Nodes(doc, oid)
            messages = []
            if oid in repairs:
                repair = repairs[oid]
                messages.append(repair(doc, n, oid) if repair is _shield_cast else repair(doc, n))
            if oid in RATIO_FILES:
                messages.append(_ratio(doc, n, oid))
            need(doc != original, "no candidate change")
        except (OSError, ValueError, KeyError, IndexError, TypeError, StopIteration) as exc:
            report.update(status="review_required", explanation=str(exc))
        else:
            candidates[relative] = doc
            report.update(status="candidate", explanation=" ".join(messages), validation="static/offline only; editor/combat not verified")
        reports.append(report)
    try:
        bundle, hashes, message = _archer_bundle(Path(root))
    except (OSError, ValueError, KeyError, IndexError, TypeError, StopIteration) as exc:
        reports.append(dict(path=ARCHER, file=ARCHER, phase="P2", group="early", issues=[38],
                            status="review_required", explanation=str(exc), atomic_bundle=True))
    else:
        candidates.update(bundle)
        for relative in bundle:
            reports.append(dict(path=relative, file=relative, phase="P2", group="early", issues=[38],
                status="candidate", explanation=message, completion="conditional_damage_candidate",
                source_sha256=hashes.get(relative), source_hashes=hashes, atomic_bundle=True,
                operation="add" if relative in (SUPPORT_ECA, SUPPORT_PROP) else "modify",
                validation="static/offline only; editor/combat not verified"))
    reports.append(dict(phase="P2", group="early", status="limitation", explanation=(
        "No live writes/reload. Shared buffs unchanged. ADD_MODIFIER callback/cover timing, local captures, "
        "modifier iteration/deletion and event ordering need engine verification. Foreign same-type buffs "
        "block new creation instead of being overwritten. Existing caller healing=100 differs from design 2% maxHP; "
        "existing piercing base levels differ from design 125%; retained outside this scope. "
        "Huang Zhong uses new 134286002, not shared attack bonus 134243369; every damage event rechecks "
        "source/squad/current 4 internal stacks (=3 visible). Buff validity timer removes departed soldiers "
        "or invalid source contributions within 1s; no target commands. Editor import/save/readback and combat remain pending.")))
    return candidates, reports

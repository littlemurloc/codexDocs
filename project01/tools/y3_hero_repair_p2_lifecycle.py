"""Offline P2 lifecycle candidates #28/#40/#41/#42/#43, with pure overlays.

No writes/reload/import. build(root) always reads fresh input, requires the
published P1 saved timer for #28, and never returns full active-skill overlays.
Apply patch_xiahou_active(latest_doc, ability_id) AFTER P2early and atomically
with the #43 passive candidate for ALL three actives.

Native map3 evidence:
* 134277037: saved one-shot timer, modifier-context existence guard, cancellation.
* 134219344: event-local final-damage value read in a one-shot timer, with empty
  local_var; #28 uses the same declaration/reference pattern for window capture.
* 134255911 / 134250273: generic 100030/1 modifier-variable left values.
* 134259517: target selector uses the native partner/formation-leader tag union;
  actual damage uses TARGET_UNIT_IN_ABILITY. No made-up elite tag is introduced.
* 134259316: custom event 1477099689 is sent AFTER counter damage.
* Unit assignment adds active skill1..4 to HERO=3 and passive skill5..8 to
  COMMON=2. These are AbilityType values, not ACTIVE=2/PASSIVE=3 cast types.
  Official enum: github.com/y3-editor/y3-lualib/blob/main/game/const.lua
* 57f68cff7ce311f18f998d57b98bbdf4 checks type 1 + normal-attack tag ONLY.
  The owner explicitly approved normal-melee-only damage reduction for the
  three heroes. This does NOT redefine resource acquisition or other heroes.

All results remain unverified editor/runtime drafts. Offline tests inject
ordering and explicit callback capture, not an implementation of the Y3 engine.
"""

from __future__ import annotations

import argparse
from copy import deepcopy
import json
from pathlib import Path


TAISHI = "modifier/134277456.json"
XIAHOU = "modifier/134259960.json"
PASSIVE = "ability/134262911.json"
SHARED = "modifier/134279904.json"
ZHANGFEI = "modifier/134224490.json"
MELEE_SOURCES = (134245809, 134283219, 134254183)
ACTIVES = (134232470, 134269479, 134265726)
COMMON_SLOT = 2  # Official AbilityType.COMMON; NOT AbilityCastType.PASSIVE=3.
HERO_SLOT = 3  # This map adds skill1..4 here; passive skill5..8 use COMMON.
PREFIX = "P2_lifecycle_"
CD = "\u5185\u7f6eCD"
PENDING = PREFIX + "next_active"
COEFFICIENT = "\u4f24\u5bb3\u7cfb\u6570"
MELEE_HELPER = "57f68cff7ce311f18f998d57b98bbdf4"
ERRORS = (OSError, ValueError, KeyError, TypeError, IndexError, AttributeError)


class ReviewError(ValueError):
    pass


def require(ok, message):
    if not ok:
        raise ReviewError(message)


def ex(kind, subtype=1, *args):
    return {"arg_type": kind, "sub_type": subtype, "args_list": list(args)}


def vr(kind, name, scope="actor", lhs=False):
    codes = {"MODIFIER_ENTITY": (100076, 11), "UNIT_ENTITY": (100006, 11),
             "ABILITY": (100014, 2), "INTEGER": (100002, 6),
             "BOOLEAN": (100001, "VARIABLE"), "FLOAT": (100000, 2),
             "NEW_TIMER": (100181, "VARIABLE")}
    typ, sub = codes[kind]
    if lhs and kind != "NEW_TIMER":
        typ, sub = 100030, 1
    return ex(typ, sub, {"__tuple__": True, "items": [kind, name, scope]})


def cm():
    return ex(100076, "CUR_MODIFIER")


def ca():
    return ex(100014, "CUR_ABILITY")


def last(owner, key):
    return ex(100076, "GET_LAST_MODIFIER_INSTANCE", deepcopy(owner), ex(100046, 1, key))


def arithmetic(left, op, right, integer=False):
    return ex(100002 if integer else 100000, "MATH_OPERATION" if integer else "ARITHMETIC_OPERATION",
              deepcopy(left), ex(100016 if integer else 100017, 1, op), deepcopy(right))


def walk(n):
    if isinstance(n, dict):
        yield n
        for v in n.values():
            yield from walk(v)
    elif isinstance(n, list):
        for v in n:
            yield from walk(v)


def running(n):
    """Native enabled actions/conditions; unknown metadata is not executable AST."""
    if isinstance(n, list):
        for value in n:
            yield from running(value)
    elif isinstance(n, dict) and n.get("enable") is not False:
        yield n
        yield from running(n.get("args_list", []))
        for enabled, value in zip(n.get("op_arg_enable", []), n.get("op_arg", [])):
            if enabled is True:
                yield from running(value)


def node(container, eid, name, category="action_type"):
    all_matches = [n for n in walk(container) if n.get("element_id") == eid and n.get(category) == name]
    require(len(all_matches) == 1, f"missing/ambiguous {name} #{eid}")
    found = all_matches[0]
    require(found.get("enable") is True and any(n is found for n in running(container)),
            f"disabled anchor/ancestor #{eid}; preserve for review")
    return found


def trigger(doc, key, event):
    t = doc["trigger_dict"][str(key)]
    require(t.get("valid") is True and t.get("call_enabled") is True, f"invalid trigger {key}")
    require(any(n.get("enable") is True and n.get("event_type") == event for n in t["event"]),
            f"event changed for {key}")
    if t.get("enabled") is not True:
        parent = doc["trigger_dict"].get(str(t.get("p_trigger_id")), {})
        require(key in parent.get("action", []) and
                t.get("sub_trigger_owner_set_var_action", {}).get("enable") is True,
                f"dynamic registration changed for {key}")
    return t


class Edit:
    def __init__(self, doc):
        self.doc = doc
        self.serial = max((n["element_id"] for n in walk(doc) if isinstance(n.get("element_id"), int)), default=0)

    def n(self, category, name, *args):
        self.serial += 1
        result = {category: name, "element_id": self.serial, "enable": True, "args_list": list(args)}
        if category == "action_type":
            result["bp"] = False
        return result

    def a(self, name, *args):
        return self.n("action_type", name, *args)

    def c(self, name, *args):
        return self.n("condition_type", name, *args)

    def exists(self, value):
        return self.c("TYPE_IS_EXIST", deepcopy(value))

    def compare(self, name, left, right, op="=="):
        return self.c(name, deepcopy(left), ex(100015 if name == "FLOAT_COMPARE" else 100035, 1, op), deepcopy(right))

    def guard(self, stages, actions):
        result = list(actions)
        for checks in reversed(stages):
            result = [self.a("IF_THEN_ELSE", ex(100021, 1, *checks),
                             ex(100022, 1, *result), ex(100022, 1))]
        return result

    def set(self, kind, name, value, scope="actor"):
        return self.a("SET_VARIABLE", vr(kind, name, scope, lhs=True), deepcopy(value))

    def kv(self, entity, key, value):
        return self.a("SET_ENTITY_KV", deepcopy(entity), ex(100003, 1, key), deepcopy(value))

    def declare(self, kind, name, default, tid=None):
        if tid is None:
            data = self.doc
        else:
            data = self.doc["local_variable"][str(tid)]
        require(not any(name in values for values in data["variable_dict"].values()), "reserved variable: " + name)
        require(name not in data["variable_length_dict"], "variable length collision: " + name)
        data["variable_dict"].setdefault(kind, {})[name] = default
        data["variable_length_dict"][name] = 0
        if tid is None:
            require(not any(n.get("items", [None])[0] == name for n in self.doc["variable_group_info"]),
                    "variable group collision: " + name)
            self.doc["variable_group_info"].append({"__tuple__": True, "items": [name, name]})
        else:
            v = self.doc["trigger_dict"][str(tid)]["var_data"]
            require(not any(name in values for values in v[0].values()) and name not in v[1] and name not in v[2],
                    "var_data collision: " + name)
            v[0].setdefault(kind, {})[name] = default
            v[1][name] = 0
            v[2].append(name)


def _taishi(doc):
    e = Edit(doc)
    hurt = trigger(doc, 1418035204, "SPECIAL_UNIT_EVENT")
    loss = trigger(doc, 594665475, "LOSS_MODIFIER")
    timer = node(hurt["action"], 1418035204974513, "RUN_ONCE_TIMER")
    require(timer["args_list"][1] == ex(100000, 1, 8.0), "P1 eight-second timer changed")
    handle = timer["args_list"][0]
    require(handle.get("arg_type") == 100181 and handle.get("sub_type") == "VARIABLE", "P1 saved handle missing")
    require(any(n.get("action_type") == "DELETE_TIMER" and n["args_list"] == [handle]
                for n in running(loss["action"])), "P1 loss cancellation missing")
    reset = node(timer["args_list"][2], 1473785861000046, "SET_BUFF_STACK")
    require(reset["args_list"][0].get("sub_type") == 11, "P1 bound-instance reset missing")
    require(any(n.get("condition_type") == "MODIFIER_COMPARE" for n in running(timer)), "P1 identity guard missing")
    cb = timer["args_list"][2]["args_list"]
    cb_checks = [n for n in cb if n.get("enable") is not False]
    require(cb_checks and all(n.get("action_type") == "IF_THEN_ELSE" for n in cb_checks),
            "unknown P1 callback layout; cannot add capture guard")
    schedulers = [n for n in hurt["action"] if any(v is timer for v in running(n))]
    require(len(schedulers) == 1 and schedulers[0].get("action_type") == "IF_THEN_ELSE",
            "P1 schedule guard changed")
    cd = node(hurt["condition"], 1418035204974479, "BOOL_COMPARE", "condition_type")
    require(cd["args_list"] == [ex(100001, "GET_BOOLEAN_KV", cm(), ex(100003, 1, CD)),
                                ex(100035, 1, "=="), ex(100001, 1, False)], "old CD predicate changed")
    letter = node(hurt["action"], 1418035204974502, "ADD_MODIFIER")
    require(letter["args_list"] == [ex(100006, "DAMAGE_TARGET_UNIT"), ex(100046, 1, 134274015)],
            "war-letter action changed")
    require(letter.get("op_arg_enable", [])[:3] == [True, True, True] and
            letter["op_arg"][:3] == [ex(100006, "MODIFIER_OWNER"), ex(100014, "DAMAGE_ABILITY"), ex(100000, 1, 8.0)],
            "war-letter source/ability/duration changed")
    # The old condition is intentionally retired, not mistaken for runtime logic.
    cd["enable"] = False
    owner, ability, target = ex(100006, "MODIFIER_OWNER"), ex(100014, "DAMAGE_ABILITY"), ex(100006, "DAMAGE_TARGET_UNIT")
    primary = ex(100006, "TARGET_UNIT_IN_ABILITY", deepcopy(ability))
    hurt["condition"].extend([e.exists(cm()), e.exists(ability)])
    book_name, target_name, serial_name, captured_name = (
        PREFIX + name for name in ("letter", "letter_target", "window", "window_snapshot"))
    for kind, name in [("MODIFIER_ENTITY", book_name), ("UNIT_ENTITY", target_name), ("INTEGER", serial_name)]:
        e.declare(kind, name, 0)
    e.declare("INTEGER", captured_name, 0, 1418035204)
    serial, captured = vr("INTEGER", serial_name), vr("INTEGER", captured_name, "local")

    def same_window():
        return e.compare("FLOAT_COMPARE", serial, captured)

    # Append to existing safe, independent stages instead of adding IF depth.
    for guard in [schedulers[0], *cb_checks]:
        guard["args_list"][0]["args_list"].append(same_window())
    old, old_target = vr("MODIFIER_ENTITY", book_name), vr("UNIT_ENTITY", target_name)
    old_remove = e.guard([
        [e.exists(old), e.compare("UNIT_COMPARE", old_target, target, "!=")],
        [e.compare("UNIT_COMPARE", ex(100006, "GET_BUFF_SOURCE", deepcopy(old)), owner)],
    ], [e.a("REMOVE_BUFF_INS", deepcopy(old))])
    new_book = last(target, 134274015)
    remember = e.guard([[e.exists(new_book)],
                        [e.compare("UNIT_COMPARE", ex(100006, "GET_BUFF_SOURCE", deepcopy(new_book)), owner)]],
                       [e.set("MODIFIER_ENTITY", book_name, new_book), e.set("UNIT_ENTITY", target_name, target)])
    old_actions = hurt["action"]
    pos = next(i for i, n in enumerate(old_actions) if n is letter)
    old_actions[pos:pos + 1] = [*old_remove, letter, *remember]
    # Native selector union, not an invented elite tag or all AOE targets.
    eligible = e.c("OR", ex(100021, 1,
        e.c("UNIT_HAS_TAG", deepcopy(target), ex(100003, 1, "\u4ec6\u4ece\u4f19\u4f34")),
        e.c("UNIT_HAS_TAG", deepcopy(target), ex(100003, 1, "\u9635\u578b\u961f\u957f"))))
    hurt["action"] = e.guard([
        [e.exists(owner), e.exists(target), e.exists(primary)],
        [e.compare("ABILITY_TYPE_COMPARE", ex(100182, "TYPE_OF_ABILITY", deepcopy(ability)), ex(100182, 1, HERO_SLOT)),
         e.compare("ABILITY_CAST_TYPE_COMPARE", ex(100219, "GET_ABILITY_CAST_TYPE", deepcopy(ability)), ex(100219, 1, 2)),
         e.compare("UNIT_COMPARE", target, primary), eligible,
         e.compare("MODIFIER_COMPARE", cm(), reset["args_list"][0]),
         e.compare("MODIFIER_COMPARE", last(owner, 134277456), reset["args_list"][0])],
    ], [e.set("INTEGER", serial_name, arithmetic(serial, "+", ex(100002, 1, 1), integer=True)),
        e.set("INTEGER", captured_name, serial, "local"), *old_actions])


def _xiahou(doc):
    e = Edit(doc)
    obtain = trigger(doc, 1485688834, "OBTAIN_MODIFIER")
    loss = trigger(doc, 594665475, "LOSS_MODIFIER")
    hurt = trigger(doc, 762560516, "SPECIAL_UNIT_EVENT")
    add = node(hurt["action"], 762560516000061, "ADD_BUFF_STACK")
    require(add["args_list"] == [cm(), ex(100002, 1, 1)], "gain amount/instance changed")
    classifier = node(hurt["condition"], 762560516000105, "FUNC_CONDITION", "condition_type")
    require(classifier["args_list"][0].get("sub_type") == MELEE_HELPER and
            classifier["args_list"][0]["args_list"] == [ex(100014, "DAMAGE_ABILITY"), ex(100003, 1, "\u8fd1\u6218\u666e\u653b")],
            "normal-melee classifier changed")
    require(any(n.get("condition_type") == "GET_IS_NORMAL_HIT_FROM_EVENT" and n.get("enable") is True
                for n in hurt["condition"]), "normal-hit boundary changed")
    require(any(n.get("args_list") == [ex(100006, "MODIFIER_OWNER"), ex(100007, 1, "ET_UNIT_BE_HURT")]
                for n in hurt["event"]), "incoming damage event changed")
    old_name, active_name, ready_name, timer_name = (
        PREFIX + name for name in ("ganglie_instance", "ganglie_active", "gain_ready", "gain_timer"))
    for kind, name, value in [("MODIFIER_ENTITY", old_name, 0), ("BOOLEAN", active_name, False),
                               ("BOOLEAN", ready_name, True), ("NEW_TIMER", timer_name, -1)]:
        e.declare(kind, name, value)
    old, handle, owner = vr("MODIFIER_ENTITY", old_name), vr("NEW_TIMER", timer_name), ex(100006, "MODIFIER_OWNER")

    def bound():
        return [[e.exists(cm()), e.exists(old)],
                [e.compare("MODIFIER_COMPARE", cm(), old), e.exists(owner),
                 e.compare("BOOL_COMPARE", vr("BOOLEAN", active_name), ex(100001, 1, True))],
                [e.compare("MODIFIER_COMPARE", last(owner, 134259960), old)]]

    expiry = e.guard(bound(), [e.set("BOOLEAN", ready_name, ex(100001, 1, True))])
    timer = e.a("RUN_ONCE_TIMER", deepcopy(handle), ex(100000, 1, 1.0), ex(100022, 1, *expiry))
    timer["local_var"] = {"__tuple__": True, "items": [{}, {}]}
    obtain["action"][0:0] = [e.set("MODIFIER_ENTITY", old_name, cm()),
                            e.set("BOOLEAN", active_name, ex(100001, 1, True)),
                            e.set("BOOLEAN", ready_name, ex(100001, 1, True))]
    loss["action"][0:0] = [e.set("BOOLEAN", active_name, ex(100001, 1, False)),
                          e.set("BOOLEAN", ready_name, ex(100001, 1, False)),
                          e.a("DELETE_TIMER", deepcopy(handle))]
    # Move the unsafe function call behind an existence boundary; preserve its ID.
    hurt["condition"].remove(classifier)
    hurt["condition"].extend([e.exists(cm()), e.exists(ex(100014, "DAMAGE_ABILITY")),
                              e.exists(ex(100006, "DAMAGE_SOURCE_UNIT"))])
    old_actions = hurt["action"]
    owner_checks = [e.exists(owner),
                    e.compare("BOOL_COMPARE", vr("BOOLEAN", ready_name), ex(100001, 1, True)),
                    e.compare("BOOL_COMPARE", vr("BOOLEAN", active_name), ex(100001, 1, True)),
                    e.compare("MODIFIER_COMPARE", cm(), old)]
    hurt["action"] = e.guard([owner_checks,
        [classifier, e.compare("UNIT_COMPARE", ex(100006, "DAMAGE_SOURCE_UNIT"), owner, "!="),
         e.compare("MODIFIER_COMPARE", last(owner, 134259960), old)]],
        [e.set("BOOLEAN", ready_name, ex(100001, 1, False)), timer, *old_actions])
    # Arm before ADD_BUFF_STACK: any synchronous loss will cancel this handle.


def _normal_melee(e):
    """Call only after DAMAGE_ABILITY existence; all checks here are independent."""
    ability = ex(100014, "DAMAGE_ABILITY")
    return [e.compare("ABILITY_TYPE_COMPARE", ex(100182, "TYPE_OF_ABILITY", deepcopy(ability)), ex(100182, 1, 1)),
            e.c("ABILITY_HAS_TAG", deepcopy(ability), ex(100003, 1, "\u8fd1\u6218\u666e\u653b"))]


def _shared(doc):
    e = Edit(doc)
    hurt = trigger(doc, 512499716, "SPECIAL_UNIT_EVENT")
    reduction = node(hurt["action"], 512499716810154, "SET_CUR_DAMAGE")
    related = ex(100014, "RELATED_ABILITY", cm())
    require(any(n.get("sub_type") == "GET_FLOAT_KV" and n.get("args_list") ==
                [related, ex(100003, 1, "\u4f24\u5bb3\u51cf\u514d%")] for n in walk(reduction)),
            "shared reduction source/formula changed")
    require(hurt["action"] == [reduction], "shared incoming-damage actions changed; review ordering")
    name = PREFIX + "allow_reduction"
    e.declare("BOOLEAN", name, False, 512499716)
    allow = e.set("BOOLEAN", name, ex(100001, 1, True), "local")
    source_id = ex(100039, "ABILITY_NAME_OF_ABILITY", deepcopy(related))
    restricted = e.c("OR", ex(100021, 1, *[
        e.compare("ABILITY_COMPARE", source_id, ex(100039, 1, key)) for key in MELEE_SOURCES]))
    melee = e.guard([[e.c("GET_IS_NORMAL_HIT_FROM_EVENT"), e.exists(ex(100014, "DAMAGE_ABILITY"))],
                     _normal_melee(e)], [allow])
    all_damage = e.set("BOOLEAN", name, ex(100001, 1, True), "local")
    dispatch = e.a("IF_THEN_ELSE", ex(100021, 1, restricted), ex(100022, 1, *melee),
                   ex(100022, 1, all_damage))
    hurt["condition"].append(e.exists(cm()))
    hurt["action"] = [e.set("BOOLEAN", name, ex(100001, 1, False), "local"),
                      *e.guard([[e.exists(related)]], [dispatch]),
                      *e.guard([[e.compare("BOOL_COMPARE", vr("BOOLEAN", name, "local"),
                                           ex(100001, 1, True))]], [reduction])]
    # No global DAMAGE_ABILITY guard: unrestricted sources still reduce
    # environmental/ability-less damage, exactly as their all-damage contract.


def _zhangfei(doc):
    e = Edit(doc)
    obtain = trigger(doc, 434970627, "OBTAIN_MODIFIER")
    loss = trigger(doc, 1485688834, "LOSS_MODIFIER")
    layers = trigger(doc, 1050472449, "MODIFIER_LAYER_CHANGE")
    hurt = trigger(doc, 1022332932, "SPECIAL_UNIT_EVENT")
    attr = node(layers["action"], 1050472449000072, "ADD_MODIFIER_OWNER_ATTR")
    require(attr["args_list"] == [cm(), ex(100042, 1, "defense_phy"), ex(100300, 1, "ATTR_ALL_RATIO"),
            arithmetic(ex(100000, 1, 6.0), "*", ex(100002, "GET_MODIFIER_LAYER_CHANGE_VALUE"))],
            "original defense contribution changed")
    require([n for t in doc["trigger_dict"].values() for n in running(t["action"])
             if n.get("action_type") == "ADD_MODIFIER_OWNER_ATTR"] == [attr],
            "additional core attribute contributions need scoped cleanup review")
    node(loss["action"], 1485688834000006, "CLEAR_MODIFIER_OWNER_ATTR")
    timer = node(hurt["action"], 1022332932000060, "RUN_ONCE_TIMER_NO_SAVE")
    gain = node(hurt["action"], 762560516000061, "ADD_BUFF_STACK")
    require(gain["args_list"] == [cm(), ex(100002, 1, 1)], "guard resource amount changed")
    require(timer["args_list"][0] in [ex(100002, 1, 1), ex(100000, 1, 1.0)], "guard gain timer changed")
    clear_cd = node(timer, 1022332932000067, "SET_ENTITY_KV")
    require(clear_cd["args_list"] == [cm(), ex(100003, 1, CD), ex(100001, 1, False)], "guard CD reset changed")
    cd = node(hurt["condition"], 1022332932000026, "BOOL_COMPARE", "condition_type")
    classifier = node(hurt["condition"], 1022332932000017, "FUNC_CONDITION", "condition_type")
    require(classifier["args_list"][0].get("sub_type") == MELEE_HELPER and
            classifier["args_list"][0]["args_list"] == [ex(100014, "DAMAGE_ABILITY"), ex(100003, 1, "\u8fd1\u6218\u666e\u653b")],
            "guard resource classifier changed")
    old_name, active_name, timer_name = (PREFIX + n for n in ("guard_instance", "guard_active", "guard_gain_timer"))
    for kind, name, default in [("MODIFIER_ENTITY", old_name, 0), ("BOOLEAN", active_name, False),
                                ("NEW_TIMER", timer_name, -1)]:
        e.declare(kind, name, default)
    old, owner, handle = vr("MODIFIER_ENTITY", old_name), ex(100006, "MODIFIER_OWNER"), vr("NEW_TIMER", timer_name)

    def bound():
        return [[e.exists(cm()), e.exists(old)],
                [e.exists(owner), e.compare("MODIFIER_COMPARE", cm(), old),
                 e.compare("BOOL_COMPARE", vr("BOOLEAN", active_name), ex(100001, 1, True))],
                [e.compare("MODIFIER_COMPARE", last(owner, 134224490), old)]]

    clear_cd["args_list"][0] = deepcopy(old)
    timer["action_type"] = "RUN_ONCE_TIMER"
    timer["args_list"] = [deepcopy(handle), ex(100000, 1, 1.0), ex(100022, 1, *e.guard(bound(), [clear_cd]))]
    timer.setdefault("local_var", {"__tuple__": True, "items": [{}, {}]})
    attr["enable"] = False
    pos = next(i for i, n in enumerate(layers["action"]) if n is attr)
    layers["action"].insert(pos + 1, e.a("CLEAR_MODIFIER_OWNER_ATTR", cm()))
    obtain["action"][0:0] = [e.set("MODIFIER_ENTITY", old_name, cm()),
                            e.set("BOOLEAN", active_name, ex(100001, 1, True)),
                            e.a("CLEAR_MODIFIER_OWNER_ATTR", cm())]
    loss["action"][0:0] = [e.set("BOOLEAN", active_name, ex(100001, 1, False)),
                          e.a("DELETE_TIMER", deepcopy(handle))]
    # Snapshot current layers for this incoming packet, then retain the original
    # gain classifier/CD path. CD limits gain, NOT per-packet damage reduction.
    visible = ex(100000, "I2F", arithmetic(ex(100002, "GET_MOD_STACK", cm()), "-", ex(100002, 1, 1), integer=True))
    multiplier = arithmetic(ex(100000, 1, 1.0), "-", arithmetic(ex(100000, 1, 0.06), "*", visible))
    reduction = e.a("SET_CUR_DAMAGE", arithmetic(ex(100000, "HURT_DAMAGE"), "*", multiplier))
    gain_actions = hurt["action"]
    require(gain_actions.index(gain) < gain_actions.index(timer), "guard gain/timer ordering changed")
    gain_actions.remove(timer)
    gain_actions.insert(gain_actions.index(gain), timer)
    hurt["condition"].remove(cd)
    hurt["condition"].remove(classifier)
    hurt["condition"].extend([e.exists(cm()), e.exists(ex(100014, "DAMAGE_ABILITY"))])
    hurt["action"] = e.guard([[classifier]], [
        *e.guard([[e.c("GET_IS_NORMAL_HIT_FROM_EVENT")]], [reduction]),
        *e.guard([[cd]], gain_actions),
    ])
    # The saved handle is armed before gain so synchronous loss can cancel it.
    # The resource path keeps its pre-existing helper taxonomy; the newly
    # approved normal-hit requirement applies only to the reduction branch.


def _passive(doc):
    e = Edit(doc)
    obtain = trigger(doc, 1959489540, "ABILITY_OBTAIN")
    loss = trigger(doc, 225054724, "ABILITY_LOSE")
    counter = trigger(doc, 58232837, "RECEIVE_CUSTOM_EVENT")
    old_damage = trigger(doc, 173064198, "SPECIAL_UNIT_EVENT")
    require(any(n.get("args_list") == [ex(100238, 1, 1477099689)] for n in counter["event"]),
            "counter notification changed")
    require(not any(n.get("action_type") == "SET_ENTITY_KV" and len(n.get("args_list", [])) > 1 and
                    n["args_list"][1] == ex(100003, 1, PENDING) for n in walk(doc)), "passive already patched")
    arm = node(counter["action"], 58232837974056, "SET_ENTITY_KV")
    require(arm["args_list"] == [ca(), ex(100003, 1, CD), ex(100001, 1, False)], "counter arm changed")
    require(len(counter["condition"]) == 1 and counter["condition"][0].get("condition_type") == "UNIT_COMPARE",
            "counter owner check changed")
    arm["args_list"][1:] = [ex(100003, 1, PENDING), ex(100001, 1, True)]
    checks = counter["condition"]
    counter["condition"] = [e.exists(ca())]
    counter["action"] = e.guard([[e.exists(ex(100006, "ABILITY_OWNER"))], checks], counter["action"])
    obtain["action"].remove(173064198)
    old_damage["sub_trigger_owner_set_var_action"]["enable"] = False
    old_damage["call_enabled"] = False
    # Preserve the retired packet-consumer AST/IDs, but explicitly unregister its lifecycle.
    unreg = node(loss["action"], 225054724000150, "UNREG_TRIGGER")
    require("temp2" in json.dumps(unreg["args_list"], ensure_ascii=False), "packet listener loss handle changed")
    # Keep legacy loss cleanup: an already registered old listener must still
    # be removable. The original source already uses this unconditional cleanup.
    obtain["action"].insert(0, e.kv(ca(), PENDING, ex(100001, 1, False)))
    loss["action"][0:0] = e.guard([[e.exists(ca())]], [e.kv(ca(), PENDING, ex(100001, 1, False))])


def patch_xiahou_active(latest_doc: dict, ability_id: int) -> dict:
    """Pure POST-P2early overlay. Apply all ACTIVES with the passive atomically.

    Snapshot/consume once at the beginning of ABILITY_SP_END; multiply each
    enabled APPLY_DAMAGE payload, leaving targets, timers, IDs, and other edits
    intact. Async damage needs a separately verified capture and is refused.
    """
    require(ability_id in ACTIVES, "active is outside #43 scope")
    doc = deepcopy(latest_doc)
    e = Edit(doc)
    cast = trigger(doc, 893440004, "ABILITY_SP_END")
    require(cast.get("group_id") == ability_id, "active object identity mismatch")
    packets = [n for n in running(cast["action"]) if n.get("action_type") == "APPLY_DAMAGE"]
    require(packets, "no enabled active damage payloads")
    for n in running(cast["action"]):
        name = n.get("action_type", "")
        if isinstance(name, str) and ("TIMER" in name or "MOVER" in name or "PROJECTILE" in name):
            require(not any(p is v for v in running(n.get("args_list", [])) for p in packets),
                    "async active damage requires capture review")
    factor_name, passive_name = PREFIX + "cast_factor", PREFIX + "cast_passive"
    e.declare("FLOAT", factor_name, 1.0, 893440004)
    e.declare("ABILITY", passive_name, 0, 893440004)
    factor, passive = vr("FLOAT", factor_name, "local"), vr("ABILITY", passive_name, "local")
    owner = ex(100006, "ABILITY_OWNER")
    prelude = [e.set("FLOAT", factor_name, ex(100000, 1, 1.0), "local")]
    prelude += e.guard([[e.exists(ca())], [e.exists(owner)]], [e.set("ABILITY", passive_name,
        ex(100014, "GET_ABILITY_BY_AID", deepcopy(owner), ex(100182, 1, COMMON_SLOT), ex(100039, 1, 134262911)), "local")])
    prelude += e.guard([[e.exists(passive)],
        [e.c("HAS_KV_ANY", deepcopy(passive), ex(100003, 1, PENDING)),
         e.c("HAS_KV_ANY", deepcopy(passive), ex(100003, 1, COEFFICIENT))],
        [e.compare("BOOL_COMPARE", ex(100001, "GET_BOOLEAN_KV", deepcopy(passive), ex(100003, 1, PENDING)),
                   ex(100001, 1, True))]],
        [e.set("FLOAT", factor_name, arithmetic(ex(100000, 1, 1.0), "+",
                    ex(100000, "GET_FLOAT_KV", deepcopy(passive), ex(100003, 1, COEFFICIENT))), "local"),
         e.kv(passive, PENDING, ex(100001, 1, False))])
    for packet in packets:
        require(len(packet["args_list"]) == 6 and packet["args_list"][1] == ca(), "damage ability/arity changed")
        packet["args_list"][4] = arithmetic(packet["args_list"][4], "*", factor)
    cast["action"][0:0] = prelude
    return doc


def _read(root, rel):
    return json.loads((root / rel).read_text(encoding="utf-8-sig"))


def build(root: Path) -> tuple[dict[str, dict], list[dict]]:
    root = Path(root)
    docs, issues = {}, []
    for rel, case, fix, explanation in [
        (TAISHI, 28, _taishi, "Active primary native leader/elite target only; retire eight-second reentry block, "
         "transfer tracked own letter, preserve P1 timer/identity/cancellation and append captured window guards."),
        (XIAHOU, 42, _xiahou, "Incoming normal melee hits only; guard damage ability/source, reject self source, "
         "one gain per one-second saved timer, cancel on loss and validate old core on expiry."),
        (SHARED, 40, _shared, "Only related skill IDs 134245809/134283219/134254183 require normal-hit + type1 + "
         "melee-normal tag. All other sources retain all-damage reduction, including ability-less damage. "
         "No source ability edits needed: their enabled related-ability operands are retained."),
        (ZHANGFEI, 41, _zhangfei, "Remove defense ratio contribution, clear only this core's owned attributes, "
         "reduce each normal-melee packet by 6% per visible pre-hit layer independently of gain CD. "
         "Preserve original resource classifier; save/cancel/bind the existing one-second gain timer."),
        (PASSIVE, 43, _passive, "Counter arms pending; obtain/loss clear pending; retire packet consumer. "
         "Requires ALL three post-P2early active overlays in the same candidate transaction."),
    ]:
        try:
            if case == 40:
                for key in MELEE_SOURCES:
                    src = _read(root, f"ability/{key}.json")
                    applies = [n for t in src["trigger_dict"].values() for n in running(t["action"])
                               if n.get("action_type") == "ADD_MODIFIER" and len(n.get("args_list", [])) == 2
                               and n["args_list"][1] == ex(100046, 1, 134279904)]
                    require(applies and all(n.get("op_arg_enable", [False, False])[1] is True and
                                            n["op_arg"][1] == ca() for n in applies),
                            f"source {key} does not reliably bind its related ability")
            source = _read(root, rel)
            changed = deepcopy(source)
            fix(changed)
            docs[rel] = changed
            item = {"file": rel, "case": case, "status": "candidate", "explanation": explanation,
                    "validation": "offline draft; editor/runtime not verified"}
            if case == 43:
                item["requires_atomic_overlays"] = [f"ability/{key}.json" for key in ACTIVES]
                item["overlay_function"] = "patch_xiahou_active(latest_doc, ability_id)"
                item["apply_order"] = "P2early first, then this pure overlay; do not install passive alone"
            if case in (40, 41):
                item["text_overlay_owner"] = "main agent; no language/table payload emitted"
            issues.append(item)
        except ERRORS as exc:
            issues.append({"file": rel, "case": case, "status": "review_required", "explanation": str(exc)})
    return docs, issues


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    args = parser.parse_args()
    documents, findings = build(args.root)
    print(json.dumps({"documents": documents, "issues": findings}, ensure_ascii=True, indent=2))

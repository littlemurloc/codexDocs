"""Read-only P2 #15/#30/#31 candidates, built from current map3 JSON.

No cached documents, live writes, reloads, or publisher. Python json preserves
integer IDs. Only the eight named modifier ECAs and Sun Ce's two-/six-star
ECAs can be returned. Four-star/caller/object-editor documents are not changed.

Native evidence: ABILITY_NAME_OF_ABILITY (ability/134220036), ABILITY_COMPARE
(modifier/134229073), POINT local refs/declarations (ability/134230297),
MODIFIER_COMPARE (modifier/134275651), and the existing Sun Ce mover/shape.
Terminal action-list slots 6/7 receive guarded cleanup, not invented APIs.
Callback capture, mover completion/interrupt semantics and attribute readings
still require editor/runtime verification. Offline tests do not run an engine.
"""

from __future__ import annotations

from copy import deepcopy
import json
import os
from pathlib import Path


MODIFIERS = (134256265, 134283923, 134283937, 134283938, 134283939,
             134284016, 134284017, 134284019)
SUNCE = "ability/134283925.json"
SUNCE_SIX = "ability/134283929.json"
CORE = 134279388
BUSY = "\u5b59\u7b56\u6f6e\u52bf\u51b2\u65a9\u5904\u7406\u4e2d"
TARGET = "\u6f6e\u52bf\u76ee\u6807"
RATIO = "\u51cf\u76ca\u6bd4\u4f8b"
ATTACK_RATIO = "\u964d\u653b\u7cfb\u6570"
FRACTIONAL_ATTACK_CALLERS = (134283919, 134280536, 134275485, 134232552)
PREFIX = "P2_latest_"
PHASE = "\u5f53\u524d\u6e38\u620f\u8fdb\u7a0b\u9636\u6bb5"
WAVE = "\u5f53\u524d\u8fdb\u7a0b\u6240\u5728\u6ce2\u6b21\u7f16\u53f7"
EVENT_OPEN = PREFIX + "sunce_event_open"
EVENT_CORE = PREFIX + "sunce_event_core"
EVENT_HITS = PREFIX + "sunce_event_hits"
EVENT_WAVE = PREFIX + "sunce_event_wave"


class ReviewError(ValueError):
    """Changed native anchors must be reviewed, never silently overwritten."""


def need(condition, message):
    if not condition:
        raise ReviewError(message)


def walk(value):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk(child)


def enabled_walk(value):
    if isinstance(value, dict):
        if value.get("enable") is False:
            return
        yield value
        for child in value.values():
            yield from enabled_walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from enabled_walk(child)


def ex(kind, subtype=1, *args):
    return {"arg_type": kind, "sub_type": subtype, "args_list": list(args)}


def literal(value):
    return ex(100000, 1, value)


def calc(left, op, right):
    return ex(100000, "ARITHMETIC_OPERATION", deepcopy(left),
              ex(100017, 1, op), deepcopy(right))


def kv(kind, owner, key):
    subtypes = {100000: "GET_FLOAT_KV", 100001: "GET_BOOLEAN_KV",
                100002: "GET_INTEGER_KV", 100006: "GET_UNIT_ENTITY_KV",
                100076: "GET_MODIFIER_ENTITY_KV"}
    return ex(kind, subtypes[kind], deepcopy(owner), ex(100003, 1, key))


def local(kind, name, target=False):
    types = {"POINT": (100004, 19), "UNIT_ENTITY": (100006, 11),
             "MODIFIER_ENTITY": (100076, 11), "ABILITY": (100014, 2),
             "FLOAT": (100000, 2), "INTEGER": (100002, 6), "BOOLEAN": (100001, "VARIABLE")}
    arg_type, subtype = types[kind]
    if target:
        arg_type, subtype = 100030, 1
    return ex(arg_type, subtype, {"__tuple__": True,
                                 "items": [kind, PREFIX + name, "local"]})


def global_integer(name):
    return ex(100002, 6, {"__tuple__": True, "items": ["INTEGER", name]})


def write_kv(edit, owner, key, value):
    return edit.act("SET_ENTITY_KV", deepcopy(owner), ex(100003, 1, key), deepcopy(value))


def initialize_event_lease(edit, doc):
    """Each participating skill lifetime closes any previous dispatch window."""
    owner, ability = ex(100006, "ABILITY_OWNER"), ex(100014, "CUR_ABILITY")
    for event in ("ABILITY_OBTAIN", "ABILITY_LOSE"):
        stage = trigger(doc, event)
        stage["action"][0:0] = edit.guard([edit.exists(ability), edit.exists(owner)], [
            write_kv(edit, owner, EVENT_OPEN, ex(100001, 1, False))])


class Edit:
    def __init__(self, document, object_id):
        self.document = document
        self.used = {n["element_id"] for n in walk(document) if "element_id" in n}
        # Separate per-object ranges also keep two-/six-star additions distinct.
        self.next = max(max(self.used, default=0), 2_300_000_000_000_000 + object_id * 10_000)

    def node(self, category, name, *args):
        self.next += 1
        self.used.add(self.next)
        node = {category: name, "args_list": list(args), "element_id": self.next,
                "enable": True}
        if category == "action_type":
            node["bp"] = False
        return node

    def act(self, name, *args):
        return self.node("action_type", name, *args)

    def cond(self, name, *args):
        return self.node("condition_type", name, *args)

    def exists(self, ref):
        return self.cond("TYPE_IS_EXIST", deepcopy(ref))

    def compare(self, name, left, op, right):
        operator = 100015 if name == "FLOAT_COMPARE" else 100035
        return self.cond(name, deepcopy(left), ex(operator, 1, op), deepcopy(right))

    def branch(self, conditions, yes, no=()):
        return self.act("IF_THEN_ELSE", ex(100021, 1, *conditions),
                        ex(100022, 1, *yes), ex(100022, 1, *no))

    def guard(self, stages, actions):
        result = list(actions)
        for stage in reversed(stages):
            result = [self.branch(stage if isinstance(stage, list) else [stage], result)]
        return result

    def assign(self, kind, name, value):
        return self.act("SET_VARIABLE", local(kind, name, True), deepcopy(value))

    def declare(self, trigger, kind, name, default):
        name = PREFIX + name
        data = self.document["local_variable"][str(trigger["trigger_id"])]
        need(not any(name in v for v in data["variable_dict"].values()),
             "reserved local variable already exists: " + name)
        data["variable_dict"].setdefault(kind, {})[name] = deepcopy(default)
        data["variable_length_dict"][name] = 0
        trigger["var_data"][0].setdefault(kind, {})[name] = deepcopy(default)
        trigger["var_data"][1][name] = 0
        trigger["var_data"][2].append(name)

    def fresh(self, value):
        result = deepcopy(value)
        for n in walk(result):
            if "element_id" in n:
                self.next += 1
                self.used.add(self.next)
                n["element_id"] = self.next
        return result


def trigger(doc, event):
    matches = [t for t in doc["trigger_dict"].values()
               if any(e.get("event_type") == event and e.get("enable") is True
                      for e in t["event"])]
    need(len(matches) == 1, "missing/ambiguous event: " + event)
    t = matches[0]
    need(t.get("valid") is True and t.get("call_enabled") is True,
         "invalid/uncallable event: " + event)
    if not t["enabled"]:
        parent = doc["trigger_dict"][str(t["p_trigger_id"])]
        need(t["trigger_id"] in parent["action"] and
             t["sub_trigger_owner_set_var_action"]["enable"] is True,
             "dynamic trigger registration changed: " + event)
    return t


def anchor(value, name, element_id=None):
    matches = [n for n in walk(value) if n.get("action_type") == name
               and (element_id is None or n.get("element_id") == element_id)]
    need(len(matches) == 1, f"missing/ambiguous {name} #{element_id}")
    result = matches[0]

    def active(n, enabled=True):
        if isinstance(n, dict):
            enabled = enabled and n.get("enable") is not False
            if n is result:
                return enabled
            children = n.values()
        elif isinstance(n, list):
            children = n
        else:
            return None
        for child in children:
            found = active(child, enabled)
            if found is not None:
                return found
        return None

    need(active(value) is True, "disabled anchor or ancestor: " + name)
    return result


def replace(value, pairs):
    """Structural substitutions only; retain unrelated fields and native metadata."""
    for before, after in pairs:
        if value == before:
            return deepcopy(after)
    if isinstance(value, dict):
        return {k: replace(v, pairs) for k, v in value.items()}
    if isinstance(value, list):
        return [replace(v, pairs) for v in value]
    return value


def splice_actions(value, replacements):
    if isinstance(value, dict):
        for child in value.values():
            splice_actions(child, replacements)
    elif isinstance(value, list):
        for index in range(len(value) - 1, -1, -1):
            child = value[index]
            key = child.get("element_id") if isinstance(child, dict) else None
            if key in replacements:
                value[index:index + 1] = replacements[key]
            else:
                splice_actions(child, replacements)


def loss_contract(doc):
    loss = trigger(doc, "LOSS_MODIFIER")
    clear = anchor(loss["action"], "CLEAR_MODIFIER_OWNER_ATTR")
    need(clear["args_list"] == [ex(100076, "CUR_MODIFIER")],
         "loss no longer clears this modifier's own contribution")


def attribute(doc, attr, mode):
    gain = trigger(doc, "OBTAIN_MODIFIER")
    matches = [n for n in walk(gain["action"])
               if n.get("action_type") == "ADD_MODIFIER_OWNER_ATTR"
               and n["args_list"][1] == ex(100042, 1, attr)]
    need(len(matches) == 1, "attribute anchor changed: " + attr)
    action = anchor(gain["action"], "ADD_MODIFIER_OWNER_ATTR", matches[0]["element_id"])
    need(action["args_list"][:3] == [ex(100076, "CUR_MODIFIER"),
         ex(100042, 1, attr), ex(100300, 1, mode)], "attribute mode/owner changed")
    return action


def patch_modifier(document, oid):
    doc = deepcopy(document)
    loss_contract(doc)
    if oid == 134256265:
        e = Edit(doc, oid)
        gain = trigger(doc, "OBTAIN_MODIFIER")
        old = attribute(doc, "attack_phy", "ATTR_ALL_RATIO")
        related = ex(100014, "RELATED_ABILITY_MODIFIER", ex(100076, "CUR_MODIFIER"))
        expected = calc(kv(100000, related, ATTACK_RATIO), "*", literal(-1.0))
        need(old["args_list"][3] == expected, "shared attack expression changed")
        scoped = e.fresh(old)
        scoped["args_list"][3] = calc(kv(100000, related, ATTACK_RATIO), "*", literal(-100.0))
        fractional_source = e.cond("OR", ex(100021, 1, *[
            e.compare("ABILITY_COMPARE", ex(100039, "ABILITY_NAME_OF_ABILITY", related),
                      "==", ex(100039, 1, aid)) for aid in FRACTIONAL_ATTACK_CALLERS]))
        index = gain["action"].index(old)
        gain["action"][index:index + 1] = e.guard([e.exists(related)], [
            e.branch([fractional_source], [scoped], [old])])
    elif oid in (134283923, 134283937, 134283938, 134283939):
        attr, mode, before, after = {
            134283923: ("attack_speed", "ATTR_ALL_RATIO", 0.3, 30.0),
            134283937: ("attack_phy", "ATTR_ALL_RATIO", -0.15, -15.0),
            134283938: ("attack_phy", "ATTR_ALL_RATIO", 0.15, 15.0),
            134283939: ("attack_speed", "ATTR_BASE", 0.2, 20.0),
        }[oid]
        action = attribute(doc, attr, mode)
        need(action["args_list"][3] == literal(before), "literal contribution changed")
        action["args_list"][2] = ex(100300, 1, "ATTR_ALL_RATIO")
        action["args_list"][3] = literal(after)
    else:
        fields = {134284016: [("attack_speed", "ATTR_BASE")],
                  134284017: [("ori_speed", "ATTR_ALL_RATIO")],
                  134284019: [("attack_phy", "ATTR_ALL_RATIO"),
                              ("attack_mag", "ATTR_ALL_RATIO")]}[oid]
        related = ex(100014, "RELATED_ABILITY", ex(100076, "CUR_MODIFIER"))
        expected = calc(literal(0.0), "-", kv(100000, related, RATIO))
        for field, mode in fields:
            action = attribute(doc, field, mode)
            need(action["args_list"][3] == expected, "Han Dang ratio expression changed")
            action["args_list"][2] = ex(100300, 1, "ATTR_ALL_RATIO")
            action["args_list"][3] = calc(expected, "*", literal(100.0))
    return doc


def patch_sunce(document):
    doc = deepcopy(document)
    e = Edit(doc, 134283925)
    t = trigger(doc, "GLOBAL_MODIFIER_EVENT")
    need(t["trigger_id"] == 1051000836, "Sun Ce entry changed")
    mover = anchor(t["action"], "CREATE_STRAIGHT_MOVER", 105047244999015)
    consume = anchor(t["action"], "SET_BUFF_STACK", 105047244999001)
    busy = anchor(t["action"], "SET_ENTITY_KV", 105100083699001)
    target_write = anchor(t["action"], "SET_ENTITY_KV", 105100083699000)
    counter = anchor(t["action"], "SET_ENTITY_KV", 105047244999002)
    finish = mover["args_list"][5]["args_list"]
    pick = anchor(finish, "PICK_UNIT_DO_ACTION", 141803520499016)
    main_damage = anchor(finish, "APPLY_DAMAGE", 105047244999004)
    other_damage = anchor(finish, "APPLY_DAMAGE", 141803520499013)
    clear = anchor(finish, "SET_ENTITY_KV", 105100083699002)
    notify = anchor(finish, "SEND_CUSTOM_EVENT", 105100083699003)
    event_core = ex(100076, "GET_MODIFIER_FROM_EVENT")
    owner = ex(100006, "ABILITY_OWNER")
    ability = ex(100014, "CUR_ABILITY")
    old_target = kv(100006, event_core, TARGET)
    need(consume["args_list"] == [event_core, ex(100002, 1, 1)], "stack convention changed")
    need(target_write["args_list"] == [event_core, ex(100003, 1, TARGET),
         ex(100006, "GET_UNIT_AI_BATTLE_TARGET_UNIT", owner)], "target lookup changed")
    need(busy["args_list"] == [event_core, ex(100003, 1, BUSY), ex(100001, 1, True)],
         "busy protocol changed")
    need(len(mover["args_list"]) == 10 and
         all(a == ex(100022, 1) for a in mover["args_list"][6:]),
         "non-arrival callbacks changed; preserve for manual merge")
    need(mover["args_list"][2].get("sub_type") == "ARITHMETIC_OPERATION" and
         mover["args_list"][2]["args_list"][2] == literal(0.7), "distance formula changed")
    for kind, name, default in [("UNIT_ENTITY", "owner", 0), ("UNIT_ENTITY", "target", 0),
                                ("MODIFIER_ENTITY", "core", 0), ("ABILITY", "ability", 0),
                                ("POINT", "start", {"__tuple__": True, "items": [0, 0, 0]}),
                                ("POINT", "end", {"__tuple__": True, "items": [0, 0, 0]}),
                                ("FLOAT", "hits", 0.0), ("BOOLEAN", "done", False),
                                ("INTEGER", "wave", 0)]:
        e.declare(t, kind, name, default)
    source, target, core, skill = (local(k, n) for k, n in
        [("UNIT_ENTITY", "owner"), ("UNIT_ENTITY", "target"),
         ("MODIFIER_ENTITY", "core"), ("ABILITY", "ability")])
    start, end = local("POINT", "start"), local("POINT", "end")
    hits, done = local("FLOAT", "hits"), local("BOOLEAN", "done")
    wave = local("INTEGER", "wave")
    lookup = ex(100076, "GET_LAST_MODIFIER_INSTANCE", source, ex(100046, 1, CORE))

    def bound():
        return [[e.exists(source), e.exists(core)],
                [e.compare("MODIFIER_COMPARE", lookup, "==", core),
                 e.compare("FLOAT_COMPARE", global_integer(WAVE), "==", wave),
                 e.compare("FLOAT_COMPARE", global_integer(PHASE), "==", ex(100002, 1, 2))]]

    def live():
        return bound() + [[e.exists(skill)], [e.cond("IS_UNIT_ALIVE", source)]]

    def enemy(unit):
        return e.cond("PLAYERS_IS_ENEMY_RELATION", ex(100025, "OWNER_PLAYER", unit),
                      ex(100025, "OWNER_PLAYER", source))

    pairs = [(owner, source), (ability, skill), (old_target, target), (event_core, core)]
    original_main, original_other = main_damage, other_damage
    original_clear, original_notify = clear, notify
    original_busy, original_consume = busy, consume
    main_damage, other_damage = replace(main_damage, pairs), replace(other_damage, pairs)
    clear, notify = replace(clear, pairs), replace(notify, pairs)
    busy, consume = replace(busy, pairs), replace(consume, pairs)
    # The rectangle is still native; only its geometry operands become snapshots.
    shape = replace(pick["args_list"][0], [
        (ex(100004, "UNIT_ENTITY_POINT", owner), start),
        (ex(100004, "UNIT_ENTITY_POINT", old_target), end), (owner, source)])
    need(shape["sub_type"] == "UNIT_LIST_IN_SHAPE", "path picker changed")
    selected = ex(100006, "FOR_EACH_SELECTED_UNIT")
    hit = lambda: e.assign("FLOAT", "hits", calc(hits, "+", literal(1.0)))
    pick["args_list"][0] = shape
    # Preserve the existing pick/limit branches and their metadata, but move the
    # counter off the disappearing core instance. The two-extra cap becomes a
    # three-total cap, so a dead primary does not waste a path hit slot.
    old_limit = [n for n in walk(pick) if n.get("condition_type") == "FLOAT_COMPARE"]
    need(len(old_limit) == 1, "path hit limit changed")
    old_limit[0]["args_list"][0] = deepcopy(hits)
    old_limit[0]["args_list"][2] = literal(3.0)
    increment = anchor(pick, "SET_ENTITY_KV", 141803520499014)
    increment["action_type"] = "SET_VARIABLE"
    increment["args_list"] = [local("FLOAT", "hits", True), calc(hits, "+", literal(1.0))]
    other_guard = e.guard(live() + [
        [e.exists(selected)], [e.cond("IS_UNIT_ALIVE", selected), enemy(selected),
         e.compare("UNIT_COMPARE", selected, "!=", target),
         e.compare("FLOAT_COMPARE", hits, "<", literal(3.0))]], [increment, other_damage])
    splice_actions(pick, {original_other["element_id"]: other_guard,
                          increment["element_id"]: []})
    primary = e.guard(live() + [[e.exists(target)],
                      [e.cond("IS_UNIT_ALIVE", target), enemy(target)]], [hit(), main_damage])
    completion = [
        write_kv(e, source, EVENT_OPEN, ex(100001, 1, False)),
        write_kv(e, source, EVENT_CORE, core), write_kv(e, source, EVENT_HITS, hits),
        write_kv(e, source, EVENT_WAVE, wave),
        write_kv(e, source, EVENT_OPEN, ex(100001, 1, True)),
        notify,
        *e.guard(bound(), [write_kv(e, source, EVENT_OPEN, ex(100001, 1, False))]),
    ]
    replacements = {original_main["element_id"]: primary,
                    pick["element_id"]: e.guard(live(), [pick]),
                    original_clear["element_id"]: e.guard(bound(), [clear]),
                    original_notify["element_id"]: e.guard(live(), completion)}
    for n in finish:
        if isinstance(n, dict) and n.get("action_type", "").startswith("CREATE_SFX"):
            replacements[n["element_id"]] = e.guard(live(), [replace(n, pairs)])
    splice_actions(finish, replacements)
    # Check again after every synchronous damage chain; old instances get no writes.
    finish[:] = e.guard([e.compare("BOOL_COMPARE", done, "==", ex(100001, 1, False))], [
        e.assign("BOOLEAN", "done", ex(100001, 1, True)),
        *replace(finish, pairs)])
    # Slots 6/7 were empty terminal action lists. Do not add collision operations.
    for slot in (6, 7):
        mover["args_list"][slot]["args_list"] = e.guard([
            e.compare("BOOL_COMPARE", done, "==", ex(100001, 1, False))], [
                e.assign("BOOLEAN", "done", ex(100001, 1, True)),
                *e.guard(bound(), [e.fresh(clear)])])
    mover["args_list"][0] = deepcopy(source)
    mover["args_list"][1] = ex(100225, "GET_POINTS_ANGLE", deepcopy(start), deepcopy(end))
    mover["args_list"][2] = ex(100000, "GET_POINTS_DIS", deepcopy(start), deepcopy(end))
    # Keep native mover options, disabled SFX, speed, acceleration and IDs.
    conditions = t["condition"]
    t["condition"] = [e.exists(ability), e.exists(event_core)]
    target_branch = [n for n in walk(t["action"]) if n.get("action_type") == "IF_THEN_ELSE"
                     and mover in n["args_list"][1]["args_list"]]
    need(len(target_branch) == 1, "target-arrival branch changed")
    # Reparent native actions instead of recreating the complete event body.
    # Additions made by P1 in this latest document survive these targeted splices.
    target_write["args_list"][2] = deepcopy(target)
    counter["action_type"] = "SET_VARIABLE"
    counter["args_list"] = [local("FLOAT", "hits", True), literal(0.0)]
    splice_actions(t["action"], {
        original_busy["element_id"]: [], original_consume["element_id"]: [],
        counter["element_id"]: [
            e.assign("POINT", "start", ex(100004, "UNIT_ENTITY_POINT", source)),
            e.assign("POINT", "end", ex(100004, "UNIT_ENTITY_POINT", target)),
            e.assign("INTEGER", "wave", global_integer(WAVE)),
            counter,
            e.assign("BOOLEAN", "done", ex(100001, 1, False)),
            write_kv(e, source, EVENT_OPEN, ex(100001, 1, False)), busy, consume],
    })
    branch = target_branch[0]
    splice_actions(t["action"], {branch["element_id"]: e.guard([
        [e.exists(target)], [enemy(target)]], [branch])})
    # SET_BUFF_STACK can synchronously run core lifecycle handlers.
    splice_actions(t["action"], {mover["element_id"]: e.guard(live(), [mover])})
    old_actions = replace(t["action"], pairs)
    t["action"] = e.guard([[e.exists(owner)], [e.cond("IS_UNIT_ALIVE", owner)], conditions], [
        e.assign("UNIT_ENTITY", "owner", owner), e.assign("MODIFIER_ENTITY", "core", event_core),
        e.assign("ABILITY", "ability", ability),
        e.assign("UNIT_ENTITY", "target", ex(100006, "GET_UNIT_AI_BATTLE_TARGET_UNIT", owner)),
        *old_actions])
    initialize_event_lease(e, doc)
    return doc


def patch_sunce_six(document):
    """Keep completion listeners independent; only this consumer gates refunds."""
    doc = deepcopy(document)
    e = Edit(doc, 134283929)
    event = trigger(doc, "RECEIVE_CUSTOM_EVENT")
    refund = anchor(event["action"], "ADD_BUFF_STACK", 105100083699022)
    owner, ability = ex(100006, "ABILITY_OWNER"), ex(100014, "CUR_ABILITY")
    lookup = ex(100076, "GET_LAST_MODIFIER_INSTANCE", owner, ex(100046, 1, CORE))
    need(refund["args_list"] == [lookup, ex(100002, 1, 1)], "six-star refund changed")
    need(event["event"][0]["args_list"] == [ex(100238, 1, 2099456001)], "completion event changed")
    e.declare(event, "MODIFIER_ENTITY", "refund_core", 0)
    saved = local("MODIFIER_ENTITY", "refund_core")
    conditions = event["condition"]
    event["condition"] = [e.exists(ability)]
    refund["args_list"][0] = deepcopy(saved)
    guarded = e.guard([
        [e.exists(owner)], [e.cond("IS_UNIT_ALIVE", owner)], conditions,
        [e.compare("BOOL_COMPARE", kv(100001, owner, EVENT_OPEN), "==", ex(100001, 1, True))],
        [e.compare("FLOAT_COMPARE", kv(100002, owner, EVENT_WAVE), "==", global_integer(WAVE)),
         e.compare("FLOAT_COMPARE", global_integer(PHASE), "==", ex(100002, 1, 2))],
    ], [e.assign("MODIFIER_ENTITY", "refund_core", kv(100076, owner, EVENT_CORE)),
        *e.guard([[e.exists(saved)],
                  [e.compare("MODIFIER_COMPARE", lookup, "==", saved),
                   e.compare("FLOAT_COMPARE", kv(100000, owner, EVENT_HITS), ">", literal(0.0))]], [
                       write_kv(e, owner, EVENT_OPEN, ex(100001, 1, False)), refund])])
    # Preserve unrelated latest P1 actions; only reparent the reviewed refund.
    splice_actions(event["action"], {refund["element_id"]: guarded})
    initialize_event_lease(e, doc)
    return doc


def load(root, relative):
    return json.loads((root / relative).read_text(encoding="utf-8-sig"))


def audit_callers(root):
    """Read actual caller defaults, all level writes, and enabled associations."""
    notes = []
    for oid, buff, key in [(134283919, 134256265, ATTACK_RATIO),
                           (134284010, 134284016, RATIO),
                           (134284012, 134284017, RATIO),
                           (134284015, 134284019, RATIO)]:
        rel = f"ability/{oid}.json"
        doc = load(root, rel)
        obj = load(root, f"editor_table/abilityall/{oid}.json")
        default = obj["kv"][key]["value"]
        need(isinstance(default, (int, float)) and not isinstance(default, bool)
             and 0 < default <= 1, f"{rel}: caller no longer uses a fractional ratio")
        writes = []
        for t in doc["trigger_dict"].values():
            for n in enabled_walk(t["action"]):
                if n.get("action_type") == "SET_ENTITY_KV" and n["args_list"][1] == ex(100003, 1, key):
                    value = n["args_list"][2]
                    need(value["sub_type"] == 1 and len(value["args_list"]) == 1
                         and 0 < value["args_list"][0] <= 1, f"{rel}: ratio write units changed")
                    writes.append({"trigger": t["trigger_id"], "value": value["args_list"][0]})
        if oid != 134283919:
            need(len(writes) == 6, f"{rel}: expected gain plus five level ratio writes")
            gain = trigger(doc, "ABILITY_OBTAIN")
            level = trigger(doc, "ABILITY_LEVEL_CHANGED")
            switches = [n for n in enabled_walk(level["action"]) if n.get("action_type") == "SWITCH"]
            need(len(switches) == 1, f"{rel}: level switch changed")
            cases = switches[0]["args_list"][1]["args_list"]
            need([v["args_list"][0]["args_list"][0] for v in cases] == [1, 2, 3, 4, 5],
                 f"{rel}: level 1..5 cases changed")
            for stage in [gain["action"], *cases]:
                setters = [n for n in enabled_walk(stage) if n.get("action_type") == "SET_ENTITY_KV"
                           and n["args_list"][1] == ex(100003, 1, key)]
                need(len(setters) == 1, f"{rel}: gain/level ratio source changed")
        calls = [n for n in enabled_walk(doc) if n.get("action_type") == "ADD_MODIFIER"
                 and n["args_list"][1] == ex(100046, 1, buff)]
        need(calls, f"{rel}: associated modifier call disappeared")
        for call in calls:
            need(call.get("op_arg_enable", [False, False])[1] is True and
                 call["op_arg"][1] == ex(100014, "CUR_ABILITY"),
                 f"{rel}: missing native related-ability parameter")
        notes.append({"status": "audited_unchanged", "file": rel, "default": default,
                      "ratio_writes": writes, "calls": len(calls)})
    shared = []
    for folder in ("ability", "modifier", "global_trigger"):
        for directory, directories, files in os.walk(root / folder):
            directories[:] = sorted(d for d in directories if d != ".git")
            for name in sorted(files):
                if not name.endswith(".json"):
                    continue
                path = Path(directory) / name
                text = path.read_text(encoding="utf-8-sig")
                if "134256265" not in text:
                    continue
                doc = json.loads(text)
                calls = [n for n in enabled_walk(doc) if n.get("action_type") == "ADD_MODIFIER"
                         and n["args_list"][1] == ex(100046, 1, 134256265)]
                if calls:
                    amounts = [n["args_list"][2] for n in enabled_walk(doc)
                               if n.get("action_type") == "SET_ENTITY_KV"
                               and n["args_list"][1] == ex(100003, 1, ATTACK_RATIO)]
                    default_file = root / "editor_table" / (folder + "all") / name
                    default = None
                    if folder in ("ability", "modifier") and default_file.is_file():
                        default = json.loads(default_file.read_text(encoding="utf-8-sig")).get(
                            "kv", {}).get(ATTACK_RATIO, {}).get("value")
                    shared.append({"file": path.relative_to(root).as_posix(), "calls": len(calls),
                                   "default": default, "ratio_write_expressions": amounts})
    notes.append({"status": "audit", "file": "modifier/134256265.json", "callers": shared,
                  "fractional_callers": list(FRACTIONAL_ATTACK_CALLERS),
                  "policy": "Convert verified fractional callers only (Xu Chu, Huang Zhong, Lu Bu, Zhuge Liang); "
                            "all other callers retain percentage-point semantics. No magnitude heuristic."})
    return notes


def build(root: Path) -> tuple[dict[str, dict], list[dict]]:
    """Re-read root each call; return detached candidates and review notes only."""
    root = Path(root)
    notes = audit_callers(root)
    candidates = {}
    for oid in MODIFIERS:
        rel = f"modifier/{oid}.json"
        # Read object settings too: cover/refresh behavior is not changed here.
        obj = load(root, f"editor_table/modifierall/{oid}.json")
        need(obj["key"] == oid, "modifier object identity changed")
        candidates[rel] = patch_modifier(load(root, rel), oid)
        notes.append({"file": rel, "status": "candidate", "issue": "P2#15",
                      "cover": {k: obj.get(k) for k in ("modifier_cover_type", "same_origin_cover",
                                  "time_change_of_cover", "layer_change_of_cover")},
                      "loss": "Original modifier-scoped CLEAR_MODIFIER_OWNER_ATTR preserved."})
    candidates[SUNCE] = patch_sunce(load(root, SUNCE))
    candidates[SUNCE_SIX] = patch_sunce_six(load(root, SUNCE_SIX))
    notes.append({"file": SUNCE, "status": "candidate", "issue": "P2#30/#31",
                  "core_file_unchanged": f"modifier/{CORE}.json",
                  "pending": ["Editor must verify native local snapshot capture in mover callbacks and terminal slots 6/7.",
                              "Engine attribute reads, cover/refresh behavior, death/loss and movement need battle acceptance.",
                              "Completion dispatch must be synchronous for the explicit open/close snapshot window; "
                              "native engine dispatch/callback capture still needs editor/runtime verification."]})
    notes.append({"file": SUNCE_SIX, "status": "candidate", "issue": "P2#30/#31 authorized dependency",
                  "protocol": "Unit snapshot: dispatch-open + exact core instance + launch wave + hit count; "
                              "six-star closes the window before one refund. Two-/six-star gain/loss close old windows.",
                  "four_star_unchanged": "ability/134283927.json",
                  "publish_together": [SUNCE, SUNCE_SIX]})
    notes.append({"status": "candidate_only", "files": sorted(candidates),
                  "actual_dependencies": "8 modifier ECAs + Sun Ce two-/six-star ECAs; four-star and four caller/default pairs read only or untouched.",
                  "validation": "offline only; no publishing or editor/runtime acceptance"})
    return candidates, notes

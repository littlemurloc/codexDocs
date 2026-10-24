"""Read-only P2 state candidates (#16/#20/#23/#24/#25); no P1 dependency.

Native evidence: 134218551 returns ADD_MODIFIER into a variable; 134248740
owns a PROJECTILE_GROUP in KV and initializes each sword's target KV. Timers,
scoped modifier attributes, GET_NEW_TABLE and typed table rows follow map3.
Unknown elite classification is deliberately NOT inferred from the JY tag.
The sword runtime's superseded blocks are kept in a disabled STORAGE_BOX,
including their IDs/unknown metadata. Tests must not execute those blocks.
"""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

MACH = "modifier/134265433.json"
ZHANG_CORE = "modifier/134259689.json"
DANHAN = "ability/134271314.json"
RECALL = "ability/134219344.json"
SPLIT = "ability/134276381.json"
FILES = (MACH, ZHANG_CORE, DANHAN, RECALL, SPLIT)
SUPPORT = "modifier/134259870.json"
SWORD_CORE = "modifier/134248740.json"
GLOBALS = "globaltriggervariable.json"
MARK = "\u9707\u6151\u5355\u4f4d"
SWORDS = "\u6e38\u5251-\u7ec4"
TARGET = "\u76ee\u6807\u5355\u4f4d"
WAVE = "\u5f53\u524d\u8fdb\u7a0b\u6240\u5728\u6ce2\u6b21\u7f16\u53f7"
PHASE = "\u5f53\u524d\u6e38\u620f\u8fdb\u7a0b\u9636\u6bb5"
CAPTAIN = "\u9635\u578b\u961f\u957f"
COMPANION = "\u4ec6\u4ece\u4f19\u4f34"
PREFIX = "P2_state_"
OWN_MARK = PREFIX + "mark_instance"
READY = PREFIX + "death_ready"
SPEED = PREFIX + "full_speed"


class ReviewRequired(ValueError):
    pass


def require(ok, message):
    if not ok:
        raise ReviewRequired(message)


def walk(x):
    if isinstance(x, dict):
        yield x
        for v in x.values():
            yield from walk(v)
    elif isinstance(x, list):
        for v in x:
            yield from walk(v)


def e(kind, subtype, *args, **extra):
    return dict(arg_type=kind, sub_type=subtype, args_list=list(args), **extra)


def lit(kind, value):
    return e(kind, 1, value)


def text(value):
    return lit(100003, value)


def i(value):
    return lit(100002, value)


def flag(value):
    return lit(100001, value)


def unit(name):
    return e(100006, name)


def buff():
    return e(100076, "CUR_MODIFIER")


def ability():
    return e(100014, "CUR_ABILITY")


def kv(entity, key, kind="UNIT_ENTITY"):
    typ, subtype = {"UNIT_ENTITY": (100006, "GET_UNIT_ENTITY_KV"),
        "MODIFIER_ENTITY": (100076, "GET_MODIFIER_ENTITY_KV"), "BOOLEAN": (100001, "GET_BOOLEAN_KV"),
        "INTEGER": (100002, "GET_INTEGER_KV"), "TABLE": (100011, "GET_TABLE_KV")}[kind]
    return e(typ, subtype, copy.deepcopy(entity), text(key))


def has(unit_expr, key):
    return e(100001, "UNIT_HAS_MODIFIER", copy.deepcopy(unit_expr), lit(100046, key))


def lookup(unit_expr, key):
    return e(100076, "GET_LAST_MODIFIER_INSTANCE", copy.deepcopy(unit_expr), lit(100046, key))


def global_int(name):
    return e(100002, 6, {"__tuple__": True, "items": ["INTEGER", name]})


def match(actual, expected):
    if isinstance(expected, dict):
        return isinstance(actual, dict) and all(k in actual and match(actual[k], v) for k, v in expected.items())
    if isinstance(expected, list):
        return isinstance(actual, list) and len(actual) == len(expected) and all(match(a, b) for a, b in zip(actual, expected))
    return type(actual) is type(expected) and actual == expected


def expect(actual, expected, label):
    require(match(actual, expected), "Native AST drift: " + label)


def trigger(doc, tid, event):
    t = doc["trigger_dict"][str(tid)]
    require(t["trigger_id"] == tid and any(x.get("event_type") == event and x.get("enable") is True for x in t["event"]),
            "Missing native event " + event)
    return t


def one(nodes, kind, element_id=None):
    found = [x for x in walk(nodes) if x.get("action_type") == kind and
             (element_id is None or x.get("element_id") == element_id)]
    require(len(found) == 1, "Expected one " + kind + " / " + str(element_id))
    require(found[0].get("enable") is True, "Target action disabled")
    return found[0]


class Nodes:
    def __init__(self, doc, resource):
        self.doc = doc
        self.used = {x["element_id"] for x in walk(doc) if "element_id" in x}
        self.serial = resource * 1_000_000 + 920_000

    def new_id(self):
        self.serial += 1
        while self.serial in self.used:
            self.serial += 1
        self.used.add(self.serial)
        return self.serial

    def action(self, kind, *args, **extra):
        n = dict(action_type=kind, args_list=list(args), element_id=self.new_id(), enable=True, bp=False, **extra)
        if kind == "IF_THEN_ELSE":
            n["fake_op"] = []
        return n

    def cond(self, kind, *args):
        return dict(condition_type=kind, args_list=list(args), element_id=self.new_id(), enable=True)

    def cmp(self, a, op, b, kind="FLOAT_COMPARE"):
        return self.cond(kind, copy.deepcopy(a), lit(100015 if kind == "FLOAT_COMPARE" else 100035, op), copy.deepcopy(b))

    def yes(self, expr):
        return self.cmp(expr, "==", flag(True), "BOOL_COMPARE")

    def branch(self, checks, actions, otherwise=()):
        return self.action("IF_THEN_ELSE", e(100021, 1, *checks), e(100022, 1, *actions), e(100022, 1, *otherwise))

    def exists(self, obj, actions):
        require(obj["arg_type"] in (100006, 100014), "Unverified existence overload")
        return self.branch([self.cond("TYPE_IS_EXIST", copy.deepcopy(obj))], actions)

    def set(self, var, value):
        return self.action("SET_VARIABLE", e(100030, 1, *copy.deepcopy(var["args_list"])), copy.deepcopy(value))

    def setkv(self, obj, key, value):
        return self.action("SET_ENTITY_KV", copy.deepcopy(obj), text(key), copy.deepcopy(value))

    def var(self, kind, name, tid=None):
        name = PREFIX + name
        typ, sub, default = {"UNIT_ENTITY": (100006, 11, 0), "MODIFIER_ENTITY": (100076, 11, None),
            "PROJECTILE_ENTITY": (100077, "VARIABLE", 0), "INTEGER": (100002, 6, 0),
            "BOOLEAN": (100001, "VARIABLE", False), "TABLE": (100011, "VARIABLE", None)}[kind]
        if tid is None:
            values, lengths = self.doc["variable_dict"], self.doc["variable_length_dict"]
            require(name not in lengths, "Candidate actor variable exists: " + name)
            values.setdefault(kind, {})[name] = default
            lengths[name] = 0
            self.doc["variable_group_info"].append({"__tuple__": True, "items": [name, name]})
            scope = "actor"
        else:
            t = self.doc["trigger_dict"][str(tid)]
            values, lengths, order = t["var_data"]
            require(name not in lengths, "Candidate local variable exists: " + name)
            values.setdefault(kind, {})[name] = default
            lengths[name] = 0
            order.append(name)
            local = self.doc["local_variable"][str(tid)]
            local["variable_dict"].setdefault(kind, {})[name] = default
            local["variable_length_dict"][name] = 0
            scope = "local"
        return e(typ, sub, {"__tuple__": True, "items": [kind, name, scope]})

    def clone(self, node):
        result = copy.deepcopy(node)
        for x in walk(result):
            if "element_id" in x:
                x["element_id"] = self.new_id()
        return result

    def legacy(self, actions):
        box = self.action("STORAGE_BOX", e(100021, 1), e(100022, 1, *actions), e(100022, 1),
                          text("P2 superseded state logic (disabled reference only)"))
        box["enable"] = False
        return box


def with_core(n, owner, resource, core, actions):
    return n.exists(owner, [n.branch([n.yes(has(owner, resource))], [n.set(core, lookup(owner, resource)), *actions])])


def same_core(n, owner, resource, core, actions):
    return n.exists(owner, [n.branch([n.yes(has(owner, resource))], [
        n.branch([n.cmp(core, "==", lookup(owner, resource), "MODIFIER_COMPARE")], actions)])])


def captain_check(n, target):
    return n.cond("OR", e(100021, 1,
        n.cond("UNIT_HAS_TAG", copy.deepcopy(target), text(COMPANION)),
        n.cond("UNIT_HAS_TAG", copy.deepcopy(target), text(CAPTAIN))))


def patch_mach(doc, n):
    gain = trigger(doc, 1485688834, "OBTAIN_MODIFIER")
    death = trigger(doc, 2133540868, "GENERIC_UNIT_EVENT")
    layer = trigger(doc, 1050472449, "MODIFIER_LAYER_CHANGE")
    loss = trigger(doc, 594665475, "LOSS_MODIFIER")
    expect(gain["action"], [2133540868, 539815941], "Ma Chao registration")
    require(len(death["action"]) == 2, "Changed death payload")
    expect(death["action"][0], {"action_type": "ADD_BUFF_STACK", "enable": True, "args_list": [buff(), i(1)]}, "death stack")
    require(any(a.get("action_type") == "CLEAR_MODIFIER_OWNER_ATTR" and a.get("enable") is True and a["args_list"] == [buff()]
                for a in loss["action"]), "Missing core-scoped cleanup")
    full = one(layer["action"], "IF_THEN_ELSE", 539815941000023)
    speed = one(full, "ADD_MODIFIER_OWNER_ATTR", 1050472449000163)
    expect(speed["args_list"], [buff(), lit(100042, "attack_speed"), lit(100300, "ATTR_ALL_RATIO"), lit(100000, 10.0)], "full attack speed")
    state_check = full["args_list"][0]["args_list"][1]
    expect(state_check, {"condition_type": "BOOL_COMPARE", "enable": True,
        "args_list": [kv(buff(), "3\u5c42\u989d\u5916\u5904\u7406", "BOOLEAN"), lit(100035, "=="), flag(False)]}, "legacy full marker")
    state_check["args_list"][0]["args_list"][1]["args_list"][0] = SPEED
    full["args_list"][1]["args_list"].insert(0, n.setkv(buff(), SPEED, flag(True)))
    below = n.branch([n.cmp(e(100002, "GET_MOD_STACK", buff()), "<", e(100002, "GET_MOD_STACK_MAX", buff()))], [
        n.branch([n.yes(kv(buff(), SPEED, "BOOLEAN"))], [n.setkv(buff(), SPEED, flag(False)),
            n.action("ADD_MODIFIER_OWNER_ATTR", buff(), lit(100042, "attack_speed"), lit(100300, "ATTR_ALL_RATIO"), lit(100000, -10.0))])])
    layer["action"].append(below)
    carrier = n.var("UNIT_ENTITY", "mach_carrier")
    gain["action"][0:0] = [n.set(carrier, unit("MODIFIER_OWNER")), n.setkv(buff(), READY, flag(True)), n.setkv(buff(), SPEED, flag(False))]
    unlock = same_core(n, carrier, 134265433, buff(), [n.setkv(buff(), READY, flag(True))])
    timer = n.action("RUN_ONCE_TIMER_NO_SAVE", lit(100000, 2.0), e(100022, 1, unlock))
    death["action"] = [n.branch([n.yes(kv(buff(), READY, "BOOLEAN"))],
                              [n.setkv(buff(), READY, flag(False)), *death["action"], timer])]
    loss["action"][0:0] = [n.setkv(buff(), READY, flag(False)), n.setkv(buff(), SPEED, flag(False))]


def patch_zhang_core(doc, n):
    t = trigger(doc, 1418035204, "SPECIAL_UNIT_EVENT")
    require(len(t["action"]) == 3, "Changed first/same/new-target routing")
    first, same, changed = t["action"]
    for a, eid in zip((first, same, changed), (1418035204974660, 1418035204974736, 1418035204974489)):
        expect(a, {"action_type": "IF_THEN_ELSE", "element_id": eid, "enable": True}, "target branch")
        require(not a["args_list"][2]["args_list"], "User ELSE payload requires review")
    target_expression = e(100006, "TARGET_UNIT_IN_ABILITY", e(100014, "DAMAGE_ABILITY"))
    for branch, left, op, right in (
        (first, kv(buff(), MARK), "==", unit("NONE_UNIT")),
        (same, target_expression, "==", kv(buff(), MARK)),
        (changed, target_expression, "!=", kv(buff(), MARK)),
    ):
        expect(branch["args_list"][0]["args_list"], [{"condition_type": "UNIT_COMPARE", "enable": True,
            "args_list": [left, lit(100035, op), right]}], "first/same/new-target routing")
    additions = [x for x in walk(t["action"]) if x.get("action_type") == "ADD_MODIFIER"]
    require(len(additions) == 3, "Expected three intimidation add sites")
    created = n.var("MODIFIER_ENTITY", "created_mark", 1418035204)
    for add in additions:
        expect(add, {"enable": True, "args_list": [kv(buff(), MARK), lit(100046, 134259870)],
            "op_arg_enable": [True, True, True, False, True, False]}, "intimidation add")
        expect(add["op_arg"][2], lit(100000, 300.0), "intimidation lifetime")
        add["op_arg"][2]["args_list"][0] = 8.0
        expression = e(100076, "ADD_MODIFIER", *copy.deepcopy(add["args_list"]))
        for key in ("op_arg", "op_arg_enable"):
            expression[key] = add.pop(key)
        add["action_type"] = "SET_VARIABLE"
        add["args_list"] = [copy.deepcopy(created), expression]
    # Append the exact created instance after the original add at every branch.
    for branch in (first, same, changed):
        branch["args_list"][1]["args_list"].append(n.setkv(buff(), OWN_MARK, created))
    same["args_list"][2]["args_list"] = [changed]
    first["args_list"][2]["args_list"] = [same]
    source_ability = e(100014, "DAMAGE_ABILITY")
    target = n.var("UNIT_ENTITY", "cast_mark_target", 1418035204)
    native_conditions = t["condition"]
    require(len(native_conditions) == 1, "Changed release-skill eligibility")
    t["condition"] = []
    t["action"] = [n.exists(source_ability, [n.branch(native_conditions, [
        n.exists(unit("MODIFIER_OWNER"), [
            n.set(target, e(100006, "TARGET_UNIT_IN_ABILITY", source_ability)), n.exists(target, [
                n.branch([n.cond("IS_UNIT_ALIVE", copy.deepcopy(target)),
                          n.cond("IS_ENEMY", copy.deepcopy(target), unit("MODIFIER_OWNER"))], [first])])])])])]


def once_wave(n, owner, key, payload, tid):
    allowed = n.var("BOOLEAN", key + "_allowed", tid)
    return [n.set(allowed, flag(True)),
        n.branch([n.cond("HAS_KV_ANY", copy.deepcopy(owner), text(PREFIX + key))], [
            n.branch([n.cmp(kv(owner, PREFIX + key, "INTEGER"), "==", global_int(WAVE))], [n.set(allowed, flag(False))])]),
        n.branch([n.cmp(global_int(WAVE), ">", i(0)), n.cmp(global_int(PHASE), "==", i(2)), n.yes(allowed)],
                 [n.setkv(owner, PREFIX + key, global_int(WAVE)), *payload])]


def patch_danhan(doc, n):
    t = trigger(doc, 1051000836, "GLOBAL_MODIFIER_EVENT")
    require(len(t["condition"]) == 2 and len(t["action"]) == 1, "Changed max-stack passive")
    add = t["action"][0]
    expect(add, {"action_type": "ADD_MODIFIER", "element_id": 892944388000009, "enable": True,
                 "args_list": [unit("ABILITY_OWNER"), lit(100046, 134264250)]}, "self-targeting fear")
    old_class, old_full = t["condition"]
    expect(old_class, {"condition_type": "MODIFIER_CLASS_COMPARE", "enable": True,
        "args_list": [e(100046, "GET_MODIFIER_ENTITY_METATYPE", e(100076, "GET_MODIFIER_FROM_EVENT")),
                      lit(100035, "=="), lit(100046, 134259870)]}, "layer event class")
    old_lookup = lookup(unit("MODIFIER_OWNER"), 134259870)
    old_stack, old_max = e(100002, "GET_MOD_STACK", old_lookup), e(100002, "GET_MOD_STACK_MAX", old_lookup)
    expect(old_full, {"condition_type": "FLOAT_COMPARE", "enable": True,
        "args_list": [old_stack, lit(100015, ">="), old_max]}, "max-stack check")
    require(old_full["args_list"][0] == old_stack and old_full["args_list"][2] == old_max,
            "Unreviewed max-stack operand metadata would be displaced")
    owner = unit("ABILITY_OWNER")
    core = n.var("MODIFIER_ENTITY", "fear_core", 1051000836)
    target = n.var("UNIT_ENTITY", "fear_target", 1051000836)
    current = n.var("MODIFIER_ENTITY", "fear_mark", 1051000836)
    history = n.var("TABLE", "fear_history", 1051000836)
    row = n.var("INTEGER", "fear_row", 1051000836)
    seen = n.var("BOOLEAN", "fear_seen", 1051000836)
    add["args_list"][0] = copy.deepcopy(target)
    old_full["args_list"][0] = e(100002, "GET_MOD_STACK", copy.deepcopy(current))
    old_full["args_list"][2] = e(100002, "GET_MOD_STACK_MAX", copy.deepcopy(current))
    key, wavekey = PREFIX + "fear_targets", PREFIX + "fear_wave"
    initialize = [n.set(history, e(100011, "GET_NEW_TABLE")), n.setkv(owner, key, history), n.setkv(owner, wavekey, global_int(WAVE))]
    get_history = n.branch([n.cond("HAS_KV_ANY", owner, text(wavekey))], [
        n.branch([n.cmp(kv(owner, wavekey, "INTEGER"), "==", global_int(WAVE))], [
            n.branch([n.cond("HAS_KV_ANY", owner, text(key))], [n.set(history, kv(owner, key, "TABLE"))],
                     [n.clone(a) for a in initialize])], [n.clone(a) for a in initialize])], initialize)
    length = e(100002, "GET_TABLE_LENGTH", copy.deepcopy(history))
    remembered = e(100006, "GET_UNIT_ENTITY_TABLE_VAR_ND", copy.deepcopy(history), copy.deepcopy(row), text("target"))
    loop = n.action("FOR_INT_DO_ACTION_NEW", copy.deepcopy(row), i(1), length,
        e(100022, 1, n.branch([n.cmp(remembered, "==", target, "UNIT_COMPARE")], [n.set(seen, flag(True))])),
        op_arg=[None], op_arg_enable=[False])
    record = n.action("SET_TABLE_VALUE_ND", copy.deepcopy(history), e(100002, "INT_PLUS_ONE", copy.deepcopy(length)), text("target"), copy.deepcopy(target))
    settle = [get_history, n.set(seen, flag(False)), loop,
              n.branch([n.cmp(seen, "==", flag(False), "BOOL_COMPARE")], [record, add])]
    qualified = n.branch([old_full, n.cmp(global_int(WAVE), ">", i(0)), n.cmp(global_int(PHASE), "==", i(2))], settle)
    identity = [n.cmp(current, "==", e(100076, "GET_MODIFIER_FROM_EVENT"), "MODIFIER_COMPARE"),
                n.cmp(current, "==", kv(core, OWN_MARK, "MODIFIER_ENTITY"), "MODIFIER_COMPARE")]
    body = n.branch([n.cond("HAS_KV_ANY", copy.deepcopy(core), text(MARK)),
                     n.cond("HAS_KV_ANY", copy.deepcopy(core), text(OWN_MARK))], [
        n.set(target, kv(core, MARK)), n.exists(target, [
            n.branch([n.cond("IS_UNIT_ALIVE", copy.deepcopy(target)), n.cond("IS_ENEMY", copy.deepcopy(target), owner),
                      captain_check(n, target)], [
                n.branch([n.yes(has(target, 134259870))], [n.set(current, lookup(target, 134259870)),
                    n.branch(identity, [qualified])])])])])
    t["condition"] = [old_class]
    t["action"] = [with_core(n, owner, 134259689, core, [body])]


def scan_swords(n, tid, owner, core):
    count = n.var("INTEGER", "sword_count", tid)
    different = n.var("BOOLEAN", "sword_different", tid)
    temp = n.var("UNIT_ENTITY", "sword_target", tid)
    targets = [n.var("UNIT_ENTITY", "sword_target" + str(k), tid) for k in (1, 2, 3)]
    swords = [n.var("PROJECTILE_ENTITY", "sword" + str(k), tid) for k in (1, 2, 3)]
    selected = e(100077, "FOR_EACH_SELECTED_PROJECTILE")
    initialize = [n.set(count, i(0)), n.set(different, flag(False))]
    initialize += [n.set(t, unit("NONE_UNIT")) for t in targets]
    capture = [n.set(count, e(100002, "INT_PLUS_ONE", copy.deepcopy(count)))]
    for k, (sword, target) in enumerate(zip(swords, targets), 1):
        capture.append(n.branch([n.cmp(count, "==", i(k))], [n.set(sword, selected), n.set(target, temp)]))
    capture.append(n.branch([n.cmp(temp, "!=", targets[0], "UNIT_COMPARE")], [n.set(different, flag(True))]))
    visit = n.branch([n.cond("HAS_KV_ANY", copy.deepcopy(selected), text(TARGET))], [
        n.set(temp, kv(selected, TARGET)), n.exists(temp, [
            n.branch([n.cond("IS_UNIT_ALIVE", copy.deepcopy(temp)),
                      n.cond("IS_ENEMY", copy.deepcopy(temp), copy.deepcopy(owner))], capture)])])
    group = e(100203, "GET_PROJECTILE_GROUP_KV", copy.deepcopy(core), text(SWORDS))
    initialize.append(n.action("PICK_PROJECTILE_DO_ACTION", group, e(100022, 1, visit)))
    return initialize, count, different, targets, swords


def safe_damage(n, damage, owner, target, wave):
    damage["args_list"][2] = copy.deepcopy(target)
    return n.exists(ability(), [n.exists(owner, [n.exists(target, [n.branch([
        n.cmp(global_int(WAVE), ">", i(0)), n.cmp(global_int(WAVE), "==", wave), n.cmp(global_int(PHASE), "==", i(2)),
        n.cond("IS_UNIT_ALIVE", copy.deepcopy(target)), n.cond("IS_ENEMY", copy.deepcopy(target), copy.deepcopy(owner))], [damage])])])])


def sword_payload(n, damage, timer, sfx, mover, owner, targets, swords, recall, wave):
    require(damage["args_list"][2] == e(100006, 11, {"__tuple__": True, "items": ["UNIT_ENTITY", TARGET, "actor"]}),
            "Unreviewed damage-target operand would be displaced")
    require(sfx["args_list"][1] == e(100004, "PROJECTILE_ENTITY_POINT", e(100077, "FOR_EACH_SELECTED_PROJECTILE")),
            "Unreviewed projectile-point operand would be displaced")
    payload = []
    for target, sword in zip(targets, swords):
        hit, delay, visual = n.clone(damage), n.clone(timer), n.clone(sfx)
        visual["args_list"][1] = e(100004, "PROJECTILE_ENTITY_POINT", copy.deepcopy(sword))
        payload.append(visual)
        if recall:
            # Synchronous capture/recall: no projectile reads survive the delay.
            payload.append(n.setkv(sword, TARGET, owner))
            orbit = n.clone(mover)
            orbit["args_list"][0] = copy.deepcopy(sword)
            orbit["args_list"][1] = copy.deepcopy(owner)
            payload.append(orbit)
        delay["args_list"][1]["args_list"] = [safe_damage(n, hit, owner, target, wave)]
        payload.append(delay)
    return payload


def validate_sword_dependencies(core, globals_doc):
    require(WAVE in globals_doc["variable_dict"]["INTEGER"], "Missing real wave declaration")
    require(any(x.get("action_type") == "SET_ENTITY_KV" and match(x.get("args_list", []),
                [buff(), text(SWORDS), e(100203, "CREATE_PROJECTILE_GOURP")]) for x in walk(core)), "Sword group initialization differs")
    require(any(x.get("action_type") == "SET_ENTITY_KV" and len(x.get("args_list", [])) == 3 and
                x["args_list"][1] == text(TARGET) for x in walk(core)), "Missing sword target initialization")
    require(any(x.get("action_type") == "SEND_CUSTOM_EVENT" and match(x.get("args_list", []),
                [lit(100238, 1710648125), unit("MODIFIER_OWNER"), e(100014, "DAMAGE_ABILITY"), unit("DAMAGE_TARGET_UNIT")])
                for x in walk(core)), "Sword custom event no longer supplies the inspected trigger-unit")


def patch_recall(doc, n):
    gain = trigger(doc, 1959489540, "ABILITY_OBTAIN")
    cast = trigger(doc, 893440004, "ABILITY_SP_END")
    timer = one(gain["action"], "RUN_LOOP_TIMER")
    old_loop_body = timer["args_list"][3]["args_list"]
    require(len(old_loop_body) == 1, "Changed auto-cast timer body")
    auto = old_loop_body[0]
    expect(auto, {"action_type": "IF_THEN_ELSE", "element_id": 1959489540974074, "enable": True}, "auto gate")
    old_scan = one(auto, "PICK_PROJECTILE_DO_ACTION", 1959489540974534)
    expect(old_scan["args_list"][0], e(100203, "GET_PROJECTILE_GROUP_KV", lookup(unit("ABILITY_OWNER"), 134248740), text(SWORDS)), "failing core group read")
    release = one(auto, "UNIT_RELEASE_COMMAND")
    command = release["args_list"][1]
    require(command["op_arg_enable"] == [False, False, True, False, False], "Changed skill-command option positions")
    actor_target = command["op_arg"][2]
    require(actor_target["arg_type"] == 100006, "Changed command target")
    auto_core = n.var("MODIFIER_ENTITY", "auto_core", 1959489540)
    owner = unit("ABILITY_OWNER")
    scan, count, different, targets, _ = scan_swords(n, 1959489540, owner, auto_core)
    release = n.clone(release)
    release["args_list"][1]["op_arg"][2] = copy.deepcopy(targets[0])
    checks = copy.deepcopy(auto["args_list"][0]["args_list"])
    for c in checks:
        c["element_id"] = n.new_id()
    ability_check = checks.pop(0)
    expect(ability_check, {"condition_type": "TYPE_IS_EXIST", "args_list": [ability()]}, "ability guard")
    qualified = n.branch([n.cmp(count, "==", i(3)), n.cmp(different, "==", flag(False), "BOOL_COMPARE"),
        captain_check(n, targets[0])], [n.set(actor_target, targets[0]), release])
    # Role reads happen only after an actual target was found, not in an eager conjunction.
    qualified["args_list"][0]["args_list"].pop()
    role_guard = n.exists(targets[0], [n.branch([captain_check(n, targets[0])],
                        qualified["args_list"][1]["args_list"])])
    qualified["args_list"][1]["args_list"] = [role_guard]
    safe = n.branch([ability_check], [n.exists(owner, [n.branch(checks, [
        n.set(actor_target, unit("NONE_UNIT")), with_core(n, owner, 134248740, auto_core, [
            n.branch([n.cond("HAS_KV_ANY", copy.deepcopy(auto_core), text(SWORDS))], [*scan, qualified])])])])])
    timer["args_list"][3]["args_list"] = [n.legacy(old_loop_body), safe]

    old = cast["action"]
    require(len(old) == 4, "Changed recall spell payload")
    damage = one(old, "APPLY_DAMAGE")
    delay = one(old, "RUN_ONCE_TIMER_NO_SAVE")
    visual = one(old, "CREATE_SFX_ON_POINT_NEW")
    orbit = one(old, "CREATE_ROUND_MOVER", 1878966277000730)
    final_damage = old[1]
    expect(final_damage, {"action_type": "SET_VARIABLE", "element_id": 893440004975259}, "spell damage snapshot")
    final_damage = n.clone(final_damage)
    core = n.var("MODIFIER_ENTITY", "cast_core", 893440004)
    damage_wave = n.var("INTEGER", "recall_damage_wave", 893440004)
    scan, count, different, targets, swords = scan_swords(n, 893440004, owner, core)
    effect = sword_payload(n, damage, delay, visual, orbit, owner, targets, swords, True, damage_wave)
    # Keep animation and its current parameters; manual target cannot override sword qualification.
    animation = n.clone(old[2])
    qualified = n.branch([n.cmp(count, "==", i(3)), n.cmp(different, "==", flag(False), "BOOL_COMPARE")], [
        n.exists(targets[0], [n.branch([captain_check(n, targets[0])],
            [n.set(damage_wave, global_int(WAVE)), final_damage, animation, *effect])])])
    cast["action"] = [n.legacy(old), n.exists(ability(), [with_core(n, owner, 134248740, core, [
        n.branch([n.cond("HAS_KV_ANY", copy.deepcopy(core), text(SWORDS))], [*scan, qualified])])])]


def patch_split(doc, n):
    t = trigger(doc, 1756393476, "RECEIVE_CUSTOM_EVENT")
    old = t["action"]
    require(len(old) == 2, "Changed split-sword passive")
    damage = one(old, "APPLY_DAMAGE")
    delay = one(old, "RUN_ONCE_TIMER_NO_SAVE")
    visual = one(old, "CREATE_SFX_ON_POINT_NEW")
    owner = unit("ABILITY_OWNER")
    # The sword core explicitly sends its owner as trigger-unit; normal hits
    # need not supply a damage-ability instance.
    require(len(t["condition"]) == 1, "Changed sword custom-event checks")
    old_condition = t["condition"][0]
    event_skill = old_condition["args_list"][0]["args_list"][0]
    expect(event_skill, e(100014, "GET_CUS_EVENT_PARAM", lit(100240, "\u89e6\u53d1\u6280\u80fd")), "custom-event ability")
    core = n.var("MODIFIER_ENTITY", "split_core", 1756393476)
    damage_wave = n.var("INTEGER", "split_damage_wave", 1756393476)
    scan, count, different, targets, swords = scan_swords(n, 1756393476, owner, core)
    effect = [n.set(damage_wave, global_int(WAVE)), *sword_payload(n, damage, delay, visual, None, owner, targets, swords, False, damage_wave)]
    effect = once_wave(n, owner, "split_wave", effect, 1756393476)
    qualified = n.branch([n.cmp(count, "==", i(3)), n.yes(different)], effect)
    body = with_core(n, owner, 134248740, core, [
        n.branch([n.cond("HAS_KV_ANY", copy.deepcopy(core), text(SWORDS))], [*scan, qualified])])
    event_unit = e(100006, "GET_CUS_EVENT_PARAM", lit(100240, "\u89e6\u53d1\u5355\u4f4d"))
    condition_copy = n.cmp(event_unit, "==", owner, "UNIT_COMPARE")
    t["condition"] = []
    reference = n.legacy(old)
    reference["args_list"][0]["args_list"] = [old_condition]
    t["action"] = [reference, n.exists(ability(), [n.exists(owner, [n.exists(event_unit, [
        n.branch([condition_copy], [body])])])])]


def unique(pairs):
    d = {}
    for key, value in pairs:
        require(key not in d, "Duplicate JSON key " + key)
        d[key] = value
    return d


def reject_constant(value):
    raise ReviewRequired("Nonfinite JSON constant " + value)


def build(root: Path) -> tuple[dict[str, dict], list[dict]]:
    """Read latest root; return in-memory candidates and review boundaries."""
    root = Path(root)
    candidates, reports, loaded = {}, [], {}
    raw = {}
    for relative in (*FILES, SUPPORT, SWORD_CORE, GLOBALS):
        try:
            raw[relative] = (root / relative).read_bytes()
            loaded[relative] = json.loads(raw[relative].decode("utf-8-sig"), object_pairs_hook=unique, parse_constant=reject_constant)
        except (OSError, UnicodeError, ValueError) as error:
            reports.append(dict(path=relative, severity="error", code="read_failed", message=str(error)))
    for relative, patcher in zip(FILES, (patch_mach, patch_zhang_core, patch_danhan, patch_recall, patch_split)):
        try:
            require(relative in loaded, "Input unavailable")
            if relative == DANHAN:
                require(ZHANG_CORE in candidates, "Requires successful #23 core-instance cache candidate")
            if relative in (DANHAN, RECALL, SPLIT):
                require(GLOBALS in loaded and all(k in loaded[GLOBALS]["variable_dict"]["INTEGER"] for k in (WAVE, PHASE)), "Real wave/phase declaration unavailable")
            if relative in (RECALL, SPLIT):
                require(SWORD_CORE in loaded, "Sword lifecycle evidence unavailable")
                validate_sword_dependencies(loaded[SWORD_CORE], loaded[GLOBALS])
            doc = copy.deepcopy(loaded[relative])
            patcher(doc, Nodes(doc, int(Path(relative).stem)))
            candidates[relative] = doc
            reports.append(dict(path=relative, severity="info", code="p2_state_candidate",
                                source_sha256=hashlib.sha256(raw[relative]).hexdigest()))
        except (ReviewRequired, KeyError, TypeError, ValueError, IndexError, AttributeError) as error:
            reports.append(dict(path=relative, severity="error", code="review_required", message=str(error), candidate_omitted=True))
    if SUPPORT in raw:
        reports.append(dict(path=SUPPORT, severity="info", code="p1_preserved_read_only",
                            source_sha256=hashlib.sha256(raw[SUPPORT]).hexdigest(),
                            message="No candidate emitted; published P1 source/formula/LOSS AST is untouched. Durations change at the three #23 add sites."))
    for relative in (SWORD_CORE, GLOBALS):
        if relative in raw:
            reports.append(dict(path=relative, severity="info", code="read_only_dependency",
                                source_sha256=hashlib.sha256(raw[relative]).hexdigest()))
    reports.extend([
        dict(severity="warning", code="elite_mapping_review", paths=[DANHAN, RECALL],
             message="Verified leader union: companion OR formation captain, including player/mirror heroes. JY also labels standard archers, so no elite alias is invented. Elite-only eligibility remains unresolved and is excluded by the candidate."),
        dict(severity="warning", code="native_callback_review", paths=[RECALL, SPLIT],
             message="SFX and recall movement/state commit synchronously; original random damage delay is retained with three independent target slots and ordered ability/unit/alive/enemy and captured-wave guards. No projectile is read after delay. Three delay timers and local-slot capture require editor/runtime tests. Sword-group iteration validity follows the inspected owning-core lifecycle, not a fabricated projectile-exists API."),
        dict(severity="warning", code="verification_boundary",
             message="Candidate only; no writes/import/save/reload. #23 retains native DAMAGE_ABILITY in ET_UNIT_RELEASE_ABILITY and optional related ability; event availability and same-origin buff-cover ordering need engine verification. #16 preserves native death eligibility; its formal-minion tagging remains outside this numeric/state patch. Inspect disabled legacy boxes as reference, never as runtime evidence.")])
    return candidates, reports

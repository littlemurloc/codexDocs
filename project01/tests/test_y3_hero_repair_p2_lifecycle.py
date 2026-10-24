"""Native AST + explicit sequence contracts, not a Y3 engine emulator.

Self-contained native slices reproduce the old faults first. Optional actual-map
checks verify current input, P1 preservation, enum evidence, and read-only build.
Timer locals are explicitly snapshotted as in the inspected native example;
tests do not claim actual engine capture/timing/registration was exercised.
"""

from collections import Counter
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools import y3_hero_repair_p2_lifecycle as p


def x(kind, sub=1, *args):
    return {"arg_type": kind, "sub_type": sub, "args_list": list(args)}


def action(name, eid, *args, enabled=True):
    return {"action_type": name, "element_id": eid, "args_list": list(args), "enable": enabled, "bp": False}


def condition(name, eid, *args):
    return {"condition_type": name, "element_id": eid, "args_list": list(args), "enable": True}


def variable(kind, name, scope="actor", lhs=False):
    types = {"MODIFIER_ENTITY": (100076, 11), "UNIT_ENTITY": (100006, 11), "ABILITY": (100014, 2),
             "BOOLEAN": (100001, "VARIABLE"), "INTEGER": (100002, 6), "NEW_TIMER": (100181, "VARIABLE")}
    typ, sub = types[kind]
    if lhs:
        typ, sub = 100030, 1
    return x(typ, sub, {"__tuple__": True, "items": [kind, name, scope]})


def fixtures():
    """Reviewed native slices; unrelated presentation AST is omitted, not faked."""
    serial = 900719925474099300
    def fresh():
        nonlocal serial
        serial += 1
        return serial
    def a(name, *args):
        return action(name, fresh(), *args)
    def c(name, *args):
        return condition(name, fresh(), *args)
    def guard(stages, acts):
        for stage in reversed(stages):
            acts = [a("IF_THEN_ELSE", x(100021, 1, *stage), x(100022, 1, *acts), x(100022, 1))]
        return acts
    def eq(name, left, right):
        return c(name, left, x(100035, 1, "=="), right)
    def exists(v):
        return c("TYPE_IS_EXIST", v)
    def t(tid, event, acts, parent=None, args=None):
        out = {"trigger_id": tid, "trigger_name": "native", "group_id": 0, "enabled": parent is None,
               "call_enabled": True, "valid": True, "p_trigger_id": parent, "condition": [],
               "action": acts, "event": [{"event_type": event, "enable": True, "element_id": fresh(),
                                           "args_list": args or []}], "var_data": [{}, {}, []]}
        if parent is not None:
            name = "temp2" if tid == 173064198 else "temp"
            out["sub_trigger_owner_set_var_action"] = a("SET_VARIABLE",
                x(100178, "VARIABLE", ["DYNAMIC_TRIGGER_INSTANCE", name, "actor"]),
                x(100178, "REG_MODIFIER_TRIGGER", x(100069, 1, tid)))
        return out
    def doc(ts, group=0):
        for trigger in ts:
            trigger["group_id"] = group
        return {"trigger_dict": {str(t["trigger_id"]): t for t in ts},
                "local_variable": {str(t["trigger_id"]): {"variable_dict": {}, "variable_length_dict": {}} for t in ts},
                "variable_dict": {}, "variable_length_dict": {}, "variable_group_info": [],
                "trigger_group_info": [], "trigger_version": "1.2", "user_unknown": {"big": 900719925474099312345}}
    cm, ca, owner = x(100076, "CUR_MODIFIER"), x(100014, "CUR_ABILITY"), x(100006, "MODIFIER_OWNER")
    cd, da = x(100003, 1, "\u5185\u7f6eCD"), x(100014, "DAMAGE_ABILITY")
    def last(unit, key):
        return x(100076, "GET_LAST_MODIFIER_INSTANCE", unit, x(100046, 1, key))
    def classifier(eid):
        fn = x(100001, p.MELEE_HELPER, da, x(100003, 1, "\u8fd1\u6218\u666e\u653b"))
        fn.update(call_rt_index=0, op_arg=[], op_arg_enable=[])
        return condition("FUNC_CONDITION", eid, fn)

    old = variable("MODIFIER_ENTITY", "P1_lifecycle_core_instance")
    handle = variable("NEW_TIMER", "P1_lifecycle_eight_seconds")
    active = variable("BOOLEAN", "P1_lifecycle_core_active")
    pending = variable("BOOLEAN", "P1_lifecycle_timer_pending")
    def bound():
        return [[exists(cm), exists(old)], [eq("MODIFIER_COMPARE", cm, old), exists(owner),
                eq("BOOL_COMPARE", active, x(100001, 1, True))],
                [eq("MODIFIER_COMPARE", last(owner, 134277456), old),
                 eq("BOOL_COMPARE", pending, x(100001, 1, True))]]
    callback = [action("SET_BUFF_STACK", 1418035204974518, cm, x(100002, 1, 1), enabled=False),
        *guard(bound(), [action("SET_BUFF_STACK", 1473785861000046, old, x(100002, 1, 1))]),
        *guard(bound(), [a("SET_VARIABLE", variable("BOOLEAN", "P1_lifecycle_timer_pending", lhs=True), x(100001, 1, False)),
                        action("SET_ENTITY_KV", 1418035204974592, old, cd, x(100001, 1, False))])]
    timer = action("RUN_ONCE_TIMER", 1418035204974513, handle, x(100000, 1, 8.0), x(100022, 1, *callback))
    timer["local_var"] = {"__tuple__": True, "items": [{}, {}]}
    letter = action("ADD_MODIFIER", 1418035204974502, x(100006, "DAMAGE_TARGET_UNIT"), x(100046, 1, 134274015))
    letter.update(op_arg=[owner, da, x(100000, 1, 8.0), None, None, None], op_arg_enable=[True, True, True, False, False, False])
    th = t(1418035204, "SPECIAL_UNIT_EVENT", [
        action("SET_ENTITY_KV", 1418035204974580, cm, cd, x(100001, 1, True)),
        action("ADD_BUFF_STACK", 1418035204974461, cm, x(100002, 1, 1)), letter,
        *guard(bound()[:-1], [a("DELETE_TIMER", handle),
          a("SET_VARIABLE", variable("BOOLEAN", "P1_lifecycle_timer_pending", lhs=True), x(100001, 1, True)), timer])], 1485688834)
    th["condition"] = [condition("BOOL_COMPARE", 1418035204974479, x(100001, "GET_BOOLEAN_KV", cm, cd),
                                 x(100035, 1, "=="), x(100001, 1, False)),
                       condition("BOOL_NOT", 1418035204974459, x(100001, "GET_IS_NORMAL_HIT_FROM_EVENT"))]
    ts = doc([t(1485688834, "OBTAIN_MODIFIER", [
        a("SET_VARIABLE", variable("MODIFIER_ENTITY", "P1_lifecycle_core_instance", lhs=True), cm),
        a("SET_VARIABLE", variable("BOOLEAN", "P1_lifecycle_core_active", lhs=True), x(100001, 1, True)),
        a("SET_VARIABLE", variable("BOOLEAN", "P1_lifecycle_timer_pending", lhs=True), x(100001, 1, False)), 1418035204]),
        t(594665475, "LOSS_MODIFIER", [
            a("SET_VARIABLE", variable("BOOLEAN", "P1_lifecycle_core_active", lhs=True), x(100001, 1, False)),
            a("SET_VARIABLE", variable("BOOLEAN", "P1_lifecycle_timer_pending", lhs=True), x(100001, 1, False)), a("DELETE_TIMER", handle)]), th], 134277456)

    gain = t(762560516, "SPECIAL_UNIT_EVENT", [action("ADD_BUFF_STACK", 762560516000061, cm, x(100002, 1, 1))],
             1485688834, [owner, x(100007, 1, "ET_UNIT_BE_HURT")])
    gain["condition"] = [condition("GET_IS_NORMAL_HIT_FROM_EVENT", 762560516000099), classifier(762560516000105)]
    xh = doc([t(1485688834, "OBTAIN_MODIFIER", [762560516]), t(594665475, "LOSS_MODIFIER", []), gain], 134259960)

    red = action("SET_CUR_DAMAGE", 512499716810154, x(100000, "ARITHMETIC_OPERATION", x(100000, "HURT_DAMAGE"),
        x(100017, 1, "*"), x(100000, "ARITHMETIC_OPERATION", x(100000, 1, 1.0), x(100017, 1, "-"),
            x(100000, "GET_FLOAT_KV", x(100014, "RELATED_ABILITY", cm), x(100003, 1, "\u4f24\u5bb3\u51cf\u514d%")))))
    shared = doc([t(1625518081, "OBTAIN_MODIFIER", [512499716]), t(512499716, "SPECIAL_UNIT_EVENT", [red], 1625518081)], 134279904)

    ztimer = action("RUN_ONCE_TIMER_NO_SAVE", 1022332932000060, x(100002, 1, 1), x(100022, 1,
        action("SET_ENTITY_KV", 1022332932000067, cm, cd, x(100001, 1, False))))
    zh = t(1022332932, "SPECIAL_UNIT_EVENT", [action("SET_ENTITY_KV", 1022332932000050, cm, cd, x(100001, 1, True)),
        action("ADD_BUFF_STACK", 762560516000061, cm, x(100002, 1, 1)), ztimer], 434970627)
    zh["condition"] = [condition("BOOL_COMPARE", 1022332932000026, x(100001, "GET_BOOLEAN_KV", cm, cd),
                                  x(100035, 1, "=="), x(100001, 1, False)), classifier(1022332932000017)]
    attr = action("ADD_MODIFIER_OWNER_ATTR", 1050472449000072, cm, x(100042, 1, "defense_phy"),
                  x(100300, 1, "ATTR_ALL_RATIO"), x(100000, "ARITHMETIC_OPERATION", x(100000, 1, 6.0),
                    x(100017, 1, "*"), x(100002, "GET_MODIFIER_LAYER_CHANGE_VALUE")))
    zf = doc([t(434970627, "OBTAIN_MODIFIER", [1022332932]), zh,
              t(1050472449, "MODIFIER_LAYER_CHANGE", [attr]), t(1485688834, "LOSS_MODIFIER", [
                action("CLEAR_MODIFIER_OWNER_ATTR", 1485688834000006, cm)])], 134224490)

    passive_owner = x(100006, "ABILITY_OWNER")
    counter = t(58232837, "RECEIVE_CUSTOM_EVENT", [action("SET_ENTITY_KV", 58232837974056, ca, cd, x(100001, 1, False))],
                1959489540, [x(100238, 1, 1477099689)])
    counter["condition"] = [condition("UNIT_COMPARE", 58232837974025,
        x(100006, "GET_CUS_EVENT_PARAM", x(100240, 1, "\u89e6\u53d1\u5355\u4f4d")), x(100035, 1, "=="), passive_owner)]
    packet = t(173064198, "SPECIAL_UNIT_EVENT", [action("SET_ENTITY_KV", 58232837974056, ca, cd, x(100001, 1, True)),
        action("SET_CUR_DAMAGE", 173064198000083, x(100000, "ARITHMETIC_OPERATION", x(100000, "HURT_DAMAGE"),
          x(100017, 1, "*"), x(100000, "ARITHMETIC_OPERATION", x(100000, 1, 1.0), x(100017, 1, "+"),
            x(100000, "GET_FLOAT_KV", ca, x(100003, 1, "\u4f24\u5bb3\u7cfb\u6570")))))], 1959489540)
    packet["condition"] = [
        condition("ABILITY_TYPE_COMPARE", 173064198000033, x(100182, "TYPE_OF_ABILITY", da),
                  x(100035, 1, "=="), x(100182, 1, 3)),
        condition("ABILITY_CAST_TYPE_COMPARE", 173064198000038, x(100219, "GET_ABILITY_CAST_TYPE", da),
                  x(100035, 1, "=="), x(100219, 1, 2)),
        condition("BOOL_COMPARE", 173064198000060, x(100001, "GET_BOOLEAN_KV", ca, cd),
                  x(100035, 1, "=="), x(100001, 1, False))]
    pas = doc([t(1959489540, "ABILITY_OBTAIN", [58232837, 173064198]), counter, packet,
               t(225054724, "ABILITY_LOSE", [action("UNREG_TRIGGER", 225054724000150,
                   x(100178, "VARIABLE", ["DYNAMIC_TRIGGER_INSTANCE", "temp2", "actor"]))])], 134262911)
    docs = {p.TAISHI: ts, p.XIAHOU: xh, p.SHARED: shared, p.ZHANGFEI: zf, p.PASSIVE: pas}
    for key in p.MELEE_SOURCES:
        src = action("ADD_MODIFIER", fresh(), passive_owner, x(100046, 1, 134279904))
        src.update(op_arg=[passive_owner, ca, None, None, None, None], op_arg_enable=[True, True, False, False, False, False])
        docs[f"ability/{key}.json"] = doc([t(1959489540, "ABILITY_OBTAIN", [src])], key)
    for key in p.ACTIVES:
        packets = [action("APPLY_DAMAGE", fresh(), passive_owner, ca, x(100006, "DAMAGE_TARGET_UNIT"),
                          x(100064, 1, 0), x(100000, 1, amount), x(100001, 1, True)) for amount in (100.0, 50.0, 25.0)]
        docs[f"ability/{key}.json"] = doc([t(893440004, "ABILITY_SP_END", packets)], key)
    return docs


def build_memory(documents):
    def read(path, *args, **kwargs):
        key = path.parent.name + "/" + path.name
        if key not in documents:
            raise FileNotFoundError(key)
        return json.dumps(documents[key])
    with patch.object(Path, "read_text", read), patch.object(Path, "write_text") as write:
        result = p.build(Path("memory/map3"))
        write.assert_not_called()
        return result


class Entity:
    def __init__(self, key=0, *, owner=None, source=None, related=None, slot=2, cast_type=3, tags=(), stack=1):
        self.exists, self.key, self.owner, self.source, self.related = True, key, owner, source, related
        self.slot, self.cast_type, self.tags, self.stack = slot, cast_type, set(tags), stack
        self.target, self.buffs, self.abilities, self.contributions = None, {}, {}, {}
        self.kv = {p.CD: False, p.COEFFICIENT: 0.2, "\u4f24\u5bb3\u51cf\u514d%": 0.1}


class LifetimeFault(RuntimeError):
    pass


class Model:
    """Only the reviewed scalar/instance contracts. Unknown ECA fails loudly."""
    def __init__(self, current=None, ability=None):
        self.context = {"CUR_MODIFIER": current, "CUR_ABILITY": ability}
        self.actor, self.local, self.registered, self.timers = {}, {}, set(), []
        self.damage, self.payloads, self.now, self.lookups = 100.0, [], 0.0, []
        self.normal, self.layer_delta, self.on_packet, self.on_stack = False, 1, None, None

    @staticmethod
    def valid(v):
        return isinstance(v, Entity) and v.exists

    def checked(self, v):
        if not self.valid(v):
            raise LifetimeFault("invalid instance dereference")
        return v

    def loc(self, n):
        raw = n["args_list"][0]
        parts = raw["items"] if isinstance(raw, dict) else raw
        return (self.local if parts[2] == "local" else self.actor), parts[1]

    def value(self, n):
        sub, args = n["sub_type"], n["args_list"]
        if sub in (1, 2, 6, 11, "VARIABLE") and args and isinstance(args[0], (dict, list)):
            store, key = self.loc(n)
            return store.get(key, 0)
        if sub == 1:
            if len(args) != 1 or isinstance(args[0], (dict, list)):
                raise NotImplementedError("invalid literal")
            return args[0]
        if sub in self.context:
            return self.context[sub]
        if sub == "MODIFIER_OWNER":
            return self.checked(self.context.get("CUR_MODIFIER")).owner
        if sub == "ABILITY_OWNER":
            return self.checked(self.context.get("CUR_ABILITY")).owner
        if sub == "RELATED_ABILITY":
            return self.checked(self.value(args[0])).related
        if sub == "GET_LAST_MODIFIER_INSTANCE":
            return self.checked(self.value(args[0])).buffs.get(self.value(args[1]))
        if sub == "GET_BUFF_SOURCE":
            return self.checked(self.value(args[0])).source
        if sub == "TARGET_UNIT_IN_ABILITY":
            return self.checked(self.value(args[0])).target
        if sub == "TYPE_OF_ABILITY":
            return self.checked(self.value(args[0])).slot
        if sub == "GET_ABILITY_CAST_TYPE":
            return self.checked(self.value(args[0])).cast_type
        if sub == "ABILITY_NAME_OF_ABILITY":
            return self.checked(self.value(args[0])).key
        if sub == "GET_ABILITY_BY_AID":
            self.assert_lookup_types(n)
            owner, slot, key = [self.value(v) for v in args]
            self.lookups.append((slot, key))
            return self.checked(owner).abilities.get((slot, key))
        if sub in ("GET_BOOLEAN_KV", "GET_FLOAT_KV"):
            return self.checked(self.value(args[0])).kv[self.value(args[1])]
        if sub in ("ARITHMETIC_OPERATION", "MATH_OPERATION"):
            left, op, right = [self.value(v) for v in args]
            return {"+": lambda: left + right, "-": lambda: left - right, "*": lambda: left * right}[op]()
        if sub == "I2F":
            return float(self.value(args[0]))
        if sub == "GET_MOD_STACK":
            return self.checked(self.value(args[0])).stack
        if sub == "GET_MODIFIER_LAYER_CHANGE_VALUE":
            return self.layer_delta
        if sub == "GET_IS_NORMAL_HIT_FROM_EVENT":
            return self.normal
        if sub == "GET_CUS_EVENT_PARAM":
            return self.context.get("counter_owner")
        if sub == "HURT_DAMAGE":
            return self.damage
        if sub == p.MELEE_HELPER:
            ability = self.checked(self.value(args[0]))
            return ability.slot == 1 and self.value(args[1]) in ability.tags
        raise NotImplementedError("expression " + str(sub))

    @staticmethod
    def assert_lookup_types(n):
        if [v["arg_type"] for v in n["args_list"]] != [100006, 100182, 100039]:
            raise AssertionError("lookup operand types")

    def check(self, n):
        name, args = n["condition_type"], n["args_list"]
        if name == "TYPE_IS_EXIST":
            return self.valid(self.value(args[0]))
        if name in ("BOOL_COMPARE", "FLOAT_COMPARE", "UNIT_COMPARE", "MODIFIER_COMPARE", "ABILITY_COMPARE",
                    "ABILITY_TYPE_COMPARE", "ABILITY_CAST_TYPE_COMPARE"):
            left, op, right = [self.value(v) for v in args]
            same = left is right if isinstance(left, Entity) else left == right
            return same if op == "==" else not same if op == "!=" else self.unsupported(op)
        if name == "BOOL_NOT":
            return not self.value(args[0])
        if name == "GET_IS_NORMAL_HIT_FROM_EVENT":
            return self.normal
        if name == "FUNC_CONDITION":
            return self.value(args[0])
        if name in ("ABILITY_HAS_TAG", "UNIT_HAS_TAG"):
            return self.value(args[1]) in self.checked(self.value(args[0])).tags
        if name == "HAS_KV_ANY":
            return self.value(args[1]) in self.checked(self.value(args[0])).kv
        if name == "OR":
            values = [self.check(c) for c in args[0]["args_list"] if c.get("enable") is not False]
            return any(values)
        raise NotImplementedError("condition " + str(name))

    @staticmethod
    def unsupported(value):
        raise NotImplementedError(value)

    def run(self, acts):
        for n in acts:
            if isinstance(n, int):
                self.registered.add(n)
                continue
            if n.get("enable") is False:
                continue
            name, args = n["action_type"], n["args_list"]
            if name == "IF_THEN_ELSE":
                values = [self.check(c) for c in args[0]["args_list"] if c.get("enable") is not False]
                self.run(args[1 if all(values) else 2]["args_list"])
            elif name == "SET_VARIABLE":
                store, key = self.loc(args[0]); store[key] = self.value(args[1])
            elif name == "SET_ENTITY_KV":
                self.checked(self.value(args[0])).kv[self.value(args[1])] = self.value(args[2])
            elif name in ("ADD_BUFF_STACK", "SET_BUFF_STACK"):
                obj, number = self.checked(self.value(args[0])), self.value(args[1])
                obj.stack = min({134277456: 2, 134224490: 4, 134259960: 5}.get(obj.key, 100),
                                obj.stack + number if name == "ADD_BUFF_STACK" else number)
                if self.on_stack: self.on_stack()
            elif name == "ADD_MODIFIER":
                target, key = self.checked(self.value(args[0])), self.value(args[1])
                source = self.value(n["op_arg"][0])
                existing = target.buffs.get(key)
                if self.valid(existing) and existing.source is source:
                    mark = existing
                else:
                    mark = Entity(key, owner=target, source=source)
                mark.expires = self.now + self.value(n["op_arg"][2])
                target.buffs[key] = mark
            elif name == "REMOVE_BUFF_INS":
                obj = self.checked(self.value(args[0])); obj.exists = False
                if obj.owner.buffs.get(obj.key) is obj:
                    obj.owner.buffs.pop(obj.key)
            elif name in ("RUN_ONCE_TIMER", "RUN_ONCE_TIMER_NO_SAVE"):
                offset = 1 if name == "RUN_ONCE_TIMER" else 0
                timer = {"body": args[offset + 1]["args_list"], "cancelled": False,
                         "duration": self.value(args[offset]), "local": self.local.copy(), "context": self.context.copy()}
                self.timers.append(timer)
                if offset:
                    store, key = self.loc(args[0]); store[key] = timer
            elif name == "DELETE_TIMER":
                timer = self.value(args[0])
                if isinstance(timer, dict): timer["cancelled"] = True
            elif name == "SET_CUR_DAMAGE":
                self.damage = self.value(args[0])
            elif name == "APPLY_DAMAGE":
                self.payloads.append(self.value(args[4]))
                if self.on_packet: self.on_packet()
            elif name == "CLEAR_MODIFIER_OWNER_ATTR":
                mod = self.checked(self.value(args[0])); mod.owner.contributions.pop(mod, None)
            elif name == "ADD_MODIFIER_OWNER_ATTR":
                mod = self.checked(self.value(args[0])); mod.owner.contributions[mod] = mod.owner.contributions.get(mod, 0) + self.value(args[3])
            elif name == "UNREG_TRIGGER":
                pass  # AST binding/registration is verified separately.
            else:
                raise NotImplementedError("action " + str(name))

    def fire(self, doc, tid):
        trigger = doc["trigger_dict"][str(tid)]
        if trigger.get("call_enabled") is False:
            return False
        if trigger.get("enabled") is False and tid not in self.registered:
            return False
        self.local = {name: value for values in trigger["var_data"][0].values() for name, value in values.items()}
        values = [self.check(c) for c in trigger["condition"] if c.get("enable") is not False]
        if not all(values): return False
        self.run(trigger["action"])
        return True

    def expire(self, timer, forced=False):
        if timer["cancelled"] and not forced: return
        old_local, old_context = self.local, self.context
        self.local, self.context = timer["local"].copy(), timer["context"].copy()
        try: self.run(timer["body"])
        finally: self.local, self.context = old_local, old_context


class LifecycleTests(unittest.TestCase):
    def setUp(self):
        self.original = fixtures()
        self.fixed, self.issues = build_memory(self.original)
        self.assertEqual(set(self.fixed), {p.TAISHI, p.XIAHOU, p.SHARED, p.ZHANGFEI, p.PASSIVE}, self.issues)

    def taishi(self, fixed=True):
        owner = Entity()
        core = Entity(134277456, owner=owner)
        owner.buffs[134277456] = core
        target = Entity(tags=("\u9635\u578b\u961f\u957f",))
        active = Entity(134259517, owner=owner, slot=3, cast_type=2)
        active.target = target
        m = Model(core)
        m.context.update(DAMAGE_ABILITY=active, DAMAGE_TARGET_UNIT=target, DAMAGE_SOURCE_UNIT=owner)
        doc = (self.fixed if fixed else self.original)[p.TAISHI]
        m.fire(doc, 1485688834)
        return m, doc, owner, core, target, active

    def test_old_eight_second_cd_blocks_refresh_then_fixed_restarts(self):
        for fixed in (False, True):
            m, doc, owner, core, target, active = self.taishi(fixed)
            m.fire(doc, 1418035204)
            first = m.timers[-1]
            first_letter = target.buffs[134274015]
            m.now = 3.0
            m.fire(doc, 1418035204)
            self.assertEqual(len(m.timers), 2 if fixed else 1)
            self.assertEqual(first_letter.expires, 11.0 if fixed else 8.0)
            if fixed: self.assertTrue(first["cancelled"])

    def test_primary_aoe_does_not_mark_splash_leaders_or_soldiers(self):
        for fixed in (False, True):
            m, doc, owner, core, main, active = self.taishi(fixed)
            splash = Entity(tags=("\u9635\u578b\u961f\u957f",))
            m.context["DAMAGE_TARGET_UNIT"] = splash
            m.fire(doc, 1418035204)
            self.assertEqual(134274015 in splash.buffs, not fixed)
        m, doc, owner, core, soldier, active = self.taishi()
        soldier.tags.clear()
        m.fire(doc, 1418035204)
        self.assertNotIn(134274015, soldier.buffs)
        self.assertFalse(m.timers)

    def test_active_classification_uses_hero_slot_and_cast_type_independently(self):
        for slot, cast, expected in [(3, 2, True), (3, 3, False), (2, 2, False), (1, 2, False)]:
            with self.subTest(slot=slot, cast=cast):
                m, doc, owner, core, target, ability = self.taishi()
                ability.slot, ability.cast_type = slot, cast
                m.fire(doc, 1418035204)
                self.assertEqual(134274015 in target.buffs, expected)

    def test_transfer_removes_only_old_tracked_own_letter(self):
        m, doc, owner, core, first, active = self.taishi()
        m.fire(doc, 1418035204)
        old = first.buffs[134274015]
        second = Entity(tags=("\u4ec6\u4ece\u4f19\u4f34",))
        active.target = second
        m.context["DAMAGE_TARGET_UNIT"] = second
        m.fire(doc, 1418035204)
        self.assertFalse(old.exists)
        self.assertNotIn(134274015, first.buffs)
        self.assertIs(second.buffs[134274015].source, owner)

    def test_transfer_never_removes_foreign_replaced_source(self):
        m, doc, owner, core, first, active = self.taishi()
        m.fire(doc, 1418035204)
        old = first.buffs[134274015]
        old.source = Entity()
        second = Entity(tags=("\u9635\u578b\u961f\u957f",))
        active.target = second; m.context["DAMAGE_TARGET_UNIT"] = second
        m.fire(doc, 1418035204)
        self.assertTrue(old.exists)

    def test_queued_old_timer_cannot_reset_new_same_instance_window(self):
        m, doc, owner, core, target, active = self.taishi()
        m.fire(doc, 1418035204)
        old = m.timers[-1]
        m.now = 4.0; m.fire(doc, 1418035204)
        new = m.timers[-1]
        self.assertTrue(old["cancelled"])
        self.assertEqual(core.stack, 2)
        m.expire(old, forced=True)
        self.assertEqual(core.stack, 2)
        self.assertTrue(core.kv[p.CD])
        self.assertTrue(m.actor["P1_lifecycle_timer_pending"])
        m.expire(new)
        self.assertEqual(core.stack, 1)
        self.assertFalse(core.kv[p.CD])

    def test_taishi_loss_reacquire_and_missing_damage_ability_are_safe(self):
        m, doc, owner, core, target, active = self.taishi()
        m.context["DAMAGE_ABILITY"] = None
        m.fire(doc, 1418035204)
        self.assertFalse(m.timers)
        m.context["DAMAGE_ABILITY"] = active
        m.fire(doc, 1418035204)
        timer = m.timers[-1]
        m.fire(doc, 594665475)
        core.exists = False
        new = Entity(134277456, owner=owner, stack=2); owner.buffs[134277456] = new
        m.expire(timer, forced=True)
        self.assertEqual(new.stack, 2)

    def incoming(self, key, fixed=True):
        owner = Entity()
        core = Entity(key, owner=owner)
        owner.buffs[key] = core
        m = Model(core)
        m.normal = True
        attack = Entity(slot=1, cast_type=2, tags=("\u8fd1\u6218\u666e\u653b",))
        m.context.update(DAMAGE_ABILITY=attack, DAMAGE_SOURCE_UNIT=Entity())
        rel, obtain, hurt, loss = ((p.XIAHOU, 1485688834, 762560516, 594665475) if key == 134259960 else
                                   (p.ZHANGFEI, 434970627, 1022332932, 1485688834))
        doc = (self.fixed if fixed else self.original)[rel]
        m.fire(doc, obtain)
        return m, doc, owner, core, hurt, loss

    def test_old_ganglie_gains_each_hit_then_fixed_one_per_second(self):
        for fixed in (False, True):
            m, doc, owner, core, hurt, loss = self.incoming(134259960, fixed)
            for _ in range(4): m.fire(doc, hurt)
            self.assertEqual(core.stack, 2 if fixed else 5)
            if fixed:
                self.assertEqual(m.timers[-1]["duration"], 1.0)
                m.expire(m.timers[-1]); m.fire(doc, hurt)
                self.assertEqual(core.stack, 3)

    def test_ganglie_rejects_null_non_normal_ranged_and_self_extra_damage(self):
        for mode in ("null", "skill", "ranged", "non_normal", "self"):
            with self.subTest(mode=mode):
                m, doc, owner, core, hurt, loss = self.incoming(134259960)
                if mode == "null": m.context["DAMAGE_ABILITY"] = None
                if mode == "skill": m.context["DAMAGE_ABILITY"] = Entity(slot=3, cast_type=3)
                if mode == "ranged": m.context["DAMAGE_ABILITY"].tags = {"\u8fdc\u7a0b\u666e\u653b"}
                if mode == "non_normal": m.normal = False
                if mode == "self": m.context["DAMAGE_SOURCE_UNIT"] = owner
                m.fire(doc, hurt)
                self.assertEqual(core.stack, 1)
                self.assertFalse(m.timers)

    def test_ganglie_loss_and_replacement_cannot_rearm_new_instance(self):
        m, doc, owner, core, hurt, loss = self.incoming(134259960)
        m.fire(doc, hurt); timer = m.timers[-1]
        m.fire(doc, loss); core.exists = False
        new = Entity(134259960, owner=owner); owner.buffs[134259960] = new
        m.expire(timer, forced=True)
        self.assertFalse(m.actor[p.PREFIX + "gain_ready"])
        self.assertEqual(new.stack, 1)

    def shared_damage(self, source_id, *, normal=True, slot=1, melee=True, ability=True, fixed=True):
        owner = Entity()
        source = Entity(source_id, owner=owner, slot=2, cast_type=3)
        buff = Entity(134279904, owner=owner, related=source)
        m = Model(buff); m.normal = normal
        m.context["DAMAGE_ABILITY"] = Entity(slot=slot, cast_type=2, tags=("\u8fd1\u6218\u666e\u653b",) if melee else ()) if ability else None
        doc = (self.fixed if fixed else self.original)[p.SHARED]
        m.fire(doc, 1625518081); m.fire(doc, 512499716)
        return m.damage

    def test_old_shared_reduces_skills_then_fixed_three_sources_melee_normal_only(self):
        for source in p.MELEE_SOURCES:
            with self.subTest(source=source):
                self.assertEqual(self.shared_damage(source, slot=3, normal=False, fixed=False), 90.0)
                self.assertEqual(self.shared_damage(source, slot=3, normal=False), 100.0)
                self.assertEqual(self.shared_damage(source), 90.0)
                self.assertEqual(self.shared_damage(source, melee=False), 100.0)
                self.assertEqual(self.shared_damage(source, normal=False), 100.0)
                self.assertEqual(self.shared_damage(source, ability=False), 100.0)

    def test_unrestricted_shared_sources_keep_all_damage_even_without_damage_ability(self):
        for source in (134262911, 134222326, 134243085, 999999):
            with self.subTest(source=source):
                self.assertEqual(self.shared_damage(source, slot=3, normal=False), 90.0)
                self.assertEqual(self.shared_damage(source, ability=False, normal=False), 90.0)
                self.assertEqual(self.shared_damage(source, melee=False), 90.0)

    def test_guard_old_defense_contribution_then_no_double_defense_and_layer_math(self):
        old_m, old_doc, owner, old_core, hurt, loss = self.incoming(134224490, False)
        old_m.fire(old_doc, 1050472449)
        self.assertEqual(owner.contributions[old_core], 6.0)
        for visible, expected in [(0, 100.0), (1, 94.0), (2, 88.0), (3, 82.0)]:
            with self.subTest(visible=visible):
                m, doc, owner, core, hurt, loss = self.incoming(134224490)
                core.stack, core.kv[p.CD] = visible + 1, True  # Gain CD must not disable mitigation.
                m.fire(doc, hurt)
                self.assertAlmostEqual(m.damage, expected)
                m.fire(doc, 1050472449)
                self.assertNotIn(core, owner.contributions)

    def test_guard_every_packet_reduces_during_gain_cd_and_consumption_is_immediate(self):
        m, doc, owner, core, hurt, loss = self.incoming(134224490)
        core.stack, core.kv[p.CD] = 4, True
        for _ in range(3):
            m.damage = 100.0; m.fire(doc, hurt); self.assertAlmostEqual(m.damage, 82.0)
        self.assertEqual(core.stack, 4)
        core.stack = 2
        m.damage = 100.0; m.fire(doc, hurt); self.assertAlmostEqual(m.damage, 94.0)
        core.stack = 1
        m.damage = 100.0; m.fire(doc, hurt); self.assertEqual(m.damage, 100.0)

    def test_guard_melee_normal_reduction_does_not_redefine_old_resource_classifier(self):
        m, doc, owner, core, hurt, loss = self.incoming(134224490)
        core.stack = 2
        m.normal = False  # Still type1 + native tag: old resource helper accepts it.
        m.fire(doc, hurt)
        self.assertEqual(m.damage, 100.0)
        self.assertEqual(core.stack, 3)
        m.damage = 100.0; m.normal = True; m.context["DAMAGE_ABILITY"] = Entity(slot=3, cast_type=2)
        m.fire(doc, hurt)
        self.assertEqual((m.damage, core.stack), (100.0, 3))

    def test_guard_cleanup_preserves_other_sources_and_cancels_bound_timer(self):
        m, doc, owner, core, hurt, loss = self.incoming(134224490)
        other = Entity()
        owner.contributions.update({core: 18.0, other: 77.0})
        m.fire(doc, 1050472449)
        self.assertEqual(owner.contributions, {other: 77.0})
        m.fire(doc, hurt); timer = m.timers[-1]
        m.fire(doc, loss); core.exists = False
        self.assertTrue(timer["cancelled"])
        new = Entity(134224490, owner=owner); new.kv[p.CD] = True; owner.buffs[134224490] = new
        m.expire(timer, forced=True)
        self.assertTrue(new.kv[p.CD])
        self.assertEqual(owner.contributions, {other: 77.0})

    def test_synchronous_loss_during_gain_cancels_already_saved_handle(self):
        for key in (134224490, 134259960):
            with self.subTest(key=key):
                m, doc, owner, core, hurt, loss = self.incoming(key)
                def lose():
                    m.fire(doc, loss)
                    core.exists = False
                m.on_stack = lose
                m.fire(doc, hurt)
                self.assertEqual(len(m.timers), 1)
                self.assertTrue(m.timers[0]['cancelled'])
                m.expire(m.timers[0], forced=True)
    def passive_model(self, fixed=True):
        owner = Entity()
        passive = Entity(134262911, owner=owner, slot=2, cast_type=3)
        owner.abilities[(2, 134262911)] = passive  # Real map adds skill5..8 to COMMON.
        m = Model(ability=passive)
        doc = (self.fixed if fixed else self.original)[p.PASSIVE]
        m.fire(doc, 1959489540)
        return m, doc, owner, passive

    def arm_counter(self, m, doc, owner, passive):
        m.context.update(CUR_ABILITY=passive, counter_owner=owner)
        m.fire(doc, 58232837)

    def cast(self, m, owner, key=134265726, doc=None):
        active = Entity(key, owner=owner, slot=3, cast_type=2)
        owner.abilities[(3, key)] = active  # skill1..4 are HERO, not COMMON.
        m.context.update(CUR_ABILITY=active, DAMAGE_ABILITY=active, DAMAGE_TARGET_UNIT=Entity())
        m.payloads.clear()
        doc = doc or p.patch_xiahou_active(self.original[f"ability/{key}.json"], key)
        m.fire(doc, 893440004)
        return m.payloads.copy()

    def test_old_yishang_before_counter_and_first_packet_only_are_reproduced(self):
        m, doc, owner, passive = self.passive_model(False)
        m.context['DAMAGE_ABILITY'] = Entity(134232470, owner=owner, slot=3, cast_type=2)
        self.assertTrue(m.fire(doc, 173064198))
        self.assertEqual(m.damage, 120.0)  # Old first benefit occurs before any counter.
        m.damage = 100.0
        self.assertFalse(m.fire(doc, 173064198))
        self.assertEqual(m.damage, 100.0)

    def test_new_yishang_no_first_counter_benefit_then_whole_cast_snapshot_once(self):
        for key in p.ACTIVES:
            with self.subTest(key=key):
                m, doc, owner, passive = self.passive_model()
                self.assertEqual(self.cast(m, owner, key), [100.0, 50.0, 25.0])
                self.arm_counter(m, doc, owner, passive)
                self.assertEqual(self.cast(m, owner, key), [120.0, 60.0, 30.0])
                self.assertFalse(passive.kv[p.PENDING])
                self.assertEqual(self.cast(m, owner, key), [100.0, 50.0, 25.0])
                self.assertTrue(all(slot == 2 for slot, aid in m.lookups if aid == 134262911))

    def test_lookup_wrong_hero_slot_cannot_find_common_passive(self):
        m, doc, owner, passive = self.passive_model()
        self.arm_counter(m, doc, owner, passive)
        overlay = p.patch_xiahou_active(self.original['ability/134232470.json'], 134232470)
        lookup = next(n for n in p.walk(overlay) if n.get('sub_type') == 'GET_ABILITY_BY_AID')
        lookup['args_list'][1] = x(100182, 1, 3)  # The exact reviewed regression.
        self.assertEqual(self.cast(m, owner, 134232470, overlay), [100.0, 50.0, 25.0])
        self.assertTrue(passive.kv[p.PENDING])
        self.assertIn((3, 134262911), m.lookups)

    def test_counter_rearmed_mid_cast_is_not_consumed_by_later_packets(self):
        m, doc, owner, passive = self.passive_model()
        self.arm_counter(m, doc, owner, passive)
        m.on_packet = lambda: passive.kv.update({p.PENDING: True})
        self.assertEqual(self.cast(m, owner), [120.0, 60.0, 30.0])
        self.assertTrue(passive.kv[p.PENDING])
        m.on_packet = None
        self.assertEqual(self.cast(m, owner), [120.0, 60.0, 30.0])
        self.assertFalse(passive.kv[p.PENDING])

    def test_passive_owner_isolation_loss_and_reobtain_clear_pending(self):
        m, doc, owner, passive = self.passive_model()
        m.context['counter_owner'] = Entity()
        m.fire(doc, 58232837)
        self.assertFalse(passive.kv[p.PENDING])
        self.arm_counter(m, doc, owner, passive)
        m.fire(doc, 225054724)
        self.assertFalse(passive.kv[p.PENDING])
        passive.kv[p.PENDING] = True
        m.fire(doc, 1959489540)
        self.assertFalse(passive.kv[p.PENDING])
        self.assertFalse(m.fire(doc, 173064198))
        legacy_cleanup = next(n for n in p.walk(doc['trigger_dict']['225054724']['action'])
                              if n.get('element_id') == 225054724000150)
        self.assertTrue(legacy_cleanup['enable'])

    def test_overlay_preserves_latest_early_edits_and_disabled_packets(self):
        key = 134232470
        latest = deepcopy(self.original[f'ability/{key}.json'])
        latest['early_marker'] = {'big': 900719925474099312348}
        active = latest['trigger_dict']['893440004']['action']
        active[0]['args_list'][4] = x(100000, 1, 321.0)
        disabled = action('APPLY_DAMAGE', 998, *deepcopy(active[0]['args_list']), enabled=False)
        active.append(disabled)
        original = deepcopy(latest)
        overlay = p.patch_xiahou_active(latest, key)
        self.assertEqual(latest, original)
        self.assertEqual(overlay['early_marker'], original['early_marker'])
        self.assertEqual(next(n for n in p.walk(overlay) if n.get('element_id') == 998), disabled)
        packets = [n for n in p.running(overlay['trigger_dict']['893440004']['action']) if n.get('action_type') == 'APPLY_DAMAGE']
        self.assertEqual(packets[0]['args_list'][4]['args_list'][0], x(100000, 1, 321.0))

    def test_overlay_rejects_async_unverified_capture_and_wrong_scope(self):
        key = 134232470
        latest = deepcopy(self.original[f'ability/{key}.json'])
        acts = latest['trigger_dict']['893440004']['action']
        latest['trigger_dict']['893440004']['action'] = [action('RUN_ONCE_TIMER_NO_SAVE', 997,
            x(100000, 1, 1.0), x(100022, 1, *acts))]
        with self.assertRaises(p.ReviewError): p.patch_xiahou_active(latest, key)
        with self.assertRaises(p.ReviewError): p.patch_xiahou_active(latest, 123)

    def test_original_ids_unknown_fields_disabled_nodes_and_input_preserved(self):
        self.assertEqual(self.original, fixtures())
        for rel, after in self.fixed.items():
            before = self.original[rel]
            old_ids = Counter(n['element_id'] for n in p.walk(before) if 'element_id' in n)
            new_ids = Counter(n['element_id'] for n in p.walk(after) if 'element_id' in n)
            self.assertFalse(old_ids - new_ids)
            self.assertTrue(all(v == 1 for k, v in new_ids.items() if k not in old_ids))
            self.assertEqual(before['user_unknown'], after['user_unknown'])
            self.assertEqual(before['trigger_group_info'], after['trigger_group_info'])
            for n in p.walk(before):
                if n.get('enable') is False: self.assertIn(n, list(p.walk(after)))

    def test_p1_callback_and_cancel_survive_with_only_new_window_conditions(self):
        before = self.original[p.TAISHI]
        after = self.fixed[p.TAISHI]
        old_timer = next(n for n in p.walk(before) if n.get('action_type') == 'RUN_ONCE_TIMER')
        new_timer = next(n for n in p.walk(after) if n.get('action_type') == 'RUN_ONCE_TIMER')
        self.assertEqual(old_timer['args_list'][:2], new_timer['args_list'][:2])
        self.assertEqual(old_timer['local_var'], new_timer['local_var'])
        for old in p.walk(old_timer):
            if 'element_id' not in old: continue
            new = next(n for n in p.walk(new_timer) if n.get('element_id') == old['element_id'])
            if old.get('action_type') == 'IF_THEN_ELSE':
                self.assertEqual(new['args_list'][0]['args_list'][:len(old['args_list'][0]['args_list'])],
                                 old['args_list'][0]['args_list'])
            elif old.get('action_type') != 'RUN_ONCE_TIMER': self.assertEqual(old, new)
        self.assertEqual(before['trigger_dict']['594665475'], after['trigger_dict']['594665475'])

    def test_fail_closed_on_disabled_anchor_missing_p1_or_unknown_extra_attribute(self):
        for mode in ('disabled', 'missing_p1', 'unknown_attr'):
            source = deepcopy(self.original)
            if mode == 'disabled':
                source[p.XIAHOU]['trigger_dict']['762560516']['action'][0]['enable'] = False
                target = p.XIAHOU
            elif mode == 'missing_p1':
                timer = next(n for n in p.walk(source[p.TAISHI]) if n.get('action_type') == 'RUN_ONCE_TIMER')
                timer['action_type'] = 'RUN_ONCE_TIMER_NO_SAVE'; target = p.TAISHI
            else:
                source[p.ZHANGFEI]['trigger_dict']['1050472449']['action'].append(
                    action('ADD_MODIFIER_OWNER_ATTR', 999, x(100076, 'CUR_MODIFIER')))
                target = p.ZHANGFEI
            docs, issues = build_memory(source)
            self.assertNotIn(target, docs)
            self.assertEqual(next(i['status'] for i in issues if i['file'] == target), 'review_required')

    def test_build_does_not_return_overlap_actives_or_shared_text_files(self):
        self.assertFalse(any(f'ability/{key}.json' in self.fixed for key in p.ACTIVES))
        self.assertNotIn('zhlanguage.json', self.fixed)
        self.assertNotIn('tables/技能作用描述表.json', self.fixed)
        issue = next(i for i in self.issues if i['case'] == 43)
        self.assertEqual(issue['requires_atomic_overlays'], [f'ability/{key}.json' for key in p.ACTIVES])

    def test_second_application_reports_instead_of_double_multiplying(self):
        source = {**self.original, **self.fixed}
        docs, issues = build_memory(source)
        self.assertEqual(docs, {})
        active = p.patch_xiahou_active(self.original['ability/134232470.json'], 134232470)
        with self.assertRaises(p.ReviewError): p.patch_xiahou_active(active, 134232470)

    def test_unknown_model_expression_is_not_silently_supported(self):
        with self.assertRaises(NotImplementedError): Model().value(x(100014, 'INVENTED_API'))

    def test_independent_checks_are_grouped_and_callback_depth_is_bounded(self):
        def depth(value, level=0):
            if isinstance(value, list):
                return max([level] + [depth(v, level) for v in value])
            if not isinstance(value, dict): return level
            kind = value.get('action_type')
            if kind in ('RUN_ONCE_TIMER', 'RUN_ONCE_TIMER_NO_SAVE'):
                return depth(value['args_list'][-1], 0)  # Separate callback execution scope.
            next_level = level + (kind == 'IF_THEN_ELSE')
            return max([next_level] + [depth(v, next_level) for v in value.values()])
        for rel, doc in self.fixed.items():
            with self.subTest(rel=rel):
                self.assertLessEqual(depth(doc), 5)
        # Shared restriction checks normal-event and ability existence together;
        # TYPE_OF_ABILITY and tag reads occur only in the following safe stage.
        shared = self.fixed[p.SHARED]['trigger_dict']['512499716']['action']
        stages = [n['args_list'][0]['args_list'] for n in p.running(shared) if n.get('action_type') == 'IF_THEN_ELSE']
        self.assertTrue(any(len(stage) == 2 and {c['condition_type'] for c in stage} ==
                            {'GET_IS_NORMAL_HIT_FROM_EVENT', 'TYPE_IS_EXIST'} for stage in stages))


class ActualMapTests(unittest.TestCase):
    def test_current_map_build_and_post_early_overlay_are_read_only(self):
        root = Path(os.environ.get('Y3_LIFECYCLE_ROOT', 'D:/littl/testTempFile/ProjectMonster02/maps/map3'))
        files = [p.TAISHI, p.XIAHOU, p.SHARED, p.ZHANGFEI, p.PASSIVE,
                 *[f'ability/{key}.json' for key in (*p.MELEE_SOURCES, *p.ACTIVES)]]
        if not all((root / f).is_file() for f in files): self.skipTest('actual map unavailable')
        data = {f: (root / f).read_bytes() for f in files}
        hashes = {f: hashlib.sha256(raw).hexdigest() for f, raw in data.items()}
        docs, issues = p.build(root)
        self.assertEqual(set(docs), {p.TAISHI, p.XIAHOU, p.SHARED, p.ZHANGFEI, p.PASSIVE}, issues)
        for key in p.ACTIVES:
            source = json.loads(data[f'ability/{key}.json'])
            overlay = p.patch_xiahou_active(source, key)
            lookup = next(n for n in p.walk(overlay) if n.get('sub_type') == 'GET_ABILITY_BY_AID')
            self.assertEqual(lookup['args_list'][1:], [x(100182, 1, 2), x(100039, 1, 134262911)])
        for rel, after in docs.items():
            before = json.loads(data[rel])
            old = Counter(n['element_id'] for n in p.walk(before) if 'element_id' in n)
            new = Counter(n['element_id'] for n in p.walk(after) if 'element_id' in n)
            self.assertFalse(old - new)
            self.assertTrue(all(v == 1 for k, v in new.items() if k not in old))
            self.assertEqual(before['trigger_group_info'], after['trigger_group_info'])
            self.assertEqual(set(before['trigger_dict']), set(after['trigger_dict']))
        self.assertEqual(hashes, {f: hashlib.sha256((root / f).read_bytes()).hexdigest() for f in files})

    def test_actual_unit_add_flow_distinguishes_active_and_passive_slots(self):
        root = Path(os.environ.get('Y3_LIFECYCLE_ROOT', 'D:/littl/testTempFile/ProjectMonster02/maps/map3'))
        path = root / 'global_trigger/function/new/功能执行/单位赋值和技能.json'
        if not path.is_file(): self.skipTest('native enum evidence unavailable')
        source = json.loads(path.read_text(encoding='utf-8-sig'))
        adds = [n for n in p.running(source['action']) if n.get('action_type') == 'UNIT_ADD_ABILITY']
        self.assertEqual([n['args_list'][1] for n in adds], [x(100182, 1, 3), x(100182, 1, 2)])
        # The passive branch offsets the ITER_INT table column by four.
        self.assertTrue(any(n.get('sub_type') == 'MATH_OPERATION' and n.get('args_list') ==
            [x(100002, 'ITER_INT'), x(100016, 1, '+'), x(100002, 1, 4)] for n in p.walk(adds[1])))


if __name__ == '__main__':
    unittest.main()

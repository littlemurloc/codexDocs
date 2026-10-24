"""Native AST regression tests plus bounded arithmetic/callback contracts.

The small evaluator rejects unknown operations. A mover request suspends;
tests explicitly call its callback AST with declared local snapshots. It does
not implement movement, collision, closure capture, cover events or an engine.
Selection is injected; rectangle math is an independent offline check only.
"""

from copy import deepcopy
from dataclasses import dataclass, field
import importlib.util
import json
import math
import os
from pathlib import Path
import unittest
from unittest.mock import patch


TOOL = Path(__file__).resolve().parents[1] / "tools/y3_hero_repair_p2_latest.py"
SPEC = importlib.util.spec_from_file_location("p2_latest", TOOL)
repair = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(repair)
LIVE = Path(os.environ.get("Y3_P2_TEST_ROOT", "D:/littl/testTempFile/ProjectMonster02/maps/map3"))


def x(kind, sub=1, *args):
    return {"arg_type": kind, "sub_type": sub, "args_list": list(args)}


def a(name, eid, *args, **extra):
    return {"action_type": name, "args_list": list(args), "element_id": eid,
            "enable": True, "bp": False, **extra}


def c(name, eid, *args):
    return {"condition_type": name, "element_id": eid, "args_list": list(args), "enable": True}


def branch(eid, conditions, yes, no=()):
    return a("IF_THEN_ELSE", eid, x(100021, 1, *conditions), x(100022, 1, *yes), x(100022, 1, *no))


def arithmetic(left, op, right):
    return x(100000, "ARITHMETIC_OPERATION", left, x(100017, 1, op), right)


def t(tid, event, actions):
    return {"trigger_id": tid, "event": [{"event_type": event, "enable": True}],
            "condition": [], "action": actions, "enabled": True, "valid": True,
            "call_enabled": True, "var_data": [{}, {}, []]}


def document(triggers):
    return {"trigger_dict": {str(v["trigger_id"]): v for v in triggers},
            "local_variable": {str(v["trigger_id"]): {"variable_dict": {}, "variable_length_dict": {}}
                               for v in triggers}, "variable_dict": {},
            "unrelated_precision": 9007199254740993123}


def caller_fixtures():
    docs = {}
    for oid, buff, key, amount in [(134283919, 134256265, repair.ATTACK_RATIO, .2),
                                   (134284010, 134284016, repair.RATIO, .25),
                                   (134284012, 134284017, repair.RATIO, .3),
                                   (134284015, 134284019, repair.RATIO, .2)]:
        def setter(eid):
            return a("SET_ENTITY_KV", eid, x(100014, "CUR_ABILITY"), x(100003, 1, key), x(100000, 1, amount))
        gain = t(1959489540, "ABILITY_OBTAIN", [] if oid == 134283919 else [setter(195948954000001)])
        gain["action"].append(a("ADD_MODIFIER", 195948954000002, x(100006, "ABILITY_OWNER"), x(100046, 1, buff),
            op_arg=[x(100006, "ABILITY_OWNER"), x(100014, "CUR_ABILITY")], op_arg_enable=[True, True]))
        cases = [] if oid == 134283919 else [a("CASE", 26066946000100 + i, x(100002, 1, i),
                                                x(100022, 1, setter(26066946000200 + i))) for i in range(1, 6)]
        level = t(26066946, "ABILITY_LEVEL_CHANGED", [a("SWITCH", 260669460500026,
            x(100002, "GET_ABILITY_INT_ATTR", x(100014, "CUR_ABILITY"), x(100079, 1, "ability_level")), x(100022, 1, *cases))])
        docs[f"ability/{oid}.json"] = document([gain, level])
        docs[f"editor_table/abilityall/{oid}.json"] = {"key": oid, "kv": {key: {"value": amount}}}
    return docs


def modifier_fixture(oid):
    cur = x(100076, "CUR_MODIFIER")
    fields = {
        134256265: [("attack_phy", "ATTR_ALL_RATIO", None)],
        134283923: [("attack_speed", "ATTR_ALL_RATIO", 0.3)],
        134283937: [("attack_phy", "ATTR_ALL_RATIO", -0.15)],
        134283938: [("attack_phy", "ATTR_ALL_RATIO", 0.15)],
        134283939: [("attack_speed", "ATTR_BASE", 0.2)],
        134284016: [("attack_speed", "ATTR_BASE", None)],
        134284017: [("ori_speed", "ATTR_ALL_RATIO", None)],
        134284019: [("attack_phy", "ATTR_ALL_RATIO", None), ("attack_mag", "ATTR_ALL_RATIO", None)],
    }[oid]
    gain = []
    for i, (attr, mode, value) in enumerate(fields):
        if value is not None:
            amount = x(100000, 1, value)
        else:
            related = x(100014, "RELATED_ABILITY_MODIFIER" if oid == 134256265 else "RELATED_ABILITY", cur)
            rate = x(100000, "GET_FLOAT_KV", related, x(100003, 1, repair.ATTACK_RATIO if oid == 134256265 else repair.RATIO))
            amount = arithmetic(rate, "*", x(100000, 1, -1.0)) if oid == 134256265 else arithmetic(x(100000, 1, 0.0), "-", rate)
        gain.append(a("ADD_MODIFIER_OWNER_ATTR", 1491812353000023 + i, cur,
                      x(100042, 1, attr), x(100300, 1, mode), amount, native_extension={"preserve": True}))
    return document([t(1491812353, "OBTAIN_MODIFIER", gain),
                     t(787386370, "LOSS_MODIFIER", [a("CLEAR_MODIFIER_OWNER_ATTR", 787386370000023, cur)])])


def sunce_fixture():
    """Observed map3 node encodings and anchor IDs, without unrelated auto-cast UI."""
    owner, ability, core = x(100006, "ABILITY_OWNER"), x(100014, "CUR_ABILITY"), x(100076, "GET_MODIFIER_FROM_EVENT")
    target = x(100006, "GET_UNIT_ENTITY_KV", core, x(100003, 1, repair.TARGET))
    selected = x(100006, "FOR_EACH_SELECTED_UNIT")
    point = lambda u: x(100004, "UNIT_ENTITY_POINT", u)
    angle = x(100225, "GET_POINTS_ANGLE", point(owner), point(target))
    distance = x(100000, "GET_POINTS_DIS", point(owner), point(target))
    count = x(100000, "GET_FLOAT_KV", core, x(100003, 1, "path_count"))
    damage = lambda eid, victim: a("APPLY_DAMAGE", eid, owner, ability, victim, x(100064, 1, 0),
        arithmetic(x(100000, "GET_UNIT_ATTR", owner, x(100301, 1, "ATTR_RESULT"), x(100042, 1, "attack_phy")),
                   "*", x(100000, 1, 1.1)), x(100001, 1, True),
        op_arg=[x(100001, 1, True)], op_arg_enable=[False], custom_marker="keep damage options")
    others = branch(141803520499015, [c("UNIT_COMPARE", 141803520499010, selected, x(100035, 1, "!="), target)], [
        branch(141803520499012, [c("FLOAT_COMPARE", 141803520499011, count, x(100015, 1, "<"), x(100000, 1, 2.0))], [
            damage(141803520499013, selected),
            a("SET_ENTITY_KV", 141803520499014, core, x(100003, 1, "path_count"), arithmetic(count, "+", x(100000, 1, 1.0)))])])
    shape = x(100026, "UNIT_LIST_IN_SHAPE",
              x(100004, "POINT_OFFSET_VECTOR_POINT", point(owner), angle, arithmetic(distance, "*", x(100000, 1, 0.5))),
              x(100060, "CONST_RECTANGLE_SHAPE", x(100000, 1, 200.0), distance,
                x(100000, "GET_FLOAT_BY_ANGLE", angle)))
    shape["op_arg"], shape["op_arg_enable"] = [x(100001, 1, False)], [True]
    clear = a("SET_ENTITY_KV", 105100083699002, core, x(100003, 1, repair.BUSY), x(100001, 1, False))
    mover = a("CREATE_STRAIGHT_MOVER", 105047244999015, owner, angle,
        arithmetic(distance, "*", x(100000, 1, 0.7)), x(100000, 1, 1000.0), x(100000, 1, 0.0),
        x(100022, 1, a("CREATE_SFX_ON_POINT_NEW", 105047244999003, x(100066, 1, 103720), point(owner)),
          damage(105047244999004, target), a("PICK_UNIT_DO_ACTION", 141803520499016, shape, x(100022, 1, others)), clear,
          a("SEND_CUSTOM_EVENT", 105100083699003, x(100238, 1, 2099456001), owner)),
        x(100022, 1), x(100022, 1), x(100022, 1), x(100022, 1),
        local_var={"__tuple__": True, "items": [{}, {}]}, op_arg=[None], op_arg_enable=[False])
    mover["args_list"][5]["args_list"][0]["enable"] = False
    entry = t(1051000836, "GLOBAL_MODIFIER_EVENT", [
        a("SET_ENTITY_KV", 105100083699000, core, x(100003, 1, repair.TARGET), x(100006, "GET_UNIT_AI_BATTLE_TARGET_UNIT", owner)),
        a("SET_ENTITY_KV", 105100083699001, core, x(100003, 1, repair.BUSY), x(100001, 1, True)),
        a("SET_BUFF_STACK", 105047244999001, core, x(100002, 1, 1)),
        branch(105047244999012, [c("IS_UNIT_ALIVE", 105047244999011, target)], [
            a("SET_ENTITY_KV", 105047244999002, core, x(100003, 1, "path_count"), x(100000, 1, 0.0)), mover])])
    entry["enabled"], entry["p_trigger_id"] = False, 1959489540
    entry["sub_trigger_owner_set_var_action"] = {"enable": True}
    entry["condition"] = [
        c("FLOAT_COMPARE", 105100083699012, x(100002, "GET_MOD_STACK", core), x(100015, 1, ">="), x(100002, 1, 3)),
        c("BOOL_NOT", 105100083699013, x(100001, "GET_BOOLEAN_KV", core, x(100003, 1, repair.BUSY)))]
    return document([entry, t(1959489540, "ABILITY_OBTAIN", [1051000836]), t(225054724, "ABILITY_LOSE", [])])


def sunce_consumer_fixture(six=True):
    owner = x(100006, "ABILITY_OWNER")
    core = x(100076, "GET_LAST_MODIFIER_INSTANCE", owner, x(100046, 1, 134279388))
    action = a("ADD_BUFF_STACK", 105100083699022, core, x(100002, 1, 1)) if six else a(
        "ADD_MODIFIER", 105047244999005, owner, x(100046, 1, 134283930),
        op_arg=[owner, x(100014, "CUR_ABILITY"), x(100000, 1, 3.0), None, None, None],
        op_arg_enable=[True, True, True, False, False, False])
    event = t(1051000836, "RECEIVE_CUSTOM_EVENT", [action])
    event["event"][0]["args_list"] = [x(100238, 1, 2099456001)]
    event["enabled"], event["p_trigger_id"] = False, 1959489540
    event["sub_trigger_owner_set_var_action"] = {"enable": True}
    event["condition"] = [c("UNIT_COMPARE", 105100083699020,
        x(100006, "GET_CUS_EVENT_PARAM", x(100240, 1, "\u89e6\u53d1\u5355\u4f4d")), x(100035, 1, "=="), owner)]
    if six:
        event["condition"].append(c("UNIT_HAS_MODIFIER", 105100083699021, owner, x(100046, 1, 134279388)))
    return document([event, t(1959489540, "ABILITY_OBTAIN", [1051000836]), t(225054724, "ABILITY_LOSE", [])])


@dataclass(eq=False)
class Entity:
    key: int
    exists: bool = True
    alive: bool = True
    team: str = "red"
    point: tuple = (0.0, 0.0, 0.0)
    stack: int = 3
    kv: dict = field(default_factory=dict)
    mods: dict = field(default_factory=dict)
    attrs: dict = field(default_factory=lambda: {"attack_phy": 100.0})
    contributions: dict = field(default_factory=dict)
    related: object = None
    target: object = None


class MoverRequested(Exception):
    """Opaque engine boundary; never pretends to create or complete a mover."""


class Frame:
    def __init__(self):
        self.owner = Entity(1)
        self.target = Entity(2, team="blue", point=(1000.0, 0.0, 0.0))
        self.owner.target = self.target
        self.skill = Entity(134283925)
        self.core = Entity(134279388, kv={repair.BUSY: False})
        self.owner.mods[134279388] = self.core
        self.modifier = self.core
        self.variables = {("INTEGER", repair.PHASE): 2, ("INTEGER", repair.WAVE): 1}
        self.selection, self.trace = [], []
        self.on_damage = self.on_consume = None
        self.on_notify = None
        self.event_source = self.owner
        self.mover = None

    def readable(self, entity):
        if not isinstance(entity, Entity) or not entity.exists:
            raise AssertionError("dereferenced an absent instance")
        return entity

    def value(self, expr):
        args, sub = expr["args_list"], expr["sub_type"]
        if sub == 1:
            return args[0]
        if args and isinstance(args[0], dict) and args[0].get("__tuple__"):
            return self.variables[tuple(args[0]["items"])]
        if sub in ("ABILITY_OWNER", "MODIFIER_OWNER"):
            return self.owner
        if sub == "CUR_ABILITY":
            return self.skill
        if sub in ("GET_MODIFIER_FROM_EVENT", "CUR_MODIFIER"):
            return self.modifier
        if sub == "FOR_EACH_SELECTED_UNIT":
            return self.selected
        if sub in ("RELATED_ABILITY", "RELATED_ABILITY_MODIFIER"):
            return self.readable(self.value(args[0])).related
        if sub == "GET_LAST_MODIFIER_INSTANCE":
            return self.readable(self.value(args[0])).mods.get(self.value(args[1]))
        if sub == "ABILITY_NAME_OF_ABILITY":
            return self.readable(self.value(args[0])).key
        if sub == "GET_MODIFIER_ENTITY_METATYPE":
            return self.readable(self.value(args[0])).key
        if sub in ("GET_FLOAT_KV", "GET_BOOLEAN_KV", "GET_UNIT_ENTITY_KV", "GET_MODIFIER_ENTITY_KV", "GET_INTEGER_KV"):
            return self.readable(self.value(args[0])).kv[self.value(args[1])]
        if sub == "GET_CUS_EVENT_PARAM":
            if self.value(args[0]) != "\u89e6\u53d1\u5355\u4f4d":
                raise NotImplementedError("unknown event parameter")
            return self.event_source
        if sub == "GET_UNIT_AI_BATTLE_TARGET_UNIT":
            return self.readable(self.value(args[0])).target
        if sub == "GET_MOD_STACK":
            return self.readable(self.value(args[0])).stack
        if sub == "OWNER_PLAYER":
            return self.readable(self.value(args[0])).team
        if sub == "GET_UNIT_ATTR":
            return self.readable(self.value(args[0])).attrs[self.value(args[2])]
        if sub == "UNIT_ENTITY_POINT":
            return self.readable(self.value(args[0])).point
        if sub == "ARITHMETIC_OPERATION":
            left, op, right = [self.value(v) for v in args]
            return {"+": lambda: left + right, "-": lambda: left - right,
                    "*": lambda: left * right}[op]()
        if sub in ("GET_POINTS_DIS", "GET_POINTS_ANGLE"):
            start, end = [self.value(v) for v in args]
            dx, dz = end[0] - start[0], end[2] - start[2]
            return math.hypot(dx, dz) if sub == "GET_POINTS_DIS" else math.degrees(math.atan2(dz, dx))
        if sub == "GET_FLOAT_BY_ANGLE":
            return self.value(args[0])
        if sub == "POINT_OFFSET_VECTOR_POINT":
            point, angle, distance = [self.value(v) for v in args]
            return (point[0] + distance * math.cos(math.radians(angle)), point[1],
                    point[2] + distance * math.sin(math.radians(angle)))
        if sub == "CONST_RECTANGLE_SHAPE":
            return tuple(self.value(v) for v in args)
        if sub == "UNIT_LIST_IN_SHAPE":
            # Mathematical descriptor, NOT an engine query or inferred selection.
            return tuple(self.value(v) for v in args)
        raise NotImplementedError((expr["arg_type"], sub))

    def condition(self, node):
        if node["condition_type"] == "OR":
            tests = [self.condition(v) for v in node["args_list"][0]["args_list"]
                     if v.get("enable") is not False]
            return any(tests)
        values = [self.value(v) for v in node["args_list"]]
        kind = node["condition_type"]
        if kind == "TYPE_IS_EXIST":
            return isinstance(values[0], Entity) and values[0].exists
        if kind == "IS_UNIT_ALIVE":
            return self.readable(values[0]).alive
        if kind == "BOOL_NOT":
            if type(values[0]) is not bool:
                raise TypeError("native bool required")
            return not values[0]
        if kind == "PLAYERS_IS_ENEMY_RELATION":
            return tuple(values) in {("red", "blue"), ("blue", "red")}
        if kind == "UNIT_HAS_MODIFIER":
            found = self.readable(values[0]).mods.get(values[1])
            return found is not None and found.exists
        if kind in ("FLOAT_COMPARE", "BOOL_COMPARE", "UNIT_COMPARE", "MODIFIER_COMPARE", "ABILITY_COMPARE", "MODIFIER_CLASS_COMPARE"):
            left, op, right = values
            return {"==": lambda: left == right, "!=": lambda: left != right,
                    "<": lambda: left < right, ">": lambda: left > right,
                    ">=": lambda: left >= right}[op]()
        raise NotImplementedError(kind)

    def run(self, actions):
        for node in actions:
            if not isinstance(node, dict):
                raise NotImplementedError("dynamic registration is not executed by the offline frame")
            if node.get("enable") is False:
                continue
            kind, args = node["action_type"], node["args_list"]
            if kind == "IF_THEN_ELSE":
                # Deliberately evaluate all conditions, not host-language short circuit.
                tests = [self.condition(v) for v in args[0]["args_list"] if v.get("enable") is not False]
                self.run(args[1 if all(tests) else 2]["args_list"])
            elif kind == "SET_VARIABLE":
                self.variables[tuple(args[0]["args_list"][0]["items"])] = self.value(args[1])
            elif kind == "SET_ENTITY_KV":
                entity, key, value = [self.value(v) for v in args]
                self.readable(entity).kv[key] = value
                self.trace.append(("kv", entity, key, value))
            elif kind == "SET_BUFF_STACK":
                entity, number = [self.value(v) for v in args]
                self.readable(entity).stack = number
                self.trace.append(("consume", entity, number))
                if self.on_consume:
                    self.on_consume(self)
            elif kind == "APPLY_DAMAGE":
                source, skill, target = [self.readable(self.value(v)) for v in args[:3]]
                if not source.alive or not target.alive:
                    raise AssertionError("damage against a dead actor")
                self.trace.append(("damage", target, self.value(args[4])))
                if self.on_damage:
                    self.on_damage(self)
            elif kind == "PICK_UNIT_DO_ACTION":
                self.value(args[0])
                for selected in self.selection:
                    self.selected = selected
                    self.run(args[1]["args_list"])
            elif kind == "CREATE_STRAIGHT_MOVER":
                self.mover = node
                self.trace.append(("mover_request", self.value(args[2])))
                raise MoverRequested()
            elif kind == "SEND_CUSTOM_EVENT":
                self.trace.append(("notify_request", self.value(args[0]), self.readable(self.value(args[1]))))
                if self.on_notify:
                    self.on_notify(self)
            elif kind == "ADD_BUFF_STACK":
                core, value = [self.value(v) for v in args]
                self.readable(core).stack += value
                self.trace.append(("refund_request", core, value))
            elif kind == "ADD_MODIFIER":
                owner = self.readable(self.value(args[0]))
                options = [self.value(value) if enabled else None for value, enabled in
                           zip(node.get("op_arg", []), node.get("op_arg_enable", []))]
                self.trace.append(("buff_request", self.value(args[1]), owner, options))
            elif kind == "ADD_MODIFIER_OWNER_ATTR":
                owner, attr, mode, amount = [self.value(v) for v in args]
                entity = self.readable(owner)
                key = attr, mode
                entity.contributions[key] = entity.contributions.get(key, 0.0) + amount
            elif kind == "CLEAR_MODIFIER_OWNER_ATTR":
                self.readable(self.value(args[0])).contributions.clear()
            elif kind.startswith("CREATE_SFX"):
                raise NotImplementedError("SFX is an opaque engine operation")
            else:
                raise NotImplementedError(kind)

    def entry(self, doc):
        event = doc["trigger_dict"]["1051000836"]
        if all([self.condition(v) for v in event["condition"]]):
            self.run(event["action"])

    def begin(self, doc):
        try:
            self.entry(doc)
        except MoverRequested:
            return
        raise AssertionError("no mover was requested")

    def finish(self, slot=5):
        self.run(self.mover["args_list"][slot]["args_list"])

    def receive(self, doc):
        event = doc["trigger_dict"]["1051000836"]
        if all([self.condition(n) for n in event["condition"]]):
            self.run(event["action"])


def contributions(doc, skill=None):
    frame = Frame()
    frame.modifier.related = skill
    gain = next(t for t in doc["trigger_dict"].values() if t["event"][0]["event_type"] == "OBTAIN_MODIFIER")
    frame.run(gain["action"])
    return frame


def effective(base, contributions, field):
    fixed = contributions.get((field, "ATTR_BASE"), 0.0)
    percent = contributions.get((field, "ATTR_ALL_RATIO"), 0.0)
    return (base + fixed) * (1.0 + percent / 100.0)


class NumericTests(unittest.TestCase):
    def test_each_old_defect_and_new_independent_numeric_result(self):
        cases = [(134283923, "attack_speed", 100, 130),
                 (134283937, "attack_phy", 200, 170),
                 (134283938, "attack_phy", 200, 230),
                 (134283939, "attack_speed", 100, 120),
                 (134284016, "attack_speed", 100, 75),
                 (134284017, "ori_speed", 400, 280),
                 (134284019, "attack_phy", 200, 160),
                 (134284019, "attack_mag", 300, 240)]
        skills = {134284016: Entity(134284010, kv={repair.RATIO: .25}),
                  134284017: Entity(134284012, kv={repair.RATIO: .30}),
                  134284019: Entity(134284015, kv={repair.RATIO: .20})}
        for oid, field, base, expected in cases:
            with self.subTest(oid=oid, field=field):
                original = modifier_fixture(oid)
                old = contributions(original, skills.get(oid))
                self.assertNotAlmostEqual(effective(base, old.modifier.contributions, field), expected)
                fixed = repair.patch_modifier(original, oid)
                new = contributions(fixed, skills.get(oid))
                self.assertAlmostEqual(effective(base, new.modifier.contributions, field), expected)
                loss = next(t for t in fixed["trigger_dict"].values() if t["event"][0]["event_type"] == "LOSS_MODIFIER")
                other_source = {("attack_phy", "ATTR_ALL_RATIO"): 7}
                new.run(loss["action"])
                self.assertEqual(new.modifier.contributions, {})
                self.assertEqual(other_source, {("attack_phy", "ATTR_ALL_RATIO"): 7})

    def test_shared_modifier_scopes_conversion_by_ability_id_not_magnitude(self):
        original = modifier_fixture(134256265)
        fixed = repair.patch_modifier(original, 134256265)
        for oid, value, expected in [(134283919, .2, -20), (134249476, 15, -15),
                                     (134244603, 30, -30), (134232552, .1, -10),
                                     (134280536, .5, -50), (134275485, .3, -30),
                                     (999, .2, -.2)]:
            with self.subTest(oid=oid):
                frame = contributions(fixed, Entity(oid, kv={repair.ATTACK_RATIO: value}))
                self.assertAlmostEqual(frame.modifier.contributions[("attack_phy", "ATTR_ALL_RATIO")], expected)
        self.assertEqual(contributions(fixed, None).modifier.contributions, {})

    def test_ratio_is_still_dynamic_at_attribute_boundary(self):
        fixed = repair.patch_modifier(modifier_fixture(134284016), 134284016)
        for value in (.10, .25, .35, .5):
            frame = contributions(fixed, Entity(134284010, kv={repair.RATIO: value}))
            self.assertAlmostEqual(effective(100, frame.modifier.contributions, "attack_speed"), 100 * (1 - value))

    def test_loss_and_unrelated_metadata_are_unchanged(self):
        for oid in repair.MODIFIERS:
            old = modifier_fixture(oid)
            saved = deepcopy(old)
            new = repair.patch_modifier(old, oid)
            self.assertEqual(old, saved)
            self.assertEqual(new["trigger_dict"]["787386370"], old["trigger_dict"]["787386370"])
            self.assertEqual(json.loads(json.dumps(new))["unrelated_precision"], 9007199254740993123)
            self.assertTrue(all(n.get("native_extension") == {"preserve": True}
                for n in repair.walk(new) if n.get("action_type") == "ADD_MODIFIER_OWNER_ATTR"))

    def test_changed_or_disabled_anchor_fails_closed(self):
        old = modifier_fixture(134283939)
        old["trigger_dict"]["1491812353"]["action"][0]["enable"] = False
        with self.assertRaises(repair.ReviewError):
            repair.patch_modifier(old, 134283939)


class SunCeTests(unittest.TestCase):
    def setUp(self):
        self.old = sunce_fixture()
        self.new = repair.patch_sunce(self.old)
        self.six = repair.patch_sunce_six(sunce_consumer_fixture())
        self.four = sunce_consumer_fixture(False)

    def dispatch(self, sender, six_first=False):
        """Explicit test-driven synchronous delivery, not an engine implementation."""
        consumers = [(134283927, self.four), (134283929, self.six)]
        if six_first:
            consumers.reverse()
        for oid, doc in consumers:
            receiver = Frame()
            receiver.owner, receiver.event_source = sender.owner, sender.owner
            receiver.core = sender.owner.mods[134279388]
            receiver.skill = Entity(oid)
            receiver.variables[("INTEGER", repair.WAVE)] = sender.variables[("INTEGER", repair.WAVE)]
            receiver.variables[("INTEGER", repair.PHASE)] = sender.variables[("INTEGER", repair.PHASE)]
            receiver.receive(doc)
            sender.trace.extend(receiver.trace)

    def test_old_dead_target_loses_resource_new_retains_it(self):
        old = Frame()
        old.target.alive = False
        old.entry(self.old)
        self.assertEqual(old.core.stack, 1)
        new = Frame()
        new.target.alive = False
        new.entry(self.new)
        self.assertEqual(new.core.stack, 3)
        self.assertFalse(new.core.kv[repair.BUSY])
        self.assertIsNone(new.mover)

    def test_absent_friendly_target_and_absent_core_do_not_consume(self):
        for mode in ("none", "deleted", "friendly", "missing_core", "dead_owner"):
            with self.subTest(mode=mode):
                frame = Frame()
                if mode == "none": frame.owner.target = None
                if mode == "deleted": frame.target.exists = False
                if mode == "friendly": frame.target.team = "red"
                if mode == "missing_core": frame.core.exists = False
                if mode == "dead_owner": frame.owner.alive = False
                frame.entry(self.new)
                self.assertEqual(frame.core.stack, 3)
                self.assertIsNone(frame.mover)

    def test_valid_target_consumes_once_before_any_damage(self):
        frame = Frame()
        frame.begin(self.new)
        self.assertEqual(frame.core.stack, 1)
        self.assertTrue(frame.core.kv[repair.BUSY])
        self.assertEqual([e[0] for e in frame.trace].count("consume"), 1)
        self.assertFalse(any(e[0] == "damage" for e in frame.trace))
        frame.selection = [frame.target, Entity(3, team="blue"), Entity(4, team="blue"), Entity(5, team="blue")]
        frame.finish()
        self.assertEqual([e[1].key for e in frame.trace if e[0] == "damage"], [2, 3, 4])
        self.assertEqual([e[0] for e in frame.trace].count("consume"), 1)
        self.assertFalse(frame.core.kv[repair.BUSY])
        self.assertEqual([e[0] for e in frame.trace].count("notify_request"), 1)
        before = deepcopy(frame.trace)
        frame.finish()
        self.assertEqual(len(frame.trace), len(before))

    def test_full_distance_and_snapshot_path_after_arrival_or_target_moves(self):
        old, new = Frame(), Frame()
        old.begin(self.old)
        new.begin(self.new)
        self.assertEqual(old.trace[-1], ("mover_request", 700.0))
        self.assertEqual(new.trace[-1], ("mover_request", 1000.0))
        old.owner.point = new.owner.point = (1000.0, 0.0, 0.0)
        find_shape = lambda frame: next(n for n in repair.walk(frame.mover) if n.get("sub_type") == "UNIT_LIST_IN_SHAPE")
        center, (width, length, angle) = new.value(find_shape(new))
        self.assertEqual(center, (500.0, 0.0, 0.0))
        self.assertEqual((width, length, angle), (200.0, 1000.0, 0.0))
        self.assertEqual(old.value(find_shape(old))[1][1], 0.0)
        new.target.point = (2100.0, 0.0, 600.0)
        self.assertEqual(new.value(find_shape(new)), (center, (width, length, angle)))
        # Independent expected path set, including the formerly missed origin half.
        points = [(100, 0), (500, 0), (900, 0), (500, 101), (1200, 0)]
        inside = [p for p in points if abs(p[0] - center[0]) <= length / 2 and abs(p[1] - center[2]) <= width / 2]
        self.assertEqual(inside, [(100, 0), (500, 0), (900, 0)])

    def test_dead_primary_does_not_block_snapshot_path_or_use_a_slot(self):
        frame = Frame()
        frame.begin(self.new)
        frame.target.exists = False
        frame.selection = [Entity(i, team="blue") for i in (3, 4, 5, 6)]
        frame.finish()
        self.assertEqual([e[1].key for e in frame.trace if e[0] == "damage"], [3, 4, 5])

    def test_selection_filters_absent_dead_and_friendly_actors(self):
        frame = Frame()
        frame.begin(self.new)
        frame.selection = [Entity(3, exists=False), Entity(4, alive=False, team="blue"), Entity(5), Entity(6, team="blue")]
        frame.finish()
        self.assertEqual([e[1].key for e in frame.trace if e[0] == "damage"], [2, 6])

    def test_async_lost_core_replacement_dead_owner_and_lost_skill(self):
        for scenario in ("lost_core", "replaced_core", "dead_owner", "deleted_owner", "lost_skill"):
            with self.subTest(scenario=scenario):
                frame = Frame()
                frame.begin(self.new)
                replacement = Entity(134279388, stack=3)
                if scenario == "lost_core": frame.core.exists = False
                if scenario == "replaced_core": frame.owner.mods[134279388] = replacement
                if scenario == "dead_owner": frame.owner.alive = False
                if scenario == "deleted_owner": frame.owner.exists = False
                if scenario == "lost_skill": frame.skill.exists = False
                frame.selection = [Entity(3, team="blue")]
                frame.finish()
                self.assertFalse(any(e[0] in ("damage", "notify_request") for e in frame.trace))
                self.assertEqual(replacement.stack, 3)
                self.assertEqual(replacement.kv, {})

    def test_damage_reentry_invalidates_objects_before_next_target_and_cleanup(self):
        for scenario in ("dead_owner", "lost_core", "replacement", "lost_skill"):
            frame = Frame()
            frame.begin(self.new)
            replacement = Entity(134279388, stack=3)
            def invalidate(f):
                if scenario == "dead_owner": f.owner.alive = False
                if scenario == "lost_core": f.core.exists = False
                if scenario == "replacement": f.owner.mods[134279388] = replacement
                if scenario == "lost_skill": f.skill.exists = False
            frame.on_damage = invalidate
            frame.selection = [Entity(3, team="blue"), Entity(4, team="blue")]
            frame.finish()
            self.assertEqual([e[1].key for e in frame.trace if e[0] == "damage"], [2], scenario)
            self.assertFalse(any(e[0] == "notify_request" for e in frame.trace), scenario)
            self.assertEqual(replacement.kv, {})

    def test_revalidates_after_secondary_damage_as_well(self):
        frame = Frame()
        frame.begin(self.new)
        def lose_after_second(f):
            if sum(e[0] == "damage" for e in f.trace) == 2:
                f.core.exists = False
        frame.on_damage = lose_after_second
        frame.selection = [Entity(i, team="blue") for i in (3, 4, 5)]
        frame.finish()
        self.assertEqual([e[1].key for e in frame.trace if e[0] == "damage"], [2, 3])
        self.assertFalse(any(e[0] == "notify_request" for e in frame.trace))

    def test_old_callback_contract_does_not_clear_a_newer_instance(self):
        old = Frame()
        old.begin(self.new)
        new = Frame()
        new.owner, new.target, new.skill = old.owner, old.target, old.skill
        new.owner.mods[134279388] = new.core
        old.core.exists = False
        new.begin(self.new)
        old.finish()
        self.assertTrue(new.core.kv[repair.BUSY])
        self.assertEqual(new.core.stack, 1)
        new.finish()
        self.assertFalse(new.core.kv[repair.BUSY])
        self.assertEqual([e[1].key for e in new.trace if e[0] == "damage"], [2])

    def test_consume_reentry_does_not_start_mover_for_lost_core(self):
        frame = Frame()
        frame.on_consume = lambda f: setattr(f.core, "exists", False)
        frame.entry(self.new)
        self.assertIsNone(frame.mover)
        self.assertFalse(any(e[0] == "damage" for e in frame.trace))

    def test_terminal_cleanup_idempotent_and_no_hit_completion_notification(self):
        for slot in (6, 7):
            frame = Frame()
            frame.begin(self.new)
            frame.finish(slot)
            self.assertFalse(frame.core.kv[repair.BUSY])
            frame.finish()
            self.assertFalse(any(e[0] in ("damage", "notify_request") for e in frame.trace))
        frame = Frame()
        frame.begin(self.new)
        frame.target.alive = False
        frame.finish()
        self.assertEqual(sum(e[0] == "notify_request" for e in frame.trace), 1)
        self.assertEqual(frame.owner.kv[repair.EVENT_HITS], 0)
        self.assertFalse(frame.owner.kv[repair.EVENT_OPEN])

    def test_zero_hit_keeps_four_star_buff_without_six_star_refund(self):
        for order in (False, True):
            frame = Frame()
            frame.begin(self.new)
            frame.target.alive = False
            frame.on_notify = lambda f: self.dispatch(f, order)
            frame.finish()
            buffs = [e for e in frame.trace if e[0] == "buff_request"]
            self.assertEqual(len(buffs), 1)
            self.assertEqual(buffs[0][1], 134283930)
            self.assertEqual(buffs[0][3][2], 3.0)
            self.assertFalse(any(e[0] == "refund_request" for e in frame.trace))
            self.assertEqual(frame.core.stack, 1)
            self.assertFalse(frame.owner.kv[repair.EVENT_OPEN])

    def test_original_six_star_refunded_zero_hit_completion(self):
        old = Frame()
        old.core.stack = 1
        old.receive(sunce_consumer_fixture())
        self.assertEqual(old.core.stack, 2)
        new = Frame()
        new.core.stack = 1
        new.owner.kv.update({repair.EVENT_OPEN: True, repair.EVENT_HITS: 0.0,
                             repair.EVENT_CORE: new.core, repair.EVENT_WAVE: 1})
        new.receive(self.six)
        self.assertEqual(new.core.stack, 1)

    def test_positive_hit_both_consumers_and_exactly_one_refund(self):
        for order in (False, True):
            frame = Frame()
            frame.begin(self.new)
            frame.selection = [Entity(3, team="blue"), Entity(4, team="blue")]
            frame.on_notify = lambda f: self.dispatch(f, order)
            frame.finish()
            self.assertEqual(sum(e[0] == "buff_request" for e in frame.trace), 1)
            self.assertEqual(sum(e[0] == "refund_request" for e in frame.trace), 1)
            self.assertEqual(frame.core.stack, 2)
            self.assertEqual(frame.owner.kv[repair.EVENT_HITS], 3)
            self.assertFalse(frame.owner.kv[repair.EVENT_OPEN])
            self.dispatch(frame)
            self.assertEqual(sum(e[0] == "refund_request" for e in frame.trace), 1)

    def test_stale_snapshot_from_previous_wave_or_core_never_refunds(self):
        for scenario in ("closed", "old_wave", "old_core", "old_phase", "other_unit"):
            frame = Frame()
            frame.owner.kv.update({repair.EVENT_OPEN: True, repair.EVENT_HITS: 3.0,
                                   repair.EVENT_WAVE: 1, repair.EVENT_CORE: frame.core})
            if scenario == "closed": frame.owner.kv[repair.EVENT_OPEN] = False
            if scenario == "old_wave": frame.variables[("INTEGER", repair.WAVE)] = 2
            if scenario == "old_core": frame.owner.kv[repair.EVENT_CORE] = Entity(134279388)
            if scenario == "old_phase": frame.variables[("INTEGER", repair.PHASE)] = -2
            if scenario == "other_unit": frame.event_source = Entity(999)
            frame.receive(self.six)
            self.assertEqual(frame.core.stack, 3)
            self.assertFalse(any(e[0] == "refund_request" for e in frame.trace))

    def test_previous_wave_callback_cannot_publish_or_clear_a_new_wave(self):
        frame = Frame()
        frame.begin(self.new)
        frame.variables[("INTEGER", repair.WAVE)] = 2
        frame.owner.kv.update({repair.EVENT_OPEN: True, repair.EVENT_WAVE: 2,
                               repair.EVENT_CORE: frame.core, repair.EVENT_HITS: 2.0})
        frame.trace.clear()
        frame.finish()
        self.assertEqual(frame.trace, [])
        self.assertTrue(frame.core.kv[repair.BUSY])
        self.assertTrue(frame.owner.kv[repair.EVENT_OPEN])
        self.assertEqual(frame.owner.kv[repair.EVENT_WAVE], 2)

    def test_gain_and_loss_close_old_dispatch_windows(self):
        for doc in (self.new, self.six):
            for key in ("1959489540", "225054724"):
                frame = Frame()
                frame.owner.kv[repair.EVENT_OPEN] = True
                # Original dynamic registration remains opaque; run only the
                # explicitly added lease-initialization prefix action.
                frame.run(doc["trigger_dict"][key]["action"][:1])
                self.assertFalse(frame.owner.kv[repair.EVENT_OPEN])

    def test_preserves_unknown_p1_fields_actions_ids_options_and_disabled_sfx(self):
        original = deepcopy(self.old)
        entry = original["trigger_dict"]["1051000836"]
        entry["p1_extension"] = {"id": 9007199254740993123}
        marker = a("P1_UNKNOWN_ACTION", 9007199254740993125, x(100003, 1, "P1"))
        entry["action"].insert(0, marker)
        for eid in (105047244999002, 141803520499014):
            repair.anchor(entry, "SET_ENTITY_KV", eid)["p1_counter_metadata"] = {"keep": eid}
        mover = repair.anchor(entry, "CREATE_STRAIGHT_MOVER")
        mover["p1_mover_option"] = [123, {"keep": True}]
        mover["args_list"][5]["args_list"].insert(0, deepcopy(marker) | {"element_id": 9007199254740993126})
        fixed = repair.patch_sunce(original)
        self.assertEqual(fixed["trigger_dict"]["1051000836"]["p1_extension"], entry["p1_extension"])
        self.assertEqual(sum(n.get("action_type") == "P1_UNKNOWN_ACTION" for n in repair.walk(fixed)), 2)
        new_mover = repair.anchor(fixed, "CREATE_STRAIGHT_MOVER")
        self.assertEqual(new_mover["p1_mover_option"], mover["p1_mover_option"])
        self.assertEqual(new_mover["op_arg_enable"], mover["op_arg_enable"])
        disabled = next(n for n in repair.walk(fixed) if n.get("element_id") == 105047244999003)
        self.assertFalse(disabled["enable"])
        for event in ("1959489540", "225054724"):
            self.assertEqual(fixed["trigger_dict"][event]["action"][1:], original["trigger_dict"][event]["action"])
        ids = [n["element_id"] for n in repair.walk(fixed) if "element_id" in n]
        self.assertEqual(len(ids), len(set(ids)))
        for eid in (105047244999002, 141803520499014):
            self.assertEqual(repair.anchor(fixed, "SET_VARIABLE", eid)["p1_counter_metadata"], {"keep": eid})
        before = deepcopy(original)
        repair.patch_sunce(original)
        self.assertEqual(original, before)

    def test_unknown_engine_operations_are_rejected(self):
        frame = Frame()
        with self.assertRaises(NotImplementedError):
            frame.run([a("FAKE_ENGINE_SUCCESS", 1)])


class BuildTests(unittest.TestCase):
    def sources(self):
        docs = {f"modifier/{oid}.json": modifier_fixture(oid) for oid in repair.MODIFIERS}
        docs.update({f"editor_table/modifierall/{oid}.json": {"key": oid} for oid in repair.MODIFIERS})
        docs[repair.SUNCE] = sunce_fixture()
        docs[repair.SUNCE_SIX] = sunce_consumer_fixture()
        return docs

    def test_build_rereads_latest_root_without_overlay_or_writes(self):
        roots = {Path("first"): self.sources(), Path("second"): self.sources()}
        roots[Path("second")][repair.SUNCE]["P1_after_publish"] = 9007199254740993129
        reads = []
        def load(root, rel):
            reads.append((root, rel))
            return deepcopy(roots[root][rel])
        with patch.object(repair, "load", side_effect=load), patch.object(repair, "audit_callers", return_value=[]), \
             patch.object(Path, "write_text", side_effect=AssertionError("must not write")), \
             patch.object(Path, "write_bytes", side_effect=AssertionError("must not write")):
            first, _ = repair.build(Path("first"))
            roots[Path("first")]["modifier/134283923.json"]["P1_latest"] = "new value"
            fresh, _ = repair.build(Path("first"))
            second, _ = repair.build(Path("second"))
        self.assertNotIn("P1_latest", first["modifier/134283923.json"])
        self.assertEqual(fresh["modifier/134283923.json"]["P1_latest"], "new value")
        self.assertEqual(second[repair.SUNCE]["P1_after_publish"], 9007199254740993129)
        self.assertEqual(set(fresh), {f"modifier/{oid}.json" for oid in repair.MODIFIERS} | {repair.SUNCE, repair.SUNCE_SIX})
        self.assertNotIn("modifier/134279388.json", fresh)
        self.assertEqual(reads.count((Path("first"), repair.SUNCE)), 2)
        new_ids = []
        for rel, doc in fresh.items():
            source_ids = {n["element_id"] for n in repair.walk(roots[Path("first")][rel]) if "element_id" in n}
            new_ids.extend(n["element_id"] for n in repair.walk(doc)
                           if "element_id" in n and n["element_id"] not in source_ids)
        self.assertEqual(len(new_ids), len(set(new_ids)))

    def test_caller_gain_and_each_level_are_audited_without_mutation(self):
        docs = caller_fixtures()
        before = deepcopy(docs)
        with patch.object(repair, "load", side_effect=lambda root, rel: docs[rel]), patch.object(repair.os, "walk", return_value=[]):
            notes = repair.audit_callers(Path("fixture"))
        self.assertEqual(docs, before)
        self.assertEqual([len(n["ratio_writes"]) for n in notes[:4]], [0, 6, 6, 6])
        doc = docs["ability/134284010.json"]
        cases = doc["trigger_dict"]["26066946"]["action"][0]["args_list"][1]["args_list"]
        cases[1]["args_list"][1]["args_list"].append(cases[0]["args_list"][1]["args_list"].pop())
        # Six total writes are insufficient if one level has none and another has two.
        with patch.object(repair, "load", side_effect=lambda root, rel: docs[rel]), patch.object(repair.os, "walk", return_value=[]):
            with self.assertRaisesRegex(repair.ReviewError, "gain/level ratio source"):
                repair.audit_callers(Path("fixture"))

    def test_caller_unit_drift_or_missing_related_ability_is_not_silently_converted(self):
        for drift in ("units", "association"):
            docs = caller_fixtures()
            if drift == "units":
                docs["editor_table/abilityall/134284010.json"]["kv"][repair.RATIO]["value"] = 25
            else:
                docs["ability/134284010.json"]["trigger_dict"]["1959489540"]["action"][-1]["op_arg_enable"][1] = False
            with patch.object(repair, "load", side_effect=lambda root, rel: docs[rel]), patch.object(repair.os, "walk", return_value=[]):
                with self.assertRaises(repair.ReviewError):
                    repair.audit_callers(Path("fixture"))

    @unittest.skipUnless(LIVE.is_dir(), "real map3 fixture is not available")
    def test_current_native_map_build_and_dependency_audit(self):
        with patch.object(Path, "write_text", side_effect=AssertionError("live write")), \
             patch.object(Path, "write_bytes", side_effect=AssertionError("live write")):
            docs, notes = repair.build(LIVE)
        self.assertEqual(len(docs), 10)
        self.assertNotIn("modifier/134279388.json", docs)
        self.assertNotIn("ability/134283927.json", docs)
        audits = [n for n in notes if n["status"] == "audited_unchanged"]
        self.assertEqual(len(audits), 4)
        self.assertEqual([len(n["ratio_writes"]) for n in audits[1:]], [6, 6, 6])
        shared = next(n for n in notes if "callers" in n)
        self.assertGreater(len(shared["callers"]), 1)
        # No caller ECA or object-editor default is a candidate, including P1's
        # freshly fixed active-target actor scope.
        for item in audits:
            self.assertNotIn(item["file"], docs)
        for oid in (134283919, 134284010, 134284012):
            caller = repair.load(LIVE, f"ability/{oid}.json")
            auto = caller["trigger_dict"]["1959489540"]
            scopes = [n["args_list"][0]["items"][-1] for n in repair.enabled_walk(auto)
                      if n.get("arg_type") == 100006 and n.get("sub_type") == 11 and n.get("args_list")
                      and n["args_list"][0].get("items", [None, None])[1] == "\u76ee\u6807\u5355\u4f4d"]
            self.assertTrue(scopes)
            self.assertEqual(set(scopes), {"actor"})
        source = repair.load(LIVE, repair.SUNCE)
        for key, original in source["trigger_dict"].items():
            if key != "1051000836":
                fixed = docs[repair.SUNCE]["trigger_dict"][key]
                self.assertEqual(fixed["action"][1:], original["action"])
                self.assertEqual({k: v for k, v in fixed.items() if k != "action"},
                                 {k: v for k, v in original.items() if k != "action"})
        for oid in repair.MODIFIERS:
            old = repair.load(LIVE, f"modifier/{oid}.json")
            fixed = docs[f"modifier/{oid}.json"]
            loss = repair.trigger(old, "LOSS_MODIFIER")
            self.assertEqual(fixed["trigger_dict"][str(loss["trigger_id"])], loss)
            old_ids = {n["element_id"] for n in repair.walk(old) if "element_id" in n}
            new_ids = [n["element_id"] for n in repair.walk(fixed) if "element_id" in n and n["element_id"] not in old_ids]
            self.assertEqual(len(new_ids), len(set(new_ids)))

    @unittest.skipUnless(LIVE.is_dir(), "real map3 fixture is not available")
    def test_shared_native_ast_preserves_every_other_current_caller_amount(self):
        docs, notes = repair.build(LIVE)
        old = repair.load(LIVE, "modifier/134256265.json")
        new = docs["modifier/134256265.json"]
        old_attribute = repair.anchor(old, "ADD_MODIFIER_OWNER_ATTR")
        retained = repair.anchor(new, "ADD_MODIFIER_OWNER_ATTR", old_attribute["element_id"])
        self.assertEqual(retained, old_attribute)
        gain = repair.trigger(new, "OBTAIN_MODIFIER")
        guard = next(n for n in gain["action"] if n.get("action_type") == "IF_THEN_ELSE")
        callers = next(n["callers"] for n in notes if "callers" in n)
        checked = set()
        for caller in callers:
            oid = int(Path(caller["file"]).stem)
            amounts = [caller["default"]] + [v["args_list"][0] for v in caller["ratio_write_expressions"] if v.get("sub_type") == 1]
            # The identical retained AST also covers the nonliteral level/battle
            # expressions; numeric cases below cover the actual literal sources.
            for amount in amounts:
                if not isinstance(amount, (int, float)):
                    continue
                frame = Frame()
                frame.modifier.related = Entity(oid, kv={repair.ATTACK_RATIO: amount})
                frame.run([guard])
                result = frame.modifier.contributions[("attack_phy", "ATTR_ALL_RATIO")]
                self.assertAlmostEqual(result, -100 * amount if oid in repair.FRACTIONAL_ATTACK_CALLERS else -amount)
                checked.add(oid)
        self.assertEqual(checked, {int(Path(v["file"]).stem) for v in callers})

    @unittest.skipUnless(LIVE.is_dir(), "real map3 fixture is not available")
    def test_current_native_four_six_consumers_with_zero_and_positive_hit_packets(self):
        docs, _ = repair.build(LIVE)
        two, six = docs[repair.SUNCE], docs[repair.SUNCE_SIX]
        four = repair.load(LIVE, "ability/134283927.json")
        saved_four = deepcopy(four)
        # Visual operations are opaque and intentionally excluded from this
        # logic-only execution. No mover or engine event dispatch is simulated.
        two = deepcopy(two)
        for n in repair.walk(two):
            if str(n.get("action_type", "")).startswith("CREATE_SFX"):
                n["enable"] = False
        for hit in (False, True):
            for order in (False, True):
                frame = Frame()
                frame.begin(two)
                frame.target.alive = hit
                results = []
                def deliver(sender):
                    items = [(134283927, four), (134283929, six)]
                    for oid, doc in reversed(items) if order else items:
                        receiver = Frame()
                        receiver.owner, receiver.event_source, receiver.core = sender.owner, sender.owner, sender.core
                        receiver.skill = Entity(oid)
                        receiver.receive(doc)
                        results.extend(receiver.trace)
                frame.on_notify = deliver
                frame.finish()
                self.assertEqual(sum(e[0] == "buff_request" for e in results), 1)
                self.assertEqual(sum(e[0] == "refund_request" for e in results), int(hit))
                self.assertEqual(frame.core.stack, 2 if hit else 1)
                self.assertFalse(frame.owner.kv[repair.EVENT_OPEN])
        self.assertEqual(four, saved_four)


if __name__ == "__main__":
    unittest.main()

"""P1 state regressions against the four real, unmodified map3 native ASTs.

Set Y3_P1_STATE_ROOT to inspect another snapshot. No fixtures, bytecode or
candidates are written. This is a bounded statement/formula model, not Y3:
registration is checked, conditions are deliberately eager, unavailable event
parameters and unsupported operations fail. Stack callbacks are tested both
immediately and queued; neither timing is asserted to be the engine contract.
Rendering, general combat, buff cover rules and engine callback teardown are
not emulated. Expected numbers/lifecycle decisions are specified independently
of the builder. Actual editor/runtime acceptance is deliberately not claimed.
"""
from __future__ import annotations

import copy
from collections import Counter
from dataclasses import dataclass, field
import hashlib
import json
import os
from pathlib import Path
import unittest
from unittest.mock import patch

from tools import y3_hero_repair_p1_state as repair


ROOT = Path(os.environ.get("Y3_P1_STATE_ROOT", "D:/littl/testTempFile/ProjectMonster02/maps/map3"))
DIANWEI, ZHANGLIAO, CAOREN, PASSIVE_DIANWEI = repair.FILES
REACHED = "\u5f53\u524d\u6b7b\u6218\u6570"
MARKED = "\u9707\u6151\u5355\u4f4d"
POSITION = "\u5f52\u5c5e\u9635\u578b\u7f16\u53f7"


def walk(value):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk(child)


def by_id(doc, element_id):
    return [n for n in walk(doc) if n.get("element_id") == element_id]


@dataclass(eq=False)
class Entity:
    kind: str = "unit"
    valid: bool = True
    resource: int = 0
    stack: int = 1
    hp: float = 100
    max_hp: float = 100
    team: int = 1
    kv: dict = field(default_factory=dict)
    modifiers: list = field(default_factory=list)
    contributions: dict = field(default_factory=dict)


class VM:
    OPAQUE = {"PRINT_MESSAGE_ACTION_TO_DIALOG", "SET_SFX_SCALE", "ENABLE_SFX_VISIBLE", "DELETE_SFX_ENTITY"}

    def __init__(self, doc, owner=None, current=None, source=None, callback_mode="immediate"):
        self.doc = doc
        self.owner = owner if owner is not None else Entity()
        self.current = current if current is not None else Entity("buff", kv={REACHED: 0})
        self.source = source
        self.ability = Entity("ability")
        self.variables = {name: None if kind.endswith("ENTITY") else value
                          for kind, values in doc["variable_dict"].items()
                          for name, value in values.items()}
        self.registered = set()
        self.context = None
        self.damage_target = None
        self.damage = 100.0
        self.delta = 0
        self.stack_trace = []
        self.removed = []
        self.created = []
        self.opaque = []
        self.pending = []
        self.callback_mode = callback_mode

    def require(self, value, kind=None):
        if not isinstance(value, Entity) or not value.valid or (kind and value.kind != kind):
            raise AssertionError("Invalid native operand: " + str(kind))
        return value

    def lookup(self, unit, key):
        found = [m for m in self.require(unit, "unit").modifiers if m.valid and m.resource == key]
        return found[-1] if found else None

    @staticmethod
    def ref(node):
        args = node["args_list"]
        if len(args) == 1 and isinstance(args[0], dict) and args[0].get("__tuple__"):
            kind, name, scope = args[0]["items"]
            if scope != "actor":
                raise AssertionError("Unsupported variable scope")
            return kind, name
        return None

    def ev(self, node):
        subtype, args = node["sub_type"], node["args_list"]
        ref = self.ref(node)
        if ref:
            return self.variables[ref[1]]
        if subtype == 1:
            if len(args) != 1 or isinstance(args[0], (dict, list)):
                raise AssertionError("Malformed literal; no expression-in-resource coercion")
            return args[0]
        if subtype == "CUR_MODIFIER":
            return self.current
        if subtype == "MODIFIER_OWNER":
            return self.owner
        if subtype == "MODIFIER_RELEASER":
            if self.context not in {"gain", "loss"}:
                raise AssertionError("Unavailable MODIFIER_RELEASER")
            return self.source
        if subtype == "ABILITY_OWNER":
            if self.context not in {"obtain_ability", "phase"}:
                raise AssertionError("Unavailable ABILITY_OWNER")
            return self.owner
        if subtype == "CUR_ABILITY":
            return self.ability
        if subtype == "GET_MODIFIER_FROM_EVENT":
            if self.context != "layer":
                raise AssertionError("Unavailable layer event modifier")
            return self.current
        if subtype == "GET_MODIFIER_LAYER_CHANGE_VALUE":
            if self.context != "layer":
                raise AssertionError("Unavailable layer event delta")
            return self.delta
        if subtype == "DAMAGE_TARGET_UNIT":
            if self.context != "damage":
                raise AssertionError("Unavailable damage target")
            return self.damage_target
        if subtype == "HURT_DAMAGE":
            if self.context != "damage":
                raise AssertionError("Unavailable damage value")
            return self.damage
        if subtype == "NONE_UNIT":
            return None
        if subtype == "GET_HP_CUR":
            return self.require(self.ev(args[0]), "unit").hp
        if subtype == "GET_UNIT_ATTR":
            unit = self.require(self.ev(args[0]), "unit")
            if [self.ev(a) for a in args[1:]] != ["ATTR_RESULT", "hp_max"]:
                raise AssertionError("Unsupported attribute query")
            return unit.max_hp
        if subtype in {"GET_INTEGER_KV", "GET_UNIT_ENTITY_KV"}:
            entity = self.require(self.ev(args[0]))
            return entity.kv[self.ev(args[1])]
        if subtype == "GET_MOD_STACK":
            return self.require(self.ev(args[0]), "buff").stack
        if subtype == "GET_LAST_MODIFIER_INSTANCE":
            return self.lookup(self.ev(args[0]), self.ev(args[1]))
        if subtype == "UNIT_HAS_MODIFIER":
            return self.lookup(self.ev(args[0]), self.ev(args[1])) is not None
        if subtype == "IS_ALLY":
            left, right = [self.require(self.ev(a), "unit") for a in args]
            return left.team == right.team
        if subtype == "GET_CUS_EVENT_PARAM":
            if self.context != "phase":
                raise AssertionError("Unavailable phase event parameter")
            if self.ev(args[0]) != "\u9636\u6bb5\u7f16\u53f7":
                raise AssertionError("Unsupported event parameter")
            return 2
        if subtype in {"MATH_OPERATION", "ARITHMETIC_OPERATION"}:
            left, operator, right = [self.ev(a) for a in args]
            operations = {"+": lambda: left + right, "-": lambda: left - right,
                          "*": lambda: left * right}
            if operator not in operations:
                raise AssertionError("Unsupported numeric operator")
            return operations[operator]()
        if subtype == "ADD_MODIFIER":
            unit, key = [self.ev(a) for a in args]
            self.require(unit, "unit")
            if self.lookup(unit, key) is not None:
                raise AssertionError("Buff-cover behavior intentionally unmodelled")
            optional = node.get("op_arg", [])
            enabled = node.get("op_arg_enable", [])
            if enabled[:2] != [True, True]:
                raise AssertionError("Source/ability association must be enabled")
            source, ability = self.ev(optional[0]), self.ev(optional[1])
            buff = Entity("buff", resource=key, kv={"test_source": source, "test_ability": ability})
            unit.modifiers.append(buff)
            self.created.append(buff)
            return buff
        raise AssertionError("Unsupported native expression: " + str(subtype))

    def cond(self, node):
        kind, args = node["condition_type"], node["args_list"]
        if kind == "TYPE_IS_EXIST":
            if args[0]["arg_type"] != 100006:
                raise AssertionError("Unverified existence operand type")
            value = self.ev(args[0])
            return isinstance(value, Entity) and value.kind == "unit" and value.valid
        if kind == "BOOL_NOT":
            result = self.ev(args[0])
            if not isinstance(result, bool):
                raise AssertionError("No host-language truthiness")
            return not result
        if kind == "OR":
            return any([self.cond(c) for c in args[0]["args_list"] if c.get("enable") is not False])
        if kind == "HAS_KV_ANY":
            return self.ev(args[1]) in self.require(self.ev(args[0])).kv
        if kind == "UNIT_HAS_TAG":
            return self.ev(args[1]) in self.require(self.ev(args[0]), "unit").kv.get("test_tags", [])
        if kind in {"FLOAT_COMPARE", "BOOL_COMPARE", "UNIT_COMPARE", "MODIFIER_COMPARE"}:
            left, operator, right = [self.ev(a) for a in args]
            return {"==": lambda: left == right, "!=": lambda: left != right,
                    "<": lambda: left < right, "<=": lambda: left <= right,
                    ">": lambda: left > right, ">=": lambda: left >= right}[operator]()
        raise AssertionError("Unsupported native condition: " + str(kind))

    def dispatch(self, tid, context):
        trigger = self.doc["trigger_dict"][str(tid)]
        if trigger.get("p_trigger_id"):
            if tid not in self.registered:
                raise AssertionError("Unregistered dynamic trigger")
        elif trigger["enabled"] is not True:
            raise AssertionError("Disabled root trigger")
        previous, self.context = self.context, context
        try:
            if all([self.cond(c) for c in trigger["condition"] if c.get("enable") is not False]):
                self.run(trigger["action"])
        finally:
            self.context = previous

    def change_stack(self, buff, value):
        self.require(buff, "buff")
        old, buff.stack = buff.stack, value
        self.stack_trace.append(value)
        if buff is self.current and 104562693 in self.registered and old != value:
            if self.callback_mode == "immediate":
                self.layer(value - old)
            else:
                self.pending.append(value - old)

    def layer(self, delta):
        self.delta = delta
        self.dispatch(104562693, "layer")

    def flush(self):
        pending, self.pending = self.pending, []
        for delta in pending:
            self.layer(delta)

    def run(self, actions):
        for action in actions:
            if isinstance(action, int):
                child = self.doc["trigger_dict"][str(action)]
                registration = child["sub_trigger_owner_set_var_action"]
                if registration["args_list"][1]["sub_type"] not in {"REG_MODIFIER_TRIGGER", "REG_ABILITY_TRIGGER"}:
                    raise AssertionError("Unsupported listener registration")
                self.variables[self.ref(registration["args_list"][0])[1]] = action
                self.registered.add(action)
                continue
            if action.get("enable") is False:
                continue
            kind, args = action["action_type"], action["args_list"]
            if kind in self.OPAQUE:
                self.opaque.append(kind)
            elif kind == "IF_THEN_ELSE":
                result = all([self.cond(c) for c in args[0]["args_list"] if c.get("enable") is not False])
                self.run(args[1 if result else 2]["args_list"])
            elif kind == "SET_VARIABLE":
                self.variables[self.ref(args[0])[1]] = self.ev(args[1])
            elif kind == "SET_ENTITY_KV":
                self.require(self.ev(args[0])).kv[self.ev(args[1])] = self.ev(args[2])
            elif kind == "SET_BUFF_STACK":
                self.change_stack(self.ev(args[0]), self.ev(args[1]))
            elif kind == "ADD_MODIFIER_OWNER_ATTR":
                buff = self.require(self.ev(args[0]), "buff")
                attr, mode, delta = [self.ev(a) for a in args[1:]]
                if mode != "ATTR_ALL_RATIO":
                    raise AssertionError("Unsupported contribution mode")
                values = self.owner.contributions.setdefault(buff, {})
                values[attr] = values.get(attr, 0) + delta
            elif kind == "CLEAR_MODIFIER_OWNER_ATTR":
                self.owner.contributions.pop(self.require(self.ev(args[0]), "buff"), None)
            elif kind == "ADD_MODIFIER":
                self.ev({"sub_type": kind, "args_list": args,
                         "op_arg": action["op_arg"], "op_arg_enable": action["op_arg_enable"]})
            elif kind == "REMOVE_BUFF_INS":
                buff = self.require(self.ev(args[0]), "buff")
                buff.valid = False
                self.removed.append(buff)
            elif kind == "SET_CUR_DAMAGE":
                self.damage = self.ev(args[0])
            elif kind == "UNREG_TRIGGER":
                self.registered.discard(self.ev(args[0]))
            else:
                raise AssertionError("Unsupported native action: " + str(kind))

    def obtain_dianwei(self):
        self.context = "gain"
        # Creation/rendering is outside this model; keep registration and state writes.
        actions = self.doc["trigger_dict"]["1485688834"]["action"]
        self.run([a for a in actions if isinstance(a, int) or a["action_type"] == "SET_ENTITY_KV"])
        self.context = None

    def hp_event(self, percent):
        self.owner.hp = self.owner.max_hp * percent / 100
        self.dispatch(1418035204, "hp")

    def contribution(self):
        return self.owner.contributions.get(self.current, {})

    def obtain_passive(self):
        self.owner.kv["test_tags"] = ["\u4ec6\u4ece\u4f19\u4f34"]
        self.dispatch(1959489540, "obtain_ability")

    def phase(self, position):
        self.owner.kv[POSITION] = position
        self.dispatch(892944388, "phase")


class NativeStateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw = {relative: (ROOT / relative).read_bytes() for relative in repair.FILES}
        cls.old = {relative: json.loads(raw) for relative, raw in cls.raw.items()}
        cls.new, cls.reports = repair.build(ROOT)
        errors = [r for r in cls.reports if r.get("severity") == "error"]
        if errors:
            raise AssertionError(errors)

    def vm(self, relative, fixed=True, **kwargs):
        return VM(copy.deepcopy((self.new if fixed else self.old)[relative]), **kwargs)

    def build_memory(self, docs):
        reads = []
        def read(path):
            relative = path.relative_to(Path("memory")).as_posix()
            reads.append(relative)
            return json.dumps(docs[relative]).encode("utf8")
        with patch.object(Path, "read_bytes", read), \
                patch.object(Path, "write_bytes", side_effect=AssertionError("Forbidden write")), \
                patch.object(Path, "write_text", side_effect=AssertionError("Forbidden write")):
            result = repair.build(Path("memory"))
        self.assertEqual(reads, list(repair.FILES))
        return result

    def test_old_low_hp_cycle_then_monotonic_candidate(self):
        old = self.vm(DIANWEI, False)
        old.obtain_dianwei()
        old.hp_event(20)
        self.assertEqual(old.stack_trace, [2, 3, 4])
        self.assertEqual(old.contribution()["attack_phy"], 30)
        old.hp_event(20)
        self.assertEqual(old.stack_trace, [2, 3, 4, 2, 3, 4])
        self.assertEqual(old.contribution()["attack_phy"], 50)
        old.hp_event(60)
        self.assertEqual(old.current.stack, 2)  # Healing wrongly discarded acquired stacks.

        for mode in ("immediate", "queued"):
            with self.subTest(callbacks=mode):
                fixed = self.vm(DIANWEI, callback_mode=mode)
                fixed.obtain_dianwei()
                fixed.hp_event(20)
                fixed.flush()
                self.assertEqual(fixed.stack_trace, [2, 3, 4])
                self.assertEqual(fixed.contribution(), {"attack_phy": 15, "attack_speed": 30, "ori_speed": 30})
                for hp in (20, 20, 60, 100, 20):
                    fixed.hp_event(hp)
                fixed.flush()
                self.assertEqual(fixed.stack_trace, [2, 3, 4])
                self.assertEqual(fixed.current.kv[REACHED], 4)
                self.assertEqual(fixed.current.stack, 4)
                self.assertEqual(fixed.contribution()["attack_phy"], 15)

    def test_old_negative_total_leaks_then_delta_withdraws(self):
        old = self.vm(DIANWEI, False)
        old.obtain_dianwei()
        old.hp_event(20)
        old.change_stack(old.current, 1)
        self.assertEqual(old.contribution()["attack_phy"], 30)
        fixed = self.vm(DIANWEI)
        fixed.obtain_dianwei()
        self.assertEqual(fixed.current.stack, 1)
        self.assertEqual(fixed.current.kv[REACHED], 1)
        self.assertEqual(fixed.contribution(), {})
        fixed.hp_event(20)
        fixed.change_stack(fixed.current, 2)
        self.assertEqual(fixed.contribution(), {"attack_phy": 5, "attack_speed": 10, "ori_speed": 10})
        fixed.change_stack(fixed.current, 1)
        fixed.layer(0)
        fixed.hp_event(20)
        self.assertEqual(fixed.current.stack, 1)  # Consumed thresholds must not be regranted.
        self.assertEqual(fixed.contribution(), {"attack_phy": 0, "attack_speed": 0, "ori_speed": 0})

    def test_threshold_boundaries_and_percent_points(self):
        fixed = self.vm(DIANWEI)
        fixed.obtain_dianwei()
        for hp, stack, atk, speed in [(100, 1, 0, 0), (75.01, 1, 0, 0), (75, 2, 5, 10),
                                      (50.01, 2, 5, 10), (50, 3, 10, 20), (25.01, 3, 10, 20), (25, 4, 15, 30)]:
            fixed.hp_event(hp)
            self.assertEqual(fixed.current.stack, stack)
            self.assertEqual(fixed.contribution().get("attack_phy", 0), atk)
            self.assertEqual(fixed.contribution().get("attack_speed", 0), speed)
            self.assertAlmostEqual(200 * (1 + fixed.contribution().get("attack_phy", 0) / 100),
                                   {1: 200, 2: 210, 3: 220, 4: 230}[stack])

    def test_dianwei_loss_scoped_and_reacquisition_isolated(self):
        owner = Entity()
        other = Entity("buff")
        owner.contributions[other] = {"attack_phy": 17}
        fixed = self.vm(DIANWEI, owner=owner)
        fixed.obtain_dianwei()
        fixed.hp_event(20)
        fixed.dispatch(594665475, "loss")
        self.assertEqual(owner.contributions, {other: {"attack_phy": 17}})
        self.assertEqual(fixed.registered, set())
        fresh = self.vm(DIANWEI, owner=owner)
        fresh.obtain_dianwei()
        self.assertEqual(fresh.current.kv[REACHED], 1)
        self.assertEqual(fresh.current.stack, 1)
        fresh.hp_event(75)
        self.assertEqual(fresh.contribution()["attack_phy"], 5)
        self.assertEqual(owner.contributions[other]["attack_phy"], 17)

    def intimidation(self, fixed=True, source=None, core=None):
        source = source if source is not None else Entity()
        if core is not None:
            source.modifiers.append(core)
        vm = self.vm(ZHANGLIAO, fixed, source=source)
        vm.dispatch(1625518081, "gain")
        return vm, source

    def test_old_damage_increases_then_candidate_ally_only_reduces(self):
        old, source = self.intimidation(False)
        for layer, expected in ((1, 104), (2, 108), (3, 112)):
            old.current.stack, old.damage = layer, 100
            old.damage_target = source
            old.dispatch(512499716, "damage")
            self.assertAlmostEqual(old.damage, expected)
        fixed, source = self.intimidation()
        ally, enemy = Entity(team=1), Entity(team=2)
        for layer, expected in ((1, 96), (2, 92), (3, 88)):
            for target, result in ((ally, expected), (source, 100), (enemy, 100), (None, 100)):
                fixed.current.stack, fixed.damage, fixed.damage_target = layer, 100, target
                fixed.dispatch(512499716, "damage")
                self.assertAlmostEqual(fixed.damage, result)
        source.valid = False
        fixed.damage, fixed.damage_target = 100, ally
        fixed.dispatch(512499716, "damage")
        self.assertEqual(fixed.damage, 100)

    def test_old_loss_null_error_then_missing_sources_safe(self):
        old, _ = self.intimidation(False)
        with self.assertRaisesRegex(AssertionError, "Invalid native operand"):
            old.dispatch(1726324738, "loss")
        for source in (None, Entity(), Entity(valid=False)):
            fixed = self.vm(ZHANGLIAO, source=source)
            fixed.dispatch(1625518081, "gain")
            fixed.dispatch(1726324738, "loss")
            self.assertEqual(fixed.registered, set())

    def test_loss_does_not_reset_replacement_core_or_new_target(self):
        for replacement, changed_target in ((True, False), (False, True)):
            with self.subTest(replacement=replacement, changed_target=changed_target):
                core = Entity("buff", resource=134259689, stack=4)
                fixed, source = self.intimidation(core=core)
                core.kv[MARKED] = fixed.owner
                if replacement:
                    core.valid = False
                    new_core = Entity("buff", resource=134259689, stack=4, kv={MARKED: fixed.owner})
                    source.modifiers.append(new_core)
                else:
                    core.kv[MARKED] = Entity()
                    new_core = core
                fixed.dispatch(1726324738, "loss")
                self.assertEqual(new_core.stack, 4)
                self.assertIsNotNone(new_core.kv[MARKED])
                self.assertEqual(fixed.registered, set())

    def test_old_loss_resets_new_wave_then_candidate_normal_loss_clears(self):
        old_core = Entity("buff", resource=134259689, stack=4)
        old, source = self.intimidation(False, core=old_core)
        old_core.valid = False
        new_core = Entity("buff", resource=134259689, stack=4)
        source.modifiers.append(new_core)
        old.dispatch(1726324738, "loss")
        self.assertEqual(new_core.stack, 1)  # Historical cross-instance corruption.
        core = Entity("buff", resource=134259689, stack=4)
        fixed, _ = self.intimidation(core=core)
        core.kv[MARKED] = fixed.owner
        fixed.dispatch(1726324738, "loss")
        self.assertEqual(core.stack, 1)
        self.assertIsNone(core.kv[MARKED])
        fixed.dispatch(1726324738, "loss")
        self.assertEqual(core.stack, 1)

    def test_passive_old_null_delete_and_churn_then_repeat_safe(self):
        for relative in (CAOREN, PASSIVE_DIANWEI):
            with self.subTest(ability=relative):
                old = self.vm(relative, False)
                old.obtain_passive()
                with self.assertRaisesRegex(AssertionError, "Invalid native operand"):
                    old.phase(4)
                old.phase(1)
                old.phase(1)
                self.assertEqual(len(old.created), 1)
                self.assertEqual(len(old.removed), 1)  # Applicable + present wrongly entered ELSE.
                fixed = self.vm(relative)
                fixed.obtain_passive()
                fixed.phase(4)
                for pos in (1, 1, 2, 3):
                    fixed.phase(pos)
                self.assertEqual(len(fixed.created), 1)
                self.assertEqual(fixed.removed, [])
                self.assertIs(fixed.created[0].kv["test_ability"], fixed.ability)
                fixed.phase(4)
                fixed.phase(4)
                self.assertEqual(fixed.removed, fixed.created)
                fixed.phase(1)
                self.assertEqual(len(fixed.created), 2)
                fixed.dispatch(225054724, "ability_loss")
                self.assertEqual(fixed.removed, fixed.created)
                self.assertEqual(fixed.registered, set())

    def test_passives_do_not_remove_other_source_or_replacement(self):
        for relative in (CAOREN, PASSIVE_DIANWEI):
            other = Entity("buff", resource=134279904)
            old = self.vm(relative, False, owner=Entity(modifiers=[other]))
            old.obtain_passive()
            old.phase(4)
            self.assertFalse(other.valid)
            other = Entity("buff", resource=134279904)
            fixed = self.vm(relative, owner=Entity(modifiers=[other]))
            fixed.obtain_passive()
            fixed.phase(1)
            fixed.phase(4)
            fixed.dispatch(225054724, "ability_loss")
            self.assertTrue(other.valid)
            self.assertEqual(fixed.created, [])
            self.assertEqual(fixed.removed, [])
            fixed = self.vm(relative)
            fixed.obtain_passive()
            fixed.phase(1)
            fixed.created[0].valid = False
            replacement = Entity("buff", resource=134279904)
            fixed.owner.modifiers.append(replacement)
            fixed.phase(4)
            fixed.dispatch(225054724, "ability_loss")
            self.assertTrue(replacement.valid)
            self.assertEqual(fixed.removed, [])

    def test_native_ast_ids_flags_and_unrelated_logic_preserved(self):
        self.assertEqual(set(self.new), set(repair.FILES))
        for relative, old in self.old.items():
            new = self.new[relative]
            before = Counter(n["element_id"] for n in walk(old) if "element_id" in n)
            after = Counter(n["element_id"] for n in walk(new) if "element_id" in n)
            self.assertFalse(before - after, relative)
            self.assertEqual(new["trigger_group_info"], old["trigger_group_info"])
            self.assertEqual(new["local_variable"], old["local_variable"])
            for tid, trigger in old["trigger_dict"].items():
                for key, value in trigger.items():
                    if key not in {"action"}:
                        self.assertEqual(new["trigger_dict"][tid][key], value, (relative, tid, key))
            disabled = [n for n in walk(old) if n.get("enable") is False]
            new_nodes = list(walk(new))
            for node in disabled:
                self.assertIn(node, new_nodes)
        old = self.old[DIANWEI]
        new = self.new[DIANWEI]
        self.assertEqual(new["trigger_dict"]["1050472449"], old["trigger_dict"]["1050472449"])
        for branch, target in zip(new["trigger_dict"]["1418035204"]["action"], (2, 3, 4)):
            check = branch["args_list"][0]["args_list"][1]
            self.assertEqual(check["args_list"][1], {"arg_type": 100015, "sub_type": 1, "args_list": ["<"]})
            active = [a for a in branch["args_list"][1]["args_list"] if a.get("enable") is True]
            self.assertEqual([a["action_type"] for a in active[:2]], ["SET_ENTITY_KV", "SET_BUFF_STACK"])
            self.assertEqual(active[0]["args_list"][2]["args_list"], [target])
        for relative in (CAOREN, PASSIVE_DIANWEI):
            outer = by_id(self.new[relative], 892944388000011)[0]
            self.assertEqual(len(outer["args_list"][0]["args_list"]), 1)
            self.assertEqual(outer["args_list"][1]["args_list"][0]["args_list"][0]["args_list"][0]["condition_type"], "BOOL_NOT")
            removed = by_id(self.new[relative], 892944388000015)[0]
            self.assertEqual(removed["args_list"][0]["sub_type"], 11)
            self.assertEqual(removed["args_list"][0]["args_list"][0]["items"], ["MODIFIER_ENTITY", repair.OWNED, "actor"])
            add = by_id(self.new[relative], 892944388000009)[0]
            self.assertEqual(add["action_type"], "SET_VARIABLE")
            native_add = self.old[relative]["trigger_dict"]["892944388"]["action"][0]["args_list"][1]["args_list"][0]
            self.assertEqual(add["args_list"][1]["op_arg"], native_add["op_arg"])
            self.assertEqual(add["args_list"][1]["op_arg_enable"], native_add["op_arg_enable"])

    def test_read_only_deterministic_and_reports_boundaries(self):
        result, reports = self.build_memory(self.old)
        self.assertEqual(result, self.new)
        self.assertEqual(repair.build(ROOT)[0], self.new)
        for relative, raw in self.raw.items():
            self.assertEqual((ROOT / relative).read_bytes(), raw)
            info = next(r for r in self.reports if r.get("path") == relative)
            self.assertEqual(info["source_sha256"], hashlib.sha256(raw).hexdigest())
        self.assertEqual(reports[-1]["code"], "verification_boundary")

    def test_unknown_fields_and_large_ids_preserved(self):
        docs = copy.deepcopy(self.old)
        big = 2**79 + 123
        for relative in repair.FILES:
            docs[relative]["user_unknown"] = {"precise_id": big}
            docs[relative]["trigger_dict"][next(iter(docs[relative]["trigger_dict"]))]["user_edit"] = big
        by_id(docs[CAOREN], 892944388000009)[0]["user_metadata"] = {"id": big}
        result, reports = self.build_memory(docs)
        self.assertFalse([r for r in reports if r.get("severity") == "error"])
        for relative in repair.FILES:
            self.assertEqual(result[relative]["user_unknown"], {"precise_id": big})
        self.assertEqual(by_id(result[CAOREN], 892944388000009)[0]["user_metadata"], {"id": big})
        self.assertEqual(json.loads(json.dumps(result))[CAOREN]["user_unknown"]["precise_id"], big)

    def test_review_drift_is_reported_without_partial_candidate(self):
        cases = [(DIANWEI, lambda d: by_id(d, 1418035204974271)[0].update(enable=False)),
                 (ZHANGLIAO, lambda d: by_id(d, 1726324738810133)[0]["args_list"][0].update(user_unknown=1)),
                 (CAOREN, lambda d: by_id(d, 892944388000015)[0]["args_list"][0].update(user_unknown=1))]
        for relative, mutate in cases:
            with self.subTest(path=relative):
                docs = copy.deepcopy(self.old)
                mutate(docs[relative])
                unchanged = copy.deepcopy(docs)
                candidates, reports = self.build_memory(docs)
                self.assertNotIn(relative, candidates)
                self.assertEqual(docs, unchanged)
                self.assertTrue(any(r.get("path") == relative and r.get("code") == "review_required" for r in reports))

    def test_bounded_model_rejects_unknown_semantics_and_event_leaks(self):
        vm = self.vm(DIANWEI)
        with self.assertRaisesRegex(AssertionError, "Unavailable layer"):
            vm.ev({"sub_type": "GET_MODIFIER_LAYER_CHANGE_VALUE", "args_list": []})
        with self.assertRaisesRegex(AssertionError, "Unsupported native expression"):
            vm.ev({"sub_type": "NOT_AN_ENGINE_API", "args_list": []})
        with self.assertRaisesRegex(AssertionError, "Unverified existence"):
            vm.cond({"condition_type": "TYPE_IS_EXIST", "args_list": [{"arg_type": 100076, "sub_type": "CUR_MODIFIER", "args_list": []}]})
        with self.assertRaisesRegex(AssertionError, "Unregistered dynamic"):
            vm.dispatch(1418035204, "hp")
        vm.obtain_dianwei()
        self.assertIn(1418035204, vm.registered)
        self.assertFalse(vm.doc["trigger_dict"]["1418035204"]["enabled"])
        vm.hp_event(75)
        self.assertEqual(vm.current.stack, 2)


if __name__ == "__main__":
    unittest.main()

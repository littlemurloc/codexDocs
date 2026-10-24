"""Native AST plus bounded offline P2 regressions, not an engine emulator.

Reads the current map (Y3_P2_STATE_ROOT may select a snapshot). Unsupported
APIs and unavailable event arguments fail. Shared auto-cast helper output is
an explicit fixture, not an implementation of that helper. Timers retain a
per-invocation local environment; the engine capture contract remains open.
The same-source cover model below tests bookkeeping only, not Y3 cover rules.
No live or scratch files are written; run Python with -B.
"""
from __future__ import annotations

from collections import Counter
import copy
from dataclasses import dataclass, field
import hashlib
import json
import os
from pathlib import Path
import unittest
from unittest.mock import patch

from tools import y3_hero_repair_p2_state as fix

ROOT = Path(os.environ.get("Y3_P2_STATE_ROOT", "D:/littl/testTempFile/ProjectMonster02/maps/map3"))
AUTO = "\u81ea\u52a8\u65bd\u6cd5"
COEFFICIENT = "\u4f24\u5bb3\u7cfb\u6570"
OLD_FULL = "3\u5c42\u989d\u5916\u5904\u7406"


@dataclass(eq=False)
class Entity:
    kind: str = "unit"
    valid: bool = True
    alive: bool = True
    team: int = 1
    resource: int = 0
    stack: int = 1
    maximum: int = 4
    kv: dict = field(default_factory=dict)
    tags: set = field(default_factory=set)
    modifiers: list = field(default_factory=list)
    contributions: dict = field(default_factory=dict)
    source: object = None
    related: object = None
    target: object = None
    ability_type: int = 2


class BreakLoop(Exception):
    pass


class VM:
    OPAQUE = {"CREATE_HARM_TEXT_NEW", "SET_UI_COMP_TEXT", "CALL_TRIGGER_FUNC",
              "PRINT_MESSAGE_ACTION_TO_DIALOG", "PLAY_ANIMATION", "DELETE_TIMER"}

    def __init__(self, doc, owner=None, current=None):
        self.doc = doc
        self.owner = owner if owner is not None else Entity(kv={AUTO: True}, tags={"\u4ec6\u4ece\u4f19\u4f34"})
        self.current = current if current is not None else Entity("buff", kv={OLD_FULL: False})
        self.skill = Entity("ability", kv={COEFFICIENT: 1.25})
        self.event_skill = self.skill
        self.event_unit = self.owner
        self.event_modifier = None
        self.killed = Entity(team=2, tags={"AI\u5355\u4f4d"})
        self.context = None
        self.actor = {name: value for values in doc["variable_dict"].values() for name, value in values.items()}
        self.local = {}
        self.global_values = {fix.WAVE: 1, fix.PHASE: 2}
        self.selected = None
        self.delta = 0
        self.registered = set()
        self.hits, self.commands, self.created, self.orbits, self.visuals = [], [], [], [], []
        self.now = 0.0
        self.timers = []
        self.on_mark = None
        self.with_layer = False
        self.auto_helper_result = True

    @staticmethod
    def ref(node):
        a = node["args_list"]
        if len(a) == 1 and isinstance(a[0], dict) and a[0].get("__tuple__"):
            return a[0]["items"]
        return None

    def require(self, obj, kind=None):
        if not isinstance(obj, Entity) or not obj.valid or (kind and obj.kind != kind):
            raise AssertionError("Invalid native operand " + str(kind))
        return obj

    def find(self, owner, key):
        items = [m for m in self.require(owner, "unit").modifiers if m.valid and m.resource == key]
        return items[-1] if items else None

    def assign(self, node, value):
        ref = self.ref(node)
        if ref is None or len(ref) != 3:
            raise AssertionError("Unsupported assignment operand")
        (_, name, scope) = ref
        if scope == "actor":
            self.actor[name] = value
        elif scope == "local":
            self.local[name] = value
        else:
            raise AssertionError("Unknown assignment scope")

    def ev(self, node):
        subtype, a = node["sub_type"], node["args_list"]
        ref = self.ref(node)
        if ref:
            if len(ref) == 2:
                return self.global_values[ref[1]]
            return (self.actor if ref[2] == "actor" else self.local)[ref[1]]
        if subtype == 1:
            if len(a) != 1 or isinstance(a[0], (dict, list)):
                raise AssertionError("No runtime expression inside resource literal")
            return a[0]
        if subtype == "CUR_MODIFIER":
            return self.current
        if subtype == "MODIFIER_OWNER":
            return self.owner
        if subtype == "ABILITY_OWNER":
            if self.context not in {"obtain", "timer", "spell", "custom", "global_layer", "delay"}:
                raise AssertionError("Unavailable ability owner")
            return self.owner
        if subtype == "CUR_ABILITY":
            return self.skill
        if subtype == "DAMAGE_ABILITY":
            if self.context != "release":
                raise AssertionError("Unavailable release ability")
            return self.event_skill
        if subtype == "GET_ABILITY_OWNER":
            return self.require(self.ev(a[0]), "ability").source
        if subtype == "TARGET_UNIT_IN_ABILITY":
            return self.require(self.ev(a[0]), "ability").target
        if subtype == "TYPE_OF_ABILITY":
            return self.require(self.ev(a[0]), "ability").ability_type
        if subtype == "KILLED_UNIT":
            if self.context != "death":
                raise AssertionError("Unavailable killed unit")
            return self.killed
        if subtype == "OWNER_PLAYER":
            return self.require(self.ev(a[0]), "unit").team
        if subtype == "RELATED_ABILITY_MODIFIER":
            return self.require(self.ev(a[0]), "buff").related
        if subtype == "GET_MODIFIER_FROM_EVENT":
            if self.context != "global_layer":
                raise AssertionError("Unavailable modifier event")
            return self.event_modifier
        if subtype == "GET_MODIFIER_ENTITY_METATYPE":
            return self.require(self.ev(a[0]), "buff").resource
        if subtype == "GET_MODIFIER_LAYER_CHANGE_VALUE":
            if self.context != "layer":
                raise AssertionError("Unavailable layer delta")
            return self.delta
        if subtype == "GET_CUS_EVENT_PARAM":
            if self.context != "custom":
                raise AssertionError("Unavailable custom event")
            key = self.ev(a[0])
            if key == "\u89e6\u53d1\u6280\u80fd":
                return self.event_skill
            if key == "\u89e6\u53d1\u5355\u4f4d":
                return self.event_unit
            raise AssertionError("Unsupported custom-event field")
        if subtype in {"GET_MOD_STACK", "GET_MOD_STACK_MAX"}:
            obj = self.require(self.ev(a[0]), "buff")
            return obj.stack if subtype == "GET_MOD_STACK" else obj.maximum
        if subtype == "GET_LAST_MODIFIER_INSTANCE":
            return self.find(self.ev(a[0]), self.ev(a[1]))
        if subtype == "UNIT_HAS_MODIFIER":
            return self.find(self.ev(a[0]), self.ev(a[1])) is not None
        if subtype == "NONE_UNIT":
            return None
        if subtype == "FOR_EACH_SELECTED_PROJECTILE":
            return self.selected
        if subtype in {"GET_UNIT_ENTITY_KV", "GET_MODIFIER_ENTITY_KV", "GET_BOOLEAN_KV", "GET_INTEGER_KV", "GET_FLOAT_KV", "GET_TABLE_KV", "GET_PROJECTILE_GROUP_KV"}:
            return self.require(self.ev(a[0])).kv[self.ev(a[1])]
        if subtype == "GET_UNIT_ATTR":
            self.require(self.ev(a[0]), "unit")
            if self.ev(a[1]) != "ATTR_RESULT":
                raise AssertionError("Unsupported attribute mode")
            key = self.ev(a[2])
            if key not in {"attack_phy", "attack_speed"}:
                raise AssertionError("Unsupported attribute")
            return 100.0
        if subtype in {"ARITHMETIC_OPERATION", "MATH_OPERATION"}:
            left, op, right = [self.ev(v) for v in a]
            return {"*": lambda: left * right, "/": lambda: left / right, "+": lambda: left + right, "-": lambda: left - right}[op]()
        if subtype == "INT_PLUS_ONE":
            return self.ev(a[0]) + 1
        if subtype == "GET_NEW_TABLE":
            return {}
        if subtype == "GET_TABLE_LENGTH":
            value = self.ev(a[0])
            if not isinstance(value, dict):
                raise AssertionError("Invalid table")
            return len(value)
        if subtype == "GET_UNIT_ENTITY_TABLE_VAR_ND":
            table, row, column = [self.ev(v) for v in a]
            return table[row][column]
        if subtype == "PROJECTILE_ENTITY_POINT":
            return self.require(self.ev(a[0]), "projectile")
        if subtype == "RANDOM_FLOAT":
            return sum(self.ev(v) for v in a) / 2  # Explicit scheduling fixture only.
        if subtype == "ABILITY_CD_LEFT_TIME":
            self.require(self.ev(a[0]), "ability")
            return 0.0
        if subtype == "97642c3d802a5935a73289745a266ac8":
            return self.auto_helper_result  # Separate shared-helper contract, not emulation.
        if subtype == "ADD_MODIFIER":
            owner, key = [self.ev(v) for v in a]
            self.require(owner, "unit")
            opts, enabled = node["op_arg"], node["op_arg_enable"]
            source = self.ev(opts[0]) if enabled[0] else None
            related = self.ev(opts[1]) if enabled[1] else None
            initial = self.ev(opts[4]) if len(enabled) > 4 and enabled[4] else 1
            existing = [m for m in owner.modifiers if m.valid and m.resource == key and m.source is source]
            if existing:
                created = existing[-1]
                created.stack = min(created.maximum, created.stack + initial)
            else:
                created = Entity("buff", resource=key, stack=initial, maximum=3, source=source, related=related)
                owner.modifiers.append(created)
            self.created.append((owner, created, self.ev(opts[2]) if enabled[2] else None))
            if self.on_mark and key == 134259870:
                self.on_mark(created)
            return created
        raise AssertionError("Unsupported native expression " + str(subtype))

    def cond(self, node):
        kind, a = node["condition_type"], node["args_list"]
        if kind == "TYPE_IS_EXIST":
            if a[0]["arg_type"] not in (100006, 100014):
                raise AssertionError("Unverified existence overload")
            obj = self.ev(a[0])
            return isinstance(obj, Entity) and obj.valid
        if kind == "HAS_KV_ANY":
            return self.ev(a[1]) in self.require(self.ev(a[0])).kv
        if kind == "UNIT_HAS_TAG":
            return self.ev(a[1]) in self.require(self.ev(a[0]), "unit").tags
        if kind == "UNIT_HAS_MODIFIER":
            return self.find(self.ev(a[0]), self.ev(a[1])) is not None
        if kind == "OR":
            return any([self.cond(c) for c in a[0]["args_list"] if c.get("enable") is not False])
        if kind == "IS_UNIT_ALIVE":
            return self.require(self.ev(a[0]), "unit").alive
        if kind == "IS_ENEMY":
            left, right = [self.require(self.ev(v), "unit") for v in a]
            return left.team != right.team
        if kind in {"FLOAT_COMPARE", "BOOL_COMPARE", "UNIT_COMPARE", "MODIFIER_COMPARE", "MODIFIER_CLASS_COMPARE", "ABILITY_TYPE_COMPARE", "PLAYER_COMPARE"}:
            left, op, right = [self.ev(v) for v in a]
            return {"==": lambda: left == right, "!=": lambda: left != right, ">=": lambda: left >= right,
                    "<=": lambda: left <= right, "<": lambda: left < right, ">": lambda: left > right}[op]()
        raise AssertionError("Unsupported native condition " + str(kind))

    def run(self, actions):
        for node in actions:
            if isinstance(node, int):
                child = self.doc["trigger_dict"][str(node)]
                registration = child["sub_trigger_owner_set_var_action"]
                self.assign(registration["args_list"][0], node)
                self.registered.add(node)
                continue
            if node.get("enable") is False:
                continue
            kind, a = node["action_type"], node["args_list"]
            if kind in self.OPAQUE:
                continue
            if kind in {"IF_THEN_ELSE", "STORAGE_BOX"}:
                passed = all([self.cond(c) for c in a[0]["args_list"] if c.get("enable") is not False])
                self.run(a[1 if passed else 2]["args_list"])
            elif kind == "SET_VARIABLE":
                self.assign(a[0], self.ev(a[1]))
            elif kind == "SET_ENTITY_KV":
                self.require(self.ev(a[0])).kv[self.ev(a[1])] = self.ev(a[2])
            elif kind in {"ADD_BUFF_STACK", "SET_BUFF_STACK"}:
                obj = self.require(self.ev(a[0]), "buff")
                before = obj.stack
                obj.stack = min(obj.maximum, self.ev(a[1]) + (before if kind == "ADD_BUFF_STACK" else 0))
                if self.with_layer and obj is self.current and before != obj.stack:
                    saved = self.delta
                    self.delta = obj.stack - before
                    self.dispatch(1050472449, "layer")
                    self.delta = saved
            elif kind == "ADD_MODIFIER_OWNER_ATTR":
                obj = self.require(self.ev(a[0]), "buff")
                attr, mode, value = [self.ev(v) for v in a[1:]]
                if mode != "ATTR_ALL_RATIO":
                    raise AssertionError("Unsupported attribute mode")
                values = self.owner.contributions.setdefault(obj, {})
                values[attr] = values.get(attr, 0) + value
            elif kind == "CLEAR_MODIFIER_OWNER_ATTR":
                self.owner.contributions.pop(self.require(self.ev(a[0]), "buff"), None)
            elif kind == "UNREG_TRIGGER":
                self.registered.discard(self.ev(a[0]))
            elif kind == "ADD_MODIFIER":
                self.ev(dict(sub_type=kind, args_list=a, op_arg=node["op_arg"], op_arg_enable=node["op_arg_enable"]))
            elif kind == "REMOVE_BUFF_INS":
                self.require(self.ev(a[0]), "buff").valid = False
            elif kind == "RUN_ONCE_TIMER_NO_SAVE":
                self.timers.append((self.now + self.ev(a[0]), a[1]["args_list"], self.local, self.selected))
            elif kind == "PICK_PROJECTILE_DO_ACTION":
                group = self.ev(a[0])
                require_unique = len({id(p) for p in group}) == len(group)
                if not require_unique:
                    raise AssertionError("Native projectile groups must not repeat members")
                previous = self.selected
                try:
                    for projectile in list(group):
                        self.selected = self.require(projectile, "projectile")
                        self.run(a[1]["args_list"])
                except BreakLoop:
                    pass
                finally:
                    self.selected = previous
            elif kind == "APPLY_DAMAGE":
                self.require(self.ev(a[0]), "unit")
                self.require(self.ev(a[1]), "ability")
                self.hits.append((self.require(self.ev(a[2]), "unit"), self.ev(a[4])))
            elif kind == "CREATE_SFX_ON_POINT_NEW":
                self.visuals.append(self.ev(a[1]))
            elif kind == "CREATE_ROUND_MOVER":
                self.orbits.append((self.require(self.ev(a[0]), "projectile"), self.require(self.ev(a[1]), "unit")))
            elif kind == "UNIT_RELEASE_COMMAND":
                command = a[1]
                if command["op_arg_enable"][2] is not True:
                    raise AssertionError("Missing enabled unit-target option")
                self.commands.append(self.ev(command["op_arg"][2]))
            elif kind == "FOR_INT_DO_ACTION_NEW":
                start, end = self.ev(a[1]), self.ev(a[2])
                for row in range(start, end + 1):
                    self.assign(a[0], row)
                    self.run(a[3]["args_list"])
            elif kind == "SET_TABLE_VALUE_ND":
                table, row, column, value = [self.ev(v) for v in a]
                table.setdefault(row, {})[column] = value
            elif kind == "BREAK_LOOP":
                raise BreakLoop()
            else:
                raise AssertionError("Unsupported native action " + str(kind))

    def dispatch(self, tid, context):
        t = self.doc["trigger_dict"][str(tid)]
        if t.get("p_trigger_id") and tid not in self.registered:
            raise AssertionError("Unregistered dynamic trigger")
        old_context, old_local = self.context, self.local
        self.context = context
        self.local = {name: value for values in t["var_data"][0].values() for name, value in values.items()}
        try:
            if all([self.cond(c) for c in t["condition"] if c.get("enable") is not False]):
                self.run(t["action"])
        finally:
            self.context, self.local = old_context, old_local

    def advance(self, until=100):
        while any(due <= until for due, *_ in self.timers):
            index = min((j for j, x in enumerate(self.timers) if x[0] <= until), key=lambda j: self.timers[j][0])
            self.now, actions, local, selected = self.timers.pop(index)
            previous = self.context, self.local, self.selected
            self.context, self.local, self.selected = "delay", local, selected
            try:
                self.run(actions)
            finally:
                self.context, self.local, self.selected = previous
        self.now = until

    def timer_body(self):
        timer = next(x for x in fix.walk(self.doc["trigger_dict"]["1959489540"]["action"]) if x.get("action_type") == "RUN_LOOP_TIMER")
        self.context = "timer"
        self.local = {name: value for values in self.doc["trigger_dict"]["1959489540"]["var_data"][0].values() for name, value in values.items()}
        self.run(timer["args_list"][3]["args_list"])


class P2StateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.paths = (*fix.FILES, fix.SUPPORT, fix.SWORD_CORE, fix.GLOBALS)
        cls.raw = {p: (ROOT / p).read_bytes() for p in cls.paths}
        cls.old = {p: json.loads(raw) for p, raw in cls.raw.items()}
        cls.new, cls.reports = fix.build(ROOT)
        errors = [r for r in cls.reports if r.get("severity") == "error"]
        if errors:
            raise AssertionError(errors)

    def vm(self, path, fixed=True, **kwargs):
        return VM(copy.deepcopy((self.new if fixed else self.old)[path]), **kwargs)

    def mach(self, fixed=True):
        core = Entity("buff", resource=134265433, kv={OLD_FULL: False})
        vm = self.vm(fix.MACH, fixed, current=core)
        vm.owner.modifiers.append(core)
        vm.with_layer = True
        vm.dispatch(1485688834, "gain")
        return vm

    def test_old_death_burst_then_two_second_gate(self):
        old = self.mach(False)
        old.dispatch(2133540868, "death")
        old.dispatch(2133540868, "death")
        self.assertEqual(old.current.stack, 3)
        new = self.mach()
        new.dispatch(2133540868, "death")
        new.advance(1.999)
        new.dispatch(2133540868, "death")
        self.assertEqual(new.current.stack, 2)
        new.advance(2)
        new.dispatch(2133540868, "death")
        self.assertEqual(new.current.stack, 3)

    def test_old_full_speed_accumulates_then_delta_and_loss(self):
        for fixed, expected in ((False, 20), (True, 10)):
            vm = self.mach(fixed)
            vm.current.stack = 3
            vm.dispatch(2133540868, "death")
            self.assertEqual(vm.owner.contributions[vm.current]["attack_speed"], 10)
            vm.delta, vm.current.stack = -2, 2
            vm.dispatch(1050472449, "layer")
            self.assertEqual(vm.owner.contributions[vm.current]["attack_speed"], 0 if fixed else 10)
            vm.advance(2)
            vm.dispatch(2133540868, "death")
            vm.advance(4)
            vm.dispatch(2133540868, "death")
            self.assertEqual(vm.owner.contributions[vm.current]["attack_speed"], expected)
            other = Entity("buff")
            vm.owner.contributions[other] = {"attack_speed": 7}
            vm.dispatch(594665475, "loss")
            self.assertEqual(vm.owner.contributions, {other: {"attack_speed": 7}})

    def test_stale_death_timer_cannot_unlock_new_core(self):
        vm = self.mach()
        vm.dispatch(2133540868, "death")
        vm.dispatch(594665475, "loss")
        vm.current.valid = False
        replacement = Entity("buff", resource=134265433, kv={fix.READY: False})
        vm.owner.modifiers.append(replacement)
        vm.advance(2)
        self.assertFalse(replacement.kv[fix.READY])

    def zhang(self, fixed=True):
        core = Entity("buff", resource=134259689, kv={fix.MARK: None})
        vm = self.vm(fix.ZHANG_CORE, fixed, current=core)
        vm.owner.modifiers.append(core)
        vm.registered.add(1418035204)
        vm.event_skill.source = vm.owner
        return vm

    def test_old_first_cast_double_then_single_and_eight_seconds(self):
        for fixed in (False, True):
            vm = self.zhang(fixed)
            target = Entity(team=2, tags={fix.CAPTAIN})
            vm.event_skill.target = target
            vm.dispatch(1418035204, "release")
            self.assertEqual(vm.current.stack, 2 if fixed else 3)
            self.assertEqual(len(vm.created), 1 if fixed else 2)
            self.assertEqual(vm.created[0][2], 8 if fixed else 300)
            if fixed:
                self.assertIs(vm.current.kv[fix.OWN_MARK], vm.created[0][1])
                vm.dispatch(1418035204, "release")
                self.assertEqual(vm.current.stack, 3)
                self.assertEqual(vm.created[-1][1].stack, 2)
                vm.event_skill.target = Entity(team=2)
                vm.dispatch(1418035204, "release")
                self.assertEqual(vm.current.stack, 2)

    def test_missing_release_ability_and_invalid_target_do_not_dereference(self):
        vm = self.zhang()
        vm.event_skill = None
        vm.dispatch(1418035204, "release")
        self.assertEqual(vm.created, [])
        vm.event_skill = vm.skill
        for target in (None, Entity(valid=False), Entity(team=1), Entity(team=2, alive=False)):
            vm.event_skill.target = target
            vm.dispatch(1418035204, "release")
        self.assertEqual(vm.created, [])

    def test_fear_old_null_then_correct_target_and_per_target_wave(self):
        source = self.zhang()
        passive = self.vm(fix.DANHAN, owner=source.owner)
        passive.registered.add(1051000836)
        target = Entity(team=2, tags={fix.CAPTAIN})
        mark = Entity("buff", resource=134259870, stack=3, maximum=3)
        target.modifiers.append(mark)
        source.current.kv.update({fix.MARK: target, fix.OWN_MARK: mark})
        old = self.vm(fix.DANHAN, False, owner=source.owner)
        old.registered.add(1051000836)
        old.event_modifier = mark
        with self.assertRaisesRegex(AssertionError, "Invalid native operand"):
            old.dispatch(1051000836, "global_layer")
        passive.event_modifier = mark
        passive.dispatch(1051000836, "global_layer")
        passive.dispatch(1051000836, "global_layer")
        self.assertEqual(len(passive.created), 1)
        self.assertIs(passive.created[0][0], target)
        self.assertIsNot(passive.created[0][0], source.owner)
        target2 = Entity(team=2, tags={fix.CAPTAIN})
        mark2 = Entity("buff", resource=134259870, stack=3, maximum=3)
        target2.modifiers.append(mark2)
        source.current.kv.update({fix.MARK: target2, fix.OWN_MARK: mark2})
        passive.event_modifier = mark2
        passive.dispatch(1051000836, "global_layer")
        self.assertEqual(len(passive.created), 2)
        passive.global_values[fix.WAVE] = 2
        passive.dispatch(1051000836, "global_layer")
        self.assertEqual(len(passive.created), 3)

    def test_fear_ownership_cache_blocks_foreign_source_and_max_order(self):
        core_vm = self.zhang()
        passive = self.vm(fix.DANHAN, owner=core_vm.owner)
        passive.registered.add(1051000836)
        target = Entity(team=2, tags={fix.CAPTAIN})
        core_vm.event_skill.target = target
        def notify(mark):
            passive.event_modifier = mark
            passive.dispatch(1051000836, "global_layer")
        core_vm.on_mark = notify
        for expected in (0, 0, 1, 1):
            core_vm.dispatch(1418035204, "release")
            self.assertEqual(len(passive.created), expected)
        foreign = Entity("buff", resource=134259870, stack=3, maximum=3, source=Entity())
        target.modifiers.append(foreign)
        passive.event_modifier = foreign
        passive.global_values[fix.WAVE] = 2
        passive.dispatch(1051000836, "global_layer")
        self.assertEqual(len(passive.created), 1)

    def swords(self, path, targets, fixed=True):
        vm = self.vm(path, fixed)
        vm.skill.kv[COEFFICIENT] = 1.25 if path == fix.RECALL else 1.1
        vm.event_skill.source = vm.owner
        vm.registered.add(1756393476)
        group = [Entity("projectile", kv={fix.TARGET: target}) for target in targets]
        core = Entity("buff", resource=134248740, kv={fix.SWORDS: group})
        vm.owner.modifiers.append(core)
        return vm, core, group

    def test_old_auto_core_null_error_then_safe_unlocked_deleted_core(self):
        old = self.vm(fix.RECALL, False)
        with self.assertRaisesRegex(AssertionError, "Invalid native operand"):
            old.timer_body()
        vm = self.vm(fix.RECALL)
        vm.timer_body()
        self.assertEqual(vm.commands, [])
        target = Entity(team=2, tags={fix.CAPTAIN})
        vm, core, _ = self.swords(fix.RECALL, [target] * 3)
        core.valid = False
        for _ in range(6):
            vm.timer_body()
        self.assertEqual(vm.commands, [])

    def test_recall_requires_same_alive_enemy_and_no_stale_auto_target(self):
        first, second = Entity(team=2, tags={fix.CAPTAIN}), Entity(team=2, tags={fix.CAPTAIN})
        for targets, eligible in (([first, first, second], False), ([first] * 3, True),
                                  ([first, None, first], False), ([first] * 2, False),
                                  ([first] * 4, False), ([Entity(team=1)] * 3, False),
                                  ([Entity(team=2, alive=False)] * 3, False)):
            vm, core, _ = self.swords(fix.RECALL, targets)
            vm.timer_body()
            self.assertEqual(len(vm.commands), 1 if eligible else 0)
            core.valid = False
            vm.timer_body()
            self.assertEqual(len(vm.commands), 1 if eligible else 0)

    def test_old_recall_leaves_state_then_candidate_375_and_reset(self):
        target = Entity(team=2, tags={fix.CAPTAIN})
        for fixed in (False, True):
            vm, _, group = self.swords(fix.RECALL, [target] * 3, fixed)
            vm.actor[fix.TARGET] = target
            vm.dispatch(893440004, "spell")
            vm.advance(1)
            self.assertEqual([amount for _, amount in vm.hits], [125, 125, 125])
            self.assertEqual(sum(amount for _, amount in vm.hits), 375)
            self.assertEqual([p.kv[fix.TARGET] for p in group], [vm.owner] * 3 if fixed else [target] * 3)
            self.assertEqual(len(vm.orbits), 3)
        vm, _, _ = self.swords(fix.RECALL, [target, target, Entity(team=2, tags={fix.CAPTAIN})])
        vm.dispatch(893440004, "spell")
        vm.advance(1)
        self.assertEqual(vm.hits, [])

    def test_delayed_damage_uses_snapshots_and_rechecks_lifetime(self):
        a, b = Entity(team=2), Entity(team=2)
        vm, core, group = self.swords(fix.SPLIT, [a, a, b])
        vm.dispatch(1756393476, "custom")
        for sword in group:
            sword.valid = False
        core.valid = False
        vm.actor[fix.TARGET] = Entity(team=2)
        vm.advance(1)
        self.assertEqual([target for target, _ in vm.hits], [a, a, b])
        for _, amount in vm.hits:
            self.assertAlmostEqual(amount, 110)
        vm, _, _ = self.swords(fix.SPLIT, [a, a, b])
        vm.dispatch(1756393476, "custom")
        a.alive = False
        b.valid = False
        vm.advance(1)
        self.assertEqual(vm.hits, [])

    def test_old_split_wrong_target_then_distinct_once_per_wave(self):
        a, b = Entity(team=2), Entity(team=2)
        old, _, _ = self.swords(fix.SPLIT, [a] * 3, False)
        old.dispatch(1756393476, "custom")
        with self.assertRaisesRegex(AssertionError, "Invalid native operand"):
            old.advance(1)
        for targets, hits in (([a] * 3, 0), ([a, a, b], 3), ([a, b], 0), ([a, a, b, b], 0),
                               ([a, b, None], 0), ([a, b, Entity(team=1)], 0)):
            vm, _, group = self.swords(fix.SPLIT, targets)
            vm.dispatch(1756393476, "custom")
            vm.dispatch(1756393476, "custom")
            vm.advance(1)
            self.assertEqual(len(vm.hits), hits)
            if hits:
                self.assertEqual([t for t, _ in vm.hits], targets)
                self.assertEqual([p.kv[fix.TARGET] for p in group], targets)  # No recall for this passive.
                vm.global_values[fix.WAVE] = 2
                vm.dispatch(1756393476, "custom")
                vm.advance(2)
                self.assertEqual(len(vm.hits), 6)

    def test_custom_event_normal_hit_needs_unit_not_damage_ability(self):
        a, b = Entity(team=2), Entity(team=2)
        vm, _, _ = self.swords(fix.SPLIT, [a, a, b])
        vm.event_skill = None
        vm.dispatch(1756393476, "custom")
        vm.advance(1)
        self.assertEqual([target for target, _ in vm.hits], [a, a, b])
        for event_unit in (None, Entity(valid=False), Entity()):
            vm, _, _ = self.swords(fix.SPLIT, [a, a, b])
            vm.event_unit = event_unit
            vm.dispatch(1756393476, "custom")
            self.assertEqual(vm.timers, [])

    def test_model_unknowns_and_unavailable_events_fail(self):
        vm = self.vm(fix.SPLIT)
        self.assertEqual(vm.timers, [])
        with self.assertRaisesRegex(AssertionError, "Unavailable layer delta"):
            vm.ev(fix.e(100002, "GET_MODIFIER_LAYER_CHANGE_VALUE"))
        with self.assertRaisesRegex(AssertionError, "Unsupported native expression"):
            vm.ev(fix.e(100076, "INVENTED_ENGINE_API"))

    def test_captain_union_accepts_player_mirror_and_npc_in_all_three_gates(self):
        for tag in (fix.COMPANION, fix.CAPTAIN):
            with self.subTest(tag=tag):
                target = Entity(team=2, tags={tag})
                vm, _, _ = self.swords(fix.RECALL, [target] * 3)
                vm.timer_body()
                self.assertEqual(vm.commands, [target])
                vm.dispatch(893440004, "spell")
                vm.advance(1)
                self.assertEqual([t for t, _ in vm.hits], [target] * 3)
                source = self.zhang()
                passive = self.vm(fix.DANHAN, owner=source.owner)
                passive.registered.add(1051000836)
                mark = Entity("buff", resource=134259870, stack=3, maximum=3)
                target.modifiers.append(mark)
                source.current.kv.update({fix.MARK: target, fix.OWN_MARK: mark})
                passive.event_modifier = mark
                passive.dispatch(1051000836, "global_layer")
                self.assertEqual([t for t, _, _ in passive.created], [target])
        target = Entity(team=2, tags={"JY\u5355\u4f4d"})
        vm, _, _ = self.swords(fix.RECALL, [target] * 3)
        vm.timer_body()
        vm.dispatch(893440004, "spell")
        vm.advance(1)
        self.assertEqual(vm.commands, [])
        self.assertEqual(vm.hits, [])

    def test_delays_do_not_cross_wave_or_combat_end(self):
        for path in (fix.RECALL, fix.SPLIT):
            for transition in ("wave", "phase"):
                with self.subTest(path=path, transition=transition):
                    a = Entity(team=2, tags={fix.COMPANION})
                    b = Entity(team=2)
                    vm, _, _ = self.swords(path, [a, a, a] if path == fix.RECALL else [a, a, b])
                    vm.dispatch(893440004 if path == fix.RECALL else 1756393476,
                                "spell" if path == fix.RECALL else "custom")
                    self.assertEqual(len(vm.timers), 3)
                    vm.global_values[fix.WAVE if transition == "wave" else fix.PHASE] = 2 if transition == "wave" else 3
                    vm.advance(1)
                    self.assertEqual(vm.hits, [])

    def test_missing_group_and_deleted_caster_or_ability_are_safe(self):
        a = Entity(team=2, tags={fix.COMPANION})
        b = Entity(team=2)
        for path in (fix.RECALL, fix.SPLIT):
            vm, core, _ = self.swords(path, [a, a, a] if path == fix.RECALL else [a, a, b])
            core.kv.clear()
            if path == fix.RECALL:
                vm.timer_body()
            vm.dispatch(893440004 if path == fix.RECALL else 1756393476,
                        "spell" if path == fix.RECALL else "custom")
            self.assertEqual(vm.timers, [])
            for removed in ("owner", "ability"):
                with self.subTest(path=path, removed=removed):
                    vm, _, _ = self.swords(path, [a, a, a] if path == fix.RECALL else [a, a, b])
                    vm.dispatch(893440004 if path == fix.RECALL else 1756393476,
                                "spell" if path == fix.RECALL else "custom")
                    (vm.owner if removed == "owner" else vm.skill).valid = False
                    vm.advance(1)
                    self.assertEqual(vm.hits, [])

    def test_full_speed_percent_points_and_repeated_refresh_are_independent(self):
        vm = self.mach()
        vm.delta, vm.current.stack = 3, 4
        vm.dispatch(1050472449, "layer")
        for _ in range(4):
            vm.delta = 0
            vm.dispatch(1050472449, "layer")
        contribution = vm.owner.contributions[vm.current]
        self.assertEqual(contribution, {"attack_phy": 12, "attack_speed": 10})
        self.assertAlmostEqual(100 * (1 + contribution["attack_speed"] / 100), 110)

    def memory_build(self, docs):
        reads = []
        def read(path):
            relative = path.relative_to(Path("memory")).as_posix()
            reads.append(relative)
            return json.dumps(docs[relative]).encode("utf8")
        with patch.object(Path, "read_bytes", read), patch.object(Path, "write_text", side_effect=AssertionError("write")), \
                patch.object(Path, "write_bytes", side_effect=AssertionError("write")):
            result = fix.build(Path("memory"))
        self.assertEqual(reads, list(self.paths))
        return result

    def test_scope_latest_root_unknown_metadata_and_p1_support_untouched(self):
        docs = copy.deepcopy(self.old)
        large = 2**83 + 11
        for path in fix.FILES:
            docs[path]["unknown_user_field"] = {"precise_id": large}
        docs[fix.SUPPORT]["P1_live_marker"] = large
        untouched = copy.deepcopy(docs)
        result, reports = self.memory_build(docs)
        self.assertEqual(docs, untouched)
        self.assertEqual(set(result), set(fix.FILES))
        self.assertNotIn(fix.SUPPORT, result)
        for path in fix.FILES:
            self.assertEqual(result[path]["unknown_user_field"]["precise_id"], large)
        self.assertTrue(any(r.get("code") == "p1_preserved_read_only" for r in reports))
        self.assertTrue(any(r.get("code") == "elite_mapping_review" for r in reports))
        for path in self.paths:
            self.assertEqual((ROOT / path).read_bytes(), self.raw[path])

    def test_deterministic_build_and_phase_notifications_do_not_reset_once_flag(self):
        self.assertEqual(fix.build(ROOT)[0], self.new)
        a, b = Entity(team=2), Entity(team=2)
        vm, _, _ = self.swords(fix.SPLIT, [a, a, b])
        vm.dispatch(1756393476, "custom")
        vm.advance(1)
        vm.global_values[fix.PHASE] = 1
        vm.dispatch(1756393476, "custom")
        vm.global_values[fix.PHASE] = 2
        vm.dispatch(1756393476, "custom")
        vm.advance(2)
        self.assertEqual(len(vm.hits), 3)
        self.assertEqual(vm.owner.kv[fix.PREFIX + "split_wave"], 1)

    def test_all_old_ids_and_metadata_retained_disabled_is_not_runtime(self):
        for path in fix.FILES:
            before = Counter(n["element_id"] for n in fix.walk(self.old[path]) if "element_id" in n)
            after = Counter(n["element_id"] for n in fix.walk(self.new[path]) if "element_id" in n)
            self.assertFalse(before - after, path)
            self.assertEqual(self.new[path]["trigger_group_info"], self.old[path]["trigger_group_info"])
            for tid, t in self.old[path]["trigger_dict"].items():
                for key in ("event", "enabled", "p_trigger_id", "sub_trigger_owner_set_var_action"):
                    self.assertEqual(self.new[path]["trigger_dict"][tid].get(key), t.get(key))
        for path in (fix.RECALL, fix.SPLIT):
            archives = [n for n in fix.walk(self.new[path]) if n.get("action_type") == "STORAGE_BOX" and n.get("enable") is False]
            self.assertGreaterEqual(len(archives), 1)
        durations = [n["op_arg"][2]["args_list"][0] for n in fix.walk(self.new[fix.ZHANG_CORE]) if n.get("sub_type") == "ADD_MODIFIER"]
        self.assertEqual(durations, [8, 8, 8])
        info = next(r for r in self.reports if r.get("path") == fix.SUPPORT)
        self.assertEqual(info["source_sha256"], hashlib.sha256(self.raw[fix.SUPPORT]).hexdigest())

    def test_drift_blocks_dependent_candidate_and_missing_global_is_reported(self):
        docs = copy.deepcopy(self.old)
        docs[fix.ZHANG_CORE]["trigger_dict"]["1418035204"]["action"].append({"action_type": "USER_CUSTOM", "enable": True})
        result, reports = self.memory_build(docs)
        self.assertNotIn(fix.ZHANG_CORE, result)
        self.assertNotIn(fix.DANHAN, result)
        self.assertTrue(any(r.get("path") == fix.DANHAN and r.get("code") == "review_required" for r in reports))
        docs = copy.deepcopy(self.old)
        del docs[fix.GLOBALS]["variable_dict"]["INTEGER"][fix.WAVE]
        result, reports = self.memory_build(docs)
        for path in (fix.DANHAN, fix.RECALL, fix.SPLIT):
            self.assertNotIn(path, result)
        self.assertTrue(any(r.get("severity") == "error" for r in reports))


if __name__ == "__main__":
    unittest.main()

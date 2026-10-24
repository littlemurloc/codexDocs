"""Native-AST regressions plus a deliberately limited, strict sequence model.

The fixtures contain the reviewed native nodes, not the builder's constructors.
The model checks injected removal/replacement ordering and arithmetic only. It
does NOT implement Y3 scheduling, capture, death ordering, SFX, or registration
semantics. Events and callback context must be supplied explicitly. Unknown
expressions fail. All conditions in a stage are evaluated without short-circuit.
No fixtures, candidates, caches, or live map files are written by these tests.
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
from tools import y3_hero_repair_p1_lifecycle as repair


def x(kind, subtype=1, *args):
    return {"arg_type": kind, "args_list": list(args), "sub_type": subtype}


def a(name, eid, *args, enabled=True):
    return {"action_type": name, "args_list": list(args), "bp": False,
            "element_id": eid, "enable": enabled}


def ref(kind, name, subtype, scope="actor"):
    types = {"MODIFIER_ENTITY": 100076, "UNIT_ENTITY": 100006,
             "BOOLEAN": 100001, "INTEGER": 100002, "NEW_TIMER": 100181}
    return x(types[kind], subtype, {"__tuple__": True, "items": [kind, name, scope]})


def last(owner, key):
    return x(100076, "GET_LAST_MODIFIER_INSTANCE", owner, x(100046, 1, key))


def native_fixtures():
    """Small native slices; unrelated actions/declarations intentionally omitted."""
    owner, cm = x(100006, "MODIFIER_OWNER"), x(100076, "CUR_MODIFIER")
    ab_owner = x(100006, "ABILITY_OWNER")
    target = ref("UNIT_ENTITY", "\u76ee\u6807\u5355\u4f4d", 11)
    source = x(100006, "MODIFIER_RELEASER")
    cd = x(100003, 1, "\u5185\u7f6eCD")

    def t(key, event, actions, parent=None):
        out = {"action": actions, "call_enabled": True, "condition": [],
               "enabled": parent is None, "event": [{"args_list": [], "element_id": key * 1000000 + 2,
               "enable": True, "event_type": event}], "group_id": 0,
               "p_trigger_id": parent, "trigger_id": key, "trigger_name": "native",
               "valid": True, "var_data": [{}, {}, []]}
        if parent is not None:
            out["sub_trigger_owner_set_var_action"] = a("SET_VARIABLE", key * 1000000 + 1,
                x(100178, "VARIABLE", ["DYNAMIC_TRIGGER_INSTANCE", str(key), "actor"]),
                x(100178, "REG_MODIFIER_TRIGGER", x(100069, 1, key)))
        return out

    def doc(triggers):
        return {"local_variable": {str(v["trigger_id"]): {"variable_dict": {},
                    "variable_length_dict": {}} for v in triggers},
                "trigger_dict": {str(v["trigger_id"]): v for v in triggers},
                "trigger_group_info": [], "trigger_version": "1.2",
                "variable_dict": {}, "variable_length_dict": {}, "variable_group_info": [],
                "unknown_user_field": {"integer": 900719925474099312345}}

    hit = [a("APPLY_DAMAGE", 893440004975596, ab_owner, x(100014, "CUR_ABILITY"), target,
             x(100064, 1, 0), x(100000, 1, 300.0), x(100001, 1, True)),
           a("REMOVE_BUFF_INS", 893440004976354, last(target, 134274015)),
           a("SET_BUFF_STACK", 893440004976362, last(ab_owner, 134277456), x(100002, 1, 1))]
    mover = a("CREATE_CHASING_MOVER", 893440004975299, ab_owner, target, x(100000, 1, 100.0),
              x(100000, 1, 2000.0), x(100000, 1, 1000.0), x(100022, 1, *hit),
              x(100022, 1), x(100022, 1), x(100022, 1), x(100022, 1), x(100022, 1))
    mover["local_var"] = {"__tuple__": True, "items": [{}, {}]}
    mover["op_arg"] = [None] * 17 + [x(100014, "CUR_ABILITY")]
    mover["op_arg_enable"] = [False] * 17 + [True]
    ability = doc([t(893440004, "ABILITY_SP_END", [mover])])

    timer = a("RUN_ONCE_TIMER_NO_SAVE", 1418035204974513, x(100000, 1, 8.0), x(100022, 1,
        a("SET_BUFF_STACK", 1418035204974518, cm, x(100002, 1, 1), enabled=False),
        a("SET_BUFF_STACK", 1473785861000046, last(owner, 134277456), x(100002, 1, 1)),
        a("SET_ENTITY_KV", 1418035204974592, cm, cd, x(100001, 1, False))))
    core = doc([t(1485688834, "OBTAIN_MODIFIER", [1418035204, 1473785861]),
                t(594665475, "LOSS_MODIFIER", []),
                t(1418035204, "SPECIAL_UNIT_EVENT", [timer], 1485688834),
                t(1473785861, "GENERIC_UNIT_EVENT", [], 1485688834)])
    pursuit = doc([t(1485688834, "OBTAIN_MODIFIER", []), t(594665475, "LOSS_MODIFIER", [
        a("ADD_BUFF_STACK", 1418035204974461, last(source, 134282266), x(100002, 1, 1)),
        a("SET_ENTITY_KV", 1418035204974592, last(source, 134282266), cd, x(100001, 1, False)),
        a("DELETE_SFX_ENTITY", 594665475000062, x(100148, 4, ["SFX_ENTITY", "native_sfx", "actor"]))])])
    optional = doc([t(1959489540, "ABILITY_OBTAIN", [1340796934]),
                   t(1340796934, "SPECIAL_UNIT_EVENT", [
                       a("RUN_ONCE_TIMER_NO_SAVE", 1340796934000035, x(100000, 1, 3.0), x(100022, 1,
                         a("SET_ENTITY_KV", 1340796934000042, ab_owner, cd, x(100001, 1, False))))],
                     1959489540)])
    return dict(zip((*repair.FILES, repair.OPTIONAL), (ability, core, pursuit, optional)))


def build_memory(documents):
    def read(path, *args, **kwargs):
        key = path.parent.name + "/" + path.name
        if key not in documents:
            raise FileNotFoundError(key)
        return json.dumps(documents[key], ensure_ascii=True)
    with patch.object(Path, "read_text", read), patch.object(Path, "write_text") as write:
        result = repair.build(Path("memory/map3"))
        write.assert_not_called()
        return result


def nodes(value):
    if isinstance(value, dict):
        yield value
        for v in value.values():
            yield from nodes(v)
    elif isinstance(value, list):
        for v in value:
            yield from nodes(v)


def find(value, eid, action):
    return next(n for n in nodes(value) if n.get("element_id") == eid and n.get("action_type") == action)


class LifetimeFault(RuntimeError):
    pass


class Entity:
    def __init__(self, *, owner=None, source=None, stack=1):
        self.exists, self.owner, self.source, self.stack = True, owner, source, stack
        self.buffs, self.kv = {}, {repair.CD: True}


class SequenceModel:
    """Injected synchronous reentry; timer execution is explicit, never clocked."""
    def __init__(self, current=None, source=None, ability_owner=None, target=None):
        self.context = {"CUR_MODIFIER": current, "MODIFIER_RELEASER": source,
                        "ABILITY_OWNER": ability_owner}
        self.actor, self.local = {}, {}
        self.global_values = {repair.PHASE: 2, repair.WAVE: 7}
        self.actor["\u76ee\u6807\u5355\u4f4d"] = target
        self.on_damage = self.on_stack = None
        self.timers, self.sfx_deleted, self.damage = [], 0, []

    def checked(self, value):
        if not isinstance(value, Entity) or not value.exists:
            raise LifetimeFault("dereferenced invalid instance")
        return value

    def variable(self, expression):
        raw = expression["args_list"][0]
        parts = raw["items"] if isinstance(raw, dict) else raw
        if len(parts) == 2:
            return self.global_values, parts[1]
        return (self.local if parts[2] == "local" else self.actor), parts[1]

    def value(self, n):
        sub, args = n["sub_type"], n["args_list"]
        if sub in (1, 2, 6, 11, "VARIABLE") and args and (
                isinstance(args[0], dict) and args[0].get("__tuple__") or
                isinstance(args[0], list)):
            store, key = self.variable(n)
            return store.get(key, 0)
        if sub == 1:
            if len(args) != 1 or isinstance(args[0], (dict, list)):
                raise NotImplementedError("not a scalar literal")
            return args[0]
        if sub in self.context:
            if self.context[sub] is None:
                raise LifetimeFault("event parameter unavailable: " + sub)
            return self.context[sub]
        if sub == "MODIFIER_OWNER":
            return self.checked(self.context["CUR_MODIFIER"]).owner
        if sub == "GET_LAST_MODIFIER_INSTANCE":
            return self.checked(self.value(args[0])).buffs.get(self.value(args[1]))
        if sub == "GET_BUFF_SOURCE":
            return self.checked(self.value(args[0])).source
        raise NotImplementedError("unsupported expression: " + str(sub))

    def condition(self, n):
        if n.get("enable") is False:
            raise AssertionError("disabled conditions must be filtered before evaluation")
        name, args = n["condition_type"], n["args_list"]
        if name == "TYPE_IS_EXIST":
            value = self.value(args[0])
            return isinstance(value, Entity) and value.exists
        if name in ("UNIT_COMPARE", "MODIFIER_COMPARE", "BOOL_COMPARE", "FLOAT_COMPARE"):
            left, op, right = [self.value(v) for v in args]
            if op != "==":
                raise NotImplementedError(op)
            return left is right if isinstance(left, Entity) else left == right
        raise NotImplementedError(name)

    def run(self, actions):
        for n in actions:
            if isinstance(n, int):
                continue  # Registration is checked structurally, not emulated.
            if n.get("enable") is False:
                continue
            name, args = n["action_type"], n["args_list"]
            if name == "IF_THEN_ELSE":
                checks = [self.condition(c) for c in args[0]["args_list"] if c.get("enable") is not False]
                self.run(args[1 if all(checks) else 2]["args_list"])
            elif name == "SET_VARIABLE":
                store, key = self.variable(args[0])
                store[key] = self.value(args[1])
            elif name in ("SET_BUFF_STACK", "ADD_BUFF_STACK"):
                obj, number = self.checked(self.value(args[0])), self.value(args[1])
                obj.stack = number if name == "SET_BUFF_STACK" else obj.stack + number
                if self.on_stack:
                    self.on_stack()
            elif name == "SET_ENTITY_KV":
                self.checked(self.value(args[0])).kv[self.value(args[1])] = self.value(args[2])
            elif name == "REMOVE_BUFF_INS":
                self.checked(self.value(args[0])).exists = False
            elif name == "APPLY_DAMAGE":
                self.damage.append(self.value(args[4]))
                if self.on_damage:
                    self.on_damage()
            elif name in ("RUN_ONCE_TIMER", "RUN_ONCE_TIMER_NO_SAVE"):
                start = 1 if name == "RUN_ONCE_TIMER" else 0
                timer = {"duration": self.value(args[start]), "body": args[start + 1]["args_list"],
                         "cancelled": False}
                self.timers.append(timer)
                if start:
                    store, key = self.variable(args[0])
                    store[key] = timer
            elif name == "DELETE_TIMER":
                timer = self.value(args[0])
                if isinstance(timer, dict):
                    timer["cancelled"] = True
            elif name == "DELETE_SFX_ENTITY":
                self.sfx_deleted += 1  # No visual or resource semantics emulated.
            else:
                raise NotImplementedError("unsupported action: " + name)

    def expire(self, timer, *, queued=False):
        if queued or not timer["cancelled"]:
            self.run(timer["body"])


class LifecycleTests(unittest.TestCase):
    def setUp(self):
        self.original = native_fixtures()
        self.fixed, self.issues = build_memory(self.original)
        self.assertEqual(set(self.fixed), set(repair.FILES))

    def actions(self, rel, tid, fixed=True):
        return (self.fixed if fixed else self.original)[rel]["trigger_dict"][str(tid)]["action"]

    def hit_model(self):
        owner, target = Entity(), Entity()
        core, letter = Entity(owner=owner, stack=5), Entity(owner=target, source=owner)
        owner.buffs[134277456], target.buffs[134274015] = core, letter
        return SequenceModel(ability_owner=owner, target=target), owner, target, core, letter

    def hit_body(self, fixed):
        return find((self.fixed if fixed else self.original)[repair.FILES[0]],
                    893440004975299, "CREATE_CHASING_MOVER")["args_list"][5]["args_list"]

    def test_old_lethal_hit_fault_then_guarded_hit(self):
        for fixed in (False, True):
            m, owner, target, core, letter = self.hit_model()
            def death():
                letter.exists = False
                target.buffs.clear()
            m.on_damage = death
            if fixed:
                m.run(self.hit_body(True))
                self.assertEqual(core.stack, 1)
                self.assertEqual(m.damage, [300.0])
            else:
                with self.assertRaises(LifetimeFault):
                    m.run(self.hit_body(False))

    def test_hit_rechecks_letter_source_after_damage(self):
        for fixed in (False, True):
            m, owner, target, core, letter = self.hit_model()
            m.on_damage = lambda: setattr(letter, "source", Entity())
            m.run(self.hit_body(fixed))
            self.assertEqual(letter.exists, fixed)

    def test_hit_normal_removes_own_letter_and_resets_to_one(self):
        m, owner, target, core, letter = self.hit_model()
        m.run(self.hit_body(True))
        self.assertFalse(letter.exists)
        self.assertEqual(core.stack, 1)
        self.assertEqual(m.damage, [300.0])

    def test_hit_cannot_reset_core_replaced_during_damage(self):
        m, owner, target, old, letter = self.hit_model()
        new = Entity(owner=owner, stack=9)
        m.on_damage = lambda: owner.buffs.update({134277456: new})
        m.run(self.hit_body(True))
        self.assertEqual((old.stack, new.stack), (5, 9))

    def core_model(self, fixed):
        owner = Entity()
        core = Entity(owner=owner, stack=6)
        owner.buffs[134277456] = core
        m = SequenceModel(current=core)
        m.run(self.actions(repair.FILES[1], 1485688834, fixed))
        m.run(self.actions(repair.FILES[1], 1418035204, fixed))
        return m, owner, core

    def test_old_anonymous_timer_survives_loss_then_fixed_cancel(self):
        for fixed in (False, True):
            m, owner, core = self.core_model(fixed)
            timer = m.timers[-1]
            m.run(self.actions(repair.FILES[1], 594665475, fixed))
            core.exists = False
            self.assertEqual(timer["cancelled"], fixed)
            if fixed:
                m.expire(timer, queued=True)
                self.assertEqual(core.stack, 6)
            else:
                with self.assertRaises(LifetimeFault):
                    m.expire(timer)

    def test_old_timer_hits_same_type_replacement_then_fixed_identity(self):
        for fixed in (False, True):
            m, owner, old = self.core_model(fixed)
            new = Entity(owner=owner, stack=12)
            owner.buffs[134277456] = new  # Keep old valid to test identity, not just existence.
            m.expire(m.timers[-1])
            self.assertEqual(new.stack, 12 if fixed else 1)
            if fixed:
                self.assertTrue(old.kv[repair.CD])

    def test_timer_positive_duration_reset_and_cd(self):
        m, owner, core = self.core_model(True)
        self.assertEqual(m.timers[-1]["duration"], 8.0)
        m.expire(m.timers[-1])
        self.assertEqual(core.stack, 1)
        self.assertIs(core.kv[repair.CD], False)
        self.assertIs(m.actor[repair.PREFIX + "timer_pending"], False)

    def test_timer_revalidates_after_layer_change(self):
        m, owner, core = self.core_model(True)
        m.on_stack = lambda: setattr(core, "exists", False)
        m.expire(m.timers[-1])
        self.assertTrue(core.kv[repair.CD])

    def test_death_cancels_old_window_before_new_window(self):
        m, owner, core = self.core_model(True)
        first = m.timers[-1]
        m.run(self.actions(repair.FILES[1], 1473785861))
        self.assertTrue(first["cancelled"])
        core.stack = 8
        m.run(self.actions(repair.FILES[1], 1418035204))
        self.assertFalse(m.timers[-1]["cancelled"])
        m.expire(first)
        self.assertEqual(core.stack, 8)
        m.expire(m.timers[-1])
        self.assertEqual(core.stack, 1)

    def pursuit_model(self, fixed):
        source = Entity()
        core = Entity(owner=source, stack=4)
        mark = Entity(owner=Entity(), source=source)
        source.buffs[134282266] = core
        m = SequenceModel(current=mark, source=source)
        m.run(self.actions(repair.FILES[2], 1485688834, fixed))
        return m, source, core

    def test_pursuit_old_invalid_source_fault_then_fixed_skip_and_cleanup(self):
        for fixed in (False, True):
            m, source, core = self.pursuit_model(fixed)
            source.exists = False
            if fixed:
                m.run(self.actions(repair.FILES[2], 594665475))
                self.assertEqual((core.stack, m.sfx_deleted), (4, 1))
            else:
                with self.assertRaises(LifetimeFault):
                    m.run(self.actions(repair.FILES[2], 594665475, False))

    def test_pursuit_old_cross_wave_rewards_new_core_then_fixed_skip(self):
        for fixed in (False, True):
            m, source, old = self.pursuit_model(fixed)
            new = Entity(owner=source, stack=10)
            source.buffs[134282266] = new
            m.global_values[repair.WAVE] = 8
            m.run(self.actions(repair.FILES[2], 594665475, fixed))
            self.assertEqual(new.stack, 10 if fixed else 11)
            self.assertEqual(m.sfx_deleted, 1)

    def test_pursuit_same_wave_identity_not_resource_id(self):
        m, source, old = self.pursuit_model(True)
        new = Entity(owner=source, stack=20)
        source.buffs[134282266] = new
        m.run(self.actions(repair.FILES[2], 594665475))
        self.assertEqual((old.stack, new.stack), (4, 20))
        self.assertTrue(new.kv[repair.CD])

    def test_pursuit_cross_wave_without_core_replacement(self):
        m, source, core = self.pursuit_model(True)
        m.global_values[repair.WAVE] = 8
        m.run(self.actions(repair.FILES[2], 594665475))
        self.assertEqual(core.stack, 4)
        self.assertTrue(core.kv[repair.CD])

    def test_pursuit_noncombat_stages_skip_reward_keep_cleanup(self):
        for phase in (-2, -1, 0, 1, 3):
            with self.subTest(phase=phase):
                m, source, core = self.pursuit_model(True)
                m.global_values[repair.PHASE] = phase
                m.run(self.actions(repair.FILES[2], 594665475))
                self.assertEqual((core.stack, m.sfx_deleted), (4, 1))
                self.assertTrue(core.kv[repair.CD])

    def test_pursuit_positive_adds_exactly_one_and_clears_cd(self):
        m, source, core = self.pursuit_model(True)
        m.run(self.actions(repair.FILES[2], 594665475))
        self.assertEqual((core.stack, m.sfx_deleted), (5, 1))
        self.assertIs(core.kv[repair.CD], False)

    def test_pursuit_no_source_core_at_obtain_cannot_adopt_later_core(self):
        source, mark = Entity(), Entity()
        m = SequenceModel(current=mark, source=source)
        m.run(self.actions(repair.FILES[2], 1485688834))
        new = Entity(owner=source, stack=15)
        source.buffs[134282266] = new
        m.run(self.actions(repair.FILES[2], 594665475))
        self.assertEqual(new.stack, 15)
        self.assertEqual(m.sfx_deleted, 1)

    def test_pursuit_rechecks_after_add_reentry(self):
        for change in ("invalid", "replacement", "wave", "phase"):
            with self.subTest(change=change):
                m, source, core = self.pursuit_model(True)
                new = Entity(owner=source, stack=30)
                def reenter():
                    if change == "invalid":
                        core.exists = False
                    elif change == "replacement":
                        source.buffs[134282266] = new
                    elif change == "wave":
                        m.global_values[repair.WAVE] += 1
                    else:
                        m.global_values[repair.PHASE] = -2
                m.on_stack = reenter
                m.run(self.actions(repair.FILES[2], 594665475))
                self.assertEqual(core.stack, 5)
                self.assertTrue(core.kv[repair.CD])
                self.assertTrue(new.kv[repair.CD])
                self.assertEqual(m.sfx_deleted, 1)

    def test_native_shapes_lvalues_and_empty_capture_preserved(self):
        core = self.fixed[repair.FILES[1]]
        timer = find(core, 1418035204974513, "RUN_ONCE_TIMER")
        self.assertEqual(timer["args_list"][0]["arg_type"], 100181)
        self.assertEqual(timer["args_list"][0]["sub_type"], "VARIABLE")
        self.assertEqual(timer["args_list"][1], x(100000, 1, 8.0))
        self.assertEqual(timer["local_var"], {"__tuple__": True, "items": [{}, {}]})
        for n in nodes(self.fixed):
            if n.get("action_type") == "SET_VARIABLE":
                lhs = n["args_list"][0]
                if repair.PREFIX in json.dumps(lhs):
                    self.assertEqual((lhs["arg_type"], lhs["sub_type"]), (100030, 1))
        for rel in repair.FILES:
            doc = self.fixed[rel]
            for kind, values in doc["variable_dict"].items():
                for name in values:
                    self.assertEqual(doc["variable_length_dict"][name], 0)
                    self.assertIn({"__tuple__": True, "items": [name, name]}, doc["variable_group_info"])

    def test_guard_depth_and_independent_checks_share_stages(self):
        def depth(value, level=0):
            result = level
            if isinstance(value, dict):
                name = value.get("action_type")
                if name in ("RUN_ONCE_TIMER", "CREATE_CHASING_MOVER"):
                    # A callback is a new execution scope, not a dependent IF.
                    return max(depth(v, 0) for v in value.get("args_list", []))
                level += name == "IF_THEN_ELSE"
                result = max([level] + [depth(v, level) for v in value.values()])
            elif isinstance(value, list):
                result = max([level] + [depth(v, level) for v in value])
            return result
        self.assertLessEqual(depth(self.fixed), 3)
        first = self.actions(repair.FILES[2], 594665475)[0]
        self.assertEqual(len(first["args_list"][0]["args_list"]), 2)

    def test_preserves_ids_unknown_fields_disabled_nodes_and_input(self):
        self.assertEqual(self.original, native_fixtures())
        for rel in repair.FILES:
            before, after = self.original[rel], self.fixed[rel]
            old_ids = Counter(n["element_id"] for n in nodes(before) if "element_id" in n)
            new_ids = Counter(n["element_id"] for n in nodes(after) if "element_id" in n)
            self.assertFalse(old_ids - new_ids)
            self.assertEqual([n for n in nodes(before) if n.get("enable") is False],
                             [n for n in nodes(after) if n.get("enable") is False])
            self.assertEqual(before["unknown_user_field"], after["unknown_user_field"])
            self.assertEqual(before["trigger_group_info"], after["trigger_group_info"])

    def test_dynamic_enabled_false_is_still_registered_and_repaired(self):
        core = self.fixed[repair.FILES[1]]
        dynamic = core["trigger_dict"]["1418035204"]
        self.assertFalse(dynamic["enabled"])
        self.assertIn(1418035204, core["trigger_dict"]["1485688834"]["action"])
        self.assertTrue(any(n.get("action_type") == "RUN_ONCE_TIMER" for n in nodes(dynamic)))

    def test_disabled_anchor_reports_without_editing_document(self):
        source = deepcopy(self.original)
        find(source[repair.FILES[1]], 1418035204974513, "RUN_ONCE_TIMER_NO_SAVE")["enable"] = False
        docs, issues = build_memory(source)
        self.assertNotIn(repair.FILES[1], docs)
        self.assertTrue(any(i["file"] == repair.FILES[1] and i["status"] == "review_required" for i in issues))

    def test_disabled_mover_ancestor_cannot_be_treated_as_running_logic(self):
        source = deepcopy(self.original)
        find(source[repair.FILES[0]], 893440004975299, "CREATE_CHASING_MOVER")["enable"] = False
        docs, issues = build_memory(source)
        self.assertNotIn(repair.FILES[0], docs)
        self.assertIn("disabled", next(i["explanation"] for i in issues if i["file"] == repair.FILES[0]))

    def test_unrelated_user_actions_and_metadata_survive(self):
        source = deepcopy(self.original)
        user_action = a("USER_ACTION_OUTSIDE_REPAIR", 900719925474099312346)
        source[repair.FILES[1]]["trigger_dict"]["1418035204"]["action"].insert(0, user_action)
        timer = find(source[repair.FILES[1]], 1418035204974513, "RUN_ONCE_TIMER_NO_SAVE")
        timer["unknown_editor_metadata"] = {"custom": [1, None, "keep"]}
        docs, issues = build_memory(source)
        self.assertIn(user_action, docs[repair.FILES[1]]["trigger_dict"]["1418035204"]["action"])
        self.assertEqual(find(docs[repair.FILES[1]], 1418035204974513, "RUN_ONCE_TIMER")["unknown_editor_metadata"],
                         timer["unknown_editor_metadata"])

    def test_malformed_declaration_is_reported_per_file(self):
        source = deepcopy(self.original)
        source[repair.FILES[1]]["variable_dict"] = None
        docs, issues = build_memory(source)
        self.assertNotIn(repair.FILES[1], docs)
        self.assertEqual(set(docs), {repair.FILES[0], repair.FILES[2]})

    def test_players_and_modifier_instances_do_not_share_actor_state(self):
        first, source1, core1 = self.pursuit_model(True)
        second, source2, core2 = self.pursuit_model(True)
        core1.stack, core2.stack = 2, 11
        first.run(self.actions(repair.FILES[2], 594665475))
        self.assertEqual((core1.stack, core2.stack), (3, 11))
        self.assertTrue(core2.kv[repair.CD])
        second.run(self.actions(repair.FILES[2], 594665475))
        self.assertEqual((core1.stack, core2.stack), (3, 12))

    def test_unknown_active_timer_action_reports_instead_of_moving_user_logic(self):
        source = deepcopy(self.original)
        timer = find(source[repair.FILES[1]], 1418035204974513, "RUN_ONCE_TIMER_NO_SAVE")
        timer["args_list"][1]["args_list"].append(a("UNKNOWN_USER_ACTION", 9999))
        docs, issues = build_memory(source)
        self.assertNotIn(repair.FILES[1], docs)
        self.assertIn("additional/reordered", next(i["explanation"] for i in issues if i["file"] == repair.FILES[1]))

    def test_changed_anchor_or_reserved_name_fails_closed_per_file(self):
        for change in ("duration", "reserved", "registration"):
            with self.subTest(change=change):
                source = deepcopy(self.original)
                core = source[repair.FILES[1]]
                if change == "duration":
                    find(core, 1418035204974513, "RUN_ONCE_TIMER_NO_SAVE")["args_list"][0] = x(100000, 1, 9.0)
                elif change == "reserved":
                    core["variable_dict"]["BOOLEAN"] = {repair.PREFIX + "core_active": True}
                else:
                    core["trigger_dict"]["1485688834"]["action"].clear()
                docs, issues = build_memory(source)
                self.assertNotIn(repair.FILES[1], docs)
                self.assertEqual(set(docs), {repair.FILES[0], repair.FILES[2]})

    def test_second_application_requires_review_does_not_duplicate_patch(self):
        second, issues = build_memory({**self.fixed, repair.OPTIONAL: self.original[repair.OPTIONAL]})
        self.assertEqual(second, {})
        self.assertTrue(all(i["status"] == "review_required" for i in issues))

    def test_huang_zhong_log_anchor_remains_additional_review_only(self):
        self.assertNotIn(repair.OPTIONAL, self.fixed)
        item = next(i for i in self.issues if i["file"] == repair.OPTIONAL)
        self.assertEqual((item["case"], item["status"]), ("additional", "review_required"))
        self.assertIn("1340796934000042", item["explanation"])
        self.assertIn("CUR_ABILITY", item["explanation"])

    def test_model_rejects_unknown_or_unavailable_event_context(self):
        m = SequenceModel()
        with self.assertRaises(NotImplementedError):
            m.value(x(100076, "INVENTED_EXISTING_BUFF"))
        with self.assertRaises(LifetimeFault):
            m.value(x(100076, "CUR_MODIFIER"))

    def test_model_ignores_disabled_actions_and_conditions(self):
        m = SequenceModel()
        m.run([a("INVENTED_ACTION", 8, enabled=False)])
        condition = {"condition_type": "INVENTED_CONDITION", "args_list": [], "enable": False}
        m.run([a("IF_THEN_ELSE", 9, x(100021, 1, condition), x(100022, 1), x(100022, 1))])


class ActualMapStructureTests(unittest.TestCase):
    def test_exact_native_lvalue_and_timer_evidence(self):
        root = Path(os.environ.get("Y3_LIFECYCLE_ROOT", "D:/littl/testTempFile/ProjectMonster02/maps/map3"))
        examples = [("modifier/134255911.json", 645177345450010),
                    ("modifier/134250273.json", 546832386000192)]
        if not all((root / rel).is_file() for rel, _ in examples):
            self.skipTest("native evidence unavailable")
        for rel, eid in examples:
            source = json.loads((root / rel).read_text(encoding="utf-8-sig"))
            native = find(source, eid, "SET_VARIABLE")["args_list"][0]
            self.assertEqual((native["arg_type"], native["sub_type"]), (100030, 1))
            parts = native["args_list"][0]
            parts = parts["items"] if isinstance(parts, dict) else parts
            self.assertEqual(parts[0], "MODIFIER_ENTITY")
            generated = repair.var("MODIFIER_ENTITY", "sample", target=True)
            self.assertEqual((native["arg_type"], native["sub_type"]),
                             (generated["arg_type"], generated["sub_type"]))
        sample = json.loads((root / "modifier/134277037.json").read_text(encoding="utf-8-sig"))
        saved = find(sample, 996392961000036, "RUN_ONCE_TIMER")
        self.assertEqual([v["arg_type"] for v in saved["args_list"]], [100181, 100000, 100022])
        self.assertTrue(any(n.get("action_type") == "DELETE_TIMER" for n in nodes(sample)))
        self.assertTrue(any(n.get("condition_type") == "TYPE_IS_EXIST" and
                            n["args_list"] == [x(100076, "CUR_MODIFIER")] for n in nodes(saved)))

    def test_read_only_build_actual_map_and_preservation(self):
        root = Path(os.environ.get("Y3_LIFECYCLE_ROOT", "D:/littl/testTempFile/ProjectMonster02/maps/map3"))
        if not all((root / rel).is_file() for rel in repair.FILES):
            self.skipTest("actual map unavailable; native-slice regressions remain self-contained")
        data = {rel: (root / rel).read_bytes() for rel in (*repair.FILES, repair.OPTIONAL)}
        hashes = {rel: hashlib.sha256(raw).hexdigest() for rel, raw in data.items()}
        docs, issues = repair.build(root)
        self.assertEqual(set(docs), set(repair.FILES), issues)
        for rel, candidate in docs.items():
            source = json.loads(data[rel])
            old = Counter(n["element_id"] for n in nodes(source) if "element_id" in n)
            new = Counter(n["element_id"] for n in nodes(candidate) if "element_id" in n)
            self.assertFalse(old - new)
            self.assertTrue(all(count == 1 for eid, count in new.items() if eid not in old))
            self.assertEqual([n for n in nodes(source) if n.get("enable") is False],
                             [n for n in nodes(candidate) if n.get("enable") is False])
            self.assertEqual(source["trigger_group_info"], candidate["trigger_group_info"])
            self.assertEqual(source["trigger_version"], candidate["trigger_version"])
            self.assertEqual(set(source["trigger_dict"]), set(candidate["trigger_dict"]))
            for tid, old_trigger in source["trigger_dict"].items():
                new_trigger = candidate["trigger_dict"][tid]
                for key, value in old_trigger.items():
                    if key not in {"action", "var_data"}:
                        self.assertEqual(value, new_trigger[key], (rel, tid, key))
            for key in source:
                if key not in {"trigger_dict", "variable_dict", "variable_length_dict",
                               "variable_group_info", "local_variable"}:
                    self.assertEqual(source[key], candidate[key])
        before_hit = json.loads(data[repair.FILES[0]])
        after_hit = docs[repair.FILES[0]]
        self.assertEqual(find(before_hit, 893440004975596, "APPLY_DAMAGE"),
                         find(after_hit, 893440004975596, "APPLY_DAMAGE"))
        # Coefficients, target selection, animation, and non-hit triggers stay exact.
        self.assertEqual(before_hit["trigger_dict"]["893440004"]["action"][:-1],
                         after_hit["trigger_dict"]["893440004"]["action"][:-1])
        for tid in before_hit["trigger_dict"]:
            if tid != "893440004":
                self.assertEqual(before_hit["trigger_dict"][tid], after_hit["trigger_dict"][tid])
        self.assertEqual(hashes, {rel: hashlib.sha256((root / rel).read_bytes()).hexdigest() for rel in data})


if __name__ == "__main__":
    unittest.main()

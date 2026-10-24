"""Regression tests against native, read-only map3 ASTs.

Set Y3_P1_NUMERIC_ROOT to an unmodified pre-repair map3 snapshot to relocate the
input. No fixtures/candidates/caches are written. The small evaluator rejects
unknown operations. It projects arithmetic, synchronous instruction order and
arguments at ADD_MODIFIER invocation, NOT engine event/callback/buff semantics.
"""

from collections import Counter
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import unittest
from unittest.mock import patch

from tools import y3_hero_repair_p1_numeric as repair


ROOT = Path(os.environ.get("Y3_P1_NUMERIC_ROOT",
                          "D:/littl/testTempFile/ProjectMonster02/maps/map3"))


def nodes(value):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from nodes(child)
    elif isinstance(value, list):
        for child in value:
            yield from nodes(child)


def action(tree, kind, element_id=None):
    found = [n for n in nodes(tree) if n.get("action_type") == kind
             and (element_id is None or n.get("element_id") == element_id)]
    if len(found) != 1:
        raise AssertionError((kind, element_id, len(found)))
    return found[0]


def cast(doc):
    return doc["trigger_dict"]["893440004"]["action"]


def collision(doc):
    return action(cast(doc), "CREATE_STRAIGHT_MOVER")["args_list"][9]["args_list"]


def formula(doc, element_id):
    return action(cast(doc), "SET_VARIABLE", element_id)["args_list"][1]


class Projection:
    """Strict operand evaluator; no automatic objects, truthiness or coercion."""

    def __init__(self, stacks=None, attack=100.0, hp=None, groups=None):
        self.stacks = {} if stacks is None else dict(stacks)
        self.attack = attack
        self.hp = {} if hp is None else hp
        self.groups = {} if groups is None else groups
        self.alive = set(self.hp)
        self.tags = {}
        self.selected = None
        self.vars = {("INTEGER", "count", "local"): 0}
        self.kv = {"伤害系数": 1.15, "额外系数": 0.45, "系数": 0.05}
        self.damage = []
        self.shields = []
        self.consumptions = []
        self.stack_reads = []
        self.target = "actor-primary"
        self.hit = "collision-unit"
        self.after_damage_assignment = None
        self.after_shield = None

    @staticmethod
    def reference(raw):
        if isinstance(raw, dict):
            if raw.get("__tuple__") is not True:
                raise AssertionError("not a native tuple")
            raw = raw["items"]
        return tuple(raw)

    def expr(self, x):
        if not isinstance(x, dict):
            raise AssertionError("expression is not a native dict")
        kind, args = x["sub_type"], x["args_list"]
        if kind == 1:
            if len(args) != 1 or isinstance(args[0], (dict, list)):
                raise AssertionError("not a primitive literal")
            return args[0]
        if kind in (2, 6, "VARIABLE"):
            return self.vars[self.reference(args[0])]
        if kind == 11:
            if self.reference(args[0]) != ("UNIT_ENTITY", "目标单位", "actor"):
                raise AssertionError("unsupported unit reference")
            return self.target
        if kind in ("ARITHMETIC_OPERATION", "MATH_OPERATION"):
            left, op, right = (self.expr(v) for v in args)
            if type(left) not in (int, float) or type(right) not in (int, float):
                raise AssertionError("non-numeric arithmetic")
            if op == "+": return left + right
            if op == "-": return left - right
            if op == "*": return left * right
            if op == "/": return left / right
            raise AssertionError(op)
        if kind == "I2F":
            value = self.expr(args[0])
            if type(value) is not int:
                raise AssertionError("I2F requires integer")
            return float(value)
        if kind == "INT_PLUS_ONE": return self.expr(args[0]) + 1
        if kind == "CUR_ABILITY": return "ability"
        if kind == "ABILITY_OWNER": return "owner"
        if kind == "CUR_MODIFIER": return "current-core"
        if kind == "HURT_DAMAGE": return 100.0
        if kind == "FOR_EACH_SELECTED_UNIT": return self.selected
        if kind == "MOVER_COLLIDE_UNIT": return self.hit
        if kind == "GET_LAST_MODIFIER_INSTANCE":
            owner = self.expr(args[0])
            if owner != "owner": raise AssertionError(owner)
            return ("core", self.expr(args[1]))
        if kind == "GET_MOD_STACK":
            handle = self.expr(args[0])
            if handle not in self.stacks:
                raise AssertionError("stack read from missing/destroyed instance")
            self.stack_reads.append(handle)
            return self.stacks[handle]
        if kind == "GET_FLOAT_KV":
            if self.expr(args[0]) != "ability": raise AssertionError("wrong KV owner")
            return self.kv[self.expr(args[1])]
        if kind == "GET_UNIT_ATTR":
            unit, result, attr = (self.expr(v) for v in args)
            if result != "ATTR_RESULT": raise AssertionError(result)
            if attr == "attack_phy" and unit == "owner": return self.attack
            if attr == "hp_max": return self.hp[unit]
            raise AssertionError((unit, attr))
        if kind == "GET_UNIT_GROUP_KV":
            unit, key = (self.expr(v) for v in args)
            if key != "带领小队": raise AssertionError(key)
            return self.groups.get(unit, [])
        if kind == 14:
            if self.reference(args[0]) != ("UNIT_GROUP", "搜索组", "actor"):
                raise AssertionError("unknown group")
            return self.groups.get("leaders", [])
        if kind == "UNIT_HAS_TAG":
            unit, tag = (self.expr(v) for v in args)
            return tag in self.tags.get(unit, set())
        raise AssertionError(f"unsupported expression: {kind}")

    def condition(self, node):
        if node.get("enable") is False:
            raise AssertionError("disabled condition must be filtered by its container")
        kind, args = node["condition_type"], node["args_list"]
        if kind == "TYPE_IS_EXIST":
            return self.expr(args[0]) in self.stacks
        if kind in ("FLOAT_COMPARE", "BOOL_COMPARE"):
            left, op, right = (self.expr(v) for v in args)
            if op == "==": return left == right
            if op == ">": return left > right
            if op == ">=": return left >= right
            if op == "<=": return left <= right
            raise AssertionError(op)
        if kind == "IS_UNIT_ALIVE": return self.expr(args[0]) in self.alive
        if kind == "BOOL_NOT":
            result = self.expr(args[0])
            if type(result) is not bool: raise AssertionError("BOOL_NOT requires bool")
            return not result
        if kind in ("AND", "OR"):
            results = [self.condition(c) for c in args[0]["args_list"]
                       if c.get("enable") is not False]
            return all(results) if kind == "AND" else any(results)
        raise AssertionError(f"unsupported condition: {kind}")

    def run(self, actions):
        for node in actions:
            if node.get("enable") is False: continue
            kind, args = node["action_type"], node["args_list"]
            if kind == "IF_THEN_ELSE":
                results = [self.condition(c) for c in args[0]["args_list"]
                           if c.get("enable") is not False]
                self.run(args[1 if all(results) else 2]["args_list"])
            elif kind == "SET_VARIABLE":
                ref = self.reference(args[0]["args_list"][0])
                self.vars[ref] = self.expr(args[1])
                if ref == ("FLOAT", "最终伤害", "local") and self.after_damage_assignment:
                    self.after_damage_assignment(self)
            elif kind == "SET_ENTITY_KV":
                if self.expr(args[0]) != "ability": raise AssertionError("wrong KV owner")
                self.kv[self.expr(args[1])] = self.expr(args[2])
            elif kind == "SET_BUFF_STACK":
                handle, value = (self.expr(v) for v in args)
                if handle not in self.stacks: raise AssertionError("clear missing instance")
                self.stacks[handle] = value
                self.consumptions.append(handle)
            elif kind == "ADD_BUFF_STACK":
                handle, delta = (self.expr(v) for v in args)
                if handle not in self.stacks: raise AssertionError("modify missing instance")
                self.stacks[handle] += delta
                self.consumptions.append(handle)
            elif kind == "PICK_UNIT_DO_ACTION":
                old = self.selected
                for unit in list(self.expr(args[0])):
                    self.selected = unit
                    self.run(args[1]["args_list"])
                self.selected = old
            elif kind == "ADD_MODIFIER":
                # Record arguments/value at invocation; do not simulate buff events.
                self.shields.append((self.expr(args[0]), self.kv["护盾值"]))
                if self.after_shield: self.after_shield(self)
            elif kind == "APPLY_DAMAGE":
                self.damage.append((self.expr(args[2]), self.expr(args[4])))
            elif kind == "CREATE_SFX_ON_UNIT_3":
                pass  # Visual instruction excluded from this projection.
            else:
                raise AssertionError(f"unsupported action: {kind}")


@unittest.skipUnless(all((ROOT / p).is_file() for p in repair.FILES),
                     "requires the seven original native map3 JSONs (Y3_P1_NUMERIC_ROOT)")
class NumericRegression(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw = {p: (ROOT / p).read_bytes() for p in repair.FILES}
        cls.old = {p: json.loads(raw) for p, raw in cls.raw.items()}
        cls.new, cls.reports = repair.build(ROOT)

    def candidate(self, number, kind="ability"):
        return self.new[f"{kind}/{number}.json"]

    def original(self, number, kind="ability"):
        return self.old[f"{kind}/{number}.json"]

    def rebuild(self, docs):
        raw = {p: json.dumps(d).encode("utf-8") for p, d in docs.items()}
        with patch.object(Path, "read_bytes", lambda path: raw[path.as_posix().split("/in-memory/")[-1]]):
            return repair.build(Path("/in-memory"))

    def test_01_build_is_complete_read_only_and_byte_hash_guarded(self):
        self.assertEqual(set(self.new), set(repair.FILES), self.reports)
        for report in self.reports:
            if "path" not in report: continue
            p = report["path"]
            self.assertEqual((ROOT / p).read_bytes(), self.raw[p])
            self.assertEqual(report["source_sha256"], hashlib.sha256(self.raw[p]).hexdigest())
            self.assertEqual(report["status"], "candidate")

    def test_02_all_original_element_ids_preserved_with_no_new_collision(self):
        for p in repair.FILES:
            before = Counter(n["element_id"] for n in nodes(self.old[p]) if "element_id" in n)
            after = Counter(n["element_id"] for n in nodes(self.new[p]) if "element_id" in n)
            self.assertFalse(before - after, p)
            self.assertTrue(all(count == 1 for _, count in (after - before).items()), p)
            self.assertEqual(self.old[p]["trigger_group_info"], self.new[p]["trigger_group_info"])
            for tid, trigger in self.old[p]["trigger_dict"].items():
                for field in ("enabled", "event", "condition", "trigger_id", "p_trigger_id"):
                    self.assertEqual(trigger.get(field), self.new[p]["trigger_dict"][tid].get(field))

    def test_03_unknown_fields_large_integers_and_unrelated_edits_survive(self):
        docs = deepcopy(self.old)
        huge = 340282366920938463463374607431768211455
        for doc in docs.values():
            doc["user_unknown"] = {"id": huge, "text": "manual"}
            doc["trigger_dict"][next(iter(doc["trigger_dict"]))]["user_note"] = "keep"
        new, reports = self.rebuild(docs)
        self.assertEqual(set(new), set(repair.FILES), reports)
        for doc in new.values(): self.assertEqual(doc["user_unknown"]["id"], huge)

    def test_04_unknown_changed_formula_is_reported_not_overwritten(self):
        docs = deepcopy(self.old)
        setter = formula(docs["ability/134263364.json"], 893440004974076)
        setter["args_list"][1]["args_list"][0] = "/"
        new, reports = self.rebuild(docs)
        self.assertNotIn("ability/134263364.json", new)
        self.assertTrue(any(r.get("path") == "ability/134263364.json"
                            and r["status"] == "review_required" for r in reports))

    def test_05_disabled_target_action_is_not_repaired_as_runtime(self):
        docs = deepcopy(self.old)
        action(cast(docs["ability/134266460.json"]), "ADD_BUFF_STACK")["enable"] = False
        new, _ = self.rebuild(docs)
        self.assertNotIn("ability/134266460.json", new)

    def test_06_disabled_duplicate_and_optional_expression_are_preserved(self):
        docs = deepcopy(self.old)
        duplicate = deepcopy(action(cast(docs["ability/134266460.json"]), "ADD_BUFF_STACK"))
        duplicate["enable"] = False
        cast(docs["ability/134266460.json"]).append(duplicate)
        first = cast(docs["ability/134263364.json"])[0]
        first["op_arg"] = [deepcopy(formula(docs["ability/134263364.json"], 893440004974076))]
        first["op_arg_enable"] = [False]
        new, reports = self.rebuild(docs)
        self.assertEqual(set(new), set(repair.FILES), reports)
        self.assertEqual(cast(new["ability/134266460.json"])[-1], duplicate)
        self.assertEqual(cast(new["ability/134263364.json"])[0]["op_arg"], first["op_arg"])

    def test_07_registered_enabled_false_dynamic_trigger_is_still_repaired(self):
        old = self.original(134282266, "modifier")["trigger_dict"]["1418035204"]
        new = self.candidate(134282266, "modifier")["trigger_dict"]["1418035204"]
        self.assertIs(old["enabled"], False)
        self.assertNotEqual(old["action"], new["action"])
        self.assertEqual(old["sub_trigger_owner_set_var_action"], new["sub_trigger_owner_set_var_action"])

    def test_08_unregistered_dynamic_trigger_is_reported(self):
        docs = deepcopy(self.old)
        docs["modifier/134282266.json"]["trigger_dict"]["1485688834"]["action"] = []
        new, _ = self.rebuild(docs)
        self.assertNotIn("modifier/134282266.json", new)

    def test_09_huangzhong_old_wrong_resource_and_fixed_clear(self):
        old = action(cast(self.original(134266460)), "ADD_BUFF_STACK")
        p = Projection({("core", 134242511): 4, ("core", 134267407): 2})
        p.run([old])
        self.assertEqual(p.stacks[("core", 134242511)], 3)  # Old: leaves two visible.
        new = action(cast(self.candidate(134266460)), "ADD_BUFF_STACK")
        for own in range(2, 5):
            for other in range(1, 5):
                p = Projection({("core", 134242511): own, ("core", 134267407): other})
                p.run([new])
                self.assertEqual(p.stacks[("core", 134242511)], 1)
                self.assertEqual(p.stacks[("core", 134267407)], other)

    def hz_resource_stage(self, doc):
        # Stop before animation/projectile instructions; manual-target IF omitted.
        stage = []
        for node in cast(doc)[1:]:
            if node.get("action_type") == "PLAY_ANIMATION": break
            stage.append(node)
        return stage

    def test_10_huangzhong_missing_core_uses_base_without_stack_dereference(self):
        p = Projection()
        p.kv.update({"伤害系数": 0.8, "额外系数": 50.0})
        with self.assertRaisesRegex(AssertionError, "missing/destroyed"):
            p.run(self.hz_resource_stage(self.original(134266460)))
        p = Projection()
        p.kv.update({"伤害系数": 0.8, "额外系数": 50.0})
        p.run(self.hz_resource_stage(self.candidate(134266460)))
        self.assertEqual(p.vars[("FLOAT", "最终伤害", "local")], 80)
        self.assertEqual(p.stack_reads, [])
        self.assertEqual(p.consumptions, [])

    def test_11_huangzhong_destroyed_core_before_clear_is_guarded(self):
        p = Projection({("core", 134242511): 4})
        p.kv.update({"伤害系数": 0.8, "额外系数": 50.0})
        # Adversarial invalidation at the amplified assignment, not an assertion
        # about engine callbacks or whether this invalidation normally occurs.
        def invalidate(state):
            if len(state.stack_reads) >= 2: state.stacks.clear()
        p.after_damage_assignment = invalidate
        p.run(self.hz_resource_stage(self.candidate(134266460)))
        self.assertEqual(p.vars[("FLOAT", "最终伤害", "local")], 230)
        self.assertEqual(p.consumptions, [])

    def test_12_huangzhong_collision_uses_actual_unit_for_all_four_operands(self):
        old_cb, new_cb = collision(self.original(134280536)), collision(self.candidate(134280536))
        old_damage = action(old_cb, "APPLY_DAMAGE")
        new_damage = action(new_cb, "APPLY_DAMAGE")
        p = Projection()
        self.assertEqual(p.expr(old_damage["args_list"][2]), "actor-primary")
        for hit in ("soldier-A", "leader-B", "elite-C"):
            p.hit = hit
            self.assertEqual(p.expr(new_damage["args_list"][2]), hit)
            self.assertEqual(p.expr(action(new_cb, "ADD_MODIFIER")["args_list"][0]), hit)
        tags = [n for n in nodes(new_cb) if n.get("condition_type") == "UNIT_HAS_TAG"]
        self.assertEqual(len(tags), 2)
        self.assertTrue(all(n["args_list"][0] == {"arg_type": 100006,
            "sub_type": "MOVER_COLLIDE_UNIT", "args_list": []} for n in tags))
        before, after = action(cast(self.original(134280536)), "CREATE_STRAIGHT_MOVER"), action(cast(self.candidate(134280536)), "CREATE_STRAIGHT_MOVER")
        self.assertEqual(before["args_list"][:9], after["args_list"][:9])
        self.assertEqual(before["op_arg_enable"], after["op_arg_enable"])
        self.assertEqual(before["op_arg"], after["op_arg"])

    def test_13_machao_old_250_percent_fixed_160_percent_not_per_stack(self):
        old = formula(self.original(134264317), 893440004975771)
        new = formula(self.candidate(134264317), 893440004975771)
        p = Projection({("core", 134265433): 3})
        self.assertAlmostEqual(p.expr(old), 250)
        for internal in (3, 4):
            p.stacks[("core", 134265433)] = internal
            self.assertAlmostEqual(p.expr(new), 160)

    def test_14_machao_zero_to_three_visible_layers_and_four_hit_cap(self):
        for visible, expected in ((0, 115), (1, 115), (2, 160), (3, 160)):
            p = Projection({("core", 134265433): visible + 1})
            for i in range(5):
                p.hit = f"hit-{i}"
                p.run(collision(self.candidate(134264317)))
            self.assertEqual([hit for hit, _ in p.damage], [f"hit-{i}" for i in range(4)])
            for _, value in p.damage: self.assertAlmostEqual(value, expected)

    def test_15_level_coefficients_checked_and_all_five_xunyu_writes_fixed(self):
        old = self.original(134222326)["trigger_dict"]["26066946"]["action"][0]
        new = self.candidate(134222326)["trigger_dict"]["26066946"]["action"][0]
        self.assertEqual([c["args_list"][0]["args_list"][0] for c in new["args_list"][1]["args_list"]], [1, 2, 3, 4, 5])
        for old_case, new_case in zip(old["args_list"][1]["args_list"], new["args_list"][1]["args_list"]):
            before = action(old_case, "SET_ENTITY_KV")["args_list"][2]
            after = action(new_case, "SET_ENTITY_KV")["args_list"][2]
            self.assertEqual(before["args_list"], [0.8])
            self.assertEqual(after["args_list"], [0.08])
            self.assertAlmostEqual(100 * (1 - after["args_list"][0]), 92)

    def test_16_xiahouyuan_core_is_bonus_not_damage_replacement(self):
        old = action(self.original(134282266, "modifier"), "SET_CUR_DAMAGE")["args_list"][0]
        new = action(self.candidate(134282266, "modifier"), "SET_CUR_DAMAGE")["args_list"][0]
        p = Projection({"current-core": 1})
        self.assertEqual(p.expr(old), 5)
        for visible, expected in ((0, 100), (1, 105), (2, 110), (3, 115)):
            p.stacks["current-core"] = visible + 1
            self.assertAlmostEqual(p.expr(new), expected)

    def test_17_xiahouyuan_active_attack_scales_entire_coefficient(self):
        old = formula(self.original(134263364), 893440004974076)
        new = formula(self.candidate(134263364), 893440004974076)
        p = Projection({("core", 134282266): 4})
        p.kv["伤害系数"] = 2.5
        self.assertAlmostEqual(p.expr(old), 251.35)
        for attack_value in (40, 100, 333):
            p.attack = attack_value
            for visible, coefficient in ((0, 2.5), (1, 2.95), (2, 3.4), (3, 3.85)):
                p.stacks[("core", 134282266)] = visible + 1
                self.assertAlmostEqual(p.expr(new), attack_value * coefficient)

    @staticmethod
    def shield_context(visible=3):
        hp = {"L1": 1000, "S1": 200, "L2": 1200, "S2": 300, "L3": 2000}
        groups = {"leaders": ["L1", "L2", "L3"], "L1": ["S1"], "L2": ["S2"]}
        return Projection({("core", 134224731): visible + 1}, hp=hp, groups=groups)

    @staticmethod
    def shield_stage(doc):
        # Original/new cast share two leading visual instructions only.
        return cast(doc)[2:]

    def test_18_caoren_old_first_team_consumes_resource_fixed_all_teams(self):
        old = self.shield_context()
        old.run(self.shield_stage(self.original(134231116)))
        self.assertEqual(old.shields, [("L1", 150), ("S1", 30), ("L2", 0), ("S2", 0), ("L3", 0)])
        for visible in range(1, 6):
            p = self.shield_context(visible)
            p.run(self.shield_stage(self.candidate(134231116)))
            for unit, value in p.shields:
                self.assertAlmostEqual(value, p.hp[unit] * 0.05 * visible)
            self.assertEqual(len(p.shields), 5)
            self.assertEqual(p.consumptions, [("core", 134224731)])
            self.assertEqual(p.stacks[("core", 134224731)], 1)

    def test_19_caoren_absent_empty_core_or_no_valid_leader_never_reads_unsafely(self):
        for case in ("absent", "empty", "no-leaders", "dead", "death-tag"):
            p = self.shield_context()
            if case == "absent": p.stacks.clear()
            if case == "empty": p.stacks[("core", 134224731)] = 1
            if case == "no-leaders": p.groups["leaders"] = []
            if case == "dead": p.alive.clear()
            if case == "death-tag": p.tags = {u: {"已死亡"} for u in p.hp}
            p.run(self.shield_stage(self.candidate(134231116)))
            self.assertEqual(p.shields, [], case)
            self.assertEqual(p.consumptions, [], case)
            if case not in ("empty",): self.assertEqual(p.stack_reads, [], case)

    def test_20_caoren_new_resource_after_consumption_is_not_cleared_again(self):
        p = self.shield_context()
        def gain_after_first_shield(state):
            if len(state.shields) == 1: state.stacks[("core", 134224731)] = 2
        p.after_shield = gain_after_first_shield
        p.run(self.shield_stage(self.candidate(134231116)))
        self.assertEqual(p.stacks[("core", 134224731)], 2)
        self.assertEqual(len(p.consumptions), 1)
        for unit, value in p.shields: self.assertAlmostEqual(value, p.hp[unit] * 0.15)

    def test_21_caoren_next_cast_resets_snapshot_and_consumption_flag(self):
        p = self.shield_context(1)
        stage = self.shield_stage(self.candidate(134231116))
        p.run(stage)
        p.stacks[("core", 134224731)] = 6
        p.shields.clear()
        p.run(stage)
        self.assertEqual(len(p.consumptions), 2)
        for unit, value in p.shields: self.assertAlmostEqual(value, p.hp[unit] * 0.25)

    def test_22_new_if_nodes_have_explicit_native_fake_op(self):
        for path in ("ability/134266460.json", "ability/134231116.json"):
            old_ids = {n.get("element_id") for n in nodes(self.old[path])}
            for n in nodes(self.new[path]):
                if n.get("action_type") == "IF_THEN_ELSE" and n["element_id"] not in old_ids:
                    self.assertEqual(n.get("fake_op"), [])

    def test_23_disabled_conditions_are_not_executed_by_projection(self):
        p = Projection()
        broken = {"condition_type": "NOT_IMPLEMENTED", "args_list": [], "enable": False}
        p.run([{"action_type": "IF_THEN_ELSE", "args_list": [
            {"args_list": [broken]}, {"args_list": []}, {"args_list": []}]}])
        with self.assertRaisesRegex(AssertionError, "unsupported expression"):
            p.expr({"arg_type": 100000, "sub_type": "UNKNOWN", "args_list": []})

    def test_24_disabled_old_autocast_gate_does_not_protect_snapshot(self):
        docs = deepcopy(self.old)
        # Deliberately disable outer auto-cast logic; cast-time guards must stand alone.
        for n in nodes(docs["ability/134231116.json"]["trigger_dict"]["1959489540"]):
            if "condition_type" in n: n["enable"] = False
        new, reports = self.rebuild(docs)
        self.assertIn("ability/134231116.json", new, reports)
        p = self.shield_context()
        p.stacks.clear()
        p.run(self.shield_stage(new["ability/134231116.json"]))
        self.assertEqual(p.stack_reads, [])

    def test_25_reviewed_level_changes_and_new_obtain_setters_are_not_overwritten(self):
        docs = deepcopy(self.old)
        t = docs["ability/134222326.json"]["trigger_dict"]["26066946"]
        first = [n for n in nodes(t) if n.get("action_type") == "SET_ENTITY_KV"][0]
        first["args_list"][2]["args_list"][0] = 0.12
        new, _ = self.rebuild(docs)
        self.assertNotIn("ability/134222326.json", new)
        docs = deepcopy(self.old)
        docs["ability/134222326.json"]["trigger_dict"]["1959489540"]["action"].append(first)
        new, _ = self.rebuild(docs)
        self.assertNotIn("ability/134222326.json", new)

    def test_26_only_owned_trigger_actions_and_caoren_local_declarations_change(self):
        allowed = {"ability/134266460.json": "893440004",
                   "ability/134280536.json": "893440004",
                   "ability/134231116.json": "893440004",
                   "ability/134264317.json": "893440004",
                   "ability/134222326.json": "26066946",
                   "modifier/134282266.json": "1418035204",
                   "ability/134263364.json": "893440004"}
        for path, tid in allowed.items():
            before, after = deepcopy(self.old[path]), deepcopy(self.new[path])
            before["trigger_dict"][tid].pop("action")
            after["trigger_dict"][tid].pop("action")
            if path == "ability/134231116.json":
                before["trigger_dict"][tid].pop("var_data")
                after["trigger_dict"][tid].pop("var_data")
                before["local_variable"].pop(tid)
                after["local_variable"].pop(tid)
            self.assertEqual(before, after, path)

    def test_27_disabled_legal_leader_gate_is_reported_not_assumed_active(self):
        for index in (0, 1):
            docs = deepcopy(self.old)
            branch = action(cast(docs["ability/134231116.json"]), "IF_THEN_ELSE", 893440004975552)
            guards = branch["args_list"][0]["args_list"][0]["args_list"][0]["args_list"]
            guards[index]["enable"] = False
            new, reports = self.rebuild(docs)
            self.assertNotIn("ability/134231116.json", new)
            self.assertTrue(any("disabled" in r.get("explanation", "") for r in reports))

    def test_28_unknown_metadata_that_would_be_removed_requires_review(self):
        docs = deepcopy(self.old)
        f = formula(docs["ability/134264317.json"], 893440004975771)
        f["args_list"][2]["args_list"][2]["args_list"][2]["user_unknown"] = "keep"
        new, reports = self.rebuild(docs)
        self.assertNotIn("ability/134264317.json", new)
        self.assertTrue(any("unknown metadata" in r.get("explanation", "") for r in reports))

    def test_29_caoren_core_destroyed_after_first_shield_uses_existing_snapshot(self):
        p = self.shield_context(3)
        p.after_shield = lambda state: state.stacks.clear()
        p.run(self.shield_stage(self.candidate(134231116)))
        self.assertEqual(len(p.shields), 5)
        self.assertEqual(len(p.consumptions), 1)
        self.assertEqual(len(p.stack_reads), 1)
        for unit, value in p.shields: self.assertAlmostEqual(value, p.hp[unit] * 0.15)

    def test_30_candidate_reapplication_is_non_destructive_and_review_only(self):
        new, reports = self.rebuild(self.new)
        self.assertEqual(new, {})
        self.assertEqual(len([r for r in reports if r["status"] == "review_required"]), 7)


class InputSafety(unittest.TestCase):
    def test_missing_inputs_are_reported_without_writes(self):
        with patch.object(Path, "read_bytes", side_effect=FileNotFoundError("missing input")), \
                patch.object(Path, "write_bytes", side_effect=AssertionError("write forbidden")), \
                patch.object(Path, "write_text", side_effect=AssertionError("write forbidden")):
            new, reports = repair.build(Path("/not-read"))
        self.assertEqual(new, {})
        self.assertEqual(len([r for r in reports if r["status"] == "review_required"]), 7)

    def test_duplicate_json_keys_are_rejected_not_silently_lost(self):
        with patch.object(Path, "read_bytes", return_value=b'{"unknown":1,"unknown":2}'):
            new, reports = repair.build(Path("/not-read"))
        self.assertEqual(new, {})
        self.assertTrue(all("duplicate JSON key" in r["explanation"]
                            for r in reports if r["status"] == "review_required"))


if __name__ == "__main__":
    unittest.main()

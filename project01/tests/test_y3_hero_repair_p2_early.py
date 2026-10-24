"""Independent, deliberately narrow AST regression model, not a Y3 emulator.

No live writes. Native actions below have explicit mock semantics. Geometry,
group membership, ADD_MODIFIER cover/callback behavior, attribute aggregation,
timer scheduling, closure capture, editor validation and movement physics are
NOT certified. Group membership and arrival timing are supplied by each test.
Unknown actions/expressions and unsupported TYPE_IS_EXIST operands fail loudly.
Run with python -B -m unittest discover -s tests -p test_y3_hero_repair_p2_early.py.
"""
from copy import deepcopy
import hashlib
import json
import os
from collections import Counter
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import y3_hero_repair_p2_early as repair

MAP = Path(os.environ.get("Y3_EARLY_TEST_ROOT", "D:/littl/testTempFile/ProjectMonster02/maps/map3"))


def nodes(value):
    if isinstance(value, dict):
        if value.get("enable") is False:
            return
        yield value
        for key, child in value.items():
            if key == "op_arg":
                for arg, enabled in zip(child, value.get("op_arg_enable", [])):
                    if enabled:
                        yield from nodes(arg)
            elif key != "op_arg_enable":
                yield from nodes(child)
    elif isinstance(value, list):
        for item in value:
            yield from nodes(item)


def find(tree, kind, eid=None):
    result = [x for x in nodes(tree) if x.get("action_type", x.get("condition_type")) == kind
              and (eid is None or x.get("element_id") == eid)]
    if len(result) != 1:
        raise AssertionError((kind, eid, len(result)))
    return result[0]


def load(relative):
    return json.loads((MAP / relative).read_bytes())


def cast(doc):
    return doc["trigger_dict"]["893440004"]["action"]


def level_values(doc, rank):
    switch = find(doc["trigger_dict"]["26066946"]["action"], "SWITCH")
    c = switch["args_list"][1]["args_list"][rank - 1]
    return {x["args_list"][1]["args_list"][0]: x["args_list"][2]["args_list"][0]
            for x in nodes(c) if x.get("action_type") == "SET_ENTITY_KV"}


class Entity:
    def __init__(self, kind="unit", hp=100, maximum=100, team=1, **values):
        self.kind, self.hp, self.maximum, self.team = kind, hp, maximum, team
        self.values = values
        self.valid = self.alive = True
        self.buffs = []
        self.tags = {"阵型队长"}
        self.attack = 100
        self.ai = None
        self.owner = None
        self.related = None
        self.resource = 0
        self.stacks = 1
        self.stackmax = 4
        self.remaining = 0
        self.shield = 0
        self.source = None
        self.cast_type = 1
        self.runtime = {}
        self.contributions = {}


class Model:
    def __init__(self, values=None):
        self.owner = Entity()
        self.ability = Entity("ability", **(values or {}))
        self.ability.owner = self.owner
        self.modifier = None
        self.selected = self.selected_buff = self.event_buff = None
        self.selection = []
        self.vars = {}
        self.damage = []
        self.costs = []
        self.timers = []
        self.movements = []
        self.on_damage = None
        self.commands = []
        self.phase = 2
        self.doc = self.support_doc = None
        self.event = None
        self.context = {}
        self.current_damage = 100.0
        self.registered = set()
        self.timer_handles = set()
        self.serial = 0
        self.on_timer_start = None

    def ref(self, v):
        raw = v["args_list"][0]
        return tuple(raw["items"] if isinstance(raw, dict) else raw)

    def typed(self, obj, kind):
        if not isinstance(obj, Entity) or not obj.valid or obj.kind != kind:
            raise AssertionError("invalid " + kind + " dereference")
        return obj

    def buff(self, resource, owner=None, related=None, stacks=1):
        owner = self.owner if owner is None else owner
        b = Entity("modifier")
        b.owner, b.related, b.resource, b.stacks = owner, related or self.ability, resource, stacks
        owner.buffs.append(b)
        return b

    def live_buffs(self, owner, resource=None):
        owner = self.typed(owner, "unit")
        return [b for b in owner.buffs if b.valid and (resource is None or b.resource == resource)]

    def invoke(self, doc, tid, modifier=None):
        previous = self.doc, self.modifier, self.vars, self.event
        self.doc, self.event = doc, doc["trigger_dict"][tid]["event"][0]["event_type"]
        if modifier is not None:
            self.modifier, self.vars = modifier, modifier.runtime
            for kind, entries in doc["variable_dict"].items():
                for name, initial in entries.items():
                    self.vars.setdefault((kind, name, "actor"), deepcopy(initial))
        try:
            self.run(doc["trigger_dict"][tid]["action"])
        finally:
            self.doc, self.modifier, self.vars, self.event = previous

    def support_callback(self, buff, actions):
        previous = self.doc, self.modifier, self.vars, self.event
        self.doc, self.modifier, self.vars, self.event = self.support_doc, buff, buff.runtime, "TIMER"
        try: self.run(actions)
        finally: self.doc, self.modifier, self.vars, self.event = previous

    def attack_speed(self, owner):
        return sum(b.contributions.get("attack_speed", 0) for b in self.live_buffs(owner))

    def expr(self, v):
        if v is None:
            raise AssertionError("missing expression")
        sub, args = v["sub_type"], v["args_list"]
        if sub in (2, 6, 11, "VARIABLE"):
            key = self.ref(v)
            if key[:2] == ("INTEGER", "当前游戏进程阶段"):
                return self.phase
            return self.vars.get(key, 0 if key[0] in ("INTEGER", "FLOAT") else None)
        if sub == 1:
            if len(args) != 1 or isinstance(args[0], (dict, list)):
                raise AssertionError("nonprimitive literal")
            return args[0]
        if sub == "ABILITY_OWNER": return self.owner
        if sub == "CUR_ABILITY": return self.ability
        if sub == "GET_ABILITY_OWNER": return self.typed(self.expr(args[0]), "ability").owner
        if sub == "GET_BUFF_SOURCE": return self.typed(self.expr(args[0]), "modifier").source
        if sub == "CUR_MODIFIER": return self.modifier
        if sub == "MODIFIER_OWNER": return self.typed(self.modifier, "modifier").owner
        if sub == "FOR_EACH_SELECTED_UNIT": return self.selected
        if sub == "FOR_EACH_SELECTED_MODIFIER": return self.selected_buff
        if sub == "GET_MODIFIER_FROM_EVENT": return self.event_buff
        if sub == "NONE_UNIT": return None
        if sub in ("DAMAGE_SOURCE_UNIT", "DAMAGE_TARGET_UNIT", "DAMAGE_ABILITY", "HURT_DAMAGE"):
            if self.event != "SPECIAL_UNIT_EVENT":
                raise AssertionError("damage parameter unavailable in " + str(self.event))
            return self.current_damage if sub == "HURT_DAMAGE" else self.context.get(sub)
        if sub == "GET_ABILITY_CAST_TYPE": return self.typed(self.expr(args[0]), "ability").cast_type
        if sub in ("REG_MODIFIER_TRIGGER", "REG_ABILITY_TRIGGER"):
            expected = "OBTAIN_MODIFIER" if sub == "REG_MODIFIER_TRIGGER" else "ABILITY_OBTAIN"
            if self.event != expected: raise AssertionError("invalid registration context")
            token = (id(self.modifier if sub == "REG_MODIFIER_TRIGGER" else self.ability), self.expr(args[0]))
            self.registered.add(token)
            return token
        if sub == "GET_ABILITY_TARGET_UNIT_FROM_EVENT": return self.vars.get(("UNIT_ENTITY", "目标单位", "actor"))
        if sub in ("GET_FLOAT_KV", "GET_INTEGER_KV", "GET_BOOLEAN_KV", "GET_UNIT_GROUP_KV", "GET_MODIFIER_ENTITY_KV"):
            obj = self.expr(args[0])
            if not isinstance(obj, Entity) or not obj.valid:
                raise AssertionError("KV of invalid object")
            key = self.expr(args[1])
            return obj.values.get(key, [] if sub == "GET_UNIT_GROUP_KV" else 0)
        if sub == "GET_HP_CUR": return self.typed(self.expr(args[0]), "unit").hp
        if sub == "GET_UNIT_ATTR":
            obj = self.typed(self.expr(args[0]), "unit")
            attr = self.expr(args[2])
            if attr == "hp_max": return obj.maximum
            if attr == "attack_phy": return obj.attack
            raise NotImplementedError(attr)
        if sub in ("ARITHMETIC_OPERATION", "MATH_OPERATION"):
            left, op, right = [self.expr(a) for a in args]
            if op == "+": return left + right
            if op == "-": return left - right
            if op == "*": return left * right
            if op == "/": return left / right
            raise NotImplementedError(op)
        if sub == "I2F": return float(self.expr(args[0]))
        if sub == "UNIT_HAS_MODIFIER": return bool(self.live_buffs(self.expr(args[0]), self.expr(args[1])))
        if sub == "GET_LAST_MODIFIER_INSTANCE":
            buffs = self.live_buffs(self.expr(args[0]), self.expr(args[1]))
            return buffs[-1] if buffs else None
        if sub in ("GET_MOD_STACK", "GET_MOD_STACK_MAX"):
            obj = self.typed(self.expr(args[0]), "modifier")
            return obj.stacks if sub == "GET_MOD_STACK" else obj.stackmax
        if sub == "RELATED_ABILITY_MODIFIER": return self.typed(self.expr(args[0]), "modifier").related
        if sub == "GET_MODIFIER_ENTITY_METATYPE": return self.typed(self.expr(args[0]), "modifier").resource
        if sub == "GET_UNIT_AI_BATTLE_TARGET_UNIT": return self.typed(self.expr(args[0]), "unit").ai
        if sub == "IS_ALLY":
            return self.typed(self.expr(args[0]), "unit").team == self.typed(self.expr(args[1]), "unit").team
        if sub == "UNIT_HAS_TAG": return self.expr(args[1]) in self.typed(self.expr(args[0]), "unit").tags
        if sub == "UNIT_LIST_IN_SHAPE":
            # Geometry and native team filtering are supplied, not fabricated.
            result = self.selection[:]
            flags = v.get("op_arg_enable", [])
            if len(flags) > 12 and flags[12]:
                result = result[:self.expr(v["op_arg"][12])]
            return result
        if sub == "ADD_MODIFIER":
            return self.add(v)
        raise NotImplementedError((v["arg_type"], sub))

    def condition(self, c):
        k, args = c["condition_type"], c["args_list"]
        if k == "TYPE_IS_EXIST":
            if args[0]["arg_type"] not in (100006, 100014):
                raise NotImplementedError("unverified existence overload")
            obj = self.expr(args[0])
            expected = {100006: "unit", 100014: "ability"}[args[0]["arg_type"]]
            return isinstance(obj, Entity) and obj.valid and obj.kind == expected
        if k == "IS_UNIT_ALIVE": return self.typed(self.expr(args[0]), "unit").alive
        if k == "UNIT_HAS_MODIFIER": return bool(self.live_buffs(self.expr(args[0]), self.expr(args[1])))
        if k in ("FLOAT_COMPARE", "BOOL_COMPARE", "UNIT_COMPARE", "MODIFIER_COMPARE", "ABILITY_ENTITY_COMPARE", "MODIFIER_CLASS_COMPARE", "ABILITY_CAST_TYPE_COMPARE"):
            left, op, right = [self.expr(a) for a in args]
            if op == "==": return left == right
            if op == "!=": return left != right
            if op == "<": return left < right
            if op == ">": return left > right
            if op == ">=": return left >= right
            raise NotImplementedError(op)
        if k == "BOOL_NOT":
            value = self.expr(args[0])
            if type(value) is not bool: raise AssertionError("not a native bool")
            return not value
        if k == "OR":
            return any([self.condition(x) for x in args[0]["args_list"]])
        if k == "UNIT_HAS_TAG": return self.expr(args[1]) in self.typed(self.expr(args[0]), "unit").tags
        if k == "IS_ENEMY":
            a, b = [self.typed(self.expr(v), "unit") for v in args]
            return a.team != b.team and a.team != 0 and b.team != 0
        raise NotImplementedError(k)

    def add(self, node):
        owner, resource = [self.expr(a) for a in node["args_list"]]
        self.typed(owner, "unit")
        optional = {}
        for i, (arg, enabled) in enumerate(zip(node.get("op_arg", []), node.get("op_arg_enable", []))):
            if enabled: optional[i] = self.expr(arg)
        b = self.buff(resource, owner, optional.get(1, self.ability))
        b.source = optional.get(0)
        b.remaining = optional.get(2, 0)
        if resource == repair.SUPPORT:
            if self.support_doc is None: raise AssertionError("support definition missing")
            self.invoke(self.support_doc, repair.SUPPORT_GAIN, b)
        return b

    def run(self, actions):
        for a in actions:
            if type(a) is int:
                if self.doc is None: raise AssertionError("registration requires owning document")
                self.run([self.doc["trigger_dict"][str(a)]["sub_trigger_owner_set_var_action"]])
                continue
            if a.get("enable") is False: continue
            k, args = a["action_type"], a["args_list"]
            if k == "IF_THEN_ELSE":
                # Eager evaluation deliberately prevents accidental short-circuit safety.
                checks = [self.condition(c) for c in args[0]["args_list"] if c.get("enable") is not False]
                self.run(args[1 if all(checks) else 2]["args_list"])
            elif k == "SET_VARIABLE": self.vars[self.ref(args[0])] = self.expr(args[1])
            elif k == "SET_ENTITY_KV":
                obj = self.expr(args[0])
                if not isinstance(obj, Entity) or not obj.valid: raise AssertionError("write invalid entity")
                obj.values[self.expr(args[1])] = self.expr(args[2])
            elif k == "ADD_BUFF_STACK":
                b = self.typed(self.expr(args[0]), "modifier")
                delta = self.expr(args[1])
                b.stacks += delta
                self.costs.append(delta)
            elif k == "ADD_MODIFIER": self.add(a)
            elif k == "SET_BUFF_SHIELD": self.typed(self.expr(args[0]), "modifier").shield = self.expr(args[1])
            elif k == "SET_BUFF_REMAINING": self.typed(self.expr(args[0]), "modifier").remaining = self.expr(args[1])
            elif k == "REMOVE_BUFF_INS":
                b = self.typed(self.expr(args[0]), "modifier")
                if b.resource == repair.SUPPORT:
                    self.invoke(self.support_doc, repair.SUPPORT_LOSS, b)
                b.valid = False
            elif k == "ADD_MODIFIER_OWNER_ATTR":
                b = self.typed(self.expr(args[0]), "modifier")
                if self.expr(args[2]) != "ATTR_ALL_RATIO": raise NotImplementedError("attribute kind")
                b.contributions[self.expr(args[1])] = self.expr(args[3])
            elif k == "CLEAR_MODIFIER_OWNER_ATTR": self.typed(self.expr(args[0]), "modifier").contributions.clear()
            elif k == "SET_CUR_DAMAGE":
                if self.event != "SPECIAL_UNIT_EVENT": raise AssertionError("not a damage event")
                self.current_damage = self.expr(args[0])
            elif k == "UNREG_TRIGGER":
                token = self.expr(args[0])
                if token not in self.registered: raise AssertionError("unregister uncreated/already removed listener")
                self.registered.remove(token)
            elif k == "DELETE_TIMER":
                token = self.expr(args[0])
                if token not in self.timer_handles: raise AssertionError("delete uncreated/already deleted timer")
                self.timer_handles.remove(token)
            elif k == "ITER_MODIFIER_DO":
                previous = self.selected_buff
                for b in self.live_buffs(self.expr(args[0]))[:]:
                    self.selected_buff = b
                    self.run(args[1]["args_list"])
                self.selected_buff = previous
            elif k == "PICK_UNIT_DO_ACTION":
                previous = self.selected
                for u in self.expr(args[0]):
                    self.selected = u
                    self.run(args[1]["args_list"])
                self.selected = previous
            elif k == "APPLY_DAMAGE":
                self.damage.append((self.typed(self.expr(args[2]), "unit"), self.expr(args[4])))
                if self.on_damage: self.on_damage(self)
            elif k == "CALL_TRIGGER_FUNC":
                # Knockback is an external dependency, not silently simulated.
                raise NotImplementedError("external knockback")
            elif k == "RUN_LOOP_TIMER":
                self.timers.append(args[3]["args_list"])
                self.serial += 1
                token = ("timer", self.serial)
                self.timer_handles.add(token)
                if self.on_timer_start: self.on_timer_start(self, args[3]["args_list"])
                # Deliberately publish the handle only after a possible immediate
                # callback, matching the dangerous RUN_LOOP continuation window.
                self.vars[self.ref(args[0])] = token
            elif k == "CREATE_STRAIGHT_MOVER":
                # Capture the observed finish-action slot only; no physics or
                # implicit execution. A test must explicitly invoke arrival.
                self.movements.append(args[5]["args_list"])
            elif k == "UNIT_RELEASE_COMMAND":
                if args[1]["sub_type"] != "UNIT_COMMAND_USE_SKILL":
                    raise NotImplementedError("command kind")
                # Record requests only; this does not prove an engine cast.
                self.commands.append((self.typed(self.expr(args[0]), "unit"),
                                      self.typed(self.expr(args[1]["args_list"][0]), "ability")))
            elif k == "ADD_CUR_HP": self.typed(self.expr(args[0]), "unit").hp += self.expr(args[1])
            elif k == "PRINT_MESSAGE_ACTION_TO_DIALOG": pass
            else: raise NotImplementedError(k)


def shield_actions(doc):
    return [a for a in cast(doc) if a.get("action_type") in {"SET_VARIABLE", "IF_THEN_ELSE", "SET_ENTITY_KV", "ADD_MODIFIER"}]


def soldier(team=1, ranged=True):
    u = Entity(team=team)
    u.tags = {"远程普攻"} if ranged else set()
    return u


def archers(docs):
    m = Model()
    m.support_doc = docs[repair.SUPPORT_ECA]
    troop = soldier()
    m.owner.values["带领小队"] = [troop]
    m.invoke(docs[repair.ARCHER], repair.GAIN)
    buff = m.live_buffs(troop, repair.SUPPORT)[0]
    return m, troop, buff


def hit(m, buff, victim=None, attacker=None, attack=None):
    m.current_damage = 100.0
    m.context = dict(DAMAGE_SOURCE_UNIT=buff.owner if attacker is None else attacker,
                     DAMAGE_TARGET_UNIT=soldier(team=2) if victim is None else victim,
                     DAMAGE_ABILITY=Entity("ability") if attack is None else attack)
    m.invoke(m.support_doc, repair.SUPPORT_HURT, buff)
    return m.current_damage


class AOriginalDefects(unittest.TestCase):
    def test_00_shield_accumulation_and_unconditional_subtraction(self):
        for oid, resource, base, extra in [(134232470, 134259960, 500, 100), (134256840, 134264323, 300, 50)]:
            d = load(f"ability/{oid}.json")
            m = Model({"护盾值": base, "额外系数": extra})
            m.vars[("UNIT_ENTITY", "目标单位", "actor")] = m.owner
            if oid == 134232470:
                m.buff(resource, stacks=2)
                m.run(shield_actions(d)); m.run(shield_actions(d))
                self.assertEqual(m.ability.values["护盾值"], 700)
            else:
                m.buff(resource, stacks=1)
                for _ in range(7): m.run(shield_actions(d))
                self.assertEqual(m.ability.values["护盾值"], -50)

    def test_01_zhangfei_mutates_base_and_cannot_deliver_snapshot(self):
        d = load("ability/134278144.json")
        writes = [x for x in nodes(cast(d)) if x.get("action_type") == "SET_ENTITY_KV"]
        self.assertEqual([x["element_id"] for x in writes], [893440004974199, 893440004974202])
        m = Model({"护盾值": 500, "额外系数": 100})
        m.buff(134224490, stacks=4)
        m.vars[("UNIT_ENTITY", "目标单位", "actor")] = m.owner
        m.run(shield_actions(d))
        self.assertEqual(m.ability.values["护盾值"], 800)

    def test_02_sweep_cost_is_inside_victim_loop(self):
        d = load("ability/134268037.json")
        pick = find(cast(d), "PICK_UNIT_DO_ACTION")
        b = find(pick, "IF_THEN_ELSE", 893440004974860)
        m = Model(); core = m.buff(134224490, stacks=4)
        for _ in range(3): m.selected = Entity(); m.run([b])
        self.assertEqual(core.stacks, 1)
        self.assertEqual(m.costs, [-1, -1, -1])

    def test_03_courage_second_event_deletes_effect(self):
        d = load("ability/134233053.json")
        b = d["trigger_dict"]["58232837"]["action"][0]
        m = Model(); m.run([b]); m.run([b])
        self.assertEqual(m.live_buffs(m.owner, 134254769), [])

    def test_04_missing_coefficients_and_heal_assignment(self):
        d = load("ability/134280536.json")
        self.assertNotIn("额外系数", level_values(d, 1))
        regen = load("modifier/134228469.json")
        self.assertFalse(any(x.get("action_type") == "SET_ENTITY_KV" for x in nodes(regen)))
        self.assertFalse(any(x.get("action_type") == "APPLY_DAMAGE" for x in nodes(cast(load("ability/134275990.json")))))

    def test_05_absolute_hp_selects_wrong_leader(self):
        for oid in sorted(repair.RATIO_FILES):
            d = load(f"ability/{oid}.json")
            tid = "58232837" if oid == 134221456 else "1959489540"
            pick = find(d["trigger_dict"][tid]["action"], "PICK_UNIT_DO_ACTION", 1959489540974145)
            a, b = Entity(hp=100, maximum=1000), Entity(hp=40, maximum=100)
            m = Model(); m.selection = [a, b]; m.run([pick])
            self.assertIs(m.vars[("UNIT_ENTITY", "目标单位", "actor")], b)

    def test_06_full_buff_remains_after_resource_consumption(self):
        d = load("ability/134236877.json")
        timer = find(d["trigger_dict"]["1959489540"]["action"], "RUN_LOOP_TIMER")
        m = Model(); soldier = Entity(); m.owner.values["带领小队"] = [soldier]
        core = m.buff(134242511, stacks=4)
        m.run(timer["args_list"][3]["args_list"])
        core.stacks = 1
        m.run(timer["args_list"][3]["args_list"])
        self.assertEqual(len(m.live_buffs(soldier, 134243369)), 1)


class BCandidateBehavior(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.docs, cls.reports = repair.build(MAP)
        bad = [r for r in cls.reports if r["status"] == "review_required"]
        if bad: raise AssertionError(bad)

    def test_10_all_shield_levels_repeat_without_base_drift(self):
        for oid, resource in [(134278144, 134224490), (134232470, 134259960), (134256840, 134264323)]:
            d = self.docs[f"ability/{oid}.json"]
            for rank in range(1, 6):
                values = level_values(d, rank)
                for visible in range(4):
                    with self.subTest(oid=oid, rank=rank, visible=visible):
                        m = Model(values); core = m.buff(resource, stacks=visible + 1)
                        m.vars[("UNIT_ENTITY", "目标单位", "actor")] = m.owner
                        m.run(shield_actions(d))
                        factor = visible if oid == 134278144 else int(visible > 0)
                        extra = values.get("额外系数", 100)
                        self.assertEqual(m.live_buffs(m.owner, 134274812)[-1].shield, values["护盾值"] + factor * extra)
                        self.assertEqual(m.ability.values, values)
                        core.stacks = 1
                        m.run(shield_actions(d))
                        self.assertEqual(m.live_buffs(m.owner, 134274812)[-1].shield, values["护盾值"])
                        self.assertEqual(m.ability.values, values)
                        self.assertEqual(level_values(load(f"ability/{oid}.json"), rank), values)

    def test_11_absent_core_is_safe_and_local_shield_is_not_actor(self):
        for oid in [134278144, 134232470, 134256840]:
            d = self.docs[f"ability/{oid}.json"]
            m = Model(level_values(d, 1)); m.vars[("UNIT_ENTITY", "目标单位", "actor")] = m.owner
            m.run(shield_actions(d))
            self.assertEqual(m.live_buffs(m.owner, 134274812)[-1].shield, m.ability.values["护盾值"])
            self.assertIn(repair.SNAPSHOT, d["local_variable"]["893440004"]["variable_dict"]["FLOAT"])
            self.assertNotIn(repair.SNAPSHOT, d["variable_dict"].get("FLOAT", {}))

    def test_12_piercing_bonus_scales_with_attack_and_keeps_collision(self):
        oid = "ability/134280536.json"; d, old = self.docs[oid], load(oid)
        for rank in range(1, 6):
            values = level_values(d, rank)
            self.assertEqual(values["额外系数"], 0.4)
            self.assertEqual(values["伤害系数"], level_values(old, rank)["伤害系数"])
            b = find(cast(d), "SET_VARIABLE", 893440004974076)
            for attack in [1, 100, 777]:
                m = Model(values); m.owner.attack = attack; m.run([b])
                self.assertAlmostEqual(m.vars[("FLOAT", "最终伤害", "local")], attack * (values["伤害系数"] + 0.4))
        self.assertEqual(find(cast(d), "CREATE_STRAIGHT_MOVER"), find(cast(old), "CREATE_STRAIGHT_MOVER"))

    def test_13_sweep_once_for_up_to_three_and_no_target_preserves(self):
        d = self.docs["ability/134268037.json"]
        pick = find(cast(d), "PICK_UNIT_DO_ACTION")
        # Exercise the cost/damage/debuff stages, substituting only the external
        # knockback call, whose implementation is outside this builder's scope.
        exercise = deepcopy(pick)
        def drop_external(value):
            if isinstance(value, dict):
                for child in value.values(): drop_external(child)
            elif isinstance(value, list):
                value[:] = [x for x in value if not isinstance(x, dict) or x.get("action_type") != "CALL_TRIGGER_FUNC"]
                for x in value: drop_external(x)
        drop_external(exercise)
        init = [a for a in cast(d) if a.get("action_type") == "SET_VARIABLE"]
        for count in range(5):
            for visible in range(4):
                m = Model({"伤害系数": .5, "击退距离": 100, "数量": 3})
                core = m.buff(134224490, stacks=visible + 1)
                m.selection = [Entity(team=2) for _ in range(count)]
                m.run(init + [exercise])
                expected = min(count, 3)
                self.assertEqual(len(m.damage), expected)
                self.assertEqual(core.stacks, visible + 1 - int(visible > 0 and count > 0))
                self.assertEqual(len(m.costs), int(visible > 0 and count > 0))
                for victim, _ in m.damage:
                    self.assertEqual(len(m.live_buffs(victim, 134256265)), int(visible > 0))
        m = Model({"数量": 3}); core = m.buff(134224490, stacks=3)
        dead = Entity(); dead.alive = False; m.selection = [None, dead]
        m.run(init + [exercise]); self.assertEqual(core.stacks, 3)

    def test_14_courage_repeated_refresh_and_foreign_isolation(self):
        d = self.docs["ability/134233053.json"]
        actions = d["trigger_dict"]["58232837"]["action"]
        m = Model(); m.run(actions)
        for _ in range(3):
            for b in m.owner.buffs: b.remaining = 1
            m.run(actions)
            self.assertEqual([b.remaining for b in m.owner.buffs], [4, 4])
            self.assertEqual(len(m.owner.buffs), 2)
        foreign = Model()
        other = Entity("ability")
        for resource in [134254769, 134278792]: foreign.buff(resource, related=other).remaining = 9
        foreign.run(actions)
        self.assertEqual([b.remaining for b in foreign.owner.buffs], [9, 9])
        self.assertTrue(all(b.valid for b in foreign.owner.buffs))
        m.owner.valid = False; m.run(actions)

    def test_15_regen_snapshots_healing_not_damage(self):
        d = self.docs["modifier/134228469.json"]
        obtain = d["trigger_dict"]["1625518081"]["action"]
        for related in [True, False]:
            m = Model({"每次回血": 100, "每次伤害": 999})
            ally = Entity(hp=100, maximum=1000)
            m.modifier = m.buff(134228469, owner=ally)
            if not related: m.modifier.related = None
            m.run([a for a in obtain if a["action_type"] != "CREATE_SFX_ON_UNIT_3"])
            m.ability.values["每次回血"] = 500
            m.run(m.timers[0]); m.run(m.timers[0])
            self.assertEqual(ally.hp, 300 if related else 100)
        caller = load("ability/134221456.json")
        for rank in range(1, 6): self.assertEqual(level_values(caller, rank)["每次回血"], 100)
        add = find(caller["trigger_dict"]["58232837"]["action"], "ADD_MODIFIER", 58232837974346)
        self.assertTrue(add["op_arg_enable"][1])
        self.assertEqual(add["op_arg"][1]["sub_type"], "CUR_ABILITY")

    def test_16_ratio_selection_empty_zero_dead_ties_and_stale(self):
        for oid in sorted(repair.RATIO_FILES):
            d = self.docs[f"ability/{oid}.json"]
            tid = "58232837" if oid == 134221456 else "1959489540"
            pick = find(d["trigger_dict"][tid]["action"], "PICK_UNIT_DO_ACTION", 1959489540974145)
            a, b = Entity(hp=100, maximum=1000), Entity(hp=50, maximum=100)
            zero, dead = Entity(hp=0, maximum=0), Entity(hp=1, maximum=999)
            dead.alive = False
            m = Model(); m.selection = [None, zero, dead, a, b]
            stale = Entity(); stale.valid = False
            m.vars[("UNIT_ENTITY", "目标单位", "actor")] = stale
            m.run([pick])
            self.assertIs(m.vars[("UNIT_ENTITY", "目标单位", "actor")], a)
            tied = Entity(hp=10, maximum=100); m.selection = [tied]; m.run([pick])
            self.assertIs(m.vars[("UNIT_ENTITY", "目标单位", "actor")], a)
            self.assertEqual(pick["args_list"][0], find(load(f"ability/{oid}.json")["trigger_dict"][tid]["action"], "PICK_UNIT_DO_ACTION", 1959489540974145)["args_list"][0])
            clears = [x for x in nodes(d["trigger_dict"][tid]["action"]) if x.get("action_type") == "SET_VARIABLE" and
                      x["args_list"][1].get("sub_type") == "NONE_UNIT"]
            self.assertEqual(len(clears), 1)
            m.selection = []; m.run(clears + [pick])
            self.assertIsNone(m.vars[("UNIT_ENTITY", "目标单位", "actor")])

    def test_17_rescue_damage_only_on_arrival_current_target_and_validity(self):
        d = self.docs["ability/134275990.json"]
        mover = find(cast(d), "CREATE_STRAIGHT_MOVER")
        arrival = mover["args_list"][5]["args_list"]
        # Existing taunt is checked structurally; isolate the newly added damage
        # sequence to avoid pretending the engine's taunt/movement behavior.
        def damage_part(value):
            value = deepcopy(value)
            def prune(v):
                if isinstance(v, list):
                    v[:] = [x for x in v if not isinstance(x, dict) or x.get("action_type") not in ("ADD_MODIFIER", "ADD_BUFF_STACK", "UNIT_RELEASE_COMMAND")]
                    for x in v: prune(x)
                elif isinstance(v, dict):
                    for child in v.values(): prune(child)
            prune(value)
            return value
        for target_state in ["enemy", "missing", "dead", "friend", "invalid"]:
            m = Model({"伤害系数": 2.6}); ally = Entity(); enemy = Entity(team=2)
            ally.ai = enemy
            if target_state == "missing": ally.ai = None
            if target_state == "dead": enemy.alive = False
            if target_state == "friend": enemy.team = 1
            if target_state == "invalid": enemy.valid = False
            m.vars[("UNIT_ENTITY", "P2_early_rescue_ally", "local")] = ally
            self.assertEqual(m.damage, [])
            m.run(damage_part(arrival))
            self.assertEqual(m.damage, [(enemy, 260)] if target_state == "enemy" else [])
        m = Model({"伤害系数": 2.6}); ally = Entity(); new_enemy = Entity(team=2)
        m.vars[("UNIT_ENTITY", "P2_early_rescue_ally", "local")] = ally
        m.vars[("UNIT_ENTITY", "目标单位", "actor")] = Entity()
        ally.ai = new_enemy; m.run(damage_part(arrival))
        self.assertEqual(m.damage, [(new_enemy, 260)])
        for rank in range(1, 6):
            self.assertEqual(level_values(d, rank)["伤害系数"], 2.6)
            self.assertEqual(level_values(d, rank)["护盾值"], level_values(load("ability/134275990.json"), rank)["护盾值"])

    def test_18_archers_damage_reads_current_full_core_without_targeting(self):
        m, troop, buff = archers(self.docs)
        core = m.buff(134242511, stacks=1)
        for stacks in (1, 2, 3, 4, 3, 4, 1):
            core.stacks = stacks
            self.assertAlmostEqual(hit(m, buff), 118 if stacks == 4 else 100)
            self.assertEqual(m.attack_speed(troop), 15)
        core.valid = False
        self.assertEqual(hit(m, buff), 100)
        replacement = m.buff(134242511, stacks=4)
        self.assertAlmostEqual(hit(m, buff), 118)
        replacement.stackmax = 5
        self.assertEqual(hit(m, buff), 100)
        self.assertEqual(m.commands, [])
        self.assertEqual(m.damage, [])
        self.assertEqual(core.stacks, 1)
        self.assertEqual(m.live_buffs(troop, 134243369), [])

    def test_18b_archers_only_ranged_nonleaders_and_engine_percent_units(self):
        d = self.docs[repair.ARCHER]
        for rank in range(1, 6):
            self.assertEqual(level_values(d, rank), {"攻速提升": 15.0, repair.BONUS: 0.18})
        for tagset in ({"远程普攻"}, {"远程普攻", "仆从伙伴"}, {"远程普攻", "阵型队长"}, set()):
            m = Model(); m.support_doc = self.docs[repair.SUPPORT_ECA]
            troop = soldier(); troop.tags = tagset
            m.owner.values["带领小队"] = [None, troop, m.owner]
            m.invoke(d, repair.GAIN)
            self.assertEqual(m.attack_speed(troop), 15 if tagset == {"远程普攻"} else 0)
            self.assertEqual(m.attack_speed(m.owner), 0)
        for tagset in ({"仆从伙伴"}, {"阵型队长"}, {"仆从伙伴", "阵型队长"}, set()):
            m = Model(); m.owner.tags = tagset
            c = d["trigger_dict"][repair.GAIN]["condition"]
            self.assertEqual(all(m.condition(x) for x in c), bool(tagset))

    def test_18c_archers_target_and_normal_attack_event_matrix(self):
        for tags in (set(), {"远程普攻"}, {"仆从伙伴"}, {"阵型队长"}, {"仆从伙伴", "阵型队长"}):
            for team in (0, 1, 2):
                for cast_type in (1, 2, 3):
                    m, troop, buff = archers(self.docs); m.buff(134242511, stacks=4)
                    victim = soldier(team=team); victim.tags = tags
                    attack = Entity("ability"); attack.cast_type = cast_type
                    self.assertAlmostEqual(hit(m, buff, victim, attack=attack),
                        118 if team == 2 and cast_type == 1 and not tags.intersection({"仆从伙伴", "阵型队长"}) else 100)
        for missing in ("DAMAGE_SOURCE_UNIT", "DAMAGE_TARGET_UNIT", "DAMAGE_ABILITY"):
            m, troop, buff = archers(self.docs); m.buff(134242511, stacks=4)
            m.context = dict(DAMAGE_SOURCE_UNIT=troop, DAMAGE_TARGET_UNIT=soldier(team=2), DAMAGE_ABILITY=Entity("ability"))
            m.context[missing] = None
            m.invoke(m.support_doc, repair.SUPPORT_HURT, buff)
            self.assertEqual(m.current_damage, 100)
        m, troop, buff = archers(self.docs); m.buff(134242511, stacks=4)
        self.assertEqual(hit(m, buff, attacker=soldier()), 100)

    def test_18d_archers_original_source_rechecked_and_no_cross_player_leak(self):
        for state in ("source_invalid", "source_dead", "skill_invalid", "skill_reparented", "source_changed",
                      "related_changed", "departed", "leader", "melee", "hostile", "source_not_leader"):
            m, troop, buff = archers(self.docs); m.buff(134242511, stacks=4)
            foreign = Entity(team=2); foreign.values["带领小队"] = [troop]
            m.buff(134242511, foreign, stacks=4)
            if state == "source_invalid": m.owner.valid = False
            if state == "source_dead": m.owner.alive = False
            if state == "skill_invalid": m.ability.valid = False
            if state == "skill_reparented": m.ability.owner = foreign
            if state == "source_changed": buff.source = foreign
            if state == "related_changed": buff.related = Entity("ability")
            if state == "departed": m.owner.values["带领小队"] = []
            if state == "leader": troop.tags.add("仆从伙伴")
            if state == "melee": troop.tags.clear()
            if state == "hostile": troop.team = 2
            if state == "source_not_leader": m.owner.tags.clear()
            self.assertEqual(hit(m, buff), 100, state)
            self.assertFalse(buff.valid, state)
            self.assertEqual(buff.contributions, {})
            self.assertFalse(any(token[0] == id(buff) for token in m.registered))
        m, troop, buff = archers(self.docs)
        other = Entity(); other.values["带领小队"] = [troop]
        m.buff(134242511, other, stacks=4)
        self.assertEqual(hit(m, buff), 100)  # another Huang Zhong's core cannot authorize this instance

    def test_18e_archers_repeat_reinforcement_departure_loss_and_reobtain(self):
        d = self.docs[repair.ARCHER]
        m, troop, buff = archers(self.docs)
        refresh = find(d["trigger_dict"][repair.GAIN]["action"], "RUN_LOOP_TIMER")["args_list"][3]["args_list"]
        for _ in range(3): m.run(refresh)
        self.assertEqual(m.live_buffs(troop, repair.SUPPORT), [buff])
        self.assertEqual(m.attack_speed(troop), 15)
        recruit = soldier(); m.owner.values["带领小队"].append(recruit)
        m.run(refresh)
        self.assertEqual(m.attack_speed(recruit), 15)
        foreign_skill = Entity("ability"); foreign_skill.owner = Entity()
        foreign = m.buff(134254769, troop, foreign_skill); foreign.contributions["attack_speed"] = 7
        old = m.buff(134243369, troop)
        m.run(refresh)
        self.assertFalse(old.valid); self.assertTrue(foreign.valid)
        m.owner.values["带领小队"] = [recruit]
        timer = find(m.support_doc["trigger_dict"][repair.SUPPORT_GAIN], "RUN_LOOP_TIMER")
        m.support_callback(buff, timer["args_list"][3]["args_list"])
        self.assertFalse(buff.valid); self.assertEqual(m.attack_speed(troop), 7)
        m.ability.valid = False
        m.invoke(d, repair.LOSS)
        self.assertEqual(m.attack_speed(recruit), 0)
        self.assertFalse(m.registered); self.assertFalse(m.timer_handles)
        m.ability = Entity("ability"); m.ability.owner = m.owner
        m.owner.values["带领小队"] = [troop, recruit]
        m.invoke(d, repair.GAIN)
        self.assertEqual(m.attack_speed(troop), 22)
        self.assertEqual(m.attack_speed(recruit), 15)
        self.assertTrue(foreign.valid)

    def test_18f_rejected_gain_never_deletes_an_uncreated_timer_or_listener(self):
        for state in ("source_missing", "source_invalid", "skill_missing", "skill_invalid", "not_in_squad"):
            m = Model({"攻速提升": 15, repair.BONUS: .18})
            m.support_doc = self.docs[repair.SUPPORT_ECA]
            troop = soldier(); m.owner.values["带领小队"] = [troop]
            buff = m.buff(repair.SUPPORT, troop); buff.source = m.owner
            if state == "source_missing": buff.source = None
            if state == "source_invalid": m.owner.valid = False
            if state == "skill_missing": buff.related = None
            if state == "skill_invalid": m.ability.valid = False
            if state == "not_in_squad": m.owner.values["带领小队"] = []
            m.invoke(m.support_doc, repair.SUPPORT_GAIN, buff)
            self.assertFalse(buff.valid, state)
            self.assertEqual(m.timer_handles, set())
            self.assertEqual(m.registered, set())
            self.assertEqual(m.timers, [])
            self.assertFalse(buff.runtime[("BOOLEAN", repair.TIMER_LIVE, "actor")])
            self.assertFalse(buff.runtime[("BOOLEAN", repair.LISTENER_LIVE, "actor")])
            self.assertTrue(buff.runtime[("BOOLEAN", repair.LOSS_SEEN, "actor")])

    def test_18g_timer_callback_self_removal_clears_flags_before_deletion(self):
        m, troop, buff = archers(self.docs)
        self.assertTrue(buff.runtime[("BOOLEAN", repair.TIMER_LIVE, "actor")])
        timer = find(m.support_doc["trigger_dict"][repair.SUPPORT_GAIN], "RUN_LOOP_TIMER")
        m.owner.values["带领小队"] = []
        m.support_callback(buff, timer["args_list"][3]["args_list"])
        self.assertFalse(buff.valid)
        self.assertFalse(buff.runtime[("BOOLEAN", repair.TIMER_LIVE, "actor")])
        self.assertFalse(buff.runtime[("BOOLEAN", repair.LISTENER_LIVE, "actor")])
        self.assertEqual(m.attack_speed(troop), 0)
        # Only the ability's own timer/stage listener remain until ability loss.
        self.assertEqual(len(m.timer_handles), 1)
        self.assertEqual(len(m.registered), 1)
        m.invoke(self.docs[repair.ARCHER], repair.LOSS)
        self.assertFalse(m.timer_handles); self.assertFalse(m.registered)

    def test_18h_immediate_timer_callback_loss_before_handle_return_does_not_rearm(self):
        m = Model(); m.support_doc = self.docs[repair.SUPPORT_ECA]
        troop = soldier(); m.owner.values["带领小队"] = [troop]
        observed = []
        def start(model, actions):
            if model.modifier is None: return
            b = model.modifier
            observed.append(b)
            self.assertFalse(b.runtime[("BOOLEAN", repair.TIMER_LIVE, "actor")])
            model.owner.values["带领小队"] = []
            model.support_callback(b, actions)
        m.on_timer_start = start
        m.invoke(self.docs[repair.ARCHER], repair.GAIN)
        self.assertEqual(len(observed), 1)
        buff = observed[0]
        self.assertFalse(buff.valid)
        self.assertFalse(buff.runtime[("BOOLEAN", repair.TIMER_LIVE, "actor")])
        self.assertTrue(buff.runtime[("BOOLEAN", repair.LOSS_SEEN, "actor")])
        self.assertEqual(m.attack_speed(troop), 0)
        self.assertEqual(len(m.timer_handles), 1)
        m.invoke(self.docs[repair.ARCHER], repair.LOSS)
        self.assertFalse(m.timer_handles); self.assertFalse(m.registered)

    def test_19_rescue_start_finish_cost_and_disappearance(self):
        d = self.docs["ability/134275990.json"]
        start = cast(d)[-1]
        self.assertEqual(find(start, "CREATE_STRAIGHT_MOVER")["element_id"], 893440004974051)
        for state in ["valid", "missing_target", "dead_target", "allied_target", "hostile_ally", "missing_ally"]:
            m = Model(level_values(d, 1)); ally = Entity(); enemy = Entity(team=2)
            ally.ai = enemy
            if state == "missing_target": ally.ai = None
            if state == "dead_target": enemy.alive = False
            if state == "allied_target": enemy.team = 1
            if state == "hostile_ally": ally.team = 2
            m.vars[("UNIT_ENTITY", "P2_early_rescue_ally", "local")] = None if state == "missing_ally" else ally
            m.run([start])
            self.assertEqual(len(m.movements), int(state == "valid"))
            self.assertEqual(m.damage, [])
        for visible in [0, 1, 3]:
            m = Model(level_values(d, 1)); ally = Entity(); enemy = Entity(team=2); ally.ai = enemy
            core = m.buff(134246678, stacks=visible + 1)
            m.owner.values["能力循环机制"] = core
            m.vars[("UNIT_ENTITY", "P2_early_rescue_ally", "local")] = ally
            m.run([start]); self.assertEqual(core.stacks, visible + 1)
            m.run(m.movements[0])
            self.assertEqual(m.damage, [(enemy, 260)])
            self.assertEqual(core.stacks, visible + 1 - int(visible > 0))
            self.assertEqual(len(m.live_buffs(ally, 134274812)), int(visible > 0))
        # Source/recipient can vanish during movement or synchronously during damage.
        for boundary in ["source", "recipient", "during_damage"]:
            m = Model(level_values(d, 1)); ally = Entity(); ally.ai = Entity(team=2)
            m.vars[("UNIT_ENTITY", "P2_early_rescue_ally", "local")] = ally
            m.run([start])
            if boundary == "source": m.owner.valid = False
            if boundary == "recipient": ally.valid = False
            if boundary == "during_damage": m.on_damage = lambda _: setattr(ally, "valid", False)
            m.run(m.movements[0])
            self.assertEqual(len(m.damage), int(boundary == "during_damage"))
            self.assertEqual(ally.buffs, [])

    def test_19b_sweep_does_not_dereference_a_victim_killed_by_damage(self):
        d = self.docs["ability/134268037.json"]
        pick = find(cast(d), "PICK_UNIT_DO_ACTION")
        m = Model({"数量": 3, "伤害系数": .5})
        m.buff(134224490, stacks=2); victim = Entity(team=2); m.selection = [victim]
        m.on_damage = lambda _: setattr(victim, "valid", False)
        # The external knockback mock deliberately raises if it is reached.
        # A dead victim must be filtered before this unsupported dependency.
        m.run([pick])
        self.assertEqual(len(m.damage), 1)
        self.assertEqual(m.costs, [-1])
        self.assertEqual(victim.buffs, [])

    def test_19c_passive_loss_uses_saved_owner_and_only_own_instances(self):
        d = self.docs["ability/134233053.json"]
        m = Model()
        m.run(d["trigger_dict"]["1959489540"]["action"][:1])
        m.run(d["trigger_dict"]["58232837"]["action"])
        own = m.owner.buffs[:]
        foreign = m.buff(134254769, related=Entity("ability"))
        old_ability = m.ability; old_ability.valid = False
        # No GetAbilityOwner call on the now-invalid skill is allowed by Model.
        m.run(d["trigger_dict"]["225054724"]["action"][:2])
        self.assertTrue(all(not b.valid for b in own)); self.assertTrue(foreign.valid)
        foreign.valid = False
        m.ability = Entity("ability"); m.ability.owner = m.owner
        m.run(d["trigger_dict"]["1959489540"]["action"][:1])
        m.run(d["trigger_dict"]["58232837"]["action"])
        self.assertEqual(len(m.live_buffs(m.owner)), 2)
        self.assertTrue(all(b.related is m.ability for b in m.live_buffs(m.owner)))

    def test_19d_rescue_automatic_request_requires_allied_leader_current_enemy(self):
        d = self.docs["ability/134275990.json"]
        source = d["trigger_dict"]["1959489540"]["action"]
        gates = [x for x in nodes(source) if x.get("action_type") == "IF_THEN_ELSE" and
                 len(x["args_list"][0]["args_list"]) == 1 and
                 x["args_list"][0]["args_list"][0].get("condition_type") == "TYPE_IS_EXIST" and
                 x["args_list"][0]["args_list"][0]["args_list"][0] == repair.target() and
                 any(y.get("element_id") == 1959489540974075 for y in nodes(x))]
        self.assertEqual(len(gates), 1)
        gate = deepcopy(gates[0])
        def remove_debug(v):
            if isinstance(v, list):
                v[:] = [x for x in v if not isinstance(x, dict) or x.get("action_type") != "DISPLAY_INFO_TO_PLAYER"]
                for x in v: remove_debug(x)
            elif isinstance(v, dict):
                for x in v.values(): remove_debug(x)
        remove_debug(gate)
        for state in ["valid", "none", "no_enemy", "dead_enemy", "invalid_enemy", "friendly_enemy", "hostile_leader"]:
            m = Model(); leader = Entity(); enemy = Entity(team=2); leader.ai = enemy
            if state == "no_enemy": leader.ai = None
            if state == "dead_enemy": enemy.alive = False
            if state == "invalid_enemy": enemy.valid = False
            if state == "friendly_enemy": enemy.team = 1
            if state == "hostile_leader": leader.team = 2
            m.vars[("UNIT_ENTITY", "目标单位", "actor")] = None if state == "none" else leader
            m.run([gate])
            self.assertEqual(len(m.commands), int(state == "valid"))
            self.assertEqual(m.damage, [])


class CBuilderContract(unittest.TestCase):
    def test_20_build_reads_passed_root_fresh_and_preserves_p1(self):
        memory = {name: (MAP / name).read_bytes() for name in repair.SOURCE_FILES}
        requested = []
        root = Path("D:/read-only-in-memory-root")
        def read(path):
            requested.append(path)
            return memory[path.relative_to(root).as_posix()]
        with patch.object(Path, "read_bytes", read):
            before, reports = repair.build(root)
            relative = "ability/134280536.json"
            current = json.loads(memory[relative])
            mover = find(cast(current), "CREATE_STRAIGHT_MOVER")
            for x in nodes(mover["args_list"][9]):
                if x.get("arg_type") == 100006 and x.get("sub_type") == 11:
                    x["sub_type"], x["args_list"] = "MOVER_COLLIDE_UNIT", []
            current["p1_sentinel"] = 99123456789012345678901234567
            memory[relative] = json.dumps(current).encode()
            after, reports = repair.build(root)
            self.assertNotEqual(before[relative], after[relative])
            self.assertEqual(find(cast(after[relative]), "CREATE_STRAIGHT_MOVER"), mover)
            self.assertEqual(after[relative]["p1_sentinel"], 99123456789012345678901234567)
            self.assertEqual(next(r for r in reports if r.get("path") == relative)["source_sha256"], hashlib.sha256(memory[relative]).hexdigest())
        self.assertEqual(set(after), set(repair.PAYLOAD_FILES))
        self.assertTrue(all(p.is_relative_to(root) for p in requested))
        self.assertEqual(len(requested), len(repair.SOURCE_FILES) * 2)

    def test_21_ast_drift_is_reported_not_patched(self):
        relative = "ability/134280536.json"
        original_read = Path.read_bytes
        def read(path):
            if path.as_posix().endswith(relative):
                d = json.loads(original_read(path))
                find(cast(d), "SET_VARIABLE", 893440004974076)["args_list"][1]["args_list"][1]["args_list"] = ["/"]
                return json.dumps(d).encode()
            return original_read(path)
        with patch.object(Path, "read_bytes", read):
            c, reports = repair.build(MAP)
        self.assertNotIn(relative, c)
        self.assertEqual(next(r for r in reports if r.get("path") == relative)["status"], "review_required")

    def test_22_unknown_native_calls_and_bad_literals_are_rejected(self):
        m = Model()
        with self.assertRaises(NotImplementedError): m.expr({"arg_type": 100076, "sub_type": "MAGIC_NATIVE", "args_list": []})
        with self.assertRaises(NotImplementedError): m.run([{"action_type": "UNKNOWN_NATIVE", "args_list": []}])
        with self.assertRaises(NotImplementedError):
            m.condition({"condition_type": "TYPE_IS_EXIST", "args_list": [{"arg_type": 100076, "sub_type": "CUR_MODIFIER", "args_list": []}]})
        with self.assertRaises(AssertionError): m.expr({"arg_type": 100011, "sub_type": 1, "args_list": [{"sub_type": "GET_TABLE_KV"}]})

    def test_23_json_exact_ids_input_unchanged_and_only_allowed_paths(self):
        hashes = {name: hashlib.sha256((MAP / name).read_bytes()).hexdigest() for name in repair.SOURCE_FILES}
        c, _ = repair.build(MAP)
        self.assertEqual(set(c), set(repair.PAYLOAD_FILES))
        for name, d in c.items():
            self.assertEqual(json.loads(json.dumps(d)), d)
        for name, digest in hashes.items():
            self.assertEqual(hashlib.sha256((MAP / name).read_bytes()).hexdigest(), digest)

    def test_24_published_p1_scope_resource_collision_are_preserved(self):
        c, reports = repair.build(MAP)
        for oid in repair.RATIO_FILES - {134221456}:
            doc = c[f"ability/{oid}.json"]
            reads = [x for x in nodes(doc["trigger_dict"]["1959489540"]["action"])
                     if x.get("arg_type") == 100006 and x.get("sub_type") == 11 and
                     isinstance(x.get("args_list", [None])[0], dict) and
                     x["args_list"][0].get("items", [])[:2] == ["UNIT_ENTITY", "目标单位"]]
            self.assertTrue(reads)
            self.assertTrue(all(x["args_list"][0]["items"][2] == "actor" for x in reads))
        path = "ability/134266460.json"
        current = load(path); clear = find(cast(current), "ADD_BUFF_STACK")
        resources = [x["args_list"][1]["args_list"][0] for x in nodes(clear) if x.get("sub_type") == "GET_LAST_MODIFIER_INSTANCE"]
        self.assertTrue(resources); self.assertEqual(set(resources), {134242511})
        self.assertEqual(find(cast(c[path]), "ADD_BUFF_STACK"), clear)
        path = "ability/134280536.json"
        current_mover = find(cast(load(path)), "CREATE_STRAIGHT_MOVER")
        self.assertEqual(find(cast(c[path]), "CREATE_STRAIGHT_MOVER"), current_mover)
        self.assertEqual(sum(x.get("sub_type") == "MOVER_COLLIDE_UNIT" for x in nodes(current_mover["args_list"][9])), 4)
        self.assertEqual(sum(r["status"] == "candidate" for r in reports), 18)

    def test_25_new_ids_registration_and_unresolved_dependency_are_explicit(self):
        c, reports = repair.build(MAP)
        for path, d in c.items():
            old = load(path) if path not in (repair.SUPPORT_ECA, repair.SUPPORT_PROP) else {}
            oldids = {x["element_id"] for x in repair.walk(old) if "element_id" in x}
            counts = Counter(x["element_id"] for x in repair.walk(d) if "element_id" in x)
            self.assertEqual({k: v for k, v in counts.items() if k not in oldids and v > 1}, {})
        d = c[repair.SUPPORT_ECA]; tid = repair.SUPPORT_HURT
        t = d["trigger_dict"][tid]
        self.assertTrue(t["is_conf"]); self.assertFalse(t["enabled"])
        self.assertEqual(t["p_trigger_id"], int(repair.SUPPORT_GAIN))
        self.assertEqual(t["event"][0]["event_type"], "SPECIAL_UNIT_EVENT")
        self.assertEqual(t["sub_trigger_owner_set_var_action"]["args_list"][1]["sub_type"], "REG_MODIFIER_TRIGGER")
        self.assertEqual(t["sub_trigger_owner_set_var_action"]["args_list"][1]["args_list"][0]["args_list"], [int(tid)])
        self.assertEqual(d["local_variable"][tid]["variable_dict"], t["var_data"][0])
        report = next(r for r in reports if r.get("path") == "ability/134236877.json")
        self.assertEqual(report["issues"], [38]); self.assertTrue(report["atomic_bundle"])
        self.assertEqual(report["completion"], "conditional_damage_candidate")
        self.assertNotIn("加攻系数", c[repair.ARCHER_PROP]["kv"])

    def test_26_duplicate_json_keys_are_not_silently_accepted(self):
        original_read = Path.read_bytes
        def read(path):
            return b'{"x":1,"x":2}' if path.name == "134278144.json" else original_read(path)
        with patch.object(Path, "read_bytes", read): c, reports = repair.build(MAP)
        self.assertNotIn("ability/134278144.json", c)
        report = next(r for r in reports if r.get("path") == "ability/134278144.json")
        self.assertEqual(report["status"], "review_required")
        self.assertIn("duplicate JSON key", report["explanation"])

    def test_27_support_registration_metadata_and_unrelated_entries_preserved(self):
        c, reports = repair.build(MAP)
        prop = c[repair.SUPPORT_PROP]
        self.assertEqual((prop["key"], prop["_ref_"], prop["uid"]), (repair.SUPPORT, repair.SUPPORT, str(repair.SUPPORT)))
        self.assertEqual((prop["name"], prop["desc"], prop["description"]),
                         (repair.NAME_TID, repair.DESC_TID, repair.DESC_TID))
        old_folder = load(repair.FOLDERS)
        new_folder = deepcopy(c[repair.FOLDERS])
        added = new_folder["d"].pop(str(repair.SUPPORT))
        self.assertEqual(new_folder, old_folder)
        self.assertEqual(added["items"][0], old_folder["d"]["134242511"]["items"][0])
        for path in (repair.LANG, repair.TIDS):
            new = deepcopy(c[path])
            for tid in (repair.NAME_TID, repair.DESC_TID): new.pop(str(tid))
            if path == repair.LANG:
                desc = str(c[repair.ARCHER_PROP]["desc"])
                self.assertIn("+15%", new[desc]); self.assertIn("+18%", new[desc])
                new[desc] = load(path)[desc]
            self.assertEqual(new, load(path))
        for tid in (repair.NAME_TID, repair.DESC_TID):
            self.assertEqual(c[repair.TIDS][str(tid)]["item_key"], repair.SUPPORT)
        for relative in (repair.SUPPORT_ECA, repair.ARCHER):
            doc = c[relative]
            self.assertFalse(any(x.get("action_type") in ("APPLY_DAMAGE", "UNIT_RELEASE_COMMAND") for x in nodes(doc)))
            for tid, t in doc["trigger_dict"].items():
                self.assertTrue(t["valid"])
                self.assertEqual(doc["local_variable"][tid]["variable_dict"], t["var_data"][0])
        for key in (repair.TIMER_LIVE, repair.LISTENER_LIVE, repair.LOSS_SEEN):
            self.assertIs(c[repair.SUPPORT_ECA]["variable_dict"]["BOOLEAN"][key], False)
        saved = [x for x in nodes(c[repair.SUPPORT_ECA]) if x.get("arg_type") == 100014 and
                 x.get("sub_type") == 2 and x["args_list"][0].get("items", [None])[0] == "ABILITY"]
        self.assertTrue(saved)  # native ABILITY actor reads use subtype 2
        additions = [r["path"] for r in reports if r.get("operation") == "add"]
        self.assertEqual(set(additions), {repair.SUPPORT_ECA, repair.SUPPORT_PROP})

    def test_28_support_collisions_and_drift_reject_the_entire_bundle(self):
        original_read, original_exists = Path.read_bytes, Path.exists
        cases = [(repair.LANG, str(repair.NAME_TID)), (repair.TIDS, str(repair.DESC_TID)),
                 (repair.FOLDERS, str(repair.SUPPORT)), ("editor_table/modifierall/134242511.json", "layer_max")]
        for relative, key in cases:
            def read(path):
                raw = original_read(path)
                if path == MAP / relative:
                    doc = json.loads(raw)
                    if relative == repair.FOLDERS: doc["d"][key] = {"__tuple__": True, "items": ["reserved", 0]}
                    else: doc[key] = 5 if key == "layer_max" else "reserved"
                    return json.dumps(doc).encode()
                return raw
            with patch.object(Path, "read_bytes", read): c, reports = repair.build(MAP)
            self.assertEqual(set(c), set(repair.FILES) - {repair.ARCHER})
            rejected = [r for r in reports if r["status"] == "review_required"]
            self.assertEqual(len(rejected), 1)
            self.assertTrue(rejected[0]["atomic_bundle"])
        for relative in (repair.SUPPORT_ECA, repair.SUPPORT_PROP):
            with patch.object(Path, "exists", lambda p: p == MAP / relative or original_exists(p)):
                c, reports = repair.build(MAP)
            self.assertEqual(set(c), set(repair.FILES) - {repair.ARCHER})
            self.assertIn("collision", next(r for r in reports if r["status"] == "review_required")["explanation"])

    def test_29_damage_event_operands_and_uncreated_timer_are_not_fabricated(self):
        m = Model()
        with self.assertRaises(AssertionError): m.expr(repair.ex(100014, "DAMAGE_ABILITY"))
        with self.assertRaises(AssertionError):
            m.run([{"action_type": "DELETE_TIMER", "args_list": [repair.lit(-1)]}])


if __name__ == "__main__":
    unittest.main()

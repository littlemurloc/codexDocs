"""Native-AST regressions; read-only input, no engine/event-order simulation.

Y3_P2_MIDDLE_ROOT can point to a pre-P2 map3 snapshot. Arithmetic and instruction
arguments are projected independently of the generator. Geometry, projectile
timing, modifier cover/refresh and engine event delivery are NOT implemented.
Unsupported operations fail instead of acquiring invented engine semantics.
"""

from collections import Counter
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import unittest
from unittest.mock import patch

from tools import y3_hero_repair_p2_middle as m

ROOT = Path(os.environ.get("Y3_P2_MIDDLE_ROOT", "D:/littl/testTempFile/ProjectMonster02/maps/map3"))


def nodes(x):
    if isinstance(x, dict):
        yield x
        for v in x.values(): yield from nodes(v)
    elif isinstance(x, list):
        for v in x: yield from nodes(v)


def find(tree, kind, eid=None):
    result = [n for n in nodes(tree) if n.get("action_type") == kind
              and (eid is None or n.get("element_id") == eid)]
    if len(result) != 1: raise AssertionError((kind, eid, len(result)))
    return result[0]


def body(doc, tid="893440004"):
    return doc["trigger_dict"][tid]["action"]


class Projection:
    def __init__(self):
        self.vars = {}
        self.units = {"owner": {"alive": True, "tags": {"仆从伙伴"}, "enemy": False}}
        self.groups = {"owner": []}
        self.abilities = {"ability": {"class": 134230908, "kv": {
            "伤害系数": 1.2, "伤害提高": 0.95, "时长": 5.0,
            "P2_normal_shots": 3, "P2_enhanced_shots": 5,
            "P2_yingshi_enhanced_ratio": 0.18}}}
        self.mods = {"current": {"class": 134266933, "source": "owner", "ability": "ability", "kv": {}}}
        self.stacks = {}
        self.core_max = 4
        self.selected = None
        self.normal = True
        self.damage_target = "enemy"
        self.damage_source = "owner"
        self.current = "current"
        self.event_buff = "event-buff"
        self.remaining = 10.0
        self.attack = 100.0
        self.actor_target = "primary"
        self.ability_target = "primary"
        self.query = []
        self.damage = []
        self.grants = []
        self.clears = []
        self.timer_counts = []
        self.contributions = []
        self.buff_duration_changes = []
        self.after_damage = None
        self.after_grant = None
        self.returned_modifier = "returned"  # Explicit test input, not a cover-rule simulation.

    @staticmethod
    def var(raw):
        if isinstance(raw, dict):
            if raw.get("__tuple__") is not True: raise AssertionError("not a tuple")
            raw = raw["items"]
        return tuple(raw)

    def exists(self, handle):
        return handle in self.units or handle in self.abilities or handle in self.mods or handle in self.stacks

    def e(self, x):
        if not isinstance(x, dict): raise AssertionError("expression must be native dict")
        s, a = x["sub_type"], x["args_list"]
        if s == 1:
            if len(a) != 1 or isinstance(a[0], (dict, list)): raise AssertionError("non-primitive literal")
            return a[0]
        if s in (2, 6, 11, 14, "VARIABLE"):
            key = self.var(a[0])
            if key == ("UNIT_ENTITY", "目标单位", "actor"): return self.actor_target
            return self.vars[key]
        if s == "ABILITY_OWNER" or s == "MODIFIER_OWNER": return "owner"
        if s == "CUR_ABILITY": return "ability"
        if s == "CUR_MODIFIER": return self.current
        if s == "DAMAGE_TARGET_UNIT": return self.damage_target
        if s == "DAMAGE_SOURCE_UNIT": return self.damage_source
        if s == "TARGET_UNIT_IN_ABILITY":
            if self.e(a[0]) != "ability": raise AssertionError("unexpected target ability")
            return self.ability_target
        if s == "FOR_EACH_SELECTED_UNIT": return self.selected
        if s == "HURT_DAMAGE": return 100.0
        if s == "GET_MODIFIER_FROM_EVENT": return self.event_buff
        if s == "MODIFIER_RELEASER": return self.mods[self.current]["source"]
        if s == "GET_BUFF_SOURCE": return self.mods[self.e(a[0])]["source"]
        if s == "RELATED_ABILITY_MODIFIER": return self.mods[self.e(a[0])]["ability"]
        if s == "ABILITY_NAME_OF_ABILITY": return self.abilities[self.e(a[0])]["class"]
        if s in ("GET_FLOAT_KV", "GET_INTEGER_KV", "GET_BOOLEAN_KV"):
            entity, key = (self.e(v) for v in a)
            record = self.abilities.get(entity, self.mods.get(entity))
            if record is None: raise AssertionError("KV read from invalid entity")
            return record["kv"][key]
        if s == "GET_LAST_MODIFIER_INSTANCE":
            if self.e(a[0]) != "owner": raise AssertionError("unexpected core owner")
            return ("core", self.e(a[1]))
        if s == "GET_MOD_STACK":
            handle = self.e(a[0])
            if handle not in self.stacks: raise AssertionError("missing core dereference")
            return self.stacks[handle]
        if s == "GET_MOD_STACK_MAX":
            if self.e(a[0]) not in self.stacks: raise AssertionError("missing core dereference")
            return self.core_max
        if s == "GET_BUFF_REMAINING":
            if not self.exists(self.e(a[0])): raise AssertionError("missing event Buff")
            return self.remaining
        if s == "GET_UNIT_ATTR":
            u, result, attr = (self.e(v) for v in a)
            if u != "owner" or result != "ATTR_RESULT" or attr != "attack_phy": raise AssertionError((u,result,attr))
            return self.attack
        if s == "GET_UNIT_GROUP_KV":
            u, key = (self.e(v) for v in a)
            if key != "带领小队": raise AssertionError(key)
            return self.groups[u]
        if s == "UNIT_HAS_TAG":
            u, tag = (self.e(v) for v in a)
            return tag in self.units[u]["tags"]
        if s == "INT_PLUS_ONE": return self.e(a[0]) + 1
        if s == "I2F":
            v = self.e(a[0])
            if type(v) is not int: raise AssertionError("I2F on noninteger")
            return float(v)
        if s in ("ARITHMETIC_OPERATION", "MATH_OPERATION"):
            left, op, right = (self.e(v) for v in a)
            if type(left) not in (int,float) or type(right) not in (int,float): raise AssertionError("non-numeric arithmetic")
            if op == "+": return left + right
            if op == "-": return left - right
            if op == "*": return left * right
            if op == "/": return left / right
            raise AssertionError(op)
        if s == "UNIT_LIST_IN_SHAPE":
            # Input sequence is supplied by each test. Only reviewed cap slot 12
            # is projected; geometry/remaining filter flags are checked as AST.
            values = list(self.query)
            if x["op_arg_enable"][12]: values = values[:self.e(x["op_arg"][12])]
            return values
        if s == "ADD_MODIFIER":
            self.record_grant(x)
            return self.returned_modifier
        raise AssertionError(f"unsupported expression {s}")

    def record_grant(self, node):
        # Reject unsafe instructions in the test contract; this does not model
        # what error/result the engine would produce for a dead/removed unit.
        args = node["args_list"]
        target = self.e(args[0])
        if target not in self.units or not self.units[target]["alive"]:
            raise AssertionError("ADD_MODIFIER attempted on invalid/dead target")
        self.grants.append((target, self.e(args[1]),
                            [self.e(v) if en else None for v,en in zip(node.get("op_arg",[]),node.get("op_arg_enable",[]))]))
        if self.after_grant: self.after_grant(self)

    def c(self, x):
        kind, a = x["condition_type"], x["args_list"]
        if kind == "TYPE_IS_EXIST": return self.exists(self.e(a[0]))
        if kind in ("FLOAT_COMPARE", "UNIT_COMPARE", "ABILITY_COMPARE", "ABILITY_ENTITY_COMPARE", "BOOL_COMPARE"):
            left, op, right = (self.e(v) for v in a)
            if op == "==": return left == right
            if op == "!=": return left != right
            if op == ">": return left > right
            if op == ">=": return left >= right
            if op == "<": return left < right
            raise AssertionError(op)
        if kind == "GET_IS_NORMAL_HIT_FROM_EVENT": return self.normal
        if kind == "IS_UNIT_ALIVE": return self.units[self.e(a[0])]["alive"]
        if kind == "IS_ENEMY":
            u, other = (self.e(v) for v in a)
            return self.units[u]["enemy"] != self.units[other]["enemy"]
        if kind == "UNIT_HAS_TAG":
            u, tag = (self.e(v) for v in a)
            return tag in self.units[u]["tags"]
        if kind == "BOOL_NOT":
            result = self.e(a[0])
            if type(result) is not bool: raise AssertionError("BOOL_NOT on nonboolean")
            return not result
        if kind in ("OR", "AND"):
            results = [self.c(v) for v in a[0]["args_list"] if v.get("enable") is not False]
            return any(results) if kind == "OR" else all(results)
        raise AssertionError(f"unsupported condition {kind}")

    def run(self, actions):
        for n in actions:
            if isinstance(n, int): raise AssertionError("dynamic registration is structural, not engine simulation")
            if n.get("enable") is False: continue
            kind, a = n["action_type"], n["args_list"]
            if kind == "IF_THEN_ELSE":
                conditions = [self.c(c) for c in a[0]["args_list"] if c.get("enable") is not False]
                self.run(a[1 if all(conditions) else 2]["args_list"])
            elif kind == "SET_VARIABLE": self.vars[self.var(a[0]["args_list"][0])] = self.e(a[1])
            elif kind == "SET_ENTITY_KV":
                entity,key,val = (self.e(v) for v in a)
                record = self.abilities.get(entity,self.mods.get(entity))
                if record is None: raise AssertionError("write invalid entity")
                record["kv"][key] = val
            elif kind == "PICK_UNIT_DO_ACTION":
                old = self.selected
                for unit in list(self.e(a[0])):
                    self.selected = unit
                    self.run(a[1]["args_list"])
                self.selected = old
            elif kind == "ADD_MODIFIER":
                self.record_grant(n)
            elif kind == "ADD_BUFF_STACK":
                handle, delta = (self.e(v) for v in a)
                if not self.exists(handle): raise AssertionError("missing modifier")
                self.stacks[handle] += delta
            elif kind == "SET_BUFF_STACK":
                handle, val = (self.e(v) for v in a)
                if handle not in self.stacks: raise AssertionError("missing core")
                self.stacks[handle] = val
                self.clears.append(handle)
            elif kind == "ADD_BUFF_REMAINING":
                self.buff_duration_changes.append(self.e(a[1]))
            elif kind == "RUN_COUNT_TIMER_NO_SAVE":
                self.timer_counts.append(tuple(self.e(v) for v in a[:3]))
            elif kind == "ADD_MODIFIER_OWNER_ATTR":
                self.contributions.append(tuple(self.e(v) for v in a))
            elif kind == "APPLY_DAMAGE":
                self.damage.append((self.e(a[2]), self.e(a[4])))
                if self.after_damage: self.after_damage(self)
            elif kind in ("CREATE_SFX_ON_UNIT_3", "CREATE_SFX_ON_POINT", "CREATE_SFX_ON_POINT_NEW", "UNIT_RELEASE_COMMAND", "PROJECTILE_DELETE"):
                pass  # Explicitly excluded visual/cleanup commands; never fake effects.
            else: raise AssertionError(f"unsupported action {kind}")


class ConditionalProjection(Projection):
    """Strict operand projection, not a modifier-cover or event-order engine."""
    def __init__(self, aid=134263656, mid=m.TARGET_SUPPORT):
        super().__init__()
        self.abilities["ability"].update(owner="owner", type=3)
        self.abilities["ability"]["class"] = aid
        self.abilities["ability"]["kv"].update({"加攻系数": .25 if aid in (134236412, 134263656) else 15.0,
            m.CONDITIONAL_ACTIVE: True})
        self.units.update({"soldier": {"alive": True, "tags": {"刀兵"}, "enemy": False, "kv": {"所属英雄": "owner"}},
                           "target": {"alive": True, "tags": {"阵型队长"}, "enemy": True, "kv": {}},
                           "other": {"alive": True, "tags": {"仆从伙伴"}, "enemy": True, "kv": {}}})
        self.mods["current"].update(owner="owner" if mid == m.SOURCE_SUPPORT else "target")
        self.mods["current"]["class"] = mid
        self.mods["current"]["kv"].update({m.CONDITIONAL_READY: True, m.CONDITIONAL_RATIO: .25,
            m.CONDITIONAL_TARGET: "target", m.CONDITIONAL_CORE: ("core", 134232832)})
        self.stacks[("core", 134232832)] = 4
        self.damage_source, self.damage_target = "soldier", "target"
        self.current_damage = 100.0
        self.layer_change = -3
        self.modifier_writes = []
        self.unregistered = []
        self.removed = []
        self.selected_modifier = None

    def record(self, handle):
        for records in (self.units, self.abilities, self.mods):
            if handle in records: return records[handle]
        raise AssertionError(f"invalid KV entity {handle}")

    def e(self, x):
        s, a = x["sub_type"], x["args_list"]
        if s in ("GET_UNIT_ENTITY_KV", "GET_MODIFIER_ENTITY_KV", "GET_FLOAT_KV", "GET_BOOLEAN_KV"):
            entity, key = (self.e(v) for v in a)
            record = self.record(entity)
            if key not in record.get("kv", {}): raise AssertionError(f"unguarded absent KV {key}")
            return record["kv"][key]
        if s == "GET_ABILITY_OWNER": return self.abilities[self.e(a[0])]["owner"]
        if s == "MODIFIER_OWNER": return self.mods[self.current]["owner"]
        if s == "FOR_EACH_SELECTED_MODIFIER": return self.selected_modifier
        if s == "GET_MODIFIER_ENTITY_METATYPE": return self.mods[self.e(a[0])]["class"]
        if s == "DAMAGE_ABILITY": return "damage-ability" if "damage-ability" in self.abilities else None
        if s == "TYPE_OF_ABILITY": return self.abilities[self.e(a[0])]["type"]
        if s == "GET_MODIFIER_LAYER_CHANGE_VALUE": return self.layer_change
        if s == "GET_ABILITY_TARGET_UNIT_FROM_EVENT": return self.ability_target
        if s == "HURT_DAMAGE": return self.current_damage
        if s == "VARIABLE":
            key = self.var(a[0])
            if key[0] == "DYNAMIC_TRIGGER_INSTANCE": return self.vars[key]
        return super().e(x)

    def c(self, x):
        kind, a = x["condition_type"], x["args_list"]
        if kind == "HAS_KV_ANY":
            entity, key = (self.e(v) for v in a)
            return key in self.record(entity).get("kv", {})
        if kind in ("MODIFIER_COMPARE", "ABILITY_TYPE_COMPARE", "MODIFIER_CLASS_COMPARE"):
            return super().c(dict(x, condition_type="UNIT_COMPARE"))
        return super().c(x)

    def run(self, actions):
        for n in actions:
            if isinstance(n, int): raise AssertionError("registration is structural only")
            if n.get("enable") is False: continue
            kind, a = n["action_type"], n["args_list"]
            if kind == "SET_CUR_DAMAGE": self.current_damage = self.e(a[0])
            elif kind == "SET_ENTITY_KV":
                entity, key, val = (self.e(v) for v in a)
                self.record(entity).setdefault("kv", {})[key] = val
                self.modifier_writes.append((entity, key, val))
            elif kind == "UNREG_TRIGGER": self.unregistered.append(self.e(a[0]))
            elif kind == "REMOVE_BUFF_INS":
                handle = self.e(a[0]); self.removed.append(handle); self.mods.pop(handle)
            elif kind == "ITER_MODIFIER_DO":
                owner = self.e(a[0])
                old = self.selected_modifier
                for handle, record in list(self.mods.items()):
                    if record.get("owner") == owner:
                        self.selected_modifier = handle
                        self.run(a[1]["args_list"])
                self.selected_modifier = old
            elif kind == "PRINT_MESSAGE_ACTION_TO_DIALOG": pass
            else: super().run([n])


@unittest.skipUnless((ROOT/'ability/134235613.json').is_file(), "requires original map3 or Y3_P2_MIDDLE_ROOT")
class MiddleRegression(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.new, cls.reports = m.build(ROOT)
        paths = {p for r in cls.reports for p, sha in r.get("source_sha256", {}).items() if sha is not None}
        paths |= {"ability/134236412.json", "ability/134263656.json"}
        cls.raw = {p: (ROOT/p).read_bytes() for p in paths}
        cls.originals = {p: json.loads(raw) for p,raw in cls.raw.items()}

    def old(self, number, kind="ability"):
        return deepcopy(self.originals[f"{kind}/{number}.json"])

    def newdoc(self, number, kind="ability"):
        return deepcopy(self.new[f"{kind}/{number}.json"])

    def rebuild(self, changes):
        original_read = Path.read_bytes
        data = {str((ROOT/p).resolve()): json.dumps(d).encode() for p,d in changes.items()}
        def read(path): return data.get(str(path.resolve()), None) or original_read(path)
        with patch.object(Path, "read_bytes", read): return m.build(ROOT)

    def test_01_build_complete_for_scoped_items_including_real_conditionals(self):
        self.assertEqual(len(self.new),26,self.reports)
        self.assertTrue(all(r["status"]=="candidate" for r in self.reports),self.reports)
        conditional = next(r for r in self.reports if r["issue"]=="15")
        self.assertEqual(conditional["allocatedID"],[134299015,134299016])
        self.assertIn("not approved design removal",conditional["elite_scope"])

    def test_02_build_did_not_write_live_and_payload_is_json_serializable(self):
        for p,raw in self.raw.items(): self.assertEqual((ROOT/p).read_bytes(),raw,p)
        for r in self.reports:
            for p,sha in r.get("source_sha256",{}).items():
                if sha is None: self.assertFalse((ROOT/p).exists())
                else: self.assertEqual(hashlib.sha256(self.raw[p]).hexdigest(),sha)
        for doc in self.new.values(): json.dumps(doc,allow_nan=False)

    def test_03_latest_root_hand_edits_are_reread_and_p1_formulas_survive(self):
        d = self.old(134273095)
        d["P1_manual_unknown"] = {"id":340282366920938463463374607431768211455}
        formula = find(body(d),"SET_VARIABLE",893440004975675)["args_list"][1]
        formula["P1_formula_annotation"] = "retain"
        formula["args_list"][2] = {"arg_type":100000,"sub_type":1,"args_list":[1.33]}
        n,reports = self.rebuild({"ability/134273095.json":d})
        self.assertIn("ability/134273095.json",n,reports)
        self.assertEqual(n["ability/134273095.json"]["P1_manual_unknown"],d["P1_manual_unknown"])
        self.assertEqual(find(body(n["ability/134273095.json"]),"SET_VARIABLE",893440004975675)["args_list"][1],formula)

    def test_04_original_ids_preserved_no_new_per_file_collisions(self):
        for p,doc in self.new.items():
            before=Counter(n["element_id"] for n in nodes(self.originals.get(p,{})) if "element_id" in n)
            after=Counter(n["element_id"] for n in nodes(doc) if "element_id" in n)
            if p not in {f"ability/{i}.json" for i in m.CONDITIONAL_IDS}: self.assertFalse(before-after,p)
            self.assertTrue(all(count==1 for count in (after-before).values()),p)

    def test_05_new_ifs_are_explicit_native_format(self):
        for p,doc in self.new.items():
            before={n.get("element_id") for n in nodes(self.originals.get(p,{}))}
            for n in nodes(doc):
                if n.get("action_type")=="IF_THEN_ELSE" and n["element_id"] not in before:
                    self.assertEqual(n["fake_op"],[])

    def test_06_eighteen_old_owner_repeated_new_only_legal_melee_soldiers(self):
        for aid in (134259902,134226331,134237178):
            oldpick=find(body(self.old(aid),"1051000836"),"PICK_UNIT_DO_ACTION")
            recipient_phase = self.old(aid)
            m.repair_recipients(recipient_phase)
            newpick=find(body(recipient_phase,"1051000836"),"PICK_UNIT_DO_ACTION")
            p=Projection()
            p.units.update({"sword":{"alive":True,"tags":{"刀兵"},"enemy":False},
                            "bow":{"alive":True,"tags":{"弓兵"},"enemy":False},
                            "dead":{"alive":False,"tags":{"枪兵"},"enemy":False},
                            "tagged":{"alive":True,"tags":{"骑兵","已死亡"},"enemy":False},
                            "hero":{"alive":True,"tags":{"骑兵","仆从伙伴"},"enemy":False}})
            p.groups["owner"]=["sword","bow","dead","tagged","missing","hero"]
            p.run([oldpick]);self.assertEqual([x[0] for x in p.grants],["owner"]*6)
            p.grants.clear();p.run([newpick]);self.assertEqual([x[0] for x in p.grants],["sword"])
            self.assertEqual(p.grants[0][2][:3],["owner","ability",6.0])
            self.assertEqual(oldpick["args_list"][0],newpick["args_list"][0])

    def test_07_eighteen_existing_owner_self_buff_is_unchanged(self):
        for aid in (134259902,134226331):
            before=body(self.old(aid),"1051000836")
            after=body(self.newdoc(aid),"1051000836")
            self.assertEqual(find(before,"ADD_MODIFIER",892944388000009),find(after,"ADD_MODIFIER",892944388000009))

    def test_08_nineteen_reverse_audit_fixed_values_and_ratio_fallback(self):
        r=next(r for r in self.reports if r["issue"]=="19")
        self.assertIn("134219157",r["explanation"])
        old=body(self.old(134245346,"modifier"),"1625518081")
        new=body(self.newdoc(134245346,"modifier"),"1625518081")
        for aid,rate in ((134219157,10),(134237178,12),(134273833,12),(999,20)):
            p=Projection();p.abilities["ability"]["class"]=aid;p.abilities["ability"]["kv"]["减甲系数"]=rate
            p.run(old);self.assertEqual(p.contributions[-1][2],"ATTR_ALL_RATIO")
            p.contributions.clear();p.run(new)
            self.assertEqual(p.contributions[-1][2],"ATTR_BASE" if aid!=999 else "ATTR_ALL_RATIO")
            self.assertEqual(p.contributions[-1][3],-rate)

    def test_09_nineteen_missing_source_safe_and_loss_only_clears_self(self):
        p=Projection();p.abilities.clear()
        p.run(body(self.newdoc(134245346,"modifier"),"1625518081"))
        self.assertEqual(p.contributions,[])
        self.assertEqual(body(self.old(134245346,"modifier"),"1726324738"),body(self.newdoc(134245346,"modifier"),"1726324738"))
        prop=self.new["editor_table/abilityall/134219157.json"]["kv"]["减甲系数"]
        self.assertEqual((prop["prop_cls"],prop["etype"],prop["type"]),("PFloat",2,1))

    def test_10_twenty_one_hit_not_release_and_each_third_hit(self):
        old=self.old(134278238,"modifier")["trigger_dict"]["1418035204"]
        new=self.newdoc(134278238,"modifier")["trigger_dict"]["1418035204"]
        self.assertEqual(old["event"][0]["args_list"][1]["args_list"],["ET_UNIT_RELEASE_ABILITY"])
        self.assertEqual(new["event"][0]["args_list"][1]["args_list"],["ET_UNIT_HURT_OTHER"])
        before=Projection();before.stacks["current"]=1
        for _ in range(3):before.run(old["action"])
        self.assertEqual(before.stacks["current"],4)  # Old: powder on every release.
        p=Projection();p.units["enemy"]={"alive":True,"tags":set(),"enemy":True};p.stacks["current"]=1
        p.vars[("INTEGER",m.HIT_COUNT,"actor")]=0
        for count in range(1,10):
            self.assertTrue(all(p.c(c) for c in new["condition"]))
            p.run(new["action"])
            self.assertEqual(p.stacks["current"],1+count//3)

    def test_11_twenty_one_skill_or_friendly_damage_does_not_count(self):
        t=self.newdoc(134278238,"modifier")["trigger_dict"]["1418035204"]
        p=Projection();p.units["enemy"]={"alive":True,"tags":set(),"enemy":True}
        p.normal=False;self.assertFalse(all(p.c(c) for c in t["condition"]))
        p.normal=True;p.units["enemy"]["enemy"]=False
        self.assertFalse(all(p.c(c) for c in t["condition"]))
        self.assertNotEqual(t["event"][0]["args_list"][1]["args_list"],["ET_UNIT_RELEASE_ABILITY"])

    def test_12_twenty_one_reacquire_resets_own_counter(self):
        t=self.newdoc(134278238,"modifier")["trigger_dict"]["1485688834"]
        p=Projection();p.vars[("INTEGER",m.HIT_COUNT,"actor")]=2
        p.run([t["action"][0]])
        self.assertEqual(p.vars[("INTEGER",m.HIT_COUNT,"actor")],0)
        self.assertEqual(body(self.old(134278238,"modifier"),"594665475"),body(self.newdoc(134278238,"modifier"),"594665475"))

    def test_13_twenty_one_burst_three_vs_five_snapshots_before_consumption(self):
        oldtimer=find(body(self.old(134235613)),"RUN_COUNT_TIMER_NO_SAVE")
        self.assertEqual(oldtimer["args_list"][1]["args_list"],[3])
        d=self.newdoc(134235613);seq=body(d);branch=find(seq,"IF_THEN_ELSE",893440004974869)
        stage=seq[seq.index(branch)-1:seq.index(branch)+1]
        timer=find(seq,"RUN_COUNT_TIMER_NO_SAVE")
        for internal,shots,damage in ((1,3,85),(3,3,85),(4,5,95)):
            p=Projection();p.abilities["ability"]["kv"]["伤害系数"]=0.85
            p.stacks[("core",134278238)]=internal
            p.run(stage);p.run([timer])
            self.assertEqual(p.timer_counts[-1],(0.3,shots,True))
            self.assertAlmostEqual(p.vars[("FLOAT","最终伤害","local")],damage)
            if internal==4:self.assertEqual(p.stacks[("core",134278238)],1)

    def test_14_twenty_one_all_levels_and_integer_property_codec(self):
        doc=self.newdoc(134235613)
        cases=doc["trigger_dict"]["26066946"]["action"][0]["args_list"][1]["args_list"]
        for case in cases:
            pairs={n["args_list"][1]["args_list"][0]:n["args_list"][2]["args_list"][0]
                   for n in nodes(case) if n.get("action_type")=="SET_ENTITY_KV"}
            self.assertEqual((pairs["P2_normal_shots"],pairs["P2_enhanced_shots"]),(3,5))
        for key in ("P2_normal_shots","P2_enhanced_shots"):
            prop=self.new["editor_table/abilityall/134235613.json"]["kv"][key]
            self.assertEqual((prop["prop_cls"],prop["etype"],prop["type"]),("PInt",1,2))

    def test_15_twenty_two_per_cast_base_enhanced_and_future_level_snapshot(self):
        d=self.newdoc(134230908);branch=find(body(d),"IF_THEN_ELSE",893440004974869)
        for internal,base,enhanced,expected in ((1,.12,.18,.12),(4,.12,.18,.18),(4,.14,.21,.21)):
            p=Projection();p.abilities["ability"]["kv"].update({"伤害系数":2.4,"伤害提高":base,m.EAGLE_ENHANCED:enhanced})
            p.stacks[("core",134232832)]=internal;p.run([branch])
            self.assertEqual(p.vars[("FLOAT",m.EAGLE_RATIO,"local")],expected)
            if internal==4:self.assertEqual(p.stacks[("core",134232832)],1)

    def test_16_twenty_two_returned_handle_only_no_last_instance_mutation(self):
        d=self.newdoc(134230908);callback=find(body(d),"CREATE_CHASING_MOVER")["args_list"][5]["args_list"]
        add=find(callback,"SET_VARIABLE",893440004975128)
        apply_guard=next(n for n in callback if any(child is add for child in nodes(n)))
        p=Projection();p.mods["returned"]={"class":134266933,"source":"owner","ability":"ability","kv":{}}
        p.mods["other-instance"]={"class":134266933,"source":"other","ability":"other-ability","kv":{m.EAGLE_RATIO:.12}}
        p.units["primary"]={"alive":True,"tags":set(),"enemy":True}
        p.vars[("UNIT_ENTITY",m.EAGLE_TARGET,"local")]="primary"
        p.vars[("FLOAT",m.EAGLE_RATIO,"local")]=.18
        p.run([apply_guard]);self.assertEqual(p.mods["returned"]["kv"][m.EAGLE_RATIO],.18)
        self.assertEqual(p.mods["other-instance"]["kv"][m.EAGLE_RATIO],.12)
        p.mods["returned"]["source"]="other";p.mods["returned"]["kv"].clear()
        p.run([apply_guard]);self.assertEqual(p.mods["returned"]["kv"],{})
        p.mods["returned"]["source"]="owner";p.mods["returned"]["ability"]="other-ability"
        p.run([apply_guard]);self.assertEqual(p.mods["returned"]["kv"],{})
        p.mods.pop("returned");p.run([apply_guard])  # Missing returned handle must not dereference.

    def test_17_twenty_two_buff_reads_own_snapshot_not_mutable_source(self):
        old=find(self.old(134266933,"modifier"),"SET_CUR_DAMAGE")["args_list"][0]
        new=find(self.newdoc(134266933,"modifier"),"SET_CUR_DAMAGE")["args_list"][0]
        p=Projection();self.assertAlmostEqual(p.e(old),112)
        p.mods["current"]["kv"][m.EAGLE_RATIO]=.18;p.abilities.clear()
        self.assertAlmostEqual(p.e(new),118)
        self.assertEqual(body(self.old(134266933,"modifier"),"1726324738"),body(self.newdoc(134266933,"modifier"),"1726324738"))
        t=self.newdoc(134266933,"modifier")["trigger_dict"]["512499716"]
        p.damage_source="other";self.assertFalse(all(p.c(c) for c in t["condition"]))

    def test_18_twenty_six_old_unassigned_zero_new_own_five_seconds(self):
        before=find(body(self.old(134253524)),"ADD_MODIFIER")
        after=find(body(self.newdoc(134253524)),"ADD_MODIFIER")
        p=Projection();p.vars[("FLOAT","最终时长","local")]=0
        self.assertEqual(p.e(before["op_arg"][2]),0)
        self.assertEqual(p.e(after["op_arg"][2]),5)
        p.abilities["ability"]["kv"]["时长"]=7;self.assertEqual(p.e(after["op_arg"][2]),7)
        self.assertEqual(before["op_arg_enable"],after["op_arg_enable"])

    def test_19_twenty_seven_threshold_visible_two_not_three(self):
        before=find(body(self.old(134267273)),"IF_THEN_ELSE",893440004975560)["args_list"][0]["args_list"][0]
        after=find(body(self.newdoc(134267273)),"IF_THEN_ELSE",893440004975560)["args_list"][0]["args_list"][0]
        p=Projection();p.stacks[("core",134275651)]=3
        self.assertFalse(p.c(before));self.assertTrue(p.c(after))
        p.stacks[("core",134275651)]=2;self.assertFalse(p.c(after))

    def test_20_twenty_seven_control_duration_zero_to_thirty(self):
        before=body(self.old(134263365),"1051000836")
        after=body(self.newdoc(134263365),"1051000836")
        p=Projection();p.mods["event-buff"]={"kv":{}};p.stacks[("core",134275651)]=1
        p.run(before);self.assertAlmostEqual(p.buff_duration_changes[-1],-1)
        for visible,expected in ((0,0),(1,-1),(2,-2),(3,-3)):
            p.stacks[("core",134275651)]=visible+1;p.run(after)
            self.assertAlmostEqual(p.buff_duration_changes[-1],expected)
        p.stacks.clear();p.buff_duration_changes.clear();p.run(after)
        self.assertEqual(p.buff_duration_changes,[])
        p.mods.clear();p.run(after);self.assertEqual(p.buff_duration_changes,[])

    def test_21_twenty_nine_primary_not_rehit_and_only_legal_extras_count(self):
        for aid,cap in ((134273095,2),(134256160,3)):
            def callback(doc):
                mover=next(n for n in nodes(body(doc)) if n.get("action_type") in ("CREATE_STRAIGHT_MOVER","CREATE_CHASING_MOVER"))
                return mover["args_list"][5]["args_list"]
            old_cb,new_cb=callback(self.old(aid)),callback(self.newdoc(aid))
            def context():
                p=Projection();p.abilities["ability"]["kv"].update({"伤害系数":1.15,"额外系数":.8})
                for u in ("primary","a","dead","b","c","d","ally"):
                    p.units[u]={"alive":u!="dead","tags":set(),"enemy":u!="ally"}
                p.query=["primary","dead","ally","a","b","c","d"]
                return p
            p=context();p.run(old_cb);self.assertEqual([u for u,_ in p.damage].count("primary"),2)
            p=context();p.run(new_cb)
            self.assertEqual([u for u,_ in p.damage],["primary",*list("abcd")[:cap]])
            self.assertAlmostEqual(p.damage[0][1],195)
            for _,damage in p.damage[1:]:self.assertAlmostEqual(damage,115)

    def test_22_twenty_nine_primary_and_group_snapshots_survive_primary_death(self):
        for aid,kind in ((134273095,"CREATE_CHASING_MOVER"),(134256160,"CREATE_STRAIGHT_MOVER")):
            cb=find(body(self.newdoc(aid)),kind)["args_list"][5]["args_list"]
            p=Projection();p.abilities["ability"]["kv"]["额外系数"]=.8
            for u in ("primary","a","b","c"):
                p.units[u]={"alive":True,"tags":set(),"enemy":True}
            p.query=["primary","a","b","c"]
            def invalidate(state):
                if len(state.damage)==1:
                    state.units["primary"]["alive"]=False;state.actor_target="new-target";state.query=[]
            p.after_damage=invalidate;p.run(cb)
            self.assertEqual(p.damage[0][0],"primary")
            self.assertTrue(all(u!="primary" for u,_ in p.damage[1:]))
            self.assertGreaterEqual(len(p.damage),3)

    def test_23_twenty_nine_query_optional_flags_preserved_except_early_cap(self):
        for aid in (134273095,134256160):
            oldpick=find(body(self.old(aid)),"PICK_UNIT_DO_ACTION")
            before=oldpick["args_list"][0]
            after=next(n for n in nodes(body(self.newdoc(aid))) if n.get("sub_type")=="UNIT_LIST_IN_SHAPE")
            expected=deepcopy(before);expected["op_arg_enable"][12]=False
            self.assertEqual(after,expected)

    def test_24_fifteen_not_disguised_as_attack_multiplier_or_partial_support(self):
        self.assertNotIn("modifier/134243369.json",self.new)
        for aid in m.CONDITIONAL_IDS:
            grants=[n for n in nodes(self.newdoc(aid)) if n.get("action_type")=="ADD_MODIFIER"
                    or n.get("sub_type")=="ADD_MODIFIER"]
            generic=[n for n in grants if n["args_list"][1]["args_list"]==[134243369]]
            self.assertEqual(len(generic),1 if aid==134259902 else 0)
        for mid in (134299015,134299016):
            self.assertFalse(any(n.get("action_type")=="ADD_MODIFIER_OWNER_ATTR" for n in nodes(self.newdoc(mid,"modifier"))))
        for aid in (134236412,134263656):
            setters=[n for n in nodes(self.old(aid)) if n.get("action_type")=="SET_ENTITY_KV"]
            self.assertTrue(any(n["args_list"][2].get("args_list")==[.25] for n in setters))

    def test_25_registered_dynamic_disabled_flag_is_not_discarded(self):
        old=self.old(134278238,"modifier")["trigger_dict"]["1418035204"]
        new=self.newdoc(134278238,"modifier")["trigger_dict"]["1418035204"]
        self.assertIs(old["enabled"],False);self.assertIs(new["enabled"],False)
        self.assertEqual(old["sub_trigger_owner_set_var_action"],new["sub_trigger_owner_set_var_action"])

    def test_26_projection_skips_disabled_action_condition_and_rejects_unknown(self):
        p=Projection()
        p.run([{"action_type":"UNSUPPORTED","enable":False,"args_list":[]}])
        p.run([{"action_type":"IF_THEN_ELSE","args_list":[{"args_list":[{"condition_type":"UNKNOWN","enable":False}]},{"args_list":[]},{"args_list":[]}]}])
        with self.assertRaisesRegex(AssertionError,"unsupported expression"):
            p.e({"arg_type":100000,"sub_type":"UNSUPPORTED","args_list":[]})

    def test_27_disabled_target_or_unknown_reviewed_value_is_reported(self):
        d=self.old(134253524);find(body(d),"ADD_MODIFIER")["enable"]=False
        new,reports=self.rebuild({"ability/134253524.json":d})
        self.assertNotIn("ability/134253524.json",new)
        self.assertTrue(any(r["issue"]=="26" and r["status"]=="review_required" for r in reports))

    def test_28_eagle_group_failure_is_atomic(self):
        d=self.old(134266933,"modifier")
        find(d,"SET_CUR_DAMAGE")["args_list"][0]["args_list"][2]["args_list"][2]["args_list"][0]=.20
        new,reports=self.rebuild({"modifier/134266933.json":d})
        for p in ("ability/134230908.json","modifier/134266933.json","editor_table/abilityall/134230908.json","editor_table/modifierall/134266933.json"):
            self.assertNotIn(p,new)
        self.assertTrue(any(r["issue"]=="22" and r["status"]=="review_required" for r in reports))

    def test_29_all_five_eagle_level_parameters_and_source_filter_retained(self):
        d=self.newdoc(134230908)
        cases=d["trigger_dict"]["26066946"]["action"][0]["args_list"][1]["args_list"]
        for c in cases:
            vals={n["args_list"][1]["args_list"][0]:n["args_list"][2]["args_list"][0] for n in nodes(c) if n.get("action_type")=="SET_ENTITY_KV"}
            self.assertEqual((vals["伤害提高"],vals[m.EAGLE_ENHANCED]),(.12,.18))
        self.assertEqual(self.old(134266933,"modifier")["trigger_dict"]["512499716"]["condition"],self.newdoc(134266933,"modifier")["trigger_dict"]["512499716"]["condition"])

    def test_30_approved_support_id_conflict_is_reported_not_reallocated(self):
        original_exists = Path.exists
        def exists(path):
            return True if path.name == "134299015.json" else original_exists(path)
        with patch.object(Path,"exists",exists):
            conflicts = m.audit_support_ids(ROOT)
        self.assertTrue(conflicts)
        self.assertTrue(any("134299015" in p for p in conflicts))

    @staticmethod
    def eagle_context(ratio=.18):
        p=Projection()
        p.units["primary"]={"alive":True,"tags":set(),"enemy":True}
        p.mods["returned"]={"class":134266933,"source":"owner","ability":"ability","kv":{"existing":.07}}
        p.vars[("FLOAT","最终伤害","local")]=240.0
        p.vars[("FLOAT",m.EAGLE_RATIO,"local")]=ratio
        # A stale but otherwise matching prior handle must not be written when
        # this hit kills its target and no new ADD_MODIFIER executes.
        p.vars[("MODIFIER_ENTITY",m.EAGLE_HANDLE,"local")]="returned"
        return p

    @staticmethod
    def eagle_callback(doc):
        return find(body(doc),"CREATE_CHASING_MOVER")["args_list"][5]["args_list"]

    def test_31_eagle_old_damage_kill_still_adds_new_guard_skips_before_add(self):
        def kill(state): state.units["primary"]["alive"]=False
        old=self.eagle_context();old.after_damage=kill
        with self.assertRaisesRegex(AssertionError,"ADD_MODIFIER attempted on invalid/dead target"):
            old.run(self.eagle_callback(self.old(134230908)))
        new=self.eagle_context();new.after_damage=kill
        new.run(self.eagle_callback(self.newdoc(134230908)))
        self.assertEqual(new.damage,[("primary",240.0)])
        self.assertEqual(new.grants,[])
        self.assertEqual(new.mods["returned"]["kv"],{"existing":.07})

    def test_32_eagle_nonlethal_hit_adds_and_snapshots_base_or_enhanced(self):
        for ratio in (.12,.18):
            p=self.eagle_context(ratio)
            p.run(self.eagle_callback(self.newdoc(134230908)))
            self.assertEqual(p.damage,[("primary",240.0)])
            self.assertEqual([g[0] for g in p.grants],["primary"])
            self.assertEqual(p.grants[0][2][:3],["owner","ability",6.0])
            self.assertEqual(p.mods["returned"]["kv"][m.EAGLE_RATIO],ratio)

    def test_33_eagle_removed_or_death_tagged_target_cannot_retarget_buff(self):
        for mode in ("removed","dead","death-tag"):
            p=self.eagle_context()
            p.units["new-target"]={"alive":True,"tags":set(),"enemy":True}
            def invalidate(state, case=mode):
                if case=="removed": state.units.pop("primary")
                if case=="dead": state.units["primary"]["alive"]=False
                if case=="death-tag": state.units["primary"]["tags"].add("已死亡")
                state.actor_target="new-target"
            p.after_damage=invalidate
            p.run(self.eagle_callback(self.newdoc(134230908)))
            self.assertEqual(p.grants,[],mode)
            self.assertEqual(p.vars[("UNIT_ENTITY",m.EAGLE_TARGET,"local")],"primary")
            self.assertEqual(p.mods["returned"]["kv"],{"existing":.07},mode)

    def test_34_eagle_native_exists_then_alive_guards_precede_add_expression(self):
        cb=self.eagle_callback(self.newdoc(134230908))
        damage=find(cb,"APPLY_DAMAGE")
        add=find(cb,"SET_VARIABLE",893440004975128)
        snapshot=next(n for n in cb if n.get("action_type")=="SET_VARIABLE"
                      and n["args_list"][0]["args_list"]==[["UNIT_ENTITY",m.EAGLE_TARGET,"local"]])
        guard=next(n for n in cb if any(child is add for child in nodes(n)))
        self.assertLess(cb.index(snapshot),cb.index(damage))
        self.assertLess(cb.index(damage),cb.index(guard))
        exists=guard["args_list"][0]["args_list"]
        self.assertEqual([c["condition_type"] for c in exists],["TYPE_IS_EXIST"])
        live_guard=guard["args_list"][1]["args_list"][0]
        conditions=live_guard["args_list"][0]["args_list"]
        self.assertEqual([c["condition_type"] for c in conditions],["IS_UNIT_ALIVE","BOOL_NOT"])
        self.assertIs(live_guard["args_list"][1]["args_list"][0],add)
        self.assertEqual(add["args_list"][1]["sub_type"],"ADD_MODIFIER")
        self.assertEqual(add["args_list"][1]["args_list"][0],exists[0]["args_list"][0])
        self.assertEqual(add["args_list"][1]["args_list"][0],conditions[0]["args_list"][0])

    def test_35_eighteen_rechecks_later_soldier_after_group_iteration_started(self):
        for aid in (134259902,134226331,134237178):
            p=Projection()
            p.units.update({"first":{"alive":True,"tags":{"刀兵"},"enemy":False},
                            "later":{"alive":True,"tags":{"枪兵"},"enemy":False},
                            "corpse":{"alive":False,"tags":{"骑兵"},"enemy":False}})
            p.groups["owner"]=["first","later","corpse","missing"]
            # Adversarial state change during prior grant, not a claim about
            # actual engine Buff callbacks. The group intentionally stays stale.
            p.after_grant=lambda state: state.units["later"].update(alive=False)
            recipient_phase=self.old(aid);m.repair_recipients(recipient_phase)
            pick=find(body(recipient_phase,"1051000836"),"PICK_UNIT_DO_ACTION")
            p.run([pick])
            self.assertEqual([g[0] for g in p.grants],["first"])
            self.assertEqual(p.groups["owner"],["first","later","corpse","missing"])

    def conditional_hit(self, state, mid=m.TARGET_SUPPORT):
        state.run(body(self.newdoc(mid,"modifier"),"512499716"))
        return state.current_damage

    def test_36_conditional_source_controller_uses_native_global_event_and_modifier_owner(self):
        t=self.newdoc(m.SOURCE_SUPPORT,"modifier")["trigger_dict"]["512499716"]
        self.assertEqual(t["event"][0]["event_type"],"GENERIC_UNIT_EVENT")
        self.assertEqual(t["event"][0]["args_list"],[m.expr(100008,"GENERIC_UNIT_EVENT","ET_UNIT_BE_HURT")])
        native=json.loads((ROOT/"modifier/134230485.json").read_bytes())
        response=native["trigger_dict"]["1418035204"]
        self.assertEqual(response["event"][0]["args_list"][0]["arg_type"],100008)
        self.assertTrue(any(n.get("sub_type")=="MODIFIER_OWNER" for n in nodes(response)))
        p=ConditionalProjection(134236412,m.SOURCE_SUPPORT)
        self.assertNotEqual(p.e(m.unit("MODIFIER_OWNER")),p.damage_target)
        self.assertAlmostEqual(self.conditional_hit(p,m.SOURCE_SUPPORT),125)

    def test_37_sima_checks_original_core_and_living_source_every_hit(self):
        for mode in ("normal","not-full","core-gone","source-dead","source-gone","skill-lost","unready"):
            p=ConditionalProjection(134236412,m.SOURCE_SUPPORT)
            if mode=="not-full": p.stacks[("core",134232832)]=3
            if mode=="core-gone": p.stacks.clear()
            if mode=="source-dead": p.units["owner"]["alive"]=False
            if mode=="source-gone": p.units.pop("owner")
            if mode=="skill-lost": p.abilities["ability"]["kv"][m.CONDITIONAL_ACTIVE]=False
            if mode=="unready": p.mods["current"]["kv"][m.CONDITIONAL_READY]=False
            self.assertEqual(self.conditional_hit(p,m.SOURCE_SUPPORT),125 if mode=="normal" else 100,mode)
        p=ConditionalProjection(134236412,m.SOURCE_SUPPORT)
        p.stacks["stale-original"]=4
        p.mods["current"]["kv"][m.CONDITIONAL_CORE]="stale-original"
        self.assertEqual(self.conditional_hit(p,m.SOURCE_SUPPORT),100)

    def test_38_sima_all_soldiers_but_gan_melee_and_exact_target(self):
        for aid,mid,tag,expected in ((134236412,m.SOURCE_SUPPORT,"弓兵",125),
                (134263656,m.TARGET_SUPPORT,"弓兵",100),(134263656,m.TARGET_SUPPORT,"刀兵",125)):
            p=ConditionalProjection(aid,mid);p.units["soldier"]["tags"]={tag}
            self.assertEqual(self.conditional_hit(p,mid),expected)
        p=ConditionalProjection();p.damage_target="other"
        self.assertEqual(self.conditional_hit(p),100)
        p=ConditionalProjection();p.units["target"]["tags"]={"刀兵"}
        self.assertEqual(self.conditional_hit(p),100)
        for tag in ("仆从伙伴","阵型队长"):
            p=ConditionalProjection();p.units["target"]["tags"]={tag}
            self.assertEqual(self.conditional_hit(p),125)

    def test_39_global_unrelated_hero_environment_or_missing_team_kv_is_safe(self):
        for mode in ("hero","missing-kv","missing-leader","other-team","no-source","friendly-target","dead-soldier"):
            p=ConditionalProjection(134236412,m.SOURCE_SUPPORT)
            if mode=="hero": p.damage_source="owner"
            if mode=="missing-kv": p.units["soldier"]["kv"]={}
            if mode=="missing-leader": p.units["soldier"]["kv"]["所属英雄"]="removed"
            if mode=="other-team": p.units["soldier"]["kv"]["所属英雄"]="other"
            if mode=="no-source": p.damage_source=None
            if mode=="friendly-target": p.units["target"]["enemy"]=False
            if mode=="dead-soldier": p.units["soldier"]["alive"]=False
            self.assertEqual(self.conditional_hit(p,m.SOURCE_SUPPORT),100,mode)

    def test_40_gan_actual_active_hit_snapshots_target_without_retarget(self):
        t=self.newdoc(134263656)["trigger_dict"]["1984499716"]
        self.assertEqual(t["event"][0]["args_list"][1]["args_list"],["ET_UNIT_HURT_OTHER"])
        self.assertEqual(t["condition"],[])
        for ability_type in (None,1,3):
            p=ConditionalProjection()
            if ability_type is not None: p.abilities["damage-ability"]={"type":ability_type}
            p.mods["returned"]={"source":"owner","ability":"ability","kv":{}}
            p.after_grant=lambda state:setattr(state,"damage_target","other")
            p.run(t["action"])
            self.assertEqual(len(p.grants),1 if ability_type==3 else 0)
            if ability_type==3:
                self.assertEqual(p.grants[0][:2],("target",m.TARGET_SUPPORT))
                self.assertEqual(p.grants[0][2][:3],["owner","ability",6.0])
                self.assertEqual(p.mods["returned"]["kv"][m.CONDITIONAL_TARGET],"target")
                self.assertTrue(p.mods["returned"]["kv"][m.CONDITIONAL_READY])
        self.assertFalse(any(n.get("action_type")=="UNIT_RELEASE_COMMAND" for n in nodes(t)))

    def test_41_returned_handle_missing_foreign_source_or_exact_ability_never_written(self):
        actions=body(self.newdoc(134263656),"1984499716")
        for mode in ("missing","source","ability"):
            p=ConditionalProjection();p.abilities["damage-ability"]={"type":3}
            if mode!="missing":
                p.mods["returned"]={"source":"other" if mode=="source" else "owner",
                    "ability":"another-instance" if mode=="ability" else "ability","kv":{"keep":7}}
            p.run(actions)
            self.assertFalse(p.modifier_writes,mode)
            if mode!="missing": self.assertEqual(p.mods["returned"]["kv"],{"keep":7})

    def test_42_sima_indefinite_controller_captures_original_core_and_gain_when_full(self):
        for tid in ("1984499716","1959489540"):
            p=ConditionalProjection(134236412,m.SOURCE_SUPPORT)
            p.event_buff=("core",134232832)
            p.mods["returned"]={"source":"owner","ability":"ability","kv":{}}
            # Skip the native registration integer: engine delivery is not simulated.
            actions=[n for n in body(self.newdoc(134236412),tid) if not isinstance(n,int)]
            p.run(actions)
            self.assertEqual(p.grants[0][2][2],-1.0)
            self.assertEqual(p.mods["returned"]["kv"][m.CONDITIONAL_CORE],("core",134232832))
            self.assertEqual(p.vars[("MODIFIER_ENTITY",m.CONDITIONAL_HANDLE,"actor")],"returned")

    def test_43_zhang_consumes_exact_three_then_self_attack_and_leader_damage(self):
        t=self.newdoc(134259902)["trigger_dict"]["1051000836"]
        self.assertEqual(t["event"][0]["event_type"],"GLOBAL_MODIFIER_EVENT")
        for delta,stack,expected in ((-3,1,2),(-2,1,0),(-1,1,0),(-3,2,0),(3,4,0)):
            p=ConditionalProjection(134259902,m.SOURCE_SUPPORT)
            p.event_buff=("core",134259689);p.stacks[p.event_buff]=stack;p.layer_change=delta
            p.mods["returned"]={"source":"owner","ability":"ability","kv":{}}
            p.run(t["action"])
            self.assertEqual(len(p.grants),expected,(delta,stack))
            if expected:
                self.assertEqual([g[1] for g in p.grants],[134243369,m.SOURCE_SUPPORT])
                self.assertEqual(p.mods["returned"]["kv"][m.CONDITIONAL_RATIO],.15)
        p=ConditionalProjection(134259902,m.SOURCE_SUPPORT)
        p.mods["current"]["kv"][m.CONDITIONAL_RATIO]=.15
        self.assertAlmostEqual(self.conditional_hit(p,m.SOURCE_SUPPORT),115)
        m.check_levels(self.newdoc(134259902),{"加攻系数":15.0})

    def test_44_ma_retains_armor_and_marks_exact_target_including_nonleader(self):
        p=ConditionalProjection(134237178)
        p.ability_target="target";p.units["target"]["tags"]={"枪兵"}
        p.mods["returned"]={"source":"owner","ability":"ability","kv":{}}
        p.run(body(self.newdoc(134237178),"1051000836"))
        self.assertEqual([g[:2] for g in p.grants],[("target",134245346),("target",m.TARGET_SUPPORT)])
        self.assertEqual(p.mods["returned"]["kv"][m.CONDITIONAL_TARGET],"target")
        p.current="returned";p.mods["returned"]["owner"]="target"
        self.assertAlmostEqual(self.conditional_hit(p),115)
        p.current_damage=100;p.damage_target="other"
        self.assertEqual(self.conditional_hit(p),100)
        m.check_levels(self.newdoc(134237178),{"减甲系数":12.0})

    def test_45_loss_unregisters_only_own_listener_and_source_instance(self):
        for mid in (m.SOURCE_SUPPORT,m.TARGET_SUPPORT):
            p=ConditionalProjection(mid=mid)
            p.vars[("DYNAMIC_TRIGGER_INSTANCE","temp触发器","actor")]="own-listener"
            p.run(body(self.newdoc(mid,"modifier"),"1726324738"))
            self.assertEqual(p.unregistered,["own-listener"])
            self.assertEqual(p.removed,[])
        for foreign in (False,True):
            p=ConditionalProjection(134236412,m.SOURCE_SUPPORT)
            p.vars[("DYNAMIC_TRIGGER_INSTANCE","temp触发器","actor")]="ability-listener"
            p.vars[("MODIFIER_ENTITY",m.CONDITIONAL_HANDLE,"actor")]="current"
            p.mods["unrelated"]={"source":"owner","ability":"other-ability","kv":{}}
            if foreign: p.mods["current"]["ability"]="other-instance"
            p.run(body(self.newdoc(134236412),"225054724"))
            self.assertEqual(p.removed,[] if foreign else ["current"])
            self.assertIn("unrelated",p.mods)

    def test_46_support_registration_text_indexes_and_native_unit_snapshot(self):
        for mid,label in ((m.SOURCE_SUPPORT,"定向增伤·来源"),(m.TARGET_SUPPORT,"定向增伤·目标")):
            prop=self.new[f"editor_table/modifierall/{mid}.json"]
            self.assertEqual(self.new["zhlanguage.json"][str(prop["name"])],label)
            self.assertEqual(self.new["tidindexinfo.json"][str(prop["name"])]["item_key"],mid)
            self.assertIn(str(mid),self.new[m.FOLDERS]["d"])
            doc=self.newdoc(mid,"modifier")
            self.assertEqual(doc["trigger_dict"]["1625518081"]["action"][-1],512499716)
            self.assertFalse(doc["trigger_dict"]["512499716"]["enabled"])
        native=json.loads((ROOT/"modifier/134259689.json").read_bytes())
        self.assertTrue(any(n.get("sub_type")=="GET_UNIT_ENTITY_KV" and n.get("arg_type")==100006
            and n["args_list"][0].get("sub_type")=="CUR_MODIFIER" for n in nodes(native)))

    def test_47_support_id_conflict_blocks_complete_conditional_group(self):
        with patch.object(m,"audit_support_ids",return_value=["occupied"]):
            new,reports=m.build(ROOT)
        report=next(r for r in reports if r["issue"]=="15")
        self.assertEqual(report["status"],"review_required")
        self.assertNotIn("modifier/134299015.json",new)
        self.assertNotIn("modifier/134299016.json",new)
        self.assertNotIn("ability/134263656.json",new)

    def test_48_none_hashes_are_nonexistence_preconditions_not_stale(self):
        report=next(r for r in self.reports if r["issue"]=="15")
        additions={p for p,sha in report["source_sha256"].items() if sha is None}
        self.assertEqual(len(additions),4)
        self.assertTrue(additions<=self.new.keys())
        self.assertEqual(report["status"],"candidate")

    def test_49_duplicate_refresh_explicitly_rebuilds_only_same_source_exact_ability(self):
        for aid,mid,tid,recipient in ((134263656,m.TARGET_SUPPORT,"1984499716","target"),
                (134236412,m.SOURCE_SUPPORT,"1984499716","owner")):
            p=ConditionalProjection(aid,mid)
            p.abilities["damage-ability"]={"type":3}
            p.event_buff=("core",134232832)
            p.mods.clear()
            for handle,source,ability,cls in (("own-a","owner","ability",mid),("own-b","owner","ability",mid),
                    ("other-source","other","ability",mid),("other-ability","owner","other-instance",mid),
                    ("other-class","owner","ability",134243369)):
                p.mods[handle]={"class":cls,"owner":recipient,"source":source,"ability":ability,"kv":{}}
            def created(state):
                state.mods["returned"]={"class":mid,"owner":recipient,"source":"owner","ability":"ability","kv":{}}
            p.after_grant=created
            actions=body(self.newdoc(aid),tid)
            p.run(actions)
            self.assertEqual(p.removed,["own-a","own-b"])
            p.run(actions)
            self.assertEqual(p.removed,["own-a","own-b","returned"])
            self.assertEqual(set(p.mods),{"other-source","other-ability","other-class","returned"})
            self.assertEqual(p.mods["returned"]["kv"][m.CONDITIONAL_RATIO],.25)
            self.assertEqual(len(p.grants),2)

    def test_50_cover_pairs_are_native_values_not_claimed_enum_meanings(self):
        for mid,native_id in ((m.SOURCE_SUPPORT,134266933),(m.TARGET_SUPPORT,134227930)):
            native=json.loads((ROOT/f"editor_table/modifierall/{native_id}.json").read_bytes())
            prop=self.new[f"editor_table/modifierall/{mid}.json"]
            self.assertEqual((prop["modifier_cover_type"],prop["same_origin_cover"]),
                             (native["modifier_cover_type"],native["same_origin_cover"]))
        report=next(r for r in self.reports if r["issue"]=="15")
        self.assertIn("without relying on cover enums",report["explanation"])


class InputSafety(unittest.TestCase):
    def test_missing_input_reports_and_never_writes(self):
        with patch.object(Path,"read_bytes",side_effect=FileNotFoundError("missing")), \
                patch.object(Path,"write_bytes",side_effect=AssertionError("write forbidden")), \
                patch.object(Path,"write_text",side_effect=AssertionError("write forbidden")), \
                patch.object(m,"audit_support_ids",return_value=[]):
            new,reports = m.build(Path("/not-read"))
        self.assertEqual(new,{})
        self.assertTrue(all(r["status"]=="review_required" for r in reports if r["issue"]!="15"))

    def test_duplicate_json_keys_require_review(self):
        with patch.object(Path,"read_bytes",return_value=b'{"unknown":1,"unknown":2}'), \
                patch.object(m,"audit_support_ids",return_value=[]):
            new,reports = m.build(Path("/not-read"))
        self.assertEqual(new,{})
        self.assertTrue(all("duplicate JSON key" in r["explanation"] for r in reports if r["issue"]!="15"))


if __name__=="__main__":
    unittest.main()

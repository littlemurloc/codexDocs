"""Read-only P1 numeric/target candidates for the seven reviewed map3 ECAs.

No imports from other repair groups, no writes, no editor calls. IDs are Python
integers. build() rereads its inputs and refuses unrecognized target structures.
Evidence: 2026-10-20 live map3, first-batch-10-heroes-skill-config-v1.md,
first-batch-8-heroes-latest-skills.md, and the additional-eight v1.0 archive.
Editor loading, callbacks, and combat behavior remain unverified.
"""

from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path


FILES = (
    "ability/134266460.json",
    "ability/134280536.json",
    "ability/134231116.json",
    "ability/134264317.json",
    "ability/134222326.json",
    "modifier/134282266.json",
    "ability/134263364.json",
)
CAST = "893440004"
LEVEL = "26066946"
SNAPSHOT = "P1_shoubei_snapshot"
CONSUMED = "P1_shoubei_consumed"


class ReviewError(ValueError):
    """The current file no longer matches the reviewed defect."""


def _need(ok, message):
    if not ok:
        raise ReviewError(message)


def _expr(arg_type, sub_type, *args):
    return {"arg_type": arg_type, "sub_type": sub_type, "args_list": list(args)}


def _literal(value, arg_type=100002):
    return _expr(arg_type, 1, value)


def _operation(left, op, right, integer=False):
    return _expr(100002 if integer else 100000,
                 "MATH_OPERATION" if integer else "ARITHMETIC_OPERATION",
                 left, _literal(op, 100016 if integer else 100017), right)


def _nodes(value):
    """Walk executable nodes, including registered dynamic-trigger bodies.

    Trigger.enabled is deliberately NOT used here. Disabled actions/conditions
    and disabled optional arguments are excluded, not interpreted as runtime.
    """
    if isinstance(value, dict):
        if value.get("enable") is False:
            return
        yield value
        for key, child in value.items():
            if key == "op_arg":
                flags = value.get("op_arg_enable", [])
                for i, arg in enumerate(child):
                    if i < len(flags) and flags[i] is True:
                        yield from _nodes(arg)
            elif key != "op_arg_enable":
                yield from _nodes(child)
    elif isinstance(value, list):
        for child in value:
            yield from _nodes(child)


def _one(value, predicate, label):
    found = [node for node in _nodes(value) if predicate(node)]
    _need(len(found) == 1, f"{label}: expected one active node, found {len(found)}")
    return found[0]


def _is_expr(node, kind, arg_type=None):
    return (isinstance(node, dict) and node.get("sub_type") == kind
            and (arg_type is None or node.get("arg_type") == arg_type))


def _value(node):
    _need(_is_expr(node, 1) and len(node.get("args_list", [])) == 1,
          "expected a native primitive literal")
    return node["args_list"][0]


def _binary(node, kind, op):
    _need(_is_expr(node, kind) and len(node.get("args_list", [])) == 3,
          f"expected {kind}")
    a, operator, b = node["args_list"]
    _need(_value(operator) == op, f"expected operator {op}")
    return a, b


def _kv(node, key):
    return (_is_expr(node, "GET_FLOAT_KV", 100000)
            and len(node.get("args_list", [])) == 2
            and _is_expr(node["args_list"][0], "CUR_ABILITY", 100014)
            and _value(node["args_list"][1]) == key)


def _stack(node, modifier, owner="ABILITY_OWNER"):
    _need(_is_expr(node, "GET_MOD_STACK", 100002), "expected integer stack read")
    instance = node["args_list"][0]
    _need(_is_expr(instance, "GET_LAST_MODIFIER_INSTANCE", 100076),
          "expected modifier-instance lookup")
    _need(_is_expr(instance["args_list"][0], owner, 100006)
          and _value(instance["args_list"][1]) == modifier,
          f"expected {owner} modifier {modifier}")
    return instance


def _trigger(doc, key, event):
    t = doc["trigger_dict"][key]
    _need(any(e.get("event_type") == event and e.get("enable") is not False
              for e in t["event"]), f"trigger {key}: wrong event")
    if t.get("enabled") is False:
        parent = doc["trigger_dict"].get(str(t.get("p_trigger_id")), {})
        registered = any(
            isinstance(x, int) and x == t["trigger_id"]
            for n in _nodes(parent.get("action", []))
            for x in n.get("args_list", [])
        ) or t["trigger_id"] in parent.get("action", [])
        _need(t.get("is_conf") is True and parent.get("enabled") is True and registered,
              f"trigger {key}: disabled and not registered by its parent")
        reg = t.get("sub_trigger_owner_set_var_action", {})
        _need(reg.get("enable") is not False and any(
            n.get("sub_type") in ("REG_ABILITY_TRIGGER", "REG_MODIFIER_TRIGGER")
            and _value(n["args_list"][0]) == t["trigger_id"]
            for n in _nodes(reg)), f"trigger {key}: missing registration")
    return t


def _action(tree, action_type, element_id=None):
    return _one(tree, lambda n: n.get("action_type") == action_type
                and (element_id is None or n.get("element_id") == element_id),
                f"{action_type}/{element_id}")


def _level_values(doc, expected):
    obtain = _trigger(doc, "1959489540", "ABILITY_OBTAIN")
    _need(not any(n.get("action_type") == "SET_ENTITY_KV"
                  and _value(n["args_list"][1]) in expected
                  for n in _nodes(obtain["action"])),
          "new obtain coefficient setter requires review")
    t = _trigger(doc, LEVEL, "ABILITY_LEVEL_CHANGED")
    switch = _action(t["action"], "SWITCH")
    cases = [x for x in switch["args_list"][1]["args_list"]
             if isinstance(x, dict) and x.get("enable") is not False]
    _need(len(cases) == 5 and [_value(c["args_list"][0]) for c in cases]
          == [1, 2, 3, 4, 5], "expected level branches 1..5")
    result = []
    for case in cases:
        _need(case.get("action_type") == "CASE", "expected native CASE")
        for key, old in expected.items():
            setter = _one(case, lambda n: n.get("action_type") == "SET_ENTITY_KV"
                          and _value(n["args_list"][1]) == key, f"level KV {key}")
            _need(_is_expr(setter["args_list"][0], "CUR_ABILITY", 100014),
                  "level KV writes another entity")
            _need(_value(setter["args_list"][2]) == old,
                  f"level KV {key} changed from reviewed value {old}")
            result.append(setter)
    return result


def _actor_target(node):
    _need(_is_expr(node, 11, 100006), "expected actor target reference")
    ref = node["args_list"][0]
    _need(isinstance(ref, dict) and ref.get("__tuple__") is True
          and ref.get("items") == ["UNIT_ENTITY", "目标单位", "actor"],
          "actor target encoding changed")
    _need(set(ref) <= {"__tuple__", "items"}, "unknown metadata on replaced tuple")


def _selected(node):
    return (_is_expr(node, "FOR_EACH_SELECTED_UNIT", 100006)
            and node.get("args_list") == [])


def _legal_leader_gate(branch):
    conditions = branch["args_list"][0]["args_list"]
    _need(len(conditions) == 1 and conditions[0].get("enable") is True
          and conditions[0].get("condition_type") == "AND", "legal-leader AND gate changed/disabled")
    guards = conditions[0]["args_list"][0]["args_list"]
    _need(len(guards) == 2 and all(c.get("enable") is True for c in guards),
          "legal-leader conditions changed/disabled")
    alive, not_dead = guards
    _need(alive.get("condition_type") == "IS_UNIT_ALIVE" and _selected(alive["args_list"][0])
          and not_dead.get("condition_type") == "BOOL_NOT", "legal-leader guard changed")
    tag = not_dead["args_list"][0]
    _need(_is_expr(tag, "UNIT_HAS_TAG", 100001) and _selected(tag["args_list"][0])
          and _value(tag["args_list"][1]) == "已死亡", "dead-tag guard changed")


def _collision_target(node):
    _actor_target(node)
    node["sub_type"] = "MOVER_COLLIDE_UNIT"
    node["args_list"] = []


def _factory(doc):
    next_id = max(n.get("element_id", 0) for n in _all_nodes(doc)) + 1

    def make(kind, *args, condition=False):
        nonlocal next_id
        node = {"condition_type" if condition else "action_type": kind,
                "args_list": list(args), "enable": True, "element_id": next_id}
        if not condition:
            node["bp"] = False
        next_id += 1
        return node

    return make


def _if(make, condition, yes, no=()):
    node = make("IF_THEN_ELSE", _expr(100021, 1, condition),
                _expr(100022, 1, *yes), _expr(100022, 1, *no))
    node["fake_op"] = []
    return node


def _hz_resource(doc):
    cast = _trigger(doc, CAST, "ABILITY_SP_END")
    clear = _action(cast["action"], "ADD_BUFF_STACK")
    target, delta = clear["args_list"]
    _need(_is_expr(target, "GET_LAST_MODIFIER_INSTANCE", 100076)
          and _value(target["args_list"][1]) == 134242511,
          "Huang Zhong clear target changed")
    count, sign = _binary(delta, "MATH_OPERATION", "*")
    stack, base = _binary(count, "MATH_OPERATION", "-")
    _need(_value(sign) == -1 and _value(base) == 1, "clear delta changed")
    _stack(stack, 134267407)
    stack["args_list"][0]["args_list"][1]["args_list"][0] = 134242511
    branch = _one(cast["action"], lambda n: n.get("action_type") == "IF_THEN_ELSE"
                  and clear in n["args_list"][1]["args_list"], "resource branch")
    fallback = branch["args_list"][2]["args_list"]
    _need(len(fallback) == 1 and fallback[0].get("action_type") == "SET_VARIABLE",
          "missing-resource damage fallback changed")
    make = _factory(doc)
    guarded_clear = _if(make, make("TYPE_IS_EXIST", deepcopy(target), condition=True), [clear])
    body = branch["args_list"][1]["args_list"]
    body[body.index(clear)] = guarded_clear
    base_actions = list(fallback)
    fallback.clear()
    guarded_resource = _if(make, make("TYPE_IS_EXIST", deepcopy(target), condition=True), [branch])
    index = cast["action"].index(branch)
    cast["action"][index:index + 1] = base_actions + [guarded_resource]
    return "Clear reads own Xu Shi 134242511; existence guards precede stack reads and clear; absent resource retains base damage."


def _hz_collision(doc):
    cast = _trigger(doc, CAST, "ABILITY_SP_END")
    mover = _action(cast["action"], "CREATE_STRAIGHT_MOVER")
    collision = mover["args_list"][9]
    damage = _action(collision, "APPLY_DAMAGE")
    debuff = _action(collision, "ADD_MODIFIER")
    tags = [n for n in _nodes(collision) if n.get("condition_type") == "UNIT_HAS_TAG"]
    _need(len(tags) == 2, "expected two leader tag tests")
    targets = [damage["args_list"][2], debuff["args_list"][0]]
    targets += [n["args_list"][0] for n in tags]
    for node in targets:
        _actor_target(node)
    for node in targets:
        _collision_target(node)
    return "Collision damage, leader tests and attack debuff use MOVER_COLLIDE_UNIT."


def _mc(doc):
    _level_values(doc, {"伤害系数": 1.15, "额外系数": 0.45})
    cast = _trigger(doc, CAST, "ABILITY_SP_END")
    mover = _action(cast["action"], "CREATE_STRAIGHT_MOVER")
    collision = mover["args_list"][9]
    damage = _action(collision, "APPLY_DAMAGE")
    _actor_target(damage["args_list"][2])
    boosted = _action(collision, "SET_VARIABLE", 893440004975771)
    attack, coefficient = _binary(boosted["args_list"][1], "ARITHMETIC_OPERATION", "*")
    _need(_is_expr(attack, "GET_UNIT_ATTR"), "Ma Chao attack expression changed")
    base, bonus = _binary(coefficient, "ARITHMETIC_OPERATION", "+")
    extra, internal = _binary(bonus, "ARITHMETIC_OPERATION", "*")
    _need(_kv(base, "伤害系数") and _kv(extra, "额外系数"), "Ma Chao KV formula changed")
    _stack(internal, 134265433)
    # Refuse pruning user metadata on the redundant internal-stack operand.
    _need(all(set(n) <= {"arg_type", "sub_type", "args_list"}
              for n in _nodes([internal, bonus["args_list"][1]])),
          "unknown metadata on removed stack operand")
    bonus.update(deepcopy(extra))
    _collision_target(damage["args_list"][2])
    return "115% + fixed 45% at >=2 visible stacks = 160%; actual collision target; levels 1..5 checked."


def _xun(doc):
    setters = _level_values(doc, {"伤害减免%": 0.8})
    _trigger(doc, "1051000836", "GLOBAL_MODIFIER_EVENT")
    for setter in setters:
        setter["args_list"][2]["args_list"][0] = 0.08
    return "All five level branches write reduction 0.08 (8%), not 0.8 (80%)."


def _xy_core(doc):
    t = _trigger(doc, "1418035204", "SPECIAL_UNIT_EVENT")
    setter = _action(t["action"], "SET_CUR_DAMAGE")
    hurt, bonus = _binary(setter["args_list"][0], "ARITHMETIC_OPERATION", "*")
    rate, stack = _binary(bonus, "ARITHMETIC_OPERATION", "*")
    _need(_is_expr(hurt, "HURT_DAMAGE", 100000) and _value(rate) == 0.05
          and _is_expr(stack, "GET_MOD_STACK", 100002)
          and _is_expr(stack["args_list"][0], "CUR_MODIFIER", 100076),
          "Xiahou Yuan core damage expression changed")
    bonus["args_list"][2] = _expr(100000, "I2F", _operation(stack, "-", _literal(1), True))
    setter["args_list"][0]["args_list"][2] = _operation(_literal(1.0, 100000), "+", bonus)
    return "HURT * (1 + .05 * (internal - 1)); preserve dynamic registration and target filtering."


def _xy_active(doc):
    _level_values(doc, {"伤害系数": 2.5, "额外系数": 0.45})
    cast = _trigger(doc, CAST, "ABILITY_SP_END")
    setter = _action(cast["action"], "SET_VARIABLE", 893440004974076)
    formula = setter["args_list"][1]
    attack_base, bonus = _binary(formula, "ARITHMETIC_OPERATION", "+")
    attack, base = _binary(attack_base, "ARITHMETIC_OPERATION", "*")
    rate, visible = _binary(bonus, "ARITHMETIC_OPERATION", "*")
    _need(_is_expr(attack, "GET_UNIT_ATTR") and _kv(base, "伤害系数")
          and _kv(rate, "额外系数") and _is_expr(visible, "I2F"),
          "Xiahou Yuan active formula changed")
    stack, one = _binary(visible["args_list"][0], "MATH_OPERATION", "-")
    _stack(stack, 134282266)
    _need(_value(one) == 1, "visible-stack offset changed")
    # Reparent existing nodes: preserve their IDs/metadata, not just their values.
    outer_op = formula["args_list"][1]
    inner_op = attack_base["args_list"][1]
    outer_op["args_list"][0] = "*"
    inner_op["args_list"][0] = "+"
    attack_base["args_list"] = [base, inner_op, bonus]
    formula["args_list"] = [attack, outer_op, attack_base]
    return "attack * (2.5 + .45 * visible stacks); levels 1..5 and internal-base subtraction checked."


def _cao(doc):
    _level_values(doc, {"系数": 0.05, "时长": 7.0})
    cast = _trigger(doc, CAST, "ABILITY_SP_END")
    actions = cast["action"]
    pick = _one(actions, lambda n: n.get("action_type") == "PICK_UNIT_DO_ACTION"
                and n.get("element_id") == 1959489540974142, "Cao Ren outer iteration")
    branch = _action(pick["args_list"][1], "IF_THEN_ELSE", 893440004975552)
    _legal_leader_gate(branch)
    body = branch["args_list"][1]["args_list"]
    clear = _action(body, "SET_BUFF_STACK")
    _need(body[-1] is clear and _value(clear["args_list"][1]) == 1,
          "Cao Ren resource clear placement changed")
    _need(_value(clear["args_list"][0]["args_list"][1]) == 134224731,
          "Cao Ren clear modifier changed")
    shields = [n for n in _nodes(body) if n.get("action_type") == "SET_ENTITY_KV"
               and _value(n["args_list"][1]) == "护盾值"]
    _need(len(shields) == 2, "expected leader and soldier shield formula")
    visible_nodes = []
    for setter in shields:
        hp_rate, visible = _binary(setter["args_list"][2], "ARITHMETIC_OPERATION", "*")
        hp, rate = _binary(hp_rate, "ARITHMETIC_OPERATION", "*")
        _need(_is_expr(hp, "GET_UNIT_ATTR") and _kv(rate, "系数"), "shield formula changed")
        stack, one = _binary(visible, "MATH_OPERATION", "-")
        _stack(stack, 134224731)
        _need(_value(one) == 1, "Cao Ren internal-base subtraction changed")
        _need(all(set(n) <= {"arg_type", "sub_type", "args_list"}
                  for n in _nodes(visible)), "unknown metadata on shield stack expression")
        visible_nodes.append(visible)

    action = _factory(doc)

    def ref(name):
        return _expr(100002, 6, ["INTEGER", name, "local"])

    def assign(name, value):
        return action("SET_VARIABLE", _expr(100030, 1, ["INTEGER", name, "local"]), value)

    declarations = doc["local_variable"][CAST]
    for name in (SNAPSHOT, CONSUMED):
        _need(name not in declarations["variable_length_dict"]
              and name not in cast["var_data"][1]
              and not any(name in values for values in declarations["variable_dict"].values())
              and not any(name in values for values in cast["var_data"][0].values()),
              f"local variable already exists: {name}")
        declarations["variable_dict"].setdefault("INTEGER", {})[name] = 0
        declarations["variable_length_dict"][name] = 0
        cast["var_data"][0].setdefault("INTEGER", {})[name] = 0
        cast["var_data"][1][name] = 0
        cast["var_data"][2].append(name)
    snapshot = assign(SNAPSHOT, deepcopy(visible_nodes[0]))
    reset_snapshot = assign(SNAPSHOT, _literal(0))
    reset = assign(CONSUMED, _literal(0))
    for visible in visible_nodes:
        visible.update(ref(SNAPSHOT))
    body.pop()
    def compare(name, op, value):
        return action("FLOAT_COMPARE", ref(name), _literal(op, 100015),
                      _literal(value), condition=True)

    consume_positive = _if(action, compare(SNAPSHOT, ">", 0),
                           [assign(CONSUMED, _literal(1)), clear])
    exists = action("TYPE_IS_EXIST", deepcopy(clear["args_list"][0]), condition=True)
    read_guard = _if(action, exists, [snapshot, consume_positive])
    once = _if(action, compare(CONSUMED, "==", 0), [read_guard])
    effects = _if(action, compare(CONSUMED, "==", 1), list(body))
    body[:] = [once, effects]
    index = actions.index(pick)
    actions[index:index] = [reset_snapshot, reset]
    return "At first valid leader, existence-check core then snapshot visible Shou Bei and consume once before shields; all teams use snapshot; absent/empty core or no valid leader produces no shields and no consumption."


def _all_nodes(value):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from _all_nodes(child)
    elif isinstance(value, list):
        for child in value:
            yield from _all_nodes(child)


REPAIRS = (_hz_resource, _hz_collision, _cao, _mc, _xun, _xy_core, _xy_active)


def _object(pairs):
    doc = {}
    for key, value in pairs:
        _need(key not in doc, f"duplicate JSON key: {key}")
        doc[key] = value
    return doc


def build(root: Path) -> tuple[dict[str, dict], list[dict]]:
    """Return only recognized candidate documents and per-file review notes.

    SHA256 is of original bytes, so a publisher can reject a stale candidate.
    Reports with status=review_required are NOT permission to overwrite a file.
    """
    candidates, reports = {}, []
    for relative, repair in zip(FILES, REPAIRS):
        report = {"path": relative, "group": "numeric", "phase": "P1"}
        try:
            raw = (Path(root) / relative).read_bytes()
            report["source_sha256"] = hashlib.sha256(raw).hexdigest()
            original = json.loads(raw, object_pairs_hook=_object)
            doc = deepcopy(original)
            explanation = repair(doc)
            _need(doc != original, "no reviewed change produced")
        except (OSError, ValueError, KeyError, TypeError, IndexError, StopIteration) as exc:
            report.update(status="review_required", explanation=str(exc))
        else:
            candidates[relative] = doc
            report.update(status="candidate", explanation=explanation,
                          validation="static/offline only; not loaded or combat-tested")
        reports.append(report)
    reports.append({"group": "numeric", "phase": "P1", "status": "limitation",
                    "explanation": "No ABILITY_OBTAIN coefficient setters exist in the reviewed seven ECA files. Level 1..5 setters were checked where relevant; engine obtain/level-event ordering is not assumed. No property tables, P2 lifecycle issues, editor state or live files are changed."})
    return candidates, reports

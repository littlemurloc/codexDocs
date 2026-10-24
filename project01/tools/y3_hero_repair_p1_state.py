"""Read-only P1 candidate builder for hero state (#6, #7, #13).

Only the four owned embedded-ECA documents are read. Nothing is published,
registered or reloaded. Python JSON preserves integer IDs, including >2**53.
Native evidence: 134218551 uses SET_VARIABLE(ADD_MODIFIER(...)) with actor
MODIFIER_ENTITY/sub_type=11; 134220754 uses IS_ALLY(unit, unit). Buff validity
is established by guarded unit lookup plus instance equality, not an assumed
TYPE_IS_EXIST overload for modifiers. Editor and combat verification remain open.
"""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path


FILES = (
    "modifier/134275651.json",
    "modifier/134259870.json",
    "ability/134247511.json",
    "ability/134226812.json",
)
REACHED = "\u5f53\u524d\u6b7b\u6218\u6570"
MARKED = "\u9707\u6151\u5355\u4f4d"
SOURCE = "P1_state_source"
SOURCE_CORE = "P1_state_source_core"
OWNED = "P1_state_owned_buff"
PASSIVE_OWNER = "P1_state_passive_owner"


class ReviewRequired(ValueError):
    """A native shape or dependency differs from the reviewed input."""


def _require(ok, message):
    if not ok:
        raise ReviewRequired(message)


def _walk(value):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from _walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk(child)


def _expr(kind, subtype, *args):
    return {"arg_type": kind, "sub_type": subtype, "args_list": list(args)}


def _lit(kind, value):
    return _expr(kind, 1, value)


def _unit(subtype):
    return _expr(100006, subtype)


def _buff():
    return _expr(100076, "CUR_MODIFIER")


def _lookup(unit, resource):
    return _expr(100076, "GET_LAST_MODIFIER_INSTANCE", unit, _lit(100046, resource))


def _has(unit, resource):
    return _expr(100001, "UNIT_HAS_MODIFIER", unit, _lit(100046, resource))


def _kv(kind, subtype, entity, key):
    return _expr(kind, subtype, entity, _lit(100003, key))


def _matches(actual, expected):
    # Additional metadata is retained. List length/order is semantically relevant.
    if isinstance(expected, dict):
        return isinstance(actual, dict) and all(
            key in actual and _matches(actual[key], value)
            for key, value in expected.items()
        )
    if isinstance(expected, list):
        return isinstance(actual, list) and len(actual) == len(expected) and all(
            _matches(a, b) for a, b in zip(actual, expected)
        )
    return type(actual) is type(expected) and actual == expected


def _expect(actual, expected, label):
    _require(_matches(actual, expected), "Native AST drift: " + label)


class _Nodes:
    def __init__(self, doc, resource):
        self.used = {n["element_id"] for n in _walk(doc) if "element_id" in n}
        self.serial = resource * 1_000_000 + 900_000

    def node(self, field, kind, *args):
        self.serial += 1
        while self.serial in self.used:
            self.serial += 1
        self.used.add(self.serial)
        result = {field: kind, "args_list": list(args),
                  "element_id": self.serial, "enable": True}
        if field == "action_type":
            result["bp"] = False
            if kind == "IF_THEN_ELSE":
                result["fake_op"] = []
        return result

    def action(self, kind, *args):
        return self.node("action_type", kind, *args)

    def condition(self, kind, *args):
        return self.node("condition_type", kind, *args)

    def compare(self, kind, left, operator, right):
        op_type = 100015 if kind == "FLOAT_COMPARE" else 100035
        return self.condition(kind, left, _lit(op_type, operator), right)

    def yes(self, expression):
        return self.compare("BOOL_COMPARE", expression, "==", _lit(100001, True))

    def branch(self, checks, then, otherwise=()):
        return self.action("IF_THEN_ELSE", _expr(100021, 1, *checks),
                           _expr(100022, 1, *then), _expr(100022, 1, *otherwise))

    def exists(self, unit, actions):
        _require(unit["arg_type"] == 100006, "Only verified unit existence overload used")
        return self.branch([self.condition("TYPE_IS_EXIST", unit)], actions)

    def set(self, variable, value):
        return self.action("SET_VARIABLE", copy.deepcopy(variable), value)


def _declare(doc, kind, name):
    _require(name not in doc["variable_length_dict"], "Candidate variable already exists: " + name)
    _require(all(name not in values for values in doc["variable_dict"].values()),
             "Variable name collision: " + name)
    doc["variable_dict"].setdefault(kind, {})[name] = None if kind == "MODIFIER_ENTITY" else 0
    doc["variable_length_dict"][name] = 0
    doc["variable_group_info"].append({"__tuple__": True, "items": [name, name]})
    typ = {"MODIFIER_ENTITY": 100076, "UNIT_ENTITY": 100006}[kind]
    return _expr(typ, 11, {"__tuple__": True, "items": [kind, name, "actor"]})


def _trigger(doc, tid, event):
    result = doc["trigger_dict"][str(tid)]
    _require(result["trigger_id"] == tid, "Trigger identity changed")
    _require(any(e.get("event_type") == event and e.get("enable") is True
                 for e in result["event"]), "Missing active event: " + event)
    # enabled=False is valid for a registered dynamic trigger.
    return result


def _patch_dianwei(doc, nodes):
    hp = _trigger(doc, 1418035204, "UNIT_ATTR_EVENT")
    gain = _trigger(doc, 1485688834, "OBTAIN_MODIFIER")
    layer = _trigger(doc, 104562693, "GLOBAL_MODIFIER_EVENT")
    loss = _trigger(doc, 594665475, "LOSS_MODIFIER")
    _require(gain["action"].count(1418035204) == 1 and
             gain["action"].count(104562693) == 1, "Missing dynamic registration")
    _expect(hp["event"][0], {"enable": True, "args_list": [
        _unit("MODIFIER_OWNER"), _lit(100041, "hp_cur")]}, "HP event operands")
    _expect(layer["event"][0], {"enable": True, "args_list": [
        _lit(100129, "ET_MODIFIER_LAYER_CHANGE")]}, "global layer event")
    _require(any(_matches(c, {"condition_type": "MODIFIER_COMPARE", "enable": True,
        "args_list": [_expr(100076, "GET_MODIFIER_FROM_EVENT"), _lit(100035, "=="), _buff()]})
                 for c in layer["condition"]), "Missing own-instance layer filter")
    _require(any(a.get("action_type") == "CLEAR_MODIFIER_OWNER_ATTR" and a.get("enable") is True
                 and a["args_list"] == [_buff()] for a in loss["action"] if isinstance(a, dict)),
             "Missing scoped attribute cleanup")
    _require(len(hp["action"]) == 3, "Unexpected threshold actions")
    for branch, threshold, target in zip(hp["action"], (0.75, 0.5, 0.25), (2, 3, 4)):
        _expect(branch, {"action_type": "IF_THEN_ELSE", "enable": True}, "threshold branch")
        checks = branch["args_list"][0]["args_list"]
        _require(len(checks) == 2, "Unexpected threshold checks")
        _expect(checks[0], {"condition_type": "FLOAT_COMPARE", "enable": True,
            "args_list": [_expr(100000, "GET_HP_CUR", _unit("MODIFIER_OWNER")),
                          _lit(100015, "<="),
                          _expr(100000, "ARITHMETIC_OPERATION",
                                _expr(100000, "GET_UNIT_ATTR", _unit("MODIFIER_OWNER"),
                                      _lit(100301, "ATTR_RESULT"), _lit(100042, "hp_max")),
                                _lit(100017, "*"), _lit(100000, threshold))]}, "HP threshold")
        _expect(checks[1], {"condition_type": "FLOAT_COMPARE", "enable": True,
            "args_list": [_kv(100002, "GET_INTEGER_KV", _buff(), REACHED),
                          _lit(100015, "!="), _lit(100002, target)]}, "reached threshold")
        checks[1]["args_list"][1]["args_list"][0] = "<"
        actions = branch["args_list"][1]["args_list"]
        active = [a for a in actions if a.get("enable") is True]
        _require(len(active) == 4, "Unexpected active threshold payload")
        set_stack, set_reached = active[:2]
        _expect(set_stack, {"action_type": "SET_BUFF_STACK", "args_list": [_buff(), _lit(100002, target)]}, "set stack")
        _expect(set_reached, {"action_type": "SET_ENTITY_KV", "args_list": [_buff(), _lit(100003, REACHED), _lit(100002, target)]}, "set reached")
        # Commit the watermark before actions that can cause nested events.
        i, j = actions.index(set_stack), actions.index(set_reached)
        actions[i], actions[j] = actions[j], actions[i]

    _require(len(layer["action"]) == 2, "Unexpected layer response")
    branch = layer["action"][1]
    _expect(branch, {"action_type": "IF_THEN_ELSE", "enable": True}, "layer branch")
    _expect(branch["args_list"][0]["args_list"], [{"condition_type": "FLOAT_COMPARE", "enable": True,
        "args_list": [_expr(100002, "GET_MODIFIER_LAYER_CHANGE_VALUE"),
                      _lit(100015, ">"), _lit(100000, 0.0)]}], "layer direction")
    for branch_index, negative in ((1, False), (2, True)):
        attrs = branch["args_list"][branch_index]["args_list"]
        _require(len(attrs) == 3, "Unexpected attribute contributions")
        for action, attr, rate in zip(attrs, ("attack_phy", "attack_speed", "ori_speed"), (5, 10, 10)):
            _expect(action, {"action_type": "ADD_MODIFIER_OWNER_ATTR", "enable": True,
                "args_list": [_buff(), _lit(100042, attr), _lit(100300, "ATTR_ALL_RATIO"), {}]}, "attribute action")
            magnitude = action["args_list"][3]
            if negative:
                _expect(magnitude, _expr(100000, "ARITHMETIC_OPERATION", {}, _lit(100017, "*"), _lit(100000, -1.0)), "negative contribution")
                magnitude["args_list"][2]["args_list"][0] = 1.0
                magnitude = magnitude["args_list"][0]
            _expect(magnitude, _expr(100000, "ARITHMETIC_OPERATION", _lit(100002, rate), _lit(100017, "*"),
                    _expr(100002, "MATH_OPERATION", _expr(100002, "GET_MOD_STACK", _buff()),
                          _lit(100016, "-"), _lit(100002, 1))), "old total-layer contribution")
            total = magnitude["args_list"][2]
            stack = total["args_list"][0]
            # The operand being removed must not carry unreviewed user data.
            _require(stack["args_list"] == [_buff()], "Unknown stack operand metadata")
            stack["sub_type"] = "GET_MODIFIER_LAYER_CHANGE_VALUE"
            stack["args_list"] = []
            total["args_list"][2]["args_list"][0] = 0
    gain["action"].insert(0, nodes.action("SET_ENTITY_KV", _buff(), _lit(100003, REACHED), _lit(100002, 1)))


def _same_live_buff(nodes, unit, resource, saved, actions):
    """No dereference of saved until a valid lookup has proved identity."""
    same = nodes.compare("MODIFIER_COMPARE", copy.deepcopy(saved), "==", _lookup(copy.deepcopy(unit), resource))
    return nodes.exists(copy.deepcopy(unit), [
        nodes.branch([nodes.yes(_has(copy.deepcopy(unit), resource))],
                     [nodes.branch([same], actions)])
    ])


def _patch_zhangliao(doc, nodes):
    damage = _trigger(doc, 512499716, "SPECIAL_UNIT_EVENT")
    gain = _trigger(doc, 1625518081, "OBTAIN_MODIFIER")
    loss = _trigger(doc, 1726324738, "LOSS_MODIFIER")
    _expect(gain["action"], [512499716], "damage listener registration")
    _expect(damage["event"][0], {"enable": True, "args_list": [
        _unit("MODIFIER_OWNER"), _lit(100007, "ET_UNIT_HURT_OTHER")]}, "outgoing damage event")
    _require(len(damage["action"]) == 1 and len(loss["action"]) == 2, "Unexpected intimidation actions")
    change = damage["action"][0]
    _expect(change, {"action_type": "SET_CUR_DAMAGE", "element_id": 512499716810154, "enable": True}, "damage write")
    formula = _expr(100000, "ARITHMETIC_OPERATION", _expr(100000, "HURT_DAMAGE"), _lit(100017, "*"),
        _expr(100000, "ARITHMETIC_OPERATION", _lit(100000, 1.0), _lit(100017, "-"),
              _expr(100000, "ARITHMETIC_OPERATION", _lit(100000, -0.04), _lit(100017, "*"),
                    _expr(100002, "GET_MOD_STACK", _buff()))))
    _expect(change["args_list"], [formula], "intimidation sign")
    change["args_list"][0]["args_list"][2]["args_list"][2]["args_list"][0]["args_list"][0] = 0.04
    reset = loss["action"][0]
    _expect(reset, {"action_type": "SET_BUFF_STACK", "element_id": 1726324738810133, "enable": True,
        "args_list": [_lookup(_unit("MODIFIER_RELEASER"), 134259689), _lit(100002, 1)]}, "historical LOSS reset")
    _require(reset["args_list"][0] == _lookup(_unit("MODIFIER_RELEASER"), 134259689),
             "Unreviewed LOSS lookup metadata would be displaced")
    source = _declare(doc, "UNIT_ENTITY", SOURCE)
    core = _declare(doc, "MODIFIER_ENTITY", SOURCE_CORE)
    gain["action"][0:0] = [
        nodes.set(source, _unit("MODIFIER_RELEASER")),
        nodes.exists(copy.deepcopy(source), [nodes.branch([nodes.yes(_has(copy.deepcopy(source), 134259689))],
            [nodes.set(core, _lookup(copy.deepcopy(source), 134259689))])]),
    ]
    target = _unit("DAMAGE_TARGET_UNIT")
    allowed = [nodes.compare("UNIT_COMPARE", copy.deepcopy(target), "!=", copy.deepcopy(source)),
               nodes.yes(_expr(100001, "IS_ALLY", copy.deepcopy(source), copy.deepcopy(target)))]
    damage["action"] = [nodes.exists(copy.deepcopy(source), [nodes.exists(target,
        [nodes.branch(allowed, [change])])])]
    reset["args_list"][0] = copy.deepcopy(core)
    marked = _kv(100006, "GET_UNIT_ENTITY_KV", copy.deepcopy(core), MARKED)
    clear = nodes.action("SET_ENTITY_KV", copy.deepcopy(core), _lit(100003, MARKED), _unit("NONE_UNIT"))
    guarded_reset = nodes.branch([nodes.condition("HAS_KV_ANY", copy.deepcopy(core), _lit(100003, MARKED))], [
        nodes.branch([nodes.compare("UNIT_COMPARE", marked, "==", _unit("MODIFIER_OWNER"))], [reset, clear])
    ])
    loss["action"][0] = _same_live_buff(nodes, source, 134259689, core, [guarded_reset])


def _patch_passive(doc, nodes):
    phase = _trigger(doc, 892944388, "RECEIVE_CUSTOM_EVENT")
    gain = _trigger(doc, 1959489540, "ABILITY_OBTAIN")
    loss = _trigger(doc, 225054724, "ABILITY_LOSE")
    _expect(gain["action"], [892944388], "passive phase registration")
    _require(len(phase["action"]) == 1, "Unexpected passive phase payload")
    branch = phase["action"][0]
    _expect(branch, {"action_type": "IF_THEN_ELSE", "element_id": 892944388000011, "enable": True}, "passive branch")
    checks, yes, no = branch["args_list"]
    _require(len(checks["args_list"]) == 2, "Unexpected passive checks")
    applicability, absent = checks["args_list"]
    _expect(applicability, {"condition_type": "OR", "enable": True}, "applicability")
    owner = _unit("ABILITY_OWNER")
    _expect(absent, {"condition_type": "BOOL_NOT", "enable": True,
                    "args_list": [_has(owner, 134279904)]}, "missing passive buff")
    _require(len(yes["args_list"]) == len(no["args_list"]) == 1, "Unexpected passive branches")
    add, remove = yes["args_list"][0], no["args_list"][0]
    _expect(add, {"action_type": "ADD_MODIFIER", "enable": True,
        "args_list": [owner, _lit(100046, 134279904)],
        "op_arg": [owner, _expr(100014, "CUR_ABILITY"), None, None, None, None],
        "op_arg_enable": [True, True, False, False, False, False]}, "owned passive creation")
    _expect(remove, {"action_type": "REMOVE_BUFF_INS", "enable": True, "element_id": 892944388000015,
                    "args_list": [_lookup(owner, 134279904)]}, "historical null removal")
    _require(remove["args_list"][0] == _lookup(owner, 134279904),
             "Unreviewed removal lookup metadata would be displaced")
    saved = _declare(doc, "MODIFIER_ENTITY", OWNED)
    saved_owner = _declare(doc, "UNIT_ENTITY", PASSIVE_OWNER)
    created = _expr(100076, "ADD_MODIFIER", *copy.deepcopy(add["args_list"]))
    for key in ("op_arg", "op_arg_enable"):
        created[key] = add.pop(key)
    add["action_type"] = "SET_VARIABLE"
    add["args_list"] = [copy.deepcopy(saved), created]
    remove["args_list"][0] = copy.deepcopy(saved)
    checks["args_list"] = [applicability]
    yes["args_list"] = [nodes.branch([absent], [nodes.set(saved_owner, copy.deepcopy(owner)), add])]
    no["args_list"] = [_same_live_buff(nodes, owner, 134279904, saved, [remove])]
    phase["action"] = [nodes.exists(owner, [branch])]
    # Loss uses the saved carrier, not event-specific ABILITY_OWNER availability.
    cleanup = nodes.action("REMOVE_BUFF_INS", copy.deepcopy(saved))
    loss["action"].insert(0, _same_live_buff(nodes, saved_owner, 134279904, saved, [cleanup]))


def _unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ReviewRequired("Duplicate JSON key: " + key)
        result[key] = value
    return result


def build(root: Path) -> tuple[dict[str, dict], list[dict]]:
    """Return candidates and diagnostics; never write root or another path."""
    root = Path(root)
    candidates, reports = {}, []
    patchers = (_patch_dianwei, _patch_zhangliao, _patch_passive, _patch_passive)
    for relative, patch in zip(FILES, patchers):
        try:
            raw = (root / relative).read_bytes()
            doc = json.loads(raw.decode("utf-8-sig"), object_pairs_hook=_unique,
                             parse_constant=lambda value: (_ for _ in ()).throw(ReviewRequired("Nonfinite JSON: " + value)))
            resource = int(Path(relative).stem)
            nodes = _Nodes(doc, resource)
            patch(doc, nodes)
        except (OSError, UnicodeError, ValueError, KeyError, TypeError, IndexError) as error:
            reports.append({"path": relative, "severity": "error", "code": "review_required",
                            "message": str(error), "candidate_omitted": True})
            continue
        candidates[relative] = doc
        reports.append({"path": relative, "severity": "info", "code": "p1_state_candidate",
                        "source_sha256": hashlib.sha256(raw).hexdigest(),
                        "message": {134275651: "Monotonic reached thresholds; signed layer delta (5/10/10 percent points); base1; scoped LOSS clear retained.",
                                    134259870: "Damage *= 1-0.04*layer only for source allies other than source; LOSS guards source/core identity and marked target.",
                                    134247511: "Separate applicability from absence; cache created instance; remove only owned current instance, including ability loss.",
                                    134226812: "Separate applicability from absence; cache created instance; remove only owned current instance, including ability loss."}[resource]})
    reports.append({"severity": "warning", "code": "verification_boundary",
                    "message": "P1 candidate only. No live writes, import, save, reload or P2. Native structure/offline tests do not certify editor/runtime behavior; buff cover/creation callbacks and wave teardown ordering require engine tests. Other source-core targeting/timing defects are outside these four documents."})
    return candidates, reports

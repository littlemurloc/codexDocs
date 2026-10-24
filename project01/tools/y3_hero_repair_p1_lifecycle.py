"""Read-only P1 #11/#12 candidate builder. No publishing, reload, or P2 work.

Native evidence (map3): modifier/134277037 RUN_ONCE_TIMER + DELETE_TIMER,
TYPE_IS_EXIST(CUR_MODIFIER()) inside its callback; modifier/134273470 actor
MODIFIER_ENTITY variables; modifier/134255911 SET_VARIABLE(100030/1, CUR_MODIFIER)
and modifier/134250273 local MODIFIER_ENTITY left value 100030/1;
ability/134219973 writes a trigger-declared local inside a chasing callback
while its mover local_var remains ({}, {}), as used for the hit-time snapshot;
modifier/134275651 MODIFIER_COMPARE; mirror cleanup
02 sets current phase to -2 before deleting units; AI behavior uses phase 2;
Shu function 15 reads the real wave number. Actor fields belong to the modifier
instance. No invented timer-local capture encoding is introduced: the saved
timer retains its native modifier context, with explicit old-instance checks.

Only build() reads input. It returns detached Python JSON documents, never
writes files. Unknown/disabled/changed anchors are review errors, not guesses.
Editor loading and actual engine lifecycle semantics remain unverified.
"""

from __future__ import annotations

import argparse
from copy import deepcopy
import json
from pathlib import Path


FILES = (
    "ability/134275696.json",
    "modifier/134277456.json",
    "modifier/134232159.json",
)
OPTIONAL = "ability/134237143.json"
CD = "\u5185\u7f6eCD"
PHASE = "\u5f53\u524d\u6e38\u620f\u8fdb\u7a0b\u9636\u6bb5"
WAVE = "\u5f53\u524d\u8fdb\u7a0b\u6240\u5728\u6ce2\u6b21\u7f16\u53f7"
PREFIX = "P1_lifecycle_"


class ReviewError(ValueError):
    """The source no longer matches the reviewed native execution path."""


def expr(kind, subtype=1, *args):
    return {"arg_type": kind, "args_list": list(args), "sub_type": subtype}


def var(kind, name, scope="actor", target=False):
    types = {"MODIFIER_ENTITY": (100076, 11), "UNIT_ENTITY": (100006, 11),
             "BOOLEAN": (100001, "VARIABLE"), "INTEGER": (100002, 6),
             "NEW_TIMER": (100181, "VARIABLE")}
    arg_type, subtype = types[kind]
    if target and kind != "NEW_TIMER":
        arg_type, subtype = 100030, 1
    items = [kind, name] + ([scope] if scope else [])
    return expr(arg_type, subtype, {"__tuple__": True, "items": items})


def cur():
    return expr(100076, "CUR_MODIFIER")


def lookup(owner, key):
    return expr(100076, "GET_LAST_MODIFIER_INSTANCE", deepcopy(owner), expr(100046, 1, key))


def walk(node):
    if isinstance(node, dict):
        yield node
        for value in node.values():
            yield from walk(value)
    elif isinstance(node, list):
        for value in node:
            yield from walk(value)


def require(ok, message):
    if not ok:
        raise ReviewError(message)


class Edit:
    def __init__(self, doc):
        self.doc = doc
        self.next_id = max((n["element_id"] for n in walk(doc)
                            if isinstance(n.get("element_id"), int)), default=0)

    def node(self, category, name, *args):
        self.next_id += 1
        out = {category: name, "args_list": list(args),
               "element_id": self.next_id, "enable": True}
        if category == "action_type":
            out["bp"] = False
        return out

    def act(self, name, *args):
        return self.node("action_type", name, *args)

    def cond(self, name, *args):
        return self.node("condition_type", name, *args)

    def exists(self, value):
        return self.cond("TYPE_IS_EXIST", deepcopy(value))

    def compare(self, name, left, right):
        return self.cond(name, deepcopy(left), expr(100035, 1, "=="), deepcopy(right))

    def integer_eq(self, left, right):
        return self.cond("FLOAT_COMPARE", deepcopy(left), expr(100015, 1, "=="), deepcopy(right))

    def guard(self, stages, actions):
        # Independent checks share a stage; only dereference boundaries nest.
        # Every condition in a stage must be safe even without short-circuiting.
        result = list(actions)
        for stage in reversed(stages):
            conditions = stage if isinstance(stage, list) else [stage]
            result = [self.act("IF_THEN_ELSE", expr(100021, 1, *conditions),
                               expr(100022, 1, *result), expr(100022, 1))]
        return result

    def set(self, kind, name, value, scope="actor"):
        return self.act("SET_VARIABLE", var(kind, name, scope, target=True), deepcopy(value))

    def declare(self, kind, name, default, trigger=None):
        if trigger is None:
            data = self.doc
            require(not any(name in values for values in data["variable_dict"].values()),
                    "reserved actor variable already exists: " + name)
            require(name not in data["variable_length_dict"], "variable length collision: " + name)
            data["variable_dict"].setdefault(kind, {})[name] = default
            data["variable_length_dict"][name] = 0
            data["variable_group_info"].append({"__tuple__": True, "items": [name, name]})
        else:
            data = self.doc["local_variable"][str(trigger)]
            t = self.doc["trigger_dict"][str(trigger)]
            require(not any(name in values for values in data["variable_dict"].values()),
                    "reserved local variable already exists: " + name)
            require(name not in data["variable_length_dict"], "local length collision: " + name)
            require(not any(name in values for values in t["var_data"][0].values()),
                    "var_data collision: " + name)
            data["variable_dict"].setdefault(kind, {})[name] = default
            data["variable_length_dict"][name] = 0
            t["var_data"][0].setdefault(kind, {})[name] = default
            t["var_data"][1][name] = 0
            t["var_data"][2].append(name)


def trigger(doc, key, event):
    t = doc["trigger_dict"][str(key)]
    require(t.get("valid") is True and t.get("call_enabled") is True,
            f"trigger {key} invalid/disabled for calls")
    require(any(e.get("event_type") == event and e.get("enable") is True
                for e in t["event"]), f"trigger {key}: event changed")
    if t.get("enabled") is not True:
        parent = doc["trigger_dict"].get(str(t.get("p_trigger_id")), {})
        require(key in parent.get("action", []) and
                t.get("sub_trigger_owner_set_var_action", {}).get("enable") is True,
                f"dynamic trigger {key} registration changed")
    return t


def anchor(container, element_id, name):
    matches = [n for n in walk(container) if n.get("element_id") == element_id
               and n.get("action_type") == name]
    require(len(matches) == 1, f"ambiguous/missing {name} #{element_id}")
    n = matches[0]
    require(n.get("enable") is True, f"disabled anchor #{element_id}: preserve for review")
    def active_path(value, enabled=True):
        if isinstance(value, dict):
            enabled = enabled and value.get("enable") is not False
            if value is n:
                return enabled
            for child in value.values():
                result = active_path(child, enabled)
                if result is not None:
                    return result
        elif isinstance(value, list):
            for child in value:
                result = active_path(child, enabled)
                if result is not None:
                    return result
        return None
    require(active_path(container) is True, f"disabled ancestor of anchor #{element_id}")
    return n


def splice(actions, old, replacement):
    require(old in actions, "anchor moved outside reviewed direct action sequence")
    i = next(i for i, n in enumerate(actions) if n is old)
    actions[i:i + 1] = replacement


def _ability(doc):
    e = Edit(doc)
    t = trigger(doc, 893440004, "ABILITY_SP_END")
    mover = anchor(t["action"], 893440004975299, "CREATE_CHASING_MOVER")
    body = mover["args_list"][5]["args_list"]
    damage = anchor(body, 893440004975596, "APPLY_DAMAGE")
    remove = anchor(body, 893440004976354, "REMOVE_BUFF_INS")
    reset = anchor(body, 893440004976362, "SET_BUFF_STACK")
    owner = expr(100006, "ABILITY_OWNER")
    target = remove["args_list"][0]["args_list"][0]
    require(remove["args_list"] == [lookup(target, 134274015)], "war-letter lookup changed")
    require(reset["args_list"][0] == lookup(owner, 134277456), "core reset lookup changed")
    require(body.index(damage) < body.index(remove) < body.index(reset), "damage/cleanup order changed")
    old_name = PREFIX + "hit_core"
    e.declare("MODIFIER_ENTITY", old_name, 0, 893440004)
    old = var("MODIFIER_ENTITY", old_name, "local")
    # Capture inside the mover callback, before synchronous damage/death reentry.
    # This adds no variables crossing a timer/mover closure boundary.
    body[0:0] = e.guard([e.exists(owner)], [
        e.set("MODIFIER_ENTITY", old_name, lookup(owner, 134277456), "local")])
    letter = remove["args_list"][0]
    splice(body, remove, e.guard([
        [e.exists(owner), e.exists(target)], [e.exists(letter)],
        [e.compare("UNIT_COMPARE", expr(100006, "GET_BUFF_SOURCE", deepcopy(letter)), owner)],
    ], [remove]))
    reset["args_list"][0] = deepcopy(old)
    splice(body, reset, e.guard([
        [e.exists(owner), e.exists(old)],
        [e.compare("MODIFIER_COMPARE", lookup(owner, 134277456), old)],
    ], [reset]))


def _core(doc):
    e = Edit(doc)
    obtain = trigger(doc, 1485688834, "OBTAIN_MODIFIER")
    loss = trigger(doc, 594665475, "LOSS_MODIFIER")
    hurt = trigger(doc, 1418035204, "SPECIAL_UNIT_EVENT")
    death = trigger(doc, 1473785861, "GENERIC_UNIT_EVENT")
    timer = anchor(hurt["action"], 1418035204974513, "RUN_ONCE_TIMER_NO_SAVE")
    require(timer["args_list"][0] == expr(100000, 1, 8.0), "eight-second duration changed")
    callback = timer["args_list"][1]["args_list"]
    reset = anchor(callback, 1473785861000046, "SET_BUFF_STACK")
    clear = anchor(callback, 1418035204974592, "SET_ENTITY_KV")
    require([a for a in callback if a.get("enable") is not False] == [reset, clear],
            "timer has additional/reordered active callback actions; review instead of relocating")
    owner = expr(100006, "MODIFIER_OWNER")
    require(reset["args_list"][0] == lookup(owner, 134277456), "timer core lookup changed")
    require(clear["args_list"] == [cur(), expr(100003, 1, CD), expr(100001, 1, False)],
            "timer CD write changed")
    old_name, active_name, pending_name, timer_name = (
        PREFIX + x for x in ("core_instance", "core_active", "timer_pending", "eight_seconds"))
    for kind, name, default in [("MODIFIER_ENTITY", old_name, 0),
                                ("BOOLEAN", active_name, False),
                                ("BOOLEAN", pending_name, False),
                                ("NEW_TIMER", timer_name, -1)]:
        e.declare(kind, name, default)
    old = var("MODIFIER_ENTITY", old_name)
    handle = var("NEW_TIMER", timer_name)

    def bound(pending=False):
        identities = [e.compare("MODIFIER_COMPARE", cur(), old),
                      e.compare("BOOL_COMPARE", var("BOOLEAN", active_name), expr(100001, 1, True)),
                      e.exists(owner)]
        if pending:
            identities.append(e.compare("BOOL_COMPARE", var("BOOLEAN", pending_name), expr(100001, 1, True)))
        return [[e.exists(cur()), e.exists(old)], identities,
                [e.compare("MODIFIER_COMPARE", lookup(owner, 134277456), old)]]

    obtain["action"][0:0] = [e.set("MODIFIER_ENTITY", old_name, cur()),
                            e.set("BOOLEAN", active_name, expr(100001, 1, True)),
                            e.set("BOOLEAN", pending_name, expr(100001, 1, False))]
    loss["action"][0:0] = [e.set("BOOLEAN", active_name, expr(100001, 1, False)),
                          e.set("BOOLEAN", pending_name, expr(100001, 1, False)),
                          e.act("DELETE_TIMER", deepcopy(handle))]
    # Death ends this window too; an old expiry must not reset a later window.
    death["action"][0:0] = [e.set("BOOLEAN", pending_name, expr(100001, 1, False)),
                           e.act("DELETE_TIMER", deepcopy(handle))]
    reset["args_list"][0] = deepcopy(old)
    clear["args_list"][0] = deepcopy(old)
    splice(callback, reset, e.guard(bound(pending=True), [reset]))
    # SET_BUFF_STACK can synchronously run layer-change ECA: revalidate again.
    splice(callback, clear, e.guard(bound(pending=True), [
        e.set("BOOLEAN", pending_name, expr(100001, 1, False)), clear]))
    payload = deepcopy(timer["args_list"][1])
    payload["args_list"] = callback
    timer["action_type"] = "RUN_ONCE_TIMER"
    timer["args_list"] = [deepcopy(handle), deepcopy(timer["args_list"][0]), payload]
    timer.setdefault("local_var", {"__tuple__": True, "items": [{}, {}]})
    # Preserve timer metadata and disabled callback actions verbatim.
    splice(hurt["action"], timer, e.guard(bound(), [
        e.act("DELETE_TIMER", deepcopy(handle)),
        e.set("BOOLEAN", pending_name, expr(100001, 1, True)), timer]))


def _pursuit(doc):
    e = Edit(doc)
    obtain = trigger(doc, 1485688834, "OBTAIN_MODIFIER")
    loss = trigger(doc, 594665475, "LOSS_MODIFIER")
    add = anchor(loss["action"], 1418035204974461, "ADD_BUFF_STACK")
    clear = anchor(loss["action"], 1418035204974592, "SET_ENTITY_KV")
    source = expr(100006, "MODIFIER_RELEASER")
    require(add["args_list"][0] == lookup(source, 134282266), "pursuit source lookup changed")
    require(clear["args_list"] == [lookup(source, 134282266), expr(100003, 1, CD),
                                    expr(100001, 1, False)], "pursuit CD write changed")
    source_name, core_name, wave_name = (PREFIX + x for x in ("source", "source_core", "wave"))
    for kind, name in [("UNIT_ENTITY", source_name), ("MODIFIER_ENTITY", core_name),
                       ("INTEGER", wave_name)]:
        e.declare(kind, name, 0)
    saved_source = var("UNIT_ENTITY", source_name)
    saved_core = var("MODIFIER_ENTITY", core_name)
    wave = var("INTEGER", WAVE, "")
    phase = var("INTEGER", PHASE, "")
    obtain["action"][0:0] = [
        e.set("INTEGER", wave_name, wave),
        e.set("UNIT_ENTITY", source_name, source),
        *e.guard([e.exists(saved_source)], [
            e.set("MODIFIER_ENTITY", core_name, lookup(saved_source, 134282266))]),
    ]

    def bound():
        return [[e.integer_eq(phase, expr(100002, 1, 2)),
                 e.integer_eq(wave, var("INTEGER", wave_name))],
                [e.exists(saved_source), e.exists(saved_core)],
                [e.compare("UNIT_COMPARE", source, saved_source),
                 e.compare("MODIFIER_COMPARE", lookup(saved_source, 134282266), saved_core)]]

    add["args_list"][0] = deepcopy(saved_core)
    clear["args_list"][0] = deepcopy(saved_core)
    splice(loss["action"], add, e.guard(bound(), [add]))
    splice(loss["action"], clear, e.guard(bound(), [clear]))
    # SFX cleanup stays outside the reward guards and is never skipped.


def _optional(doc):
    t = trigger(doc, 1340796934, "SPECIAL_UNIT_EVENT")
    callback = anchor(t["action"], 1340796934000042, "SET_ENTITY_KV")
    require(callback["args_list"] == [expr(100006, "ABILITY_OWNER"),
                                       expr(100003, 1, CD), expr(100001, 1, False)],
            "logged Huang Zhong callback has changed")


def build(root: Path) -> tuple[dict[str, dict], list[dict]]:
    """Return only reviewed candidates; each failure is isolated per object."""
    root = Path(root)
    candidates, issues = {}, []
    explanations = (
        "After damage, recheck target/war-letter existence and source before removal. "
        "Snapshot core inside the hit callback before damage and reset only that still-current instance.",
        "Bind obtain-time core, replace anonymous 8-second timer with a saved handle, "
        "cancel on loss/death/new window, validate identity/active state at expiry, "
        "and revalidate before CD write after stack-change reentry.",
        "Snapshot source/core/real wave on obtain. LOSS grants +1 and clears CD only "
        "in battle phase 2, same wave, same valid source/core; recheck before each write. "
        "SFX cleanup remains unconditional.",
    )
    for rel, repair, case, explanation in zip(FILES, (_ability, _core, _pursuit),
                                             ("P1#11", "P1#12", "P1#12"), explanations):
        try:
            doc = json.loads((root / rel).read_text(encoding="utf-8-sig"))
            patched = deepcopy(doc)
            repair(patched)
            candidates[rel] = patched
            issues.append({"file": rel, "case": case, "status": "candidate",
                           "explanation": explanation,
                           "validation": "offline candidate; not editor/runtime verified"})
        except (OSError, ValueError, KeyError, TypeError, IndexError, AttributeError) as exc:
            issues.append({"file": rel, "case": case, "status": "review_required",
                           "explanation": str(exc)})
    try:
        _optional(json.loads((root / OPTIONAL).read_text(encoding="utf-8-sig")))
        reason = ("Additional logged item: trigger 1340796934 / element 1340796934000042 "
                  "uses ABILITY_OWNER in a 3-second callback. No patch: CD is written on "
                  "the owner but read on CUR_ABILITY by trigger 2111275013; ownership "
                  "and reset-on-loss policy require review before changing behavior.")
    except (OSError, ValueError, KeyError, TypeError, IndexError, AttributeError) as exc:
        reason = "Additional Huang Zhong item not patched: " + str(exc)
    issues.append({"file": OPTIONAL, "case": "additional", "status": "review_required",
                   "explanation": reason})
    return candidates, issues


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    args = parser.parse_args()
    docs, findings = build(args.root)
    print(json.dumps({"documents": docs, "issues": findings}, ensure_ascii=True, indent=2))

"""Improve the primary roster action and restore complete mouse placement."""

import argparse
import copy
import json

import y3_safezone_ui_polish as release


b = release.ui
WORK = b.ROOT / "tmp/safezone-formation-mouse-20261120"
REGISTER = b.FD + "刷新安全区队长9宫格点击UI界面事件.json"
FILES = (b.UI, REGISTER, b.OLD)
PICK, DROP, ESC = "117711631", "1465037587", "2101119701"
GRID = "d6b92c2c-92a1-4cdb-9370-62f7211a151f"
SOURCE_KEY = "安全区摆阵_源阵位"
GHOST = b.uid("formation-mouse/portrait")
HINT = b.uid("roster/formation-hint")
IDLE_HINT = "左键点武将拾取，再点目标阵位放下\n右键或 Esc 取消"
PICKED_HINT = "已拾取武将，点击目标阵位放下\n空位移动，已有武将则交换"


def by_id(doc, element_id):
    matches = [n for n in b.walk(doc) if n.get("element_id") == element_id]
    if len(matches) != 1:
        raise ValueError(f"Expected one ECA node {element_id}; found {len(matches)}")
    return matches[0]


def style_canvas(doc):
    hero = b.find_uid(doc, b.DETAIL)
    action = b.find_uid(hero, b.uid("roster/deploy"))
    release.place(hero, action, 581, 533, 154, 50)
    action["font"] = b.tup("MSYH", 23)
    states = {
        "normal": ((40, 99, 79, 255), (255, 248, 219, 255)),
        "suspend": ((54, 125, 94, 255), (255, 251, 231, 255)),
        "press": ((29, 75, 59, 255), (255, 248, 219, 255)),
        "disabled": ((244, 242, 235, 255), (88, 88, 79, 255)),
    }
    for state, (tint, ink) in states.items():
        action[state + "_color"] = b.tup(*tint)
        action[state + "_font_color"] = b.tup(*ink)
    status = b.find_uid(hero, b.uid("roster/state"))
    release.place(hero, status, 421, 535, 151, 26)
    formation = b.at(b.find_uid(doc, b.CONTENT), "右侧区域.上阵面板")
    hint = b.find_uid(formation, HINT)
    hint["text"] = b.tup(IDLE_HINT, False)
    grid = b.find_uid(formation, GRID)
    for index, cell in enumerate(grid["children"], 1):
        frame = b.child(cell, "frameIMG")
        frame["swallow_touches"] = True
        b.child(frame, "numIMG")["swallow_touches"] = False
        b.child(frame, "阵位编号")["swallow_touches"] = False
        border = release.detail.image("摆阵选中", f"formation-mouse/frame/{index}",
                                      904162, 60, 60, 116, 116, (16, 16, 16, 16))
        release.place(frame, border, 60, 60, 116, 116)
        border.update(visible=False, swallow_touches=False, size_adaptive=False)
        frame["children"].insert(0, border)
    ghost = release.detail.image("摆阵跟鼠头像", "formation-mouse/portrait", 999, 270, 360, 72, 72)
    release.place(formation, ghost, 270, 360, 72, 72)
    ghost.update(uid=GHOST, swallow_touches=False, size_adaptive=False, is_scale9_enable=False)
    formation["children"].append(ghost)
    return doc


def full_cell_events(doc):
    for node in b.walk(doc):
        if node.get("action_type") in ("DEL_UI_COMP_EVENT", "CREATE_UI_COMP_EVENT_EX_EX"):
            path = node["args_list"][0]["args_list"][2]
            old = path["op_arg"][0]["args_list"]
            assert old == [".frameIMG.numIMG"]
            old[0] = ".frameIMG"
    return doc


def placement_flow(doc):
    nodes = b.Nodes(2101124100)
    init = by_id(doc["action"], 117711631000027)
    assert init["args_list"][1]["sub_type"] == "CREATE_UI_COMP"
    init["args_list"][1] = b.u(GHOST)
    by_id(doc["action"], 117711631000010)["args_list"][2] = b.boolean(False)
    ghost_size = by_id(doc["action"], 117711631000058)
    ghost_size["args_list"][2:] = [b.lit(100000, 72.0), b.lit(100000, 72.0)]

    pick, drop, esc = (doc["sub_trigger"][key] for key in (PICK, DROP, ESC))
    p, ghost = drop["action"][1]["args_list"]
    state_target, none = drop["action"][2]["args_list"]
    selected = drop["condition"][0]["args_list"][0]
    whose_slot = b.kv(p, SOURCE_KEY)
    event_slot = drop["action"][0]["args_list"][0]["args_list"][2]
    original_pick = {n["element_id"]: n for n in pick["action"]}
    read_unit = original_pick[117711631000628]["args_list"][1]
    lookup_fid = read_unit["sub_type"]
    router = drop["action"][3]["args_list"][0]["sub_type"]

    def highlight(slot):
        return b.s.path(p, GRID, b.join("格子", b.join(b.intstr(slot), ".frameIMG.摆阵选中")))

    def stop():
        return [
            nodes.act("CLEAR_UI_COMP_IMAGE", p, ghost),
            nodes.act("SET_UI_COMP_FOLLOW_MOUSE", p, ghost, b.boolean(False)),
            nodes.act("SET_VARIABLE", state_target, none),
            nodes.put(p, SOURCE_KEY, b.integer(0)),
            nodes.label(p, HINT, IDLE_HINT),
            nodes.call(router, p, b.boolean(True)),
        ]

    def hide_source():
        return nodes.branch([nodes.cmp(whose_slot, ">=", b.integer(1)),
                             nodes.cmp(whose_slot, "<=", b.integer(9))],
                            [nodes.vis(p, highlight(whose_slot), False)])

    def delete_this_timer():
        return nodes.act("DELETE_TIMER", b.ex(100181, "CURRENT_EXPIRED_TIMER"))

    timer = original_pick[117711631000179]
    loop = next(x for x in timer["args_list"] if isinstance(x, dict) and x.get("arg_type") == 100022)
    outside, right = loop["args_list"]
    for branch in (outside, right):
        branch["args_list"][1]["args_list"] = [hide_source(), *stop(), delete_this_timer()]
    outside["args_list"][2]["args_list"] = [right]
    loop["args_list"] = [
        nodes.branch([nodes.cmp(selected, "==", none, "UNIT_CLASS_COMPARE")],
                     [delete_this_timer()], [outside])
    ]
    pick["action"] = [
        nodes.branch([nodes.cmp(selected, "==", none, "UNIT_CLASS_COMPARE"),
                      nodes.cmp(read_unit, "!=", none, "UNIT_CLASS_COMPARE")], [
            original_pick[117711631000628],
            original_pick[117711631000142],
            original_pick[117711631000042],
            nodes.put(p, SOURCE_KEY, event_slot),
            nodes.vis(p, highlight(event_slot), True),
            nodes.label(p, HINT, PICKED_HINT),
            original_pick[117711631000111],
            original_pick[117711631000619],
            timer,
        ]),
    ]

    lookup = b.foreign(lookup_fid, 100002, whose_slot, p)
    unit_at_source = copy.deepcopy(read_unit)
    unit_at_source["args_list"][0] = whose_slot
    move = drop["action"][0]
    move["args_list"][0]["args_list"][1] = lookup
    drop["action"] = [
        hide_source(),
        nodes.branch([nodes.cmp(whose_slot, ">=", b.integer(1)),
                      nodes.cmp(whose_slot, "<=", b.integer(9)),
                      nodes.cmp(event_slot, ">=", b.integer(1)),
                      nodes.cmp(event_slot, "<=", b.integer(9)),
                      nodes.cmp(event_slot, "!=", whose_slot),
                      nodes.cmp(unit_at_source, "==", selected, "UNIT_CLASS_COMPARE")],
                     [move]),
        *stop(),
    ]
    # The Esc listener's existing condition may require a visible detail popup.
    old_conditions = esc["condition"]
    old_actions = esc["action"]
    esc["condition"] = []
    cancel = nodes.branch([nodes.cmp(selected, "!=", none, "UNIT_CLASS_COMPARE")],
                          [hide_source(), *stop()])
    esc["action"] = [nodes.branch(old_conditions, old_actions), cancel] if old_conditions else [*old_actions, cancel]
    return doc


def stage():
    transforms = (style_canvas, full_cell_events, placement_flow)
    manifest = {}
    for path, transform in zip(FILES, transforms, strict=True):
        before = (b.PROJECT / path).read_bytes()
        after = b.encode(transform(json.loads(before)))
        assert before != after
        for section, raw in (("before", before), ("candidate", after)):
            target = WORK / section / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(raw)
        manifest[path] = {"before": b.sha(before), "candidate": b.sha(after)}
    (WORK / "manifest.json").write_bytes(b.encode(manifest))
    print("Staged: safety-zone canvas, formation event bindings and placement flow.")


def verify():
    staged = release.read_release()
    for path, transform in zip(FILES, (style_canvas, full_cell_events, placement_flow), strict=True):
        _, before, candidate = staged[path]
        assert b.encode(transform(json.loads(before))) == candidate
    old, new = [json.loads(raw) for raw in staged[b.OLD][1:]]
    assert old["trigger_id"] == new["trigger_id"]
    assert set(old["sub_trigger"]) == set(new["sub_trigger"])
    for key, entry in old["sub_trigger"].items():
        if key not in (PICK, DROP, ESC):
            assert entry == new["sub_trigger"][key], key
        else:
            assert entry["event"] == new["sub_trigger"][key]["event"], key
    assert b.load(b.PROJECT / b.GRID_MOVE)["func_id"] == "4704f805993411f18d6d0fea6c511829"
    print("Original deployment handlers, save/swap function and event IDs verified.")


def install():
    if list((b.PROJECT / "lock").glob("header_*.lock")):
        raise RuntimeError("Close Y3 before installing.")
    release.install()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=["stage", "verify", "install"])
    mode = parser.parse_args().mode
    release.WORK, release.FILES, release.verify = WORK, FILES, verify
    {"stage": stage, "verify": verify, "install": install}[mode]()

"""Build and check the November 20 safe-zone presentation patch."""

import argparse
import copy
import json
import os

import y3_hero_detail_restore as detail
import y3_safezone_inner_pages as ui


WORK = ui.ROOT / "tmp/safezone-ui-polish-20261120"
HERO = ui.FD + "刷新安全区武将选择.json"
TROOP = ui.FD + "刷新安全区兵种选择.json"
FILES = (ui.UI, ui.ROW, ui.MAIN, ui.SUB, HERO, TROOP, ui.OLD)
INK = (34, 47, 40, 255)
MUTED = (71, 80, 74, 255)
JADE = (17, 87, 62, 255)
GOLD = (116, 75, 26, 255)
RED = (153, 44, 35, 255)


def box(node):
    return (*node["pos_data"]["items"][:2], *node["size"]["items"])


def place(parent, node, x, y, w, h):
    return ui.pos(node, x, y, w, h, *parent["size"]["items"])


def type_style(node, size, color=INK, horizontal=2, display=False):
    ui.font(node, size, color)
    node["font"] = ui.tup("HKSongW9" if display else "MSYH", size)
    node["alignment"] = ui.tup(horizontal, 8)
    node["swallow_touches"] = False
    return node


def button(node, size=24, quiet=False):
    font = ui.tup("MSYH", size)
    node.update(font=font, border=False, shadow=False, gradient=False,
                label_effect=ui.tup(False, False, False, False, False, False),
                hover_status_added=True, pressed_status_added=True,
                disabled_status_added=True, touch_scale=ui.tup(.97, .97))
    if quiet:
        for state, alpha in (("suspend", 160), ("press", 245)):
            node[state + "_picture"] = 134241138
            node[state + "_cap_insets"] = ui.tup(22, 12, 22, 12)
            node[state + "_color"] = ui.tup(218, 241, 223, alpha)
        node["is_scale9_enable"] = True
        return
    for state, tint, ink in (
        ("normal", (255, 255, 255, 255), JADE),
        ("suspend", (239, 255, 227, 255), JADE),
        ("press", (178, 214, 187, 255), INK),
        ("disabled", (244, 242, 235, 255), (83, 85, 77, 255)),
    ):
        node[state + "_color"] = ui.tup(*tint)
        node[state + "_font_color"] = ui.tup(*ink)


def effect_anchor(parent, target, key, prefab=False):
    x, y, _, _ = box(target)
    anchor = ui.newnode("培养生效特效定位", key, x, y, 92, 92)
    place(parent, anchor, x, y, 92, 92)
    ui.extra(parent, anchor, prefab)
    return anchor


def supply(section, troop=False):
    balance = ui.child(section, "货币区域")
    if troop:
        title_box, amount_box = (243, 82, 264, 32), (243, 43, 264, 42)
    else:
        title_box, amount_box = (153, 35, 152, 34), (335, 35, 192, 44)
    type_style(place(balance, ui.child(balance, "title"), *title_box), 22, MUTED)
    type_style(place(balance, ui.child(balance, "数额"), *amount_box), 31, JADE)
    for control in ui.child(section, "抽装备区域")["children"]:
        if control["type"] != 1:
            continue
        w, _ = control["size"]["items"]
        button(control, 24)
        cost = ui.child(control, "cost")
        type_style(place(control, cost, w / 2, 13, w - 60, 22), 18, GOLD)


def canvas(doc):
    find = lambda key: ui.find_uid(doc, ui.uid(key))
    hero = ui.find_uid(doc, ui.DETAIL)
    for key in ("hero/support-entry", "hero/skill-row/3", "hero/v2/core"):
        button(find(key), quiet=True)
    type_style(find("hero/support-entry-text"), 20, JADE)
    type_style(find("hero/v2/normal-text"), 20, JADE)
    type_style(find("hero/v2/core-name"), 24, JADE, 1)
    type_style(find("hero/v2/core-status"), 20, MUTED, 1)
    type_style(find("hero/v2/active-caption"), 22, INK, display=True)
    type_style(find("hero/v2/passive-caption"), 22, INK, display=True)
    for level in range(1, 7):
        tile = find(f"hero/v2/skill/{level}")
        button(tile, quiet=True)
        for part in ("frame", "icon"):
            node = find(f"hero/v2/skill-{part}/{level}")
            size = 56 if part == "frame" else 50
            place(tile, node, 55, 88, size, size)
        type_style(place(tile, find(f"hero/v2/skill-name/{level}"), 55, 39, 106, 40), 19)
        type_style(place(tile, find(f"hero/v2/skill-state/{level}"), 55, 9, 106, 18), 17, MUTED)
    for key, size, color in (
        ("roster/state", 22, JADE), ("hero/upgrade-level", 25, GOLD),
        ("roster/reason", 18, RED), ("hero/v2/detail-state", 23, JADE),
    ):
        type_style(find(key), size, color)
    type_style(place(hero, find("roster/material"), 258, 68, 300, 27), 20, MUTED, 1)
    amount = ui.label("升星材料数额", "polish/hero/material-value", "", 258, 36, 300, 32)
    ui.extra(hero, type_style(place(hero, amount, 258, 36, 300, 32), 27, JADE, 1))
    for key in ("roster/upgrade", "roster/deploy"):
        button(find(key), 22)
    effect_anchor(hero, find("roster/upgrade"), "polish/hero/effect")
    troop = ui.find_uid(doc, ui.s.TROOP_PAGE)
    right = ui.child(ui.find_uid(doc, ui.CONTENT), "右侧区域")
    supply(right)
    formation = ui.child(right, "上阵面板")
    type_style(ui.child(formation, "操作说明"), 21, MUTED)
    for cell in ui.child(formation, "阵型9宫格区域")["children"]:
        frame = ui.child(cell, "frameIMG")
        type_style(place(frame, ui.child(frame, "阵位编号"), 60, 13, 108, 22), 17, GOLD)
    supply(ui.child(troop, "右侧区域"), troop=True)
    power = ui.find_uid(doc, "b3b282ab-a3a7-4eef-a484-e2562a7d9296")
    backing = place(power, ui.child(power, "bg"), 175, 20, 340, 40)
    type_style(place(backing, ui.child(backing, "title"), 65, 20, 105, 32), 20, MUTED)
    type_style(place(backing, ui.child(backing, "战力值"), 224, 20, 196, 36), 27, JADE)
    for i in range(1, 6):
        tile = ui.child(troop, str(i))
        button(tile, quiet=True)
        type_style(place(tile, ui.child(tile, "名称"), 235, 82, 234, 34), 27, INK, 1, True)
        type_style(place(tile, ui.child(tile, "状态"), 178, 40, 120, 32), 25, GOLD, 1)
        badge = find(f"troop/chosen/{i}")
        type_style(place(tile, badge, 314, 40, 112, 26), 19, JADE)
        badge["visible"] = False
        frame = detail.image("兵种选中框", f"polish/troop/selected/{i}",
                             904162, 200, 60, 394, 114, (16, 16, 16, 16))
        place(tile, frame, 200, 60, 394, 114)
        frame.update(visible=False, size_adaptive=False, swallow_touches=False)
        tile["children"].insert(0, frame)
    explanation = find("hero/v2/detail-description")
    # Keep the native expanding text inside the scroll viewport's content origin.
    scroll = find("hero/v2/detail-scroll")
    place(scroll, explanation, 420, 342, 800, 26)
    type_style(explanation, 24, INK, 1)
    explanation.update(over_pattern=True, anchor=ui.tup(.5, 1))
    return doc


def roster_row(doc):
    row = doc["data"]["children"][0]
    head = ui.at(row, "信息.name_bg")
    type_style(place(head, ui.child(head, "name"), 84, 25, 154, 43), 29, INK, 1, True)
    type_style(ui.child(row, "列表星级"), 25, GOLD)
    type_style(ui.child(row, "上阵状态"), 21, MUTED)
    button(ui.child(row, "详情bt"), quiet=True)
    frame = ui.child(row, "整行选中框")
    place(row, frame, 230, 53, 456, 102)
    frame.update(size_adaptive=False, swallow_touches=False)
    return doc


def troop_row(doc, main):
    row = doc["data"]["children"][0]
    group = ui.child(row, "套装区域") if main else row
    top, bottom = (ui.child(group, name) for name in ("上部区域", "下部区域"))
    name, num = (ui.child(top, name) for name in ("name", "num"))
    activate = ui.child(top, "激活bt")
    if main:
        place(row, group, 440, 608, 840, 156)
        place(group, top, 420, 78, 840, 156)
        place(group, bottom, 420, -25, 840, 50)
        place(top, ui.child(top, "icon"), 68, 84, 88, 88)
        place(top, name, 377, 125, 460, 40)
        place(top, ui.child(top, "stars"), 377, 68, 460, 32)
        place(top, activate, 726, 90, 176, 56)
        type_style(place(bottom, ui.child(bottom, "text"), 420, 25, 784, 44), 21, JADE)
        type_style(place(row, ui.child(row, "培养条件"), 440, 466, 792, 28), 20, MUTED)
        caption = ui.child(row, "能力标题")
        type_style(place(row, caption, 230, 420, 412, 38), 26, INK, 1, True)
    else:
        place(top, name, 258, 92, 350, 32)
        place(top, ui.child(top, "stars"), 255, 57, 344, 26)
        place(top, num, 535, 83, 162, 32)
        place(top, activate, 733, 70, 170, 52)
        type_style(num, 25, JADE)
        place(row, bottom, 420, 21, 840, 40)
        type_style(place(bottom, ui.child(bottom, "text"), 349, 20, 528, 38), 20, JADE, 1)
        hint = ui.child(row, "培养条件")
        type_style(place(row, hint, 708, 20, 240, 28), 18, MUTED)
        stock = ui.label("材料标签", "polish/troop/stock-caption", "材料", 535, 55, 140, 24)
        ui.extra(top, type_style(place(top, stock, 535, 55, 140, 24), 17, MUTED), True)
    type_style(name, 30 if main else 25, INK, 1, True)
    button(activate, 22)
    effect_anchor(top, activate, "polish/troop/effect/" + ("main" if main else "sub"), True)
    return doc


def recolor(action, color):
    action["args_list"][2:5] = [ui.lit(100000, value) for value in color[:3]]


def hero_refresh(doc):
    nodes = ui.Nodes(2101122001)
    material = ui.u(ui.uid("polish/hero/material-value"))
    keyed = {n["element_id"]: n for n in ui.walk(doc) if "action_type" in n}
    balance = keyed[2101119301000038]
    name, value = balance["args_list"][2]["args_list"]
    balance["args_list"][2] = name
    chosen = doc["action"][3]["args_list"][1]["args_list"]
    chosen.insert(chosen.index(balance) + 1, nodes.label(balance["args_list"][0], material, value))
    for actions in ui.walk(doc):
        values = actions.get("args_list", [])
        for i, a in reversed(list(enumerate(values))):
            if not isinstance(a, dict):
                continue
            element = a.get("element_id")
            if element in (2101119301000044, 2101119301000047):
                color = JADE if element == 2101119301000044 else RED
                recolor(a, color)
                values.insert(i + 1, ui.color(nodes, a["args_list"][0], material, color))
            if element in (2101119301000023, 2101119301000024):
                p, target, _ = a["args_list"]
                values.insert(i + 1, ui.color(nodes, p, target, JADE if element == 2101119301000023 else MUTED))
    recolor(keyed[2101119301000034], JADE)
    keyed[2101119752000004]["args_list"][2] = ui.integer(22)
    keyed[2101119752000005]["args_list"][2] = ui.integer(26)
    return doc


def troop_refresh(doc):
    nodes = ui.Nodes(2101122002)
    for slot in range(1, 6):
        star = doc["action"][4 * slot - 1]
        prefix, value = star["args_list"][2]["args_list"]
        assert prefix["args_list"] == ["当前星级 "]
        star["args_list"][2] = ui.join(value, ui.text("星"))
        for branch in doc["action"][4 * slot]["args_list"][1:]:
            previous, = branch["args_list"]
            p, state, badge = previous["args_list"]
            assert badge == ui.u(ui.uid(f"troop/chosen/{slot}"))
            branch["args_list"].append(nodes.vis(p, ui.u(ui.uid(f"polish/troop/selected/{slot}")), state["args_list"][0]))
    colors = {
        2101119303000057: JADE, 2101119303000059: RED, 2101119303000079: JADE,
        2101119303000081: JADE, 2101119303000082: RED, 2101119303000084: RED,
    }
    for action in ui.walk(doc):
        if action.get("element_id") in colors:
            recolor(action, colors[action["element_id"]])
    return doc


def upgrade_feedback(doc):
    trigger = doc["sub_trigger"]
    for key in ("593396238", "123634214", "1348370981"):
        entry = trigger[key]
        call, = (n for n in ui.walk(entry["action"])
                 if n.get("element_id") == 593396238000012)
        args = call["args_list"][0]["args_list"]
        p = args[0]
        if key == "593396238":
            args[1] = ui.u(ui.uid("polish/hero/effect"))
            continue
        from_event = ui.ex(100070, "GET_UI_COMP_FROM_EVENT")
        path = ("兵种养成主项.套装区域.上部区域" if key == "123634214"
                else "兵种养成子项.上部区域")
        args[1] = ui.pp(ui.prefab(p, from_event), path + ".培养生效特效定位")
    return doc


def stage():
    changes = (canvas, roster_row, lambda d: troop_row(d, True),
               lambda d: troop_row(d, False), hero_refresh, troop_refresh, upgrade_feedback)
    manifest = {}
    for path, change in zip(FILES, changes, strict=True):
        raw = (ui.PROJECT / path).read_bytes()
        out = ui.encode(change(json.loads(raw)))
        assert out != raw
        manifest[path] = {"before": ui.sha(raw), "candidate": ui.sha(out)}
        for folder, data in (("before", raw), ("candidate", out)):
            dst = WORK / folder / path
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_bytes(data)
    (WORK / "manifest.json").write_bytes(ui.encode(manifest))
    print(f"Staged {len(manifest)} files in {WORK}")


def read_release():
    manifest = ui.load(WORK / "manifest.json")
    assert set(manifest) == set(FILES)
    release = {}
    for path, hashes in manifest.items():
        target = ui.PROJECT / path
        assert target.resolve() == ui.PROJECT.resolve() / path
        baseline = (WORK / "before" / path).read_bytes()
        candidate = (WORK / "candidate" / path).read_bytes()
        assert ui.sha(baseline) == hashes["before"]
        assert ui.sha(candidate) == hashes["candidate"]
        assert target.read_bytes() == baseline, f"Y3 file changed since staging: {path}"
        release[path] = (target, baseline, candidate)
    return release


def verify():
    release = read_release()
    ui_ids = {}
    for path in FILES[:4]:
        _, baseline, candidate = release[path]
        old, new = (json.loads(raw) for raw in (baseline, candidate))
        for field in ("uid", "prefab_sub_key"):
            old_nodes = {n[field]: n for n in ui.walk(old) if n.get(field)}
            new_nodes = [n for n in ui.walk(new) if n.get(field)]
            index = {n[field]: n for n in new_nodes}
            assert len(index) == len(new_nodes)
            assert old_nodes.keys() <= index.keys()
            for key, node in old_nodes.items():
                assert node["type"] == index[key]["type"]
                assert node.get("event_list") == index[key].get("event_list")
            if field == "uid":
                ui_ids.update(index)
    for path in (HERO, TROOP):
        _, baseline, candidate = release[path]
        old, new = (json.loads(raw) for raw in (baseline, candidate))
        assert old["valid"] and new["valid"] and old["func_id"] == new["func_id"]
        actions = [n for n in ui.walk(new) if "action_type" in n]
        ids = [n["element_id"] for n in actions]
        assert len(ids) == len(set(ids))
        for node in actions:
            if node["action_type"] in ("SET_UI_COMP_TEXT", "SET_UI_COMP_FONT_COLOR_NORM",
                                       "SET_UI_COMP_VISIBLE"):
                target = node["args_list"][-1 if node["action_type"] == "SET_UI_COMP_VISIBLE" else 1]
                if target["sub_type"] == 1:
                    assert target["args_list"][0] in ui_ids
    _, baseline, candidate = release[ui.OLD]
    old, new = (json.loads(raw) for raw in (baseline, candidate))
    normalized = copy.deepcopy(new)
    for key in ("593396238", "123634214", "1348370981"):
        def effect(doc):
            return next(n for n in ui.walk(doc["sub_trigger"][key]["action"])
                        if n.get("element_id") == 593396238000012)["args_list"][0]
        new_effect = effect(normalized)
        assert new_effect["args_list"][1] != effect(old)["args_list"][1]
        new_effect["args_list"][1] = effect(old)["args_list"][1]
    assert old == normalized, "Expected only the three sequence parent targets to change"
    print("Verified component identity/events, ECA targets and three success-effect-only edits.")


def install():
    marker = WORK / "publication.json"
    if marker.exists():
        raise RuntimeError("This staged release has already been installed")
    verify()
    release = read_release()
    applied = []
    try:
        for path, (target, baseline, candidate) in release.items():
            if target.read_bytes() != baseline:
                raise RuntimeError(f"Y3 file changed during installation: {path}")
            temp = target.with_name(target.name + ".safezone-ui-polish.tmp")
            with temp.open("xb") as file:
                file.write(candidate)
            try:
                os.replace(temp, target)
            finally:
                temp.unlink(missing_ok=True)
            applied.append(path)
            assert target.read_bytes() == candidate
        marker.write_bytes(ui.encode({"installed": applied, "checksums": ui.load(WORK / "manifest.json")}))
    except BaseException:
        for path in reversed(applied):
            target, baseline, candidate = release[path]
            if target.read_bytes() == candidate:
                target.write_bytes(baseline)
        raise
    print(f"Installed and read back {len(applied)} files.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=["stage", "verify", "install"])
    mode = parser.parse_args().mode
    {"stage": stage, "verify": verify, "install": install}[mode]()

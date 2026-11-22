"""Apply the layout corrections identified in the two runtime screenshots."""

import argparse
import json

import y3_safezone_ui_polish as polish


ui = polish.ui
WORK = ui.ROOT / "tmp/safezone-ui-spacing-20261120-closed"
FILES = (ui.UI, ui.ROW, ui.MAIN, ui.SUB)
place = polish.place


def clean(node):
    node.update(border=False, shadow=False, gradient=False,
                label_effect=ui.tup(False, False, False, False, False, False),
                text_border_width=0, text_border_color=ui.tup(0, 0, 0, 0),
                text_shadow_color=ui.tup(0, 0, 0, 0), text_shadow_offset=ui.tup(0, 0))
    return node


def label(node, size, color=polish.INK, align=2, display=False):
    return clean(polish.type_style(node, size, color, align, display))


def set_button_label(node, size):
    node["font"] = ui.tup("MSYH", size)
    clean(node)


def split_cost(section, suffix):
    for index, button in enumerate(ui.child(section, "抽装备区域")["children"]):
        if button["type"] != 1:
            continue
        w, h = button["size"]["items"]
        caption = button["normal_text"]["items"][0]
        assert caption in ("招募一次", "招募十次", "补给一次", "补给十次")
        set_button_label(button, 23)
        for state in ("normal", "suspend", "press", "disabled"):
            button[state + "_text"] = ui.tup("", False)
        title = ui.label("操作文字", f"spacing/{suffix}/caption/{index}", caption,
                         w * .32, h / 2, w * .48, 32)
        ui.extra(button, label(place(button, title, w * .32, h / 2, w * .48, 32), 23, polish.JADE))
        cost = ui.child(button, "cost")
        label(place(button, cost, w * .75, h / 2, w * .35, 28), 19, polish.GOLD)


def canvas(doc):
    find = lambda key: ui.find_uid(doc, ui.uid(key))
    hero = ui.find_uid(doc, ui.DETAIL)
    head = ui.at(hero, "bg.headBar")
    place(ui.child(hero, "bg"), head, 490, 548, 340, 108)
    label(place(head, ui.child(head, "name"), 189, 76, 238, 46), 34, align=1, display=True)
    rarity = place(head, ui.child(head, "品质图标"), 41, 76, 54, 54)
    rarity.update(size_adaptive=False, swallow_touches=False)
    label(place(head, ui.child(head, "阵营名称"), 146, 12, 250, 24), 18, polish.MUTED, 1)
    label(place(hero, find("roster/state"), 433, 535, 169, 26), 19, polish.JADE, 1)
    star = polish.detail.image("当前星级图标", "spacing/hero/star", 100427, 337, 535, 20, 20)
    ui.extra(hero, place(hero, star, 337, 535, 20, 20))
    deploy = place(hero, find("roster/deploy"), 593, 535, 122, 37)
    set_button_label(deploy, 20)

    core = find("hero/v2/core")
    place(hero, core, 488, 454, 330, 66)
    for part, size in (("frame", 54), ("icon", 44)):
        place(core, find(f"hero/v2/core-{part}"), 34, 33, size, size)
    label(place(core, find("hero/v2/core-name"), 190, 45, 235, 26), 22, polish.JADE, 1)
    label(place(core, find("hero/v2/core-status"), 190, 19, 235, 24), 18, polish.MUTED, 1)

    for key, y, text in (("active", 399, "主动技能"), ("passive", 262, "被动技能")):
        heading = find(f"hero/v2/{key}-caption")
        heading["text"] = ui.tup(text, False)
        label(place(hero, heading, 491, y, 338, 24), 22, align=1, display=True)
    for level in range(1, 7):
        tile = find(f"hero/v2/skill/{level}")
        x = 375 + ((level - 1) // 2) * 115
        y = 329 if level % 2 else 193
        place(hero, tile, x, y, 110, 104)
        for part, size in (("frame", 44), ("icon", 40)):
            place(tile, find(f"hero/v2/skill-{part}/{level}"), 55, 80, size, size)
        label(place(tile, find(f"hero/v2/skill-name/{level}"), 55, 38, 106, 38), 17)
        label(place(tile, find(f"hero/v2/skill-state/{level}"), 55, 9, 106, 18), 16, polish.MUTED)

    label(place(hero, find("hero/upgrade-level"), 340, 111, 568, 30), 22, polish.GOLD)
    label(place(hero, find("roster/material"), 251, 70, 294, 26), 20, polish.MUTED, 1)
    label(place(hero, find("polish/hero/material-value"), 251, 39, 294, 32), 26, polish.JADE, 1)
    label(place(hero, find("roster/reason"), 545, 29, 222, 20), 17, polish.RED)
    upgrade = place(hero, find("roster/upgrade"), 545, 67, 176, 44)
    set_button_label(upgrade, 21)
    place(hero, find("polish/hero/effect"), 545, 67, 92, 92)

    right = ui.child(ui.find_uid(doc, ui.CONTENT), "右侧区域")
    formation = ui.child(right, "上阵面板")
    for cell in ui.child(formation, "阵型9宫格区域")["children"]:
        frame = ui.child(cell, "frameIMG")
        portrait = place(frame, ui.child(frame, "numIMG"), 60, 71, 74, 74)
        portrait["size_adaptive"] = False
        number = ui.child(frame, "阵位编号")
        label(place(frame, number, 60, 22, 92, 20), 16, polish.GOLD)
    split_cost(right, "recruit")
    troop = ui.find_uid(doc, ui.s.TROOP_PAGE)
    split_cost(ui.child(troop, "右侧区域"), "supply")
    return doc


def roster(doc):
    row = ui.child(doc["data"], "伙伴元素")
    info = ui.child(row, "信息")
    heading = place(info, ui.child(info, "name_bg"), 90, 56, 180, 41)
    label(place(heading, ui.child(heading, "name"), 84, 20, 154, 38),
          28, align=1, display=True)
    stars = place(info, ui.child(info, "starList"), 80, 20, 128, 24)
    stars["visible"] = True
    grid = place(stars, ui.child(stars, "grid_view"), 64, 12, 128, 24)
    # Five 22 px native stars with 2 px gaps fit a single 118 px row.
    grid["grid_align"] = ui.tup(1, 8)
    label(place(row, ui.child(row, "列表星级"), 291, 31, 76, 26), 20, polish.GOLD)
    label(place(row, ui.child(row, "上阵状态"), 389, 54, 116, 30), 21, polish.MUTED)
    return doc


def troop(doc, main):
    row = doc["data"]["children"][0]
    group = ui.child(row, "套装区域") if main else row
    top, bottom = (ui.child(group, name) for name in ("上部区域", "下部区域"))
    name, count = (ui.child(top, name) for name in ("name", "num"))
    # Native editor migration kept the resolved border width even with border disabled.
    label(name, 28 if main else 23, polish.INK, 1)
    label(count, 25, polish.JADE)
    label(ui.child(bottom, "text"), 21 if main else 20, polish.JADE, 2 if main else 1)
    clean(ui.child(row, "培养条件"))
    return doc


def stage():
    changes = (canvas, roster, lambda d: troop(d, True), lambda d: troop(d, False))
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
    print(f"Staged {len(manifest)} UI files in {WORK}")


def verify():
    release = polish.read_release()
    for _, baseline, candidate in release.values():
        old, new = [json.loads(raw) for raw in (baseline, candidate)]
        for field in ("uid", "prefab_sub_key"):
            old_nodes = {n[field]: n for n in ui.walk(old) if n.get(field)}
            new_nodes = [n for n in ui.walk(new) if n.get(field)]
            index = {n[field]: n for n in new_nodes}
            assert len(index) == len(new_nodes)
            for key, node in old_nodes.items():
                assert node["type"] == index[key]["type"]
                assert node.get("event_list") == index[key].get("event_list")
    canvas_doc = json.loads(release[ui.UI][2])
    find = lambda key: ui.find_uid(canvas_doc, ui.uid(key))

    def vertical(node):
        _, y, _, height = polish.box(node)
        return y - height / 2, y + height / 2

    active = vertical(find("hero/v2/skill/1"))
    passive = vertical(find("hero/v2/skill/2"))
    active_title = vertical(find("hero/v2/active-caption"))
    passive_title = vertical(find("hero/v2/passive-caption"))
    assert active_title[0] - active[1] >= 6
    assert active[0] - passive_title[1] >= 3
    assert passive_title[0] - passive[1] >= 5
    assert passive[0] - vertical(find("hero/upgrade-level"))[1] >= 12
    assert vertical(find("roster/reason"))[0] >= 18
    hero = ui.find_uid(canvas_doc, ui.DETAIL)
    head = ui.at(hero, "bg.headBar")
    badge = ui.child(head, "品质图标")
    name = ui.child(head, "name")
    assert badge["uid"] == "6e50d319-8bac-45f8-9b02-8c9665b592af"
    assert polish.box(badge)[1] == polish.box(name)[1]
    assert polish.box(badge)[2:] == (54, 54)
    right = ui.child(ui.find_uid(canvas_doc, ui.CONTENT), "右侧区域")
    cells = ui.at(right, "上阵面板.阵型9宫格区域")["children"]
    for cell in cells:
        frame = ui.child(cell, "frameIMG")
        number = vertical(ui.child(frame, "阵位编号"))
        portrait = vertical(ui.child(frame, "numIMG"))
        assert 12 <= number[0] < number[1] < portrait[0]
        assert portrait[1] <= frame["size"]["items"][1] - 10
    troop_panel = ui.child(ui.find_uid(canvas_doc, ui.s.TROOP_PAGE), "右侧区域")
    for section in (right, troop_panel):
        for command in ui.child(section, "抽装备区域")["children"]:
            if command["type"] != 1:
                continue
            width, height = command["size"]["items"]
            caption = ui.child(command, "操作文字")
            price = ui.child(command, "cost")
            assert all(14 <= vertical(node)[0] < vertical(node)[1] <= height - 14
                       for node in (caption, price))
            x_name, _, w_name, _ = polish.box(caption)
            x_price, _, w_price, _ = polish.box(price)
            assert 18 <= x_name - w_name / 2 < x_name + w_name / 2 < x_price - w_price / 2
            assert x_price + w_price / 2 <= width - 18
            assert price["text_border_width"] == 0
    for level in range(1, 7):
        tile = find(f"hero/v2/skill/{level}")
        bounds = [vertical(find(f"hero/v2/skill-{part}/{level}"))
                  for part in ("state", "name", "frame")]
        assert bounds[0][0] >= 0 and bounds[-1][1] <= tile["size"]["items"][1]
        assert all(a[1] < b[0] for a, b in zip(bounds, bounds[1:]))
    row = json.loads(release[ui.ROW][2])
    stars = ui.at(row["data"], "伙伴元素.信息.starList")
    grid = ui.child(stars, "grid_view")
    assert stars["visible"] and grid["layout_type"] == 2
    _, columns = grid["grid_count"]["items"]
    width = columns * grid["grid_size"]["items"][0] + (columns - 1) * grid["grid_space"]["items"][0]
    assert columns == 5 and width <= grid["size"]["items"][0]
    for path in (ui.MAIN, ui.SUB):
        prefab = json.loads(release[path][2])
        for node in ui.walk(prefab):
            if node.get("type") == 3 and node.get("name") in ("name", "num", "text"):
                if node.get("visible", True):
                    assert node["text_border_width"] == 0
    print("Verified UI IDs and events, skill and footer spacing, star grid fit and text border widths.")


def install():
    locks = list((ui.PROJECT / "lock").glob("header_*.lock"))
    if locks:
        raise RuntimeError("Y3 still has the project open. Close the editor before installing.")
    polish.install()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=["stage", "verify", "install"])
    mode = parser.parse_args().mode
    polish.WORK, polish.FILES, polish.verify = WORK, FILES, verify
    {"stage": stage, "verify": verify, "install": install}[mode]()

"""Replace the image IDs returned by the existing star and quality lookups."""

import argparse
import copy
import json

import y3_safezone_ui_polish as release


b = release.ui
WORK = b.ROOT / "tmp/jade-insignia-direct-20261120"
ASSETS = b.ROOT / "assets/art/packages/safezone-jade-insignia-v01"
FUNCTION_ROOT = b.MAP + "global_trigger/function/业务逻辑/"
LOOKUPS = {
    FUNCTION_ROOT + "仆从召唤功能/返回【数量】【图片】伙伴星星控件级别展示.json": {
        100427: "star_locked", 134232916: "star_gold", 134227207: "star_jade",
        134259325: "star_cinnabar", 134244278: "star_imperial",
    },
    FUNCTION_ROOT + "兵种养成/返回【数量】【图片】兵种养成星级展示.json": {
        100427: "star_locked", 134281252: "star_gold", 100661: "star_jade",
    },
    FUNCTION_ROOT + "仆从召唤功能/返回【品质图片】根据品质.json": dict(zip(
        (134232600, 134276653, 134230113, 134275960, 134247488, 134269764, 134241283),
        ("quality_n", "quality_r", "quality_sr", "quality_ssr",
         "quality_ur", "quality_sur", "quality_tur"), strict=True)),
}
FILES = (*LOOKUPS, b.UI)


def icon_ids():
    records = b.load(ASSETS / "y3-icons.json")
    required = {key for mapping in LOOKUPS.values() for key in mapping.values()}
    assert set(records) == required
    ids = {}
    for key, record in records.items():
        icon_id = record["id"]
        source = ASSETS / "png" / (key + ".png")
        package = b.PROJECT / "custom/OriginalRes/icon" / (key + ".package")
        imported = package / source.name
        assert b.sha(source.read_bytes()) == b.sha(imported.read_bytes()) == record["sha256"], key
        assert b.load(package / "meta.json")["id"] == icon_id
        assert b.load(b.PROJECT / f"editor_table/editoricon/{icon_id}.json")["key"] == icon_id
        ids[key] = icon_id
    assert len(set(ids.values())) == len(required)
    return ids


def replace_returns(doc, mapping):
    assert doc["valid"]
    found = []
    for node in b.walk(doc):
        if node.get("action_type") != "SET_VARIABLE":
            continue
        destination, value = node["args_list"]
        if destination["arg_type"] != 100030:
            continue
        variable, = destination["args_list"]
        parts = variable["items"] if isinstance(variable, dict) else variable
        if parts[0] != "TEXTURE":
            continue
        if value["arg_type"] != 100115 or value["sub_type"] != 1:
            continue
        old_id, = value["args_list"]
        if old_id in mapping:
            found.append(old_id)
            value["args_list"][0] = mapping[old_id]
    assert sorted(found) == sorted(mapping), doc["func_name"]
    return doc


def update_canvas(doc, icons):
    hero = b.find_uid(doc, b.DETAIL)
    badge = b.at(hero, "bg.headBar.品质图标")
    emblem = b.child(hero, "当前星级图标")
    assert badge["size"]["items"] == [54, 54] and badge["image"] == 134269764
    assert emblem["image"] == 100427
    badge["image"] = icons["quality_sur"]
    emblem["image"] = icons["star_gold"]
    return doc


def stage():
    icons = icon_ids()
    manifest = {}
    for path in FILES:
        raw = (b.PROJECT / path).read_bytes()
        doc = json.loads(raw)
        if path in LOOKUPS:
            mapping = {old: icons[key] for old, key in LOOKUPS[path].items()}
            result = replace_returns(doc, mapping)
        else:
            result = update_canvas(doc, icons)
        out = b.encode(result)
        assert out != raw
        for section, data in (("before", raw), ("candidate", out)):
            target = WORK / section / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
        manifest[path] = {"before": b.sha(raw), "candidate": b.sha(out)}
    (WORK / "manifest.json").write_bytes(b.encode(manifest))
    print(f"Staged {len(LOOKUPS)} existing functions and the safe-zone canvas.")


def verify():
    icons = icon_ids()
    for path, (_, baseline, candidate) in release.read_release().items():
        previous = json.loads(baseline)
        actual = json.loads(candidate)
        if path in LOOKUPS:
            # Restore only image IDs in memory. Every original ECA field must match.
            reverse = {icons[key]: old for old, key in LOOKUPS[path].items()}
            assert replace_returns(copy.deepcopy(actual), reverse) == previous
        else:
            assert update_canvas(previous, icons) == actual
    print("Verified 15 returned image IDs and 2 default images. ECA identity, references and logic are identical.")


def install():
    if list((b.PROJECT / "lock").glob("header_*.lock")):
        raise RuntimeError("Close the Y3 editor before applying the icon ID changes.")
    release.install()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=["stage", "verify", "install"])
    mode = parser.parse_args().mode
    release.WORK, release.FILES, release.verify = WORK, FILES, verify
    {"stage": stage, "verify": verify, "install": install}[mode]()

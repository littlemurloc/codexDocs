"""把 DD1 安装目录的数据抽取为结构化 JSON。

用法：
    python tools/extract.py [--game "D:/.../DarkestDungeon"] [--out data]

产出（全部为 UTF-8 JSON）：
    data/heroes.json      15 名英雄，技能按 id 聚合 5 个等级
    data/monsters.json    254 个怪物变体
    data/effects.json     1189 条效果定义
    data/buffs.json       2020 条 buff
    data/dungeons.json    地图生成参数 + 遭遇表 + 奇物刷新权重
    data/loot.json        掉落表
    data/trinkets.json    饰品
    data/quirks.json      怪癖
    data/quests.json      任务生成规则
    data/inventory.json   物品定义
    data/rules.json       战斗数学常量（原样拷贝并补索引）
    data/_raw/*.json      未加工的原始记录，便于回溯
    data/stats.json       覆盖率与计数

设计原则：**无损优先**。归一化只做「分组」和「类型转换」，不改写语义；
所有未识别的字段原样保留，避免我理解错导致数据丢失。
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from collections import OrderedDict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from darkest_parser import (  # noqa: E402
    ParseStats,
    Record,
    find_darkest_files,
    parse_file,
    parse_files,
    to_number,
    typed,
    typed_list,
)

DEFAULT_GAME = r"D:/Program Files (x86)/Steam/steamapps/common/DarkestDungeon"
EXCLUDE_DLC = ("dlc/1117860_arena_mp", "dlc/445700_musketeer/heroes/musketeer/anim")


# ----------------------------------------------------------------- 通用工具

def all_fields(rec: Record) -> dict:
    """把一条记录的所有字段转成带类型的字典（无损）。"""
    out: dict = {}
    for key, vals in rec.fields.items():
        if not vals:
            out[key] = None
            continue
        conv = []
        for v in vals:
            low = v.strip().lower()
            if low in ("true", "false"):
                conv.append(low == "true")
            else:
                conv.append(to_number(v))
        out[key] = conv[0] if len(conv) == 1 else conv
    return out


def as_list(v) -> list:
    if v is None:
        return []
    return v if isinstance(v, list) else [v]


def write_json(path: Path, obj) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(obj, ensure_ascii=False, indent=1, sort_keys=False)
    path.write_text(text, encoding="utf-8")
    return len(text)


def load_json(path: Path):
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


# ----------------------------------------------------------------- 英雄

def extract_hero(hero_dir: Path, root: Path, stats: dict) -> dict | None:
    hid = hero_dir.name
    info_path = hero_dir / f"{hid}.info.darkest"
    if not info_path.exists():
        stats["heroes_skipped"].append(hid)
        return None

    recs = parse_file(info_path, root=root)
    art_recs = []
    art_path = hero_dir / f"{hid}.art.darkest"
    if art_path.exists():
        art_recs = parse_file(art_path, root=root)

    hero: dict = {
        "id": hid,
        "source": str(info_path.relative_to(root)).replace("\\", "/"),
        "resistances": {},
        "crit_effects": [],
        "weapons": [],
        "armours": [],
        "skills": [],
        "move_skill": None,
        "tags": [],
        "deaths_door": {},
        "target_rank": None,
        "generation": {},
        "skill_selection": {},
        "extra": {},
    }

    skill_levels: "OrderedDict[str, dict]" = OrderedDict()

    for r in recs:
        f = all_fields(r)
        t = r.type
        if t == "resistances":
            hero["resistances"] = f
        elif t == "crit":
            hero["crit_effects"] = as_list(f.get("effects"))
        elif t == "weapon":
            hero["weapons"].append(f)
        elif t == "armour":
            hero["armours"].append(f)
        elif t == "combat_skill":
            sid = str(f.get("id"))
            lvl = f.get("level", 0)
            slot = skill_levels.setdefault(sid, {"id": sid, "levels": {}})
            slot["levels"][int(lvl) if isinstance(lvl, int) else 0] = f
        elif t == "combat_move_skill":
            hero["move_skill"] = f
        elif t == "tag":
            hero["tags"].append(f.get("id"))
        elif t == "deaths_door":
            hero["deaths_door"] = f
        elif t == "controlled":
            hero["target_rank"] = f.get("target_rank")
        elif t == "generation":
            hero["generation"] = f
        elif t == "skill_selection":
            hero["skill_selection"] = f
        elif t == "id_index":
            hero["id_index"] = f.get("index")
        else:
            hero["extra"].setdefault(t, []).append(f)

    # 技能按等级排序输出；同时挂上美术映射
    art_by_skill = {}
    commonfx = {}
    for r in art_recs:
        f = all_fields(r)
        if r.type == "combat_skill" or r.type == "combat_move_skill":
            art_by_skill[str(f.get("id"))] = f
        elif r.type == "commonfx":
            commonfx = f
        elif r.type == "act_out_display":
            hero.setdefault("act_out_display", f)

    for sid, slot in skill_levels.items():
        levels = [slot["levels"][k] for k in sorted(slot["levels"])]
        hero["skills"].append({
            "id": sid,
            "levels": levels,
            "art": art_by_skill.get(sid, {}),
        })
    hero["commonfx"] = commonfx

    # 武器/护甲的美术图标来自 art 文件
    for r in art_recs:
        if r.type in ("weapon", "armour"):
            f = all_fields(r)
            name = str(f.get("name"))
            bucket = "weapons" if r.type == "weapon" else "armours"
            for item in hero[bucket]:
                if str(item.get("name")) == name:
                    item["icon"] = f.get("icon")

    return hero


def extract_heroes(root: Path, stats: dict) -> list[dict]:
    out = []
    for d in sorted((root / "heroes").iterdir()):
        if not d.is_dir():
            continue
        h = extract_hero(d, root, stats)
        if h:
            out.append(h)
    return out


# ----------------------------------------------------------------- 怪物

def extract_monsters(root: Path, stats: dict) -> list[dict]:
    out = []
    mroot = root / "monsters"
    for family_dir in sorted(p for p in mroot.iterdir() if p.is_dir()):
        for variant_dir in sorted(p for p in family_dir.iterdir() if p.is_dir()):
            info = variant_dir / f"{variant_dir.name}.info.darkest"
            if not info.exists():
                continue
            recs = parse_file(info, root=root)
            art_recs = []
            art_path = variant_dir / f"{variant_dir.name}.art.darkest"
            if art_path.exists():
                art_recs = parse_file(art_path, root=root)

            mon: dict = {
                "id": variant_dir.name,
                "family": family_dir.name,
                "source": str(info.relative_to(root)).replace("\\", "/"),
                "size": None,
                "enemy_types": [],
                "stats": {},
                "skills": [],
                "loot": {},
                "death_class": {},
                "battle_modifier": {},
                "wave_spawning": {},
                "initiative": {},
                "brain": None,
                "personality": {},
                "extra": {},
            }

            art_by_skill = {}
            for r in art_recs:
                f = all_fields(r)
                if r.type == "skill":
                    art_by_skill[str(f.get("id"))] = f
                elif r.type == "commonfx":
                    mon["commonfx"] = f
                else:
                    mon["extra"].setdefault(f"art_{r.type}", []).append(f)

            for r in recs:
                f = all_fields(r)
                t = r.type
                if t == "display":
                    mon["size"] = f.get("size")
                elif t == "enemy_type":
                    mon["enemy_types"].append(f.get("id"))
                elif t == "stats":
                    mon["stats"] = f
                elif t == "skill":
                    f["art"] = art_by_skill.get(str(f.get("id")), {})
                    mon["skills"].append(f)
                elif t == "loot":
                    mon["loot"] = f
                elif t == "death_class":
                    mon["death_class"] = f
                elif t == "battle_modifier":
                    mon["battle_modifier"] = f
                elif t == "wave_spawning":
                    mon["wave_spawning"] = f
                elif t == "initiative":
                    mon["initiative"] = f
                elif t == "monster_brain":
                    mon["brain"] = f.get("id")
                elif t == "personality":
                    mon["personality"] = f
                else:
                    mon["extra"].setdefault(t, []).append(f)

            out.append(mon)
    return out


# ----------------------------------------------------------------- 效果 / buff

def extract_effects(root: Path) -> list[dict]:
    recs = parse_files([root / "effects/base.effects.darkest"], root=root)
    recs += parse_files([p for p in (root / "effects").glob("mode.effects.darkest")], root=root)
    out = []
    for r in recs:
        f = all_fields(r)
        out.append(f)
    return out


def extract_buffs(root: Path) -> list[dict]:
    data = load_json(root / "shared/buffs/base.buffs.json") or {}
    return data.get("buffs", [])


# ----------------------------------------------------------------- 地牢

RE_MASH_LEVEL = re.compile(r"\.(\d+)\.mash\.darkest$")
RE_MASH_COND = re.compile(r"\.conditional\.(\d+)\.mash\.darkest$")


def extract_dungeons(root: Path) -> dict:
    maps = []
    for r in parse_files([root / "scripts/map_generator.darkest"], root=root):
        f = all_fields(r)
        maps.append(f)

    # 遭遇表：dungeons/<region>/<region>.<lv>.mash.darkest
    encounters: dict = {}
    for region_dir in sorted((root / "dungeons").iterdir()):
        if not region_dir.is_dir():
            continue
        region = region_dir.name
        for mash in sorted(region_dir.glob("*.mash.darkest")):
            name = mash.name
            cond = RE_MASH_COND.search(name)
            lvl = RE_MASH_LEVEL.search(name)
            if cond:
                key = f"conditional_{cond.group(1)}"
            elif lvl:
                key = lvl.group(1)
            else:
                continue
            recs = parse_file(mash, root=root)
            table: dict = {}
            for r in recs:
                f = all_fields(r)
                kind = r.type
                if kind == "named":
                    bucket = f"named:{f.get('name')}"
                else:
                    bucket = kind
                entry = {"chance": f.get("chance"), "types": as_list(f.get("types"))}
                table.setdefault(bucket, []).append(entry)
            encounters.setdefault(region, {})[key] = table

    # 奇物 / 陷阱 / 障碍的刷新权重
    props: dict = {}
    for props_file in sorted((root / "dungeons").glob("*/*.props.darkest")):
        region = props_file.parent.name
        recs = parse_file(props_file, root=root)
        table: dict = {}
        for r in recs:
            f = all_fields(r)
            table.setdefault(r.type, []).append({
                "chance": f.get("chance"),
                "types": as_list(f.get("types")),
            })
        props[region] = table

    # 区域元数据
    meta: dict = {}
    for jf in sorted((root / "dungeons").glob("*/*.dungeon.json")):
        meta[jf.parent.name] = load_json(jf)

    return {"maps": maps, "encounters": encounters, "props": props, "meta": meta}


# ----------------------------------------------------------------- 其它表

def extract_loot(root: Path) -> dict:
    data = load_json(root / "loot/loot.json") or {}
    overrides = {}
    for p in sorted((root / "loot").glob("*overrides.loot.json")):
        overrides[p.name] = load_json(p)
    return {"loot_tables": data.get("loot_tables", []), "overrides": overrides}


def extract_trinkets(root: Path) -> dict:
    out = {}
    for name in ("base.entries", "base.rarities", "base.starting"):
        out[name] = load_json(root / f"trinkets/{name}.trinkets.json")
    return out


def extract_quirks(root: Path) -> dict:
    return load_json(root / "shared/quirk/quirk_library.json") or {}


def extract_quests(root: Path) -> dict:
    out = {}
    for p in sorted((root / "campaign/quest").glob("*.json")):
        out[p.stem] = load_json(p)
    return out


def extract_inventory(root: Path) -> list[dict]:
    recs = []
    for p in sorted((root / "inventory").glob("*.darkest")):
        recs.extend(parse_file(p, root=root))
    return [all_fields(r) for r in recs]


def extract_curio_props(root: Path) -> list[dict]:
    """奇物 -> 精灵图/音频映射（这是干净的运行期数据）。"""
    path = root / "curios/curio_props.csv"
    if not path.exists():
        return []
    rows = []
    with path.open(encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            if any((v or "").strip() for v in row.values()):
                rows.append({(k or "").strip(): (v or "").strip() for k, v in row.items()})
    return rows


def extract_curio_library(root: Path) -> list[list[str]]:
    """奇物交互设计表（策划草稿，非严格数据），保留为单元格矩阵供人工查阅。"""
    path = root / "curios/curio_type_library.csv"
    if not path.exists():
        return []
    with path.open(encoding="utf-8-sig", newline="") as fh:
        return [[c.strip() for c in row] for row in csv.reader(fh)]


def extract_rules(root: Path) -> dict:
    rules = load_json(root / "shared/rules.json") or {}
    raid = load_json(root / "scripts/raid_settings.json") or {}
    return {"rules": rules, "raid_settings": raid}


# ----------------------------------------------------------------- 主流程

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--game", default=DEFAULT_GAME)
    ap.add_argument("--out", default=str(Path(__file__).parent.parent / "data"))
    args = ap.parse_args()

    root = Path(args.game)
    out = Path(args.out)
    if not root.exists():
        print(f"[错误] 游戏目录不存在: {root}")
        return 1

    stats: dict = {"heroes_skipped": [], "counts": {}, "parse": {}}
    parse_stats = ParseStats()

    print(f"[1/9] 解析英雄 ...")
    heroes = extract_heroes(root, stats)
    stats["counts"]["heroes"] = len(heroes)
    write_json(out / "heroes.json", heroes)

    print(f"[2/9] 解析怪物 ...")
    monsters = extract_monsters(root, stats)
    stats["counts"]["monsters"] = len(monsters)
    stats["counts"]["monster_families"] = len({m["family"] for m in monsters})
    write_json(out / "monsters.json", monsters)

    print(f"[3/9] 解析效果 ...")
    effects = extract_effects(root)
    stats["counts"]["effects"] = len(effects)
    write_json(out / "effects.json", effects)

    print(f"[4/9] 解析 buff ...")
    buffs = extract_buffs(root)
    stats["counts"]["buffs"] = len(buffs)
    write_json(out / "buffs.json", buffs)

    print(f"[5/9] 解析地牢 ...")
    dungeons = extract_dungeons(root)
    stats["counts"]["map_configs"] = len(dungeons["maps"])
    stats["counts"]["encounter_regions"] = len(dungeons["encounters"])
    stats["counts"]["encounter_tables"] = sum(
        len(v) for v in dungeons["encounters"].values()
    )
    write_json(out / "dungeons.json", dungeons)

    print(f"[6/9] 解析掉落/饰品/怪癖 ...")
    write_json(out / "loot.json", extract_loot(root))
    write_json(out / "trinkets.json", extract_trinkets(root))
    write_json(out / "quirks.json", extract_quirks(root))

    print(f"[7/9] 解析任务/物品/奇物 ...")
    write_json(out / "quests.json", extract_quests(root))
    inv = extract_inventory(root)
    stats["counts"]["inventory_items"] = len(inv)
    write_json(out / "inventory.json", inv)
    curio_props = extract_curio_props(root)
    stats["counts"]["curio_props"] = len(curio_props)
    write_json(out / "curio_props.json", curio_props)
    write_json(out / "curio_design_table.json", extract_curio_library(root))

    print(f"[8/9] 解析全局规则 ...")
    write_json(out / "rules.json", extract_rules(root))

    print(f"[9/9] 全量原始记录 + 统计 ...")
    # 全量原始记录：便于回溯任何一条数值的出处
    raw_files = find_darkest_files(root, exclude_dirs=EXCLUDE_DLC)
    by_dir: dict = {}
    for p in raw_files:
        recs = parse_file(p, root=root, stats=parse_stats)
        rel = str(p.relative_to(root)).replace("\\", "/")
        by_dir[rel] = [{"_type": r.type, "_line": r.line, **all_fields(r)} for r in recs]
    write_json(out / "_raw/all_records.json", by_dir)

    stats["parse"] = parse_stats.as_dict()
    stats["parse"]["darkest_files_scanned"] = len(raw_files)
    stats["parse"]["total_records"] = parse_stats.records

    # 交叉校验：技能引用的 effect 是否都存在
    effect_names = {str(e.get("name")) for e in effects}
    missing = set()
    for h in heroes:
        for s in h["skills"]:
            for lv in s["levels"]:
                for e in as_list(lv.get("effect")):
                    if str(e) not in effect_names:
                        missing.add(str(e))
    for m in monsters:
        for s in m["skills"]:
            for e in as_list(s.get("effect")):
                if str(e) not in effect_names:
                    missing.add(str(e))
    stats["referential_check"] = {
        "effect_defs": len(effect_names),
        "missing_effect_refs": sorted(missing)[:40],
        "missing_count": len(missing),
    }

    write_json(out / "stats.json", stats)

    print()
    print("完成。计数：")
    for k, v in stats["counts"].items():
        print(f"  {k:24s} {v}")
    print(f"  {'darkest 记录总数':24s} {parse_stats.records}")
    print(f"  {'未解析孤儿行':24s} {len(parse_stats.orphan_lines)}")
    print(f"  {'缺失 effect 引用':24s} {len(missing)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

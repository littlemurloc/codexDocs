class_name TestData
extends RefCounted
## 数据层一致性：抽取的 JSON 与 DD1 原始配置是否对得上。
## 这一层不测玩法，只测「我读到的数字是不是真的」。


static func run(t: TestLib, db: DdDb) -> void:
	t.section("数据规模")
	t.eq(db.heroes.size(), 15, "英雄 15 名")
	t.ok(db.monsters.size() >= 250, "怪物变体 ≥ 250，实际 %d" % db.monsters.size())
	t.ok(db.effects.size() >= 1180, "效果定义 ≥ 1180，实际 %d" % db.effects.size())
	t.ok(db.buffs.size() >= 2000, "buff ≥ 2000，实际 %d" % db.buffs.size())

	t.section("十字军基础属性（对照源文件）")
	var b: Dictionary = db.hero_base("crusader", 0)
	t.eq(int(b["hp_max"]), 33, "L0 生命 33")
	t.near(float(b["dodge"]), 0.05, 1e-9, "L0 闪避 5%")
	t.near(float(b["speed"]), 1.0, 1e-9, "L0 速度 1（来自武器）")
	t.near(float(b["dmg_low"]), 6.0, 1e-9, "L0 武器伤害下限 6")
	t.near(float(b["dmg_high"]), 12.0, 1e-9, "L0 武器伤害上限 12")
	t.near(float(b["crit"]), 0.03, 1e-9, "L0 暴击 3%")

	var b4: Dictionary = db.hero_base("crusader", 4)
	t.eq(int(b4["hp_max"]), 61, "L4 生命 61")
	t.near(float(b4["dmg_low"]), 10.0, 1e-9, "L4 武器伤害下限 10")
	t.near(float(b4["dmg_high"]), 19.0, 1e-9, "L4 武器伤害上限 19")

	t.section("怪物属性")
	var m: Dictionary = db.monster_base("cultist_brawler_A")
	t.eq(int(m["hp_max"]), 15, "邪教徒斗士 A 生命 15")
	t.near(float(m["speed"]), 5.0, 1e-9, "邪教徒斗士 A 速度 5")
	t.near(float(m["stun_resist"]), 0.25, 1e-9, "眩晕抗性 25%")

	t.section("技能站位掩码")
	var hero: Dictionary = db.hero("crusader")
	var actions: Array = Combatant.build_actions(hero["skills"], 0, true)
	var smite: Dictionary = _find(actions, "smite")
	t.eq(int(smite["launch_mask"]), 0b0011, "惩击可从 1、2 号位发动（launch 21）")
	t.eq(int(smite["target_mask"]), 0b0011, "惩击命中敌方 1、2 号位（target 12）")
	t.eq(bool(smite["target_aoe"]), false, "惩击是单体")
	t.near(float(smite["atk"]), 0.85, 1e-9, "惩击 L0 命中 85%")

	var aoe_found: bool = false
	for h in db.heroes.values():
		for a in Combatant.build_actions(h["skills"], 0, true):
			if bool(a["target_aoe"]):
				aoe_found = true
				break
		if aoe_found:
			break
	t.ok(aoe_found, "存在 AOE 技能（~ 前缀被正确识别）")

	t.section("效果引用闭合")
	var missing: Array = []
	var checked: int = 0
	for h in db.heroes.values():
		for lv in _all_levels(h.get("skills", [])):
			for name in DdDb.effect_names(lv):
				checked += 1
				if db.effect(str(name)).is_empty():
					missing.append(name)
	for mo in db.monsters.values():
		for sk in mo.get("skills", []):
			for name in DdDb.effect_names(sk):
				checked += 1
				if db.effect(str(name)).is_empty():
					missing.append(name)
	t.eq(missing.size(), 0, "英雄/怪物引用的 %d 个效果全部可解析" % checked)

	t.section("规则常量")
	t.near(db.rules.cutoff_hit, 0.95, 1e-9, "命中上限 0.95")
	t.eq(db.rules.initiative_base, 8, "先攻基础值 8")
	t.near(db.rules.monster_crit_stress, 10.0, 1e-9, "怪物暴击自身 +10 压力")
	t.near(db.rules.monster_crit_companion_stress, 5.0, 1e-9, "怪物暴击队友 +5 压力")


static func _find(actions: Array, id: String) -> Dictionary:
	for a in actions:
		if str(a["id"]) == id:
			return a
	return {}


static func _all_levels(skills: Array) -> Array:
	var out: Array = []
	for s in skills:
		for lv in s.get("levels", []):
			out.append(lv)
	return out

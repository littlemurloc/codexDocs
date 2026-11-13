class_name TestM73
extends RefCounted
## M73 尸体（残骸）可摧毁。
##
## 尸体占位是「不清掉后排就换不到前排」的机制基础，但它必须**能被清掉** ——
## 否则一具尸体能把近战卡死到僵持（敌人全在后面，前排是尸体，够不到）。
##
## 三条要点：
##   1. 怪物死了留耐久，英雄倒下不留（不能鞭尸队友）
##   2. 只有带伤害的技能能选残骸（治疗/增益不该往尸体上招呼）
##   3. 耐久归零 → 移出队列 → 后面的人 rank 前移一格

const HEROES: Array = ["crusader", "highwayman", "vestal", "plague_doctor"]
const MONSTERS: Array = ["cultist_brawler_A", "cultist_brawler_A", "cultist_witch_A"]


static func run(t: TestLib, db: DdDb) -> void:
	_test_durability(t, db)
	_test_targetable(t, db)
	_test_destroy(t, db)


# ------------------------------------------------------------
# 1. 耐久从哪来
# ------------------------------------------------------------

static func _test_durability(t: TestLib, db: DdDb) -> void:
	t.section("残骸：耐久")
	var b := Battle.new()
	b.setup(HEROES, MONSTERS, 12345)
	var m: Combatant = b.enemies[0]
	t.eq(m.corpse_hp, -1, "活着时没有耐久（-1）")
	m.take_damage(9999)
	t.ok(m.dead, "怪物被打死")
	t.ok(m.corpse_hp >= 1, "死后留下耐久 %d" % m.corpse_hp)

	# 英雄倒下不该留残骸：队友打自己人的尸体没有意义
	var h: Combatant = b.party[0]
	h.at_deaths_door = true
	h.hp = 0
	h.take_damage(10)
	t.ok(h.dead, "英雄在死门上被击穿")
	t.eq(h.corpse_hp, -1, "英雄不留残骸")


# ------------------------------------------------------------
# 2. 谁能选残骸
# ------------------------------------------------------------

static func _test_targetable(t: TestLib, db: DdDb) -> void:
	t.section("残骸：可选性")
	var b := Battle.new()
	b.setup(HEROES, MONSTERS, 777)
	var m: Combatant = b.enemies[0]
	m.take_damage(9999)
	var hero: Combatant = b.party[0]

	var atk: Dictionary = _first_foe_action(hero)
	t.ok(not atk.is_empty(), "十字军有打敌方的技能")
	var pool: Array = b._legal_targets(hero, atk)
	t.ok(pool.has(m), "敌方技能把残骸算进目标池")

	var vestal: Combatant = b.party[2]
	var heal: Dictionary = _first_heal(vestal)
	if not heal.is_empty():
		var hpool: Array = b._legal_targets(vestal, heal)
		t.ok(not hpool.has(m), "治疗技能不选残骸")


# ------------------------------------------------------------
# 3. 清掉之后队列收拢
# ------------------------------------------------------------

static func _test_destroy(t: TestLib, db: DdDb) -> void:
	t.section("残骸：清掉后排队前移")
	var b := Battle.new()
	b.setup(HEROES, MONSTERS, 4242)
	var dead_one: Combatant = b.enemies[0]
	var behind: Combatant = b.enemies[1]
	dead_one.take_damage(9999)
	var behind_rank: int = behind.rank

	b._strike_corpse(b.party[0], dead_one)
	if dead_one.corpse_hp > 0:
		t.eq(b.enemies.size(), 3, "耐久没掉光时仍占位")

	var guard: int = 0
	while dead_one.corpse_hp > 0 and guard < 20:
		b._strike_corpse(b.party[0], dead_one)
		guard += 1
	t.eq(dead_one.corpse_hp, 0, "耐久被打光")
	t.eq(b.enemies.size(), 2, "清掉后队列少一个")
	t.eq(b.enemies[0].uid, behind.uid, "后面的人顶到 1 号位")
	t.eq(behind.rank, behind_rank - 1, "rank 前移一格")

	# 清掉的残骸不能再被选
	var atk: Dictionary = _first_foe_action(b.party[0])
	t.ok(not atk.is_empty(), "还有打敌方的技能")
	var pool: Array = b._legal_targets(b.party[0], atk)
	t.ok(not pool.has(dead_one), "清掉的残骸不再进目标池")

	# 行动序里不该再出现它（否则条上会留一个永远轮不到的格子）
	var ev: Array = b.run_round()
	var order_ev: Dictionary = {}
	for e in ev:
		if str(e["t"]) == "order":
			order_ev = e
			break
	t.ok(not order_ev.is_empty(), "下一轮重新发了行动序")
	t.ok(not (order_ev["ids"] as Array).has(dead_one.uid), "行动序里没有已清掉的残骸")


static func _first_foe_action(u: Combatant) -> Dictionary:
	for a in u.actions:
		if not bool(a.friendly):
			return a
	return {}


static func _first_heal(u: Combatant) -> Dictionary:
	for a in u.actions:
		if float(a.heal) > 0.0:
			return a
	return {}

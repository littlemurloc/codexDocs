class_name TestSummon
extends RefCounted
## 召唤（M12）回归。
##
## 召唤是第四批「数据齐备但从未执行」的机制：59 条效果、35 只怪，从 M0 就在
## 库里，而 effect_resolver 一直把它们落到 `unsupported = "summon"`。
##
## 但「接通解析」只完成了三分之一。实测证明另外三分之二各自能单独失效：
##
##   1. 解析层把 `summon_monsters` 当成数组，单值条目（字符串）会被读成空
##   2. 没有估值时 AI 一次都不选——`cannon_summon` 的分数正好是 0.00
##   3. 没有上限时「死一个补一个」，ectoplasm 场景打到 23.7 轮（基线 4.1）
##
## 这一组断言分别钉住这三层，外加四条边界：满位、尸体让位、同种上限、
## 阵营总量闸。少测任何一条，都只能知道「召出来了」，不知道「召得对不对」。

const HEROES: Array = ["crusader", "highwayman", "vestal", "plague_doctor"]


static func run(t: TestLib, db: DdDb) -> void:
	_test_parse(t, db)
	_test_slot(t, db)
	_test_full(t, db)
	_test_corpse_yields(t, db)
	_test_limits(t, db)
	_test_battle_cap(t, db)
	_test_unit_shape(t, db)
	_test_score(t, db)
	_test_action_tag(t, db)


## 拿一个单位身上第一条带召唤的技能。
static func _summon_action(u: Combatant) -> Dictionary:
	for a in u.actions:
		var info: Dictionary = a.get("summon", {})
		if not info.is_empty():
			return a
	return {}


static func _ctx(b: Battle) -> Dictionary:
	return {"hit": true, "rng": DdRng.new(11), "all_units": b.all_units()}


## 解析层：单值/列表两种形态都要吃，三个对齐字段要跟着走。
static func _test_parse(t: TestLib, db: DdDb) -> void:
	t.section("召唤：解析")
	# _apply_one 的 attacker/target 用真实单位：它内部还有别的分支会读
	# resistance()，传 null 会在别的数据上炸（这里虽然走不到，但不值得赌）。
	var dummy := Combatant.new()
	dummy.setup_from_monster(db, "cultist_brawler_A")
	# 单值：summon_monsters 是字符串，不是字符串数组。
	# 这是最容易错的一处——Python 侧遍历字符串会拆成单字符，M11 踩过。
	var one: Dictionary = EffectResolver._apply_one(db,
		db.effect("Summon Fuseman 1"), dummy, dummy, DdRng.new(1), {})
	t.eq(bool(one.get("summon", false)), true, "单值召唤被识别")
	t.eq((one.get("summon_list", []) as Array).size(), 1, "单值 -> 长度 1 的列表")
	t.eq(str((one.get("summon_list", []) as Array)[0]), "brigand_fuseman_A", "单值内容正确")

	# 列表 + 并行数组：两个候选各有自己的权重/上限/落点。
	var multi: Dictionary = EffectResolver._apply_one(db,
		db.effect("Summon Brigand 1"), dummy, dummy, DdRng.new(1), {})
	var ids: Array = multi.get("summon_list", [])
	t.eq(ids.size(), 2, "列表召唤有两个候选")
	t.eq((multi.get("summon_weights", []) as Array).size(), ids.size(), "权重与候选等长")
	t.eq((multi.get("summon_limits", []) as Array).size(), ids.size(), "上限与候选等长")
	t.eq((multi.get("summon_ranks", []) as Array).size(), ids.size(), "落点与候选等长")

	# 位掩码语义：这份数据写 ranks = [1, 4]，对应 [割喉贼, 火枪手]。
	# 按位掩码解释是「1 号位 / 3 号位」——近战在前、火枪在后，语义自洽；
	# 按槽位号解释则 4 号位会落在阵型外面。这条断言钉住的是语义。
	var ranks: Array = multi.get("summon_ranks", [])
	t.eq(int(ranks[0]), 1, "第一个候选落在 1 号位")
	t.eq(int(ranks[1]), 4, "第二个候选的落点是 3 号位（位掩码 0b100）")


## 槽位选择：位掩码优先、尸体其次、最后往后接。
static func _test_slot(t: TestLib, db: DdDb) -> void:
	t.section("召唤：槽位")
	var b := Battle.new()
	b.setup(HEROES, ["cultist_brawler_A", "cultist_brawler_A"], 401)
	t.eq(b.summon_slot(Combatant.SIDE_ENEMY), 2, "两人阵型 -> 往后接到 2")
	# 掩码指向一个活人：不能强占，也不能因为「掩码对不上」就放弃召唤——
	# 那会让大部分召唤永远不触发（数据里的 3 号位在只有 1 个怪时永远不成立）。
	t.eq(b.summon_slot(Combatant.SIDE_ENEMY, 1 << 0), 2, "掩码指活人 -> 退到下一个空位")
	b.enemies[0].dead = true
	t.eq(b.summon_slot(Combatant.SIDE_ENEMY, 1 << 0), 0, "掩码指 1 号位、那里是尸体 -> 用 0")
	t.eq(b.summon_slot(Combatant.SIDE_ENEMY), 0, "无掩码时也优先用尸体格")
	t.eq(b.summon_slot(Combatant.SIDE_ENEMY, 1 << 2), 2, "掩码指 3 号位、正好是下一个空位 -> 用 2")


## 满位：4 个敌人全活着就不召唤。这是 DD1 的行为，也是 4 位目标掩码的硬约束。
static func _test_full(t: TestLib, db: DdDb) -> void:
	t.section("召唤：满位")
	var b := Battle.new()
	b.setup(HEROES, ["cultist_brawler_A", "cultist_brawler_A",
		"cultist_brawler_A", "cultist_brawler_A"], 402)
	t.eq(b.summon_slot(Combatant.SIDE_ENEMY), -1, "满位返回 -1")
	t.eq(b.enemies.size(), 4, "满位时阵容不增长")

	var n0: int = b.enemies.size()
	var ev: Dictionary = {"summon": true, "summon_list": ["brigand_fuseman_A"],
		"summon_weights": [1.0], "summon_limits": [0], "summon_ranks": [0],
		"summon_count": 1, "summon_erase": false, "summon_loot": true}
	b._consume_summon_effect(ev, b.enemies[0], {"id": "t"})
	t.eq(b.enemies.size(), n0, "满位时消费召唤不增员")
	var failed: bool = false
	for e in b.events:
		if str(e.get("t", "")) == "summon_fail":
			failed = true
	t.eq(failed, true, "满位会发 summon_fail（不静默）")


## 尸体让位：这是本项目特有的规则，因为尸体一直占着格子。
static func _test_corpse_yields(t: TestLib, db: DdDb) -> void:
	t.section("召唤：尸体让位")
	var b := Battle.new()
	b.setup(HEROES, ["cultist_brawler_A", "cultist_brawler_A",
		"cultist_brawler_A", "cultist_brawler_A"], 403)
	var dead_uid: int = b.enemies[1].uid
	b.enemies[1].dead = true
	var before: int = b.enemies.size()

	var ev: Dictionary = {"summon": true, "summon_list": ["brigand_fuseman_A"],
		"summon_weights": [1.0], "summon_limits": [0], "summon_ranks": [0],
		"summon_count": 1, "summon_erase": false, "summon_loot": true}
	b._consume_summon_effect(ev, b.enemies[0], {"id": "t"})
	t.eq(b.enemies.size(), before, "尸体让位不改变阵容长度")
	t.eq(b.enemies[1].def_id, "brigand_fuseman_A", "尸体格被替换成召唤物")
	t.ok(b.enemies[1].uid != dead_uid, "替换后是新的单位，不是复活")
	t.eq(b.unit_by_uid(dead_uid) == null, true, "旧 uid 不再指向任何单位")


## 同种上限：数据有就用数据的（炮船只能有一门炮灰）。
static func _test_limits(t: TestLib, db: DdDb) -> void:
	t.section("召唤：数量上限")
	var b := Battle.new()
	b.setup(HEROES, ["brigand_cannon_A"], 404)
	var actor: Combatant = b.enemies[0]
	var action: Dictionary = _summon_action(actor)
	t.ok(not action.is_empty(), "炮船身上找到召唤技能")

	var ev: Dictionary = {"summon": true, "summon_list": ["brigand_fuseman_A"],
		"summon_weights": [1.0], "summon_limits": [1], "summon_ranks": [0],
		"summon_count": 1, "summon_erase": false, "summon_loot": true}
	b._consume_summon_effect(ev, actor, action)
	t.eq(b.summon_count("brigand_fuseman_A", Combatant.SIDE_ENEMY), 1, "第一次召唤成功")
	# 数据写 limits = 1，所以第二次必须被拒——否则炮船会无限堆炮灰。
	b._consume_summon_effect(ev, actor, action)
	t.eq(b.summon_count("brigand_fuseman_A", Combatant.SIDE_ENEMY), 1, "达到 limits 后不再召")


## 阵营总量闸：防「死一个补一个」的震荡循环。
static func _test_battle_cap(t: TestLib, db: DdDb) -> void:
	t.section("召唤：阵营总量闸")
	var b := Battle.new()
	b.setup(HEROES, ["necromancer_A"], 405)
	var actor: Combatant = b.enemies[0]
	var action: Dictionary = _summon_action(actor)
	# 反复召唤 + 反复腾位置，模拟「打死一个又补一个」。
	var guard: int = 0
	while guard < 30:
		guard += 1
		# 让出一个位置
		var freed: bool = false
		for u in b.enemies:
			if (u as Combatant).uid != actor.uid and not (u as Combatant).is_alive():
				freed = true
		if not freed:
			for u in b.enemies:
				if (u as Combatant).uid != actor.uid:
					(u as Combatant).dead = true
					freed = true
					break
		if not freed:
			break
		b._consume_summon_effect({"summon": true, "summon_list": ["skeleton_common_A"],
			"summon_weights": [1.0], "summon_limits": [0], "summon_ranks": [0],
			"summon_count": 1, "summon_erase": false, "summon_loot": true}, actor, {"id": "t2"})
	t.eq(b._summoned_total <= Battle.MAX_SUMMONED_PER_BATTLE, true,
		"累计召唤不超过 %d（实际 %d）" % [Battle.MAX_SUMMONED_PER_BATTLE, b._summoned_total])

	# 关掉闸门后应当能超过这个数——证明闸门真的在起作用，而不是巧合。
	var b2 := Battle.new()
	b2.setup(HEROES, ["necromancer_A"], 406)
	b2.summon_default_limit_enabled = false
	var a2: Combatant = b2.enemies[0]
	for i in 8:
		for u in b2.enemies:
			if (u as Combatant).uid != a2.uid:
				(u as Combatant).dead = true
		b2._consume_summon_effect({"summon": true, "summon_list": ["skeleton_common_A"],
			"summon_weights": [1.0], "summon_limits": [0], "summon_ranks": [0],
			"summon_count": 1, "summon_erase": false, "summon_loot": true}, a2, {"id": "t3"})
	t.ok(b2._summoned_total > Battle.MAX_SUMMONED_PER_BATTLE,
		"关掉闸门后能超过上限（%d）" % b2._summoned_total)


## 召唤物本身要是一个完整的战斗单位，不是只有名字的占位。
static func _test_unit_shape(t: TestLib, db: DdDb) -> void:
	t.section("召唤：单位完整性")
	var b := Battle.new()
	b.setup(HEROES, ["necromancer_A"], 407)
	var u: Combatant = b.summon_monster("skeleton_common_A", Combatant.SIDE_ENEMY, 1)
	t.ok(u != null, "召唤物创建成功")
	t.eq(u.side, Combatant.SIDE_ENEMY, "阵营正确")
	t.eq(u.is_hero, false, "不是英雄")
	t.ok(u.hp > 0, "有血量（%d）" % u.hp)
	t.ok(u.actions.size() > 0, "有技能（%d 个）" % u.actions.size())
	t.eq(b.enemies.size(), 2, "已加入敌人数组")
	t.eq(u.rank, 1, "站位是 1 号位")
	# 新单位的技能必须打过标记，否则「召唤物不会还手 / 不会守护」这种差异
	# 不会报错，只会让同一只怪在召唤前后行为不同。
	var has_tag: bool = true
	for a in u.actions:
		if not (a as Dictionary).has("is_guard") or not (a as Dictionary).has("is_riposte"):
			has_tag = false
	t.eq(has_tag, true, "召唤物的技能带 is_guard / is_riposte 标记")
	# uid 必须唯一，否则关系表（守护/反击）会串到别人身上。
	var uids: Dictionary = {}
	var dup: bool = false
	for x in b.all_units():
		if uids.has((x as Combatant).uid):
			dup = true
		uids[(x as Combatant).uid] = true
	t.eq(dup, false, "uid 全局唯一")


## 估值：没有它，前面六节全绿也没用——AI 一次都不会选。
static func _test_score(t: TestLib, db: DdDb) -> void:
	t.section("召唤：估值")
	var b := Battle.new()
	b.setup(HEROES, ["brigand_cannon_A"], 408)
	var actor: Combatant = b.enemies[0]
	var action: Dictionary = _summon_action(actor)
	var s_on: float = b._eval_summon(action, actor)
	t.ok(s_on > 0.0, "召唤有正估值（%.2f）" % s_on)

	b.summon_value_enabled = false
	t.eq(b._eval_summon(action, actor), 0.0, "关掉估值后归零")
	b.summon_value_enabled = true
	b.summon_enabled = false
	t.eq(b._eval_summon(action, actor), 0.0, "关掉实现后估值也归零（避免空过）")
	b.summon_enabled = true

	# 满位时估值必须是 0：否则 AI 会反复选一个注定失败的动作。
	var b2 := Battle.new()
	b2.setup(HEROES, ["brigand_cannon_A", "cultist_brawler_A",
		"cultist_brawler_A", "cultist_brawler_A"], 409)
	var a2: Combatant = b2.enemies[0]
	t.eq(b2._eval_summon(_summon_action(a2), a2), 0.0, "满位时估值为 0")

	# 召唤**不吃命中率**：数据里 59 条全是 on_hit / on_miss 双 true。
	# 乘命中率会让低命中召唤者永不召唤，而它实际照样召得出来。
	var b3 := Battle.new()
	b3.setup(HEROES, ["brigand_cannon_A"], 410)
	var a3: Combatant = b3.enemies[0]
	a3.base_acc = -9.0     # 命中率压到地板
	var s_low: float = b3._eval_summon(_summon_action(a3), a3)
	t.ok(s_low > 0.0, "命中率极低时召唤估值仍为正（%.2f）" % s_low)


## 技能标记：`summon` 信息在 setup 就打进 action，战斗中不能再解析
## （_score 每个候选都调一次，一旦抽了 rng，基线会悄悄漂移）。
static func _test_action_tag(t: TestLib, db: DdDb) -> void:
	t.section("召唤：技能标记")
	var b := Battle.new()
	b.setup(HEROES, ["necromancer_A"], 411)
	var actor: Combatant = b.enemies[0]
	var tagged: int = 0
	for a in actor.actions:
		if (a as Dictionary).has("summon"):
			tagged += 1
			var info: Dictionary = a.get("summon", {})
			if not info.is_empty():
				t.ok((info.get("ids", []) as Array).size() > 0, "标记里带候选列表")
	t.eq(tagged, actor.actions.size(), "每个技能都带 summon 键（空字典表示不是召唤技）")

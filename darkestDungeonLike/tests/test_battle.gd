class_name TestBattle
extends RefCounted
## 整场战斗回归。这一层测的是「多个系统拼在一起还对不对」，
## 单看每块都对、装起来就歪，是这类移植最常见的翻车方式。

const HEROES: Array = ["crusader", "highwayman", "vestal", "plague_doctor"]
const MONSTERS: Array = ["cultist_brawler_A", "cultist_brawler_A", "cultist_witch_A"]


static func run(t: TestLib, db: DdDb) -> void:
	t.section("战斗装配")
	var b := Battle.new()
	t.eq(b.setup(HEROES, MONSTERS, 20261102), true, "4 英雄 vs 3 怪物装配成功")
	t.eq(b.party.size(), 4, "我方 4 人")
	t.eq(b.enemies.size(), 3, "敌方 3 人")
	t.eq(b.party[0].rank, 0, "1 号位 rank 为 0")
	t.eq(b.enemies[2].rank, 2, "3 号位 rank 为 2")
	t.eq(b.is_over(), false, "开局未结束")

	var crusader: Combatant = b.party[0]
	t.eq(crusader.base_hp, 33, "十字军 33 生命")
	t.eq(crusader.hp, 33, "开局满血")
	t.ok(crusader.actions.size() > 0, "技能已装载")
	t.eq(EffectResolver.collect_attack_mods(db, crusader.actions[0].effects,
		crusader, b.enemies[0]).has("damage_mod"), true, "攻击修正接口可用")

	t.section("单轮结算")
	b = Battle.new()
	b.setup(HEROES, MONSTERS, 424242)
	var ev: Array = b.run_round()
	t.ok(ev.size() > 0, "产生了事件")
	t.eq(str(ev[0]["t"]), "round_start", "首事件为回合开始")
	t.eq(b.round_index, 1, "回合计数为 1")

	var order_ev: Dictionary = _first(ev, "order")
	t.eq((order_ev["ids"] as Array).size(), 7, "行动序包含全部 7 个单位")

	var turns: int = 0
	for e in ev:
		if str(e["t"]) == "turn":
			turns += 1
	t.ok(turns >= 5, "至少 5 个单位行动过，实际 %d" % turns)

	var attacks: int = 0
	var misses: int = 0
	for e in ev:
		match str(e["t"]):
			"attack":
				attacks += 1
				t.ok(int(e["damage"]) >= 0, "伤害非负")
			"miss":
				misses += 1
	t.ok(attacks + misses > 0, "本轮至少发生一次攻击判定")

	t.section("整场战斗可收敛")
	var b2 := Battle.new()
	b2.setup(HEROES, MONSTERS, 999)
	b2.run_until_over(30)
	t.ok(b2.round_index <= 30, "30 轮内结束，实际 %d 轮" % b2.round_index)
	t.ok(b2.winner() in ["party", "enemy"], "有明确的胜方：%s" % b2.winner())

	for u in b2.party:
		t.ok(u.hp >= 0, "%s 生命不为负" % u.display_name)
		if u.dead:
			t.ok(u.hp == 0, "阵亡者生命归零")
		if u.at_deaths_door:
			t.ok(u.hp == 0, "死门状态生命为 0")
	for u in b2.enemies:
		if u.dead:
			t.ok(u.hp == 0, "死亡怪物生命归零，实际 %d" % u.hp)

	t.section("同种子可复现")
	var b3 := Battle.new()
	b3.setup(HEROES, MONSTERS, 13579)
	b3.run_until_over(20)
	var b4 := Battle.new()
	b4.setup(HEROES, MONSTERS, 13579)
	b4.run_until_over(20)
	t.eq(b3.round_index, b4.round_index, "两次运行轮数一致")
	t.eq(JSON.stringify(_digest(b3)), JSON.stringify(_digest(b4)), "两次运行状态快照完全一致")

	t.section("压力只落在英雄身上")
	var b5 := Battle.new()
	b5.setup(HEROES, MONSTERS, 24680)
	b5.run_until_over(25)
	for u in b5.enemies:
		t.eq(u.stress, 0.0, "怪物不累积压力")
	var any_stress: bool = false
	for u in b5.party:
		if u.stress > 0.0:
			any_stress = true
		t.ok(u.stress >= 0.0 and u.stress <= 200.0, "英雄压力在 0-200 之间")
	t.ok(any_stress or b5.winner() == "party", "战斗过程产生过压力或速胜")

	t.section("多个种子都能跑通")
	var wins: Dictionary = {"party": 0, "enemy": 0, "": 0}
	for s in range(20):
		var bb := Battle.new()
		bb.setup(HEROES, MONSTERS, 1000 + s)
		bb.run_until_over(30)
		wins[bb.winner()] = int(wins.get(bb.winner(), 0)) + 1
		if str(wins.get("", 0)) != "0":
			pass
	_test_movement(t, db)

	t.eq(int(wins[""]), 0, "20 个种子全部正常分出胜负")
	t.ok(int(wins["party"]) > 0, "英雄能赢（%d/20）" % int(wins["party"]))


# ------------------------------------------------------------
# 位移（M9）
# ------------------------------------------------------------
#
# 这一节是为了把一段**死代码**钉住。`effect_resolver` 里 push/pull 会算出
# `out["move"]`，`_relayout()` 也写好了，但两者之间没有任何东西把它们连起来：
# 位移结果写进事件后就被丢掉了，`_relayout` 从开局起再没被调用过。
#
# 所以先写断言、先跑红，再实现——否则「修好了」只是我自己的说法。
static func _test_movement(t: TestLib, db: DdDb) -> void:
	t.section("位移")
	var b := Battle.new()
	b.setup(HEROES, MONSTERS, 777)
	var target: Combatant = b.enemies[0]
	var uid: int = target.uid
	t.eq(target.rank, 0, "目标初始站在 1 号位")

	# 走 Battle 的公开路径，而不是直接调 EffectResolver——直接调只能证明
	# 「算出了位移量」，证明不了「位置变了」。这两件事正是原来的断点。
	#
	# M11 起位移要吃目标的 move 抗性（怪物 0~0.95），这一节测的是**位移机制**
	# 本身而不是抗性，所以显式关掉抗性——否则断言会因为「这次抽到了抵抗」
	# 随机变红，而失败信息只会说「位置没变」，看起来像位移坏了。
	# 抗性本身在 tests/test_move.gd 里单独测。
	var ctx: Dictionary = {"hit": true, "rng": DdRng.new(1), "all_units": b.all_units(),
		"move_resist_enabled": false}
	var push1: Dictionary = {"id": "test_push_1", "effects": ["Push 1A"]}
	b.apply_effects(push1, b.party[0], target, ctx)

	# 核心断言：位置必须真的变。只写事件不算。
	t.eq(target.rank, 1, "推 1 格后站到 2 号位（实际 %d）" % target.rank)
	# 被推的人现在在数组第 2 个，原本第 2 个被挤到第 1 个
	t.eq(int(b.enemies[1].uid), uid, "被推的单位移到数组第 2 位")
	t.eq(b.enemies[0].rank, 0, "原本 2 号位的怪被挤到 1 号位（实际 %d）" % b.enemies[0].rank)
	t.eq(int(b.enemies[0].uid) == uid, false, "被挤开的不是被推的那个")

	# 挤到边界就停，不能越界，也不能把人挤出去
	var last: Combatant = b.enemies[b.enemies.size() - 1]
	var last_rank: int = last.rank
	b.apply_effects({"id": "test_push_2", "effects": ["Push 2A"]}, b.party[0], last,
		{"hit": true, "rng": DdRng.new(2), "all_units": b.all_units(),
			"move_resist_enabled": false})
	t.eq(last.rank, last_rank, "最后一格再被推仍然留在最后一格")
	t.eq(b.enemies.size(), 3, "队伍人数不变")

	# pull 是反方向（test_move 是 pull 2）
	var back: Combatant = b.enemies[b.enemies.size() - 1]
	var back_rank: int = back.rank
	b.apply_effects({"id": "test_pull", "effects": ["test_move"]}, b.party[0], back,
		{"hit": true, "rng": DdRng.new(3), "all_units": b.all_units(),
			"move_resist_enabled": false})
	t.eq(back.rank, back_rank - 2, "拉 2 格前移两格（%d → %d）" % [back_rank, back.rank])

	# —— 主动移动：英雄第一次能换位 ——
	var mb := Battle.new()
	mb.setup(HEROES, MONSTERS, 778)
	var cr: Combatant = mb.party[0]
	t.eq(cr.move_action.is_empty(), false, "十字军装载了移动技能")
	var mv1: Array = cr.move_action.get("move", [])
	t.eq("%d,%d" % [int(mv1[0]), int(mv1[1])], "1,1", "crusader 的 move 是 [1,1]")
	t.eq(str(mb.move_options(cr)), str([1]), "站在 1 号位只能往后挪一格")
	var pd: Combatant = mb.party[3]
	t.eq(str(mb.move_options(pd)), str([2]), "站在 4 号位只能往前挪一格")
	# highwayman 的 move 是 [2,2]：只能跳两格，不能走一格
	var hm: Combatant = mb.party[1]
	var mv2: Array = hm.move_action.get("move", [])
	t.eq("%d,%d" % [int(mv2[0]), int(mv2[1])], "2,2", "highwayman 的 move 是 [2,2]")
	t.eq(str(mb.move_options(hm)), str([3]), "站在 2 号位的强盗只能跳到 4 号位")

	t.eq(mb.perform_move(cr, 1), true, "十字军能挪到 2 号位")
	t.eq(cr.rank, 1, "十字军 rank 变成 1")
	t.eq(int(mb.party[1].uid), int(cr.uid), "移动后十字军占了数组第 2 位")
	t.eq(mb.party[0].rank, 0, "原本 2 号位的人被挤到 1 号位")
	t.eq(int(mb.party[0].uid) == int(cr.uid), false, "被挤开的是别人")
	t.eq(mb.perform_move(cr, 3), false, "不能一次挪到不合法位置")

	# 站位连续性：任何一次位移之后，rank 必须是 0..n-1 的排列
	var ranks: Array = []
	for u in b.all_units():
		ranks.append(u.rank)
	var pair: Dictionary = {}
	for r in b.party:
		pair[r.rank] = true
	t.eq(pair.size(), b.party.size(), "我方 rank 互不重复")
	var foe_pair: Dictionary = {}
	for r2 in b.enemies:
		foe_pair[r2.rank] = true
	t.eq(foe_pair.size(), b.enemies.size(), "敌方 rank 互不重复")


static func _first(events: Array, type_name: String) -> Dictionary:
	for e in events:
		if str(e["t"]) == type_name:
			return e
	return {}


## 状态快照：只要是确定性实现，同种子两次运行必然一致
static func _digest(b: Battle) -> Array:
	var out: Array = []
	for u in b.all_units():
		out.append({
			"id": u.def_id, "hp": u.hp, "stress": snappedf(u.stress, 0.001),
			"dead": u.dead, "buffs": u.buffs.size(), "dots": u.dots.size(),
		})
	return out


## M18：僵持（打到回合上限）。
##
## 这一条原本只在同步驱动（`run_until_over`）里有上限，**逐步驱动没有**——
## 界面和自检走的都是逐步驱动，所以「双方互相打不死」时会无限加轮。
## M18 的自检撞上过一场 228 回合的战斗，卡在那儿不动。
##
## 这些断言直接推到上限，不靠真的跑几十轮——那样既慢又不能定位边界。
static func run_stalemate(t: TestLib, db: DdDb) -> void:
	t.section("战斗：回合上限与僵持")

	var b := Battle.new()
	b.setup(HEROES, MONSTERS, 20261118)
	t.eq(b.stalemate, false, "开局不是僵持")
	t.eq(b.is_over(), false, "开局未结束")

	# 推到上限前一轮：还在正常
	b.round_index = Battle.MAX_ROUNDS - 1
	b._round_open = false
	b.begin_round()
	t.eq(b.stalemate, false, "第 %d 轮仍正常" % Battle.MAX_ROUNDS)
	t.eq(int(b.round_index), Battle.MAX_ROUNDS, "轮数已到上限")

	# 再开一轮：判定僵持
	b._round_open = false
	b.begin_round()
	t.eq(b.stalemate, true, "到上限后判僵持")
	t.eq(b.is_over(), true, "僵持即结束")
	t.eq(b.winner(), "none", "僵持没有赢家（不是 party 也不是 enemy）")

	# 僵持之后再次 begin_round 不该继续推进
	var r_before: int = int(b.round_index)
	b._round_open = false
	b.begin_round()
	t.eq(int(b.round_index), r_before, "僵持后再开轮不会推进轮数")

	# 正常战斗不该被误判：第 1 轮开完仍是 false
	var b2 := Battle.new()
	b2.setup(HEROES, MONSTERS, 20261119)
	b2.begin_round()
	t.eq(b2.stalemate, false, "第 1 轮不会误判僵持")
	t.eq(int(b2.round_index), 1, "第 1 轮轮数为 1")

	# 上限值本身：太小会让正常战斗被切断，太大则形同没有
	t.ok(Battle.MAX_ROUNDS >= 30, "上限 %d 轮不小于 30（正常战斗 5–15 轮）"
		% Battle.MAX_ROUNDS)

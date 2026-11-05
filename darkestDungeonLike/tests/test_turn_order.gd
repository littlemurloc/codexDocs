class_name TestTurnOrder
extends RefCounted
## 行动序测试。
##
## 重点不是「排序对不对」，而是「快的人是不是更常先手」——
## DD1 每轮重掷先攻，速度的优势是概率性的，这一点必须用统计检验，
## 不能靠单次结果判断。


static func run(t: TestLib) -> void:
	t.section("行动序覆盖")
	var units: Array = [
		_unit("fast", 8.0), _unit("slow", 1.0),
		_unit("mid_a", 5.0), _unit("mid_b", 5.0),
		_unit("mid_c", 5.0), _unit("mid_d", 5.0),
	]
	var rng := DdRng.new(2026)
	var order: Array = TurnScheduler.build_order(units, rng, 8)
	t.eq(order.size(), 6, "6 个存活单位全部进入行动序")
	var seen: Dictionary = {}
	for e in order:
		seen[e.actor.display_name] = true
	t.eq(seen.size(), 6, "无重复无遗漏")

	t.section("先攻区间")
	var lo: float = INF
	var hi: float = -INF
	for i in 200:
		var o: Array = TurnScheduler.build_order([_unit("a", 5.0)], DdRng.new(1000 + i), 8)
		lo = minf(lo, float(o[0].initiative))
		hi = maxf(hi, float(o[0].initiative))
	t.ok(lo >= 5.0, "先攻不低于速度本身，最低 %s" % str(lo))
	t.ok(hi <= 13.0, "先攻不高于 速度+8，最高 %s" % str(hi))
	t.ok(hi - lo >= 6.0, "先攻确实有随机跨度，实际跨度 %s" % str(hi - lo))

	t.section("速度优势是概率性的")
	var fast_first: int = 0
	var trials: int = 600
	for i in trials:
		var o: Array = TurnScheduler.build_order(
			[_unit("fast", 8.0), _unit("slow", 1.0)], DdRng.new(5000 + i), 8)
		if o[0].actor.display_name == "fast":
			fast_first += 1
	var ratio: float = float(fast_first) / float(trials)
	# 速度 8 vs 1：先攻 = 速度 + 0..8。快方只在掷出 0 且慢方掷出 8 时落后，
	# 概率约 1/81 ≈ 1.2%，所以先手率应在 98% 以上——这印证了
	# 「先攻加 d8」这个推断：速度差 7 档时，运气几乎无法翻盘。
	t.between(ratio, 0.96, 1.0, "速度 8 对 1 先手率应在 98%% 以上")
	t.ok(ratio < 1.0, "速度高也不是必然先手（保留运气成分）")

	t.section("同速时不会出现确定性偏差")
	var a_first: int = 0
	for i in 400:
		var o: Array = TurnScheduler.build_order(
			[_unit("a", 5.0), _unit("b", 5.0)], DdRng.new(9000 + i), 8)
		if o[0].actor.display_name == "a":
			a_first += 1
	var r2: float = float(a_first) / 400.0
	t.between(r2, 0.40, 0.60, "同速双方先手率应接近 50%%，实际 %.3f" % r2)

	t.section("死亡单位不参与")
	var dead := _unit("dead_one", 9.0)
	dead.dead = true
	dead.hp = 0
	var o3: Array = TurnScheduler.build_order([_unit("alive", 3.0), dead], DdRng.new(77), 8)
	t.eq(o3.size(), 1, "死亡的 9 速单位不进行动序")


static func _unit(name: String, speed: float) -> Combatant:
	var c := Combatant.new()
	c.display_name = name
	c.side = Combatant.SIDE_PARTY
	c.base_speed = speed
	c.base_hp = 20
	c.hp = 20
	return c

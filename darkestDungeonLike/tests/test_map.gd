class_name TestMap
extends RefCounted
## 房间图生成的回归测试。
##
## 生成器最典型的失败方式不是崩溃，而是「生成了但不像地图」：
## 房间重叠、图不连通、走廊横跨半张图、入口和目标挨在一起。
## 这些都不会报错，只会在玩的时候觉得怪。所以每条都要断言。

static func run(t: TestLib, db: DdDb) -> void:
	_test_basic(t, db)
	_test_shape(t, db)
	_test_content(t, db)
	_test_hallway(t, db)


static func _test_basic(t: TestLib, db: DdDb) -> void:
	t.section("地图生成：基本性质")
	var m: Dictionary = MapGen.build(db, "weald", "medium", 3, DdRng.new(101))
	t.ok(not m.is_empty(), "medium 图生成成功")
	t.eq((m["room_ids"] as Array).size(), 14, "房间数等于 base_room_number")
	t.eq(int(m["start"]) != int(m["goal"]), true, "入口与目标不是同一间房")
	t.eq(str((m["rooms"][int(m["start"])] as Dictionary)["kind"]), MapGen.K_START, "入口类型正确")
	t.eq(str((m["rooms"][int(m["goal"])] as Dictionary)["kind"]), MapGen.K_GOAL, "目标类型正确")
	t.eq(MapGen.all_reachable(m), true, "所有房间都可达")

	# 同种子必须同图：否则「同一张图换预设对比」的对照实验不成立
	var a: Dictionary = MapGen.build(db, "weald", "long", 5, DdRng.new(777))
	var b: Dictionary = MapGen.build(db, "weald", "long", 5, DdRng.new(777))
	t.eq(JSON.stringify(_digest(a)), JSON.stringify(_digest(b)), "同种子生成完全一致")

	# 房间不能重叠
	var seen: Dictionary = {}
	var dup: int = 0
	for id in (m["room_ids"] as Array):
		var p: Vector2i = (m["rooms"][int(id)] as Dictionary)["pos"]
		if seen.has(p):
			dup += 1
		seen[p] = true
	t.eq(dup, 0, "没有两个房间占同一格")


static func _test_shape(t: TestLib, db: DdDb) -> void:
	t.section("地图生成：形状")
	for size in ["short", "medium", "long"]:
		var mp: Dictionary = db.map_for("weald", size)
		var need: int = int(mp.get("min_final_distance", 3))
		var conn: int = 0
		var deep: int = 0
		var near: int = 0
		var runs: int = 12
		for i in runs:
			var m: Dictionary = MapGen.build(db, "weald", size, 3, DdRng.new(2000 + i))
			if m.is_empty():
				continue
			if MapGen.all_reachable(m):
				conn += 1
			if MapGen.shortest_path(m) >= need:
				deep += 1
			var all_near: bool = true
			for e in (m["edges"] as Array):
				var pa: Vector2i = (m["rooms"][int(e.a)] as Dictionary)["pos"]
				var pb: Vector2i = (m["rooms"][int(e.b)] as Dictionary)["pos"]
				if absi(pa.x - pb.x) + absi(pa.y - pb.y) > 2:
					all_near = false
			if all_near:
				near += 1
		t.eq(conn, runs, "%s：全部连通（%d/%d）" % [size, conn, runs])
		t.eq(deep, runs, "%s：入口到目标都 >= %d 跳（%d/%d）" % [size, need, deep, runs])
		t.eq(near, runs, "%s：走廊都连相邻房间（%d/%d）" % [size, near, runs])

	# 图上的最短路要和缓存的 shortest 一致
	var m2: Dictionary = MapGen.build(db, "weald", "medium", 3, DdRng.new(55))
	t.eq(MapGen.shortest_path(m2), int(m2["shortest"]), "缓存的最短路与实际一致")

	# 邻接表与边表自洽
	var bad: int = 0
	for id in (m2["room_ids"] as Array):
		for ei in ((m2["adj"] as Dictionary)[int(id)] as Array):
			var e: Dictionary = (m2["edges"] as Array)[int(ei)]
			if int(e.a) != int(id) and int(e.b) != int(id):
				bad += 1
	t.eq(bad, 0, "邻接表里的每条边都真的连着该房间")


static func _test_content(t: TestLib, db: DdDb) -> void:
	t.section("地图生成：内容投放")
	var m: Dictionary = MapGen.build(db, "weald", "medium", 3, DdRng.new(9))
	var rooms: Dictionary = m["rooms"]
	var battles: int = 0
	var curios: int = 0
	var bad_step: int = 0
	for id in (m["room_ids"] as Array):
		var r: Dictionary = rooms[int(id)]
		match str(r["kind"]):
			MapGen.K_BATTLE:
				battles += 1
				var st: Dictionary = r["step"]
				if str(st.get("kind", "")) != "battle" or (st.get("monsters", []) as Array).is_empty():
					bad_step += 1
			MapGen.K_CURIO:
				curios += 1
	t.eq(bad_step, 0, "战斗房的 step 都是合法遭遇")
	t.ok(battles >= 1, "至少有 1 个战斗房（实际 %d）" % battles)
	t.ok(curios >= 0, "奇物房数量非负（实际 %d）" % curios)

	# 起始房与目标房不挂战斗：一进去就打、或刚到就打的体验都很差
	t.eq(str((rooms[int(m["start"])] as Dictionary)["kind"]), MapGen.K_START, "起始房不挂战斗")
	t.eq(str((rooms[int(m["goal"])] as Dictionary)["kind"]), MapGen.K_GOAL, "目标房不挂战斗")

	var hall_battles: int = 0
	var hungers: int = 0
	var hall_bad: int = 0
	for e in (m["edges"] as Array):
		for st2 in (e["steps"] as Array):
			var k: String = str((st2 as Dictionary).get("kind", ""))
			if k == "battle":
				hall_battles += 1
				if ((st2 as Dictionary).get("monsters", []) as Array).is_empty():
					hall_bad += 1
			elif k == "hunger":
				hungers += 1
	t.eq(hall_bad, 0, "走廊战斗的遭遇都合法")
	t.ok(hall_battles + hungers <= (m["edges"] as Array).size(), "走廊事件数不超过走廊数")

	# 不同地牢形状不同：weald 成簇、crypts 更散
	var w: Dictionary = MapGen.build(db, "weald", "medium", 3, DdRng.new(31))
	var c: Dictionary = MapGen.build(db, "crypts", "medium", 3, DdRng.new(31))
	t.eq((w["room_ids"] as Array).size(), (c["room_ids"] as Array).size(), "两个地牢房间数相同")
	t.eq(MapGen.all_reachable(c), true, "crypts 图同样连通")


## 只取结构信息做快照：位置、类型、边。用于同种子一致性比较。
static func _digest(m: Dictionary) -> Dictionary:
	var rooms: Array = []
	for id in (m["room_ids"] as Array):
		var r: Dictionary = m["rooms"][int(id)]
		var p: Vector2i = r["pos"]
		rooms.append([int(id), p.x, p.y, str(r["kind"])])
	var edges: Array = []
	for e in (m["edges"] as Array):
		edges.append([int(e.a), int(e.b), (e["steps"] as Array).size()])
	return {"rooms": rooms, "edges": edges, "start": int(m["start"]), "goal": int(m["goal"])}


# ------------------------------------------------------------
# 走廊内容配额（M8）
# ------------------------------------------------------------

## 配额分配是这一层最容易悄悄出错的地方：算错了不会崩，只会让某类内容
## 在某档地图上整类消失。所以单独钉住它的三条不变量。
static func _test_hallway(t: TestLib, db: DdDb) -> void:
	t.section("走廊内容：配额分配")

	var q: Array = MapGen._allocate([4, 5, 4, 4], 8)
	var sum: int = 0
	for v in q:
		sum += int(v)
	t.eq(sum, 8, "分配结果正好用满容量")
	var all_pos: bool = true
	for i in q.size():
		if int(q[i]) < 1:
			all_pos = false
	t.eq(all_pos, true, "每类至少保留 1 个（%s）" % str(q))

	var loose: Array = MapGen._allocate([1, 1, 1, 1], 10)
	t.eq(str(loose), str([1, 1, 1, 1]), "容量宽松时原样返回")

	var tight: Array = MapGen._allocate([3, 3, 1, 1], 3)
	var tsum: int = 0
	for v in tight:
		tsum += int(v)
	t.eq(tsum, 3, "容量不足时也不超发（%s）" % str(tight))

	# 任何情况下都不能超出 wanted：多给一类等于从别类偷
	var wants: Array = [3, 2, 1, 1]
	var q2: Array = MapGen._allocate(wants, 5)
	var over: bool = false
	for i in wants.size():
		if int(q2[i]) > int(wants[i]):
			over = true
	t.eq(over, false, "分配结果不超出各类需求（%s）" % str(q2))

	# 生成出来的图：四类都该出现，且必须留出空走廊
	t.section("走廊内容：生成结果")
	var tally: Dictionary = {"battle": 0, "trap": 0, "obstacle": 0, "hunger": 0, "none": 0}
	var runs: int = 24
	for i in runs:
		var m: Dictionary = MapGen.build(db, "weald", "medium", 3, DdRng.new(500 + i))
		for e in (m["edges"] as Array):
			var sts: Array = (e as Dictionary).get("steps", [])
			var k: String = "none" if sts.is_empty() else str((sts[0] as Dictionary)["kind"])
			tally[k] = int(tally.get(k, 0)) + int(1)
	for k2 in ["battle", "trap", "obstacle", "hunger"]:
		t.ok(int(tally[k2]) > 0, "%s 在 %d 张图里出现过（%d 次）" % [k2, runs, int(tally[k2])])
	t.ok(int(tally["none"]) > 0, "仍有空走廊（%d 条），安全路线存在" % int(tally["none"]))

	# 陷阱步必须带等级：难度靠它算，缺了会静默退回 1 级
	var m2: Dictionary = MapGen.build(db, "weald", "long", 5, DdRng.new(9))
	var bad: int = 0
	for e2 in (m2["edges"] as Array):
		for st in ((e2 as Dictionary)["steps"] as Array):
			if str((st as Dictionary).get("kind", "")) == "trap" and int((st as Dictionary).get("level", -1)) != 5:
				bad += 1
	t.eq(bad, 0, "陷阱步带地牢等级")

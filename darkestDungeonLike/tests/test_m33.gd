class_name TestM33
extends RefCounted
## M33 任务奇物标签化 + 收集 / 激活任务。
##
## 这一期的核心不是「多接两种任务」，而是**承认数据缺了一整层**：
## `quests.json` 让任务去 10 个奇物上收集/激活，其中 9 个在抽取数据里
## 根本不存在（M32 §5 查出来的）。所以目标不能硬编一个 id 替换掉，
## 只能降到标签层：「任务要的是一类东西，区域内带这个标签的奇物都算」。
##
## 三条最容易写错的：
##
## 1. **解析必须是确定的**。同一个（奇物名，区域）永远落到同一个 id，
##    否则同一张任务卡每次进图指的东西都不一样，玩家没法记。
## 2. **地图必须真的放够目标奇物**。这类地图的普通奇物只有 1–2 个、
##    还全是随机种类；不额外投放的话任务几乎必然做不完，
##    而这种「做不完」不会报错，只会让玩家觉得运气差。
## 3. **同一处只算一次**。重走一条走廊不能重复计数，
##    否则要 3 件的任务走两次同一条路就完成了。

const TEST_PATH: String = "user://test_m33_unit.json"
const HEROES: Array = ["crusader", "highwayman", "vestal", "plague_doctor"]


static func run(t: TestLib, db: DdDb) -> void:
	_test_resolve(t, db)
	_test_inject(t, db)
	_test_count(t, db)
	_test_board(t, db)
	_cleanup()


# ------------------------------------------------------------
# 1. 标签解析
# ------------------------------------------------------------

static func _test_resolve(t: TestLib, db: DdDb) -> void:
	t.section("任务奇物：标签解析")
	var curios: Dictionary = db.curio_lib.curios
	t.ok(not curios.is_empty(), "奇物表加载了（%d 个）" % curios.size())

	# 唯一一个真存在的：直接命中，不该走标签
	t.eq(QuestGoal.resolve_curio("iron_maiden", "crypts", curios), "iron_maiden",
		"铁处女本身就是真的，直接用它")
	t.eq(QuestGoal.resolve_curio("iron_maiden", "weald", curios), "",
		"铁处女只属于墓穴，放到荒野解析不出来")

	# 九个不存在的：按标签落到同区域的真奇物上
	var cases: Array = [
		["reliquary", "crypts", "Worship"],
		["chirurgeons_satchel", "weald", "Scrounging"],
		["foodstuff_crate", "warrens", "Food"],
		["shipment_crates", "cove", "Treasure"],
		["corrupted_altar", "cove", "Worship"],
		["infected_corpse", "warrens", "Haunted"],
		["animalistic_shrine", "warrens", "Unholy"],
	]
	var bad: int = 0
	for row in cases:
		var name: String = str(row[0])
		var region: String = str(row[1])
		var tag: String = str(row[2])
		var got: String = QuestGoal.resolve_curio(name, region, curios)
		if got.is_empty():
			bad += 1
			t.ok(false, "%s 在 %s 上解析失败" % [name, region])
			continue
		var def: Dictionary = curios.get(got, {})
		if not (def.get("tags", []) as Array).has(tag):
			bad += 1
			t.ok(false, "%s 解析到 %s，但后者没有标签 %s" % [name, got, tag])
	t.eq(bad, 0, "7 个残缺目标全部落到带正确标签的真实奇物上")

	# 确定性与区域优先：同一区域里的奇物优先于 ALL
	var a: String = QuestGoal.resolve_curio("reliquary", "crypts", curios)
	var b: String = QuestGoal.resolve_curio("reliquary", "crypts", curios)
	t.eq(a, b, "同一次解析结果稳定")
	var reg: String = str((curios.get(a, {}) as Dictionary).get("region", ""))
	t.eq(reg, "Ruins", "优先落在本区域的奇物上（不是 ALL）")
	t.eq(QuestGoal.resolve_curio("no_such_curio", "weald", curios), "",
		"表里没有的名字解析不出来")
	t.eq(QuestGoal.resolve_curio("reliquary", "weald", curios),
		QuestGoal.resolve_curio("reliquary", "weald", curios), "重复调用结果一致")


# ------------------------------------------------------------
# 2. 地图投放
# ------------------------------------------------------------

## 图上所有「能碰到的目标奇物」（含自然刷新 + 任务投放）。
## 这才是玩家真正数得到的东西——判据也是按这个来的。
static func _count_quest_curios(m: Dictionary, cid: String) -> int:
	var n: int = 0
	for id in (m["room_ids"] as Array):
		var st: Dictionary = (m["rooms"][int(id)] as Dictionary).get("step", {})
		if str(st.get("curio", "")) == cid:
			n += 1
	for e in (m["edges"] as Array):
		var steps: Array = (e as Dictionary).get("steps", [])
		if steps.is_empty():
			continue
		if str((steps[0] as Dictionary).get("curio", "")) == cid:
			n += 1
	return n


## 只数「被投进来的」任务奇物（step 上带 quest 标记）。
##
## 不能只比 curio id：探索地图也可能**自然地**刷出同一个奇物
## （同一个种子下 crate 之类到处都有），那样断言「探索图里 0 个」
## 会随机红，而红的理由是数据随机，不是代码坏了。
static func _count_injected(m: Dictionary) -> int:
	var n: int = 0
	for id in (m["room_ids"] as Array):
		var st: Dictionary = (m["rooms"][int(id)] as Dictionary).get("step", {})
		if bool(st.get("quest", false)):
			n += 1
	for e in (m["edges"] as Array):
		var steps: Array = (e as Dictionary).get("steps", [])
		if steps.is_empty():
			continue
		if bool((steps[0] as Dictionary).get("quest", false)):
			n += 1
	return n


static func _test_inject(t: TestLib, db: DdDb) -> void:
	t.section("地图投放：目标奇物必须够数")
	var qg: Dictionary = QuestGoal.parse(db.quests, "gather", "weald", db.curio_lib.curios)
	t.eq(bool(qg.get("supported", false)), true, "荒野的收集任务能解析出目标")
	var cid: String = str(qg.get("curio", ""))
	var need: int = int(qg.get("amount", 0))
	t.ok(need > 0, "要收集 %d 件" % need)

	var m: Dictionary = MapGen.build(db, "weald", "medium", 3, DdRng.new(9182), "gather")
	t.ok(not m.is_empty(), "收集地图能生成")
	var got: int = _count_quest_curios(m, cid)
	t.ok(got >= need, "图上有 %d 个「%s」（需要 %d 个）" % [got,
		DdNames.curio_name(cid), need])

	# 投放不能占掉入口/出口，也不能减少房间数
	var start: int = int(m["start"])
	var goal: int = int(m["goal"])
	var on_start: bool = str(((m["rooms"][start] as Dictionary).get("step", {}) as Dictionary)
		.get("curio", "")) == cid
	var on_goal: bool = str(((m["rooms"][goal] as Dictionary).get("step", {}) as Dictionary)
		.get("curio", "")) == cid
	t.eq(on_start, false, "入口房间不放目标奇物")
	t.eq(on_goal, false, "终点房间不放目标奇物")
	t.eq((m["room_ids"] as Array).size(), int((m["content"] as Dictionary).get("rooms", 0)),
		"投放不改房间数")

	# 探索地图不该有任何**投进来**的任务奇物（自然刷出来的不算）
	var me: Dictionary = MapGen.build(db, "weald", "medium", 3, DdRng.new(9182), "explore")
	t.eq(_count_injected(me), 0, "探索地图不投任务奇物")
	# 投放只加内容、不改形状：房间数应该等于这类图自己的参数
	var mp_g: Dictionary = db.map_for("weald", "medium", "gather")
	var mp_e: Dictionary = db.map_for("weald", "medium", "explore")
	t.eq((m["room_ids"] as Array).size(), int(mp_g.get("base_room_number", -1)),
		"收集图的房间数 = 它自己的 base_room_number（投放没改形状）")
	t.eq((me["room_ids"] as Array).size(), int(mp_e.get("base_room_number", -1)),
		"探索图的房间数 = 它自己的 base_room_number")

	# 激活：铁处女只放 1 个
	var ma: Dictionary = MapGen.build(db, "crypts", "medium", 3, DdRng.new(9182), "activate")
	t.ok(not ma.is_empty(), "激活地图能生成")
	t.eq(_count_quest_curios(ma, "iron_maiden"), 1, "图上有 1 个铁处女")


# ------------------------------------------------------------
# 3. 计数
# ------------------------------------------------------------

static func _test_count(t: TestLib, db: DdDb) -> void:
	t.section("收集：碰一次算一件")
	var preset: Dictionary = db.expedition_cfg.preset("standard")
	var m: Dictionary = MapGen.build(db, "weald", "medium", 3, DdRng.new(5150), "gather")
	var e := Expedition.new()
	e.setup(db, HEROES, [], preset, 5150, "standard", {}, {})
	e.set_location("weald", "medium", 3, "gather")
	e.enter_map(m)

	var cid: String = str(e.quest_goal.get("curio", ""))
	var need: int = int(e.quest_goal.get("amount", 0))
	t.ok(not cid.is_empty(), "远征层拿到了目标奇物 id")
	t.eq(int(e.stats.get("quest_gathered", 0)), 0, "开局 0 件")
	t.eq(e.quest_met(), false, "0 件不算完成")

	# 碰一个不是目标的奇物：不算
	e.resolve_curio({"curio": "crate", "room": 900})
	if cid != "crate":
		t.eq(int(e.stats.get("quest_gathered", 0)), 0, "碰到别的奇物不算收集")

	# 碰目标奇物：+1；同一处第二次不再加；换一处继续加
	e.resolve_curio({"curio": cid, "room": 1})
	t.eq(int(e.stats.get("quest_gathered", 0)), 1, "碰目标奇物 +1")
	e.resolve_curio({"curio": cid, "room": 1})
	t.eq(int(e.stats.get("quest_gathered", 0)), 1,
		"同一处再碰一次不再加（否则走回头路就能刷满）")
	e.resolve_curio({"curio": cid, "room": 2})
	t.eq(int(e.stats.get("quest_gathered", 0)), 2,
		"换一处目标奇物继续加（图上本来就该有 3 个）")
	# 走廊上的目标奇物用 edge 当键，和房间的 room 不冲突
	e.resolve_curio({"curio": cid, "edge": 1})
	t.eq(int(e.stats.get("quest_gathered", 0)), 3, "走廊上的目标奇物也算一处")

	# 补到 need 件。上面已经拿了 3 件（need 一般就是 3），
	# 这里只兜「数据改了数量」的底——测的是判据，不是「怎么凑够」。
	e.stats["quest_gathered"] = need
	t.eq(e.quest_met(), true, "集齐 %d 件算完成" % need)
	var pr: Vector2i = QuestGoal.progress(e.quest_goal, e.quest_state())
	t.eq(pr, Vector2i(need, need), "进度报 %d/%d" % [need, need])

	# 没集齐就走到出口 → 未完成（和清剿同一个口子）
	var e2 := Expedition.new()
	e2.setup(db, HEROES, [], preset, 5150, "standard", {}, {})
	e2.set_location("weald", "medium", 3, "gather")
	e2.enter_map(m)
	e2.current_room = int(m["goal"])
	e2._end("complete")
	t.eq(e2.end_reason, "incomplete", "收集没做完就走 → 任务未完成")

	var e3 := Expedition.new()
	e3.setup(db, HEROES, [], preset, 5150, "standard", {}, {})
	e3.set_location("weald", "medium", 3, "gather")
	e3.enter_map(m)
	e3.stats["quest_gathered"] = need
	e3.current_room = int(m["goal"])
	e3._end("complete")
	t.eq(e3.end_reason, "complete", "集齐后走到出口 → 完成")


# ------------------------------------------------------------
# 4. 任务板：每张卡在它的区域都得能解析出目标
# ------------------------------------------------------------

static func _test_board(t: TestLib, db: DdDb) -> void:
	t.section("任务板：没有解析不了的卡")
	var c := Campaign.new()
	c.setup_from_cfg(db.campaign_cfg, TEST_PATH)
	var bad: int = 0
	var seen_gather: int = 0
	var seen_activate: int = 0
	for region in Campaign.BOARD_REGIONS:
		var rgn: String = str(region)
		for slot in Campaign.board_slots_for(rgn):
			var qt: String = str((slot as Array)[1])
			var qg: Dictionary = QuestGoal.parse(db.quests, qt, rgn, db.curio_lib.curios)
			if not bool(qg.get("supported", false)):
				bad += 1
				t.ok(false, "%s 的 %s 任务解析不出目标" % [rgn, qt])
			if qt == "gather":
				seen_gather += 1
			if qt == "activate":
				seen_activate += 1
	# 每种任务都要有图参数，否则出发时 MapGen 返回空字典
	for region2 in Campaign.BOARD_REGIONS:
		var rgn2: String = str(region2)
		for slot2 in Campaign.board_slots_for(rgn2):
			var sz: String = str((slot2 as Array)[0])
			var qt2: String = str((slot2 as Array)[1])
			if db.map_for(rgn2, sz, qt2).is_empty():
				bad += 1
				t.ok(false, "%s/%s/%s 没有地图参数" % [rgn2, sz, qt2])
	t.eq(bad, 0, "四区十六张卡：目标都能解析、地图参数都有")
	t.ok(seen_gather >= 2, "收集任务出现在 %d 个区域" % seen_gather)
	t.ok(seen_activate >= 1, "激活任务出现在 %d 个区域" % seen_activate)

	# 板上只有这四种：探索 / 清剿 / 收集 / 激活 / 首领
	var kinds: Dictionary = {}
	for region3 in Campaign.BOARD_REGIONS:
		for slot3 in c.board_for(str(region3)):
			kinds[str((slot3 as Dictionary).get("quest", ""))] = true
	t.ok(kinds.has("cleanse") and kinds.has("gather") and kinds.has("kill_boss"),
		"清剿 / 收集 / 首领 同时在板上")


static func _cleanup() -> void:
	for p in [TEST_PATH]:
		if FileAccess.file_exists(p):
			DirAccess.remove_absolute(ProjectSettings.globalize_path(p))

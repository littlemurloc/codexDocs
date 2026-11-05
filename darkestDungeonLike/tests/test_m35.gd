class_name TestM35
extends RefCounted
## M35 任务物品与「带道具激活」。
##
## `inventory_activate` 在数据里和 `activate` 是**同一个 type**——
## goal 里唯一多出来的是 `starting_items`。所以这一期的本质是：
## **给任务加一个「要不要用道具」的维度**，而不是加一种新玩法。
##
## 四件事要钉死：
##   1. 任务物品从数据里来，出发时自动带上，不是玩家买的
##   2. 目标奇物碰到但没道具 → **不计数**（这就是它和普通激活的区别）
##   3. 道具每用一次少一件，用完了就不能再推进
##   4. 任务物品不进补给：不能被商店当补给卖掉、也不会被奇物交互顺手用掉

const TEST_PATH: String = "user://test_m35_unit.json"
const HEROES: Array = ["crusader", "highwayman", "vestal", "plague_doctor"]


static func run(t: TestLib, db: DdDb) -> void:
	_test_parse(t, db)
	_test_carry(t, db)
	_test_consume(t, db)
	_test_board(t, db)
	_cleanup()


# ------------------------------------------------------------
# 1. 解析：四个区域带不同的任务物品
# ------------------------------------------------------------

static func _test_parse(t: TestLib, db: DdDb) -> void:
	t.section("解析：任务物品从 starting_items 来")
	var curios: Dictionary = db.curio_lib.curios

	var cases: Array = [
		["weald", "antivenom", "infected_corpse", "Haunted"],
		["crypts", "holy_water", "corrupted_altar", "Worship"],
		["warrens", "pickaxe", "animalistic_shrine", "Unholy"],
		["cove", "eldritch_lantern", "protective_ward", "Worship"],
	]
	var bad: int = 0
	for row in cases:
		var region: String = str(row[0])
		var want_item: String = str(row[1])
		var qg: Dictionary = QuestGoal.parse(db.quests, "inventory_activate", region, curios)
		if not bool(qg.get("supported", false)):
			bad += 1
			t.ok(false, "%s 的带道具激活解析不出目标奇物" % region)
			continue
		if QuestGoal.required_item(qg) != want_item:
			bad += 1
			t.ok(false, "%s 要的道具是 %s，实际 %s" % [region, want_item,
				QuestGoal.required_item(qg)])
		var items: Array = qg.get("items", [])
		if items.size() != 1 or int((items[0] as Dictionary).get("amount", 0)) != 3:
			bad += 1
			t.ok(false, "%s 的任务物品应该只有一种、3 件" % region)
		# 目标奇物必须真存在（M33 的标签解析）
		if not curios.has(str(qg.get("curio", ""))):
			bad += 1
			t.ok(false, "%s 解析出的奇物不在库里" % region)
	t.eq(bad, 0, "四个区域的带道具激活：道具/数量/奇物全对")

	# 普通激活没有道具，这一条是两种任务的分界线
	var act: Dictionary = QuestGoal.parse(db.quests, "activate", "crypts", curios)
	t.eq(QuestGoal.required_item(act), "", "普通激活不需要道具")
	t.eq((act.get("items", []) as Array).is_empty(), true, "普通激活不带物品")
	t.eq(str(act.get("curio", "")), "iron_maiden", "普通激活的目标是铁处女")

	# 收集任务同样没有道具（它要的是「收到的东西」，不是「带着的东西」）
	var g: Dictionary = QuestGoal.parse(db.quests, "gather", "weald", curios)
	t.eq(QuestGoal.required_item(g), "", "收集任务不用任务物品")

	t.eq(QuestGoal.supported("inventory_activate"), true, "inventory_activate 现在可结算")


# ------------------------------------------------------------
# 2. 出发时自动带上
# ------------------------------------------------------------

static func _test_carry(t: TestLib, db: DdDb) -> void:
	t.section("出发：任务物品自动进包")
	var preset: Dictionary = db.expedition_cfg.preset("standard")
	var e := Expedition.new()
	e.setup(db, HEROES, [], preset, 31, "standard", {}, {})
	e.set_location("warrens", "medium", 1, "inventory_activate")
	t.eq(int(e.quest_items.get("pickaxe", 0)), 3, "带着 3 把镐")
	t.eq(e.quest_items.size(), 1, "只带这一种物品")
	# 不进补给：补给里不该出现任务物品
	t.eq(e.supply_count("pickaxe"), 0, "任务物品不在补给里")
	t.eq(e.supply_count("holy_water") > 0, true, "默认补给包照旧（圣水还在）")

	# 普通任务不该凭空多出任务物品
	var e2 := Expedition.new()
	e2.setup(db, HEROES, [], preset, 31, "standard", {}, {})
	e2.set_location("weald", "short", 1, "explore")
	t.eq(e2.quest_items.is_empty(), true, "探索任务没有任务物品")


# ------------------------------------------------------------
# 3. 消耗与计数
# ------------------------------------------------------------

static func _test_consume(t: TestLib, db: DdDb) -> void:
	t.section("消耗：没道具不算，用一次少一件")
	var preset: Dictionary = db.expedition_cfg.preset("standard")
	var m: Dictionary = MapGen.build(db, "warrens", "medium", 1, DdRng.new(606), "inventory_activate")
	if m.is_empty():
		t.ok(false, "带道具激活的地图能生成")
		return
	var e := Expedition.new()
	e.setup(db, HEROES, [], preset, 606, "standard", {}, {})
	e.set_location("warrens", "medium", 1, "inventory_activate")
	e.enter_map(m)

	var cid: String = str(e.quest_goal.get("curio", ""))
	t.ok(not cid.is_empty(), "远征层拿到了目标奇物")
	t.eq(int(e.stats.get("quest_activated", 0)), 0, "开局 0 次")
	t.eq(e.quest_met(), false, "0 次不算完成")

	# 碰一次：+1，物品 -1
	e.resolve_curio({"curio": cid, "room": 1})
	t.eq(int(e.stats.get("quest_activated", 0)), 1, "带道具激活一次 +1")
	t.eq(int(e.quest_items.get("pickaxe", 0)), 2, "物品少一件")
	t.eq(int(e.stats.get("quest_items_used", 0)), 1, "记录了用掉 1 件")

	e.resolve_curio({"curio": cid, "room": 2})
	e.resolve_curio({"curio": cid, "room": 3})
	t.eq(int(e.stats.get("quest_activated", 0)), 3, "三次全做完")
	t.eq(int(e.quest_items.get("pickaxe", 0)), 0, "物品用光了")
	t.eq(e.quest_met(), true, "3/3 完成")

	# 第 4 个目标奇物（图上会多放吗？）：没道具就不该再计数
	e.resolve_curio({"curio": cid, "room": 4})
	t.eq(int(e.stats.get("quest_activated", 0)), 3, "没道具不再计数")
	t.eq(int(e.stats.get("quest_items_missing", 0)), 1, "记了一次「缺道具」")

	# 普通激活（无道具）在同一张图上应该「碰到就算」
	var e2 := Expedition.new()
	e2.setup(db, HEROES, [], preset, 606, "standard", {}, {})
	e2.set_location("crypts", "medium", 1, "activate")
	e2.enter_map(MapGen.build(db, "crypts", "medium", 1, DdRng.new(606), "activate"))
	e2.resolve_curio({"curio": "iron_maiden", "room": 1})
	t.eq(int(e2.stats.get("quest_activated", 0)), 1, "普通激活碰到就算")
	t.eq(e2.quest_items.is_empty(), true, "普通激活不带物品")

	# 没做完就走 → 未完成（和其他任务同一个口子）
	var e3 := Expedition.new()
	e3.setup(db, HEROES, [], preset, 606, "standard", {}, {})
	e3.set_location("warrens", "medium", 1, "inventory_activate")
	e3.enter_map(m)
	e3.current_room = int(m["goal"])
	e3._end("complete")
	t.eq(e3.end_reason, "incomplete", "一次都没激活就走 → 任务未完成")


# ------------------------------------------------------------
# 4. 任务板
# ------------------------------------------------------------

static func _test_board(t: TestLib, db: DdDb) -> void:
	t.section("任务板：六种任务都有位置")
	var seen: Dictionary = {}
	for region in Campaign.BOARD_REGIONS:
		var rgn: String = str(region)
		for slot in Campaign.board_slots_for(rgn):
			var qt: String = str((slot as Array)[1])
			seen[qt] = true
			var qg: Dictionary = QuestGoal.parse(db.quests, qt, rgn, db.curio_lib.curios)
			t.ok(bool(qg.get("supported", false)), "%s 的 %s 能解析出目标" % [rgn, qt])
	t.eq(seen.size(), 6, "六种任务类型全部出现在板上（%s）" % str(seen.keys()))
	t.eq(seen.has("inventory_activate"), true, "带道具激活至少有一个区域")

	# 带道具激活只有 medium 图参数，写在 short 上会出发失败
	for region2 in Campaign.BOARD_REGIONS:
		for slot2 in Campaign.board_slots_for(str(region2)):
			if str((slot2 as Array)[1]) == "inventory_activate":
				t.eq(str((slot2 as Array)[0]), "medium", "带道具激活只安排在 medium")
	# 每张卡的图参数都得存在，否则点了就「地图生成失败」
	t.ok(not db.map_for("warrens", "medium", "inventory_activate").is_empty(),
		"warrens/medium/inventory_activate 有地图参数")


static func _cleanup() -> void:
	for p in [TEST_PATH]:
		if FileAccess.file_exists(p):
			DirAccess.remove_absolute(ProjectSettings.globalize_path(p))

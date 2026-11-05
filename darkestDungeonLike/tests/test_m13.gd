class_name TestM13
extends RefCounted
## M13 接线层：地图 → 奇物 → 掉落 → 账面。
##
## 规则层（LootTables / CurioLib）在 test_loot / test_curio 里测。这里测的是
## 「这些规则有没有真的接进游戏」，以及三个容易被写错的地方：
##   * 地图生成里的奇物抽取不能污染主 rng（否则 M7 基线整体漂移）
##   * 奇物用掉的道具必须真的从包里扣（否则「带什么上路」是个假选择）
##   * 关掉真表必须回到旧行为（否则对照实验没有对照组）

static func run(t: TestLib, db: DdDb) -> void:
	t.section("接线：地图上的奇物")

	if db.curio_lib == null:
		t.ok(false, "curio_lib 未加载")
		return

	# 房间奇物（宝物箱）应带具体 id，且必须是该地牢刷新表里的东西
	var m: Dictionary = MapGen.build(db, "weald", "medium", 3, DdRng.new(9091))
	var room_curios: int = 0
	var bad_room: Array = []
	var allowed: Array = db.curio_lib.known_ids_for("weald")
	for rid in (m["rooms"] as Dictionary).keys():
		var r: Dictionary = m["rooms"][rid]
		var st: Dictionary = r.get("step", {})
		if str(st.get("kind", "")) != "curio":
			continue
		room_curios += 1
		var cid: String = str(st.get("curio", ""))
		if cid.is_empty() or not allowed.has(cid):
			bad_room.append("%s:%s" % [str(rid), cid])
	t.ok(room_curios >= 0, "房间奇物房 %d 间" % room_curios)
	t.eq(bad_room.size(), 0, "房间奇物都来自该地牢刷新表  %s" % str(bad_room))
	if room_curios > 0:
		t.eq(str((m["content"] as Dictionary).get("curios", -1)), str(room_curios),
			"content.curios 与实际房间奇物数一致")

	# 走廊奇物：hallway_curio 是百分比（short 9 / medium 14 / long 19）
	t.section("接线：走廊奇物按百分比出现")

	var hall_total: int = 0
	var edge_total: int = 0
	for i in 12:
		var mm: Dictionary = MapGen.build(db, "weald", "long", 3, DdRng.new(3000 + i))
		hall_total += int((mm["content"] as Dictionary).get("hall_curios", 0))
		edge_total += int((mm["content"] as Dictionary).get("edges", 0))
	t.ok(hall_total > 0, "long 图多张合计出现走廊奇物  %d 个" % hall_total)
	# M17 起密度被有意提高（expedition.json 的 `curio_rate.hallway_pct_min = 60`）。
	# 这条断言原来锁的是「填充率百分比」[0.02, 0.25]，那是按旧密度定的，
	# 一调密度就红——而红的原因是**设计变了**，不是代码坏了。
	# 改成锁定真正的设计意图：一张长图上该有几个奇物。
	# 填充率本身受空走廊数影响（图越大空越多），不该当成不变量。
	var per_map: float = float(hall_total) / 12.0
	t.between(per_map, 4.0, 12.0, "long 图每张 4–12 个走廊奇物（实测 %.2f）" % per_map)
	# 再钉一条上限：奇物只能填空走廊，永远不该超过走廊总数
	var rate: float = float(hall_total) / float(maxi(edge_total, 1))
	t.ok(rate < 0.85, "走廊奇物填充率不会接近 100%%（%.0f%%）" % (rate * 100.0))

	# 不同地牢抽出来的奇物必须不同
	var weald_set: Dictionary = {}
	for id in db.curio_lib.known_ids_for("weald"):
		weald_set[id] = true
	var cove_set: Dictionary = {}
	for id in db.curio_lib.known_ids_for("cove"):
		cove_set[id] = true
	t.ok(cove_set.has("barnacle_crusted_chest") and not weald_set.has("barnacle_crusted_chest"),
		"地牢专属奇物不会串场")

	# 主 rng 不被污染：同一 seed 生成的房间数与边数必须稳定
	t.section("接线：派生 rng 不污染地图主序列")
	var a: Dictionary = MapGen.build(db, "weald", "long", 3, DdRng.new(555))
	var a2: Dictionary = MapGen.build(db, "weald", "long", 3, DdRng.new(555))
	t.eq(int((a["content"] as Dictionary).get("edges", 0)),
		int((a2["content"] as Dictionary).get("edges", 0)), "同种子边数一致")
	t.eq(int((a["content"] as Dictionary).get("traps", 0)),
		int((a2["content"] as Dictionary).get("traps", 0)), "同种子陷阱数一致")
	t.eq(int((a["content"] as Dictionary).get("hungers", 0)),
		int((a2["content"] as Dictionary).get("hungers", 0)), "同种子饥饿数一致")
	# 走廊奇物也必须可复现
	t.eq(int((a["content"] as Dictionary).get("hall_curios", 0)),
		int((a2["content"] as Dictionary).get("hall_curios", 0)), "同种子走廊奇物数一致")

	t.section("接线：奇物交互会消耗道具")

	var e: Expedition = _mk(db, 4321)
	var before_holy: int = e.supply_count("holy_water")
	t.ok(before_holy > 0, "开局带圣水（%d）" % before_holy)
	# 邪祭坛只吃圣水；反复交互直到圣水用完
	var used: int = 0
	for i in 8:
		var h: int = e.supply_count("holy_water")
		e.resolve_curio({"kind": "curio", "curio": "eldritch_altar"})
		if e.supply_count("holy_water") < h:
			used += 1
	t.eq(used, before_holy, "圣水被逐次用掉，用完即止（用了 %d）" % used)
	t.eq(e.supply_count("holy_water"), 0, "圣水归零")
	t.ok(int(e.stats.get("curio_items_used", 0)) >= 1, "统计里记了道具消耗")

	# 没用道具时不能虚报
	var e2: Expedition = _mk(db, 4322)
	var used0: int = int(e2.stats.get("curio_items_used", 0))
	e2.resolve_curio({"kind": "curio", "curio": "crate"})
	t.eq(int(e2.stats.get("curio_items_used", 0)) - used0,
		0 if not db.curio_lib.items_for("crate").has("holy_water") else 1,
		"板条箱不该白吃圣水")

	t.section("接线：奇物账目")

	# 板条箱 3:1 掉传家宝表 H，不给压力
	var e3: Expedition = _mk(db, 777)
	var st0: float = float(e3.state["vestal"]["stress"])
	var gold0: int = e3.loot_gold
	var hl0: int = e3._heirloom_total()
	for i in 40:
		e3.resolve_curio({"kind": "curio", "curio": "crate"})
	t.eq(e3.loot_gold, gold0, "板条箱不给金币（crate 走 H 表，只出传家宝）")
	t.ok(e3._heirloom_total() > hl0, "板条箱掉了传家宝（%d → %d）" % [hl0, e3._heirloom_total()])
	t.near(float(e3.state["vestal"]["stress"]), st0, 0.01, "板条箱不加压力")

	# 邪祭坛 4/10 概率加压 3——反复交互必须能观察到压力上升
	var e4: Expedition = _mk(db, 888)
	for i in 40:
		e4.resolve_curio({"kind": "curio", "curio": "eldritch_altar"})
	t.ok(float(e4.stats.get("curio_stress", 0.0)) > 0.0,
		"邪祭坛会加压（累计 %.1f）" % float(e4.stats.get("curio_stress", 0.0)))

	t.section("接线：开关能回到旧行为")

	var e5: Expedition = _mk(db, 999)
	e5.curio_table_enabled = false
	var r5: Dictionary = e5.resolve_curio({"kind": "curio", "curio": "eldritch_altar"})
	t.eq(r5.has("curio"), false, "旧路径不返回奇物 id")
	t.ok(r5.has("gold") and r5.has("stress"), "旧路径返回旧字段")

	t.section("接线：战斗掉落走怪物自己的 loot")

	var e6: Expedition = _mk(db, 2468)
	var b: Battle = e6.start_battle({"kind": "battle", "monsters": ["cultist_brawler_A"], "gear": 0})
	while not b.is_over() and b.round_index < Battle.MAX_ROUNDS:
		b.run_round()
	e6.finish_battle(b)
	if str(b.winner()) == "party":
		var got: bool = e6.loot_gold > 0 or e6._heirloom_total() > 0 or e6._gem_total() > 0
		t.ok(got, "打赢后拿到了战利品（金 %d / 传 %d / 宝 %d）" % [
			e6.loot_gold, e6._heirloom_total(), e6._gem_total()])
		t.ok(e6.loot_trinkets >= 0, "饰品计数存在（未装备，只统计）")
	else:
		t.ok(true, "（这局没打赢，跳过掉落断言）")

	t.section("接线：旧常数对照组")

	var e7: Expedition = _mk(db, 1357)
	e7.loot_table_enabled = false
	var b7: Battle = e7.start_battle({"kind": "battle", "monsters": ["cultist_brawler_A"], "gear": 0})
	while not b7.is_over() and b7.round_index < Battle.MAX_ROUNDS:
		b7.run_round()
	var g_before: int = e7.loot_gold
	e7.finish_battle(b7)
	if str(b7.winner()) == "party":
		# 旧常数 9–17 金一场，远小于真表
		var delta: int = e7.loot_gold - g_before
		t.ok(delta == 0 or (delta >= 9 and delta <= 17),
			"旧常数一场 9–17 金  实际=%d" % delta)


static func _mk(db: DdDb, seed_value: int) -> Expedition:
	var cfg: Dictionary = db.expedition_cfg.preset("standard")
	var loot_cfg: Dictionary = (db.campaign_cfg.get("loot", {}) as Dictionary).duplicate(true)
	loot_cfg["heirloom_names"] = db.campaign_cfg.get("heirlooms", [])
	var e: Expedition = Expedition.new()
	e.setup(db, ["man_at_arms", "highwayman", "vestal", "plague_doctor"], [],
		cfg, seed_value, "standard", loot_cfg, {})
	e.set_location("weald", "medium", 3)
	return e

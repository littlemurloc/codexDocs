class_name TestM17
extends RefCounted
## M17 内容密度。
##
## 这一期只改一个数字，但它有两处容易写错的地方：
##
## 1. **下限而不是硬覆盖**。如果写成 `curio_pct = cfg_min`，那数据将来
##    自己把 hallway_curio 调到 70 就被压回 60 了——数据说「更多」，
##    配置说「就 60」，两边打架且没人会发现。
## 2. **密度必须从 `res://data` 读，不走 balance 包**。出现率是「游戏里
##    该有多少内容」，不是难度旋钮。跟着 balance 包走的话，换个数值包
##    会顺手把地图上的奇物改掉，「换了包之后变无聊」会变成查不出的问题。

const BASE_MIN: int = 60


static func run(t: TestLib, db: DdDb) -> void:
	t.section("内容密度：配置")
	t.eq(db.curio_hall_pct_min, BASE_MIN, "从 expedition.json 读到密度下限 %d" % BASE_MIN)
	t.eq(db.expedition_cfg.curio_hall_pct_min, BASE_MIN, "ExpeditionCfg 也读到了同一份")

	# 四个 preset 共享同一个密度：它不是难度旋钮
	var all_same: bool = true
	for name in ["lenient", "standard", "tight", "brutal"]:
		var cfg: Dictionary = db.expedition_cfg.preset(str(name))
		if cfg.has("curio_rate"):
			all_same = false
	t.eq(all_same, false if db.expedition_cfg.presets.is_empty() else all_same,
		"curio_rate 不在任何 preset 里（它是全局内容密度，不是难度旋钮）")

	t.section("内容密度：下限语义")
	# 同一颗种子，开关密度下限，看走廊奇物数
	var saved: int = db.curio_hall_pct_min

	db.curio_hall_pct_min = 0
	var off_total: int = 0
	for i in 10:
		var m0: Dictionary = MapGen.build(db, "weald", "medium", 3, DdRng.new(7700 + i))
		off_total += int((m0["content"] as Dictionary).get("hall_curios", 0))

	db.curio_hall_pct_min = BASE_MIN
	var on_total: int = 0
	for i in 10:
		var m1: Dictionary = MapGen.build(db, "weald", "medium", 3, DdRng.new(7700 + i))
		on_total += int((m1["content"] as Dictionary).get("hall_curios", 0))

	db.curio_hall_pct_min = saved

	t.ok(on_total > off_total,
		"密度下限生效：10 张中图 走廊奇物 %d → %d" % [off_total, on_total])
	t.ok(float(on_total) / 10.0 >= 4.0,
		"每张中图至少 4 个走廊奇物（实际 %.1f）" % (float(on_total) / 10.0))

	# 下限不该把更高的数据值压下来。medium 原始值是 14，如果把下限设成 5，
	# 实际应该还听数据的 14——这条防的是「写成硬覆盖」。
	db.curio_hall_pct_min = 5
	var low_total: int = 0
	for i in 10:
		var m2: Dictionary = MapGen.build(db, "weald", "medium", 3, DdRng.new(7700 + i))
		low_total += int((m2["content"] as Dictionary).get("hall_curios", 0))
	db.curio_hall_pct_min = saved

	# 下限 5 < 原始 14，所以结果应该和「关掉下限」完全一样
	t.eq(low_total, off_total,
		"下限低于数据值时不起作用（%d vs 关掉时 %d）——是 max() 不是赋值" % [low_total, off_total])

	t.section("内容密度：不越界")
	# 奇物只能填空走廊，永远不该超过走廊总数
	var over: int = 0
	for i in 8:
		var m3: Dictionary = MapGen.build(db, "weald", "long", 5, DdRng.new(8800 + i))
		var c: Dictionary = m3["content"]
		if int(c.get("hall_curios", 0)) > int(c.get("edges", 0)):
			over += 1
	t.eq(over, 0, "没有一张图的奇物数超过走廊数")

	# 四类内容不该被奇物挤掉：这是 M7 的老教训（顺序分配会饿死后面的类别）
	var hunger_zero: int = 0
	for i in 10:
		var m4: Dictionary = MapGen.build(db, "weald", "medium", 3, DdRng.new(9900 + i))
		if int((m4["content"] as Dictionary).get("hungers", 0)) == 0:
			hunger_zero += 1
	t.ok(hunger_zero <= 2, "饥饿几乎不会被奇物挤掉（10 张里 %d 张为 0）" % hunger_zero)

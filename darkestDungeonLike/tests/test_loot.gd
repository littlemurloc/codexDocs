class_name TestLoot
extends RefCounted
## M13 战利品抽卡树。
##
## 这组断言盯的是三件容易「看起来对、其实错」的事：
##   1. A 表只存在于 overrides 里。没合并的话所有引用 A 的抽取都是空的，
##      而且不会报错——只会静默掉得少。
##   2. 同名表有多个难度变体。用 id 当键会让深地牢的经济优势全部消失。
##   3. 一次抽取只消耗一个 rng。序列错位不会让任何断言直接失败，
##      但会让历史对照数据失去可比性。

const EPS: float = 1.0

static func run(t: TestLib, db: DdDb) -> void:
	t.section("战利品：加载与合并")

	var lt: LootTables = db.loot_tables
	if not t.ok(lt != null and lt.is_loaded(), "LootTables 已加载"):
		return

	t.ok(lt.tables.size() >= 30, "表 id 数量 ≥30  实际=%d" % lt.tables.size())

	# A 表是整棵树的根，只存在于 overrides。这一条是整个合并逻辑的守门员。
	t.ok(lt.has_table("A"), "A 表存在（来自 overrides 合并）")
	t.eq(lt.variant_count("A"), 1, "A 表只有一份变体")
	if lt.has_table("A"):
		var va: Dictionary = lt.variant_for("A")
		t.eq(str(va.get("origin", "")), "common_overrides.loot.json", "A 表来源是 common_overrides")
		t.eq(lt.weight_sum("A"), 174, "A 表权重和 = 50+38+48+28+8+2")

	t.ok(lt.has_table("S"), "S 表存在（同样只来自 overrides）")
	t.ok(lt.has_table("H"), "H 表存在")
	t.ok(lt.has_table("C"), "C 表存在")

	# 表引用完整性：任何 table 条目指向的子表都应该存在。
	var dangling: Array = lt.dangling_tables()
	t.eq(dangling.size(), 0, "没有悬空表引用（只看有权重的）  %s" % str(dangling))
	# 原表里有权重 0 的占位引用（A → J），永远不会被抽到，记录但不影响运行
	var dormant: Array = lt.dormant_dangling_tables()
	t.ok(not dormant.has("H") and not dormant.has("C"), "权重 0 的悬空引用不涉及主干表  %s" % str(dormant))

	t.section("战利品：难度变体")

	# 同 id 多份，不能当重复数据吞掉
	t.ok(lt.variant_count("C") >= 4, "C 表至少 4 份难度变体  实际=%d" % lt.variant_count("C"))
	t.ok(lt.variant_count("H") >= 13, "H 表至少 13 份（4 地牢 × 3 难度 + 1）  实际=%d" % lt.variant_count("H"))

	lt.set_context("crypts", 1)
	var h1: Dictionary = lt.variant_for("H")
	t.eq(int(h1.get("difficulty", 0)), 1, "crypts/1 选到 H 的 difficulty=1")
	t.eq(str(h1.get("dungeon", "")), "crypts", "crypts/1 选到本地牢的 H")

	lt.set_context("cove", 5)
	var h5: Dictionary = lt.variant_for("H")
	t.eq(int(h5.get("difficulty", 0)), 5, "cove/5 选到 H 的 difficulty=5")
	t.eq(str(h5.get("dungeon", "")), "cove", "cove/5 选到本地牢的 H")

	# 本地牢没有该难度档时，应退回通用表而不是空表
	lt.set_context("nowhere", 3)
	var hx: Dictionary = lt.variant_for("H")
	t.eq(str(hx.get("dungeon", "")), "", "未知地牢退回通用 H 表")

	t.section("战利品：金币档的难度梯度")

	# C 表 d1 期望 253.41，d5 期望 559.17。差 2.2 倍——这就是深地牢的价值。
	# 如果 tables 用 id 当键，这两行会变成同一个数。
	var e1: float = _mean_gold(t, lt, "C", "crypts", 1, 3000)
	var e3: float = _mean_gold(t, lt, "C", "crypts", 3, 3000)
	var e5: float = _mean_gold(t, lt, "C", "crypts", 5, 3000)
	# 容差按抽样误差给：单次 sd≈258，3000 样本 3σ≈15。写死 ±3 会因为随机性偶发失败。
	t.between(e1, 238.0, 268.0, "C 表难度 1 期望金币 ≈253")
	t.between(e3, 417.0, 446.0, "C 表难度 3 期望金币 ≈431")
	t.between(e5, 545.0, 574.0, "C 表难度 5 期望金币 ≈559")
	t.ok(e5 > e1 * 1.5, "难度 5 的金币期望超过难度 1 的 1.5 倍  实际=%.1f/%.1f" % [e5, e1])

	t.section("战利品：抽取语义")

	lt.set_context("crypts", 1)
	# 一次抽取恰好消耗一个 rng —— 对照实验的前提
	var rng: DdRng = DdRng.new(12345)
	var r0: int = rng.draw_count
	var out: Dictionary = LootTables.empty_result()
	lt.draw_into("C", rng, out)
	t.eq(rng.draw_count - r0, 1, "抽一次叶子表恰好消耗 1 个 rng")
	t.eq(int(out["draws"]), 1, "结果里 draws=1")

	# draws 语义：说抽几次就抽几次
	var rng2: DdRng = DdRng.new(999)
	var out2: Dictionary = LootTables.empty_result()
	var res: Array = [{"kind": "loot_table", "table": "C", "draws": 3}]
	lt.draw_for(res, rng2, out2)
	t.eq(int(out2["draws"]), 3, "draws=3 的分支抽 3 次")
	t.ok(int(out2["gold"]) > 0, "3 次金币抽取拿到钱")

	# draws=0 的写法在原表里存在，被写进 outcome 就说明该给东西，不能什么都不掉
	var rng3: DdRng = DdRng.new(777)
	var out3: Dictionary = LootTables.empty_result()
	lt.draw_for([{"kind": "loot_table", "table": "C", "draws": 0}], rng3, out3)
	t.eq(int(out3["draws"]), 1, "draws=0 时仍抽 1 次")

	# 递归：A 表是复合表，抽一次会展开成多张子表
	var rng4: DdRng = DdRng.new(2468)
	var out4: Dictionary = LootTables.empty_result()
	lt.draw_into("A", rng4, out4)
	t.ok(int(out4["draws"]) >= 1, "A 表抽取产生 draws")
	var got_something: bool = int(out4["gold"]) > 0 \
		or (out4["heirlooms"] as Dictionary).size() > 0 \
		or (out4["gems"] as Dictionary).size() > 0 \
		or (out4["trinkets"] as Array).size() > 0 \
		or int(out4["journal_pages"]) > 0
	t.ok(got_something, "A 表不会每次都空手（权重 174 里 nothing 为 0）")

	t.section("战利品：缺表与折算")

	var rng5: DdRng = DdRng.new(1)
	var out5: Dictionary = LootTables.empty_result()
	var ok5: bool = lt.draw_into("NO_SUCH_TABLE", rng5, out5)
	t.ok(not ok5, "缺表返回 false")
	t.ok(lt.missing_tables.has("NO_SUCH_TABLE"), "缺表被记录")

	# 宝石折算：换成一笔钱，才能在对照实验里和旧常数比
	var synthetic: Dictionary = LootTables.empty_result()
	synthetic["gold"] = 100
	synthetic["gems"] = {"ruby": 2}      # sell 1250 × 2
	var gv: int = lt.gold_value(synthetic)
	t.eq(gv, 100 + 2500, "gold_value 把宝石按 sell 价折算")

	# 传家宝不折算（是升级材料，不是钱）
	var s2: Dictionary = LootTables.empty_result()
	s2["heirlooms"] = {"bust": 5}
	t.eq(lt.gold_value(s2), 0, "传家宝不折算成金币")

	t.section("战利品：确定性")

	var a: Dictionary = _draw_seeded(lt, 424242)
	var b: Dictionary = _draw_seeded(lt, 424242)
	t.eq(int(a["gold"]), int(b["gold"]), "同种子金币相同")
	t.eq(str(a["heirlooms"]), str(b["heirlooms"]), "同种子传家宝相同")
	t.eq(int(a["draws"]), int(b["draws"]), "同种子抽取次数相同")

	var c: Dictionary = _draw_seeded(lt, 424243)
	var differs: bool = int(a["gold"]) != int(c["gold"]) \
		or str(a["heirlooms"]) != str(c["heirlooms"])
	t.ok(differs, "换种子结果会变（不是常量）")


static func _mean_gold(t: TestLib, lt: LootTables, table: String, dungeon: String, level: int, n: int) -> float:
	lt.set_context(dungeon, level)
	var rng: DdRng = DdRng.new(0xC0FFEE + level * 131)
	var acc: Dictionary = LootTables.empty_result()
	for i in n:
		lt.draw_into(table, rng, acc)
	return float(acc["gold"]) / float(n)


static func _draw_seeded(lt: LootTables, seed_value: int) -> Dictionary:
	lt.set_context("crypts", 3)
	var rng: DdRng = DdRng.new(seed_value)
	var acc: Dictionary = LootTables.empty_result()
	for i in 20:
		lt.draw_into("A", rng, acc)
	return acc

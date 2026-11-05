class_name TestCurio
extends RefCounted
## M13 奇物：定义、刷新、交互。
##
## 断言盯的是「旧实现根本分不出这些差别」的地方：
##   * 板条箱和邪祭坛必须是两个东西（一个给传家宝，一个给压力）
##   * 锁箱用钥匙是 A 表 3 抽，用铲子有一半概率砸空
##   * outcome 内部的多个 result 有的是「清单」（全给），有的是「选择题」（抽一个）
## 最后一条最容易搞错：Loot 分支的百分比列被 draws 占用了，看起来像概率其实不是。

static func run(t: TestLib, db: DdDb) -> void:
	t.section("奇物：加载")

	var cl: CurioLib = db.curio_lib
	if not t.ok(cl != null and cl.is_loaded(), "CurioLib 已加载"):
		return

	t.eq(cl.curios.size(), 60, "奇物数量 60")
	t.eq(int(cl.stats.get("curios", 0)), 60, "生成统计与运行时一致")
	t.eq(int(cl.stats.get("outcome_rows", 0)), 480, "outcome 行 480（60 × 8）")
	t.eq(int(cl.stats.get("item_interaction_rows", 0)), 46, "道具交互行 46")

	# 每种奇物都该有 8 个 outcome 槽位（Nothing/Loot/Quirk/Effect/Purge/
	# Scouting/Teleport/Disease），策划表是固定列布局，缺了说明摊平错位。
	var bad_slots: Array = []
	for id in cl.curios.keys():
		if (cl.curios[id].get("outcomes", []) as Array).size() != 8:
			bad_slots.append(str(id))
	t.eq(bad_slots.size(), 0, "每个奇物都有 8 个 outcome 槽位  %s" % str(bad_slots))

	t.section("奇物：刷新表覆盖率")

	# props 引用了 67 个 id，其中 49 个是奇物，18 个是陷阱/障碍/牢门。
	# 这是数据完整性的硬指标：一个都缺就说明设计表和刷新表对不上。
	var unknown: Array = cl.unknown_ids()
	t.eq(unknown.size(), 18, "props 里有 18 个非奇物 id（陷阱/障碍/牢门）")
	t.ok(unknown.has("spikes") and unknown.has("rubble"), "未知名里包含陷阱与障碍")
	t.ok(not unknown.has("locked_strongbox"), "已知奇物不在未知名单里")

	for dungeon in ["cove", "crypts", "warrens", "weald"]:
		var ids: Array = cl.known_ids_for(dungeon)
		t.ok(ids.size() >= 10, "%s 有 ≥10 种可刷奇物  实际=%d" % [dungeon, ids.size()])
		var missing: Array = []
		for id in ids:
			if not cl.has(str(id)):
				missing.append(id)
		# 允许陷阱类缺失，但奇物类不能缺
		var real_missing: Array = []
		for id in missing:
			if not unknown.has(id):
				real_missing.append(id)
		t.eq(real_missing.size(), 0, "%s 的奇物定义齐全  %s" % [dungeon, str(real_missing)])

	# 地牢之间必须真的不一样，否则 props 那套权重就没意义
	var cove_ids: Array = cl.known_ids_for("cove")
	t.ok(cove_ids.has("barnacle_crusted_chest"), "cove 有专属奇物 barnacle_crusted_chest")
	var crypts_ids: Array = cl.known_ids_for("crypts")
	t.ok(not crypts_ids.has("barnacle_crusted_chest"), "crypts 没有 cove 专属奇物")

	t.section("奇物：按权重刷新")

	var rng: DdRng = DdRng.new(2024)
	var ok_pick: bool = true
	var seen: Dictionary = {}
	for i in 400:
		var id: String = cl.pick("cove", CurioLib.SLOT_HALL, rng)
		if id.is_empty() or not cove_ids.has(id):
			ok_pick = false
		seen[id] = true
	t.ok(ok_pick, "cove 走廊抽到的奇物都在该地牢的刷新表里")
	t.ok(seen.size() >= 5, "多次抽取能见到多种奇物  实际=%d 种" % seen.size())

	# 没有该 slot 配置时返回空，不能瞎给
	t.eq(cl.pick("cove", "no_such_slot", DdRng.new(1)), "", "未配置的 slot 返回空")

	t.section("奇物：板条箱 vs 邪祭坛")

	# 这两个奇物在旧实现里是同一枚硬币。现在必须一个给传家宝、一个给压力。
	var crate: Dictionary = cl.get_curio("crate")
	t.eq(str(crate.get("tier", "")), "Good", "crate 是 Good 档")
	var crate_live: Array = _live_outcomes(crate)
	t.eq(crate_live.size(), 2, "crate 有两个有效分支（空 / 掉落）")
	t.ok(_outcome_of(crate, "loot") >= 0, "crate 有 loot 分支")
	t.ok(_outcome_of(crate, "effect") < 0, "crate 没有 effect 分支（不会加压）")

	var altar: Dictionary = cl.get_curio("eldritch_altar")
	var altar_eff: Dictionary = _outcome_dict(altar, "effect")
	t.ok(not altar_eff.is_empty(), "eldritch_altar 有 effect 分支")
	if not altar_eff.is_empty():
		t.eq(int(altar_eff.get("weight", 0)), 4, "eldritch_altar 的 effect 权重 4")
		var r0: Dictionary = (altar_eff.get("results", []) as Array)[0]
		t.eq(str(r0.get("kind", "")), "stress", "eldritch_altar 的 effect 是加压")
		t.eq(int(r0.get("value", 0)), 3, "加压数值 3")

	t.section("奇物：道具交互")

	var items: Array = cl.items_for("locked_strongbox")
	t.ok(items.has("skeleton_key"), "锁箱能用骷髅钥匙")
	t.ok(items.has("shovel"), "锁箱能用铲子")

	# 钥匙必然成功：A 表 3 抽，且只有这一种结果
	var rk: DdRng = DdRng.new(777)
	var rk_out: Dictionary = cl.resolve("locked_strongbox", "skeleton_key", rk)
	t.eq(str(rk_out.get("item", "")), "skeleton_key", "记录了使用的道具")
	t.eq(str(rk_out.get("outcome", "")), "loot", "钥匙交互结果是 loot")
	var res_k: Array = rk_out.get("results", [])
	t.eq(res_k.size(), 1, "钥匙只有一个结果")
	if res_k.size() == 1:
		t.eq(str(res_k[0].get("table", "")), "A", "钥匙抽 A 表")
		t.eq(int(res_k[0].get("draws", 0)), 3, "钥匙抽 3 次")

	# 铲子是 50/50：砸空或抽 A 表 2 次。必须两种都能出现。
	var rng_sh: DdRng = DdRng.new(31337)
	var key_count: int = 0
	var nothing_count: int = 0
	for i in 400:
		var o: Dictionary = cl.resolve("locked_strongbox", "shovel", rng_sh)
		var rs: Array = o.get("results", [])
		if rs.is_empty():
			continue
		var tid: String = str((rs[0] as Dictionary).get("table", ""))
		if tid == "A":
			key_count += 1
		elif tid == "Nothing":
			nothing_count += 1
	t.ok(key_count > 100 and nothing_count > 100,
		"铲子交互两种结果都会出现  砸开=%d 砸空=%d" % [key_count, nothing_count])

	# 该道具对这个奇物没用时，不能虚报消耗
	var rbad: DdRng = DdRng.new(5)
	var bad: Dictionary = cl.resolve("crate", "skeleton_key", rbad)
	t.eq(str(bad.get("item", "")), "", "无效道具不会记为已使用")

	t.section("奇物：outcome 内部的并列 vs 互斥")

	# goal_strongbox 的 loot 分支：B 抽 3 次 + T 抽 1 次，是清单不是选择题
	var goal: Dictionary = cl.get_curio("goal_strongbox")
	var gl: Dictionary = _outcome_dict(goal, "loot")
	t.ok(not gl.is_empty(), "goal_strongbox 有 loot 分支")
	var g_res: Array = gl.get("results", [])
	t.eq(g_res.size(), 2, "goal_strongbox loot 有两个并列结果")

	var rgo: DdRng = DdRng.new(88)
	var go: Dictionary = cl.resolve("goal_strongbox", "", rgo)
	t.eq(str(go.get("outcome", "")), "loot", "goal_strongbox 必掉（loot 权重 1，其余 0）")
	t.eq((go.get("results", []) as Array).size(), 2, "并列结果一次全给（不是二选一）")

	# 反过来：锁箱的 effect 分支是 Blight 1 / Bleed 1 各 50%，必须互斥
	var lk: Dictionary = cl.get_curio("locked_strongbox")
	var le: Dictionary = _outcome_dict(lk, "effect")
	var l_res: Array = le.get("results", [])
	t.eq(l_res.size(), 2, "锁箱 effect 有两个备选")
	# 直接测 _pick_results 的互斥性：多次抽取每次只返回一个
	var rng_e: DdRng = DdRng.new(606)
	var blight_n: int = 0
	var bleed_n: int = 0
	var multi: int = 0
	for i in 400:
		var got: Array = cl._pick_results(l_res, rng_e)
		if got.size() > 1:
			multi += 1
		elif str((got[0] as Dictionary).get("raw", "")) == "Blight 1":
			blight_n += 1
		else:
			bleed_n += 1
	t.eq(multi, 0, "互斥分支每次只给一个结果")
	t.ok(blight_n > 120 and bleed_n > 120,
		"两个结果都会出现  Blight=%d Bleed=%d" % [blight_n, bleed_n])

	t.section("奇物：scripted 效果不猜数值")

	# Suit of Armor Shield 这种表里只有名字没有数值，必须标 unsupported 而不是编个数字
	var hf: Dictionary = cl.get_curio("holy_fountain")
	var hf_eff: Dictionary = _outcome_dict(hf, "effect")
	var hf_res: Array = hf_eff.get("results", [])
	t.ok(hf_res.size() > 0, "holy_fountain 有 effect 结果")
	if hf_res.size() > 0:
		t.eq(str((hf_res[0] as Dictionary).get("kind", "")), "scripted", "HolyFountainEffects 标为 scripted")

	var armor: Dictionary = cl.get_curio("suit_of_armor")
	var armor_eff: Dictionary = _outcome_dict(armor, "effect")
	var armor_res: Array = armor_eff.get("results", [])
	var armor_scripted: bool = false
	for r in armor_res:
		if str((r as Dictionary).get("kind", "")) == "scripted":
			armor_scripted = true
	t.ok(armor_scripted, "Suit of Armor Shield 标为 scripted")

	# resolve 要把 scripted 原样带出来，供上层计数
	var rng_a: DdRng = DdRng.new(1234)
	var found_unsupported: bool = false
	for i in 60:
		var o: Dictionary = cl.resolve("suit_of_armor", "", rng_a)
		if (o.get("unsupported", []) as Array).size() > 0:
			found_unsupported = true
			break
	t.ok(found_unsupported, "resolve 会带出 unsupported 列表")

	t.section("奇物：统计口径")

	var counts: Dictionary = cl.outcome_type_counts()
	t.eq(int(counts.get("loot", 0)), 41, "有权重的 loot 分支 41")
	t.eq(int(counts.get("effect", 0)), 38, "有权重的 effect 分支 38")
	t.eq(int(counts.get("nothing", 0)), 29, "有权重的 nothing 分支 29")
	t.eq(int(counts.get("quirk", 0)), 15, "有权重的 quirk 分支 15")

	t.section("奇物：确定性")

	var a1: Dictionary = _resolve_n(cl, "locked_strongbox", "", 4242)
	var a2: Dictionary = _resolve_n(cl, "locked_strongbox", "", 4242)
	t.eq(str(a1.get("outcome", "")), str(a2.get("outcome", "")), "同种子 outcome 相同")
	t.eq(str(a1.get("results", [])), str(a2.get("results", [])), "同种子结果相同")


# —— 小工具 ——

static func _live_outcomes(c: Dictionary) -> Array:
	var out: Array = []
	for o in (c.get("outcomes", []) as Array):
		if int((o as Dictionary).get("weight", 0)) > 0:
			out.append(o)
	return out


static func _outcome_of(c: Dictionary, type_name: String) -> int:
	var arr: Array = c.get("outcomes", [])
	for i in arr.size():
		var o: Dictionary = arr[i]
		if str(o.get("type", "")) == type_name and int(o.get("weight", 0)) > 0:
			return i
	return -1


static func _outcome_dict(c: Dictionary, type_name: String) -> Dictionary:
	var idx: int = _outcome_of(c, type_name)
	if idx < 0:
		return {}
	return (c.get("outcomes", []) as Array)[idx]


static func _resolve_n(cl: CurioLib, id: String, item: String, seed_value: int) -> Dictionary:
	var rng: DdRng = DdRng.new(seed_value)
	var out: Dictionary = {}
	for i in 5:
		out = cl.resolve(id, item, rng)
	return out

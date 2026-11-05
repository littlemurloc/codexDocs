class_name TestTrinket
extends RefCounted
## M15 饰品。
##
## 这一期有三处「看着对、其实什么都没连上」的地方，全部要钉住：
##
## 1. **抽卡表只写稀有度**（`{"type":"trinket","data":{"rarity":"very_common"}}`），
##    不写 id。不解析就等于「掉了件不知道是什么的东西」——M13/M14 都在
##    这一层留过坑，所以断言既要查 id 非空，也要查 id 真在库里。
## 2. **掉落解析必须用派生 rng**。主序列的抽取次数决定后面所有金币，
##    多抽一次 M13 量到的全部掉落基线就作废。这里直接对比「开表前后」
##    的金币序列，证明解析饰品没有挪动主序列。
## 3. **装备与仓库是两个容器**。合成一个列表后「仓库满了但人身上还能戴」
##    就表达不出来，而且 limit 会退化成只看一半。

static func run(t: TestLib, db: DdDb) -> void:
	var tl: TrinketLib = db.trinket_lib
	t.section("饰品：数据装载")
	if tl == null or not tl.is_loaded():
		t.ok(false, "trinket_lib 未加载")
		return

	var st: Dictionary = tl.stats
	t.eq(int(st["trinkets"]), 490, "饰品 490 件")
	t.eq(int(st["buff_refs"]), 1964, "buff 引用 1964 条")
	t.eq(int(st["distinct_buffs"]), 943, "去重后 943 个不同 buff")
	t.eq(int(st["missing_buffs"]), 0, "没有指向不存在 buff 的引用")

	# 数据里出现了代码不认识的 rule_type，必须报出来而不是静默当无效
	var unk: Array = tl.unknown_rules()
	t.eq(unk.size(), 0, "没有未知 rule_type  %s" % str(unk))

	# 覆盖率：可判 + 有承载 才算真的做完了
	t.eq(int(st["landable"]), 1625, "可落地 1625 条")
	var parts: int = int(st["landable"]) + int(st["rule_blocked"]) \
		+ int(st["no_channel"]) + int(st["both_blocked"])
	t.eq(parts, 1964, "四类相加等于全部引用（不重复不遗漏）")
	t.ok(float(parts) == float(st["buff_refs"]), "引用总数自洽")

	t.section("饰品：稀有度与掉落池")

	# kickstarter 是众筹支持者专享的 294 件，任何抽卡表都没引用它们。
	# 它们漏进随机池就会变成「普通宝箱开出赞助者礼品」。
	t.eq(tl.pool_for_rarity("kickstarter").size(), 0, "kickstarter 不进任何池")
	t.eq(int((st["by_rarity"] as Dictionary).get("kickstarter", 0)), 294,
		"库里确实有 294 件 kickstarter")

	var drop: Array = tl.droppable_rarities()
	t.ok(drop.size() >= 10, "可掉落稀有度 %d 档" % drop.size())
	var total_drop: int = 0
	for r in drop:
		total_drop += tl.pool_for_rarity(str(r)).size()
	t.eq(total_drop, 196, "可掉落合计 196 件")

	t.eq(tl.pool_for_rarity("common").size(), 44, "common 池 44 件")
	t.eq(tl.pool_for_rarity("very_common").size(), 16, "very_common 池 16 件")

	# 抽选确定性：同种子同一件。不然 bench 的对照根本没法复现。
	var a1: String = tl.pick_for_rarity("rare", DdRng.new(4242))
	var a2: String = tl.pick_for_rarity("rare", DdRng.new(4242))
	t.eq(a1, a2, "同种子抽到同一件（%s）" % a1)
	t.eq(tl.rarity_of(a1), "rare", "抽出来的确实是 rare")

	# exclude 要真的排除，否则 limit=1 的件会重复掉落
	var excluded: Array = tl.pool_for_rarity("very_common").duplicate()
	excluded.remove_at(0)
	var pick_x: String = tl.pick_for_rarity("very_common", DdRng.new(77), excluded)
	t.ok(not pick_x.is_empty(), "exclude 选项下仍能抽到（%s）" % pick_x)

	t.section("饰品：字段语义")

	# 职业限制：空数组 = 谁都能戴；非空只限列出的职业。
	# 79 件有职业限制，配错会变成「给了但穿不上」。
	t.eq(tl.classes_of("swift_cloak").size(), 0, "swift_cloak 谁都能戴")
	t.eq(tl.fits_class("swift_cloak", "vestal"), true, "通用件对 vestal 可用")
	t.eq(tl.fits_class("padlock_1", "vestal"), false,
		"padlock_1 限 abomination（实际 %s）" % str(tl.classes_of("padlock_1")))
	t.eq(tl.fits_class("padlock_1", "abomination"), true, "同一件对 abomination 可用")

	# limit：1 = 唯一，0 = 不限。490 件里 330 件唯一、159 件不限、1 件限 3。
	var limits: Dictionary = {}
	for id in tl.order:
		var l: int = tl.limit_of(str(id))
		limits[l] = int(limits.get(l, 0)) + 1
	t.eq(int(limits.get(1, 0)), 330, "330 件唯一")
	t.eq(int(limits.get(0, 0)), 159, "159 件不限")
	t.eq(int(limits.get(3, 0)), 1, "1 件限 3")

	t.section("饰品：界面名字")

	# 490 件饰品**没有任何显示名**：trinkets.json 只有 id/rarity/price/limit/buffs，
	# _raw 里也没有 localization。所以名字是按 id 词根拼出来的，
	# 覆盖不了的会回退成英文 id。
	#
	# 只要求「可掉落的 196 件」100% 覆盖——玩家只会碰到这些。
	# 294 件 kickstarter 永远不出现在游戏里，为它们造译名是浪费。
	var drop_ids: Array = []
	for r in drop:
		drop_ids.append_array(tl.pool_for_rarity(str(r)))
	var cov: float = DdNames.trinket_name_coverage(drop_ids)
	t.near(cov, 1.0, 0.0001, "可掉落件中文名覆盖 100%%（%.1f%%）" % (cov * 100.0))
	t.eq(DdNames.trinket_name("swift_cloak"), "迅捷斗篷", "词根拼装正确")
	t.eq(DdNames.trinket_name("ancestors_pen"), "先祖笔", "虚词 of/the 被跳过")
	t.eq(DdNames.trinket_name("padlock_1"), "挂锁", "数字后缀不参与译名")
	t.eq(DdNames.trinket_name("no_such_trinket_xyz"), "No Such Trinket Xyz",
		"认不出的 id 整件回退英文（不出现半中半英）")

	t.section("饰品：掉落解析不改主序列")

	# 这是本期的硬约束：解析「掉的是哪一件」如果直接用主 rng，
	# 同一次抽卡的金币就会整体漂移，M13 的全部对照作废。
	var lt: LootTables = db.loot_tables
	var r1: DdRng = DdRng.new(31337)
	var out1: Dictionary = LootTables.empty_result()
	for i in 30:
		lt.draw_into("A", r1, out1, 0)
	var gold_with: int = int(out1["gold"])
	var draws_with: int = int(r1.draw_count)

	# 关掉饰品解析（模拟「还没做这一期」）再跑一遍同样的 30 次
	var saved: TrinketLib = lt.trinket_lib
	lt.trinket_lib = null
	var r2: DdRng = DdRng.new(31337)
	var out2: Dictionary = LootTables.empty_result()
	for i in 30:
		lt.draw_into("A", r2, out2, 0)
	lt.trinket_lib = saved
	t.eq(int(out2["gold"]), gold_with, "金币完全一致（%d）" % gold_with)
	t.eq(int(r2.draw_count), draws_with, "主序列消耗次数一致（%d）" % draws_with)
	t.eq((out2["trinket_ids"] as Array).size(), 0, "关掉时不产出具体 id")
	t.ok((out1["trinkets"] as Array).size() > 0, "A 表确实会掉饰品（%d 件）"
		% (out1["trinkets"] as Array).size())

	# 开着的时候，每个 id 都必须真在库里
	var bad_ids: Array = []
	for id in (out1["trinket_ids"] as Array):
		if not tl.has(str(id)):
			bad_ids.append(id)
	t.eq(bad_ids.size(), 0, "掉出来的 id 全部在库里  %s" % str(bad_ids))

	t.section("饰品：仓库与装备")

	var camp: Campaign = Campaign.new()
	camp.setup_from_cfg(db.campaign_cfg, "user://t15_camp.json")
	camp.trinket_lib = tl
	camp.new_game()

	t.eq(camp.store_slots, 16, "仓库 16 格（inventory.json）")
	t.eq(camp.equip_slots, 2, "每人 2 格（inventory.json）")
	t.eq(camp.trinket_store.size(), 0, "新档仓库是空的")

	# 入仓库
	t.eq(camp.add_trinket("swift_cloak"), "", "入仓库成功")
	t.eq(camp.trinket_store.size(), 1, "仓库 1 件")

	# 装备：从仓库移到人身上
	t.eq(camp.equip_trinket("vestal", "swift_cloak"), "", "装备成功")
	t.eq(camp.trinket_store.size(), 0, "装备后仓库少一件")
	t.eq(camp.equipped_of("vestal"), ["swift_cloak"], "vestal 身上有它")
	t.eq(camp.trinket_count("swift_cloak"), 1, "总量仍是 1（仓库 + 装备）")

	# 装备中的件不占仓库格：再塞满仓库也不该挤掉它
	for i in camp.store_slots:
		camp.add_trinket("speed_stone")
	t.eq(camp.store_free(), 0, "仓库塞满")
	t.eq(camp.equipped_of("vestal").size(), 1, "装备不受仓库容量影响")

	# 仓库满时卸不下来，否则这件会凭空消失
	t.eq(camp.unequip_trinket("vestal", 0), "store_full", "仓库满时卸不下来")
	t.eq(camp.equipped_of("vestal").size(), 1, "卸失败后仍在身上")

	# 腾一格就能卸
	camp.trinket_store.pop_back()
	t.eq(camp.unequip_trinket("vestal", 0), "", "腾出空格后能卸")
	t.eq(camp.equipped_of("vestal").size(), 0, "身上空了")
	t.eq(camp.trinket_store.has("swift_cloak"), true, "回到仓库")

	t.section("饰品：同名上限与职业限制")

	var camp2: Campaign = Campaign.new()
	camp2.setup_from_cfg(db.campaign_cfg, "user://t15_camp2.json")
	camp2.trinket_lib = tl
	camp2.new_game()

	# limit=1：第二件必须被拒，且计入拒绝原因。
	# 注意 swift_cloak 的 limit 是 0（不限）——「一件稀有件就该唯一」是错的假设，
	# 数据里 330 件唯一、159 件不限，两者都大量存在。
	t.eq(tl.limit_of("crow_wingfeather"), 1, "crow_wingfeather 是唯一件")
	t.eq(tl.limit_of("swift_cloak"), 0, "swift_cloak 不限量")
	t.eq(camp2.add_trinket("crow_wingfeather"), "", "第一件进得来")
	t.eq(camp2.add_trinket("crow_wingfeather"), "limit", "第二件被 limit 挡住")
	t.eq(int(camp2.trinket_refused.get("limit", 0)), 1, "拒绝被记了一笔（不是静默丢弃）")

	# limit=0 的件可以重复拿
	var dup_ok: int = 0
	for i in 3:
		if camp2.add_trinket("speed_stone") == "":
			dup_ok += 1
	t.eq(dup_ok, 3, "limit=0 的件可以拿三件")

	# 职业限制：能拿进仓库，但穿不上
	# 注意：`abomination` 不在开局名册里（campaign.json 只有四个职业），
	# 所以拿它当测试对象会得到 "refused" 而不是 class_mismatch——
	# 那是「名册里没这个人」，不是「职业不符」。两者要分开测。
	camp2.add_trinket("haste_chalice")
	t.eq(camp2.equip_trinket("highwayman", "haste_chalice"), "class_mismatch",
		"haste_chalice 限 vestal，highwayman 穿不上")
	t.eq(camp2.equip_trinket("vestal", "haste_chalice"), "", "对 vestal 可以穿")

	# 每人 2 格
	var camp3: Campaign = Campaign.new()
	camp3.setup_from_cfg(db.campaign_cfg, "user://t15_camp3.json")
	camp3.trinket_lib = tl
	camp3.new_game()
	camp3.add_trinket("swift_cloak")
	camp3.add_trinket("speed_stone")
	camp3.add_trinket("dodge_stone")
	t.eq(camp3.equip_trinket("vestal", "swift_cloak"), "", "第 1 件上身")
	t.eq(camp3.equip_trinket("vestal", "speed_stone"), "", "第 2 件上身")
	t.eq(camp3.equip_trinket("vestal", "dodge_stone"), "slots_full", "第 3 件被拒")

	t.section("饰品：战斗里真的生效")

	# 速度 +2 的件：4 → 6
	var e1: Expedition = _mk(db, 9001)
	e1.set_hero_trinkets({"vestal": ["swift_cloak"]})
	var b1: Battle = e1.start_battle({"kind": "battle", "monsters": ["cultist_brawler_A"], "gear": 0})
	var v1: Combatant = _unit(b1, "vestal")
	var e0: Expedition = _mk(db, 9001)
	var b0: Battle = e0.start_battle({"kind": "battle", "monsters": ["cultist_brawler_A"], "gear": 0})
	var v0: Combatant = _unit(b0, "vestal")
	if v1 != null and v0 != null:
		t.near(v1.speed() - v0.speed(), 2.0, 0.0001,
			"swift_cloak 让速度 +2（%.2f → %.2f）" % [v0.speed(), v1.speed()])
		t.eq(v1.trinket_ids, ["swift_cloak"], "战斗单位记得自己戴了什么")
		t.ok(v1.active_trinket_count() > 0, "有生效中的饰品 buff（%d 条）"
			% v1.active_trinket_count())
		t.eq(v0.active_trinket_count(), 0, "空手时没有饰品 buff")
	else:
		t.ok(false, "战斗里找不到 vestal")

	# 伤害倍率的件：1.00 → 1.10
	var e3: Expedition = _mk(db, 9002)
	e3.set_hero_trinkets({"vestal": ["damage_stone"]})
	var b3: Battle = e3.start_battle({"kind": "battle", "monsters": ["cultist_brawler_A"], "gear": 0})
	var v3: Combatant = _unit(b3, "vestal")
	if v3 != null:
		t.near(v3.damage_mult("low"), 1.1, 0.0001, "damage_stone 让伤害倍率 1.10")
	else:
		t.ok(false, "战斗里找不到 vestal")

	# 关掉开关：同一个人、同一件，不该有任何变化
	var e4: Expedition = _mk(db, 9003)
	e4.trinket_enabled = false
	e4.set_hero_trinkets({"vestal": ["swift_cloak"]})
	var b4: Battle = e4.start_battle({"kind": "battle", "monsters": ["cultist_brawler_A"], "gear": 0})
	var v4: Combatant = _unit(b4, "vestal")
	var e5: Expedition = _mk(db, 9003)
	var b5: Battle = e5.start_battle({"kind": "battle", "monsters": ["cultist_brawler_A"], "gear": 0})
	var v5: Combatant = _unit(b5, "vestal")
	if v4 != null and v5 != null:
		t.eq(v4.trinket_ids.size(), 0, "关掉后不挂饰品")
		t.near(v4.speed(), v5.speed(), 0.0001, "关掉后速度与空手一致")

	# 跨战斗不丢：M14 的坑（capture_party_state 整份替换 state）
	var e6: Expedition = _mk(db, 9004)
	e6.set_hero_trinkets({"vestal": ["swift_cloak"]})
	var b6: Battle = e6.start_battle({"kind": "battle", "monsters": ["cultist_brawler_A"], "gear": 0})
	if b6 != null:
		e6.finish_battle(b6)
		var st6: Dictionary = e6.state.get("vestal", {})
		t.eq((st6.get("trinkets", []) as Array), ["swift_cloak"],
			"打完一场后装备仍在 state 里（不被快照覆盖）")

	t.section("饰品：存档往返")

	var camp4: Campaign = Campaign.new()
	camp4.setup_from_cfg(db.campaign_cfg, "user://t15_save.json")
	camp4.trinket_lib = tl
	camp4.new_game()
	camp4.add_trinket("swift_cloak")
	camp4.add_trinket("speed_stone")
	camp4.equip_trinket("vestal", "swift_cloak")
	camp4.save()

	var camp5: Campaign = Campaign.new()
	camp5.setup_from_cfg(db.campaign_cfg, "user://t15_save.json")
	camp5.trinket_lib = tl
	camp5.load_or_new()
	t.eq(camp5.equipped_of("vestal"), ["swift_cloak"], "读档后装备还在")
	t.eq(camp5.trinket_store, ["speed_stone"], "读档后仓库还在")
	t.eq(camp5.trinket_count("swift_cloak"), 1, "总量没错（没有复制出一件）")

	# 旧档缺 trinket_store / equipped 字段：读成空，不报错也不凭空给东西
	var legacy: Dictionary = camp5.to_dict()
	(legacy as Dictionary).erase("trinket_store")
	for hid in (legacy["roster"] as Dictionary).keys():
		((legacy["roster"] as Dictionary)[hid] as Dictionary).erase("equipped")
	var camp6: Campaign = Campaign.new()
	camp6.setup_from_cfg(db.campaign_cfg, "user://t15_save2.json")
	camp6.trinket_lib = tl
	camp6.from_dict(legacy)
	t.eq(camp6.trinket_store.size(), 0, "旧档缺字段时读成空仓库")
	t.eq(camp6.equipped_of("vestal").size(), 0, "旧档缺字段时身上为空")

	t.section("饰品：掉落进仓库")

	# 走一遍真正的入账路径：掉落 → settle → 仓库
	var e7: Expedition = _mk(db, 9005)
	# 真实状态里 loot_trinkets 是「掉了几个叶子」，loot_trinket_ids 是
	# 「其中解析出 id 的那几个」。两件同名唯一件 = 叶子 2、id 2。
	e7.loot_trinkets = 2
	e7.loot_trinket_ids = ["crow_wingfeather", "crow_wingfeather"]
	var camp7: Campaign = Campaign.new()
	camp7.setup_from_cfg(db.campaign_cfg, "user://t15_camp7.json")
	camp7.trinket_lib = tl
	camp7.new_game()
	var res: Dictionary = camp7.settle(e7)
	t.eq(res["trinket_ids"], ["crow_wingfeather"], "limit=1 只放进去一件")
	t.eq(int(res["trinkets"]), 1, "结算屏报 1 件")
	t.eq(int(res["trinkets_dropped"]), 1, "另一件记成被丢弃（不静默消失）")
	t.eq(camp7.trinket_store.has("crow_wingfeather"), true, "东西真进了仓库")


static func _unit(b: Battle, hid: String) -> Combatant:
	if b == null:
		return null
	for u in b.party:
		if u.def_id == hid:
			return u
	return null


static func _mk(db: DdDb, seed_value: int) -> Expedition:
	var cfg: Dictionary = db.expedition_cfg.preset("standard")
	var e: Expedition = Expedition.new()
	e.setup(db, ["vestal", "crusader", "highwayman", "plague_doctor"], [],
		cfg, seed_value, "standard", {}, {})
	e.set_location("weald", "medium", 3)
	return e

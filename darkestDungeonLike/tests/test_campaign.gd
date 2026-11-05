class_name TestCampaign
extends RefCounted
## 元层回归：账、名册、存档。
##
## 这一层的错误不会崩，只会让数字慢慢失真——多扣一次钱、升级没写进档、
## 阵亡的人还能出征。所以每条都要能一眼看出对错。

const TEST_PATH: String = "user://test_campaign_unit.json"


static func run(t: TestLib, db: DdDb) -> void:
	_cleanup()
	var c := Campaign.new()
	c.setup_from_cfg(db.campaign_cfg, TEST_PATH)

	t.section("新档")
	# 名册人数从配置读，不写死。M18 把名册扩到 5 人（出战仍是 4 人），
	# 写死的 4 会让这条红一次——而红的理由是设计变了，不是代码坏了。
	var roster_n: int = (db.campaign_cfg["roster_start"]["heroes"] as Array).size()
	t.eq(c.roster.size(), roster_n, "开局 %d 名英雄（按配置）" % roster_n)
	t.eq(c.gold, 0, "开局无金币")
	t.eq(c.heirloom_total(), 0, "开局无传家宝")
	t.eq(c.alive_ids().size(), roster_n, "全员在册")
	# 能上路的只有 4 个：战斗层只认 rank 0–3
	t.eq(c.default_party().size(), Campaign.PARTY_MAX, "默认出战 %d 人" % Campaign.PARTY_MAX)
	t.eq(c.gear_of("man_at_arms"), 0, "装备 0 阶")

	t.section("收支")
	# 金额从配置读，不写死：M13 按真表产出把升级价重标定过一次
	# （40→1000），写死数字的测试会跟着配置一起碎。
	var cost0: Dictionary = c.upgrade_cost("man_at_arms")
	var seed_gold: int = int(cost0.get("gold", 0)) + 1000
	c.add_loot(seed_gold, {"bust": 9})
	t.eq(c.gold, seed_gold, "金币入账")
	t.eq(int(c.heirlooms["bust"]), 9, "传家宝入账")
	t.eq(c.can_afford({"gold": 100, "heirlooms": {"bust": 3}}), true, "刚好够")
	t.eq(c.can_afford({"gold": seed_gold + 1, "heirlooms": {}}), false, "差一金币就不够")
	t.eq(c.pay({"gold": seed_gold + 1, "heirlooms": {}}), false, "付不起时不扣款")
	t.eq(c.gold, seed_gold, "失败的支付不改变余额")

	t.section("升级")
	# 装备阶卡在决心等级上（M25）：新兵 1 级只能穿 1 阶。
	# 这是原版的规则——「第 N 级解锁第 N 阶武器」——不是我们加的额外限制。
	t.eq(c.upgrade_cost("man_at_arms").is_empty(), true, "1 级升不了 2 阶")
	t.eq(c.gear_gate_reason("man_at_arms").is_empty(), false, "并且给得出原因")
	# 练到 3 级之后有 2 阶的准入
	(c.roster["man_at_arms"] as Dictionary)["resolve"] = 3
	t.eq(c.gear_cap("man_at_arms"), 2, "3 级能穿到 3 阶（index 2）")
	t.eq(c.upgrade_cost("man_at_arms").is_empty(), false, "0 阶有价格")
	t.eq(c.can_upgrade("man_at_arms"), true, "首阶可升")
	var before: int = c.gold
	t.eq(c.upgrade("man_at_arms"), true, "升级成功")
	t.eq(c.gear_of("man_at_arms"), 1, "装备 +1")
	t.eq(c.skill_of("man_at_arms"), 1, "技能同步 +1")
	t.ok(c.gold < before, "扣了金币（%d → %d）" % [before, c.gold])

	t.section("存档往返")
	t.eq(c.save(), true, "写档成功")
	var c2 := Campaign.new()
	c2.setup_from_cfg(db.campaign_cfg, TEST_PATH)
	t.eq(c2.load_or_new(), true, "读档成功")
	t.eq(c2.gold, c.gold, "金币一致")
	t.eq(c2.heirloom_total(), c.heirloom_total(), "传家宝一致")
	t.eq(c2.gear_of("man_at_arms"), 1, "装备阶一致")
	t.eq(c2.expeditions, c.expeditions, "远征计数一致")

	t.section("阵亡与招募")
	c2.roster["highwayman"]["alive"] = false
	t.eq(c2.alive_ids().has("highwayman"), false, "阵亡者不在出发名单")
	t.eq(c2.alive_ids().size(), roster_n - 1, "只剩 %d 人" % (roster_n - 1))
	t.eq(c2.can_upgrade("highwayman"), false, "阵亡者不能升级")
	var rc: Dictionary = c2.recruit_cost()
	c2.add_loot(int(rc.get("gold", 0)), (rc.get("heirlooms", {}) as Dictionary).duplicate())
	t.eq(c2.can_recruit("highwayman"), true, "资源够时可招募")
	t.eq(c2.recruit("highwayman"), true, "招募成功")
	t.eq(c2.alive_ids().size(), roster_n, "归队")

	t.section("封顶")
	# 给得足够多，好让这条只测「封顶」而不受价格影响
	for i in range(6):
		c2.add_loot(20000, {"bust": 99, "portrait": 99, "crest": 99, "deed": 99})
	# 满级才谈得上封顶：3 级只能穿到 2 阶，会卡在等级而不是 4 阶上限上
	(c2.roster["man_at_arms"] as Dictionary)["resolve"] = Campaign.MAX_RESOLVE
	var guard: int = 0
	while c2.gear_of("man_at_arms") < Campaign.MAX_GEAR and guard < 10:
		c2.upgrade("man_at_arms")
		guard += 1
	t.eq(c2.gear_of("man_at_arms"), Campaign.MAX_GEAR, "封顶在 4 阶")
	t.eq(c2.upgrade_cost("man_at_arms").is_empty(), true, "满阶返回空价格")
	t.eq(c2.can_upgrade("man_at_arms"), false, "满阶不可再升")

	t.section("破产保护")
	var c3 := Campaign.new()
	c3.setup_from_cfg(db.campaign_cfg, TEST_PATH)
	for hid in c3.hero_ids():
		c3.roster[hid]["alive"] = false
	c3.gold = 0
	for k in c3.heirlooms.keys():
		c3.heirlooms[k] = 0
	t.eq(c3.alive_ids().size(), 0, "全员阵亡")
	t.eq(c3.free_recruits, 0, "初始没有免费额度")
	c3.free_recruits = c3.hero_ids().size()
	t.eq(c3.effective_recruit_cost("man_at_arms").is_empty(), true, "有额度时免费")
	var recruited: int = 0
	for hid in c3.hero_ids():
		if c3.recruit(hid):
			recruited += 1
	t.eq(recruited, roster_n, "额度够时能一次补满")
	t.eq(c3.alive_ids().size(), roster_n, "补满后可以正常出征")
	t.eq(c3.free_recruits, 0, "额度用完即止")
	t.eq(c3.gold, 0, "免费征召不扣钱")

	# 成绩口径：图模式下 step_index 是「消耗掉的待结算步骤」，不等于走过的房间数。
	# 这一条是真机上抓到的——玩家打完一趟，结算屏写「推进 9/9 步」，
	# 城镇屏却写「最好成绩 22 步」。两个数都对，错的是它们不该是同一个数。
	t.section("成绩口径")
	var cm := Campaign.new()
	cm.setup_from_cfg(db.campaign_cfg, TEST_PATH)
	var heroes: Array = ["man_at_arms", "highwayman", "vestal", "plague_doctor"]
	var m: Dictionary = MapGen.build(db, "weald", "short", 1, DdRng.new(4242))
	var e := Expedition.new()
	e.setup(db, heroes, [], db.expedition_cfg.preset("standard"), 4242, "standard", {}, {})
	e.set_location("weald", "short")
	e.enter_map(m)
	var nb0: Dictionary = (MapGen.neighbors(m, int(m["start"])) as Array)[0]
	# 故意给这条走廊塞三件事：一步移动 = 三个待结算步骤
	(m["edges"][int(nb0["edge"])] as Dictionary)["steps"] = [
		{"kind": "walk"}, {"kind": "walk"}, {"kind": "walk"}]
	e.travel(int(nb0["room"]))
	while e.has_pending():
		e.take_step()
	var rooms: int = int(e.stats.get("rooms_visited", 0))
	t.eq(e.step_index > rooms, true, "step_index(%d) 与房间数(%d) 确实不是一个口径" % [e.step_index, rooms])
	cm.settle(e)
	t.eq(cm.best_steps, rooms, "成绩记的是房间数（%d），不是 step_index（%d）" % [rooms, e.step_index])

	t.section("战利品只由远征产生")
	var exp_loot_cfg: Dictionary = c2.cfg.get("loot", {})
	t.ok(exp_loot_cfg.has("battle_gold"), "掉落配置存在")
	t.ok(int((exp_loot_cfg.get("battle_gold", [0, 0]) as Array)[1]) > 0, "每场胜利有金币下限以上")

	t.section("技能组（M19）")
	# 技能表要手动注入：Campaign 不自己读表，场景在 load_or_new 之前灌进来。
	# 不注入 = 空表 = 全装，也就是 M18 及以前的行为。
	c.skill_table = db.hero_skill_table()
	t.eq(c.skill_slot_max("crusader"), 4, "十字军技能栏 4 格（heroes.json 的 skill_selection）")
	t.eq(c.skill_slot_max("abomination"), 7, "憎恶不能选技能，7 个全开")
	t.eq(c.equipped_skills("crusader").size(), 4, "默认装 4 个")
	var preset: Array = (c.cfg.get("default_skills", {}) as Dictionary).get("crusader", [])
	t.ok(preset.size() > 0, "campaign.json 里有 default_skills.crusader")
	t.eq(c.equipped_skills("crusader"), preset, "默认组取自 default_skills，不是拍脑袋")
	# 每个默认技能都必须是这个职业真有的——写错一个 id 不会报错，
	# 只会让这个英雄少一个技能，战斗里看起来像「技能栏少一格」。
	for sid in c.equipped_skills("crusader"):
		t.ok(c.skill_choices("crusader").has(str(sid)), "默认技能 %s 在该职业技能表里" % str(sid))

	t.eq(c.set_skills("crusader", []), "至少带一个技能", "不能一个技能都不带")
	t.eq(c.set_skills("crusader",
		["smite", "holy_lance", "inspiring_cry", "zealous_accusation", "battle_heal"]),
		"最多带 4 个", "超过 4 个被拒，且给的是明确原因")
	t.eq(c.set_skills("crusader", ["smite", "not_a_skill"]).is_empty(), false, "非法技能 id 被拒")
	t.eq(c.set_skills("crusader", ["smite", "smite"]), "", "重复 id 去重后合法")
	t.eq(c.equipped_skills("crusader"), ["smite"], "去重生效：只剩一个")
	t.eq(c.set_skills("crusader", ["smite", "holy_lance"]), "", "合法组合可以改")
	t.eq(c.equipped_skills("crusader").size(), 2, "改成 2 个后生效")

	# 不可选职业：憎恶是变身职业，数据里 can_select=false。
	var cfg_ab: Dictionary = db.campaign_cfg.duplicate(true)
	cfg_ab["roster_start"]["heroes"] = ["abomination"]
	var cab := Campaign.new()
	cab.setup_from_cfg(cfg_ab, TEST_PATH + ".ab.json")
	cab.skill_table = db.hero_skill_table()
	cab.new_game()
	t.eq(cab.equipped_skills("abomination").size(), 0, "不可选 = 空 = 全装")
	t.eq(cab.set_skills("abomination", [str(cab.skill_choices("abomination")[0])]).is_empty(),
		false, "不可选职业拒绝改技能")

	# 变身职业（M31）：憎恶不能选技能，7 个全开；界面上要能区分
	# 「他没选」和「他不用选」——否则公会屏会显示「已装备 0 / 7」。
	t.eq(c.skill_selectable("abomination"), false, "憎恶不可选技能")
	t.eq(c.skill_selectable("crusader"), true, "十字军可选技能")
	t.eq(c.skill_slot_max("abomination"), 7, "变身职业的格子数 = 技能总数")
	t.eq(c.equipped_skills("abomination").is_empty(), true,
		"憎恶的技能组是空的（空 = 全开，不是没带）")

	# 存档往返：技能组要跟着人走
	c.set_skills("vestal", ["judgement", "divine_grace"])
	c.save()
	var c_rt := Campaign.new()
	c_rt.setup_from_cfg(db.campaign_cfg, TEST_PATH)
	c_rt.skill_table = db.hero_skill_table()
	t.ok(c_rt.load_or_new(), "重新读档")
	t.eq(c_rt.equipped_skills("vestal"), ["judgement", "divine_grace"], "技能组随存档保留")

	# 旧档兼容：M18 及以前的存档没有 skills 字段。
	# **必须回默认组，不能回落成空数组**——空数组在战斗层表示「全装」，
	# 那会让老档读进来还是 7 个技能，和新档不一致。
	var old: Dictionary = c.to_dict()
	for k in (old["roster"] as Dictionary).keys():
		old["roster"][k].erase("skills")
	var c_old := Campaign.new()
	c_old.setup_from_cfg(db.campaign_cfg, TEST_PATH + ".old.json")
	c_old.skill_table = db.hero_skill_table()
	c_old.from_dict(old)
	t.eq(c_old.equipped_skills("crusader").size(), 4, "旧档缺 skills → 回默认 4 个，不是全开")

	# 战斗层：传了才收窄，不传保持全装（旧基线靠这一条）
	var bl := Battle.new()
	bl.setup(["crusader"], ["cultist_brawler_A"], 7, 0, 0, {}, {},
		{"crusader": ["smite", "holy_lance"]})
	t.eq((bl.party[0] as Combatant).actions.size(), 2, "只装传进来的 2 个技能")
	var bl2 := Battle.new()
	bl2.setup(["crusader"], ["cultist_brawler_A"], 7, 0, 0, {}, {}, {})
	t.eq((bl2.party[0] as Combatant).actions.size(), 7, "不传 = 全装 7 个（M18 及以前的行为）")
	# 顺序必须跟数据一致，不能按传入顺序重排——否则同一英雄在不同档里技能位置会跳
	var bl3 := Battle.new()
	bl3.setup(["crusader"], ["cultist_brawler_A"], 7, 0, 0, {}, {},
		{"crusader": ["holy_lance", "smite"]})
	t.eq((bl3.party[0] as Combatant).actions.size(), 2, "反序传入也是 2 个")
	t.eq(str(((bl3.party[0] as Combatant).actions[0] as Dictionary).get("id", "")), "smite",
		"技能顺序跟数据一致（smite 在 holy_lance 之前）")

	t.section("建筑（M22）")
	# 疗养院 / 修道院 / 酒馆：这三座补的是规则缺口（cure 从没被调用、回城减压写死 40），
	# 不是把按钮换个位置。所以每条都要能看出「钱扣了没有、东西真的没了没有」。
	var cb := Campaign.new()
	cb.setup_from_cfg(db.campaign_cfg, TEST_PATH + ".bld.json")
	cb.quirk_lib = db.quirk_lib
	cb.skill_table = db.hero_skill_table()
	cb.start_quirks_enabled = false
	cb.new_game()
	cb.add_loot(5000, {})

	# 从真表里取一条负面怪癖和一条疾病，不写死 id——
	# 硬编码的 id 哪天被数据管线改名，测试会红在一个和本事无关的地方。
	var neg: String = ""
	var dis: String = ""
	for qid in db.quirk_lib.order:
		var s: String = str(qid)
		if db.quirk_lib.is_disease(s):
			if dis.is_empty():
				dis = s
		elif db.quirk_lib.slot_kind(s) == "negative" and neg.is_empty():
			neg = s
	t.ok(not neg.is_empty() and not dis.is_empty(), "真表里能找到负面怪癖和疾病")

	(cb.roster["crusader"] as Dictionary)["quirks"] = [neg, dis]
	t.eq(cb.diseases_of("crusader"), [dis], "疾病只认疾病")
	t.eq(cb.negative_quirks_of("crusader"), [neg], "负面怪癖不含疾病")

	var g_d: int = cb.gold
	t.eq(cb.treat_disease("crusader"), "", "治病成功")
	t.eq(cb.gold, g_d - cb.disease_cost(), "治病扣钱")
	t.eq(cb.diseases_of("crusader").is_empty(), true, "病真的没了")
	t.eq(cb.treat_disease("crusader").is_empty(), false, "没病时拒绝，且不白扣钱")

	# 周次（M23）：进一次建筑占一周，这一周不能再进别的门，也不能出征
	t.eq(cb.busy_of("crusader"), 1, "治完占一周")
	t.eq(cb.purge_quirk("crusader").is_empty(), false, "这周已经占着，不能再清怪癖")
	t.eq(cb.selectable_ids().has("crusader"), false, "忙的人不在可出战名单里")
	t.eq(cb.default_party().has("crusader"), false, "默认出战也不会带他")
	cb.advance_week()
	t.eq(cb.busy_of("crusader"), 0, "推进一周后空出来")
	t.eq(cb.selectable_ids().has("crusader"), true, "空出来后回到可出战名单")

	var g_q: int = cb.gold
	t.eq(cb.purge_quirk("crusader"), "", "清负面怪癖成功")
	t.eq(cb.gold, g_q - cb.quirk_cost(), "清怪癖扣钱")
	t.eq(cb.negative_quirks_of("crusader").is_empty(), true, "怪癖真的没了")
	cb.advance_week()

	cb.gold = 0
	t.eq(cb.treat_disease("crusader").is_empty(), false, "钱不够时拒绝")

	# 减压：两座建筑减得不一样多，钱也不一样
	cb.gold = 5000
	(cb.roster["vestal"] as Dictionary)["stress"] = 120.0
	t.eq(cb.rest_options().size(), 2, "两种减压建筑")
	var ta: Dictionary = cb.rest_option("tavern")
	t.eq(int(ta.get("relief", 0)) > int(cb.rest_option("abbey").get("relief", 0)), true,
		"酒馆减得比修道院多")
	var g_s: int = cb.gold
	t.eq(cb.rest_at("tavern", "vestal"), "", "酒馆减压成功")
	t.eq(float((cb.roster["vestal"] as Dictionary)["stress"]),
		120.0 - float(ta.get("relief", 0)), "压力按 relief 减")
	t.eq(cb.gold, g_s - int(ta.get("cost", 0)), "减压扣钱")
	t.eq(cb.busy_of("vestal"), 1, "减压也占一周")
	cb.advance_week()
	(cb.roster["vestal"] as Dictionary)["stress"] = 0.0
	t.eq(cb.rest_at("abbey", "vestal").is_empty(), false, "压力为 0 时拒绝")

	# 墓园：只展示，不改档
	t.eq(cb.graveyard().is_empty(), true, "没人死过 → 墓园为空")
	(cb.roster["highwayman"] as Dictionary)["deaths"] = 3
	var gv: Array = cb.graveyard()
	t.eq(gv.size(), 1, "有阵亡记录才出现在墓园")
	t.eq(int((gv[0] as Dictionary).get("deaths", 0)), 3, "墓园记的是阵亡次数")

	t.section("周次（M23）")
	# 一趟 = 一周。settle 推进周次，忙的人在这里少忙一周。
	var cw := Campaign.new()
	cw.setup_from_cfg(db.campaign_cfg, TEST_PATH + ".week.json")
	cw.skill_table = db.hero_skill_table()
	cw.start_quirks_enabled = false
	cw.new_game()
	t.eq(cw.week, 1, "新档是第 1 周")
	(cw.roster["crusader"] as Dictionary)["busy"] = 2
	t.eq(cw.selectable_ids().has("crusader"), false, "忙 2 周的人不可出战")
	cw.advance_week()
	t.eq(cw.week, 2, "推进到第 2 周")
	t.eq(cw.busy_of("crusader"), 1, "忙的人少忙一周")
	cw.advance_week()
	t.eq(cw.busy_of("crusader"), 0, "两周后空出来")
	t.eq(cw.selectable_ids().has("crusader"), true, "空出来就能出战")

	# 存档往返：周次和占用都要跟着档走
	cw.save()
	var cw2 := Campaign.new()
	cw2.setup_from_cfg(db.campaign_cfg, TEST_PATH + ".week.json")
	cw2.skill_table = db.hero_skill_table()
	t.ok(cw2.load_or_new(), "读档成功")
	t.eq(cw2.week, cw.week, "周次随存档保留")

	# 旧档没有 week 字段：按「趟数 + 1」补，而不是从 1 重来
	var old_d: Dictionary = cw.to_dict()
	old_d.erase("week")
	var cw3 := Campaign.new()
	cw3.setup_from_cfg(db.campaign_cfg, TEST_PATH + ".week_old.json")
	cw3.skill_table = db.hero_skill_table()
	cw3.from_dict(old_d)
	t.eq(cw3.week, int(old_d.get("expeditions", 0)) + 1, "旧档按趟数补周次")

	# 主动休整（M24）：时间从「打完一趟顺便过」变成「可以主动买的资源」
	var cyc: Dictionary = cw.cfg.get("town_cycle", {})
	var idle_cost: int = int(cyc.get("idle_cost", 50))
	var wk_relief: float = float(cyc.get("weekly_stress_relief", 0.0))
	t.ok(idle_cost > 0, "休整有成本（否则就是免费的商店刷新）")
	t.ok(wk_relief > 0.0, "每周有自然恢复（否则休整纯亏）")

	(cw.roster["vestal"] as Dictionary)["stress"] = 100.0
	(cw.roster["crusader"] as Dictionary)["busy"] = 1
	cw.gold = 1000
	var wk_before: int = cw.week
	var gold_before: int = cw.gold
	t.eq(cw.idle_week(), "", "休整一周成功")
	t.eq(cw.week, wk_before + 1, "周次推进一周")
	t.eq(cw.gold, gold_before - idle_cost, "休整扣钱")
	t.eq(float((cw.roster["vestal"] as Dictionary)["stress"]), 100.0 - wk_relief,
		"压力按配置自然恢复")
	t.eq(cw.busy_of("crusader"), 0, "休整也让建筑队列前进")

	cw.gold = 0
	t.eq(cw.idle_week().is_empty(), false, "钱不够时不能休整")
	t.eq(cw.week, wk_before + 1, "失败的休整不推进时间")

	_test_resolve(t, db)
	_test_board(t, db)
	_test_roster(t, db)
	_test_dismiss(t, db)

	_cleanup()


## 决心等级（M25）：经验、装备上限、双向锁。
##
## 这一节的重点不是「能升级」，而是**不能**去做某些事：
## 等级不够穿不上装备、超了 2 级进不去低难度本、低了要白吃压力。
## 四条限制缺任何一条，「往高难度走」就不再是唯一出路。
static func _test_resolve(t: TestLib, db: DdDb) -> void:
	t.section("决心等级")
	var r := Campaign.new()
	r.setup_from_cfg(db.campaign_cfg, TEST_PATH + ".resolve.json")
	var hid: String = str((db.campaign_cfg["roster_start"]["heroes"] as Array)[0])

	t.eq(r.resolve_of(hid), 1, "新兵 1 级")
	t.eq(r.xp_of(hid), 0, "新兵 0 经验")
	t.eq(r.xp_to_next(hid), int(Campaign.RESOLVE_XP[2]), "到 2 级需要 5 点")

	# 差一点点升不了
	t.eq(r.gain_xp(hid, 4), 0, "4 点不够升 2 级")
	t.eq(r.resolve_of(hid), 1, "还是 1 级")
	t.eq(r.xp_of(hid), 4, "经验攒着")
	t.eq(r.gain_xp(hid, 1), 1, "再来 1 点升上去")
	t.eq(r.resolve_of(hid), 2, "到 2 级")
	t.eq(r.xp_of(hid), 0, "升级后余经验归零")

	# 一趟给得多要能连升（2→3 要 6，3→4 要 8，所以 14 点正好跨两级）
	t.eq(r.gain_xp(hid, 14), 2, "14 点连升两级")
	t.eq(r.resolve_of(hid), 4, "到 4 级")

	# 满级封顶
	r.gain_xp(hid, 999)
	t.eq(r.resolve_of(hid), Campaign.MAX_RESOLVE, "封顶在 %d 级" % Campaign.MAX_RESOLVE)
	t.eq(r.xp_to_next(hid), 0, "满级不用再攒")
	t.eq(r.gain_xp(hid, 999), 0, "满级后加经验无效")

	t.section("装备上限绑等级")
	# 原版是「第 N 级解锁第 N 阶武器」，我们是 0 基索引所以再减一
	r.roster[hid]["gear"] = 0
	for lv in range(1, Campaign.MAX_RESOLVE + 1):
		r.roster[hid]["resolve"] = lv
		r.roster[hid]["gear"] = 0
		t.eq(r.gear_cap(hid), mini(lv - 1, Campaign.MAX_GEAR),
			"%d 级能穿到 %d 阶" % [lv, mini(lv - 1, Campaign.MAX_GEAR)])
	# 反过来：升级被等级挡住时，价格是空的、原因是有的
	r.roster[hid]["resolve"] = 1
	r.roster[hid]["gear"] = 0
	r.gold = 999999
	t.eq(r.can_upgrade(hid), false, "1 级有钱也升不了 2 阶")
	t.eq(r.upgrade_cost(hid).is_empty(), true, "被等级挡住时没有报价")
	t.eq(r.gear_gate_reason(hid).is_empty(), false, "但要给得出原因")

	t.section("双向等级锁")
	r.roster[hid]["resolve"] = 3
	# 高出 2 级 → 拒绝（1 级本、3 级人：差 2）
	t.eq(r.can_join(hid, 1), false, "3 级打学徒本被拒")
	t.eq(r.can_join(hid, 3), true, "3 级打精英本正常")
	# 低 2 级 → 能进，但吃 40 点
	t.eq(r.entry_stress(hid, 5), 40.0, "低 2 级进本吃 40 压力")
	r.roster[hid]["resolve"] = 5
	t.eq(r.can_join(hid, 5), true, "5 级打冠军本正常")
	t.eq(r.entry_stress(hid, 5), 0.0, "够格就没有进本压力")
	t.eq(r.can_join(hid, 3), false, "5 级打精英本被拒")
	r.roster[hid]["resolve"] = 1
	t.eq(r.entry_stress(hid, 5), 80.0, "1 级打冠军本吃 80 压力")
	t.eq(r.can_join(hid, 5), true, "但不会被拒绝——能打，只是很难")

	# 受压倍率（M29）：和进本压力配套的另一半
	t.near(r.stress_mult_for(hid, 1), 1.0, 0.001, "够格时倍率是 1.0")
	t.near(r.stress_mult_for(hid, 3), 1.5, 0.001, "低 2 级 → ×1.5")
	t.near(r.stress_mult_for(hid, 5), 2.0, 0.001, "低 4 级 → ×2.0")
	r.roster[hid]["resolve"] = 5
	t.near(r.stress_mult_for(hid, 5), 1.0, 0.001, "同级没有惩罚")

	t.section("经验只认完成")
	t.eq(r.quest_xp(1, "short", "explore"), 2, "学徒短本 2 点")
	t.eq(r.quest_xp(5, "long", "explore"), 12, "冠军长本 12 点")
	t.eq(r.quest_xp(3, "medium", "kill_boss"), 8, "首领本按 boss 档，不看尺寸")
	t.eq(r.quest_xp(2, "short", "explore"), 2, "不规整的等级归到不超过它的档")

	# 一趟给多少经验，取决于「完成没完成」
	var e := Expedition.new()
	e.set_location("weald", "short", 1)
	e.quest_type = "explore"
	e.end_reason = "complete"
	t.eq(r.xp_for(e), 2, "完成给满")
	e.end_reason = "incomplete"
	t.eq(r.xp_for(e), 1, "打到了没打下来给一半")
	e.end_reason = "retreat"
	t.eq(r.xp_for(e), 0, "撤退不给经验")
	e.quest_type = "kill_boss"
	e.dungeon_level = 3
	e.end_reason = "complete"
	t.eq(r.xp_for(e), 8, "首领任务按 boss 档算，不看尺寸")

	t.section("招募是新人不复活")
	var r2 := Campaign.new()
	r2.setup_from_cfg(db.campaign_cfg, TEST_PATH + ".resolve2.json")
	var h2: String = str((db.campaign_cfg["roster_start"]["heroes"] as Array)[0])
	r2.gain_xp(h2, 20)
	r2.roster[h2]["gear"] = 2
	r2.roster[h2]["deaths"] = 2
	r2.roster[h2]["alive"] = false
	r2.free_recruits = 1
	t.eq(r2.recruit(h2), true, "免费征召成功")
	t.eq(r2.resolve_of(h2), 1, "招回来是 1 级新人")
	t.eq(r2.gear_of(h2), 0, "装备也回到 1 阶")
	t.eq(int((r2.roster[h2] as Dictionary).get("deaths", 0)), 2, "战绩计数保留（墓园要记）")

	t.section("旧档兼容")
	# 没有 resolve 字段的档：按装备阶反推，而不是一律补 1
	var raw: Dictionary = r2.to_dict()
	(raw["roster"][h2] as Dictionary).erase("resolve")
	(raw["roster"][h2] as Dictionary).erase("xp")
	(raw["roster"][h2] as Dictionary)["gear"] = 3
	var r3 := Campaign.new()
	r3.setup_from_cfg(db.campaign_cfg, TEST_PATH + ".resolve3.json")
	r3.from_dict(raw)
	t.eq(r3.resolve_of(h2), 4, "装备 3 阶的旧档反推成 4 级")
	t.eq(r3.can_join(h2, 3), true, "反推之后不会把自己的装备锁在门外")

	# 存档往返
	var r4 := Campaign.new()
	r4.setup_from_cfg(db.campaign_cfg, TEST_PATH + ".resolve4.json")
	r4.save()
	t.eq(r4.load_or_new(), true, "格式正确能读回")
	var r5 := Campaign.new()
	r5.setup_from_cfg(db.campaign_cfg, TEST_PATH + ".resolve4.json")
	r5.gain_xp(h2, 6)
	r5.save()
	var r6 := Campaign.new()
	r6.setup_from_cfg(db.campaign_cfg, TEST_PATH + ".resolve4.json")
	r6.load_or_new()
	t.eq(r6.resolve_of(h2), 2, "等级随存档保留")
	t.eq(r6.xp_of(h2), 1, "余下的经验也保留")


## 任务板（M26）：等级跟着名册走，但永远留一张学徒本。
##
## 这一段测的核心是**两条规则的合力**：
##   · 加权 → 名册强了，板子跟着变硬（往上赶）
##   · 保底 → 板子里永远有学徒本（留退路）
## 只做前者会锁死玩家，只做后者等于没做。所以两条都要单独钉住。
static func _test_board(t: TestLib, db: DdDb) -> void:
	t.section("任务板")
	var b := Campaign.new()
	b.setup_from_cfg(db.campaign_cfg, TEST_PATH + ".board.json")

	t.eq(b.board.size(), Campaign.BOARD_SLOTS.size(),
		"板子有 %d 个槽" % Campaign.BOARD_SLOTS.size())
	t.eq(b.board_ceiling(), 1, "全员 1 级时上限是 1")
	var all_easy: bool = true
	for slot in b.board:
		if int((slot as Dictionary).get("level", 0)) != 1:
			all_easy = false
	t.eq(all_easy, true, "1 级名册只出学徒本")

	# 名册拉到 5 级：低档会从池里消失——5 级的人打学徒本会被直接拒绝，
	# 留着那种槽只会得到「够格 0 人」的废卡。
	for k in b.roster.keys():
		(b.roster[k] as Dictionary)["resolve"] = 5
	t.eq(b.board_ceiling(), 5, "5 级名册上限是 5")
	t.eq(b.board_level_pool(), [5], "全员 5 级时只剩冠军本")
	t.eq(b.board_floor_level(), 5, "保底档跟着抬到 5 级")

	# 只要名册里有一个 1 级新人，三档就都回来了
	(b.roster[str((db.campaign_cfg["roster_start"]["heroes"] as Array)[0])] as Dictionary)["resolve"] = 1
	t.eq(b.board_level_pool(), [1, 3, 5], "有人在 1 级时三档全在")
	t.eq(b.board_floor_level(), 1, "保底档回到学徒本")

	# 重抽 40 次：每一次都必须在保底档上有一张，且不能超出名册上限
	var floor_missing: int = 0
	var over_cap: int = 0
	for i in range(40):
		b.roll_board()
		var has_floor: bool = false
		var fl: int = b.board_floor_level()
		for slot2 in b.board:
			var lv2: int = int((slot2 as Dictionary).get("level", 0))
			if lv2 == fl:
				has_floor = true
			if lv2 > 5:
				over_cap += 1
		if not has_floor:
			floor_missing += 1
	t.eq(floor_missing, 0, "40 次重抽都留着保底档")
	t.eq(over_cap, 0, "没有超出名册上限的等级")

	# 3 级名册不该刷出 5 级本——板子永远不给你打不过的东西
	for k2 in b.roster.keys():
		(b.roster[k2] as Dictionary)["resolve"] = 3
	var too_high: int = 0
	for i2 in range(40):
		b.roll_board()
		for slot3 in b.board:
			if int((slot3 as Dictionary).get("level", 0)) > 3:
				too_high += 1
	t.eq(too_high, 0, "3 级名册不会刷出 5 级本")

	# 全员 5 级 + 板子里只剩学徒本 = 谁都带不动
	for k3 in b.roster.keys():
		(b.roster[k3] as Dictionary)["resolve"] = 5
	for slot4 in b.board:
		(slot4 as Dictionary)["level"] = 1
	t.eq(b.board_has_runnable(), false, "全员 5 级时学徒本谁都带不动")
	for slot5 in b.board:
		(slot5 as Dictionary)["level"] = 5
	t.eq(b.board_has_runnable(), true, "5 级本有人能打")

	# 存档往返：板子必须逐槽保留，**读档不能重抽**——
	# 重抽等于「读一次档刷一次任务」，正好能绕开 M25 的等级锁。
	b.roll_board()
	var snap: Array = b.board.duplicate(true)
	b.save()
	var b2 := Campaign.new()
	b2.setup_from_cfg(db.campaign_cfg, TEST_PATH + ".board.json")
	t.eq(b2.load_or_new(), true, "读档成功")
	t.eq(b2.board.size(), snap.size(), "板子随存档保留")
	t.eq(b2.board, snap, "每一槽都和存进去的一模一样")

	# 体验底线：一周四张卡里，**最多一张**「凑不够 4 人」。
	# 那一张是给名册里最弱的人的保底，其余三张必须能出发。
	# 超过一张废卡，玩家第一反应就是「这游戏坏了」，而不是「我该招人」。
	#
	# 用 4×Lv5 + 1×Lv1 来测：这是最容易出废卡的名册结构
	# （老人嫌学徒本太简单被拒，新人凑不齐一队）。
	for k5 in b.roster.keys():
		(b.roster[k5] as Dictionary)["resolve"] = 5
	(b.roster[str((db.campaign_cfg["roster_start"]["heroes"] as Array)[0])] as Dictionary)["resolve"] = 1
	var over_dead: int = 0
	var worst: int = 0
	for i3 in range(60):
		b.roll_board()
		var dead: int = 0
		for slot7 in b.board:
			if b.fit_count(int((slot7 as Dictionary).get("level", 0))) < Campaign.PARTY_MAX:
				dead += 1
		worst = maxi(worst, dead)
		if dead > 1:
			over_dead += 1
	t.eq(over_dead, 0, "60 次重抽里废卡从不超过 1 张（最多见到 %d 张）" % worst)

	# 推进一周会重抽，否则板子就永远停在存档那一刻
	var prev: Array = b.board.duplicate(true)
	var changed: int = 0
	for i4 in range(20):
		b.advance_week()
		if b.board != prev:
			changed += 1
		prev = b.board.duplicate(true)
	t.ok(changed > 0, "推进一周会重抽任务板（20 周里变了 %d 次）" % changed)

	# 旧档没有 board 字段：按当前名册现抽一块，而不是留空
	var raw: Dictionary = b2.to_dict()
	raw.erase("board")
	var b3 := Campaign.new()
	b3.setup_from_cfg(db.campaign_cfg, TEST_PATH + ".board3.json")
	b3.from_dict(raw)
	t.eq(b3.board.size(), Campaign.BOARD_SLOTS.size(), "旧档自动补一块板子")
	var b3_ok: bool = true
	for slot6 in b3.board:
		if not (slot6 as Dictionary).has("level"):
			b3_ok = false
	t.eq(b3_ok, true, "补出来的槽都有等级")


## 名册扩容与招新（M27）。
##
## 最要紧的一条不是「能招人」，是**扩张之后读档不能丢人**：
## 老版 `from_dict` 以配置里的 5 人重建 roster，名册一旦超过 5 个，
## 多出来的会被静默丢掉——而丢的正好是玩家花金币招来的那几个。
static func _test_roster(t: TestLib, db: DdDb) -> void:
	t.section("名册扩容")
	var c := Campaign.new()
	c.setup_from_cfg(db.campaign_cfg, TEST_PATH + ".roster.json")
	c.known_heroes = db.hero_ids()

	var all_n: int = db.hero_ids().size()
	t.eq(c.roster_max(), all_n, "名册上限 = 职业总数（%d）" % all_n)
	t.eq(c.roster_full(), false, "开局没满")

	var start_n: int = c.hero_ids().size()
	# M34 起同职业可以多人：池子不再排除「已入册的职业」，就是全部职业
	t.eq(c.hireable_pool().size(), all_n, "候选池 = 全部已知职业（同职业可多人）")

	c.roll_recruit_candidates()
	t.eq(c.recruit_candidates.size(), 2, "本周来 2 个新面孔")
	t.eq((c.hire_cost().get("heirlooms", {}) as Dictionary).is_empty(), true,
		"招新只收金币（传家宝留给建筑）")
	t.eq(c.recruit_candidates[0] != c.recruit_candidates[1], true, "一周内两个候选不重复")

	# —— 招一个 ——
	c.add_loot(99999, {"bust": 99, "portrait": 99, "crest": 99, "deed": 99})
	var pick: String = str(c.recruit_candidates[0])
	t.eq(c.can_hire(pick), true, "有钱就能招")
	t.eq(c.hire(pick), true, "招进来了")
	t.eq(c.hero_ids().size(), start_n + 1, "名册 +1")
	t.eq(c.alive_ids().has(pick), true, "新人是活的")
	t.eq(c.resolve_of(pick), 1, "新人是 1 级")
	t.eq(c.gear_of(pick), 0, "装备 0 阶")
	t.eq(c.can_join(pick, 1), true, "新人能打学徒本")
	t.eq(c.recruit_candidates.has(pick), false, "招走后从这一周的候选里移除")
	t.eq(c.can_hire(pick), false, "同一张卡不能连招两次")

	# —— 再招一批，凑到 8 人以上（这才是扩容真正开始起作用的地方）——
	c.roll_recruit_candidates()
	for cls2 in c.recruit_candidates.duplicate():
		if c.can_hire(str(cls2)):
			c.hire(str(cls2))
	var n_before: int = c.hero_ids().size()
	var order_before: Array = c.hero_ids()
	t.ok(n_before > 5, "名册已经超过开局的 5 人（%d）" % n_before)

	# —— 关键：读档不能丢人 ——
	c.save()
	var c2 := Campaign.new()
	c2.setup_from_cfg(db.campaign_cfg, TEST_PATH + ".roster.json")
	c2.known_heroes = db.hero_ids()
	t.eq(c2.load_or_new(), true, "读档成功")
	t.eq(c2.hero_ids().size(), n_before, "名册一个不少（%d 人）" % n_before)
	t.eq(c2.hero_ids(), order_before, "顺序也一致")

	# —— 旧档没有 order 字段：靠兜底循环保住多出来的人 ——
	var raw: Dictionary = c2.to_dict()
	raw.erase("order")
	var c3 := Campaign.new()
	c3.setup_from_cfg(db.campaign_cfg, TEST_PATH + ".roster3.json")
	c3.known_heroes = db.hero_ids()
	c3.from_dict(raw)
	t.eq(c3.hero_ids().size(), n_before, "没有 order 字段也不会丢人")
	var cfg_n: int = (db.campaign_cfg["roster_start"]["heroes"] as Array).size()
	t.eq(c3.hero_ids().slice(0, cfg_n), order_before.slice(0, cfg_n),
		"配置里的那几个人排在最前")

	# —— 名册满（M34：上限是 15 人头，不再是职业数量）——
	var c4 := Campaign.new()
	c4.setup_from_cfg(db.campaign_cfg, TEST_PATH + ".roster4.json")
	c4.known_heroes = db.hero_ids()
	c4.add_loot(999999, {"bust": 99, "portrait": 99, "crest": 99, "deed": 99})
	_fill_roster(c4)
	t.eq(c4.roster_full(), true, "招到 15 人就是满的（%d）" % c4.hero_ids().size())
	t.eq(c4.can_hire("vestal"), false, "满员时谁都不能招")
	# 满了之后池子仍然非空——只是招不进来。这两件事必须分开：
	# 池子空 = 游戏里没有这个名字，招不了 = 你名册没位置。
	t.ok(c4.hireable_pool().size() > 0, "满员时候选池仍然非空（是名额满了，不是没人）")


## 解雇（M28）：名册唯一的出口。
##
## 三段重点：
##   · 删干净（roster + _order + 候选池），不留下引用不到的空壳
##   · **不能删到零**：名册空了而金币又不够招人，存档就再也走不动了
##   · 忙人不能删：他这周在疗养院，人走了那笔钱算什么
static func _test_dismiss(t: TestLib, db: DdDb) -> void:
	t.section("解雇")
	var c := Campaign.new()
	c.setup_from_cfg(db.campaign_cfg, TEST_PATH + ".dismiss.json")
	c.known_heroes = db.hero_ids()

	var ids: Array = c.hero_ids()
	var first: String = str(ids[0])
	var n0: int = ids.size()
	t.eq(c.can_dismiss(first), true, "名册 %d 人时可以解雇" % n0)
	t.eq(c.dismiss(first), true, "解雇成功")
	t.eq(c.hero_ids().size(), n0 - 1, "名册 -1")
	t.eq(c.roster.has(first), false, "数据也删了")
	t.eq(c.hero_ids().has(first), false, "顺序表里也没了")

	# 一路删到只剩一个活人
	var guard: int = 0
	while c.alive_ids().size() > 1 and guard < 30:
		c.dismiss(str(c.alive_ids()[0]))
		guard += 1
	t.eq(c.alive_ids().size(), 1, "只剩 1 个活人")
	var last: String = str(c.alive_ids()[0])
	t.eq(c.can_dismiss(last), false, "最后一个人不能解雇")
	t.eq(c.dismiss(last), false, "拒绝时也不真的删")
	t.eq(c.alive_ids().size(), 1, "人数没变")

	# 忙人不能解雇
	var c2 := Campaign.new()
	c2.setup_from_cfg(db.campaign_cfg, TEST_PATH + ".dismiss2.json")
	c2.known_heroes = db.hero_ids()
	var h2: String = str(c2.hero_ids()[0])
	(c2.roster[h2] as Dictionary)["busy"] = 1
	t.eq(c2.can_dismiss(h2), false, "忙人不能解雇")
	t.eq(c2.dismiss(h2), false, "点了也不删")

	# 死人可以移除（清墓园记录）
	(c2.roster[h2] as Dictionary)["busy"] = 0
	(c2.roster[h2] as Dictionary)["alive"] = false
	(c2.roster[h2] as Dictionary)["deaths"] = 3
	t.eq(c2.graveyard().is_empty(), false, "墓园里有他")
	t.eq(c2.dismiss(h2), true, "死人可以移除")
	t.eq(c2.graveyard().is_empty(), true, "墓园记录也没了")

	# 解雇要把名额让出来，否则「满了不能换人」还是没解
	# （M34：上限是 15 人头，所以要真的招满才测得出这条）
	var c3 := Campaign.new()
	c3.setup_from_cfg(db.campaign_cfg, TEST_PATH + ".dismiss3.json")
	c3.known_heroes = db.hero_ids()
	c3.add_loot(999999, {"bust": 99, "portrait": 99, "crest": 99, "deed": 99})
	_fill_roster(c3)
	t.eq(c3.roster_full(), true, "先招满")
	var gone: String = str(c3.hero_ids()[0])
	var gone_def: String = c3.def_of(gone)
	c3.dismiss(gone)
	t.eq(c3.roster_full(), false, "解雇后有名额了")
	t.eq(c3.hireable_pool().has(gone_def), true, "被解雇的职业仍在候选池里（M34）")

	# 存档往返：删掉的人不能读档又回来
	var c4 := Campaign.new()
	c4.setup_from_cfg(db.campaign_cfg, TEST_PATH + ".dismiss4.json")
	c4.known_heroes = db.hero_ids()
	var drop: String = str(c4.hero_ids()[0])
	c4.dismiss(drop)
	var left: Array = c4.hero_ids()
	c4.save()
	var c5 := Campaign.new()
	c5.setup_from_cfg(db.campaign_cfg, TEST_PATH + ".dismiss4.json")
	c5.known_heroes = db.hero_ids()
	t.eq(c5.load_or_new(), true, "读档成功")
	t.eq(c5.hero_ids(), left, "名册和存档前一致")
	t.eq(c5.hero_ids().has(drop), false, "解雇掉的人没有回来")


## 把名册招满（M34）。
##
## 上限是人头 15，而职业只有 15 个、开局已经占了 5 个——所以**必须靠同职业重复**
## 才填得满。这个 helper 本身就是这一期的证据：填不满就说明同职业多人没生效。
static func _fill_roster(c: Campaign) -> void:
	var guard: int = 0
	while not c.roster_full() and guard < 300:
		guard += 1
		c.roll_recruit_candidates()
		var hired: bool = false
		for cls in c.recruit_candidates.duplicate():
			if c.can_hire(str(cls)):
				c.hire(str(cls))
				hired = true
		if not hired:
			break


static func _cleanup() -> void:
	var abs_path: String = ProjectSettings.globalize_path(TEST_PATH)
	if FileAccess.file_exists(TEST_PATH):
		DirAccess.remove_absolute(abs_path)

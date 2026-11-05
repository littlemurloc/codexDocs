class_name TestQuirk
extends RefCounted
## M14 怪癖与疾病。
##
## 这一层最容易出错的不是「读表」，是**条件判定的方向**和**阈值口径**：
##   * lightabove 75 是 >= 还是 >（差一点就在 75 那一格翻脸）
##   * hpbelow 的 rule_data 是比例（0.5）还是百分比数字（50）
##   * stress_above 的 rule_data 反过来是绝对值（50）
## 三者口径不同，是原表就这么写的。写错了不会报错，只会让「夜盲症」
## 在白天生效——那类 bug 只能靠断言抓。
##
## 第二组是槽位语义：3 正 / 3 负 / 1 疾病，满了**拒绝**而不是随机替换。
## 随机替换会让「攒一套想要的组合」变成不可能，是设计层面的错，不是数值问题。

static func run(t: TestLib, db: DdDb) -> void:
	var ql: QuirkLib = db.quirk_lib
	t.section("怪癖：数据装载")
	if ql == null or not ql.is_loaded():
		t.ok(false, "quirk_lib 未加载")
		return

	t.eq(int(ql.stats["quirks"]), 170, "怪癖 170 条")
	t.eq(int(ql.stats["diseases"]), 23, "其中疾病 23 条")
	t.eq(int(ql.stats["positive"]), 68, "正面 68 条")
	t.eq(int(ql.stats["negative"]), 79, "负面 79 条")
	t.eq(int(ql.stats["buff_refs"]), 195, "buff 引用 195 条")
	t.eq(int(ql.stats["missing_buffs"]), 0, "没有指向不存在 buff 的引用")

	# 数据里出现了代码不认识的 rule_type，必须报出来而不是静默当无效
	var unk: Array = ql.unknown_rules()
	t.eq(unk.size(), 0, "没有未知 rule_type  %s" % str(unk))

	# 覆盖率：可判 + 有承载 才算真的做完了
	var land: int = int(ql.stats["landable"])
	t.eq(land, 178, "战斗/远征/元层可落地 178 条")
	var parts: int = land + int(ql.stats["rule_blocked"]) + int(ql.stats["no_channel"]) \
		+ int(ql.stats["both_blocked"])
	t.eq(parts, 195, "四类相加等于全部引用（不重复不遗漏）")
	t.ok(float(land) / 195.0 > 0.9,
		"落地率 %.1f%% > 90%%" % (float(land) / 195.0 * 100.0))

	var empty_buff: int = 0
	for id in ql.order:
		if (ql.get_quirk(str(id)).get("buffs", []) as Array).is_empty():
			empty_buff += 1
	t.eq(empty_buff, 32, "32 条怪癖没有任何数值效果（纯奇物标记）")

	# 中文名必须全覆盖：界面回退到英文会让一屏中文里混进 night_blindness
	var no_cn: Array = []
	for id in ql.order:
		if not DdNames.QUIRK_NAMES.has(str(id)):
			no_cn.append(str(id))
	t.eq(no_cn.size(), 0, "170 条怪癖全部有中文名  %s" % str(no_cn.slice(0, 6)))

	# —— 规则判定 ——
	t.section("怪癖：条件判定方向")

	var b_tough: Dictionary = _buff_of(ql, "tough", 0)
	t.eq(ql.rule_active(b_tough, {}), true, "always 恒真")

	var b_dun: Dictionary = _buff_of(ql, "ruins_explorer", 0)
	t.eq(str(b_dun.get("rule_type", "")), "in_dungeon", "ruins_explorer 是 in_dungeon")
	t.eq(ql.rule_active(b_dun, {"dungeon": "crypts"}), true, "在 crypts 生效")
	t.eq(ql.rule_active(b_dun, {"dungeon": "weald"}), false, "在 weald 不生效")
	t.eq(ql.rule_active(b_dun, {}), false, "语境缺失按不生效（不是按 0 算）")

	# lightabove 75：>= 75 生效
	var b_rise: Dictionary = _buff_of(ql, "early_riser", 0)
	t.eq(str(b_rise.get("rule_type", "")), "lightabove", "early_riser 是 lightabove")
	t.eq(ql.rule_active(b_rise, {"light": 75.0}), true, "光照正好 75 生效（>=）")
	t.eq(ql.rule_active(b_rise, {"light": 74.9}), false, "光照 74.9 不生效")
	# lightbelow 26：<= 26 生效
	var b_owl: Dictionary = _buff_of(ql, "night_owl", 0)
	t.eq(str(b_owl.get("rule_type", "")), "lightbelow", "night_owl 是 lightbelow")
	t.eq(ql.rule_active(b_owl, {"light": 26.0}), true, "光照正好 26 生效（<=）")
	t.eq(ql.rule_active(b_owl, {"light": 26.1}), false, "光照 26.1 不生效")
	# 中间地带两者都不生效，这是设计（27–74 是无判定的灰带）
	t.eq(ql.rule_active(b_rise, {"light": 50.0}) or ql.rule_active(b_owl, {"light": 50.0}),
		false, "光照 50 时亮处/暗处怪癖都不生效")

	# hpbelow 的 rule_data 是比例
	var b_wind: Dictionary = _buff_of(ql, "second_wind", 0)
	t.eq(str(b_wind.get("rule_type", "")), "hpbelow", "second_wind 是 hpbelow")
	t.eq(ql.rule_active(b_wind, {"hp_ratio": 0.40}), true, "40% 血生效")
	t.eq(ql.rule_active(b_wind, {"hp_ratio": 0.60}), false, "60% 血不生效")

	# stress_above 的 rule_data 是绝对压力值
	var b_eat: Dictionary = _buff_of(ql, "stress_faster", 0)
	t.eq(str(b_eat.get("rule_type", "")), "stress_above", "stress_faster 是 stress_above")
	t.eq(ql.rule_active(b_eat, {"stress": 60.0}), true, "压力 60 生效")
	t.eq(ql.rule_active(b_eat, {"stress": 40.0}), false, "压力 40 不生效")

	var b_draw: Dictionary = _buff_of(ql, "quickdraw", 0)
	t.eq(str(b_draw.get("rule_type", "")), "firstroundonly", "quickdraw 是 firstroundonly")
	t.eq(ql.rule_active(b_draw, {"round": 1}), true, "第 1 轮生效")
	t.eq(ql.rule_active(b_draw, {"round": 2}), false, "第 2 轮不生效")

	var b_fear: Dictionary = _buff_of(ql, "fear_of_eldritch", 0)
	t.eq(ql.rule_active(b_fear, {"enemy_types": ["eldritch"]}), true, "对面有异形时生效")
	t.eq(ql.rule_active(b_fear, {"enemy_types": ["beast"]}), false, "对面没异形时不生效")

	var b_zoo: Dictionary = _buff_of(ql, "zoophobia", 0)
	t.eq(str(b_zoo.get("rule_type", "")), "monster_type_count_min", "zoophobia 是数量型")
	t.eq(ql.rule_active(b_zoo, {"enemy_types": ["beast"]}), true, "1 只兽类即生效")
	t.eq(ql.rule_active(b_zoo, {"enemy_types": []}), false, "没有兽类不生效")

	var b_slug: Dictionary = _buff_of(ql, "slugger", 0)
	t.eq(ql.rule_active(b_slug, {"skill_type": "melee"}), true, "近战技能生效")
	t.eq(ql.rule_active(b_slug, {"skill_type": "ranged"}), false, "远程技能不生效")
	t.eq(ql.rule_active(b_slug, {"skill_type": ""}), false, "技能未定时不生效")
	var b_eye: Dictionary = _buff_of(ql, "natural_eye", 0)
	t.eq(ql.rule_active(b_eye, {"skill_type": "ranged"}), true, "远程怪癖在远程生效")
	t.eq(ql.rule_active(b_eye, {"skill_type": "melee"}), false, "远程怪癖在近战不生效")

	# 判不了的四种：一律 false，不能「假装生效」
	t.section("怪癖：判不了的条件一律不生效")
	var camp_buff: Dictionary = {}
	for id in ql.order:
		for b in (ql.get_quirk(str(id)).get("buffs", []) as Array):
			if str(b.get("rule_type", "")) == "in_camp":
				camp_buff = b
				break
		if not camp_buff.is_empty():
			break
	t.eq(camp_buff.is_empty(), false, "数据里确实有 in_camp 的 buff")
	t.eq(ql.rule_active(camp_buff, {"dungeon": "crypts", "light": 100.0}), false,
		"in_camp 在战斗语境里判 false")

	# —— 抽选 ——
	t.section("怪癖：抽选")

	var rng: DdRng = DdRng.new(20260101)
	var pos_ok: bool = true
	var neg_ok: bool = true
	var zero_weight_picked: Array = []
	var disease_picked: bool = false
	for i in 200:
		var pid: String = ql.pick("positive", rng, [], false)
		if pid.is_empty() or not ql.is_positive(pid) or ql.is_disease(pid):
			pos_ok = false
		var nid: String = ql.pick("negative", rng, [], false)
		if nid.is_empty() or ql.is_positive(nid) or ql.is_disease(nid):
			neg_ok = false
		if float((ql.get_quirk(pid) as Dictionary).get("random_chance", 1.0)) <= 0.0 \
				and pid != "" and not zero_weight_picked.has(pid):
			zero_weight_picked.append(pid)
	t.eq(pos_ok, true, "positive 抽出来的一定是正面且非疾病")
	t.eq(neg_ok, true, "negative 抽出来的一定是负面且非疾病")
	t.eq(zero_weight_picked.size(), 0,
		"random_chance=0 的怪癖不进随机池  %s" % str(zero_weight_picked))

	# 疾病只从疾病池里出
	for i in 60:
		var did: String = ql.pick("any", rng, [], true)
		if did.is_empty() or not ql.is_disease(did):
			disease_picked = true
	t.eq(disease_picked, false, "疾病抽选只出疾病")

	# 互斥：持有 tough 之后不能再抽到 fragile
	var got_fragile: bool = false
	for i in 300:
		if ql.pick("negative", rng, ["tough"], false) == "fragile":
			got_fragile = true
	t.eq(got_fragile, false, "持有 tough 时抽不到互斥的 fragile")

	# 已持有不再抽到
	var dup: bool = false
	for i in 300:
		if ql.pick("negative", rng, ["fragile"], false) == "fragile":
			dup = true
	t.eq(dup, false, "已持有的怪癖不会再被抽到")

	# —— 战斗内落地 ——
	t.section("怪癖：战斗内数值")

	var base_c: Combatant = Combatant.new()
	base_c.setup_from_hero(db, "vestal", 0, 0)
	var hp0: int = base_c.base_hp
	var speed0: float = base_c.speed()
	var acc0: float = base_c.acc()
	var dmg0: float = base_c.damage_mult("low")
	base_c.refresh_quirks({})
	t.eq(base_c.active_quirk_count(), 0, "无怪癖时生效 buff 为 0")
	t.eq(base_c.speed(), speed0, "无怪癖时速度不变")
	t.eq(base_c.acc(), acc0, "无怪癖时命中不变")
	t.eq(base_c.damage_mult("low"), dmg0, "无怪癖时伤害倍率不变")
	t.eq(base_c.base_hp, hp0, "无怪癖时最大生命不变")

	# tough = 最大生命 +10%
	var c1: Combatant = Combatant.new()
	c1.setup_from_hero(db, "vestal", 0, 0)
	var mult: float = c1.set_quirks(["tough"], ql)
	t.near(mult, 1.1, 0.0001, "tough 的最大生命倍率 1.1")
	t.eq(c1.base_hp, int(round(float(hp0) * 1.1)), "最大生命真的涨了")
	t.eq(c1.hp, c1.base_hp, "满血进场时血量跟着涨（不是只改分母）")

	# fragile = -10%，且不能在刷新时重复乘
	var c2: Combatant = Combatant.new()
	c2.setup_from_hero(db, "vestal", 0, 0)
	c2.set_quirks(["fragile"], ql)
	var once: int = c2.base_hp
	for i in 5:
		c2.refresh_quirks({"light": 50.0})
	t.eq(c2.base_hp, once, "反复刷新不会重复缩放最大生命")
	t.eq(once, int(round(float(hp0) * 0.9)), "fragile 的最大生命是 90%")

	# 光照条件影响速度
	var c3: Combatant = Combatant.new()
	c3.setup_from_hero(db, "vestal", 0, 0)
	c3.set_quirks(["early_riser"], ql)
	c3.refresh_quirks({"light": 80.0})
	var spd_lit: float = c3.speed()
	c3.refresh_quirks({"light": 40.0})
	var spd_dark: float = c3.speed()
	t.near(spd_lit - spd_dark, 2.0, 0.0001, "早鸟在亮处比暗处快 2")

	# 首轮限定的速度加成
	var c4: Combatant = Combatant.new()
	c4.setup_from_hero(db, "vestal", 0, 0)
	c4.set_quirks(["quickdraw"], ql)
	c4.refresh_quirks({"round": 1})
	var r1: float = c4.speed()
	c4.refresh_quirks({"round": 2})
	var r2: float = c4.speed()
	t.near(r1 - r2, 4.0, 0.0001, "疾拔首轮快 4，第二轮还回去")

	# 近战限定只加近战伤害
	var c5: Combatant = Combatant.new()
	c5.setup_from_hero(db, "vestal", 0, 0)
	c5.set_quirks(["slugger"], ql)
	c5.refresh_quirks({"skill_type": "melee"})
	var m_mult: float = c5.damage_mult("low")
	c5.refresh_quirks({"skill_type": "ranged"})
	var r_mult: float = c5.damage_mult("low")
	t.near(m_mult, 1.1, 0.0001, "重击手近战伤害 ×1.1")
	t.near(r_mult, 1.0, 0.0001, "重击手远程不加工")

	# 疾病减抗：血友病 -50 流血抗性
	var c6: Combatant = Combatant.new()
	c6.setup_from_hero(db, "vestal", 0, 0)
	var bleed0: float = c6.resistance("bleed")
	c6.set_quirks(["hemophilia"], ql)
	t.near(c6.resistance("bleed"), clampf(bleed0 - 0.5, -1.0, 0.95), 0.0001,
		"血友病把流血抗性砍 50%%（%.2f → %.2f）" % [bleed0, c6.resistance("bleed")])

	# 对面有种族时的命中惩罚
	var c7: Combatant = Combatant.new()
	c7.setup_from_hero(db, "vestal", 0, 0)
	c7.set_quirks(["fear_of_eldritch"], ql)
	c7.refresh_quirks({"enemy_types": ["eldritch"]})
	var acc_fear: float = c7.acc()
	c7.refresh_quirks({"enemy_types": ["man"]})
	var acc_calm: float = c7.acc()
	t.near(acc_calm - acc_fear, 0.1, 0.0001, "惧异形对异形时命中低 10%")

	# —— 远征层：槽位 ——
	t.section("怪癖：槽位与互斥")

	var e: Expedition = _mk(db, 5150)
	e.seed_quirks({})
	var hed: String = "vestal"
	t.eq(e.quirks_of(hed).size(), 0, "开局没有怪癖")

	t.eq(e.grant_quirk(hed, "tough"), "tough", "能拿到 tough")
	t.eq(e.grant_quirk(hed, "tough"), "", "同名不能重复拿")
	t.eq(int(e.stats.get("quirk_refused_duplicate", 0)), 1, "重复被记为 duplicate")
	t.eq(e.grant_quirk(hed, "fragile"), "", "互斥的 fragile 拿不到")

	# 槽位上限必须来自 rules.json（5 正 / 5 负 / 3 病），不是代码里拍的 3/3/1。
	# M14 第一版这里是 3/3/1，是照 DD1 印象写的，数据里根本不是这个数。
	t.eq(ql.slot_cap("positive"), int(db.rules.quirk_max_positive), "正面上限来自规则表")
	t.eq(ql.slot_cap("negative"), int(db.rules.quirk_max_negative), "负面上限来自规则表")
	t.eq(ql.slot_cap("disease"), int(db.rules.quirk_max_diseases), "疾病上限来自规则表")
	t.eq(ql.slot_cap("positive"), 5, "规则表里正面是 5")
	t.eq(ql.slot_cap("disease"), 3, "规则表里疾病是 3")

	# 正面槽位填到上限（tough 已占 1 个），再多一个就拒
	var pos_ids: Array = []
	for id in ql.order:
		if ql.slot_kind(str(id)) == "positive" and not e.quirks_of(hed).has(str(id)) \
				and e.can_take_quirk(hed, str(id)):
			pos_ids.append(str(id))
		if pos_ids.size() >= 8:
			break
	t.ok(pos_ids.size() >= 4, "随机池里还有别的正面怪癖可拿（%d 个）" % pos_ids.size())
	for id in pos_ids:
		e.grant_quirk(hed, str(id))
	var cap_pos: int = ql.slot_cap("positive")
	t.eq(int(e.quirk_slots(hed)["positive"]), cap_pos, "正面槽位封顶在 %d" % cap_pos)
	t.ok(int(e.stats.get("quirk_refused_slot_full", 0)) >= 1,
		"溢出的那个被记为 slot_full（不是静默吞掉）")

	# 负面与正面互不占位：负面槽没满，能继续拿
	t.eq(e.grant_quirk(hed, "fragile") != "", false,
		"互斥仍然生效（tough 在场时 fragile 进不来）")
	var neg_got: String = ""
	for id in ql.order:
		if ql.slot_kind(str(id)) == "negative" and e.can_take_quirk(hed, str(id)):
			neg_got = e.grant_quirk(hed, str(id))
			break
	t.ok(not neg_got.is_empty(), "负面槽没被正面占满，仍能拿负面（%s）" % neg_got)

	# 疾病有自己的一组槽（规则表里是 3 个）
	var e2: Expedition = _mk(db, 5151)
	e2.disease_roll_enabled = false
	var cap_dis: int = ql.slot_cap("disease")
	t.eq(e2.contract_disease(hed, "tetanus", DdRng.new(1)), "tetanus", "染上破伤风")
	# 换不同的病来填，同名会被 duplicate 挡住（那也是对的）
	var dis_pool: Array = []
	for id in ql.order:
		if ql.is_disease(str(id)) and str(id) != "tetanus":
			dis_pool.append(str(id))
	for i in dis_pool.size():
		e2.contract_disease(hed, str(dis_pool[i]), DdRng.new(100 + i))
	t.eq(int(e2.quirk_slots(hed)["disease"]), cap_dis, "疾病槽封顶在 %d" % cap_dis)
	t.eq(e2.cure_disease(hed) != "", true, "治病清掉一个疾病")
	t.eq(int(e2.quirk_slots(hed)["disease"]), cap_dis - 1, "清完少一个")

	# purge 只清负面，不动疾病
	var e3: Expedition = _mk(db, 5152)
	e3.disease_roll_enabled = false
	e3.grant_quirk(hed, "fragile")
	e3.contract_disease(hed, "tetanus", DdRng.new(3))
	t.eq(e3.purge_negative(hed), "fragile", "purge 清掉负面怪癖")
	t.eq(e3.quirks_of(hed).has("tetanus"), true, "purge 不会顺手把病也治了")
	t.eq(e3.purge_negative(hed), "", "没有负面时 purge 不硬清")

	# 疾病抗性：0.3 抗性 → 约 70% 染上
	t.section("怪癖：疾病抗性判定")
	var hit: int = 0
	var tries: int = 200
	var er: Expedition = _mk(db, 6001)
	for i in tries:
		if not er.contract_disease(hed, "tetanus", er._curio_rng).is_empty():
			hit += 1
			er.cure_disease(hed)
	var rate: float = float(hit) / float(tries)
	t.between(rate, 0.55, 0.85, "30%% 疾病抗性下染病率约 70%%")
	t.ok(int(er.stats.get("disease_resisted", 0)) > 0, "抗性成功被计数")

	# 关掉抗性判定时必中（对照用）
	var er2: Expedition = _mk(db, 6002)
	er2.disease_roll_enabled = false
	var all_hit: bool = true
	for i in 20:
		if er2.contract_disease(hed, "tetanus", er2._curio_rng).is_empty():
			all_hit = false
		er2.cure_disease(hed)
	t.eq(all_hit, true, "关掉抗性判定后必定染病")

	# —— 接入战斗 ——
	t.section("怪癖：真的进了战斗")
	var e4: Expedition = _mk(db, 7001)
	e4.seed_quirks({hed: ["tough"]})
	var b4: Battle = e4.start_battle({"kind": "battle", "monsters": ["cultist_brawler_A"], "gear": 0})
	if b4 == null:
		t.ok(false, "战斗装配失败")
	else:
		var v: Combatant = null
		for u in b4.party:
			if u.def_id == hed:
				v = u
		t.ok(v != null, "队伍里有 vestal")
		if v != null:
			t.eq(v.quirk_ids.has("tough"), true, "怪癖从 state 进了 Combatant")
			t.ok(v.base_hp > hp0, "战斗里最大生命被 tough 撑大（%d → %d）" % [hp0, v.base_hp])

	# 关掉开关后不生效
	var e5: Expedition = _mk(db, 7002)
	e5.seed_quirks({hed: ["tough"]})
	e5.quirk_enabled = false
	var b5: Battle = e5.start_battle({"kind": "battle", "monsters": ["cultist_brawler_A"], "gear": 0})
	if b5 != null:
		var v5: Combatant = null
		for u in b5.party:
			if u.def_id == hed:
				v5 = u
		if v5 != null:
			t.eq(v5.quirk_ids.size(), 0, "关掉开关后不挂怪癖")

	# 打完一场之后怪癖必须还在。
	# state 是「整份替换」的（capture_party_state 只拍血量压力），
	# 不显式保留的话第一场打完怪癖就清零了——而这个 bug 只有在
	# 「打满两场以上」时才看得见，单场测试永远抓不到。
	var e9: Expedition = _mk(db, 7006)
	e9.seed_quirks({hed: ["tough"]})
	var b9: Battle = e9.start_battle({"kind": "battle", "monsters": ["cultist_brawler_A"], "gear": 0})
	if b9 != null:
		while not b9.is_over() and b9.round_index < Battle.MAX_ROUNDS:
			b9.run_round()
		e9.finish_battle(b9)
		t.eq(e9.quirks_of(hed).has("tough"), true, "打完一场后怪癖仍在（不被 state 覆盖）")
		t.eq(int(e9.summary().get("quirks_total", 0)), 1, "账面数得上这 1 条怪癖")
		# 更隐蔽的一条：打完一场之后，给**本来没有怪癖**的人发怪癖。
		# state 是整份替换的，替换后的行里根本没有 quirks 这个键，
		# 直接 append 会抛 "Invalid access to property or key"，
		# 而这个异常在自动流程里会被静默吞掉——看起来就是「什么都没发生」。
		var clean_hid: String = "highwayman"
		t.eq(e9.quirks_of(clean_hid).size(), 0, "highwayman 本来没有怪癖")
		t.eq(e9.grant_quirk(clean_hid, "fragile"), "fragile",
			"打完一场后仍能给没怪癖的人发怪癖（键不能丢）")

	# —— 奇物 → 怪癖 ——
	t.section("怪癖：奇物真的会给你怪癖")

	# stack_of_books 的 quirk 分支权重 4（60 个奇物里给的权重最高的一个），
	# 反复交互一定能命中。这一条测的是 M13 留下那 27 个「只解析不落地」
	# 分支里最核心的一类：quirk / disease / purge。
	var e10: Expedition = _mk(db, 8001)
	for i in 150:
		e10.resolve_curio({"kind": "curio", "curio": "stack_of_books"})
	var gained: int = int(e10.stats.get("quirks_gained", 0))
	t.ok(gained > 0, "书架给到了怪癖（%d 次）" % gained)
	var total_owned: int = 0
	for hid in e10.hero_ids:
		total_owned += e10.quirks_of(str(hid)).size()
	t.ok(total_owned > 0, "怪癖真的挂在了英雄身上（合计 %d 条）" % total_owned)
	# 槽位上限必须真的挡住：4 人 × 6 个槽 = 24，超过就会开始拒
	t.ok(int(e10.stats.get("quirk_refused_slot_full", 0)) > 0,
		"刷够次数后槽位会满并拒绝（%d 次）" % int(e10.stats.get("quirk_refused_slot_full", 0)))
	var cap_total: int = 4 * (ql.slot_cap("positive") + ql.slot_cap("negative") + ql.slot_cap("disease"))
	t.ok(total_owned <= cap_total, "总持有量不超过 4 人 × %d 槽 = %d（实际 %d）" % [
		cap_total / 4, cap_total, total_owned])

	# 疾病：beast_carcass 有 disease 分支，且要过抗性
	var e11: Expedition = _mk(db, 8002)
	for i in 150:
		e11.resolve_curio({"kind": "curio", "curio": "beast_carcass"})
	var sick: int = int(e11.stats.get("diseases_contracted", 0))
	var resisted: int = int(e11.stats.get("diseases_resisted", 0))
	t.ok(sick + resisted > 0, "尸体会带来疾病判定（染上 %d / 抗住 %d）" % [sick, resisted])
	t.ok(sick > 0, "反复接触最终会染上（%d 次）" % sick)

	# 清负面：先刷出负面，再靠 purge 清掉
	var e12: Expedition = _mk(db, 8003)
	for i in 150:
		e12.resolve_curio({"kind": "curio", "curio": "stack_of_books"})
	var neg_before: int = 0
	for hid in e12.hero_ids:
		neg_before += int(e12.quirk_slots(str(hid))["negative"])
	t.ok(neg_before > 0, "先攒出负面怪癖（%d 条）" % neg_before)
	for i in 200:
		e12.resolve_curio({"kind": "curio", "curio": "eldritch_altar"})
	t.ok(int(e12.stats.get("quirks_purged", 0)) > 0,
		"邪祭坛能清掉负面（%d 条）" % int(e12.stats.get("quirks_purged", 0)))
	var neg_after: int = 0
	for hid in e12.hero_ids:
		neg_after += int(e12.quirk_slots(str(hid))["negative"])
	t.ok(neg_after < neg_before, "清完之后负面变少（%d → %d）" % [neg_before, neg_after])

	# —— 开局自带怪癖（原版的主渠道）——
	t.section("怪癖：新英雄自带")

	var gen: Dictionary = db.hero_quirk_generation()
	t.eq(gen.size(), 15, "15 个英雄都有生成怪癖区间")
	var gv: Dictionary = gen.get("vestal", {})
	t.eq(int(gv.get("pos_min", -1)), 1, "vestal 生成时至少 1 个正面")
	t.eq(int(gv.get("pos_max", -1)), 2, "vestal 生成时至多 2 个正面")
	t.eq(int(gv.get("neg_min", -1)), 1, "vestal 生成时至少 1 个负面")
	t.eq(int(gv.get("neg_max", -1)), 2, "vestal 生成时至多 2 个负面")

	var camp6: Campaign = Campaign.new()
	camp6.setup_from_cfg(db.campaign_cfg, "user://t14_campaign6.json")
	camp6.quirk_lib = ql
	camp6.start_quirk_gen = gen
	camp6.start_rng_seed = 20261103
	camp6.new_game()
	var bad_hero: Array = []
	for hid in camp6.hero_ids():
		var pos: int = 0
		var neg: int = 0
		for q in camp6.quirks_of(str(hid)):
			if ql.slot_kind(str(q)) == "positive":
				pos += 1
			elif ql.slot_kind(str(q)) == "negative":
				neg += 1
		if pos < 1 or pos > 2 or neg < 1 or neg > 2:
			bad_hero.append("%s:+%d/-%d" % [str(hid), pos, neg])
	t.eq(bad_hero.size(), 0, "每个新英雄都是 1–2 正 + 1–2 负  %s" % str(bad_hero))

	# 同种子必须同结果（否则「这档怎么长这样」没法复现）
	var camp7: Campaign = Campaign.new()
	camp7.setup_from_cfg(db.campaign_cfg, "user://t14_campaign7.json")
	camp7.quirk_lib = ql
	camp7.start_quirk_gen = gen
	camp7.start_rng_seed = 20261103
	camp7.new_game()
	t.eq(camp7.quirks_of("vestal"), camp6.quirks_of("vestal"), "同种子开局怪癖一致")

	# 关掉开关就回到「白纸英雄」
	var camp8: Campaign = Campaign.new()
	camp8.setup_from_cfg(db.campaign_cfg, "user://t14_campaign8.json")
	camp8.quirk_lib = ql
	camp8.start_quirk_gen = gen
	camp8.start_rng_seed = 20261103
	camp8.start_quirks_enabled = false
	camp8.new_game()
	t.eq(camp8.quirks_of("vestal").size(), 0, "关掉开关后新英雄没有开局怪癖")

	# —— 元层 ——
	t.section("怪癖：跨远征留存")
	var camp: Campaign = Campaign.new()
	camp.setup_from_cfg(db.campaign_cfg, "user://t14_campaign.json")
	camp.quirk_lib = ql
	camp.new_game()
	t.eq(camp.quirks_of(hed).size(), 0, "新档没有怪癖")
	var e6: Expedition = _mk(db, 7003)
	e6.disease_roll_enabled = false
	e6.grant_quirk(hed, "tough")
	e6.contract_disease(hed, "tetanus", DdRng.new(9))
	e6.end_reason = "retreat"
	camp.settle(e6)
	t.eq(camp.quirks_of(hed).has("tough"), true, "settle 把正面怪癖写回名册")
	t.eq(camp.quirks_of(hed).has("tetanus"), true, "疾病也跟回城镇（不会自动治好）")
	var round_trip: Dictionary = camp.to_dict()
	var camp2: Campaign = Campaign.new()
	camp2.setup_from_cfg(db.campaign_cfg, "user://t14_campaign2.json")
	camp2.quirk_lib = ql
	camp2.from_dict(round_trip)
	t.eq(camp2.quirks_of(hed).has("tough"), true, "存档往返后怪癖还在")

	# 旧档没有 quirks 字段：读进来应该是空数组，而不是报错或凭空给负面
	var legacy: Dictionary = camp.to_dict()
	for hid in (legacy["roster"] as Dictionary).keys():
		(legacy["roster"][hid] as Dictionary).erase("quirks")
	var camp3: Campaign = Campaign.new()
	camp3.setup_from_cfg(db.campaign_cfg, "user://t14_campaign3.json")
	camp3.from_dict(legacy)
	t.eq(camp3.quirks_of(hed).size(), 0, "旧档缺 quirks 字段时读成空数组")

	# 开局怪癖：配置里有就带（DD1 的英雄本来就是带着怪癖入职的），
	# 但默认必须是空的——默认值一变，整套基线就跟着变。
	var cfg2: Dictionary = db.campaign_cfg.duplicate(true)
	var rs: Dictionary = (cfg2.get("roster_start", {}) as Dictionary).duplicate(true)
	rs["quirks"] = {"vestal": ["tough", "no_such_quirk"]}
	cfg2["roster_start"] = rs
	var camp4: Campaign = Campaign.new()
	camp4.setup_from_cfg(cfg2, "user://t14_campaign4.json")
	camp4.quirk_lib = ql
	camp4.new_game()
	t.eq(camp4.quirks_of("vestal"), ["tough"], "开局怪癖只带配置里存在的那个")
	t.eq(camp4.quirks_of("highwayman").size(), 0, "没配的人不带开局怪癖")
	var camp5: Campaign = Campaign.new()
	camp5.setup_from_cfg(db.campaign_cfg, "user://t14_campaign5.json")
	camp5.new_game()
	t.eq(camp5.quirks_of(hed).size(), 0, "默认配置下新档没有开局怪癖")

	# 侦察与食物通道
	t.section("怪癖：战斗外的两条通道")
	var e7: Expedition = _mk(db, 7004)
	var base_scout: float = e7.scout_chance()
	e7.seed_quirks({hed: ["ruins_explorer"]})     # in_dungeon crypts，weald 不生效
	t.near(e7.scout_chance(), base_scout, 0.0001, "地牢不符时侦察加成不生效")
	e7.set_location("crypts", "medium", 3)
	t.near(e7.scout_chance(), clampf(base_scout + 0.1, 0.0, 1.0), 0.0001,
		"进 crypts 后侦察 +10%")

	var e8: Expedition = _mk(db, 7005)
	t.near(e8.food_cost_mult(), 1.0, 0.0001, "没有暴食怪癖时食物消耗 1.0 倍")
	e8.seed_quirks({hed: ["stress_faster"]})
	t.near(e8.food_cost_mult(), 1.0, 0.0001, "压力未过 50 时暴食类条件不成立")
	for hid_s in e8.hero_ids:
		e8.state[hid_s]["stress"] = 60.0
	t.near(e8.food_cost_mult(), 0.5, 0.0001, "压力过 50 后生效，且被下限夹到 0.5 倍")


static func _buff_of(ql: QuirkLib, qid: String, idx: int) -> Dictionary:
	var b: Array = ql.get_quirk(qid).get("buffs", [])
	if idx < b.size():
		return b[idx]
	return {}


static func _mk(db: DdDb, seed_value: int) -> Expedition:
	var cfg: Dictionary = db.expedition_cfg.preset("standard")
	var loot_cfg: Dictionary = (db.campaign_cfg.get("loot", {}) as Dictionary).duplicate(true)
	loot_cfg["heirloom_names"] = db.campaign_cfg.get("heirlooms", [])
	var e: Expedition = Expedition.new()
	e.setup(db, ["man_at_arms", "highwayman", "vestal", "plague_doctor"], [],
		cfg, seed_value, "standard", loot_cfg, {})
	e.set_location("weald", "medium", 3)
	return e

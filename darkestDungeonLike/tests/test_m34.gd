class_name TestM34
extends RefCounted
## M34 同职业多人。
##
## 这一期只改一件事：**名册的 key 从「职业 id」变成「实例 id」**。
## 但它是地基——`roster`、存档、任务板、招募、解雇、战斗状态快照全都踩在上面。
##
## 命名方案是刻意的：第一个同职业的实例 id 就是职业 id 本身（`crusader`），
## 第二个起才加后缀（`crusader#2`）。这样 M0~M33 的存档、测试、
## 以及所有「按职业 id 找数据」的代码都不用改——它们的 key 本来就更等于 def。
##
## 需要钉死的四件事：
##   1. 查数据用 def、记状态用 key，这两条不能混
##   2. 两个人除了职业以外**什么都不共享**（血量、压力、等级、装备、怪癖）
##   3. 存档往返之后第二个人的身份不能丢（这条最容易静默失败）
##   4. 旧档（没有 def 字段）读进来要能正常工作

const TEST_PATH: String = "user://test_m34_unit.json"


static func run(t: TestLib, db: DdDb) -> void:
	_test_identity(t, db)
	_test_two_of_a_kind(t, db)
	_test_battle(t, db)
	_test_save(t, db)
	_cleanup()


# ------------------------------------------------------------
# 1. 身份命名
# ------------------------------------------------------------

static func _test_identity(t: TestLib, db: DdDb) -> void:
	t.section("实例 id")
	var c := Campaign.new()
	c.setup_from_cfg(db.campaign_cfg, TEST_PATH)
	c.known_heroes = db.hero_ids()
	c.skill_table = db.hero_skill_table()

	t.eq(c.def_of("crusader"), "crusader", "第一个人：实例 id 就是职业 id")
	t.eq(c.next_uid_for("crusader"), "crusader#2", "第二个人带 #2 后缀")
	t.eq(c.next_uid_for("crusader#2"), c.next_uid_for("crusader"),
		"传实例 id 和传职业 id 问的是同一件事（都是「再给这个职业一个号」）")
	t.eq(c.variant_suffix("crusader"), "", "第一个人没有后缀")
	t.eq(c.variant_suffix("crusader#2"), "Ⅱ", "第二个人后缀是 Ⅱ")
	t.eq(c.variant_suffix("crusader#3"), "Ⅲ", "第三个人后缀是 Ⅲ")

	# def_of 对不在名册里的 id 也要能推（界面会拿职业 id 直接问）
	c.roster.erase("crusader")
	t.eq(c.def_of("crusader#2"), "crusader", "名册里没有时按命名规则推 def")


# ------------------------------------------------------------
# 2. 同职业两个人
# ------------------------------------------------------------

static func _test_two_of_a_kind(t: TestLib, db: DdDb) -> void:
	t.section("同职业多人：招两个十字军")
	var c := Campaign.new()
	c.setup_from_cfg(db.campaign_cfg, TEST_PATH)
	c.known_heroes = db.hero_ids()
	c.skill_table = db.hero_skill_table()
	c.add_loot(999999, {"bust": 99, "portrait": 99, "crest": 99, "deed": 99})

	# 第一个人的装备和等级先改掉，好验证「后来的那个人不受影响」
	(c.roster["crusader"] as Dictionary)["gear"] = 3
	(c.roster["crusader"] as Dictionary)["resolve"] = 4
	(c.roster["crusader"] as Dictionary)["stress"] = 55.0

	# 让马车这周摆出十字军
	c.recruit_candidates = ["crusader"]
	t.eq(c.can_hire("crusader"), true, "已经在名册里的职业也能招（M34 解开了这条）")
	t.eq(c.hire("crusader"), true, "招进第二个十字军")
	t.eq(c.roster.has("crusader#2"), true, "实例 id 是 crusader#2")
	t.eq(c.def_of("crusader#2"), "crusader", "他的职业还是十字军")
	t.eq(c.alive_ids().has("crusader#2"), true, "出现在出战候选里")

	# 两个人各归各的
	t.eq(c.gear_of("crusader"), 3, "老人装备 3 阶")
	t.eq(c.gear_of("crusader#2"), 0, "新人装备 0 阶")
	t.eq(c.resolve_of("crusader"), 4, "老人 4 级")
	t.eq(c.resolve_of("crusader#2"), 1, "新人 1 级")
	t.near(float((c.roster["crusader"] as Dictionary)["stress"]), 55.0, 0.001,
		"老人的压力不变")
	t.near(float((c.roster["crusader#2"] as Dictionary)["stress"]), 0.0, 0.001,
		"新人压力 0")
	t.ok((c.roster["crusader"] as Dictionary).has("def"), "每个人身上都写了 def")

	# 技能表按职业查：两个人都要能拿到同一份
	var a: Array = c.skill_choices("crusader")
	var b: Array = c.skill_choices("crusader#2")
	t.ok(not a.is_empty(), "老人的可选技能非空（%d 个）" % a.size())
	t.eq(a, b, "新人的技能表和老人一模一样（按职业查）")
	t.eq(c.skill_slot_max("crusader#2"), c.skill_slot_max("crusader"),
		"技能格数也按职业算")

	# 第三个人
	t.eq(c.next_uid_for("crusader"), "crusader#3", "再招一个就是 #3")

	# 解雇其中一个人不影响另一个
	c.recruit_candidates = []
	t.eq(c.can_dismiss("crusader#2"), true, "新人可以解雇")
	c.dismiss("crusader#2")
	t.eq(c.roster.has("crusader#2"), false, "新人走了")
	t.eq(c.roster.has("crusader"), true, "老人还在")
	t.eq(c.def_of("crusader"), "crusader", "老人的身份没被牵连")


# ------------------------------------------------------------
# 3. 战斗层：两个同职业的人状态不串
# ------------------------------------------------------------

static func _test_battle(t: TestLib, db: DdDb) -> void:
	t.section("战斗层：同职业两人的状态快照")
	var ids: Array = ["crusader", "crusader#2"]
	var defs: Dictionary = {"crusader": "crusader", "crusader#2": "crusader"}
	var b := Battle.new()
	var ok: bool = b.setup(ids, [], 7, 0, 0, {}, {}, {}, defs)
	t.eq(ok, true, "两个人能一起上阵")
	t.eq(b.party.size(), 2, "场上两个人")
	t.eq((b.party[0] as Combatant).def_id, "crusader", "第一个查职业是十字军")
	t.eq((b.party[1] as Combatant).def_id, "crusader", "第二个查职业也是十字军")
	t.eq((b.party[0] as Combatant).hero_key, "crusader", "第一个的实例键")
	t.eq((b.party[1] as Combatant).hero_key, "crusader#2", "第二个的实例键")

	# 两个人在战斗里的血量/压力互相独立
	var u0: Combatant = b.party[0]
	var u1: Combatant = b.party[1]
	u0.hp = 3
	u1.hp = 11
	u0.stress = 80.0
	u1.stress = 5.0
	var snap: Dictionary = b.capture_party_state()
	t.eq(snap.size(), 2, "快照是两条，不是一条（同 def 不合并）")
	t.eq(int((snap["crusader"] as Dictionary)["hp"]), 3, "第一个的血量记在自己名下")
	t.eq(int((snap["crusader#2"] as Dictionary)["hp"]), 11, "第二个的血量记在自己名下")
	t.near(float((snap["crusader"] as Dictionary)["stress"]), 80.0, 0.001, "第一个压力 80")
	t.near(float((snap["crusader#2"] as Dictionary)["stress"]), 5.0, 0.001, "第二个压力 5")

	# 灌回去也要分开
	var b2 := Battle.new()
	b2.setup(ids, [], 9, 0, 0, {}, {}, {}, defs)
	b2.apply_party_state(snap)
	t.eq(int((b2.party[0] as Combatant).hp), 3, "回灌时第一个人还是 3 血")
	t.eq(int((b2.party[1] as Combatant).hp), 11, "回灌时第二个人还是 11 血")

	# 不传 def_by_key 时必须回到旧行为（bench 与全部历史基线靠这条）。
	# 注意这时传的必须是**职业 id**——传 `crusader#2` 会查不到数据，
	# 那正是「缺映射就该失败」而不是「猜一个」的证据。
	var b3 := Battle.new()
	var ok3: bool = b3.setup(["crusader", "vestal"], [], 7, 0, 0, {}, {}, {}, {})
	t.eq(ok3, true, "不传映射时，纯职业 id 照样能装配")
	t.eq((b3.party[0] as Combatant).def_id, "crusader", "def 等于 key")
	t.eq((b3.party[0] as Combatant).hero_key, "crusader", "实例键照旧")
	var b4 := Battle.new()
	t.eq(b4.setup(ids, [], 7, 0, 0, {}, {}, {}, {}), false,
		"不传映射却传实例 id → 装配失败（不猜）")


# ------------------------------------------------------------
# 4. 存档
# ------------------------------------------------------------

static func _test_save(t: TestLib, db: DdDb) -> void:
	t.section("存档：第二个人的身份不能丢")
	var c := Campaign.new()
	c.setup_from_cfg(db.campaign_cfg, TEST_PATH)
	c.known_heroes = db.hero_ids()
	c.add_loot(999999, {"bust": 99, "portrait": 99, "crest": 99, "deed": 99})
	c.recruit_candidates = ["crusader", "vestal"]
	c.hire("crusader")
	c.hire("vestal")
	(c.roster["crusader#2"] as Dictionary)["gear"] = 2
	(c.roster["vestal#2"] as Dictionary)["resolve"] = 3
	var n: int = c.hero_ids().size()
	t.eq(c.save(), true, "存档成功")

	var c2 := Campaign.new()
	c2.setup_from_cfg(db.campaign_cfg, TEST_PATH)
	c2.known_heroes = db.hero_ids()
	t.eq(c2.load_or_new(), true, "读档成功")
	t.eq(c2.hero_ids().size(), n, "人数一个不少（%d）" % n)
	t.eq(c2.roster.has("crusader#2"), true, "第二个十字军还在")
	t.eq(c2.def_of("crusader#2"), "crusader", "读回来 def 还对")
	t.eq(c2.gear_of("crusader#2"), 2, "第二个人的装备阶也对")
	t.eq(c2.resolve_of("vestal#2"), 3, "第二个修女的等级也对")
	t.eq(c2.variant_suffix("crusader#2"), "Ⅱ", "显示后缀仍然算得出来")

	# 旧档：没有 def 字段（M33 及以前）
	var raw: Dictionary = c2.to_dict()
	for k in (raw["roster"] as Dictionary).keys():
		(raw["roster"][k] as Dictionary).erase("def")
	var c3 := Campaign.new()
	c3.setup_from_cfg(db.campaign_cfg, TEST_PATH)
	c3.known_heroes = db.hero_ids()
	c3.from_dict(raw)
	t.eq(c3.hero_ids().size(), n, "旧档不会因为缺 def 丢人")
	t.eq(c3.def_of("crusader#2"), "crusader", "缺 def 时按命名规则推出来")
	t.eq(c3.def_of("crusader"), "crusader", "第一个人的 def 就是 key 本身")


static func _cleanup() -> void:
	if FileAccess.file_exists(TEST_PATH):
		DirAccess.remove_absolute(ProjectSettings.globalize_path(TEST_PATH))

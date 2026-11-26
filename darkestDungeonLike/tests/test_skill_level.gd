class_name TestSkillLevel
extends RefCounted
## 每技能等级（M126）与建筑升级（M131）的回归。
##
## 这两块都是「改了数字、界面看着对、其实没生效」的高危区：
## 技能等级接没接进战斗、建筑折扣有没有真的算在价上，
## 光看截图都看不出来。所以这里锁的是**数值链路**，不是界面。

const TEST_PATH: String = "user://test_skill_level_unit.json"


static func run(t: TestLib, db: DdDb) -> void:
	_cleanup()
	var c := Campaign.new()
	c.setup_from_cfg(db.campaign_cfg, TEST_PATH)

	var hid: String = str(c.alive_ids()[0])
	var def: String = c.def_of(hid)
	var h: Dictionary = db.hero(def)
	var sid: String = str((h.get("skills", [])[0] as Dictionary).get("id", ""))

	t.section("技能等级 · 初始")
	t.eq(c.skill_level_of(hid, sid), 0, "新档所有技能都是 0 级")
	t.eq(c.skill_level_of(hid, "不存在的技能"), 0, "没记录的技能按 0 级算")

	t.section("技能等级 · 决心上限")
	# 决心 1~2 → 技能只能到 1 级（索引 0）；3~4 → 2 级；依此类推
	c.roster[hid]["resolve"] = 1
	t.eq(c.skill_cap(hid), 0, "决心 1：上限索引 0（1 级）")
	c.roster[hid]["resolve"] = 2
	t.eq(c.skill_cap(hid), 1, "决心 2：放开到索引 1")
	c.roster[hid]["resolve"] = 3
	t.eq(c.skill_cap(hid), 2, "决心 3：放开到索引 2")
	# 决心上限只有 5 级（MAX_RESOLVE），写 9 会被钳住 —— 这条是 M131 抓到的：
	# 原来按原版公式算，决心拉满也只能到索引 2，5 级技能永远升不到。
	c.roster[hid]["resolve"] = Campaign.MAX_RESOLVE
	t.eq(c.skill_cap(hid), Campaign.SKILL_MAX_LEVEL, "决心拉满：技能能到 5 级")

	t.section("技能等级 · 升级要花钱")
	c.roster[hid]["resolve"] = Campaign.MAX_RESOLVE
	c.gold = 0
	t.ne(c.upgrade_skill(hid, sid), "", "没钱时被拒绝")
	t.eq(c.skill_level_of(hid, sid), 0, "被拒绝后等级不变")
	var cost0: int = c.skill_upgrade_cost(hid, sid)
	c.gold = 100000
	t.eq(c.upgrade_skill(hid, sid), "", "有钱时升级成功")
	t.eq(c.skill_level_of(hid, sid), 1, "等级 +1")
	t.eq(c.gold, 100000 - cost0, "扣了正好一份钱")
	t.gt(c.skill_upgrade_cost(hid, sid), cost0, "下一级更贵")

	t.section("技能等级 · 决心不够就拦住")
	c.roster[hid]["resolve"] = 1
	t.ne(c.upgrade_skill(hid, sid), "", "决心 1 想升 2 级 → 拒绝")
	t.eq(c.skill_level_of(hid, sid), 1, "等级没变")

	t.section("技能等级 · 满级")
	c.roster[hid]["resolve"] = Campaign.MAX_RESOLVE
	c.gold = 1000000
	for _i in 8:
		c.upgrade_skill(hid, sid)
	t.eq(c.skill_level_of(hid, sid), Campaign.SKILL_MAX_LEVEL, "最多升到 5 级")
	t.ne(c.upgrade_skill(hid, sid), "", "满级后再升被拒绝")
	t.eq(c.skill_upgrade_cost(hid, sid), -1, "满级时费用返回 -1")

	t.section("技能等级 · 越界钳制")
	c.roster[hid]["skill_levels"][sid] = 99
	t.eq(c.skill_level_of(hid, sid), Campaign.SKILL_MAX_LEVEL, "存档里的越界值被钳回上限")
	c.roster[hid]["skill_levels"][sid] = -5
	t.eq(c.skill_level_of(hid, sid), 0, "负数被钳回 0")

	t.section("建筑升级")
	t.eq(c.building_level("guild"), 0, "新档建筑都是 0 阶")
	c.gold = 0
	t.ne(c.upgrade_building("guild"), "", "没钱时被拒绝")
	c.gold = 100000
	var c0: int = c.building_upgrade_cost("guild")
	t.eq(c.upgrade_building("guild"), "", "有钱时升级成功")
	t.eq(c.building_level("guild"), 1, "阶数 +1")
	t.eq(c.gold, 100000 - c0, "扣了正好一份钱")

	t.section("建筑升级 · 公会打折")
	var full: int = int(120.0 * pow(1.9, 0.0))
	t.eq(int(120.0 * pow(1.9, 0.0) * c.skill_cost_multiplier()), full - full / 10,
		"公会 1 阶：技能升级费打 9 折")
	c.building_levels["guild"] = 3
	t.eq(int(120.0 * pow(1.9, 0.0) * c.skill_cost_multiplier()), int(full * 0.729),
		"公会 3 阶：0.9^3")

	t.section("建筑升级 · 满级")
	t.ne(c.upgrade_building("guild"), "", "满级后再升被拒绝")
	t.eq(c.building_upgrade_cost("guild"), -1, "满级时费用返回 -1")

	t.section("建筑升级 · 存档往返")
	c.save()
	var c2 := Campaign.new()
	c2.setup_from_cfg(db.campaign_cfg, TEST_PATH)
	c2.load_from(TEST_PATH)
	t.eq(c2.building_level("guild"), Campaign.BUILDING_MAX_LEVEL, "建筑阶数进了档")
	t.eq(c2.skill_level_of(hid, sid), Campaign.SKILL_MAX_LEVEL, "技能等级进了档")

	_cleanup()


static func _cleanup() -> void:
	if FileAccess.file_exists(TEST_PATH):
		DirAccess.remove_absolute(ProjectSettings.globalize_path(TEST_PATH))

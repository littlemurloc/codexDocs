class_name TestM32
extends RefCounted
## M32 任务板分区 + 任务目标层 + 清剿。
##
## 这一期最容易写错的三处，各有一组断言钉住：
##
## 1. **`board` 与 `boards[board_region]` 必须是同一个数组**。
##    复制一份的话，界面改了、存档存的还是老的，症状是
##    「换个区域再换回来，刚选的难度没了」——而且只在换区域时出现。
## 2. **旧档迁移不能把已有的四格冲掉**。`roll_board()` 会整本重抽，
##    如果读档走它，玩家每周读一次档就白刷一遍任务。
## 3. **清剿的分母在进门时固定**。边打边数分母的话，打过一间分母就少一间，
##    永远都能凑成 100%——这种 bug 不会崩，只会让任务白送。

const TEST_PATH: String = "user://test_m32_unit.json"
const HEROES: Array = ["crusader", "highwayman", "vestal", "plague_doctor"]


static func run(t: TestLib, db: DdDb) -> void:
	_test_parse(t, db)
	_test_met(t)
	_test_boards(t, db)
	_test_cleanse(t, db)
	_cleanup()


# ------------------------------------------------------------
# 1. 解析：quests.json → 目标
# ------------------------------------------------------------

static func _test_parse(t: TestLib, db: DdDb) -> void:
	t.section("任务定义：从 quests.json 解析")
	t.ok(not db.quests.is_empty(), "quests.json 被加载了（M0 抽出来，M32 才有人读）")
	var types_block: Dictionary = db.quests.get("quest.types", {})
	t.eq((types_block.get("types", []) as Array).size(), 6, "六种任务类型")
	t.eq((types_block.get("goals", []) as Array).size(), 48, "四十八个目标定义")

	var ex: Dictionary = QuestGoal.parse(db.quests, "explore", "weald")
	t.eq(str(ex["kind"]), QuestGoal.KIND_REACH, "探索 → 走到终点")
	t.eq(bool(ex["supported"]), true, "探索可结算")

	var kb: Dictionary = QuestGoal.parse(db.quests, "kill_boss", "cove")
	t.eq(str(kb["kind"]), QuestGoal.KIND_BOSS, "首领 → 杀首领")
	t.eq(int(kb["amount"]), 1, "首领目标数量 1")
	t.eq(bool(kb["supported"]), true, "首领可结算")

	# 清剿：数据里是 `battle_all_rooms`，percentage 1
	var cl: Dictionary = QuestGoal.parse(db.quests, "cleanse", "warrens")
	t.eq(str(cl["kind"]), QuestGoal.KIND_BATTLE, "清剿 → 清光战斗房")
	t.near(float(cl["percentage"]), 1.0, 0.0001, "清剿要求 100% 的战斗房")
	t.eq(str(cl["goal_id"]), "battle_all_rooms", "命中 battle_all_rooms")
	t.eq(bool(cl["supported"]), true, "清剿可结算")

	# 收集 / 激活：不给奇物表时解析不出目标，所以标成不支持——
	# 任务板只从可结算的类型里抽卡。M33 起会传奇物表进来，那时才为真。
	for qt in ["gather", "activate"]:
		var g: Dictionary = QuestGoal.parse(db.quests, qt, "cove")
		t.eq(bool(g["supported"]), false, "%s 没有奇物表时解析不出目标" % qt)
	var inv: Dictionary = QuestGoal.parse(db.quests, "inventory_activate", "cove",
		db.curio_lib.curios)
	t.eq(bool(inv["supported"]), false, "inventory_activate 还要任务道具，仍然没接")
	# 区域变体：同一类型在不同区域指向不同奇物
	var gw: Dictionary = QuestGoal.parse(db.quests, "gather", "weald")
	t.eq(str(gw["curio_raw"]), "chirurgeons_satchel", "weald 的收集目标是外科医生的包")
	t.eq(str(gw["item"]), "medicines", "要收的物品是 medicines")
	t.eq(int(gw["amount"]), 3, "数量 3（来自 item.amount）")
	var gc: Dictionary = QuestGoal.parse(db.quests, "gather", "cove")
	t.eq(str(gc["curio_raw"]), "shipment_crates", "cove 的收集目标是货箱（区域变体生效）")
	t.ok(str(gw["curio_raw"]) != str(gc["curio_raw"]), "两个区域的目标奇物不同")

	# 表里没有的类型不能变成「永远结算不了」的卡
	var junk: Dictionary = QuestGoal.parse(db.quests, "no_such_type", "weald")
	t.eq(bool(junk["supported"]), false, "未知任务类型标为不支持")


# ------------------------------------------------------------
# 2. 判据
# ------------------------------------------------------------

static func _test_met(t: TestLib) -> void:
	t.section("任务判据")

	var reach: Dictionary = {"kind": QuestGoal.KIND_REACH, "amount": 0, "percentage": 0.0}
	t.eq(QuestGoal.met(reach, {"at_goal": false}), false, "没到终点不算完成")
	t.eq(QuestGoal.met(reach, {"at_goal": true}), true, "到了终点就算完成")

	var boss: Dictionary = {"kind": QuestGoal.KIND_BOSS, "amount": 1, "percentage": 0.0}
	t.eq(QuestGoal.met(boss, {"boss_killed": false}), false, "首领没死不算完成")
	t.eq(QuestGoal.met(boss, {"boss_killed": true}), true, "首领死了算完成")

	# 清剿：比例目标乘总数再向上取整
	var cl: Dictionary = {"kind": QuestGoal.KIND_BATTLE, "amount": 0, "percentage": 1.0}
	t.eq(QuestGoal.met(cl, {"battles_total": 4, "battles_cleared": 3}), false, "4 场清 3 场不算完成")
	t.eq(QuestGoal.met(cl, {"battles_total": 4, "battles_cleared": 4}), true, "4 场清 4 场完成")
	# 图上本来没仗 → 自动成立。不写这条的话，一张没有战斗房的地图
	# 会让清剿任务永远无法完成（分母 0，玩家怎么打都差一场）。
	t.eq(QuestGoal.met(cl, {"battles_total": 0, "battles_cleared": 0}), true,
		"图上没有战斗房时清剿自动成立")

	var half: Dictionary = {"kind": QuestGoal.KIND_BATTLE, "amount": 0, "percentage": 0.5}
	t.eq(QuestGoal.met(half, {"battles_total": 5, "battles_cleared": 2}), false, "50% of 5 = 3，清 2 不够")
	t.eq(QuestGoal.met(half, {"battles_total": 5, "battles_cleared": 3}), true, "50% of 5 向上取整到 3")
	var pr: Vector2i = QuestGoal.progress(half, {"battles_total": 5, "battles_cleared": 2})
	t.eq(pr, Vector2i(2, 3), "进度报 2/3（和判据同一个分母）")

	# 不支持的类型不能判成完成，也不能判成失败（M33 改）：判不了就不罚，
	# 否则一张解析失败的任务卡会把整趟远征钉成「未完成」。
	var gather: Dictionary = {"kind": QuestGoal.KIND_GATHER, "amount": 3,
		"percentage": 0.0, "supported": false}
	t.eq(QuestGoal.met(gather, {"gathered": 3}), true, "解析不出来的收集目标不判失败")
	var gather_ok: Dictionary = {"kind": QuestGoal.KIND_GATHER, "amount": 3,
		"percentage": 0.0, "supported": true}
	t.eq(QuestGoal.met(gather_ok, {"gathered": 2}), false, "能解析时 2/3 不算完成")
	t.eq(QuestGoal.met(gather_ok, {"gathered": 3}), true, "能解析时 3/3 完成")


# ------------------------------------------------------------
# 3. 分区任务板
# ------------------------------------------------------------

static func _test_boards(t: TestLib, db: DdDb) -> void:
	t.section("任务板：四个区域各一块")
	var c := Campaign.new()
	c.setup_from_cfg(db.campaign_cfg, TEST_PATH)

	t.eq(Campaign.BOARD_REGIONS.size(), 4, "四个区域")
	t.eq(c.boards.size(), 4, "四块板子")
	t.eq(c.board_region, "weald", "默认区域是 weald")
	t.eq(c.board_for("cove").size(), Campaign.BOARD_SLOTS.size(), "每个区域都是四格")

	# 每区的槽位形状必须和配置表一致——这条防的是「抽卡时用错区域表」
	var mismatch: int = 0
	for region in Campaign.BOARD_REGIONS:
		var rgn: String = str(region)
		var expect: Array = Campaign.BOARD_SLOTS_BY_REGION[rgn]
		var got: Array = c.board_for(rgn)
		for i in expect.size():
			var e: Array = expect[i]
			var g: Dictionary = got[i]
			if str(g["size"]) != str(e[0]) or str(g["quest"]) != str(e[1]):
				mismatch += 1
			if str(g.get("region", "")) != rgn:
				mismatch += 1
	t.eq(mismatch, 0, "16 张卡的尺寸/类型/区域全部对得上配置表")

	# 每张卡的任务类型都必须真的能结算
	var bad_quest: int = 0
	for region2 in Campaign.BOARD_REGIONS:
		for slot in c.board_for(str(region2)):
			if not QuestGoal.supported(str((slot as Dictionary).get("quest", ""))):
				bad_quest += 1
	t.eq(bad_quest, 0, "板上没有一张结算不了的任务卡")

	# 清剿必须真的出现在板上，否则这一期等于没做
	var cleanse_n: int = 0
	for region3 in Campaign.BOARD_REGIONS:
		for slot2 in c.board_for(str(region3)):
			if str((slot2 as Dictionary).get("quest", "")) == "cleanse":
				cleanse_n += 1
	t.ok(cleanse_n >= 4, "清剿在四块板子上都有位置（共 %d 张）" % cleanse_n)

	# 保底是**区域级**的：每一块板子都至少有一格给名册里最弱的人。
	# 只在「四块加起来有一格」的话，玩家切到另一个区域就没活可接。
	var no_floor: int = 0
	for region4 in Campaign.BOARD_REGIONS:
		var has_floor: bool = false
		for slot3 in c.board_for(str(region4)):
			if int((slot3 as Dictionary).get("level", 0)) == c.board_floor_level():
				has_floor = true
		if not has_floor:
			no_floor += 1
	t.eq(no_floor, 0, "每块板子都有一格保底档")

	# 序号最多的那一格：换区域之后 `board` 必须指向新区域那份，
	# 而且**是同一个数组对象**，不是复制品。
	c.select_board_region("cove")
	t.eq(c.board_region, "cove", "切到 cove")
	t.eq(c.board, c.board_for("cove"), "board 指向 cove 那份")
	var before: int = int((c.board[0] as Dictionary)["level"])
	(c.board_for("cove")[0] as Dictionary)["level"] = 3
	t.eq(int((c.board[0] as Dictionary)["level"]), 3,
		"改 boards 里的字典，board 立刻能看到（同一份数据）")
	(c.board[0] as Dictionary)["level"] = before
	c.select_board_region("nope")
	t.eq(c.board_region, "cove", "未知区域被忽略，不会把 board 变空")

	# 存档往返：四块板子逐槽保留
	c.select_board_region("weald")
	c.roll_board()
	var snap: Dictionary = c.boards.duplicate(true)
	t.eq(c.save(), true, "存档成功")
	var c2 := Campaign.new()
	c2.setup_from_cfg(db.campaign_cfg, TEST_PATH)
	t.eq(c2.load_or_new(), true, "读档成功")
	t.eq(c2.boards, snap, "四块板子逐槽一致")
	t.eq(c2.board_region, "weald", "当前区域也存下来了")

	# 旧档兼容：只有单块 `board` 的老存档。
	# 要求是「把那四格救回来，其余三区现抽」——不能整本重抽。
	var raw: Dictionary = c2.to_dict()
	raw.erase("boards")
	var kept: Array = (raw["board"] as Array).duplicate(true)
	var c3 := Campaign.new()
	c3.setup_from_cfg(db.campaign_cfg, TEST_PATH)
	c3.from_dict(raw)
	t.eq(c3.boards.size(), 4, "旧档补齐成四块")
	t.eq(c3.board_for(str(raw.get("board_region", "weald"))), kept,
		"旧档那四格被原样救回来（读档不重抽）")
	var all_have_level: bool = true
	for region5 in Campaign.BOARD_REGIONS:
		for slot4 in c3.board_for(str(region5)):
			if not (slot4 as Dictionary).has("level"):
				all_have_level = false
	t.eq(all_have_level, true, "补出来的三块也有等级")

	# 存了坏数据不能变成废卡：尺寸不认识 / 类型不支持 → 那一块重抽
	var dirty: Dictionary = c2.to_dict()
	(dirty["boards"]["crypts"] as Array)[0] = {"size": "huge", "quest": "explore", "level": 1}
	(dirty["boards"]["crypts"] as Array)[1] = {"size": "short", "quest": "gather", "level": 1}
	var c4 := Campaign.new()
	c4.setup_from_cfg(db.campaign_cfg, TEST_PATH)
	c4.from_dict(dirty)
	t.eq(c4.board_for("crypts").size(), Campaign.BOARD_SLOTS.size(), "坏档被重抽成四格")
	var crypts_ok: bool = true
	for slot5 in c4.board_for("crypts"):
		var q5: String = str((slot5 as Dictionary).get("quest", ""))
		var s5: String = str((slot5 as Dictionary).get("size", ""))
		if q5 == "gather" or (s5 != "short" and s5 != "medium" and s5 != "long"):
			crypts_ok = false
	t.eq(crypts_ok, true, "重抽之后没有未知尺寸、没有不支持的类型")
	_cleanup()


# ------------------------------------------------------------
# 4. 清剿真的会「清不完就走 = 未完成」
# ------------------------------------------------------------

static func _test_cleanse(t: TestLib, db: DdDb) -> void:
	t.section("清剿任务：分母、计数、结算")
	# 清剿的地图参数比探索多战斗房——这是 dungeons.json 自己的差别，
	# 不是我们编的。这条挂了说明 map_for 没按 quest_type 取表。
	var clean_mp: Dictionary = db.map_for("weald", "medium", "cleanse")
	var expl_mp: Dictionary = db.map_for("weald", "medium", "explore")
	t.ok(not clean_mp.is_empty(), "weald/medium/cleanse 有地图参数")
	t.ok(int((clean_mp.get("total_room_battles", [0, 0]) as Array)[1])
		>= int((expl_mp.get("total_room_battles", [0, 0]) as Array)[1]),
		"清剿的战斗房上限不低于探索（%s vs %s）" % [
			str(clean_mp.get("total_room_battles")), str(expl_mp.get("total_room_battles"))])

	var m: Dictionary = MapGen.build(db, "weald", "medium", 3, DdRng.new(4242), "cleanse")
	if m.is_empty():
		t.ok(false, "清剿地图能生成")
		return
	var preset: Dictionary = db.expedition_cfg.preset("standard")
	var e := Expedition.new()
	e.setup(db, HEROES, [], preset, 4242, "standard", {}, {})
	e.set_location("weald", "medium", 3, "cleanse")
	e.enter_map(m)

	t.eq(e.quest_type, "cleanse", "任务类型记在远征层")
	t.eq(str(e.quest_goal.get("kind", "")), QuestGoal.KIND_BATTLE, "目标是清战斗房")
	var total: int = int(e.stats["quest_battles_total"])
	t.eq(total, int((m["content"] as Dictionary).get("battles", 0)),
		"分母 = 图上战斗房数（%d）" % total)
	t.eq(int(e.stats["quest_battles_cleared"]), 0, "开局一场没清")
	t.eq(e.quest_met(), total == 0, "开局只有「图上没仗」时才算完成")

	# 分母固定：反复进门不能把它改成「剩下的」
	var total_before: int = total
	e.enter_map(m)
	t.eq(int(e.stats["quest_battles_total"]), total_before, "重进地图分母不变（不能边打边缩）")

	# 清到差一场：不能走
	if total > 0:
		e.stats["quest_battles_cleared"] = total - 1
		t.eq(e.quest_met(), false, "清 %d/%d 场不算完成" % [total - 1, total])
		e._end("complete")
		t.eq(e.end_reason, "incomplete", "清剿没清完就走 → 任务未完成")
	# 清完：能走
	var e2 := Expedition.new()
	e2.setup(db, HEROES, [], preset, 4242, "standard", {}, {})
	e2.set_location("weald", "medium", 3, "cleanse")
	e2.enter_map(m)
	e2.stats["quest_battles_cleared"] = int(e2.stats["quest_battles_total"])
	e2.current_room = int(m["goal"])
	e2._end("complete")
	t.eq(e2.end_reason, "complete", "清光之后走到出口 → 完成")

	# 探索任务的判据不能被这一期带偏：路线模式（没有房间）仍然照旧完成。
	# bench 全部走这条路，破了它 M3 以来所有数字同时作废。
	var e3 := Expedition.new()
	e3.setup(db, HEROES, [], preset, 4242, "standard", {}, {})
	e3.set_location("weald", "medium", 3, "explore")
	e3._end("complete")
	t.eq(e3.end_reason, "complete", "路线模式下的探索任务不受房间判据影响")

	# 汇总里要能把两种任务分开统计
	var s: Dictionary = e2.summary()
	t.eq(str(s.get("quest_type", "")), "cleanse", "summary 带任务类型")
	t.eq(bool(s.get("quest_met", false)), true, "summary 带完成判据")
	t.eq(int(s.get("quest_battles_total", -1)), int(e2.stats["quest_battles_total"]),
		"summary 带分母")


static func _cleanup() -> void:
	for p in [TEST_PATH]:
		if FileAccess.file_exists(p):
			DirAccess.remove_absolute(ProjectSettings.globalize_path(p))

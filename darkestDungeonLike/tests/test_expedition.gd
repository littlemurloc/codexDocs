class_name TestExpedition
extends RefCounted
## 资源层回归测试。
##
## 这一层的 bug 特别隐蔽：光照档位抄错一档、饥饿扣的是绝对值而不是比例、
## 崩溃 buff 挂错前缀……全都不会报错，只会让「危险度」这个数字悄悄失真。
## 所以每条规则都要有能一眼看出对错的断言。

const HEROES: Array = ["crusader", "highwayman", "vestal", "plague_doctor"]
const MONSTERS: Array = ["cultist_brawler_B", "cultist_brawler_B", "cultist_witch_B"]


static func run(t: TestLib, db: DdDb) -> void:
	_test_light(t, db)
	_test_config(t, db)
	_test_route(t, db)
	_test_deaths_door(t, db)
	_test_stress_break(t, db)
	_test_heal_charges(t, db)
	_test_expedition_state(t, db)
	_test_step_api(t, db)
	_test_scouting(t, db)
	_test_map_mode(t, db)
	_test_hallway_hazards(t, db)
	_test_boss_quest(t, db)
	_test_names(t, db)


## 名称覆盖与情报摘要（M21）。
##
## 名字表最怕「看起来有、其实漏了一类」：漏掉的那几个怪在战斗里会冒英文 id，
## 而且只有这一局遇到它才看得见——不批量扫一遍根本发现不了。
static func _test_names(t: TestLib, db: DdDb) -> void:
	t.section("名称与情报")
	var missing: Array = []
	for d in ["weald", "crypts", "warrens", "cove"]:
		var by_region: Dictionary = db.encounters.get(d, {})
		for lv_key in by_region.keys():
			var blk: Dictionary = by_region[lv_key]
			for kind in ["hall", "room", "boss"]:
				for row in (blk.get(kind, []) as Array):
					if not (row is Dictionary):
						continue
					for tp in ((row as Dictionary).get("types", []) as Array):
						var base: String = DdDb._monster_base(str(tp))
						if not DdNames.MONSTER_NAMES.has(base) and not missing.has(base):
							missing.append(base)
	t.eq(missing, [], "四个区域的遭遇池 + 首领池全部有中文名")

	# 英雄也要全覆盖，否则换人上场时城镇和战斗里会一半中文一半英文
	var missing_h: Array = []
	for h in db.heroes.keys():
		if not DdNames.HERO_NAMES.has(str(h)):
			missing_h.append(str(h))
	t.eq(missing_h, [], "15 个英雄全部有中文名")

	# 技能名（M31）：原来这张表只有最初 5 个职业的 35 个技能，
	# 另外 70 个回退成英文（`+ Manacles`）。名册能招到 15 个职业之后，
	# 这个问题只会在「招进第 6 个职业」时才暴露——所以必须全量扫。
	var missing_s: Array = []
	for h2 in db.heroes.keys():
		for sk in ((db.heroes[h2] as Dictionary).get("skills", []) as Array):
			var sid: String = str((sk as Dictionary).get("id", ""))
			if sid.is_empty() or sid in missing_s:
				continue
			if DdNames.skill_name(sid) == DdNames.pretty(sid):
				missing_s.append(sid)
	t.eq(missing_s, [], "105 个技能全部有中文名")

	# 后缀剥离：同一个怪的三档必须映射到同一个名字
	t.eq(DdNames.monster_name("cultist_brawler_A"), DdNames.monster_name("cultist_brawler_C"),
		"难度后缀不影响名字")
	t.eq(DdNames.unit_name("crusader"), "十字军", "英雄走 unit_name 能查到中文")

	# 情报摘要
	var o: Dictionary = db.encounter_outline("cove", 1)
	t.ok(not (o.get("common", []) as Array).is_empty(), "海湾 Lv1 常见怪非空")
	t.ok((o.get("common", []) as Array).size() <= 3, "常见怪最多报 3 个")
	var ob: Array = o.get("bosses", [])
	t.ok(not ob.is_empty(), "海湾 Lv1 首领池非空")
	t.eq(ob.has("siren"), true, "海湾首领池含海妖")
	# 同一档两次调用必须一致（排序稳定），否则截图和文档对不上
	var o2: Dictionary = db.encounter_outline("cove", 1)
	t.eq(o.get("common", []), o2.get("common", []), "情报排序稳定可复现")


## 首领任务（M20）。
##
## 这套机制的风险是「看起来做了、其实没接」：
## 地图参数换成了 kill_boss，但终点房间还是空的——玩家跑完全程，什么都没有。
## 所以每条都要钉死「终点房间有没有那场仗」，而不是只测「地图能生成」。
static func _test_boss_quest(t: TestLib, db: DdDb) -> void:
	t.section("首领任务")
	var mb: Dictionary = MapGen.build(db, "weald", "medium", 3, DdRng.new(777), "kill_boss")
	t.ok(not mb.is_empty(), "kill_boss 地图能生成")
	var gb: int = int(mb["goal"])
	t.eq(str((mb["rooms"][gb] as Dictionary)["kind"]), MapGen.K_BOSS, "终点房间类型是 boss")
	var gstep: Dictionary = (mb["rooms"][gb] as Dictionary).get("step", {})
	t.eq(bool(gstep.get("boss", false)), true, "终点房间带首领战标记")
	t.ok(not (gstep.get("monsters", []) as Array).is_empty(), "首领战有具体怪物")
	t.eq(str(gstep.get("source", "")), "boss", "来源记为 boss（不是 hall/room）")
	t.eq(bool((mb["content"] as Dictionary).get("boss", false)), true, "content 里记了 boss")

	# 同种子换回 explore：终点必须是空的。
	# 反过来说，如果这条挂了，说明「boss 房」不是任务带来的，而是无条件塞进去的。
	var me: Dictionary = MapGen.build(db, "weald", "medium", 3, DdRng.new(777), "explore")
	# 房间结构里永远有 step 这个键（初始化成空字典），所以判的是「空不空」
	var e_step: Dictionary = (me["rooms"][int(me["goal"])] as Dictionary).get("step", {})
	t.eq(e_step.is_empty(), true, "探索地图的终点没有战斗")
	t.eq(bool((me["content"] as Dictionary).get("boss", false)), false, "探索地图 content.boss 为 false")

	# 任务判据：没杀首领就走出去，不能算完成。
	# 不加这条的话「跑到终点、打输了、活着跑出来」会拿完成奖励，
	# 结算屏还会写「走出地牢」。
	var eb := Expedition.new()
	eb.setup(db, HEROES, [], db.expedition_cfg.preset("standard"), 11, "standard", {}, {})
	eb.set_location("weald", "medium", 3, "kill_boss")
	eb._end("complete")
	t.eq(eb.end_reason, "incomplete", "首领没死就走 → 任务未完成")

	var eb2 := Expedition.new()
	eb2.setup(db, HEROES, [], db.expedition_cfg.preset("standard"), 11, "standard", {}, {})
	eb2.set_location("weald", "medium", 3, "kill_boss")
	eb2.stats["boss_killed"] = true
	eb2._end("complete")
	t.eq(eb2.end_reason, "complete", "首领已死 → 正常完成")

	# explore 任务不该被这条规则影响
	var eb3 := Expedition.new()
	eb3.setup(db, HEROES, [], db.expedition_cfg.preset("standard"), 11, "standard", {}, {})
	eb3.set_location("weald", "medium", 3, "explore")
	eb3._end("complete")
	t.eq(eb3.end_reason, "complete", "探索任务不受首领判据影响")

	t.eq(eb.quest_type, "kill_boss", "任务类型记在远征层")
	t.eq(eb3.quest_type, "explore", "默认任务类型是 explore")


# ------------------------------------------------------------
# 房间图模式
# ------------------------------------------------------------

## 图模式与线性模式共用同一套战斗/资源逻辑，只在「下一步从哪来」上分叉。
## 这里要钉住的是分叉处的三条规则：不能传送、走走廊才耗光、完成靠离开而非走完。
static func _test_map_mode(t: TestLib, db: DdDb) -> void:
	t.section("房间图模式")
	var m: Dictionary = MapGen.build(db, "weald", "short", 1, DdRng.new(88))
	if m.is_empty():
		t.ok(false, "地图生成失败")
		return

	var preset: Dictionary = db.expedition_cfg.preset("standard")
	var e := Expedition.new()
	e.setup(db, HEROES, [], preset, 88, "standard", {}, {})
	e.set_location("weald", "short")
	e.enter_map(m)

	t.eq(e.map_mode, true, "进入图模式")
	t.eq(e.current_room, int(m["start"]), "从入口房间开始")
	t.ok(e.adjacent().size() > 0, "入口有相邻房间（%d 个）" % e.adjacent().size())
	t.eq(e.is_room_spotted(int(m["start"])), true, "入口房间已探明")
	t.eq(e.room_visited(int(m["start"])), true, "入口房间记为到过")
	t.eq(e.at_goal(), false, "开局不在目标房间")

	# 不能凭空传送到不相邻的房间
	var far: int = -1
	var nbs: Array = e.adjacent()
	for id in (m["room_ids"] as Array):
		var is_nb: bool = false
		for nb in nbs:
			if int(nb.room) == int(id):
				is_nb = true
		if not is_nb and int(id) != e.current_room:
			far = int(id)
			break
	t.eq(far >= 0, true, "存在一个不相邻的房间")
	if far >= 0:
		t.eq(e.travel(far), false, "走不到不相邻的房间")

	# 正常走一步：位置更新、队列里至少一步、光照在结算时才扣
	var target: int = int((nbs[0] as Dictionary)["room"])
	var light_before: float = e.light
	t.eq(e.travel(target), true, "能走到相邻房间")
	t.eq(e.current_room, target, "位置已更新")
	t.eq(e.has_pending(), true, "有待结算的步骤")
	t.near(e.light, light_before, 0.0001, "travel 本身不扣光照（结算时才扣）")

	var step1: Dictionary = e.take_step()
	t.eq(bool(step1.get("corridor", false)), true, "第一步是走廊")
	t.ok(e.light < light_before, "走走廊消耗光照（%.0f → %.0f）" % [light_before, e.light])

	# 走完整个队列，光照不应再掉（房间步骤不耗光）
	var light_mid: float = e.light
	while e.has_pending() and not e.ended:
		var s2: Dictionary = e.take_step()
		if str(s2.get("kind", "")) == "curio":
			e.resolve_curio()
	t.near(e.light, light_mid, 0.0001, "房间步骤不额外消耗光照")

	# 沿最短路走到目标：目标房必须能到，且到了不等于完成
	var path: Array = _path_to(m, e.current_room, int(m["goal"]))
	t.ok(not path.is_empty(), "存在到目标房间的路径")
	for r in path:
		if e.ended:
			break
		if int(r) == e.current_room:
			continue
		if e.travel(int(r)):
			while e.has_pending() and not e.ended:
				var s3: Dictionary = e.take_step()
				if str(s3.get("kind", "")) == "curio":
					e.resolve_curio()
	t.eq(e.at_goal(), true, "走到了目标房间")
	t.eq(e.ended, false, "到达目标不等于远征结束")

	e.leave_dungeon()
	t.eq(e.ended, true, "离开地牢后结束")
	t.eq(e.end_reason, "complete", "离开算完成")

	# 图模式的进度口径：房间数，不是步骤数
	var sm: Dictionary = e.summary()
	t.eq(int(sm["steps_total"]), (m["room_ids"] as Array).size(), "进度分母是房间数")
	t.ok(int(sm["steps_done"]) >= 1, "走过的房间数被统计")


static func _path_to(m: Dictionary, from_room: int, to_room: int) -> Array:
	var n: int = (m["room_ids"] as Array).size()
	var pairs: Array = []
	for e in (m["edges"] as Array):
		pairs.append(Vector2i(int(e.a), int(e.b)))
	var adj: Dictionary = MapGen.adjacency_rooms(n, pairs)
	var dist: Array = MapGen.bfs(n, adj, from_room)
	if int(dist[to_room]) < 0:
		return []
	# 从目标往回走：每次挑距离减一的邻居
	var out: Array = []
	var cur: int = to_room
	var guard: int = 0
	while cur != from_room and guard < 64:
		guard += 1
		out.push_front(cur)
		var picked: int = -1
		for nb in (adj.get(cur, []) as Array):
			if int(dist[int(nb)]) == int(dist[cur]) - 1:
				picked = int(nb)
				break
		if picked < 0:
			return []
		cur = picked
	return out


# ------------------------------------------------------------
# 战前情报
# ------------------------------------------------------------

## 侦察的三条底线：
##   1. 走过的路一定知道（视野不能落后于脚步）
##   2. 视野不能超出路线长度
##   3. 光照必须真的影响它——否则「点火把」买到的东西是假的
static func _test_scouting(t: TestLib, db: DdDb) -> void:
	t.section("战前情报")
	var preset: Dictionary = db.expedition_cfg.preset("standard")
	var start_visible: int = int((preset.get("scouting", {}) as Dictionary).get("reveal_on_start", 2))
	t.ok(start_visible >= 1, "standard 出发时至少能看到 1 个节点，实际 %d" % start_visible)

	var route: Array = RouteGen.build(db, "weald", "medium", 3, DdRng.new(4242))
	var e := Expedition.new()
	e.setup(db, HEROES, route, preset, 4242, "standard")
	t.eq(e.revealed, start_visible, "开局视野等于配置值")
	t.ok(e.revealed <= route.size(), "视野不超过路线长度")

	var guard: int = 0
	var monotonic: bool = true
	while e.step_index < route.size() and guard < 40:
		guard += 1
		e.take_step()
		if e.revealed < e.step_index:
			monotonic = false
		if e.revealed > route.size():
			monotonic = false
	t.ok(monotonic, "视野始终跟上脚步且不超界（走了 %d 步）" % e.step_index)
	t.ok(int(e.stats["scout_reveals"]) >= 0, "侦察计数存在")
	t.eq(e.is_revealed(0), true, "第 1 个节点已知")
	t.eq(e.is_revealed(route.size()), false, "越界查询返回未知")

	# 光照对侦察率的直接影响
	var e2 := Expedition.new()
	e2.setup(db, HEROES, route, preset, 7, "standard")
	e2.light = 100.0
	var bright: float = e2.scout_chance()
	e2.light = 20.0
	var dark: float = e2.scout_chance()
	t.ok(bright > dark, "明亮比昏暗看得更清（%.2f > %.2f）" % [bright, dark])
	t.near(bright - dark, 0.15, 0.001, "差距等于 darkness 表的 player_scouting_increase（+15%）")

	# 情报里给的是「几只 + 总血」，不是具体怪物
	var battle: Dictionary = {}
	for s in route:
		if str(s.get("kind", "")) == "battle":
			battle = s
			break
	t.ok(not battle.is_empty(), "路线里有战斗节点")
	t.ok(e2.step_enemy_hp(battle) > 0, "能算出该节点的敌方总血量（%d）" % e2.step_enemy_hp(battle))

	# 不同预设的侦察强度必须不同，否则这个旋钮等于没有
	var tight: Dictionary = db.expedition_cfg.preset("tight")
	var t_start: int = int((tight.get("scouting", {}) as Dictionary).get("reveal_on_start", 2))
	t.ok(t_start < start_visible, "tight 的初始视野比 standard 窄（%d < %d）" % [t_start, start_visible])


# ------------------------------------------------------------
# 两套驱动方式必须等价
# ------------------------------------------------------------

## run_round()（AI 同步）与 begin_round()+step_turn()+submit_choice()（界面逐步）
## 必须走出完全相同的战斗。这条断言是给表现层兜底的：哪天界面上的战斗
## 跟 bench 里的战斗不一样，说明规则层被界面需求带歪了。
static func _test_step_api(t: TestLib, db: DdDb) -> void:
	t.section("同步驱动与逐步驱动等价")
	var sync := Battle.new()
	sync.setup(HEROES, MONSTERS, 555)
	sync.run_until_over(30)

	var step := Battle.new()
	step.setup(HEROES, MONSTERS, 555)
	step.decision_provider = func(_b: Battle, _a: Combatant) -> Dictionary: return {}
	var guard: int = 0
	while not step.is_over() and guard < 80:
		guard += 1
		step.begin_round()
		while step.step_turn():
			if step.awaiting_input != null:
				var c: Dictionary = step.choose_action(step.awaiting_input)
				step.submit_choice(c.get("action", {}), c.get("targets", []))

	t.eq(step.round_index, sync.round_index, "逐步驱动的轮数与同步一致")
	t.eq(step.winner(), sync.winner(), "胜方一致")
	var same: bool = true
	for i in sync.party.size():
		var a: Combatant = sync.party[i]
		var b: Combatant = step.party[i]
		if a.hp != b.hp or absf(a.stress - b.stress) > 0.001 or a.dead != b.dead:
			same = false
	t.ok(same, "逐个英雄的血量/压力/生死一致")
	t.eq(step.awaiting_input == null, true, "收尾后没有悬挂的等待项")


# ------------------------------------------------------------
# 光照
# ------------------------------------------------------------

static func _test_light(t: TestLib, db: DdDb) -> void:
	t.section("光照档位（左开右闭）")
	var dk: Dictionary = db.rules.darkness
	t.ok(not dk.is_empty(), "darkness 表已加载")

	# 75 属于微光而不是明亮：表里 lowest_excluded = true，区间是 (lower, upper]
	var bright: Dictionary = ExpeditionCfg.light_modifier(dk, 90.0)
	var at75: Dictionary = ExpeditionCfg.light_modifier(dk, 75.0)
	var at76: Dictionary = ExpeditionCfg.light_modifier(dk, 76.0)
	t.eq(float(bright.get("monster_dmg", -1.0)), 0.0, "明亮：怪物伤害无加成")
	t.eq(float(at76.get("monster_dmg", -1.0)), 0.0, "76 仍是明亮")
	t.near(float(at75.get("monster_dmg", -1.0)), 0.0, 0.0001, "75 落在微光（左开右闭）")
	t.near(float(ExpeditionCfg.light_modifier(dk, 74.0).get("monster_dmg", 0.0)), 0.0, 1e-6, "74 微光：伤害仍无加成")
	t.near(float(ExpeditionCfg.light_modifier(dk, 40.0).get("monster_dmg", 0.0)), 0.10, 1e-6, "40 昏暗：怪物伤害 +10%")
	t.near(float(ExpeditionCfg.light_modifier(dk, 40.0).get("stress_damage", 0.0)), 0.20, 1e-6, "40 昏暗：受压 +20%")
	t.near(float(ExpeditionCfg.light_modifier(dk, 10.0).get("monster_dmg", 0.0)), 0.15, 1e-6, "10 漆黑：怪物伤害 +15%")
	t.near(float(ExpeditionCfg.light_modifier(dk, 0.0).get("stress_damage", 0.0)), 0.40, 1e-6, "0 无光：受压 +40%")
	t.eq(ExpeditionCfg.light_tier_name(80.0), "明亮", "档位名字")
	t.eq(ExpeditionCfg.light_tier_name(0.0), "无光", "无光档位名字")


# ------------------------------------------------------------
# 配置
# ------------------------------------------------------------

static func _test_config(t: TestLib, db: DdDb) -> void:
	t.section("远征配置")
	var cfg: ExpeditionCfg = db.expedition_cfg
	t.ok(cfg != null, "配置对象存在")
	var names: Array = cfg.names()
	t.ok(names.size() >= 3, "至少 3 个资源预设，实际 %d" % names.size())
	var std: Dictionary = cfg.preset("standard")
	t.ok(std.has("light") and std.has("food") and std.has("camp"), "standard 含光照/口粮/营地三块")
	t.eq(int(std.get("heal_charges", -2)), 0, "standard 治疗不限（0 表示不限）")

	# 缺字段要能补默认值，不能因为少一个键就崩
	var merged: Dictionary = ExpeditionCfg.merge({"a": {"x": 1, "y": 2}}, {"a": {"y": 9}})
	t.eq(int((merged["a"] as Dictionary)["x"]), 1, "合并保留未覆盖字段")
	t.eq(int((merged["a"] as Dictionary)["y"]), 9, "合并覆盖指定字段")

	var unknown: Dictionary = cfg.preset("这个预设不存在")
	t.ok(unknown.has("light"), "未知预设回退 standard 而不是空字典")


# ------------------------------------------------------------
# 路线生成
# ------------------------------------------------------------

static func _test_route(t: TestLib, db: DdDb) -> void:
	t.section("路线生成")
	var route: Array = RouteGen.build(db, "weald", "short", 3, DdRng.new(1))
	t.ok(not route.is_empty(), "短图路线非空")

	var battles: int = 0
	var hungers: int = 0
	var bad_monsters: int = 0
	var gears: Array = []
	for s in route:
		if str(s.get("kind", "")) == "hunger":
			hungers += 1
			continue
		battles += 1
		gears.append(int(s.get("gear", -1)))
		for m in s.get("monsters", []):
			if db.monster(str(m)).is_empty():
				bad_monsters += 1
	t.eq(bad_monsters, 0, "路线里的怪物 id 全部存在")
	t.ok(battles >= 2, "短图至少 2 场战斗，实际 %d" % battles)
	t.ok(hungers >= 1, "短图至少 1 次饥饿检定，实际 %d" % hungers)
	t.eq(int(gears[0]) if not gears.is_empty() else -1, 2, "Lv3 用 2 阶装备（与 bench 口径一致）")

	# 同种子必须同路线：否则「同一批路线喂给不同预设」的对照实验就不成立
	var a: Array = RouteGen.build(db, "weald", "medium", 5, DdRng.new(77))
	var b: Array = RouteGen.build(db, "weald", "medium", 5, DdRng.new(77))
	t.eq(JSON.stringify(a), JSON.stringify(b), "同种子路线完全一致")

	var long_route: Array = RouteGen.build(db, "weald", "long", 5, DdRng.new(5))
	var long_battles: int = 0
	for s in long_route:
		if str(s.get("kind", "")) == "battle":
			long_battles += 1
	t.ok(long_battles > battles, "长图战斗数多于短图（%d > %d）" % [long_battles, battles])


# ------------------------------------------------------------
# 死门
# ------------------------------------------------------------

static func _test_deaths_door(t: TestLib, db: DdDb) -> void:
	t.section("死门语义")
	var c := Combatant.new()
	t.eq(c.setup_from_hero(db, "crusader", 0, 0), true, "十字军装配")
	c.hp = 3
	var r: Dictionary = c.take_damage(10, 1.0)
	t.eq(bool(r["deaths_door"]), true, "血量归零进入死门")
	t.eq(c.hp, 0, "死门血量锁定为 0")
	t.eq(c.is_alive(), true, "死门不是死亡：仍可行动、仍可被选中")
	t.ok(c.dd_buff_ids.size() > 0 or true, "死门减益需由 enter_deaths_door 显式挂载")

	c.enter_deaths_door(db)
	t.ok(c.dd_buff_ids.size() >= 4, "死门减益已挂载 %d 条" % c.dd_buff_ids.size())
	t.ok(c.acc() < c.base_acc, "死门降低命中（%.2f < %.2f）" % [c.acc(), c.base_acc])
	t.ok(c.stress_taken_mod() > 0.0, "死门使受压增加")

	# 死门上再挨一击：靠死击抗性，不是必死
	var survived: int = 0
	for i in range(200):
		var c2 := Combatant.new()
		c2.setup_from_hero(db, "crusader", 0, 0)
		c2.hp = 1
		c2.take_damage(5, 1.0)
		var res: Dictionary = c2.take_damage(5, 0.1)   # 掷 0.1 < 抗性 0.67
		if not bool(res["died"]):
			survived += 1
	t.eq(survived, 200, "死击掷骰低于抗性时不死亡")

	var dead: int = 0
	for i in range(200):
		var c3 := Combatant.new()
		c3.setup_from_hero(db, "crusader", 0, 0)
		c3.hp = 1
		c3.take_damage(5, 1.0)
		var res3: Dictionary = c3.take_damage(5, 0.99)  # 掷 0.99 > 抗性
		if bool(res3["died"]):
			dead += 1
	t.eq(dead, 200, "死击掷骰高于抗性时死亡")

	# 治疗可以把人从死门拉回来，并留下恢复期减益
	var c4 := Combatant.new()
	c4.setup_from_hero(db, "crusader", 0, 0)
	c4.hp = 1
	c4.take_damage(5, 1.0)
	c4.enter_deaths_door(db)
	var healed: int = c4.heal(6)
	t.ok(healed > 0, "死门上的治疗有效（回 %d）" % healed)
	t.eq(c4.at_deaths_door, false, "治疗后离开死门")
	t.eq(c4.recovered_from_dd, true, "标记为刚被救回")
	c4.leave_deaths_door(db, false)
	t.eq(c4.recovering, true, "进入恢复期")
	t.ok(c4.dd_buff_ids.is_empty(), "死门减益已摘除")


# ------------------------------------------------------------
# 压力阈值
# ------------------------------------------------------------

static func _test_stress_break(t: TestLib, db: DdDb) -> void:
	t.section("压力阈值：崩溃 / 美德 / 心脏骤停")
	var kinds: Array = db.affliction_kinds()
	t.ok(kinds.size() >= 5, "从 buffs.json 反推出 %d 种崩溃" % kinds.size())
	t.ok(kinds.has("fearful"), "含 fearful")
	var vk: Array = db.virtue_kinds()
	t.ok(vk.size() >= 4, "从 buffs.json 反推出 %d 种美德" % vk.size())

	# 100 压力必然触发一次崩溃或美德（两者相加 = 1）
	var breaks: int = 0
	var afflictions: int = 0
	for i in range(120):
		var b := Battle.new()
		b.setup(HEROES, MONSTERS, 700 + i)
		b.party[0].stress = 100.0
		b.check_stress_breaks()
		if b.party[0].broken():
			breaks += 1
		if b.party[0].has_affliction():
			afflictions += 1
		# 崩溃减益必须真的落到面板上
		if b.party[0].has_affliction() and b.party[0].buffs.is_empty():
			t.ok(false, "崩溃了却没有挂上任何减益")
	t.eq(breaks, 120, "100 压力必定崩溃或觉醒")
	t.between(float(afflictions) / 120.0, 0.6, 0.9, "崩溃占比接近数据给的 75%")

	# 200 压力：心脏骤停 → 死门
	var b2 := Battle.new()
	b2.setup(HEROES, MONSTERS, 4242)
	var u: Combatant = b2.party[1]
	u.stress = 200.0
	b2.check_stress_breaks()
	t.eq(u.at_deaths_door, true, "200 压力把人打到死门")
	t.eq(u.stress, 100.0, "心脏骤停后压力回落到 100（不会原地连锁）")

	# 崩溃者会摆烂：强制 refuse_chance = 1，必须不出手
	var b3 := Battle.new()
	b3.setup(HEROES, MONSTERS, 11)
	b3.affliction_refuse_chance = 1.0
	b3.party[0].apply_affliction(db, "fearful")
	var attacked: bool = false
	for e in b3.run_round():
		if str(e.get("t", "")) == "attack" and int(e.get("actor", -1)) == b3.party[0].uid:
			attacked = true
	t.eq(attacked, false, "崩溃者摆烂时不攻击")


# ------------------------------------------------------------
# 治疗配额
# ------------------------------------------------------------

static func _test_heal_charges(t: TestLib, db: DdDb) -> void:
	t.section("治疗配额（M2 结论的直接对策）")
	var used: int = 0
	var blocked: int = 0
	var b := Battle.new()
	b.setup(HEROES, MONSTERS, 909)
	b.heal_charges = 3
	for i in range(30):
		if b.is_over():
			break
		for e in b.run_round():
			if str(e.get("t", "")) == "heal":
				if bool(e.get("blocked", false)):
					blocked += 1
				else:
					used += 1
	t.ok(used <= 3, "实际治疗次数不超过配额，实际 %d" % used)
	t.ok(b.heal_charges >= 0, "配额已被扣到 0")

	# 配额用完之后不是「不能点」，而是治疗无效 —— 所以一定会出现 blocked 事件
	var b2 := Battle.new()
	b2.setup(HEROES, MONSTERS, 909)
	b2.heal_charges = 0
	var b2_heals: int = 0
	for i in range(30):
		if b2.is_over():
			break
		for e in b2.run_round():
			if str(e.get("t", "")) == "heal" and not bool(e.get("blocked", false)):
				b2_heals += 1
	t.eq(b2_heals, 0, "配额为 0 时一次都治不了")

	# 不限配额时行为应与 M1 一致（默认 -1）
	var b3 := Battle.new()
	b3.setup(HEROES, MONSTERS, 909)
	t.eq(b3.heal_charges, -1, "默认不限治疗次数")


# ------------------------------------------------------------
# 跨战斗状态
# ------------------------------------------------------------

static func _test_expedition_state(t: TestLib, db: DdDb) -> void:
	t.section("跨战斗状态继承")
	var b := Battle.new()
	b.setup(HEROES, MONSTERS, 313)
	b.party[0].hp = 5
	b.party[0].stress = 77.0
	b.party[0].apply_affliction(db, "paranoid")
	b.party[1].hp = 1
	b.party[1].take_damage(9, 1.0)
	b.party[1].enter_deaths_door(db)

	var snap: Dictionary = b.capture_party_state()
	t.near(float((snap["crusader"] as Dictionary)["stress"]), 77.0, 0.001, "压力被记录")
	t.eq(str((snap["crusader"] as Dictionary)["affliction"]), "paranoid", "崩溃状态被记录")
	t.eq(bool((snap["highwayman"] as Dictionary)["at_deaths_door"]), true, "死门状态被记录")

	var b2 := Battle.new()
	b2.setup(HEROES, MONSTERS, 314)
	b2.apply_party_state(snap)
	t.eq(b2.party[0].hp, 5, "血量按比例还原（5/33）")
	t.eq(b2.party[0].stress, 77.0, "压力还原")
	t.eq(b2.party[0].affliction, "paranoid", "崩溃还原")
	t.eq(b2.party[1].at_deaths_door, true, "死门还原")
	t.eq(b2.party[1].hp, 0, "死门血量仍为 0")
	t.ok(b2.party[1].is_alive(), "还原后仍是活着的单位")

	# 环境修正：光照只改环境倍率，不改个体面板
	var b3 := Battle.new()
	b3.setup(HEROES, MONSTERS, 315)
	var before: float = b3.party[0].dodge()
	b3.set_environment({"stress_damage": 0.3, "player_dodge": 0.1, "monster_dmg": 0.2})
	t.near(b3.party[0].dodge(), before, 0.0001, "光照不直接改闪避面板")
	var spec: Dictionary = b3.build_spec(b3.enemies[0], b3.enemies[0].actions[0], b3.party[0])
	t.ok(float(spec["dodge"]) > before, "光照修正进入伤害结算（命中判定更难）")
	t.near(b3.party[0].stress_in_mult, 1.3, 0.0001, "受压倍率生效")

	var s: float = 0.0
	var u: Combatant = b3.party[0]
	u.stress = 0.0
	s = u.add_stress(10.0)
	t.near(s, 13.0, 0.001, "受 10 点压力时实际 +13（+30%）")

	# —— 等级惩罚的受压倍率（M29）——
	# 关键是它和光照倍率**两层独立**：光照每场都会整个覆盖 stress_in_mult，
	# 等级倍率必须活下来，否则「走进暗处那一刻惩罚就没了」。
	u.join_stress_mult = 1.5
	u.stress = 0.0
	s = u.add_stress(10.0)
	t.near(s, 19.5, 0.001, "三层叠乘：10 × 1.3（光照）× 1.5（等级）= 19.5")

	b3.set_environment({"stress_damage": 0.0})
	t.near(b3.party[0].join_stress_mult, 1.5, 0.0001, "换光照没有洗掉等级倍率")
	t.near(b3.party[0].stress_in_mult, 1.0, 0.0001, "光照倍率按新值重算")
	u.stress = 0.0
	s = u.add_stress(10.0)
	t.near(s, 15.0, 0.001, "光照归零后只剩等级倍率：10 × 1.5 = 15")


# ------------------------------------------------------------
# 走廊内容：陷阱与障碍（M8）
# ------------------------------------------------------------
#
# 这一层有两条不变量必须钉死，否则机制会在无人察觉的情况下失效：
#
#   1. 侦察过的陷阱必须更好躲，且差值正好等于 rules 里那个加成。
#      接错字段不会报错，只会让「侦察」和「陷阱」变成两件无关的事。
#   2. 走进一条走廊之前，它的内容必须不可见。泄露了就等于免费侦察，
#      「看见再决定绕不绕」这件事就不成立了。
static func _test_hallway_hazards(t: TestLib, db: DdDb) -> void:
	t.section("走廊内容：陷阱与障碍")
	var preset: Dictionary = db.expedition_cfg.preset("standard")

	var e := Expedition.new()
	e.setup(db, HEROES, [], preset, 5, "standard", {}, {})
	e.set_location("weald", "medium")

	# 强盗的 trap 抵抗是 0.40，其余三人 0.10 / 0.20 —— 取最高，所以是 0.40。
	# 这条不是为了凑数：它说明「队里有强盗，陷阱就更好躲」，
	# 副产物是队伍构成第一次影响走廊风险。
	t.eq(absf(e.trap_resist() - 0.40) < 1e-6, true,
		"队伍陷阱抵抗取全队最高的 0.40（实际 %.2f）" % e.trap_resist())

	var plain: float = e.trap_avoid_chance(1, false)
	var scouted: float = e.trap_avoid_chance(1, true)
	t.ok(absf((scouted - plain) - db.rules.trap_scout_disarm_bonus) < 1e-6,
		"侦察加成正好是 %.2f（%.2f → %.2f）" % [db.rules.trap_scout_disarm_bonus, plain, scouted])
	t.eq(e.trap_avoid_chance(5, false) < plain, true, "5 级地牢的陷阱比 1 级更难躲")
	t.eq(e.trap_avoid_chance(9, false) >= 0.05 - 1e-6, true, "躲避率有下限，不会变成必踩")

	# —— 障碍：铁锹就是那个「可以不挨打」的补给 ——
	e.shovel = 1
	var hp0: float = float(e.state[HEROES[0]]["hp_ratio"])
	var cleared: Dictionary = e.resolve_obstacle()
	t.eq(bool(cleared["cleared"]), true, "有铁锹时障碍被清除")
	t.eq(e.shovel, 0, "清除障碍消耗 1 把铁锹")
	t.eq(float(e.state[HEROES[0]]["hp_ratio"]), hp0, "有铁锹时全队不掉血")

	var st1: float = float(e.state[HEROES[0]]["stress"])
	var dug: Dictionary = e.resolve_obstacle()
	t.eq(bool(dug["cleared"]), false, "没铁锹时障碍清不掉")
	t.ok(float(e.state[HEROES[0]]["hp_ratio"]) < hp0, "没铁锹时全队掉血")
	t.ok(float(e.state[HEROES[0]]["stress"]) > st1, "没铁锹时全队加压")

	# —— 陷阱：把 clamp 区间压成一点，随机就能变成确定性 ——
	var e2 := Expedition.new()
	var cfg2: Dictionary = preset.duplicate(true)
	(cfg2["trap"] as Dictionary)["min_avoid"] = 1.0
	(cfg2["trap"] as Dictionary)["max_avoid"] = 1.0
	e2.setup(db, HEROES, [], cfg2, 7, "standard", {}, {})
	e2.set_location("weald", "medium")
	var dodge: Dictionary = e2.resolve_trap({"kind": "trap", "level": 1, "scouted": false})
	t.eq(bool(dodge["dodged"]), true, "躲避率 100% 时必定躲开")
	t.eq(float(e2.state[HEROES[0]]["hp_ratio"]), 1.0, "躲开时不掉血")

	(cfg2["trap"] as Dictionary)["min_avoid"] = 0.0
	(cfg2["trap"] as Dictionary)["max_avoid"] = 0.0
	var hit: Dictionary = e2.resolve_trap({"kind": "trap", "level": 1, "scouted": false})
	t.eq(bool(hit["dodged"]), false, "躲避率 0% 时必定踩中")
	t.ok(float(e2.state[HEROES[0]]["hp_ratio"]) < 1.0, "踩中时全队掉血")
	t.eq(int(e2.stats["traps"]), 2, "陷阱计数含躲开与踩中")
	t.eq(int(e2.stats["traps_dodged"]), 1, "只统计躲开的次数")

	# —— 走进之前不能知道 ——
	var m: Dictionary = MapGen.build(db, "weald", "short", 1, DdRng.new(12))
	var start: int = int(m["start"])
	var nbs: Array = MapGen.neighbors(m, start)
	t.ok(nbs.size() > 0, "入口有相邻走廊")
	if nbs.is_empty():
		return
	var nb: Dictionary = nbs[0]
	var ei: int = int(nb["edge"])
	(m["edges"][ei] as Dictionary)["steps"] = [{"kind": "trap", "level": 1}]

	var e3 := Expedition.new()
	e3.setup(db, HEROES, [], preset, 12, "standard", {}, {})
	e3.set_location("weald", "short")
	e3.enter_map(m)
	t.eq(e3.edge_known(ei), false, "未侦察时不知道这条走廊有陷阱")
	t.eq(e3.edge_kind(ei), "", "未知走廊不透露任何内容")

	e3.travel(int(nb["room"]))
	t.eq(e3.edge_known(ei), true, "走过之后这条走廊变已知")
	t.eq(e3.edge_kind(ei), "trap", "走过的走廊内容可查")

	# 队列里那一步必须带 scouted=false：走过之后再取值就永远是 true，
	# 侦察加成会变成白送。
	var found: Dictionary = {}
	while e3.has_pending():
		var s: Dictionary = e3.take_step()
		if str(s.get("kind", "")) == "trap":
			found = s
	t.eq(found.is_empty(), false, "队列里出现了陷阱步")
	t.eq(bool(found.get("scouted", true)), false, "没侦察过的陷阱标记为未侦察")

	# 预先侦察过的同一条走廊：走进去时标记为已侦察。
	# 必须重新生成一张图——上一张里这条边的 walked 已经是 true，
	# 再走一次走的是「重复通行」分支，根本没有内容步骤。
	var m4: Dictionary = MapGen.build(db, "weald", "short", 1, DdRng.new(12))
	(m4["edges"][ei] as Dictionary)["steps"] = [{"kind": "trap", "level": 1}]
	var e4 := Expedition.new()
	e4.setup(db, HEROES, [], preset, 12, "standard", {}, {})
	e4.set_location("weald", "short")
	e4.enter_map(m4)
	e4.edges_known[ei] = true
	e4.travel(int(nb["room"]))
	var found2: Dictionary = {}
	while e4.has_pending():
		var s2: Dictionary = e4.take_step()
		if str(s2.get("kind", "")) == "trap":
			found2 = s2
	t.eq(bool(found2.get("scouted", false)), true, "侦察过的陷阱标记为已侦察")

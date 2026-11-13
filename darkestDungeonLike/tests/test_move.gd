class_name TestMove
extends RefCounted
## 位移与洗位（M11）回归。
##
## M9 的结论里有一句是错的：「没有任何怪物技能带 push/pull，所以敌人从来没
## 打乱过你的阵型」。实际上 41 只怪物、46 个技能带着位移效果——问题在别处：
##
##   1. 位移**从来不判 move 抗性**（字段从 M0 就解析进 resistances，没人读）
##   2. `shuffletarget` / `shuffleparty` 落到 effect_resolver 的兜底分支，返回空字典
##   3. **最要命的一条**：`_score` 不给位移估值，于是带位移的技能永远输给
##      同伤害但附带 +20 压力的技能。也就是说「怪物不会推人」的真正原因是
##      AI 不会选，而不是数据没有。
##
## 这一组断言对应这三层，缺一条就不知道是哪一层还断着。

const HEROES: Array = ["crusader", "highwayman", "vestal", "plague_doctor"]
const MONSTERS: Array = ["cultist_brawler_A", "cultist_brawler_A", "cultist_witch_A"]


static func run(t: TestLib, db: DdDb) -> void:
	_test_resist(t, db)
	_test_no_rng_waste(t, db)
	_test_shuffle(t, db)
	_test_score(t, db)
	_test_pick(t, db)
	_test_self_move(t, db)


## 位移抗性：res 高的人推不动，res 为 0 的人一定推得动。
##
## 用「推 60 次，数成功几次」而不是断言单次，因为抗性本身就是概率的。
## 60 次对 0.9 的抗性来说，期望成功 6 次，断言区间放到 0~15，
## 既不会随机红，也足以否掉「抗性根本没生效」（那样会是 60 次）。
static func _test_resist(t: TestLib, db: DdDb) -> void:
	t.section("位移：抗性")
	var b := Battle.new()
	b.setup(HEROES, MONSTERS, 301)
	var tank: Combatant = b.party[0]
	tank.resistances["move"] = 0.9

	var moved_high: int = 0
	for i in 60:
		var before: int = tank.rank
		var ctx: Dictionary = {"hit": true, "rng": DdRng.new(700 + i), "all_units": b.all_units()}
		b.apply_effects({"id": "p", "effects": ["Push 1A"]}, b.party[3], tank, ctx)
		if tank.rank != before:
			moved_high += 1
		# 推回去，保证每次都在同一个起点上试
		if tank.rank != 0:
			b.move_unit(tank, -tank.rank)
	t.ok(moved_high <= 15, "move 抗性 0.9 时 60 次里只推动 %d 次（应远少于 60）" % moved_high)
	t.ok(moved_high > 0, "抗性 0.9 不是绝对免疫（推动了 %d 次）" % moved_high)

	# 抗性 0：60 次全成功
	tank.resistances["move"] = 0.0
	var moved_zero: int = 0
	for i in 60:
		var before2: int = tank.rank
		var ctx2: Dictionary = {"hit": true, "rng": DdRng.new(800 + i), "all_units": b.all_units()}
		b.apply_effects({"id": "p", "effects": ["Push 1A"]}, b.party[3], tank, ctx2)
		if tank.rank != before2:
			moved_zero += 1
		if tank.rank != 0:
			b.move_unit(tank, -tank.rank)
	t.eq(moved_zero, 60, "抗性 0 时每一次推都成功（%d/60）" % moved_zero)

	# 抗性可以关掉：这是对照实验的唯一开关，必须真的能关
	tank.resistances["move"] = 0.9
	var moved_off: int = 0
	for i in 30:
		var before3: int = tank.rank
		var ctx3: Dictionary = {"hit": true, "rng": DdRng.new(900 + i),
			"all_units": b.all_units(), "move_resist_enabled": false}
		b.apply_effects({"id": "p", "effects": ["Push 1A"]}, b.party[3], tank, ctx3)
		if tank.rank != before3:
			moved_off += 1
		if tank.rank != 0:
			b.move_unit(tank, -tank.rank)
	t.eq(moved_off, 30, "关掉抗性后高抗性目标也能被推（%d/30）" % moved_off)


## 抗性为 0 的路径不能消耗随机数。
##
## 这条看着像洁癖，其实是正确性问题：不短路的话，即使逻辑完全等价
## （res=0 永远不抵抗），rng 序列也会整体错位一格，所有下游随机全部改变。
## 表现是「改了个不生效的功能，基线却变了」，而且查不出来。
static func _test_no_rng_waste(t: TestLib, db: DdDb) -> void:
	t.section("位移：抗性为 0 不消耗随机数")
	var b := Battle.new()
	b.setup(HEROES, MONSTERS, 302)
	b.party[0].resistances["move"] = 0.0

	var used: DdRng = DdRng.new(4242)
	var ctrl: DdRng = DdRng.new(4242)
	var ctx: Dictionary = {"hit": true, "rng": used, "all_units": b.all_units()}
	b.apply_effects({"id": "p", "effects": ["Push 1A"]}, b.party[3], b.party[0], ctx)
	# 对照组什么都不做。两条 rng 的下一个值必须相同。
	t.ok(absf(used.next_float() - ctrl.next_float()) < 0.0000001,
		"抗性 0 时推一次不改变 rng 序列")


## 洗位：单个换槽、整队打乱、尸体不参与。
static func _test_shuffle(t: TestLib, db: DdDb) -> void:
	t.section("洗位：单个换槽")
	var b := Battle.new()
	b.setup(HEROES, MONSTERS, 303)
	var u: Combatant = b.party[1]
	var before: int = u.rank
	var mv: Dictionary = b.shuffle_unit(u)
	t.ok(not mv.is_empty(), "洗位返回了结果")
	t.ok(u.rank != before, "换到了别的槽（%d → %d）" % [before, u.rank])
	t.eq(b.party[u.rank], u, "数组里单位确实在那个槽")
	# 人数不变、没有复制
	t.eq(b.party.size(), 4, "洗一个单位不改变队伍人数")
	var seen: Dictionary = {}
	for p in b.party:
		seen[p.uid] = true
	t.eq(seen.size(), 4, "没有出现重复单位")

	t.section("洗位：整队打乱")
	var b2 := Battle.new()
	b2.setup(HEROES, MONSTERS, 304)
	var ids_before: Array = []
	for p in b2.party:
		ids_before.append(p.uid)
	var moved: Array = b2.shuffle_team(Combatant.SIDE_PARTY)
	t.eq(b2.party.size(), 4, "打乱后人数不变")
	var ids_after: Array = []
	for p in b2.party:
		ids_after.append(p.uid)
	ids_before.sort()
	ids_after.sort()
	t.eq(str(ids_before), str(ids_after), "打乱只是换顺序，成员集合不变")
	t.ok(moved.size() > 0, "至少有一个单位换了位置（%d 个）" % moved.size())

	# 尸体不参与洗位：否则打死的怪会在阵型里滑来滑去，看起来像又活了
	t.section("洗位：尸体不动")
	var b3 := Battle.new()
	b3.setup(HEROES, MONSTERS, 305)
	var corpse: Combatant = b3.party[3]
	corpse.dead = true
	corpse.hp = 0
	var corpse_rank: int = corpse.rank
	for i in 12:
		b3.shuffle_team(Combatant.SIDE_PARTY)
	t.eq(corpse.rank, corpse_rank, "尸体 12 次洗位后仍在原槽（%d）" % corpse.rank)
	t.eq(b3.party[corpse_rank], corpse, "尸体确实还在那个位置")
	# 活着的三个仍然是一个排列
	var alive_seen: Dictionary = {}
	for p in b3.party:
		if not p.dead:
			alive_seen[p.uid] = true
	t.eq(alive_seen.size(), 3, "三个活人没有重叠")

	# 只剩一个人时洗不动，也不能报错
	t.section("洗位：人数不足")
	var b4 := Battle.new()
	b4.setup(HEROES, MONSTERS, 306)
	for i in range(1, 4):
		b4.party[i].dead = true
		b4.party[i].hp = 0
	var solo: Combatant = b4.party[0]
	var solo_rank: int = solo.rank
	t.eq(str(b4.shuffle_unit(solo)), str({}), "只有一个人时换槽返回空")
	var none: Array = b4.shuffle_team(Combatant.SIDE_PARTY)
	t.eq(none.size(), 0, "只有一个人时打乱返回空列表")
	t.eq(solo.rank, solo_rank, "那个人没被移动")


## 位移估值：这是 M11 里唯一「不是数据给的数」，所以必须钉住它的行为。
static func _test_score(t: TestLib, db: DdDb) -> void:
	t.section("位移估值")
	var b := Battle.new()
	b.setup(HEROES, ["cultist_witch_C", "cultist_witch_C", "cultist_witch_C"], 307)
	var witch: Combatant = b.enemies[0]
	var push_sk: Dictionary = _skill(witch, "cultist_push")
	t.ok(not push_sk.is_empty(), "女巫装载了 cultist_push")

	var crusader: Combatant = b.party[0]     # 1 号位，push 有空间
	var pd: Combatant = b.party[3]           # 4 号位，push 到边界

	b.move_value_enabled = true
	var s_on: float = b._score(witch, push_sk, crusader)
	var s_edge_on: float = b._score(witch, push_sk, pd)
	b.move_value_enabled = false
	var s_off: float = b._score(witch, push_sk, crusader)
	var s_edge_off: float = b._score(witch, push_sk, pd)

	t.ok(s_on > s_off, "开启估值后 1 号位的分数更高（%.3f > %.3f）" % [s_on, s_off])
	t.ok(absf(s_edge_on - s_edge_off) < 0.0001,
		"推到边界不产生价值（%.3f vs %.3f）—— 已经在最后一位的人推不动" % [s_edge_on, s_edge_off])

	# 抗性越高，位移的期望价值越低。
	# 注意这里必须把开关拨回来——上一段为了拿 s_off 把它设成了 false，
	# 忘了恢复的话两段都会算出「不含位移」的分数，断言就成了 4.693 > 4.693。
	b.move_value_enabled = true
	var before_res: float = crusader.resistances.get("move", 0.0)
	crusader.resistances["move"] = 0.0
	var s_nores: float = b._score(witch, push_sk, crusader)
	crusader.resistances["move"] = 0.9
	var s_highres: float = b._score(witch, push_sk, crusader)
	t.ok(s_nores > s_highres, "抗性 0 时位移更值钱（%.3f > %.3f）" % [s_nores, s_highres])
	crusader.resistances["move"] = before_res


## 最终验收：位移真的改变了「谁挨打」。
##
## 前面几条测的都是零件。这一条测整条链：一个会推人的怪，把前排推到后面，
## 于是原本安全的脆皮被顶到前面。这正是 DD1 位移机制的价值，
## 也是「接通了但没效果」和「真的起作用」的分界。
static func _test_pick(t: TestLib, db: DdDb) -> void:
	t.section("位移：真的改变了挨打的顺序")
	var moved_any: int = 0
	var exposed: int = 0
	for i in 20:
		var b := Battle.new()
		b.setup(HEROES, ["fishman_crabby_A", "fishman_crabby_A", "fishman_crabby_A"],
			500 + i, 0, 0)
		# 必须先抓住「这个单位」，不能记下 rank 再去读 b.party[3]——
		# 战斗一开局阵型就可能变，数组下标和单位已经对不上了。
		# 这和 M10 里 `remove_at + insert` 之后 enemies[1] 就是被推的人本身
		# 是同一类错误：下标不等于身份。
		var pd: Combatant = b.party[3]
		var pd_start: int = pd.rank
		var log: Array = []
		while not b.is_over() and b.round_index < 12:
			for e in b.run_round():
				log.append(e)
		for e in log:
			# `self` 要排除：那是出手的人自己挪（M53），不是被别人推。
			# 不排除的话这条断言会被自己的位移喂饱，测不出「怪物会不会推人」。
			if str(e.get("t", "")) == "move" and str(e.get("skill", "")) != "move" \
					and not bool(e.get("self", false)):
				moved_any += 1
		# 4 号位的人（瘟疫医生）如果被顶到更前面，就是被暴露了
		if pd.rank < pd_start:
			exposed += 1
	t.ok(moved_any > 0, "20 场里发生了 %d 次被技能推动" % moved_any)
	t.ok(exposed > 0, "有 %d 场里末位的人被顶到了前面" % exposed)


## 技能自带的位移（M53）。
##
## 数据里每个技能都有 `move: [后退上限, 前进上限]`，12 个技能非 0，但这个字段
## 从 M0 解析进动作字典之后**一直没人读**——所以原版招牌的「攻击时人物位移」
## 在我们这儿一次都没发生过。这一组守住三件事：
##   a) 真的会挪（方向对）
##   b) 多目标只挪一次（放进逐目标循环里会按人数挪）
##   c) 顶到边不算错误（不该报错、也不该卡住回合）
static func _test_self_move(t: TestLib, db: DdDb) -> void:
	t.section("位移：技能自带的挪位")
	var b := Battle.new()
	b.setup(HEROES, MONSTERS, 909)
	var cr: Combatant = b.party[0]
	var hl: Dictionary = _skill(cr, "holy_lance")
	t.eq(hl.is_empty(), false, "十字军装载了 holy_lance")
	var hl_mv: Array = hl.get("move", [])
	t.eq("%d,%d" % [int(hl_mv[0]), int(hl_mv[1])], "0,1",
		"holy_lance 的 move 是 [后退0, 前进1]（数据里是浮点，比之前先转 int）")

	# 站到队尾，才挪得动
	b.move_unit(cr, 3)
	t.eq(cr.rank, 3, "先把十字军挪到 4 号位")
	# 一次给两个目标：验证「只挪一次」，而不是按目标个数挪
	b._apply_choice(cr, {"action": hl, "targets": [b.enemies[0], b.enemies[1]]})
	t.eq(cr.rank, 2, "圣枪突进后 4 号位 -> 3 号位（两个目标也只挪一格）")
	var mv: Dictionary = _first_of(b.events, "move")
	t.eq(bool(mv.get("self", false)), true, "位移事件带 self 标记")
	t.eq(str(mv.get("skill", "")), "holy_lance", "事件记着是哪个技能挪的")

	# 反方向：开枪之后后退
	var b2 := Battle.new()
	b2.setup(HEROES, MONSTERS, 910)
	var hm: Combatant = b2.party[1]
	var pbs: Dictionary = _skill(hm, "point_blank_shot")
	t.eq(pbs.is_empty(), false, "强盗装载了 point_blank_shot")
	t.eq(hm.rank, 1, "强盗开局在 2 号位")
	b2._apply_choice(hm, {"action": pbs, "targets": [b2.enemies[0]]})
	t.eq(hm.rank, 2, "零距离开枪后 2 号位 -> 3 号位（后退一格）")

	# 没打中也要挪：原版位移是动作的一部分，不是命中奖励。
	#
	# 造「必空」不能靠压 atk：`_resolve_action` 里 `atk <= 0` 会被判成功能技，
	# 连命中判定都不走（第一版就是这么写错的，压根没产生 miss 事件）。
	# 正确做法是把目标的闪避顶到上限 0.95，命中率必然被夹到 0。
	var b4 := Battle.new()
	b4.setup(HEROES, MONSTERS, 912)
	var cr4: Combatant = b4.party[0]
	var hl4: Dictionary = _skill(cr4, "holy_lance")
	b4.enemies[0].base_dodge = 5.0
	b4.move_unit(cr4, 3)
	var n4: int = b4.events.size()
	b4._apply_choice(cr4, {"action": hl4, "targets": [b4.enemies[0]]})
	var saw_miss: bool = false
	for i in range(n4, b4.events.size()):
		if str(b4.events[i].get("t", "")) == "miss":
			saw_miss = true
	t.eq(saw_miss, true, "闪避顶满后这一下确实没打中（产生 miss 事件）")
	t.eq(cr4.rank, 2, "没打中也照样突进（4 号位 -> 3 号位）")

	# 顶到边：在最前排再突进，挪不动也不算错
	var b3 := Battle.new()
	b3.setup(HEROES, MONSTERS, 911)
	var cr3: Combatant = b3.party[0]
	t.eq(cr3.rank, 0, "十字军开局在 1 号位")
	var n_before: int = b3.events.size()
	b3._apply_choice(cr3, {"action": _skill(cr3, "holy_lance"),
		"targets": [b3.enemies[0]]})
	t.eq(cr3.rank, 0, "已在最前排，突进不动")
	var got_move: bool = false
	for i in range(n_before, b3.events.size()):
		if str(b3.events[i].get("t", "")) == "move":
			got_move = true
	t.eq(got_move, false, "挪不动时不发 move 事件（否则日志会写一句空话）")


static func _first_of(events: Array, type_name: String) -> Dictionary:
	for e in events:
		if str(e.get("t", "")) == type_name:
			return e
	return {}


static func _skill(c: Combatant, id: String) -> Dictionary:
	for a in c.actions:
		if str(a.get("id", "")) == id:
			return a
	return {}

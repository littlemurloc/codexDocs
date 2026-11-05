class_name TestGuard
extends RefCounted
## 守护与反击（M10）回归。
##
## 这两套机制和 M9 的位移一样，属于「数据早就写好了，代码从来没读过」：
##   effects.json 里有 21 条带 guard 的效果、14 条带 riposte 的效果，
##   combatant.gd 甚至在 build_actions 里解析了 ignore_guard，
##   但整条链路没有任何一处消费它们。
##
## 所以这一组断言的重点不是「函数返回什么」，而是**血到底掉在谁身上**——
## 守护的唯一可观测结果就是这件事。

const GUARD_HEROES: Array = ["man_at_arms", "highwayman", "vestal", "plague_doctor"]
const MONSTERS: Array = ["cultist_brawler_A", "cultist_brawler_A", "cultist_witch_A"]

## 固定伤害：不掷区间，方便断言「掉了几点」而不是「掉了没」。
const PROBE_DMG: Array = [6.0, 6.0]


static func run(t: TestLib, db: DdDb) -> void:
	# 这一组测「打谁」，不测「打不打中」。命中上限固定 0.95，
	# 不放开的话每条断言都要靠循环重试，失败时还分不清是逻辑错还是掷骰背。
	var saved: float = db.rules.cutoff_hit
	db.rules.cutoff_hit = 1.0
	_test_guard(t, db)
	_test_guard_rules(t)
	_test_riposte(t, db)
	_test_swap(t, db)
	db.rules.cutoff_hit = saved


# ------------------------------------------------------------
# 守护：伤害重定向
# ------------------------------------------------------------
static func _test_guard(t: TestLib, db: DdDb) -> void:
	t.section("守护：装配与目标")
	var b := Battle.new()
	b.setup(GUARD_HEROES, MONSTERS, 100)
	var maa: Combatant = b.party[0]
	var vestal: Combatant = b.party[2]
	var sk: Dictionary = _skill(maa, "defender")
	t.ok(not sk.is_empty(), "战争老兵装载了 defender")
	t.eq(bool(sk.get("is_guard", false)), true, "defender 被标记为守护技")
	t.eq(str(sk.get("target_mask", 0)), str(0b1111), "守护的目标掩码覆盖 1-4 号位")

	# 这是 M10 修掉的那个坑：原来「无攻击无治疗」的技能一律只作用于自己，
	# 于是守护的目标池永远是 [自己]，而守自己不会产生任何重定向。
	var pool: Array = b._legal_targets(maa, sk)
	t.eq(pool.has(maa), false, "守护不能选自己")
	t.eq(pool.size(), 3, "守护可选 3 名队友（实际 %d）" % pool.size())

	t.section("守护：伤害真的改道")
	b._resolve_action(maa, sk, vestal)
	t.eq(b.guard_target_of(maa.uid), vestal, "老兵在守奶妈")
	t.eq(b.guardian_of(vestal.uid), maa, "奶妈这一侧也知道自己被守")
	t.ok(b.guard_target_of(vestal.uid) == null, "奶妈没有反过来守人")
	t.ok(b.guardian_of(maa.uid) == null, "老兵自己没有被别人守")

	var maa_hp: int = maa.hp
	var v_hp: int = vestal.hp
	b._resolve_action(b.enemies[0], _probe(b.enemies[0]), vestal)
	t.eq(vestal.hp, v_hp, "打向奶妈的一击没有落在奶妈身上")
	t.ok(maa.hp < maa_hp, "伤害改落在老兵身上（%d → %d）" % [maa_hp, maa.hp])

	var g_ev: Dictionary = _event(b.events, "guard")
	t.ok(not g_ev.is_empty(), "产生了 guard 事件")
	t.eq(int(g_ev.get("guard", -1)), maa.uid, "事件指明了替谁挡")
	t.eq(int(g_ev.get("target", -1)), vestal.uid, "事件保留了原本的目标")
	# attack 事件的 target 必须是守护者——否则日志写「打奶妈」而血条掉在老兵上
	var a_ev: Dictionary = _event(b.events, "attack")
	t.eq(int(a_ev.get("target", -1)), maa.uid, "attack 事件记的是实际挨打的人")

	t.section("守护：三条穿透路径")
	# 1. AOE 不重定向（本项目取舍，见 M10_GUARD.md）
	var aoe: Dictionary = _probe(b.enemies[1])
	aoe["target_aoe"] = true
	var v2: int = vestal.hp
	b._resolve_action(b.enemies[1], aoe, vestal)
	t.ok(vestal.hp < v2, "AOE 不被守护挡住，奶妈自己挨打（%d → %d）" % [v2, vestal.hp])

	# 2. ignore_guard 穿透（这个字段 build_actions 一直在解析，直到 M10 才有人读）
	var pierce: Dictionary = _probe(b.enemies[2])
	pierce["ignore_guard"] = true
	var v3: int = vestal.hp
	b._resolve_action(b.enemies[2], pierce, vestal)
	t.ok(vestal.hp < v3, "ignore_guard 穿透守护（%d → %d）" % [v3, vestal.hp])

	# 3. 友方技能不重定向：治疗被守护者，不该治到守护者头上
	var heal_sk: Dictionary = _skill(vestal, "divine_grace")
	if not heal_sk.is_empty():
		t.eq(b.guard_redirect(vestal, heal_sk, maa), maa, "友方治疗不重定向")
	t.eq(b.guard_redirect(vestal, sk, maa), maa, "友方技能一律不重定向")

	t.section("守护：守护者阵亡即失效")
	maa.hp = 0
	maa.dead = true
	var v4: int = vestal.hp
	b._resolve_action(b.enemies[0], _probe(b.enemies[0]), vestal)
	t.ok(vestal.hp < v4, "守护者阵亡后攻击回到原目标")
	t.ok(b.guardian_of(vestal.uid) == null, "阵亡后关系已解除")


# ------------------------------------------------------------
# 守护：关系表本身的规则
# ------------------------------------------------------------
static func _test_guard_rules(t: TestLib) -> void:
	t.section("守护：关系表")
	var b := Battle.new()
	b.setup(GUARD_HEROES, MONSTERS, 101)
	var maa: Combatant = b.party[0]
	var hw: Combatant = b.party[1]
	var vestal: Combatant = b.party[2]
	var pd: Combatant = b.party[3]

	b.set_guard(maa.uid, maa.uid, 3)
	t.ok(b.guard_target_of(maa.uid) == null, "守自己被拒绝（无关系建立）")

	b.set_guard(maa.uid, vestal.uid, 3)
	t.eq(b.guard_target_of(maa.uid), vestal, "建立守护")
	# 一个人只能守一个
	b.set_guard(maa.uid, pd.uid, 3)
	t.ok(b.guardian_of(vestal.uid) == null, "新守护替换旧守护")
	t.eq(b.guardian_of(pd.uid), maa, "守的是后建立的那个")
	# 一个目标只能被一个人守
	b.set_guard(hw.uid, pd.uid, 3)
	t.eq(b.guardian_of(pd.uid), hw, "第二个人来守同一目标时接管")
	t.ok(b.guard_target_of(maa.uid) == null, "原守护者的关系被清掉，不留半边状态")

	# 计时
	var b2 := Battle.new()
	b2.setup(GUARD_HEROES, MONSTERS, 102)
	var m2: Combatant = b2.party[0]
	var v2: Combatant = b2.party[2]
	b2.set_guard(m2.uid, v2.uid, 2)
	b2._tick_guards_and_riposte()
	t.eq(b2.guardian_of(v2.uid), m2, "2 回合守护：1 轮后仍在")
	b2._tick_guards_and_riposte()
	t.ok(b2.guardian_of(v2.uid) == null, "2 回合守护：2 轮后解除")

	# 死人不能被守
	var b3 := Battle.new()
	b3.setup(GUARD_HEROES, MONSTERS, 103)
	var m3: Combatant = b3.party[0]
	var p3: Combatant = b3.party[3]
	p3.hp = 0
	p3.dead = true
	b3.set_guard(m3.uid, p3.uid, 3)
	t.ok(b3.guard_target_of(m3.uid) == null, "不能守护已经阵亡的队友")


# ------------------------------------------------------------
# 反击
# ------------------------------------------------------------
static func _test_riposte(t: TestLib, db: DdDb) -> void:
	t.section("反击：姿态")
	var b := Battle.new()
	b.setup(GUARD_HEROES, MONSTERS, 110)
	var hw: Combatant = b.party[1]
	var sk: Dictionary = _skill(hw, "duelist_advance")
	t.ok(not sk.is_empty(), "强盗装载了 duelist_advance")
	t.eq(bool(sk.get("is_riposte", false)), true, "duelist_advance 带反击")
	# 反击的命中率取英雄本身（武器 atk ≈ 0.85），一次失败就是随机红。
	# cutoff_hit 只能抬高上限，不能保证命中——要保证，得把 acc 本身顶上去。
	hw.base_acc = 2.0

	b._resolve_action(hw, sk, b.enemies[0])
	t.eq(b.has_riposte(hw.uid), true, "强盗进入反击姿态")
	t.eq(b.riposte_turns_left(hw.uid), 3, "反击持续 3 回合")

	var st: Dictionary = {"mult": 0.6, "turns": 1, "on_hit": 1.0, "on_miss": 1.0}
	t.near(float(b.riposte_action(st).get("dmg_mult_extra", 0.0)), 0.6, 0.001,
		"反击伤害倍率取自 riposte 的伤害修正")
	t.eq(bool(b.riposte_action(st).get("ignore_guard", false)), true,
		"反击本身不会被守护重定向")

	t.section("反击：被打就还手")
	var foe: Combatant = b.enemies[1]
	var foe_hp: int = foe.hp
	var hw_hp: int = hw.hp
	b._resolve_action(foe, _probe(foe), hw)
	t.ok(hw.hp < hw_hp, "强盗挨了这一下（%d → %d）" % [hw_hp, hw.hp])
	t.ok(foe.hp < foe_hp, "打强盗的人被反击了（%d → %d）" % [foe_hp, foe.hp])
	var r_ev: Dictionary = _event(b.events, "riposte")
	t.ok(not r_ev.is_empty(), "产生了 riposte 事件")
	t.eq(int(r_ev.get("actor", -1)), hw.uid, "还手的是强盗")
	t.eq(int(r_ev.get("target", -1)), foe.uid, "挨打的是刚才那个攻击者")

	t.section("反击：没打中也还手")
	# 数据里 riposte_on_miss_chance_add 也是 1.0——「他扑空了，正好露出破绽」。
	#
	# 让这一击必失手的办法是把攻击者的 acc 压到负数，而不是把 cutoff_hit 设 0：
	# cutoff 是全局的，设 0 之后连**反击本身**也打不中，断言会以
	# 「未命中也会触发反击（15 → 15）」的形式失败，但原因完全在别处。
	var b2 := Battle.new()
	b2.setup(GUARD_HEROES, MONSTERS, 111)
	var hw2: Combatant = b2.party[1]
	hw2.base_acc = 2.0
	b2.set_riposte(hw2.uid, {"turns": 3, "mult": 0.6, "on_hit": 1.0, "on_miss": 1.0})
	var foe2: Combatant = b2.enemies[0]
	foe2.base_acc = -3.0
	var foe2_hp: int = foe2.hp
	b2._resolve_action(foe2, _probe(foe2), hw2)
	t.ok(_event(b2.events, "miss").size() > 0, "这一击确实未命中")
	t.ok(foe2.hp < foe2_hp, "未命中也会触发反击（%d → %d）" % [foe2_hp, foe2.hp])

	t.section("反击：不会连锁")
	# A 反击 B、B 反击 A —— 没有这个闸门就是栈溢出。
	var b3 := Battle.new()
	b3.setup(GUARD_HEROES, MONSTERS, 112)
	var hw3: Combatant = b3.party[1]
	var foe3: Combatant = b3.enemies[0]
	b3.set_riposte(hw3.uid, {"turns": 3, "mult": 0.6, "on_hit": 1.0, "on_miss": 1.0})
	b3.set_riposte(foe3.uid, {"turns": 3, "mult": 0.6, "on_hit": 1.0, "on_miss": 1.0})
	b3._resolve_action(hw3, _probe(hw3), foe3)
	var n: int = 0
	for e in b3.events:
		if str(e.get("t", "")) == "riposte":
			n += 1
	t.eq(n, 1, "一轮交互只产生 1 次反击（实际 %d）" % n)

	t.section("反击：计时")
	var b4 := Battle.new()
	b4.setup(GUARD_HEROES, MONSTERS, 113)
	var hw4: Combatant = b4.party[1]
	b4.set_riposte(hw4.uid, {"turns": 2, "mult": 0.6, "on_hit": 1.0, "on_miss": 1.0})
	b4._tick_guards_and_riposte()
	t.eq(b4.riposte_turns_left(hw4.uid), 1, "1 轮后剩 1 回合")
	b4._tick_guards_and_riposte()
	t.eq(b4.has_riposte(hw4.uid), false, "2 轮后消失")


# ------------------------------------------------------------
# 换位（古物学家的「保护我」）
# ------------------------------------------------------------
static func _test_swap(t: TestLib, db: DdDb) -> void:
	t.section("守护：换位是数据驱动的")
	var b := Battle.new()
	b.setup(["antiquarian", "highwayman", "vestal", "plague_doctor"], MONSTERS, 120)
	var aq: Combatant = b.party[0]
	var tgt: Combatant = b.party[2]
	var aq_uid: int = aq.uid
	var tg_uid: int = tgt.uid
	var sk: Dictionary = _skill(aq, "protect_me")
	t.ok(not sk.is_empty(), "古物学家装载了 protect_me")

	b._resolve_action(aq, sk, tgt)
	t.eq(b.unit_by_uid(tg_uid).rank, 0, "被保护者被换到前排（实际 %d 号位）" % b.unit_by_uid(tg_uid).rank)
	t.eq(b.unit_by_uid(aq_uid).rank, 2, "古物学家退到后排（实际 %d 号位）" % b.unit_by_uid(aq_uid).rank)
	t.eq(b.guard_target_of(aq_uid), b.unit_by_uid(tg_uid), "换位之后守护关系仍然成立")
	t.ok(_event(b.events, "swap").size() > 0, "产生了 swap 事件")

	# 换位不能把人挤出阵型：rank 仍是 0..3 的排列
	var seen: Dictionary = {}
	for u in b.party:
		seen[u.rank] = true
	t.eq(seen.size(), 4, "换位后 rank 互不重复")


# ------------------------------------------------------------
# 辅助
# ------------------------------------------------------------

## 一定命中的探针攻击：伤害固定、无附带效果，只用来观察「掉在谁身上」。
##
## 两个数都是被规则层逼出来的，不是随手写的：
##   atk 不能给 0 —— `_resolve_action` 用 `atk <= 0` 判定「这是纯功能技」，
##     给 0 会让探针掉进 utility 分支，一刀伤害都不打。
##   atk 还得给足 1.0 —— 怪物没有 acc（monster_base 里 acc 恒为 0），
##     命中率就是 atk 本身。给 0.5 的话每次探针都是一半概率，断言随机红。
static func _probe(actor: Combatant) -> Dictionary:
	return {
		"id": "test_probe", "type": "melee", "level": 0,
		"atk": 1.0, "dmg_mod": 0.0, "dmg_range": PROBE_DMG, "crit": 0.0,
		"launch_mask": 0, "target_mask": 0, "target_aoe": false,
		"friendly": false, "effects": [], "crit_valid": true,
		"ignore_prot": false, "ignore_guard": false,
		"heal": 0.0, "heal_range": [0.0, 0.0], "move": [],
		"per_turn_limit": 0, "per_battle_limit": 0,
		"is_stall_invalidating": false, "is_continue_turn": false,
		"self_target_valid": false,
		"is_guard": false, "is_riposte": false,
	}


static func _skill(u: Combatant, id: String) -> Dictionary:
	for a in u.actions:
		if str(a.get("id", "")) == id:
			return a
	return {}


static func _event(events: Array, type_name: String) -> Dictionary:
	for e in events:
		if str(e.get("t", "")) == type_name:
			return e
	return {}

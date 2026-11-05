class_name EffectResolver
extends RefCounted
## 效果结算。
##
## DD1 的技能不是「造成 X 伤害」，而是「造成伤害 + 一串 effect 引用」。
## effect 才是原子单位：一次攻击的伤害修正、流血、眩晕、压力、增益，
## 全部是挂在技能上的 effect 条目。所以这个文件才是战斗逻辑真正的主干。
##
## 结算分两趟，这个顺序不能反：
##   第一趟（攻击前）  collect_attack_mods —— 收集本次攻击的伤害/命中/暴击修正
##   第二趟（攻击后）  apply                —— 施加伤害之外的状态变化
## 之所以要分两趟：像「对邪物 +15% 伤害」这种 effect，必须在掷伤害之前生效；
## 而「造成流血」必须在命中之后。两者写在同一个 effect 列表里，靠 target 字段
## 和是否有 damage_multiply 区分。

## 第一趟：收集本次攻击的修正。
##
## 只有 target == "performer" 的 effect 才算「本次攻击修正」——
## 它描述的是攻击者这一击的特性，不是给谁上 buff。
## target == "target" 的 damage_multiply 是持久增伤（给宝宝/怪物上的 buff），
## 走第二趟进 buffs。
static func collect_attack_mods(db: DdDb, effect_names: Array, attacker: Combatant, target: Combatant) -> Dictionary:
	var out: Dictionary = {
		"damage_mod": 0.0,
		"acc": 0.0,
		"crit": 0.0,
		"reasons": [],
	}
	for name in effect_names:
		var e: Dictionary = db.effect(str(name))
		if e.is_empty():
			continue
		if str(e.get("target", "")) != "performer":
			continue
		if not _conditions_met(e, attacker, target):
			continue

		if e.has("damage_low_multiply"):
			out.damage_mod += float(e.get("damage_low_multiply", 0.0))
			out.reasons.append(str(name))
		if e.has("attack_rating_add"):
			out.acc += float(e.get("attack_rating_add", 0.0))
		if e.has("crit_chance_add"):
			out.crit += float(e.get("crit_chance_add", 0.0))
	return out


## 条件判定：monsterType 要求目标属于该怪物类型，keyStatus 要求目标带有该状态。
## 这两条覆盖了数据里全部 66 条带条件的伤害修正。
static func _conditions_met(e: Dictionary, attacker: Combatant, target: Combatant) -> bool:
	if e.has("monsterType"):
		if not target.enemy_types.has(str(e["monsterType"])):
			return false
	if e.has("keyStatus"):
		if not target.has_status(str(e["keyStatus"])):
			return false
	return true


## 第二趟：施加状态类效果。
##
## ctx: { hit:bool, rng:DdRng, all_units:Array, log:Array }
static func apply(db: DdDb, effect_names: Array, attacker: Combatant, targets: Array, ctx: Dictionary) -> Array:
	var rng: DdRng = ctx.get("rng")
	var hit: bool = bool(ctx.get("hit", true))
	var results: Array = []

	for name in effect_names:
		var e: Dictionary = db.effect(str(name))
		if e.is_empty():
			continue

		# on_hit / on_miss 门控。
		#
		# 这两个字段在数据里的类型并不干净：on_hit 全是 bool，但 on_miss
		# 有 3 条是**列表**。所以既不能写 bool(...)（GDScript 4 的
		# bool(null) 会抛「Nonexistent 'bool' constructor」），
		# 也不能写 == true（Array == bool 直接是非法运算）。
		# 只有「显式 true」才算真，其余一律假——它们本来就是开关，不是数值。
		var allow: bool = _flag(e.get("on_hit", false)) if hit else _flag(e.get("on_miss", false))
		if not allow:
			continue

		# 概率门控
		var chance: float = float(e.get("chance", 1.0))
		if chance < 1.0 and not rng.chance(chance):
			continue

		for t in _scope_targets(db, e, attacker, targets, ctx):
			if t == null or not t.is_alive():
				continue
			if not _conditions_met(e, attacker, t):
				continue
			var r: Dictionary = _apply_one(db, e, attacker, t, rng, ctx)
			if not r.is_empty():
				r["effect"] = str(name)
				r["target"] = t.uid
				results.append(r)
	return results


## 作用域。数据里出现的 5 种全部覆盖。
static func _scope_targets(db: DdDb, e: Dictionary, attacker: Combatant, targets: Array, ctx: Dictionary) -> Array:
	var scope: String = str(e.get("target", "target"))
	var all_units: Array = ctx.get("all_units", [])
	match scope:
		"performer":
			return [attacker]
		"target":
			return targets
		"global":
			return all_units
		"performer_group_other":
			var out: Array = []
			for u in all_units:
				if u != attacker and u.side == attacker.side:
					out.append(u)
			return out
		"target_group":
			var out2: Array = []
			for u in all_units:
				if u.side != attacker.side:
					out2.append(u)
			return out2
		_:
			return targets


## 数据里的「开关字段」取值。只有显式 true 才算真。
##
## 存在理由：on_miss 有 3 条是列表，bool(null) 会抛异常，Array 和 bool
## 之间连 == 都是非法运算。这三种情况在同一个字段上同时出现过，
## 所以不能靠任何一种简写蒙过去。
static func _flag(v: Variant) -> bool:
	return v is bool and (v as bool)


## 把「单值 或 与候选等长的列表」摊平成等长数组。
##
## 召唤数据里 summon_chances / summon_limits / summon_ranks 三个字段都是
## 这种双形态：单个怪时写一个数，多个候选时写一个等长列表。
## 长度不匹配时**按下标能取多少取多少、不足的填默认值**，
## 而不是整体退化——下标错位的后果是「第二个候选拿到第一个候选的上限」，
## 不会报错，只是行为悄悄变成另一个东西。
static func _aligned(v: Variant, n: int, dflt: float) -> Array:
	var out: Array = []
	for i in n:
		if v is Array and i < (v as Array).size():
			out.append(float((v as Array)[i]))
		elif v is float or v is int:
			out.append(float(v))
		else:
			out.append(dflt)
	return out


static func _apply_one(db: DdDb, e: Dictionary, attacker: Combatant, t: Combatant, rng: DdRng, ctx: Dictionary = {}) -> Dictionary:
	var duration: int = int(e.get("duration", 0))
	var out: Dictionary = {}
	# 位移抗性的开关（M11 对照实验用）。关掉只影响 push/pull/洗位，
	# 其余抗性（眩晕/流血/中毒）走各自的分支，不受这个开关影响。
	var move_resist_on: bool = bool(ctx.get("move_resist_enabled", true))

	# —— 持续性伤害 ——
	if e.has("dotBleed"):
		var res: float = t.resistance("bleed")
		if rng.next_float() >= res:
			t.add_dot("bleed", int(e["dotBleed"]), maxi(duration, 1))
			out["dot"] = "bleed"
			out["amount"] = int(e["dotBleed"])
			return out
		out["resisted"] = "bleed"
		return out
	if e.has("dotPoison"):
		var res2: float = t.resistance("poison")
		if rng.next_float() >= res2:
			t.add_dot("poison", int(e["dotPoison"]), maxi(duration, 1))
			out["dot"] = "poison"
			out["amount"] = int(e["dotPoison"])
			return out
		out["resisted"] = "poison"
		return out
	if e.has("dotStress"):
		t.add_dot("stress", int(e["dotStress"]), maxi(duration, 1))
		out["dot"] = "stress"
		out["amount"] = int(e["dotStress"])
		return out

	# —— 眩晕：基础概率减去目标眩晕抗性 ——
	if e.has("stun"):
		var stun_chance: float = clampf(float(e.get("chance", 1.0)) - t.resistance("stun"), 0.0, 1.0)
		if rng.chance(stun_chance):
			t.stun_turns = maxi(t.stun_turns, int(e["stun"]))
			out["stun"] = int(e["stun"])
			out["chance"] = stun_chance
		else:
			out["resisted"] = "stun"
		return out

	# —— 压力 / 减压 ——
	if e.has("stress"):
		var delta: float = t.add_stress(float(e["stress"]))
		out["stress"] = delta
		return out
	if e.has("healstress"):
		var before: float = t.stress
		t.stress = clampf(t.stress - float(e["healstress"]), 0.0, 200.0)
		out["stress"] = t.stress - before
		return out

	# —— 治疗 ——
	if e.has("heal"):
		var healed: int = t.heal(int(e["heal"]))
		out["heal"] = healed
		return out

	# —— 位移 ——
	# 约定用「rank 增量」：正数往后（push），负数往前（pull）。
	# 原实现写成 `-push + pull`，符号是反的——push 一格会算出 -1，
	# 消费方按「往后」解读就会把人往前推。这种错不会有任何报错，
	# 只会让推拉看起来「作用了但方向不对」。
	#
	# 位移吃目标的 move 抗性（M11）。数据里英雄 0.2~0.4、怪物 0~0.95
	# （原始值大于 0.95 的会在 resistance() 里被 clamp，表示「基本推不动」）。
	#
	# `res > 0` 这个短路不是优化，是**正确性**：不判的话，抗性为 0 的单位
	# 也会白白消耗一次随机数，整个 rng 序列跟着错位——逻辑上等价，数字全变。
	if e.has("push") or e.has("pull"):
		var move_res: float = t.resistance("move")
		if move_resist_on and move_res > 0.0 and rng.next_float() < move_res:
			out["resisted"] = "move"
			return out
		out["move"] = int(e.get("push", 0)) - int(e.get("pull", 0))
		return out

	# —— 洗位（M11）——
	#
	# 和 push/pull 的区别：push/pull 是「沿阵型挪 N 格」，洗位是「换到另一个槽」。
	# 数据里两个键的值都是 null，只有「有没有」这一个信息。
	#
	#   shuffletarget  把**这一个单位**随机换到己方另一个槽
	#   shuffleparty   把**整个阵营**打乱
	#
	# `Shuffle Self` 的 target 是 performer（怪物自己乱跳），所以 t == attacker
	# 时不吃抗性——自己抖一下还要过自己的抗性，等于「这只怪有 95% 概率拒绝
	# 自己跳」，数据里显然不是这个意思。
	if e.has("shuffletarget") or e.has("shuffleparty"):
		var shuf_res: float = t.resistance("move")
		if move_resist_on and t != attacker and shuf_res > 0.0 and rng.next_float() < shuf_res:
			out["resisted"] = "move"
			return out
		out["shuffle"] = "team" if e.has("shuffleparty") else "target"
		return out

	# —— 守护 / 解除守护（M10）——
	#
	# 这三条数据从 M0 就在库里（MAA Guard 1 / Clear Guard Performer /
	# Antiq ProtectMe Guard），但 M1~M9 从来没解析过：`guard` 落到函数末尾的
	# 兜底分支变成空字典，于是「战争老兵的守护」在战斗里等于什么都没发生。
	#
	# 这里只负责**表达意图**，不碰守护关系表——表在 Battle 里（见 _guards）。
	# 和 move 一样：解析层说「要守护」，编排层决定「守护意味着什么」。
	if e.has("guard") or e.has("clearguarding") or e.has("clearguarded"):
		if e.has("clearguarding"):
			out["clear_guarding"] = true      # t 不再守护别人
		if e.has("clearguarded"):
			out["clear_guarded"] = true       # t 不再被别人守护
		if e.has("guard"):
			out["guard"] = true
			out["guard_turns"] = maxi(duration, 1)
			# 古物学家的「保护我」顺带把自己和被保护者换个位置：
			# 她站后排，把人拽到身后。数据用 swap_source_and_target 标这件事。
			if bool(e.get("swap_source_and_target", false)):
				out["swap"] = true
		return out

	# —— 反击（M10）——
	#
	# riposte 是「授予一个受击还手的姿态」，不是一次攻击。真正的还手发生在
	# Battle._try_riposte 里——因为「被打中」这件事只有编排层知道。
	#
	# damage_low_multiply 是负的（-0.4）：反击伤害 = 武器伤害 × (1 - 0.4)。
	# 等级越高负得越少，反击越疼——这是数据本来的设计，不是笔误。
	if e.has("riposte"):
		out["riposte"] = true
		out["riposte_turns"] = maxi(duration, 1)
		out["riposte_mult"] = 1.0 + float(e.get("damage_low_multiply", 0.0))
		out["riposte_on_hit"] = float(e.get("riposte_on_hit_chance_add", 1.0))
		out["riposte_on_miss"] = float(e.get("riposte_on_miss_chance_add", 1.0))
		return out

	# —— 标记类状态 ——
	if e.has("keyStatus"):
		var key: String = str(e["keyStatus"])
		t.add_status(key, maxi(duration, 1))
		out["status"] = key
		return out

	# —— 即死 ——
	if e.has("kill"):
		t.dead = true
		t.hp = 0
		out["killed"] = true
		return out

	# —— buff 引用 ——
	if e.has("buff_ids"):
		var ids: Variant = e["buff_ids"]
		var list: Array = ids if ids is Array else [ids]
		var applied: Array = []
		for bid in list:
			var b: Dictionary = db.buff(str(bid))
			if b.is_empty():
				continue
			t.add_buff(b, maxi(duration, 1))
			applied.append(str(bid))
		if not applied.is_empty():
			out["buffs"] = applied
			out["duration"] = duration
			return out

	# —— 内联属性修正（无 buff_ids 的临时增益）——
	var inline: Dictionary = {}
	for pair in [["attack_rating_add", "combat_stat_add", "attack_rating"],
				 ["crit_chance_add", "combat_stat_add", "crit_chance"],
				 ["defense_rating_add", "combat_stat_add", "defense_rating"],
				 ["speed_rating_add", "combat_stat_add", "speed_rating"],
				 ["protection_rating_add", "combat_stat_add", "protection_rating"],
				 ["damage_low_multiply", "combat_stat_multiply", "damage_low"],
				 ["damage_high_multiply", "combat_stat_multiply", "damage_high"]]:
		var field: String = pair[0]
		if e.has(field):
			inline[field] = float(e[field])
			t.add_ad_hoc_buff(str(e.get("name", "adhoc")), pair[1], pair[2], float(e[field]), maxi(duration, 1))
	if not inline.is_empty():
		out["inline"] = inline
		return out

	# —— 召唤（M12）——
	#
	# 59 条数据、35 只怪，从 M0 就在库里，M1~M11 一直落到这里返回
	# `unsupported = "summon"`。于是「召唤者」在战斗里等于一个只会平砍的普通怪，
	# 而 DD1 里收藏家、死灵法师、海盗炮船的核心威胁正是「你打不完」。
	#
	# 数据有两种形态，必须都吃：
	#   summon_monsters  字符串 "brigand_fuseman_A"  或  列表 ["a", "b"]
	#   summon_chances   单值 1.0  或  与列表等长的权重 [2.0, 1.0]
	# 单值写成字符串这一点，Python 侧遍历会把它拆成单字符——M11 已经踩过一次，
	# 这里在解析层统一成数组，下游就不必再判类型。
	#
	# 语义分工和 push/guard 一致：解析层只说「要召唤什么、几只、上限多少」，
	# 至于「格子满了怎么办、尸体能不能让位」，是 Battle 的事。
	if e.has("summon_monsters"):
		var raw: Variant = e["summon_monsters"]
		var ids: Array = []
		if raw is Array:
			for x in (raw as Array):
				ids.append(str(x))
		else:
			# 单值时数据写的是字符串，不是字符串数组。Python 侧遍历字符串
			# 会拆成单字符（M11 踩过），所以这里必须显式包一层。
			ids.append(str(raw))

		out["summon"] = true
		out["summon_list"] = ids
		out["summon_weights"] = _aligned(e.get("summon_chances", 1.0), ids.size(), 1.0)
		out["summon_limits"] = _aligned(e.get("summon_limits", 0.0), ids.size(), 0.0)
		out["summon_count"] = int(e.get("summon_count", 1))
		# summon_ranks 是**位掩码**，不是槽位号。证据：brigand_sapper 写 12，
		# 按槽位号无解，按位掩码是 0b1100 = 3、4 号位（近战在后排）。
		# 同一份数据里 brigand_cannon 的 [1, 4] 对应 [cutthroat, fusilier]：
		# 割喉贼 1 号位、火枪手 3 号位——位掩码解释在语义上自洽。
		# 0 表示「数据没指定」，由 Battle 找空位。
		out["summon_ranks"] = _aligned(e.get("summon_ranks", 0.0), ids.size(), 0.0)
		out["summon_loot"] = _flag(e.get("summon_can_spawn_loot", true))
		out["summon_erase"] = _flag(e.get("summon_erase_data_on_roll", false))
		return out

	# 其余（奇物专用、变形等）不属战斗循环
	if e.has("cure"):
		out["unsupported"] = "cure"
	elif e.has("disease"):
		out["unsupported"] = "disease"
	return out


## 持续性伤害结算（回合末调用）。
##
## rng 必须传：死门上的持续伤害也要过一次死击抗性。原实现用默认 1.0
## （必定死亡），等于「死门上挂一个流血就必死」——这是把随机性写死成最坏情况。
static func tick_dots(actor: Combatant, rng: DdRng = null) -> Array:
	var out: Array = []
	if actor.dead:
		return out
	var kept: Array = []
	for d in actor.dots:
		var amount: int = int(d.amount)
		if d.kind == "stress":
			actor.add_stress(float(amount))
			out.append({"kind": "stress", "amount": amount})
		else:
			var roll: float = 1.0 if rng == null else rng.next_float()
			var r: Dictionary = actor.take_damage(amount, roll)
			out.append({"kind": d.kind, "amount": int(r.damage), "died": bool(r.died)})
		d.remaining = int(d.remaining) - 1
		if int(d.remaining) > 0:
			kept.append(d)
	actor.dots = kept
	return out

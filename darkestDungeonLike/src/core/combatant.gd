class_name Combatant
extends RefCounted
## 战斗单位：英雄或怪物的运行时状态。
##
## 分三层：
##   基础层  base_*      装备/怪物配置给定的固定值，战斗内不变
##   修正层  buffs[]     战斗中获得的临时/持久修正
##   状态层  hp/stress/dots/statuses
## 取值一律走方法（speed()/dodge()/...），不要在外部直接读 base_*，
## 否则 buff 会被静默忽略——这是移植时最典型的一类 bug。

const SIDE_PARTY: String = "party"
const SIDE_ENEMY: String = "enemy"

var uid: int = 0
var def_id: String = ""          # hero id 或 monster id
## 名册上的实例 id（M34）。英雄才有，怪物留空。
##
## `def_id` 回答「这个人是干什么的」（查数值表用），`hero_key` 回答
## 「这是名册上的哪一个人」（记状态用）。同职业多人之后这两件事必须分开：
## 两个十字军的 def_id 一样，但他们的血量、压力、怪癖各归各的。
var hero_key: String = ""
var display_name: String = ""
var side: String = SIDE_PARTY
var rank: int = 0                # 0 基站位
var size: int = 1
var is_hero: bool = true

# —— 基础层 ——
var base_hp: int = 1
var base_dodge: float = 0.0
var base_prot: float = 0.0
var base_speed: float = 0.0
var base_crit: float = 0.0
var base_acc: float = 0.0
var base_dmg_low: float = 0.0
var base_dmg_high: float = 0.0

# —— 状态层 ——
var hp: int = 1
var stress: float = 0.0
var dead: bool = false
var at_deaths_door: bool = false
var stun_turns: int = 0
var consecutive_misses: int = 0
var buffs: Array = []            # {id, stat_type, stat_sub_type, amount, remaining, source}
## 怪癖（M14）。
##
## 为什么不直接塞进 buffs：buffs 是**战斗内**的临时状态，战斗结束要清、
## 同名要刷新持续时间、死门减益靠 id 反查删除。怪癖是**跨远征的**，
## 生命周期完全不同，混进去会让「清 buff」顺手把人物性格洗掉。
##
## 所以分两条通道：quirk_pool 是原始定义（带 rule_type），
## _quirk_active 是「按当前语境筛过一遍」的结果。
## 读取数值时两条都算，写入时各管各的。
var quirk_ids: Array = []
var quirk_lib: QuirkLib = null
var quirk_pool: Array = []       # 全部怪癖 buff 原始定义（含 rule_type / rule_data）
var quirk_ctx: Dictionary = {}   # 最近一次刷新的语境，供调试与自检查看
var _quirk_active: Array = []    # 当前语境下生效的子集

## —— 饰品（M15）——
##
## 走的是和怪癖**同一条**外部 buff 通道，但分成独立的池。
## 不分会因为两件事出错：一是「这人的怪癖有几条在生效」要能单独回答，
## 二是卸下饰品时不该动到怪癖（反过来也一样）。
## 判定规则完全一致（BuffRules），饰品只多 6 种 rule_type。
var trinket_ids: Array = []
var trinket_lib: TrinketLib = null
var trinket_pool: Array = []     # 全部饰品 buff 原始定义
var _trinket_active: Array = []  # 当前语境下生效的子集
var dots: Array = []             # {kind, amount, remaining}
var statuses: Dictionary = {}    # "tagged" -> 剩余回合
var resistances: Dictionary = {}
var enemy_types: Array = []      # ["unholy"], ["man"], ...
var tags: Array = []

# —— 远征层携带状态（M3）——
# 崩溃/美德不是「战斗内的临时状态」：它一旦触发就跟着英雄走完整个远征，
# 所以必须存在 Combatant 上而不是 Battle 上——每场战斗新建 Combatant 时由
# Expedition 把这几项重新灌回去。
var affliction: String = ""      # "fearful"/"paranoid"...；空 = 未崩溃
var virtue: String = ""          # "stalwart"/"courageous"...；空 = 未觉醒
var stress_in_mult: float = 1.0  # 环境（光照）造成的受压倍率

## 等级惩罚造成的受压倍率（M29）。英雄比任务低 N 级时 = 1 + 0.25N。
##
## **必须和 `stress_in_mult` 分开**，不能塞进同一个字段：
## 那个每场战斗都会被 `Battle.set_environment` 整个覆盖掉（光照一变就重算），
## 而这个整趟远征固定不变。合在一起的话，走进暗处那一刻等级惩罚就没了。
var join_stress_mult: float = 1.0
var initiative_bonus: float = 0.0
var dd_buff_ids: Array = []      # 死门减益 buff id，离开死门时要按名删除
var recovered_from_dd: bool = false  # 刚被救回，Battle 负责补「恢复期」减益
var recovering: bool = false         # 恢复期未过：跨战斗保留「久病」减益
var heart_attacked: bool = false     # 由心脏骤停进入死门，恢复时用更重的一组减益

# —— 行动 ——
var actions: Array = []          # 见 DdDb.build_actions 产出的规范化技能
## 移动技能（M9）。空字典 = 这个单位不能主动换位。
##
## 和普通技能分开存，是因为「移动」的目标是**位置**而不是单位，
## 塞进 actions 会让 _legal_targets / 评分全部要写特例。
var move_action: Dictionary = {}
var per_battle_uses: Dictionary = {}
var per_turn_uses: Dictionary = {}

# —— 命中/暴击倍率表（由 Battle 注入）——
var crit_table: Array = [{"chance": 1, "value": 1.5}]
var crit_mult_value: float = 1.5


## `selected` 为已装备的技能 id 列表（M19）。**空 = 全部装上**——
## 这是 M1~M18 的历史行为，bench 与旧基线要靠它复现，
## 所以默认值不能改，只能在调用方显式传入时才收窄。
func setup_from_hero(db: DdDb, hero_id: String, gear_level: int, skill_level: int,
		selected: Array = []) -> bool:
	var h: Dictionary = db.hero(hero_id)
	if h.is_empty():
		push_error("Combatant: 未知英雄 %s" % hero_id)
		return false
	is_hero = true
	def_id = hero_id
	display_name = hero_id.capitalize()
	var b: Dictionary = db.hero_base(hero_id, gear_level)
	_apply_base(b)
	resistances = {}
	for k in (h.get("resistances", {}) as Dictionary):
		resistances[str(k)] = float(h["resistances"][k])
	enemy_types = []
	tags = h.get("tags", [])
	actions = build_actions(filter_actions(h.get("skills", []), selected), skill_level, true)
	# 移动技能：数据里是单独一条扁平记录，不在 skills 数组里，
	# M1~M8 一直没解析，所以英雄从来不能换位。
	var ms: Variant = h.get("move_skill", {})
	if ms is Dictionary and not (ms as Dictionary).is_empty():
		var built: Array = build_actions([ms], 0, true)
		if not built.is_empty():
			move_action = built[0]
	crit_table = db.rules.player_crit_table
	crit_mult_value = _resolve_crit_mult()
	hp = base_hp
	return true


func setup_from_monster(db: DdDb, monster_id: String, skill_level: int = 0) -> bool:
	var m: Dictionary = db.monster(monster_id)
	if m.is_empty():
		push_error("Combatant: 未知怪物 %s" % monster_id)
		return false
	is_hero = false
	def_id = monster_id
	display_name = monster_id
	var b: Dictionary = db.monster_base(monster_id)
	_apply_base(b)
	resistances = {}
	var resist_keys: Array = ["stun_resist", "poison_resist", "bleed_resist",
		"debuff_resist", "move_resist", "death_blow_resist"]
	for key in resist_keys:
		resistances[key.replace("_resist", "")] = float(b.get(key, 0.0))
	enemy_types = m.get("enemy_types", [])
	size = int(m.get("size", 1))
	actions = build_actions(m.get("skills", []), skill_level, false)
	crit_table = db.rules.monster_crit_table
	crit_mult_value = _resolve_crit_mult()
	hp = base_hp
	return true


## 暴击倍率表当前只有一条 {chance:1, value:1.5}，取末项即可。
## 若将来换成多条权重表，这里需要改成逐次抽取——接口保持不变。
func _resolve_crit_mult() -> float:
	if crit_table.is_empty():
		return 1.5
	return float((crit_table[-1] as Dictionary).get("value", 1.5))


func _apply_base(b: Dictionary) -> void:
	base_hp = int(b.get("hp_max", 1))
	base_dodge = float(b.get("dodge", 0.0))
	base_prot = float(b.get("prot", 0.0))
	base_speed = float(b.get("speed", 0.0))
	base_crit = float(b.get("crit", 0.0))
	base_acc = float(b.get("acc", 0.0))
	base_dmg_low = float(b.get("dmg_low", 0.0))
	base_dmg_high = float(b.get("dmg_high", 0.0))


# ============================================================
# 技能规范化
# ============================================================

## 按已装备的技能 id 收窄技能池（M19）。
##
## **保持数据里的原始顺序**，不按传入顺序重排：战斗栏的按钮位置必须
## 跟 `heroes.json` 一致，否则同一个英雄在不同存档里技能顺序会跳。
## 空列表原样返回，等于「全装」。
static func filter_actions(pool: Array, selected: Array) -> Array:
	if selected.is_empty():
		return pool
	var want: Dictionary = {}
	for sid in selected:
		want[str(sid)] = true
	var out: Array = []
	for s in pool:
		if not (s is Dictionary):
			continue
		if want.has(str((s as Dictionary).get("id", ""))):
			out.append(s)
	return out


## 把原始技能配置转成战斗可直接用的结构。
##
## 站位编码：`.launch 21` 表示可从己方 1、2 号位发动，`.target 12` 表示
## 可命中敌方 1、2 号位；前缀 `~` 表示对该集合全体生效（AOE）。
## 用位掩码表达后，判定就是 `mask & (1 << rank)`。
static func build_actions(skills: Array, level: int, is_hero_action: bool) -> Array:
	var out: Array = []
	for s in skills:
		# 两种数据形状：英雄技能是 {id, levels:[...], art}，带 5 个等级；
		# 怪物技能是扁平的，字段直接摊在技能字典上。这里统一处理，
		# 否则怪物会一条技能都装不上——而且不会报错，只是「站着不动」。
		var levels: Array = s.get("levels", [])
		var lv: Dictionary
		if levels.is_empty():
			lv = s
		else:
			lv = levels[clampi(level, 0, levels.size() - 1)]
		var launch: Dictionary = _parse_rank_mask(str(lv.get("launch", "")))
		var target: Dictionary = _parse_rank_mask(str(lv.get("target", "")))

		var dmg_mod: float = 0.0
		var dmg_range: Array = []
		var raw_dmg: Variant = lv.get("dmg", 0.0)
		if raw_dmg is Array and (raw_dmg as Array).size() >= 2:
			dmg_range = [float(raw_dmg[0]), float(raw_dmg[1])]
		elif raw_dmg is float or raw_dmg is int:
			if is_hero_action:
				dmg_mod = float(raw_dmg)      # 英雄：百分比修正（叠在武器伤害上）
			else:
				dmg_range = [float(raw_dmg), float(raw_dmg)]

		# 治疗量在数据里是区间 [low, high]，不是单值
		var heal_low: float = 0.0
		var heal_high: float = 0.0
		var raw_heal: Variant = lv.get("heal", 0.0)
		if raw_heal is Array and (raw_heal as Array).size() >= 2:
			heal_low = float(raw_heal[0])
			heal_high = float(raw_heal[1])
		elif raw_heal is float or raw_heal is int:
			heal_low = float(raw_heal)
			heal_high = float(raw_heal)

		out.append({
			"id": str(lv.get("id", s.get("id", "?"))),
			"type": str(lv.get("type", "melee")),
			"level": int(lv.get("level", level)),
			"atk": float(lv.get("atk", 0.0)),
			"dmg_mod": dmg_mod,
			"dmg_range": dmg_range,
			"crit": float(lv.get("crit", 0.0)),
			"launch_mask": int(launch.mask),
			"target_mask": int(target.mask),
			"target_aoe": bool(target.aoe),
			"friendly": bool(target.friendly),
			"effects": DdDb.effect_names(lv),
			"crit_valid": bool(lv.get("is_crit_valid", true)),
			"ignore_prot": bool(lv.get("ignore_protection", false)),
			"ignore_guard": bool(lv.get("ignore_guard", false)),
			"heal": (heal_low + heal_high) * 0.5,
			"heal_range": [heal_low, heal_high],
			"move": lv.get("move", []),
			"per_turn_limit": int(lv.get("per_turn_limit", 0)),
			"per_battle_limit": int(lv.get("per_battle_limit", 0)),
			"is_stall_invalidating": bool(lv.get("is_stall_invalidating", false)),
			"is_continue_turn": bool(lv.get("is_continue_turn", false)),
			"self_target_valid": bool(lv.get("self_target_valid", false)),
		})
	return out


## 站位字符串解码。三种前缀：
##   `~` 对该集合全体生效（AOE）
##   `@` 目标是友方（治疗/增益）——这是数据里唯一区分敌我的标记
## 例如 "~12" = 敌方 1、2 号位 AOE；"@1234" = 友方任选一人；"@~1234" = 友方全体
static func _parse_rank_mask(text: String) -> Dictionary:
	var aoe: bool = text.contains("~")
	var friendly: bool = text.contains("@")
	var mask: int = 0
	for i in text.length():
		var ch: String = text.substr(i, 1)
		if ch >= "1" and ch <= "9":
			mask |= 1 << (int(ch) - 1)
	return {"mask": mask, "aoe": aoe, "friendly": friendly}


# ============================================================
# 派生属性
# ============================================================

## 下面四个取值函数同时遍历三条通道：buffs（战斗内临时）、
## _quirk_active（怪癖）、_trinket_active（饰品）。
##
## 写成两个循环而不是拼一个数组，是因为这些函数在每次伤害计算里会被调很多次，
## 每次拼接都会分配一个新 Array。多一个循环是这里最便宜的代价。
func _sum_add(sub_type: String) -> float:
	var total: float = 0.0
	for b in buffs:
		if b.stat_type == "combat_stat_add" and b.stat_sub_type == sub_type:
			total += float(b.amount)
	for b in _quirk_active:
		if b.stat_type == "combat_stat_add" and b.stat_sub_type == sub_type:
			total += float(b.amount)
	for b in _trinket_active:
		if b.stat_type == "combat_stat_add" and b.stat_sub_type == sub_type:
			total += float(b.amount)
	return total


func _product_mult(sub_type: String) -> float:
	var total: float = 1.0
	for b in buffs:
		if b.stat_type == "combat_stat_multiply" and b.stat_sub_type == sub_type:
			total *= (1.0 + float(b.amount))
	for b in _quirk_active:
		if b.stat_type == "combat_stat_multiply" and b.stat_sub_type == sub_type:
			total *= (1.0 + float(b.amount))
	for b in _trinket_active:
		if b.stat_type == "combat_stat_multiply" and b.stat_sub_type == sub_type:
			total *= (1.0 + float(b.amount))
	return total


func _sum_stat(stat_type: String) -> float:
	var total: float = 0.0
	for b in buffs:
		if b.stat_type == stat_type:
			total += float(b.amount)
	for b in _quirk_active:
		if b.stat_type == stat_type:
			total += float(b.amount)
	for b in _trinket_active:
		if b.stat_type == stat_type:
			total += float(b.amount)
	return total


func speed() -> float:
	return base_speed + _sum_add("speed_rating")


func dodge() -> float:
	return clampf(base_dodge + _sum_add("defense_rating"), 0.0, 0.95)


func prot() -> float:
	return clampf(base_prot + _sum_add("protection_rating"), 0.0, 0.99)


func crit() -> float:
	return clampf(base_crit + _sum_add("crit_chance"), 0.0, 1.0)


func acc() -> float:
	return base_acc + _sum_add("attack_rating") + consecutive_misses * 0.04


## 持久伤害倍率（buff 类修正，连乘）
func damage_mult(kind: String) -> float:
	return _product_mult("damage_low" if kind == "low" else "damage_high")


## 受到伤害的修正（如 +25% 则 0.25）
func damage_taken_mod() -> float:
	return _sum_stat("damage_received_percent")


func stress_taken_mod() -> float:
	return _sum_stat("stress_dmg_received_percent")


func resistance(kind: String) -> float:
	var base_val: float = float(resistances.get(kind, 0.0))
	for b in buffs:
		if b.stat_type == "resistance" and b.stat_sub_type == kind:
			base_val += float(b.amount)
	for b in _quirk_active:
		if b.stat_type == "resistance" and b.stat_sub_type == kind:
			base_val += float(b.amount)
	for b in _trinket_active:
		if b.stat_type == "resistance" and b.stat_sub_type == kind:
			base_val += float(b.amount)
	return clampf(base_val, -1.0, 0.95)


func hp_ratio() -> float:
	return float(hp) / float(maxi(base_hp, 1))


## 死门不是「死了」。
##
## 这里踩过一个很隐蔽的坑：原先写成 `hp > 0`，于是英雄一进死门就被
## living()/行动序/targeting 全部排除——等于进了死门就直接消失，
## 后面所有「死门上再挨一下才真死」的规则都成了死代码。
## 死门上的英雄仍然行动、仍然可被选为目标，只是血量锁定在 0。
func is_alive() -> bool:
	return not dead and (hp > 0 or at_deaths_door)


func can_act() -> bool:
	return is_alive() and stun_turns <= 0


# ============================================================
# 状态变更
# ============================================================

func add_buff(buff_def: Dictionary, duration: int = 0) -> void:
	var entry: Dictionary = {
		"id": str(buff_def.get("id", "?")),
		"stat_type": str(buff_def.get("stat_type", "")),
		"stat_sub_type": str(buff_def.get("stat_sub_type", "")),
		"amount": float(buff_def.get("amount", 0.0)),
		"remaining": duration,
	}
	# 同名 buff 刷新持续时间而非叠加，避免同一 buff 每回合叠一层导致数值爆炸
	for i in buffs.size():
		if buffs[i].id == entry.id and buffs[i].stat_sub_type == entry.stat_sub_type:
			buffs[i].remaining = maxi(int(buffs[i].remaining), duration)
			return
	buffs.append(entry)


func add_ad_hoc_buff(id: String, stat_type: String, sub_type: String, amount: float, duration: int) -> void:
	add_buff({"id": id, "stat_type": stat_type, "stat_sub_type": sub_type, "amount": amount}, duration)


# ============================================================
# 怪癖（M14）
# ============================================================

## 挂上怪癖。必须在 `hp = base_hp` 之后调用——
## max_hp 类怪癖改的是 base_hp 这个分母，早于赋值会被覆盖掉。
##
## 返回值是本次实际把最大生命乘了多少，供 Battle / 测试核对。
func set_quirks(ids: Array, lib: QuirkLib) -> float:
	quirk_lib = lib
	quirk_ids = ids.duplicate()
	quirk_pool = []
	if lib != null and lib.is_loaded():
		quirk_pool = lib.buffs_for(quirk_ids)

	# max_hp 必须在注入时一次性算掉（见 QuirkLib.max_hp_mult 的注释）。
	# 血量按同比例缩放，否则「装上 +10% 生命的怪癖」会顺手把伤治了。
	var mult: float = 1.0
	if lib != null and lib.is_loaded():
		mult = lib.max_hp_mult(quirk_ids)
	if not is_zero_approx(mult) and not is_equal_approx(mult, 1.0):
		var old_max: int = base_hp
		var new_max: int = maxi(1, int(round(float(base_hp) * mult)))
		base_hp = new_max
		if old_max > 0:
			hp = clampi(int(round(float(hp) * float(new_max) / float(old_max))), 0, new_max)
	# 其余 buff 交给语境刷新；初始语境只有「无条件」那批会生效
	refresh_quirks({})
	return mult


## 按当前语境重算生效子集。
##
## 调用点：战斗开始、每轮开始、以及**每次行动前**。最后一条是必要的——
## 「只对近战生效」「只在首轮生效」这类条件随行动本身变化，
## 一轮刷一次会让它们永远差半拍。
##
## 不消耗 rng：纯查表，随便刷。
func refresh_quirks(ctx: Dictionary) -> void:
	quirk_ctx = ctx.duplicate()
	_quirk_active = []
	_trinket_active = []
	# 两个池走同一个判定器（BuffRules），分别收进各自的生效列表。
	# 饰品池即使 quirk_lib 为空也要刷——不然「只有饰品、没有怪癖」的人
	# 会连自己的饰品都不生效，而这种组合在后期是常态。
	if quirk_lib != null and quirk_lib.is_loaded():
		_quirk_active = BuffRules.filter_active(quirk_pool, quirk_ctx)
	if trinket_lib != null and trinket_lib.is_loaded():
		_trinket_active = BuffRules.filter_active(trinket_pool, quirk_ctx)


## 当前生效的怪癖 buff 条数。自检与界面用。
func active_quirk_count() -> int:
	return _quirk_active.size()


## 当前生效的饰品 buff 条数。单独报，不和怪癖混——
## 「这人身上三条怪癖在生效」和「他戴的两个饰品在生效」是两个问题。
func active_trinket_count() -> int:
	return _trinket_active.size()


## 挂上饰品。和 set_quirks 一样必须在 `hp = base_hp` 之后调用，
## 而且**必须在 set_quirks 之后**：两者都会缩放 base_hp，
## 顺序变了血量比例就算不准（先乘 1.1 再乘 1.2 和反过来，
## 舍入结果不一样）。这里不改血量，只把倍率交给调用方去乘。
##
## 返回值是这件身上饰品的最大生命倍率，供 Battle / 测试核对。
func set_trinkets(ids: Array, lib: TrinketLib) -> float:
	trinket_lib = lib
	trinket_ids = ids.duplicate()
	trinket_pool = []
	if lib != null and lib.is_loaded():
		trinket_pool = lib.buffs_for(trinket_ids)
	var mult: float = 1.0
	if lib != null and lib.is_loaded():
		mult = lib.max_hp_mult(trinket_ids)
	if not is_zero_approx(mult) and not is_equal_approx(mult, 1.0):
		var old_max: int = base_hp
		var new_max: int = maxi(1, int(round(float(base_hp) * mult)))
		base_hp = new_max
		if old_max > 0:
			hp = clampi(int(round(float(hp) * float(new_max) / float(old_max))), 0, new_max)
	refresh_quirks(quirk_ctx)
	return mult


## 返回实际扣除的血量。英雄血量归零进入死门；死门上再受伤要过死击抗性。
##
## deathblow_roll 由调用方（Battle）从 RNG 取，保持本类不依赖随机源：
## 传 1.0 表示「必死」，传 0.0 表示「必被抗住」。
func take_damage(amount: int, deathblow_roll: float = 1.0) -> Dictionary:
	if dead or amount <= 0:
		return {"damage": 0, "died": false, "deaths_door": false}
	if is_hero and at_deaths_door:
		var resist: float = resistance("death_blow")
		if deathblow_roll < resist:
			return {"damage": 0, "died": false, "deaths_door": true, "resisted": true}
		dead = true
		hp = 0
		return {"damage": 0, "died": true, "deaths_door": true}

	var applied: int = mini(amount, hp)
	hp -= applied
	var entered_dd: bool = false
	if hp <= 0:
		if is_hero:
			hp = 0
			at_deaths_door = true
			entered_dd = true
		else:
			dead = true
	return {"damage": applied, "died": dead, "deaths_door": entered_dd}


func heal(amount: int) -> int:
	if dead or amount <= 0:
		return 0
	# 死门上的治疗可以把人拉回来，但只回这一点点，并且会留下「恢复期」减益
	# （由 Battle 补 buff）。原实现直接 return 0，等于治疗对死门完全无效——
	# 那会让死门变成单向陷阱，和 DD1 的手感正好相反。
	if at_deaths_door:
		var before_dd: int = hp
		hp = mini(hp + amount, base_hp)
		at_deaths_door = false
		recovered_from_dd = true
		return hp - before_dd
	var before: int = hp
	hp = mini(hp + amount, base_hp)
	return hp - before


func add_stress(amount: float) -> float:
	if dead or amount == 0.0 or not is_hero:
		return 0.0
	var delta: float = amount
	if delta > 0.0:
		# 三层倍率叠乘：
		#   环境（光照）× 自身 buff（如死门的 +33%）× 等级惩罚（M29）
		# 三层都是独立来源，任何两层合并都会互相洗掉（见 join_stress_mult 的注释）。
		delta *= (1.0 + stress_taken_mod()) * stress_in_mult * join_stress_mult
	stress = clampf(stress + delta, 0.0, 200.0)
	return delta


## 眩晕消耗：被跳过的那一次行动消耗一层。
## 注意不能同时在 tick_round 里递减，否则一层眩晕会跳过两个回合。
func consume_stun() -> void:
	if stun_turns > 0:
		stun_turns -= 1


func add_dot(kind: String, amount: int, duration: int) -> void:
	for d in dots:
		if d.kind == kind:
			d.amount = maxi(int(d.amount), amount)
			d.remaining = maxi(int(d.remaining), duration)
			return
	dots.append({"kind": kind, "amount": amount, "remaining": duration})


func add_status(key: String, duration: int) -> void:
	statuses[key] = maxi(int(statuses.get(key, 0)), duration)


func has_status(key: String) -> bool:
	return int(statuses.get(key, 0)) > 0


## 回合结束：buff/dot/状态计时递减
func tick_round() -> void:
	var kept: Array = []
	for b in buffs:
		if int(b.remaining) > 0:
			b.remaining = int(b.remaining) - 1
			if int(b.remaining) > 0:
				kept.append(b)
			# remaining == 0 表示持续型 buff 到期
		else:
			kept.append(b)   # remaining 0 = 永久（战斗结束才清）
	buffs = kept

	for key in statuses.keys():
		statuses[key] = int(statuses[key]) - 1
		if int(statuses[key]) <= 0:
			statuses.erase(key)


func clear_temp_buffs() -> void:
	var kept: Array = []
	for b in buffs:
		if int(b.remaining) == 0:
			kept.append(b)
	buffs = kept


# ============================================================
# 崩溃 / 美德 / 死门（M3 资源层）
# ============================================================
#
# 这三个状态都不是「拍脑袋加个 -10% 命中」，而是直接吃 buffs.json 里
# DD1 自己的定义：崩溃是一组 5 条 buff（afflictionFearfulBuff1..5 全上），
# 美德是一组 2 条（virtueStalwartBuff1..2），死门是一组 5 条（deathsdoor*）。
# 好处是数值全部可查、可替换——换数值包时它们跟着 buffs.json 一起换。

func has_affliction() -> bool:
	return not affliction.is_empty()


func is_virtuous() -> bool:
	return not virtue.is_empty()


## 已崩溃或已觉醒：两者都不会再触发第二次（DD1 是每场远征一次）
func broken() -> bool:
	return has_affliction() or is_virtuous()


## 按前缀把一组 buff 全挂上（永久，战斗结束才清）。
## 返回实际挂上的 id，供事件日志与回滚使用。
func apply_buff_prefix(db: DdDb, prefix: String) -> Array:
	var applied: Array = []
	if db == null:
		return applied
	var ids: Array = db.buff_ids_with_prefix(prefix)
	for bid in ids:
		var b: Dictionary = db.buff(str(bid))
		if b.is_empty():
			continue
		add_buff(b, 0)
		applied.append(str(bid))
	return applied


func remove_buff_ids(ids: Array) -> void:
	if ids.is_empty():
		return
	var kept: Array = []
	for b in buffs:
		if not ids.has(b.id):
			kept.append(b)
	buffs = kept


func apply_affliction(db: DdDb, kind: String) -> void:
	affliction = kind
	apply_buff_prefix(db, "affliction" + kind.capitalize())


func apply_virtue(db: DdDb, kind: String) -> void:
	virtue = kind
	apply_buff_prefix(db, "virtue" + kind.capitalize())


## 进入死门：挂上 hero 配置里 deaths_door.buffs 那一组减益
## （-10% 命中、-25% 伤害、-5 速度、+33% 受压）。
func enter_deaths_door(db: DdDb) -> void:
	at_deaths_door = true
	if not dd_buff_ids.is_empty() or db == null:
		return
	var h: Dictionary = db.hero(def_id)
	var dd: Dictionary = h.get("deaths_door", {})
	var ids: Array = dd.get("buffs", [])
	for bid in ids:
		var b: Dictionary = db.buff(str(bid))
		if b.is_empty():
			continue
		add_buff(b, 0)
		dd_buff_ids.append(str(bid))


## 离开死门：换成「恢复期」减益（heart_attack=true 时用更重的那一组）
func leave_deaths_door(db: DdDb, heart_attack: bool = false) -> void:
	at_deaths_door = false
	remove_buff_ids(dd_buff_ids)
	dd_buff_ids = []
	recovered_from_dd = false
	recovering = true
	apply_recovery_buffs(db, heart_attack)


## 恢复期减益单独提出来，是因为它要跨战斗存活：
## 战斗里救回来的人，下一场仍然带着「久病」的减益，
## 否则「救回来」就等于「完全没事」，死门又变成没有代价的。
func apply_recovery_buffs(db: DdDb, heart_attack: bool = false) -> void:
	if db == null:
		return
	var h: Dictionary = db.hero(def_id)
	var dd: Dictionary = h.get("deaths_door", {})
	var key: String = "recovery_heart_attack_buffs" if heart_attack else "recovery_buffs"
	for bid in (dd.get(key, []) as Array):
		var b: Dictionary = db.buff(str(bid))
		if not b.is_empty():
			add_buff(b, 0)


## 战斗结束/新战斗开始时清理战斗内的临时状态，但保留远征携带状态。
## 这是「跨战斗」正确性的关键：buff 里的死门/崩溃减益必须留下，
## 而眩晕、持续伤害、本场标记必须清掉。
func reset_for_new_battle() -> void:
	dots = []
	statuses = {}
	stun_turns = 0
	consecutive_misses = 0
	per_battle_uses = {}
	per_turn_uses = {}

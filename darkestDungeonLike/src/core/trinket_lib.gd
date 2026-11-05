class_name TrinketLib
extends RefCounted
## 饰品：每趟出发前由玩家**主动选择**的那一层。
##
## 怪癖是被动接受的（碰了什么就长什么），饰品是这个游戏里第一处
## 「我决定带什么下去」。`data/trinkets.json` 的账是完整的：
## 490 件、1964 条 buff 引用、943 个不同 buff、**缺失 0**。
##
## ## 数据形状
##
## 顶层是三个 `base.*` 键，每个里面再包一层同名键（抽取脚本的产物）：
##   base.entries.entries   -> 490 件饰品
##   base.rarities.rarities -> 14 档稀有度
##   base.starting.starting -> []（本作没有开局饰品）
##
## 抽卡表**按稀有度引用饰品**（`{"type":"trinket","data":{"rarity":"very_common"}}`），
## 不按 id。所以「掉一件饰品」= 在该稀有度池里等概率抽一件。
## 被引用的 10 档合计 182 件可掉落；`kickstarter`（294 件，众筹支持者专享）
## 从来没被任何表引用，这里也明确排除，避免它们漏进随机池。
##
## ## 与怪癖的关系
##
## 判定规则是同一套（`BuffRules`），只是多 6 种。buff 通道也是同一条
## （`Combatant` 的外部 buff 池）——所以饰品不是新机制，是**同一机制的第二个来源**。
##
## ## 三条要知道的字段语义
##
##   * `hero_class_requirements`：空数组 = 谁都能戴；否则只限列出的职业
##   * `limit`：1 = 唯一（全库只能有一件）；0 = 不限；3 = 极少数特例
##   * `price`：1 = 众筹件的占位价，不是真实价格；真实件 5000–50000

const RARITY_KICKSTARTER: String = "kickstarter"
const DEFAULT_EQUIP_SLOTS: int = 2

var entries: Dictionary = {}     ## id -> {id, buffs:[defs], rarity, price, limit, ...}
var order: Array = []            ## 稳定顺序
var rarities: Array = []         ## 稀有度 id 列表（data 原序）
var stats: Dictionary = {}
var source_base: String = ""

var _loaded: bool = false


func is_loaded() -> bool:
	return _loaded


## buff_index 由 DdDb 传入（它已经为 effects/buffs 建过索引）。
## 不传就自己读一份 buffs.json——但那是 552 KB，别让它成为默认路径。
func load_from(base: String = "res://data", buff_index: Dictionary = {}) -> bool:
	entries.clear()
	order.clear()
	rarities.clear()
	stats.clear()
	source_base = ""

	var tpath: String = _resolve(base, "trinkets.json")
	if tpath.is_empty():
		push_warning("TrinketLib: 找不到 trinkets.json")
		return false
	var tp: Variant = JSON.parse_string(FileAccess.get_file_as_string(tpath))
	if tp == null or typeof(tp) != TYPE_DICTIONARY:
		push_warning("TrinketLib: %s 解析失败" % tpath)
		return false

	var buffs: Dictionary = buff_index
	if buffs.is_empty():
		var bpath: String = _resolve(base, "buffs.json")
		if not bpath.is_empty():
			var bp: Variant = JSON.parse_string(FileAccess.get_file_as_string(bpath))
			if bp is Array:
				for b in (bp as Array):
					if b is Dictionary:
						buffs[str(b.get("id", ""))] = b

	var doc: Dictionary = tp
	var row: Dictionary = doc.get("base.entries", {})
	var raw: Array = row.get("entries", [])
	var rar: Dictionary = doc.get("base.rarities", {})
	for r in (rar.get("rarities", []) as Array):
		if r is Dictionary:
			rarities.append(str(r.get("id", "")))

	var missing_buffs: int = 0
	for e in raw:
		if not (e is Dictionary):
			continue
		var id: String = str(e.get("id", ""))
		if id.is_empty():
			continue
		var ent: Dictionary = e.duplicate(true)
		var expanded: Array = []
		var missing: Array = []
		for bid in (e.get("buffs", []) as Array):
			var key: String = str(bid)
			if buffs.has(key):
				var def: Dictionary = (buffs[key] as Dictionary).duplicate(true)
				def["trinket_id"] = id
				expanded.append(def)
			else:
				missing.append(key)
		ent["buffs"] = expanded
		if not missing.is_empty():
			ent["missing_buffs"] = missing
			missing_buffs += missing.size()
		entries[id] = ent
		order.append(id)

	source_base = tpath.get_base_dir()
	_loaded = true
	stats = compute_stats()
	stats["missing_buffs"] = missing_buffs
	return true


func _resolve(base: String, name: String) -> String:
	var p: String = base + "/" + name
	if FileAccess.file_exists(p):
		return p
	var alt: String = "res://data/" + name
	if FileAccess.file_exists(alt):
		return alt
	return ""


func has(id: String) -> bool:
	return entries.has(id)


func get_trinket(id: String) -> Dictionary:
	return entries.get(id, {})


func rarity_of(id: String) -> String:
	return str((entries.get(id, {}) as Dictionary).get("rarity", ""))


func price_of(id: String) -> int:
	return int((entries.get(id, {}) as Dictionary).get("price", 0))


## 全库同名上限。1 = 唯一，0 = 不限。
func limit_of(id: String) -> int:
	return int((entries.get(id, {}) as Dictionary).get("limit", 0))


## 职业限制。空数组 = 谁都能戴。
func classes_of(id: String) -> Array:
	return (entries.get(id, {}) as Dictionary).get("hero_class_requirements", [])


func fits_class(id: String, hero_id: String) -> bool:
	var req: Array = classes_of(id)
	if req.is_empty():
		return true
	return req.has(hero_id)


# ============================================================
# 抽选
# ============================================================

## 这个稀有度能掉落的全部 id（已排序，便于复现）。
## `kickstarter` 恒返回空：那 294 件是众筹支持者专享，任何抽卡表都没引用它们。
func pool_for_rarity(rarity: String) -> Array:
	var out: Array = []
	if rarity == RARITY_KICKSTARTER:
		return out
	for id in order:
		if str((entries[id] as Dictionary).get("rarity", "")) == rarity:
			out.append(id)
	out.sort()
	return out


## 按稀有度抽一件。池空返回 ""。
## `exclude` 用来把「已经有的唯一件」排除掉——limit=1 的件重复掉落没有意义。
func pick_for_rarity(rarity: String, rng: DdRng, exclude: Array = []) -> String:
	var pool: Array = []
	for id in pool_for_rarity(rarity):
		if not exclude.has(id):
			pool.append(id)
	if pool.is_empty() or rng == null:
		return ""
	return str(pool[rng.next_int(pool.size())])


## 掉落表引用过、且池子非空的稀有度。自检与文档用。
func droppable_rarities() -> Array:
	var out: Array = []
	for r in rarities:
		if str(r) == RARITY_KICKSTARTER:
			continue
		if not pool_for_rarity(str(r)).is_empty():
			out.append(str(r))
	return out


# ============================================================
# buff
# ============================================================

func buffs_for(ids: Array) -> Array:
	var out: Array = []
	for id in ids:
		var t: Dictionary = entries.get(str(id), {})
		for b in (t.get("buffs", []) as Array):
			out.append(b)
	return out


func active_buffs(ids: Array, ctx: Dictionary) -> Array:
	return BuffRules.filter_active(buffs_for(ids), ctx)


## 最大生命倍率。和怪癖一样必须在注入时一次性算掉（见 QuirkLib 的同名注释）：
## 它改的是 `hp_ratio` 的分母，做成每帧可变会让「当前血量」失去定义。
func max_hp_mult(ids: Array) -> float:
	var m: float = 1.0
	for b in buffs_for(ids):
		if str(b.get("stat_type", "")) == "combat_stat_multiply" \
				and str(b.get("stat_sub_type", "")) == "max_hp":
			m *= (1.0 + float(b.get("amount", 0.0)))
	return m


# ============================================================
# 自检
# ============================================================

## 战斗内由 Combatant 消费的通道（与 QuirkLib.STAT_COMBAT 同一套）。
const STAT_COMBAT: Array = [
	"combat_stat_add", "combat_stat_multiply",
	"stress_dmg_received_percent", "stress_heal_received_percent",
	"resistance",
]
## 远征层：侦察、食物消耗、怪物偷袭率。
const STAT_EXPEDITION: Array = [
	"scouting_chance", "food_consumption_percent", "monsters_surprise_chance",
]
## 没有承载的通道：营地/城镇/决心检定/眩晕概率等。
const STAT_UNSUPPORTED: Array = [
	"hp_heal_percent", "hp_heal_received_percent", "resolve_check_percent",
	"resolve_xp_bonus_percent", "stun_chance", "damage_received_percent",
	"activity_side_effect_chance",
]


func channel_of(b: Dictionary) -> String:
	var s: String = str(b.get("stat_type", ""))
	if STAT_COMBAT.has(s):
		return "combat"
	if STAT_EXPEDITION.has(s):
		return "expedition"
	return "unsupported"


## 覆盖率：这 1964 条引用里有多少真的会生效。
func compute_stats() -> Dictionary:
	var out: Dictionary = {
		"trinkets": entries.size(),
		"buff_refs": 0,
		"distinct_buffs": 0,
		"landable": 0,
		"rule_blocked": 0,
		"no_channel": 0,
		"both_blocked": 0,
		"rule_counts": {},
		"channel_counts": {},
		"by_rarity": {},
	}
	var seen: Dictionary = {}
	for id in order:
		var t: Dictionary = entries[id]
		var r: String = str(t.get("rarity", ""))
		out["by_rarity"][r] = int((out["by_rarity"] as Dictionary).get(r, 0)) + 1
		for b in (t.get("buffs", []) as Array):
			out["buff_refs"] = int(out["buff_refs"]) + 1
			seen[str(b.get("id", ""))] = true
			var rule: String = str(b.get("rule_type", BuffRules.RULE_ALWAYS))
			var rc: Dictionary = out["rule_counts"]
			rc[rule] = int(rc.get(rule, 0)) + 1
			var ch: String = channel_of(b)
			var cc: Dictionary = out["channel_counts"]
			cc[ch] = int(cc.get(ch, 0)) + 1
			var rok: bool = BuffRules.RULES_EVALUABLE.has(rule)
			var cok: bool = ch != "unsupported"
			if rok and cok:
				out["landable"] = int(out["landable"]) + 1
			elif cok:
				out["rule_blocked"] = int(out["rule_blocked"]) + 1
			elif rok:
				out["no_channel"] = int(out["no_channel"]) + 1
			else:
				out["both_blocked"] = int(out["both_blocked"]) + 1
	out["distinct_buffs"] = seen.size()
	return out


func unknown_rules() -> Array:
	var all_defs: Array = []
	for id in order:
		for b in (entries[id].get("buffs", []) as Array):
			all_defs.append(b)
	return BuffRules.unknown_rules(all_defs)

class_name QuirkLib
extends RefCounted
## 怪癖与疾病：英雄身上那些「跟着你走」的东西。
##
## 这一层此前完全不存在。`effect_resolver` 遇到 `disease` 只标一句 unsupported，
## 遇到奇物给的 `quirk` 连标都没标——直接掉在地上。而 data 里躺着 170 个怪癖
## （其中 23 个是疾病）、195 条 buff 引用、15 种触发条件。
##
## ## 为什么疾病不是独立系统
##
## `quirks.json` 里每个条目都有 `is_disease`，23 条为 true。疾病就是「带疾病的怪癖」：
## 同样的槽位语法、同样的 buff 通道、同样的清负面规则，只是获得途径不同
## （奇物接触而非战斗结算），且多一条疾病抗性判定。单独造一套疾病表会让
## 两者永远不同步——这正是本项目在 M13 修过的那类问题。
##
## ## 条件怪癖才是主体
##
## 195 条 buff 引用里，只有 64 条是 `always`。其余靠 15 种 `rule_type` 决定
## 「什么时候生效」：血量低于一半、光照高于 75、面对兽类、只在首轮、
## 只在近战……如果只落地 `always`，等于把 2/3 的怪癖做成静态数值，
## 而「夜盲症在亮处难受」这类设计就完全不存在了。
##
## 所以这一层的关键不是「读表」，是**把条件翻译成可判定的谓词**，
## 并且诚实地区分「现在能判」与「判不了」：
##
##   * 可判（11 种）：always / in_dungeon / lightabove / lightbelow /
##     hpbelow / hpabove / stress_above / stress_below / firstroundonly /
##     monsterType / monster_type_count_min / meleeonly / rangedonly
##   * 判不了（4 种）：in_camp / in_activity / walking_backwards / in_corridor
##     —— 这些依赖营地、城镇活动、走动方向，本作没有对应系统。
##     一律返回 false 并计数，**不猜**。宁可这个怪癖暂时无效，
##     也不要给一个「看起来生效了」的假实现。
##
## ## 阈值方向
##
## `lightabove: 75` 判 `light >= 75`，`lightbelow: 26` 判 `light <= 26`。
## 中间 27–74 是一段无判定的安全带，和 DD1 的火把区间语义一致：
## 亮处、暗处、以及两者之间那片「谁都不得罪」的灰。
##
## `hpbelow` 的 rule_data 是**比例**（0.5 = 半血以下），不是百分比数字；
## `stress_above` 的 rule_data 是**绝对值**（50 = 压力过 50）。两者口径不同，
## 是原表就这么写的，不是笔误。

## 槽位上限的**默认值**，实际以 `rules.json` 为准（见 apply_caps）。
##
## 一开始这三个数写成 3/3/1，是按「DD1 印象」拍的；数据里其实是 5/5/3。
## 留成变量而不是常量，就是为了让数据能覆盖它——槽位是平衡旋钮，
## 不该焊在代码里。
const SLOT_POSITIVE: int = 3
const SLOT_NEGATIVE: int = 3
const SLOT_DISEASE: int = 1

var cap_positive: int = SLOT_POSITIVE
var cap_negative: int = SLOT_NEGATIVE
var cap_disease: int = SLOT_DISEASE


## 用规则表覆盖槽位上限。DdDb 加载完 rules 之后调一次。
func apply_caps(pos: int, neg: int, disease: int) -> void:
	cap_positive = maxi(0, pos)
	cap_negative = maxi(0, neg)
	cap_disease = maxi(0, disease)

## 规则词表已抽到 BuffRules（M15）：饰品的 943 个 buff 用的是同一套，
## 且多出 6 种。这里只做转发，不再维护第二份。
const RULES_EVALUABLE: Array = BuffRules.RULES_EVALUABLE
const RULES_UNSUPPORTED: Array = BuffRules.RULES_UNSUPPORTED
const RULE_ALWAYS: String = BuffRules.RULE_ALWAYS

var quirks: Dictionary = {}      ## id -> {id, is_positive, is_disease, buffs:[{...}], ...}
var order: Array = []            ## 稳定顺序（按 data 原序），抽选与展示都靠它
var stats: Dictionary = {}       ## 加载时算一次，供自检对照
var source_base: String = ""

var _buffs: Dictionary = {}      ## buff id -> 原始定义
var _loaded: bool = false


func is_loaded() -> bool:
	return _loaded


func load_from(base: String = "res://data") -> bool:
	quirks.clear()
	order.clear()
	stats.clear()
	_buffs.clear()
	source_base = ""

	var qpath: String = _resolve(base, "quirks.json")
	var bpath: String = _resolve(base, "buffs.json")
	if qpath.is_empty() or bpath.is_empty():
		push_warning("QuirkLib: 缺少 quirks.json 或 buffs.json")
		return false

	var qp: Variant = JSON.parse_string(FileAccess.get_file_as_string(qpath))
	var bp: Variant = JSON.parse_string(FileAccess.get_file_as_string(bpath))
	if qp == null or typeof(qp) != TYPE_DICTIONARY:
		push_warning("QuirkLib: %s 解析失败" % qpath)
		return false
	if bp == null or typeof(bp) != TYPE_ARRAY:
		push_warning("QuirkLib: %s 解析失败" % bpath)
		return false

	for b in (bp as Array):
		if b is Dictionary:
			_buffs[str(b.get("id", ""))] = b

	var raw: Array = (qp as Dictionary).get("quirks", [])
	for q in raw:
		if not (q is Dictionary):
			continue
		var id: String = str(q.get("id", ""))
		if id.is_empty():
			continue
		var row: Dictionary = q.duplicate(true)
		# 把 buff id 展开成定义，运行时不再查两次表。
		# 缺失的 buff 单独记下来，而不是静默丢——那会让「这个怪癖没效果」
		# 变成一个查不出来的谜。
		var expanded: Array = []
		var missing: Array = []
		for bid in (q.get("buffs", []) as Array):
			var key: String = str(bid)
			if _buffs.has(key):
				var def: Dictionary = (_buffs[key] as Dictionary).duplicate(true)
				def["quirk_id"] = id
				expanded.append(def)
			else:
				missing.append(key)
		row["buffs"] = expanded
		if not missing.is_empty():
			row["missing_buffs"] = missing
		quirks[id] = row
		order.append(id)

	source_base = qpath.get_base_dir()
	_loaded = true
	stats = compute_stats()
	return true


## 数值包（balance/*）与 res://data 谁能提供就给谁。怪癖是规则数据，
## 不是平衡旋钮；换包时不该让整层静默变成空表。
func _resolve(base: String, name: String) -> String:
	var p: String = base + "/" + name
	if FileAccess.file_exists(p):
		return p
	var alt: String = "res://data/" + name
	if FileAccess.file_exists(alt):
		return alt
	return ""


func has(id: String) -> bool:
	return quirks.has(id)


func get_quirk(id: String) -> Dictionary:
	return quirks.get(id, {})


func is_disease(id: String) -> bool:
	return bool((quirks.get(id, {}) as Dictionary).get("is_disease", false))


func is_positive(id: String) -> bool:
	return bool((quirks.get(id, {}) as Dictionary).get("is_positive", false))


## 这个怪癖占哪个槽位。疾病单独一类，正负分开。
func slot_kind(id: String) -> String:
	var q: Dictionary = quirks.get(id, {})
	if bool(q.get("is_disease", false)):
		return "disease"
	return "positive" if bool(q.get("is_positive", false)) else "negative"


func slot_cap(kind: String) -> int:
	match kind:
		"disease":
			return cap_disease
		"positive":
			return cap_positive
		_:
			return cap_negative


# ============================================================
# 抽选
# ============================================================

## 抽一个怪癖 id。抽不到返回 ""。
##
## polarity：positive / negative / any（any 只对疾病有意义，疾病本身不分正负）。
## owned：已有的怪癖 id，既用于排重，也用于**不兼容判定**——
##        tough 与 fragile 互为 incompatible，同时持有等于白拿两份数值。
## 权重用 random_chance（原表里 6 条为 0，表示只能由特定奇物指定，
## 不进随机池）。这不是「概率」，是相对权重。
func pick(polarity: String, rng: DdRng, owned: Array = [], want_disease: bool = false) -> String:
	if rng == null:
		return ""
	var pool: Array = []
	var weights: Array = []
	var total: int = 0
	for id in order:
		var q: Dictionary = quirks[id]
		if bool(q.get("is_disease", false)) != want_disease:
			continue
		if owned.has(id):
			continue
		if polarity == "positive" and not bool(q.get("is_positive", false)):
			continue
		if polarity == "negative" and bool(q.get("is_positive", false)):
			continue
		if not _compatible(q, owned):
			continue
		var w: int = int(round(float(q.get("random_chance", 1.0)) * 1000.0))
		if w <= 0:
			continue
		pool.append(id)
		weights.append(w)
		total += w
	if total <= 0:
		return ""
	var roll: int = rng.next_int(total)
	var acc: int = 0
	for i in pool.size():
		acc += int(weights[i])
		if roll < acc:
			return str(pool[i])
	return str(pool[pool.size() - 1])


## 与已持有的是否互斥。互斥表是**单向写**的（tough 列了 fragile，
## fragile 也列了 tough），但数据里不保证两边都写，所以两个方向都查一次。
func _compatible(q: Dictionary, owned: Array) -> bool:
	var inc: Array = q.get("incompatible_quirks", [])
	for o in owned:
		if inc.has(o):
			return false
		var other: Dictionary = quirks.get(str(o), {})
		if (other.get("incompatible_quirks", []) as Array).has(str(q.get("id", ""))):
			return false
	return true


# ============================================================
# 条件判定
# ============================================================

## 单条 buff 的规则在当前语境下是否成立。
##
## ctx 里没有的键按「不成立」处理，而不是按 0 处理——把「不知道光照」
## 当成「光照 0」会让夜行性怪癖在数据缺失时白送一份加成。
func rule_active(b: Dictionary, ctx: Dictionary) -> bool:
	return BuffRules.rule_active(b, ctx)


## 这批怪癖在当前语境下实际生效的 buff 列表（已按 quirk_id 标好来源）。
func active_buffs(ids: Array, ctx: Dictionary) -> Array:
	var out: Array = []
	for id in ids:
		var q: Dictionary = quirks.get(str(id), {})
		for b in (q.get("buffs", []) as Array):
			if rule_active(b, ctx):
				out.append(b)
	return out


## 全部 buff（不看条件）。用于展示「这个怪癖理论上有哪些效果」。
func buffs_for(ids: Array) -> Array:
	var out: Array = []
	for id in ids:
		var q: Dictionary = quirks.get(str(id), {})
		for b in (q.get("buffs", []) as Array):
			out.append(b)
	return out


## max_hp 是乘法通道里唯一「必须在注入时一次性算掉」的项：
## 它改的是分母（hp_ratio / 治疗上限都依赖 base_hp），
## 做成每帧可变的会让「当前血量」失去定义。九条 max_hp buff 全是 always，
## 所以可以安全地在这里取乘积。
func max_hp_mult(ids: Array) -> float:
	var m: float = 1.0
	for b in buffs_for(ids):
		if str(b.get("stat_type", "")) == "combat_stat_multiply" \
				and str(b.get("stat_sub_type", "")) == "max_hp":
			m *= (1.0 + float(b.get("amount", 0.0)))
	return m


# ============================================================
# 效果落入哪些通道
# ============================================================

## 战斗内由 Combatant 的 _sum_add / _product_mult / resistance 直接消费。
const STAT_COMBAT: Array = [
	"combat_stat_add", "combat_stat_multiply",
	"stress_dmg_received_percent", "stress_heal_received_percent",
	"resistance",
]
## 远征层消费：侦察概率、食物消耗。
const STAT_EXPEDITION: Array = ["scouting_chance", "food_consumption_percent"]
## 元层消费：升级折扣。
const STAT_CAMPAIGN: Array = ["upgrade_discount"]
## 没有承载的口径。逐条计数，不折算、不猜。
const STAT_UNSUPPORTED: Array = [
	"hp_heal_percent",            # 营地治疗，本作没有营地治疗
	"resolve_check_percent",      # 决心检定，本作只有崩溃判定
	"activity_side_effect_chance",# 城镇活动副作用，本作没有活动
]


func channel_of(b: Dictionary) -> String:
	var s: String = str(b.get("stat_type", ""))
	if STAT_COMBAT.has(s):
		return "combat"
	if STAT_EXPEDITION.has(s):
		return "expedition"
	if STAT_CAMPAIGN.has(s):
		return "campaign"
	return "unsupported"


## 全量覆盖率。这是这一期最重要的一个数：它决定「怪癖系统到底做完了多少」。
func compute_stats() -> Dictionary:
	var out: Dictionary = {
		"quirks": quirks.size(),
		"diseases": 0,
		"positive": 0,
		"negative": 0,
		"buff_refs": 0,
		"rule_counts": {},
		"channel_counts": {},
		"landable": 0,          # 条件可判 且 有承载
		"rule_blocked": 0,      # 有承载但条件判不了
		"no_channel": 0,        # 条件能判但没有承载
		"both_blocked": 0,
		"missing_buffs": 0,
	}
	for id in order:
		var q: Dictionary = quirks[id]
		if bool(q.get("is_disease", false)):
			out["diseases"] = int(out["diseases"]) + 1
		elif bool(q.get("is_positive", false)):
			out["positive"] = int(out["positive"]) + 1
		else:
			out["negative"] = int(out["negative"]) + 1
		out["missing_buffs"] = int(out["missing_buffs"]) + (q.get("missing_buffs", []) as Array).size()
		for b in (q.get("buffs", []) as Array):
			out["buff_refs"] = int(out["buff_refs"]) + 1
			var r: String = str(b.get("rule_type", RULE_ALWAYS))
			var rc: Dictionary = out["rule_counts"]
			rc[r] = int(rc.get(r, 0)) + 1
			var ch: String = channel_of(b)
			var cc: Dictionary = out["channel_counts"]
			cc[ch] = int(cc.get(ch, 0)) + 1
			var rok: bool = RULES_EVALUABLE.has(r)
			var cok: bool = ch != "unsupported"
			if rok and cok:
				out["landable"] = int(out["landable"]) + 1
			elif cok:
				out["rule_blocked"] = int(out["rule_blocked"]) + 1
			elif rok:
				out["no_channel"] = int(out["no_channel"]) + 1
			else:
				out["both_blocked"] = int(out["both_blocked"]) + 1
	return out


## 数据里出现了、但代码不认识的 rule_type。空数组才算干净。
func unknown_rules() -> Array:
	var all_defs: Array = []
	for id in order:
		for b in (quirks[id].get("buffs", []) as Array):
			all_defs.append(b)
	return BuffRules.unknown_rules(all_defs)

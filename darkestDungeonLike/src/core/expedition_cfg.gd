class_name ExpeditionCfg
extends RefCounted
## 远征资源层的策略配置。
##
## 分工要说清楚，否则以后一定会出现「同一个数写在两个地方」的烂账：
##
##   rules.json      原始规则常量——光照档位修正（darkness）、每格光耗、
##                   饥饿回血/掉血比例、营地点数、崩溃触发率。这些是 DD1 自己的数。
##   expedition.json 本文件——DD1 数据里没有的东西：补给品带多少、自动用火把的阈值、
##                   休整策略、崩溃之后的『动作失控』规则。
##
## 分成 presets 是为了做对照实验：同一套战斗数值，只换资源策略，
## 危险度指标若不动，说明资源层白做了；若动，才证明 M3 是有效的。

const DEFAULT_PATH: String = "res://data/expedition.json"
const FALLBACK_PATH: String = "res://data/expedition.json"

var presets: Dictionary = {}
var source_path: String = ""
var missing: Array = []

## 内容密度（顶层 `curio_rate` 段），**不属于任何 preset**。
##
## 出现率不是难度旋钮：不管打 lenient 还是 brutal，一张短图上该有几个奇物
## 是同一个数。放进 preset 会导致「换难度顺手改了内容密度」，
## 那会和难度调整混在一起，两个变量分不开。
##
## 0 = 不干预，完全听 dungeons.json 的原始百分比。
var curio_hall_pct_min: int = 0


func load_from(path: String) -> bool:
	var use: String = path
	if use.is_empty() or not FileAccess.file_exists(use):
		use = FALLBACK_PATH
	if not FileAccess.file_exists(use):
		push_warning("ExpeditionCfg: 找不到 %s，使用内置默认值" % use)
		presets = {"standard": defaults()}
		source_path = "<builtin>"
		return false

	var parsed: Variant = JSON.parse_string(FileAccess.get_file_as_string(use))
	if parsed == null or typeof(parsed) != TYPE_DICTIONARY:
		push_error("ExpeditionCfg: %s 不是合法 JSON" % use)
		presets = {"standard": defaults()}
		return false

	source_path = use
	var doc: Dictionary = parsed
	var cr: Dictionary = doc.get("curio_rate", {})
	curio_hall_pct_min = clampi(int(cr.get("hallway_pct_min", 0)), 0, 100)

	var raw: Dictionary = (parsed as Dictionary).get("presets", {})
	presets = {}
	for name in raw.keys():
		presets[str(name)] = merge(defaults(), raw[name])
	if presets.is_empty():
		presets = {"standard": defaults()}
	return true


## 取一个预设；名字不认识时退回 standard，并把缺失记下来——
## 静默回退会让「我明明换了配置」变成一个查不出来的 bug。
func preset(name: String) -> Dictionary:
	if presets.has(name):
		return presets[name]
	if not missing.has(name):
		missing.append(name)
		push_warning("ExpeditionCfg: 未知预设 %s，回退 standard" % name)
	return presets.get("standard", defaults())


func names() -> Array:
	return presets.keys()


static func defaults() -> Dictionary:
	return {
		"desc": "内置默认",
		"light": {"start": 100, "loss_per_step": 10, "torch_start": 4,
			"torch_gain": 25, "auto_torch_below": 50},
		"food": {"start": 4, "per_hunger": 1, "starve_stress": 15, "starve_dmg_ratio": 0.2},
		"camp": {"max": 1, "food_cost": 2, "heal_ratio": 0.3, "stress_relief": 40,
			"light_gain": 60, "ambush_chance": 0.25},
		"affliction": {"refuse_chance": 0.15, "aura_stress": 2.0, "virtue_relief": 1.0},
		# 陷阱与障碍（M8）。伤害按「最大血量比例」算而不是固定值——
		# 固定值在 4 阶装备的队里等于挠痒，在 0 阶队里等于致命。
		"supply": {"shovel_start": 1},
		"trap": {"damage_ratio": 0.10, "stress": 7.0, "min_avoid": 0.05, "max_avoid": 0.85},
		"obstacle": {"damage_ratio": 0.09, "stress": 5.0, "shovel_uses": 1},
		"heal_charges": 0,
	}


## 逐层合并：缺字段就用默认值，多出来的字段原样保留（方便试新旋钮）。
static func merge(base: Dictionary, over: Variant) -> Dictionary:
	var out: Dictionary = base.duplicate(true)
	if not (over is Dictionary):
		return out
	for k in (over as Dictionary).keys():
		var v: Variant = over[k]
		if out.has(k) and out[k] is Dictionary and v is Dictionary:
			out[k] = merge(out[k], v)
		else:
			out[k] = v
	return out


# ============================================================
# 光照档位
# ============================================================

## 查 rules.json 的 darkness 表，返回该光照值对应的修正（已转成小数倍率）。
##
## 表里 `lowest_excluded: true`，含义是区间左开右闭——75 属于「微光」而不是「明亮」。
## 这个细节抄错一档，整条光照曲线就会平移，且不会有任何报错。
static func light_modifier(darkness: Dictionary, light: float) -> Dictionary:
	var table: Array = darkness.get("range_table", [])
	var lowest_excluded: bool = bool(darkness.get("lowest_excluded", true))
	for row in table:
		if not (row is Dictionary):
			continue
		var rng_box: Dictionary = row.get("range", {})
		var lo: float = float(rng_box.get("lower", -INF))
		var hi: float = float(rng_box.get("upper", INF))
		var inside: bool
		if lowest_excluded:
			inside = light > lo and light <= hi
		else:
			inside = light >= lo and light <= hi
		if inside:
			return _to_rates(row.get("value", {}))
	return {}


## 表里的数是百分数（10.0 = +10%），这里统一转成小数，
## 免得下游一半地方除 100、一半地方忘了除——这类 bug 只表现为「手感有点怪」。
static func _to_rates(v: Variant) -> Dictionary:
	var src: Dictionary = v if v is Dictionary else {}
	return {
		"stress_chance": float(src.get("stress_chance_increase", 0.0)) / 100.0,
		"stress_damage": float(src.get("stress_damage_increase", 0.0)) / 100.0,
		"monster_acc": float(src.get("monster_attack_increase", 0.0)) / 100.0,
		"monster_dmg": float(src.get("monster_damage_increase", 0.0)) / 100.0,
		"monster_crit": float(src.get("monster_crit_increase", 0.0)) / 100.0,
		"player_crit": float(src.get("player_crit_increase", 0.0)) / 100.0,
		"player_dodge": float(src.get("player_def_increase", 0.0)) / 100.0,
		"monsters_surprised": float(src.get("monsters_surprised_increase", 0.0)) / 100.0,
		"heroes_surprised": float(src.get("heroes_surprised_increase", 0.0)) / 100.0,
		# 侦察：明亮 +15%、微光 +7.5%，昏暗以下是 0。
		# 这是光照的第三个作用——不只是「挨打更疼」，还决定你能提前看见多少。
		"player_scouting": float(src.get("player_scouting_increase", 0.0)) / 100.0,
		"loot_gold": float(src.get("loot_increase_gold", 0.0)) / 100.0,
	}


## 光照档位的可读名字，只用于报告。
static func light_tier_name(light: float) -> String:
	if light > 75.0:
		return "明亮"
	if light > 50.0:
		return "微光"
	if light > 25.0:
		return "昏暗"
	if light > 0.0:
		return "漆黑"
	return "无光"

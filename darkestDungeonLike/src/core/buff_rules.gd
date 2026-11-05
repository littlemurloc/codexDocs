class_name BuffRules
extends RefCounted
## buff 的「什么时候生效」判定。
##
## 这一层原先是写死在 `QuirkLib` 里的方法。做饰品（M15）时发现：
## `trinkets.json` 的 943 个 buff 用的是**同一套 `rule_type` 词表**，
## 只是多出 6 种。复制一份判定逻辑等于给自己埋一个必然漂移的副本——
## 所以抽出来共用，谁都可以调。
##
## 判定只吃 `ctx`（一个纯字典），不碰任何类实例：
##   ctx = {
##     dungeon: String, light: float, round: int,
##     hp_ratio: float, stress: float,
##     enemy_types: Array,           # 场上活着的敌人的种
##     skill_type: String,           # "melee" / "ranged"
##     skill_id: String,             # 当前技能 id
##     rank: int,                    # 自己 0 基站位
##     at_deaths_door: bool,
##     statuses: Array,              # 自身状态标签（tagged 等）
##     target_types: Array,          # 当前目标的种
##     target_size: int,             # 当前目标的体型
##   }
## 缺键一律按「不成立」，不按 0 处理——把「不知道光照」当成「光照 0」
## 会让夜行性效果在数据缺失时白送一份加成。
##
## ## 两种判不了
##
##   * `in_camp` / `in_activity` / `walking_backwards` / `in_corridor`
##     —— 本作没有营地、城镇活动、走动方向。一律 false 并计数。
##   * `is_false_rule` —— 原表里存在取反标记，但目前 0 条实际使用。
##     仍然实现了，因为「读到但没实现」比「没读到」更难查（M14 的教训）。

const RULE_ALWAYS: String = "always"

## 能判的条件。列成常量而不是 match 里隐式判断，是为了让自检能报出
## 「数据里出现了但代码不认识」的 rule_type。
const RULES_EVALUABLE: Array = [
	"always", "in_dungeon", "lightabove", "lightbelow",
	"hpbelow", "hpabove", "stress_above", "stress_below",
	"firstroundonly", "monsterType", "monster_type_count_min",
	"meleeonly", "rangedonly",
	# —— M15 饰品的 6 种 ——
	"in_rank", "at_deaths_door", "attacking_monster_type",
	"actorStatus", "skill", "monsterSize",
]
const RULES_UNSUPPORTED: Array = [
	"in_camp", "in_activity", "walking_backwards", "in_corridor",
]


static func rule_active(b: Dictionary, ctx: Dictionary) -> bool:
	var rule: String = str(b.get("rule_type", RULE_ALWAYS))
	var rd: Dictionary = b.get("rule_data", {})
	var fv: float = float(rd.get("float", 0.0))
	var sv: String = str(rd.get("string", ""))
	var neg: bool = bool(b.get("is_false_rule", false))
	var res: bool = false

	match rule:
		"always":
			res = true
		"in_dungeon":
			res = sv != "" and str(ctx.get("dungeon", "")) == sv
		"lightabove":
			res = ctx.has("light") and float(ctx["light"]) >= fv
		"lightbelow":
			res = ctx.has("light") and float(ctx["light"]) <= fv
		"hpbelow":
			# rule_data 是比例（0.5 = 半血），不是百分比数字
			res = ctx.has("hp_ratio") and float(ctx["hp_ratio"]) < fv
		"hpabove":
			res = ctx.has("hp_ratio") and float(ctx["hp_ratio"]) > fv
		"stress_above":
			# rule_data 是绝对压力值（50 = 压力过 50）
			res = ctx.has("stress") and float(ctx["stress"]) > fv
		"stress_below":
			res = ctx.has("stress") and float(ctx["stress"]) < fv
		"firstroundonly":
			res = int(ctx.get("round", 0)) <= 1
		"monsterType":
			res = sv != "" and (ctx.get("enemy_types", []) as Array).has(sv)
		"monster_type_count_min":
			var n: int = 0
			for t in (ctx.get("enemy_types", []) as Array):
				if str(t) == sv:
					n += 1
			res = n >= int(round(fv))
		"meleeonly":
			res = str(ctx.get("skill_type", "")) == "melee"
		"rangedonly":
			res = str(ctx.get("skill_type", "")) == "ranged"

		# —— M15 ——
		"in_rank":
			# rule_data.float 就是 0 基站位号。
			# 证据：这批 buff 的 id 自带 `_FRONT` / `_BACKRANK`，
			# 而 float 恰好只有 0 和 3 两种（前排 / 后排），不是掩码。
			res = ctx.has("rank") and int(ctx["rank"]) == int(round(fv))
		"at_deaths_door":
			res = bool(ctx.get("at_deaths_door", false))
		"attacking_monster_type":
			res = sv != "" and (ctx.get("target_types", []) as Array).has(sv)
		"actorStatus":
			res = sv != "" and (ctx.get("statuses", []) as Array).has(sv)
		"skill":
			res = sv != "" and str(ctx.get("skill_id", "")) == sv
		"monsterSize":
			res = ctx.has("target_size") and int(ctx["target_size"]) >= int(round(fv))
		_:
			# 营地/活动/走廊方向：本作没有对应系统
			res = false

	return not res if neg else res


## 数据里出现了、但代码不认识的 rule_type。空数组才算干净。
static func unknown_rules(defs: Array) -> Array:
	var out: Array = []
	for b in defs:
		if not (b is Dictionary):
			continue
		var r: String = str(b.get("rule_type", RULE_ALWAYS))
		if not RULES_EVALUABLE.has(r) and not RULES_UNSUPPORTED.has(r) and not out.has(r):
			out.append(r)
	out.sort()
	return out


## 这批 buff 在当前语境下生效的条目。
##
## `skip_max_hp` 默认 true：最大生命不是「每帧可变」的属性，它改的是
## `base_hp` 这个分母，注入时已经一次性乘过（见 QuirkLib.max_hp_mult）。
## 留在生效列表里目前不会算错（没有读 max_hp 的出口），但它会污染
## 「这人几条 buff 在生效」的计数，也会在将来有人加出口时变成双重乘。
static func filter_active(defs: Array, ctx: Dictionary, skip_max_hp: bool = true) -> Array:
	var out: Array = []
	for b in defs:
		if not (b is Dictionary):
			continue
		if skip_max_hp and str(b.get("stat_type", "")) == "combat_stat_multiply" \
				and str(b.get("stat_sub_type", "")) == "max_hp":
			continue
		if rule_active(b, ctx):
			out.append(b)
	return out

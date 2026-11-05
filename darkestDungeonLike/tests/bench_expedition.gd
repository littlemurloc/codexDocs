extends SceneTree
## 远征测量器：把「这趟路到底危不危险」变成数字。
##
## 和 bench_battle.gd 的分工：
##   bench_battle     单场战斗的手感（轮数、溢出、暴击）
##   bench_expedition 一整段远征的生存压力（崩溃、死门、团灭、补给）
##
## M2 的结论是「单场战斗里没有危险，危险只能在资源层出现」。
## 这个脚本就是去验证那句话：同一套战斗数值，只换资源策略，
## 下面的指标必须显著移动；如果不动，说明资源层没接上。
##
## 用法：
##   godot --headless --path . --script res://tests/bench_expedition.gd -- \
##     --runs=60 --data=<绝对路径> --size=short --level=3 --out=<绝对路径>

const HEROES: Array = ["crusader", "highwayman", "vestal", "plague_doctor"]
const DEFAULT_PRESETS: Array = ["lenient", "standard", "tight", "brutal"]

## 队伍可换（M10）：换队形会改所有绝对数，所以默认不变。
var _heroes: Array = HEROES.duplicate()
## 技能组（M19）。默认 all = 每人技能全开，这是 M1~M18 的行为，
## 历史 bench 数字靠它复现。`--skills=loadout` 才切到「每人 4 个」。
var _skills_mode: String = "all"

## 模拟「全员 N 级」打这一档（M25）。0 = 不模拟，历史基线逐位不变。
##
## 存在的理由：等级锁的真实代价是**进本压力**，而它发生在 setup 里，
## 不灌进去就没法回答「1 级队伍硬闯 Lv3 会怎样」。之前 bench 的数字
## 全是「不计等级惩罚」的，那在新规则下已经不是玩家真实处境了。
var _resolve: int = 0

## `--resolve-mult`：在进本压力之外，再模拟「受压 +25%/级」（M29）。
##
## 两个开关分开，是因为它们回答的是两个问题：
##   --resolve=1              低等级硬闯，只是因为开局压力多付一笔
##   --resolve=1 --resolve-mult  那笔钱还是分期付的，全程都更疼
## 只有对照这两组，才知道「+25% 受压」到底贡献了多少难度。
var _resolve_mult: bool = false
var _no_guard: bool = false
var _no_riposte: bool = false
var _no_move_value: bool = false
var _no_move_resist: bool = false
var _no_summon: bool = false
var _no_summon_value: bool = false
var _no_summon_limit: bool = false
var _no_loot_table: bool = false
var _no_curio_table: bool = false
var _hall_curio: int = 0
var _no_quirk: bool = false
var _quirks_per_hero: int = 0
var _no_trinket: bool = false
var _trinkets_per_hero: int = 0
var _trinket_polarity: String = "mix"
## base = 不覆盖（走 Expedition 默认，历史基线）
## lean = 只带最低限度（1 火把 / 1 口粮 / 无铁锹）
## rich = 带满（火把 8 / 口粮 8 / 铁锹 4 / 其余 6）
var _pack_mode: String = "base"
var _quirk_polarity: String = "alt"
var _no_curio_item: bool = false

var _runs: int = 60
var _data: String = ""
var _out: String = ""
var _dungeon: String = "weald"
var _size: String = "short"
var _level: int = 3
var _presets: Array = DEFAULT_PRESETS


func _initialize() -> void:
	for arg in OS.get_cmdline_user_args():
		if arg.begins_with("--runs="):
			_runs = int(arg.substr(7))
		elif arg.begins_with("--data="):
			_data = arg.substr(7)
		elif arg.begins_with("--out="):
			_out = arg.substr(6)
		elif arg.begins_with("--dungeon="):
			_dungeon = arg.substr(10)
		elif arg.begins_with("--size="):
			_size = arg.substr(7)
		elif arg.begins_with("--level="):
			_level = int(arg.substr(8))
		elif arg.begins_with("--presets="):
			_presets = arg.substr(10).split(",", false)
		elif arg.begins_with("--heroes="):
			var picked: Array = []
			for h in arg.substr(9).split(","):
				var hs: String = str(h).strip_edges()
				if not hs.is_empty():
					picked.append(hs)
			if picked.size() > 0:
				_heroes = picked
		elif arg.begins_with("--skills="):
			_skills_mode = arg.substr(9)
		elif arg.begins_with("--resolve="):
			_resolve = int(arg.substr(10))
		elif arg == "--resolve-mult":
			_resolve_mult = true
		elif arg == "--no-guard":
			_no_guard = true
		elif arg == "--no-riposte":
			_no_riposte = true
		elif arg == "--no-move-value":
			_no_move_value = true
		elif arg == "--no-move-resist":
			_no_move_resist = true
		elif arg == "--no-summon":
			_no_summon = true
		elif arg == "--no-summon-value":
			_no_summon_value = true
		elif arg == "--no-summon-limit":
			_no_summon_limit = true
		elif arg == "--no-loot-table":
			_no_loot_table = true
		elif arg == "--no-curio-table":
			_no_curio_table = true
		elif arg == "--no-quirk":
			_no_quirk = true
		elif arg.begins_with("--quirks="):
			_quirks_per_hero = int(arg.substr(9))
		elif arg == "--no-trinket":
			_no_trinket = true
		elif arg.begins_with("--trinkets="):
			_trinkets_per_hero = int(arg.substr(11))
		elif arg.begins_with("--trinket-pick="):
			_trinket_polarity = arg.substr(15)
		elif arg.begins_with("--pack="):
			_pack_mode = arg.substr(7)
		elif arg.begins_with("--quirk-polarity="):
			_quirk_polarity = arg.substr(17)
		elif arg == "--no-curio-item":
			_no_curio_item = true
		elif arg.begins_with("--hall-curio="):
			_hall_curio = int(arg.substr(13))

	var db: DdDb = DdDb.shared(_data)
	if db.heroes.is_empty():
		push_error("数据未加载：%s" % (_data if not _data.is_empty() else "res://data"))
		quit(1)
		return
	if db.encounters.is_empty():
		push_error("dungeons.json 未加载，无法生成路线")
		quit(1)
		return

	# 路线先全部生成好，各预设共用同一批——这是对照实验的关键。
	# 若每个预设各生成一批路线，差异里就混进了「这次遇到的怪不一样」，
	# 得不出「资源层有没有用」的结论。
	var routes: Array = []
	for i in _runs:
		var rt: Array = RouteGen.build(db, _dungeon, _size, _level, DdRng.new(40000 + i))
		if _hall_curio > 0:
			rt = _inject_curios(db, rt, _hall_curio, DdRng.new(60000 + i))
		routes.append(rt)
	var bad: int = 0
	for r in routes:
		if (r as Array).is_empty():
			bad += 1
	if bad > 0:
		push_warning("%d/%d 条路线为空（遭遇表或地图参数缺失）" % [bad, _runs])

	var result: Dictionary = {
		"runs": _runs,
		"data": _data,
		"dungeon": _dungeon,
		"size": _size,
		"level": _level,
		"heroes": _heroes,
		"route_steps_avg": _route_len(routes),
		"presets": {},
	}

	for name in _presets:
		if not (db.expedition_cfg.presets as Dictionary).has(name):
			push_warning("未知预设 %s，跳过" % name)
			continue
		result["presets"][name] = _bench(db, name, routes)

	var text: String = JSON.stringify(result, "  ")
	if _out.is_empty():
		print(text)
	else:
		var f: FileAccess = FileAccess.open(_out, FileAccess.WRITE)
		if f == null:
			push_error("无法写入 %s" % _out)
			quit(1)
			return
		f.store_string(text)
		f.close()
	_print_table(result)
	quit(0)


## 全员按 `_resolve` 级算，进本时每人该吃多少压力（M25）。
##
## 刻意不引用 `Campaign.entry_stress`——bench 跑的是远征层，
## 把元层拖进来会让「改元层要不要重跑 bench」变成一个问题。
## 常量只借一个，规则本身三行就能对齐。
func _entry_stress_map() -> Dictionary:
	var low: int = maxi(0, _level - _resolve)
	var v: float = float(low) * Campaign.JOIN_STRESS_PER_LEVEL
	var out: Dictionary = {}
	for h in _heroes:
		out[str(h)] = v
	return out


## 全员按 `_resolve` 级算，进本后每次受压的倍率（M29）。
## 只有 `--resolve-mult` 才灌——默认不灌，M25 的基线和更早的历史都逐位不变。
func _stress_mult_map() -> Dictionary:
	var v: float = 1.0 + float(maxi(0, _level - _resolve)) \
		* Campaign.JOIN_STRESS_MULT_PER_LEVEL
	var out: Dictionary = {}
	for h in _heroes:
		out[str(h)] = v
	return out


## 每人带哪 4 个（`--skills=loadout`）。读 `heroes.json` 的 skill_selection
## 和 `campaign.json` 的 default_skills，和元层走同一个 `SkillLoadout`。
func _loadouts(db: DdDb) -> Dictionary:
	var tbl: Dictionary = db.hero_skill_table()
	var cfg: Dictionary = db.campaign_cfg
	var out: Dictionary = {}
	for hid in _heroes:
		var k: String = str(hid)
		out[k] = SkillLoadout.default_for(tbl, cfg, k)
	return out


func _route_len(routes: Array) -> float:
	var s: int = 0
	for r in routes:
		s += (r as Array).size()
	return float(s) / float(maxi(routes.size(), 1))


func _bench(db: DdDb, preset_name: String, routes: Array) -> Dictionary:
	var preset: Dictionary = db.expedition_cfg.preset(preset_name)
	var rows: Array = []
	for i in _runs:
		var exp := Expedition.new()
		# 进本压力必须在 setup **之前**灌（队伍状态在 setup 里建）。
		if _resolve > 0:
			exp.join_stress = _entry_stress_map()
		if not exp.setup(db, _heroes, routes[i], preset, 9000 + i, preset_name):
			continue
		exp.set_location(_dungeon, _size, _level)
		# 技能组：默认空 = 全装（M1~M18 的行为）。
		# 只有 --skills=loadout 才按「每人 4 个 + campaign.json 的默认组」装配，
		# 这样它和游戏内是对同一条路径——bench 数字才说明得了玩家的处境。
		if _skills_mode == "loadout":
			exp.hero_loadout = _loadouts(db)
		# 受压倍率由 start_battle 读取，setup 之后赋就行
		if _resolve > 0 and _resolve_mult:
			exp.join_stress_mult = _stress_mult_map()
		exp.guard_enabled = not _no_guard
		exp.riposte_enabled = not _no_riposte
		exp.move_value_enabled = not _no_move_value
		exp.move_resist_enabled = not _no_move_resist
		exp.summon_enabled = not _no_summon
		exp.summon_value_enabled = not _no_summon_value
		exp.summon_default_limit_enabled = not _no_summon_limit
		exp.loot_table_enabled = not _no_loot_table
		exp.curio_table_enabled = not _no_curio_table
		exp.quirk_enabled = not _no_quirk
		exp.trinket_enabled = not _no_trinket
		# base 不调用 set_start_supplies（空字典 = 不覆盖），
		# 所以默认路径与 M13~M15 逐位一致。
		exp.set_start_supplies(_pack_for())
		exp.curio_auto_item_enabled = not _no_curio_item
		# 默认 0：不塞怪癖，历史基线逐位不变。
		# 只有显式 --quirks=N 才给每个人挂 N 条（正负交替），
		# 用来回答「怪癖到底改变了什么」。
		if _quirks_per_hero > 0:
			exp.seed_quirks(_make_quirks(db, i))
		# 默认 0：谁都不戴，历史基线逐位不变。
		if _trinkets_per_hero > 0:
			exp.set_hero_trinkets(_make_trinkets(db, i))
		exp.run_auto()
		rows.append(exp.summary())
	return _aggregate(rows, preset_name)


func _aggregate(rows: Array, preset_name: String) -> Dictionary:
	var n: int = rows.size()
	if n == 0:
		return {"runs": 0}

	var sums: Dictionary = {}
	for key in ["battles", "rounds", "hero_deaths", "afflictions", "virtues",
			"heart_attacks", "dd_entries", "act_outs", "heals", "heals_blocked",
			"hunger_checks", "hunger_unfed", "camp_used", "camp_ambush",
			"torches_used", "steps_done", "steps_total", "alive",
			"hp_end", "stress_end", "hp_low_water", "light_end", "food_end",
			"torch_end", "overkill_ratio", "hit_rate", "crit_rate",
			"afflicted_alive", "virtuous_alive", "at_deaths_door_end",
			"alive_ratio", "heal_charges_left",
			"gold", "heirloom_total", "gems_total", "trinkets", "supply_end",
			"curios", "curio_loot", "curio_stress", "curio_items_used",
			"curio_unsupported", "curio_hp_lost",
			"trinkets_equipped",
			"quirks_total", "diseases_total", "quirks_gained",
			"diseases_contracted", "diseases_resisted", "diseases_cured",
			"quirks_purged", "quirk_purge_failed", "quirk_pool_empty",
			"quirk_refused_slot_full", "quirk_refused_duplicate", "light_drained",
			"quirk_refused_no_hero", "quirk_refused_no_lib", "quirk_refused_unknown_quirk",
			"quirk_target_empty", 			"curio_oc_nothing", "curio_oc_loot", "curio_oc_effect", "curio_oc_quirk",
			"curio_oc_disease", "curio_oc_purge", "curio_oc_scouting",
			"curio_oc_teleport", "curio_oc_summon"]:
		sums[key] = 0.0
	var complete: int = 0
	var wiped: int = 0
	var retreated: int = 0

	for r in rows:
		for k in sums.keys():
			sums[k] = float(sums[k]) + float(r.get(k, 0.0))
		if bool(r.get("completed", false)):
			complete += 1
		if bool(r.get("wiped", false)):
			wiped += 1
		if bool(r.get("retreated", false)):
			retreated += 1

	var out: Dictionary = {"runs": n, "preset": preset_name}
	for k in sums.keys():
		out[k] = snappedf(float(sums[k]) / float(n), 0.0001)

	out["complete_rate"] = float(complete) / float(n)
	out["wipe_rate"] = float(wiped) / float(n)
	out["retreat_rate"] = float(retreated) / float(n)
	# 人均口径：每个「英雄·趟」的死亡率/崩溃率。
	# 注意 sums 存的是**每趟平均**，所以分母是队伍人数而不是「趟数×人数」——
	# 这里写错过一次，结果 0.975 的团灭率算出来死亡率只有 0.02。
	var per_hero: float = float(_heroes.size())
	out["death_rate_per_hero_run"] = float(out["hero_deaths"]) / per_hero
	out["affliction_rate_per_hero_run"] = float(out["afflictions"]) / per_hero
	out["virtue_rate_per_hero_run"] = float(out["virtues"]) / per_hero
	out["heart_attack_rate_per_hero_run"] = float(out["heart_attacks"]) / per_hero
	out["dd_rate_per_hero_run"] = float(out["dd_entries"]) / per_hero
	out["step_completion"] = float(out["steps_done"]) / maxf(float(out["steps_total"]), 1.0)
	# 综合压迫指数：把四个方向的信号压成一个数，便于一眼对比。
	# 权重是设计判断，不是物理量——所以原始指标全部保留，别只看这个数。
	out["pressure_index"] = snappedf(
		float(out["wipe_rate"]) * 1.0
		+ float(out["retreat_rate"]) * 0.7
		+ float(out["death_rate_per_hero_run"]) * 2.0
		+ float(out["affliction_rate_per_hero_run"]) * 0.8
		+ float(out["heart_attack_rate_per_hero_run"]) * 1.2, 0.0001)
	return out


func _print_table(result: Dictionary) -> void:
	print("\n远征测量  %s/%s  Lv%d  %d 趟/预设  路线平均 %.1f 步" % [
		result["dungeon"], result["size"], int(result["level"]),
		int(result["runs"]), float(result["route_steps_avg"])])
	var cols: Array = result["presets"].keys()
	var head: String = "%-26s" % "指标"
	for c in cols:
		head += "%12s" % c
	print(head)
	var rows: Array = [
		["完成率", "complete_rate"], ["撤退率", "retreat_rate"],
		["团灭率", "wipe_rate"], ["英雄死亡率", "death_rate_per_hero_run"],
		["崩溃率", "affliction_rate_per_hero_run"],
		["美德率", "virtue_rate_per_hero_run"],
		["心脏骤停率", "heart_attack_rate_per_hero_run"],
		["死门次数/趟", "dd_entries"],
		["崩溃者摆烂次数/趟", "act_outs"],
		["治疗被封次数/趟", "heals_blocked"],
		["终局血量", "hp_end"], ["最低血量水位", "hp_low_water"],
		["终局压力", "stress_end"],
		["终局光照", "light_end"], ["终局口粮", "food_end"],
		["终局火把", "torch_end"], ["断粮次数/趟", "hunger_unfed"],
		["休整次数/趟", "camp_used"], ["营地被偷袭/趟", "camp_ambush"],
		["推进进度", "step_completion"],
		["压迫指数", "pressure_index"],
	]
	for r in rows:
		var line: String = "%-26s" % r[0]
		for c in cols:
			var v: float = float((result["presets"][c] as Dictionary).get(r[1], 0.0))
			# 比率两位小数，其余一位
			if r[1].ends_with("_rate") or r[1] == "step_completion" or r[1] == "pressure_index":
				line += "%12.3f" % v
			elif r[1].begins_with("hp_") or r[1] == "stress_end" or r[1] == "alive_ratio":
				line += "%12.3f" % v
			else:
				line += "%12.2f" % v
		print(line)
	print("")


## 线性路线没有「走廊」这个概念，奇物是按地图的 hallway_curio 百分比撒的，
## RouteGen 不生成它们。为了能在 bench 里量到奇物，这里显式注入 N 个。
## 默认 0：不加就不会改变任何历史基线（路线长度变了，step_index 就全变）。
func _inject_curios(db: DdDb, route: Array, n: int, rng: DdRng) -> Array:
	var out: Array = route.duplicate(true)
	if db == null or db.curio_lib == null or not db.curio_lib.is_loaded():
		return out
	for k in n:
		var cid: String = db.curio_lib.pick(_dungeon, CurioLib.SLOT_HALL, rng)
		if cid.is_empty():
			continue
		var pos: int = rng.next_int(out.size() + 1)
		out.insert(pos, {"kind": "curio", "curio": cid, "slot": CurioLib.SLOT_HALL})
	return out


## 给这趟的四个人各挂 N 条怪癖，正负交替。
## 用独立的 rng（70000+i）保证「同一趟、同一种子」可复现，
## 而且抽怪癖这个动作不会污染战斗/掉落/奇物任何一条既有随机流。
func _make_quirks(db: DdDb, run_index: int) -> Dictionary:
	var out: Dictionary = {}
	if db.quirk_lib == null or not db.quirk_lib.is_loaded():
		return out
	var qrng: DdRng = DdRng.new(70000 + run_index)
	for hid in _heroes:
		var lst: Array = []
		for k in _quirks_per_hero:
			var pol: String = "positive" if k % 2 == 0 else "negative"
			if _quirk_polarity == "neg":
				pol = "negative"
			elif _quirk_polarity == "pos":
				pol = "positive"
			var qid: String = db.quirk_lib.pick(pol, qrng, lst, false)
			if not qid.is_empty():
				lst.append(qid)
		out[str(hid)] = lst
	return out


## 给四个人各挂 N 件饰品，用独立 rng（80000+i），理由同 _make_quirks：
## 抽饰品这件事不能污染战斗/掉落/奇遇任何一条既有随机流。
##
## `--trinket-pick` 三种：
##   mix  —— 按稀有度随机（接近「打到什么戴什么」）
##   best —— 只挑对战斗有利的（速度/伤害/暴击/闪避）
##   worst—— 只挑有负面副作用的（速度/伤害/闪避为负）
## 这是为了回答「饰品到底带来多少收益」——只随机抽，正负会互相抵消。
func _make_trinkets(db: DdDb, run_index: int) -> Dictionary:
	var out: Dictionary = {}
	var tl: TrinketLib = db.trinket_lib
	if tl == null or not tl.is_loaded():
		return out
	var trng: DdRng = DdRng.new(80000 + run_index)
	var pool: Array = _trinket_pool_for(tl)
	for hid in _heroes:
		var lst: Array = []
		for k in _trinkets_per_hero:
			var picks: Array = []
			for id in pool:
				if tl.fits_class(str(id), str(hid)):
					picks.append(str(id))
			if picks.is_empty():
				break
			var chosen: String = str(picks[trng.next_int(picks.size())])
			if not lst.has(chosen):
				lst.append(chosen)
		out[str(hid)] = lst
	return out


## 按 --trinket-pick 过滤候选池。判据只看 combat_stat_add 里的四项，
## 因为那是唯一能一眼看出「好/坏」的通道。
func _trinket_pool_for(tl: TrinketLib) -> Array:
	var out: Array = []
	for id in tl.order:
		var rid: String = str(id)
		if tl.rarity_of(rid) == TrinketLib.RARITY_KICKSTARTER:
			continue
		if _trinket_polarity == "mix":
			out.append(rid)
			continue
		var score: float = _trinket_score(tl, rid)
		if _trinket_polarity == "best" and score > 0.5:
			out.append(rid)
		elif _trinket_polarity == "worst" and score < -0.5:
			out.append(rid)
	return out


## 一件饰品的「好坏」粗分。
##
## 只认 always 规则，因为带条件的件在平均意义上不确定——拿它们分组
## 会让「好/坏」两组混进同一批东西，对照就失去意义。
##
## 两类都要算：`combat_stat_add` 的加减，和 `combat_stat_multiply` 的
## 伤害倍率。第一版只算了前者，结果「好」组反而比随机组差——
## 因为 damage_low/high 的倍率件（+10% 伤害）全被漏掉了。
func _trinket_score(tl: TrinketLib, id: String) -> float:
	var sc: float = 0.0
	for b in tl.buffs_for([id]):
		if str(b.get("rule_type", "")) != BuffRules.RULE_ALWAYS:
			continue
		var st: String = str(b.get("stat_type", ""))
		var sub: String = str(b.get("stat_sub_type", ""))
		var amt: float = float(b.get("amount", 0.0))
		if st == "combat_stat_add":
			if sub in ["speed_rating", "crit_chance", "attack_rating"]:
				sc += amt
			elif sub == "defense_rating":
				sc += amt * 10.0
		elif st == "combat_stat_multiply":
			# 倍率换算成「等价点数」：+10% 伤害约等于 +1 点
			if sub in ["damage_low", "damage_high"]:
				sc += amt * 10.0
		elif st in ["stress_dmg_received_percent"]:
			sc -= amt * 5.0
	return sc


## 补给包。`base` 返回空字典——`set_start_supplies({})` 是「不覆盖」，
## 这条路径必须和历史完全一样，否则所有 bench 数字作废。
func _pack_for() -> Dictionary:
	match _pack_mode:
		"lean":
			return {"torch": 1, "food": 1, "shovel": 0, "bandage": 0, "antivenom": 0,
				"medicinal_herbs": 0, "holy_water": 0, "skeleton_key": 0}
		"rich":
			return {"torch": 8, "food": 8, "shovel": 4, "bandage": 6, "antivenom": 6,
				"medicinal_herbs": 6, "holy_water": 6, "skeleton_key": 6}
		# 拆开测：到底是缺火把伤了，还是缺口粮伤了。两者机制完全不同
		# （火把掉光照→全队加压；口粮断了→饥饿直接伤人）。
		"nofood":
			return {"torch": 4, "food": 0, "shovel": 1, "bandage": 1, "antivenom": 1,
				"medicinal_herbs": 1, "holy_water": 1, "skeleton_key": 1}
		"notorch":
			return {"torch": 0, "food": 4, "shovel": 1, "bandage": 1, "antivenom": 1,
				"medicinal_herbs": 1, "holy_water": 1, "skeleton_key": 1}
		_:
			return {}

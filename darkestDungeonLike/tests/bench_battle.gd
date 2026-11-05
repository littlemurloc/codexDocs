extends SceneTree
## 战斗手感基准测量器。
##
## 目的：把"手感"换成可对比的数字，让换数值这件事有依据，而不是凭感觉。
##
## 用法：
##   godot --headless --path . --script res://tests/bench_battle.gd -- [--runs=N] [--out=path]
##
## 输出 JSON 指标，供 tools/compare_balance.py 对比不同数值包。

const HEROES: Array = ["crusader", "highwayman", "vestal", "plague_doctor"]
## 三档难度的标准遭遇：同族不同变体，保证只有难度在变。
## 队伍装备等级同步提升——DD1 里打 5 层的队伍不会还穿 1 阶装备，
## 否则测出来的是"1 级队打 5 层"这种不存在的场景。
const ENCOUNTERS: Dictionary = {
	"tier1_weald": {
		"monsters": ["cultist_brawler_A", "cultist_brawler_A", "cultist_witch_A"],
		"gear": 0, "skill": 0,
	},
	"tier2_weald": {
		"monsters": ["cultist_brawler_B", "cultist_brawler_B", "cultist_witch_B"],
		"gear": 2, "skill": 2,
	},
	"tier3_weald": {
		"monsters": ["cultist_brawler_C", "cultist_brawler_C", "cultist_witch_C"],
		"gear": 4, "skill": 4,
	},
	# 高压场景：满编四只、最高难度。前三档都太安全（100% 全胜、零死亡），
	# 只有加大敌方规模才能看出危险度维度的差异。
	"tier3_pressured": {
		"monsters": ["cultist_brawler_C", "cultist_brawler_C",
			"cultist_witch_C", "cultist_witch_C"],
		"gear": 4, "skill": 4,
	},
}

## 位移专项遭遇（M11）。**不进 summary**——它们的存在是为了回答
## 「AI 会不会用位移技能」，而不是「这队人有多强」。
##
## 默认那三档遭遇里没有一只怪带 push/pull（`cultist_witch_C` 有，但它的
## `cultist_incantation` 带 +20 压力，估值远高于推 2 格，所以永远不选它）。
## 也就是说：光看默认遭遇，永远测不出位移到底通没通。
const MOVE_PROBES: Dictionary = {
	# 主技能 pincer_smack：3–7 伤 + 眩晕 + push 3，伤害和位移都在
	"crabby_push3": {
		"monsters": ["fishman_crabby_A", "fishman_crabby_A", "fishman_crabby_A"],
		"gear": 0, "skill": 0,
	},
	# 主技能 shambler_howl：1–1 伤 + 10 压力 + 洗整个队伍
	"shambler_shuffle": {
		"monsters": ["shambler_A"],
		"gear": 2, "skill": 2,
	},
	# 反对照：witch 有位移技能，但它的 incantation 带 +20 压力。
	# 期望是「一次都不用」——这不是 bug，是这个 AI 判断对了。
	"witch_no_push": {
		"monsters": ["cultist_witch_C", "cultist_witch_C", "cultist_witch_C"],
		"gear": 4, "skill": 4,
	},
}

## 召唤专项遭遇（M12）。同样**不进 summary**——它们回答的是
## 「召唤到底通没通、值不值」，不是「这队人有多强」。
##
## 默认三档遭遇里一只召唤怪都没有，所以光跑 summary 永远看不见 M12。
const SUMMON_PROBES: Dictionary = {
	# 死灵法师：召唤是它的核心动作，且阵型是 3 人（留一个空位给它）。
	"necromancer": {
		"monsters": ["necromancer_A", "skeleton_common_A", "skeleton_common_A"],
		"gear": 2, "skill": 2,
	},
	# 溺亡船长：all_hands 是「召唤锚 + pull 3」，伤害为 0，纯功能性。
	"drowned_captain": {
		"monsters": ["drowned_captain_A", "drowned_pirate_A", "drowned_pirate_A"],
		"gear": 2, "skill": 2,
	},
	# 极端场景：史莱姆分裂，数据里**没有 summon_limits**，只能靠 4 格兜底。
	# 这一栏存在的目的就是把这个失控幅度量出来，而不是假装它不存在。
	"ectoplasm_split": {
		"monsters": ["ectoplasm_A", "cultist_brawler_A"],
		"gear": 0, "skill": 0,
	},
	# 反对照：炮船有召唤技，但 cannon_boom 期望伤害 9–27，估值远高于
	# 召唤一个 5 血炮灰。期望是「一次都不召」——AI 判断对了，不是没实现。
	"cannon_no_summon": {
		"monsters": ["brigand_cannon_A", "brigand_cutthroat_A"],
		"gear": 2, "skill": 2,
	},
}

var _runs: int = 120
var _out_path: String = ""
var _data: String = ""
## 队伍可换：M10 的守护/反击只长在 man_at_arms / highwayman 身上，
## 默认队伍里只有一个强盗，测不出「有人替你挡刀」的差别。
## 换队伍会改变所有绝对数字，所以默认仍是原四人组——换队形是另一个实验，不是新基线。
var _heroes: Array = HEROES.duplicate()
## 对照开关：同队伍、同种子，只把守护/反击关掉。
## 「守护到底有没有用」不能靠换职业来证明——换了职业，变化的就不只是守护。
var _no_guard: bool = false
var _no_riposte: bool = false
## M11 的两个对照开关。分开是因为它们回答的是两个不同的问题：
##   --no-move-value   怪物不会去选带位移的技能（= M10 的行为）
##   --no-move-resist  位移不被抵抗（抗性只影响 rng 序列与命中率，不影响「会不会用」）
var _no_move_value: bool = false
var _no_move_resist: bool = false
## M12 的两个对照开关：
##   --no-summon        召唤实现整个关掉（回到 M11：召唤技被丢弃）
##   --no-summon-value  只关估值。用来区分「AI 不选」和「机制无效」——
##                      M11 已经证明，关掉估值就等于没实现。
var _no_summon: bool = false
var _no_summon_value: bool = false


func _initialize() -> void:
	for arg in OS.get_cmdline_user_args():
		if arg.begins_with("--runs="):
			_runs = int(arg.substr(7))
		elif arg.begins_with("--out="):
			_out_path = arg.substr(6)
		elif arg.begins_with("--data="):
			_data = arg.substr(7)
		elif arg.begins_with("--heroes="):
			var raw: Array = arg.substr(9).split(",")
			var picked: Array = []
			for h in raw:
				var hs: String = str(h).strip_edges()
				if not hs.is_empty():
					picked.append(hs)
			if picked.size() > 0:
				_heroes = picked
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

	var db: DdDb = DdDb.shared(_data)
	if db.heroes.is_empty():
		push_error("数据未加载：%s" % (_data if not _data.is_empty() else "res://data"))
		quit(1)
		return

	var result: Dictionary = {
		"runs_per_scenario": _runs,
		"heroes": _heroes,
		"data": _data,
		"guard_enabled": not _no_guard,
		"riposte_enabled": not _no_riposte,
		"move_value_enabled": not _no_move_value,
		"move_resist_enabled": not _no_move_resist,
		"summon_enabled": not _no_summon,
		"summon_value_enabled": not _no_summon_value,
		"scenarios": {},
	}
	for name in ENCOUNTERS.keys():
		result["scenarios"][name] = _bench(db, ENCOUNTERS[name])

	# 连续遭遇：血量不清零、压力不回落。
	# 单场普通交火根本打不死人（怪物单次 2-7 伤、英雄 22-33 血），
	# DD1 的死亡风险来自「连续几场没有休整」，这个维度不测就等于没测。
	result["scenarios"]["gauntlet_3x_tier3"] = _bench_gauntlet(db)

	# 位移专项：单独一栏，不进 summary
	result["move_probe"] = {}
	for name in MOVE_PROBES.keys():
		result["move_probe"][name] = _bench(db, MOVE_PROBES[name])

	# 召唤专项（M12）：同样单独一栏
	result["summon_probe"] = {}
	for name in SUMMON_PROBES.keys():
		result["summon_probe"][name] = _bench(db, SUMMON_PROBES[name])

	# 汇总：跨场景取平均，方便一眼对比
	result["summary"] = _summarize(result["scenarios"])

	var text: String = JSON.stringify(result, "  ")
	if _out_path.is_empty():
		print(text)
	else:
		var f: FileAccess = FileAccess.open(_out_path, FileAccess.WRITE)
		if f == null:
			push_error("无法写入 %s" % _out_path)
			quit(1)
			return
		f.store_string(text)
		f.close()
		# 浏览器看不了 JSON，直接打一份摘要到 stdout
		print("__SUMMARY__ %s" % JSON.stringify(result["summary"]))
	quit(0)


func _bench(db: DdDb, spec: Dictionary) -> Dictionary:
	var monster_ids: Array = spec["monsters"]
	var gear: int = int(spec.get("gear", 0))
	var skill: int = int(spec.get("skill", 0))
	var acc: Dictionary = {
		"rounds": [], "hero_alive": [], "hero_deaths": [], "stress_end": [],
		"deaths_door_hits": [], "overkill_ratio": [], "damage_ratio": [],
		"hits": 0, "attacks": 0, "crits": 0, "party_wins": 0,
		"timeouts": 0, "first_kill_round": [],
		# —— 守护 / 反击（M10）——
		"guard_ups": 0, "guard_blocks": 0, "ripostes": 0, "riposte_dmg": 0.0,
		# —— 位移 / 洗位（M11）——
		"forced_moves": 0, "shuffles": 0, "move_resists": 0,
		# —— 召唤（M12）——
		# enemy_peak 是「场上最多同时有几个敌人」，它才是召唤的真实结果：
		# 召唤事件数会重复统计同一次成功，peak 不会。
		"summons": 0, "summon_fails": 0, "enemy_peak": 0, "enemy_end": 0,
		"total_dealt": 0.0,
		# 危险度必须是连续量：只看「死没死」太钝，
		# 怪物伤害 +60% 都可能仍然零死亡，血量占比却会立刻响应
		"hp_end_ratio": [], "hp_low_water": [],
	}
	# 用同一段种子区间，保证不同数值包之间是可比样本
	for i in _runs:
		var b: Battle = Battle.new()
		b.setup(_heroes, monster_ids, 9000 + i, gear, skill)
		b.guard_enabled = not _no_guard
		b.riposte_enabled = not _no_riposte
		b.move_value_enabled = not _no_move_value
		b.move_resist_enabled = not _no_move_resist
		b.summon_enabled = not _no_summon
		b.summon_value_enabled = not _no_summon_value

		# Battle.events 每轮开头会重置，必须自己逐轮累积；
		# 同时给事件打上轮次，否则事后读 b.round_index 只能拿到结束时的总轮数
		var log: Array = []
		# 阵容峰值按「每轮采样」而不是「数召唤事件」：同一只怪可以被反复
		# 召唤，事件数会高估规模；峰值只关心「最多同时有几个」。
		var peak: int = b.enemies.size()
		while not b.is_over() and b.round_index < Battle.MAX_ROUNDS:
			var evs: Array = b.run_round()
			peak = maxi(peak, b.enemies.size())
			for e in evs:
				e["_round"] = b.round_index
				log.append(e)

		acc["rounds"].append(b.round_index)
		acc["enemy_peak"] += peak
		acc["enemy_end"] += b.enemies.size()
		var alive: int = 0
		var deaths: int = 0
		var stress_sum: float = 0.0
		var hp_sum: float = 0.0
		var hp_low: float = 1.0
		for u in b.party:
			if u.dead:
				deaths += 1
			else:
				alive += 1
			stress_sum += u.stress
			var ratio: float = u.hp_ratio()
			hp_sum += ratio
			hp_low = minf(hp_low, ratio)
		acc["hero_alive"].append(alive)
		acc["hp_end_ratio"].append(hp_sum / maxf(1.0, float(b.party.size())))
		acc["hp_low_water"].append(hp_low)
		acc["hero_deaths"].append(deaths)
		acc["stress_end"].append(stress_sum / maxf(1.0, float(b.party.size())))
		if b.winner() == "party":
			acc["party_wins"] += 1
		if b.round_index >= Battle.MAX_ROUNDS:
			acc["timeouts"] += 1

		# 从事件流里提指标
		var total_dealt: float = 0.0
		var total_gross: float = 0.0
		var total_overkill: float = 0.0
		var dd_hits: int = 0
		var enemy_hp_total: float = 0.0
		for u in b.enemies:
			enemy_hp_total += float(u.base_hp)
		var kill_round: int = -1
		for e in log:
			match str(e.get("t", "")):
				"miss":
					acc["attacks"] += 1
				"attack":
					acc["attacks"] += 1
					acc["hits"] += 1
					var dmg: float = float(e.get("damage", 0))
					var gross: float = float(e.get("gross", dmg))
					total_dealt += dmg
					total_gross += gross
					# 反击打出来的伤害要单独记。靠技能 id 区分——反击用的是
					# 虚拟技能 "riposte"，这是唯一能把它和普通攻击分开的无歧义标记。
					if str(e.get("skill", "")) == "riposte":
						acc["riposte_dmg"] += dmg
					# 真实溢出：扣血条之前 vs 实际扣掉。用 raw 会混入护甲减免。
					total_overkill += maxf(0.0, gross - dmg)
					if bool(e.get("crit", false)):
						acc["crits"] += 1
					if bool(e.get("deaths_door", false)):
						dd_hits += 1
				"guard_up":
					acc["guard_ups"] += 1
				"guard":
					# 重定向：这一击本来打 A，实际打在 B 身上
					acc["guard_blocks"] += 1
				"riposte":
					acc["ripostes"] += 1
				"move":
					# 三种 move 要分开：洗位、被技能推拉、英雄自己走的。
					# 混在一起就看不出「怪物到底有没有在推人」。
					if bool(e.get("shuffle", false)):
						acc["shuffles"] += 1
					elif str(e.get("skill", "")) != "move":
						acc["forced_moves"] += 1
				"effect":
					if str(e.get("resisted", "")) == "move":
						acc["move_resists"] += 1
				"summon":
					acc["summons"] += 1
				"summon_fail":
					acc["summon_fails"] += 1
				"death":
					if kill_round < 0:
						kill_round = int(e.get("_round", b.round_index))
		acc["deaths_door_hits"].append(dd_hits)
		acc["overkill_ratio"].append(
			total_overkill / total_gross if total_gross > 0.0 else 0.0)
		acc["damage_ratio"].append(
			total_dealt / enemy_hp_total if enemy_hp_total > 0.0 else 0.0)
		acc["total_dealt"] += total_dealt
		acc["first_kill_round"].append(kill_round if kill_round > 0 else b.round_index)

	var attacks: int = int(acc["attacks"])
	var out: Dictionary = {
		"runs": _runs,
		"rounds_avg": _avg(acc["rounds"]),
		"rounds_p50": _pct(acc["rounds"], 0.5),
		"rounds_p90": _pct(acc["rounds"], 0.9),
		"party_win_rate": _ratio(int(acc["party_wins"]), _runs),
		"hero_alive_avg": _avg(acc["hero_alive"]),
		"hero_death_rate": _ratio(_sumi(acc["hero_deaths"]), _runs * _heroes.size()),
		# 危险度主指标：连续、灵敏，死亡/死门只是它的极端形式
		"hero_hp_end_ratio": _avg(acc["hp_end_ratio"]),
		"hero_hp_low_water": _avg(acc["hp_low_water"]),
		"timeout_rate": _ratio(int(acc["timeouts"]), _runs),
		"stress_end_avg": _avg(acc["stress_end"]),
		"deaths_door_per_fight": _avg(acc["deaths_door_hits"]),
		"first_kill_round_avg": _avg(acc["first_kill_round"]),
		"hit_rate": _ratio(int(acc["hits"]), attacks),
		"crit_rate": _ratio(int(acc["crits"]), attacks),
		"overkill_ratio": _avg(acc["overkill_ratio"]),
		"damage_to_hp_ratio": _avg(acc["damage_ratio"]),
		# 守护/反击：这三个数回答的是「这套机制到底有没有在跑」。
		# 只加这几行而不加断言，是因为它们不是通过/失败，是频率与占比。
		"guard_up_per_fight": _ratio(int(acc["guard_ups"]), _runs),
		"guard_block_per_fight": _ratio(int(acc["guard_blocks"]), _runs),
		"riposte_per_fight": _ratio(int(acc["ripostes"]), _runs),
		"riposte_dmg_share": _ratio_f(float(acc["riposte_dmg"]), float(acc["total_dealt"])),
		# 位移 / 洗位（M11）：这三个数回答「怪物是不是真的开始打乱阵型了」
		"forced_move_per_fight": _ratio(int(acc["forced_moves"]), _runs),
		"shuffle_per_fight": _ratio(int(acc["shuffles"]), _runs),
		"move_resist_per_fight": _ratio(int(acc["move_resists"]), _runs),
		"summon_per_fight": _ratio(int(acc["summons"]), _runs),
		"summon_fail_per_fight": _ratio(int(acc["summon_fails"]), _runs),
		"enemy_peak_avg": _ratio(int(acc["enemy_peak"]), _runs),
		"enemy_end_avg": _ratio(int(acc["enemy_end"]), _runs),
	}
	return out


## 连续三场遭遇，中间不休整：继承血量与压力，阵亡者缺席后续战斗。
func _bench_gauntlet(db: DdDb) -> Dictionary:
	var spec: Dictionary = ENCOUNTERS["tier3_weald"]
	var monster_ids: Array = spec["monsters"]
	var gear: int = int(spec.get("gear", 0))
	var skill: int = int(spec.get("skill", 0))

	var tot_rounds: int = 0
	var tot_deaths: int = 0
	var wiped: int = 0
	var end_hp: Array = []
	var end_stress: Array = []
	var min_water: Array = []

	for i in _runs:
		var alive_ids: Array = _heroes.duplicate()
		var carry_hp: Dictionary = {}
		var carry_stress: Dictionary = {}
		var low: float = 1.0

		for leg in 3:
			var b: Battle = Battle.new()
			if not b.setup(alive_ids, monster_ids, 9000 + i * 31 + leg, gear, skill):
				break
			b.guard_enabled = not _no_guard
			b.riposte_enabled = not _no_riposte
			b.move_value_enabled = not _no_move_value
			b.move_resist_enabled = not _no_move_resist
			for u in b.party:
				# 继承的是血量比例，不是绝对值——各英雄上限不同，
				# 写死一个分母会得到超过 100% 的荒谬结果
				if carry_hp.has(u.def_id):
					var keep: float = float(carry_hp[u.def_id])
					u.hp = clampi(int(round(keep * float(u.base_hp))), 1, u.base_hp)
					u.stress = float(carry_stress[u.def_id])
					if keep <= 0.0:
						u.at_deaths_door = true
			while not b.is_over() and b.round_index < Battle.MAX_ROUNDS:
				var evs: Array = b.run_round()
				for e in evs:
					if str(e.get("t", "")) == "attack":
						low = minf(low, b.party[0].hp_ratio())
			tot_rounds += b.round_index

			var next_ids: Array = []
			for u in b.party:
				low = minf(low, u.hp_ratio())
				if u.dead:
					tot_deaths += 1
					continue
				next_ids.append(u.def_id)
				carry_hp[u.def_id] = u.hp_ratio()
				carry_stress[u.def_id] = u.stress
			alive_ids = next_ids
			if alive_ids.is_empty():
				wiped += 1
				break

		var hp_sum: float = 0.0
		var st_sum: float = 0.0
		for u in alive_ids:
			hp_sum += float(carry_hp.get(u, 0.0))
			st_sum += float(carry_stress.get(u, 0.0))
		if alive_ids.is_empty():
			end_hp.append(0.0)
			end_stress.append(200.0)
		else:
			end_hp.append(hp_sum / float(alive_ids.size()))
			end_stress.append(st_sum / float(alive_ids.size()))
		min_water.append(low)

	return {
		"runs": _runs,
		"rounds_avg": float(tot_rounds) / float(_runs),
		"hero_death_rate": _ratio(tot_deaths, _runs * _heroes.size()),
		"wipeout_rate": _ratio(wiped, _runs),
		"hero_hp_end_ratio": _avg(end_hp),
		"hero_hp_low_water": _avg(min_water),
		"stress_end_avg": _avg(end_stress),
	}


func _summarize(scen: Dictionary) -> Dictionary:
	var keys: Array = []
	for s in scen.values():
		for k in s.keys():
			if not keys.has(k) and k != "runs":
				keys.append(k)
	var out: Dictionary = {}
	for k in keys:
		var vals: Array = []
		for sname in scen.keys():
			# 连续遭遇是三场合计，混进平均会把轮数口径搞乱，单独看
			if str(sname).begins_with("gauntlet"):
				continue
			var s: Dictionary = scen[sname]
			if s.has(k):
				vals.append(float(s[k]))
		if not vals.is_empty():
			out[k] = snappedf(_avg(vals), 0.0001)
	return out


func _avg(a: Array) -> float:
	if a.is_empty():
		return 0.0
	var s: float = 0.0
	for v in a:
		s += float(v)
	return s / float(a.size())


func _sumi(a: Array) -> int:
	var s: int = 0
	for v in a:
		s += int(v)
	return s


func _ratio(a: int, b: int) -> float:
	return float(a) / float(b) if b > 0 else 0.0


func _ratio_f(a: float, b: float) -> float:
	return a / b if b > 0.0 else 0.0


func _pct(a: Array, q: float) -> float:
	if a.is_empty():
		return 0.0
	var s: Array = a.duplicate()
	s.sort()
	var idx: int = clampi(int(round(q * float(s.size() - 1))), 0, s.size() - 1)
	return float(s[idx])

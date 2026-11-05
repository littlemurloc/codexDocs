extends SceneTree
## 走廊内容测量器：陷阱与障碍到底有没有变成「决策」。
##
## 这一层最容易犯的错不是数值不准，而是**机制存在但没人会为它改变行为**。
## 如果玩家即使看见了陷阱也照直走，那么陷阱就只是「随机掉血按钮」，
## 和它在 M8 之前的状态没有区别。
##
## 所以这里跑两种策略，同一张图、同一个种子：
##   straight  一路走最短路，看见陷阱也照走
##   avoid     看见陷阱就绕（权重 +3，等价于绕 3 步的代价）
##
## 如果 avoid 的踩中次数没有明显下降，或者下降的代价（步数、补给）大过收益，
## 那就说明这层没做对——而不是「玩家不懂」。
##
## 用法：
##   godot --headless --path . --script res://tests/bench_hazards.gd -- \
##     --runs=60 --size=medium --level=3 --out=<绝对路径>

const HEROES: Array = ["crusader", "highwayman", "vestal", "plague_doctor"]
const MAX_STEPS: int = 400

var _runs: int = 60
var _size: String = "medium"
var _level: int = 3
var _dungeon: String = "weald"
var _out: String = ""
var _preset: String = "standard"
var _data: String = ""
## avoid 策略愿意为「躲开一个已知陷阱」付出几步的绕路代价。
## 扫描这个值等于在问：玩家的耐心是多少？
var _weight: float = 3.0


func _initialize() -> void:
	for arg in OS.get_cmdline_user_args():
		if arg.begins_with("--runs="):
			_runs = int(arg.substr(7))
		elif arg.begins_with("--size="):
			_size = arg.substr(7)
		elif arg.begins_with("--level="):
			_level = int(arg.substr(8))
		elif arg.begins_with("--dungeon="):
			_dungeon = arg.substr(10)
		elif arg.begins_with("--preset="):
			_preset = arg.substr(9)
		elif arg.begins_with("--weight="):
			_weight = float(arg.substr(9))
		elif arg.begins_with("--out="):
			_out = arg.substr(6)
		elif arg.begins_with("--data="):
			_data = arg.substr(7)

	var db: DdDb = DdDb.shared(_data)
	if db == null or db.heroes.is_empty():
		print("数据未加载")
		quit(1)
		return

	var straight: Dictionary = _run_all(db, "straight")
	var avoid: Dictionary = _run_all(db, "avoid")
	var smart: Dictionary = _run_all(db, "smart")

	var result: Dictionary = {
		"size": _size, "level": _level, "dungeon": _dungeon,
		"preset": _preset, "runs": _runs,
		"straight": straight, "avoid": avoid, "smart": smart,
	}
	_report(straight, avoid, smart)
	if not _out.is_empty():
		var f: FileAccess = FileAccess.open(_out, FileAccess.WRITE)
		if f != null:
			f.store_string(JSON.stringify(result, "  "))
			f.close()
			print("已写出 %s" % _out)
	quit(0)


func _run_all(db: DdDb, policy: String) -> Dictionary:
	var sum: Dictionary = _blank()
	for i in _runs:
		var seed_value: int = 9000 + i
		var one: Dictionary = _run_one(db, seed_value, policy)
		for k in one.keys():
			sum[k] = float(sum[k]) + float(one[k])
	var n: float = float(maxi(_runs, 1))
	var out: Dictionary = {}
	for k in sum.keys():
		out[k] = float(sum[k]) / n
	out["policy"] = policy
	return out


func _blank() -> Dictionary:
	return {
		"completed": 0.0, "wiped": 0.0, "retreated": 0.0,
		"steps": 0.0, "hp_end": 0.0, "stress_end": 0.0, "deaths": 0.0,
		"traps": 0.0, "traps_hit": 0.0, "traps_dodged": 0.0,
		"obstacles": 0.0, "obstacles_cleared": 0.0,
		"light_end": 0.0, "shovel_end": 0.0,
	}


func _run_one(db: DdDb, seed_value: int, policy: String) -> Dictionary:
	var m: Dictionary = MapGen.build(db, _dungeon, _size, _level, DdRng.new(seed_value))
	if m.is_empty():
		return _blank()
	var e := Expedition.new()
	e.setup(db, HEROES, [], db.expedition_cfg.preset(_preset), seed_value, _preset, {}, {})
	e.set_location(_dungeon, _size)
	e.enter_map(m)
	_drive(e, policy)

	var s: Dictionary = e.summary()
	var out: Dictionary = {
		"completed": 1.0 if str(s["end_reason"]) == "complete" else 0.0,
		"wiped": 1.0 if str(s["end_reason"]) == "wipe" else 0.0,
		"retreated": 1.0 if str(s["end_reason"]) == "retreat" else 0.0,
		"steps": float(s["steps_done"]),
		"hp_end": float(s["hp_end"]),
		"stress_end": float(s["stress_end"]),
		"deaths": float(s["hero_deaths"]),
		"traps": float(s.get("traps", 0)),
		"traps_dodged": float(s.get("traps_dodged", 0)),
		"obstacles": float(s.get("obstacles", 0)),
		"obstacles_cleared": float(s.get("obstacles_cleared", 0)),
		"light_end": float(s["light_end"]),
		"shovel_end": float(s.get("shovel_end", 0)),
	}
	out["traps_hit"] = float(out["traps"]) - float(out["traps_dodged"])
	return out


## 驱动一趟远征：优先消化待结算队列，否则在图上挪一步。
func _drive(e: Expedition, policy: String) -> void:
	var guard: int = 0
	while not e.ended and guard < MAX_STEPS:
		guard += 1
		if e.has_pending():
			e.run_step()
			continue
		if e.at_goal():
			e.leave_dungeon()
			return
		var nxt: int = _choose(e, policy)
		if nxt < 0:
			# 走不动就撤：这不是策略胜负，是地图被走遍了
			e.retreat()
			return
		if not e.travel(nxt):
			e.retreat()
			return


## 选下一步。
##
## straight：只按「离目标还有几步」走。
## avoid   ：在同样的距离上，给已知有陷阱的走廊加权重，宁可多走几步绕开。
func _choose(e: Expedition, policy: String) -> int:
	var nbs: Array = e.adjacent()
	if nbs.is_empty():
		return -1
	var goal: int = int(e.map["goal"])
	var n: int = (e.map["room_ids"] as Array).size()
	var pairs: Array = []
	for edge in (e.map["edges"] as Array):
		pairs.append(Vector2i(int(edge.a), int(edge.b)))
	var adj: Dictionary = MapGen.adjacency_rooms(n, pairs)
	var dist: Array = MapGen.bfs(n, adj, goal)

	var best: int = -1
	var best_cost: float = 1e9
	for nb in nbs:
		var rid: int = int(nb.room)
		var d: float = float(dist[rid]) if int(dist[rid]) >= 0 else 999.0
		var cost: float = d
		if policy == "avoid":
			# 已知有陷阱/障碍就当作 3 步的代价。数值不重要，
			# 重要的是「是否愿意为安全多走一段」这件事被真的计算了。
			# 只对**已知**的陷阱/障碍加权。
			# 第一版还给「未知走廊」加了 0.6，结果 avoid 变成「乱走」：
			# 未知走廊占多数，它绕的不是陷阱而是信息盲区，
			# 于是对照组测出来的是「瞎逛比走最短路更差」这种废话。
			var k: String = e.edge_kind(int(nb.edge))
			if k == "trap" or k == "obstacle":
				cost += _weight
		elif policy == "smart":
			# 综合评分：距离 / 走廊内容 / 房间类型一起看。
			#
			# 这一组存在的意义是回答一个问题：avoid 输给 straight，
			# 到底是「陷阱不值得躲」，还是「只看陷阱这一个因素本来就会输」？
			# 单目标优化输给综合判断是必然的，不分开这两件事就会得出错误结论。
			# 距离主导（×10），局部判断只在**同样近**的候选之间起作用。
			# 第一版让奇物房 -1.0 直接抵消一步距离，结果策略为了捡奇物
			# 反复横跳：推进 6.2 间（比最短路少 3.5），光照掉到 21，
			# 完成率 0.30。那是贪心震荡，不是「信息不值钱」。
			var cur_d: int = int(dist[int(e.current_room)])
			var rk: String = e.room_kind(rid)
			var bonus: float = 0.0
			match e.edge_kind(int(nb.edge)):
				"trap":
					bonus += 1.5
				"obstacle":
					bonus += 1.5
				"battle":
					bonus += 2.0
				"hunger":
					bonus -= 0.8     # 饥饿检定是补血点，值得顺路
			if rk == MapGen.K_BATTLE:
				bonus += 2.0
			elif rk == MapGen.K_CURIO:
				bonus -= 1.2
			cost = float(d) * 10.0 + bonus
			if int(d) > cur_d:
				continue        # 不往回走：这一步会把趟数拖成来回横跳
		if cost < best_cost:
			best_cost = cost
			best = rid
	return best


func _report(a: Dictionary, b: Dictionary, c: Dictionary) -> void:
	print("")
	print("走廊内容 · %s %s Lv%d · %d 趟 · 预设 %s" % [_dungeon, _size, _level, _runs, _preset])
	print("")
	print("指标              straight       avoid       smart")
	print("-----------------------------------------------------")
	_row3("完成率", a["completed"], b["completed"], c["completed"])
	_row3("团灭率", a["wiped"], b["wiped"], c["wiped"])
	_row3("平均推进房间", a["steps"], b["steps"], c["steps"])
	_row3("踩中陷阱", a["traps_hit"], b["traps_hit"], c["traps_hit"])
	_row3("躲开陷阱", a["traps_dodged"], b["traps_dodged"], c["traps_dodged"])
	_row3("遭遇障碍", a["obstacles"], b["obstacles"], c["obstacles"])
	_row3("凿开障碍", a["obstacles_cleared"], b["obstacles_cleared"], c["obstacles_cleared"])
	_row3("阵亡人数", a["deaths"], b["deaths"], c["deaths"])
	_row3("终局血量", a["hp_end"], b["hp_end"], c["hp_end"])
	_row3("终局压力", a["stress_end"], b["stress_end"], c["stress_end"])
	_row3("终局光照", a["light_end"], b["light_end"], c["light_end"])
	print("")

	var hit_a: float = float(a["traps_hit"])
	var hit_b: float = float(b["traps_hit"])
	if hit_a > 0.01:
		var drop: float = (hit_a - hit_b) / hit_a * 100.0
		print("绕路把踩中次数从 %.2f 降到 %.2f（%+.0f%%）" % [hit_a, hit_b, -drop])
	else:
		print("陷阱几乎没被踩到——检查侦察率与走廊密度是否太低")
	if float(b["steps"]) > float(a["steps"]) + 0.01:
		print("avoid 的代价：平均多走 %.2f 间房" % (float(b["steps"]) - float(a["steps"])))
	var d_c: float = float(c["completed"]) - float(a["completed"])
	if d_c > 0.01:
		print("综合评分策略比走最短路高 %.1f 个百分点 —— 信息确实值钱" % (d_c * 100.0))
	elif d_c < -0.01:
		print("综合评分策略低 %.1f 个百分点 —— 信息还不够，或权重配错" % (-d_c * 100.0))
	else:
		print("综合评分策略与最短路持平 —— 房间差异还没到值得规划的程度")


func _row3(label: String, va: float, vb: float, vc: float) -> void:
	print("%-14s %10.3f %11.3f %11.3f" % [label, va, vb, vc])


func _row(label: String, va: float, vb: float) -> void:
	var d: float = vb - va
	var mark: String = ""
	if absf(d) > 0.005:
		mark = "  ↑" if d > 0.0 else "  ↓"
	print("%-14s %10.3f %11.3f %9.3f%s" % [label, va, vb, d, mark])

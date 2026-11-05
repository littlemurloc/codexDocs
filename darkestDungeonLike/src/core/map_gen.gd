class_name MapGen
extends RefCounted
## 房间图生成：把 dungeons.json 的 25 个地图参数真正用起来。
##
## 在此之前路线是一条 Array —— 遭遇是随机的，但「往哪走」不存在。
## 这里补的就是那个结构：在网格上放房间、连走廊、选出入口与目标房间，
## 再往房间和走廊里投放内容。
##
## 生成顺序（顺序不能换，换了深度就不达标）：
##   1. 按 nudge 倾向在 gridsize 网格上撒 base_room_number 个房间
##   2. 用带抖动的 Kruskal 连成一棵树（保证连通），再按 connectivity 加少量环
##   3. 在全图上做全对最短路，取距离最远的一对作为入口 / 目标房间
##   4. 按区间投放战斗、奇物、饥饿
##
## 第 3 步是「先连再选端点」而不是反过来：min_final_distance 要的是**图上的跳数**，
## 不是网格上的曼哈顿距离。5×5 的网格曼哈顿最多 8，而长图要求 10 跳——
## 只有先建好树再挑最远对，这个数才有意义。

const K_START: String = "start"
const K_GOAL: String = "goal"
const K_BOSS: String = "boss"
const K_BATTLE: String = "battle"
const K_CURIO: String = "curio"
const K_EMPTY: String = "empty"

const DIRS: Array = [Vector2i(1, 0), Vector2i(-1, 0), Vector2i(0, 1), Vector2i(0, -1)]
const MAX_TRY: int = 16


## `quest_type`（M20）：`explore` / `kill_boss`。`dungeons.json` 每个区域
## 两种任务各有一套地图参数（kill_boss 的图更短、房间更少）。
## 默认 explore = M7~M19 的行为，旧基线靠它复现。
static func build(db: DdDb, dungeon: String, size: String, level: int, rng: DdRng,
		quest_type: String = "explore") -> Dictionary:
	var mp: Dictionary = db.map_for(dungeon, size, quest_type)
	if mp.is_empty():
		push_warning("MapGen: 没有 %s/%s 的地图参数" % [dungeon, size])
		return {}

	var grid: Array = mp.get("gridsize", [4, 4])
	var gw: int = clampi(int(grid[0]), 2, 8)
	var gh: int = clampi(int(grid[1]), 2, 8)
	var want: int = maxi(mini(int(mp.get("base_room_number", 9)), gw * gh), 4)
	var min_dist: int = int(mp.get("min_final_distance", 3))
	var nb_bias: float = clampf(float(mp.get("nudge_neighbour_bias", 0.5)), 0.0, 1.0)
	# connectivity 不直接当边密度用：0.85 若解释成「85% 的相邻对都连」，
	# 图会密到最短路只有 2-3 跳，min_final_distance 永远达不到。
	# 这里只把它当成「额外环的数量」，主结构仍是树。
	var extra_rate: float = clampf(float(mp.get("connectivity", 0.85)) - 0.45, 0.0, 0.60)

	var best: Dictionary = {}
	var best_key: float = -1.0
	for attempt in MAX_TRY:
		var cells: Array = _place_rooms(gw, gh, want, nb_bias, rng)
		if cells.size() < 4:
			continue
		var tree: Array = _connect(cells, rng)
		if tree.is_empty():
			continue
		var ends: Dictionary = _farthest_pair(cells.size(), tree)
		if ends.is_empty():
			continue
		# 端点定下来之后才加环，而且只加**不会缩短入口→目标最短路**的环。
		# 顺序反过来（先加环再选最远对）会两头不讨好：环把最远对压短，
		# 长图的 min_final_distance=10 直接达不到，实测只有 40%。
		var pairs: Array = _add_loops(cells, tree, int(ends["start"]), int(ends["goal"]),
			min_dist, extra_rate, rng)
		# 必须重算：加环会把最短路缩短，用树上的距离当结论，
		# 图上标出来的「出口 X 步之外」就会一直偏大。
		var shortest: int = _pair_dist(cells.size(), pairs, int(ends["start"]), int(ends["goal"]))
		# 达标优先，达标里取跳数最大的那张。
		# 一旦达标就 break（第一版）会停在「刚好等于 min_final_distance」的图上，
		# 短图因此只有 3 跳就走到出口——合规，但一点探索感都没有。
		var key: float = float(shortest) + (100.0 if shortest >= min_dist else 0.0)
		if key > best_key:
			best_key = key
			best = {"cells": cells, "pairs": pairs, "start": int(ends["start"]),
				"goal": int(ends["goal"]), "shortest": shortest}

	if best.is_empty():
		push_warning("MapGen: 生成失败 %s/%s" % [dungeon, size])
		return {}

	var cells2: Array = best["cells"]
	var pairs2: Array = best["pairs"]
	var rooms: Dictionary = {}
	var room_ids: Array = []
	for i in cells2.size():
		rooms[i] = {
			"pos": cells2[i],
			"kind": K_EMPTY,
			"step": {},
			"visited": false,
			"spotted": false,   # 被侦察到（只是看见，不等于进去过）
		}
		room_ids.append(i)
	rooms[int(best["start"])]["kind"] = K_START
	rooms[int(best["goal"])]["kind"] = K_GOAL

	var edges: Array = []
	for p in pairs2:
		edges.append({"a": int(p.x), "b": int(p.y), "walked": false, "steps": []})

	var map: Dictionary = {
		"dungeon": dungeon, "size": size, "level": level,
		"grid": [gw, gh],
		"rooms": rooms,
		"room_ids": room_ids,
		"edges": edges,
		"adj": _adjacency(cells2.size(), pairs2),
		"start": int(best["start"]),
		"goal": int(best["goal"]),
		"shortest": int(best["shortest"]),
	}
	_fill_contents(db, map, mp, level, rng, quest_type)
	# 任务目标奇物（M33）：收集/激活任务要求玩家在图里找到指定奇物，
	# 而这类地图的普通奇物只有 1–2 个、还全是随机种类——不管的话
	# 任务几乎必然做不完。所以按需**额外投放**，放在常规内容之后，
	# 不挤占战斗/陷阱/饥饿的配额。
	_place_quest_curios(db, map, quest_type, dungeon, rng)
	return map


## 往图里补足任务目标奇物。返回实际放了几个（bench / 测试用）。
##
## 位置优先级：**空房间 → 空走廊**。先房间是因为「进房间」是玩家愿意付的代价
## （要走路），走廊上的奇物是路过即触发的，放在走廊会让任务变得太便宜。
## 空房间不够才退到走廊——小图上这是常态，不是异常。
##
## 全部用派生的 rng：地图形状和内容分布吃的是主序列，这里多抽一次，
## M7 以来的全部地图基线同时作废（M11/M13/M15 各踩过一次）。
static func _place_quest_curios(db: DdDb, map: Dictionary, quest_type: String,
		dungeon: String, rng: DdRng) -> int:
	if db == null or db.curio_lib == null or not db.curio_lib.is_loaded():
		return 0
	if not QuestGoal.CURIO_TYPES.has(quest_type):
		return 0
	var qg: Dictionary = QuestGoal.parse(db.quests, quest_type, dungeon, db.curio_lib.curios)
	if not bool(qg.get("supported", false)):
		return 0
	var cid: String = str(qg.get("curio", ""))
	if cid.is_empty():
		return 0
	var need: int = maxi(1, int(qg.get("amount", 1)))
	# 收集类一次交互只产出一件，所以「要几件」就等于「要几个奇物」。
	# 激活同一处可以反复算，但**同一张图上的同一个奇物只算一次**
	# （见 Expedition 的计数），所以也按数量放。
	var sub: DdRng = DdRng.new(_derive_seed(rng, need * 101 + 7))

	var rooms: Dictionary = map["rooms"]
	var ids: Array = map["room_ids"]
	var start: int = int(map["start"])
	var goal: int = int(map["goal"])
	var empties: Array = []
	for id in ids:
		var rid: int = int(id)
		if rid == start or rid == goal:
			continue
		var r: Dictionary = rooms[rid]
		if str(r.get("kind", "")) == K_EMPTY and (r.get("step", {}) as Dictionary).is_empty():
			empties.append(rid)
	_shuffle(empties, sub)
	var placed: int = 0
	for rid2 in empties:
		if placed >= need:
			break
		rooms[rid2]["kind"] = K_CURIO
		rooms[rid2]["step"] = {"kind": "curio", "curio": cid, "slot": CurioLib.SLOT_ROOM, "quest": true}
		placed += 1
	if placed >= need:
		return placed

	var edges: Array = map["edges"]
	var free_edges: Array = []
	for i in edges.size():
		if (edges[i].get("steps", []) as Array).is_empty():
			free_edges.append(i)
	_shuffle(free_edges, sub)
	for i2 in free_edges:
		if placed >= need:
			break
		edges[i2]["steps"] = [{"kind": "curio", "curio": cid, "slot": CurioLib.SLOT_HALL, "quest": true}]
		placed += 1
	return placed


# ============================================================
# 1. 撒房间
# ============================================================

## 从随机一格开始，按 nudge_neighbour_bias 决定「贴着已有房间长」还是「随便撒」。
## weald 的 neighbour_bias 是 1（成簇），crypts 是 0.5（更均匀）——
## 这就是两个地牢形状不一样的原因，不是随机噪声。
static func _place_rooms(gw: int, gh: int, n: int, nb_bias: float, rng: DdRng) -> Array:
	var cells: Array = []
	var taken: Dictionary = {}
	var first := Vector2i(rng.next_int_range(0, gw - 1), rng.next_int_range(0, gh - 1))
	cells.append(first)
	taken[first] = true

	var guard: int = 0
	while cells.size() < n and guard < 600:
		guard += 1
		var pick: Variant = null
		if rng.next_float() < nb_bias:
			var cand: Array = []
			for c in cells:
				for d in DIRS:
					var q: Vector2i = (c as Vector2i) + (d as Vector2i)
					if q.x < 0 or q.y < 0 or q.x >= gw or q.y >= gh:
						continue
					if taken.has(q):
						continue
					cand.append(q)
			if not cand.is_empty():
				pick = cand[rng.next_int_range(0, cand.size() - 1)]
		if pick == null:
			var empties: Array = []
			for x in gw:
				for y in gh:
					var q2 := Vector2i(x, y)
					if not taken.has(q2):
						empties.append(q2)
			if empties.is_empty():
				break
			pick = empties[rng.next_int_range(0, empties.size() - 1)]
		cells.append(pick)
		taken[pick] = true
	return cells


# ============================================================
# 2. 连走廊
# ============================================================

## Kruskal：只在**相邻**房间之间连走廊，再补齐连通、加少量环。
##
## 第一版没有限制距离，结果生成了 0 号房到 5 号房这种跨半张图的长边——
## 图上它们是邻居、空间上隔着三个房间，玩家看到的就是「地图在骗我」。
## 走廊必须连相邻房间（曼哈顿 <= 2），长边只作为连通性兜底。
static func _connect(cells: Array, rng: DdRng) -> Array:
	var n: int = cells.size()
	var near: Array = []
	for i in n:
		for j in range(i + 1, n):
			var md: int = _manhattan(cells[i], cells[j])
			if md > 2:
				continue
			near.append({"a": i, "b": j, "w": float(md) + rng.next_float() * 0.9})
	near.sort_custom(func(x, y): return float(x.w) < float(y.w))

	var parent: Array = []
	for i in n:
		parent.append(i)
	var pairs: Array = []
	var linked: Dictionary = {}
	for e in near:
		var ra: int = _find(parent, int(e.a))
		var rb: int = _find(parent, int(e.b))
		if ra == rb:
			continue
		parent[ra] = rb
		pairs.append(Vector2i(int(e.a), int(e.b)))
		linked[_key(int(e.a), int(e.b))] = true

	# 兜底：房间撒得太散时，近邻不够连成一整块，用最近的跨距对补上
	var guard: int = 0
	while guard < n:
		guard += 1
		var roots: Dictionary = {}
		for i in n:
			roots[_find(parent, i)] = true
		if roots.size() <= 1:
			break
		var best: Variant = null
		var bd: float = 1e9
		for i in n:
			for j in range(i + 1, n):
				if _find(parent, i) == _find(parent, j):
					continue
				var d: float = float(_manhattan(cells[i], cells[j])) + rng.next_float() * 0.5
				if d < bd:
					bd = d
					best = {"a": i, "b": j}
		if best == null:
			break
		parent[_find(parent, int(best.a))] = _find(parent, int(best.b))
		pairs.append(Vector2i(int(best.a), int(best.b)))
		linked[_key(int(best.a), int(best.b))] = true

	return pairs


## 加环：允许缩短最短路，但只能缩到 min_final_distance 为止。
##
## 两个极端都试过，都不行：
##   完全不缩短（第一版）  最短路唯一，玩家没有第二个选择。
##                        中图 14 房 15 边 = 树 + 1 环，「选路」是假的。
##   无脑加满              中图跳数 7.5 → 6.9、长图 10.8 → 8.4，
##                        长图深度达标率掉到 5%。
##
## 所以真正的约束不是「不许缩短」，而是「别缩过头」。
## 下限就是数据给的 min_final_distance —— 它本来就是「入口到目标至少多远」，
## 而不是「必须正好等于最远对」。
static func _add_loops(cells: Array, tree: Array, start: int, goal: int,
		min_dist: int, extra_rate: float, rng: DdRng) -> Array:
	var n: int = cells.size()
	var out: Array = tree.duplicate()
	var base: int = _pair_dist(n, out, start, goal)
	if base <= 0:
		return out
	# 下限取「数据下限」与「树深度 - 2」的较大者。
	# 只用数据下限的话，短图会被缩到刚好 3 跳——9 间房 3 步就走完，
	# 合规但毫无探索感。留 2 步的余量，深度和环数才都合理。
	var floor_dist: int = mini(base, maxi(maxi(min_dist, 1), base - 2))

	var near: Array = []
	for i in n:
		for j in range(i + 1, n):
			if _manhattan(cells[i], cells[j]) > 2:
				continue
			if _has_pair(out, i, j):
				continue
			near.append(Vector2i(i, j))
	_shuffle(near, rng)

	var want: int = int(round(float(n) * extra_rate))
	var added: int = 0
	for p in near:
		if added >= want:
			break
		var trial: Array = out.duplicate()
		trial.append(p)
		if _pair_dist(n, trial, start, goal) < floor_dist:
			continue     # 缩过头了：这张图的深度就此失守
		out.append(p)
		added += 1
	return out


static func _has_pair(pairs: Array, a: int, b: int) -> bool:
	for p in pairs:
		if (int(p.x) == a and int(p.y) == b) or (int(p.x) == b and int(p.y) == a):
			return true
	return false


static func _pair_dist(n: int, pairs: Array, a: int, b: int) -> int:
	var adj: Dictionary = adjacency_rooms(n, pairs)
	var d: Array = bfs(n, adj, a)
	if b < 0 or b >= d.size():
		return -1
	return int(d[b])


static func _find(parent: Array, x: int) -> int:
	var cur: int = x
	var guard: int = 0
	while int(parent[cur]) != cur and guard < 64:
		parent[cur] = parent[int(parent[cur])]
		cur = int(parent[cur])
		guard += 1
	return cur


static func _manhattan(a: Variant, b: Variant) -> int:
	var pa: Vector2i = a
	var pb: Vector2i = b
	return absi(pa.x - pb.x) + absi(pa.y - pb.y)


static func _key(a: int, b: int) -> String:
	return "%d-%d" % [mini(a, b), maxi(a, b)]


static func _adjacency(n: int, pairs: Array) -> Dictionary:
	var adj: Dictionary = {}
	for i in n:
		adj[i] = []
	for idx in pairs.size():
		var p: Vector2i = pairs[idx]
		(adj[int(p.x)] as Array).append(idx)
		(adj[int(p.y)] as Array).append(idx)
	return adj


# ============================================================
# 3. 选入口 / 目标房间
# ============================================================

## 全对 BFS，取距离最远的一对。距离就是 min_final_distance 的度量口径。
static func _farthest_pair(n: int, pairs: Array) -> Dictionary:
	var room_adj: Dictionary = adjacency_rooms(n, pairs)
	var best: Dictionary = {}
	var best_d: int = -1
	for s in n:
		var dist: Array = bfs(n, room_adj, s)
		for g in n:
			if g == s:
				continue
			var d: int = int(dist[g])
			if d > best_d:
				best_d = d
				best = {"start": s, "goal": g, "dist": d}
	if best_d <= 0:
		return {}
	return best


## 从 src 出发的单源最短路（跳数，不可达记 -1）。
## 注意 adj 必须是「房间 → 邻居房间」，不是「房间 → 边索引」。
static func bfs(n: int, adj: Dictionary, src: int) -> Array:
	var dist: Array = []
	for i in n:
		dist.append(-1)
	dist[src] = 0
	var queue: Array = [src]
	var head: int = 0
	while head < queue.size():
		var cur: int = int(queue[head])
		head += 1
		for nxt in (adj.get(cur, []) as Array):
			var v: int = int(nxt)
			if v < 0 or v >= n:
				continue
			if int(dist[v]) >= 0:
				continue
			dist[v] = int(dist[cur]) + 1
			queue.append(v)
	return dist


## 把「房间 -> 边索引」的邻接表转成「房间 -> 邻居房间」，供 BFS 用。
static func adjacency_rooms(n: int, pairs: Array) -> Dictionary:
	var out: Dictionary = {}
	for i in n:
		out[i] = []
	for p in pairs:
		(out[int(p.x)] as Array).append(int(p.y))
		(out[int(p.y)] as Array).append(int(p.x))
	return out


# ============================================================
# 4. 投放内容
# ============================================================

static func _fill_contents(db: DdDb, map: Dictionary, mp: Dictionary, level: int, rng: DdRng,
		quest_type: String = "explore") -> void:
	var enc: Dictionary = RouteGen.encounter_block(db, map["dungeon"], level)
	var gear: int = int(RouteGen.GEAR_BY_LEVEL.get(clampi(level, 1, 6), 0))
	var rooms: Dictionary = map["rooms"]
	var room_ids: Array = map["room_ids"]
	var start: int = int(map["start"])
	var goal: int = int(map["goal"])

	var pool: Array = []
	for id in room_ids:
		if int(id) == start or int(id) == goal:
			continue
		pool.append(int(id))
	_shuffle(pool, rng)

	var n_battle: int = RouteGen.roll_range(mp.get("total_room_battles", [1, 2]), rng)
	var n_curio: int = RouteGen.roll_range(mp.get("room_curio", [0, 0]), rng) \
		+ RouteGen.roll_range(mp.get("room_guarded_curio", [0, 1]), rng)

	var idx: int = 0
	for i in n_battle:
		if idx >= pool.size():
			break
		var step: Dictionary = _battle_step(db, enc, gear, "room", rng)
		if step.is_empty():
			break
		rooms[pool[idx]]["kind"] = K_BATTLE
		rooms[pool[idx]]["step"] = step
		idx += 1
	for i in n_curio:
		if idx >= pool.size():
			break
		rooms[pool[idx]]["kind"] = K_CURIO
		# 房间里的「奇物房」在 DD1 是**宝物箱**（unlocked/locked strongbox、heirloom_chest），
		# 不是走廊上那些雕像祭坛。所以刷 room_treasures 那一栏，不是 room_curios。
		rooms[pool[idx]]["step"] = {"kind": "curio", "slot": CurioLib.SLOT_TREASURE}
		# 具体是哪个奇物，在地图生成时就按该地牢的权重定下来。
		# 这里**必须用派生 rng**，不能碰主 rng：地图形状、房间内容分布
		# 全是同一条序列出来的，多抽一次会让 M7 的全部基线整体漂移。
		# 派生种子由「已抽次数 + 房间号」算出，不消耗主序列。
		if db != null and db.curio_lib != null and db.curio_lib.is_loaded():
			var sub: DdRng = DdRng.new(_derive_seed(rng, int(pool[idx]) * 7 + i))
			var cid: String = db.curio_lib.pick(str(map["dungeon"]), CurioLib.SLOT_TREASURE, sub)
			if not cid.is_empty():
				rooms[pool[idx]]["step"]["curio"] = cid
		idx += 1

	var edges: Array = map["edges"]
	var eidx: Array = []
	for i in edges.size():
		eidx.append(i)
	_shuffle(eidx, rng)

	# 走廊内容互斥：一条走廊只放一件事。
	# 理由是「看见内容才谈得上绕不绕」——一条走廊同时有陷阱和战斗，
	# 玩家拿到的信息就没法变成选择。
	#
	# 配额必须按比例分，不能按顺序先到先得。第一版就是顺序分配，
	# 结果陷阱一上，饥饿从 3.5 掉到 0.2 —— 排在后面的类别直接饿死，
	# 而饥饿是 M3 资源压力的主循环，不能没有。
	var cap: int = maxi(4, int(round(float(edges.size()) * 0.55)))
	var wants: Array = [
		RouteGen.roll_range(mp.get("hallway_battle", [1, 2]), rng),
		RouteGen.roll_range(mp.get("hallway_hunger", [1, 2]), rng),
		RouteGen.roll_range(mp.get("hallway_trap", [1, 2]), rng),
		RouteGen.roll_range(mp.get("hallway_obstacle", [0, 1]), rng),
	]
	var quota: Array = _allocate(wants, cap)
	var n_hall: int = int(quota[0])
	var n_hunger: int = int(quota[1])
	var n_trap: int = int(quota[2])
	var n_obst: int = int(quota[3])

	var ei: int = 0
	for i in n_hall:
		if ei >= eidx.size():
			n_hall = i
			break
		var st: Dictionary = _battle_step(db, enc, gear, "hall", rng)
		if st.is_empty():
			n_hall = i
			break
		edges[eidx[ei]]["steps"] = [st]
		ei += 1
	for i in n_trap:
		if ei >= eidx.size():
			n_trap = i
			break
		edges[eidx[ei]]["steps"] = [{"kind": "trap", "level": level}]
		ei += 1
	for i in n_obst:
		if ei >= eidx.size():
			n_obst = i
			break
		edges[eidx[ei]]["steps"] = [{"kind": "obstacle"}]
		ei += 1
	for i in n_hunger:
		if ei >= eidx.size():
			n_hunger = i
			break
		edges[eidx[ei]]["steps"] = [{"kind": "hunger"}]
		ei += 1

	# —— 走廊奇物 ——
	#
	# hallway_curio 是**百分比**不是数量：short=9 / medium=14 / long=19，
	# 与图尺寸线性相关，而 hallway_battle 是 2–4 个。9 条走廊要是真放 9 个奇物，
	# 密度会高到每走一步都撞上。
	#
	# 只填空走廊，不动已经分好的四类内容——那四类是按 cap 比例分配的，
	# 往里面塞会挤掉饥饿，而饥饿是资源压力的主循环（M3 的老教训）。
	var n_hall_curio: int = 0
	var curio_pct: int = int(mp.get("hallway_curio", [0, 0])[0])
	# 密度下限：原始 9/14/19 实测只出 0.57/1.30/2.53 个奇物，短图等于看不见。
	# 取下限而不是硬覆盖，这样数据将来自己调高会生效（见 expedition.json 的 curio_rate）。
	if db != null and db.curio_hall_pct_min > curio_pct:
		curio_pct = db.curio_hall_pct_min
	if curio_pct > 0 and db != null and db.curio_lib != null and db.curio_lib.is_loaded():
		for k in eidx.size():
			var e2: Dictionary = edges[eidx[k]]
			if not ((e2.get("steps", []) as Array) as Array).is_empty():
				continue
			var sub2: DdRng = DdRng.new(_derive_seed(rng, int(eidx[k]) * 13 + 5))
			if not sub2.chance(float(curio_pct) / 100.0):
				continue
			var cid2: String = db.curio_lib.pick(str(map["dungeon"]), CurioLib.SLOT_HALL, sub2)
			if cid2.is_empty():
				continue
			e2["steps"] = [{"kind": "curio", "curio": cid2, "slot": CurioLib.SLOT_HALL}]
			n_hall_curio += 1

	# —— 首领任务（M20）——
	# `dungeons.json` 给每个区域都配了 kill_boss 的地图参数和 boss 遭遇表
	# （weald 3 组、cove 2 组、crypts 2 组、warrens 2 组、至暗 2 组），
	# 但 M7~M19 只按 explore 取图，那 30 条 boss 数据一次都没用上。
	#
	# 做法是给**终点房间**塞一个战斗步：`Expedition.travel` 进门时会把
	# `rooms[id].step` 压进待结算队列，所以这里不需要改远征层的流程。
	# 独立派生的 rng：地图形状和内容分布都吃主序列，多抽一次会让 M7 的基线整体漂移。
	if quest_type == "kill_boss":
		var bsub: DdRng = DdRng.new(_derive_seed(rng, goal * 17 + 3))
		var bstep: Dictionary = _boss_step(db, enc, gear, bsub)
		if not bstep.is_empty():
			rooms[goal]["kind"] = K_BOSS
			rooms[goal]["step"] = bstep

	map["content"] = {
		"battles": n_battle, "curios": n_curio, "hall_battles": n_hall,
		"hall_curios": n_hall_curio,
		"traps": n_trap, "obstacles": n_obst,
		"hungers": n_hunger, "rooms": room_ids.size(), "edges": edges.size(),
		"cap": cap,
		"boss": quest_type == "kill_boss" and not (rooms[goal].get("step", {}) as Dictionary).is_empty(),
	}


## 首领遭遇。`enc["boss"]` 每级有 2–3 组，和 hall/room 一样按 chance 权重抽。
static func _boss_step(db: DdDb, enc: Dictionary, gear: int, rng: DdRng) -> Dictionary:
	var rows: Array = enc.get("boss", [])
	if rows.is_empty():
		return {}
	var mons: Array = RouteGen.pick_encounter(db, rows, rng)
	if mons.is_empty():
		return {}
	# `boss: true` 是给远征层和界面认的标记：用来在结算屏区分
	# 「打完一场普通仗」和「把首领杀了」，也方便自检单独统计。
	return {"kind": "battle", "monsters": mons, "gear": gear, "skill": gear,
		"source": "boss", "boss": true}


static func _battle_step(db: DdDb, enc: Dictionary, gear: int, source: String, rng: DdRng) -> Dictionary:
	var rows: Array = enc.get("room" if source == "room" else "hall", [])
	var mons: Array = RouteGen.pick_encounter(db, rows, rng)
	if mons.is_empty():
		return {}
	return {"kind": "battle", "monsters": mons, "gear": gear, "skill": gear, "source": source}


## 把 cap 个走廊槽按比例分给各类，want>0 的类至少保留 1 个。
##
## 纯按比例向下取整会让小数位小的类别拿到 0；而「这趟图里一个陷阱都没有」
## 和「陷阱太少」是两回事，前者会让整层机制在某些图上完全缺席。
static func _allocate(wants: Array, cap: int) -> Array:
	var total: int = 0
	for w in wants:
		total += int(w)
	if total <= cap:
		return wants.duplicate()

	var out: Array = []
	for w in wants:
		out.append(1 if int(w) > 0 else 0)
	var used: int = 0
	for v in out:
		used += int(v)
	if used >= cap:
		# 连保底都放不下：按 want 从大到小给，剩下的清零
		var order: Array = []
		for i in wants.size():
			order.append(i)
		order.sort_custom(func(a, b): return int(wants[a]) > int(wants[b]))
		out = []
		for i in wants.size():
			out.append(0)
		for j in mini(cap, wants.size()):
			out[int(order[j])] = 1
		return out

	var rest: int = cap - used
	var surplus: int = total - used
	for i in wants.size():
		if int(wants[i]) > 1 and surplus > 0:
			out[i] = int(out[i]) + int(floor(float(int(wants[i]) - 1) * float(rest) / float(surplus)))

	# 余数补齐：向下取整会剩几个槽，补到 want 最大的那一类
	var guard: int = 0
	while guard < 64:
		guard += 1
		var now: int = 0
		for v in out:
			now += int(v)
		if now >= cap:
			break
		var best: int = 0
		for i in wants.size():
			if int(out[i]) < int(wants[i]) and int(wants[i]) > int(wants[best]):
				best = i
		out[best] = int(out[best]) + 1
	return out


static func _shuffle(arr: Array, rng: DdRng) -> void:
	for i in range(arr.size() - 1, 0, -1):
		var j: int = rng.next_int_range(0, i)
		var tmp: Variant = arr[i]
		arr[i] = arr[j]
		arr[j] = tmp


## 从主 rng 派生一个子种子，**不消耗**主序列。
##
## 用途：地图生成完之后还要决定"这间房里放哪个奇物"，但地图形状、房间内容
## 分布全是从主 rng 一条序列里抽出来的。哪怕多抽一个数，M7 的全部基线
## （房间数、走廊内容配额、形状）都会整体漂移，历史对照全部作废。
## 所以这里只读 draw_count 当盐，另开一条独立的流。
static func _derive_seed(rng: DdRng, salt: int) -> int:
	var s: int = (rng.draw_count * 2654435761 + salt * 40503 + 12345) & 0x7FFFFFFF
	if s == 0:
		s = 1
	return s


# ============================================================
# 查询（给 Expedition 与测试用）
# ============================================================

## 从某房间出发能去的房间列表（含途经的边索引）
static func neighbors(map: Dictionary, room: int) -> Array:
	var out: Array = []
	var pairs: Array = []
	for e in (map["edges"] as Array):
		pairs.append(Vector2i(int(e.a), int(e.b)))
	var adj: Dictionary = adjacency_rooms((map["room_ids"] as Array).size(), pairs)
	for nb in (adj.get(room, []) as Array):
		var ei: int = _edge_index(map, room, int(nb))
		if ei >= 0:
			out.append({"room": int(nb), "edge": ei})
	return out


static func _edge_index(map: Dictionary, a: int, b: int) -> int:
	var edges: Array = map["edges"]
	for i in edges.size():
		var e: Dictionary = edges[i]
		if (int(e.a) == a and int(e.b) == b) or (int(e.a) == b and int(e.b) == a):
			return i
	return -1


## 入口到目标的最短路（跳数）。bench 用它当口径。
static func shortest_path(map: Dictionary) -> int:
	var n: int = (map["room_ids"] as Array).size()
	var pairs: Array = []
	for e in (map["edges"] as Array):
		pairs.append(Vector2i(int(e.a), int(e.b)))
	var dist: Array = bfs(n, adjacency_rooms(n, pairs), int(map["start"]))
	return int(dist[int(map["goal"])])


## 全部房间连通吗？生成器最基本的正确性。
## 不能叫 is_connected——那是 Object 的内置方法，重名会直接编译失败。
static func all_reachable(map: Dictionary) -> bool:
	var n: int = (map["room_ids"] as Array).size()
	var pairs: Array = []
	for e in (map["edges"] as Array):
		pairs.append(Vector2i(int(e.a), int(e.b)))
	var dist: Array = bfs(n, adjacency_rooms(n, pairs), 0)
	for d in dist:
		if int(d) < 0:
			return false
	return true

extends SceneTree
## 把生成出来的房间图打成 ASCII，肉眼确认「像不像一张地图」。
## 数字能证明连通和深度，但「能不能看懂」只能看。
##
## 用法：godot --headless --path . --script res://tests/dump_map.gd -- [--size=medium] [--seed=1] [--runs=1]

var _size: String = "medium"
var _seed: int = 1
var _runs: int = 1
var _stats: bool = false


func _initialize() -> void:
	for a in OS.get_cmdline_user_args():
		if a.begins_with("--size="):
			_size = a.substr(7)
		elif a.begins_with("--seed="):
			_seed = int(a.substr(7))
		elif a.begins_with("--runs="):
			_runs = int(a.substr(7))
		elif a == "--stats":
			_stats = true

	var db: DdDb = DdDb.shared()
	if db.heroes.is_empty() or db.encounters.is_empty():
		print("数据未加载")
		quit(1)
		return

	if _stats:
		_report(db)
		quit(0)
		return

	for i in _runs:
		var m: Dictionary = MapGen.build(db, "weald", _size, 3, DdRng.new(_seed + i))
		if m.is_empty():
			print("生成失败")
			continue
		print(_render(m))
	quit(0)


## 批量统计：连通率、深度达标率、走廊是否都是近邻。
func _report(db: DdDb) -> void:
	print("规格    生成  连通  深度达标(需 X)  近邻走廊  房间  走廊  跳数  战斗 陷阱 障碍 饥饿 空")
	for size in ["short", "medium", "long"]:
		var mp: Dictionary = db.map_for("weald", size)
		var need: int = int(mp.get("min_final_distance", 3))
		var ok: int = 0
		var conn: int = 0
		var deep: int = 0
		var near_ok: int = 0
		var rooms_sum: int = 0
		var edges_sum: int = 0
		var hop_sum: int = 0
		var tallies: Dictionary = {"battle": 0, "trap": 0, "obstacle": 0, "hunger": 0, "none": 0}
		for i in _runs:
			var m: Dictionary = MapGen.build(db, "weald", size, 3, DdRng.new(_seed + i))
			if m.is_empty():
				continue
			ok += 1
			if MapGen.all_reachable(m):
				conn += 1
			var sp: int = MapGen.shortest_path(m)
			hop_sum += sp
			if sp >= need:
				deep += 1
			rooms_sum += (m["room_ids"] as Array).size()
			edges_sum += (m["edges"] as Array).size()
			for e in (m["edges"] as Array):
				var sts: Array = (e as Dictionary).get("steps", [])
				var k: String = "none" if sts.is_empty() else str((sts[0] as Dictionary).get("kind", "?"))
				tallies[k] = int(tallies.get(k, 0)) + 1
			var all_near: bool = true
			for e in (m["edges"] as Array):
				var a: Vector2i = (m["rooms"][int(e.a)] as Dictionary)["pos"]
				var b: Vector2i = (m["rooms"][int(e.b)] as Dictionary)["pos"]
				if absi(a.x - b.x) + absi(a.y - b.y) > 2:
					all_near = false
			if all_near:
				near_ok += 1
		var n: float = float(maxi(ok, 1))
		print("%-6s %5d %5.0f%% %8.0f%% (%d) %8.0f%% %5.1f %5.1f %4.1f %5.1f %4.1f %4.1f %4.1f %4.1f" % [
			size, ok, float(conn) / n * 100.0, float(deep) / n * 100.0, need,
			float(near_ok) / n * 100.0, float(rooms_sum) / n, float(edges_sum) / n,
			float(hop_sum) / n,
			float(tallies["battle"]) / n, float(tallies["trap"]) / n,
			float(tallies["obstacle"]) / n, float(tallies["hunger"]) / n,
			float(tallies["none"]) / n])


func _render(m: Dictionary) -> String:
	var gw: int = int((m["grid"] as Array)[0])
	var gh: int = int((m["grid"] as Array)[1])
	var rooms: Dictionary = m["rooms"]

	var cell: Dictionary = {}
	for id in rooms.keys():
		cell[rooms[id]["pos"]] = int(id)

	var lines: Array = []
	lines.append("seed 房间 %d · 走廊 %d · 入口→目标 %d 跳 · 内容 %s" % [
		(m["room_ids"] as Array).size(), (m["edges"] as Array).size(),
		MapGen.shortest_path(m), JSON.stringify(m.get("content", {}))])
	lines.append("")

	for y in gh:
		var top: String = "  "
		var mid: String = "  "
		for x in gw:
			var p := Vector2i(x, y)
			var has: bool = cell.has(p)
			var ch: String = "   "
			if has:
				var r: Dictionary = rooms[cell[p]]
				ch = " %s " % _mark(str(r["kind"]))
			top += "+---"
			mid += "|" + ch
		lines.append(top + "+")
		lines.append(mid + "|")

	lines.append("")
	var adj: Dictionary = m["adj"]
	for id in (m["room_ids"] as Array):
		var nb: Array = []
		for ei in (adj[id] as Array):
			var e: Dictionary = (m["edges"] as Array)[int(ei)]
			nb.append(int(e.b) if int(e.a) == int(id) else int(e.a))
		var bits: Array = []
		for n in nb:
			bits.append("%d%s" % [int(n), _mark(str((rooms[int(n)] as Dictionary)["kind"]))])
		lines.append("  %-2d %s → %s" % [int(id),
			_mark(str((rooms[int(id)] as Dictionary)["kind"])), ", ".join(bits)])
	return "\n".join(lines)


func _mark(kind: String) -> String:
	match kind:
		MapGen.K_START:
			return "S"
		MapGen.K_GOAL:
			return "G"
		MapGen.K_BATTLE:
			return "B"
		MapGen.K_CURIO:
			return "C"
		_:
			return "·"

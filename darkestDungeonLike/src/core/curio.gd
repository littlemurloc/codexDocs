class_name CurioLib
extends RefCounted
## 奇物：地图上那些「要不要碰」的东西。
##
## 这一层此前也是假的。resolve_curio() 只有一句：
##   65% 概率拿 12–26 金，否则全队 +9 压力。
## 而 data 里躺着 60 个奇物、139 个有权重的分支、46 条道具交互。
## 一次板条箱和一次邪祭坛在旧实现里是同一个骰子，玩家没有任何理由记住
## 「铁处女要用绷带」「邪祭坛要带圣水」——因为那些区别根本不存在。
##
## ## 抽取规则
##
## 奇物 -> 按权重抽一个 outcome（nothing / loot / effect / quirk / disease /
## scouting / purge / teleport）。outcome 内部可能并列多个 result，分两种：
##   * 所有 result 都没给百分比（原表写 "<- # Draws"）→ **全部执行**。
##     典型是 Loot：goal_strongbox 抽 B 三次 + T 一次，是奖励清单不是选择题。
##   * 给了百分比 → **互斥抽一个**。典型是 Effect：Blight 1 与 Bleed 1 各 50%。
## 这条区分不是猜的：Loot 的百分比列在原表里被 draws 占用，Effect 的才是概率。
##
## ## 道具交互
##
## 给了道具就用 items[道具] 那组 outcome 顶替奇物自身的 outcome。同一个奇物
## 对不同道具给不同结果——锁箱用钥匙是 A 表 3 抽，用铲子是 50% 砸空。
## 这就是「带什么上路」第一次真的有意义。
##
## ## 效果落地边界
##
## 只解析不执行。stress / blight / bleed / heal_* 这类有数值的，交给远征层去扣；
## scripted（Suit of Armor Shield、fish_idol_curse_1…）表里只有名字没有数值，
## 一律标 unsupported 并原样带出，**不猜数值**。

var curios: Dictionary = {}      ## id -> 定义
var props: Dictionary = {}       ## dungeon -> slot -> [{chance, types}]
var stats: Dictionary = {}       ## 生成时的统计，供自检对照
var source_base: String = ""     ## 实际从哪个目录读到（数值包可能没有这份）

## 哪些 slot 属于「奇物房」，哪些属于「走廊内容」。
const SLOT_ROOM: String = "room_curios"
const SLOT_HALL: String = "hall_curios"
const SLOT_TREASURE: String = "room_treasures"

var _loaded: bool = false


func is_loaded() -> bool:
	return _loaded


func load_from(base: String = "res://data") -> bool:
	curios.clear()
	props.clear()
	stats.clear()
	source_base = ""

	# 数值包（balance/*）里没有 curios.json——它由 tools/gen_curios.py 从策划表
	# 生成，属于规则数据而非平衡旋钮。所以换包时回退到 res://data，
	# 而不是让整个奇物系统在换包后静默变成空表。
	# 注意只有 curios.json 回退：dungeons.json 里的 props 是数值包的地盘，
	# 换包就应该换刷新权重，那个不能跟着回退。
	var origin_base: String = base
	var cpath: String = base + "/curios.json"
	if not FileAccess.file_exists(cpath) and base != "res://data":
		cpath = "res://data/curios.json"
		base = "res://data"
	if not FileAccess.file_exists(cpath):
		push_warning("CurioLib: 找不到 %s（先跑 tools/gen_curios.py）" % cpath)
		return false
	var parsed: Variant = JSON.parse_string(FileAccess.get_file_as_string(cpath))
	if parsed == null or typeof(parsed) != TYPE_DICTIONARY:
		push_warning("CurioLib: %s 解析失败" % cpath)
		return false
	var doc: Dictionary = parsed
	curios = doc.get("curios", {})
	stats = doc.get("stats", {})
	source_base = base

	var dpath: String = origin_base + "/dungeons.json"
	if FileAccess.file_exists(dpath):
		var dp: Variant = JSON.parse_string(FileAccess.get_file_as_string(dpath))
		if dp is Dictionary:
			props = (dp as Dictionary).get("props", {})

	_loaded = true
	return true


func has(id: String) -> bool:
	return curios.has(id)


func get_curio(id: String) -> Dictionary:
	return curios.get(id, {})


# ============================================================
# 刷新：这个地牢的这个位置该出什么
# ============================================================

## 某地牢某 slot 是否有配置。
func has_slot(dungeon: String, slot: String) -> bool:
	var d: Dictionary = props.get(dungeon, {})
	return not (d.get(slot, []) as Array).is_empty()


## 按 props 权重抽一个具体奇物 id。抽不到返回 ""。
##
## 两层权重：先按 chance 抽条目，再从条目的 types 里等概率取一个。
## darkestdungeon 的 hall_curios 就是「chance 1，types 五个」——
## 五个等概率，不是一个 chance 5 的条目。
func pick(dungeon: String, slot: String, rng: DdRng) -> String:
	var d: Dictionary = props.get(dungeon, {})
	var rows: Array = d.get(slot, [])
	var total: int = 0
	for e in rows:
		if e is Dictionary:
			total += maxi(0, int(e.get("chance", 0)))
	if total <= 0:
		return ""
	var roll: int = rng.next_int(total)
	var acc: int = 0
	var picked: Dictionary = {}
	for e in rows:
		if not (e is Dictionary):
			continue
		var c: int = maxi(0, int(e.get("chance", 0)))
		if c <= 0:
			continue
		acc += c
		if roll < acc:
			picked = e
			break
	if picked.is_empty():
		return ""
	var types: Array = picked.get("types", [])
	if types.is_empty():
		return ""
	return str(types[rng.next_int(types.size())])


## 该地牢所有能被刷出来的奇物 id（去重、排序）。用于自检覆盖率。
func known_ids_for(dungeon: String) -> Array:
	var out: Array = []
	var d: Dictionary = props.get(dungeon, {})
	for slot in d.keys():
		for e in (d[slot] as Array):
			if not (e is Dictionary):
				continue
			for t in (e.get("types", []) as Array):
				var s: String = str(t)
				if not s.is_empty() and not out.has(s):
					out.append(s)
	out.sort()
	return out


# ============================================================
# 交互：抽一个结果
# ============================================================

## 这个奇物能用哪些道具。返回按 id 排序的数组（顺序稳定，便于测试）。
func items_for(curio_id: String) -> Array:
	var c: Dictionary = curios.get(curio_id, {})
	var out: Array = (c.get("items", {}) as Dictionary).keys()
	out.sort()
	return out


## 该奇物 + 该道具的有效 outcome 列表。
## 没给道具、或该道具对这个奇物没有交互，就退回奇物自身的 outcomes。
func outcomes_for(curio_id: String, item_id: String = "") -> Array:
	var c: Dictionary = curios.get(curio_id, {})
	if c.is_empty():
		return []
	var items: Dictionary = c.get("items", {})
	if not item_id.is_empty() and items.has(item_id):
		var rows: Array = items[item_id]
		# 道具交互的多行按各自行内权重归一；行内没给权重时等概率。
		return rows
	return c.get("outcomes", [])


## 抽一次交互。返回：
##   curio / item / outcome / results / unsupported / roll_total
## results 里每项是原表 result 的结构（kind + 值），由调用方决定怎么落地。
func resolve(curio_id: String, item_id: String, rng: DdRng) -> Dictionary:
	var c: Dictionary = curios.get(curio_id, {})
	var out: Dictionary = {
		"curio": curio_id,
		"item": "",
		"outcome": "",
		"results": [],
		"unsupported": [],
		"ok": false,
	}
	if c.is_empty():
		return out

	var used_item: String = item_id
	if not used_item.is_empty() and not (c.get("items", {}) as Dictionary).has(used_item):
		used_item = ""      # 这个道具对这个奇物没用，别记为「消耗了」
	out["item"] = used_item

	var rows: Array = outcomes_for(curio_id, used_item)
	# 只留权重 > 0 的分支；权重全 0 说明这个奇物在这个状态下什么都不给
	var live: Array = []
	var total: int = 0
	for r in rows:
		if not (r is Dictionary):
			continue
		var w: int = maxi(0, int(r.get("weight", 0)))
		if w <= 0:
			continue
		live.append(r)
		total += w
	if total <= 0:
		out["ok"] = true
		out["outcome"] = "nothing"
		return out

	var roll: int = rng.next_int(total)
	var acc: int = 0
	var picked: Dictionary = live[0]
	for r in live:
		acc += maxi(0, int(r.get("weight", 0)))
		if roll < acc:
			picked = r
			break

	out["ok"] = true
	out["outcome"] = str(picked.get("type", ""))
	out["results"] = _pick_results(picked.get("results", []), rng)
	for r in out["results"]:
		if str(r.get("kind", "")) == "scripted":
			out["unsupported"].append(str(r.get("raw", "")))
	return out


## outcome 内部的 result 抽取（见文件头：并列 or 互斥）。
##
## 互斥时的权重**不能直接用 weight 列**。原表里 weight 是给 Loot 分支当
## 「抽几次」用的，跟概率无关。真正的概率在百分比列：
##   shovel 砸锁箱 → Nothing 50% / A 表（百分比列写 "<- # Draws"，即没给）
## 没给百分比的那个要吃掉剩下的概率，不是按 weight 1:2 分。
## 按 weight 分会变成 33/67，和表里的 50/50 对不上。
func _pick_results(results: Array, rng: DdRng) -> Array:
	if results.is_empty():
		return []
	# 有没有任何一个 result 给了概率？给了就是选择题，没给就是清单。
	var given: float = 0.0
	var blanks: int = 0
	var exclusive: bool = false
	for r in results:
		if not (r is Dictionary):
			continue
		var p: float = float(r.get("pct", -1.0))
		if p > 0.0:
			given += p
			exclusive = true
		else:
			blanks += 1
	if not exclusive:
		return results.duplicate(true)

	# 缺百分比的平分剩余概率。全是 100% 之外的情况都归到这里。
	var rest: float = maxf(0.0, 1.0 - given) / float(maxi(1, blanks))
	# 放大成整数权重，避免浮点比较进入 rng 消耗路径
	var weights: Array = []
	var total: int = 0
	for r in results:
		if not (r is Dictionary):
			weights.append(0)
			continue
		var p: float = float(r.get("pct", -1.0))
		var w: int = int(round((p if p > 0.0 else rest) * 10000.0))
		weights.append(maxi(0, w))
		total += maxi(0, w)
	if total <= 0:
		return [results[0].duplicate(true)]
	var roll: int = rng.next_int(total)
	var acc: int = 0
	for i in results.size():
		acc += int(weights[i])
		if roll < acc:
			return [(results[i] as Dictionary).duplicate(true)]
	return [results[0].duplicate(true)]


# ============================================================
# 自检
# ============================================================

## props 引用了、但 curios.json 里没有的 id。
## 这些通常是陷阱/障碍/牢门（本来就不是奇物），所以单独报，不当错误。
func unknown_ids() -> Array:
	var out: Array = []
	for dungeon in props.keys():
		for id in known_ids_for(str(dungeon)):
			if not curios.has(id) and not out.has(id):
				out.append(id)
	out.sort()
	return out


## curios.json 里有、但任何地牢都刷不出来的 id（任务/教学专用）。
func unreferenced_ids() -> Array:
	var used: Dictionary = {}
	for dungeon in props.keys():
		for id in known_ids_for(str(dungeon)):
			used[id] = true
	var out: Array = []
	for id in curios.keys():
		if not used.has(id):
			out.append(str(id))
	out.sort()
	return out


## 每种 outcome 类型出现多少次（有权重的）。和生成时的统计对照用。
func outcome_type_counts() -> Dictionary:
	var out: Dictionary = {}
	for id in curios.keys():
		for oc in (curios[id].get("outcomes", []) as Array):
			if int((oc as Dictionary).get("weight", 0)) <= 0:
				continue
			var t: String = str((oc as Dictionary).get("type", ""))
			out[t] = int(out.get(t, 0)) + 1
	return out

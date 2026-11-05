class_name LootTables
extends RefCounted
## 战利品抽卡树：data/loot.json 的表，按权重递归抽取。
##
## 这一层此前是**假的**。M5 的战利品是手写常数（每场 9–17 金、30% 掉一件传家宝、
## 通关 45 + 22×场次），和 data/ 里那套抽卡树没有任何关系。真表长这样：
##   A ──50──> C（金币档 25…1000）
##     ──38──> G（宝石，按稀有度 10/10/10/10/5/5/2 分布）
##     ──48──> H（传家宝）
##     ──28──> S     ──8──> T（饰品）
## 换成真表之后，「一场战斗值多少金」不再是一个可以随便改的数字，
## 而是这套权重的自然结果。
##
## ## 三个必须记住的结构事实
##
## **一、overrides 的语义是「覆盖」，不是「另存一份」。**
## extract.py 把 loot/*overrides.loot.json 原样塞进 overrides 字段，没有合并。
## 而那批文件里就有 **A 表和 S 表**——恰恰是整棵树的根。只读 loot_tables
## 的话，所有引用 A 的奇物都会静默抽到空。合并在这里做：先装 loot_tables，
## 再按文件名顺序让 overrides 覆盖同名表。
##
## **二、表 id 不是唯一键。** 同名的 C/G/T 各有 4 份（difficulty 1/3/5/6），
## H 有 13 份（4 地牢 × 3 难度 + 1 份 difficulty 6 通用）。它们不是重复数据，
## 是**难度梯度**：C 表 d1 均值约 330 金，d5 约 600；H 表 d1 给 1–4 件、
## d5 给 2–8 件。用 id 当键会让最后一份吃掉全部，深地牢的经济优势直接消失。
## 所以 tables 的值是**变体数组**，抽的时候按 (地牢, 难度) 选一份。
##
## **三、rng 消耗纪律。** 每次真正抽一次（有可选条目时）恰好消耗一个 next_int。
## 权重为 0 的条目在求和阶段就被剔除，不参与、不消耗。逻辑等价但 rng 序列
## 错位，会让所有历史对照数据失去可比性——这是前几期反复踩过的坑。

const MAX_DEPTH: int = 8

## 表 id -> Array[{difficulty:int, dungeon:String, entries:Array, origin:String}]
var tables: Dictionary = {}
## 物品定义（data/inventory.json）：id -> 原始字典，用来把宝石折成金币。
var item_defs: Dictionary = {}

var source_base: String = ""        ## 实际从哪个目录读到

## 饰品库（M15）。抽卡表的 trinket 叶子只写稀有度，具体是哪一件由它决定。
## 为空时退回旧行为：只记稀有度、不落 id，不崩。
var trinket_lib: TrinketLib = null

var missing_tables: Array = []      ## 被引用但不存在的表 id
var missing_items: Array = []       ## 被引用但不存在的物品 id

var _ctx_dungeon: String = ""
var _ctx_level: int = 1

var _loaded: bool = false


func is_loaded() -> bool:
	return _loaded


## 设当前抽取语境：哪个地牢、几级。同一次远征里只需设一次。
func set_context(dungeon: String, level: int) -> void:
	_ctx_dungeon = dungeon
	_ctx_level = maxi(1, level)


func context() -> Dictionary:
	return {"dungeon": _ctx_dungeon, "level": _ctx_level}


## 读 loot.json 与 inventory.json。base 目录可切换（跟 DdDb 一致）。
func load_from(base: String = "res://data") -> bool:
	tables.clear()
	item_defs.clear()
	missing_tables.clear()
	missing_items.clear()
	source_base = ""

	var path: String = base + "/loot.json"
	# 数值包里可能只有 loot_tables 而缺 overrides（A 表就藏在那里），
	# 这种情况下宁可退回完整的一份，也不要让所有引用 A 的抽取静默变空。
	if FileAccess.file_exists(path) and base != "res://data" and not _has_overrides(path):
		path = "res://data/loot.json"
		base = "res://data"
	if not FileAccess.file_exists(path):
		push_warning("LootTables: 找不到 %s" % path)
		return false
	var parsed: Variant = JSON.parse_string(FileAccess.get_file_as_string(path))
	if parsed == null or typeof(parsed) != TYPE_DICTIONARY:
		push_warning("LootTables: %s 解析失败" % path)
		return false

	var d: Dictionary = parsed
	for t in (d.get("loot_tables", []) as Array):
		if t is Dictionary and t.has("id"):
			_add_variant(t, "base")

	# 覆盖：后装的同名表**整体替换**同名同难度的那一份，而不是逐条合并。
	# 原文件里 A 表只有一份（在 common_overrides），不存在「部分覆盖」的写法。
	var ov: Dictionary = d.get("overrides", {})
	var names: Array = ov.keys()
	names.sort()
	for name in names:
		var blob: Variant = ov[name]
		if not (blob is Dictionary):
			continue
		for t in ((blob as Dictionary).get("loot_tables", []) as Array):
			if t is Dictionary and t.has("id"):
				_add_variant(t, str(name))

	_load_items(base)
	_loaded = true
	source_base = base
	return true


## 加入一份表变体。overrides 来的同名同难度表替换原有那份。
func _add_variant(t: Dictionary, origin: String) -> void:
	var id: String = str(t["id"])
	var diff: int = int(t.get("difficulty", 0))
	var dung: String = str(t.get("dungeon", ""))
	var v: Dictionary = {
		"difficulty": diff,
		"dungeon": dung,
		"entries": (t.get("entries", []) as Array),
		"origin": origin,
	}
	if not tables.has(id):
		tables[id] = [] as Array
	var arr: Array = tables[id]
	for i in arr.size():
		var old: Dictionary = arr[i]
		if int(old["difficulty"]) == diff and str(old["dungeon"]) == dung:
			# 覆盖语义：同名同难度同样的地牢，后到的整份替换
			if old["origin"] == "base" and origin != "base":
				arr[i] = v
			return
	arr.append(v)


## 这个 loot.json 里有没有 overrides（哪怕只有一份）。A/S 表只在 overrides 里。
static func _has_overrides(path: String) -> bool:
	var parsed: Variant = JSON.parse_string(FileAccess.get_file_as_string(path))
	if not (parsed is Dictionary):
		return false
	return not ((parsed as Dictionary).get("overrides", {}) as Dictionary).is_empty()


func _load_items(base: String) -> void:
	var path: String = base + "/inventory.json"
	if not FileAccess.file_exists(path):
		return
	var parsed: Variant = JSON.parse_string(FileAccess.get_file_as_string(path))
	if parsed == null or not (parsed is Array):
		return
	for row in (parsed as Array):
		if row is Dictionary and row.has("id"):
			var rid: String = str(row["id"])
			if not rid.is_empty():
				item_defs[rid] = row


func has_table(id: String) -> bool:
	return tables.has(id) and not (tables[id] as Array).is_empty()


func variant_count(id: String) -> int:
	return (tables.get(id, []) as Array).size()


## 按当前语境选一份变体。
##
## 优先级：本地牢 + 难度不超过当前 → 通用表 + 难度不超过当前 → 任意一份。
## 同组里取难度最大的那份（深地牢给更多）。
## difficulty 0 的变体（overrides 里的 A/S/BLUEPRINT）任何难度都适用。
func variant_for(id: String) -> Dictionary:
	var arr: Array = tables.get(id, [])
	if arr.is_empty():
		return {}
	var cap: int = _ctx_level

	var best_local: Dictionary = {}
	var best_generic: Dictionary = {}
	var lowest: Dictionary = {}
	for v in arr:
		if not (v is Dictionary):
			continue
		var vd: int = int(v["difficulty"])
		if lowest.is_empty() or vd < int(lowest["difficulty"]):
			lowest = v
		if vd > cap:
			continue
		if str(v["dungeon"]) == _ctx_dungeon and not _ctx_dungeon.is_empty():
			if best_local.is_empty() or vd > int(best_local["difficulty"]):
				best_local = v
		elif str(v["dungeon"]).is_empty():
			if best_generic.is_empty() or vd > int(best_generic["difficulty"]):
				best_generic = v
	if not best_local.is_empty():
		return best_local
	if not best_generic.is_empty():
		return best_generic
	# 难度上限之内没有通用表：宁可放宽难度取通用表，也不要拿到**别的**地牢
	# 的专属表。地牢专属表里给的是该地牢的传家宝配比，张冠李戴比给少了更糟。
	var best_fallback: Dictionary = {}
	for v in arr:
		if not (v is Dictionary) or not str(v["dungeon"]).is_empty():
			continue
		if best_fallback.is_empty() or int(v["difficulty"]) < int(best_fallback["difficulty"]):
			best_fallback = v
	if not best_fallback.is_empty():
		return best_fallback
	return lowest


func entries_for(id: String) -> Array:
	var v: Dictionary = variant_for(id)
	return (v.get("entries", []) as Array)


## 一张表里权重 > 0 的条目总数。全为 0 时这张表等价于空抽。
func weight_sum(id: String) -> int:
	var n: int = 0
	for e in entries_for(id):
		if e is Dictionary:
			n += maxi(0, int(e.get("chances", 0)))
	return n


## 空结果：所有抽取都从这份结构上长出来，字段固定，调用方不用 has() 试探。
static func empty_result() -> Dictionary:
	return {
		"gold": 0,
		"heirlooms": {},
		"gems": {},
		"supplies": {},
		"provisions": 0,
		"trinkets": [],
		"trinket_ids": [],
		"journal_pages": 0,
		"nothing": 0,
		"draws": 0,
	}


## 抽一张表一次，把结果累加进 out。
## 返回 false 表示表不存在（调用方据此记一次 miss）。
func draw_into(table_id: String, rng: DdRng, out: Dictionary, depth: int = 0) -> bool:
	if depth > MAX_DEPTH:
		return false
	if not has_table(table_id):
		if not missing_tables.has(table_id):
			missing_tables.append(table_id)
		return false
	var entries: Array = entries_for(table_id)
	var total: int = 0
	for e in entries:
		if e is Dictionary:
			total += maxi(0, int(e.get("chances", 0)))
	if total <= 0:
		out["nothing"] = int(out["nothing"]) + 1
		out["draws"] = int(out["draws"]) + 1
		return true

	# 恰好一次 next_int：条目数变化才会改变序列，权重变化不会。
	var roll: int = rng.next_int(total)
	out["draws"] = int(out["draws"]) + 1
	var acc: int = 0
	var picked: Dictionary = {}
	for e in entries:
		if not (e is Dictionary):
			continue
		var c: int = maxi(0, int(e.get("chances", 0)))
		if c <= 0:
			continue
		acc += c
		if roll < acc:
			picked = e
			break
	if picked.is_empty():
		out["nothing"] = int(out["nothing"]) + 1
		return true

	_apply_entry(picked, rng, out, depth)
	return true


func _apply_entry(e: Dictionary, rng: DdRng, out: Dictionary, depth: int) -> void:
	var t: String = str(e.get("type", ""))
	var data: Dictionary = e.get("data", {})
	match t:
		"nothing":
			out["nothing"] = int(out["nothing"]) + 1
		"table":
			draw_into(str(data.get("table", "")), rng, out, depth + 1)
		"item":
			_apply_item(data, out)
		"trinket":
			_apply_trinket(data, rng, out)
		"journal_page":
			out["journal_pages"] = int(out["journal_pages"]) + 1
		_:
			out["nothing"] = int(out["nothing"]) + 1


## 饰品叶子：表里只写稀有度（`{"rarity":"very_common"}`），这里换成具体的一件。
##
## 为什么用派生 rng 而不是直接用 `rng`：`draw_n` 的抽取次数决定后面所有
## 金币/传家宝/宝石的序列。多抽一次，M13 量到的全部掉落基线就整体漂移，
## 历史对照全部作废——而这次改动跟「这趟掉多少金」毫无关系。
## 所以只读 `draw_count` 当盐，另开一条独立的流。
##
## 池空（例如 `kickstarter` 从不参与掉落）时只记稀有度、不落 id，
## 账面上仍然看得见「这里本该掉一件」，而不是静默消失。
func _apply_trinket(data: Dictionary, rng: DdRng, out: Dictionary) -> void:
	out["trinkets"].append(data.duplicate(true))
	var rarity: String = str(data.get("rarity", ""))
	if rarity.is_empty() or trinket_lib == null or not trinket_lib.is_loaded():
		return
	var sub: DdRng = DdRng.new(_derive_seed(rng, (out["trinkets"] as Array).size() * 131 + 7))
	var exclude: Array = out["trinket_ids"]
	var tid: String = trinket_lib.pick_for_rarity(rarity, sub, exclude)
	if not tid.is_empty():
		out["trinket_ids"].append(tid)


static func _derive_seed(rng: DdRng, salt: int) -> int:
	var s: int = (rng.draw_count * 2654435761 + salt * 40503 + 12345) & 0x7FFFFFFF
	return s if s != 0 else 1


func _apply_item(data: Dictionary, out: Dictionary) -> void:
	var itype: String = str(data.get("type", ""))
	var iid: String = str(data.get("id", ""))
	var amount: int = int(data.get("amount", 1))
	match itype:
		"gold":
			out["gold"] = int(out["gold"]) + maxi(0, amount)
		"heirloom":
			_add_count(out["heirlooms"], iid, amount)
		"gem":
			_add_count(out["gems"], iid, amount)
		"supply":
			_add_count(out["supplies"], iid, amount)
		"provision":
			out["provisions"] = int(out["provisions"]) + maxi(0, amount)
		_:
			if not iid.is_empty() and not missing_items.has(iid):
				missing_items.append(iid)


static func _add_count(d: Dictionary, key: String, n: int) -> void:
	if key.is_empty() or n <= 0:
		return
	d[key] = int(d.get(key, 0)) + n


## 抽 n 次同一张表。
func draw_n(table_id: String, n: int, rng: DdRng, out: Dictionary) -> Dictionary:
	for i in maxi(0, n):
		draw_into(table_id, rng, out)
	return out


## 按 loot 分支的 draws 抽：一次奇物 outcome 说「抽 A 表 2 次」就抽 2 次。
## draws 位在原表里是抽取次数，0 表示「至少抽一次」——被写进 outcome 就说明
## 这个分支确实是给东西的，不该因为 0 而什么都不掉。
func draw_for(results: Array, rng: DdRng, out: Dictionary) -> Dictionary:
	for r in results:
		if not (r is Dictionary):
			continue
		if str(r.get("kind", "")) != "loot_table":
			continue
		var tid: String = str(r.get("table", ""))
		var n: int = maxi(0, int(r.get("draws", 1)))
		draw_n(tid, n if n > 0 else 1, rng, out)
	return out


## 把一批结果折算成金币。宝石与补给按 inventory 的 sell_gold_value 折，
## 传家宝不折（它是升级材料，不是钱）。用于对照实验里比「一趟值多少」。
func gold_value(out: Dictionary) -> int:
	var g: int = int(out.get("gold", 0))
	for key in ["gems", "supplies"]:
		var m: Dictionary = out.get(key, {})
		for id in m.keys():
			var def: Dictionary = item_defs.get(str(id), {})
			g += int(def.get("sell_gold_value", 0)) * int(m[id])
	return g


## 把 out 合并进另一份同结构结果（跨多次抽取累计时用）。
static func merge_into(dst: Dictionary, src: Dictionary) -> void:
	dst["gold"] = int(dst.get("gold", 0)) + int(src.get("gold", 0))
	dst["provisions"] = int(dst.get("provisions", 0)) + int(src.get("provisions", 0))
	dst["journal_pages"] = int(dst.get("journal_pages", 0)) + int(src.get("journal_pages", 0))
	dst["nothing"] = int(dst.get("nothing", 0)) + int(src.get("nothing", 0))
	dst["draws"] = int(dst.get("draws", 0)) + int(src.get("draws", 0))
	for key in ["heirlooms", "gems", "supplies"]:
		var s: Dictionary = src.get(key, {})
		var d: Dictionary = dst.get(key, {})
		for k in s.keys():
			d[str(k)] = int(d.get(str(k), 0)) + int(s[k])
		dst[key] = d
	dst["trinkets"] = (dst.get("trinkets", []) as Array) + (src.get("trinkets", []) as Array)
	dst["trinket_ids"] = (dst.get("trinket_ids", []) as Array) + (src.get("trinket_ids", []) as Array)


## 依赖自检：所有被 table 条目引用的子表都存在（任一难度变体都算存在）。
##
## 只看权重 > 0 的引用。原表里存在 "chances": 0 的占位引用（A 表就有一条指向
## 不存在的 J 表），它们永远不会被抽到，报出来只是噪音。真断了的是有权重的那些。
func dangling_tables() -> Array:
	var out: Array = []
	for id in tables.keys():
		for v in (tables[id] as Array):
			for e in ((v as Dictionary).get("entries", []) as Array):
				if not (e is Dictionary) or str(e.get("type", "")) != "table":
					continue
				if int(e.get("chances", 0)) <= 0:
					continue
				var sub: String = str((e.get("data", {}) as Dictionary).get("table", ""))
				if not has_table(sub) and not out.has(sub):
					out.append(sub)
	out.sort()
	return out


## 权重 0 的悬空引用（保留给文档：它们是不影响运行的占位）。
func dormant_dangling_tables() -> Array:
	var live: Array = dangling_tables()
	var out: Array = []
	for id in tables.keys():
		for v in (tables[id] as Array):
			for e in ((v as Dictionary).get("entries", []) as Array):
				if not (e is Dictionary) or str(e.get("type", "")) != "table":
					continue
				if int(e.get("chances", 0)) > 0:
					continue
				var sub: String = str((e.get("data", {}) as Dictionary).get("table", ""))
				if not has_table(sub) and not out.has(sub) and not live.has(sub):
					out.append(sub)
	out.sort()
	return out

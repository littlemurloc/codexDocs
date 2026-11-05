class_name RouteGen
extends RefCounted
## 远征路线生成：从 dungeons.json 的地图参数 + 遭遇表里抽一条真实路线。
##
## 为什么不手写「三个固定遭遇」：那样测出来的危险度只反映这三场，
## 而 DD1 的压迫感来自**路线长度与补给消耗的比例**——短图 4-7 场、
## 长图 14 场，能不能撑到出口本身就是玩法。路线必须和地图参数挂钩，
## 否则资源层调得再细也只是在给固定剧本配资源。
##
## 数据来源：
##   maps[].total_room_battles   房间里的大型遭遇数
##   maps[].hallway_battle       走廊遭遇数
##   maps[].hallway_hunger       饥饿检定次数
##   encounters[dungeon][level][hall|room]  权重化遭遇表

## 英雄等级 → 装备/技能阶。和 bench_battle 的口径一致：
## 打 5 层的队伍不会还穿 1 阶装备，否则测的是不存在的场景。
const GEAR_BY_LEVEL: Dictionary = {1: 0, 2: 0, 3: 2, 4: 2, 5: 4, 6: 4}


static func build(db: DdDb, dungeon: String, size: String, level: int, rng: DdRng) -> Array:
	var map: Dictionary = db.map_for(dungeon, size)
	if map.is_empty():
		push_warning("RouteGen: 没有 %s/%s 的地图参数" % [dungeon, size])
		return []

	var room_battles: int = roll_range(map.get("total_room_battles", [1, 2]), rng)
	var hall_battles: int = roll_range(map.get("hallway_battle", [1, 2]), rng)
	var hungers: int = roll_range(map.get("hallway_hunger", [1, 2]), rng)

	var gear: int = int(GEAR_BY_LEVEL.get(clampi(level, 1, 6), 0))
	var enc: Dictionary = encounter_block(db, dungeon, level)

	var battles: Array = []
	for i in room_battles:
		var m: Array = pick_encounter(db, enc.get("room", []), rng)
		if not m.is_empty():
			battles.append({"kind": "battle", "monsters": m, "gear": gear,
				"skill": gear, "source": "room"})
	for i in hall_battles:
		var m2: Array = pick_encounter(db, enc.get("hall", []), rng)
		if not m2.is_empty():
			battles.append({"kind": "battle", "monsters": m2, "gear": gear,
				"skill": gear, "source": "hall"})

	if battles.is_empty():
		var fallback: Array = pick_encounter(db, enc.get("hall", []), rng)
		if fallback.is_empty():
			return []
		battles.append({"kind": "battle", "monsters": fallback, "gear": gear,
			"skill": gear, "source": "hall"})

	return _interleave_hunger(battles, hungers)


## 饥饿检定均匀插在战斗之间——不能全堆在开头或结尾，
## 否则「带不带口粮」这个决策的收益会随位置剧烈波动。
static func _interleave_hunger(battles: Array, hungers: int) -> Array:
	var out: Array = []
	var n: int = battles.size()
	for i in n:
		out.append(battles[i])
		# 在第 i 场之后插 hunger：把 n 场分成 hungers+1 段，取段首
		if hungers > 0:
			var want: int = int(floor(float((i + 1) * hungers) / float(n + 1)))
			var have: int = _count_kind(out, "hunger")
			if want > have:
				out.append({"kind": "hunger"})
	while _count_kind(out, "hunger") < hungers:
		out.append({"kind": "hunger"})
	return out


static func _count_kind(steps: Array, kind: String) -> int:
	var n: int = 0
	for s in steps:
		if str(s.get("kind", "")) == kind:
			n += 1
	return n


## 等级 → 遭遇表档位。数据里只有 1/3/5 三档（对应地牢 1-2/3-4/5 层），
## 中间等级向下取档，避免「6 级队打 5 层表」这种越级组合悄悄出现。
## 公开给 MapGen 用：遭遇投放逻辑只能有一份，否则线性路线和房间图
## 会抽出两套难度分布，bench 与界面再也对不上。
static func encounter_block(db: DdDb, dungeon: String, level: int) -> Dictionary:
	var by_dungeon: Dictionary = db.encounters.get(dungeon, {})
	if by_dungeon.is_empty():
		return {}
	var key: String = "1"
	if level >= 5:
		key = "5"
	elif level >= 3:
		key = "3"
	elif level >= 2:
		key = "2"
	var blk: Dictionary = by_dungeon.get(key, {})
	if blk.is_empty():
		# 有的地牢没有 2 层表，退回最近的档位
		for k in ["1", "3", "5"]:
			if by_dungeon.has(k):
				blk = by_dungeon[k]
				break
	return blk


## 权重抽样。表里的 chance 是相对权重（0.01 到 3 不等），不是概率，
## 直接当概率用会得到「大部分条目永不出场」的假分布。
static func pick_encounter(db: DdDb, rows: Array, rng: DdRng) -> Array:
	if rows.is_empty():
		return []
	var total: float = 0.0
	var usable: Array = []
	for r in rows:
		if not (r is Dictionary):
			continue
		var types: Array = r.get("types", [])
		var kept: Array = []
		for t in types:
			if not db.monster(str(t)).is_empty():
				kept.append(str(t))
		if kept.is_empty():
			continue
		var w: float = maxf(float(r.get("chance", 1.0)), 0.0001)
		usable.append({"w": w, "types": kept})
		total += w
	if usable.is_empty():
		return []

	var roll: float = rng.next_float() * total
	var acc: float = 0.0
	for u in usable:
		acc += float(u.w)
		if roll <= acc:
			return (u.types as Array).duplicate()
	return (usable[-1].types as Array).duplicate()


static func roll_range(r: Variant, rng: DdRng) -> int:
	if r is Array and (r as Array).size() >= 2:
		var lo: int = int(r[0])
		var hi: int = int(r[1])
		if hi <= lo:
			return lo
		return rng.next_int_range(lo, hi)
	if r is float or r is int:
		return int(r)
	return 0

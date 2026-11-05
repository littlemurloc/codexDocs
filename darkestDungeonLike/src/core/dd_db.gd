class_name DdDb
extends RefCounted
## 数据访问层：把 M0 抽出的 JSON 读成索引好的字典。
##
## 只做「查得到」和「查不到要报错」两件事，不含任何玩法判断——
## 规则逻辑全在 Battle / EffectResolver 里，方便单独替换数值集。

var rules: DdRules

var heroes: Dictionary = {}      # id -> 原始字典
var monsters: Dictionary = {}    # id -> 原始字典
var effects: Dictionary = {}     # name -> 原始字典
var buffs: Dictionary = {}       # id -> 原始字典
var trinkets: Dictionary = {}
var dungeon_mash: Dictionary = {}
var map_generator: Dictionary = {}   # "dungeon|quest|size" -> 参数

# —— 远征层（M3）——
var dungeon_maps: Array = []         # dungeons.json 的 maps 列表
var encounters: Dictionary = {}      # dungeon -> level -> kind -> [{chance, types}]
var dungeon_props: Dictionary = {}   # dungeon -> 奇物刷新权重（M13 起由 CurioLib 消费）
var expedition_cfg: ExpeditionCfg    # 资源层策略（expedition.json）
## 走廊奇物密度下限（百分数）。0 = 完全听 dungeons.json 的原始值。
## 从 expedition.json 顶层读，不进 preset——见 ExpeditionCfg 的说明。
var curio_hall_pct_min: int = 0
var campaign_cfg: Dictionary = {}    # 元层参数（campaign.json）
## 任务定义（M32）：`quest.types.types` 的 6 种任务 × `quest.types.goals` 的 48 个目标。
## 这份表 M0 就抽出来了，M20 做「到终点打首领」时只用了一个写死的字符串，
## 到这里才真的被读。见 QuestGoal 的注释。
var quests: Dictionary = {}

# —— 战利品与奇物（M13）——
# 这两份此前是「数据在、无人读」：M5 的战利品是手写常数，奇物是一枚硬币。
var loot_tables: LootTables
var curio_lib: CurioLib
var quirk_lib: QuirkLib
var trinket_lib: TrinketLib
var shop: Shop

var missing_refs: Array = []     # 引用缺失记录（应当为空）


## 解析 1 MB 级 JSON 不算便宜，多场战斗共用一份即可
var _base: String = "res://data"


static var _shared: DdDb = null


static func shared(base: String = "") -> DdDb:
	# 传入非空路径会切换数值包并强制重载，便于同一进程内对比多套平衡
	if _shared == null or (not base.is_empty() and base != _shared._base):
		var fresh := DdDb.new()
		if not base.is_empty():
			fresh._base = base
		fresh.load_all(fresh._base)
		_shared = fresh
	return _shared


func load_all(base: String = "") -> bool:
	if not base.is_empty():
		_base = base
	rules = DdRules.new()
	if not rules.load_from(_base + "/rules.json"):
		return false

	heroes = _index(_read_array(_base + "/heroes.json"), "id")
	monsters = _index(_read_array(_base + "/monsters.json"), "id")
	effects = _index(_read_array(_base + "/effects.json"), "name")
	buffs = _index(_read_array(_base + "/buffs.json"), "id")

	if heroes.is_empty() or monsters.is_empty() or effects.is_empty():
		push_error("DdDb: 核心数据缺失，请先运行 tools/extract.py")
		return false

	_load_dungeons()

	expedition_cfg = ExpeditionCfg.new()
	expedition_cfg.load_from(_base + "/expedition.json")
	curio_hall_pct_min = _read_curio_rate(_base)

	# 元层参数：数值包里没有就退回 res://data。
	# 掉落与开销不是「战斗数值」，所以不跟着 balance 包走同一套旋钮。
	campaign_cfg = _read_dict_fallback(_base + "/campaign.json", "res://data/campaign.json")
	# 任务定义同样不走 balance 包：它描述「任务要你做什么」，
	# 换数值包不该顺手把「清剿要求打几场」改掉。
	quests = _read_dict_fallback(_base + "/quests.json", "res://data/quests.json")

	loot_tables = LootTables.new()
	if not loot_tables.load_from(_base):
		loot_tables = null
	curio_lib = CurioLib.new()
	if not curio_lib.load_from(_base):
		curio_lib = null
	quirk_lib = QuirkLib.new()
	if not quirk_lib.load_from(_base):
		quirk_lib = null
	# 槽位上限以规则表为准（5 正 / 5 负 / 3 病），不是写死在 QuirkLib 里的默认值。
	if quirk_lib != null:
		quirk_lib.apply_caps(rules.quirk_max_positive, rules.quirk_max_negative,
			rules.quirk_max_diseases)
	# 饰品把 DdDb 已经建好的 buff 索引递进去，不再重复解析 552 KB。
	trinket_lib = TrinketLib.new()
	if not trinket_lib.load_from(_base, buffs):
		trinket_lib = null
	# 抽卡表的 trinket 叶子只写稀有度，具体是哪件得由饰品库定。
	# 放在这里而不是 LootTables.load 里，是因为加载顺序：loot 先于 trinket。
	if loot_tables != null:
		loot_tables.trinket_lib = trinket_lib
	# 商店读 inventory.json 的价格，上架时用饰品库的稀有度池。
	shop = Shop.new()
	if not shop.load_from(_base, trinket_lib):
		shop = null
	return true


## 内容密度只从 `res://data` 读，**不走 balance 包**。
##
## 理由和 loot / curios 一样：它是「游戏里该有多少内容」的规则数据，
## 不是难度旋钮。balance 包换的是数值强弱，不该顺手把地图上的奇物
## 数量改掉——那会让「换了数值包之后玩家抱怨太无聊」变成一个查不出的问题。
##
## 优先读 base（自定义数据包可以覆盖），读不到再退 res://data。
func _read_curio_rate(base: String) -> int:
	for path in [base + "/expedition.json", "res://data/expedition.json"]:
		if not FileAccess.file_exists(path):
			continue
		var parsed: Variant = JSON.parse_string(FileAccess.get_file_as_string(path))
		if parsed == null or typeof(parsed) != TYPE_DICTIONARY:
			continue
		var cr: Dictionary = (parsed as Dictionary).get("curio_rate", {})
		if cr.has("hallway_pct_min"):
			return clampi(int(cr["hallway_pct_min"]), 0, 100)
	return 0


func _read_dict_fallback(a: String, b: String) -> Dictionary:
	for p in [a, b]:
		if not FileAccess.file_exists(p):
			continue
		var parsed: Variant = JSON.parse_string(FileAccess.get_file_as_string(p))
		if parsed is Dictionary:
			return parsed
	push_warning("DdDb: 找不到 %s，元层参数使用空表" % a)
	return {}


## 地图参数与遭遇表。缺失不致命——战斗本身不需要它们，
## 只有远征层（RouteGen）才用得上，所以只警告不返回 false。
func _load_dungeons() -> void:
	var path: String = _base + "/dungeons.json"
	if not FileAccess.file_exists(path):
		push_warning("DdDb: 找不到 %s，远征层将无法生成路线" % path)
		return
	var parsed: Variant = JSON.parse_string(FileAccess.get_file_as_string(path))
	if parsed == null or typeof(parsed) != TYPE_DICTIONARY:
		push_warning("DdDb: %s 解析失败" % path)
		return
	var d: Dictionary = parsed
	dungeon_maps = d.get("maps", [])
	encounters = d.get("encounters", {})
	dungeon_props = d.get("props", {})
	for m in dungeon_maps:
		if m is Dictionary:
			var key: String = "%s|%s|%s" % [m.get("dungeon_type", ""), m.get("quest_type", ""), m.get("size", "")]
			map_generator[key] = m


## 取某个地牢/任务/规模的 map 参数；找不到就返回空字典。
func map_for(dungeon: String, size: String, quest_type: String = "explore") -> Dictionary:
	return map_generator.get("%s|%s|%s" % [dungeon, quest_type, size], {})


func _read_array(path: String) -> Array:
	if not FileAccess.file_exists(path):
		push_error("DdDb: 找不到 %s" % path)
		return []
	var parsed: Variant = JSON.parse_string(FileAccess.get_file_as_string(path))
	if parsed == null:
		push_error("DdDb: %s 解析失败" % path)
		return []
	return parsed if parsed is Array else []


func _index(rows: Array, key: String) -> Dictionary:
	var out: Dictionary = {}
	for row in rows:
		if row is Dictionary and row.has(key):
			out[str(row[key])] = row
	return out


## 英雄「生成」时自带几条怪癖。
##
## 这是 M14 漏掉的那条主渠道：DD1 的新英雄不是白纸，
## 每个都带 1–2 正 + 1–2 负（`heroes.json` 的 generation 段）。
## 只接奇物渠道，等于把「人物个性」全押在「这趟有没有碰到书架」上。
## 返回 {hid: {pos_min, pos_max, neg_min, neg_max}}。
func hero_quirk_generation() -> Dictionary:
	var out: Dictionary = {}
	for hid in heroes.keys():
		var h: Dictionary = heroes[hid]
		var g: Dictionary = h.get("generation", {})
		if g.is_empty():
			continue
		out[str(hid)] = {
			"pos_min": int(g.get("number_of_positive_quirks_min", 0)),
			"pos_max": int(g.get("number_of_positive_quirks_max", 0)),
			"neg_min": int(g.get("number_of_negative_quirks_min", 0)),
			"neg_max": int(g.get("number_of_negative_quirks_max", 0)),
		}
	return out


## 某一档遭遇的「情报摘要」（M21）：会遇到哪些怪、首领是谁。
##
## 按**基础 id** 去重计数——`:cultist_brawler_A/B/C` 对玩家来说是同一个东西，
## 报三次没有意义。返回 {common: [id...], bosses: [id...]}，common 按频次降序取前 3。
##
## 这里只做统计，不负责翻译成中文：命名规则属于表现层（`DdNames.monster_name`）。
func encounter_outline(dungeon: String, level: int) -> Dictionary:
	var blk: Dictionary = RouteGen.encounter_block(self, dungeon, level)
	var common: Dictionary = {}
	for key in ["hall", "room"]:
		for row in (blk.get(key, []) as Array):
			if not (row is Dictionary):
				continue
			for t in ((row as Dictionary).get("types", []) as Array):
				var b: String = _monster_base(str(t))
				common[b] = int(common.get(b, 0)) + 1
	var bosses: Array = []
	for row2 in (blk.get("boss", []) as Array):
		if not (row2 is Dictionary):
			continue
		for t2 in ((row2 as Dictionary).get("types", []) as Array):
			var b2: String = _monster_base(str(t2))
			if not bosses.has(b2):
				bosses.append(b2)
	# 按频次降序。sort_custom 的比较函数要稳定，所以带上 base id 做二级排序，
	# 否则同频次的怪每次跑出来的顺序都可能不同，截图和测试都没法复现。
	var keys: Array = common.keys()
	keys.sort_custom(func(a, b):
		if int(common[a]) != int(common[b]):
			return int(common[a]) > int(common[b])
		return str(a) < str(b))
	return {"common": keys.slice(0, 3), "bosses": bosses}


## 去掉难度后缀：`cultist_brawler_B` → `cultist_brawler`。
## DdTheme 里有一份同名的静态函数（那边不依赖数据层），两处逻辑一样简单，
## 交叉引用见各自的注释——`MONSTER_NAMES` 的 key 用的就是这个形态。
static func _monster_base(id: String) -> String:
	for suf in ["_A", "_B", "_C", "_D"]:
		if id.ends_with(suf):
			return id.substr(0, id.length() - 2)
	return id


func hero(id: String) -> Dictionary:
	return heroes.get(id, {})


## 全部职业 id（按 `heroes.json` 的顺序）。招新的候选池用它（M27）——
## 元层的名册上限等于这个列表的长度，所以它不该自己硬编码 15。
func hero_ids() -> Array:
	var out: Array = []
	for k in heroes.keys():
		out.append(str(k))
	return out


## 技能组规则（`heroes.json` 的 skill_selection 段，M19）。
##
## 这段数据从 M0 就抽出来了，但十来期没人读过——表现是「每个英雄 7 个技能
## 全开」，玩家没有搭 build 的空间，而原版是 4 个。
## 憎恶是唯一的例外（变身职业，can_select=false，7 个全开）。
##
## 返回 {hid: {can_select, max, ids}}，`ids` 按数据顺序。
func hero_skill_table() -> Dictionary:
	var out: Dictionary = {}
	for hid in heroes.keys():
		var h: Dictionary = heroes[hid]
		var ids: Array = []
		for s in (h.get("skills", []) as Array):
			if s is Dictionary:
				ids.append(str((s as Dictionary).get("id", "")))
		var ss: Dictionary = h.get("skill_selection", {})
		out[str(hid)] = {
			"can_select": ss.get("can_select_combat_skills", true) == true,
			"max": int(ss.get("number_of_selected_combat_skills_max", 0)),
			"ids": ids,
		}
	return out


func monster(id: String) -> Dictionary:
	return monsters.get(id, {})


func effect(name: String) -> Dictionary:
	var e: Dictionary = effects.get(name, {})
	if e.is_empty() and not name.is_empty():
		missing_refs.append(name)
	return e


func buff(id: String) -> Dictionary:
	return buffs.get(id, {})


## 按前缀枚举 buff id。崩溃/美德/死门的 buff 都是成组出现的
## （afflictionFearfulBuff1..5），写死条数会在换数值包时静默失效，
## 所以一律按前缀查。
func buff_ids_with_prefix(prefix: String) -> Array:
	var out: Array = []
	for id in buffs.keys():
		if str(id).begins_with(prefix):
			out.append(str(id))
	out.sort()
	return out


## 崩溃种类直接从 buffs.json 里反推：afflictionFearfulBuff1..5 存在，
## 就说明有 "fearful" 这一种。写死一份种类表会在换数据时静默错位。
func affliction_kinds() -> Array:
	return _kinds_by_prefix("affliction")


func virtue_kinds() -> Array:
	return _kinds_by_prefix("virtue")


func _kinds_by_prefix(prefix: String) -> Array:
	var out: Array = []
	for id in buffs.keys():
		var s: String = str(id)
		if not s.begins_with(prefix) or not s.ends_with("Buff1"):
			continue
		var kind: String = s.substr(prefix.length(), s.length() - prefix.length() - 5).to_lower()
		if not kind.is_empty() and not out.has(kind):
			out.append(kind)
	out.sort()
	return out


## 技能上的 effect 字段可能是字符串也可能是数组，统一成数组
static func effect_names(skill_level: Dictionary) -> Array:
	var v: Variant = skill_level.get("effect", [])
	if v is String:
		return [v] if not (v as String).is_empty() else []
	if v is Array:
		return v
	return []


## 英雄在指定装备等级（0-4）下的基础属性。
## 速度取自武器、生命/闪避/防护取自护甲——这是 DD1 的原始分法。
func hero_base(hero_id: String, gear_level: int = 0) -> Dictionary:
	var h: Dictionary = hero(hero_id)
	if h.is_empty():
		return {}
	var lv: int = clampi(gear_level, 0, 4)
	var weapons: Array = h.get("weapons", [])
	var armours: Array = h.get("armours", [])
	if weapons.size() <= lv or armours.size() <= lv:
		return {}
	var w: Dictionary = weapons[lv]
	var a: Dictionary = armours[lv]
	var dmg: Array = w.get("dmg", [0, 0])
	return {
		"hp_max": int(a.get("hp", 0)),
		"dodge": float(a.get("def", 0.0)),
		"prot": float(a.get("prot", 0.0)),
		"speed": float(w.get("spd", 0)) + float(a.get("spd", 0)),
		"crit": float(w.get("crit", 0.0)),
		"acc": float(w.get("atk", 0.0)),
		"dmg_low": float(dmg[0]) if dmg.size() > 0 else 0.0,
		"dmg_high": float(dmg[1]) if dmg.size() > 1 else 0.0,
	}


## 怪物基础属性
func monster_base(monster_id: String) -> Dictionary:
	var m: Dictionary = monster(monster_id)
	if m.is_empty():
		return {}
	var s: Dictionary = m.get("stats", {})
	return {
		"hp_max": int(s.get("hp", 0)),
		"dodge": float(s.get("def", 0.0)),
		"prot": float(s.get("prot", 0.0)),
		"speed": float(s.get("spd", 0)),
		"crit": 0.0,
		"acc": 0.0,
		"dmg_low": 0.0,
		"dmg_high": 0.0,
		"stun_resist": float(s.get("stun_resist", 0.0)),
		"poison_resist": float(s.get("poison_resist", 0.0)),
		"bleed_resist": float(s.get("bleed_resist", 0.0)),
		"debuff_resist": float(s.get("debuff_resist", 0.0)),
		"move_resist": float(s.get("move_resist", 0.0)),
		"death_blow_resist": float(s.get("death_blow_resist", 0.0)),
	}

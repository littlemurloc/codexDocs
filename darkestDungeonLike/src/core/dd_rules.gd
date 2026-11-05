class_name DdRules
extends RefCounted
## shared/rules.json 的类型化包装。
##
## 这是 DD1 的「手感常量表」：三十几个浮点数决定了整个游戏的硬度。
## 直接把原始字典摊在这里，不做归一化——因为这些数值将来要整体替换成
## 自研参数集（M2），保持与源文件一对一，替换时才好逐项对照。

const DEFAULT_PATH: String = "res://data/rules.json"

# —— 命中 / 暴击 ——
var cutoff_miss: float = 0.0
var cutoff_hit: float = 0.95
var player_crit_table: Array = [{"chance": 1, "value": 1.5}]
var monster_crit_table: Array = [{"chance": 1, "value": 1.5}]
var consecutive_miss_acc_buff: float = 0.04

# —— 行动序 ——
var initiative_base: int = 8

# —— 压力 ——
var monster_crit_stress: float = 10.0
var monster_crit_companion_chance: float = 0.5
var monster_crit_companion_stress: float = 5.0
var player_crit_relief: float = 3.0
var player_crit_companion_chance: float = 0.25
var player_crit_companion_relief: float = 3.0
var stun_ends_turn: bool = true

# —— 死门 ——
var deaths_door_self_stress: float = 8.0
var deaths_door_companion_chance: float = 0.25
var deaths_door_companion_stress: float = 4.0

# —— 乱序突袭 ——
var surprise_corridor_monsters: float = 0.1
var surprise_corridor_party: float = 0.1

# —— 压力阈值（M3 崩溃/美德）——
var affliction_onset_chance: float = 0.75
var affliction_critical_success_chance: float = 0.25
var affliction_critically_resisted: float = 45.0

# —— 光照（M3）——
# darkness 是 DD1 自己的光照档位修正表：明亮/微光/昏暗/漆黑/无光五档，
# 每档给压力、怪物伤害、暴击、闪避、被惊袭概率的加成。原表照搬，不改。
var darkness: Dictionary = {}
var tile_light_loss: Array = []

# —— 陷阱与障碍（M8）——
# difficulty_trap_base 是 DD1 自己的「按地牢等级给的陷阱难度」表，
# 索引就是等级（1..6），0 位留空。它减的是**躲避几率**，不是伤害。
var difficulty_trap_base: Array = []
# 侦察过的陷阱解除加成：这一条是「看见就能应对」的直接证据，
# 不是我们发明的规则。
var trap_scout_disarm_bonus: float = 0.4

# —— 口粮（M3）——
var hunger_hp_restore: float = 0.05   # 吃到口粮回的血量比例
var hunger_starve_hp_dmg: float = 0.2 # 没吃到掉的血量比例

# —— 营地（M3）——
var camp_restore_torch: float = 100.0
var camp_relieve_stress: float = 0.0
var camp_points: float = 12.0
var camp_max_skills: int = 3
var camp_ambush_chance: float = 0.33

# —— 撤退 ——
var retreat_stress: float = 20.0


## 某个地牢等级的陷阱难度（超出表长按最后一档算）。
func trap_difficulty(level: int) -> float:
	if difficulty_trap_base.is_empty():
		return 0.0
	var i: int = clampi(level, 0, difficulty_trap_base.size() - 1)
	return float(difficulty_trap_base[i])

# —— 走廊压力 ——
var hallway_stress: Dictionary = {}

var raw: Dictionary = {}
var raid: Dictionary = {}

# —— 怪癖（M14 修正）——
#
# 这三个数原先是按「DD1 印象」写成 3/3/1 的，而 rules.json 里写的是 5/5/3。
# 数据一直都在，是我没读。槽位从 3 提到 5 之后，「怪癖满了」这件事会晚来很多，
# 抬高了单次奇物的价值——这不是数值偏好，是还原。
var quirk_max_positive: int = 5
var quirk_max_negative: int = 5
var quirk_max_diseases: int = 3
## 负面怪癖在若干回合后有概率「锁定」，锁定后不能再被洗掉。
## 本作没有医院/疗养所，锁定暂无落点，只把参数读进来备用。
var quirk_negative_lock_chance: float = 0.25
var quirk_negative_lock_after_turns: int = 2


func load_from(path: String = DEFAULT_PATH) -> bool:
	if not FileAccess.file_exists(path):
		push_error("DdRules: 找不到 %s" % path)
		return false
	var text: String = FileAccess.get_file_as_string(path)
	var parsed: Variant = JSON.parse_string(text)
	if parsed == null or typeof(parsed) != TYPE_DICTIONARY:
		push_error("DdRules: %s 不是合法 JSON 对象" % path)
		return false
	raw = parsed.get("rules", {})
	raid = parsed.get("raid_settings", {})
	_apply()
	return true


func _apply() -> void:
	cutoff_miss = _f("cutoffAlwaysMiss", 0.0)
	cutoff_hit = _f("cutoffAlwaysHit", 0.95)
	consecutive_miss_acc_buff = _f("consecutive_miss_reduction_acc_buff", 0.04)
	initiative_base = int(raw.get("initiative_base", 8))

	quirk_max_positive = int(raw.get("quirks_max_positive", 5))
	quirk_max_negative = int(raw.get("quirks_max_negative", 5))
	quirk_max_diseases = int(raw.get("quirks_max_diseases", 3))
	quirk_negative_lock_chance = float(raw.get("quirk_chance_to_lock_negative", 0.25))
	quirk_negative_lock_after_turns = int(raw.get("quirk_negative_locked_after_turn_count", 2))

	var pt: Variant = raw.get("player_crit_multiplier_table")
	if pt is Array and not pt.is_empty():
		player_crit_table = pt
	var mt: Variant = raw.get("monster_crit_multiplier_table")
	if mt is Array and not mt.is_empty():
		monster_crit_table = mt

	var mc: Dictionary = raw.get("monster_crit", {})
	monster_crit_stress = float(mc.get("stress_damage", 10))
	monster_crit_companion_chance = float(mc.get("companion_stress_chance", 0.5))
	monster_crit_companion_stress = float(mc.get("companion_stress_damage", 5))

	var pc: Dictionary = raw.get("player_crit", {})
	player_crit_relief = float(pc.get("stress_relief", 3))
	player_crit_companion_chance = float(pc.get("companion_relief_chance", 0.25))
	player_crit_companion_relief = float(pc.get("companion_stress_relief", 3))

	stun_ends_turn = bool(raw.get("stun_ends_turn", true))

	deaths_door_self_stress = _f("deaths_door_self_stress_dmg", 8.0)
	deaths_door_companion_chance = _f("deaths_door_companion_stress_chance", 0.25)
	deaths_door_companion_stress = _f("deaths_door_companion_stress_dmg", 4.0)

	surprise_corridor_monsters = _f("surprise_corridor_monsters_base_chance", 0.1)
	surprise_corridor_party = _f("surprise_corridor_party_base_chance", 0.1)

	# —— M3 资源层 ——
	affliction_onset_chance = _f("affliction_base_onset_chance", 0.75)
	affliction_critical_success_chance = _f("affliction_critical_success_chance", 0.25)
	affliction_critically_resisted = _f("stress_affliction_critically_resisted", 45.0)

	var dk: Variant = raw.get("darkness")
	if dk is Dictionary:
		darkness = dk
	var tl: Variant = raw.get("tile_light_loss")
	if tl is Array:
		tile_light_loss = tl

	var dtb: Variant = raw.get("difficulty_trap_base", [])
	difficulty_trap_base = dtb if typeof(dtb) == TYPE_ARRAY else [0.0, 0.0, 0.0, 0.2, 0.2, 0.4, 0.5]
	trap_scout_disarm_bonus = _f("trap_scout_disarm_bonus", 0.4)
	hunger_hp_restore = _f("hallway_hunger_HPrestore", 0.05)
	hunger_starve_hp_dmg = _f("hallway_hunger_starve_HPdmg", 0.2)

	camp_restore_torch = _f("camp_restore_torch", 100.0)
	camp_relieve_stress = _f("camp_relieve_stress", 0.0)
	camp_points = _f("camp_start_camping_points", 12.0)
	camp_max_skills = int(raw.get("max_number_of_camping_skills", 3))
	camp_ambush_chance = _f("ambush_camping_base_chance", 0.33)

	retreat_stress = _f("combat_retreat_stress", 20.0)

	var hs: Variant = raw.get("hallway_stress")
	if hs is Dictionary:
		hallway_stress = hs


func _f(key: String, fallback: float) -> float:
	var v: Variant = raw.get(key, fallback)
	if typeof(v) == TYPE_FLOAT or typeof(v) == TYPE_INT:
		return float(v)
	return fallback

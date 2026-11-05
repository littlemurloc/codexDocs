class_name Expedition
extends RefCounted
## 远征：把「一场战斗」变成「一段路程」。
##
## M2 测出来的问题是硬的：连续三场、满编高难怪、怪物伤害 ×1.6，结果都是
## 零死亡、终局血量 94%。原因不在伤害数字，在**资源**——治疗把累积伤害
## 完全抵消了，压力涨到多少也不会有任何事发生。
##
## 所以这一层负责四件事，每件都直接对着 M2 的漏洞：
##
##   1. 资源约束  火把（光照）与口粮有限，用完了不会自己回来
##   2. 状态延续  血量比例、压力、崩溃/美德、死门跨战斗带着走
##   3. 压力兑现  100 压力崩溃、200 压力心脏骤停——压力终于有后果
##   4. 撤退成本  打不过可以撤，但要付压力代价，且这趟远征算失败
##
## 规则边界：本类不实现任何战斗规则，只决定「什么时候开打、开打前环境如何」。
## 战斗规则一律在 Battle 里。这样资源层的参数可以做对照实验，
## 而不必担心把战斗数学改成另一套。

const MAX_STEPS: int = 64

var db: DdDb
var rng: DdRng
var cfg: Dictionary = {}
var preset_name: String = ""
var dungeon: String = "weald"     # 只用于查地图参数（每步走几格）
var size_name: String = "short"
var hero_ids: Array = []
var route: Array = []
var step_index: int = 0

# 每个英雄自己的装备/技能阶（元层升级的结果）。路线里的 step.gear 只是默认值，
# 有 hero_gear 时以英雄为准——不然「花钱升级」在下一趟里毫无体现。
var hero_gear: Dictionary = {}
var hero_skill: Dictionary = {}
## 这一趟每个人装备了哪 4 个战斗技能（hid -> Array[skill_id]，M19）。
## 缺省为空 = 全装，这是 M1~M18 的行为，bench 复现旧基线靠它。
## 和 `hero_skill`（技能**等级**）是两件事，别混。
var hero_loadout: Dictionary = {}
## 这一趟每个人身上戴了哪些饰品（hid -> Array[trinket_id]）。
## 由场景从元层的装备状态灌进来：远征不认识 Campaign，也不该认识
## （那样元层和远征层会互相引用）。缺省为空 = 这趟谁都没戴。
var hero_trinkets: Dictionary = {}
## 这一趟每人进本时白吃的压力（hid -> float，M25）。
##
## 来由：英雄决心等级低于任务等级时，每低一级 +20 点。远征层不认识
## Campaign，也不该认识，所以由场景算好灌进来——和上面三张表同一个口径。
## **必须在 setup 之前赋值**（state 是在 setup 里建的）。缺省为空 = 无惩罚，
## bench 不加这个参数，历史基线逐位不变。
var join_stress: Dictionary = {}

## 这一趟每人的受压倍率（hid -> float，M29）。
##
## 和 `join_stress` 是同一个来源的两半：英雄比任务低 N 级时，
## 进本时白吃 20N 压力（一次性），**而且之后每次受压都 × (1 + 0.25N)**。
## 前者是「进门就要付的门票」，后者是「在里面每一步都更疼」——
## 只做前者的话，低等级打高级本只是开局难一点，撑过前两场就恢复了。
##
## 缺省为空 = 无倍率，bench 不灌这个参数，M9 以来的基线逐位不变。
var join_stress_mult: Dictionary = {}

# —— 远征资源 ——
var light: float = 100.0
var food: int = 0
var torch: int = 0
var shovel: int = 0
var camps_left: int = 0
var heal_charges: int = -1      # -1 = 不限

# —— 守护 / 反击（M10）——
# 纯透传：远征层不认识这两个机制，只是把开关交给它创建的每一场战斗。
# 存在的唯一理由是测量——「守护对一整趟路有没有用」必须同队伍对照，
# 而换职业变的东西远不止守护。
var guard_enabled: bool = true
var riposte_enabled: bool = true

# —— 位移 / 洗位（M11）——
# 同样只是透传。位移会改变 rank，而 rank 决定「谁挨打」和「技能能不能用」，
# 所以它在远征层的效果可能和单场完全不同——单场看不见的东西要摊到资源层看。
var move_value_enabled: bool = true
var move_resist_enabled: bool = true

# —— 召唤（M12）——
# 透传，但比前两组更值得摊到资源层看：召唤改变的是「一场战斗要打多久」，
# 而远征里时间就是压力、光照和口粮。单场多 1.4 轮，摊到一趟路上可能
# 直接变成多一次崩溃判定。
var summon_enabled: bool = true
var summon_value_enabled: bool = true
var summon_default_limit_enabled: bool = true

# —— 怪癖 / 疾病（M14）——
#
# 怪癖挂在 state[hid]["quirks"] 上，而不是单独开一个字典。
# 理由很实际：怪癖是**队伍状态**的一部分，和血量压力一样要跨战斗传递、
# 进战斗时灌给 Combatant。`apply_party_state` 已经在逐英雄读 state，
# 多读一个键就行；另开一份状态等于要维护两条同步路径，
# 迟早出现「远征说他有，战斗说他没」。
var quirk_enabled: bool = true
## 饰品开关（M15）。默认开，但默认谁都没戴，所以既有基线逐位不变。
var trinket_enabled: bool = true
## 疾病抗性判定用：接触脏东西时，过了抗性就不生病。
## 不写死 1.0，是因为不同英雄的 disease 抗性差很多，做了判定才有属性可言。
var disease_roll_enabled: bool = true
## 奇物自动用道具。默认开：给玩家省掉逐次点选，也让「带什么上路」有回报。
##
## 但它有个副作用，M14 才量出来：**道具交互会顶掉奇物自身的 outcome**，
## 而怪癖/疾病几乎全在「自己碰」的那一侧。于是自动流程总是「用对道具」，
## 负面结果几乎不发生——怪癖系统在自动玩法下近似不可见。
## 这不是 bug 而是 DD1 的设计（带对补给就不容易中招），
## 但必须能关掉，否则我们没有任何办法量到它。
var curio_auto_item_enabled: bool = true
## 食物小数债：把 1.4 倍消耗摊成「每五次多吃一次」，见 _resolve_hunger。
var _food_debt: float = 0.0
# —— 队伍状态：def_id -> {hp_ratio, stress, affliction, virtue, at_deaths_door, ...} ——
var state: Dictionary = {}

var events: Array = []          # 只存远征级事件，战斗事件折成 stats 计数
var stats: Dictionary = {}

# —— 界面驱动的活动战斗 ——
# 界面不能一次跑完整场，只能「推一个单位、等一次点击」。
# 这三个字段就是那段时间里「当前在打的是什么」。
var active_battle: Battle = null
var active_index: int = 0
## 当前这场是不是首领战（M20）。`finish_battle` 拿不到 step 局部变量，
## 所以在这里存一份，结算时用来区分「普通胜利」和「首领击杀」。
var active_is_boss: bool = false
var _active_uids: Dictionary = {}

# —— 战利品（M5 元层）——
# 规则层只负责「这趟捡到了什么」，不负责「金币能买什么」——
# 后者是 Campaign 的事。没有 loot_cfg 时整段逻辑不跑，
# 所以 bench 的随机流不受影响，历史数据仍然可比。
# —— 战前情报（M6）——
# revealed = 前多少个节点已知。走过的必然知道，前方的要靠侦察。
var revealed: int = 0
var _scout_rng: DdRng

var loot_cfg: Dictionary = {}
var loot_gold: int = 0
var loot_heirlooms: Dictionary = {}
var loot_gems: Dictionary = {}          # 宝石：结算时按 sell 价折成金币
var loot_trinkets: int = 0              # 掉到的饰品件数
var loot_trinket_ids: Array = []        # 掉到的具体饰品 id（M15 起会进仓库）
var _loot_rng: DdRng

# —— 真表开关（M13）——
#
# 关掉就走 M5 那套手写常数（每场 9–17 金、30% 掉传家宝、通关 45+22×场次），
# 用于两件事：历史基线复现，以及「换真表到底差多少」的对照实验。
# 默认开——那套常数只是当年没有解析抽卡树时的占位，留着当基线可以，
# 不该继续当真相。
var loot_table_enabled: bool = true
var curio_table_enabled: bool = true

## 具体补给（holy_water / bandage / medicinal_herbs / …），奇物交互消耗。
## shovel 不放在这里：它有自己的独立字段，是 M8 障碍逻辑的既有口径，
## 在两处镜像同一份数量只会制造不同步。取用一律走 supply_count/take_supply。
var supplies: Dictionary = {}
var _curio_rng: DdRng

## 开局补给包。默认每样一件：够演示「铁处女用绷带」「邪祭坛用圣水」，
## 又不够一路通吃，逼玩家在奇物之间取舍。preset 的 supply.start 可以覆盖。
const DEFAULT_SUPPLY_PACK: Dictionary = {
	"holy_water": 1, "bandage": 1, "medicinal_herbs": 1,
	# 火把、口粮、铁锹**不在这里**：它们各有独立字段（见 `torch` / `food` /
	# `shovel`），默认值来自 expedition.json。M13 把 torch 也塞进来过，
	# 结果是「点灯用 torch 字段（4 支），奇物交互读 supplies（1 支）」，
	# 同一个数量两个值。M16 统一成独立字段。
	"antivenom": 1, "skeleton_key": 1,
}

# —— 房间图模式（M7）——
# 线性路线仍是默认（bench 走这条，口径不变）；地图模式是界面的路：
# 玩家自己选相邻房间，走一条走廊、进一个房间，可能各有内容。
var map_mode: bool = false
var map: Dictionary = {}
var current_room: int = -1
var spotted: Dictionary = {}     # 已知存在的房间（含类型）
## 走廊**内容**是否已知。站在房间里就看得见出口在哪（这不叫侦察），
## 但边上有什么（陷阱/障碍/战斗）要靠侦察——M8 让「绕路」成立的就是这个区别。
var edges_known: Dictionary = {}
var _trap_rng: DdRng
var _pending: Array = []         # 已决定但还没结算的步骤（走廊在前、房间在后）

var ended: bool = false
var end_reason: String = ""     # complete / wipe / retreat

## 地牢难度（1/3/5/6）。战利品表按它选变体，缺省 1 = 最浅的一档。
var dungeon_level: int = 1

## 任务类型（M20）：`explore` / `kill_boss`；M32 起还有 `cleanse`。
## kill_boss 用另一套地图参数（图更短），终点房间放首领战。
## 缺省 explore = M7~M19 的行为。
var quest_type: String = "explore"

## 这条任务的目标（M32），由 `set_location` 从 `quests.json` 解析。
##
## 空字典 = 没解析（没有 quests.json / 旧调用路径），此时按 M31 的老规矩走：
## explore 走到终点就算完成，kill_boss 用那条写死的首领判断。
var quest_goal: Dictionary = {}

## 正在打的这场的来源（room / hall / boss）。清剿任务只数**房间**战斗，
## 走廊遭遇不算——「清光所有房间」和「清光所有走廊」是两件事，
## 而 `dungeons.json` 里 cleanse 的地图参数加的是 room_battle。
var active_source: String = ""

## 这一趟已经算过任务进度的奇物（M33）。收集/激活都是「一处一次」，
## 记在这里才不会因为重走一条走廊重复计数。
var quest_curios_used: Dictionary = {}


func setup(p_db: DdDb, p_heroes: Array, p_route: Array, p_preset: Dictionary,
		seed_value: int = 1, p_preset_name: String = "",
		p_loot_cfg: Dictionary = {}, p_gear: Dictionary = {}) -> bool:
	db = p_db
	if db == null or db.heroes.is_empty():
		push_error("Expedition: 数据未加载")
		return false
	rng = DdRng.new(seed_value)
	cfg = p_preset
	preset_name = p_preset_name
	hero_ids = p_heroes.duplicate()
	route = p_route.duplicate(true)
	hero_gear = p_gear.duplicate()

	loot_cfg = p_loot_cfg
	loot_gold = 0
	loot_heirlooms = {}
	for k in (loot_cfg.get("heirloom_names", []) as Array):
		loot_heirlooms[str(k)] = 0
	# 战利品用独立的随机源：即使开启，也不会改变战斗的随机流。
	# 否则「加了掉落」会连带改变战斗结果，以后所有对比都失去可比性。
	_loot_rng = DdRng.new(seed_value * 31 + 17)
	# 奇物用第三条随机源：它同时决定「碰上哪个奇物」和「给出什么结果」，
	# 混进战利品流会让「同样的战斗、不同的奇物」没法单独对照。
	_curio_rng = DdRng.new(seed_value * 91 + 43)
	loot_gems = {}
	loot_trinkets = 0
	loot_trinket_ids = []
	supplies = {}
	for k in DEFAULT_SUPPLY_PACK.keys():
		supplies[str(k)] = int(DEFAULT_SUPPLY_PACK[k])
	var ss: Dictionary = (cfg.get("supply", {}) as Dictionary).get("start", {})
	for k in ss.keys():
		supplies[str(k)] = int(ss[k])
	# 侦察同样用独立随机源：它每步都要掷，混进战斗流会让既有基线整体漂移。
	_scout_rng = DdRng.new(seed_value * 53 + 7)
	# 陷阱/障碍也各自独立：它们每走一条走廊都可能掷骰，
	# 混进战斗流会让 M3 的全部历史指标漂移（同 M5/M6 的教训）。
	_trap_rng = DdRng.new(seed_value * 67 + 23)
	var sc: Dictionary = cfg.get("scouting", {})
	revealed = clampi(int(sc.get("reveal_on_start", 2)), 0, route.size())

	var lc: Dictionary = cfg.get("light", {})
	light = float(lc.get("start", 100.0))
	torch = int(lc.get("torch_start", 4))

	var fc: Dictionary = cfg.get("food", {})
	food = int(fc.get("start", 4))
	_food_debt = 0.0
	shovel = int((cfg.get("supply", {}) as Dictionary).get("shovel_start", 1))

	var cc: Dictionary = cfg.get("camp", {})
	camps_left = int(cc.get("max", 1))

	heal_charges = int(cfg.get("heal_charges", 0))
	if heal_charges == 0:
		heal_charges = -1     # 0 = 不限，和「用完了」的 0 区分开

	state = {}
	var entry_total: float = 0.0
	for hid in hero_ids:
		# 进本压力（M25）：英雄等级低于任务等级时，每低一级 +20 点。
		# 由 Campaign 在 setup 之前灌进来；bench 不灌就是 0，基线不变。
		var entry: float = maxf(0.0, float(join_stress.get(str(hid), 0.0)))
		state[hid] = {"hp_ratio": 1.0, "stress": clampf(entry, 0.0, 200.0), "affliction": "",
			"virtue": "", "at_deaths_door": false, "dead": false, "recovering": false,
			"quirks": [], "trinkets": (hero_trinkets.get(str(hid), []) as Array).duplicate()}
		entry_total += entry

	stats = {
		"battles": 0, "rounds": 0, "hunger_checks": 0, "hunger_unfed": 0,
		"hero_deaths": 0, "afflictions": 0, "virtues": 0, "heart_attacks": 0,
		"stalemates": 0,
		"dd_entries": 0, "act_outs": 0, "heals": 0, "heals_blocked": 0,
		"attacks": 0, "hits": 0, "crits": 0, "damage_dealt": 0.0,
		"gross_dealt": 0.0, "overkill": 0.0, "stress_added": 0.0,
		"camp_used": 0, "camp_ambush": 0, "torches_used": 0, "scout_reveals": 0,
		"rooms_visited": 0, "curios": 0,
		# 首领击杀（M20）：fought = 真的开了那场仗，killed = 打赢了。
		# 两个字段分开记，才能分清「没走到终点」和「走到了但打不过」——
		# 这是两种完全不同的病，只报一个击杀率会把它们混在一起。
		"boss_fought": false, "boss_killed": false,
		"curio_loot": 0, "curio_stress": 0.0, "curio_items_used": 0,
		"curio_unsupported": 0, "curio_hp_lost": 0.0,
		# 任务奇物进度（M33）：收集到几件 / 激活了几处。
		"quest_gathered": 0, "quest_activated": 0,
		"traps": 0, "traps_dodged": 0, "obstacles": 0, "obstacles_cleared": 0,
		"hp_low_water": 1.0, "min_light": float(light),
		# 怪癖（M14）：获得/被拒/染病/抗病/清负面分开计。
		# 「获得」和「被拒」必须分开——只有获得数会让人误以为奇物总能给到东西。
		"quirks_gained": 0, "quirk_refused_slot_full": 0, "quirk_refused_no_hero": 0,
		"quirk_refused_no_lib": 0, "quirk_target_empty": 0,
		"quirk_refused_duplicate": 0, "quirk_refused_unknown_quirk": 0,
		"diseases_contracted": 0, "diseases_resisted": 0, "diseases_cured": 0,
		"quirks_purged": 0, "quirk_purge_failed": 0, "quirk_pool_empty": 0,
		"light_drained": 0.0,
		# 等级惩罚（M25）：进本时因为「人不够格」白吃的压力总和。
		# 单独记一份，才能分清「这趟是被怪物打崩的」还是「一开始就欠着债」。
		"entry_stress": entry_total,
	}
	quest_curios_used = {}
	_emit({"t": "exp_start", "heroes": hero_ids.duplicate(), "preset": preset_name})
	return true


# ============================================================
# 主循环
# ============================================================

func set_location(p_dungeon: String, p_size: String, p_level: int = 1,
		p_quest: String = "explore") -> void:
	dungeon = p_dungeon
	size_name = p_size
	dungeon_level = maxi(1, p_level)
	quest_type = p_quest
	# 任务目标（M32 / M33）：真正读 `quests.json`，而不是只认一个字符串。
	# 没有这份表时 `parse` 仍然返回一个可用的目标（explore → 走到终点），
	# 所以缺数据不会让远征直接坏掉。
	# M33 起要把奇物表一起传进去：gather / activate 的目标是从标签解析出来的。
	var curios: Dictionary = {}
	if db != null and db.curio_lib != null and db.curio_lib.is_loaded():
		curios = db.curio_lib.curios
	quest_goal = QuestGoal.parse(db.quests if db != null else {}, p_quest, p_dungeon, curios)
	# 战利品表按「地牢 × 难度」选变体：C 表 d1 期望 253 金、d5 期望 559，
	# H 表 d1 给 1–4 件、d5 给 2–8 件。不设语境的话会退化成同一档。
	if db != null and db.loot_tables != null:
		db.loot_tables.set_context(dungeon, dungeon_level)


## 自动走完一整趟。bench 与测试走这条。
func run_auto() -> void:
	var guard: int = 0
	while not ended and step_index < route.size() and guard < MAX_STEPS:
		run_step()
		guard += 1
	if not ended:
		_end("complete")


## 走完一步：取步 → 饥饿或战斗 → 收尾。
##
## 这是「自动模式」的总装线。界面走的是下面四个原语（take_step / start_battle /
## finish_battle / after_step），两者共用同一套内部逻辑——
## 否则界面上打出来的战斗和 bench 里打出来的会是两套东西，测了也白测。
func run_step() -> Dictionary:
	if ended:
		return {}
	var step: Dictionary = take_step()
	if step.is_empty():
		return {}
	match str(step.get("kind", "battle")):
		"hunger":
			_resolve_hunger()
		"curio":
			resolve_curio(step)
		"trap":
			resolve_trap(step)
		"obstacle":
			resolve_obstacle()
		"walk":
			pass
		_:
			var b: Battle = start_battle(step)
			if b != null:
				_play_out(b)
	after_step(true)
	return step


## 原语 1：耗光、走廊压力、取出下一步（并推进 step_index）。
## 返回空字典 = 已经没得走了（会顺手把远征标记为完成）。
func take_step() -> Dictionary:
	if ended:
		return {}
	if map_mode:
		return _take_map_step()
	if step_index >= route.size():
		_end("complete")
		return {}
	_consume_light()
	_hallway_stress()
	var s: Dictionary = route[step_index]
	step_index += 1
	# 走过的路一定知道，视野至少跟上脚步，然后才轮到侦察判定
	revealed = maxi(revealed, step_index)
	_try_scout()
	return s


## 地图模式的一步。光照只在**走走廊**时消耗——
## 走一条走廊和进一个房间如果各扣一次，一次移动的光耗会翻倍，
## 短图的补给根本撑不到出口。
func _take_map_step() -> Dictionary:
	if _pending.is_empty():
		return {}
	var s: Dictionary = _pending.pop_front()
	if bool(s.get("corridor", false)):
		_consume_light()
		_hallway_stress()
	step_index += 1
	return s


func has_pending() -> bool:
	return not _pending.is_empty()


# ============================================================
# 房间图（M7）
# ============================================================

## 进入一张已经生成好的图。必须在 setup() 之后调用。
func enter_map(m: Dictionary) -> void:
	map = m
	map_mode = true
	current_room = int(m["start"])
	spotted = {}
	edges_known = {}
	_pending = []
	step_index = 0
	var rooms: Dictionary = map["rooms"]
	(rooms[current_room] as Dictionary)["visited"] = true
	(rooms[current_room] as Dictionary)["spotted"] = true
	stats["rooms_visited"] = 1
	# 任务目标的分母（M32）：图上一共几间房、其中几间有仗要打。
	# 必须在**进门时**算一次并固定下来——「清剿」的判据是
	# 「打过的战斗房 / 图上原有的战斗房」，如果边打边数分母，
	# 打过一间分母就少一间，永远都能凑成 100%。
	var n_battle_rooms: int = 0
	for rid in (m["room_ids"] as Array):
		var k: String = str((rooms[int(rid)] as Dictionary).get("kind", ""))
		if k == MapGen.K_BATTLE or k == MapGen.K_BOSS:
			n_battle_rooms += 1
	stats["quest_rooms_total"] = (m["room_ids"] as Array).size()
	stats["quest_battles_total"] = n_battle_rooms
	stats["quest_battles_cleared"] = 0
	_spot_neighbors(current_room)
	_emit({"t": "map_enter", "rooms": (m["room_ids"] as Array).size(),
		"shortest": int(m["shortest"]), "at": current_room})


## 当前房间能去哪（含途经的走廊索引）
func adjacent() -> Array:
	if not map_mode:
		return []
	return MapGen.neighbors(map, current_room)


## 走一条走廊到相邻房间。会把「走廊内容 + 房间内容」压进待结算队列。
func travel(room_id: int) -> bool:
	if ended or not map_mode:
		return false
	var edge: int = -1
	for nb in adjacent():
		if int(nb.room) == room_id:
			edge = int(nb.edge)
			break
	if edge < 0:
		return false

	var e: Dictionary = (map["edges"] as Array)[edge]
	var first_time: bool = not bool(e.get("walked", false))
	# 「走进去之前知不知道」这件事必须在走过之后还原不回来，
	# 所以在这里就取快照。它决定陷阱能不能被解除（+40%）。
	var was_known: bool = edges_known.has(edge)
	e["walked"] = true
	edges_known[edge] = true
	if first_time and not (e["steps"] as Array).is_empty():
		for st in (e["steps"] as Array):
			var s2: Dictionary = (st as Dictionary).duplicate()
			s2["corridor"] = true
			s2["from"] = current_room
			s2["to"] = room_id
			s2["edge"] = edge
			s2["scouted"] = was_known
			_pending.append(s2)
	else:
		# 走过的走廊、或本来就没事件的走廊：也要走一步，照样耗光
		_pending.append({"kind": "walk", "corridor": true,
			"from": current_room, "to": room_id, "repeat": not first_time})

	current_room = room_id
	var r: Dictionary = map["rooms"][room_id]
	r["spotted"] = true
	if not bool(r.get("visited", false)):
		r["visited"] = true
		stats["rooms_visited"] = int(stats["rooms_visited"]) + 1
		var st3: Dictionary = r.get("step", {})
		if not st3.is_empty():
			var step_copy: Dictionary = (st3 as Dictionary).duplicate()
			# 标上「这一步属于哪个房间」（M33）：任务奇物的去重键是位置，
			# 而清剿用不到它、其它内容也不受这个多余字段影响。
			step_copy["room"] = room_id
			_pending.append(step_copy)

	_spot_neighbors(room_id)
	_try_scout_map()
	_emit({"t": "travel", "from": int(e.a), "to": int(e.b), "room": room_id,
		"kind": str(r["kind"])})
	return true


func at_goal() -> bool:
	return map_mode and current_room == int(map["goal"])


## 任务进度的原料（M32）。判据在 `QuestGoal.met`，这里只负责把散在
## stats / map 里的数字**拼成一份扁平状态**——两处各算一遍，
## 迟早会出现「结算屏说没完成、地图屏说完成了」。
func quest_state() -> Dictionary:
	return {
		"at_goal": at_goal(),
		"boss_killed": bool(stats.get("boss_killed", false)),
		"battles_total": int(stats.get("quest_battles_total", 0)),
		"battles_cleared": int(stats.get("quest_battles_cleared", 0)),
		"rooms_total": int(stats.get("quest_rooms_total", 0)),
		"rooms_visited": int(stats.get("rooms_visited", 0)),
		"gathered": int(stats.get("quest_gathered", 0)),
		"activated": int(stats.get("quest_activated", 0)),
	}


## 这个任务的要求完成了吗。
func quest_met() -> bool:
	if quest_goal.is_empty():
		return true
	return QuestGoal.met(quest_goal, quest_state())


## 目标的一句话 + 进度，给地图屏和结算屏用。
##
## `curio_label` 是目标奇物的显示名，由界面层传（核心层不认识名字表）。
## 收集/激活任务没有它就只能说「目标奇物」，玩家没法知道该找哪个。
func quest_line(curio_label: String = "") -> String:
	if quest_goal.is_empty():
		return ""
	var pr: Vector2i = QuestGoal.progress(quest_goal, quest_state())
	if str(quest_goal.get("kind", "")) == QuestGoal.KIND_REACH:
		return QuestGoal.describe(quest_goal, quest_state(), curio_label)
	return "%s（%d/%d）" % [
		QuestGoal.describe(quest_goal, quest_state(), curio_label), pr.x, pr.y]


## 在目标房间选择离开。这是"完成"，和撤退不是一回事。
func leave_dungeon() -> void:
	if ended or not map_mode:
		return
	_emit({"t": "leave", "step": step_index})
	_end("complete")


func is_room_spotted(id: int) -> bool:
	return spotted.has(id)


## 这条走廊里有什么，是否已经知道。不知道的时候界面不能画任何标记——
## 画了就等于免费侦察，M8 的一半机制就白做了。
func edge_known(edge: int) -> bool:
	return edges_known.has(edge)


func _edge_kind(edge: int) -> String:
	var edges: Array = map["edges"]
	if edge < 0 or edge >= edges.size():
		return ""
	var st: Array = (edges[edge] as Dictionary).get("steps", [])
	if st.is_empty():
		return ""
	return str((st[0] as Dictionary).get("kind", ""))


## 给界面用：某条走廊已知的内容类型（未知返回空串）。
func edge_kind(edge: int) -> String:
	if not edge_known(edge):
		return ""
	return _edge_kind(edge)


## 调试/截图专用：点亮整张图。正常流程里没有入口——
## 侦察的价值就在于「不全知道」，这个函数只能在调试参数下被调用。
func debug_reveal_all() -> void:
	if not map_mode:
		return
	for id in (map["room_ids"] as Array):
		spotted[int(id)] = true
	# 走廊内容也要点亮：只点亮房间的话，截图里永远看不到陷阱/障碍徽标，
	# 调试开关就失去了它的用途。
	for i in (map["edges"] as Array).size():
		edges_known[i] = true


func room_kind(id: int) -> String:
	if not map_mode:
		return ""
	return str((map["rooms"][id] as Dictionary)["kind"])


func room_visited(id: int) -> bool:
	if not map_mode:
		return false
	return bool((map["rooms"][id] as Dictionary).get("visited", false))


func _spot_neighbors(room: int) -> void:
	spotted[room] = true
	for nb in MapGen.neighbors(map, room):
		spotted[int(nb.room)] = true


## 地图模式下的侦察：掷一次，成功就把「两步之内」的一个未知房间也标出来。
## 线性模式是「往前推一格」，图上自然变成「多看见一个房间」。
func _try_scout_map() -> void:
	if _scout_rng == null:
		return
	var all_rooms: Array = map["room_ids"]
	var all_edges: int = (map["edges"] as Array).size()
	if spotted.size() >= all_rooms.size() and edges_known.size() >= all_edges:
		return
	if not _scout_rng.chance(scout_chance()):
		return

	# 两类候选一起抽：远处的房间，和**脚下这条走廊里有什么**。
	# 后者才是让「绕路」成立的东西——只知道远处有间战斗房，
	# 并不会让你改变下一步走哪条走廊。
	var cand: Array = []
	for id in all_rooms:
		if spotted.has(int(id)):
			continue
		if _room_dist(current_room, int(id)) <= 2:
			cand.append({"kind": "room", "id": int(id)})
	for nb in MapGen.neighbors(map, current_room):
		var ei: int = int(nb.edge)
		if edges_known.has(ei):
			continue
		if ((map["edges"] as Array)[ei] as Dictionary)["steps"].is_empty():
			continue
		cand.append({"kind": "edge", "id": ei})
	if cand.is_empty():
		return

	var pick: Dictionary = cand[_scout_rng.next_int_range(0, cand.size() - 1)]
	stats["scout_reveals"] = int(stats["scout_reveals"]) + 1
	if str(pick["kind"]) == "room":
		spotted[int(pick["id"])] = true
		_emit({"t": "scout", "room": int(pick["id"]), "revealed": spotted.size(),
			"total": all_rooms.size(), "chance": scout_chance()})
	else:
		var ei2: int = int(pick["id"])
		edges_known[ei2] = true
		_emit({"t": "scout_edge", "edge": ei2,
			"kind": _edge_kind(ei2), "chance": scout_chance()})


func _room_dist(a: int, b: int) -> int:
	var n: int = (map["room_ids"] as Array).size()
	var pairs: Array = []
	for e in (map["edges"] as Array):
		pairs.append(Vector2i(int(e.a), int(e.b)))
	var dist: Array = MapGen.bfs(n, MapGen.adjacency_rooms(n, pairs), a)
	if b < 0 or b >= dist.size():
		return 999
	return int(dist[b])


# ============================================================
# 奇物
# ============================================================

## 房间里的一次搜刮。
##
## 旧实现（M5）只有一枚硬币：65% 拿 12–26 金，否则全队 +9 压力。
## 60 个奇物在那个实现里是同一个东西，玩家没有任何理由记住
## 「铁处女要用绷带」「邪祭坛要带圣水」——因为那些区别根本不存在。
##
## 现在走真表：奇物由地图生成时按地牢权重挑好（step.curio），
## 有对应补给就自动用上，然后按奇物自己的分支给结果。
## 没给 step 时退回旧硬币，保证老调用方（含历史测试）仍然能跑。
func resolve_curio(step: Dictionary = {}) -> Dictionary:
	if curio_table_enabled and db != null and db.curio_lib != null and db.curio_lib.is_loaded():
		return _resolve_curio_table(step)
	return _resolve_curio_legacy()


## 记一次任务奇物进度（M33）。
##
## 只有「碰到的正是任务要的那个奇物」才算——不是随便一个奇物。
## 判据是 id 相等：`QuestGoal.resolve_curio` 已经把数据里那个（不存在的）
## 名字解析成本作真实奇物，所以这里比的是解析后的 id。
##
## 去重键是**位置**（房间号 / 走廊号），不是奇物 id。
## 这一点踩过：按 id 去重时，任务要 3 件、图上 3 个都是同一类奇物，
## 碰完第一个之后另外两个全被挡掉，收集数永远停在 1。
func _note_quest_curio(cid: String, step: Dictionary = {}) -> void:
	if quest_goal.is_empty() or cid.is_empty():
		return
	if str(quest_goal.get("curio", "")) != cid:
		return
	# 位置键：房间步带 room、走廊步带 edge（都在 travel() 里标好）。
	# 两个都没有时（线性路线 / 手动调用）不去重——那种场景本来就不会重复。
	var key: String = ""
	if step.has("room"):
		key = "room:%d" % int(step["room"])
	elif step.has("edge"):
		key = "edge:%d" % int(step["edge"])
	if not key.is_empty():
		if quest_curios_used.has(key):
			return
		quest_curios_used[key] = true
	var stat_key: String = ""
	match str(quest_goal.get("kind", "")):
		QuestGoal.KIND_GATHER:
			stat_key = "quest_gathered"
		QuestGoal.KIND_ACTIVATE:
			stat_key = "quest_activated"
		_:
			return
	stats[stat_key] = int(stats.get(stat_key, 0)) + 1
	_emit({"t": "quest_progress", "curio": cid, "kind": str(quest_goal.get("kind", "")),
		"now": int(stats[stat_key]), "need": int(quest_goal.get("amount", 1))})


func _resolve_curio_table(step: Dictionary) -> Dictionary:
	stats["curios"] = int(stats.get("curios", 0)) + 1
	var cl: CurioLib = db.curio_lib

	# 地图生成时已经把奇物挑好放在 step 里。没有就现场按地牢权重补一个，
	# 这样线性路线（bench 走的）也能用上真表。
	var cid: String = str(step.get("curio", ""))
	if cid.is_empty():
		var slot: String = str(step.get("slot", CurioLib.SLOT_ROOM))
		cid = cl.pick(dungeon, slot, _curio_rng)
	if cid.is_empty() or not cl.has(cid):
		return _resolve_curio_legacy()

	# 任务目标奇物（M33）：碰到就算一次进度，**不看这次交互的结果**。
	# 收集任务要的是「去那儿翻」，不是「翻出好东西」——
	# 挂上结果判定的话，一个给疾病的箱子会让任务反而更难，那不是原版语义。
	_note_quest_curio(cid, step)

	# 自动选补给：该奇物能用、且背包里有的第一个。
	# 顺序按奇物自己的 items 表（已排序），结果稳定，便于对照。
	var use_item: String = ""
	if curio_auto_item_enabled:
		for it in cl.items_for(cid):
			if supply_count(str(it)) > 0:
				use_item = str(it)
				break

	var out: Dictionary = cl.resolve(cid, use_item, _curio_rng)
	if use_item.is_empty():
		pass
	elif bool(out.get("item", "") != ""):
		take_supply(use_item)
		stats["curio_items_used"] = int(stats.get("curio_items_used", 0)) + 1

	var got_gold: int = 0
	var got_heirlooms: Dictionary = {}
	var got_supplies: Dictionary = {}
	var pressure: float = 0.0
	var hp_lost: float = 0.0
	var outcome: String = str(out.get("outcome", "nothing"))
	# 结果类型计数。没有这一栏的话，「奇物在跑但怪癖不出现」这种问题
	# 只能靠猜——bench 里 5.47 次接触换来 0.025 条怪癖，就是靠它定位的。
	var oc_key: String = "curio_oc_" + outcome
	stats[oc_key] = int(stats.get(oc_key, 0)) + 1

	# 落地。loot 分支里可能并列多张表（goal_strongbox 就是 B×3 + T×1）。
	var loot_results: Array = []
	for r in (out.get("results", []) as Array):
		if str((r as Dictionary).get("kind", "")) == "loot_table":
			loot_results.append(r)
	if not loot_results.is_empty():
		var agg: Dictionary = LootTables.empty_result()
		db.loot_tables.draw_for(loot_results, _curio_rng, agg)
		var applied: Dictionary = _apply_loot_result(agg)
		got_gold = int(applied["gold"])
		got_heirlooms = applied["heirlooms"]
		got_supplies = applied["supplies"]
		stats["curio_loot"] = int(stats.get("curio_loot", 0)) + got_gold

	# 怪癖/疾病落到谁头上是随机的——这就是「带谁上路」的代价来源。
	# 先抽定目标，同一个奇物的多条结果落在同一个人身上（一次接触一个受害者）。
	var quirk_target: String = random_alive_hero(_curio_rng) if quirk_enabled else ""
	if quirk_target.is_empty():
		stats["quirk_target_empty"] = int(stats.get("quirk_target_empty", 0)) + 1
	var gained_quirk: String = ""
	var lost_quirk: String = ""
	var gained_disease: String = ""

	for r in (out.get("results", []) as Array):
		var d: Dictionary = r
		match str(d.get("kind", "")):
			"stress":
				pressure += float(d.get("value", 0))
			"blight", "bleed":
				# 战斗外的持续伤害没有承载：折算成即时血量损失，
				# 每层按最大生命的 2% 扣。数值小，但方向对——奇物陷阱会掉血。
				hp_lost += float(d.get("value", 0)) * 0.02
			"heal_hp":
				hp_lost -= float(d.get("value", 0)) * 0.02
			"heal_stress":
				pressure -= float(d.get("value", 0))
			"quirk":
				if not quirk_target.is_empty():
					var want: String = str(d.get("quirk", ""))
					if want == "positive" or want == "negative":
						gained_quirk = grant_random_quirk(quirk_target, want, _curio_rng)
					elif not want.is_empty():
						gained_quirk = grant_quirk(quirk_target, want)
			"disease":
				if not quirk_target.is_empty():
					gained_disease = contract_disease(quirk_target,
						str(d.get("disease", "")), _curio_rng)
			"purge":
				# 清负面：挑一个活着的、身上确实有负面怪癖的人。
				# 全队都没有负面时算白跑一趟，计数而不是硬塞一个「什么都没清」。
				var purged: bool = false
				for hid_p in _alive_ids():
					lost_quirk = purge_negative(str(hid_p))
					if not lost_quirk.is_empty():
						purged = true
						break
				if not purged:
					stats["quirk_purge_failed"] = int(stats.get("quirk_purge_failed", 0)) + 1
			"scout":
				# 奇物帮你看了几步。和地牢侦察走同一个 revealed 计数，
				# 不另开一套「已知」状态——否则地图上会出现两种「知道」。
				var hops: int = maxi(0, int(d.get("hops", 0)))
				if hops > 0:
					revealed = mini(route.size(), revealed + hops)
					stats["scout_reveals"] = int(stats.get("scout_reveals", 0)) + 1
			"darkness":
				# 吹灭火把。这是奇物里唯一一种「主动变暗」的结果，
				# 而在暗处受压显著更重——它不是小惩罚。
				var dk: float = float(d.get("value", 0))
				light = clampf(light - dk * 10.0, 0.0, 100.0)
				stats["light_drained"] = float(stats.get("light_drained", 0.0)) + dk * 10.0
			"scripted":
				stats["curio_unsupported"] = int(stats.get("curio_unsupported", 0)) + 1
			_:
				pass

	if pressure > 0.0:
		for hid in _alive_ids():
			var s: Dictionary = state[hid]
			s["stress"] = clampf(float(s["stress"]) + pressure, 0.0, 200.0)
		stats["stress_added"] = float(stats["stress_added"]) + pressure * float(_alive_ids().size())
	elif pressure < 0.0:
		for hid2 in _alive_ids():
			var s2: Dictionary = state[hid2]
			s2["stress"] = clampf(float(s2["stress"]) + pressure, 0.0, 200.0)
	stats["curio_stress"] = float(stats.get("curio_stress", 0.0)) + pressure

	if not is_zero_approx(hp_lost):
		for hid3 in _alive_ids():
			var s3: Dictionary = state[hid3]
			s3["hp_ratio"] = clampf(float(s3["hp_ratio"]) - hp_lost, 0.02, 1.0)
		stats["curio_hp_lost"] = float(stats.get("curio_hp_lost", 0.0)) + hp_lost

	_emit({"t": "curio", "curio": cid, "item": str(out.get("item", "")),
		"outcome": outcome, "gold": got_gold, "heirlooms": got_heirlooms,
		"supplies": got_supplies, "stress": pressure, "hp_lost": hp_lost,
		"quirk": gained_quirk, "disease": gained_disease,
		"quirk_lost": lost_quirk, "quirk_target": quirk_target,
		"unsupported": out.get("unsupported", [])})
	return {"gold": got_gold, "heirlooms": got_heirlooms, "stress": pressure,
		"curio": cid, "outcome": outcome, "quirk": gained_quirk,
		"disease": gained_disease, "quirk_lost": lost_quirk,
		"quirk_target": quirk_target}


## 旧路径：一枚硬币。保留给历史基线与关掉真表时的对照。
func _resolve_curio_legacy() -> Dictionary:
	stats["curios"] = int(stats.get("curios", 0)) + 1
	var cc: Dictionary = loot_cfg.get("curio", {})
	var chance: float = float(cc.get("loot_chance", 0.65))
	var got_gold: int = 0
	var got_gems: Dictionary = {}
	var pressure: float = 0.0

	if _loot_rng != null and _loot_rng.chance(chance):
		var gr: Array = cc.get("gold", [12, 26])
		got_gold = _loot_rng.next_int_range(int(gr[0]), int(gr[mini(1, gr.size() - 1)]))
		loot_gold += got_gold
		_emit({"t": "loot", "gold": got_gold, "heirlooms": got_gems, "complete": false,
			"source": "curio"})
	else:
		pressure = float(cc.get("stress", 9.0))
		for hid in _alive_ids():
			var s: Dictionary = state[hid]
			s["stress"] = clampf(float(s["stress"]) + pressure, 0.0, 200.0)
		stats["stress_added"] = float(stats["stress_added"]) + pressure * float(_alive_ids().size())

	_emit({"t": "curio", "gold": got_gold, "stress": pressure})
	return {"gold": got_gold, "heirlooms": got_gems, "stress": pressure}


# ============================================================
# 补给
# ============================================================

## 背包里某样补给还有几个。shovel 走自己的字段，其余走 supplies。
## 分成两处是因为 shovel 在 M8 就是独立字段（障碍逻辑在用），
## 强行合并会牵动那条已经很稳的路径。这里做统一入口，调用方不必知道区别。
## 背包里这种东西有几件。
##
## 火把 / 口粮 / 铁锹有**独立字段**（点灯、饥饿、凿障碍各读各的），
## 其余六种在 `supplies` 字典里。这里统一入口，调用方不用知道区别——
## 之前 M13 让火把同时存在于两处，导致「点灯 4 支、奇物交互 1 支」，
## 同一个数字两个值。凡是「数量」都必须只从这里读。
func supply_count(id: String) -> int:
	match id:
		"shovel":
			return shovel
		"torch":
			return torch
		"food":
			return food
		_:
			return maxi(0, int(supplies.get(id, 0)))


func add_supply(id: String, n: int) -> void:
	if id.is_empty() or n <= 0:
		return
	match id:
		"shovel":
			shovel += n
		"torch":
			torch += n
		"food":
			food += n
		_:
			supplies[id] = int(supplies.get(id, 0)) + n


func take_supply(id: String) -> bool:
	if supply_count(id) <= 0:
		return false
	match id:
		"shovel":
			shovel -= 1
		"torch":
			torch -= 1
		"food":
			food -= 1
		_:
			supplies[id] = int(supplies.get(id, 0)) - 1
	return true


func supply_total() -> int:
	var n: int = shovel + torch + food
	for k in supplies.keys():
		n += maxi(0, int(supplies[k]))
	return n


func _heirloom_total() -> int:
	var n: int = 0
	for k in loot_heirlooms.keys():
		n += maxi(0, int(loot_heirlooms[k]))
	return n


## 宝石已经按 sell 价折进 loot_gold 了，这里只报「件数」用于展示。
func _gem_total() -> int:
	var n: int = 0
	for k in loot_gems.keys():
		n += maxi(0, int(loot_gems[k]))
	return n


# ============================================================
# 怪癖 / 疾病（M14）
# ============================================================
#
# 槽位：3 正 / 3 负 / 1 疾病。满了就不再获得——不是「替换掉一个旧的」。
# 替换会让玩家永远拿不到想要的组合（每次都是随机的），而 DD1 的体验是
# 「满了就得去医院清」，那是资源决策；随机替换等于把决策变成运气。
#
# 疾病过抗性：奇物给了 disease 结果，还要过英雄自己的 disease 抗性。
# 不过抗性的话，一个 30% 抗性的圣辉使和一个 10% 的麻风病人得病概率一样，
# 那这项属性在整局里从来没有被用上过。

## 灌入这趟出发前买的补给。必须在 `setup()` 之后调。
##
## 四种有独立字段（火把 `torch`、口粮 `food`、铁锹 `shovel`），
## 其余进 `supplies` 字典——这是 M3~M13 一层层长出来的结构，
## 不是设计，但改它要动十几处调用点，代价远大于这里多写三个 if。
##
## **传空字典等于不覆盖**：bench 走默认路径，基线必须逐位不变。
func set_start_supplies(pack: Dictionary) -> void:
	if pack.is_empty():
		return
	for k in pack.keys():
		var id: String = str(k)
		var n: int = maxi(0, int(pack[k]))
		match id:
			"torch":
				torch = n
			"shovel":
				shovel = n
			"food":
				food = n
			_:
				supplies[id] = n


## 这一趟实际带了什么。出发准备屏与结算屏都要能把它读回来。
func supply_pack() -> Dictionary:
	var out: Dictionary = {"torch": torch, "shovel": shovel, "food": food}
	for k in supplies.keys():
		var n: int = int(supplies[k])
		if n > 0:
			out[str(k)] = n
	return out


## 灌入这趟的装备。必须在 `setup()` 之后调（setup 会重建 state）。
## 同步写进 state，是为了让 `apply_party_state` 与 `capture_party_state`
## 走同一条路——只在 Battle 侧单独传一份，就会出现「战斗里生效、
## 打完快照里没有」这种 M14 踩过的坑。
func set_hero_trinkets(m: Dictionary) -> void:
	hero_trinkets = {}
	for hid in m.keys():
		var lst: Array = []
		for t in (m[hid] as Array):
			if not str(t).is_empty():
				lst.append(str(t))
		hero_trinkets[str(hid)] = lst
		if state.has(str(hid)):
			(state[str(hid)] as Dictionary)["trinkets"] = lst.duplicate()


## 某英雄现在有哪些怪癖。
func quirks_of(hid: String) -> Array:
	return (state.get(hid, {}) as Dictionary).get("quirks", [])


## 取「可写的」怪癖数组。
##
## 必须单独有这么一个入口，因为 `state` 会被 `finish_battle` 整份替换成
## `capture_party_state()` 的结果，而那份快照里没有 quirks 时，
## 新字典里就**根本没有这个键**——`d["quirks"].append()` 会直接抛
## "Invalid access to property or key"，而且抛在自动流程里会被静默吞掉。
## 症状是「奇物抽到了 quirk 分支、槽位也空着，但什么都没发生」。
func _quirk_list(hid: String) -> Array:
	if not state.has(hid):
		return []
	var row: Dictionary = state[hid]
	if not row.has("quirks"):
		row["quirks"] = []
	return row["quirks"]


## 从元层名册把怪癖灌进来。开局调一次。
## 传 {hero_id: [quirk_id, ...]}。
func seed_quirks(src: Dictionary) -> void:
	for hid in state.keys():
		var lst: Array = src.get(str(hid), [])
		var clean: Array = []
		for q in lst:
			if db != null and db.quirk_lib != null and db.quirk_lib.has(str(q)):
				clean.append(str(q))
		(state[hid] as Dictionary)["quirks"] = clean


## 当前占用的槽位。返回 {positive, negative, disease}。
func quirk_slots(hid: String) -> Dictionary:
	var out: Dictionary = {"positive": 0, "negative": 0, "disease": 0}
	if db == null or db.quirk_lib == null:
		return out
	for q in quirks_of(hid):
		var k: String = db.quirk_lib.slot_kind(str(q))
		out[k] = int(out.get(k, 0)) + 1
	return out


## 还能不能再装一个。槽位满、已有同名、互斥都算不能。
func can_take_quirk(hid: String, qid: String) -> bool:
	if db == null or db.quirk_lib == null or not db.quirk_lib.has(qid):
		return false
	if quirks_of(hid).has(qid):
		return false
	var kind: String = db.quirk_lib.slot_kind(qid)
	var slots: Dictionary = quirk_slots(hid)
	if int(slots.get(kind, 0)) >= db.quirk_lib.slot_cap(kind):
		return false
	# 互斥
	for owned in quirks_of(hid):
		var q: Dictionary = db.quirk_lib.get_quirk(qid)
		if (q.get("incompatible_quirks", []) as Array).has(str(owned)):
			return false
	return true


## 给某个英雄一个怪癖。返回实际获得的是哪个（失败返回 ""）。
##
## 失败要能区分原因，否则「碰了奇物但什么都没发生」在统计里看不出是
## 槽位满了、互斥、还是没有这个 id。三种都记到 stats。
func grant_quirk(hid: String, qid: String) -> String:
	if not state.has(hid):
		stats["quirk_refused_no_hero"] = int(stats.get("quirk_refused_no_hero", 0)) + 1
		return ""
	if not can_take_quirk(hid, qid):
		var reason: String = "unknown"
		if db == null or db.quirk_lib == null or not db.quirk_lib.has(qid):
			reason = "unknown_quirk"
		elif quirks_of(hid).has(qid):
			reason = "duplicate"
		else:
			reason = "slot_full"
		stats["quirk_refused_" + reason] = int(stats.get("quirk_refused_" + reason, 0)) + 1
		_emit({"t": "quirk_refused", "hero": hid, "quirk": qid, "reason": reason})
		return ""
	_quirk_list(hid).append(qid)
	stats["quirks_gained"] = int(stats.get("quirks_gained", 0)) + 1
	if db.quirk_lib.is_disease(qid):
		stats["diseases_contracted"] = int(stats.get("diseases_contracted", 0)) + 1
	_emit({"t": "quirk", "hero": hid, "quirk": qid,
		"disease": db.quirk_lib.is_disease(qid),
		"positive": db.quirk_lib.is_positive(qid)})
	return qid


## 指定极性抽一个并给出去。polarity: positive / negative。
## 随机池里没有合适的（全被互斥或已持有）时返回 ""。
func grant_random_quirk(hid: String, polarity: String, rng: DdRng) -> String:
	if db == null or db.quirk_lib == null:
		stats["quirk_refused_no_lib"] = int(stats.get("quirk_refused_no_lib", 0)) + 1
		return ""
	var qid: String = db.quirk_lib.pick(polarity, rng, quirks_of(hid), false)
	if qid.is_empty():
		stats["quirk_pool_empty"] = int(stats.get("quirk_pool_empty", 0)) + 1
		return ""
	return grant_quirk(hid, qid)


## 染病。具名就指定，`random` 就随机抽一个疾病。
##
## 过抗性：`p = 1 - disease_抗性`，用这条独立的 rng 流，不动主序列。
## 抗性判定关掉时直接算染上（对照用）。
func contract_disease(hid: String, which: String, rng: DdRng) -> String:
	if db == null or db.quirk_lib == null:
		stats["quirk_refused_no_lib"] = int(stats.get("quirk_refused_no_lib", 0)) + 1
		return ""
	var qid: String = which
	if which.is_empty() or which == "random":
		qid = db.quirk_lib.pick("any", rng, quirks_of(hid), true)
		if qid.is_empty():
			stats["quirk_pool_empty"] = int(stats.get("quirk_pool_empty", 0)) + 1
			return ""
	if not db.quirk_lib.is_disease(qid):
		return ""
	if disease_roll_enabled:
		var resist: float = 0.0
		var h: Dictionary = db.hero(hid)
		resist = float((h.get("resistances", {}) as Dictionary).get("disease", 0.0))
		var p: float = clampf(1.0 - resist, 0.05, 1.0)
		if not rng.chance(p):
			stats["disease_resisted"] = int(stats.get("disease_resisted", 0)) + 1
			_emit({"t": "disease_resisted", "hero": hid, "disease": qid})
			return ""
	return grant_quirk(hid, qid)


## 清掉一个负面怪癖（奇物的 purge）。疾病不清——那是 cure 的事。
func purge_negative(hid: String) -> String:
	if db == null or db.quirk_lib == null:
		return ""
	var lst: Array = _quirk_list(hid)
	for q in lst:
		if db.quirk_lib.slot_kind(str(q)) == "negative":
			lst.erase(q)
			stats["quirks_purged"] = int(stats.get("quirks_purged", 0)) + 1
			_emit({"t": "quirk_lost", "hero": hid, "quirk": q, "reason": "purge"})
			return str(q)
	stats["quirk_purge_failed"] = int(stats.get("quirk_purge_failed", 0)) + 1
	return ""


## 治病（cure）。没病就什么也不做。
func cure_disease(hid: String) -> String:
	if db == null or db.quirk_lib == null:
		return ""
	var lst: Array = _quirk_list(hid)
	for q in lst:
		if db.quirk_lib.is_disease(str(q)):
			lst.erase(q)
			stats["diseases_cured"] = int(stats.get("diseases_cured", 0)) + 1
			_emit({"t": "quirk_lost", "hero": hid, "quirk": q, "reason": "cure"})
			return str(q)
	return ""


## 随机挑一个活着的英雄。奇物给怪癖时落到谁头上是随机的——
## 这正是「带谁上路」的代价来源：全队轮着碰，负面怪癖迟早落到主力身上。
func random_alive_hero(rng: DdRng) -> String:
	var alive: Array = _alive_ids()
	if alive.is_empty():
		return ""
	return str(alive[rng.next_int(alive.size())])


## 怪癖带来的远征级修正（侦测概率、食物消耗）。
## 战斗内那部分由 Combatant 自己算，这里只管战斗外。
##
## 语境必须**逐英雄**建：`stress_above` 看的是这个人自己的压力，
## 用一份全队共用的 ctx 会让「压力过 50 才暴食」对所有人都按同一个值判。
## `stat_type` 属于「整队合计」的那几条：侦察、食物、偷袭率。
## 名字沿用 quirk_mod，但它现在同时算**怪癖与饰品**——两者在这一层
## 是同一个问题（「这个人身上带了什么，让这趟更好过一点」），
## 分成两个函数只会让每个调用点都得加两次。
func quirk_mod(stat_type: String) -> float:
	if db == null:
		return 0.0
	if not quirk_enabled and not trinket_enabled:
		return 0.0
	var total: float = 0.0
	for hid in _alive_ids():
		var s: Dictionary = state[hid]
		var ctx: Dictionary = {
			"dungeon": dungeon, "light": light, "round": 0,
			"hp_ratio": float(s.get("hp_ratio", 1.0)),
			"stress": float(s.get("stress", 0.0)),
			"enemy_types": [], "skill_type": "",
		}
		if quirk_enabled and db.quirk_lib != null:
			for b in db.quirk_lib.active_buffs(quirks_of(str(hid)), ctx):
				if str(b.get("stat_type", "")) == stat_type:
					total += float(b.get("amount", 0.0))
		if trinket_enabled and db.trinket_lib != null:
			var worn: Array = (s.get("trinkets", []) as Array)
			if not worn.is_empty():
				for b in db.trinket_lib.active_buffs(worn, ctx):
					if str(b.get("stat_type", "")) == stat_type:
						total += float(b.get("amount", 0.0))
	return total


## 全队合计的侦察加成。M6 的侦察概率直接加上它。
func scouting_bonus() -> float:
	return quirk_mod("scouting_chance")


## 食物消耗倍率。
##
## 数据里 `food_consumption_percent` 是**增量**：绦虫 +1.0 = 吃两倍
## （DD1 里 tapeworm 就是这个效果），所以按 1+mod 算。
##
## 但有一条 `stress_faster` 写的是 -1.0，照字面就是「一点粮食都不吃」——
## 那会让饥饿系统对这个人彻底失效。宁可保守：下限夹到 0.5，
## 让最极端的「省粮」也只省一半。这是对数据的一处刻意偏离，理由如上。
func food_cost_mult() -> float:
	return clampf(1.0 + quirk_mod("food_consumption_percent"), 0.5, 3.0)


# ============================================================
# 走廊内容：陷阱与障碍（M8）
# ============================================================
#
# 在此之前走廊里只有「战斗」和「饥饿」，而「往哪走」这个决策只能靠房间里的
# 奇物来区分——两条走廊在玩家眼里是一样的。陷阱和障碍补的正是这个缺口：
#
#   陷阱  看不见就踩上去挨一下；看见了可以绕，硬要走也有 +40% 解除
#         （rules.trap_scout_disarm_bonus，DD1 自己的数，不是我们发明的）
#   障碍  和「出发前带几把铁锹」直接挂钩，是补给预算的第三个去处
#
# 两者的前提都是「走进去之前能知道」。做不到这一点，它们就只是
# 每一步随机掉血的按钮，和「选路」没有半点关系。


## 队伍的陷阱抵抗：取全队最高的那位。
##
## 不取平均——玩家没法调整谁走前面，取平均等于四个人一起被绊；
## 取最高等于「让最警觉的那个去探路」，这才是合理的默认假设。
func trap_resist() -> float:
	var best: float = 0.0
	var ids: Array = _alive_ids()
	for hid in ids:
		var h: Dictionary = db.hero(str(hid))
		var r: Dictionary = h.get("resistances", {})
		best = maxf(best, float(r.get("trap", 0.0)))
	return best


## 躲开（或解除）陷阱的几率。
##
## 装备阶给一点点加成：更熟路的队伍更少踩坑，同时避免 0 阶队在高等级地牢
## 被压到「必踩」——那会把陷阱从机制变成税收。
func trap_avoid_chance(level: int, scouted: bool) -> float:
	var tc: Dictionary = cfg.get("trap", {})
	var ids: Array = _alive_ids()
	var gear_sum: float = 0.0
	for hid in ids:
		gear_sum += float(hero_gear.get(str(hid), 0))
	var n: float = maxf(1.0, float(ids.size()))
	var base: float = trap_resist() + 0.03 * (gear_sum / n)
	base -= db.rules.trap_difficulty(level)
	if scouted:
		base += db.rules.trap_scout_disarm_bonus
	return clampf(base, float(tc.get("min_avoid", 0.05)), float(tc.get("max_avoid", 0.85)))


func resolve_trap(step: Dictionary) -> Dictionary:
	stats["traps"] = int(stats["traps"]) + 1
	var level: int = int(step.get("level", 1))
	var scouted: bool = bool(step.get("scouted", false))
	var chance: float = trap_avoid_chance(level, scouted)
	var dodged: bool = _trap_rng != null and _trap_rng.chance(chance)

	if dodged:
		stats["traps_dodged"] = int(stats["traps_dodged"]) + 1
		_emit({"t": "trap", "dodged": true, "chance": chance, "level": level,
			"scouted": scouted})
		return {"dodged": true, "chance": chance, "scouted": scouted}

	var tc: Dictionary = cfg.get("trap", {})
	var dmg_ratio: float = float(tc.get("damage_ratio", 0.10))
	var stress: float = float(tc.get("stress", 7.0))
	var ids: Array = _alive_ids()
	for hid in ids:
		var s: Dictionary = state[hid]
		s["stress"] = clampf(float(s["stress"]) + stress, 0.0, 200.0)
		stats["stress_added"] = float(stats["stress_added"]) + stress
		var max_hp: int = _max_hp(hid)
		var dmg: int = maxi(1, int(round(float(max_hp) * dmg_ratio)))
		_apply_out_of_battle_damage(hid, s, dmg, max_hp, "trap")
	_emit({"t": "trap", "dodged": false, "chance": chance, "level": level,
		"scouted": scouted, "ratio": dmg_ratio, "stress": stress})
	return {"dodged": false, "chance": chance, "scouted": scouted,
		"ratio": dmg_ratio, "stress": stress}


## 障碍：有铁锹就凿开（消耗一把），没有就用手扒——全队掉血 + 加压。
##
## 这条是「出发前带几把铁锹」的直接兑现。没有它，补给预算里只有火把和口粮
## 两个按钮，而这两个都只影响「挨打多少」；铁锹影响的是「能不能不挨打」。
func resolve_obstacle() -> Dictionary:
	stats["obstacles"] = int(stats["obstacles"]) + 1
	var oc: Dictionary = cfg.get("obstacle", {})
	var uses: int = maxi(1, int(oc.get("shovel_uses", 1)))
	if shovel >= uses:
		shovel -= uses
		stats["obstacles_cleared"] = int(stats["obstacles_cleared"]) + 1
		_emit({"t": "obstacle", "cleared": true, "shovel": shovel})
		return {"cleared": true, "shovel": shovel}

	var dmg_ratio: float = float(oc.get("damage_ratio", 0.09))
	var stress: float = float(oc.get("stress", 5.0))
	var ids: Array = _alive_ids()
	for hid in ids:
		var s: Dictionary = state[hid]
		s["stress"] = clampf(float(s["stress"]) + stress, 0.0, 200.0)
		stats["stress_added"] = float(stats["stress_added"]) + stress
		var max_hp: int = _max_hp(hid)
		var dmg: int = maxi(1, int(round(float(max_hp) * dmg_ratio)))
		_apply_out_of_battle_damage(hid, s, dmg, max_hp, "obstacle")
	_emit({"t": "obstacle", "cleared": false, "shovel": shovel,
		"ratio": dmg_ratio, "stress": stress})
	return {"cleared": false, "shovel": shovel, "ratio": dmg_ratio, "stress": stress}


# ============================================================
# 战前情报（M6）
# ============================================================
#
# DD1 里光照的第三个作用就是侦察（rules.darkness 的 player_scouting_increase：
# 明亮 +15%、微光 +7.5%）。在此之前这条数据一直是解析出来但没人用——
# 光照只影响挨打和受压，玩家自然算得出「省火把只多挨一点」。
#
# 现在它决定你能提前看见多远：看见下一场是 4 只怪还是 2 只，
# 「先休整还是先冲」「要不要点这根火把」才从赌博变成决策。

## 当前侦察成功率。界面上要显示，否则玩家不知道「点亮」到底买到了什么。
##
## 「废墟探索者 +10% 侦察」这类怪癖加在这一层：它们本来就是
## 「在这座地牢里更会找路」，强行塞进战斗数值只会变成命中率。
func scout_chance() -> float:
	var sc: Dictionary = cfg.get("scouting", {})
	return clampf(float(sc.get("base_chance", 0.5))
		+ float(light_mods().get("player_scouting", 0.0))
		+ scouting_bonus(), 0.0, 1.0)


func _try_scout() -> void:
	if revealed >= route.size():
		return
	if _scout_rng == null:
		return
	if _scout_rng.chance(scout_chance()):
		revealed += 1
		stats["scout_reveals"] = int(stats["scout_reveals"]) + 1
		_emit({"t": "scout", "revealed": revealed, "total": route.size(),
			"chance": scout_chance()})


## 第 i 个节点是否已知。未知不等于「不存在」——它可能是一场硬仗。
func is_revealed(i: int) -> bool:
	return i < revealed


## 一场遭遇的总血量，给情报面板显示用。
## 只显示「几只 + 总共多少血」，不显示具体是什么怪：
## 知道「4 只、约 60 血」足够决定要不要休整，知道名字只是提前抄答案。
func step_enemy_hp(step: Dictionary) -> int:
	var total: int = 0
	for m in step.get("monsters", []):
		total += int(db.monster_base(str(m)).get("hp_max", 0))
	return total


## 原语 2：装配一场战斗，但不打完。界面拿到 Battle 后自己逐步驱动。
func start_battle(step: Dictionary) -> Battle:
	var alive: Array = _alive_ids()
	if alive.is_empty():
		_end("wipe")
		return null

	var b := Battle.new()
	var ok: bool = b.setup(alive, step.get("monsters", []),
		rng.next_int_range(1, 1 << 30), int(step.get("gear", 0)), int(step.get("skill", 0)),
		hero_gear, hero_skill, hero_loadout)
	if not ok:
		push_warning("Expedition: 装配失败，跳过该步 %s" % str(step.get("monsters", [])))
		return null
	# 测量用的透传开关：远征层不给它开口，「守护对一整趟路有没有用」
	# 就只能靠换职业来猜，而换职业变的东西远不止守护。
	b.guard_enabled = guard_enabled
	b.riposte_enabled = riposte_enabled
	b.move_value_enabled = move_value_enabled
	b.move_resist_enabled = move_resist_enabled
	b.summon_enabled = summon_enabled
	b.summon_value_enabled = summon_value_enabled
	b.summon_default_limit_enabled = summon_default_limit_enabled
	b.quirk_enabled = quirk_enabled
	b.trinket_enabled = trinket_enabled

	var m: Dictionary = light_mods()
	b.set_environment({
		"stress_damage": float(m.get("stress_damage", 0.0)),
		"monster_dmg": float(m.get("monster_dmg", 0.0)),
		"monster_acc": float(m.get("monster_acc", 0.0)),
		"monster_crit": float(m.get("monster_crit", 0.0)),
		"player_dodge": float(m.get("player_dodge", 0.0)),
		"player_crit": float(m.get("player_crit", 0.0)),
		# 怪癖条件要判「这座地牢」「现在多亮」——两样都不在战斗内部
		"dungeon": dungeon,
		"light": light,
	})
	# 等级惩罚的受压倍率（M29）：整趟固定，所以在这里灌一次。
	# 不能塞进 set_environment——那个每场都会整个覆盖 stress_in_mult。
	if not join_stress_mult.is_empty():
		for u in b.party:
			u.join_stress_mult = float(join_stress_mult.get(str(u.def_id), 1.0))
	b.surprised = _roll_surprise(m)
	b.apply_party_state(state)
	b.heal_charges = heal_charges

	var ac: Dictionary = cfg.get("affliction", {})
	b.affliction_refuse_chance = float(ac.get("refuse_chance", 0.15))
	b.affliction_aura_stress = float(ac.get("aura_stress", 2.0))
	b.virtue_relief = float(ac.get("virtue_relief", 1.0))

	active_battle = b
	active_index = int(stats["battles"])
	active_is_boss = bool(step.get("boss", false))
	active_source = str(step.get("source", ""))
	if active_is_boss:
		stats["boss_fought"] = true
	_active_uids = {}
	for u in b.party:
		_active_uids[u.uid] = u.def_id

	_emit({"t": "battle_start", "index": active_index, "monsters": step.get("monsters", []),
		"light": light, "surprised": b.surprised, "gear": int(step.get("gear", 0))})
	return b


## 原语 3：战斗收尾——继承状态、记统计、判团灭。
func finish_battle(b: Battle) -> void:
	if b == null:
		return
	heal_charges = b.heal_charges
	# 合并而不是替换：capture_party_state 只包含「这一场参战的人」，
	# 前面几场就阵亡的队友不在里面。整份替换会把他们的记录抹掉，
	# 于是阵亡者在结算时又变回「活着」——这个 bug 只在多人先后死亡时出现，
	# 单场测试永远抓不到。
	var fresh: Dictionary = b.capture_party_state()
	for k in fresh.keys():
		# 怪癖不在 capture 的语义里（它拍的是「这一场打完的血量压力」），
		# 但 state 是整份替换的——不补回来的话，打完第一场怪癖就全没了。
		# 症状极隐蔽：战斗内明明生效（战斗开始时读到了），
		# 战斗后突然清零，而且只有「打满两场以上」才看得出来。
		var row: Dictionary = fresh[k]
		var old_q: Array = (state.get(k, {}) as Dictionary).get("quirks", [])
		if (row.get("quirks", []) as Array).is_empty() and not old_q.is_empty():
			row["quirks"] = old_q.duplicate()
		state[k] = row
	stats["battles"] = active_index + 1
	stats["rounds"] = int(stats["rounds"]) + b.round_index
	# 清剿进度（M32）：只数**房间**战斗，而且**打赢或脱战都算清过**。
	# 打输就没机会继续走，所以那条路不需要在这里处理；
	# 僵持（回合上限）算「没清掉」——那正是清剿任务要罚的情形。
	if map_mode and (active_source == "room" or active_source == "boss") \
			and not b.stalemate:
		stats["quest_battles_cleared"] = int(stats.get("quest_battles_cleared", 0)) + 1
	_emit({"t": "battle_end", "index": active_index, "winner": b.winner(),
		"rounds": b.round_index})
	# 只有打赢才有战利品。撤退/团灭的路上捡到的东西照样算——
	# 不然「打不过就跑」会变成零收益，撤退按钮永远没人点。
	if str(b.winner()) == "party":
		# 首领击杀（M20）：只有打赢才算。撤退/僵持都不算，
		# 否则「跑到终点打一下就跑」也能拿任务奖励。
		if active_is_boss:
			stats["boss_killed"] = true
		# 逐只怪的 loot 要靠敌人列表，所以必须在这里传：
		# active_battle 下一行就被清空了。
		_roll_battle_loot(b.enemies)
	elif b.stalemate:
		# 僵持按「脱离接触」处理：没掉落，全队加压。
		# 不给惩罚的话，遇到打不过的阵容可以故意拖到回合上限白跑一场。
		stats["stalemates"] = int(stats.get("stalemates", 0)) + 1
		var pen: float = float(db.rules.retreat_stress) if db != null else 20.0
		for hid in _alive_ids():
			var srow: Dictionary = state[hid]
			srow["stress"] = clampf(float(srow["stress"]) + pen, 0.0, 200.0)
		stats["stress_added"] = float(stats.get("stress_added", 0.0)) + pen * float(_alive_ids().size())
	active_battle = null
	if _alive_ids().is_empty():
		_end("wipe")


## 原语 4：一步之后的收尾。auto_camp=false 时把「休整」留给玩家决定。
func after_step(auto_camp: bool = true) -> void:
	if ended:
		return
	if auto_camp:
		_maybe_camp()
	_update_low_water()
	if _alive_ids().is_empty():
		_end("wipe")
	elif not map_mode and step_index >= route.size():
		# 跑完全部步骤却没结束，说明是直接调 run_step 的外部循环——
		# 不在这里收尾，调用方会一路越界读下去。
		# 图模式不适用：图上没有「走完」，完成只能靠玩家在目标房间选择离开。
		_end("complete")


## 把一场战斗自动打完（bench / 自动模式用）
func _play_out(b: Battle) -> void:
	while not b.is_over() and b.round_index < Battle.MAX_ROUNDS:
		for e in b.run_round():
			_ingest_active(e)
	finish_battle(b)


func retreat() -> void:
	if ended:
		return
	# 撤退不是免费的：全员加压（rules.combat_retreat_stress = 20），
	# 否则「打不过就跑」会变成无损重置，整个资源层立刻失去意义。
	for hid in _alive_ids():
		var s: Dictionary = state[hid]
		s["stress"] = clampf(float(s["stress"]) + db.rules.retreat_stress, 0.0, 200.0)
		stats["stress_added"] = float(stats["stress_added"]) + db.rules.retreat_stress
	_emit({"t": "retreat", "step": step_index})
	_end("retreat")


func _end(reason: String) -> void:
	if ended:
		return
	ended = true
	# 任务判据（M20 / M32）。
	#
	# 原来这里只有一条写死的首领特例：跑到终点 → 打输了 → 活着跑出来
	# 也会走 complete，既拿完成奖励，结算屏还写「走出地牢」——
	# 和任务目标直接矛盾。M32 把这条推广成「凡是有目标的任务都要过判据」：
	# 清剿没清完就走，同样只能是 incomplete。
	#
	# 路线模式（bench / 旧基线）不参与：那里根本没有房间，`at_goal` 恒为 false，
	# 一开判据就把 M3 以来所有 bench 结果变成「未完成」。
	# 首领任务例外——它在路线模式下也成立（终点就是最后一格），
	# 所以照旧无条件判。
	if reason == "complete" and not quest_goal.is_empty():
		var gated: bool = map_mode or str(quest_goal.get("kind", "")) == QuestGoal.KIND_BOSS
		if gated and not quest_met():
			reason = "incomplete"
	end_reason = reason
	if reason == "complete":
		_grant_complete_loot()
	_emit({"t": "exp_end", "reason": reason, "step": step_index,
		"light": light, "food": food, "torch": torch,
		"gold": loot_gold, "heirlooms": loot_heirlooms.duplicate()})


# ============================================================
# 战利品
# ============================================================
#
# 只负责「这趟捡到了什么」。「金币能买什么」是 Campaign 的事——
# 分开放，才能单独测「掉落曲线」而不牵动城镇经济。

## 战斗胜利后的战利品。
##
## 真表版本不再是「每场 9–17 金」这种拍脑袋常数，而是**逐只怪抽它自己的 loot**：
## monsters.json 里 254 只怪都带 {code, count}——100 只是 A×1、22 只 A×2、
## 9 只 C×1、10 只 T×2、17 只 NONE（不掉）。于是「这波怪值多少」变成了
## 遭遇表与怪物表的自然结果，换一层地牢就会变，不用手调。
func _roll_battle_loot(enemies: Array = []) -> void:
	if loot_cfg.is_empty() and not loot_table_enabled:
		return
	if loot_table_enabled and db != null and db.loot_tables != null and db.loot_tables.is_loaded():
		_roll_battle_loot_table(enemies)
		return
	_roll_battle_loot_legacy()


func _roll_battle_loot_table(enemies: Array) -> void:
	var agg: Dictionary = LootTables.empty_result()
	var used: int = 0
	for c in enemies:
		if not (c is Combatant):
			continue
		var m: Dictionary = db.monster((c as Combatant).def_id)
		if m.is_empty():
			continue
		var l: Dictionary = m.get("loot", {})
		if l.is_empty():
			continue
		var code: String = str(l.get("code", ""))
		var cnt_var: Variant = l.get("count", 0)
		var cnt: int = int(cnt_var) if cnt_var != null else 0
		# NONE 是「这怪不掉东西」的显式写法，不是缺数据
		if code.is_empty() or code == "NONE" or cnt <= 0:
			continue
		if not db.loot_tables.has_table(code):
			continue
		db.loot_tables.draw_n(code, cnt, _loot_rng, agg)
		used += 1
	if used <= 0:
		return
	var got: Dictionary = _apply_loot_result(agg)
	_emit({"t": "loot", "gold": int(got["gold"]), "heirlooms": got["heirlooms"],
		"supplies": got["supplies"], "gems": got["gems"], "complete": false,
		"source": "battle", "monsters": used, "draws": int(agg["draws"])})


## 把一次抽取结果落到远征账面。
## 宝石直接按 sell 价折进金币——本项目没有商店库存，宝石除了卖钱没有别的用途，
## 单开一个「宝石袋」只会让结算屏多一行没人看的东西。
func _apply_loot_result(agg: Dictionary) -> Dictionary:
	var gold_now: int = int(agg.get("gold", 0))
	for id in (agg.get("gems", {}) as Dictionary).keys():
		var def: Dictionary = db.loot_tables.item_defs.get(str(id), {})
		gold_now += int(def.get("sell_gold_value", 0)) * int(agg["gems"][id])
		loot_gems[str(id)] = int(loot_gems.get(str(id), 0)) + int(agg["gems"][id])

	var gained: Dictionary = {}
	for k in (agg.get("heirlooms", {}) as Dictionary).keys():
		var n: int = int(agg["heirlooms"][k])
		if n <= 0:
			continue
		loot_heirlooms[str(k)] = int(loot_heirlooms.get(str(k), 0)) + n
		gained[str(k)] = int(gained.get(str(k), 0)) + n

	var sup: Dictionary = {}
	for k in (agg.get("supplies", {}) as Dictionary).keys():
		var n2: int = int(agg["supplies"][k])
		if n2 <= 0:
			continue
		add_supply(str(k), n2)
		sup[str(k)] = n2

	var prov: int = int(agg.get("provisions", 0))
	if prov > 0:
		food += prov
	loot_trinkets += (agg.get("trinkets", []) as Array).size()
	for tid in (agg.get("trinket_ids", []) as Array):
		var s_id: String = str(tid)
		if not s_id.is_empty() and not loot_trinket_ids.has(s_id):
			loot_trinket_ids.append(s_id)

	loot_gold += gold_now
	return {"gold": gold_now, "heirlooms": gained, "supplies": sup,
		"gems": (agg.get("gems", {}) as Dictionary).duplicate()}


## 旧路径：M5 的手写常数。保留是为了复现历史基线，不是因为它对。
func _roll_battle_loot_legacy() -> void:
	if loot_cfg.is_empty():
		return
	var br: Array = loot_cfg.get("battle_gold", [9, 17])
	var g: int = _loot_rng.next_int_range(int(br[0]), int(br[mini(1, br.size() - 1)]))
	loot_gold += g
	var gained: Dictionary = {}
	if _loot_rng.chance(float(loot_cfg.get("battle_heirloom_chance", 0.30))):
		var k: String = _pick_heirloom()
		if not k.is_empty():
			loot_heirlooms[k] = int(loot_heirlooms.get(k, 0)) + 1
			gained[k] = 1
	_emit({"t": "loot", "gold": g, "heirlooms": gained, "complete": false})


func _grant_complete_loot() -> void:
	if loot_cfg.is_empty():
		return
	var g: int = int(loot_cfg.get("complete_gold", 45)) \
		+ int(loot_cfg.get("complete_gold_per_battle", 22)) * int(stats["battles"])
	var cr: Array = loot_cfg.get("complete_heirlooms", [1, 3])
	var n: int = _loot_rng.next_int_range(int(cr[0]), int(cr[mini(1, cr.size() - 1)]))
	var gained: Dictionary = {}
	for i in n:
		var k: String = _pick_heirloom()
		if k.is_empty():
			break
		loot_heirlooms[k] = int(loot_heirlooms.get(k, 0)) + 1
		gained[k] = int(gained.get(k, 0)) + 1
	loot_gold += g
	_emit({"t": "loot", "gold": g, "heirlooms": gained, "complete": true})


func _pick_heirloom() -> String:
	var names: Array = loot_heirlooms.keys()
	if names.is_empty():
		return ""
	return str(names[_loot_rng.next_int_range(0, names.size() - 1)])


# ============================================================
# 光照
# ============================================================

func _consume_light() -> void:
	var lc: Dictionary = cfg.get("light", {})
	var loss: float = float(lc.get("loss_per_step", 10.0))
	light = maxf(0.0, light - loss)
	stats["min_light"] = minf(float(stats["min_light"]), light)

	# 自动用火把：低于阈值就点一根。做成自动策略而不是玩家操作，
	# 是为了让对照实验只差「资源参数」这一个变量——否则测出来的是 AI 策略差异。
	var threshold: float = float(lc.get("auto_torch_below", 50.0))
	while torch > 0 and light < threshold:
		use_torch()

	_emit({"t": "light", "light": light, "tier": ExpeditionCfg.light_tier_name(light)})


## 点一根火把。界面上是一个按钮，自动模式里由阈值触发——同一套逻辑。
func use_torch() -> bool:
	if torch <= 0:
		return false
	var lc: Dictionary = cfg.get("light", {})
	torch -= 1
	light = minf(100.0, light + float(lc.get("torch_gain", 25.0)))
	stats["torches_used"] = int(stats["torches_used"]) + 1
	_emit({"t": "torch_used", "left": torch, "light": light})
	return true


func light_mods() -> Dictionary:
	return ExpeditionCfg.light_modifier(db.rules.darkness, light)


## 走廊里走路本身也会加压（rules.hallway_stress：每格 30% 概率、2 点压力）。
## 这不是可有可无的点缀：没有它，光照只影响「怪物伤害」，
## 而玩家一眼就能看出「省火把只多挨一点打」，于是火把永远省着不用。
## 有了它，省火把 = 持续加压 = 崩溃风险，光照才成为一个真正的选择。
func _hallway_stress() -> void:
	var hs: Dictionary = db.rules.hallway_stress
	if hs.is_empty():
		return
	var tiles: int = _tiles_per_step()
	var chance: float = float(hs.get("hallway_per_tile_stress_damage_chance_fwd", 0.3))
	var amount: float = float(hs.get("hallway_per_tile_stress_damage_fwd", 2.0))
	if chance <= 0.0 or amount <= 0.0:
		return
	var m: Dictionary = light_mods()
	amount *= (1.0 + float(m.get("stress_damage", 0.0)))
	var alive: Array = _alive_ids()
	if alive.is_empty():
		return
	for i in tiles:
		if not rng.chance(chance):
			continue
		var hid: String = alive[rng.next_int_range(0, alive.size() - 1)]
		var s: Dictionary = state[hid]
		s["stress"] = clampf(float(s["stress"]) + amount, 0.0, 200.0)
		stats["stress_added"] = float(stats["stress_added"]) + amount
		_emit({"t": "hallway_stress", "hero": hid, "amount": amount})


## 一步走多少格：取地图参数里的 spacing（走廊间距），拿不到就按 4 格算。
func _tiles_per_step() -> int:
	var map: Dictionary = db.map_for(dungeon, size_name)
	var sp: int = int(map.get("spacing", 4))
	return clampi(sp, 1, 10)


# ============================================================
# 遭遇
# ============================================================

## 惊袭：数据给的是走廊/房间的基准概率，光照再叠一层
## （明亮时玩家更容易先发现怪物，无光时反过来）。
func _roll_surprise(m: Dictionary) -> String:
	var party_chance: float = clampf(db.rules.surprise_corridor_party
		+ float(m.get("heroes_surprised", 0.0)), 0.0, 0.65)
	var monster_chance: float = clampf(db.rules.surprise_corridor_monsters
		+ float(m.get("monsters_surprised", 0.0)), 0.0, 0.65)
	var hero_surprised: bool = rng.chance(party_chance)
	var monster_surprised: bool = rng.chance(monster_chance)
	if hero_surprised and not monster_surprised:
		return Combatant.SIDE_PARTY
	if monster_surprised and not hero_surprised:
		return Combatant.SIDE_ENEMY
	return ""


# ============================================================
# 口粮
# ============================================================

func resolve_hunger() -> Dictionary:
	return _resolve_hunger()


func _resolve_hunger() -> Dictionary:
	stats["hunger_checks"] = int(stats["hunger_checks"]) + 1
	var fc: Dictionary = cfg.get("food", {})
	var need: int = maxi(1, int(fc.get("per_hunger", 1)))
	# 暴食类怪癖（stress_above 时的 food_consumption_percent）在这里生效。
	# 食物是整数，1.4 倍直接四舍五入永远等于 1——等于这条怪癖不存在。
	# 所以攒一个小数债：每次多出的 0.4 记在账上，攒够一整份才真的多吃一个。
	# 1.4 倍的效果于是变成「每五次饥饿多吃一次」，这才是可感的。
	_food_debt += float(need) * (food_cost_mult() - 1.0)
	if _food_debt >= 1.0:
		var extra: int = int(floor(_food_debt))
		need += extra
		_food_debt -= float(extra)

	if food >= need:
		food -= need
		# 吃到口粮回一点血（rules.hallway_hunger_HPrestore = 5%）
		var restore: float = db.rules.hunger_hp_restore
		for hid in _alive_ids():
			var s: Dictionary = state[hid]
			if bool(s.get("at_deaths_door", false)):
				continue
			var max_hp: int = _max_hp(hid)
			var gain: int = maxi(1, int(round(float(max_hp) * restore)))
			s["hp_ratio"] = minf(1.0, float(s["hp_ratio"]) + float(gain) / float(maxi(max_hp, 1)))
		_emit({"t": "hunger", "fed": true, "food": food})
		return {"kind": "hunger", "fed": true}

	# 断粮：全员加压 + 掉血。掉血按比例而不是固定值——
	# 否则对高血量英雄是挠痒，对低血量英雄是处决。
	stats["hunger_unfed"] = int(stats["hunger_unfed"]) + 1
	var stress: float = float(fc.get("starve_stress", 15.0))
	var dmg_ratio: float = float(fc.get("starve_dmg_ratio", 0.2))
	for hid in _alive_ids():
		var s2: Dictionary = state[hid]
		s2["stress"] = clampf(float(s2["stress"]) + stress, 0.0, 200.0)
		stats["stress_added"] = float(stats["stress_added"]) + stress
		var max_hp2: int = _max_hp(hid)
		var dmg: int = maxi(1, int(round(float(max_hp2) * dmg_ratio)))
		_apply_out_of_battle_damage(hid, s2, dmg, max_hp2)
	_emit({"t": "hunger", "fed": false, "food": food})
	return {"kind": "hunger", "fed": false}


## 战斗外的伤害（断粮、事件）。死门上再受伤要过死击抗性，
## 不能直接扣血——否则「断粮」等于必定处决所有死门英雄。
func _apply_out_of_battle_damage(hid: String, s: Dictionary, dmg: int, max_hp: int,
		cause: String = "starve") -> void:
	if bool(s.get("at_deaths_door", false)):
		if rng.chance(1.0 - _deathblow_resist(hid)):
			s["dead"] = true
			s["hp_ratio"] = 0.0
			stats["hero_deaths"] = int(stats["hero_deaths"]) + 1
			_emit({"t": "death", "hero": hid, "cause": cause})
		return
	var ratio: float = float(s["hp_ratio"]) - float(dmg) / float(maxi(max_hp, 1))
	if ratio <= 0.0:
		s["hp_ratio"] = 0.0
		s["at_deaths_door"] = true
		stats["dd_entries"] = int(stats["dd_entries"]) + 1
		_emit({"t": "deaths_door", "hero": hid, "cause": cause})
	else:
		s["hp_ratio"] = ratio


# ============================================================
# 休整
# ============================================================

func can_camp() -> bool:
	var cc: Dictionary = cfg.get("camp", {})
	return (not ended) and camps_left > 0 and food >= int(cc.get("food_cost", 2))


## 休整策略：血量见底或压力逼近崩溃时才用。
## 这是 AI 策略而非规则——真实玩家会更晚才休整，所以这里的数字偏保守，
## 测出来的危险度是「乐观下界」。
func _maybe_camp() -> void:
	var cc: Dictionary = cfg.get("camp", {})
	if not can_camp():
		return
	var hp_sum: float = 0.0
	var st_max: float = 0.0
	var n: int = 0
	for hid in _alive_ids():
		var s: Dictionary = state[hid]
		hp_sum += float(s["hp_ratio"])
		st_max = maxf(st_max, float(s["stress"]))
		n += 1
	if n == 0:
		return
	var hp_avg: float = hp_sum / float(n)
	if hp_avg > 0.55 and st_max < 65.0:
		return
	camp()


func camp() -> bool:
	if not can_camp():
		return false
	var cc: Dictionary = cfg.get("camp", {})
	camps_left -= 1
	# 暴食类怪癖对营地口粮同样生效。营地的消耗是一次性的，
	# 不攒小数债，直接按倍率四舍五入（最少 1 份）。
	var camp_cost: int = maxi(1, int(round(float(cc.get("food_cost", 2)) * food_cost_mult())))
	food -= camp_cost
	stats["camp_used"] = int(stats["camp_used"]) + 1

	var heal_ratio: float = float(cc.get("heal_ratio", 0.3))
	var relief: float = float(cc.get("stress_relief", 40.0))
	for hid in _alive_ids():
		var s: Dictionary = state[hid]
		s["stress"] = clampf(float(s["stress"]) - relief, 0.0, 200.0)
		if bool(s.get("at_deaths_door", false)):
			# 营地能把死门上的英雄救回来——这是休整最重要的用途
			s["at_deaths_door"] = false
			s["recovering"] = true
			s["hp_ratio"] = heal_ratio
		else:
			s["hp_ratio"] = minf(1.0, float(s["hp_ratio"]) + heal_ratio)
	light = minf(100.0, light + float(cc.get("light_gain", 60.0)))
	_emit({"t": "camp", "camps_left": camps_left, "food": food, "light": light})

	# 营地会被偷袭。数据里 ambush_camping_base_chance = 0.33，
	# 这意味着「休整」不是稳赚——它本身是一个风险决策。
	var amb: float = float(cc.get("ambush_chance", 0.0))
	if amb > 0.0 and rng.chance(amb) and step_index < route.size():
		stats["camp_ambush"] = int(stats["camp_ambush"]) + 1
		_emit({"t": "camp_ambush"})
		var enc: Dictionary = _pick_ambush_encounter()
		if not enc.is_empty():
			var ab: Battle = start_battle(enc)
			if ab != null:
				_play_out(ab)
	return true


func _pick_ambush_encounter() -> Dictionary:
	for i in range(step_index, route.size()):
		var s: Dictionary = route[i]
		if str(s.get("kind", "")) == "battle":
			return s
	return {}


# ============================================================
# 事件归属与统计
# ============================================================

func _emit(e: Dictionary) -> void:
	events.append(e)


## 战斗事件不进 events（120 次远征 × 7 场 × 上百条会撑爆内存），
## 只把要用的量折成计数。
func _ingest_active(e: Dictionary) -> void:
	_ingest(e, active_index, _active_uids)


func _ingest(e: Dictionary, battle_index: int, uid_to_id: Dictionary = {}) -> void:
	match str(e.get("t", "")):
		"attack":
			stats["attacks"] = int(stats["attacks"]) + 1
			stats["hits"] = int(stats["hits"]) + 1
			var dmg: float = float(e.get("damage", 0))
			var gross: float = float(e.get("gross", dmg))
			stats["damage_dealt"] = float(stats["damage_dealt"]) + dmg
			stats["gross_dealt"] = float(stats["gross_dealt"]) + gross
			stats["overkill"] = float(stats["overkill"]) + maxf(0.0, gross - dmg)
			if bool(e.get("crit", false)):
				stats["crits"] = int(stats["crits"]) + 1
		"miss":
			stats["attacks"] = int(stats["attacks"]) + 1
		"heal":
			if bool(e.get("blocked", false)):
				stats["heals_blocked"] = int(stats["heals_blocked"]) + 1
			else:
				stats["heals"] = int(stats["heals"]) + 1
		"affliction":
			stats["afflictions"] = int(stats["afflictions"]) + 1
			_emit({"t": "affliction", "battle": battle_index, "kind": e.get("kind", ""),
				"stress": float(e.get("stress", 100.0)),
				"hero": str(uid_to_id.get(e.get("target", -1), ""))})
		"virtue":
			stats["virtues"] = int(stats["virtues"]) + 1
			_emit({"t": "virtue", "battle": battle_index, "kind": e.get("kind", ""),
				"hero": str(uid_to_id.get(e.get("target", -1), ""))})
		"heart_attack":
			stats["heart_attacks"] = int(stats["heart_attacks"]) + 1
			_emit({"t": "heart_attack", "battle": battle_index,
				"hero": str(uid_to_id.get(e.get("target", -1), ""))})
		"deaths_door":
			stats["dd_entries"] = int(stats["dd_entries"]) + 1
			_emit({"t": "deaths_door", "battle": battle_index,
				"hero": str(uid_to_id.get(e.get("actor", -1), "")),
				"cause": str(e.get("cause", "battle"))})
		"act_out":
			stats["act_outs"] = int(stats["act_outs"]) + 1
			_emit({"t": "act_out", "battle": battle_index,
				"hero": str(uid_to_id.get(e.get("actor", -1), "")),
				"kind": str(e.get("kind", ""))})
		"stress":
			stats["stress_added"] = float(stats["stress_added"]) + maxf(0.0, float(e.get("delta", 0.0)))
		"death":
			# 只数英雄的死亡。怪物的死亡事件同样叫 "death"，
			# 不区分阵营会得到「每趟死 14 个人」这种一眼假的数据。
			if bool(e.get("hero", false)):
				stats["hero_deaths"] = int(stats["hero_deaths"]) + 1
				_emit({"t": "death", "battle": battle_index,
					"hero": str(uid_to_id.get(e.get("actor", -1), "")),
					"cause": str(e.get("cause", "battle"))})


# ============================================================
# 小工具
# ============================================================

func _alive_ids() -> Array:
	var out: Array = []
	for hid in hero_ids:
		var s: Dictionary = state.get(hid, {})
		if s.is_empty() or bool(s.get("dead", false)):
			continue
		out.append(hid)
	return out


## 这一趟里该英雄是否已经阵亡（跨多场累计，不只是最后一场）。
func is_dead(hid: String) -> bool:
	return bool((state.get(hid, {}) as Dictionary).get("dead", false))


func _max_hp(hid: String) -> int:
	var b: Dictionary = db.hero_base(hid, _gear_of_current_step())
	return int(b.get("hp_max", 1))


## 装备阶随路线里的步骤走：同一趟远征装备阶不变，所以取上一步的即可。
func _gear_of_current_step() -> int:
	for i in range(mini(step_index, route.size()) - 1, -1, -1):
		var s: Dictionary = route[i]
		if s.has("gear"):
			return int(s["gear"])
	return 0


func _deathblow_resist(hid: String) -> float:
	var h: Dictionary = db.hero(hid)
	var r: Dictionary = h.get("resistances", {})
	return clampf(float(r.get("death_blow", 0.67)), 0.0, 1.0)


func _update_low_water() -> void:
	for hid in _alive_ids():
		var s: Dictionary = state[hid]
		var r: float = 0.0 if bool(s.get("at_deaths_door", false)) else float(s["hp_ratio"])
		stats["hp_low_water"] = minf(float(stats["hp_low_water"]), r)


## 结果快照，供 bench 汇总。
func summary() -> Dictionary:
	var hp_sum: float = 0.0
	var st_sum: float = 0.0
	var n: int = 0
	var afflicted: int = 0
	var virtuous: int = 0
	var dd: int = 0
	for hid in _alive_ids():
		var s: Dictionary = state[hid]
		hp_sum += float(s["hp_ratio"])
		st_sum += float(s["stress"])
		if not str(s.get("affliction", "")).is_empty():
			afflicted += 1
		if not str(s.get("virtue", "")).is_empty():
			virtuous += 1
		if bool(s.get("at_deaths_door", false)):
			dd += 1
		n += 1

	var out: Dictionary = stats.duplicate(true)
	out["preset"] = preset_name
	out["end_reason"] = end_reason
	# 任务口径（M32）：bench 要能把「清剿完成率」和「探索完成率」分开统计，
	# 否则两种任务的完成率混在一个数字里，谁也不知道差在哪。
	out["quest_type"] = quest_type
	out["quest_goal"] = str(quest_goal.get("kind", ""))
	out["quest_met"] = quest_met()
	out["quest_battles_total"] = int(stats.get("quest_battles_total", 0))
	out["quest_battles_cleared"] = int(stats.get("quest_battles_cleared", 0))
	out["quest_curio"] = str(quest_goal.get("curio", ""))
	out["quest_gathered"] = int(stats.get("quest_gathered", 0))
	out["quest_activated"] = int(stats.get("quest_activated", 0))
	if map_mode:
		out["steps_total"] = (map["room_ids"] as Array).size()
		out["steps_done"] = int(stats["rooms_visited"])
	else:
		out["steps_total"] = route.size()
		out["steps_done"] = step_index
	out["alive"] = n
	out["alive_ratio"] = float(n) / float(maxi(hero_ids.size(), 1))
	out["hp_end"] = hp_sum / float(n) if n > 0 else 0.0
	out["stress_end"] = st_sum / float(n) if n > 0 else 200.0
	out["afflicted_alive"] = afflicted
	out["virtuous_alive"] = virtuous
	out["at_deaths_door_end"] = dd
	out["light_end"] = light
	out["food_end"] = food
	out["torch_end"] = torch
	out["shovel_end"] = shovel
	out["heal_charges_left"] = heal_charges
	# 战利品账面（M13）：换真表之后，「一趟值多少」必须能被直接读出来做对照
	out["gold"] = loot_gold
	out["heirloom_total"] = _heirloom_total()
	out["heirlooms"] = loot_heirlooms.duplicate()
	out["gems_total"] = _gem_total()
	out["trinkets"] = loot_trinkets
	out["trinket_ids"] = loot_trinket_ids.duplicate()
	# 这趟参战的人身上一共戴了几件。仓库里的不算——那是元层的账。
	var worn: int = 0
	for hid in hero_ids:
		worn += (hero_trinkets.get(str(hid), []) as Array).size()
	out["trinkets_equipped"] = worn
	# 怪癖账面（M14）：终局身上还剩多少，和这一趟拿了多少，是两件事。
	# 只记「拿了多少」会看不见「槽位满了白拿」和「清负面生效」。
	var q_total: int = 0
	var q_disease: int = 0
	for hid_q in state.keys():
		for q in quirks_of(str(hid_q)):
			q_total += 1
			if db != null and db.quirk_lib != null and db.quirk_lib.is_disease(str(q)):
				q_disease += 1
	out["quirks_total"] = q_total
	out["diseases_total"] = q_disease
	out["supply_end"] = supply_total()
	out["completed"] = end_reason == "complete"
	out["wiped"] = end_reason == "wipe"
	out["retreated"] = end_reason == "retreat"
	var attacks: int = int(out.get("attacks", 0))
	out["hit_rate"] = float(out.get("hits", 0)) / float(attacks) if attacks > 0 else 0.0
	out["crit_rate"] = float(out.get("crits", 0)) / float(attacks) if attacks > 0 else 0.0
	var gross: float = float(out.get("gross_dealt", 0.0))
	out["overkill_ratio"] = float(out.get("overkill", 0.0)) / gross if gross > 0.0 else 0.0
	return out

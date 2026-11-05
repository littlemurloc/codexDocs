class_name QuestGoal
extends RefCounted
## 任务目标层（M32）：把 `quests.json` 的任务定义翻译成「这一趟要做什么」。
##
## 在这之前，「任务」在代码里只是一个字符串：`explore` 或 `kill_boss`。
## 前者没有任何判据（走到终点就算），后者只有一条特例判断（`_end` 里那个
## `quest_type == "kill_boss" and not boss_killed`）。6 种任务类型、48 个目标定义
## 从 M0 就躺在 `data/quests.json` 里，一个都没被读过。
##
## 这一层只做三件事：**解析、判进度、判完成**。它不认识 Expedition，
## 也不认识界面——状态由调用方拼成一个扁平字典递进来（见 `met` 的参数）。
## 和 `SkillLoadout` / `BuffRules` 同样的理由：同一套判定有两个调用方
## （远征层与 bench），两边各写一份迟早在边界上分叉。
##
## ## 一个必须说明的偏离
##
## 数据里 `explore` 的目标是 `explore_all_rooms`——**走满 90% 的房间**。
## 我们的 `explore` 一直是「走到终点房间就算」，从 M7 起就是这样。
## M32 **故意不改**它：改了两件事会同时发生——
##   1. 所有 bench 基线作废（路线模式根本没有「房间」这个概念）；
##   2. 地图的支线是死胡同（M18 量过），要求 90% 会把「探索」变成「绕完所有死路」。
## 90% 这条留在 `raw` 字段里可查，等将来真的要做「完整探索」任务时再启用。

## 数据里存在、但我们还没接的任务类型。它出现在这里而不是被静默忽略：
## 任务板只从 `supported()` 为真的类型里抽卡，玩家不会看到一张点不动的卡。
##
## `inventory_activate` 需要「先带任务道具，再在奇物上用它」——那要求
## 任务物品能进背包、能被指定为交互道具，属于道具系统（M34 之后）。
## `gather` / `activate` 在 M33 接上：它们只要求「在某个奇物上交互」。
const UNSUPPORTED_TYPES: Array = ["inventory_activate"]

## 需要「目标奇物」的任务类型（M33）。
const CURIO_TYPES: Array = ["gather", "activate"]

const KIND_REACH: String = "reach_goal"
const KIND_BOSS: String = "kill_monster"
const KIND_BATTLE: String = "battle_room"
const KIND_GATHER: String = "gather"
const KIND_ACTIVATE: String = "activate"

## 任务目标奇物 → 本作的等价标签（M33）。
##
## 为什么需要这张表：`quests.json` 让任务去 10 个奇物上收集/激活，
## 但其中 **9 个在抽取数据里根本不存在**（`_raw` 里出现 0 次）。
## 它们是 DD1 在生成任务时动态创建的「任务专用奇物」，定义不在基础游戏里。
## （详见 M32 文档 §5，那是这一期之前查出来的。）
##
## 处理方式不是硬编一个 id 替换掉——那等于假造数据。做法是**降到标签层**：
## 任务要的其实是「一类东西」（祭祀用、食物、财货……），
## 只要该区域里有带这个标签的奇物，交互就算数。
##
## `why` 写在这里是给后来的人看的：为什么「外科医生的包」是 Scrounging
## 而不是 Food——因为 Weald 的 Food 只有兽尸一个，而 Scrounging 那一组
## （老树、旅人帐篷、浅坟、强盗陷阱箱）才是「翻找/采集」的语义。
const CURIO_TAG_MAP: Dictionary = {
	"reliquary": {"tag": "Worship", "why": "圣髑匣 = 祭祀圣物"},
	"chirurgeons_satchel": {"tag": "Scrounging", "why": "外科包 = 翻找采集（Weald 无医疗类标签）"},
	"foodstuff_crate": {"tag": "Food", "why": "粮箱 = 食物"},
	"shipment_crates": {"tag": "Treasure", "why": "货箱 = 财货"},
	"corrupted_altar": {"tag": "Worship", "why": "腐化祭坛 = 祭祀"},
	"infected_corpse": {"tag": "Haunted", "why": "腐尸 = 尸骸"},
	"animalistic_shrine": {"tag": "Unholy", "why": "兽性神龛 = 邪祀"},
	"protective_ward": {"tag": "Worship", "why": "护符 = 祭祀"},
	"beacon": {"tag": "Worship", "why": "信标 = 祭祀（至暗之地，未开）"},
	"iron_maiden": {"tag": "Torture", "why": "铁处女 = 刑具"},
}

## 我们的区域 id → `curios.json` 里的 region 拼写。
## 两套命名不一样（crypts 在数据里叫 Ruins），不映射的话
## 「同一区域的奇物」这条判断会永远不成立。
const REGION_NAME: Dictionary = {
	"weald": "Weald", "crypts": "Ruins", "warrens": "Warrens", "cove": "Cove",
	"darkest_dungeon": "Darkest Dungeon",
}


## 这个任务类型现在能不能真的结算。
static func supported(quest_type: String) -> bool:
	return not UNSUPPORTED_TYPES.has(quest_type)


## 解析任务类型 → 目标。
##
## `region` 用来选 `goal_lists` 里的区域变体（gather / activate 每个区域
## 的奇物不同），找不到就走 `dungeon == "all"` 那一条。
##
## 返回：
##   kind        KIND_*
##   amount      要几个 / 要几场
##   percentage  按比例算的目标（0 表示不用）
##   curio       目标奇物 id（gather / activate）
##   item        要收集的任务物品 id（gather）
##   raw_type    `quests.json` 里的原始 type，排查数据用
##   goal_id     命中的 goal id，排查数据用
##   curio_raw   数据里写的奇物名（可能就是 9 个不存在的之一）
##   curio       落到本作真实奇物上的 id（M33）；解析不出来是空串
##   supported   现在能不能结算
static func parse(quests: Dictionary, quest_type: String, region: String = "",
		curios: Dictionary = {}) -> Dictionary:
	var out: Dictionary = {
		"quest_type": quest_type, "kind": KIND_REACH, "amount": 0,
		"percentage": 0.0, "curio": "", "curio_raw": "", "item": "", "raw_type": "",
		"goal_id": "", "supported": supported(quest_type),
	}
	# `kill_boss` 在数据里 goals 是 `[[]]`（空目标），它的语义写在
	# dungeons.json 的遭遇表里（终点房间放 boss）。所以这一条不查 goal 表，
	# 直接按「杀死首领」处理——这也正是 M20 的行为，这里只是把它显式化。
	if quest_type == "kill_boss":
		out["kind"] = KIND_BOSS
		out["amount"] = 1
		out["raw_type"] = "kill_monster"
		return out
	# `explore` 同样不查表，理由见文件头那个「必须说明的偏离」。
	if quest_type == "explore" or quest_type.is_empty():
		out["kind"] = KIND_REACH
		out["raw_type"] = "explore_room"
		return out

	var types_block: Dictionary = quests.get("quest.types", {})
	var goals_index: Dictionary = {}
	for g in (types_block.get("goals", []) as Array):
		if g is Dictionary and (g as Dictionary).has("id"):
			goals_index[str((g as Dictionary)["id"])] = g
	var goal_ids: Array = _pick_goal_ids(types_block.get("types", []), quest_type, region)
	if goal_ids.is_empty():
		# 表里没有这个类型 / 没有区域变体：保持「走到终点」，但标记为不支持，
		# 免得任务板抽到一张永远结算不了的卡。
		out["supported"] = false
		return out
	var gid: String = str(goal_ids[0])
	var def: Dictionary = goals_index.get(gid, {})
	if def.is_empty():
		out["supported"] = false
		return out

	out["goal_id"] = gid
	out["raw_type"] = str(def.get("type", ""))
	var data: Dictionary = def.get("data", {})
	out["amount"] = int(data.get("amount", 0))
	out["percentage"] = float(data.get("percentage", 0.0))
	# 数据里写的奇物名先原样记下来，再尝试落到本作真实存在的奇物上（M33）。
	out["curio_raw"] = str(data.get("curio_name", ""))
	var item: Dictionary = data.get("item", {})
	if not item.is_empty():
		out["item"] = str(item.get("id", ""))
		if int(item.get("amount", 0)) > 0:
			out["amount"] = int(item.get("amount", 0))
	match str(def.get("type", "")):
		"battle_room":
			out["kind"] = KIND_BATTLE
		"gather":
			out["kind"] = KIND_GATHER
		"activate":
			out["kind"] = KIND_ACTIVATE
		"kill_monster":
			out["kind"] = KIND_BOSS
		_:
			out["kind"] = KIND_REACH
	# 需要目标奇物的任务：解析不出来就不能算「可结算」。
	# 这一条必须在**解析阶段**定下来，而不是等交互的时候才发现——
	# 那时候玩家已经在图里走了一半，任务却永远做不完。
	if CURIO_TYPES.has(quest_type):
		out["curio"] = resolve_curio(str(out["curio_raw"]), region, curios)
		out["supported"] = not str(out["curio"]).is_empty()
	return out


## 把一个（可能不存在的）任务奇物名落到本作真实奇物上。
##
## 两种情形：
##   1. 名字本身就是真的（`iron_maiden`）→ 直接用，不加任何解释。
##   2. 名字不存在 → 查 `CURIO_TAG_MAP` 拿标签，在该区域的奇物里找一个
##      带这个标签的。**同区域的优先于 ALL**：`eldritch_altar` 到处都是，
##      但荒野兽尸比它更能代表「这里的食物」。
##
## 同一个 (名字, 区域) 永远解析到同一个 id（按 id 排序取第一个），
## 否则同一张任务卡每次进图指的东西都不一样，玩家没法记。
static func resolve_curio(quest_curio: String, region: String, curios: Dictionary) -> String:
	if quest_curio.is_empty() or curios.is_empty():
		return ""
	var own: String = str(REGION_NAME.get(region, ""))
	var exact: Dictionary = curios.get(quest_curio, {})
	if not exact.is_empty():
		var r0: String = str(exact.get("region", ""))
		if r0 == own or r0 == "ALL":
			return quest_curio
	var tag: String = str((CURIO_TAG_MAP.get(quest_curio, {}) as Dictionary).get("tag", ""))
	if tag.is_empty():
		return ""
	var best_own: Array = []
	var best_all: Array = []
	for id in curios.keys():
		var cid: String = str(id)
		var def: Dictionary = curios[id]
		if not (def.get("tags", []) as Array).has(tag):
			continue
		var r: String = str(def.get("region", ""))
		if r == own:
			best_own.append(cid)
		elif r == "ALL":
			best_all.append(cid)
	best_own.sort()
	best_all.sort()
	if not best_own.is_empty():
		return str(best_own[0])
	return str(best_all[0]) if not best_all.is_empty() else ""


## 从 `goal_lists` 里挑这个区域的变体：先找精确区域，再找 `all`。
static func _pick_goal_ids(types_list: Array, quest_type: String, region: String) -> Array:
	var lists: Array = []
	for t in types_list:
		if t is Dictionary and str((t as Dictionary).get("id", "")) == quest_type:
			lists = (t as Dictionary).get("goal_lists", [])
			break
	if lists.is_empty():
		return []
	var picked: Array = []
	var fallback: Array = []
	for row in lists:
		if not (row is Dictionary):
			continue
		var d: String = str((row as Dictionary).get("dungeon", "all"))
		var goals: Array = (row as Dictionary).get("goals", [])
		var first: Array = (goals[0] as Array) if not goals.is_empty() else []
		if d == region:
			picked = first
			break
		if d == "all":
			fallback = first
	return picked if not picked.is_empty() else fallback


## 完成判据。`st` 是调用方拼的扁平状态（见 `Expedition.quest_state`）：
##   at_goal / boss_killed / battles_total / battles_cleared / rooms_visited / rooms_total
static func met(goal: Dictionary, st: Dictionary) -> bool:
	var need: int = _need(goal, st)
	match str(goal.get("kind", KIND_REACH)):
		KIND_REACH:
			return bool(st.get("at_goal", false))
		KIND_BOSS:
			return bool(st.get("boss_killed", false))
		KIND_BATTLE:
			# need == 0 = 图上本来就没有仗，那「清完全部战斗」自动成立。
			return int(st.get("battles_cleared", 0)) >= need
		KIND_GATHER:
			# 解析不出目标奇物（区域里没有带该标签的东西）时不判失败：
			# 任务板本来就不该发这种卡，真发出来了也该放玩家过去，
			# 而不是让人在结算屏看到一个永远做不完的任务。
			if not bool(goal.get("supported", false)):
				return true
			return int(st.get("gathered", 0)) >= need
		KIND_ACTIVATE:
			if not bool(goal.get("supported", false)):
				return true
			return int(st.get("activated", 0)) >= need
		_:
			return false


## 进度（当前 / 需要）。界面用，判据仍然只看 `met`——
## 两处各算一遍的话，改规则时只会改一处。
static func progress(goal: Dictionary, st: Dictionary) -> Vector2i:
	var need: int = _need(goal, st)
	match str(goal.get("kind", KIND_REACH)):
		KIND_BOSS:
			return Vector2i(1 if bool(st.get("boss_killed", false)) else 0, 1)
		KIND_BATTLE:
			return Vector2i(mini(int(st.get("battles_cleared", 0)), need), need)
		KIND_GATHER:
			return Vector2i(mini(int(st.get("gathered", 0)), need), need)
		KIND_ACTIVATE:
			return Vector2i(mini(int(st.get("activated", 0)), need), need)
		_:
			return Vector2i(1 if met(goal, st) else 0, 1)


## 要多少。按比例的目标把百分比乘上总数再向上取整——
## 向下取整会让「90% 的 9 间房」变成 8 间，比例越低差得越多。
static func _need(goal: Dictionary, st: Dictionary) -> int:
	var pct: float = float(goal.get("percentage", 0.0))
	if pct > 0.0:
		var total: int = int(st.get("battles_total", 0))
		if str(goal.get("kind", "")) == KIND_REACH:
			total = int(st.get("rooms_total", 0))
		if total <= 0:
			return 0
		return maxi(1, int(ceil(float(total) * pct)))
	return maxi(0, int(goal.get("amount", 0)))


## 任务目标的一句话，给任务卡和地图屏用。
##
## `curio_label` 是目标奇物的显示名（由界面层传进来，核心层不认识名字表）。
## 传了就说清「在哪」，没传就只说动作——报一个玩家认不出的 id 比不报更糟。
static func describe(goal: Dictionary, st: Dictionary = {},
		curio_label: String = "") -> String:
	match str(goal.get("kind", KIND_REACH)):
		KIND_BOSS:
			return "杀掉终点房间的首领"
		KIND_BATTLE:
			var need: int = _need(goal, st)
			if need <= 0:
				return "清光图上所有战斗（这趟没有战斗房）"
			return "清光图上全部 %d 场战斗" % need
		KIND_GATHER:
			var n: int = int(goal.get("amount", 1))
			if not bool(goal.get("supported", false)):
				return "去出口（收集目标解析失败，本趟不判这个）"
			if curio_label.is_empty():
				return "在目标奇物上收集 %d 件东西" % n
			return "在「%s」上收集 %d 件东西" % [curio_label, n]
		KIND_ACTIVATE:
			var n2: int = int(goal.get("amount", 1))
			if not bool(goal.get("supported", false)):
				return "去出口（激活目标解析失败，本趟不判这个）"
			if curio_label.is_empty():
				return "在目标奇物上激活 %d 次" % n2
			return "在「%s」上激活 %d 次" % [curio_label, n2]
		_:
			return "走到出口"

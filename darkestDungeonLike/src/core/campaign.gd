class_name Campaign
extends RefCounted
## 元层：两趟远征之间发生的事。
##
## M3 做完资源层之后，玩家其实没有理由关心「撤退」和「死人」——
## 死掉的英雄下一趟照样满编出现，撤退除了少走两步什么也没损失。
## 这一层的唯一目的就是让那两件事开始有后果：
##
##   战利品  → 只能靠走出去拿，撤退只保得住已经到手的
##   阵亡    → 人真的没了，要花资源招募，招不起就少人出发
##   装备阶  → 用战利品升级，下一趟变强（而不是跟着地图白送）
##   压力    → 跨远征累积，回城只减一部分
##
## 存档是一份 JSON，放在 user:// 下。刻意不用二进制/序列化对象：
## 出问题时能直接用记事本打开看，这在调数值阶段比省几十字节重要得多。

const DEFAULT_PATH: String = "user://campaign.json"
const DEFAULT_CFG: String = "res://data/campaign.json"
const MAX_GEAR: int = 4

# ============================================================
# 决心等级（M25）
# ============================================================
#
# 在这之前，「难度攀升」这件事在我们这里是**完全缺失**的：玩家有钱就能把
# 装备顶到 4 阶，然后拿 4 阶装备打短途 Lv1 刷一辈子金币。原版不可能这样，
# 因为原版有另一根轴在往上顶——**英雄自己的决心等级**。
#
# 原版的三条机制（2026-11 查证 wiki 后照抄，不是拍的）：
#
#   1. 只有三档离散台阶（1/3/5），同档内怪物数值固定，没有连续膨胀
#   2. **双向等级锁**：英雄比任务高 2 级或以上 → 拒绝参战；
#      比任务低 → 可进，但进本每低一级 +20 压力
#   3. 任务板按名册等级加权随机，但永远保底一张学徒本
#
# 第 2 条是整个节奏的来源：它切断了「练满级回头虐菜」这条路。
# 结果就是原版的真实循环——约 5 趟，一个英雄就会被踢出学徒本。

const MAX_RESOLVE: int = 6

## 从「上一级」升到 index 这一级需要的经验。index = 目标等级。
##
## 原版的累计表是 2/7/13/21/29（0→5 级），取差分得到 2/5/6/8/8，6 级再加 11。
## 我们从 1 级起步（新兵就是 1 级），所以 index 0 和 1 都用不上。
const RESOLVE_XP: Array = [0, 0, 5, 6, 8, 8, 11]

## 一趟远征给多少经验。`level → 尺寸 → xp`。
##
## 原版表：学徒 2/3/4/4，精英 2/4/6/8，冠军 4/8/12/16（短/中/长/首领）。
## 尺寸和难度是**乘性**关系，不是加性——所以冠军长本是学徒短本的 4 倍，
## 这也是为什么「练级」在原版里是往高难度走，而不是刷次数。
const QUEST_XP: Dictionary = {
	1: {"short": 2, "medium": 3, "long": 4, "boss": 4},
	3: {"short": 2, "medium": 4, "long": 6, "boss": 8},
	5: {"short": 4, "medium": 8, "long": 12, "boss": 16},
}

## 进本时，英雄每比任务低一级要吃多少压力。
const JOIN_STRESS_PER_LEVEL: float = 20.0

## 进本之后，英雄每比任务低一级，受压多多少（M29）。原版是 25%。
const JOIN_STRESS_MULT_PER_LEVEL: float = 0.25

## 英雄最多能比任务高几级。到 2 就是「拒绝参战」。
const REFUSE_GAP: int = 2

## 每周任务板的槽位（M26）。尺寸固定，等级每周重抽。
##
## 尺寸固定是**我们的槽位设计**，不是原版规则——原版是「尺寸和难度独立随机」
## 生成一堆任务。我们只有四个格子，把尺寸钉死能让玩家一眼记住
## 「第三格是长途」，比每次重新认一遍强。
## 首领槽只能是 medium：`dungeons.json` 里 kill_boss 只有 medium / long 两档参数。
const BOARD_SLOTS: Array = [
	["short", "explore"],
	["medium", "explore"],
	["long", "explore"],
	["medium", "kill_boss"],
]

## 任务板覆盖的区域（M32）。顺序就是界面上的排列顺序。
const BOARD_REGIONS: Array = ["weald", "crypts", "warrens", "cove"]

## 每个区域各有一套槽位（M32 / M33）。
##
## M26 的四格对四个区域是同一张表——同一个尺寸、同一个任务类型，
## 换区域只换遭遇表和奇物池。原版不是这样：**任务板本来就长在区域上**，
## 每个区域按自己的推进度出任务，任务卡自带区域。
##
## M32 把「区域」提到卡片属性里并接上清剿；M33 再接收集 / 激活。
##
## 三条硬约束，改这张表之前必须先想清楚：
##  1. **清剿有短/中/长三档图参数**，探索也有三档，首领只有中/长。
##  2. **收集 / 激活 / 带道具激活在 `dungeons.json` 里只有 medium 一档**。
##     写成 short 会拿到空地图参数，`MapGen` 直接返回空字典（出发失败）。
##  3. **普通激活的目标是铁处女，只在墓穴（Ruins）有**。
##     放进荒野的板上就是一张永远做不完的卡。
##  4. **带道具激活（M35）每个区域的目标不同**（祭坛/尸骸/神龛/护符），
##     四个区域都能解析，但同样只有一张卡——别让四块板子全长一样。
const BOARD_SLOTS_BY_REGION: Dictionary = {
	"weald": [
		["short", "cleanse"], ["medium", "gather"],
		["long", "explore"], ["medium", "kill_boss"],
	],
	"crypts": [
		["short", "explore"], ["medium", "activate"],
		["long", "cleanse"], ["medium", "kill_boss"],
	],
	"warrens": [
		["short", "explore"], ["medium", "inventory_activate"],
		["long", "cleanse"], ["medium", "kill_boss"],
	],
	"cove": [
		["short", "cleanse"], ["medium", "gather"],
		["long", "explore"], ["medium", "kill_boss"],
	],
}

var path: String = DEFAULT_PATH
var cfg: Dictionary = {}

var gold: int = 0
var heirlooms: Dictionary = {}      # name -> 数量
var roster: Dictionary = {}         # hero_id -> {gear, skill, alive, stress, runs, deaths}
var expeditions: int = 0
var best_steps: int = 0
## 成绩口径版本。1 = 旧口径（step_index，含走廊内容结算的累计步数），
## 2 = 房间数（与结算屏「推进 X/Y 步」一致）。
## 两套口径混用会出现「结算屏写 9，城镇写 22」这种自相矛盾，
## 所以旧档读进来直接清零重记，而不是留着让它永远压住新纪录。
var steps_metric: int = 2
var free_recruits: int = 0   # 破产保护额度：全员阵亡后赠送的免费征召次数

## 本周任务板（M26）：4 个 `{size, level, quest}`。
##
## 在这之前，城镇难度卡的四个等级是**写死在场景里的常量**，
## 玩家永远能选 1/3/5 三档。于是「往上走」全靠自觉——
## M25 的双向锁只负责不让你往下走，却没有任何力把你往上赶。
##
## 现在每周重抽一次，等级按名册强度加权。它补的正是那半边：
## 你练得越强，摆在你面前的任务就越硬。
## 现在摆在玩家面前的板子（`boards[board_region]` 的同名引用）。
##
## 保留这个名字是为了让 M26 以来所有读 `campaign.board` 的地方（界面、测试）
## 一行都不用改。**它和 `boards[board_region]` 是同一个数组对象**，
## 所以改里面的字典两边都看得到；但给 `board` 整体赋值不会同步回去，
## 换区域请走 `select_board_region()`。
var board: Array = []

## 四个区域各自的板子（M32）：region -> Array[4]。
var boards: Dictionary = {}
## 当前选中区域。城镇上那排区域按钮改的就是它。
var board_region: String = "weald"

## 周次（M23）。**一趟远征 = 一周**。
##
## 原来商店已经是「按趟刷新」，但那只是巧合——没有显式的时间轴，
## 建筑就不可能「把人派出去、下周回来」，M22 的八座建筑只能退化成八个功能面板。
##
## 有了这个计数，建筑才有代价：派人去减压/疗养，这一周他就不能出征。
## 这和「花多少钱」是完全不同的取舍维度。
var week: int = 1

var _order: Array = []              # 名册显示顺序（已入册的职业，按加入先后）

## 全部已知职业（M27）。由场景从 `heroes.json` 灌进来。
##
## 招新只从「已知但还没入册」的职业里抽。不灌的话招新自动失效，
## 其余逻辑照旧——测试里很多地方不关心这件事。
var known_heroes: Array = []

## 名册上限（M27）。**M34 起它是一个人头上限，和职业数量无关**——
## 那时 key 还是职业 id，所以上限只能等于职业总数；现在同职业能多人了。
## 上限就等于职业总数（`heroes.json` 15 个）。
const ROSTER_HARD_MAX: int = 15

## 本周马车里的新面孔（M27）：2 个还没入册的职业。每周重抽。
var recruit_candidates: Array = []

## 怪癖表。由场景在加载完 DdDb 之后注入——Campaign 不认识 db，
## 也不该为了两个折扣字段去读一份 88 KB 的表。
## 没注入时折扣恒为 0，其余逻辑照常。
var quirk_lib: QuirkLib = null
## 英雄「生成」时自带的怪癖数量区间（来自 heroes.json 的 generation 段）。
## 这是 M14 一开始漏掉的主渠道——DD1 的新英雄不是白纸。
var start_quirk_gen: Dictionary = {}
## 开局怪癖的随机源。为 0 时用 randi()；测试里给个固定种子以便复现。
var start_rng_seed: int = 0
## 关掉它就不会有开局怪癖（回到 M14 第一版的行为）。
var start_quirks_enabled: bool = true

## —— 技能组（M19）——
##
## 每个英雄能带几个、能带哪些，来自 `heroes.json` 的 `skill_selection`。
## 由场景注入，和 quirk_lib / trinket_lib 一样：Campaign 不自己去读表。
## 没注入时 `_default_loadout` 返回空数组，等于「全装」——也就是 M18 及以前的行为。
var skill_table: Dictionary = {}     # hid -> {can_select, max, ids}

## —— 饰品（M15）——
##
## 仓库与装备是**两个不同的容器**，不是「一个列表加一个布尔」：
## 装备中的件不占仓库格，容量上限也不一样（仓库 16、每人 2），
## 合成一个列表之后「仓库满了但人身上还能戴」这种状态就没法表达。
## 容量取自 inventory.json：trinket_store.max_slots = 16、
## hero_equipped_trinkets.max_slots = 2。
##
## 饰品库只用来判职业限制、同名上限和展示名；没注入时这两条检查
## 一律放行（宁可能装上，也不要因为缺表把功能变成不可用）。
var trinket_lib: TrinketLib = null
var trinket_store: Array = []           # 仓库里的饰品 id（可重复，受 limit 约束）
var store_slots: int = 16
var equip_slots: int = 2
## 掉进仓库时的失败计数。静默丢弃最难查，所以失败要留痕。
var trinket_refused: Dictionary = {}    # reason -> 次数

## —— 商店（M16）——
##
## `shop` 只提供价格与上架规则；**货币结算在 Campaign 这一层**，
## 因为「够不够钱」要同时看金币和传家宝，那是元层的账。
##
## 上架用独立种子：它只在「完成一趟 / 开新档」时掷一次，
## 但如果它碰了任何一条主序列，bench 的全部数字同时作废
## （M11/M13/M15 各踩过一次）。存档里带 `shop_seed`，
## 同一个档的货架就不会每次读档都变。
var shop: Shop = null
var shop_stock: Array = []
var shop_seed: int = 0
## 上架失败/购买失败的计数。同一类问题在 M13/M14 都吃过「静默吞掉」的亏。
var shop_refused: Dictionary = {}


func setup(cfg_path: String = DEFAULT_CFG, save_path: String = DEFAULT_PATH) -> bool:
	return setup_from_cfg(_read_json(cfg_path), save_path)


## 也可以直接吃 DdDb 已经解析好的表——避免同一个 JSON 被读两遍、
## 两处各有一份可能不同步的副本。
func setup_from_cfg(c: Dictionary, save_path: String = DEFAULT_PATH) -> bool:
	path = save_path
	cfg = c if not c.is_empty() else _fallback_cfg()
	var names: Array = cfg.get("heirlooms", ["bust", "portrait", "crest", "deed"])
	heirlooms = {}
	for n in names:
		heirlooms[str(n)] = 0
	_order = (cfg.get("roster_start", {}) as Dictionary).get("heroes",
		["man_at_arms", "highwayman", "vestal", "plague_doctor"]).duplicate()
	var start_q: Dictionary = (cfg.get("roster_start", {}) as Dictionary).get("quirks", {})
	for hid in _order:
		roster[str(hid)] = {"def": str(hid), "gear": 0, "skill": 0, "alive": true,
			"stress": 0.0, "runs": 0, "deaths": 0,
			# 新兵 = 1 级 0 经验（M25）。原版新招募的英雄也是 1 级起步。
			"resolve": 1, "xp": 0,
			"quirks": _start_quirks(str(hid), start_q)}
	# 新档的名册全是 1 级，所以这块板子必然只有学徒本——
	# 这不是特例，是 board_ceiling 在名册弱时的自然结果。
	roll_board()
	return true


## 按 `heroes.json` 的生成区间掷开局怪癖：正 1–2、负 1–2。
##
## 这条路才是原版怪癖的主要来源。只接奇物渠道的话，一趟真实远征里
## 大概只能碰到 0–1 个奇物 × 一成概率 ≈ 0.05 条，等于整期功能不可见。
func _roll_start_quirks(hid: String, rng: DdRng) -> Array:
	var out: Array = []
	if not start_quirks_enabled or rng == null:
		return out
	if quirk_lib == null or not quirk_lib.is_loaded():
		return out
	var g: Dictionary = start_quirk_gen.get(hid, {})
	if g.is_empty():
		return out
	var n_pos: int = rng.next_int_range(int(g.get("pos_min", 0)), int(g.get("pos_max", 0)))
	var n_neg: int = rng.next_int_range(int(g.get("neg_min", 0)), int(g.get("neg_max", 0)))
	for i in n_pos:
		var q: String = quirk_lib.pick("positive", rng, out, false)
		if not q.is_empty():
			out.append(q)
	for i in n_neg:
		var q2: String = quirk_lib.pick("negative", rng, out, false)
		if not q2.is_empty():
			out.append(q2)
	return out


## 显式配置的开局怪癖（`campaign.json` 的 roster_start.quirks）。
##
## M14 量出来一个不好看的事实：真实地图一趟只碰到 0–1 个奇物，
## 而奇物里只有约一成会给怪癖——也就是**自然获得率约 0.05 条/趟**。
## 代码是对的，但玩家几乎看不见它。
##
## 所以留这个入口：在 campaign.json 的 roster_start.quirks 里写
##   "vestal": ["tough"]
## 就能让新档带初始怪癖（DD1 的英雄本来也是带着怪癖入职的）。
## **默认留空**——填了就等于改平衡，那是另一件事，得单独量。
func _start_quirks(hid: String, table: Dictionary) -> Array:
	var raw: Array = table.get(hid, [])
	var out: Array = []
	for q in raw:
		var qid: String = str(q)
		if qid.is_empty():
			continue
		# 没有 quirk_lib 时照单全收（Campaign 不读数据表），有就过滤一遍，
		# 免得配置里写错一个 id 变成永远不生效的隐形选项。
		if quirk_lib != null and quirk_lib.is_loaded() and not quirk_lib.has(qid):
			push_warning("Campaign: roster_start.quirks 里的 %s 不存在，已跳过" % qid)
			continue
		out.append(qid)
	return out


func _read_json(p: String) -> Dictionary:
	if not FileAccess.file_exists(p):
		return {}
	var parsed: Variant = JSON.parse_string(FileAccess.get_file_as_string(p))
	return parsed if parsed is Dictionary else {}


static func _fallback_cfg() -> Dictionary:
	return {
		"heirlooms": ["bust", "portrait", "crest", "deed"],
		"loot": {"battle_gold": [9, 17], "battle_heirloom_chance": 0.30,
			"complete_gold": 45, "complete_gold_per_battle": 22,
			"complete_heirlooms": [1, 3]},
		"costs": {"recruit": {"gold": 1000, "heirlooms": {"crest": 4}},
			"upgrade": [{"gold": 1000, "heirlooms": {"bust": 3}},
				{"gold": 2200, "heirlooms": {"portrait": 4}},
				{"gold": 4800, "heirlooms": {"deed": 6}},
				{"gold": 10000, "heirlooms": {"crest": 10}}]},
		"roster_start": {"heroes": ["man_at_arms", "highwayman", "vestal", "plague_doctor"]},
	}


# ============================================================
# 档
# ============================================================

func new_game() -> void:
	gold = 0
	for k in heirlooms.keys():
		heirlooms[k] = 0
	roster = {}
	var start_q: Dictionary = (cfg.get("roster_start", {}) as Dictionary).get("quirks", {})
	var rng: DdRng = DdRng.new(start_rng_seed if start_rng_seed != 0 else randi())
	for hid in _order:
		var hid_s: String = str(hid)
		# 配置写了就听配置（哪怕写的是空数组）；没写才按英雄生成规则掷。
		var qlist: Array = _start_quirks(hid_s, start_q) if start_q.has(hid_s) \
			else _roll_start_quirks(hid_s, rng)
		roster[hid_s] = {"gear": 0, "skill": 0, "alive": true,
			"stress": 0.0, "runs": 0, "deaths": 0, "quirks": qlist, "equipped": [],
			"skills": _default_loadout(hid_s), "busy": 0}
	trinket_store = []
	trinket_refused = {}
	shop_stock = []
	shop_refused = {}
	# 新档的货架种子：有 start_rng_seed 就用它（测试可复现），
	# 否则随机。**不能直接用 randi() 而不记下来**——那样读档后货架会变。
	shop_seed = start_rng_seed if start_rng_seed != 0 else randi()
	refresh_shop()
	expeditions = 0
	week = 1
	best_steps = 0
	steps_metric = 2
	free_recruits = 0


## 有档就读，没档就开新档。返回 true 表示读到了旧档。
func load_or_new() -> bool:
	if not FileAccess.file_exists(path):
		new_game()
		return false
	var d: Dictionary = _read_json(path)
	if d.is_empty() or not d.has("roster"):
		new_game()
		return false
	from_dict(d)
	return true


func to_dict() -> Dictionary:
	return {
		"version": int(cfg.get("version", 1)),
		"gold": gold,
		"heirlooms": heirlooms.duplicate(),
		"roster": roster.duplicate(true),
		"expeditions": expeditions,
		"week": week,
		"best_steps": best_steps,
		"steps_metric": steps_metric,
		"free_recruits": free_recruits,
		"trinket_store": trinket_store.duplicate(),
		"shop_stock": shop_stock.duplicate(),
		"shop_seed": shop_seed,
		# 任务板（M26）：存进档里，读档时不能重抽——
		# 重抽等于「存档可以刷任务」，而刷任务正好能绕开 M25 的等级锁。
		# M32 起四个区域各一块，所以存整本 `boards`；`board` 同时写一份
		# 当前区域的，让只认旧字段的读法（以及 M26 的存档测试）继续工作。
		"board": board.duplicate(true),
		"boards": boards.duplicate(true),
		"board_region": board_region,
		# 名册组成与马车候选（M27）。
		# order 必须存：读档时靠它还原「谁在第几个」，配置只是新档的起点。
		"order": _order.duplicate(),
		"recruit_candidates": recruit_candidates.duplicate(),
	}


func from_dict(d: Dictionary) -> void:
	gold = int(d.get("gold", 0))
	heirlooms = {}
	for k in (cfg.get("heirlooms", []) as Array):
		heirlooms[str(k)] = 0
	for k in (d.get("heirlooms", {}) as Dictionary).keys():
		heirlooms[str(k)] = int(d["heirlooms"][k])
	roster = {}
	var src: Dictionary = d.get("roster", {})
	# 名册组成（M27）：先读存档里记的顺序。
	#
	# 老写法是「以配置的初始名册为准」重建 roster——M27 之后名册能超过 5 人，
	# 那样写会把人**静默丢掉**（存了 8 个、读回来 5 个），
	# 而且丢的正好是玩家花金币招来的那几个。
	var start_list: Array = (cfg.get("roster_start", {}) as Dictionary).get("heroes", [])
	_order = []
	for hid in (d.get("order", []) as Array):
		var hs: String = str(hid)
		if src.has(hs) and not _order.has(hs):
			_order.append(hs)
	# 旧档没有 order 字段：按配置里的初始名册顺序补
	for hid in start_list:
		var hs2: String = str(hid)
		if src.has(hs2) and not _order.has(hs2):
			_order.append(hs2)
	# 兜底：存档里有、但上面两条都没覆盖到的（改过配置、换过开局阵容）
	for hid in src.keys():
		var hs3: String = str(hid)
		if _order.has(hs3):
			continue
		# 校验要用**职业 id**（M34）：实例 id 可能是 `crusader#2`，
		# 直接拿它去查 known_heroes 会被当成未知职业丢掉——正好把同职业的第二个人吃了。
		var def3: String = str((src[hs3] as Dictionary).get("def", ""))
		if def3.is_empty():
			var cut3: int = hs3.find("#")
			def3 = hs3.substr(0, cut3) if cut3 > 0 else hs3
		if not known_heroes.is_empty() and not known_heroes.has(def3):
			push_warning("Campaign: 存档里的 %s 不是已知职业，已跳过" % hs3)
			continue
		_order.append(hs3)
	for hid in _order:
		var hid_s: String = str(hid)
		var row: Dictionary = src.get(hid_s, {})
		# 职业 id（M34）：第一个同职业的实例 id 就是职业 id 本身，
		# 第二个起是 `crusader#2`。老档没有 def 字段 → 实例 id 即职业 id。
		var def: String = str(row.get("def", ""))
		if def.is_empty():
			var cut: int = hid_s.find("#")
			def = hid_s.substr(0, cut) if cut > 0 else hid_s
		roster[hid_s] = {
			"def": def,
			"gear": clampi(int(row.get("gear", 0)), 0, MAX_GEAR),
			"skill": clampi(int(row.get("skill", 0)), 0, MAX_GEAR),
			"alive": bool(row.get("alive", true)),
			"stress": clampf(float(row.get("stress", 0.0)), 0.0, 200.0),
			"runs": int(row.get("runs", 0)),
			"deaths": int(row.get("deaths", 0)),
			# 旧档没有这个字段。缺省空数组，不报错——M13 之前的存档
			# 本来就没有怪癖，硬补一个会凭空给玩家加负面。
			"quirks": (row.get("quirks", []) as Array).duplicate(),
			# 旧档没有装备字段；缺省空数组。装备不占仓库格，所以两处都要读。
			"equipped": (row.get("equipped", []) as Array).duplicate(),
			# 技能组（M19）：旧档没有这个字段，缺省走默认组合。
			# **不能缺省成空数组**——空数组在战斗层表示「全装」，
			# 那会让老存档读进来还是 7 个技能，和新档不一致。
			"skills": _loadout_or_default(hid_s, row.get("skills", [])),
			# 建筑占用（M23）：还要忙几周，0 = 空闲。
			# 旧档没有这个字段 → 0 = 谁都不忙，行为和 M22 一致。
			"busy": maxi(0, int(row.get("busy", 0))),
			# 决心等级（M25）。旧档没有这两个字段。
			#
			# **不能一律补 1**：一个已经把装备升到 4 阶的旧档，说明它至少
			# 打了十几趟，补成 1 级会让它当场穿不上自己身上的装备，等于
			# 把玩家的进度没收了。所以旧档按装备阶反推——能升到几阶，
			# 就说明这个人至少练到了几级。这是「旧档不从 1 重来」的同一原则。
			"resolve": _resolve_from_save(row),
			"xp": maxi(0, int(row.get("xp", 0))),
		}
	expeditions = int(d.get("expeditions", 0))
	# 旧档没有周次：按「趟数 + 1」补，而不是从 1 重来——
	# 重来会让已经打了 10 趟的档显示「第 1 周」，比不显示还糟。
	week = maxi(1, int(d.get("week", expeditions + 1)))
	best_steps = int(d.get("best_steps", 0))
	steps_metric = int(d.get("steps_metric", 1))
	if steps_metric < 2:
		best_steps = 0     # 旧口径的数没法换算，重记
		steps_metric = 2
	free_recruits = int(d.get("free_recruits", 0))
	trinket_store = []
	for t in (d.get("trinket_store", []) as Array):
		var tid: String = str(t)
		if not tid.is_empty():
			trinket_store.append(tid)
	# 货架：有存档就照搬（含空格位——玩家买走哪一格要保留），
	# 旧档没有这个字段就现场掷一批，而不是留一个空商店。
	shop_stock = []
	shop_seed = int(d.get("shop_seed", 0))
	for t2 in (d.get("shop_stock", []) as Array):
		shop_stock.append(str(t2))
	if shop_stock.is_empty():
		refresh_shop()

	# 任务板（M26）。旧档没有这个字段就按当前名册现抽一块。
	# **存档里的板子绝不能重抽**——重抽等于「读一次档刷一次任务」，
	# 那正好能绕开 M25 的等级锁（反复读档直到刷出一张学徒本）。
	#
	# M32：`boards` 是四区各一块。旧档只有 `board`（单块），
	# 把它当作**存档里记的那个区域**的板子收进来，其他三区现抽——
	# 丢掉旧档那四格会让每周读一次档就白刷一遍，比少三个区域糟得多。
	board_region = str(d.get("board_region", "weald"))
	if not BOARD_REGIONS.has(board_region):
		board_region = "weald"
	boards = {}
	var raw_boards: Dictionary = d.get("boards", {})
	for region in BOARD_REGIONS:
		var rows: Array = _sanitize_board(raw_boards.get(region, []), str(region))
		if rows.size() == board_slots_for(str(region)).size():
			boards[str(region)] = rows
	if boards.is_empty():
		# 旧档 / 什么都没读到：先收旧字段，再补齐其余三区。
		var legacy: Array = _sanitize_board(d.get("board", []), board_region)
		if legacy.size() == board_slots_for(board_region).size():
			boards[board_region] = legacy
	# 缺哪个区域就补哪个。不用 `roll_board()` 整体重抽——
	# 那会把已经读进来的三块好板子一起冲掉，等于每周读一次档就白刷一遍。
	for region2 in BOARD_REGIONS:
		if not boards.has(str(region2)):
			boards[str(region2)] = _roll_region_slots(str(region2))
	_sync_board()

	# 马车候选（M27）。旧档没有这个字段就现抽一批——
	# 留空数组会让马车永远空着，玩家会以为功能坏了。
	recruit_candidates = []
	for c in (d.get("recruit_candidates", []) as Array):
		var cs: String = str(c)
		if not roster.has(cs):
			recruit_candidates.append(cs)
	if recruit_candidates.is_empty():
		roll_recruit_candidates()


## 存档里的一块板子：只留合法的尺寸、合法的任务类型、夹住的等级。
##
## 任务类型要过 `QuestGoal.supported()`：将来某张卡的机制被下线，
## 旧档里那张卡必须变成「重抽」，而不是变成一张点了没反应的废卡。
func _sanitize_board(raw: Variant, region: String) -> Array:
	var out: Array = []
	if not (raw is Array):
		return out
	for b in (raw as Array):
		if not (b is Dictionary):
			continue
		var bs: String = str((b as Dictionary).get("size", ""))
		if bs != "short" and bs != "medium" and bs != "long":
			continue
		var q: String = str((b as Dictionary).get("quest", "explore"))
		if not QuestGoal.supported(q):
			continue
		out.append({
			"size": bs,
			"quest": q,
			"level": clampi(int((b as Dictionary).get("level", 1)), 1, 5),
			"region": region,
		})
	return out


func save() -> bool:
	var f: FileAccess = FileAccess.open(path, FileAccess.WRITE)
	if f == null:
		push_error("Campaign: 无法写入 %s" % path)
		return false
	f.store_string(JSON.stringify(to_dict(), "  "))
	f.close()
	return true


# ============================================================
# 账
# ============================================================

func has_heirlooms(cost: Dictionary) -> bool:
	for k in cost.keys():
		if int(heirlooms.get(str(k), 0)) < int(cost[k]):
			return false
	return true


func can_afford(cost: Dictionary) -> bool:
	return gold >= int(cost.get("gold", 0)) and has_heirlooms(cost.get("heirlooms", {}))


func pay(cost: Dictionary) -> bool:
	if not can_afford(cost):
		return false
	gold -= int(cost.get("gold", 0))
	for k in (cost.get("heirlooms", {}) as Dictionary).keys():
		heirlooms[str(k)] = int(heirlooms.get(str(k), 0)) - int(cost["heirlooms"][k])
	return true


func add_loot(gold_add: int, gems: Dictionary) -> void:
	gold += maxi(0, gold_add)
	for k in gems.keys():
		heirlooms[str(k)] = int(heirlooms.get(str(k), 0)) + maxi(0, int(gems[k]))


func heirloom_total() -> int:
	var n: int = 0
	for k in heirlooms.keys():
		n += int(heirlooms[k])
	return n


# ============================================================
# 名册
# ============================================================

func hero_ids() -> Array:
	return _order.duplicate()


func hero(hid: String) -> Dictionary:
	return roster.get(hid, {})


## 名册实例 id → 职业 id（M34）。
##
## **这是这一期唯一的一条规则：查数据用 def，记状态用 key。**
##
## 命名方案是刻意的：第一个同职业的实例 id 就是职业 id 本身（`crusader`），
## 第二个起才加后缀（`crusader#2`）。这样 M0~M33 的所有存档、测试、
## 以及「按职业 id 找数据」的代码一行都不用改——它们的 key 本来就更等于 def。
func def_of(hid: String) -> String:
	var r: Dictionary = roster.get(hid, {})
	var d: String = str(r.get("def", ""))
	if not d.is_empty():
		return d
	# 名册里没有这个人 / 老档没写 def：按命名规则推
	var cut: int = hid.find("#")
	return hid.substr(0, cut) if cut > 0 else hid


## 给某个职业分配一个新的实例 id。
##
## 不复用已解雇的编号：`crusader#2` 被解雇之后，下一个新十字军仍然是 `crusader#2`
## ——反正那个位置已经空了。这样做的好处是编号永远从 1 开始连续，
## 界面上不会出现「十字军 5」却只有两个人的怪象。
func next_uid_for(cls: String) -> String:
	# 传进来的是实例 id 时先归到职业：`crusader#2` 和 `crusader` 问的是同一件事
	# ——「再给这个职业分配一个号」。不归的话会去查 `crusader#2#2` 这种鬼名字。
	var d: String = def_of(cls)
	if not roster.has(d):
		return d
	var n: int = 2
	while roster.has("%s#%d" % [d, n]):
		n += 1
	return "%s#%d" % [d, n]


## 这个人显示成什么。同职业多人时用罗马数字区分（界面层会补上职业名）。
##
## 返回的是**后缀**（"" 或 "Ⅱ"），不是完整名字：核心层不认识中文名，
## 名字表在 `DdNames` 里。这条边界和 `QuestGoal.describe` 收 curio_label 是同一条理由。
func variant_suffix(hid: String) -> String:
	var cut: int = hid.find("#")
	if cut <= 0:
		return ""
	var n: int = int(hid.substr(cut + 1))
	return _roman(n)


static func _roman(n: int) -> String:
	# 直接查表，不做减法拼装：拼装会把 2 拼成「ⅠⅠ」而不是「Ⅱ」，
	# 而这一共只有 15 个可能的号（名册上限）。
	const R: Array = ["", "Ⅰ", "Ⅱ", "Ⅲ", "Ⅳ", "Ⅴ", "Ⅵ", "Ⅶ", "Ⅷ",
		"Ⅸ", "Ⅹ", "Ⅺ", "Ⅻ", "ⅩⅢ", "ⅩⅣ", "ⅩⅤ"]
	if n < 1 or n >= R.size():
		return ""
	return str(R[n])


## 可以带上路的人（活着、**且这周没被建筑占着**）。
##
## M18 起这个名字的含义是「能出战的」，M23 又收窄了一层：
## 派去疗养院/减压的人这一周不能出征。出发准备屏用它列候选，
## 所以「被占着的人」根本不会出现在名单里——而不是出现在名单里点了才报错。
func selectable_ids() -> Array:
	var out: Array = []
	for hid in alive_ids():
		if busy_of(str(hid)) <= 0:
			out.append(hid)
	return out


## 这个人还要忙几周（0 = 空闲）。
func busy_of(hid: String) -> int:
	return maxi(0, int((roster.get(hid, {}) as Dictionary).get("busy", 0)))


## 建筑里能不能对他动手：活着、且这周不忙。
func _busy_guard(hid: String) -> String:
	if not roster.has(hid):
		return "名册里没有这个人"
	if not bool((roster[hid] as Dictionary).get("alive", true)):
		return "这个人已经阵亡"
	var n: int = busy_of(hid)
	if n > 0:
		return "这周还有事（剩 %d 周）" % n
	return ""


## 推进一周。**这是时间唯一的入口**——远征结束和主动休整都走它。
##
## 做四件事：周次 +1、忙的人少忙一周、按配置做压力自然恢复、换一批货。
##
## 压力恢复默认 0（`town_cycle.weekly_stress_relief`）。理由不是偷懒：
## M16 量过「无口粮死亡 0.72→1.35」，整条续航基线是靠回城那 40 点撑着的，
## 动它必须重跑全部续航对照。M24 把它开成 10 点/周——**只影响城镇回合**，
## bench 不走 Campaign，所以那批数字逐位不变。
func advance_week() -> void:
	week += 1
	for hid in roster.keys():
		var r: Dictionary = roster[hid]
		var b: int = int(r.get("busy", 0))
		if b > 0:
			r["busy"] = b - 1
	var cyc: Dictionary = cfg.get("town_cycle", {})
	var relief: float = float(cyc.get("weekly_stress_relief", 0.0))
	if relief > 0.0:
		for hid2 in roster.keys():
			var r2: Dictionary = roster[hid2]
			if bool(r2.get("alive", false)):
				r2["stress"] = clampf(float(r2.get("stress", 0.0)) - relief, 0.0, 200.0)
	# 每周换一批货。放这里而不是 settle，是为了让「主动休整」也有同样的副作用——
	# 时间推进的后果应该只有一个来源。
	shop_seed = randi()
	refresh_shop()
	# 任务板同理（M26）：新的一周有新的一批活，难度跟着名册走。
	roll_board()
	# 马车也换一批新面孔（M27）。
	roll_recruit_candidates()


## 主动过一周（M24）：不出发，让时间走。
##
## 这是「时间」第一次变成玩家可以主动消耗的资源。用途只有两个：
## 让建筑队列前进、让压力自然恢复。**没有收入**。
##
## 要收 `idle_cost`，原因见 `campaign.json` 的 town_cycle.note：
## 不收就是免费的商店刷新，可以无限刷。
func idle_week() -> String:
	var cost: int = int((cfg.get("town_cycle", {}) as Dictionary).get("idle_cost", 50))
	if gold < cost:
		return "金币不足（需 %d）" % cost
	gold -= cost
	advance_week()
	return ""


## 出战上限。战斗层只认 rank 0–3（目标掩码是 4 位），
## 所以这里必须硬夹住，不能靠调用方自觉。
const PARTY_MAX: int = 4


## 默认出战名单：按名册顺序取前 4 个能出战的人（活着且不忙）。
func default_party() -> Array:
	var avail: Array = selectable_ids()
	return avail.slice(0, mini(PARTY_MAX, avail.size()))


func alive_ids() -> Array:
	var out: Array = []
	for hid in _order:
		var r: Dictionary = roster.get(str(hid), {})
		if bool(r.get("alive", false)):
			out.append(str(hid))
	return out


# ============================================================
# 决心等级（M25）
# ============================================================
#
# 这一节补的是「人往上走」那根轴。没有它的时候，难度的唯一来源是
# 玩家自己愿意挑多难的本，所以最优解永远是「顶满装备打最简单的图」。
#
# 三个问题在这里回答：
#   · 这个人现在几级、还差多少经验（resolve_of / xp_to_next）
#   · 他能穿几阶装备（gear_cap）
#   · 他能进哪个等级的本、进不去要付什么代价（can_join / entry_stress）

## 旧档没有 resolve 字段时怎么补。
##
## 按装备阶反推：gear 0 → 1 级，gear 4 → 5 级。原版里「能穿第 N 阶装备」
## 本来就等价于「至少 N 级」，所以这个反推不是猜，是同一条规则的逆运算。
## 一律补 1 会让老档当场穿不上自己身上的装备——那是没收进度，不是兼容。
func _resolve_from_save(row: Dictionary) -> int:
	if row.has("resolve"):
		return clampi(int(row["resolve"]), 1, MAX_RESOLVE)
	return clampi(int(row.get("gear", 0)) + 1, 1, MAX_RESOLVE)


func resolve_of(hid: String) -> int:
	return clampi(int((roster.get(hid, {}) as Dictionary).get("resolve", 1)), 1, MAX_RESOLVE)


## 当前等级内已攒的经验（不是累计值）。满级后固定 0。
func xp_of(hid: String) -> int:
	return maxi(0, int((roster.get(hid, {}) as Dictionary).get("xp", 0)))


## 还差多少经验升下一级。满级返回 0。
func xp_to_next(hid: String) -> int:
	var lv: int = resolve_of(hid)
	if lv >= MAX_RESOLVE:
		return 0
	return maxi(0, int(RESOLVE_XP[lv + 1]) - xp_of(hid))


## 加经验，自动连升（一趟给的经验可能跨两级）。返回升了几级。
##
## 满级后经验不再累积：留着会让存档里出现「29/0」这种看不懂的数，
## 而且满级的人也不需要它。
func gain_xp(hid: String, amount: int) -> int:
	if amount <= 0:
		return 0
	var r: Dictionary = roster.get(hid, {})
	if r.is_empty() or not bool(r.get("alive", false)):
		return 0
	var lv: int = resolve_of(hid)
	if lv >= MAX_RESOLVE:
		return 0
	var xp: int = xp_of(hid) + amount
	var up: int = 0
	while lv < MAX_RESOLVE and xp >= int(RESOLVE_XP[lv + 1]):
		xp -= int(RESOLVE_XP[lv + 1])
		lv += 1
		up += 1
	if lv >= MAX_RESOLVE:
		xp = 0
	r["resolve"] = lv
	r["xp"] = xp
	return up


## 这个人最高能穿到第几阶装备（index，0 = 一阶）。
##
## 原版是「第 N 级解锁第 N 阶武器」，我们是 0 基索引，所以再减一。
## 6 级和 5 级一样封顶在 4——原版最高阶装备也只要求 5 级。
func gear_cap(hid: String) -> int:
	return clampi(resolve_of(hid) - 1, 0, MAX_GEAR)


## 装备阶卡在等级上时，返回一句人话给界面用；能升就返回空。
func gear_gate_reason(hid: String) -> String:
	if gear_of(hid) < gear_cap(hid):
		return ""
	# 下一阶是 gear+1，它需要 resolve = gear+2（因为 cap = resolve-1）。
	# 第一版两个数都写成了 gear+2，界面上出现「要 4 级才能穿 4 阶」——
	# 人还在 2 阶，却说 4 阶，读起来像已经跳了两级。
	return "要 %d 级才能穿 %d 阶" % [gear_of(hid) + 2, gear_of(hid) + 1]


## 英雄等级减任务等级。**正数 = 英雄不够格，负数 = 英雄超了。**
func level_gap(hid: String, quest_level: int) -> int:
	return quest_level - resolve_of(hid)


## 能不能进这个等级的本。
##
## 只有一条硬规则：**英雄比任务高 2 级或以上就拒绝**。
## 这是原版切断「回头虐菜」的唯一手段，也是难度必须往上走的根本原因——
## 你不能把练满的人留在低难度里养老，只能往上送或者招新人。
func can_join(hid: String, quest_level: int) -> bool:
	return resolve_of(hid) - quest_level < REFUSE_GAP


## 进本时一次性吃的压力。每低一级 20 点，够格就是 0。
func entry_stress(hid: String, quest_level: int) -> float:
	var low: int = maxi(0, level_gap(hid, quest_level))
	return float(low) * JOIN_STRESS_PER_LEVEL


## 进本之后的受压倍率：每低一级 +25%（M29）。
##
## 和 `entry_stress` 是配套的，原版两条一起写。只做前一条的话，
## 低等级打高级本只是「开局结算一次」，撑过前两场就回本；
## 后一条才是让玩家真正不敢硬上的那个——它跟着你走完整趟。
func stress_mult_for(hid: String, quest_level: int) -> float:
	var low: int = maxi(0, level_gap(hid, quest_level))
	return 1.0 + float(low) * JOIN_STRESS_MULT_PER_LEVEL


## 把任意等级归到 1/3/5 三档里「不超过它的最高档」。
## 自检可以传 --level=2 这种值，直接返回 0 经验会变成「悄悄没加」。
func _xp_tier(level: int) -> int:
	if level >= 5:
		return 5
	if level >= 3:
		return 3
	return 1


## 一趟远征值多少经验。
func quest_xp(level: int, size_name: String, quest_type: String) -> int:
	var row: Dictionary = QUEST_XP.get(_xp_tier(level), {})
	var key: String = "boss" if quest_type == "kill_boss" else size_name
	return int(row.get(key, 0))


## 这趟该给多少经验。
##
## **只有完成才给满**。原版撤退不给经验，这条很重要：否则「进去打两间房、
## 撤退重来」会变成刷级的最优解，难度锁就形同虚设。
##
## 任务打到一半但没达成目标（incomplete）给一半：人确实走到了终点、
## 也确实打了一场硬仗，和「半路逃跑」不是一回事。
## M32 起这条覆盖所有有判据的任务（首领没杀死 / 清剿没清完）。
func xp_for(exp: Expedition) -> int:
	var full: int = quest_xp(exp.dungeon_level, exp.size_name, exp.quest_type)
	match exp.end_reason:
		"complete":
			return full
		"incomplete":
			return int(full / 2)
		_:
			return 0


# ============================================================
# 任务板（M26）
# ============================================================
#
# 原版每周刷新的任务难度「按名册加权」，但永远保底一张学徒本。
# 两件事一起才成立：
#
#   加权      → 你练得越强，摆在你面前的任务越硬（往上赶）
#   保底学徒本 → 新招的人永远有本可打（留退路）
#
# 只做加权会锁死玩家：名册里只剩高级人时，板子上全是 3/5 级，
# 新兵没有任何成长路径。只做保底则等于没做——板子永远那么软。

## 名册能撑到的最高任务等级（按名册里最高的那个人算，**再高一级**）。
##
## 用「最高」而不是「平均」：原版任务板是给整支队伍挑的，
## 平均会被一两个新人拖住，导致练到 5 级的人永远等不到 5 级本。
##
## 再高一级是为了让板子上永远有一个「略微超纲」的选项——
## 高 1 级只是进本吃 20 点压力，不是拒绝。原版就是用这个甜点
## 催玩家往上走的；不给这个选项，板子会永远停在「刚好能打」，
## 玩家没有任何动力多练一级。
func board_ceiling() -> int:
	var top: int = 1
	for hid in alive_ids():
		top = maxi(top, resolve_of(str(hid)))
	top += 1
	if top >= 5:
		return 5
	if top >= 3:
		return 3
	return 1


## 本周等级池：1 / 3 / 5 里，**名册里至少有一个活人能进**的那些。
##
## 这一条同时顶替了原版的两个机制：
##   · 「按名册加权」——名册强了，低档自动从池里消失
##   · 「保底学徒本」的一半——只要名册里有新人，学徒本一定在池里
##
## 为什么不是照抄「永远有学徒本」：原版敢这么定，是因为马车每周能补 1 级新人。
## 我们只有 5 个固定 ID，全员 5 级时硬塞一张学徒本，得到的是
## 「够格 0 人 · 全都超级了」的废卡——四张卡里三张红的，那不是丰富度。
func board_level_pool() -> Array:
	var top: int = board_ceiling()
	var out: Array = []
	for lv in [1, 3, 5]:
		if int(lv) > top:
			continue
		for hid in alive_ids():
			if can_join(str(hid), int(lv)):
				out.append(int(lv))
				break
	if out.is_empty():
		out = [1]
	return out


## 保底档：名册里**最弱**那个人不用吃惩罚就能打的最高档。
##
## 原版保底是「永远一张学徒本」，这里改成「永远一张最弱的人打得动的」。
## 名册是 5/5/1 混编时两者等价（都保底 Lv1）；全员 5 级时前者是废卡，
## 后者才是玩家真正需要的那个难度。
func board_floor_level() -> int:
	if alive_ids().is_empty():
		return 1
	var low: int = MAX_RESOLVE
	for hid in alive_ids():
		low = mini(low, resolve_of(str(hid)))
	var pick: int = 1
	for lv in [1, 3, 5]:
		if int(lv) <= low:
			pick = int(lv)
	return pick


## 名册里有多少人能进这个等级的副本（不看忙闲）。
##
## 场景层的「够格 N 人」和任务板的权重都走这一条——
## 两处各算一遍的话，改规则时只会改一处，另一处就变成旧口径。
func fit_count(level: int) -> int:
	var n: int = 0
	for hid in alive_ids():
		if can_join(str(hid), int(level)):
			n += 1
	return n


## 池里每一档的权重。
##
## 两件事同时影响：名册相对这一档的强度（越接近上限越常见），
## 以及**凑不凑得够一队**——凑不够 4 人的档玩家根本出发不了，
## 它只提供信息（「你名册结构不对」），不提供选择，所以权重压到底。
func _level_weight(level: int) -> int:
	var gap: int = board_ceiling() - level
	var w: int = 4
	if gap > 2:
		w = 1
	elif gap > 0:
		w = 3
	if fit_count(level) < PARTY_MAX:
		w = 1
	return w


func _weighted_pick(pool: Array) -> int:
	var weights: Array = []
	var total: int = 0
	for lv in pool:
		var w: int = _level_weight(int(lv))
		weights.append(w)
		total += w
	if total <= 0:
		return int(pool[0]) if not pool.is_empty() else 1
	var roll: int = randi() % total
	for i in weights.size():
		roll -= int(weights[i])
		if roll < 0:
			return int(pool[i])
	return int(pool[0])


## 重抽任务板。新档、每周推进、读旧档时都调。
##
## 规则一句话：**一个槽给名册里最弱的人，剩下的槽给主力队伍。**
##
## 那句「最弱的」就是原版的学徒本保底，只是换成按名册算而不是写死 Lv1
## （理由见 board_level_pool）。剩下的槽从「能凑够一队」的档里抽——
## 凑不够 4 人的档玩家点了也走不了，占三格只会让人以为游戏坏了。
##
## M32 起是**四个区域各抽一块**：等级按同一份名册算，但各自独立掷，
## 所以「weald 刷出一张学徒本、cove 全是冠军本」是正常结果。
## 每块板子都满足「至少一格是保底档」——保底是**区域级**的，
## 不是「四块板子加起来有一格」，否则玩家换个区域就没有出路了。
func roll_board() -> void:
	boards = {}
	for region in BOARD_REGIONS:
		boards[str(region)] = _roll_region_slots(str(region))
	_sync_board()


## 抽一个区域的四格。
func _roll_region_slots(region: String) -> Array:
	var pool: Array = board_level_pool()
	var floor_lv: int = board_floor_level()
	var runnable: Array = []
	for lv in pool:
		if fit_count(int(lv)) >= PARTY_MAX:
			runnable.append(int(lv))
	var src: Array = runnable if not runnable.is_empty() else pool
	# 保底档随机落在某一格，而不是永远钉在第一格：
	# 钉死的话「短途」就等于「入门」，其他三种尺寸永远拿不到低难度。
	var floor_slot: int = randi() % BOARD_SLOTS.size()

	var out: Array = []
	var slots: Array = board_slots_for(region)
	for i in slots.size():
		var slot: Array = slots[i]
		var pick: int = floor_lv if i == floor_slot else _weighted_pick(src)
		out.append({
			"size": str(slot[0]),
			"quest": str(slot[1]),
			"level": pick,
			"region": region,
		})
	return out


## 这个区域的槽位表。没配的区域退回 M26 那四格，方便只关心一个区域的测试。
static func board_slots_for(region: String) -> Array:
	var s: Array = BOARD_SLOTS_BY_REGION.get(region, [])
	return s if not s.is_empty() else BOARD_SLOTS


## 某区域的板子（只读）。没抽过返回空数组，调用方自己决定怎么兜底。
func board_for(region: String) -> Array:
	return boards.get(region, [])


## 切换当前区域。城镇上那排区域按钮走这里。
func select_board_region(region: String) -> void:
	if not BOARD_REGIONS.has(region):
		return
	board_region = region
	_sync_board()


## 把 `board` 指向当前区域的那份。**不能复制**：复制之后界面上改的
## 和存档里存的会是两份东西，症状是「换个区域再换回来，选的难度没了」。
func _sync_board() -> void:
	board = boards.get(board_region, [])


## 这周的板子里有没有玩家真能打的（够格人数 > 0）。
##
## 整块板子都打不了是会发生的：名册全员 5 级而保底槽是学徒本时，
## 那张卡对谁都是「拒绝参战」。这时候城镇必须明说「去招人」，
## 否则玩家会以为是 bug。
func board_has_runnable() -> bool:
	for b in board:
		var lv: int = int((b as Dictionary).get("level", 1))
		for hid in alive_ids():
			if can_join(str(hid), lv):
				return true
	return false


# ============================================================
# 技能组（M19）
# ============================================================

## 默认技能组。判定在 `SkillLoadout` 里（bench 也要用同一套）。
##
## 返回空数组 = 全装：不可选职业（憎恶），或者这张表还没注入。
##
## 注意传进去的是**职业 id**（M34）：技能表按职业建，两个十字军共用一份。
func _default_loadout(hid: String) -> Array:
	return SkillLoadout.default_for(skill_table, cfg, def_of(hid))


## 读档时的技能组：合法的留下，非法的丢掉，空了或超了就回默认。
func _loadout_or_default(hid: String, raw: Variant) -> Array:
	return SkillLoadout.sanitize(skill_table, cfg, def_of(hid), raw)


## 这个英雄这一趟带哪几个技能。空 = 全装（不可选职业）。
func equipped_skills(hid: String) -> Array:
	var row: Dictionary = roster.get(hid, {})
	var got: Array = row.get("skills", [])
	if got.is_empty():
		return _default_loadout(hid)
	return got.duplicate()


## 技能栏有几个格子。不可选职业返回它自己的技能总数（7）。
func skill_slot_max(hid: String) -> int:
	return SkillLoadout.max_slots(skill_table, def_of(hid))


## 这个职业能不能自己选技能（M31）。
##
## 憎恶是变身职业：`heroes.json` 里 `can_select_combat_skills = false`，
## 7 个技能全开、不进技能组。界面上必须能区分「他没选」和「他不用选」，
## 否则公会屏会显示「已装备 0 / 7」加七个「未装备」——正好是反的意思。
func skill_selectable(hid: String) -> bool:
	return (skill_table.get(def_of(hid), {}) as Dictionary).get("can_select", false) == true


## 所有可选技能 id（公会用）。
func skill_choices(hid: String) -> Array:
	return ((skill_table.get(def_of(hid), {}) as Dictionary).get("ids", []) as Array).duplicate()


## 改技能组。返回空串 = 成功，否则是给玩家看的原因。
##
## 校验放在这里而不是界面里：界面只是画按钮的，换个入口（自检、将来的存档编辑）
## 不该能绕过上限——M18「1 人队出发」就是只在界面层做判断，结果被另一条路径绕过去了。
func set_skills(hid: String, ids: Array) -> String:
	if not roster.has(hid):
		return "名册里没有这个人"
	if not bool((roster[hid] as Dictionary).get("alive", true)):
		return "这个人已经阵亡"
	var rule: Dictionary = skill_table.get(def_of(hid), {})
	if rule.get("can_select", false) != true:
		return "这个职业不能换技能"
	var allowed: Array = rule.get("ids", [])
	var clean: Array = []
	for sid in ids:
		var s: String = str(sid)
		if not allowed.has(s):
			return "没有技能 %s" % s
		if not clean.has(s):
			clean.append(s)
	if clean.is_empty():
		return "至少带一个技能"
	var max_n: int = int(rule.get("max", 4))
	if clean.size() > max_n:
		return "最多带 %d 个" % max_n
	(roster[hid] as Dictionary)["skills"] = clean
	return ""


## 给远征层用的整份技能组（hid -> Array）。只含 roster 里有的人。
func loadout_map(heroes: Array = []) -> Dictionary:
	var out: Dictionary = {}
	var who: Array = heroes if not heroes.is_empty() else _order
	for hid in who:
		var k: String = str(hid)
		if roster.has(k):
			out[k] = equipped_skills(k)
	return out


func gear_of(hid: String) -> int:
	return int((roster.get(hid, {}) as Dictionary).get("gear", 0))


func skill_of(hid: String) -> int:
	return int((roster.get(hid, {}) as Dictionary).get("skill", 0))


# ============================================================
# 怪癖（M14）
# ============================================================

## 某英雄名下的怪癖。旧档没有这个字段时返回空数组。
func quirks_of(hid: String) -> Array:
	return (roster.get(hid, {}) as Dictionary).get("quirks", [])


## 全队的怪癖快照，交给远征层灌进去。
## 只给这一趟出发的人——没上路的英雄不会在别处中招。
func quirk_map_for(ids: Array) -> Dictionary:
	var out: Dictionary = {}
	for hid in ids:
		out[str(hid)] = quirks_of(str(hid)).duplicate()
	return out


## 「升级更便宜」类怪癖（weapon / armour 两个子类）。
##
## 原表把折扣分成武器和护甲两份，本作的升级是**一个**装备阶，
## 没有武器/护甲之分。合成一个总折扣是有损的，但方向对：
## 玩家感受到的是「这个人会砍价，升他更便宜」。
## 上限压在 40%——不封顶的话叠到几件就白送了。
# ============================================================
# 商店（M16）
# ============================================================

## 掷一批新上架。`seed_override` 只给测试用——线上走 `shop_seed`。
##
## 排除「仓库里已有的唯一件」：limit=1 的件重复上架，玩家买回来也戴不上
## （同名上限会挡住第二件进仓库），那等于花钱买一个失败。
func refresh_shop(seed_override: int = 0) -> void:
	shop_stock = []
	if shop == null:
		shop_refused["no_shop"] = int(shop_refused.get("no_shop", 0)) + 1
		return
	if seed_override != 0:
		shop_seed = seed_override
	elif shop_seed == 0:
		shop_seed = randi()
	var rng: DdRng = DdRng.new(shop_seed)
	var owned: Array = []
	for t in owned_trinket_ids():
		var tid: String = str(t)
		if trinket_lib != null and trinket_lib.is_loaded() and trinket_lib.limit_of(tid) == 1:
			owned.append(tid)
	shop_stock = shop.roll_stock(rng, Shop.STOCK_SIZE, owned)


## 换一批货架（花钱刷新）。DD1 里这是「下周再来看看」的等价物。
func reroll_shop() -> bool:
	shop_seed = randi()
	refresh_shop()
	return not shop_stock.is_empty()


func shop_price_at(idx: int) -> int:
	if idx < 0 or idx >= shop_stock.size() or shop == null:
		return 0
	return shop.trinket_buy_price(str(shop_stock[idx]))


## 买货架上第 idx 件。成功返回 ""，否则是原因。
##
## 顺序很重要：**先判能不能装进仓库，再扣钱**。反过来的话，
## 「钱扣了但仓库满了」会变成一件无法申诉的事——玩家只会觉得游戏坏了。
func buy_shop_trinket(idx: int) -> String:
	if idx < 0 or idx >= shop_stock.size():
		return "no_such_item"
	var id: String = str(shop_stock[idx])
	var price: int = shop_price_at(idx)
	if price <= 0:
		return "not_for_sale"
	if gold < price:
		shop_refused["no_gold"] = int(shop_refused.get("no_gold", 0)) + 1
		return "no_gold"
	if not can_add_trinket(id):
		shop_refused["limit"] = int(shop_refused.get("limit", 0)) + 1
		return "limit"
	if store_free() <= 0:
		shop_refused["store_full"] = int(shop_refused.get("store_full", 0)) + 1
		return "store_full"
	gold -= price
	trinket_store.append(id)
	# 买走的格子留空，而不是让后面的往前挤：货架是「格子」不是「列表」，
	# 挤上去会让玩家眼睁睁看着自己没买的那件变了位置。
	shop_stock[idx] = ""
	return ""


## 卖仓库里的第 store_idx 件。
## 不卖身上的——卸装是两步操作（先卸再卖），合成一步容易手滑。
func sell_trinket(store_idx: int) -> String:
	if store_idx < 0 or store_idx >= trinket_store.size():
		return "no_such_item"
	var id: String = str(trinket_store[store_idx])
	if shop == null:
		return "no_shop"
	var gain: int = shop.trinket_sell_price(id)
	trinket_store.remove_at(store_idx)
	gold += gain
	return ""


## 一套补给的报价与结账。补给**不进元层仓库**——买完直接进这一趟的背包。
##
## 返回 `{ok, cost, reason}`；`ok` 为 true 时金币已扣。
func buy_pack(pack: Dictionary) -> Dictionary:
	var out: Dictionary = {"ok": false, "cost": 0, "reason": ""}
	if shop == null:
		out["reason"] = "no_shop"
		return out
	# 数量要在上限之内，否则玩家能买 99 根火把带进去
	for k in pack.keys():
		var n: int = int(pack[k])
		if n <= 0:
			continue
		var lim: int = shop.supply_limit(str(k))
		if lim > 0 and n > lim:
			out["reason"] = "over_limit"
			out["item"] = str(k)
			return out
	var cost: int = shop.pack_cost(pack)
	out["cost"] = cost
	if cost <= 0:
		out["ok"] = true
		return out
	if gold < cost:
		out["reason"] = "no_gold"
		shop_refused["pack_no_gold"] = int(shop_refused.get("pack_no_gold", 0)) + 1
		return out
	gold -= cost
	out["ok"] = true
	return out


# ============================================================
# 饰品（M15）
# ============================================================

## 手上所有的饰品 id：仓库里的 + 已经戴在别人身上的。
##
## 同名上限（`limit`）要按**总量**判——否则「仓库两件、身上两件」
## 就能绕过 limit=3。这个函数的存在就是为了别再写出只看一半的检查。
func owned_trinket_ids() -> Array:
	var out: Array = trinket_store.duplicate()
	for hid in roster.keys():
		for t in ((roster[hid] as Dictionary).get("equipped", []) as Array):
			if not str(t).is_empty():
				out.append(str(t))
	return out


func trinket_count(id: String) -> int:
	var n: int = 0
	for t in owned_trinket_ids():
		if str(t) == id:
			n += 1
	return n


func equipped_of(hid: String) -> Array:
	return ((roster.get(hid, {}) as Dictionary).get("equipped", []) as Array)


## 仓库还剩几格。装备中的件不占仓库，所以这里只算 trinket_store。
func store_free() -> int:
	return maxi(0, store_slots - trinket_store.size())


## 这件能不能再拿一件？同名上限以 `limit` 为准：0 = 不限，1 = 唯一。
## 缺表时一律放行——宁可多给，也不要因为没注入数据把功能变成死的。
func can_add_trinket(id: String) -> bool:
	if id.is_empty():
		return false
	if trinket_lib != null and trinket_lib.is_loaded():
		var lim: int = trinket_lib.limit_of(id)
		if lim > 0 and trinket_count(id) >= lim:
			return false
	return true


## 新拿到一件饰品，放进仓库。返回 "" 表示成功，否则是拒绝原因。
##
## 拒绝原因要留痕（`trinket_refused`）：M13/M14 都是「静默丢弃」
## 拖掉了半天工期，这次一开头就把失败计数摆出来。
func add_trinket(id: String) -> String:
	var reason: String = ""
	if id.is_empty():
		reason = "empty_id"
	elif not can_add_trinket(id):
		reason = "limit"
	elif store_free() <= 0:
		# 仓库满不等于「该扔」：先把件留在仓库外，由调用方决定
		# （现在的策略是丢弃并计数，因为本作还没有商店/熔毁）。
		reason = "store_full"
	if reason.is_empty():
		trinket_store.append(id)
		return ""
	trinket_refused[reason] = int(trinket_refused.get(reason, 0)) + 1
	return reason


## 一次掉落的批量入账。返回实际进仓库的 id 列表（结算屏要用）。
func add_trinkets(ids: Array) -> Array:
	var got: Array = []
	for t in ids:
		var tid: String = str(t)
		if tid.is_empty():
			continue
		if add_trinket(tid) == "":
			got.append(tid)
	return got


## 这件能不能给这个英雄戴。职业限制来自 `hero_class_requirements`
## （空数组 = 谁都能戴）。79 件有职业限制，配错会变成「给了但穿不上」。
func can_equip(hid: String, id: String) -> bool:
	if not roster.has(hid) or id.is_empty():
		return false
	if not bool((roster[hid] as Dictionary).get("alive", true)):
		return false
	if equipped_of(hid).size() >= equip_slots:
		return false
	if trinket_lib != null and trinket_lib.is_loaded() and not trinket_lib.fits_class(id, def_of(hid)):
		return false
	return true


## 把仓库里的一件装到某个英雄身上。成功返回 ""，否则是拒绝原因。
func equip_trinket(hid: String, id: String) -> String:
	if not trinket_store.has(id):
		return "not_in_store"
	if not can_equip(hid, id):
		if equipped_of(hid).size() >= equip_slots:
			return "slots_full"
		if trinket_lib != null and trinket_lib.is_loaded() and not trinket_lib.fits_class(id, def_of(hid)):
			return "class_mismatch"
		return "refused"
	trinket_store.erase(id)
	var row: Dictionary = roster[hid]
	if not row.has("equipped"):
		row["equipped"] = []
	(row["equipped"] as Array).append(id)
	return ""


## 卸下某个英雄身上的第 slot 件，放回仓库。
## 仓库满时**不卸**（返回 "store_full"）——否则这一件会凭空消失。
func unequip_trinket(hid: String, slot: int) -> String:
	var eq: Array = equipped_of(hid)
	if slot < 0 or slot >= eq.size():
		return "no_such_slot"
	if store_free() <= 0:
		return "store_full"
	var id: String = str(eq[slot])
	eq.remove_at(slot)
	trinket_store.append(id)
	return ""


## 装备了哪些件（整队合计）。战斗注入与远征加成用。
func equipped_map() -> Dictionary:
	var out: Dictionary = {}
	for hid in roster.keys():
		var lst: Array = equipped_of(str(hid))
		if not lst.is_empty():
			out[str(hid)] = lst.duplicate()
	return out


func quirk_upgrade_discount() -> float:
	if quirk_lib == null or not quirk_lib.is_loaded():
		return 0.0
	var total: float = 0.0
	for hid in roster.keys():
		for q in quirks_of(str(hid)):
			for b in quirk_lib.buffs_for([str(q)]):
				if str(b.get("stat_type", "")) != "upgrade_discount":
					continue
				# 条件怪癖（in_dungeon 等）在城镇里一律不生效：
				# 城里的语境是「没有地牢、没有战斗」，用空 ctx 判。
				if not quirk_lib.rule_active(b, {}):
					continue
				total += absf(float(b.get("amount", 0.0)))
	return clampf(total, 0.0, 0.4)


## 下一阶的价格；已满阶返回空字典（空 = 不能再升）
##
## 返回的是**副本**：原表要原样留着，否则折扣会一层层叠进配置里，
## 升几次之后价格就永久变了。
func upgrade_cost(hid: String) -> Dictionary:
	var g: int = gear_of(hid)
	if g >= MAX_GEAR:
		return {}
	# 等级不够就升不上去（M25）。这是**准入**问题不是价格问题，
	# 所以和「已满阶」一样返回空字典，具体原因由 gear_gate_reason 给。
	# 界面上两个「不能升」必须显示成两句话，否则玩家会以为只是钱不够。
	if g >= gear_cap(hid):
		return {}
	var table: Array = (cfg.get("costs", {}) as Dictionary).get("upgrade", [])
	if g >= table.size():
		return {}
	var row: Dictionary = (table[g] as Dictionary).duplicate(true)
	var disc: float = quirk_upgrade_discount()
	if disc > 0.0 and row.has("gold"):
		row["gold"] = maxi(1, int(round(float(row["gold"]) * (1.0 - disc))))
	return row


func can_upgrade(hid: String) -> bool:
	var r: Dictionary = roster.get(hid, {})
	if not bool(r.get("alive", false)):
		return false
	var cost: Dictionary = upgrade_cost(hid)
	return not cost.is_empty() and can_afford(cost)


func upgrade(hid: String) -> bool:
	if not can_upgrade(hid):
		return false
	if not pay(upgrade_cost(hid)):
		return false
	var r: Dictionary = roster[hid]
	r["gear"] = int(r["gear"]) + 1
	r["skill"] = int(r["skill"]) + 1
	return true


func recruit_cost() -> Dictionary:
	return (cfg.get("costs", {}) as Dictionary).get("recruit", {"gold": 1000, "heirlooms": {"crest": 4}})


## 实际要付的价格。
##
## 全员阵亡之后会发一批「免费征召额度」——这是破产保护，不是仁慈：
## 没有它，玩家会在「没人能出征、也没钱招募」的死局里彻底卡住，而存档不会自己回退。
## 额度按人头一次性发满，是因为只补一个人的话下一趟必死，
## 等于让玩家亲手把死循环演一遍。
func effective_recruit_cost(hid: String) -> Dictionary:
	if free_recruits > 0:
		return {}
	return recruit_cost()


func _alive_count() -> int:
	var n: int = 0
	for hid in _order:
		if bool((roster.get(str(hid), {}) as Dictionary).get("alive", false)):
			n += 1
	return n


func can_recruit(hid: String) -> bool:
	var r: Dictionary = roster.get(hid, {})
	if r.is_empty() or bool(r.get("alive", false)):
		return false
	return can_afford(effective_recruit_cost(hid))


func recruit(hid: String) -> bool:
	if not can_recruit(hid):
		return false
	if free_recruits > 0:
		free_recruits -= 1
	elif not pay(recruit_cost()):
		return false
	var r: Dictionary = roster[hid]
	r["alive"] = true
	r["stress"] = 0.0
	r["deaths"] = int(r.get("deaths", 0))   # 战绩保留
	# 招募回来的是**新人**，不是复活的老人（M25）。
	#
	# 等级和装备一起归零：原版里英雄死了就是永久失去，招来的是另一个
	# 1 级英雄。不归零会死锁——5 个人全练到 6 级后只能打冠军本，
	# 团灭再招回来还是 6 级，存档就卡死在必死循环里，没有退路。
	#
	# **怪癖不清**：原版没有这个问题是因为「招来的是别人」，我们只有
	# 5 个固定 ID，重招的是同一个人。清空怪癖会造出「故意送死洗负面」
	# 的漏洞——那比「新人带着旧怪癖」这种不精确要糟得多。
	r["resolve"] = 1
	r["xp"] = 0
	r["gear"] = 0
	r["skill"] = 0
	r["skills"] = _default_loadout(hid)
	return true


# ============================================================
# 名册扩容与招新（M27）
# ============================================================
#
# 在这之前名册是**固定 5 人**：`_order` 只在 new_game 时从配置填一次，
# 之后再没有任何地方往里加人。于是所有「名册结构」的问题都无解——
# M25 的等级断层、M26 的废卡率压不下去，根都在这里：
# 5 个人练到同一档之后，名册就只剩一种强度。
#
# M27 当时 key 就是职业 id，所以「一个职业最多一个人」，名册上限 = 职业总数。
# M34 把 key 换成了实例 id（`crusader#2`），这条限制才解开——
# 名册上限从此是**人头数**，不是职业数。

func roster_max() -> int:
	# 名册上限（M34）：原来是「职业总数」（因为 key 就是职业 id），
	# 现在同职业能多人，所以它是一个**人头上限**，和职业数量无关。
	# 仍然取 15：城镇名册两列 15 格的排版（M31）是按这个数排的。
	return ROSTER_HARD_MAX


## 名册满了没有。
##
## 按**活人**数算，不是 `_order.size()`（M28）：死掉的人还留在 `_order` 里
## （墓园要记），如果他们也占名额，一个团灭过两轮的档会永远招不进新人——
## 名册上写着 15、实际能出征的只有 3 个。
func roster_full() -> bool:
	return alive_ids().size() >= roster_max()


## 马车能摆出哪些职业。
##
## M27 时这里是「还没入册的职业」——因为名册 key 就是职业 id，一个职业只能一个人。
## M34 起同职业可以多人，所以**池子就是全部已知职业**：你名册里已经有两个修女，
## 马车照样可以再摆一个修女出来。这也是原版的行为。
func hireable_pool() -> Array:
	return known_heroes.duplicate()


## 马车本周的新面孔：从全部职业里抽 2 个**不同**的职业。
##
## 每周重抽，抽到招走为止。不重复抽已经能招的，
## 否则「同一批人挂一周」会让人以为功能坏了。
##
## M34 起候选可以是名册里已有的职业（同职业多人）——
## 但仍然**一周两个不重复**：同一周摆两个修女没有信息量，只是占格子。
## 「按阵容短板加权」（缺治疗更容易来修女）仍然没做，见 M27 §7。
func roll_recruit_candidates() -> void:
	var pool: Array = hireable_pool()
	recruit_candidates = []
	var n: int = mini(2, pool.size())
	for i in n:
		if pool.is_empty():
			break
		var idx: int = randi() % pool.size()
		recruit_candidates.append(pool[idx])
		pool.remove_at(idx)


## 招新要多少钱。
##
## **只收金币，不收传家宝**（和 `recruit_cost` 不一样）。传家宝只有远征产出、
## 而且建筑升级要吃掉大量；用它卡住招新会让「换个阵容试试」这件事变得不敢做，
## 而招新解锁的是玩法不是数值，不该被稀缺资源锁住。
func hire_cost() -> Dictionary:
	return {"gold": int(recruit_cost().get("gold", 1000)), "heirlooms": {}}


func can_hire(cls: String) -> bool:
	if not recruit_candidates.has(cls):
		return false
	# 同职业多人（M34）：不再要求「这个职业还没入册」。
	# 原来那一条是把「名册 key = 职业 id」这个实现限制泄漏成了游戏规则——
	# 玩家看到的是「马车永远不给我第二个修女」，而不是「代码里字典键不够用」。
	if roster_full():
		return false
	return can_afford(hire_cost())


## 招一个新人入册。
##
## 和 `recruit` 的区别：`recruit` 是**把死掉的人捞回来**（破产保护），
## `hire` 是**往名册里加一个从没见过的人**。
##
## 两条路并存是过渡设计：原版死人不复活，但我们的名册从 5 人起步，
## 直接删掉复活会让 M27 之前的存档里那些死人永远消失。
## 等名册真的够大一局（15 人），复活这条路就可以关掉了。
func hire(cls: String) -> bool:
	if not can_hire(cls):
		return false
	if not pay(hire_cost()):
		return false
	# 实例 id（M34）：同职业第二个起是 `crusader#2`。
	# 名册的 key 从此不再等于职业 id，这一行就是起点。
	var uid: String = next_uid_for(cls)
	roster[uid] = {
		"def": cls,
		"gear": 0, "skill": 0, "alive": true,
		"stress": 0.0, "runs": 0, "deaths": 0,
		# 新人和新档一样掷开局怪癖：原版的新英雄不是白纸，
		# 而「招来的人是干净的」会变成一条洗怪癖的捷径。
		"quirks": _roll_start_quirks(cls, DdRng.new(randi())),
		"equipped": [],
		"skills": _default_loadout(uid),
		"busy": 0,
		"resolve": 1, "xp": 0,
	}
	_order.append(uid)
	# 招走的是**这一周的这张卡**，不是这个职业。
	# 下周马车会重新抽——同职业还能再来一次，那正是 M34 想要的效果。
	recruit_candidates.erase(cls)
	return true


# ============================================================
# 解雇（M28）
# ============================================================
#
# M27 让名册能扩到 15 人，但只能加不能减——满了就没法换人，
# 练废的人也只能一直占着位置。解雇补的就是这条出口。
#
# 原版的规则：免费，但你在那个人身上投入的等级和装备**全部归零**。
# 这正好是 M25「招募=新人」的同一条逻辑：这个 ID 代表的不是
# 「某个具体的英雄」，而是「名册上的一个位置」。

## 能不能解雇。
##
## 唯一的硬限制是**至少留一个活人**。这不是数值平衡，是防锁死：
## 名册空了之后如果金币也不够招人，这个档就再也走不动了，而存档不会自己回退。
## 原版没这个限制是因为马车永远有货、而且便宜；我们的招新要 1000 金币。
func can_dismiss(hid: String) -> bool:
	if not roster.has(hid):
		return false
	# 忙的人不能解雇：他这周还在疗养院里，人走了那笔钱算什么？
	# 放进 can_dismiss 而不是 dismiss 里，是为了让按钮直接灰掉——
	# 可点但点了报错，玩家会以为是 bug。
	if busy_of(hid) > 0:
		return false
	var alive: bool = bool((roster[hid] as Dictionary).get("alive", true))
	# 死人本来就不占出征名额，随时可以清记录；活人才要守那条底线
	if alive and alive_ids().size() <= 1:
		return false
	return true


## 解雇。解雇死人 = 从墓园里删掉这条记录。
func dismiss(hid: String) -> bool:
	if not can_dismiss(hid):
		return false
	roster.erase(hid)
	_order.erase(hid)
	# 不清马车候选（M34）：那里放的是**职业**，不是人。
	# 赶走一个十字军不等于「本周不卖十字军」——想再招一个随时可以。
	return true


# ============================================================
# 建筑（M22）
# ============================================================
#
# 原版八座建筑在这里分两类：
#
#   **只是换个入口**：马车（招募）、铁匠铺（升级装备）、公会（技能组，M19 已有）、
#   饰品车（饰品 + 补给商店，M15/M16 已有）。这些的逻辑一行没改，
#   只是按钮从英雄卡上搬进建筑里——城镇屏原来同时摆着「5 张卡 + 4 张难度卡 +
#   3 个按钮 + 2 行说明」，那不是信息多，是没分层。
#
#   **补规则缺口的**：疗养院、修道院、酒馆。这三座是这一期真正的工作量：
#   M14 的 `cure` 从做出来就没人调用（疾病只能靠奇物清），
#   而回城减压是写死的 40 点（`town_stress_relief`），玩家没有任何选择。
#
# 墓园只做展示：从 roster 的 `deaths` 读，不新增数据结构。
# 真正的「阵亡记录」（谁死在哪一趟、什么原因）需要结算时落盘，
# 那是另一期的事——先不要为了填满八座建筑编一个半成品。

func _bcfg() -> Dictionary:
	return cfg.get("buildings", {})


func disease_cost() -> int:
	return int(_bcfg().get("disease_cost", 600))


func quirk_cost() -> int:
	return int(_bcfg().get("quirk_cost", 350))


## 这个人身上的疾病。
func diseases_of(hid: String) -> Array:
	var out: Array = []
	if quirk_lib == null:
		return out
	for q in quirks_of(hid):
		if quirk_lib.is_disease(str(q)):
			out.append(str(q))
	return out


## 负面怪癖（不含疾病——疾病在疗养院是另一条更贵的项目）。
func negative_quirks_of(hid: String) -> Array:
	var out: Array = []
	if quirk_lib == null:
		return out
	for q in quirks_of(hid):
		var qid: String = str(q)
		if quirk_lib.is_disease(qid):
			continue
		if quirk_lib.slot_kind(qid) == "negative":
			out.append(qid)
	return out


## 治病。返回空串 = 成功。
##
## 只治一条：一次一条是原版的做法，也是唯一能让「钱不够」变成真实取舍的做法。
## 一次治全部的话，疗养院就退化成一个「点一下」的按钮。
func treat_disease(hid: String) -> String:
	var why: String = _busy_guard(hid)
	if not why.is_empty():
		return why
	var ds: Array = diseases_of(hid)
	if ds.is_empty():
		return "没有疾病要治"
	var cost: int = disease_cost()
	if gold < cost:
		return "金币不足（需 %d）" % cost
	var row: Dictionary = roster[hid]
	var lst: Array = (row.get("quirks", []) as Array).duplicate()
	lst.erase(ds[0])
	row["quirks"] = lst
	gold -= cost
	# 占一周（M23）：这一周他不能出征。效果立即生效，代价是时间。
	row["busy"] = 1
	return ""


## 去掉一条负面怪癖。返回空串 = 成功。
func purge_quirk(hid: String) -> String:
	var why: String = _busy_guard(hid)
	if not why.is_empty():
		return why
	var ns: Array = negative_quirks_of(hid)
	if ns.is_empty():
		return "没有负面怪癖要清"
	var cost: int = quirk_cost()
	if gold < cost:
		return "金币不足（需 %d）" % cost
	var row: Dictionary = roster[hid]
	var lst: Array = (row.get("quirks", []) as Array).duplicate()
	lst.erase(ns[0])
	row["quirks"] = lst
	gold -= cost
	row["busy"] = 1
	return ""


## 减压建筑。两种的差别是「便宜但少」和「贵但多」——
## 原版靠每周次数限制区分，我们没有周次系统，只能用性价比区分。
func rest_options() -> Array:
	var out: Array = []
	for r in (_bcfg().get("rest", []) as Array):
		if r is Dictionary:
			out.append((r as Dictionary).duplicate())
	return out


func rest_option(bid: String) -> Dictionary:
	for r in rest_options():
		if str((r as Dictionary).get("id", "")) == bid:
			return r
	return {}


## 在一个减压建筑里待一次。返回空串 = 成功。
func rest_at(bid: String, hid: String) -> String:
	var opt: Dictionary = rest_option(bid)
	if opt.is_empty():
		return "没有这座建筑"
	var why: String = _busy_guard(hid)
	if not why.is_empty():
		return why
	var row: Dictionary = roster[hid]
	var cur: float = float(row.get("stress", 0.0))
	if cur <= 0.01:
		return "压力已经是 0 了"
	var cost: int = int(opt.get("cost", 0))
	if gold < cost:
		return "金币不足（需 %d）" % cost
	var relief: float = float(opt.get("relief", 0))
	row["stress"] = clampf(cur - relief, 0.0, 200.0)
	gold -= cost
	# 占一周（M23）：这一周他不能出征。效果立即生效，代价是时间。
	row["busy"] = 1
	return ""


## 墓园：只看，不改。按阵亡次数排，死的多的在前。
func graveyard() -> Array:
	var out: Array = []
	for hid in _order:
		var r: Dictionary = roster.get(str(hid), {})
		var deaths: int = int(r.get("deaths", 0))
		if deaths <= 0:
			continue
		out.append({"hero": str(hid), "deaths": deaths, "alive": bool(r.get("alive", false)),
			"runs": int(r.get("runs", 0)), "gear": int(r.get("gear", 0))})
	out.sort_custom(func(a, b): return int(a["deaths"]) > int(b["deaths"]))
	return out


# ============================================================
# 结算：把一趟远征的结果落到档里
# ============================================================

## 返回本次结算摘要，给结算屏显示用。
func settle(exp: Expedition) -> Dictionary:
	var out: Dictionary = {
		"gold": 0, "heirlooms": {}, "deaths": [], "stress_left": 0.0,
		"reason": exp.end_reason, "relief": int(cfg.get("town_stress_relief", 40)),
		"quirks": 0, "diseases": 0,
	}
	for k in heirlooms.keys():
		out["heirlooms"][k] = 0

	out["gold"] = int(exp.loot_gold)
	for k in (exp.loot_heirlooms as Dictionary).keys():
		out["heirlooms"][str(k)] = int(exp.loot_heirlooms[k])
	# 宝石的钱已经折算进 loot_gold（见 Expedition._apply_loot_result），
	# 这里只把「件数」带出来给结算屏展示。
	out["gems"] = (exp.loot_gems as Dictionary).duplicate()
	# 饰品真正入仓库。之前只记件数——件数进了结算屏，东西没进游戏。
	# 拒绝的（仓库满/超同名上限）不会静默消失，count 留在 trinket_refused 里。
	out["trinket_ids"] = add_trinkets(exp.loot_trinket_ids)
	out["trinkets"] = (out["trinket_ids"] as Array).size()
	# 被拒的不静默消失：件数对不上就记在这里。夹 0 是因为
	# `loot_trinkets` 只统计「有 id 的」掉落，理论上不会小于进仓库数——
	# 真小于了说明上游账错了，报负数只会让结算屏出现 -1 件这种鬼话。
	out["trinkets_dropped"] = maxi(0, int(exp.loot_trinkets) - int(out["trinkets"]))
	out["quirks"] = int(exp.stats.get("quirks_gained", 0))
	out["diseases"] = int(exp.stats.get("diseases_contracted", 0))
	add_loot(int(out["gold"]), out["heirlooms"])

	# 决心经验（M25）。**每个活着回来的人拿同样的量**——
	# 原版也是全队平分经验，不是「杀得多的人拿得多」：
	# 后者会让辅助职业永远升不了级，而治疗恰恰是最需要等级的抗性。
	var gained_xp: int = xp_for(exp)
	out["xp"] = gained_xp
	out["levelups"] = {}

	for hid in exp.hero_ids:
		var hid_s: String = str(hid)
		var r: Dictionary = roster.get(hid_s, {})
		if r.is_empty():
			continue
		var s: Dictionary = exp.state.get(hid_s, {})
		r["runs"] = int(r.get("runs", 0)) + 1
		# 怪癖跟人走，不跟远征走：一趟里染的病回城还在，
		# 除非去医院治。这和「压力回城减一部分」是两个不同的设计取舍——
		# 压力是消耗品，怪癖是人物的一部分。
		r["quirks"] = exp.quirks_of(hid_s).duplicate()
		if exp.is_dead(hid_s):
			r["alive"] = false
			r["deaths"] = int(r.get("deaths", 0)) + 1
			r["stress"] = 0.0
			out["deaths"].append(hid_s)
		else:
			# 回城只减一部分：压力跨远征累积，是「再打一趟要不要换人」的决策依据
			var relief: float = float(out["relief"])
			r["stress"] = clampf(float(s.get("stress", 0.0)) - relief, 0.0, 200.0)
			out["stress_left"] = maxf(float(out["stress_left"]), float(r["stress"]))
			# 死人拿不到经验（原版也是），所以这条路只在活着的人身上走
			var ups: int = gain_xp(hid_s, gained_xp)
			if ups > 0:
				out["levelups"][hid_s] = ups

	expeditions += 1
	# 一趟 = 一周（M23）。忙的人在这里少忙一周，商店也在这里换货——
	# 时间推进只有 `advance_week` 这一个入口。
	advance_week()
	# 图模式下 step_index 是「消耗掉的待结算步骤数」（走廊一步 + 房间内容一步），
	# 和玩家看到的「走了几间房」不是一个数。成绩必须用后者，否则同一趟远征
	# 在结算屏和城镇屏会显示成两个不同的数字。
	var advance: int = int(exp.step_index)
	if exp.map_mode:
		advance = int(exp.stats.get("rooms_visited", 0))
	best_steps = maxi(best_steps, advance)
	# 全员阵亡 → 发一批免费征召额度，保证这档还能继续玩下去。
	#
	# 额度是「够凑一队 + 1」而不是「名册人数」（M27）：名册 15 人时
	# 发 15 个免费名额，等于「全员阵亡没有代价」——那比破产保护慷慨太多了。
	# 5 人名册时两者相等（PARTY_MAX+1 = 5），旧行为一字不变。
	if _alive_count() == 0:
		free_recruits = mini(_order.size(), PARTY_MAX + 1)
		out["free_recruits"] = free_recruits
	return out

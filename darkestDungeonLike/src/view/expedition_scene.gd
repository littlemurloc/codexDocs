extends Control
## 可玩的远征循环：出发 → 地图 → 战斗 → 结算。
##
## 为什么要有这一层：M1/M2/M3 都是「测量」，能证明规则对、数值成立，
## 但证明不了「有没有人愿意再打一趟」。那件事只能让人真的玩一次才知道。
##
## 设计约束（刻意的）：
##   1. 全程自绘，不用任何外部素材 —— 换美术时不需要重写布局
##   2. 不做地图生成、不做城镇、不做饰品 —— 只做「一趟远征」的最小闭环
##   3. 所有规则都来自 src/core，这里一格判定都不写
##
## 操作：
##   鼠标点按钮 / 点敌人 = 选技能与目标
##   空格 = 自动代打一回合（调试用）   F = 点火把   C = 休整   Esc = 撤退
##
## 自检用参数：
##   --auto            让 AI 一路代打，用于截图与冒烟
##   --shot=<路径>     第 --shot-at 秒截图后退出

enum { S_TOWN, S_MAP, S_BATTLE, S_RESULT, S_TRINKET, S_PREP, S_SHOP, S_GUILD, S_BUILDING }

const STEP_DELAY: float = 0.34
const LOG_MAX: int = 200

# —— 可选场景 ——
var _dungeon: String = "weald"
var _size: String = "short"
var _level: int = 1
var _preset: String = "standard"

# —— 运行时 ——
var db: DdDb
var exp: Expedition
var _state: int = S_TOWN
## 城镇饰品界面里「正在挑的那一件」。空 = 没选中。
## 有选中时点英雄的空槽＝装上去，否则点槽＝卸下来。
var _sel_trinket: String = ""

## —— 出发准备（M16）——
## 选好的补给。键是 Shop 的 id（食物用 `food`），值是份数。
## 默认给的是「保底包」，和 M13 之前硬编码的默认完全一致——
## 所以第一趟（没钱）的体验和以前一模一样。
var _prep_pack: Dictionary = {}
var _prep_size: String = "short"
var _prep_level: int = 1
## 这次出发带谁。空 = 用 `campaign.default_party()`（名册前 4 个活人）。
var _prep_party: Array = []

## 公会屏当前选中的英雄（M19）。空 = 进屏时自动取名册第一个活人。
var _guild_hero: String = ""
## 准备屏当前的任务类型（M20）：explore / kill_boss。
var _prep_quest: String = "explore"

## —— 城镇建筑（M22）——
##
## 原版八座。前四座是「换个入口」——逻辑 M5/M13/M15/M16/M19 就有了，
## 只是按钮原来散落在英雄卡和右下角；后四座是这一期新写的规则。
##
## `act` 是进屏后右侧给出的动作 id，空表示「进去只有展示或子入口」。
const BUILDINGS: Array = [
	["coach", "马车", "招募"],
	["smith", "铁匠铺", "升级装备"],
	["guild", "公会", "技能组"],
	["sanitarium", "疗养院", "治病 · 清怪癖"],
	["abbey", "修道院", "减压 40"],
	["tavern", "酒馆", "减压 70"],
	["wagon", "商队", "饰品 · 补给"],
	["graveyard", "墓园", "阵亡记录"],
]

var _building: String = ""       ## 当前进的建筑 id
var _building_hero: String = ""  ## 建筑屏里选中的英雄
## 待确认解雇的 hid（M28）。非空时马车上的按钮变成「再点一次确认」。
##
## 自绘 UI 没有弹窗，而解雇是**不可逆且清空投入**的操作——
## 一个按钮点错就把练了十趟的人删了。所以用「点两次」代替确认框：
## 第一次不执行任何事，第二次才真的删。
var _fire_pending: String = ""

## —— 自动代打的走路策略（M18）——
##
## 默认 False = **直奔目标的最短路径**。这条路径是自检的基线，
## 也是「最少步数能走到哪」，但它**不代表玩家**——玩家会绕路拿东西。
##
## 打开之后优先走没去过的、且不增加「到目标距离」的邻居（侧向支线），
## 走完了再回最短路径。用来回答「绕路到底有没有回报」。
var _explore: bool = false
var _seen_rooms: Dictionary = {}
var _battle: Battle = null
var _ev_pos: int = 0
var _exp_ev_pos: int = 0
var _step_timer: float = 0.0
var _options: Array = []
var _pending: Dictionary = {}
var _move_mode: bool = false       # 技能面板切到「选落点」状态
var _show_move_demo: bool = false  # 截屏用：一进战斗就展开落点列表
var _show_guard_demo: bool = false # 截屏用：让守护者守一次后冻住画面
var _guard_demo_done: bool = false
var _move_checked: bool = false    # 自检：站位调整路径是否已跑过
var moved_ok: bool = false         # 自检：那次调整是否真的改变了 rank
var _guard_checked: bool = false   # 自检：守护路径是否已跑过
var guarded_ok: bool = false       # 自检：那次守护是否真的建立了关系
## 自检：整趟里由技能造成的位移 / 洗位次数（M11）。
## 和守护不同，这一项玩家控制不了——怪物推不推人取决于遭遇里有没有带
## 位移技能的怪，所以它只报数，不参与 PASS/FAIL 判定。
var forced_moves: int = 0
var shuffle_moves: int = 0
var move_resists: int = 0
## 自检：整趟里的召唤次数（M12）。同位移，只报数不判 PASS——
## 路上有没有召唤怪由地图决定，不是玩家能选的。
var summons: int = 0
var summon_fails: int = 0
var _font: Font
var _mouse: Vector2 = Vector2.ZERO
var _log: Array = []           # {text, color}
var _floaters: Array = []
var _buttons: Array = []       # {rect, id, enabled, label}
var _slots: Array = []         # {rect, uid, side}
var _room_hits: Array = []     # {rect, id}：地图上能走过去的房间
var _hover_uid: int = -1
var _flash: String = ""
var _flash_life: float = 0.0

# —— 元层 ——
var campaign: Campaign
var _save_path: String = Campaign.DEFAULT_PATH
var _settle_gain: Dictionary = {}
var _settled: bool = false

# —— 自检 ——
var _auto: bool = false
var _auto_map_only: bool = false
var _skip_battles: bool = false   # 调试：战斗瞬间结算，让镜头一直停在地图上
var _step_delay: float = STEP_DELAY
var _auto_start: bool = false
var _to_result: bool = false
var _selftest: bool = false
var _reveal_all: bool = false
var _auto_timer: float = 0.0
var _shot_path: String = ""
var _shot_at: float = 3.0
## 截图/冒烟用：启动后直接停在出发准备屏（`--prep`）。
## 加它是因为「准备屏的布局与门槛」以前只能靠手点验证，改一次要人肉看一次。
var _boot_prep: bool = false
## 同上：启动后直接停在公会屏（`--guild`），用于截图验证技能组界面。
var _boot_guild: bool = false
## 启动时的任务类型（`--quest=kill_boss`），给自检和截图用。
var _boot_quest: String = "explore"
## 启动后直接进某座建筑（`--bld=sanitarium`），给截图用。
var _boot_building: String = ""
## 截图用：直接进建筑、并把解雇按钮置成「待确认」（`--pending-fire`）。
## 「点两次才删」这个交互没法靠静态截图验证，所以给它一个入口。
var _boot_pending_fire: bool = false
## 开发信息开关（M31）：`--dev` 打开。
##
## 界面上有一部分字只有做这个项目的人需要看——存档路径、内部 id、诊断数字。
## 它们以前一直在屏幕上，和玩家真正需要的「我能不能出发」混在同一层，
## 于是玩家要先学会忽略一半的字。默认关掉，`--dev` 才显示。
var _dev_ui: bool = false

## 截图/回归用：启动后模拟点一次这个按钮 id（`--click=bld:coach`）。
## 和 `--bld=` 的区别是它走 `_activate`，能测出「状态没切换」这类断线。
var _boot_click: String = ""
## 截图用：指定建筑屏选中的人（`--bld-hero=<hid>`）。
## 默认选第一个活人，所以「墓园里的死人」那半屏永远截不到。
var _boot_building_hero: String = ""
var _elapsed: float = 0.0


func _ready() -> void:
	_font = ThemeDB.fallback_font
	for a in OS.get_cmdline_user_args():
		if a == "--auto":
			_auto = true
		elif a == "--selftest":
			_selftest = true
		elif a == "--show-move":
			_show_move_demo = true
		elif a == "--show-guard":
			_show_guard_demo = true
		elif a == "--reveal":
			_reveal_all = true
		elif a == "--to-result":
			_to_result = true
		elif a == "--explore":
			_explore = true
		elif a == "--fast":
			_step_delay = 0.02
		elif a == "--auto-map":
			_auto = true
			_auto_map_only = true
			_skip_battles = true
		elif a.begins_with("--shot="):
			_shot_path = a.substr(7)
			DisplayServer.window_set_size(Vector2i(1280, 760))
		elif a.begins_with("--shot-at="):
			_shot_at = float(a.substr(10))
		elif a.begins_with("--size="):
			_size = a.substr(7)
		elif a.begins_with("--dungeon="):
			_dungeon = a.substr(10)
		elif a.begins_with("--quest="):
			_boot_quest = a.substr(8)
		elif a.begins_with("--bld="):
			_boot_building = a.substr(6)
		elif a == "--pending-fire":
			_boot_pending_fire = true
		elif a.begins_with("--bld-hero="):
			_boot_building_hero = a.substr(11)
		elif a.begins_with("--click="):
			_boot_click = a.substr(8)
		elif a == "--dev":
			_dev_ui = true
		elif a.begins_with("--level="):
			_level = int(a.substr(8))
		elif a.begins_with("--preset="):
			_preset = a.substr(9)
		elif a == "--start":
			_auto_start = true
		elif a == "--prep":
			_boot_prep = true
		elif a == "--guild":
			_boot_guild = true
		elif a.begins_with("--save="):
			_save_path = a.substr(7)

	db = DdDb.shared()
	if db == null or db.heroes.is_empty():
		push_error("数据未加载")
		return

	campaign = Campaign.new()
	campaign.setup_from_cfg(db.campaign_cfg, _save_path)
	# 元层要判「升级打折」类怪癖，但它不该自己去读一份 88 KB 的表
	campaign.quirk_lib = db.quirk_lib
	# 新英雄自带 1–2 正 + 1–2 负（heroes.json 的 generation 段）。
	# 这是原版怪癖的主要来源，M14 第一版漏了它，导致整期功能几乎不可见。
	campaign.start_quirk_gen = db.hero_quirk_generation()
	# 饰品库：仓库/装备要判职业限制与同名上限，但它同样不该自己去读表。
	campaign.trinket_lib = db.trinket_lib
	# 商店：价格表与上架规则都在 Shop 里，元层只管钱。
	# **必须在 load_or_new 之前**：开新档时要立刻掷一批货架。
	campaign.shop = db.shop
	# 技能组：每个英雄能带 4 个（heroes.json 的 skill_selection，M19 才接上）。
	# **必须在 load_or_new 之前**：读档时要按它校验存档里的技能列表。
	campaign.skill_table = db.hero_skill_table()
	# 招新的候选池（M27）：名册上限 = 职业总数，所以元层得知道有哪些职业。
	# **必须在 load_or_new 之前**：读档时要用它校验存档里的名册组成。
	campaign.known_heroes = db.hero_ids()
	var had_save: bool = campaign.load_or_new()
	if not had_save:
		campaign.save()
	# 启动时对齐「选中的区域」和「读档时那个区域」（M32）：
	# 命令行 `--dungeon=` 或者存档里记的区域都算数，两者不一致时以场景为准，
	# 因为城镇上那排按钮高亮的正是 `_dungeon`。
	campaign.select_board_region(_dungeon)
	print("城镇：金币 %d，名册 %d 人，远征 %d 趟%s" % [
		campaign.gold, campaign.alive_ids().size(), campaign.expeditions,
		"（读档）" if had_save else "（新档）"])

	set_process(true)
	# 截图/冒烟用：直接进地图，不必先点按钮
	if _boot_guild and not campaign.alive_ids().is_empty():
		_guild_hero = str(campaign.alive_ids()[0])
		_state = S_GUILD
	elif not _boot_building.is_empty() and not campaign.alive_ids().is_empty():
		_building = _boot_building
		# 默认选第一个活人；`--bld-hero` 可以指定（截图要看死人那半屏）
		_building_hero = str(campaign.alive_ids()[0])
		if campaign.roster.has(_boot_building_hero):
			_building_hero = _boot_building_hero
		if _boot_pending_fire:
			_fire_pending = _building_hero
		_state = S_BUILDING
	elif _boot_prep and not campaign.alive_ids().is_empty():
		# 和点难度卡进准备屏走同一套初始化，否则截出来的不是玩家看到的那一屏
		_prep_size = _size
		_prep_level = _level
		_prep_pack = _default_prep_pack()
		_prep_party = _party_for(_prep_level)
		_state = S_PREP
	elif _auto_start:
		_start_expedition(_size, _level, {}, [], _boot_quest)
		if _reveal_all and exp != null:
			exp.debug_reveal_all()
	elif _to_result:
		# 一次性跑完一整趟再展示结算：给截图和冒烟测试用，
		# 免得为了看结算屏等上几分钟战斗动画。
		#
		# 不能调 exp.run_auto()：那是线性路线的驱动器，图模式的待结算队列
		# 它不会消化，于是「推进 1/9 步」就被判定完成——截图上完全看不出来。
		_start_expedition(_size, _level)
		if exp != null:
			# 战斗也走「秒结算」，否则循环会停在战斗屏等玩家点击
			_skip_battles = true
			var guard: int = 0
			while not exp.ended and guard < 400:
				guard += 1
				_selftest_move()
			_sync_exp_events()
			_enter_result()
	elif _selftest:
		_selftest_run()
	# 截图/回归用：走**真正的那条点击路径**（按钮 id → _activate），
	# 而不是像 `--bld=` 那样直接赋状态。
	#
	# 为什么需要它：`--bld=` 绕过了点击分发，所以「点了没反应」这类 bug
	# 截图全绿也看不见——M30 修的那个漏赋 `_state` 就是这么活下来的。
	if not _boot_click.is_empty():
		print("模拟点击：%s → 状态 %d" % [_boot_click, _state])
		_activate(_boot_click)
		print("点击后状态：%d（S_TOWN=%d S_BUILDING=%d S_GUILD=%d S_SHOP=%d）" % [
			_state, S_TOWN, S_BUILDING, S_GUILD, S_SHOP])
	queue_redraw()


## 自检专用：当前可选技能里第一个守护技的下标，没有返回 -1。
##
## 不写死索引（defender 在第 4 个）是为了换职业/换数据时自检不会假装通过：
## 找不到就不测，而不是拿错技能去点。
func _find_guard_option() -> int:
	for i in _options.size():
		var op: Dictionary = _options[i]
		if bool((op.get("action", {}) as Dictionary).get("is_guard", false)):
			return i
	return -1


## 端到端自检：不改一行规则，只走界面自己的那条路
## （出发 → 地图 → 战斗 → 选技能 → 选目标 → 结算），
## 用来验证「界面接线」有没有断开。这类断裂不会让规则测试变红，
## 只会让玩家点了没反应。
## 自检专用：朝出口走一步。到了出口就离开。
func _selftest_move() -> void:
	if exp == null or exp.ended:
		_enter_result()
		return
	# 到了出口还要看任务达没达成（M32）：清剿任务走到出口但还有仗没清时，
	# 现在离开只能是「未完成」——AI 应该把剩下的仗打完，而不是照旧走人。
	# 对探索任务这一条不改变任何行为（at_goal ⇒ quest_met）。
	if exp.at_goal() and exp.quest_met():
		_leave_dungeon()
		return
	var nxt: int = _pick_step()
	if nxt < 0:
		_leave_dungeon()
		return
	_travel_to(nxt)


## 下一步往哪走。默认朝出口；任务有明确目标时先去做目标。
##
## M32 只处理清剿（战斗房），M33 加上收集/激活（指定奇物）。
## 三种目标共用同一条「找最近的目标 → 朝它走」的骨架，
## 差别只在「目标是什么」——所以分别写成一个返回房间号的函数。
func _pick_step() -> int:
	if exp == null:
		return -1
	if exp.quest_met():
		return _step_toward_goal()
	var kind: String = str(exp.quest_goal.get("kind", ""))
	var target: int = -1
	match kind:
		QuestGoal.KIND_BATTLE:
			target = _nearest_uncleared_battle()
		QuestGoal.KIND_GATHER, QuestGoal.KIND_ACTIVATE:
			target = _nearest_quest_target()
	if target >= 0 and target != exp.current_room:
		var st: int = _step_toward_room(target)
		if st >= 0:
			return st
	# 已经到了出口、又没有别的目标可做：走人。结算会把它判成「未完成」，
	# 那是合法结果（和清剿没清完就走是同一种），不是失败。
	if exp.at_goal():
		return -1
	return _step_toward_goal()


## 离得最近的任务目标奇物所在房间（M33）。
##
## 房间里的目标奇物直接就是候选；走廊里的要取两端——奇物挂在边上，
## 走到任意一端都会触发。取两端里更近的那个，AI 才不会绕远路。
func _nearest_quest_target() -> int:
	var cid: String = str(exp.quest_goal.get("curio", ""))
	if cid.is_empty() or exp.map.is_empty():
		return -1
	var m: Dictionary = exp.map
	var rooms: Dictionary = m["rooms"]
	var ids: Array = m["room_ids"]
	var n: int = ids.size()
	var pairs: Array = []
	for e in (m["edges"] as Array):
		pairs.append(Vector2i(int(e.a), int(e.b)))
	var adj: Dictionary = MapGen.adjacency_rooms(n, pairs)
	var dist: Array = MapGen.bfs(n, adj, exp.current_room)
	var best: int = -1
	var best_d: int = 1 << 30
	for id in ids:
		var rid: int = int(id)
		var r: Dictionary = rooms[rid]
		var st: Dictionary = r.get("step", {})
		if str(st.get("curio", "")) != cid:
			continue
		if bool(r.get("visited", false)):
			continue
		var d: int = int(dist[rid])
		if d >= 0 and d < best_d:
			best_d = d
			best = rid
	for e2 in (m["edges"] as Array):
		if bool((e2 as Dictionary).get("walked", false)):
			continue
		var steps: Array = (e2 as Dictionary).get("steps", [])
		if steps.is_empty() or str((steps[0] as Dictionary).get("curio", "")) != cid:
			continue
		for endp in [int(e2.a), int(e2.b)]:
			var d2: int = int(dist[endp])
			if d2 >= 0 and d2 < best_d:
				best_d = d2
				best = endp
	return best


## 离得最近的、还没打过的战斗房。
##
## 「还没打过」用 `visited` 判：房间的 step 只在第一次进门时触发，
## 所以到过就等于清过（同地图屏那个变暗标记，两处必须同一条判据）。
func _nearest_uncleared_battle() -> int:
	var m: Dictionary = exp.map
	if m.is_empty():
		return -1
	var rooms: Dictionary = m["rooms"]
	var ids: Array = m["room_ids"]
	var n: int = ids.size()
	var pairs: Array = []
	for e in (m["edges"] as Array):
		pairs.append(Vector2i(int(e.a), int(e.b)))
	var adj: Dictionary = MapGen.adjacency_rooms(n, pairs)
	# 以**当前房间**为源做一次 BFS：这样能往回走，而不是只会朝出口方向搜。
	var dist: Array = MapGen.bfs(n, adj, exp.current_room)
	var best: int = -1
	var best_d: int = 1 << 30
	for id in ids:
		var rid: int = int(id)
		var r: Dictionary = rooms[rid]
		var k: String = str(r.get("kind", ""))
		if k != MapGen.K_BATTLE and k != MapGen.K_BOSS:
			continue
		if bool(r.get("visited", false)):
			continue
		var d: int = int(dist[rid])
		if d >= 0 and d < best_d:
			best_d = d
			best = rid
	return best


## 朝某个房间走一步：以目标为源做 BFS，选距离更小的邻居。
##
## 不能复用 `_dist_table()`——那张表是「到出口的距离」，
## 目标不是出口时会把人往反方向带（而且不报错，只是越走越远）。
func _step_toward_room(target: int) -> int:
	var m: Dictionary = exp.map
	var n: int = (m["room_ids"] as Array).size()
	var pairs: Array = []
	for e in (m["edges"] as Array):
		pairs.append(Vector2i(int(e.a), int(e.b)))
	var adj: Dictionary = MapGen.adjacency_rooms(n, pairs)
	var dist: Array = MapGen.bfs(n, adj, target)
	var cur_d: int = int(dist[exp.current_room])
	var nbs: Array = exp.adjacent()
	for nb in nbs:
		var rid: int = int(nb.room)
		if int(dist[rid]) == cur_d - 1:
			return rid
	return int((nbs[0] as Dictionary).room) if not nbs.is_empty() else -1


func _step_toward_goal() -> int:
	if _explore:
		return _step_explore()
	var dist: Array = _dist_table()
	var cur: int = exp.current_room
	for nb in exp.adjacent():
		var rid: int = int(nb.room)
		if int(dist[rid]) == int(dist[cur]) - 1:
			return rid
	var nbs: Array = exp.adjacent()
	return int((nbs[0] as Dictionary).room) if not nbs.is_empty() else -1


## 探索策略：先走「没去过且不后退」的邻居，没有就走最短路径。
##
## 为什么要限制「不后退」：允许回头的话会在死胡同里来回走，
## 把预算烧光却什么都拿不到。`<= cur` 这个条件保证每一步都在朝目标
## 或者横向移动，不会离目标更远。
##
## 走完侧支线之后自动回到最短路径——因为下一步就没有未访问的邻居了。
func _step_explore() -> int:
	var dist: Array = _dist_table()
	var cur: int = exp.current_room
	var cur_d: int = int(dist[cur])
	var side: Array = []
	var forward: Array = []
	var nbs: Array = exp.adjacent()
	for nb in nbs:
		var rid: int = int(nb.room)
		var d: int = int(dist[rid])
		if not _seen_rooms.has(rid) and d <= cur_d:
			side.append(rid)
		if d == cur_d - 1:
			forward.append(rid)
	if not side.is_empty():
		return int(side[0])
	if not forward.is_empty():
		return int(forward[0])
	return int((nbs[0] as Dictionary).room) if not nbs.is_empty() else -1


## 到目标的 BFS 距离**表**（按房间 id 索引）。
##
## 注意别和 `_dist_to_goal()` 混：那个返回「自己离出口还有几步」，
## 是个标量，界面用来显示提示；这个是每个房间到出口的距离，走路决策要用。
## M18 一开始就撞了名，撞出的报错是「不能把 int 赋给 Array」。
func _dist_table() -> Array:
	var m: Dictionary = exp.map
	var n: int = (m["room_ids"] as Array).size()
	var pairs: Array = []
	for e in (m["edges"] as Array):
		pairs.append(Vector2i(int(e.a), int(e.b)))
	var adj: Dictionary = MapGen.adjacency_rooms(n, pairs)
	return MapGen.bfs(n, adj, int(m["goal"]))


func _selftest_run() -> void:
	# 上一趟全灭又没钱时，玩家会去点「免费征召」。自检也照做，
	# 否则第二次跑就会停在城镇里，看起来像失败，其实是没模拟那一步操作。
	# 注意要**补满**而不是补一个：单人出门必死，只补一个等于把死循环演一遍。
	if campaign.alive_ids().is_empty():
		var n: int = 0
		for hid in campaign.hero_ids():
			if campaign.can_recruit(hid):
				campaign.recruit(hid)
				n += 1
		if n > 0:
			campaign.save()
			print("SELFTEST 名册为空，免费征召 %d 人" % n)
	_start_expedition(_size, _level, {}, [], _boot_quest)
	_seen_rooms = {}
	if exp != null:
		_seen_rooms[int(exp.current_room)] = true
	var guard: int = 0
	var acted: int = 0
	var battles: int = 0
	_move_checked = false
	moved_ok = false
	_guard_checked = false
	guarded_ok = false
	forced_moves = 0
	shuffle_moves = 0
	move_resists = 0
	summons = 0
	summon_fails = 0
	# 循环预算：每轮处理一个动作（一次点击/一回合推进/一步移动）。
	# 600 在 M16 之前够用，M17 把奇物密度从 0.6 提到 3.5 个/趟之后不够了——
	# 奇物交互要占轮次，而且它们带来的掉血/加压让战斗回合变长。
	# 超预算的表现是停在 S_BATTLE（state=2），看起来像「没走到结算屏」。
	while guard < 1200:
		guard += 1
		if _state == S_RESULT:
			break
		if _state == S_MAP:
			_selftest_move()
			continue
		if _state == S_BATTLE and _battle != null:
			if _battle.awaiting_input != null:
				# 自检也要走一次「调整站位」——M9 之前站位是静态的，
				# 这条路径（按钮 → submit_move → perform_move）没有任何测试覆盖，
				# 而它正是玩家手里唯一能改阵型的入口。
				var who: Combatant = _battle.awaiting_input
				if not _move_checked and not _battle.move_options(who).is_empty():
					_move_checked = true
					var spots: Array = _battle.move_options(who)
					var before_rank: int = who.rank
					_move_mode = true
					_activate("goto:%d" % int(spots[0]))
					moved_ok = moved_ok or (who.rank != before_rank)
					continue
				# 自检也要走一次「守护」：点技能 → 点队友 → 关系建立。
				# 规则层对了不代表这条路径通——按钮的 rect、目标池、_pending 的状态机
				# 任何一环断了，玩家只会看到「点了守护，什么也没发生」。
				if not _guard_checked:
					var gi: int = _find_guard_option()
					if gi >= 0:
						var opt: Dictionary = _options[gi]
						_guard_checked = true
						_activate("skill:%d" % gi)
						if not _pending.is_empty():
							var mates: Array = _pending.get("targets", [])
							if not mates.is_empty():
								_pick_target(int((mates[0] as Combatant).uid))
								guarded_ok = _battle.guard_target_of(who.uid) != null
								acted += 1
								continue
				if _options.is_empty():
					_submit({}, [])
				else:
					_activate("skill:0")
					if not _pending.is_empty():
						var pool: Array = _pending.get("targets", [])
						if pool.is_empty():
							_submit({}, [])
						else:
							_pick_target(int((pool[0] as Combatant).uid))
					acted += 1
				if int(_battle.round_index) == 1 and acted == 1:
					battles += 1
			else:
				_battle_step()
			continue
		break

	var s: Dictionary = exp.summary() if exp != null else {}
	print("SELFTEST 状态=%d 推进=%d/%d 玩家出手=%d 结束原因=%s" % [
		_state, int(s.get("steps_done", 0)), int(s.get("steps_total", 0)),
		acted, str(s.get("end_reason", "?"))])

	# —— 元层闭环：入账 → 存档 → 重新读档 → 数值必须一致 ——
	var gold_after: int = campaign.gold
	var alive_after: int = campaign.alive_ids().size()
	# 入账**不判 PASS**，只报数。
	#
	# 试过两版判据，都不成立：
	#   1.0 `end_reason == "wipe"` 才允许零收入 → 「一场没打就撤退」被误判。
	#   2.0 `battles > 0` 就该有钱 → 遇到 `loot: NONE` 的怪组照样零收入。
	#      （`monsters.json` 里 17 只怪的 loot 就是 NONE，那是数据事实。）
	# 真正能判的是「存档往返一致」，那条已经在下面硬判。
	# 收入是遭遇决定的，和位移/召唤一样，不该由玩家行为保证。
	var fight_n: int = int(s.get("battles", 0))
	var loot_ok: bool = true
	var probe := Campaign.new()
	probe.setup_from_cfg(db.campaign_cfg, _save_path)
	var reloaded: bool = probe.load_or_new()
	var save_ok: bool = reloaded and probe.gold == gold_after \
		and probe.alive_ids().size() == alive_after \
		and probe.expeditions == campaign.expeditions
	print("SELFTEST 战利品 金币=%d 传家宝=%d 战斗=%d 结束=%s 入账=%s" % [
		gold_after, campaign.heirloom_total(), fight_n, str(s.get("end_reason", "?")),
		"OK" if loot_ok else "FAIL"])
	print("SELFTEST 存档往返 %s（远征 %d 趟，存活 %d 人）" % [
		"OK" if save_ok else "FAIL", probe.expeditions, probe.alive_ids().size()])

	print("SELFTEST 站位调整 %s" % (
		"OK" if moved_ok else ("未触发（这场没有可挪的单位）" if not _move_checked else "FAIL 选择了移动但 rank 没变")))
	print("SELFTEST 守护 %s" % (
		"OK" if guarded_ok else ("未触发（队伍里没人能守护）" if not _guard_checked else "FAIL 点了守护但关系没建立")))
	# 位移只报数：它取决于这趟路线里有没有带位移技能的怪，
	# 不像守护那样由玩家自己点，所以不能拿它判 PASS。
	if forced_moves > 0 or shuffle_moves > 0:
		print("SELFTEST 位移 推拉=%d 洗位=%d 抵抗=%d" % [forced_moves, shuffle_moves, move_resists])
	else:
		print("SELFTEST 位移 未触发（本趟没有带位移技能的敌人）")
	# 召唤同理：由遭遇决定，不能拿它判 PASS。
	if summons > 0:
		print("SELFTEST 召唤 成功=%d 失败=%d" % [summons, summon_fails])
	else:
		print("SELFTEST 召唤 未触发（本趟没有会召唤的敌人，或它们没选这个技能）")
	# 怪癖：同样只报数。默认名册开局没有怪癖，能不能拿到全靠这趟碰了什么奇物，
	# 拿它判 PASS 等于要求「这趟必须踩到坑」。
	var q_gain: int = int(s.get("quirks_gained", 0))
	var q_have: int = int(s.get("quirks_total", 0))
	if q_gain > 0 or q_have > 0:
		print("SELFTEST 怪癖 获得=%d 在手=%d 染病=%d 抗病=%d 清负面=%d" % [
			q_gain, q_have, int(s.get("diseases_contracted", 0)),
			int(s.get("diseases_resisted", 0)), int(s.get("quirks_purged", 0))])
	else:
		print("SELFTEST 怪癖 未触发（本趟奇物 %d 次，其中没有给怪癖的分支）" % int(s.get("curios", 0)))
	# 饰品：这趟谁戴了、掉了什么、进没进仓库。
	# 这里只报数不判 PASS——「这趟没掉饰品」不是失败，
	# 拿它当断言等于要求每次都得开箱出货。
	var worn: int = int(s.get("trinkets_equipped", 0))
	var drops: int = int(s.get("trinkets", 0))
	var got_ids: Array = (s.get("trinket_ids", []) as Array)
	if worn > 0 or drops > 0:
		print("SELFTEST 饰品 佩戴=%d 掉落=%d 有id=%d 样例=%s" % [
			worn, drops, got_ids.size(), str(got_ids.slice(0, 3))])
	else:
		print("SELFTEST 饰品 未触发（这趟没人戴、也没掉到；仓库 %d 件）" % campaign.trinket_store.size())

	# 循环是怎么退出的？预算用完 vs 正常走到结算屏，是两种完全不同的病：
	# 前者说明「这一趟真的需要更多动作」，后者说明「卡在一个不推进的状态里」。
	# 不打印这个数就只能靠猜——M18 这里连挂两次才想到要加。
	if _state != S_RESULT:
		var bt: Battle = _battle
		print("SELFTEST 诊断 循环用了 %d/%d 轮  state=%d  战斗轮=%d  待输入=%s  待结算=%s" % [
			guard, 1200, _state,
			(bt.round_index if bt != null else -1),
			(bt.awaiting_input != null if bt != null else false),
			(exp.has_pending() if exp != null else false)])

	# 内容密度：地图上**有**多少 vs 这一趟**遇到**多少。
	# 两个数差很多——玩家只走一条路，图上的奇物大半碰不到。
	# M13 说「奇物几乎不出现」，M17 调密度，靠的就是这一栏。
	print("SELFTEST 内容 奇物=%d 陷阱=%d 障碍=%d 饥饿=%d 房间=%d 步数=%d" % [
		int(s.get("curios", 0)), int(s.get("traps", 0)), int(s.get("obstacles", 0)),
		int(s.get("hunger_checks", 0)), int(s.get("rooms_visited", 0)), int(exp.step_index)])
	# 首领任务（M20）：任务是 kill_boss 时，终点房间必须真的有一场首领战。
	# 「地图生成了 boss 房」和「这一趟打到了 boss」是两件事——
	# 走不到终点、或者中途团灭，击杀就是 false，这栏要把这两种情况分开报。
	if exp.quest_type == "kill_boss":
		print("SELFTEST 首领 任务=%s 打到=%s 击杀=%s 结果=%s" % [
			exp.quest_type, str(bool(s.get("boss_fought", false))),
			str(bool(s.get("boss_killed", false))), exp.end_reason])

	# 任务目标（M32 / M33）：类型、目标、达成与否、各类进度。
	# 自检走最短路径，所以清剿/收集「走到出口但没做完」是**正常结果**——
	# 这一行要把这种情况和「机制坏了」区分开。
	print("SELFTEST 任务 类型=%s 目标=%s 达成=%s 奇物=%s 战斗房=%d/%d 收集=%d 激活=%d 物品用=%d 缺=%d" % [
		exp.quest_type, str(exp.quest_goal.get("kind", "")), str(exp.quest_met()),
		str(exp.quest_goal.get("curio", "")),
		int(exp.stats.get("quest_battles_cleared", 0)), int(exp.stats.get("quest_battles_total", 0)),
		int(exp.stats.get("quest_gathered", 0)), int(exp.stats.get("quest_activated", 0)),
		int(exp.stats.get("quest_items_used", 0)), int(exp.stats.get("quest_items_missing", 0))])

	# 失败时要说清是哪一项挂了。之前只打一个 FAIL，
	# 遇到偶发（跑五次过一次）根本没法查——那等于自己给自己出难题。
	var bad: Array = []
	if acted <= 0:
		bad.append("玩家一次都没出手")
	if _state != S_RESULT:
		bad.append("没走到结算屏（state=%d）" % _state)
	if not loot_ok:
		bad.append("战利品入账可疑（金币 %d，结束原因 %s）" % [
			gold_after, str(s.get("end_reason", "?"))])
	if not save_ok:
		bad.append("存档往返不一致（档内金币 %d / 内存 %d，档内活人 %d / 内存 %d）" % [
			probe.gold, gold_after, probe.alive_ids().size(), alive_after])
	if _move_checked and not moved_ok:
		bad.append("站位调整失败")
	if _guard_checked and not guarded_ok:
		bad.append("守护关系没建立")
	# 「结算说完成了」和「任务目标达成了」必须是同一件事（M32）。
	# 清剿的自检走最短路径，所以经常走到出口却没清完——那是**合法的未完成**，
	# 不是失败。真正要抓的是反过来的情况：判据坏了，什么都没清也算完成。
	if exp != null and exp.end_reason == "complete" and not exp.quest_met():
		bad.append("结算写了完成，但任务目标没达成")
	var pass_all: bool = bad.is_empty()
	print("SELFTEST %s%s" % ["PASS" if pass_all else "FAIL",
		"" if pass_all else "： " + "；".join(bad)])
	get_tree().quit(0 if pass_all else 1)


# ============================================================
# 开局
# ============================================================

## `pack` 是出发前买的补给。**默认空 = 不覆盖**：自动代打、bench、
## 以及「钱不够按保底包出发」都走这条，所以历史行为逐位不变。
func _start_expedition(size_name: String, level: int, pack: Dictionary = {},
		picked: Array = [], quest: String = "explore") -> void:
	# 名册现在有 5 人、出战上限 4 人。**必须在这里夹住**——
	# 战斗层的 rank 只有 0–3，多一个人会站到第 5 位，目标掩码选不中他，
	# 表现是「队伍里有个永远不被打也不会被治疗的人」。
	var party: Array = picked.duplicate() if not picked.is_empty() \
		else _party_for(level)
	if party.size() > Campaign.PARTY_MAX:
		party = party.slice(0, Campaign.PARTY_MAX)
	if party.is_empty():
		_flash_msg("名册里没有可出发的英雄")
		return

	_size = size_name
	_level = level
	match quest:
		"kill_boss":
			_flash_msg("首领任务：终点房间必有一战")
		"cleanse":
			_flash_msg("清剿任务：图上的战斗全打完，走到出口才算完成")
		"inventory_activate":
			_flash_msg("仪式任务：带着任务物品去激活，用完就没了")
		_:
			pass
	var m: Dictionary = MapGen.build(db, _dungeon, _size, _level, DdRng.new(randi()), quest)
	if m.is_empty():
		_flash_msg("地图生成失败")
		return

	# 装备阶来自城镇（花钱升的），不是路线白送的
	var gear: Dictionary = {}
	var skill: Dictionary = {}
	for hid in party:
		gear[hid] = campaign.gear_of(hid)
		skill[hid] = campaign.skill_of(hid)

	exp = Expedition.new()
	# 等级惩罚（M25 / M29）：低一级，进本 +20 压力，之后每次受压 +25%。
	# 进本压力**必须在 setup 之前赋**——队伍状态是在 setup 里建的，晚一步就白赋；
	# 受压倍率是每场战斗开始时读的，晚一点赋没关系，但放一起更清楚。
	var js: Dictionary = {}
	var js_mult: Dictionary = {}
	for hid_j in party:
		js[str(hid_j)] = campaign.entry_stress(str(hid_j), _level)
		js_mult[str(hid_j)] = campaign.stress_mult_for(str(hid_j), _level)
	exp.join_stress = js
	exp.join_stress_mult = js_mult
	# 名册实例 id → 职业 id（M34）。`party` 里装的是实例（可能是 `crusader#2`），
	# 而数值表、技能表、饰品职业限制全都按职业查，所以这张映射必须一起递下去。
	var defs: Dictionary = {}
	for hid_d in party:
		defs[str(hid_d)] = campaign.def_of(str(hid_d))
	exp.setup(db, party, [], db.expedition_cfg.preset(_preset), randi(), _preset,
		_loot_cfg(), gear, defs)
	exp.hero_skill = skill
	# 技能组（M19）：只传这四个人带的 4 个技能，没上路的人不影响战斗。
	exp.hero_loadout = campaign.loadout_map(party)
	# 怪癖跟人走：把这趟出发的四个人身上的怪癖灌进去。
	# 没上路的人不会在别处中招，所以只传 party 而不是整个名册。
	exp.seed_quirks(campaign.quirk_map_for(party))
	# 装备同理：只带这四个人身上的，仓库里的留在城里。
	exp.set_hero_trinkets(campaign.equipped_map())
	# 补给：买了就按买的带，没买（或钱不够）就走默认包。
	exp.set_start_supplies(pack)
	exp.set_location(_dungeon, _size, _level, quest)
	exp.enter_map(m)

	_log.clear()
	_exp_ev_pos = 0
	_settled = false
	_settle_gain = {}
	_sync_exp_events()
	_battle = null
	_state = S_MAP
	var goal_word: String = "首领" if quest == "kill_boss" else "出口"
	_add_log("出发：%s %s · %d 间房 · 入口到%s约 %d 步 · 队伍 %d 人" % [
		DdNames.dungeon_name(_dungeon), _size_name_of(_size),
		(m["room_ids"] as Array).size(), goal_word, int(m["shortest"]), party.size()],
		DdTheme.TEXT)
	queue_redraw()


func _loot_cfg() -> Dictionary:
	var lc: Dictionary = (campaign.cfg.get("loot", {}) as Dictionary).duplicate(true)
	lc["heirloom_names"] = campaign.cfg.get("heirlooms", [])
	return lc


## 进结算屏：把战利品入账、英雄状态落盘、存档。只做一次。
func _enter_result() -> void:
	if not _settled and exp != null and campaign != null:
		_settled = true
		_settle_gain = campaign.settle(exp)
		campaign.save()
	_state = S_RESULT


func _sync_exp_events() -> void:
	if exp == null:
		return
	while _exp_ev_pos < exp.events.size():
		_consume_exp_event(exp.events[_exp_ev_pos])
		_exp_ev_pos += 1


func _consume_exp_event(e: Dictionary) -> void:
	var t: String = str(e.get("t", ""))
	match t:
		"light":
			pass    # 光照变化不进流水，顶栏实时显示，写日志会刷屏
		"torch_used":
			_add_log("【火把】光照 %.0f（剩 %d 根）" % [float(e["light"]), int(e["left"])], DdTheme.LIGHT)
		"hallway_stress":
			_add_log("走过走廊：%s 压力 +%.0f" % [
				_hero_label(str(e.get("hero", ""))), float(e.get("amount", 0.0))], DdTheme.DIM)
		"hunger":
			if bool(e["fed"]):
				_add_log("【饥饿】吃了口粮（剩 %d 份），全队略回血" % int(e["food"]), DdTheme.FOOD)
			else:
				_add_log("【饥饿】断粮！全员加压并掉血", DdTheme.WARN)
		"battle_start":
			_add_log("【遭遇】%s" % ", ".join(_monster_list(e.get("monsters", []))), DdTheme.TEXT)
			if not str(e.get("surprised", "")).is_empty():
				_add_log("　惊袭：%s 第一轮不行动" % ("我方" if str(e["surprised"]) == "party" else "敌方"), DdTheme.CRIT)
		"battle_end":
			_add_log("【战果】%s（%d 轮）" % [
				"我方胜" if str(e["winner"]) == "party" else "战败", int(e["rounds"])], DdTheme.DIM)
		"loot":
			var bits: Array = []
			if int(e.get("gold", 0)) > 0:
				bits.append("金币 %d" % int(e["gold"]))
			for k in (e.get("heirlooms", {}) as Dictionary).keys():
				bits.append("%s ×%d" % [DdNames.heirloom_name(str(k)), int(e["heirlooms"][k])])
			for k in (e.get("supplies", {}) as Dictionary).keys():
				bits.append("%s ×%d" % [DdNames.supply_name(str(k)), int(e["supplies"][k])])
			for k in (e.get("gems", {}) as Dictionary).keys():
				bits.append("%s ×%d" % [DdNames.heirloom_name(str(k)), int(e["gems"][k])])
			if not bits.is_empty():
				_add_log("【%s】%s" % ["结算" if bool(e.get("complete", false)) else "拾取",
					"、".join(bits)], DdTheme.CRIT)
		"curio":
			# 奇物必须报出来。不报的话玩家只看到金币涨了，永远学不会
			# 「这个祭坛该带圣水」——那正是这一层唯一的意义。
			var cname: String = DdNames.curio_name(str(e.get("curio", "")))
			var used: String = str(e.get("item", ""))
			var outcome: String = str(e.get("outcome", ""))
			var tail: Array = []
			if int(e.get("gold", 0)) > 0:
				tail.append("金币 %d" % int(e["gold"]))
			for k2 in (e.get("heirlooms", {}) as Dictionary).keys():
				tail.append("%s ×%d" % [DdNames.heirloom_name(str(k2)), int(e["heirlooms"][k2])])
			for k3 in (e.get("supplies", {}) as Dictionary).keys():
				tail.append("%s ×%d" % [DdNames.supply_name(str(k3)), int(e["supplies"][k3])])
			if float(e.get("stress", 0.0)) > 0.0:
				tail.append("全员压力 +%.0f" % float(e["stress"]))
			if float(e.get("hp_lost", 0.0)) > 0.0:
				tail.append("全员掉血 %.0f%%" % (float(e["hp_lost"]) * 100.0))
			# 怪癖与疾病必须点名报到人：这是玩家唯一能看见的获得渠道，
			# 只写「获得了负面怪癖」等于让人不知道自己被坑在哪。
			var who: String = _hero_label(str(e.get("quirk_target", "")))
			if not str(e.get("quirk", "")).is_empty():
				tail.append("%s 获得「%s」" % [who, DdNames.quirk_name(str(e["quirk"]))])
			if not str(e.get("disease", "")).is_empty():
				tail.append("%s 染上「%s」" % [who, DdNames.quirk_name(str(e["disease"]))])
			if not str(e.get("quirk_lost", "")).is_empty():
				tail.append("清除了「%s」" % DdNames.quirk_name(str(e["quirk_lost"])))
			if not (e.get("unsupported", []) as Array).is_empty():
				tail.append("（效果未实装）")
			var verb: String = "空手而归"
			if not tail.is_empty():
				verb = "、".join(tail)
			elif outcome == "nothing":
				verb = "什么也没有"
			var item_txt: String = ""
			if not used.is_empty():
				item_txt = "（用了%s）" % DdNames.supply_name(used)
			_add_log("【奇物】%s%s：%s" % [cname, item_txt, verb],
				DdTheme.WARN if float(e.get("stress", 0.0)) > 0.0 or float(e.get("hp_lost", 0.0)) > 0.0 else DdTheme.TEXT)
		"affliction":
			_add_log("【崩溃】%s 陷入 %s" % [_hero_label(str(e.get("hero", ""))), str(e.get("kind", ""))], DdTheme.WARN)
			_flash_msg("崩溃！")
		"virtue":
			_add_log("【美德】%s 觉醒（%s）" % [_hero_label(str(e.get("hero", ""))), str(e.get("kind", ""))], DdTheme.CRIT)
			_flash_msg("美德觉醒")
		"heart_attack":
			_add_log("【心脏骤停】%s" % _hero_label(str(e.get("hero", ""))), DdTheme.WARN)
			_flash_msg("心脏骤停")
		"deaths_door":
			_add_log("【死门】%s" % _hero_label(str(e.get("hero", ""))), DdTheme.WARN)
		"death":
			_add_log("【阵亡】%s（%s）" % [_hero_label(str(e.get("hero", ""))), str(e.get("cause", ""))], DdTheme.WARN)
		"act_out":
			_add_log("　%s 崩溃发作，本回合不行动" % _hero_label(str(e.get("hero", ""))), DdTheme.WARN)
		"camp":
			_add_log("【休整】回血减压，光照 %.0f" % float(e["light"]), DdTheme.HEAL)
		"camp_ambush":
			_add_log("【休整】营地被偷袭！", DdTheme.WARN)
		"scout":
			if exp != null and exp.map_mode:
				_add_log("【侦察】看清一间房（已探明 %d/%d，成功率 %.0f%%）" % [
					int(e["revealed"]), int(e["total"]), float(e["chance"]) * 100.0], DdTheme.OK)
			else:
				_add_log("【侦察】看清前方第 %d 个节点（成功率 %.0f%%）" % [
					int(e["revealed"]), float(e["chance"]) * 100.0], DdTheme.OK)
		"scout_edge":
			_add_log("【侦察】看清前方走廊：%s（解除率 +%.0f%%）" % [
				_hazard_name(str(e.get("kind", ""))),
				db.rules.trap_scout_disarm_bonus * 100.0], DdTheme.OK)
		"trap":
			var sc: String = "已察觉" if bool(e.get("scouted", false)) else "没察觉"
			if bool(e.get("dodged", false)):
				_add_log("【陷阱】%s，队伍避开了（%.0f%%）" % [sc, float(e["chance"]) * 100.0], DdTheme.OK)
			else:
				_add_log("【陷阱】%s，全队掉血并加压（躲避率 %.0f%%）" % [sc, float(e["chance"]) * 100.0], DdTheme.WARN)
				_flash_msg("踩中陷阱")
		"obstacle":
			if bool(e.get("cleared", false)):
				_add_log("【障碍】用掉 1 把铁锹凿开（剩 %d）" % int(e["shovel"]), DdTheme.FOOD)
			else:
				_add_log("【障碍】没有铁锹，只能硬挖——全队掉血加压", DdTheme.WARN)
				_flash_msg("没有铁锹")
		"retreat":
			_add_log("【撤退】全员加压 %.0f" % db.rules.retreat_stress, DdTheme.DIM)
		"exp_end":
			_add_log("【结束】%s" % str(e["reason"]), DdTheme.TEXT)


func _add_log(text: String, col: Color = DdTheme.TEXT) -> void:
	_log.append({"text": text, "color": col})
	if _log.size() > LOG_MAX:
		_log = _log.slice(_log.size() - LOG_MAX)


func _flash_msg(text: String) -> void:
	_flash = text
	_flash_life = 1.8


# ============================================================
# 地图阶段的动作
# ============================================================

## 走向相邻房间。真正的内容结算交给 _drain_queue ——
## 一次移动可能同时包含「走廊事件」和「房间内容」，不能只处理第一个。
func _travel_to(room: int) -> void:
	if exp == null or exp.ended:
		return
	if not exp.travel(room):
		_flash_msg("走不到那间房")
		return
	_seen_rooms[room] = true
	_sync_exp_events()
	_drain_queue()


## 消化「已决定但还没结算」的步骤：走廊内容 → 房间内容。
## 碰到战斗就切到战斗屏，剩下的步骤等打完再继续。
func _drain_queue() -> void:
	var guard: int = 0
	while exp != null and not exp.ended and exp.has_pending() and guard < 32:
		guard += 1
		var step: Dictionary = exp.take_step()
		_sync_exp_events()
		if step.is_empty():
			break
		match str(step.get("kind", "walk")):
			"hunger":
				exp.resolve_hunger()
				_sync_exp_events()
			"curio":
				exp.resolve_curio(step)
				_sync_exp_events()
			"trap":
				exp.resolve_trap(step)
				_sync_exp_events()
			"obstacle":
				exp.resolve_obstacle()
				_sync_exp_events()
			"walk":
				pass
			_:
				_battle = exp.start_battle(step)
				_sync_exp_events()
				if _battle == null:
					continue
				# 让规则层知道「英雄的决策由外部给」——它只认这个标志，不认识界面
				_battle.decision_provider = func(_b: Battle, _a: Combatant) -> Dictionary: return {}
				_ev_pos = 0
				_options = []
				_pending = {}
				if _skip_battles:
					# 调试用：不切战斗屏，直接按 AI 打完，镜头留在地图上
					exp._play_out(_battle)
					_battle = null
					_sync_exp_events()
					continue
				_step_timer = 0.20
				_state = S_BATTLE
				return
	if exp != null and exp.ended:
		_enter_result()


func _leave_dungeon() -> void:
	if exp == null or exp.ended:
		return
	exp.leave_dungeon()
	_sync_exp_events()
	_enter_result()


func _use_torch() -> void:
	if exp == null or exp.ended:
		return
	if exp.use_torch():
		_sync_exp_events()


func _do_camp() -> void:
	if exp == null or exp.ended:
		return
	if exp.camp():
		_sync_exp_events()
		if exp.ended:
			_enter_result()
		elif _battle != null:
			_state = S_BATTLE


func _do_retreat() -> void:
	if exp == null or exp.ended:
		return
	exp.retreat()
	_sync_exp_events()
	_enter_result()


# ============================================================
# 战斗阶段
# ============================================================

func _process(delta: float) -> void:
	_elapsed += delta
	_flash_life = maxf(0.0, _flash_life - delta)

	if not _shot_path.is_empty() and _elapsed >= _shot_at:
		var img: Image = get_viewport().get_texture().get_image()
		img.save_png(_shot_path)
		print("截图已保存：", _shot_path)
		get_tree().quit()
		return

	var i: int = 0
	while i < _floaters.size():
		_floaters[i].life -= delta
		_floaters[i].pos.y -= 26.0 * delta
		if _floaters[i].life <= 0.0:
			_floaters.remove_at(i)
		else:
			i += 1

	if _state == S_BATTLE and _battle != null:
		if _battle.awaiting_input != null:
			if _auto and not _auto_map_only:
				_auto_timer += delta
				if _auto_timer > 0.25:
					_auto_timer = 0.0
					_auto_submit()
		else:
			_step_timer -= delta
			if _step_timer <= 0.0:
				_battle_step()
	elif _state == S_MAP and _auto:
		_auto_timer += delta
		if _auto_timer > 0.7:
			_auto_timer = 0.0
			_selftest_move()
	elif _state == S_TOWN and _auto:
		_auto_timer += delta
		if _auto_timer > 0.3:
			_auto_timer = 0.0
			_start_expedition(_size, _level)

	queue_redraw()


func _battle_step() -> void:
	if _battle == null:
		return
	if _battle.is_over():
		_step_timer = 0.45
		_end_battle_ui()
		return
	if not _battle.round_open():
		_battle.begin_round()
		_ev_pos = 0
		_drain_battle_events()
		_step_timer = _step_delay
		return

	_battle.step_turn()
	_drain_battle_events()
	if _battle.awaiting_input != null:
		_begin_player_turn()
	_step_timer = _step_delay


func _end_battle_ui() -> void:
	if exp == null or _battle == null:
		return
	exp.finish_battle(_battle)
	_battle = null
	_sync_exp_events()
	if exp.ended:
		_enter_result()
		return
	exp.after_step(false)
	_sync_exp_events()
	if exp.ended:
		_enter_result()
		return
	_options = []
	_pending = {}
	_state = S_MAP
	# 战斗可能发生在走廊里，房间里还有内容没结算
	_drain_queue()


func _begin_player_turn() -> void:
	_options = _battle.player_options(_battle.awaiting_input)
	_pending = {}
	_auto_timer = 0.0


func _auto_submit() -> void:
	if _battle == null or _battle.awaiting_input == null:
		return
	# 截图用：让第一个能守护的人真的守一次，然后把画面冻住——
	# 守护是一项「持续状态」，不冻住的话截图永远落在它已经过期之后。
	if _show_guard_demo:
		if _guard_demo_done:
			return
		var gi: int = _find_guard_option()
		if gi < 0:
			# 这一回合不是守护者发起的：照常代打，等轮到他
			var c0: Dictionary = _battle.choose_action(_battle.awaiting_input)
			_submit(c0.get("action", {}), c0.get("targets", []))
			return
		_guard_demo_done = true
		_activate("skill:%d" % gi)
		var mates: Array = _pending.get("targets", [])
		if not mates.is_empty():
			_pick_target(int((mates[0] as Combatant).uid))
		return
	var c: Dictionary = _battle.choose_action(_battle.awaiting_input)
	_submit(c.get("action", {}), c.get("targets", []))


func _submit(action: Dictionary, targets: Array) -> void:
	if _battle == null:
		return
	_battle.submit_choice(action, targets)
	_drain_battle_events()
	_options = []
	_pending = {}
	_move_mode = false
	_step_timer = _step_delay


# ============================================================
# 输入
# ============================================================

func _gui_input(event: InputEvent) -> void:
	if event is InputEventMouseMotion:
		_mouse = (event as InputEventMouseMotion).position
		_hover_uid = -1
		for s in _slots:
			if (s.rect as Rect2).has_point(_mouse):
				_hover_uid = int(s.uid)
		queue_redraw()
	elif event is InputEventMouseButton:
		var mb := event as InputEventMouseButton
		if mb.pressed and mb.button_index == MOUSE_BUTTON_LEFT:
			_on_click(mb.position)


func _unhandled_input(event: InputEvent) -> void:
	if not (event is InputEventKey) or not (event as InputEventKey).pressed:
		return
	match (event as InputEventKey).keycode:
		KEY_ESCAPE:
			if _state == S_MAP:
				_do_retreat()
		KEY_SPACE:
			if _state == S_BATTLE and _battle != null and _battle.awaiting_input != null:
				_auto_submit()
		KEY_F:
			if _state == S_MAP:
				_use_torch()
		KEY_C:
			if _state == S_MAP:
				_do_camp()


func _on_click(pos: Vector2) -> void:
	# 地图上点房间优先：房间就在眼前，右侧才是按钮区
	if _state == S_MAP:
		for h in _room_hits:
			if (h.rect as Rect2).has_point(pos):
				_travel_to(int(h.id))
				return

	# 战斗里选目标优先于按钮：目标就在场上，按钮在角落，误点的代价不一样
	if _state == S_BATTLE and _battle != null and _battle.awaiting_input != null and not _pending.is_empty():
		for s in _slots:
			if (s.rect as Rect2).has_point(pos):
				_pick_target(int(s.uid))
				return

	for b in _buttons:
		if not bool(b.enabled):
			continue
		if (b.rect as Rect2).has_point(pos):
			_activate(str(b.id))
			return


func _pick_target(uid: int) -> void:
	if _pending.is_empty():
		return
	var pool: Array = _pending.get("targets", [])
	for t in pool:
		if int(t.uid) == uid:
			_submit(_pending.action, [t])
			return


func _activate(id: String) -> void:
	if id.begins_with("upgrade:"):
		var hid_u: String = id.substr(8)
		if campaign.upgrade(hid_u):
			campaign.save()
			_flash_msg("%s 升到 %d 阶" % [_hero_label(hid_u), campaign.gear_of(hid_u)])
		return
	if id.begins_with("recruit:"):
		var hid_r: String = id.substr(8)
		if campaign.recruit(hid_r):
			campaign.save()
			_flash_msg("%s 归队" % _hero_label(hid_r))
		return
	if id.begins_with("goto:"):
		if _battle != null:
			_move_mode = false
			_battle.submit_move(int(id.substr(5)))
			_drain_battle_events()
			_options = []
			_pending = {}
			_step_timer = _step_delay
		return
	if id.begins_with("skill:"):
		var idx: int = int(id.substr(6))
		if idx < 0 or idx >= _options.size():
			return
		var opt: Dictionary = _options[idx]
		var action: Dictionary = opt.action
		_pending = opt
		if bool(action.target_aoe) or (opt.targets as Array).size() == 1:
			_submit(action, opt.targets)
		return
	# —— 出发准备 ——
	if id.begins_with("prep:"):
		# prep:<size>:<level>[:<quest>]
		var parts: PackedStringArray = id.split(":", false)
		if parts.size() >= 3:
			_prep_size = str(parts[1])
			_prep_level = int(parts[2])
			_prep_quest = str(parts[3]) if parts.size() > 3 else "explore"
			_prep_pack = _default_prep_pack()
			# 默认名单按**这一趟的等级**筛（M25），不能直接取 Campaign.default_party()：
			# 那样会把等级太高的人排进去，玩家要按到「出发」才看到报错。
			_prep_party = _party_for(_prep_level)
			_state = S_PREP
			queue_redraw()
		return
	if id.begins_with("prep_pick:"):
		_toggle_party(str(id.substr(10)))
		return
	if id.begins_with("prep_add:") or id.begins_with("prep_sub:"):
		var add: bool = id.begins_with("prep_add:")
		var sid: String = id.substr(9)
		_adjust_pack(sid, 1 if add else -1)
		return
	if id.begins_with("shop_buy:"):
		var why: String = campaign.buy_shop_trinket(int(id.substr(9)))
		if why.is_empty():
			_flash_msg("买下 %d 件" % 1)
			campaign.save()
		else:
			_flash_msg(_shop_reason(why))
		queue_redraw()
		return
	if id.begins_with("shop_sell:"):
		var si: int = int(id.substr(10))
		var sold: String = str(campaign.trinket_store[si]) if si >= 0 \
			and si < campaign.trinket_store.size() else ""
		var err2: String = campaign.sell_trinket(si)
		if err2.is_empty():
			_flash_msg("卖掉 %s，+%d 金币" % [DdNames.trinket_name(sold),
				campaign.shop.trinket_sell_price(sold)])
			campaign.save()
		else:
			_flash_msg(_shop_reason(err2))
		queue_redraw()
		return
	if id.begins_with("tk_store:"):
		# 点仓库里的一件：选中/取消选中。真正装上去要等玩家点某个槽，
		# 因为「装给谁」是这一屏唯一的决策，替玩家决定就失去意义了。
		var sid: String = id.substr(9)
		_sel_trinket = "" if _sel_trinket == sid else sid
		queue_redraw()
		return
	if id.begins_with("tk_slot:"):
		# tk_slot:<hid>:<slot>
		var rest: String = id.substr(8)
		var cut: int = rest.rfind(":")
		if cut > 0:
			_toggle_slot(rest.substr(0, cut), int(rest.substr(cut + 1)))
		return
	if id.begins_with("bld:"):
		var bid: String = id.substr(4)
		# 公会和商队是「已有屏的入口」，不重复造一个只有两个按钮的中间屏
		if bid == "guild":
			var av2: Array = campaign.alive_ids()
			_guild_hero = str(av2[0]) if not av2.is_empty() else ""
			_state = S_GUILD
		else:
			_building = bid
			var av3: Array = campaign.alive_ids()
			_building_hero = str(av3[0]) if not av3.is_empty() else ""
			# M30 修正：这里一直漏了 `_state = S_BUILDING`。
			# 只赋值 `_building` 不改状态的话，点了等于什么都没发生——
			# 而公会那条分支改了状态，所以八座建筑里只有它能进。
			# 表现上完全一致（按钮都高亮、都有 hover），所以两年期都没人发现。
			_fire_pending = ""
			_state = S_BUILDING
		queue_redraw()
		return
	if id.begins_with("bld_hero:"):
		_building_hero = id.substr(9)
		_fire_pending = ""    # 换人就取消上膛，否则会误删下一个选中的人
		queue_redraw()
		return
	if id.begins_with("bld_act:"):
		_do_building_action(id.substr(8))
		return
	if id.begins_with("hire:"):
		_do_hire(id.substr(5))
		return
	if id.begins_with("fire:"):
		# 第一次点只是「上膛」，第二次才真的删（见 _fire_pending 的注释）
		_fire_pending = id.substr(5)
		queue_redraw()
		return
	if id.begins_with("fire2:"):
		_do_fire(id.substr(6))
		return
	if id == "bld_back":
		_state = S_TOWN
		queue_redraw()
		return
	if id.begins_with("dungeon:"):
		# 换区域不改难度：玩家常常「还是这张短图，换个地方打」。
		# M32：区域现在同时决定「看哪一块板子」——任务板长在区域上，
		# 不跟着切的话会出现「顶着海湾的标题挑 weald 的任务」。
		_dungeon = id.substr(8)
		campaign.select_board_region(_dungeon)
		queue_redraw()
		return
	if id.begins_with("guild_pick:"):
		_guild_hero = id.substr(11)
		queue_redraw()
		return
	if id.begins_with("guild_skill:"):
		_toggle_skill(id.substr(12))
		return
	match id:
		"prep_go":
			_launch_with_pack()
		"prep_back":
			_state = S_TOWN
			queue_redraw()
		"open_guild":
			var av: Array = campaign.alive_ids()
			_guild_hero = str(av[0]) if not av.is_empty() else ""
			_state = S_GUILD
			queue_redraw()
		"close_guild":
			_state = S_TOWN
			queue_redraw()
		"idle_week":
			var iw: String = campaign.idle_week()
			if iw.is_empty():
				campaign.save()
				_flash_msg("过了一周")
			else:
				_flash_msg(iw)
			queue_redraw()
		"open_shop":
			_sel_trinket = ""
			_state = S_SHOP
			queue_redraw()
		"close_shop":
			_state = S_TOWN
			queue_redraw()
		"open_trinkets":
			_sel_trinket = ""
			_state = S_TRINKET
			queue_redraw()
		"close_trinkets":
			_sel_trinket = ""
			_state = S_TOWN
			queue_redraw()
		"start_short":
			_start_expedition("short", 1)
		"start_medium":
			_start_expedition("medium", 3)
		"start_long":
			_start_expedition("long", 5)
		"torch":
			_use_torch()
		"camp":
			_do_camp()
		"retreat":
			_do_retreat()
		"leave":
			_leave_dungeon()
		"pass":
			_submit({}, [])
		"movemode":
			_move_mode = true
			queue_redraw()
		"movecancel":
			_move_mode = false
			queue_redraw()
		"restart":
			back_to_town()

func back_to_town() -> void:
	_state = S_TOWN
	_sel_trinket = ""
	exp = null
	_battle = null
	_options = []
	_pending = {}
	_settled = false
	_log.clear()


# ============================================================
# 绘制
# ============================================================

func _draw() -> void:
	draw_rect(Rect2(Vector2.ZERO, size), DdTheme.BG)
	_buttons.clear()
	_slots.clear()
	_room_hits.clear()
	if db == null:
		return

	match _state:
		S_TOWN:
			_draw_town()
		S_MAP:
			_draw_map()
		S_BATTLE:
			_draw_battle()
		S_RESULT:
			_draw_result()
		S_TRINKET:
			_draw_trinket()
		S_PREP:
			_draw_prep()
		S_SHOP:
			_draw_shop()
		S_GUILD:
			_draw_guild()
		S_BUILDING:
			_draw_building()

	_draw_buttons()
	_draw_floaters()

	if _flash_life > 0.0:
		var a: float = clampf(_flash_life, 0.0, 1.0)
		_text(Vector2(0, 96), _flash, DdTheme.FONT_HERO, Color(DdTheme.CRIT.r, DdTheme.CRIT.g, DdTheme.CRIT.b, a),
			HORIZONTAL_ALIGNMENT_CENTER, size.x)


# —— 基础绘制工具 ——

func _text(pos: Vector2, s: String, fs: int, col: Color,
		align: int = HORIZONTAL_ALIGNMENT_LEFT, width: float = -1.0) -> void:
	draw_string(_font, pos, s, align, width, fs, col)


func _panel(r: Rect2, bg: Color = DdTheme.PANEL, edge: bool = true) -> void:
	draw_rect(r, bg)
	if edge:
		draw_rect(r, DdTheme.PANEL_EDGE, false, 1.0)


## 可点方块的统一外观（M31）。
##
## 之前每个调用点自己 draw_rect，于是「选中」有三种长相：
## 城镇区域按钮是 2px 蓝边、准备屏出战卡是 ✓ 前缀、建筑行只是 hover 提亮。
## 同一种状态三种表现，玩家每换一屏都要重新学一遍「我选了什么」。
enum { TILE_IDLE, TILE_HOVER, TILE_ACTIVE, TILE_OFF, TILE_DANGER }


func _tile(r: Rect2, st: int, bg: Color = DdTheme.PANEL_DEEP) -> void:
	match st:
		TILE_ACTIVE:
			draw_rect(r, DdTheme.BTN_ACTIVE)
			draw_rect(r, DdTheme.PARTY, false, 2.0)
		TILE_HOVER:
			draw_rect(r, DdTheme.BTN_HOVER)
			draw_rect(r, DdTheme.DIM, false, 1.0)
		TILE_OFF:
			draw_rect(r, DdTheme.BTN_OFF)
			draw_rect(r, DdTheme.PANEL_EDGE, false, 1.0)
		TILE_DANGER:
			draw_rect(r, DdTheme.BTN)
			draw_rect(r, DdTheme.CRIT, false, 2.0)
		_:
			draw_rect(r, bg)
			draw_rect(r, DdTheme.PANEL_EDGE, false, 1.0)


func _bar(r: Rect2, ratio: float, fill: Color, track: Color) -> void:
	draw_rect(r, track)
	var w: float = clampf(ratio, 0.0, 1.0) * r.size.x
	if w > 0.5:
		draw_rect(Rect2(r.position, Vector2(w, r.size.y)), fill)


## 所有屏共用的表头：一条 56 高的横带，标题在左、提示在右。
##
## 高度、边距、字号都从令牌取——之前 52 是写死的，五处内容面板按 88 起排，
## 中间那 36px 的空白没有任何依据，改一次要试半天。
func _header(title: String, hint: String) -> void:
	draw_rect(Rect2(0, 0, size.x, DdTheme.HEADER_H), DdTheme.PANEL)
	draw_line(Vector2(0, DdTheme.HEADER_H), Vector2(size.x, DdTheme.HEADER_H),
		DdTheme.PANEL_EDGE, 1.0)
	_text(Vector2(DdTheme.MARGIN, 33), title, DdTheme.FONT_H1, DdTheme.TEXT)
	_text(Vector2(size.x - 620, 32), hint, DdTheme.FONT_MD, DdTheme.FAINT,
		HORIZONTAL_ALIGNMENT_RIGHT, 592)


func _draw_buttons() -> void:
	for b in _buttons:
		var r: Rect2 = b.rect
		var label: String = str(b.get("label", ""))
		if label.is_empty():
			continue
		var hover: bool = r.has_point(_mouse)
		var enabled: bool = bool(b.enabled)
		# 危险态（M28）：解雇的「再点一次确认」必须一眼看出和平常按钮不一样。
		# 只改文字不改样式没用——玩家连点两下时不会读字。
		var danger: bool = bool(b.get("danger", false))
		var st: int = TILE_IDLE
		if not enabled:
			st = TILE_OFF
		elif danger:
			st = TILE_DANGER
		elif hover:
			st = TILE_HOVER
		_tile(r, st, DdTheme.BTN)
		_text(Vector2(r.position.x, r.position.y + r.size.y * 0.5 + 5.0), label, DdTheme.FONT_BD, DdTheme.FAINT if not enabled else (DdTheme.CRIT if danger else DdTheme.TEXT),
			HORIZONTAL_ALIGNMENT_CENTER, r.size.x)


func _add_button(r: Rect2, id: String, label: String, enabled: bool = true,
		danger: bool = false) -> void:
	_buttons.append({"rect": r, "id": id, "label": label, "enabled": enabled, "danger": danger})


func _add_hit(r: Rect2, id: String) -> void:
	_buttons.append({"rect": r, "id": id, "label": "", "enabled": true})


func _draw_floaters() -> void:
	for f in _floaters:
		var col: Color = f.color
		col.a = clampf(f.life, 0.0, 1.0)
		_text(f.pos - Vector2(80, 0), str(f.text), 15 if not f.big else 20, col,
			HORIZONTAL_ALIGNMENT_CENTER, 160)


func _spawn_float(uid: int, text: String, col: Color, big: bool = false) -> void:
	var pos: Vector2 = _slot_center(uid)
	if pos == Vector2(-1, -1):
		return
	_floaters.append({"pos": pos + Vector2(randf_range(-12, 12), 0), "text": text,
		"color": col, "life": 1.1, "big": big})


func _slot_center(uid: int) -> Vector2:
	for s in _slots:
		if int(s.uid) == uid:
			var r: Rect2 = s.rect
			return Vector2(r.position.x + r.size.x * 0.5, r.position.y + r.size.y * 0.38)
	return Vector2(-1, -1)


# ============================================================
# 城镇屏（元层）
# ============================================================

func _draw_town() -> void:
	# 副标题把「每周恢复多少」写出来：不写的话「休整一周」看起来只是浪费时间，
	# 玩家不会知道那 50 金买到了什么。
	var wk_relief: int = int((campaign.cfg.get("town_cycle", {}) as Dictionary).get(
		"weekly_stress_relief", 0))
	_header("城镇 · 第 %d 周" % campaign.week,
		"远征 %d 趟 · 每周恢复 %d 压力 · 任务板每周按名册重抽" % [campaign.expeditions, wk_relief])

	# —— 资源 ——
	# 纵向重排（M31）：视口是 1280×760，而内容原来只排到 586，
	# 底下空了 174px——看起来像「这屏还没画完」。现在按 760 重新分配。
	var y: float = 76.0
	_text(Vector2(28, y), "金币 %d" % campaign.gold, DdTheme.FONT_BD, DdTheme.CRIT)
	var hx: float = 180.0
	for k in campaign.heirlooms.keys():
		_text(Vector2(hx, y), "%s %d" % [DdNames.heirloom_name(str(k)), int(campaign.heirlooms[k])], DdTheme.FONT_MD, DdTheme.DIM)
		hx += 110.0
	if campaign.best_steps > 0:
		_text(Vector2(size.x - 28, y), "最深推进 %d 间房" % campaign.best_steps, DdTheme.FONT_MD, DdTheme.FAINT, HORIZONTAL_ALIGNMENT_RIGHT, 260)

	# —— 名册 ——
	# **名册 ≠ 队伍**：名册是「你拥有的英雄」，出战上限恒为 4 人。
	# 这两件事必须在屏幕上分开说，否则「5 张卡」会被读成「5 人队」——
	# M18 之后第一版就栽在这里。
	var ids: Array = campaign.hero_ids()
	var alive_n: int = campaign.alive_ids().size()
	# 名册布局（M27）：最多 15 人（= 职业总数），所以改成「每行 8 张的小卡 + 两行」。
	#
	# 卡片从 240 压到 112：城镇屏只回答「谁在、几级、压力多少、忙不忙」，
	# 生命/护甲/闪避这些细节在铁匠铺面板里看——和 M22 的分层是同一个方向。
	# 一行大卡放不下 15 个人，而「看不到我有哪些人」比「看不到闪避」糟得多。
	var per_row: int = 8
	var tgap: float = 10.0
	var cw: float = (size.x - 56.0 - tgap * float(per_row - 1)) / float(per_row)
	var tile_h: float = 116.0
	_text(Vector2(28, 96), "名册 %d 人 · 存活 %d · 每次出战最多 %d 人" % [
		ids.size(), alive_n, Campaign.PARTY_MAX], DdTheme.FONT_MD, DdTheme.DIM)
	if alive_n == 0:
		# 警告挪到标题右边：原来占第二行，会把刚压下来的卡片往下挤。
		_text(Vector2(380, 96),
			"全员阵亡 · 免费征召还剩 %d 次" % campaign.free_recruits, DdTheme.FONT_MD, DdTheme.WARN)
	for i in ids.size():
		var col: int = i % per_row
		var row: int = i / per_row
		_draw_hero_tile(str(ids[i]), Rect2(28.0 + float(col) * (cw + tgap),
			112.0 + float(row) * (tile_h + 8.0), cw, tile_h))

	# 空着的第二行不该是一片黑（M31）：名册 4 人的档看起来像「界面没加载完」。
	# 这里把「还能招几个」写进那块空白——它本来就是玩家此刻该知道的事。
	var rows_used: int = int(ceil(float(ids.size()) / float(per_row)))
	var cap: int = campaign.roster_max()
	if rows_used < 2 and ids.size() < cap:
		_text(Vector2(28, 112.0 + tile_h + 8.0 + 40.0),
			"名册还有 %d 个空位（上限 %d）—— 马车每周来一批新人，缺人就先去招。" % [
				cap - ids.size(), cap],
			DdTheme.FONT_MD, DdTheme.FAINT)

	# —— 出发 ——
	# 区域选择（M20）：四个区域的遭遇表 / 地图参数 / 奇物池全是分开的，
	# 但 M7~M19 一直硬编码 weald。这里让它成为一屏之内的选择，
	# 而不是「换个区域要改代码重开」。
	_text(Vector2(28, 388), "出发 · %s" % DdNames.dungeon_name(_dungeon), DdTheme.FONT_BD, DdTheme.TEXT)
	_text(Vector2(690, 387), DdNames.dungeon_tag(_dungeon), DdTheme.FONT_MD, DdTheme.FAINT)
	var dungeons: Array = ["weald", "crypts", "warrens", "cove"]
	for i in dungeons.size():
		var did: String = str(dungeons[i])
		var on: bool = did == _dungeon
		var dr := Rect2(210.0 + float(i) * 118.0, 372.0, 110.0, 28.0)
		var dst: int = TILE_ACTIVE if on else (TILE_HOVER if dr.has_point(_mouse) else TILE_IDLE)
		_tile(dr, dst)
		_text(Vector2(dr.position.x, dr.position.y + 19.0), DdNames.dungeon_name(did), DdTheme.FONT_MD, DdTheme.TEXT if on else DdTheme.DIM, HORIZONTAL_ALIGNMENT_CENTER, dr.size.x)
		_add_hit(dr, "dungeon:" + did)

	# 休整一周（M24）：时间第一次成为可以主动消耗的东西。
	# 和出发放在同一行，因为这是同一层的选择——这周出门，还是在家待着。
	var idle_cost: int = int((campaign.cfg.get("town_cycle", {}) as Dictionary).get("idle_cost", 50))
	_add_button(Rect2(880, 372, 152, 28), "idle_week",
		"休整一周（%d 金）" % idle_cost, campaign.gold >= idle_cost)

	var alive: int = campaign.alive_ids().size()
	# 等级不再写死（M26）：`campaign.board` 每周按名册强度重抽。
	# 尺寸和槽位顺序仍然是固定的——那是我们只有四张卡时唯一的记忆点。
	var rows: Array = _board_rows()
	# 难度卡是 4 张，宽度不能跟着名册的「每行 8 格」走。
	var dcw: float = (size.x - 56.0 - 16.0 * 3.0) / 4.0
	for i in rows.size():
		var row: Array = rows[i]
		var r := Rect2(28.0 + float(i) * (dcw + 16.0), 416.0, dcw, 98.0)
		_panel(r)
		draw_rect(Rect2(r.position, Vector2(r.size.x, 3)), DdTheme.PARTY)
		_text(Vector2(r.position.x + 16, r.position.y + 30), str(row[2]), DdTheme.FONT_LG, DdTheme.TEXT if alive > 0 else DdTheme.FAINT)
		_text(Vector2(r.position.x + 16, r.position.y + 50), str(row[3]), DdTheme.FONT_SM, DdTheme.DIM)
		# 情报（M21）：这一档会遇到什么。原来卡片只说「几级怪、几场」，
		# 玩家点进去之前完全不知道对面是疯狗还是骷髅——而这两者的应对完全不同。
		var info: Dictionary = db.encounter_outline(_dungeon, int(row[1]))
		var foes: String = _foe_brief(info, str(row[4]))
		if not foes.is_empty():
			_text(Vector2(r.position.x + 16, r.position.y + 68), foes, DdTheme.FONT_SM, DdTheme.FAINT)
		# 「够格几人」（M25）——它替代了原来的「可出战几人」。
		# 后者只数活人，不回答「我能不能打这一档」；等级锁上来之后，
		# 一支满编队伍对学徒本完全可能是「0 人够格」。
		var qlv: int = int(row[1])
		var fit: int = _fit_count(qlv)
		var fit_col: Color = DdTheme.OK if fit >= Campaign.PARTY_MAX else DdTheme.WARN
		if fit <= 0:
			fit_col = DdTheme.CRIT
		_text(Vector2(r.position.x + 16, r.position.y + 86), "够格 %d 人" % fit, DdTheme.FONT_TAG, fit_col)
		if alive > 0 and fit <= 0:
			# 一个都不够格只有一种可能：**全员等级过高**。
			# 低等级永远能进，只有超出 2 级才会被拒（见 Campaign.can_join）。
			_text(Vector2(r.position.x + 84, r.position.y + 86), "全都超级了", DdTheme.FONT_TAG, DdTheme.CRIT)
		elif alive > 0 and fit < Campaign.PARTY_MAX:
			_text(Vector2(r.position.x + 84, r.position.y + 86),
				"缺 %d 人" % (Campaign.PARTY_MAX - fit), DdTheme.FONT_TAG, DdTheme.WARN)
		if alive > 0 and fit > 0:
			# 点难度卡不再直接出发，而是进「出发准备」——
			# 补给是这一屏唯一能在出发前调整的东西，
			# 直接开走等于把这层决策藏起来。
			_add_hit(r, "prep:%s:%d:%s" % [str(row[0]), int(row[1]), str(row[4])])
			if r.has_point(_mouse):
				draw_rect(r, Color(1, 1, 1, 0.04))
				draw_rect(r, DdTheme.DIM, false, 1.0)

	# —— 说明 ——
	# 整块板子都带不动是会发生的（名册全员 5 级，而保底槽是学徒本）。
	# 这时候必须明说「去招人」——不说的话，四张卡全是红字「全都超级了」，
	# 玩家的第一反应是「存档坏了」，而不是「我该换一批人」。
	if alive > 0 and not campaign.board_has_runnable():
		_text(Vector2(28, 642),
			"这周的任务板你一个人都带不动 —— 去马车招募新人，或者休整一周等下一批。", DdTheme.FONT_MD, DdTheme.CRIT)
	else:
		_text(Vector2(28, 642),
			"任务板每周按名册等级重抽；装备要用金币和传家宝升级；阵亡后花钱招募，全员阵亡给免费征召。", DdTheme.FONT_MD, DdTheme.DIM)
	_text(Vector2(28, 664),
		"战利品只在远征里拿：赢一场就有，走完全程另有结算奖励，撤退只保得住已到手的。", DdTheme.FONT_MD, DdTheme.FAINT)
	# —— 建筑入口（M22）——
	# 城镇屏原来同时摆着「5 张英雄卡（卡上还有招募/升级按钮）+ 4 张难度卡 +
	# 3 个角落按钮 + 2 行说明」——那不是信息多，是没分层。
	# 现在英雄卡只负责显示状态，所有「对你做点什么」的动作都进建筑。
	var bw: float = (size.x - 56.0 - 8.0 * float(BUILDINGS.size() - 1)) / float(BUILDINGS.size())
	for i in BUILDINGS.size():
		var b: Array = BUILDINGS[i]
		var bid: String = str(b[0])
		var rb := Rect2(28.0 + float(i) * (bw + 8.0), 560.0, bw, 52.0)
		var bst: int = TILE_HOVER if rb.has_point(_mouse) else TILE_IDLE
		_tile(rb, bst)
		_text(Vector2(rb.position.x, rb.position.y + 19.0), str(b[1]), DdTheme.FONT_BD, DdTheme.TEXT,
			HORIZONTAL_ALIGNMENT_CENTER, rb.size.x)
		_text(Vector2(rb.position.x, rb.position.y + 37.0), str(b[2]), DdTheme.FONT_TAG, DdTheme.FAINT,
			HORIZONTAL_ALIGNMENT_CENTER, rb.size.x)
		_add_hit(rb, "bld:" + bid)
	if _dev_ui:
		_text(Vector2(28, 628), "存档：%s" % _save_path, DdTheme.FONT_SM, DdTheme.FAINT)


## 一句话情报。首领任务报首领池（「首领：海妖、溺亡船长」），
## 普通任务报这一档最常见的两种怪。
##
## 只报基础名，不报具体是哪一只——遭遇是随机抽的，
## 写死一个名字等于撒谎。报「可能出现哪几种」才是诚实的说法。
func _foe_brief(info: Dictionary, quest: String) -> String:
	var ids: Array = info.get("bosses" if quest == "kill_boss" else "common", [])
	if ids.is_empty():
		return ""
	var names: Array = []
	for i in ids.slice(0, 2):
		names.append(DdNames.monster_name(str(i)))
	return ("首领：" if quest == "kill_boss" else "主要：") + "、".join(names)


## 存活英雄的平均装备阶。用来判断「这趟够不够格」，不是精确战力评估。
## 不传 `ids` 就是整个存活名册；传了就是这几个人（准备屏要算的是**出战名单**）。
func _party_gear_avg(ids: Array = []) -> int:
	var who: Array = ids if not ids.is_empty() else campaign.alive_ids()
	if who.is_empty():
		return 0
	var s: int = 0
	for hid in who:
		s += campaign.gear_of(hid)
	return int(round(float(s) / float(who.size())))


## 名册里有几个人能进这个等级的本（M25）。
##
## 逻辑在 `Campaign.fit_count` 里，这里只转发——任务板的权重也算同一件事，
## 两处各写一遍的话，改规则时必然只改一处，然后界面和板子对不上。
func _fit_count(quest_level: int) -> int:
	return campaign.fit_count(quest_level)


## 默认出战名单：够格的人里，**最能打的那 4 个**（M27）。
##
## 不能直接用 `Campaign.default_party()`——它不知道这一趟打几级。
## 也不能「按名册顺序取前 4」：名册顺序是加入顺序，和强度无关。
## 名册扩到 15 人之后，按顺序取会默认派上刚到手的 4 个 1 级新人，
## 而后面明明坐着一排 4 级老将——玩家每次都要手动改，那就等于没有默认值。
func _party_for(level: int) -> Array:
	var cands: Array = []
	for hid in campaign.selectable_ids():
		if campaign.can_join(str(hid), level):
			cands.append(str(hid))
	return _sort_by_power(cands).slice(0, mini(Campaign.PARTY_MAX, cands.size()))


## 按「等级 → 装备阶」降序。
##
## 准备屏的列表和默认出战名单**必须用同一个序**：两边不一致的话，
## 玩家会看到「前两行一个勾都没有，最后一行全勾上」，第一反应是选中逻辑坏了。
func _sort_by_power(arr: Array) -> Array:
	var out: Array = arr.duplicate()
	out.sort_custom(func(a: String, b: String) -> bool:
		var la: int = campaign.resolve_of(a)
		var lb: int = campaign.resolve_of(b)
		if la != lb:
			return la > lb
		return campaign.gear_of(a) > campaign.gear_of(b))
	return out


## 城镇名册的一张卡（M27，112 高）。
##
## 从 240 高压缩过来的：名册要能显示 15 个人，一行大卡放不下。
## 砍掉的是「生命 / 护甲 / 闪避」那一块——那些在铁匠铺面板里有，
## 而城镇屏真正要回答的只有四件事：谁在、几级、压力多少、这周忙不忙。
func _draw_hero_tile(hid: String, r: Rect2) -> void:
	var row: Dictionary = campaign.hero(hid)
	var alive: bool = bool(row.get("alive", false))
	_panel(r)
	draw_rect(Rect2(r.position, Vector2(r.size.x, 3)),
		DdTheme.PARTY if alive else Color("#3a3a3a"))

	# 名字最长四字（瘟疫医生），13px 约 52px，144 宽的卡放得下
	_text(Vector2(r.position.x + 10, r.position.y + 22), _hero_label(hid), DdTheme.FONT_BD, DdTheme.TEXT if alive else DdTheme.FAINT)

	# 忙要单独标：名册里「忙」和「阵亡」看起来一样（都是不能出征），
	# 但一个是等几周、一个是花钱重招。不区分玩家会点进去骂人。
	var busy: int = campaign.busy_of(hid)
	if alive and busy > 0:
		_text(Vector2(r.position.x + r.size.x - 10, r.position.y + 22), "忙 %d 周" % busy, DdTheme.FONT_TAG, DdTheme.WARN, HORIZONTAL_ALIGNMENT_RIGHT, 64)

	_text(Vector2(r.position.x + 10, r.position.y + 40),
		"Lv%d · 装备 %d 阶" % [campaign.resolve_of(hid), campaign.gear_of(hid)], DdTheme.FONT_SM, DdTheme.DIM)

	var st: float = float(row.get("stress", 0.0))
	_bar(Rect2(r.position.x + 10, r.position.y + 48, r.size.x - 20, 4),
		st / 200.0, DdTheme.STRESS, DdTheme.STRESS_TRACK)
	_text(Vector2(r.position.x + 10, r.position.y + 64), "压力 %.0f" % st, DdTheme.FONT_TAG, DdTheme.STRESS if st >= 100.0 else DdTheme.FAINT)

	# 病 / 负面怪癖：有病整行转警告色，那是唯一需要立刻去疗养院的状态
	var dn: int = campaign.diseases_of(hid).size()
	var qn: int = campaign.negative_quirks_of(hid).size()
	var bits: Array = []
	if dn > 0:
		bits.append("病 %d" % dn)
	if qn > 0:
		bits.append("负 %d" % qn)
	if not bits.is_empty():
		_text(Vector2(r.position.x + 10, r.position.y + 80), " · ".join(bits), DdTheme.FONT_TAG, DdTheme.WARN if dn > 0 else DdTheme.FAINT)

	# 最后一行：这张卡现在「卡在哪」。三种状态互斥，只写一条。
	if not alive:
		_text(Vector2(r.position.x + 10, r.position.y + 98), "已阵亡 · 马车可招", DdTheme.FONT_TAG, DdTheme.WARN)
	elif campaign.gear_of(hid) >= Campaign.MAX_GEAR:
		_text(Vector2(r.position.x + 10, r.position.y + 98), "已满阶", DdTheme.FONT_TAG, DdTheme.OK)
	elif campaign.upgrade_cost(hid).is_empty():
		_text(Vector2(r.position.x + 10, r.position.y + 98),
			"要 Lv%d 才能升装备" % (campaign.gear_of(hid) + 2), DdTheme.FONT_TAG, DdTheme.FAINT)
	else:
		_text(Vector2(r.position.x + 10, r.position.y + 98), "铁匠铺可升级", DdTheme.FONT_TAG, DdTheme.FAINT)


# ============================================================
# 地图屏
# ============================================================

func _draw_map() -> void:
	if exp == null:
		return
	var tier: String = ExpeditionCfg.light_tier_name(exp.light)
	_header("远征 · %s · %s %s" % [DdNames.dungeon_name(_dungeon),
		_size_name_of(_size), "Lv%d" % _level],
		"点相邻房间移动    F 点火把    C 休整    Esc 撤退")

	# —— 资源条 ——
	var y: float = 76.0
	_text(Vector2(24, y), "光照", DdTheme.FONT_MD, DdTheme.DIM)
	_bar(Rect2(60, y - 10, 148, 12), exp.light / 100.0, DdTheme.LIGHT, DdTheme.PANEL_DEEP)
	_text(Vector2(214, y), "%.0f · %s" % [exp.light, tier], DdTheme.FONT_MD, DdTheme.LIGHT if exp.light < 50.0 else DdTheme.DIM)
	_text(Vector2(316, y), "口粮 %d" % exp.food, DdTheme.FONT_MD, DdTheme.FOOD)
	_text(Vector2(386, y), "火把 %d" % exp.torch, DdTheme.FONT_MD, DdTheme.LIGHT)
	_text(Vector2(456, y), "铁锹 %d" % exp.shovel, DdTheme.FONT_MD, DdTheme.FOOD if exp.shovel <= 0 else DdTheme.DIM)
	_text(Vector2(524, y), "休整 %d" % exp.camps_left, DdTheme.FONT_MD, DdTheme.DIM)
	_text(Vector2(592, y), "已探明 %d/%d 间" % [exp.spotted.size(),
		(exp.map["room_ids"] as Array).size()], DdTheme.FONT_MD, DdTheme.OK)
	_text(Vector2(size.x - 24, y), "侦察 %.0f%%" % (exp.scout_chance() * 100.0), DdTheme.FONT_MD, DdTheme.OK if exp.scout_chance() >= 0.6 else DdTheme.FAINT,
		HORIZONTAL_ALIGNMENT_RIGHT, 200)

	# 地图区域按接近正方形给：5×5 的图放在宽扁区域里，格子只能按高度定，
	# 于是左右各空一大片。收窄之后格子填满，省下的宽度给右面板。
	_draw_grid_map(Rect2(24, 96, 470, 350))
	_draw_room_panel(Rect2(510, 96, size.x - 534, 350))
	_draw_party_strip(Rect2(24, 456, size.x - 48, 100))
	_draw_log_panel(Rect2(24, 566, size.x - 48, 146))
	_text(Vector2(24, 732),
		"光照决定你能提前看见多远：明亮侦察 +15%、微光 +7.5%，昏暗以下基本摸黑。", DdTheme.FONT_MD, DdTheme.FAINT)


## 房间图。只画「已经探明」的房间——没探明的连位置都不显示，
## 否则侦察就没有意义了。
func _draw_grid_map(r: Rect2) -> void:
	var m: Dictionary = exp.map
	var grid: Array = m["grid"]
	var rooms: Dictionary = m["rooms"]

	# 视野跟着「已探明的房间」走：只框住已知区域向外扩一格。
	# 固定按整张网格画的话，开局只有两间房却占满一整屏，看着像空页面。
	var minx: int = 999
	var maxx: int = -999
	var miny: int = 999
	var maxy: int = -999
	for id in (m["room_ids"] as Array):
		if not exp.is_room_spotted(int(id)):
			continue
		var p0: Vector2i = (rooms[int(id)] as Dictionary)["pos"]
		minx = mini(minx, p0.x); maxx = maxi(maxx, p0.x)
		miny = mini(miny, p0.y); maxy = maxi(maxy, p0.y)
	if minx > maxx:
		minx = 0; maxx = 0; miny = 0; maxy = 0
	minx = maxi(minx - 1, 0); maxx = mini(maxx + 1, int(grid[0]) - 1)
	miny = maxi(miny - 1, 0); maxy = mini(maxy + 1, int(grid[1]) - 1)
	var gx0: int = minx
	var gy0: int = miny
	var cols: int = maxx - minx + 1
	var rows: int = maxy - miny + 1

	# 格子必须接近正方：按宽度铺满会让房间横向稀疏、纵向拥挤，
	# 看起来像表格而不是地图。取两边较小的那个，再整体居中。
	var cell: float = minf(r.size.x / float(cols), r.size.y / float(rows))
	var cw: float = cell
	var ch: float = cell
	# 房间要留出走廊中点的位置：徽标半径 8，两边各让 12——
	# 不留的话「陷」会压在房间边框上，看起来像房间自己的标记。
	var bw: float = minf(56.0, cell - 30.0)
	var bh: float = minf(cell * 0.68, cell - 28.0)
	var origin: Vector2 = r.position + Vector2(
		(r.size.x - cell * float(cols)) * 0.5, (r.size.y - cell * float(rows)) * 0.5)

	var cell_center := func(gx: int, gy: int) -> Vector2:
		return origin + Vector2(float(gx - gx0) * cw + cw * 0.5, float(gy - gy0) * ch + ch * 0.5)

	# 点阵背景：只给空间感，不泄露房间位置
	for gx in cols:
		for gy in rows:
			draw_circle(origin + Vector2(float(gx) * cw + cw * 0.5, float(gy) * ch + ch * 0.5),
				1.2, Color(DdTheme.PANEL_EDGE.r, DdTheme.PANEL_EDGE.g, DdTheme.PANEL_EDGE.b, 0.7))

	# 走廊：两端都探明才画
	var edge_i: int = 0
	for e in (m["edges"] as Array):
		var ei_now: int = edge_i
		edge_i += 1
		var ea: int = int(e.a)
		var eb: int = int(e.b)
		if not exp.is_room_spotted(ea) or not exp.is_room_spotted(eb):
			continue
		var pa: Vector2i = (rooms[ea] as Dictionary)["pos"]
		var pb: Vector2i = (rooms[eb] as Dictionary)["pos"]
		var ca: Vector2 = cell_center.call(pa.x, pa.y)
		var cb: Vector2 = cell_center.call(pb.x, pb.y)
		if bool(e.get("walked", false)):
			draw_line(ca, cb, Color(DdTheme.LIGHT.r, DdTheme.LIGHT.g, DdTheme.LIGHT.b, 0.65), 5.0)
		else:
			draw_dashed_line(ca, cb, DdTheme.DIM, 2.0, 5.0)
		_edge_badge((ca + cb) * 0.5, exp.edge_kind(ei_now))

	# 房间
	for id in (m["room_ids"] as Array):
		var rid: int = int(id)
		if not exp.is_room_spotted(rid):
			continue
		var rr: Dictionary = rooms[rid]
		var pos: Vector2i = rr["pos"]
		var center: Vector2 = cell_center.call(pos.x, pos.y)
		var box := Rect2(center - Vector2(bw, bh) * 0.5, Vector2(bw, bh))
		var kind: String = str(rr["kind"])
		var visited: bool = bool(rr.get("visited", false))
		var is_cur: bool = rid == exp.current_room
		var movable: bool = _is_adjacent(rid)

		draw_rect(box, DdTheme.PANEL_HI if visited else DdTheme.PANEL)
		var edge: Color = DdTheme.PANEL_EDGE
		if kind == MapGen.K_GOAL:
			edge = DdTheme.CRIT
		elif kind == MapGen.K_BOSS:
			edge = DdTheme.HP
		elif kind == MapGen.K_BATTLE:
			edge = DdTheme.ENEMY.lightened(0.15)
		elif kind == MapGen.K_CURIO:
			edge = DdTheme.STAT
		draw_rect(box, edge, false, 1.0)
		if is_cur:
			draw_rect(box, DdTheme.CRIT, false, 2.0)
		elif movable:
			draw_rect(box, DdTheme.HEAL, false, 2.0)

		var mark: String = _room_mark(kind)
		var mark_col: Color = DdTheme.TEXT
		if kind == MapGen.K_GOAL:
			mark_col = DdTheme.CRIT
		elif kind == MapGen.K_BOSS:
			mark_col = DdTheme.HP
		elif kind == MapGen.K_BATTLE:
			mark_col = DdTheme.ENEMY.lightened(0.35)
		elif kind == MapGen.K_CURIO:
			mark_col = DdTheme.STAT
		# 打过的战斗房要看得出来（M32）：清剿任务的判据是「图上所有战斗都清掉」，
		# 而房间类型打完仍然是 K_BATTLE。两者画成一个样子的话，
		# 玩家只能靠记忆判断还剩几场——那正好是这一期想消灭的东西。
		# 房间的 step 只在第一次进门时触发，所以「到过」就等于「清过」。
		if kind == MapGen.K_BATTLE and visited:
			mark_col = DdTheme.FAINT
		# 「你在这里」放在框内底部：放框外会压到下一间房
		var mark_y: float = box.position.y + box.size.y * (0.46 if is_cur else 0.60)
		_text(Vector2(box.position.x, mark_y), mark, DdTheme.FONT_LG, mark_col,
			HORIZONTAL_ALIGNMENT_CENTER, box.size.x)
		# 「你在这里」只在房间够宽时写：窄格里那四个字会溢出到邻居头上，
		# 而金框本身已经说明了位置，右侧面板也写着「位置 N」。
		if is_cur and box.size.x >= 46.0:
			_text(Vector2(box.position.x, box.position.y + box.size.y - 9), "你在这里", DdTheme.FONT_TAG, DdTheme.CRIT, HORIZONTAL_ALIGNMENT_CENTER, box.size.x)

		if movable:
			_room_hits.append({"rect": box, "id": rid})


## 走廊中点的内容徽标。
##
## 只有**已侦察**的走廊才有徽标——这一层机制的全部价值就在于
## 「走进去之前知不知道」，在这里免费泄露等于把陷阱变成纯掉血。
func _edge_badge(pos: Vector2, kind: String) -> void:
	if kind.is_empty():
		return
	var col: Color = DdTheme.DIM
	var mark: String = ""
	match kind:
		"trap":
			col = DdTheme.WARN
			mark = "陷"
		"obstacle":
			col = DdTheme.FOOD
			mark = "障"
		"battle":
			col = DdTheme.ENEMY.lightened(0.2)
			mark = "战"
		"hunger":
			col = DdTheme.FOOD
			mark = "饥"
		_:
			return
	var r: float = 8.0
	draw_circle(pos, r, Color(0.05, 0.05, 0.06, 0.95))
	draw_arc(pos, r, 0.0, TAU, 20, col, 1.3, true)
	_text(Vector2(pos.x - r, pos.y + 3.5), mark, DdTheme.FONT_TAG, col,
		HORIZONTAL_ALIGNMENT_CENTER, r * 2.0)


## 当前房间能走的每一条走廊：通往哪、路上有什么。
##
## 逐行列出而不是挤成一句——玩家站在房间里要做的判断就是「这几条里选哪条」，
## 一行一条才对得上他的思考顺序。
func _front_rows() -> Array:
	var out: Array = []
	if exp == null:
		return out
	for nb in exp.adjacent():
		var ei: int = int(nb.edge)
		var rid: int = int(nb.room)
		var known: bool = exp.edge_known(ei)
		var k: String = exp.edge_kind(ei)
		var label: String = "路况不明" if not known else "无异常"
		var col: Color = DdTheme.FAINT
		match k:
			"trap":
				label = "有陷阱"
				col = DdTheme.WARN
			"obstacle":
				label = "有障碍"
				col = DdTheme.FOOD
			"battle":
				label = "有敌人"
				col = DdTheme.ENEMY.lightened(0.25)
			"hunger":
				label = "可补给"
				col = DdTheme.OK
		var rk: String = _room_label(rid)
		out.append({"room": rid, "label": label, "col": col, "room_kind": rk})
	return out


## 房间的显示名（M33）。奇物房报**具体奇物**，其它房间报类型。
##
## 为什么要把奇物名提前告诉玩家：收集/激活任务的判据是「找到某一类奇物」，
## 而这一屏原本只会写「奇物房」——玩家得一间间进才知道是不是要找的那个。
## 原版靠美术就能认出来（精灵图摆在那儿），我们没有美术，
## 名字就是它的等价物。信息层级没变：房间类型本来就已探明。
func _room_label(rid: int) -> String:
	var kind: String = exp.room_kind(rid)
	if kind != MapGen.K_CURIO:
		return _kind_name(kind)
	var step: Dictionary = ((exp.map["rooms"][rid] as Dictionary).get("step", {}) as Dictionary)
	var cid: String = str(step.get("curio", ""))
	if cid.is_empty():
		return _kind_name(kind)
	return DdNames.curio_name(cid)


func _room_mark(kind: String) -> String:
	match kind:
		MapGen.K_START:
			return "入"
		MapGen.K_GOAL:
			return "出"
		MapGen.K_BOSS:
			return "王"
		MapGen.K_BATTLE:
			return "战"
		MapGen.K_CURIO:
			return "奇"
		_:
			return "·"


func _is_adjacent(rid: int) -> bool:
	if exp == null or exp.ended:
		return false
	for nb in exp.adjacent():
		if int(nb.room) == rid:
			return true
	return false


## 右侧信息面板：当前房间 + 操作按钮。
## 相邻房间靠点地图走，面板不重复列一遍——两个入口会让人犹豫点哪个。
func _draw_room_panel(r: Rect2) -> void:
	_panel(r, DdTheme.PANEL_DEEP)
	var kind: String = exp.room_kind(exp.current_room)
	_text(Vector2(r.position.x + 14, r.position.y + 26), _room_label(exp.current_room), DdTheme.FONT_LG, DdTheme.TEXT)
	_text(Vector2(r.position.x + 14, r.position.y + 48),
		"位置 %d · 已走 %d 步" % [exp.current_room, exp.step_index], DdTheme.FONT_SM, DdTheme.FAINT)
	# 任务目标（M32）：原来这一屏只有「已探明 X/Y 间」这种过程指标，
	# 玩家不知道自己在为哪件事走——清剿和探索在这一屏长得一模一样，
	# 于是「走到出口发现还差两场仗」变成一次纯粹的背刺。
	#
	# 放在右面板而不是顶部状态条：顶条在 1080 宽下已经排到「侦察」，
	# 再塞一句会把两个数叠在一起（缩放窗口就复现）。
	var ql: String = _quest_line()
	if not ql.is_empty():
		_text(Vector2(r.position.x + 14, r.position.y + 66), "任务 " + ql,
			DdTheme.FONT_TAG, DdTheme.OK if exp.quest_met() else DdTheme.WARN,
			HORIZONTAL_ALIGNMENT_LEFT, r.size.x - 28.0)
	# 任务物品（M35）：只有带道具的任务才有这一行。
	# 不显示的话玩家无法判断「还剩几次能激活」——而那直接决定要不要绕路。
	var qi: String = _quest_items_line()
	if not qi.is_empty():
		_text(Vector2(r.position.x + 14, r.position.y + 78), qi,
			DdTheme.FONT_TAG, DdTheme.FAINT, HORIZONTAL_ALIGNMENT_LEFT, r.size.x - 28.0)

	# 有物品行时整体下移一行，避免和下面的房间状态挤在一起
	var lines_y: float = r.position.y + (98.0 if not qi.is_empty() else 88.0)
	var lines: Array = []
	if kind == MapGen.K_GOAL:
		# 目标房间不再无条件写「可以离开」（M32）：清剿任务走到出口
		# 只是「到了出口」，图上还有仗没打。这一句是玩家最后一次知道
		# 「现在走会算未完成」的机会，藏起来等于让人白跑一趟。
		if exp.quest_met():
			lines.append(["这里可以离开地牢", DdTheme.CRIT])
		else:
			lines.append(["任务还没完成，现在走算未完成", DdTheme.WARN])
			lines.append([exp.quest_line(), DdTheme.WARN])
	elif kind == MapGen.K_BOSS:
		# 首领会战结束后房间仍然是 K_BOSS，这里按「有没有打完」给两种文案
		if bool(exp.stats.get("boss_killed", false)):
			lines.append(["首领已被击杀，可以离开地牢", DdTheme.OK])
		else:
			lines.append(["首领就在这儿——打不赢别想走", DdTheme.HP])
	elif kind == MapGen.K_START:
		lines.append(["入口。选一个相邻房间开始探索", DdTheme.DIM])
	elif kind == MapGen.K_BATTLE:
		lines.append(["这里的战斗已经结束", DdTheme.DIM])
	elif kind == MapGen.K_CURIO:
		lines.append(["这里的奇物已经搜过", DdTheme.DIM])
	else:
		lines.append(["空房间，没有东西", DdTheme.FAINT])
	var ly: float = lines_y
	for ln in lines:
		_text(Vector2(r.position.x + 14, ly), str(ln[0]), DdTheme.FONT_MD, ln[1])
		ly += 20.0

	# 前路：一行一条走廊。这是玩家此刻真正要做的判断。
	ly += 6.0
	_text(Vector2(r.position.x + 14, ly), "可走的走廊", DdTheme.FONT_MD, DdTheme.DIM)
	ly += 18.0
	var rows: Array = _front_rows()
	if rows.is_empty():
		_text(Vector2(r.position.x + 14, ly), "没有可走的路", DdTheme.FONT_MD, DdTheme.FAINT)
	for row in rows:
		_text(Vector2(r.position.x + 14, ly), "→ %d 号 · %s" % [int(row["room"]), str(row["room_kind"])], DdTheme.FONT_MD, DdTheme.TEXT)
		_text(Vector2(r.position.x + 168, ly), str(row["label"]), DdTheme.FONT_MD, row["col"])
		ly += 17.0
	_text(Vector2(r.position.x + 14, ly + 4), "点地图上的绿框走过去", DdTheme.FONT_SM, DdTheme.HEAL)

	var bw: float = minf(340.0, r.size.x - 28.0)
	var by: float = r.position.y + 196.0
	if exp.at_goal():
		_add_button(Rect2(r.position.x + 14, by, bw, 36), "leave", "离开地牢（完成远征）")
		by += 40.0
	_add_button(Rect2(r.position.x + 14, by, bw, 34), "torch",
		"点火把 +光（剩 %d）" % exp.torch, exp.torch > 0)
	by += 38.0
	_add_button(Rect2(r.position.x + 14, by, bw, 34), "camp",
		"休整（口粮 %d）" % int((exp.cfg.get("camp", {}) as Dictionary).get("food_cost", 2)),
		exp.can_camp())
	by += 38.0
	_add_button(Rect2(r.position.x + 14, by, bw, 34),
		"retreat", "撤退（全队 +%.0f 压力）" % db.rules.retreat_stress)

	_text(Vector2(r.position.x + 14, r.position.y + r.size.y - 14),
		"出口在 %d 步之外（按最短路算）" % _dist_to_goal(), DdTheme.FONT_SM, DdTheme.FAINT)


## 任务目标的一句话（M33）。核心层不认识名字表，所以奇物名在这里补上：
## 收集/激活任务如果只说「在目标奇物上」，玩家不知道要找哪个。
func _quest_line() -> String:
	if exp == null or exp.quest_goal.is_empty():
		return ""
	var cid: String = str(exp.quest_goal.get("curio", ""))
	return exp.quest_line(DdNames.curio_name(cid) if not cid.is_empty() else "")


## 名册里的人显示成什么（M34）。
##
## 名字表按**职业**建（`DdNames.hero_name`），而屏幕上要区分的**人**。
## 同职业第二个起带罗马数字：`十字军 Ⅱ`。
## 这条后缀来自实例 id 本身（`crusader#2`），所以读档之后仍然一样。
func _hero_label(hid: String) -> String:
	var nm: String = DdNames.hero_name(campaign.def_of(str(hid)))
	var sfx: String = campaign.variant_suffix(str(hid))
	return nm if sfx.is_empty() else "%s %s" % [nm, sfx]


## 任务物品那一行（M35）。没有任务物品时返回空串。
##
## 只报「还剩几件」，不报「总共带了几件」：玩家关心的是还能做几次，
## 而总数已经在任务行里（激活 0/3）说过了。
func _quest_items_line() -> String:
	if exp == null or exp.quest_items.is_empty():
		return ""
	var bits: Array = []
	for id in exp.quest_items.keys():
		var n: int = int(exp.quest_items[id])
		if n <= 0 and not str(id).is_empty():
			# 用完的也列出来（写 ×0），否则玩家会以为「本来就没带」
			bits.append("%s ×0" % DdNames.quest_item_name(str(id)))
			continue
		bits.append("%s ×%d" % [DdNames.quest_item_name(str(id)), n])
	return "任务物品 " + "、".join(bits)


func _hazard_name(kind: String) -> String:
	match kind:
		"trap":
			return "有陷阱"
		"obstacle":
			return "有障碍"
		"battle":
			return "有敌人"
		"hunger":
			return "补给点"
		_:
			return "无异常"


func _kind_name(kind: String) -> String:
	match kind:
		MapGen.K_START:
			return "入口房间"
		MapGen.K_GOAL:
			return "出口房间"
		MapGen.K_BOSS:
			return "首领房间"
		MapGen.K_BATTLE:
			return "战斗房"
		MapGen.K_CURIO:
			return "奇物房"
		_:
			return "空房间"


func _dist_to_goal() -> int:
	if exp == null or not exp.map_mode:
		return 0
	return exp._room_dist(exp.current_room, int(exp.map["goal"]))


## 紧凑队伍条：四条信息（名字、血量、压力、状态）就够，
## 详细数值在战斗界面里看。
func _draw_party_strip(r: Rect2) -> void:
	var n: int = exp.hero_ids.size()
	if n == 0:
		return
	var gap: float = 12.0
	var cw: float = (r.size.x - gap * float(n - 1)) / float(n)
	for i in n:
		var hid: String = str(exp.hero_ids[i])
		var s: Dictionary = exp.state.get(hid, {})
		var cr := Rect2(r.position.x + float(i) * (cw + gap), r.position.y, cw, r.size.y)
		var dead: bool = bool(s.get("dead", false))
		_panel(cr)
		draw_rect(Rect2(cr.position, Vector2(cr.size.x, 3)),
			Color("#3a3a3a") if dead else DdTheme.PARTY)

		_text(Vector2(cr.position.x + 12, cr.position.y + 24), _hero_label(hid), DdTheme.FONT_BD, DdTheme.FAINT if dead else DdTheme.TEXT)
		_text(Vector2(cr.position.x + cr.size.x - 64, cr.position.y + 24),
			"装备 %d" % _hero_gear(hid), DdTheme.FONT_SM, DdTheme.FAINT)

		var hp_r: float = float(s.get("hp_ratio", 0.0))
		var max_hp: int = _max_hp(hid)
		var bar := Rect2(cr.position.x + 12, cr.position.y + 34, cr.size.x - 24, 14)
		_bar(bar, hp_r, DdTheme.HP, DdTheme.HP_TRACK)
		_text(Vector2(bar.position.x, bar.position.y + 11),
			"%d / %d" % [int(round(hp_r * float(max_hp))), max_hp], DdTheme.FONT_TAG,
			Color("#f2eee2"), HORIZONTAL_ALIGNMENT_CENTER, bar.size.x)

		var st: float = float(s.get("stress", 0.0))
		var sb := Rect2(bar.position.x, bar.position.y + 20, bar.size.x, 5)
		_bar(sb, st / 200.0, DdTheme.STRESS, DdTheme.STRESS_TRACK)
		_text(Vector2(sb.position.x, sb.position.y + 16), "压力 %.0f" % st, DdTheme.FONT_TAG, DdTheme.STRESS if st >= 100.0 else DdTheme.FAINT)

		var tags: Array = []
		if dead:
			tags.append("阵亡")
		else:
			if bool(s.get("at_deaths_door", false)):
				tags.append("死门")
			if not str(s.get("affliction", "")).is_empty():
				tags.append("崩溃")
			elif not str(s.get("virtue", "")).is_empty():
				tags.append("美德")
			if bool(s.get("recovering", false)):
				tags.append("恢复期")
		if not tags.is_empty():
			_text(Vector2(sb.position.x, cr.position.y + cr.size.y - 8), " ".join(tags), DdTheme.FONT_TAG, DdTheme.FAINT if dead else DdTheme.WARN)


func _draw_log_panel(r: Rect2) -> void:
	_panel(r, DdTheme.PANEL_DEEP)
	_text(Vector2(r.position.x + 14, r.position.y + 22), "行程记录", DdTheme.FONT_MD, DdTheme.DIM)
	var line_h: float = 18.0
	var max_lines: int = int((r.size.y - 40.0) / line_h)
	var start: int = maxi(0, _log.size() - max_lines)
	var y: float = r.position.y + 44.0
	for i in range(start, _log.size()):
		var e: Dictionary = _log[i]
		_text(Vector2(r.position.x + 14, y),
			DdTheme.ellipsis(str(e.text), _font, r.size.x - 28.0, 12), DdTheme.FONT_MD, e.color)
		y += line_h


# ============================================================
# 战斗屏
# ============================================================

func _draw_battle() -> void:
	if _battle == null:
		return
	var tier: String = ExpeditionCfg.light_tier_name(exp.light)
	_header("战斗 · 第 %d 轮 · 光照 %.0f（%s）" % [_battle.round_index, exp.light, tier],
		"点技能 → 点目标    空格 自动一回合")

	# —— 敌方 ——
	var en: Array = _battle.enemies
	var ecw: float = 152.0
	var egap: float = 18.0
	var etot: float = ecw * float(en.size()) + egap * float(en.size() - 1)
	var ex: float = (size.x - etot) * 0.5
	for i in en.size():
		var u: Combatant = en[i]
		var r := Rect2(ex + float(i) * (ecw + egap), 82, ecw, 104)
		_draw_unit(u, r, true)

	# —— 我方 ——
	var pa: Array = _battle.party
	var pcw: float = 152.0
	var ptot: float = pcw * float(pa.size()) + egap * float(pa.size() - 1)
	var px: float = (size.x - ptot) * 0.5
	for i in pa.size():
		var u2: Combatant = pa[i]
		var r2 := Rect2(px + float(i) * (pcw + egap), 200, pcw, 104)
		_draw_unit(u2, r2, false)

	# —— 日志 ——
	_draw_log_panel(Rect2(40, 320, 660, 392))

	# —— 技能面板 ——
	_draw_skill_panel(Rect2(716, 320, size.x - 756, 392))

	_text(Vector2(40, 736), "光照影响：怪物伤害 %+.0f%% · 我方受压 %+.0f%%" % [
		exp.light_mods().get("monster_dmg", 0.0) * 100.0,
		exp.light_mods().get("stress_damage", 0.0) * 100.0], DdTheme.FONT_MD, DdTheme.FAINT)


func _draw_unit(u: Combatant, r: Rect2, is_enemy: bool) -> void:
	var is_active: bool = _battle.awaiting_input != null and _battle.awaiting_input.uid == u.uid
	var is_target: bool = false
	if not _pending.is_empty():
		for t in (_pending.get("targets", []) as Array):
			if t.uid == u.uid:
				is_target = true
				break

	var accent: Color = DdTheme.ENEMY if is_enemy else DdTheme.PARTY
	if u.dead:
		accent = Color("#3a3a3a")

	_panel(r)
	draw_rect(Rect2(r.position, Vector2(r.size.x, 3)), accent)
	if is_active:
		draw_rect(r, DdTheme.CRIT, false, 2.0)
	elif is_target:
		draw_rect(r, DdTheme.HEAL, false, 2.0)
	elif _hover_uid == u.uid:
		draw_rect(r, DdTheme.DIM, false, 1.0)

	var text_col: Color = DdTheme.FAINT if u.dead else DdTheme.TEXT
	_text(Vector2(r.position.x + 10, r.position.y + 24),
		DdTheme.ellipsis(DdNames.unit_name(u.def_id), _font, r.size.x - 20.0, 12), DdTheme.FONT_MD, text_col)
	_text(Vector2(r.position.x + 10, r.position.y + 40), "位 %d" % (u.rank + 1), DdTheme.FONT_SM, DdTheme.FAINT)

	var bar := Rect2(r.position.x + 10, r.position.y + 50, r.size.x - 20, 14)
	_bar(bar, u.hp_ratio(), DdTheme.HP, DdTheme.HP_TRACK)
	_text(Vector2(bar.position.x, bar.position.y + 11), "%d / %d" % [u.hp, u.base_hp], DdTheme.FONT_TAG,
		Color("#f2eee2"), HORIZONTAL_ALIGNMENT_CENTER, bar.size.x)

	if u.is_hero:
		var sb := Rect2(bar.position.x, bar.position.y + 20, bar.size.x, 5)
		_bar(sb, u.stress / 200.0, DdTheme.STRESS, DdTheme.STRESS_TRACK)
		_text(Vector2(sb.position.x, sb.position.y + 18), "压力 %.0f" % u.stress, DdTheme.FONT_TAG, DdTheme.STRESS if u.stress >= 100.0 else DdTheme.FAINT)

	var marks: Array = []
	if u.dead:
		marks.append("阵亡")
	else:
		if u.at_deaths_door:
			marks.append("死门")
		if u.stun_turns > 0:
			marks.append("眩晕")
		if u.dots.size() > 0:
			marks.append("DOT×%d" % u.dots.size())
		if u.has_affliction():
			marks.append("崩溃")
		elif u.is_virtuous():
			marks.append("美德")
		# 守护/反击（M10）。放在状态行末尾而不是另起一行：
		# 卡片只有 104 高，再开一行就会和血条/压力条打架。
		# 超过 4 项就截断——宁可少显示一个，也不要让文字溢出卡片。
		var gt: Combatant = _battle.guard_target_of(u.uid)
		if gt != null:
			marks.append("守%d" % (gt.rank + 1))
		if _battle.guardian_of(u.uid) != null:
			marks.append("被守")
		if _battle.has_riposte(u.uid):
			marks.append("反击")
		if marks.size() > 4:
			marks = marks.slice(0, 4)
	if not marks.is_empty():
		_text(Vector2(bar.position.x, r.position.y + r.size.y - 8), " ".join(marks), DdTheme.FONT_TAG, DdTheme.WARN if (u.dead or u.at_deaths_door) else DdTheme.STAT)

	_slots.append({"rect": r, "uid": u.uid, "side": "enemy" if is_enemy else "party"})


func _draw_skill_panel(r: Rect2) -> void:
	_panel(r, DdTheme.PANEL_DEEP)
	var actor: Combatant = _battle.awaiting_input
	if actor == null:
		_text(Vector2(r.position.x, r.position.y + 22), "敌方行动中…", DdTheme.FONT_MD, DdTheme.FAINT,
			HORIZONTAL_ALIGNMENT_CENTER, r.size.x)
		return

	_text(Vector2(r.position.x + 14, r.position.y + 22),
		"%s 的行动" % DdNames.unit_name(actor.def_id), DdTheme.FONT_BD, DdTheme.TEXT)
	_text(Vector2(r.position.x + 14, r.position.y + 40),
		"武器伤害 %d-%d · 暴击 %.0f%% · 速度 %.0f" % [
			int(actor.base_dmg_low), int(actor.base_dmg_high),
			_crit_pct(actor), actor.speed()], DdTheme.FONT_SM, DdTheme.FAINT)

	if _show_move_demo and _battle != null and _battle.awaiting_input != null:
		_move_mode = true

	var bw: float = (r.size.x - 36.0) * 0.5
	var bh: float = 40.0
	var y0: float = r.position.y + 52.0

	# —— 移动模式：把技能区让给落点列表 ——
	if _move_mode:
		var spots: Array = _battle.move_options(actor)
		_text(Vector2(r.position.x + 14, y0 - 8), "挪到哪个位置？换位会消耗这一回合", DdTheme.FONT_MD, DdTheme.HEAL)
		for i in spots.size():
			var rk: int = int(spots[i])
			var sr := Rect2(r.position.x + 12, y0 + 6.0 + float(i) * 40.0, r.size.x - 24.0, 34.0)
			_add_button(sr, "goto:%d" % rk, "移到 %d 号位" % (rk + 1))
		_add_button(Rect2(r.position.x + 12, r.position.y + r.size.y - 44.0, r.size.x - 24.0, 32.0),
			"movecancel", "取消，回到技能")
		return

	for i in _options.size():
		var col: int = i % 2
		var row: int = i / 2
		var br := Rect2(r.position.x + 12 + float(col) * (bw + 12), y0 + float(row) * (bh + 6), bw, bh)
		if br.position.y + br.size.y > r.position.y + r.size.y - 12.0:
			break
		var opt: Dictionary = _options[i]
		var action: Dictionary = opt.action
		var selected: bool = not _pending.is_empty() and str(_pending.action.id) == str(action.id)
		var hover: bool = br.has_point(_mouse)
		draw_rect(br, DdTheme.BTN_ACTIVE if selected else (DdTheme.BTN_HOVER if hover else DdTheme.BTN))
		draw_rect(br, DdTheme.CRIT if selected else DdTheme.PANEL_EDGE, false, 1.0)
		_text(Vector2(br.position.x + 8, br.position.y + 17),
			DdTheme.ellipsis(DdNames.skill_name(str(action.id)), _font, bw - 16.0, 12), DdTheme.FONT_MD, DdTheme.TEXT)
		_text(Vector2(br.position.x + 8, br.position.y + 32), _action_summary(action, actor), DdTheme.FONT_TAG, DdTheme.FAINT)
		_add_hit(br, "skill:%d" % i)

	var pass_r := Rect2(r.position.x + 12, r.position.y + r.size.y - 44.0, r.size.x - 24.0, 32.0)
	_add_button(pass_r, "pass", "跳过本回合（+%.0f 压力）" % float(db.rules.raw.get("passed_turn_stress_dmg", 5.0)))

	# 移动入口：只有这个单位有 move_skill、且真的能挪时才给按钮。
	# 站位在 M9 之前是完全静态的，这个按钮是玩家第一次能主动改阵型。
	if not _battle.move_options(actor).is_empty():
		_add_button(Rect2(r.position.x + 12, r.position.y + r.size.y - 82.0, r.size.x - 24.0, 32.0),
			"movemode", "调整站位（当前 %d 号位）" % (actor.rank + 1))

	if not _pending.is_empty():
		_text(Vector2(r.position.x + 12, r.position.y + r.size.y - 52),
			"选择目标：点击高亮的单位（绿框）", DdTheme.FONT_SM, DdTheme.HEAL)


func _action_summary(action: Dictionary, actor: Combatant) -> String:
	var bits: Array = []
	if float(action.heal) > 0.0:
		bits.append("治疗 %d-%d" % [int((action.heal_range as Array)[0]), int((action.heal_range as Array)[1])])
	var rng_arr: Array = action.dmg_range
	if rng_arr.size() >= 2:
		bits.append("伤害 %d-%d" % [int(rng_arr[0]), int(rng_arr[1])])
	elif absf(float(action.dmg_mod)) > 0.001:
		bits.append("修正 %+.0f%%" % (float(action.dmg_mod) * 100.0))
	if float(action.atk) != 0.0:
		bits.append("命中 %+.0f%%" % (float(action.atk) * 100.0))
	if bool(action.get("is_guard", false)):
		bits.append("守护")
	if bool(action.get("is_riposte", false)):
		bits.append("反击")
	bits.append("敌" if not bool(action.friendly) else "友")
	if bool(action.target_aoe):
		bits.append("全体")
	bits.append("效×%d" % (action.effects as Array).size())
	return " · ".join(bits)


func _crit_pct(u: Combatant) -> float:
	return u.crit() * 100.0


# ============================================================
# 结算屏
# ============================================================

func _draw_result() -> void:
	if exp == null:
		return
	var s: Dictionary = exp.summary()
	var title: String = "远征结束"
	var color: Color = DdTheme.TEXT
	match str(s.get("end_reason", "")):
		"complete":
			title = "走出地牢"
			color = DdTheme.OK
		"wipe":
			title = "全队覆没"
			color = DdTheme.WARN
		"retreat":
			title = "撤退"
			color = DdTheme.LIGHT
		"incomplete":
			# M32 起这条不只属于首领任务：清剿没清完就走，同样落在这里。
			# 标题里带上没完成的目标，否则玩家只看到「任务未完成」，
			# 不知道是没杀首领还是漏了两场仗。
			title = "任务未完成 · %s" % str(s.get("quest_goal", ""))
			if exp != null and not exp.quest_goal.is_empty():
				var cid: String = str(exp.quest_goal.get("curio", ""))
				title = "任务未完成 · " + QuestGoal.describe(exp.quest_goal, exp.quest_state(),
					DdNames.curio_name(cid) if not cid.is_empty() else "")
			color = DdTheme.WARN

	_header("结算", "点下面的按钮回城镇")
	_text(Vector2(0, 128), title, DdTheme.FONT_DISPLAY, color, HORIZONTAL_ALIGNMENT_CENTER, size.x)

	var cx: float = size.x * 0.5
	# 卡片高度从 424 提到 470（M25）：结算里最坏情况要放
	# 统计 10 行 + 金币 + 传家宝 + 宝石 + 经验 + 升级 + 饰品 + 阵亡 8 段，
	# 按原来的行距会掉出卡片底边。行距从 31 压到 26，纵向腾了 50。
	var card := Rect2(cx - 320, 138, 640, 470)
	_panel(card, DdTheme.PANEL_DEEP)

	var lines: Array = [
		["推进", "%d / %d 步" % [int(s.steps_done), int(s.steps_total)]],
		["遭遇", "%d 场 · 共 %d 轮" % [int(s.battles), int(s.rounds)]],
		["阵亡", "%d 人" % int(s.hero_deaths)],
		["崩溃 / 美德", "%d / %d" % [int(s.afflictions), int(s.virtues)]],
		["陷阱", "%d 次 · 躲开 %d" % [int(s.get("traps", 0)), int(s.get("traps_dodged", 0))]],
		["障碍", "%d 处 · 凿开 %d" % [int(s.get("obstacles", 0)), int(s.get("obstacles_cleared", 0))]],
		["心脏骤停", "%d 次" % int(s.heart_attacks)],
		["终局血量", "%.0f%%" % (float(s.hp_end) * 100.0)],
		["终局压力", "%.0f / 200" % float(s.stress_end)],
		["剩余补给", "光照 %.0f · 口粮 %d · 火把 %d · 铁锹 %d" % [
			float(s.light_end), int(s.food_end), int(s.torch_end), int(s.get("shovel_end", 0))]],
	]
	var y: float = card.position.y + 34.0
	for line in lines:
		_text(Vector2(card.position.x + 30, y), str(line[0]), DdTheme.FONT_BD, DdTheme.DIM)
		_text(Vector2(card.position.x + 190, y), str(line[1]), DdTheme.FONT_BD, DdTheme.TEXT)
		y += 26.0

	# —— 战利品：这一趟真正的产出 ——
	draw_line(Vector2(card.position.x + 24, y - 6), Vector2(card.position.x + card.size.x - 24, y - 6),
		DdTheme.PANEL_EDGE, 1.0)
	y += 16.0
	var got_gold: int = int(_settle_gain.get("gold", 0))
	_text(Vector2(card.position.x + 30, y), "本趟所得", DdTheme.FONT_BD, DdTheme.DIM)
	_text(Vector2(card.position.x + 190, y), "金币 +%d" % got_gold, DdTheme.FONT_BD, DdTheme.CRIT)
	y += 26.0
	var hb: Dictionary = _settle_gain.get("heirlooms", {})
	var bits: Array = []
	for k in hb.keys():
		if int(hb[k]) > 0:
			bits.append("%s ×%d" % [DdNames.heirloom_name(str(k)), int(hb[k])])
	_text(Vector2(card.position.x + 190, y),
		"传家宝 " + ("、".join(bits) if not bits.is_empty() else "无"), DdTheme.FONT_MD, DdTheme.TEXT)

	# 宝石已经折进上面的金币，这里只报件数——否则玩家会以为还有一笔没进账
	var gem_counts: Dictionary = _settle_gain.get("gems", {})
	var gem_n: int = 0
	for gk in gem_counts.keys():
		gem_n += int(gem_counts[gk])
	if gem_n > 0:
		y += 20.0
		_text(Vector2(card.position.x + 190, y),
			"附带宝石 %d 颗（已折入金币）" % gem_n, DdTheme.FONT_MD, DdTheme.FAINT)

	# —— 决心经验（M25）——
	# 这是这一趟里唯一「只要完成就一定有、而且永久留着」的收获。
	# 没升级也要报：不报的话玩家不知道「再打一趟就能升」还差多远，
	# 而等级现在决定了能穿几阶装备、能进哪些本。
	var xp_gain: int = int(_settle_gain.get("xp", 0))
	if xp_gain > 0:
		y += 22.0
		_text(Vector2(card.position.x + 190, y), "经验 +%d（全队）" % xp_gain, DdTheme.FONT_MD, DdTheme.OK)
	var ups: Dictionary = _settle_gain.get("levelups", {})
	if not ups.is_empty():
		y += 18.0
		# 名字最多列两个：四个人一起升级时，全列出来有 36 个字（约 430px），
		# 而这一栏从 x+190 到卡片右边只有 420px——正好会顶出边框。
		var names_u: Array = []
		var max_lv: int = 0
		for uk in ups.keys():
			names_u.append(_hero_label(str(uk)))
			max_lv = maxi(max_lv, campaign.resolve_of(str(uk)))
		var tail: String = "" if names_u.size() <= 2 else " 等 %d 人" % names_u.size()
		_text(Vector2(card.position.x + 190, y),
			"升级：%s%s → Lv%d" % ["、".join(names_u.slice(0, 2)), tail, max_lv], DdTheme.FONT_MD, DdTheme.OK)

	# —— 饰品：这一期唯一「拿到了就能改变下次出发」的东西 ——
	# 件数要和进仓库分开报：仓库满或超同名上限时，掉出来的东西会进不去，
	# 只报「掉了 2 件」而实际一件没进，玩家会以为存档坏了。
	var tids: Array = _settle_gain.get("trinket_ids", [])
	var dropped: int = int(_settle_gain.get("trinkets_dropped", 0))
	if not tids.is_empty() or dropped > 0:
		y += 22.0
		var tbits: Array = []
		for tid in tids:
			tbits.append(DdNames.trinket_name(str(tid)))
		_text(Vector2(card.position.x + 190, y),
			"饰品 " + ("、".join(tbits) if not tbits.is_empty() else "无"), DdTheme.FONT_MD, DdTheme.CRIT)
		if dropped > 0:
			y += 18.0
			_text(Vector2(card.position.x + 190, y),
				"另有 %d 件没能带走（仓库满或已达同名上限）" % dropped, DdTheme.FONT_MD, DdTheme.WARN)

	var deaths: Array = _settle_gain.get("deaths", [])
	if not deaths.is_empty():
		y += 24.0
		var names: Array = []
		for d in deaths:
			names.append(_hero_label(str(d)))
		_text(Vector2(card.position.x + 190, y), "永久损失：" + "、".join(names), DdTheme.FONT_MD, DdTheme.WARN)

	_add_button(Rect2(cx - 120, 634, 240, 44), "restart", "回城镇")
	_text(Vector2(0, 700), "金币与传家宝已入账并存档。回城镇可以升级装备、招募阵亡英雄，或者再来一趟。", DdTheme.FONT_MD, DdTheme.FAINT, HORIZONTAL_ALIGNMENT_CENTER, size.x)


# ============================================================
# 出发准备（M16）
# ============================================================

## 保底包：和 M13 之前硬编码的默认完全一致
## （`DEFAULT_SUPPLY_PACK` 六种各 1 + 火把 4 + 口粮 4 + 铁锹 1）。
##
## 为什么要有它：新档金币是 0。如果出发必须先买补给，第一趟就卡死了。
## 保底包让「不花钱也能走」，钱只花在「比保底多带的那部分」上。
func _default_prep_pack() -> Dictionary:
	return {
		"torch": 4, "food": 4, "shovel": 1,
		"bandage": 1, "antivenom": 1, "medicinal_herbs": 1,
		"holy_water": 1, "skeleton_key": 1,
	}


## 现在还能招到几个死掉的英雄（免费额度或者钱够）。
##
## 准备屏用它决定「队伍不满 4 人时该不该放人走」：
## 能招就必须先招满，招不到才允许少人出发——两边都是为了避免死循环。
func _recruitable_now() -> int:
	var n: int = 0
	for hid in campaign.hero_ids():
		var hid_s: String = str(hid)
		if bool((campaign.hero(hid_s) as Dictionary).get("alive", false)):
			continue
		if campaign.can_recruit(hid_s):
			n += 1
	return n


## 点一个人：已选就移出，没选就加入。
##
## 满 4 人时加入会先挤掉**最后加入的那个**，而不是拒绝——
## 「点不动」比「换掉一个」更让人困惑。至少保留 1 人：
## 0 人出发在 Battle 里会直接崩，而且也没意义。
func _toggle_party(hid: String) -> void:
	if _prep_party.has(hid):
		if _prep_party.size() <= 1:
			_flash_msg("至少带一个人")
			return
		_prep_party.erase(hid)
	elif _prep_party.size() >= Campaign.PARTY_MAX:
		_prep_party.remove_at(_prep_party.size() - 1)
		_prep_party.append(hid)
	else:
		_prep_party.append(hid)
	queue_redraw()


func _adjust_pack(id: String, delta: int) -> void:
	var cur: int = int(_prep_pack.get(id, 0)) + delta
	if campaign.shop != null:
		var lim: int = campaign.shop.supply_limit(id)
		if lim > 0:
			cur = mini(cur, lim)
	_prep_pack[id] = maxi(0, cur)
	queue_redraw()


## 支付并出发。
##
## 金币不够时**不阻止出发**：改用保底包（免费），并明说一句。
## 阻止出发会让「打完一趟才有钱」这个循环在第一趟就断掉。
func _launch_with_pack() -> void:
	var cost: int = 0
	if campaign.shop != null:
		cost = campaign.shop.pack_cost(_prep_pack)
	if cost > campaign.gold:
		_flash_msg("金币不足（需 %d，有 %d），按保底补给出发" % [cost, campaign.gold])
		_prep_pack = _default_prep_pack()
		_state = S_TOWN
		_start_expedition(_prep_size, _prep_level, {}, _prep_party, _prep_quest)
		return
	var res: Dictionary = campaign.buy_pack(_prep_pack)
	if not bool(res.get("ok", false)):
		_flash_msg(_shop_reason(str(res.get("reason", ""))))
		return
	campaign.save()
	_state = S_TOWN
	_start_expedition(_prep_size, _prep_level, _prep_pack, _prep_party, _prep_quest)


func _draw_prep() -> void:
	_header("出发准备 · %s · %s %d 级" % [DdNames.dungeon_name(_dungeon),
		_size_name_of(_prep_size), _prep_level],
		"名册 %d 人 · 出战上限 %d 人 · 金币 %d    补给按份买，买完直接进背包" % [
			campaign.alive_ids().size(), Campaign.PARTY_MAX, campaign.gold])

	# —— 左：补给清单 ——
	if campaign.shop == null:
		_text(Vector2(28, 90), "inventory.json 没读到，补给不可用（可按保底包出发）。", DdTheme.FONT_MD, DdTheme.WARN)
		_add_button(Rect2(size.x - 208, 640, 180, 40), "prep_back", "返回")
		return
	var sw: float = size.x * 0.5 - 40.0
	var y: float = 88.0
	_text(Vector2(28, y), "补给", DdTheme.FONT_BD, DdTheme.TEXT)
	y += 12.0
	for sid in campaign.shop.supply_ids():
		var id: String = str(sid)
		var n: int = int(_prep_pack.get(id, 0))
		var price: int = campaign.shop.supply_buy(id)
		var lim: int = campaign.shop.supply_limit(id)
		var rr := Rect2(28, y, sw, 46.0)
		_panel(rr, DdTheme.PANEL_DEEP)
		_text(Vector2(rr.position.x + 12, rr.position.y + 20), _supply_label(id), DdTheme.FONT_BD, DdTheme.TEXT)
		_text(Vector2(rr.position.x + 12, rr.position.y + 38),
			"%d 金 / 份    上限 %d" % [price, lim], DdTheme.FONT_SM, DdTheme.DIM)
		# 减 / 数量 / 加
		var bx: float = rr.position.x + rr.size.x - 152.0
		_add_hit(Rect2(bx, rr.position.y + 8, 32, 30), "prep_sub:" + id)
		_text(Vector2(bx, rr.position.y + 28), "－", DdTheme.FONT_LG, DdTheme.WARN,
			HORIZONTAL_ALIGNMENT_CENTER, 32)
		_text(Vector2(bx + 36, rr.position.y + 28), "%d" % n, DdTheme.FONT_BD, DdTheme.TEXT if n > 0 else DdTheme.FAINT, HORIZONTAL_ALIGNMENT_CENTER, 40)
		_add_hit(Rect2(bx + 78, rr.position.y + 8, 32, 30), "prep_add:" + id)
		_text(Vector2(bx + 78, rr.position.y + 28), "＋", DdTheme.FONT_LG, DdTheme.OK,
			HORIZONTAL_ALIGNMENT_CENTER, 32)
		_text(Vector2(rr.position.x + rr.size.x - 200, rr.position.y + 28),
			"%d 金" % (n * price), DdTheme.FONT_MD, DdTheme.DIM, HORIZONTAL_ALIGNMENT_RIGHT, 44)
		y += 52.0

	# —— 右：难度与结算 ——
	var rx: float = size.x * 0.5 + 16.0
	var rw: float = size.x - rx - 28.0
	_text(Vector2(rx, 88), "行程", DdTheme.FONT_BD, DdTheme.TEXT)
	# 和城镇用同一块板子（M26）：这一屏是「换一张卡」的地方，
	# 如果它自己另算一套等级，玩家在这里切一下就和城镇看到的对不上了。
	var rows: Array = _board_rows()
	var ry: float = 100.0
	for i in rows.size():
		var row: Array = rows[i]
		# 选中态要同时比尺寸、任务类型**和等级**（M29）：
		#   · 中程与首领都是 medium —— 只比尺寸会让两张卡同时高亮
		#   · 同一个尺寸每周的等级不同 —— 只比尺寸+类型会让「中程 1 级」
		#     在标题写着「中程 3 级」时也亮着，玩家会以为自己选错了
		var sel: bool = _prep_size == str(row[0]) and _prep_quest == str(row[4]) \
			and _prep_level == int(row[1])
		var rr2 := Rect2(rx, ry + float(i) * 52.0, rw, 44.0)
		_panel(rr2, DdTheme.PANEL_HI if sel else DdTheme.PANEL_DEEP)
		if sel:
			draw_rect(rr2, DdTheme.PARTY, false, 2.0)
		_text(Vector2(rr2.position.x + 12, rr2.position.y + 20), str(row[2]), DdTheme.FONT_BD, DdTheme.TEXT if sel else DdTheme.DIM)
		_text(Vector2(rr2.position.x + 12, rr2.position.y + 36), str(row[3]), DdTheme.FONT_SM, DdTheme.FAINT)
		_add_hit(rr2, "prep:%s:%d:%s" % [str(row[0]), int(row[1]), str(row[4])])

	# —— 出战名单（M18）——
	# 名册 5 人、只能带 4 个，所以这里是一个真实的选择。
	# 点一下切换；满员时加入会挤掉最后加进来的那个（不是拒绝）。
	var py: float = ry + 4.0 * 52.0 + 16.0
	# 按强度排序（M27）：和默认名单同一个序，见 _sort_by_power 的注释
	var ids_all: Array = _sort_by_power(campaign.selectable_ids())
	# 够格的人数（M25）。等级锁之后「名册有几个活人」不再是可带人数——
	# 太高级的人会被拒绝，所以门槛必须跟着**够格人数**走。
	# 不这么改的话，一个 6 级的名册去打学徒本会永远显示「还缺 4 人」。
	var fit_ids: Array = []
	for hid_f in ids_all:
		if campaign.can_join(str(hid_f), _prep_level):
			fit_ids.append(hid_f)
	# 门槛 = min(上限, 够格人数)，但**能招人时不许降门槛**。
	# 只降门槛会放 1 人队出门，那是必死，不是「灵活」；
	# 只有真的一个人都招不到了（没钱、没免费额度），才允许少人出发，否则死锁。
	var fillable: int = _recruitable_now()
	var need: int = mini(Campaign.PARTY_MAX, fit_ids.size())
	var must_recruit: bool = need < Campaign.PARTY_MAX and fillable > 0
	var want: int = Campaign.PARTY_MAX if must_recruit else need
	_text(Vector2(rx, py), "出战（已选 %d / %d 人）· 点一下切换" % [
		_prep_party.size(), want], DdTheme.FONT_MD, DdTheme.OK if _prep_party.size() >= want else DdTheme.WARN)
	# 出战卡布局（M27）：名册能到 15 人，一行放不下，改成 6 列 × 最多 3 行。
	# 卡片从 68 压到 52，只留「名字 + Lv」两行——「出征 N 次」这种信息
	# 在这一屏没有决策价值，占着位置反而让人看不清谁够格。
	var per_row: int = 6
	var bw: float = (rw - 8.0 * float(per_row - 1)) / float(per_row)
	for k in ids_all.size():
		var hid: String = str(ids_all[k])
		var picked: bool = _prep_party.has(hid)
		# 等级锁（M25）：带不了的人要**显示出来并说明原因**，
		# 而不是从列表里消失。消失会让玩家以为「这个人没了」，
		# 而真相是「他太高级，不屑于来这种小地方」——这两种感觉完全不同。
		var fit: bool = campaign.can_join(hid, _prep_level)
		var col: int = k % per_row
		var rowi: int = k / per_row
		var br := Rect2(rx + float(col) * (bw + 8.0), py + 10.0 + float(rowi) * 56.0, bw, 52.0)
		_panel(br, DdTheme.PANEL_HI if picked else DdTheme.PANEL_DEEP)
		if picked:
			draw_rect(br, DdTheme.PARTY, false, 2.0)
		# 光靠边框粗细分辨「选没选」在小屏上几乎看不出来，
		# 所以再给一个文字标记——这是唯一能一眼确认的地方。
		_text(Vector2(br.position.x + 8, br.position.y + 20), ("✓ " if picked else "＋ ") +
			_hero_label(hid), DdTheme.FONT_MD, DdTheme.TEXT if picked else (DdTheme.FAINT if fit else DdTheme.CRIT))
		if fit:
			# 够格但等级不够（会吃惩罚）：这一行转警告色，具体代价在下面的队伍摘要里
			var gap_h: int = campaign.level_gap(hid, _prep_level)
			_text(Vector2(br.position.x + 8, br.position.y + 38),
				"Lv%d · 装备 %d 阶" % [campaign.resolve_of(hid), campaign.gear_of(hid)], DdTheme.FONT_TAG, DdTheme.WARN if gap_h > 0 else DdTheme.DIM)
			_add_hit(br, "prep_pick:" + hid)
		else:
			# 「高出 2 级就拒绝」是原版唯一的硬门槛，所以这句话要直说：
			# 玩家会以为是 bug（我的人更强了为什么不能带），必须解释。
			_text(Vector2(br.position.x + 8, br.position.y + 38),
				"高出 %d 级" % (campaign.resolve_of(hid) - _prep_level), DdTheme.FONT_TAG, DdTheme.CRIT)
		if br.has_point(_mouse):
			draw_rect(br, Color(1, 1, 1, 0.05))

	var cost: int = campaign.shop.pack_cost(_prep_pack)
	var enough: bool = cost <= campaign.gold
	# 三行卡最坏情况占 py+10 ~ py+178，所以补给区从 +196 起，
	# 留 18px 空隙——贴着卡片底边画会让字和边框粘在一起。
	var cy: float = py + 196.0
	_text(Vector2(rx, cy), "补给合计", DdTheme.FONT_MD, DdTheme.DIM)
	_text(Vector2(rx + 120, cy), "%d 金" % cost, DdTheme.FONT_LG, DdTheme.CRIT if enough else DdTheme.WARN)
	_text(Vector2(rx, cy + 24),
		"余额 %d 金%s" % [campaign.gold, "" if enough else "　— 不足，将按保底补给出发"], DdTheme.FONT_MD, DdTheme.DIM if enough else DdTheme.WARN)
	# 等级惩罚（M29）：不够格的人要在这里说清楚代价。
	# 卡片太小写不下（那是 6 列 × 52 高），而「这趟会吃多少罚」正好是一整队的事，
	# 放队伍摘要里比放在某张卡上更合适。
	var under: int = 0
	var max_gap: int = 0
	for hid_p in _prep_party:
		var g: int = campaign.level_gap(str(hid_p), _prep_level)
		if g > 0:
			under += 1
			max_gap = maxi(max_gap, g)
	var line: String = "出战 %d 人 · 平均装备 %d 阶" % [
		_prep_party.size(), _party_gear_avg(_prep_party)]
	if _prep_party.size() < want:
		line += "　— 不满 %d 人，单挑必死" % want
	elif under > 0:
		# 报「最多」而不是逐人列：队伍里可能同时有差 1 级和差 2 级的人，
		# 逐人列太长，而玩家需要的判断只有一句「这趟大概多疼」。
		line += "　— %d 人低于任务等级：最多进本 +%d 压力、受压 ×%.2f" % [
			under, int(float(max_gap) * Campaign.JOIN_STRESS_PER_LEVEL),
			1.0 + float(max_gap) * Campaign.JOIN_STRESS_MULT_PER_LEVEL]
	_text(Vector2(rx, cy + 48), line, DdTheme.FONT_MD, DdTheme.WARN if (under > 0 or _prep_party.size() < want) else DdTheme.DIM)

	# 不满 `want` 人就不给走：这不是数值平衡，是防手滑——
	# 上一版允许 1 人出发，结果「5 张卡全是尸体只剩 1 个新兵」的档
	# 一路 1v4，玩家看到的是「战斗里只有 1 个人」。
	var ready: bool = want > 0 and _prep_party.size() >= want
	var go_label: String = "出发（%d 金）" % cost if enough else "按保底补给出发"
	if not ready and must_recruit:
		go_label = "先回城镇征召 —— 队伍要满 %d 人" % Campaign.PARTY_MAX
	elif not ready:
		go_label = "还缺 %d 人 —— 名册里够格的人不够" % (want - _prep_party.size())
	_add_button(Rect2(rx, 596, rw, 48), "prep_go", go_label, ready)
	_add_button(Rect2(rx, 652, rw, 36), "prep_back", "返回城镇")
	_text(Vector2(28, 660), "补给只在出发前买，回城不结余——增加的那部分就是这趟的赌注。", DdTheme.FONT_MD, DdTheme.FAINT)


# ============================================================
# 建筑屏（M22）
# ============================================================

## 六座「对人做事」的建筑共用这一屏。
##
## 不拆成六个屏，是因为它们百分之七十是一样的：左边同样的名册列表、
## 同样的「选中态」、同样的返回按钮。差别只在右侧那几行字和一个动作按钮。
## 拆开会得到六份几乎相同的代码，改一次排版要改六处——
## 而这类重复正是 M13~M19 反复踩的坑（同一套判定两处实现，然后分叉）。
func _draw_building() -> void:
	var meta: Array = _building_meta(_building)
	# 商队和墓园没有左栏名册，副标题就别再写「左侧点人」——
	# 它会让玩家去找一个不存在的东西，而这一屏本来就没有可点的人。
	var has_list: bool = _building != "wagon" and _building != "graveyard"
	_header("%s · %s" % [str(meta[1]), str(meta[2])],
		("金币 %d · 左侧点人 · 右下角返回城镇" % campaign.gold) if has_list
		else ("金币 %d · 右下角返回城镇" % campaign.gold))

	var rx: float = 288.0
	var rw: float = size.x - rx - 28.0

	# 墓园和商队不需要选人，直接给整块面板
	if _building == "graveyard":
		_draw_graveyard(Rect2(rx, 88, rw, 560))
		_add_button(Rect2(size.x - 208, 664, 180, 40), "bld_back", "返回城镇")
		_text(Vector2(DdTheme.MARGIN, 726), _building_hint(_building), DdTheme.FONT_MD,
			DdTheme.FAINT)
		return
	if _building == "wagon":
		_draw_wagon(Rect2(rx, 88, rw, 560))
		_add_button(Rect2(size.x - 208, 664, 180, 40), "bld_back", "返回城镇")
		_text(Vector2(DdTheme.MARGIN, 726), _building_hint(_building), DdTheme.FONT_MD,
			DdTheme.FAINT)
		return

	# —— 左：名册 ——
	var alive: Array = campaign.alive_ids()
	if alive.is_empty():
		_text(Vector2(28, 120), "名册里没有活人，先去马车征召。", DdTheme.FONT_BD, DdTheme.WARN)
		_add_button(Rect2(size.x - 208, 664, 180, 40), "bld_back", "返回城镇")
		_text(Vector2(DdTheme.MARGIN, 726), _building_hint(_building), DdTheme.FONT_MD,
			DdTheme.FAINT)
		return
	# 马车要能选到死人（M28）：复活和「从墓园移除」都作用在他们身上。
	# 其他建筑只列活人——铁匠铺对着一个死人没有可做的事。
	var who: Array = campaign.hero_ids() if _building == "coach" else alive
	if _building_hero.is_empty() or not who.has(_building_hero):
		_building_hero = str(alive[0])

	_text(Vector2(28, 88), "名册 %d 人" % who.size(), DdTheme.FONT_BD, DdTheme.TEXT)
	# 名册列表（M27）：15 人按「68 高一列」排会直接溢出屏幕底部
	# （15 × 78 = 1170，而可用高度只有 600 出头）。
	# 改成两列 × 42 高：8 行 × 46 = 368，从 100 到 468，正好落在面板里。
	for i in who.size():
		var hid: String = str(who[i])
		var sel: bool = hid == _building_hero
		var col: int = i % 2
		var rowi: int = i / 2
		var r := Rect2(28.0 + float(col) * 126.0, 100.0 + float(rowi) * 46.0, 118.0, 42.0)
		_panel(r, DdTheme.PANEL_HI if sel else DdTheme.PANEL_DEEP)
		if sel:
			draw_rect(r, DdTheme.PARTY, false, 2.0)
		# 死人在马车里也要能认出来（M28）：他们会出现在同一列里，
		# 但可做的事完全不同（复活 / 移除记录，而不是解雇）。
		var is_alive: bool = bool((campaign.hero(hid) as Dictionary).get("alive", true))
		_text(Vector2(r.position.x + 10, r.position.y + 16), _hero_label(hid), DdTheme.FONT_MD,
			(DdTheme.TEXT if sel else DdTheme.DIM) if is_alive else DdTheme.FAINT)
		# 压力放右边：它和名字同属「一眼要看到」的那一档。
		# draw_string 的 width 是从 pos.x **向右**量的文本框宽度，
		# 所以右对齐要把起点左移一个框宽，否则文字整个画到卡片外面去。
		var st: float = float((campaign.hero(hid) as Dictionary).get("stress", 0.0))
		_text(Vector2(r.position.x + r.size.x - 34, r.position.y + 16), "%.0f" % st, DdTheme.FONT_TAG, DdTheme.STRESS if st >= 100.0 else DdTheme.FAINT, HORIZONTAL_ALIGNMENT_RIGHT, 24)
		# 第二行只放「需要处理」的状态：没状态就留白，别拿「装备 0 阶」凑数——
		# 那一行在 118 宽里放不下，硬塞会溢出到隔壁格子。
		_text(Vector2(r.position.x + 10, r.position.y + 33),
			_hero_flags(hid) if is_alive else "已阵亡", DdTheme.FONT_TAG, DdTheme.WARN if is_alive else DdTheme.FAINT)
		_add_hit(r, "bld_hero:" + hid)
		if r.has_point(_mouse):
			draw_rect(r, Color(1, 1, 1, 0.04))

	_draw_building_panel(Rect2(rx, 88, rw, 560))
	_add_button(Rect2(size.x - 208, 664, 180, 40), "bld_back", "返回城镇")
	# 页脚（M31）：建筑屏原来是唯一没有底注的屏，内容排到 470 就断了，
	# 下面 290px 全空——看起来像「这屏还没画完」。城镇/地图/准备屏都有页脚，
	# 这里补上同一层的解释，顺便把「这个建筑在规则上到底怎么运作」说清楚。
	_text(Vector2(DdTheme.MARGIN, 726), _building_hint(_building), DdTheme.FONT_MD, DdTheme.FAINT)


## 建筑屏名册卡的第二行：只列「需要处理的状态」（M27）。
##
## 原来这里写的是「装备 0 阶 · 压力 0」，一列 236 宽够用；
## 改成两列 118 宽之后放不下，而且装备阶在这个位置没有决策价值——
## 你在疗养院看的是「他有没有病」，在铁匠铺才看装备。
func _hero_flags(hid: String) -> String:
	var bits: Array = []
	var dn: int = campaign.diseases_of(hid).size()
	if dn > 0:
		bits.append("病 %d" % dn)
	var qn: int = campaign.negative_quirks_of(hid).size()
	if qn > 0:
		bits.append("负 %d" % qn)
	var bz: int = campaign.busy_of(hid)
	if bz > 0:
		bits.append("忙 %d 周" % bz)
	return " · ".join(bits)


func _draw_building_panel(r: Rect2) -> void:
	var hid: String = _building_hero
	_panel(r, DdTheme.PANEL_DEEP)
	# 马车不按「选中的人」组织（M27）：它卖的是**没见过的人**，
	# 而那些人还不在名册里，左侧列表根本没有他们的位置。
	# 所以这一屏跳过通用标题，整个面板交给 _panel_coach 自己排版。
	if _building == "coach":
		_panel_coach(r, hid)
		return
	var row: Dictionary = campaign.hero(hid)
	_text(Vector2(r.position.x + 16, r.position.y + 30), _hero_label(hid), DdTheme.FONT_H1, DdTheme.TEXT)
	_text(Vector2(r.position.x + 16, r.position.y + 52),
		"出征 %d 次 · 阵亡 %d 次" % [int(row.get("runs", 0)), int(row.get("deaths", 0))], DdTheme.FONT_SM, DdTheme.FAINT)
	# 忙的时候按钮会全灰，光灰着不解释等于「点了没反应」
	var bz: int = campaign.busy_of(hid)
	if bz > 0:
		_text(Vector2(r.position.x + 300, r.position.y + 30),
			"这周还有事（剩 %d 周）" % bz, DdTheme.FONT_MD, DdTheme.WARN,
			HORIZONTAL_ALIGNMENT_RIGHT, r.size.x - 320)

	match _building:
		"coach":
			pass
		"smith":
			_panel_smith(r, hid)
		"sanitarium":
			_panel_sanitarium(r, hid)
		"abbey", "tavern":
			_panel_rest(r, hid)
		_:
			_text(Vector2(r.position.x + 16, r.position.y + 96), "这座建筑还在图纸上。", DdTheme.FONT_MD, DdTheme.FAINT)


## 马车（M27 / M28）：招人、捞人、赶人。
##
## 三件事挤在一屏，是因为它们都作用在「名册上的人」——
## 但分成上下两半：上半是**往名册里加**（新面孔），
## 下半是**处理名册里的人**（复活 / 解雇）。
func _panel_coach(r: Rect2, hid: String) -> void:
	var x: float = r.position.x + 16
	var y: float = r.position.y + 30
	_text(Vector2(x, y), "马车", DdTheme.FONT_H1, DdTheme.TEXT)
	_text(Vector2(x, y + 22), "名册 %d / %d 人（存活 %d）" % [
		campaign.hero_ids().size(), campaign.roster_max(), campaign.alive_ids().size()], DdTheme.FONT_SM, DdTheme.FAINT)
	y += 46

	# —— 上半：本周新面孔 ——
	_text(Vector2(x, y), "本周新面孔（每周换一批）", DdTheme.FONT_MD, DdTheme.DIM)
	var cands: Array = campaign.recruit_candidates
	if cands.is_empty():
		var why: String = "所有职业都已入册" if campaign.hireable_pool().is_empty() \
			else "这批都招走了，下周再来"
		_text(Vector2(x, y + 22), why, DdTheme.FONT_MD, DdTheme.FAINT)
	else:
		for i in cands.size():
			var cls: String = str(cands[i])
			var cost: Dictionary = campaign.hire_cost()
			_add_button(Rect2(x, y + 16.0 + float(i) * 48.0, 340, 42), "hire:" + cls,
				"%s（%d 金币）" % [_hero_label(cls), int(cost.get("gold", 0))],
				campaign.can_hire(cls))
	y += 130.0
	draw_line(Vector2(x, y), Vector2(x + 340, y), DdTheme.PANEL_EDGE, 1.0)
	y += 22.0

	# —— 下半：处理选中的人 ——
	_text(Vector2(x, y), "名册管理", DdTheme.FONT_MD, DdTheme.DIM)
	y += 10.0
	if hid.is_empty() or campaign.hero(hid).is_empty():
		_text(Vector2(x, y + 16), "左侧点一个人。", DdTheme.FONT_MD, DdTheme.FAINT)
		return
	var alive: bool = bool((campaign.hero(hid) as Dictionary).get("alive", true))
	var nm: String = _hero_label(hid)
	y += 12.0
	if alive:
		_text(Vector2(x, y),
			"%s · Lv%d · 装备 %d 阶 · 出征 %d 次" % [nm, campaign.resolve_of(hid),
			campaign.gear_of(hid), int((campaign.hero(hid) as Dictionary).get("runs", 0))], DdTheme.FONT_MD, DdTheme.TEXT)
		y += 18.0
		_text(Vector2(x, y), "解雇会把他的等级和装备一起抹掉，招回来还是 Lv1。", DdTheme.FONT_SM, DdTheme.FAINT)
	else:
		_text(Vector2(x, y), "%s · 已阵亡 %d 次" % [
			nm, int((campaign.hero(hid) as Dictionary).get("deaths", 0))], DdTheme.FONT_MD, DdTheme.WARN)
		y += 18.0
		_text(Vector2(x, y), "复活他，或者把这条墓园记录删掉。", DdTheme.FONT_SM, DdTheme.FAINT)
	y += 22.0

	if not alive:
		# 复活（破产保护）：没有它，玩家会在「没人能出征、也没钱招募」
		# 的死局里卡住，而存档不会自己回退。
		var rc: Dictionary = campaign.effective_recruit_cost(hid)
		var label: String = "免费征召（全员阵亡保底）"
		if not rc.is_empty():
			label = "复活（%d 金币）" % int(rc.get("gold", 0))
		_add_button(Rect2(x, y, 340, 42), "bld_act:recruit", label,
			campaign.can_recruit(hid))
		y += 50.0

	# 解雇（M28）：不可逆且清空投入，所以要点两次。
	if _fire_pending == hid:
		_add_button(Rect2(x, y, 340, 42), "fire2:" + hid,
			"再点一次 —— %s 会消失，等级不保留" % nm, true, true)
	else:
		var reason: String = ""
		if campaign.busy_of(hid) > 0:
			reason = "（他这周还在外面办事）"
		elif alive and campaign.alive_ids().size() <= 1:
			reason = "（至少要留一个能出征的人）"
		_add_button(Rect2(x, y, 340, 42), "fire:" + hid,
			("解雇 %s%s" % [nm, reason]) if alive else ("从墓园移除 %s" % nm),
			campaign.can_dismiss(hid))


## 真的解雇（M28）。到这一步时玩家已经点过两次了。
func _do_fire(hid: String) -> void:
	_fire_pending = ""
	var nm: String = _hero_label(hid)
	var alive: bool = bool((campaign.hero(hid) as Dictionary).get("alive", true))
	if not campaign.dismiss(hid):
		if campaign.busy_of(hid) > 0:
			_flash_msg("这周他还在外面办事，下周再说")
		elif alive and campaign.alive_ids().size() <= 1:
			_flash_msg("至少要留一个能出征的人")
		else:
			_flash_msg("这个人已经不在名册上了")
		queue_redraw()
		return
	campaign.save()
	# 选中的人被删了，指针要换到别人身上，否则右侧面板会引用一个不存在的 id
	if _building_hero == hid:
		var av: Array = campaign.alive_ids()
		if av.is_empty():
			av = campaign.hero_ids()
		_building_hero = str(av[0]) if not av.is_empty() else ""
	_flash_msg(("已解雇 %s" % nm) if alive else ("已从墓园移除 %s" % nm))
	queue_redraw()


func _panel_smith(r: Rect2, hid: String) -> void:
	var y: float = r.position.y + 96
	var gear: int = campaign.gear_of(hid)
	var cost: Dictionary = campaign.upgrade_cost(hid)
	if cost.is_empty():
		if gear >= Campaign.MAX_GEAR:
			_text(Vector2(r.position.x + 16, y), "已经满阶（%d 阶）。" % gear, DdTheme.FONT_MD, DdTheme.OK)
		else:
			# 等级不够（M25）。这和「满阶」是两件事：一个到头了，一个还能练。
			# 混成一句会让玩家以为这个人的装备线走完了，去练别人——
			# 而真相是他自己再打几趟就能升。
			_text(Vector2(r.position.x + 16, y),
				"要 Lv%d 才能穿 %d 阶。" % [gear + 2, gear + 1], DdTheme.FONT_MD, DdTheme.WARN)
			_text(Vector2(r.position.x + 16, y + 22),
				"他目前 Lv%d（经验 %d/%d），打几趟升上去就能升装备。" % [
					campaign.resolve_of(hid), campaign.xp_of(hid),
					int(Campaign.RESOLVE_XP[mini(campaign.resolve_of(hid) + 1,
						Campaign.MAX_RESOLVE)])], DdTheme.FONT_MD, DdTheme.FAINT)
			# 只说「不行」不够：这一屏得告诉玩家「练上去能拿到什么」，
			# 否则他没有任何理由继续投这个人的等级。
			var c0: Dictionary = db.hero_base(campaign.def_of(hid), gear)
			var n0: Dictionary = db.hero_base(campaign.def_of(hid), mini(gear + 1, Campaign.MAX_GEAR))
			if not c0.is_empty() and not n0.is_empty():
				_text(Vector2(r.position.x + 16, y + 46),
					"升上去会变成：生命 %d（+%d）· 护甲 %.0f%% · 速度 %.0f" % [
						int(n0.get("hp_max", 0)),
						int(n0.get("hp_max", 0)) - int(c0.get("hp_max", 0)),
						float(n0.get("prot", 0.0)) * 100.0, float(n0.get("speed", 0.0))], DdTheme.FONT_MD, DdTheme.FAINT)
		return
	var hb: Dictionary = cost.get("heirlooms", {})
	var extra: String = ""
	if not hb.is_empty():
		var k: String = str(hb.keys()[0])
		extra = " + %d %s" % [int(hb[k]), DdNames.heirloom_name(k)]
	var cur: Dictionary = db.hero_base(campaign.def_of(hid), gear)
	var nxt: Dictionary = db.hero_base(campaign.def_of(hid), mini(gear + 1, Campaign.MAX_GEAR))
	var dhp: int = int(nxt.get("hp_max", 0)) - int(cur.get("hp_max", 0))
	_text(Vector2(r.position.x + 16, y), "当前：生命 %d · 护甲 %.0f%% · 闪避 %.0f%%" % [
		int(cur.get("hp_max", 0)), float(cur.get("prot", 0.0)) * 100.0,
		float(cur.get("dodge", 0.0)) * 100.0], DdTheme.FONT_MD, DdTheme.DIM)
	_text(Vector2(r.position.x + 16, y + 22),
		"升一阶：生命 +%d，命中与伤害随武器提升" % dhp, DdTheme.FONT_MD, DdTheme.OK if dhp > 0 else DdTheme.FAINT)
	_add_button(Rect2(r.position.x + 16, y + 46, 340, 44), "bld_act:upgrade",
		"升到 %d 阶（%d 金币%s）" % [gear + 1, int(cost.get("gold", 0)), extra],
		campaign.can_upgrade(hid))


func _panel_sanitarium(r: Rect2, hid: String) -> void:
	var y: float = r.position.y + 96
	var ds: Array = campaign.diseases_of(hid)
	var ns: Array = campaign.negative_quirks_of(hid)

	_text(Vector2(r.position.x + 16, y), "疾病 %d 条" % ds.size(), DdTheme.FONT_MD, DdTheme.WARN if not ds.is_empty() else DdTheme.DIM)
	var dx: float = r.position.x + 130
	for d in ds:
		_text(Vector2(dx, y), DdNames.quirk_name(str(d)), DdTheme.FONT_MD, DdTheme.DIM)
		dx += 100.0
	_add_button(Rect2(r.position.x + 16, y + 14, 320, 42), "bld_act:disease",
		"治病一条（%d 金币）" % campaign.disease_cost(),
		not ds.is_empty() and campaign.gold >= campaign.disease_cost() \
		and campaign.busy_of(hid) <= 0)

	var y2: float = y + 84.0
	_text(Vector2(r.position.x + 16, y2), "负面怪癖 %d 条" % ns.size(), DdTheme.FONT_MD, DdTheme.WARN if not ns.is_empty() else DdTheme.DIM)
	var qx: float = r.position.x + 150
	for q in ns.slice(0, 6):
		_text(Vector2(qx, y2), DdNames.quirk_name(str(q)), DdTheme.FONT_SM, DdTheme.DIM)
		qx += 92.0
	_add_button(Rect2(r.position.x + 16, y2 + 14, 320, 42), "bld_act:quirk",
		"清掉一条（%d 金币）" % campaign.quirk_cost(),
		not ns.is_empty() and campaign.gold >= campaign.quirk_cost() \
		and campaign.busy_of(hid) <= 0)
	_text(Vector2(r.position.x + 16, y2 + 78),
		"一次只处理一条：一次全清的话，疗养院就退化成一个「点一下」的按钮。", DdTheme.FONT_SM, DdTheme.FAINT)


func _panel_rest(r: Rect2, hid: String) -> void:
	var y: float = r.position.y + 96
	var opt: Dictionary = campaign.rest_option(_building)
	var cur: float = float((campaign.hero(hid) as Dictionary).get("stress", 0.0))
	var relief: int = int(opt.get("relief", 0))
	var cost: int = int(opt.get("cost", 0))

	_text(Vector2(r.position.x + 16, y), "当前压力 %.0f / 200 —— 待完这次是 %.0f" % [
		cur, maxf(0.0, cur - float(relief))], DdTheme.FONT_BD, DdTheme.STRESS if cur >= 100.0 else DdTheme.DIM)
	_bar(Rect2(r.position.x + 16, y + 10, 340, 12), cur / 200.0, DdTheme.STRESS,
		DdTheme.STRESS_TRACK)
	_text(Vector2(r.position.x + 16, y + 42),
		"一次减 %d 点，%d 金币。压力过 100 就该来了——崩溃一次要赔进去的可不止这点。" % [
			relief, cost], DdTheme.FONT_MD, DdTheme.DIM)
	_add_button(Rect2(r.position.x + 16, y + 64, 320, 44), "bld_act:rest",
		"减压（%d 金币）" % cost, cur > 0.01 and campaign.gold >= cost \
		and campaign.busy_of(hid) <= 0)


func _draw_graveyard(r: Rect2) -> void:
	_panel(r, DdTheme.PANEL_DEEP)
	_text(Vector2(r.position.x + 16, r.position.y + 30), "墓园", DdTheme.FONT_H1, DdTheme.TEXT)
	_text(Vector2(r.position.x + 16, r.position.y + 54),
		"只记阵亡次数——谁死在哪一趟、什么原因，需要结算时落盘，还没做。", DdTheme.FONT_SM, DdTheme.FAINT)
	var gv: Array = campaign.graveyard()
	if gv.is_empty():
		_text(Vector2(r.position.x + 16, r.position.y + 96), "还没有人死在这里。", DdTheme.FONT_BD, DdTheme.DIM)
		return
	var y: float = r.position.y + 88
	for g in gv:
		var row: Dictionary = g
		_text(Vector2(r.position.x + 16, y), _hero_label(str(row["hero"])), DdTheme.FONT_BD, DdTheme.TEXT if bool(row["alive"]) else DdTheme.DIM)
		_text(Vector2(r.position.x + 180, y), "阵亡 %d 次 · 出征 %d 次 · %s" % [
			int(row["deaths"]), int(row["runs"]),
			"已归队" if bool(row["alive"]) else "未归队"], DdTheme.FONT_MD, DdTheme.FAINT)
		y += 28.0


func _draw_wagon(r: Rect2) -> void:
	_panel(r, DdTheme.PANEL_DEEP)
	# 商队只有两件事可做，而面板和别的建筑一样高——
	# 内容靠上排会显得「下半截是空的」，所以整体垂直居中（M31）。
	var inner: float = 30.0 + 26.0 + 22.0 + 44.0 + 10.0 + 44.0
	var top: float = r.position.y + maxf(30.0, (r.size.y - inner) * 0.5)
	_text(Vector2(r.position.x + 16, top), "商队", DdTheme.FONT_H1, DdTheme.TEXT)
	_text(Vector2(r.position.x + 16, top + 26),
		"饰品要在仓库里装上才生效——买回来放着不会自动戴。", DdTheme.FONT_MD, DdTheme.DIM)
	_add_button(Rect2(r.position.x + 16, top + 48, 340, 44), "bld_act:trinkets",
		("饰品仓库（%d / %d）" % [campaign.trinket_store.size(), int(campaign.store_slots)])
		if not campaign.trinket_store.is_empty() else "饰品仓库 · 空（打一趟才会有）",
		not campaign.trinket_store.is_empty())
	_add_button(Rect2(r.position.x + 16, top + 102, 340, 44), "bld_act:shop",
		"补给与饰品买卖", not campaign.shop_stock.is_empty())


## 每个建筑底部的一句「规则说明」（M31）。
##
## 建筑的规则都藏在代码里（占周、价格、上限），玩家只能靠试。
## 这句放在页脚，和城镇/地图屏的底部说明同一层：不抢视线，想知道时能看到。
func _building_hint(bid: String) -> String:
	match bid:
		"coach":
			return "新面孔每周换一批；免费征召是全员阵亡的保底。解雇会连等级和装备一起清空。"
		"smith":
			return "装备阶受等级限制：第 N 级才穿得上 N 阶。升级时技能等级同步 +1。"
		"guild":
			return "每人只能带 4 个技能：带上治疗就少一格输出，这是这一屏唯一的取舍。"
		"sanitarium":
			return "一次只处理一条：先治病还是先清负面怪癖，本身就是要做的决定。"
		"abbey", "tavern":
			return "减压一次占一周。压力过 100 就会开始崩溃，越早处理越便宜。"
		"wagon":
			return "饰品买回来是放进仓库的，要在仓库里装上才生效——不会自动佩戴。"
		"graveyard":
			return "只记阵亡次数。谁死在哪一趟、什么原因，需要在结算时落盘，还没做。"
		_:
			return ""


func _building_meta(bid: String) -> Array:
	for b in BUILDINGS:
		if str((b as Array)[0]) == bid:
			return b
	return ["", bid, ""]


## 建筑里的动作。全部走 Campaign 的校验方法，界面只负责把错误原因显示出来——
## 「为什么点不动」比「点了没反应」重要得多。
func _do_building_action(act: String) -> void:
	if act == "trinkets":
		_sel_trinket = ""
		_state = S_TRINKET
		queue_redraw()
		return
	if act == "shop":
		_sel_trinket = ""
		_state = S_SHOP
		queue_redraw()
		return
	if _building_hero.is_empty():
		_flash_msg("先选一个英雄")
		return
	var err: String = ""
	match act:
		"recruit":
			if not campaign.recruit(_building_hero):
				err = "招募失败（钱不够，或这个人还活着）"
		"upgrade":
			if not campaign.upgrade(_building_hero):
				err = "升级失败（钱或传家宝不够，或已满阶）"
		"disease":
			err = campaign.treat_disease(_building_hero)
		"quirk":
			err = campaign.purge_quirk(_building_hero)
		"rest":
			err = campaign.rest_at(_building, _building_hero)
	if not err.is_empty():
		_flash_msg(err)
	else:
		campaign.save()
		# 招募和升级是「立刻办完」，不占时间；疗养和减压才占一周
		if act == "disease" or act == "quirk" or act == "rest":
			_flash_msg("办好了 · 这一周他不能出征")
		else:
			_flash_msg("办好了")
	queue_redraw()


## 招一个新人入册（M27）。
##
## 单独一个入口而不是塞进 `_do_building_action`：那个函数的每一个分支
## 都作用在 `_building_hero`（左侧选中的人）上，而招新的对象还不在名册里，
## 根本没有「选中」这回事。硬塞进去只会让参数变成摆设。
func _do_hire(cls: String) -> void:
	if not campaign.hire(cls):
		# 三种失败原因分开说：钱不够 / 名册满 / 候选过期（换周了）
		if campaign.roster_full():
			# M28 起能解雇了，这句「还没做」从那时起就是错的
			_flash_msg("名册满了（%d 人）—— 先去马车赶走一个" % campaign.roster_max())
		elif not campaign.recruit_candidates.has(cls):
			_flash_msg("这个人已经不在本周的马车上了")
		else:
			_flash_msg("金币不足（需 %d）" % int(campaign.hire_cost().get("gold", 0)))
		return
	campaign.save()
	_flash_msg("%s 入册了 · Lv1，装备 0 阶" % _hero_label(cls))
	queue_redraw()


# ============================================================
# 公会屏：技能组（M19）
# ============================================================

## 一个英雄从 7 个技能里带 4 个。
##
## 这一屏存在的理由不是「配置」，是**取舍**：带上治疗就少一个输出位，
## 带满控制就没有回血。原来 7 个全开的时候，战斗里每个英雄都有 7 个按钮，
## 从来没有「必须放弃什么」的时刻——那不像原版，也不像决策。
func _draw_guild() -> void:
	_header("公会 · 技能组",
		"每个英雄只能带 4 个 · 点技能卡切换 · 改完自动存档")

	var alive: Array = campaign.alive_ids()
	if alive.is_empty():
		_text(Vector2(28, 120), "名册里没有活人，先回城镇征召。", DdTheme.FONT_BD, DdTheme.WARN)
		_add_button(Rect2(size.x - 208, 664, 180, 40), "close_guild", "返回城镇")
		return
	if _guild_hero.is_empty() or not alive.has(_guild_hero):
		_guild_hero = str(alive[0])

	# —— 左：名册 ——
	# 两列紧凑列表（M31）：M19 建这一屏时名册只有 5 个人，单列 68 高刚好；
	# M27 名册能到 15 人后，单列 15×78 = 1170 会直接冲出屏幕底部，
	# 盖住底部说明和返回按钮——而工会是唯一没跟着改的建筑屏。
	_text(Vector2(28, 88), "名册 %d 人" % alive.size(), DdTheme.FONT_BD, DdTheme.TEXT)
	for i in alive.size():
		var hid: String = str(alive[i])
		var sel: bool = hid == _guild_hero
		var col: int = i % 2
		var rowi: int = i / 2
		var r := Rect2(28.0 + float(col) * 126.0, 100.0 + float(rowi) * 46.0, 118.0, 42.0)
		_tile(r, TILE_ACTIVE if sel else (TILE_HOVER if r.has_point(_mouse) else TILE_IDLE))
		_text(Vector2(r.position.x + 10, r.position.y + 16), _hero_label(hid), DdTheme.FONT_MD,
			DdTheme.TEXT if sel else DdTheme.DIM)
		var n: int = campaign.equipped_skills(hid).size()
		var mx: int = campaign.skill_slot_max(hid)
		# 变身职业写「全开」而不是「0 / 7」——后者读起来像「一个都没带」
		var sel_ok: bool = campaign.skill_selectable(hid)
		_text(Vector2(r.position.x + 10, r.position.y + 33),
			("%d / %d" % [n, mx]) if sel_ok else "全开", DdTheme.FONT_TAG,
			DdTheme.OK if (not sel_ok or (mx > 0 and n >= mx)) else DdTheme.WARN)
		_add_hit(r, "guild_pick:" + hid)

	# —— 右：技能池 ——
	var rx: float = 288.0
	var rw: float = size.x - rx - 28.0
	var taken: Array = campaign.equipped_skills(_guild_hero)
	var slots: int = campaign.skill_slot_max(_guild_hero)
	# 憎恶这类变身职业：7 个技能全开、不进技能组（M31）。
	# 区分「没选」和「不用选」——原来这里显示「已装备 0 / 7」，
	# 七个技能全是「未装备」，意思正好是反的。
	var selectable: bool = campaign.skill_selectable(_guild_hero)
	if not selectable:
		_text(Vector2(rx, 88), "%s · 变身职业，%d 个技能全开" % [
			_hero_label(_guild_hero), slots], DdTheme.FONT_BD, DdTheme.OK)
	else:
		_text(Vector2(rx, 88), "%s · 已装备 %d / %d" % [
			_hero_label(_guild_hero), taken.size(), slots], DdTheme.FONT_BD,
			DdTheme.TEXT if taken.size() >= slots else DdTheme.WARN)

	var ids: Array = campaign.skill_choices(_guild_hero)
	for i in ids.size():
		var sid: String = str(ids[i])
		var on: bool = taken.has(sid) or not selectable
		var r2 := Rect2(rx, 100.0 + float(i) * 76.0, rw, 68.0)
		_tile(r2, TILE_ACTIVE if on else (TILE_HOVER if r2.has_point(_mouse) else TILE_IDLE))
		# ✓ / ＋ 同样是为了「一眼看出装没装」——M18 的出战卡就在这里栽过一次
		_text(Vector2(r2.position.x + 14, r2.position.y + 27),
			("✓ " if on else "＋ ") + DdNames.skill_name(sid), DdTheme.FONT_BD, DdTheme.TEXT if on else DdTheme.DIM)
		_text(Vector2(r2.position.x + 14, r2.position.y + 49),
			_skill_line(_guild_hero, sid), DdTheme.FONT_SM, DdTheme.FAINT)
		_text(Vector2(r2.position.x + r2.size.x - 88, r2.position.y + 34),
			("全开" if not selectable else "已装备") if on else "未装备", DdTheme.FONT_MD,
			DdTheme.OK if on else DdTheme.FAINT, HORIZONTAL_ALIGNMENT_RIGHT, 74)
		if selectable:
			_add_hit(r2, "guild_skill:" + sid)

	_add_button(Rect2(size.x - 208, 664, 180, 40), "close_guild", "返回城镇")
	_text(Vector2(DdTheme.MARGIN, 726), _building_hint("guild"), DdTheme.FONT_MD, DdTheme.FAINT)


## 切换一个技能。满格时**不挤掉**别人，直接提示——挤掉的做法在 M18 的出战屏
## 已经被证明会让人误以为「点了没反应」。
func _toggle_skill(sid: String) -> void:
	if _guild_hero.is_empty():
		return
	var cur: Array = campaign.equipped_skills(_guild_hero)
	if cur.has(sid):
		if cur.size() <= 1:
			_flash_msg("至少带一个技能")
			return
		cur.erase(sid)
	else:
		var max_n: int = campaign.skill_slot_max(_guild_hero)
		if cur.size() >= max_n:
			_flash_msg("技能栏满（%d 个）——先点掉一个再装" % max_n)
			return
		cur.append(sid)
	var why: String = campaign.set_skills(_guild_hero, cur)
	if not why.is_empty():
		_flash_msg(why)
		return
	campaign.save()
	queue_redraw()


## 一行技能说明：类型 + 可发动位 + 目标 + 数值。
##
## 原版有完整描述文本，但那在 `.strings` 里，M0 的管线没抽，
## 所以这里只能从数值反推——比没有强，但离「读得懂这技能干什么」还差一步。
##
## 踩过的坑：`launch` / `target` 在 JSON 里是 **int 或 null**，不是字符串，
## `target` 还带两种前缀（`@` 己方、`~` 全体）。第一版直接 `str()` + 逐字符拆，
## 结果 null 变成 `<null>`，显示成「打 <、11、1、1、> 位」。
func _skill_line(hid: String, sid: String) -> String:
	var h: Dictionary = db.hero(campaign.def_of(hid))
	var lv_i: int = campaign.skill_of(hid)
	for s in (h.get("skills", []) as Array):
		if not (s is Dictionary) or str((s as Dictionary).get("id", "")) != sid:
			continue
		var levels: Array = (s as Dictionary).get("levels", [])
		if levels.is_empty():
			return ""
		var lv: Dictionary = levels[clampi(lv_i, 0, levels.size() - 1)]
		var bits: Array = []
		bits.append(_skill_kind(lv))
		var launch: String = _rank_list(lv.get("launch", null))
		if not launch.is_empty():
			bits.append("可从 %s 发动" % launch)
		bits.append(_target_text(lv.get("target", null)))
		var heal: Array = lv.get("heal", [])
		if not heal.is_empty():
			bits.append("回血 %d–%d" % [int(heal[0]), int(heal[1])])
		var dmg: float = float(lv.get("dmg", 0.0))
		if absf(dmg) > 0.001:
			bits.append("伤害 %+.0f%%" % (dmg * 100.0))
		var atk: float = float(lv.get("atk", 0.0))
		if absf(atk) > 0.001:
			bits.append("命中 %+.0f%%" % (atk * 100.0))
		var cr: float = float(lv.get("crit", 0.0))
		if absf(cr) > 0.001:
			bits.append("暴击 %+.0f%%" % (cr * 100.0))
		if int(lv.get("per_battle_limit", 0)) > 0:
			bits.append("每场 %d 次" % int(lv.get("per_battle_limit", 0)))
		bits.append("Lv%d" % lv_i)
		return " · ".join(bits)
	return ""


## 技能类型。数据里相当一部分辅助技能没有 `type` 字段
## （battle_heal / inspiring_cry 都是空的），只能从效果反推。
##
## 先认「减压」再认「治疗」：鼓舞呐喊也有 heal（1–1），
## 但它的实际作用是压压力，标成治疗会让人以为它是奶。
## 这一格到底带奶还是带减压，是技能组里最核心的取舍，不能标错。
static func _skill_kind(lv: Dictionary) -> String:
	var t: String = str(lv.get("type", ""))
	match t:
		"melee": return "近战"
		"ranged": return "远程"
		"heal": return "治疗"
		"buff": return "增益"
		"debuff": return "减益"
		"move": return "位移"
		_: pass
	for e in (lv.get("effect", []) as Array):
		if str(e).to_lower().contains("stress"):
			return "减压"
	if not (lv.get("heal", []) as Array).is_empty():
		return "治疗"
	if not (lv.get("effect", []) as Array).is_empty():
		return "增益"
	return "其他"


## 掩码里能读出哪些数字位。"21" → "1、2 位"；null → ""。
static func _rank_list(mask: Variant) -> String:
	if mask == null:
		return ""
	var s: String = str(mask)
	var parts: Array = []
	for i in s.length():
		var ch: String = s.substr(i, 1)
		if ch >= "1" and ch <= "4" and not parts.has(ch):
			parts.append(ch)
	if parts.is_empty():
		return ""
	parts.sort()
	return "、".join(parts) + " 位"


## 目标描述。`~` = 敌方全体，`@` = 己方，null = 自身。
static func _target_text(mask: Variant) -> String:
	if mask == null:
		return "自身"
	var s: String = str(mask)
	if s.is_empty() or s == "null":
		return "自身"
	var ranks: String = _rank_list(mask)
	var ally: bool = s.begins_with("@")
	# 己方 1–4 位就是「全队」，写成「作用于己方 1、2、3、4 位」纯属噪音
	if ally and ranks == "1、2、3、4 位":
		return "作用于己方全体"
	var who: String = "己方" if ally else "敌方"
	var verb: String = "作用于" if ally else "打"
	if ranks.is_empty():
		return "%s %s" % [verb, who]
	if s.begins_with("~"):
		who = "敌方全体"
		verb = "打"
	return "%s %s %s" % [verb, who, ranks]


func _size_name_of(size_id: String) -> String:
	match size_id:
		"short": return "短途"
		"medium": return "中程"
		"long": return "长途"
		_: return size_id


## 本周任务板 → 难度卡的五行数据（M26 / M32）。
##
## 在这之前这四行是写死的常量，玩家永远能选 1/3/5 三档。
## 现在等级由 `Campaign.board` 每周重抽，尺寸固定（见 BOARD_SLOTS 的注释）。
## 返回格式沿用老的 `[size, level, 标题, 说明, quest]`，
## 这样两张屏幕里所有的排版代码一行都不用改。
##
## M32 起板子是**按区域**的：城镇上选哪个区域，就显示哪个区域那四张卡。
## 不传区域时用当前选中的，保持旧的调用方（准备屏）不用改。
func _board_rows(region: String = "") -> Array:
	var rgn: String = region if not region.is_empty() else _dungeon
	var src: Array = campaign.board_for(rgn)
	if src.is_empty():
		# 还没抽过（比如老驱动只建了 campaign 没读档）/ 区域名拼错：
		# 退回当前板子，宁可显示一张别的区域的卡，也不要一整屏空白。
		src = campaign.board
	var out: Array = []
	for slot in src:
		var d: Dictionary = slot
		var sn: String = str(d.get("size", "short"))
		var lv: int = int(d.get("level", 1))
		var q: String = str(d.get("quest", "explore"))
		var title: String = "%s · %d 级怪" % [_quest_size_word(q, sn), lv]
		if q == "kill_boss":
			title = "首领 · %d 级怪" % lv
		out.append([sn, lv, title, _board_note(sn, q), q])
	return out


## 任务类型 + 尺寸 → 卡片第一行那个词。
##
## 「探索 · 中程」和「清剿 · 中程」必须长得不一样：两种任务的目标完全不同
## （走到出口 vs 清光全图），只说尺寸等于让玩家点开才知道要干什么。
static func _quest_size_word(quest: String, size_id: String) -> String:
	var head: String = "探索"
	if quest == "cleanse":
		head = "清剿"
	elif quest == "gather":
		head = "收集"
	elif quest == "activate":
		head = "激活"
	elif quest == "inventory_activate":
		# 和「激活」分开写：两者在数据里同 type，但一个是碰到就算、
		# 一个是必须带道具。卡片上混成一个词，玩家进去才发现进度不动。
		head = "仪式"
	var tail: String = "短途"
	match size_id:
		"medium": tail = "中程"
		"long": tail = "长途"
	return "%s · %s" % [head, tail]


## 卡片第二行：这个任务长什么样。按尺寸和类型写，不按等级——
## 等级已经在标题里了，再重复一遍没有信息量。
static func _board_note(size_id: String, quest: String) -> String:
	if quest == "kill_boss":
		return "中程，终点必有首领"
	if quest == "cleanse":
		# 清剿不说「几场」：场数取决于地图随机，写死一个数会骗人。
		# 真正要传达的是「不能走直线」——这条决定玩家怎么规划路线。
		return "清光全图战斗，支路也得去"
	if quest == "gather":
		# 数量来自数据（item.amount = 3），但地图上会多放几个，
		# 所以不写「正好 3 个」——写死了玩家会以为漏找了一个。
		return "翻找指定奇物，集齐 3 件"
	if quest == "activate":
		return "找到铁处女，交互一次"
	if quest == "inventory_activate":
		# 和普通激活的区别就是「要带道具」——不写出来，玩家会以为
		# 这张卡和墓穴那张是一样的，进去才发现进度不动。
		return "带任务物品，用 3 次"
	match size_id:
		"short": return "4-7 场，休整 1 次"
		"medium": return "7-8 场，补给吃紧"
		"long": return "14 场，走出来就算赢"
		_: return ""


func _supply_label(id: String) -> String:
	if id == Shop.FOOD_KEY:
		return "口粮"
	return DdNames.supply_name(id)


# ============================================================
# 饰品商店（M16）
# ============================================================

## 拒绝原因翻人话。和 `_equip_reason` 分开写，因为两边的集合只有一半重叠
## （比如 `no_gold` 只有商店会有）。合成一个函数会让每个分支都要想
## 「这个 reason 另一半用不用」，反而更容易错。
func _shop_reason(reason: String) -> String:
	match reason:
		"no_gold":
			return "金币不够"
		"store_full":
			return "仓库满了"
		"limit":
			return "这件已经有一份了（唯一件）"
		"no_such_item":
			return "那里没有东西"
		"not_for_sale":
			return "这件不卖"
		"over_limit":
			return "超出携带上限"
		"no_shop":
			return "商店数据没加载"
		_:
			return reason


func _draw_shop() -> void:
	_header("城镇商店",
		"金币 %d    每趟回来换一批货" % campaign.gold)
	if campaign.shop == null:
		_text(Vector2(28, 100), "inventory.json / trinkets.json 没读到，商店不可用。", DdTheme.FONT_BD, DdTheme.WARN)
		_add_button(Rect2(size.x - 208, 640, 180, 40), "close_shop", "返回城镇")
		return

	# —— 上排：货架 ——
	_text(Vector2(28, 78), "在售（点一下买）", DdTheme.FONT_BD, DdTheme.DIM)
	var cw: float = 240.0
	var ch: float = 92.0
	var gap: float = 12.0
	for i in campaign.shop_stock.size():
		var id: String = str(campaign.shop_stock[i])
		var col: int = i % 3
		var row: int = i / 3
		var r := Rect2(28.0 + float(col) * (cw + gap), 90.0 + float(row) * (ch + gap), cw, ch)
		_panel(r, DdTheme.PANEL_DEEP)
		if id.is_empty():
			_text(Vector2(r.position.x + 12, r.position.y + 34), "已售出", DdTheme.FONT_MD, DdTheme.FAINT)
			continue
		var price: int = campaign.shop_price_at(i)
		var can: bool = campaign.gold >= price
		_text(Vector2(r.position.x + 12, r.position.y + 26), DdNames.trinket_name(id), DdTheme.FONT_BD, DdTheme.TEXT if can else DdTheme.DIM)
		_text(Vector2(r.position.x + 12, r.position.y + 46), _trinket_summary(id), DdTheme.FONT_SM, DdTheme.DIM)
		_text(Vector2(r.position.x + 12, r.position.y + 66), _trinket_rarity_name(
			campaign.trinket_lib.rarity_of(id)), DdTheme.FONT_TAG, DdTheme.STAT)
		_text(Vector2(r.position.x + 12, r.position.y + 84), "%d 金" % price, DdTheme.FONT_MD, DdTheme.CRIT if can else DdTheme.WARN)
		_add_hit(r, "shop_buy:%d" % i)
		if r.has_point(_mouse):
			draw_rect(r, Color(1, 1, 1, 0.05))

	# —— 下排：仓库（卖） ——
	_text(Vector2(28, 316), "仓库（点一下卖，只能卖仓库里的，身上戴的要先卸）", DdTheme.FONT_BD, DdTheme.DIM)
	var sy: float = 330.0
	var sw: float = 148.0
	var sh: float = 62.0
	if campaign.trinket_store.is_empty():
		_text(Vector2(28, sy + 24), "空。打几趟就有了。", DdTheme.FONT_MD, DdTheme.FAINT)
	for j in campaign.trinket_store.size():
		var tid: String = str(campaign.trinket_store[j])
		var col2: int = j % 8
		var row2: int = j / 8
		var rr := Rect2(28.0 + float(col2) * (sw + 8.0), sy + float(row2) * (sh + 8.0), sw, sh)
		_panel(rr, DdTheme.PANEL)
		_text(Vector2(rr.position.x + 8, rr.position.y + 22), DdNames.trinket_name(tid), DdTheme.FONT_MD, DdTheme.TEXT)
		_text(Vector2(rr.position.x + 8, rr.position.y + 42),
			"卖 %d 金" % campaign.shop.trinket_sell_price(tid), DdTheme.FONT_SM, DdTheme.DIM)
		_add_hit(rr, "shop_sell:%d" % j)
		if rr.has_point(_mouse):
			draw_rect(rr, Color(1, 1, 1, 0.06))

	_text(Vector2(28, 556),
		"卖出价是买价的 10%%（数据里补给就是 10%%，饰品没有自己的卖价字段）。", DdTheme.FONT_MD, DdTheme.FAINT)
	_text(Vector2(28, 578),
		"货架每趟回来换一批；已被买走的格子留空，不会往前挤。", DdTheme.FONT_MD, DdTheme.FAINT)
	_add_button(Rect2(size.x - 208, 640, 180, 40), "close_shop", "返回城镇")


# ============================================================
# 饰品：仓库与装备（M15）
# ============================================================

## 点一个槽位。三种情况，都走同一个入口，避免「装/卸」两套代码分叉：
##   * 选中了仓库里的一件 + 槽是空的 → 装上
##   * 槽里有东西 → 卸下来（不管有没有选中）
##   * 槽有东西 + 也选中了一件 → 先卸再装，等于换装
func _toggle_slot(hid: String, slot: int) -> void:
	var eq: Array = campaign.equipped_of(hid)
	var cur: String = str(eq[slot]) if slot < eq.size() else ""
	if not cur.is_empty():
		var err: String = campaign.unequip_trinket(hid, slot)
		if not err.is_empty():
			_flash_msg(_equip_reason(err))
			return
		campaign.save()
		queue_redraw()
		return
	if _sel_trinket.is_empty():
		_flash_msg("先在左边挑一件饰品")
		return
	var why: String = campaign.equip_trinket(hid, _sel_trinket)
	if why.is_empty():
		_flash_msg("%s 戴上 %s" % [_hero_label(hid), DdNames.trinket_name(_sel_trinket)])
		_sel_trinket = ""
		campaign.save()
	else:
		_flash_msg(_equip_reason(why))
	queue_redraw()


## 把拒绝原因翻成人话。
##
## 这些字符串是 Campaign 那一层返回的：那是规则层，不该知道界面语言；
## 界面层也不该反过来猜规则——所以在这里做一次显式映射。
## 不认识的 reason 原样显示，而不是吞掉（吞掉等于「点了没反应」）。
func _equip_reason(reason: String) -> String:
	match reason:
		"store_full":
			return "仓库满了，先把别的卸下来"
		"slots_full":
			return "这个人已经戴了两件"
		"class_mismatch":
			return "这个职业戴不了这件"
		"not_in_store":
			return "仓库里没有这件"
		"no_such_slot":
			return "这个格子是空的"
		"refused":
			return "装不上"
		_:
			return reason


func _draw_trinket() -> void:
	# 没有库就不画格子——`rarity_of` 会在 null 上炸。
	# 这种情况只会在数据包缺 trinkets.json 时出现，属于配置问题，
	# 说清楚比画一堆空格子强。
	if campaign.trinket_lib == null or not campaign.trinket_lib.is_loaded():
		_header("饰品仓库", "数据未加载")
		_text(Vector2(28, 100), "trinkets.json 没读到，饰品系统不可用。", DdTheme.FONT_BD, DdTheme.WARN)
		_add_button(Rect2(size.x - 208, 640, 180, 40), "close_trinkets", "返回城镇")
		return
	_header("饰品仓库",
		"点左边一件 → 再点右边某个空槽    仓库 %d / %d" % [
			campaign.trinket_store.size(), campaign.store_slots])

	# —— 左：仓库 4×4 ——
	var gx: float = 28.0
	var gy: float = 78.0
	var cw: float = 148.0
	var ch: float = 78.0
	var gap: float = 10.0
	_text(Vector2(gx, gy - 12), "仓库（点一下选中）", DdTheme.FONT_MD, DdTheme.DIM)
	for i in campaign.store_slots:
		var col: int = i % 4
		var row: int = i / 4
		var r := Rect2(gx + float(col) * (cw + gap), gy + float(row) * (ch + gap), cw, ch)
		var tid: String = str(campaign.trinket_store[i]) if i < campaign.trinket_store.size() else ""
		_panel(r, DdTheme.PANEL_DEEP if tid.is_empty() else DdTheme.PANEL)
		if tid.is_empty():
			_text(Vector2(r.position.x + 10, r.position.y + 30), "空", DdTheme.FONT_MD, DdTheme.FAINT)
			continue
		var sel: bool = _sel_trinket == tid
		if sel:
			draw_rect(r, DdTheme.CRIT, false, 2.0)
		_text(Vector2(r.position.x + 10, r.position.y + 26),
			DdNames.trinket_name(tid), DdTheme.FONT_BD, DdTheme.TEXT)
		_text(Vector2(r.position.x + 10, r.position.y + 46),
			_trinket_summary(tid), DdTheme.FONT_SM, DdTheme.DIM)
		_text(Vector2(r.position.x + 10, r.position.y + 66),
			_trinket_rarity_name(campaign.trinket_lib.rarity_of(tid)), DdTheme.FONT_TAG, DdTheme.STAT)
		_add_hit(r, "tk_store:" + tid)
		if r.has_point(_mouse):
			draw_rect(r, Color(1, 1, 1, 0.05))

	# —— 右：四个人各两个槽 ——
	var rx: float = 28.0 + 4.0 * (cw + gap) + 24.0
	var ry: float = 78.0
	var rw: float = size.x - rx - 28.0
	_text(Vector2(rx, ry - 12), "谁戴什么（点槽位卸下）", DdTheme.FONT_MD, DdTheme.DIM)
	var ids: Array = campaign.hero_ids()
	for hi in ids.size():
		var hid: String = str(ids[hi])
		var row2: Dictionary = campaign.hero(hid)
		var alive: bool = bool(row2.get("alive", true))
		var e: Array = campaign.equipped_of(hid)
		var by: float = ry + float(hi) * 118.0
		_text(Vector2(rx, by + 20), _hero_label(hid), DdTheme.FONT_BD, DdTheme.TEXT if alive else DdTheme.FAINT)
		var lv: int = int(row2.get("gear", 0))
		_text(Vector2(rx + 120, by + 20), "装备 %d 阶" % lv, DdTheme.FONT_SM, DdTheme.DIM)
		for s in campaign.equip_slots:
			var sr := Rect2(rx, by + 32.0 + float(s) * 36.0, rw - 8.0, 32.0)
			var cur: String = str(e[s]) if s < e.size() else ""
			_panel(sr, DdTheme.PANEL_DEEP if cur.is_empty() else DdTheme.PANEL_HI)
			if cur.is_empty():
				_slot_hint(sr, alive)
				_add_hit(sr, "tk_slot:%s:%d" % [hid, s])
				continue
			_text(Vector2(sr.position.x + 10, sr.position.y + 21),
				DdNames.trinket_name(cur), DdTheme.FONT_MD, DdTheme.TEXT)
			_text(Vector2(sr.position.x + sr.size.x - 46, sr.position.y + 21), "卸下", DdTheme.FONT_SM, DdTheme.WARN)
			_add_hit(sr, "tk_slot:%s:%d" % [hid, s])
			if sr.has_point(_mouse):
				draw_rect(sr, Color(1, 1, 1, 0.05))

	_add_button(Rect2(size.x - 208, 640, 180, 40), "close_trinkets", "返回城镇")
	_text(Vector2(28, 660),
		"每人两格。职业专用的件只能给对应职业；同名唯一的件全库只有一件。", DdTheme.FONT_MD, DdTheme.DIM)


## 空槽里的提示：能装就写「装这件」，不能装就写原因。
## 直接写「空」的话，玩家点了没反应会以为坏了。
func _slot_hint(sr: Rect2, alive: bool) -> void:
	var msg: String = ""
	if not alive:
		msg = "已阵亡"
	elif _sel_trinket.is_empty():
		msg = "空"
	else:
		msg = "装这件"
	_text(Vector2(sr.position.x + 10, sr.position.y + 21), msg, DdTheme.FONT_MD, DdTheme.DIM if not msg.begins_with("装") else DdTheme.OK)


## 一件饰品「大概加什么」。规则千奇百怪，这里只挑最常见的几种说，
## 说不了的就报 buff 条数——不编造。
func _trinket_summary(id: String) -> String:
	if campaign.trinket_lib == null or not campaign.trinket_lib.is_loaded():
		return ""
	var bits: Array = []
	for b in campaign.trinket_lib.buffs_for([id]):
		var st: String = str(b.get("stat_type", ""))
		var sub: String = str(b.get("stat_sub_type", ""))
		var amt: float = float(b.get("amount", 0.0))
		if st == "combat_stat_add":
			match sub:
				"speed_rating": bits.append("速度%+.0f" % amt)
				"crit_chance": bits.append("暴击%+.0f%%" % (amt * 100.0))
				"attack_rating": bits.append("命中%+.0f" % amt)
				"defense_rating": bits.append("闪避%+.0f%%" % (amt * 100.0))
				"protection_rating": bits.append("护甲%+.0f%%" % (amt * 100.0))
		elif st == "combat_stat_multiply" and sub in ["damage_low", "damage_high"]:
			bits.append("伤害%+.0f%%" % (amt * 100.0))
		elif st == "stress_dmg_received_percent":
			bits.append("受压%+.0f%%" % (amt * 100.0))
		elif st == "resistance":
			bits.append("%s抗%+.0f%%" % [sub, amt * 100.0])
		if bits.size() >= 2:
			break
	if bits.is_empty():
		var n: int = (campaign.trinket_lib.get_trinket(id).get("buffs", []) as Array).size()
		return "%d 条效果" % n
	return " ".join(bits)


func _trinket_rarity_name(r: String) -> String:
	match r:
		"very_common": return "普通"
		"common": return "常见"
		"uncommon": return "少见"
		"rare": return "稀有"
		"very_rare": return "珍稀"
		"ancestral": return "先祖"
		"trophy": return "战利品"
		"crow": return "乌鸦"
		"madman": return "疯汉"
		"collector": return "收藏家"
		"courtier": return "廷臣"
		"darkest_dungeon": return "至暗"
		"ancestral_shambler": return "先祖·蹒跚者"
		_:
			return DdNames.pretty(r)


# ============================================================
# 杂项
# ============================================================

func _drain_battle_events() -> void:
	if _battle == null:
		return
	if _battle.events.size() < _ev_pos:
		_ev_pos = 0
	while _ev_pos < _battle.events.size():
		_consume_battle_event(_battle.events[_ev_pos])
		_ev_pos += 1


func _consume_battle_event(e: Dictionary) -> void:
	match str(e.get("t", "")):
		"round_start":
			_add_log("第 %d 轮" % int(e["round"]), DdTheme.FAINT)
		"attack":
			var crit: bool = bool(e["crit"])
			_add_log("%s → %s  %d%s" % [_nm(e["actor"]), _nm(e["target"]), int(e["damage"]),
				"   暴击" if crit else ""], DdTheme.CRIT if crit else DdTheme.TEXT)
			_spawn_float(int(e["target"]), str(int(e["damage"])),
				DdTheme.CRIT if crit else DdTheme.HARM, crit)
			if bool(e["died"]):
				_add_log("【阵亡】%s" % _nm(e["target"]), DdTheme.WARN)
			elif bool(e["deaths_door"]):
				_add_log("【死门】%s" % _nm(e["target"]), DdTheme.WARN)
		"miss":
			_add_log("%s → %s  未命中（%.0f%%）" % [_nm(e["actor"]), _nm(e["target"]),
				float(e["chance"]) * 100.0], DdTheme.FAINT)
			_spawn_float(int(e["target"]), "MISS", DdTheme.FAINT)
		"heal":
			if bool(e.get("blocked", false)):
				_add_log("%s 治疗 %s  配额已尽" % [_nm(e["actor"]), _nm(e["target"])], DdTheme.WARN)
			elif int(e["amount"]) > 0:
				_add_log("%s 治疗 %s  +%d" % [_nm(e["actor"]), _nm(e["target"]), int(e["amount"])], DdTheme.HEAL)
				_spawn_float(int(e["target"]), "+%d" % int(e["amount"]), DdTheme.HEAL)
		"effect":
			if e.has("stress") and absf(float(e["stress"])) >= 1.0:
				_spawn_float(int(e["target"]), "%+.0f 压力" % float(e["stress"]), DdTheme.STAT)
			if e.has("dot"):
				_add_log("　%s 陷入%s %d 层" % [_nm(e["target"]),
					"流血" if str(e["dot"]) == "bleed" else "中毒", int(e["amount"])], DdTheme.DIM)
			# 站稳了：这一下本来要把人推开，过了 move 抗性。
			# 不写出来的话，「被推」和「没被推」在界面上没有区别，
			# 玩家会以为抗性这个属性不存在。
			if str(e.get("resisted", "")) == "move":
				move_resists += 1
				_add_log("　%s 站稳了（位移被抵抗）" % _nm(e["target"]), DdTheme.DIM)
		"dot":
			_spawn_float(int(e["target"]), "-%d" % int(e["amount"]), DdTheme.HP)
		"stress":
			_spawn_float(int(e["target"]), "%+.0f" % float(e["delta"]), DdTheme.STAT)
		"stunned":
			_add_log("　%s 被眩晕，跳过" % _nm(e["actor"]), DdTheme.FAINT)
		"pass":
			_add_log("　%s 空过" % _nm(e["actor"]), DdTheme.FAINT)
		"act_out":
			_add_log("　%s 崩溃发作，本回合不行动" % _nm(e["actor"]), DdTheme.WARN)
		"affliction":
			_add_log("【崩溃】%s（%s）" % [_nm(e["target"]), str(e.get("kind", ""))], DdTheme.WARN)
			_flash_msg("崩溃！")
		"virtue":
			_add_log("【美德】%s（%s）" % [_nm(e["target"]), str(e.get("kind", ""))], DdTheme.CRIT)
			_flash_msg("美德觉醒")
		"heart_attack":
			_add_log("【心脏骤停】%s" % _nm(e["target"]), DdTheme.WARN)
			_flash_msg("心脏骤停")
		"deaths_door":
			_add_log("【死门】%s" % _nm(e["actor"]), DdTheme.WARN)
		"surprised":
			_add_log("　%s 被惊袭，本轮不动" % _nm(e["actor"]), DdTheme.CRIT)
		"guard_up":
			_add_log("　%s 守护 %s（%d 回合）" % [_nm(e["actor"]), _nm(e["target"]),
				int(e.get("turns", 0))], DdTheme.OK)
		"guard":
			# 这一击原本打 target，实际落在 guard 身上。两个名字都要写出来，
			# 否则玩家只会看到「打向奶妈的一击，奶妈却没掉血」。
			_add_log("　%s 挡在 %s 前面" % [_nm(e["guard"]), _nm(e["target"])], DdTheme.OK)
			_spawn_float(int(e["guard"]), "挡住", DdTheme.OK)
		"riposte_up":
			_add_log("　%s 摆出反击姿态（%d 回合）" % [_nm(e["actor"]),
				int(e.get("turns", 0))], DdTheme.CRIT)
		"riposte":
			_add_log("　%s 反击%s" % [_nm(e["actor"]), "" if bool(e.get("hit", true)) else "（对方扑空）"],
				DdTheme.CRIT)
		"swap":
			_add_log("　%s 与 %s 交换位置" % [_nm(e["a"]), _nm(e["b"])], DdTheme.HEAL)
		"move":
			# 三种 move 必须分开写，否则玩家会以为「怪物在推我」和「我自己走」
			# 是同一件事：前者是被动挨打，后者是花一回合换位置。
			#   skill == "move"  英雄主动调整站位（M9）
			#   shuffle == true  阵型被打乱，落点是随机的（M11）
			#   其它             被技能推开/拉近（M9 的 push/pull，M11 起会判抗性）
			if bool(e.get("shuffle", false)):
				shuffle_moves += 1
				_add_log("　%s 被挤到 %d 号位（阵型打乱）" % [
					_nm(e["actor"]), int(e["to"]) + 1], DdTheme.WARN)
			elif str(e.get("skill", "")) == "move":
				_add_log("　%s 移动到 %d 号位" % [
					_nm(e["actor"]), int(e["to"]) + 1], DdTheme.DIM)
			else:
				forced_moves += 1
				var pushed_back: bool = int(e["to"]) > int(e["from"])
				_add_log("　%s 被%s到 %d 号位" % [_nm(e["actor"]),
					"推" if pushed_back else "拉", int(e["to"]) + 1], DdTheme.WARN)
				_spawn_float(int(e["actor"]), "推" if pushed_back else "拉", DdTheme.WARN)
		"death":
			_add_log("【阵亡】%s" % _nm(e["actor"]), DdTheme.WARN)
		"summon":
			# 召唤物是凭空出现的：没有这条日志，玩家只会看到敌人格子里
			# 多了一个单位，却不知道是谁叫来的、站在第几位。
			summons += 1
			_add_log("　%s 召来了 %s（%d 号位）" % [
				_nm(e["actor"]), DdNames.monster_name(str(e.get("monster", ""))),
				int(e.get("rank", 0)) + 1], DdTheme.WARN)
			_spawn_float(int(e["uid"]), "召唤", DdTheme.WARN)
		"summon_fail":
			# 失败也要报。静默失败会让「这只怪为什么一直不召唤」变成
			# 只能读代码才能回答的问题。
			summon_fails += 1
			var why: String = str(e.get("reason", ""))
			var text: String = "场面满了" if why == "full" else (
				"已经召够了" if why == "capped" else "没有可召的目标")
			_add_log("　%s 想召唤，但%s" % [_nm(e["actor"]), text], DdTheme.DIM)


func _nm(uid: Variant) -> String:
	if _battle == null:
		return "?"
	for u in _battle.all_units():
		if u.uid == int(uid):
			return DdNames.unit_name(u.def_id)
	return "?"


func _monster_list(ids: Array) -> Array:
	var out: Array = []
	for i in ids:
		out.append(DdNames.monster_name(str(i)))
	return out


func _gear_level() -> int:
	if exp == null:
		return 0
	for s in exp.route:
		if s.has("gear"):
			return int(s["gear"])
	return 0


## 英雄自己的装备阶（城镇里花钱升的），路线里的 gear 只是兜底默认值
func _hero_gear(hid: String) -> int:
	if exp != null and exp.hero_gear.has(hid):
		return int(exp.hero_gear[hid])
	return _gear_level()


func _max_hp(hid: String) -> int:
	var b: Dictionary = db.hero_base(campaign.def_of(hid), _hero_gear(hid))
	return int(b.get("hp_max", 1))

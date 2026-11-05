class_name Battle
extends RefCounted
## 战斗编排：一轮的行动顺序、每个单位的决策、伤害与效果结算、事件广播。
##
## 设计原则：这里不含任何表现层代码。所有结果以事件字典推入 events 数组，
## 表现层（场景/动画/音效）自己订阅。这样换美术、加动效、做回放都不用碰规则层。

const MAX_ROUNDS: int = 40

var db: DdDb
var rng: DdRng
var party: Array = []          # Combatant，index 0 = 1 号位（最前）
var enemies: Array = []
var round_index: int = 0
var events: Array = []
var _next_uid: int = 1

# —— 环境（M3）——
# 光照等外部条件对整场战斗的修正。规则层不认识「火把」，
# 只认识这几个倍率——这样资源层和战斗层可以各自替换、各自测试。
var env: Dictionary = {}
var surprised: String = ""     # ""/"party"/"enemy"：被惊袭的一方第一轮不行动

# —— 崩溃（M3）——
var affliction_refuse_chance: float = 0.15  # 崩溃者本回合摆烂的概率
var affliction_aura_stress: float = 2.0     # 崩溃者每轮给随机队友加压
var virtue_relief: float = 1.0              # 美德者每轮给随机队友减压
var stress_break_at: float = 100.0
var heart_attack_at: float = 200.0

# —— 治疗配额（M3）——
# -1 = 不限。这是 M2 结论的直接对策：治疗不设上限时，
# 累积伤害会被完全抵消，危险度无论怎么调怪物伤害都起不来。
var heal_charges: int = -1
var heals_used: int = 0

# —— 守护与反击（M10）——
#
# 两者都是「关系 / 姿态」，不是单位面板上的数值，所以放在编排层而不是 Combatant：
#   _guards      守护者 uid -> 被守护者 uid   （一个守护者只能守一个人）
#   _guarded     被守护者 uid -> 守护者 uid   （一个目标只能被一个人守）
#   _guard_left  守护者 uid -> 剩余回合
#   _riposte     uid -> {turns, mult, on_hit, on_miss}
#
# 为什么不放 Combatant：守护必须成对成立。只写在一边就会出现
# 「A 认为自己在守 B，B 不知道自己被守」——重定向查的是 B 那一侧，于是当场失效。
# 放在同一组字典里成对增删，这种半边状态根本没有机会存在。
var _guards: Dictionary = {}
var _guarded: Dictionary = {}
var _guard_left: Dictionary = {}
var _riposte: Dictionary = {}
var _riposte_depth: int = 0

## 调试开关：关掉后守护不重定向、反击不触发，用于和旧基线逐事件对照。
var guard_enabled: bool = true
var riposte_enabled: bool = true

# —— 怪癖（M14）——
#
# 条件怪癖要判「光照多少」「哪座地牢」「对面是什么种」。
# 前两个不在战斗内部，得由远征层灌进来；第三个可以自己数。
## 对照开关：关掉后不给任何人挂怪癖数值（奇物照样能拿到怪癖，只是无效）。
var quirk_enabled: bool = true
## 饰品开关。默认开——但默认没人戴东西，所以既有基线逐位不变。
var trinket_enabled: bool = true

## 僵持：打到回合上限还没分出胜负。
##
## 这一条原本只在同步驱动（`run_until_over`）里由循环上限兜住，
## **逐步驱动（界面、自检）完全没有上限**——双方互相打不死时
## `begin_round` 会一直加轮。M18 的自检就撞上过一场 228 回合的战斗：
## 治疗量压过敌方伤害、或者对面剩个打不中的残血，就会无限拉锯。
##
## 判僵持而不是判某方赢：这不是「谁更强」，是「这场打不完」。
## 后果按「脱离接触」处理——没掉落、全队加压（同撤退），
## 否则玩家可以靠拖回合白跑一场。
var stalemate: bool = false
var dungeon_name: String = ""
var light_value: float = 100.0

# —— 召唤（M12）——
#
# 阵型的硬上限是 4，不是设计选择，是**目标掩码决定的**：
# 技能的 launch/target 是 4 位掩码（`@1234`），第 5 格永远无法被任何技能
# 指定为目标。允许第 5 个敌人存在，等于造一个打不到也打不了人的摆设。
const MAX_SLOTS: int = 4

## 调试开关：关掉后召唤效果被直接丢弃，怪物回到「只会平砍」的 M11 行为。
var summon_enabled: bool = true

## 对照开关：只关估值、不关实现。用来把「AI 会用召唤」和
## 「召唤本身有效」分开——M11 已经证明，没有估值等于没有实现。
var summon_value_enabled: bool = true

## 每场召唤出了什么（monster_id → 次数），供基准与调试读取。
var summoned: Dictionary = {}

# —— 召唤估值（M12）——
#
# 又一次「解析通了但没人用」：59 条召唤效果从 M0 就在库里，接通之后
# AI 依然一次都不召唤——`cannon_summon` 的实测分数是 **0.00**，
# 因为它 atk=0、dmg=[0,0]，_score 里没有任何一条给它加分。
#
# 口径：**多出来的那个单位值多少血**。一个 brigand_fuseman 约 12 血、
# 每回合 3~6 伤，折算成「一块要多打的血 + 之后每回合多一次攻击」，
# 大约值一次平砍。用被召怪的血量归一化，不写死一个常数——
# 换数值包、换怪时会自动跟着变。
const SUMMON_VALUE_BASE: float = 1.5
const SUMMON_VALUE_HP_DIV: float = 4.0     # 每 4 点血折 1 分

## 折扣：召唤占用一回合，而且召唤物下一轮才动（本轮 _order 已快照）。
## 不打折的话，一次召 3 只的技能会因为「总价值 × 3」直接压过所有输出。
const SUMMON_DISCOUNT: float = 0.8

## 数据里没写 summon_limits 时，同一个 monster_id 在场上最多同时存在几个。
##
## **这是补充规则，不是数据。** 59 条召唤效果里只有 22 条带 summon_limits，
## 其余（包括 ectoplasm 召自己）完全无上限。只靠「阵型 4 格」兜底挡不住：
## 死一个就让位，于是 ectoplasm 场景实测 **16.3 轮**（基线 4.1），
## 关掉召唤只要 **1.97 轮**——14 轮的差距不是机制忠实，是数据缺口。
##
## 取 2 的理由：DD1 的召唤是「补位」，不是「增殖」。给 2 允许一次补员，
## 又不至于让同一种怪占满整个阵型——占满阵型正是 ectoplasm 那种
## 「打死一个又补一个」死循环的来源。
const DEFAULT_SUMMON_LIMIT: int = 2

## 一场战斗里，一个阵营累计最多召唤出几个单位。
##
## 这是第二道闸，因为它和上面那条挡的东西不一样：
##   DEFAULT_SUMMON_LIMIT    挡「同一种怪占满阵型」
##   MAX_SUMMONED_PER_BATTLE 挡「死一个补一个」的震荡循环
##
## 只上第一道闸时实测过：ectoplasm 在 16.3 轮和 23.7 轮之间波动，
## 因为同种数量始终卡在 2 个上下——打死一个，剩下那个立刻补回来，
## 阵型长度不再增长，但「要打掉的总血量」无限延伸。
##
## 取 4 = 一次填满阵型。语义是「召唤最多补充一整支队伍」，
## 超过这个量就只剩重复劳动，不再产生新的战术压力。
const MAX_SUMMONED_PER_BATTLE: int = 4

## 对照开关：关掉上面两条默认闸，回到「只靠 4 格兜底」的行为。
## 有这个开关，才能把「轮数暴涨是数据缺口」和「是机制本意」分开。
var summon_default_limit_enabled: bool = true

## 已按「抽走即移除」消费掉的条目：action.id → {monster_id: true}。
## 对应数据字段 summon_erase_data_on_roll。
var _summon_used: Dictionary = {}

## 本场累计召唤出的单位总数，受 MAX_SUMMONED_PER_BATTLE 约束。
var _summoned_total: int = 0


## gear_by_id / skill_by_id 可选：传入后按英雄各自的装备阶装配。
## 元层升级买的是「某个英雄的装备」，全队统一的 gear_level 只作为兜底默认值。
##
## loadout_by_id（M19）同理：hid -> 已装备技能 id 列表。缺省空字典 = 每人全装，
## 和 M1~M18 的历史行为逐位相同，bench 靠这一点复现旧基线。
func setup(hero_ids: Array, monster_ids: Array, seed_value: int = 1,
		gear_level: int = 0, skill_level: int = 0,
		gear_by_id: Dictionary = {}, skill_by_id: Dictionary = {},
		loadout_by_id: Dictionary = {}) -> bool:
	db = DdDb.shared()
	if db == null or db.heroes.is_empty():
		push_error("Battle: 数据未加载")
		return false
	rng = DdRng.new(seed_value)

	for hid in hero_ids:
		var c := Combatant.new()
		var g: int = int(gear_by_id.get(str(hid), gear_level))
		var s: int = int(skill_by_id.get(str(hid), skill_level))
		var lo: Array = loadout_by_id.get(str(hid), [])
		if not c.setup_from_hero(db, str(hid), g, s, lo):
			return false
		c.side = Combatant.SIDE_PARTY
		c.uid = _next_uid
		_next_uid += 1
		party.append(c)

	for mid in monster_ids:
		var m := Combatant.new()
		if not m.setup_from_monster(db, str(mid)):
			return false
		m.side = Combatant.SIDE_ENEMY
		m.uid = _next_uid
		_next_uid += 1
		enemies.append(m)

	_relayout()
	_tag_actions()
	return true


## 给每个技能预先打上「是不是守护技 / 是不是反击技」的标记。
##
## 这两个判断每回合都要用（目标过滤、AI 估值各一次），而它们要看的是
## effect 表里的字段——每回合重新查一遍 1 MB 的效果库，纯属白烧。
## 技能字典本来就是可以加键的普通字典，一次标好，之后 O(1)。
##
## 放在 setup 而不是 Combatant.build_actions：那一层是 static、拿不到 db。
func _tag_actions() -> void:
	for u in all_units():
		for a in u.actions:
			_tag_action(a)
		if not u.move_action.is_empty():
			_tag_action(u.move_action)


func _tag_action(a: Dictionary) -> void:
	var is_guard: bool = false
	var is_riposte: bool = false
	var summon: Dictionary = {}
	for en in (a.get("effects", []) as Array):
		var e: Dictionary = db.effect(str(en))
		if e.has("guard") or e.has("clearguarding") or e.has("clearguarded"):
			is_guard = true
		if e.has("riposte"):
			is_riposte = true
		if e.has("summon_monsters") and summon.is_empty():
			summon = _summon_info(e)
	a["is_guard"] = is_guard
	a["is_riposte"] = is_riposte
	a["summon"] = summon


## 把召唤效果的原始字段摊平成估值能直接用的形状。
##
## 为什么在这里做、而不是等 EffectResolver 算：估值要走 _score，
## 而 _score 绝不能消耗随机数——它每个候选技能都调一次，一旦抽了
## rng，整个基线会在「AI 多看了几个选项」这种理由下悄悄漂移。
##
## 只在 setup 时算一次（_tag_actions），战斗中零成本。
## 这里复刻 EffectResolver 的摊平规则，而不是复用它的输出——
## 那条路径要 rng。两处规则必须一致，所以共用 _aligned。
func _summon_info(e: Dictionary) -> Dictionary:
	var raw: Variant = e.get("summon_monsters", "")
	var ids: Array = []
	if raw is Array:
		for x in (raw as Array):
			ids.append(str(x))
	elif str(raw) != "":
		ids.append(str(raw))
	if ids.is_empty():
		return {}
	return {
		"ids": ids,
		"weights": EffectResolver._aligned(e.get("summon_chances", 1.0), ids.size(), 1.0),
		"limits": EffectResolver._aligned(e.get("summon_limits", 0.0), ids.size(), 0.0),
		"count": int(e.get("summon_count", 1)),
		"erase": EffectResolver._flag(e.get("summon_erase_data_on_roll", false)),
	}


func _relayout() -> void:
	for i in party.size():
		party[i].rank = i
	for i in enemies.size():
		enemies[i].rank = i


## 沿阵型移动一个单位（正 = 往后，负 = 往前），沿途的人依次让位。
##
## 阵型是「一条没有空格的线」：抽出来再插进去，中间的人自然顺移一格。
## 到边界就停在边界，不会有人被挤出去，也不会有人叠在同一格。
##
## 返回空字典表示没动（已在边界 / delta 为 0 / 找不到这个单位）。
func move_unit(u: Combatant, delta: int) -> Dictionary:
	if u == null or delta == 0:
		return {}
	var arr: Array = party if u.side == Combatant.SIDE_PARTY else enemies
	var from: int = arr.find(u)
	if from < 0:
		return {}
	var to: int = clampi(from + delta, 0, arr.size() - 1)
	if to == from:
		return {}
	arr.remove_at(from)
	arr.insert(to, u)
	_relayout()
	return {"uid": u.uid, "from": from, "to": to, "moved": to - from}


## 这个单位这一步能移到哪些位置（0-based rank）。
##
## 数据里 `move` 是 [min, max] 的**格数**范围，不是目标位置：
## crusader/vestal/plague_doctor 是 [1,1]，highwayman 是 [2,2]，
## hellion/leper 是 [0,1]。只有 0/1/2 三个值，且 0 只在「可以不动」时才出现，
## 所以它不可能是 1..4 的位置坐标。方向由玩家选，所以每个格数给出前后两个落点。
func move_options(actor: Combatant) -> Array:
	if actor == null or actor.move_action.is_empty():
		return []
	var own: Array = party if actor.side == Combatant.SIDE_PARTY else enemies
	var mr: Array = actor.move_action.get("move", [])
	if mr.size() < 2:
		return []
	var lo: int = maxi(0, int(mr[0]))
	var hi: int = maxi(lo, int(mr[1]))
	var out: Array = []
	for k in range(maxi(lo, 1), hi + 1):
		for dir in [-1, 1]:
			var r: int = actor.rank + dir * k
			if r >= 0 and r < own.size() and not out.has(r):
				out.append(r)
	out.sort()
	return out


## 执行一次移动。返回 false 表示这个落点不合法（UI 传错/已失效）。
func perform_move(actor: Combatant, target_rank: int) -> bool:
	if actor == null or not move_options(actor).has(target_rank):
		return false
	var mv: Dictionary = move_unit(actor, target_rank - actor.rank)
	if mv.is_empty():
		return false
	_emit({"t": "move", "actor": actor.uid, "from": int(mv["from"]),
		"to": int(mv["to"]), "skill": "move"})
	return true


## 交换同一方两个单位的位置。
##
## 和 move_unit 的「抽出来再插进去」不同：这里是**对调**，中间的人不动。
## 古物学家的「保护我」用它——她要求被保护者站到她前面，
## 而她自己退到后排；如果按逐格移动实现，沿途三个人都会被挤开。
func swap_units(a: Combatant, b: Combatant) -> bool:
	if a == null or b == null or a == b:
		return false
	if a.side != b.side:
		return false
	var arr: Array = party if a.side == Combatant.SIDE_PARTY else enemies
	var ia: int = arr.find(a)
	var ib: int = arr.find(b)
	if ia < 0 or ib < 0:
		return false
	arr[ia] = b
	arr[ib] = a
	_relayout()
	return true


func unit_by_uid(uid: int) -> Combatant:
	for u in all_units():
		if int(u.uid) == uid:
			return u
	return null


## 阵型里「活人的槽位」。尸体仍然占格（M1 的遗留），所以洗位只在
## 活人之间换，尸体留在原地——否则打死的怪会在阵型里滑来滑去，
## 看起来像又活了一次。
func _alive_slots(side: String) -> Array:
	var arr: Array = party if side == Combatant.SIDE_PARTY else enemies
	var out: Array = []
	for i in arr.size():
		if not (arr[i] as Combatant).dead:
			out.append(i)
	return out


## 把单个单位随机换到己方另一个槽位（数据里的 `Shuffle Self` / `Disorient`）。
##
## 「随机换到另一个槽」和「洗一遍牌」对单个单位是等价的：它最后落在哪个槽
## 只取决于一次均匀抽取。所以这里不洗整个阵营，只抽一个不同于当前位置的槽。
func shuffle_unit(u: Combatant) -> Dictionary:
	if u == null:
		return {}
	var arr: Array = party if u.side == Combatant.SIDE_PARTY else enemies
	var slots: Array = _alive_slots(u.side)
	if slots.size() < 2:
		return {}
	var from: int = arr.find(u)
	if from < 0:
		return {}
	# 从「除自己之外」的活人槽位里抽。抽不到就说明没地方可去。
	var candidates: Array = []
	for s in slots:
		if int(s) != from:
			candidates.append(int(s))
	if candidates.is_empty():
		return {}
	var to: int = int(candidates[rng.next_int(candidates.size())])
	arr[from] = arr[to]
	arr[to] = u
	_relayout()
	return {"uid": u.uid, "from": from, "to": to}


## 打乱整个阵营（数据里的 `Shuffle Party 1..5`）。
##
## 只重排活人的槽位，尸体原地不动。Fisher-Yates，消耗 n-1 次随机数。
func shuffle_team(side: String) -> Array:
	var arr: Array = party if side == Combatant.SIDE_PARTY else enemies
	var slots: Array = _alive_slots(side)
	if slots.size() < 2:
		return []
	var picked: Array = []
	var old_rank: Dictionary = {}      # uid -> 洗之前站第几位
	for k in slots.size():
		var slot: int = int(slots[k])
		var u: Combatant = arr[slot]
		picked.append(u)
		old_rank[u.uid] = slot
	for i in range(picked.size() - 1, 0, -1):
		var j: int = rng.next_int(i + 1)
		var tmp: Variant = picked[i]
		picked[i] = picked[j]
		picked[j] = tmp
	var out: Array = []
	for k in slots.size():
		var slot2: int = int(slots[k])
		var u2: Combatant = picked[k]
		var was: int = int(old_rank[u2.uid])
		if was != slot2:
			out.append({"uid": u2.uid, "from": was, "to": slot2})
		arr[slot2] = u2
	_relayout()
	return out


# ============================================================
# 召唤（M12）
# ============================================================

## 找这个阵营里能给召唤物用的槽位。返回 -1 表示满了。
##
## rank_mask 是数据里的 summon_ranks，**位掩码**不是槽位号（见 effect_resolver
## 那段注释：brigand_sapper 写 12 = 0b1100 = 3、4 号位）。
##
## 四条规则，按优先级：
##   1. 掩码里、且那一格躺着尸体 → 用它（数据说了「去这个位置」）
##   2. 掩码里、且还没被占（掩码的位正好等于当前长度）→ 往后接
##   3. 任何躺着尸体的格子 → 尸体让位
##   4. 阵型还没满 → 往后接
##
## 第 3、4 条是**兜底**：掩码常常指向「3 号位」，但场上只有 1 个怪。
## 因为掩码不匹配就拒绝召唤，会让大部分召唤永远不触发——比放错位置糟得多。
##
## 尸体让位是这个项目特有的：DD1 里尸体不占位，「召不出来」只有
## 4 个敌人全活着时才成立。这里尸体占位（M1 遗留），不让位就会出现
## 「打死了两个，剩下两个活的 + 两具尸体，却因为没有空位召不出来」。
##
## 尸体会被**替换**而不是挪走：阵型是一条没有空洞的线（_relayout 直接把
## rank 写成下标），不存在「给尸体换个位置」这回事。
func summon_slot(side: String, rank_mask: int = 0) -> int:
	var arr: Array = party if side == Combatant.SIDE_PARTY else enemies
	if rank_mask > 0:
		for i in arr.size():
			if (rank_mask & (1 << i)) != 0 and not (arr[i] as Combatant).is_alive():
				return i
		if arr.size() < MAX_SLOTS and (rank_mask & (1 << arr.size())) != 0:
			return arr.size()
	for i in arr.size():
		if not (arr[i] as Combatant).is_alive():
			return i
	if arr.size() < MAX_SLOTS:
		return arr.size()
	return -1


## 场上某种怪还活着几个。summon_limits 按这个数判定。
func summon_count(monster_id: String, side: String) -> int:
	var arr: Array = party if side == Combatant.SIDE_PARTY else enemies
	var n: int = 0
	for u in arr:
		if (u as Combatant).def_id == monster_id and (u as Combatant).is_alive():
			n += 1
	return n


## 把一个怪物实体化到指定阵营的指定槽位。
##
## slot >= 数组长度 → 追加；否则替换那一格（那个位置一定躺着尸体，
## 调用方要先过 summon_slot）。
func summon_monster(monster_id: String, side: String, slot: int) -> Combatant:
	var u := Combatant.new()
	if not u.setup_from_monster(db, monster_id):
		return null
	u.side = side
	u.uid = _next_uid
	_next_uid += 1
	# 光照的先攻加值是按阵营一次性写进单位的（set_environment），
	# 中途加入的单位拿不到那一次写入，必须在这里补。
	u.initiative_bonus = float(env.get("init_enemy" if side == Combatant.SIDE_ENEMY else "init_party", 0.0))

	var arr: Array = party if side == Combatant.SIDE_PARTY else enemies
	if slot >= arr.size():
		arr.append(u)
	else:
		# 被顶掉的尸体如果有反击姿态，关系表里会留一条指向死 uid 的孤项。
		# 清掉：不清不会报错，但字典会随战斗无限长，且 tick 时要多走一遍。
		var old: Combatant = arr[slot]
		_riposte.erase(old.uid)
		_guards.erase(old.uid)
		_guard_left.erase(old.uid)
		arr[slot] = u
	_relayout()

	# 和 setup() 一样要打标记，否则新单位的 is_guard / is_riposte 缺失。
	# 怪物目前没有守护数据，但反击是有的——漏了就是「召唤物不会还手」，
	# 这种差异不会报错，只会让同一只怪在召唤前后行为不同。
	for a in u.actions:
		_tag_action(a)
	if not u.move_action.is_empty():
		_tag_action(u.move_action)
	return u


## 权重抽一个可召的候选，返回**列表下标**（-1 = 抽不出来）。
##
## 返回下标而不是 id：summon_ranks 是按候选一一对齐的，
## 只拿 id 会丢掉「这个候选该站哪」。
##
## 三重过滤：已达数量上限、已被「抽走即移除」消费过、权重为 0。
##
## 数量上限的取法：数据有 summon_limits 就用数据的（炮船 = 1，意思是
## 「只能有一门炮灰」）；没有就退到 DEFAULT_SUMMON_LIMIT。
## **不能反过来**——数据为 0 的条目表示题不对，不该被当成「随便召」。
func _pick_summon_index(pool: Array, weights: Array, limits: Array,
		used: Dictionary, side: String) -> int:
	var idx: Array = []
	var ws: Array = []
	var total: float = 0.0
	for i in pool.size():
		var mid: String = str(pool[i])
		if used.has(mid):
			continue
		var lim: int = int(limits[i]) if i < limits.size() else 0
		if lim <= 0 and summon_default_limit_enabled:
			lim = DEFAULT_SUMMON_LIMIT
		if lim > 0 and summon_count(mid, side) >= lim:
			continue
		var w: float = float(weights[i]) if i < weights.size() else 1.0
		if w <= 0.0:
			continue
		idx.append(i)
		ws.append(w)
		total += w
	if idx.is_empty():
		return -1
	var roll: float = rng.next_float() * total
	var acc: float = 0.0
	for k in idx.size():
		acc += float(ws[k])
		if roll <= acc:
			return int(idx[k])
	return int(idx[idx.size() - 1])


## 把解析层算出的召唤意图落成实际单位。
##
## 三条放弃条件，每条都发事件而不是静默返回——召唤失败和成功在日志里
## 长得一样的话，「为什么这只怪一直不召唤」会变成无法调试的现象：
##   满位      4 个敌人全活着，数据里没有「替换谁」的信息，只能放弃
##   达上限    summon_limits 到了（炮船只能有一门炮灰，就是这条）
##   池空      候选都被过滤掉了
func _consume_summon_effect(ev: Dictionary, actor: Combatant, action: Dictionary) -> void:
	if not summon_enabled or not bool(ev.get("summon", false)):
		return
	var ids: Array = ev.get("summon_list", [])
	if ids.is_empty():
		return
	var weights: Array = ev.get("summon_weights", [])
	var limits: Array = ev.get("summon_limits", [])
	var ranks: Array = ev.get("summon_ranks", [])
	var count: int = maxi(int(ev.get("summon_count", 1)), 0)
	var erase: bool = bool(ev.get("summon_erase", false))
	var used: Dictionary = _summon_used.get(action.id, {})

	for _n in count:
		if summon_default_limit_enabled and _summoned_total >= MAX_SUMMONED_PER_BATTLE:
			_emit({"t": "summon_fail", "actor": actor.uid, "reason": "capped",
				"skill": action.id})
			return
		var k: int = _pick_summon_index(ids, weights, limits, used, actor.side)
		if k < 0:
			_emit({"t": "summon_fail", "actor": actor.uid, "reason": "pool_empty",
				"skill": action.id})
			return
		var mid: String = str(ids[k])
		var mask: int = int(ranks[k]) if k < ranks.size() else 0
		var slot: int = summon_slot(actor.side, mask)
		if slot < 0:
			_emit({"t": "summon_fail", "actor": actor.uid, "reason": "full",
				"skill": action.id})
			return
		var u: Combatant = summon_monster(mid, actor.side, slot)
		if u == null:
			_emit({"t": "summon_fail", "actor": actor.uid, "reason": "unknown_monster",
				"monster": mid, "skill": action.id})
			return
		if erase:
			used[mid] = true
			_summon_used[action.id] = used
		summoned[mid] = int(summoned.get(mid, 0)) + 1
		_summoned_total += 1
		_emit({"t": "summon", "actor": actor.uid, "uid": u.uid,
			"monster": mid, "rank": slot, "skill": action.id,
			"loot": bool(ev.get("summon_loot", true))})


## 环境修正。字段全部可缺省，缺省即「无修正」，所以不传 env 的老用法完全不变。
##   stress_damage    光照对受压的加成（0.2 = +20%）
##   monster_dmg / monster_acc / monster_crit   光照给怪物的加成
##   player_dodge / player_crit                  光照给英雄的加成
##   init_party / init_enemy                     先攻加值（速度之上再加）
func set_environment(e: Dictionary) -> void:
	env = e
	# 怪癖条件里的「哪座地牢」「多亮」也从这里进。不另开一个 setter，
	# 是因为这两个数本来就属于「这一场战斗发生在什么环境里」，
	# 分开传会让调用方以后只记得改一个。
	if e.has("dungeon"):
		dungeon_name = str(e["dungeon"])
	if e.has("light"):
		light_value = float(e["light"])
	var stress_mult: float = 1.0 + float(e.get("stress_damage", 0.0))
	for u in party:
		u.stress_in_mult = stress_mult
		u.initiative_bonus = float(e.get("init_party", 0.0))
	for m in enemies:
		m.initiative_bonus = float(e.get("init_enemy", 0.0))


## 把远征携带的血量/压力/崩溃状态灌回新一场战斗。
## 这是「跨战斗」语义的唯一入口——没有它，每场战斗都是满血零压力，
## 资源层就退化成「打了几场」的计数器。
func apply_party_state(state: Dictionary) -> void:
	for u in party:
		var s: Dictionary = state.get(u.def_id, {})
		if s.is_empty():
			continue
		var ratio: float = float(s.get("hp_ratio", 1.0))
		if bool(s.get("at_deaths_door", false)) or ratio <= 0.0:
			u.hp = 0
			u.enter_deaths_door(db)
		else:
			u.hp = clampi(int(round(ratio * float(u.base_hp))), 1, u.base_hp)
		u.stress = clampf(float(s.get("stress", 0.0)), 0.0, 200.0)
		var aff: String = str(s.get("affliction", ""))
		if not aff.is_empty():
			u.apply_affliction(db, aff)
		var vir: String = str(s.get("virtue", ""))
		if not vir.is_empty():
			u.apply_virtue(db, vir)
		if bool(s.get("recovering", false)):
			u.recovering = true
			u.apply_recovery_buffs(db, bool(s.get("heart_attacked", false)))
		# 怪癖放在最后：max_hp 类怪癖改的是 base_hp 这个分母，
		# 必须在「按比例还原血量」之后做，否则先把分母改小再乘比例，
		# 血量会被算两遍。set_quirks 内部会把 hp 同比例缩回去，比值不变。
		if quirk_enabled and db.quirk_lib != null and db.quirk_lib.is_loaded():
			var qids: Array = s.get("quirks", [])
			if not qids.is_empty():
				u.set_quirks(qids, db.quirk_lib)
		# 饰品同理，而且必须在 set_quirks 之后：两者都可能乘 base_hp，
		# 顺序换了血量比例会因为舍入差一点。功能上不是错的，但基线会漂。
		if trinket_enabled and db.trinket_lib != null and db.trinket_lib.is_loaded():
			var tids: Array = s.get("trinkets", [])
			if not tids.is_empty():
				u.set_trinkets(tids, db.trinket_lib)


## 怪癖判定的语境。每轮/每次行动前重算，所以这里现取现用。
##
## enemy_types 只统计**活着**的敌人：对面的兽类死光了，
## 「恐惧兽类」就不该继续加压。这是条件怪癖里唯一需要实时看场的项。
## `target` 与 `skill_id` 是 M15 加的：饰品的 6 种新规则里，
## `attacking_monster_type` / `monsterSize` 要看目标，
## `actorStatus` / `skill` / `in_rank` / `at_deaths_door` 要看自己。
## 不传 target 时这几项按「不成立」处理——不是按 0 处理，
## 否则「对兽类增伤」会在没指定目标时白送。
func _quirk_ctx_for(u: Combatant, skill_type: String = "", skill_id: String = "",
		target: Combatant = null) -> Dictionary:
	var et: Array = []
	for e in living(enemies):
		for t in e.enemy_types:
			et.append(str(t))
	var st: Array = []
	for k in u.statuses.keys():
		if int(u.statuses[k]) > 0:
			st.append(str(k))
	var ctx: Dictionary = {
		"dungeon": dungeon_name,
		"light": light_value,
		"round": round_index,
		"hp_ratio": u.hp_ratio(),
		"stress": u.stress,
		"enemy_types": et,
		"skill_type": skill_type,
		"skill_id": skill_id,
		"rank": u.rank,
		"at_deaths_door": u.at_deaths_door,
		"statuses": st,
	}
	if target != null:
		ctx["target_types"] = target.enemy_types.duplicate()
		ctx["target_size"] = target.size
	return ctx


## 全场按当前轮次刷新。每轮开头调一次。
func _refresh_all_quirks() -> void:
	if not quirk_enabled:
		return
	for u in all_units():
		u.refresh_quirks(_quirk_ctx_for(u))


## 战斗结束后把队伍状态交给远征层。血量存比例而不是绝对值——
## 各英雄上限不同，存绝对值在换装备阶后必然错。
func capture_party_state() -> Dictionary:
	var out: Dictionary = {}
	for u in party:
		out[u.def_id] = {
			"hp_ratio": 0.0 if u.dead else u.hp_ratio(),
			"hp": u.hp,
			"stress": u.stress,
			"affliction": u.affliction,
			"virtue": u.virtue,
			"at_deaths_door": u.at_deaths_door,
			"dead": u.dead,
			"recovering": u.recovering,
			"heart_attacked": u.heart_attacked,
			# 怪癖跟着人走。放进快照里，`state` 整份替换时才不会丢；
			# 只靠远征层「替换后补回来」也能work，但那是两处状态在同步，
			# 迟早有一条路径漏掉（这个 bug 就是这么来的）。
			"quirks": u.quirk_ids.duplicate(),
			"trinkets": u.trinket_ids.duplicate(),
		}
	return out


func all_units() -> Array:
	var out: Array = []
	out.append_array(party)
	out.append_array(enemies)
	return out


func living(team: Array) -> Array:
	var out: Array = []
	for u in team:
		if u.is_alive():
			out.append(u)
	return out


func is_over() -> bool:
	return stalemate or living(party).is_empty() or living(enemies).is_empty()


func winner() -> String:
	# 僵持优先：双方都还有人活着，谁也不算赢
	if stalemate:
		return "none"
	if living(enemies).is_empty():
		return "party"
	if living(party).is_empty():
		return "enemy"
	return ""


# ============================================================
# 回合循环
# ============================================================
#
# 这一层有两套驱动方式，共用同一段结算逻辑：
#
#   run_round()      同步跑完整轮，英雄由 AI 决策 —— bench、测试、回放都走这条
#   begin_round() +  逐步推进，遇到英雄行动就停下来等外部 submit_choice()
#   step_turn()      —— 给玩家操作的表现层走这条
#
# 为什么不是「在 run_round 里 await」：规则层是 RefCounted，没有信号，
# 也不该为了界面去引信号。把它做成「可以停、可以续」的状态机，
# 表现层自己决定什么时候调用下一次 step，规则层反而更干净。

## 非空时，英雄的决策交给外部（玩家）。返回 {} 表示交回 AI 兜底。
var decision_provider: Callable = Callable()

var _order: Array = []
var _order_pos: int = 0
var _round_open: bool = false
var awaiting_input: Combatant = null


func begin_round() -> void:
	if _round_open:
		return
	events = []
	if is_over():
		return
	if round_index >= MAX_ROUNDS:
		# 到上限就收场。注意这里 return 之前要置 _round_open，
		# 否则调用方会以为这一轮已经开过而反复进来。
		stalemate = true
		_round_open = true
		_emit({"t": "stalemate", "round": round_index})
		return
	round_index += 1
	# 必须在 build_order **之前**刷：行动序是按速度算的，
	# 而「首轮 +2 速度」这类怪癖就是要改这一轮的先手。
	# 放到排序之后再刷，速度怪癖就永远慢半拍，只能影响伤害不能影响顺序。
	_refresh_all_quirks()
	_order = TurnScheduler.build_order(all_units(), rng, db.rules.initiative_base)
	_order_pos = 0
	_round_open = true
	_emit({"t": "round_start", "round": round_index})
	var ids: Array = []
	for entry in _order:
		ids.append(entry.actor.uid)
	_emit({"t": "order", "ids": ids})


func round_open() -> bool:
	return _round_open


## 推进一个单位。
##
## 返回 true = 本轮还没结束（可以继续调）；
## 返回 false = 本轮已收尾（end_of_round 已执行），下一次要重新 begin_round。
## 返回 true 且 awaiting_input 非空 = 卡在英雄行动上，必须 submit_choice 才能继续。
func step_turn() -> bool:
	if not _round_open:
		return false
	while _order_pos < _order.size():
		if is_over():
			break
		var entry: Dictionary = _order[_order_pos]
		_order_pos += 1
		var actor: Combatant = entry.actor
		if not actor.is_alive():
			continue

		# 惊袭：被偷袭的一方第一轮整轮不行动。DD1 的惊袭就是这个意思，
		# 不是「先攻低一点」——做成先攻惩罚会让它变成可以忽略的小事。
		if round_index == 1 and not surprised.is_empty() and actor.side == surprised:
			_emit({"t": "surprised", "actor": actor.uid})
			continue

		if actor.stun_turns > 0:
			_emit({"t": "stunned", "actor": actor.uid})
			actor.consume_stun()
			continue

		if not _open_turn(actor):
			return true
		if actor.is_hero and decision_provider.is_valid() and not awaiting_input:
			awaiting_input = actor
			_emit({"t": "await_input", "actor": actor.uid})
			return true
		_take_action(actor)
		check_stress_breaks()
		return true

	_round_open = false
	_end_of_round()
	check_stress_breaks()
	return false


## 玩家提交决策。action 为空 = 跳过本回合（吃空过压力）。
func submit_choice(action: Dictionary, targets: Array = []) -> void:
	if awaiting_input == null:
		return
	var actor: Combatant = awaiting_input
	awaiting_input = null
	if action.is_empty():
		if actor.is_hero:
			actor.add_stress(float(db.rules.raw.get("passed_turn_stress_dmg", 5.0)))
		_emit({"t": "pass", "actor": actor.uid})
	else:
		_apply_choice(actor, {"action": action, "targets": targets})
	check_stress_breaks()


## 玩家选择移动到某个位置。和 submit_choice 一样消耗这一回合。
func submit_move(target_rank: int) -> void:
	if awaiting_input == null:
		return
	var actor: Combatant = awaiting_input
	awaiting_input = null
	if not perform_move(actor, target_rank):
		# 落点失效（比如队列错位）：不惩罚，重新等一次输入
		awaiting_input = actor
		return
	check_stress_breaks()


## 当前可以出手的英雄能选哪些技能、各自能打谁。表现层据此画按钮。
func player_options(actor: Combatant) -> Array:
	var out: Array = []
	for action in actor.actions:
		if not _can_use(actor, action):
			continue
		var targets: Array = _legal_targets(actor, action)
		if targets.is_empty():
			continue
		out.append({"action": action, "targets": targets})
	return out


## 跑一整轮，返回本轮事件（同时累加到 self.events 供外部读取）。
## 没有 decision_provider 时行为与 M1 完全一致——bench 就是靠这一点保持可比的。
func run_round() -> Array:
	begin_round()
	while step_turn():
		if awaiting_input != null:
			# 同步模式下没人会来点按钮，用 AI 兜底
			var a: Combatant = awaiting_input
			awaiting_input = null
			_take_action(a)
	return events


func run_until_over(max_rounds: int = MAX_ROUNDS) -> void:
	var guard: int = 0
	while not is_over() and guard < max_rounds:
		run_round()
		guard += 1


## 回合开场：广播 turn，处理崩溃者摆烂。返回 false 表示这一回合直接废掉。
func _open_turn(actor: Combatant) -> bool:
	_emit({"t": "turn", "actor": actor.uid, "name": actor.display_name})

	# 崩溃者会「摆烂」：这一回合什么都不做。这是崩溃真正的代价——
	# 不是面板上 -10% 命中，而是队伍在关键时刻少一个行动。
	if actor.is_hero and actor.has_affliction() and rng.chance(affliction_refuse_chance):
		_emit({"t": "act_out", "actor": actor.uid, "kind": actor.affliction})
		return false
	return true


func _take_action(actor: Combatant) -> void:
	_apply_choice(actor, choose_action(actor))


func _apply_choice(actor: Combatant, choice: Dictionary) -> void:
	if choice.is_empty():
		# 无可用行动：空过并吃压力（rules.passed_turn_stress_dmg = 5）
		if actor.is_hero:
			actor.add_stress(float(db.rules.raw.get("passed_turn_stress_dmg", 5.0)))
		_emit({"t": "pass", "actor": actor.uid})
		return

	# 移动没有 action，只有一个落点
	if str(choice.get("kind", "")) == "move":
		perform_move(actor, int(choice.get("move_to", -1)))
		return

	var action: Dictionary = choice.action
	var targets: Array = choice.targets

	# 「只对近战生效」「只对远程生效」这类条件要等技能定了才知道判什么。
	# 轮初那次刷新用的是 skill_type=""，两者都不会生效——所以这里按实际
	# 动作再刷一次。否则 meleeonly 的 +10% 伤害永远不会进伤害公式。
	# M15 起还要带上技能 id 与目标：`skill` / `attacking_monster_type` /
	# `monsterSize` 三条饰品规则全靠它们。多目标时取第一个当代表——
	# 逐目标刷新会让「同一个技能对不同人有不同增伤」，那是逐次结算的语义，
	# 不是这套 buff 的语义。
	if quirk_enabled:
		var first_target: Combatant = null
		if not targets.is_empty():
			first_target = targets[0]
		actor.refresh_quirks(_quirk_ctx_for(actor, str(action.get("type", "")),
			str(action.get("id", "")), first_target))

	if int(action.per_battle_limit) > 0:
		actor.per_battle_uses[action.id] = int(actor.per_battle_uses.get(action.id, 0)) + 1

	for t in targets:
		if t.dead:
			continue
		_resolve_action(actor, action, t)


func _end_of_round() -> void:
	for u in all_units():
		if not u.is_alive():
			continue
		var ticks: Array = EffectResolver.tick_dots(u, rng)
		for tk in ticks:
			_emit({"t": "dot", "target": u.uid, "kind": tk.kind, "amount": tk.amount})
		if u.dead:
			_emit({"t": "death", "actor": u.uid, "hero": u.is_hero})
			continue
		_ensure_deaths_door_buffs(u)
		u.tick_round()
	_affliction_aura()
	# 放在最后：先让持续伤害把该带走的带走，再判守护者还在不在。
	# 反过来的话，一个刚被流血打死的守护者还能再挡一整轮。
	_tick_guards_and_riposte()


## 死门减益的统一补挂点。
## 触发路径有三条（普通攻击、持续伤害、心脏骤停），逐个去挂必然漏一条，
## 所以改成「谁在死门上但没挂 buff，就补上」。
func _ensure_deaths_door_buffs(u: Combatant) -> void:
	if not u.is_hero or not u.at_deaths_door:
		return
	if not u.dd_buff_ids.is_empty():
		return
	u.enter_deaths_door(db)
	_emit({"t": "deaths_door", "actor": u.uid})


## 崩溃者的「氛围伤害」：每个崩溃英雄每轮给一名随机队友加压；
## 美德者反过来给队友减压。这是把压力从「一个数字」变成「队伍战力」的关键——
## 没有它，压力 100 和压力 0 在战斗里没有任何区别。
func _affliction_aura() -> void:
	for u in party:
		if not u.is_alive():
			continue
		if u.has_affliction():
			var mate: Combatant = _random_mate(u)
			if mate != null:
				var d: float = mate.add_stress(affliction_aura_stress)
				_emit({"t": "stress", "target": mate.uid, "delta": d,
					"source": "afflicted_aura", "from": u.uid})
		elif u.is_virtuous():
			var mate2: Combatant = _random_mate(u)
			if mate2 != null and mate2.stress > 0.0:
				var before: float = mate2.stress
				mate2.stress = clampf(mate2.stress - virtue_relief, 0.0, 200.0)
				_emit({"t": "stress", "target": mate2.uid,
					"delta": mate2.stress - before, "source": "virtue_aura", "from": u.uid})


func _random_mate(u: Combatant) -> Combatant:
	var mates: Array = []
	for m in living(party):
		if m != u:
			mates.append(m)
	if mates.is_empty():
		return null
	return mates[rng.next_int_range(0, mates.size() - 1)]


func _emit(e: Dictionary) -> void:
	events.append(e)


# ============================================================
# 决策
# ============================================================

## 从 actor 可用技能里挑一个评分最高的，并选定目标。
## M1 的打分是显著简化版——DD1 真实 AI 的评分函数在 exe 里，数据只给 brain id。
## 移动占掉一整回合的折扣。
##
## 不是 1.0：移动本身不产出伤害或治疗，只有「换位置之后能做的事」变好才划算。
## 0.75 表示「移动后的收益至少要比现在高三分之一，才值得花这个回合」。
## 这个数直接决定 AI 会不会乱动，所以它是要量的，不是拍的（见 M9 文档）。
const MOVE_DISCOUNT: float = 0.75

## 调试开关：关掉之后 AI 完全不会考虑移动，用于和旧基线逐事件对照。
var move_ai_enabled: bool = true

# —— M11：位移与洗位 ——

## 每挪动一格值多少分。
##
## 这个数不是从数据里读的，DD1 也没有等价字段——它是**本项目的估值**，
## 所以必须显式写出来并说明依据：位移本身不造成伤害，它改变的是
## 「目标还能不能用它想用的技能」。给太低（0.2）位移技能永远输给
## 带压力的同类技能（见 M11 文档）；给太高，AI 会为了推人放弃输出。
const MOVE_VALUE_PER_RANK: float = 1.0

## 洗位的估值。洗位不保证把人送到坏位置（随机），所以给一个低于
## 「稳定挪 1 格」的固定值——它值的是「打乱」，不是「安置」。
const SHUFFLE_VALUE: float = 1.5

## 对照开关：关掉位移估值，AI 就回到 M10 的行为（永远不选带位移的技能）。
## 这是把「AI 开始用位移」和「位移本身有效」分开的唯一办法。
var move_value_enabled: bool = true

## 对照开关：关掉位移抗性。抗性会影响 rng 序列，所以这个开关
## 是「抗性到底改变了多少」的唯一干净对照。
var move_resist_enabled: bool = true


func choose_action(actor: Combatant) -> Dictionary:
	var best: Dictionary = {}
	var best_score: float = -1.0

	for action in actor.actions:
		if not _can_use(actor, action):
			continue
		var targets: Array = _legal_targets(actor, action)
		if targets.is_empty():
			continue
		var target: Combatant = _pick_target(actor, action, targets)
		var score: float = _score(actor, action, target)
		if score > best_score:
			best_score = score
			best = {"action": action, "targets": targets if action.target_aoe else [target]}

	# 移动：只有「换个位置能做的事明显更好」才值得花一回合。
	# 这里不模拟「移动后再行动」——那会让 AI 多算一整回合，
	# 也会让 bench 的随机流难以复现。折扣就是那个粗糙但可解释的近似。
	if move_ai_enabled and not actor.move_action.is_empty():
		var plan: Dictionary = best_move_plan(actor)
		if not plan.is_empty():
			var discounted: float = float(plan["score"]) * MOVE_DISCOUNT
			if discounted > best_score:
				return {"kind": "move", "move_to": int(plan["rank"]), "score": discounted}
	return best


## 算「移到哪个位置 + 用什么技能」收益最高。
##
## 做法是临时把 rank 改掉再走一遍正常的可用性判断——不改任何状态，
## 只是让 launch_mask / target_mask 在别的位置上重新算一次。
## 这是唯一能准确回答「挪过去之后到底能做什么」的办法：
## 手工推演 mask 一定会和 _can_use / _legal_targets 的实际规则走偏。
func best_move_plan(actor: Combatant) -> Dictionary:
	var opts: Array = move_options(actor)
	if opts.is_empty():
		return {}
	var orig: int = actor.rank
	var best: Dictionary = {}
	var best_score: float = -1.0
	for r in opts:
		actor.rank = int(r)
		for action in actor.actions:
			if not _can_use(actor, action):
				continue
			var targets: Array = _legal_targets(actor, action)
			if targets.is_empty():
				continue
			var t: Combatant = _pick_target(actor, action, targets)
			var sc: float = _score(actor, action, t)
			if sc > best_score:
				best_score = sc
				best = {"rank": int(r), "score": sc, "action": action}
	actor.rank = orig
	return best


func _can_use(actor: Combatant, action: Dictionary) -> bool:
	if int(action.launch_mask) > 0 and (int(action.launch_mask) & (1 << actor.rank)) == 0:
		return false
	if int(action.per_battle_limit) > 0:
		if int(actor.per_battle_uses.get(action.id, 0)) >= int(action.per_battle_limit):
			return false
	return true


func _legal_targets(actor: Combatant, action: Dictionary) -> Array:
	# 敌我由 target 字段的 `@` 前缀决定，不是由有没有 heal 决定——
	# 「鼓舞」「信仰壁垒」这类纯增益技能的 heal 是 0，但目标仍是友方。
	var friendly: bool = bool(action.friendly) or float(action.heal) > 0.0

	# 纯功能技（无攻击无治疗、也不是给友方的）：只作用于自己。
	#
	# 这里原来少了 `friendly` 这一项。后果很隐蔽：守护技能（atk=0, heal=0,
	# target="@1234"）全被归进「自身增益」，目标池永远是 [自己]，
	# 于是"守护"只能守自己——而守护自己不产生任何重定向，等于没实现。
	var pure_self: bool = float(action.atk) <= 0.0 and float(action.heal) <= 0.0 and not friendly
	if pure_self:
		return [actor]

	var own: Array = party if actor.side == Combatant.SIDE_PARTY else enemies
	var foe: Array = enemies if actor.side == Combatant.SIDE_PARTY else party
	var pool: Array = living(own if friendly else foe)

	var mask: int = int(action.target_mask)
	var is_guard: bool = bool(action.get("is_guard", false))
	var out: Array = []
	for u in pool:
		# 守护不能守自己：数据里 target 是 @1234（含自己所在的位置），
		# 但「我保护我自己」既没有意义，也会让 AI 在没人可守时白占一回合。
		if is_guard and u == actor:
			continue
		if mask == 0 or (mask & (1 << u.rank)) != 0:
			out.append(u)
	if out.is_empty() and bool(action.self_target_valid):
		out.append(actor)
	return out


func _pick_target(actor: Combatant, action: Dictionary, targets: Array) -> Combatant:
	var best: Combatant = targets[0]
	var best_score: float = -INF
	for t in targets:
		var s: float = _score(actor, action, t)
		if s > best_score:
			best_score = s
			best = t
	return best


## 打分：期望伤害为主，治疗按缺失血量折算。
## 刻意保持简单可解释——它应该是可替换的，而不是黑箱。
func _score(actor: Combatant, action: Dictionary, target: Combatant) -> float:
	# 召唤值先算：它和命中率无关，也不属于任何一条下面的分支。
	# 每个 return 都要带上它——漏掉任何一条，那个分支里的召唤技就永远 0 分。
	var summon_bonus: float = _eval_summon(action, actor)

	var heal: float = float(action.heal)
	if heal > 0.0:
		var missing: float = 1.0 - target.hp_ratio()
		# 满血治疗没有意义，压到接近 0，避免 AI 在全员满血时还在刷治疗
		if missing <= 0.0:
			return 0.05 + summon_bonus
		return heal * (0.2 + missing * 1.6) + summon_bonus

	# 守护：价值来自「队友接下来会挨的那一下」。
	# 满血队友只值 2 分（比任何攻击都低），残血队友值 5~8 分——
	# 这条曲线决定了 AI 是「开打就守」还是「快死了才守」，前者会浪费半场行动。
	if bool(action.get("is_guard", false)):
		# 守护 + 召唤合体的技能是存在的（brigand_sapper 的 sapper_guard），
		# 所以这里不能直接 return 0.0 丢掉召唤值。
		if target == actor:
			return summon_bonus
		if guardian_of(target.uid) != null:
			return summon_bonus     # 已经有人在守，再来一个只是抢占关系
		var miss: float = 1.0 - target.hp_ratio()
		var gs: float = 2.0 + miss * 6.0
		# 自己也快死了就别去挡刀：守护是拿自己的血换队友的血，
		# 一个残血的人去挡，通常等于把两个人的死门叠在一起。
		if actor.hp_ratio() < 0.35:
			gs *= 0.5
		return gs + summon_bonus

	var spec: Dictionary = build_spec(actor, action, target)
	var dmg: float = DamageFormula.expected_damage(spec)
	var hit: float = DamageFormula.hit_chance(
		float(spec["acc"]), float(spec["dodge"]), db.rules.cutoff_miss, db.rules.cutoff_hit)

	# 纯功能技（自身增益之类）没有伤害，给一个低分让它只在没别的选择时出场
	if float(action.atk) <= 0.0 and float(action.dmg_mod) == 0.0 and (action.dmg_range as Array).is_empty():
		return 1.0 + summon_bonus

	# 附带效果的价值也必须乘命中率，否则低命中高控制技能会被严重高估
	var bonus: float = 0.0
	for en in action.effects:
		var e: Dictionary = db.effect(str(en))
		var base_chance: float = float(e.get("chance", 1.0))
		if e.has("stun"):
			var success: float = maxf(0.0, base_chance - target.resistance("stun"))
			bonus += 3.0 * success
		if e.has("riposte"):
			# 反击是姿态，不是一次伤害：期望值 ≈ 持续回合数 × 每回合被打一次的收益。
			#
			# 乘上数据给的反击伤害倍率（0 级 0.6、4 级 0.75）是必须的：
			# 不乘的话，低等级反击会被估成和高等级一样值，AI 就会在
			# 「反击只有六成伤害」的前期放弃平砍去摆姿态——实测让平均轮数从
			# 4.10 涨到 4.31，而反击一次都没触发。数值来自 effects.json，
			# 不来自这里的常数，所以换数值包时会跟着变。
			var rmult: float = 1.0 + float(e.get("damage_low_multiply", 0.0))
			bonus += float(e.get("duration", 1)) * 0.3 * rmult
		if e.has("stress"):
			bonus += float(e["stress"]) * 0.35 * base_chance
		if e.has("dotBleed") or e.has("dotPoison"):
			var amt: float = float(e.get("dotBleed", e.get("dotPoison", 0)))
			var resist: float = target.resistance("bleed" if e.has("dotBleed") else "poison")
			bonus += amt * float(e.get("duration", 1)) * 0.6 * base_chance * (1.0 - resist)
		# —— 位移（M11）——
		#
		# 这段是 M11 的核心。数据从 M0 就有 46 个带位移的怪物技能、
		# 解析层从 M9 就能算出 move，但**怪物一次都没用过 push/pull**——
		# 因为评分函数不认识位移，带位移的技能永远输给同伤害但附带压力的技能。
		# 也就是说「怪物不会推人」的真正原因是估值缺失，不是数据缺失。
		#
		# 价值按**实际能挪几格**算，不是数据里写的格数：一个已经在 4 号位的
		# 人被 push 2 其实是纹丝不动，给它记 2 格的分会让 AI 一直去推边角。
		if move_value_enabled and (e.has("push") or e.has("pull")):
			var push_delta: int = int(e.get("push", 0)) - int(e.get("pull", 0))
			var team: Array = party if target.side == Combatant.SIDE_PARTY else enemies
			var land: int = clampi(target.rank + push_delta, 0, team.size() - 1)
			var real_ranks: int = absi(land - target.rank)
			if real_ranks > 0:
				bonus += (MOVE_VALUE_PER_RANK * float(real_ranks)
					* (1.0 - target.resistance("move")) * base_chance)
		if move_value_enabled and (e.has("shuffletarget") or e.has("shuffleparty")):
			# 洗位不保证把人送到坏位置，所以它值的是「打乱」而不是「安置」，
			# 用固定值。同样要乘「洗得动」的概率。
			var team2: Array = party if target.side == Combatant.SIDE_PARTY else enemies
			if living(team2).size() >= 2:
				bonus += SHUFFLE_VALUE * (1.0 - target.resistance("move")) * base_chance
	bonus *= hit

	var overkill: float = 0.0
	if dmg > float(target.hp):
		overkill = (dmg - float(target.hp)) * 0.15
	# summon_bonus 加在 `bonus *= hit` 之后：数据里 59 条召唤效果全是
	# on_hit / on_miss 双 true，也就是命中与否都会召唤。乘命中率会让
	# 低命中的召唤者永远不去召唤，而它实际照样召得出来。
	return dmg * hit + bonus + summon_bonus - overkill


## 召唤的估值。返回 0 表示「现在召不出来，别选它」。
##
## 「能不能召出来」必须和 _consume_summon_effect / summon_slot 用同一套判定，
## 否则 AI 会反复选一个注定失败的动作，白占回合——这种 bug 不报错，
## 表现只是「这只怪明明有技能却一直空过」。
func _eval_summon(action: Dictionary, actor: Combatant) -> float:
	# 实现关掉时估值必须一起归零。否则 AI 会去选一个「实装了但会被丢弃」
	# 的技能，表现成空过——那样 --no-summon 测到的就不是 M11 行为，
	# 而是「一个更笨的 AI」，对照立刻失去意义。
	if not summon_enabled or not summon_value_enabled:
		return 0.0
	var info: Dictionary = action.get("summon", {})
	if info.is_empty():
		return 0.0
	# 阵营总量闸。和 _consume_summon_effect 用同一个计数，
	# 否则 AI 会去做一件必然被拒的事。
	var budget: int = 1 << 20
	if summon_default_limit_enabled:
		budget = MAX_SUMMONED_PER_BATTLE - _summoned_total
		if budget <= 0:
			return 0.0
	var ids: Array = info.get("ids", [])
	var limits: Array = info.get("limits", [])
	var erase: bool = bool(info.get("erase", false))
	var used: Dictionary = _summon_used.get(str(action.id), {})

	var total: float = 0.0
	var n_ok: int = 0
	for i in ids.size():
		var mid: String = str(ids[i])
		if erase and used.has(mid):
			continue
		# 上限判定必须和 _pick_summon_index 完全一致。不一致的后果不是报错，
		# 而是 AI 反复选一个注定被拒的技能，表现成「这只怪有技能却在空过」。
		var lim: int = int(limits[i]) if i < limits.size() else 0
		if lim <= 0 and summon_default_limit_enabled:
			lim = DEFAULT_SUMMON_LIMIT
		if lim > 0 and summon_count(mid, actor.side) >= lim:
			continue
		total += _summon_unit_value(mid)
		n_ok += 1
	if n_ok == 0:
		return 0.0

	# 还能放几个：尸体虽然占位，但 summon_slot 会让它让位，
	# 所以「剩余容量」= 4 - 活着的人数，和阵型长度无关。
	var arr: Array = party if actor.side == Combatant.SIDE_PARTY else enemies
	var room: int = MAX_SLOTS - living(arr).size()
	if room <= 0:
		return 0.0
	var n: int = mini(int(info.get("count", 1)), room)
	n = mini(n, budget)
	return (total / float(n_ok)) * float(n) * SUMMON_DISCOUNT


## 一个召唤物值多少分。按血量折算：hp 12 ≈ 4.5 分（约一次平砍），
## hp 40 的坦克 ≈ 11 分（值得为它放弃一回合输出）。
func _summon_unit_value(monster_id: String) -> float:
	var b: Dictionary = db.monster_base(monster_id)
	if b.is_empty():
		return SUMMON_VALUE_BASE
	var hp: float = float(b.get("hp_max", 10))
	return SUMMON_VALUE_BASE + hp / SUMMON_VALUE_HP_DIV


# ============================================================
# 单次攻击结算
# ============================================================

## 构造伤害结算输入。公开以便单测直接验证「某个技能打某个目标应该多少伤害」。
func build_spec(actor: Combatant, action: Dictionary, target: Combatant) -> Dictionary:
	var base_low: float = actor.base_dmg_low
	var base_high: float = actor.base_dmg_high
	var r: Array = action.dmg_range
	if r.size() >= 2:
		base_low = float(r[0])
		base_high = float(r[1])

	# 反击的伤害折扣。数据把它写在 riposte 的 damage_low_multiply 里（负值），
	# 所以这里乘的是「1 + 那个负数」。其它技能没有这个键，取 1.0 即无影响。
	var extra: float = float(action.get("dmg_mult_extra", 1.0))
	if absf(extra - 1.0) > 0.0001:
		base_low *= extra
		base_high *= extra

	# 光照/环境修正。只影响「谁打谁」的方向，不改变个体面板——
	# 这样同一场战斗换光照，个体的 speed()/dodge() 读数仍然可比。
	var acc_add: float = 0.0
	var crit_add: float = 0.0
	var dodge_add: float = 0.0
	if actor.side == Combatant.SIDE_ENEMY:
		var md: float = 1.0 + float(env.get("monster_dmg", 0.0))
		base_low *= md
		base_high *= md
		acc_add += float(env.get("monster_acc", 0.0))
		crit_add += float(env.get("monster_crit", 0.0))
	else:
		crit_add += float(env.get("player_crit", 0.0))
	if target.is_hero:
		dodge_add = float(env.get("player_dodge", 0.0))

	var am: Dictionary = EffectResolver.collect_attack_mods(db, action.effects, actor, target)
	var mods: Array = [float(action.dmg_mod), float(am.damage_mod)]

	return {
		"base_low": base_low,
		"base_high": base_high,
		"acc": actor.acc() + float(action.atk) + float(am.acc) + acc_add,
		"dodge": target.dodge() + dodge_add,
		"crit": actor.crit() + float(action.crit) + float(am.crit) + crit_add,
		"crit_mult": actor.crit_mult_value,
		"crit_valid": bool(action.crit_valid),
		"prot": target.prot(),
		"mods": mods,
		"dmg_mult_buffs": actor.damage_mult("low"),
		"dmg_taken_mod": target.damage_taken_mod(),
		"ignore_prot": bool(action.ignore_prot),
		"cutoff_hit": db.rules.cutoff_hit,
		"cutoff_miss": db.rules.cutoff_miss,
		"attack_mods": am,
	}


## 结算一批 effect，并把其中的位移真正作用到阵型上。
##
## 只写事件是不够的：`launch_mask` / `target_mask` 读的是 rank，
## rank 不变的话「推开了」就只是日志里的一句话，技能限制完全不受影响。
func apply_effects(action: Dictionary, actor: Combatant, target: Combatant, ctx: Dictionary) -> void:
	for r in EffectResolver.apply(db, action.effects, actor, [target], ctx):
		var ev: Dictionary = r.duplicate()
		ev["t"] = "effect"
		_emit(ev)
		# 守护/反击先消费：它们和位移共用同一个结果字典，
		# 所以不能像位移那样写 `if delta == 0: continue` 提前跳过。
		_consume_guard_effects(ev, actor)
		_consume_riposte_effect(ev)
		# 召唤也在这里消费，理由同守护：它的目标写的是 performer（自己），
		# 但如果 performer 万一已经不在了，下面那句 `u == null: continue`
		# 会把它整个跳过。放在守卫之前，召唤不依赖目标是否可解析。
		_consume_summon_effect(ev, actor, action)

		var u: Combatant = unit_by_uid(int(ev.get("target", -1)))
		if u == null:
			continue

		# 洗位（M11）。必须排在 `delta == 0: continue` 之前——
		# 洗位结果里没有 move 字段，走原来那条路会被直接跳过。
		var shuf: String = str(ev.get("shuffle", ""))
		if shuf == "team":
			for mv2 in shuffle_team(u.side):
				_emit({"t": "move", "actor": int(mv2["uid"]), "from": int(mv2["from"]),
					"to": int(mv2["to"]), "skill": action.id, "shuffle": true})
			continue
		if shuf == "target":
			var mv3: Dictionary = shuffle_unit(u)
			if not mv3.is_empty():
				_emit({"t": "move", "actor": u.uid, "from": int(mv3["from"]),
					"to": int(mv3["to"]), "skill": action.id, "shuffle": true})
			continue

		var delta: int = int(ev.get("move", 0))
		if delta == 0:
			continue
		var mv: Dictionary = move_unit(u, delta)
		if not mv.is_empty():
			_emit({"t": "move", "actor": u.uid, "from": int(mv["from"]),
				"to": int(mv["to"]), "skill": action.id})


## 把 effect 结算出的守护意图落到关系表上。
##
## 「清两条 → 建一条」的顺序就是数据里的顺序（Clear Guard Performer、
## Clear Guard Target 排在 MAA Guard 1 前面）。不要自作聪明调换：
## 先建后清会把刚建立的守护立刻删掉，而且不会报错，只是守护永远失效。
func _consume_guard_effects(ev: Dictionary, actor: Combatant) -> void:
	var t: Combatant = unit_by_uid(int(ev.get("target", -1)))
	if t == null:
		return
	if bool(ev.get("clear_guarding", false)):
		drop_guard_by(t.uid)
	if bool(ev.get("clear_guarded", false)):
		drop_guard_on(t.uid)
	if bool(ev.get("guard", false)):
		set_guard(actor.uid, t.uid, int(ev.get("guard_turns", 1)))
		_emit({"t": "guard_up", "actor": actor.uid, "target": t.uid,
			"turns": int(ev.get("guard_turns", 1))})
	if bool(ev.get("swap", false)):
		var ra: int = actor.rank
		var rb: int = t.rank
		if swap_units(actor, t):
			_emit({"t": "swap", "a": actor.uid, "b": t.uid,
				"a_from": ra, "b_from": rb})


func _consume_riposte_effect(ev: Dictionary) -> void:
	if not bool(ev.get("riposte", false)):
		return
	var t: Combatant = unit_by_uid(int(ev.get("target", -1)))
	if t == null:
		return
	var turns: int = int(ev.get("riposte_turns", 1))
	set_riposte(t.uid, {
		"turns": turns,
		"mult": float(ev.get("riposte_mult", 1.0)),
		"on_hit": float(ev.get("riposte_on_hit", 1.0)),
		"on_miss": float(ev.get("riposte_on_miss", 1.0)),
	})
	_emit({"t": "riposte_up", "actor": t.uid, "turns": turns})


# ============================================================
# 守护 / 反击：查询与关系维护
# ============================================================

## u 正在守护谁（没在守护返回 null）
func guard_target_of(uid: int) -> Combatant:
	var t: int = int(_guards.get(uid, -1))
	return null if t < 0 else unit_by_uid(t)


## 谁在守护 u（没被守护返回 null）
func guardian_of(uid: int) -> Combatant:
	var g: int = int(_guarded.get(uid, -1))
	return null if g < 0 else unit_by_uid(g)


func has_riposte(uid: int) -> bool:
	return not (_riposte.get(uid, {}) as Dictionary).is_empty()


func riposte_turns_left(uid: int) -> int:
	return int((_riposte.get(uid, {}) as Dictionary).get("turns", 0))


## 建立守护。守护者同时只能守一个人，目标同时只能被一个人守——
## 新关系覆盖旧关系，调用方不必自己维护这两条互斥。
func set_guard(guard_uid: int, target_uid: int, turns: int) -> void:
	if guard_uid == target_uid:
		return
	var g: Combatant = unit_by_uid(guard_uid)
	var t: Combatant = unit_by_uid(target_uid)
	if g == null or t == null or g.side != t.side:
		return
	# 死人不能当守护者，也不能被守护。少了这条，「守一个刚死的队友」
	# 会留下一条永远不会被清理的关系，直到回合末才失效。
	if not g.is_alive() or not t.is_alive():
		return
	drop_guard_by(guard_uid)
	drop_guard_on(target_uid)
	_guards[guard_uid] = target_uid
	_guarded[target_uid] = guard_uid
	_guard_left[guard_uid] = maxi(turns, 1)


## 解除「guard_uid 作为守护者」的关系（含对方那一侧的对称记录）
func drop_guard_by(guard_uid: int) -> void:
	if not _guards.has(guard_uid):
		return
	var t: int = int(_guards[guard_uid])
	_guards.erase(guard_uid)
	_guard_left.erase(guard_uid)
	if int(_guarded.get(t, -1)) == guard_uid:
		_guarded.erase(t)


## 解除「target_uid 被守护」的关系
func drop_guard_on(target_uid: int) -> void:
	if not _guarded.has(target_uid):
		return
	var g: int = int(_guarded[target_uid])
	_guarded.erase(target_uid)
	_guards.erase(g)
	_guard_left.erase(g)


func set_riposte(uid: int, st: Dictionary) -> void:
	if unit_by_uid(uid) == null:
		return
	_riposte[uid] = st


## 回合末：守护与反击各自计时。
##
## 守护的四种失效条件必须都在这里判——守护者死了、被守护者死了、
## 有人走了、时间到了。前三种如果不判，就会出现「守护者已阵亡，
## 但攻击仍然打在他身上」这种人已经不在场却还在挨打的局面。
func _tick_guards_and_riposte() -> void:
	for g_uid in (_guards.keys() as Array).duplicate():
		var t_uid: int = int(_guards[g_uid])
		var g: Combatant = unit_by_uid(g_uid)
		var t: Combatant = unit_by_uid(t_uid)
		var left: int = int(_guard_left.get(g_uid, 0)) - 1
		if g == null or t == null or not g.is_alive() or not t.is_alive() or left <= 0:
			drop_guard_by(g_uid)
			_emit({"t": "guard_end", "actor": g_uid, "target": t_uid})
		else:
			_guard_left[g_uid] = left

	for uid in (_riposte.keys() as Array).duplicate():
		var st: Dictionary = _riposte[uid]
		var u: Combatant = unit_by_uid(uid)
		st["turns"] = int(st.get("turns", 0)) - 1
		if int(st["turns"]) <= 0 or u == null or not u.is_alive():
			_riposte.erase(uid)
			_emit({"t": "riposte_end", "actor": uid})


func _resolve_action(actor: Combatant, action: Dictionary, target: Combatant) -> void:
	var ctx: Dictionary = {"rng": rng, "all_units": all_units(),
		"move_resist_enabled": move_resist_enabled}

	# 守护重定向必须在一切结算之前发生。放到算伤害之后，面板显示的是
	# 「原本要挨打的人」，实际扣血的却是守护者——日志和血条会对不上。
	var actual: Combatant = guard_redirect(actor, action, target)
	if actual != target:
		_emit({"t": "guard", "actor": actor.uid, "target": target.uid, "guard": actual.uid,
			"skill": action.id})
		target = actual

	# 纯治疗技能：不走伤害管线
	if float(action.heal) > 0.0:
		var hr: Array = action.heal_range
		var amount: int = int(action.heal)
		if hr.size() >= 2:
			amount = rng.next_int_range(int(hr[0]), int(hr[1]))
		# 治疗配额用尽后不是「不能点」，而是「点了没效果」——
		# 这样 AI 与玩家共用同一套决策代码，不必额外教 AI 认识配额。
		var blocked: bool = heal_charges == 0
		var healed: int = 0
		if not blocked:
			healed = target.heal(amount)
			if heal_charges > 0 and healed > 0:
				heal_charges -= 1
				heals_used += 1
		_emit({"t": "heal", "actor": actor.uid, "target": target.uid,
			"amount": healed, "skill": action.id, "blocked": blocked})
		ctx["hit"] = true
		apply_effects(action, actor, target, ctx)
		_settle_dd_recovery([target])
		return

	# 无攻击判定的功能技（自身增益、姿态等）：只结算效果，绝不走伤害管线——
	# 否则会把武器伤害套上去，凭空打出一发伤害。
	#
	# is_attack 是给反击留的唯一例外：反击用的虚拟技能 atk=0（不该给它额外命中加成，
	# 它就该用英雄本来的命中率），但它是实打实的一刀。只认 atk 就会把反击
	# 判成姿态技，于是「还手」只留下一条日志，一滴血都不掉——而且是静默的。
	if float(action.atk) <= 0.0 and not bool(action.get("is_attack", false)):
		_emit({"t": "utility", "actor": actor.uid, "target": target.uid, "skill": action.id})
		ctx["hit"] = true
		apply_effects(action, actor, target, ctx)
		_settle_dd_recovery([target])
		return

	var spec: Dictionary = build_spec(actor, action, target)
	var result: Dictionary = DamageFormula.resolve_attack(spec, rng)

	if not bool(result["hit"]):
		actor.consecutive_misses += 1
		_emit({"t": "miss", "actor": actor.uid, "target": target.uid,
			"skill": action.id, "chance": result["hit_chance"]})
		ctx["hit"] = false
		EffectResolver.apply(db, action.effects, actor, [target], ctx)
		_try_riposte(target, actor, false)
		return

	actor.consecutive_misses = 0

	var dmg: int = int(result["damage"])
	var damaged: Dictionary = {"damage": 0, "died": false, "deaths_door": false}
	if dmg > 0:
		damaged = target.take_damage(dmg, rng.next_float())
		if bool(damaged.get("deaths_door", false)):
			target.enter_deaths_door(db)

	_emit({
		"t": "attack", "actor": actor.uid, "target": target.uid, "skill": action.id,
		"hit": true, "crit": bool(result["crit"]), "damage": int(damaged.get("damage", 0)),
		# gross = 扣血条之前的最终伤害（已乘修正、已减护甲）；
		# 与 damage 之差才是真正的溢出，用 raw 算会把护甲减免误计成浪费。
		"gross": int(result["damage"]),
		"raw": result["raw"], "mult": result["mult"],
		"deaths_door": bool(damaged.get("deaths_door", false)),
		"died": bool(damaged.get("died", false)),
		"deathblow_resisted": bool(damaged.get("resisted", false)),
	})

	if bool(result["crit"]):
		_apply_crit_stress(actor, target)

	ctx["hit"] = true
	apply_effects(action, actor, target, ctx)

	_settle_dd_recovery([target])

	if target.dead:
		_emit({"t": "death", "actor": target.uid, "hero": target.is_hero})

	# 反击放在最后：被打的人可能已经死了，死人不还手（_try_riposte 里判）。
	_try_riposte(target, actor, true)


# ============================================================
# 守护 / 反击（M10）
# ============================================================

## 这一击到底打在谁身上。
##
## 守护的语义只有一句：**打向被守护者的敌方单体攻击，改由守护者承受**。
## 但有三条例外，每一条都对应一个具体问题：
##
##   1. 友方技能不重定向 —— 治疗被守护者不该治到守护者身上。
##   2. AOE 不重定向 —— 这是本项目的取舍，不是 DD1 原样。
##      一个守护者替四个人吃掉整轮 AOE，等于把守护的收益翻了四倍；
##      而且 AI 完全无法预期这件事，前排会突然变成必死位。
##   3. 带 ignore_guard 的技能穿透 —— 数据早就有这个字段
##      （combatant.build_actions 一直在解析它），只是一直没人读。
func guard_redirect(actor: Combatant, action: Dictionary, target: Combatant) -> Combatant:
	if not guard_enabled or actor == null or target == null:
		return target
	if actor.side == target.side:
		return target
	if bool(action.get("target_aoe", false)):
		return target
	if bool(action.get("ignore_guard", false)):
		return target
	var g_uid: int = int(_guarded.get(target.uid, -1))
	if g_uid < 0:
		return target
	var g: Combatant = unit_by_uid(g_uid)
	# 守护者死了/不在了：关系当场作废，不能让它变成一个永久免伤罩
	if g == null or not g.is_alive():
		drop_guard_on(target.uid)
		return target
	return g


## 受击还手。
##
## 触发点在 _resolve_action 的四条出口上（命中 / 未命中），而不是在伤害结算里：
## 未命中也要还手，这是数据写明的（riposte_on_miss_chance_add = 1.0）——
## 「他扑空了，正好露出破绽」。
##
## _riposte_depth 是防止 A 反击 B、B 再反击 A 的无限递归。
## 现在怪物身上没有任何 riposte，所以这条防线看起来多余；
## 但一旦给怪物接上同类效果，没有它就会直接栈溢出。
func _try_riposte(defender: Combatant, attacker: Combatant, hit: bool) -> void:
	if not riposte_enabled or _riposte_depth > 0:
		return
	if defender == null or attacker == null or defender.side == attacker.side:
		return
	var st: Dictionary = _riposte.get(defender.uid, {})
	if st.is_empty():
		return
	if not defender.is_alive() or not attacker.is_alive():
		return
	var chance: float = float(st.get("on_hit" if hit else "on_miss", 1.0))
	if chance <= 0.0 or not rng.chance(chance):
		return
	_riposte_depth += 1
	_emit({"t": "riposte", "actor": defender.uid, "target": attacker.uid, "hit": hit})
	_resolve_action(defender, riposte_action(st), attacker)
	_riposte_depth -= 1


## 反击用的虚拟技能。它不属于任何英雄的技能表——是「用武器普通攻击一下」，
## 所以 dmg_range 留空（走 build_spec 里的 base_dmg），效果列表也留空。
func riposte_action(st: Dictionary) -> Dictionary:
	return {
		"id": "riposte", "type": "melee", "level": 0,
		"atk": 0.0, "dmg_mod": 0.0, "dmg_range": [], "crit": 0.0,
		"launch_mask": 0, "target_mask": 0, "target_aoe": false,
		"friendly": false, "effects": [], "crit_valid": true,
		"ignore_prot": false,
		# 反击本身就是「被守护挡下来之后仍然还手」的那一手，
		# 再被守护重定向一次会变成「守护者替攻击者挨自己人一刀」。
		"ignore_guard": true,
		"heal": 0.0, "heal_range": [0.0, 0.0], "move": [],
		"per_turn_limit": 0, "per_battle_limit": 0,
		"is_stall_invalidating": false, "is_continue_turn": false,
		"self_target_valid": false,
		"dmg_mult_extra": float(st.get("mult", 1.0)),
		"is_attack": true,
		"is_guard": false, "is_riposte": false,
	}


## 从死门被治疗回来：换成「恢复期」减益。
## 不补这一步的话，死门就是完全免费的——救回来的人下一场还是满状态，
## 那死门就只剩戏剧效果，没有代价。
func _settle_dd_recovery(targets: Array) -> void:
	for t in targets:
		if t.recovered_from_dd:
			t.leave_deaths_door(db, t.heart_attacked)
			t.heart_attacked = false
			_emit({"t": "recovered", "actor": t.uid})


# ============================================================
# 压力阈值：崩溃 / 美德 / 心脏骤停
# ============================================================
#
# 这三件事原先一件都没做（M1 记为「已知未实现」），后果是压力只是一个
# 会涨的数字：涨到 200 也不会有任何事发生，于是「压力管理」这个核心玩法
# 在系统里根本不存在。M3 要补的正是这一段。

func check_stress_breaks() -> void:
	for u in party:
		if not u.is_alive():
			continue
		if u.stress >= heart_attack_at:
			_heart_attack(u)
		elif u.stress >= stress_break_at and not u.broken():
			_roll_break(u)


## 100 压力：崩溃检定。数据给的是 75% 崩溃 / 25% 美德
## （rules.affliction_base_onset_chance 与 affliction_critical_success_chance）。
func _roll_break(u: Combatant) -> void:
	var onset: float = db.rules.affliction_onset_chance
	if rng.chance(onset):
		var kinds: Array = db.affliction_kinds()
		if kinds.is_empty():
			kinds = ["fearful"]
		var k: String = str(kinds[rng.next_int_range(0, kinds.size() - 1)])
		u.apply_affliction(db, k)
		_emit({"t": "affliction", "target": u.uid, "kind": k, "stress": u.stress})
	else:
		var vkinds: Array = db.virtue_kinds()
		if vkinds.is_empty():
			vkinds = ["stalwart"]
		var vk: String = str(vkinds[rng.next_int_range(0, vkinds.size() - 1)])
		u.apply_virtue(db, vk)
		# 美德是「顶住了」：减压一次（data: stress_affliction_critically_resisted = 45）
		var before: float = u.stress
		u.stress = clampf(u.stress - db.rules.affliction_critically_resisted, 0.0, 200.0)
		_emit({"t": "virtue", "target": u.uid, "kind": vk,
			"relief": u.stress - before})


## 200 压力：心脏骤停。已在死门上则直接死亡。
func _heart_attack(u: Combatant) -> void:
	_emit({"t": "heart_attack", "target": u.uid})
	u.stress = stress_break_at
	if u.at_deaths_door:
		u.dead = true
		u.hp = 0
		_emit({"t": "death", "actor": u.uid, "hero": true, "cause": "heart_attack"})
		return
	u.hp = 0
	u.heart_attacked = true
	u.remove_buff_ids(u.dd_buff_ids)
	u.dd_buff_ids = []
	u.enter_deaths_door(db)
	_emit({"t": "deaths_door", "actor": u.uid, "cause": "heart_attack"})


## 暴击的压力后果：怪物暴击让被打的英雄加压、队友受牵连；
## 英雄暴击反而给自己和队友减压。这个不对称是 DD1 压迫感的主要来源之一。
func _apply_crit_stress(attacker: Combatant, target: Combatant) -> void:
	if attacker.side == Combatant.SIDE_ENEMY:
		if target.is_hero and target.is_alive():
			var d: float = target.add_stress(db.rules.monster_crit_stress)
			_emit({"t": "stress", "target": target.uid, "delta": d, "source": "monster_crit"})
		for mate in living(party):
			if mate == target:
				continue
			if rng.chance(db.rules.monster_crit_companion_chance):
				var d2: float = mate.add_stress(db.rules.monster_crit_companion_stress)
				_emit({"t": "stress", "target": mate.uid, "delta": d2, "source": "monster_crit_ally"})
	else:
		if target.is_hero and target.is_alive():
			var d3: float = target.add_stress(-db.rules.player_crit_relief)
			_emit({"t": "stress", "target": target.uid, "delta": d3, "source": "hero_crit"})
		for mate in living(party):
			if mate == target:
				continue
			if rng.chance(db.rules.player_crit_companion_chance):
				var d4: float = mate.add_stress(-db.rules.player_crit_companion_relief)
				_emit({"t": "stress", "target": mate.uid, "delta": d4, "source": "hero_crit_ally"})

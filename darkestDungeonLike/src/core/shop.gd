class_name Shop
extends RefCounted
## 城镇经济：补给采购 + 饰品买卖。
##
## 这一层补的是 M15 留下的两个洞：金币只有「升级」一个出口，而
## `trinkets.json` 的 `price`、`inventory.json` 的 `purchase_gold_value`
## 全都读进来了却没地方用。
##
## ## 三条价格从哪来
##
##   * 补给买价 / 卖价 / 堆叠上限 —— **全部来自 `inventory.json`**，不拍数字。
##     10 种补给都带 `purchase_gold_value` 与 `sell_gold_value`。
##   * 饰品买价 —— **来自 `trinkets.json` 的 `price`**，按稀有度规整地分成
##     5000 / 7500 / 10000 / 15000 / 25000 / 50000 六档。
##   * 饰品卖价 —— **数据里没有**。这里取买价的 10%，理由见 `SELL_RATIO`。
##
## ## 为什么补给不进元层仓库
##
## DD1 的补给是「这趟带下去的」，回城不结余。做成元层库存会多出一堆
## 边界（囤货、跨趟折损、上限共用什么），而它换不来任何决策——
## 真正的决策是「这趟带几根火把」，那发生在出发前。
## 所以补给只在出发准备屏买一次，买完直接进 `Expedition.supplies`。
##
## ## 上架为什么必须用派生 rng
##
## 上架是随机抽的，但它和地图、掉落、奇物一样，只会「偶然」被调用。
## 只要它碰了主序列，所有 bench 数字同时作废（M11/M13/M15 各踩过一次）。
## 这里接受一个外部传入的 `DdRng`，**由调用方用独立种子构造**，
## 而不是在这里偷偷 new 一个——那会让「同种子同结果」变成不可验证的承诺。

## 饰品卖出价＝买价的这个比例。
##
## 数据里补给是 10%（火把 75 买 / 5 卖、铲子 250 / 25），饰品没有自己的
## 卖价字段。跟着补给用 10%，是**最少假设**的选择：不发明新数字，
## 也让「卖饰品」只承担清仓职能，不变成赚钱手段。
##
## 如果哪天想让卖饰品更有价值，只改这一个常量，并重跑 bench 的
## 「打一趟卖一趟」对照。
const SELL_RATIO: float = 0.10

## 上架件数。DD1 的饰品商店是 6 格。
const STOCK_SIZE: int = 6

## 上架稀有度权重。数值取自掉落表的相对频率量级（common 最多、
## ancestral 极少），但商店比地牢更「友好」一点——不然六格全是普通件，
## 商店就没有存在意义。
const RARITY_WEIGHTS: Dictionary = {
	"very_common": 30,
	"common": 26,
	"uncommon": 18,
	"rare": 14,
	"very_rare": 8,
	"ancestral": 4,
}

## 补给顺序与展示顺序一致。`food` 是 provision（id 为空的那条），
## 单独处理——它的 id 在数据里是空字符串。
const FOOD_KEY: String = "food"

var supply_defs: Dictionary = {}   ## id -> {buy, sell, limit}
var food_def: Dictionary = {}      ## provision 那条的 {buy, sell, limit}
var trinket_lib: TrinketLib = null
var stats: Dictionary = {}


func load_from(base: String = "res://data", tl: TrinketLib = null) -> bool:
	supply_defs.clear()
	food_def = {}
	trinket_lib = tl

	var path: String = _resolve(base, "inventory.json")
	if path.is_empty():
		push_warning("Shop: 找不到 inventory.json")
		return false
	var parsed: Variant = JSON.parse_string(FileAccess.get_file_as_string(path))
	if parsed == null or typeof(parsed) != TYPE_ARRAY:
		push_warning("Shop: %s 解析失败" % path)
		return false

	for e in (parsed as Array):
		if not (e is Dictionary):
			continue
		var t: String = str(e.get("type", ""))
		var id: String = str(e.get("id", ""))
		# provision 单独处理：数据里**所有** provision 的 id 都是空串
		# （一条是容器定义 max_slots=14，一条才是食物本身），
		# 靠 id 判断不出来，只能靠 base_stack_limit 分辨。见下面的回退段。
		if t == "provision":
			continue
		if t != "supply":
			continue
		if id.is_empty():
			continue
		if int(e.get("purchase_gold_value", 0)) <= 0 and int(e.get("sell_gold_value", 0)) <= 0:
			# firewood / dog_treats 的买卖价都是 0：它们不是商品
			# （柴火来自营地、狗饼干只对猎犬有用）。收进来但标成非卖品。
			var d0: Dictionary = _def_of(e)
			d0["tradable"] = false
			supply_defs[id] = d0
			continue
		supply_defs[id] = _def_of(e)

	# 食物：两条 provision 里，只有带 `base_stack_limit` 的那条是商品，
	# 另一条是容器定义（`max_slots: 14`）。用「有没有堆叠上限」区分，
	# 因为 id 两边都是空串、类型也一样。
	for e2 in (parsed as Array):
		if e2 is Dictionary and str(e2.get("type", "")) == "provision" \
				and int(e2.get("base_stack_limit", 0)) > 0:
			food_def = _def_of(e2)
			break

	stats = _compute_stats()
	return not supply_defs.is_empty()


func _def_of(e: Dictionary) -> Dictionary:
	return {
		"id": str(e.get("id", "")),
		"buy": int(e.get("purchase_gold_value", 0)),
		"sell": int(e.get("sell_gold_value", 0)),
		"limit": int(e.get("base_stack_limit", 0)),
		"tradable": true,
	}


func _resolve(base: String, name: String) -> String:
	var p: String = base + "/" + name
	if FileAccess.file_exists(p):
		return p
	var alt: String = "res://data/" + name
	return alt if FileAccess.file_exists(alt) else ""


func _compute_stats() -> Dictionary:
	var out: Dictionary = {
		"supplies": 0, "tradable": 0, "food_buy": 0, "food_limit": 0,
		"cheapest_trinket": 0, "priciest_trinket": 0, "stock_pool": 0,
	}
	var cheapest: int = 0
	var priciest: int = 0
	for id in supply_defs.keys():
		out["supplies"] = int(out["supplies"]) + 1
		if bool((supply_defs[id] as Dictionary).get("tradable", true)):
			out["tradable"] = int(out["tradable"]) + 1
	out["food_buy"] = int(food_def.get("buy", 0))
	out["food_limit"] = int(food_def.get("limit", 0))
	if trinket_lib != null and trinket_lib.is_loaded():
		var pool: int = 0
		for r in RARITY_WEIGHTS.keys():
			var ids: Array = trinket_lib.pool_for_rarity(str(r))
			pool += ids.size()
			for id2 in ids:
				var p: int = trinket_lib.price_of(str(id2))
				if p <= 1:
					continue
				if cheapest == 0 or p < cheapest:
					cheapest = p
				if p > priciest:
					priciest = p
		out["stock_pool"] = pool
	out["cheapest_trinket"] = cheapest
	out["priciest_trinket"] = priciest
	return out


# ============================================================
# 补给
# ============================================================

## 可买补给列表（含食物），顺序固定，便于界面与复现。
func supply_ids() -> Array:
	var out: Array = []
	for id in supply_defs.keys():
		if bool((supply_defs[id] as Dictionary).get("tradable", true)):
			out.append(str(id))
	out.sort()
	if not food_def.is_empty():
		out.push_front(FOOD_KEY)
	return out


func supply_def(id: String) -> Dictionary:
	if id == FOOD_KEY:
		return food_def
	return supply_defs.get(id, {})


func supply_buy(id: String) -> int:
	return int(supply_def(id).get("buy", 0))


func supply_sell(id: String) -> int:
	return int(supply_def(id).get("sell", 0))


func supply_limit(id: String) -> int:
	return int(supply_def(id).get("limit", 0))


func food_buy() -> int:
	return int(food_def.get("buy", 0))


## 一套补给的总价。`pack` 形如 {"torch": 4, "shovel": 1, "food": 2}。
func pack_cost(pack: Dictionary) -> int:
	var total: int = 0
	for k in pack.keys():
		total += supply_buy(str(k)) * maxi(0, int(pack[k]))
	return total


# ============================================================
# 饰品
# ============================================================

## 卖出价。数据里没有饰品的 `sell_gold_value`，见 `SELL_RATIO` 的说明。
func trinket_sell_price(id: String) -> int:
	if trinket_lib == null or not trinket_lib.is_loaded():
		return 0
	# 特殊渠道件（trophy / crow / darkest_dungeon 等）price 是 0 或 1，
	# 它们是占位价，不是真实价格。卖出去至少给 1 金，避免「卖了个 0」。
	return maxi(1, int(round(float(trinket_lib.price_of(id)) * SELL_RATIO)))


func trinket_buy_price(id: String) -> int:
	if trinket_lib == null or not trinket_lib.is_loaded():
		return 0
	return trinket_lib.price_of(id)


## 能不能买到这件：占位价（<=1）的特殊件不上架，也不该被买。
func can_stock(id: String) -> bool:
	if trinket_lib == null or not trinket_lib.is_loaded():
		return false
	if not trinket_lib.has(id):
		return false
	if trinket_lib.rarity_of(id) == TrinketLib.RARITY_KICKSTARTER:
		return false
	return trinket_lib.price_of(id) > 1


## 按稀有度权重抽一批上架。
##
## `rng` 必须是**调用方用独立种子构造**的——见文件头。
## `exclude` 通常传「仓库里已有的唯一件」：唯一件重复上架没有意义。
func roll_stock(rng: DdRng, count: int = STOCK_SIZE, exclude: Array = []) -> Array:
	var out: Array = []
	if trinket_lib == null or not trinket_lib.is_loaded() or rng == null:
		return out
	var guard: int = 0
	while out.size() < count and guard < count * 40:
		guard += 1
		var rarity: String = _roll_rarity(rng)
		if rarity.is_empty():
			break
		var skip: Array = exclude.duplicate()
		skip.append_array(out)
		var id: String = trinket_lib.pick_for_rarity(rarity, rng, skip)
		if id.is_empty() or not can_stock(id):
			continue
		out.append(id)
	return out


func _roll_rarity(rng: DdRng) -> String:
	var total: int = 0
	for k in RARITY_WEIGHTS.keys():
		total += int(RARITY_WEIGHTS[k])
	if total <= 0:
		return ""
	var roll: int = rng.next_int(total)
	var acc: int = 0
	for k in RARITY_WEIGHTS.keys():
		acc += int(RARITY_WEIGHTS[k])
		if roll < acc:
			return str(k)
	return "very_common"

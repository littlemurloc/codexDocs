class_name TestM66
extends RefCounted
## M66 商店卖补给。
##
## 改动横跨三层（数据 / 规则 / 界面），但真正会**静默出错**的只有两条账：
##
## 1. 商店买一份要当场扣钱，而且库存不能超过这一趟的携带上限
##    （否则能囤 99 根火把，带队下去等于无限光照）。
## 2. 出发时**先扣库存再收钱**。这一条错了不会报任何错，
##    只会在玩家的金币上慢慢体现——「我在商店买了，为什么出发又收一次」。
##
## 第二条的观测点是「报价」和「实扣」必须相等：
## 界面写 1700、实际扣 1925，是最容易发生也最难解释的一类不一致。

const TEST_PATH: String = "user://test_m66_unit.json"


static func run(t: TestLib, db: DdDb) -> void:
	_test_buy(t, db)
	_test_launch_with_stock(t, db)
	_test_save(t, db)
	_cleanup()


# ------------------------------------------------------------
# 1. 商店买入
# ------------------------------------------------------------

static func _test_buy(t: TestLib, db: DdDb) -> void:
	t.section("商店：买补给")
	var c := Campaign.new()
	c.setup_from_cfg(db.campaign_cfg, TEST_PATH)
	c.shop = db.shop
	c.new_game()
	c.gold = 1000

	var r: Dictionary = c.buy_supply("torch", 3)
	t.ok(bool(r.get("ok", false)), "买 3 根火把成功")
	t.eq(int(r.get("cost", 0)), 225, "3 根火把 = 225 金（数据价 75/份）")
	t.eq(c.gold, 775, "金币当场扣掉")
	t.eq(c.supply_stock("torch"), 3, "库存记 3 份")

	# 上限是「这一趟能带多少」，库存也按它卡
	var r2: Dictionary = c.buy_supply("torch", 8)
	t.eq(str(r2.get("reason", "")), "over_limit", "3 + 8 超上限 8，被拒")
	t.eq(c.supply_stock("torch"), 3, "被拒时不加库存")

	c.gold = 10
	var r3: Dictionary = c.buy_supply("shovel", 1)
	t.eq(str(r3.get("reason", "")), "no_gold", "钱不够被拒")
	t.eq(c.supply_stock("shovel"), 0, "钱不够时不加库存")
	t.eq(c.gold, 10, "钱不够时一分不扣")


# ------------------------------------------------------------
# 2. 出发优先用库存
# ------------------------------------------------------------

static func _test_launch_with_stock(t: TestLib, db: DdDb) -> void:
	t.section("出发：先扣库存再收钱")
	var c := Campaign.new()
	c.setup_from_cfg(db.campaign_cfg, TEST_PATH)
	c.shop = db.shop
	c.new_game()
	c.gold = 1000
	c.buy_supply("torch", 3)          # 花 225，库存 3，余额 775

	# 想带 5 根：库存 3 根已经付过钱，只买 2 根
	var res: Dictionary = c.buy_pack_with_stock({"torch": 5})
	t.ok(bool(res.get("ok", false)), "带 5 根火把（库存 3 + 现买 2）")
	t.eq(int(res.get("cost", 0)), 150, "只收 2 根的 150 金")
	t.eq(c.gold, 625, "775 - 150")
	t.eq(c.supply_stock("torch"), 0, "库存被扣光")

	# 报价必须等于实扣：这一条错了，界面和钱包会长期不一致
	c.supplies = {"torch": 2}
	t.eq(c.pack_cost_with_stock({"torch": 4}), 150, "报价扣掉库存的 2 根")
	t.eq(c.pack_cost_with_stock({"torch": 2}), 0, "全用库存 = 0 金")

	# 只用一部分库存时，剩下的还留在库存里
	c.gold = 1000
	var res2: Dictionary = c.buy_pack_with_stock({"torch": 1})
	t.ok(bool(res2.get("ok", false)), "只带 1 根")
	t.eq(int(res2.get("cost", 0)), 0, "1 根全走库存，不收钱")
	t.eq(c.supply_stock("torch"), 1, "剩下的 1 根还在库存里")

	# 超上限仍然要挡（这是「这一趟带多少」，和库存无关）
	var over: Dictionary = c.buy_pack_with_stock({"torch": 9})
	t.eq(str(over.get("reason", "")), "over_limit", "带 9 根超上限")

	# 空包：不该崩，也不该收钱
	var empty: Dictionary = c.buy_pack_with_stock({})
	t.ok(bool(empty.get("ok", false)), "空包可以出发")
	t.eq(int(empty.get("cost", 0)), 0, "空包 0 金")


# ------------------------------------------------------------
# 3. 存档往返
# ------------------------------------------------------------

static func _test_save(t: TestLib, db: DdDb) -> void:
	t.section("存档：补给库存")
	var c := Campaign.new()
	c.setup_from_cfg(db.campaign_cfg, TEST_PATH)
	c.shop = db.shop
	c.new_game()
	c.supplies = {"torch": 2, "food": 1}
	c.save()

	var p := Campaign.new()
	p.setup_from_cfg(db.campaign_cfg, TEST_PATH)
	var loaded: bool = p.load_or_new()
	t.ok(loaded, "读回存档")
	t.eq(p.supply_stock("torch"), 2, "火把库存 2 保留")
	t.eq(p.supply_stock("food"), 1, "口粮库存 1 保留")
	t.eq(p.supply_stock("shovel"), 0, "没买过的仍是 0")

	# 旧档没有 supplies 字段：必须读成空，而不是崩或变成 null
	var old: Dictionary = {"gold": 50, "roster": {}}
	p.from_dict(old)
	t.eq(p.supply_stock("torch"), 0, "旧档读成空库存")


static func _cleanup() -> void:
	var abs_path: String = ProjectSettings.globalize_path(TEST_PATH)
	if FileAccess.file_exists(TEST_PATH):
		DirAccess.remove_absolute(abs_path)

class_name TestShop
extends RefCounted
## M16 城镇经济。
##
## 这一期最容易被做错的三处，各有一组断言：
##
## 1. **先判容量再扣钱**。反过来的话「钱扣了但仓库满了」会变成
##    一件无法申诉的事——玩家只会觉得游戏坏了。
## 2. **买走的货架格子留空**，不往前挤。挤上去会让玩家眼睁睁看着
##    自己没买的那件换了位置。
## 3. **补给数量只能有一个口径**。M13 让火把同时存在于 `supplies`
##    字典和 `torch` 字段，导致「点灯 4 支、奇物交互 1 支」。

static func run(t: TestLib, db: DdDb) -> void:
	var sh: Shop = db.shop
	t.section("商店：数据装载")
	if sh == null:
		t.ok(false, "shop 未加载")
		return

	t.eq(int(sh.stats["supplies"]), 10, "补给 + 食物共 10 条定义")
	t.eq(int(sh.stats["tradable"]), 8, "其中 8 种 supply 可交易")
	t.eq(sh.food_buy(), 75, "食物 75 金/份")
	t.eq(sh.supply_limit(Shop.FOOD_KEY), 12, "食物上限 12")

	# 价格全部来自 inventory.json，一个都不许拍
	t.eq(sh.supply_buy("torch"), 75, "火把 75")
	t.eq(sh.supply_buy("shovel"), 250, "铁锹 250")
	t.eq(sh.supply_buy("skeleton_key"), 200, "骷髅钥匙 200")
	t.eq(sh.supply_sell("torch"), 5, "火把卖 5")
	t.eq(sh.supply_sell("shovel"), 25, "铁锹卖 25")
	t.eq(sh.supply_limit("torch"), 8, "火把上限 8")
	t.eq(sh.supply_limit("shovel"), 4, "铁锹上限 4")

	# 买卖价都是 0 的那两种不是商品（柴火来自营地、狗饼干只对猎犬有用）
	t.eq(sh.supply_ids().has("firewood"), false, "柴火不出售")
	t.eq(sh.supply_ids().has("dog_treats"), false, "狗饼干不出售")
	t.eq(sh.supply_ids().has(Shop.FOOD_KEY), true, "食物在售")

	t.section("商店：补给包计价")
	var pack: Dictionary = {"torch": 4, "shovel": 1, "food": 2}
	t.eq(sh.pack_cost(pack), 300 + 250 + 150, "4 火把 + 1 铲 + 2 食物 = 700")
	t.eq(sh.pack_cost({}), 0, "空包 0 金")

	# 这个比例决定了补给是「一趟收入的 20%」而不是「1%」
	t.ok(float(sh.pack_cost(pack)) > 500.0 and float(sh.pack_cost(pack)) < 900.0,
		"一套基础补给在 500–900 金之间（%d）" % sh.pack_cost(pack))

	t.section("商店：饰品价格")
	t.eq(sh.trinket_buy_price("swift_cloak"), 10000, "少见件 10000")
	t.eq(sh.trinket_buy_price("speed_stone"), 7500, "常见件 7500")
	t.eq(sh.trinket_buy_price("ancestors_pen"), 50000, "先祖件 50000")
	t.eq(sh.trinket_sell_price("swift_cloak"), 1000, "卖价是买价的 10%")

	# 占位价（<=1）的特殊渠道件不上架
	t.eq(sh.can_stock("crow_wingfeather"), false, "crow 件 price=1，不上架")
	t.eq(sh.can_stock("swift_cloak"), true, "正常件可以上架")

	t.section("商店：上架")
	var s1: Array = sh.roll_stock(DdRng.new(555), 6)
	t.eq(s1.size(), 6, "上架 6 件")
	var s2: Array = sh.roll_stock(DdRng.new(555), 6)
	t.eq(s1, s2, "同种子上架一致（可复现）")
	var s3: Array = sh.roll_stock(DdRng.new(556), 6)
	t.ok(s1 != s3, "不同种子换一批货")

	var bad: Array = []
	for id in s1:
		if not sh.can_stock(str(id)):
			bad.append(id)
		if db.trinket_lib.rarity_of(str(id)) == "kickstarter":
			bad.append(id)
	t.eq(bad.size(), 0, "上架里没有占位价/众筹件  %s" % str(bad))

	# 不同稀有度要真的能出现——全是一种说明权重写错了
	var seen: Dictionary = {}
	for i in 40:
		for id2 in sh.roll_stock(DdRng.new(900 + i), 6):
			seen[db.trinket_lib.rarity_of(str(id2))] = true
	t.ok(seen.size() >= 3, "40 次上架覆盖到 %d 种稀有度" % seen.size())

	t.section("商店：买入")
	var c: Campaign = _mk(db, "user://t16_buy.json")
	t.eq(c.shop_stock.size(), 6, "新档就有 6 件货")

	# 没钱：必须被挡住，且不扣任何东西
	var poor: int = c.buy_shop_trinket(0).length() > 0 and 0 or 1
	t.eq(poor, 1, "新档 0 金买不了")
	t.eq(c.gold, 0, "失败不扣钱")
	t.eq(c.trinket_store.size(), 0, "失败不入库")
	t.eq(int(c.shop_refused.get("no_gold", 0)), 1, "拒绝被计数（不静默）")

	# 给钱再买
	c.add_loot(100000, {})
	var idx_price: int = c.shop_price_at(0)
	var bought_id: String = str(c.shop_stock[0])
	t.eq(c.buy_shop_trinket(0), "", "有钱能买")
	t.eq(c.gold, 100000 - idx_price, "扣了正好 %d" % idx_price)
	t.eq(c.trinket_store.has(bought_id), true, "东西进了仓库")
	t.eq(str(c.shop_stock[0]), "", "买走的格子留空（不往前挤）")
	t.eq(c.shop_stock.size(), 6, "货架长度不变")
	t.eq(c.buy_shop_trinket(0), "not_for_sale", "空格位买不了")

	# 仓库满：先判容量再扣钱
	var c2: Campaign = _mk(db, "user://t16_full.json")
	c2.add_loot(1000000, {})
	for i in c2.store_slots:
		c2.add_trinket("speed_stone")
	var g_before: int = c2.gold
	t.eq(c2.buy_shop_trinket(1), "store_full", "仓库满时买不了")
	t.eq(c2.gold, g_before, "仓库满时**不扣钱**（顺序：先判容量再扣款）")

	t.section("商店：卖出")
	var c3: Campaign = _mk(db, "user://t16_sell.json")
	c3.add_trinket("swift_cloak")
	var g0: int = c3.gold
	t.eq(c3.sell_trinket(0), "", "卖得掉")
	t.eq(c3.gold, g0 + 1000, "到账 1000（买价 10000 的 10%）")
	t.eq(c3.trinket_store.size(), 0, "仓库少一件")
	t.eq(c3.sell_trinket(0), "no_such_item", "空仓库卖不了")

	# 身上戴的卖不掉——必须先卸
	c3.add_trinket("swift_cloak")
	c3.equip_trinket("vestal", "swift_cloak")
	t.eq(c3.trinket_store.size(), 0, "装备后仓库为空")
	t.eq(c3.sell_trinket(0), "no_such_item", "身上戴的不能直接卖")

	t.section("商店：补给包购买")
	var c4: Campaign = _mk(db, "user://t16_pack.json")
	var no_money: Dictionary = c4.buy_pack({"torch": 4})
	t.eq(bool(no_money.get("ok", false)), false, "没钱买不了包")
	t.eq(str(no_money.get("reason", "")), "no_gold", "原因是 no_gold")
	t.eq(c4.gold, 0, "失败不扣钱")

	c4.add_loot(10000, {})
	var ok: Dictionary = c4.buy_pack({"torch": 4, "shovel": 1})
	t.eq(bool(ok.get("ok", false)), true, "有钱能买")
	t.eq(int(ok.get("cost", 0)), 300 + 250, "报价 550")
	t.eq(c4.gold, 10000 - 550, "扣了 550")

	# 超上限
	var over: Dictionary = c4.buy_pack({"torch": 99})
	t.eq(str(over.get("reason", "")), "over_limit", "买 99 根火把被上限挡住")
	t.eq(c4.gold, 10000 - 550, "被挡住时不扣钱")

	t.section("商店：存档")
	var c5: Campaign = _mk(db, "user://t16_save.json")
	c5.add_loot(100000, {})
	c5.buy_shop_trinket(2)
	c5.save()
	var c6: Campaign = Campaign.new()
	c6.setup_from_cfg(db.campaign_cfg, "user://t16_save.json")
	c6.trinket_lib = db.trinket_lib
	c6.shop = db.shop
	c6.load_or_new()
	t.eq(c6.shop_stock.size(), 6, "读档后货架还在")
	t.eq(c6.shop_stock, c5.shop_stock, "货架逐格一致（含空格位）")
	t.eq(str(c6.shop_stock[2]), "", "买走的空格位读回来后仍然是空的")

	# 旧档没有 shop_stock：现场掷一批，而不是给一个空商店
	var legacy: Dictionary = c6.to_dict()
	(legacy as Dictionary).erase("shop_stock")
	(legacy as Dictionary).erase("shop_seed")
	var c7: Campaign = Campaign.new()
	c7.setup_from_cfg(db.campaign_cfg, "user://t16_save2.json")
	c7.trinket_lib = db.trinket_lib
	c7.shop = db.shop
	c7.from_dict(legacy)
	t.eq(c7.shop_stock.size(), 6, "旧档缺货架字段时现场生成 6 件（不是空商店）")

	t.section("商店：补给口径")
	# 火把 / 口粮 / 铁锹只能有一个数字。M13 让火把同时存在于
	# `supplies` 字典和 `torch` 字段，于是「点灯 4 支、奇物交互 1 支」。
	var e0: Expedition = _mk_exp(db, 7001)
	t.eq(e0.supply_count("torch"), e0.torch, "torch 的计数与字段一致")
	t.eq(e0.supply_count("food"), e0.food, "food 的计数与字段一致")
	t.eq(e0.supply_count("shovel"), e0.shovel, "shovel 的计数与字段一致")
	t.eq(e0.torch, 4, "默认 4 支火把")
	t.eq(e0.food, 4, "默认 4 份口粮")
	t.eq(e0.supply_total(), 14, "默认共 14 件补给")

	# 取一件，只减一处
	var e1: Expedition = _mk_exp(db, 7002)
	var before: int = e1.supply_count("torch")
	e1.take_supply("torch")
	t.eq(e1.supply_count("torch"), before - 1, "取一支火把只减 1")
	t.eq(e1.torch, before - 1, "字段同步减少")

	# 外部包覆盖
	var e2: Expedition = _mk_exp(db, 7003)
	e2.set_start_supplies({"torch": 6, "food": 3, "shovel": 2, "bandage": 2})
	t.eq(e2.supply_count("torch"), 6, "外部包覆盖火把数")
	t.eq(e2.supply_count("food"), 3, "外部包覆盖口粮数")
	t.eq(e2.supply_count("shovel"), 2, "外部包覆盖铁锹数")
	t.eq(e2.supply_count("bandage"), 2, "外部包覆盖字典里的补给")

	# 空包 = 不覆盖（bench 与自动代打走这条，基线必须不变）
	var e3: Expedition = _mk_exp(db, 7004)
	e3.set_start_supplies({})
	t.eq(e3.supply_pack(), _mk_exp(db, 7004).supply_pack(), "空包不改变任何补给")


static func _mk(db: DdDb, save: String) -> Campaign:
	var c: Campaign = Campaign.new()
	c.setup_from_cfg(db.campaign_cfg, save)
	c.trinket_lib = db.trinket_lib
	c.shop = db.shop
	# 固定种子：货架与开局怪癖都可复现，否则这套断言跑两次两个结果
	c.start_rng_seed = 4242
	c.new_game()
	return c


static func _mk_exp(db: DdDb, seed_value: int) -> Expedition:
	var e: Expedition = Expedition.new()
	e.setup(db, ["vestal", "crusader", "highwayman", "plague_doctor"], [],
		db.expedition_cfg.preset("standard"), seed_value, "standard", {}, {})
	return e

extends SceneTree
## 测试入口。用 `--headless --script res://tests/run_tests.gd` 运行。
##
## 之所以脱离场景树跑：核心逻辑全是 RefCounted 类，不挂节点。
## 这样规则层可以完全独立于表现层迭代，也方便将来接进 CI。

func _initialize() -> void:
	print("DarkestLike 核心测试")
	var db: DdDb = DdDb.shared()
	if db == null or db.heroes.is_empty():
		print("数据加载失败，先运行 tools/extract.py")
		quit(2)
		return

	print("数据：%d 英雄 / %d 怪物 / %d 效果 / %d buff" % [
		db.heroes.size(), db.monsters.size(), db.effects.size(), db.buffs.size()])

	var t := TestLib.new()
	TestData.run(t, db)
	TestDamage.run(t)
	TestTurnOrder.run(t)
	TestBattle.run(t, db)
	TestBattle.run_stalemate(t, db)
	TestGuard.run(t, db)
	TestMove.run(t, db)
	TestSummon.run(t, db)
	TestLoot.run(t, db)
	TestCurio.run(t, db)
	TestM13.run(t, db)
	TestQuirk.run(t, db)
	TestTrinket.run(t, db)
	TestShop.run(t, db)
	TestM17.run(t, db)
	TestExpedition.run(t, db)
	TestCampaign.run(t, db)
	TestMap.run(t, db)
	TestM32.run(t, db)
	TestM33.run(t, db)
	TestM34.run(t, db)
	TestM35.run(t, db)

	# 与 Python 参考实现逐条对账
	if FileAccess.file_exists("res://tests/fixtures/cross_validation.json"):
		TestCross.run(t)
	else:
		print("\n（跳过交叉验证：缺少 tests/fixtures/cross_validation.json）")

	quit(t.summary())

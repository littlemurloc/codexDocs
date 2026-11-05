extends SceneTree
## 把一趟远征打成可读的战报。和 dump_battle 是同一思路：
## 数字对不上要看日志，手感不对也要看日志。
##
## 用法：
##   godot --headless --path . --script res://tests/dump_expedition.gd -- \
##     [--preset=standard] [--seed=1] [--size=short] [--level=3] [--dungeon=weald]

const HEROES: Array = ["crusader", "highwayman", "vestal", "plague_doctor"]

var _preset: String = "standard"
var _seed: int = 1
var _size: String = "short"
var _level: int = 3
var _dungeon: String = "weald"


func _initialize() -> void:
	for arg in OS.get_cmdline_user_args():
		if arg.begins_with("--preset="):
			_preset = arg.substr(9)
		elif arg.begins_with("--seed="):
			_seed = int(arg.substr(7))
		elif arg.begins_with("--size="):
			_size = arg.substr(7)
		elif arg.begins_with("--level="):
			_level = int(arg.substr(8))
		elif arg.begins_with("--dungeon="):
			_dungeon = arg.substr(10)

	var db: DdDb = DdDb.shared()
	if db.heroes.is_empty() or db.encounters.is_empty():
		print("数据未加载")
		quit(1)
		return

	var route: Array = RouteGen.build(db, _dungeon, _size, _level, DdRng.new(40000 + _seed))
	if route.is_empty():
		print("路线为空")
		quit(1)
		return

	var preset: Dictionary = db.expedition_cfg.preset(_preset)
	var exp := Expedition.new()
	if not exp.setup(db, HEROES, route, preset, 9000 + _seed, _preset):
		print("远征装配失败")
		quit(1)
		return

	print("远征  %s/%s  Lv%d  预设 %s  种子 %d" % [_dungeon, _size, _level, _preset, _seed])
	print("路线  %d 步：%s" % [route.size(), _route_text(route)])
	print("补给  火把 %d  口粮 %d  休整 %d  治疗配额 %s" % [
		exp.torch, exp.food, exp.camps_left,
		"不限" if exp.heal_charges < 0 else str(exp.heal_charges)])
	print("")

	exp.set_location(_dungeon, _size)

	var guard: int = 0
	while not exp.ended and guard < 40:
		guard += 1
		var before: int = exp.events.size()
		exp.run_step()
		for i in range(before, exp.events.size()):
			_print_event(exp, exp.events[i], route)
		_print_party(exp)

	print("=".repeat(60))
	print("结束：%s  推进 %d/%d 步  战斗 %d 场" % [
		exp.end_reason, exp.step_index, route.size(), int(exp.stats["battles"])])
	var s: Dictionary = exp.summary()
	print("阵亡 %d  崩溃 %d  美德 %d  心脏骤停 %d  死门 %d  摆烂 %d" % [
		int(s["hero_deaths"]), int(s["afflictions"]), int(s["virtues"]),
		int(s["heart_attacks"]), int(s["dd_entries"]), int(s["act_outs"])])
	print("终局血量 %.2f  终局压力 %.0f  光照 %.0f  口粮 %d  火把 %d" % [
		float(s["hp_end"]), float(s["stress_end"]), float(s["light_end"]),
		int(s["food_end"]), int(s["torch_end"])])
	quit(0)


func _print_event(exp: Expedition, e: Dictionary, route: Array) -> void:
	match str(e.get("t", "")):
		"light":
			print("  ◦ 光照 %.0f（%s）" % [float(e["light"]), str(e["tier"])])
		"torch_used":
			print("  ◦ 点燃火把，剩余 %d 根 → 光照 %.0f" % [int(e["left"]), float(e["light"])])
		"hunger":
			if bool(e["fed"]):
				print("  ◦ 饥饿检定：吃到口粮，剩 %d" % int(e["food"]))
			else:
				print("  ◦ 饥饿检定：断粮！全员加压并掉血")
		"battle_start":
			print("  ⚔ 第 %d 场：%s%s" % [int(e["index"]) + 1,
				", ".join(e["monsters"]),
				"（被惊袭）" if str(e["surprised"]) == "party" else
				("（我方偷袭）" if str(e["surprised"]) == "enemy" else "")])
		"battle_end":
			print("    战斗结束：%s，%d 轮" % [str(e["winner"]), int(e["rounds"])])
		"affliction":
			print("    ☠ 崩溃！%s 陷入「%s」，压力 %.0f" % [
				str(e.get("hero", "?")), str(e["kind"]), float(e.get("stress", 100.0))])
		"virtue":
			print("    ✦ 美德！%s 顶住了（%s）" % [str(e.get("hero", "?")), str(e["kind"])])
		"heart_attack":
			print("    ☠☠ %s 心脏骤停！" % str(e.get("hero", "?")))
		"act_out":
			print("    ✗ %s 崩溃发作，本回合不行动" % str(e.get("hero", "?")))
		"deaths_door":
			print("    † %s 进入死门（%s）" % [str(e.get("hero", "?")), str(e.get("cause", "战斗"))])
		"death":
			print("    † %s 阵亡（%s）" % [str(e.get("hero", "?")), str(e.get("cause", "战斗"))])
		"camp":
			print("  ⛺ 休整：剩 %d 次，口粮 %d，光照 %.0f" % [
				int(e["camps_left"]), int(e["food"]), float(e["light"])])
		"camp_ambush":
			print("  ⛺⚠ 营地被偷袭！")
		"retreat":
			print("  ← 撤退")
		"exp_end":
			print("  ■ 远征结束（%s）" % str(e["reason"]))


func _print_party(exp: Expedition) -> void:
	var bits: Array = []
	for hid in exp.hero_ids:
		var s: Dictionary = exp.state.get(hid, {})
		if s.is_empty():
			continue
		var tag: String = ""
		if bool(s.get("dead", false)):
			tag = "【阵亡】"
		elif bool(s.get("at_deaths_door", false)):
			tag = "【死门】"
		elif not str(s.get("affliction", "")).is_empty():
			tag = "【崩溃·%s】" % str(s["affliction"])
		elif not str(s.get("virtue", "")).is_empty():
			tag = "【美德·%s】" % str(s["virtue"])
		bits.append("%s %.0f%% 压%.0f%s" % [hid, float(s.get("hp_ratio", 0.0)) * 100.0,
			float(s.get("stress", 0.0)), tag])
	print("    队伍：" + " | ".join(bits))


func _route_text(route: Array) -> String:
	var bits: Array = []
	for s in route:
		if str(s.get("kind", "")) == "hunger":
			bits.append("饥")
		else:
			var m: Array = s.get("monsters", [])
			bits.append("%d怪" % m.size())
	return " ".join(bits)

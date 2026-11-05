extends SceneTree
## 把一场战斗打成可读的战报。用于人工核对「数值对不对」之外的手感问题。
## 用法：godot --headless --path . --script res://tests/dump_battle.gd

const HEROES: Array = ["crusader", "highwayman", "vestal", "plague_doctor"]
const MONSTERS: Array = ["cultist_brawler_A", "cultist_brawler_A", "cultist_witch_A"]


func _initialize() -> void:
	var seed_value: int = 20261102
	var args: PackedStringArray = OS.get_cmdline_user_args()
	if args.size() > 0:
		seed_value = int(args[0])

	var b := Battle.new()
	if not b.setup(HEROES, MONSTERS, seed_value):
		print("装配失败")
		quit(1)
		return

	var names: Dictionary = {}
	for u in b.all_units():
		names[u.uid] = _short(u)

	print("种子 %d" % seed_value)
	print("我方：%s" % ", ".join(HEROES))
	print("敌方：%s" % ", ".join(MONSTERS))
	print("")

	var rounds: int = 0
	while not b.is_over() and rounds < 30:
		rounds += 1
		var events: Array = b.run_round()
		_print_round(events, names, b, rounds)
		print("")

	print("=".repeat(56))
	print("%d 轮结束，胜方：%s" % [rounds, b.winner()])
	for u in b.all_units():
		print("  %-22s HP %3d/%-3d  压力 %5.1f %s" % [
			_short(u), u.hp, u.base_hp, u.stress,
			"【死门】" if u.at_deaths_door else ("【阵亡】" if u.dead else "")])
	quit(0)


func _print_round(events: Array, names: Dictionary, b: Battle, round_no: int) -> void:
	print("── 第 %d 轮 ──" % round_no)
	for e in events:
		match str(e["t"]):
			"order":
				var seq: Array = []
				for id in e["ids"]:
					seq.append(str(names.get(id, "?")))
				print("  行动序：%s" % " → ".join(seq))
			"turn":
				pass
			"attack":
				var line: String = "  %s 使用 [%s] 攻击 %s" % [
					names.get(e["actor"], "?"), str(e["skill"]), names.get(e["target"], "?")]
				if bool(e["crit"]):
					line += "  【暴击】"
				line += "  伤害 %d" % int(e["damage"])
				if bool(e["deaths_door"]):
					line += "  → 进入死门"
				if bool(e["died"]):
					line += "  → 击杀"
				print(line)
			"miss":
				print("  %s 攻击 %s  未命中（命中率 %.0f%%）" % [
					names.get(e["actor"], "?"), names.get(e["target"], "?"),
					float(e["chance"]) * 100.0])
			"heal":
				print("  %s 治疗 %s  +%d" % [names.get(e["actor"], "?"),
					names.get(e["target"], "?"), int(e["amount"])])
			"effect":
				var who: String = str(names.get(e.get("target", -1), "?"))
				var bits: Array = []
				if e.has("dot"):
					bits.append("%s %d 层" % [e["dot"], int(e["amount"])])
				if e.has("stun"):
					bits.append("眩晕")
				if e.has("stress"):
					bits.append("压力 %+.0f" % float(e["stress"]))
				if e.has("heal"):
					bits.append("治疗 %d" % int(e["heal"]))
				if e.has("status"):
					bits.append("标记[%s]" % str(e["status"]))
				if e.has("buffs"):
					bits.append("增益×%d" % (e["buffs"] as Array).size())
				if e.has("resisted"):
					bits.append("%s 被抵抗" % str(e["resisted"]))
				if not bits.is_empty():
					print("    · %s ← %s：%s" % [who, str(e["effect"]), "，".join(bits)])
			"dot":
				print("    · %s 受 %s 伤害 %d" % [
					names.get(e["target"], "?"), str(e["kind"]), int(e["amount"])])
			"stress":
				print("    · %s 压力 %+.0f（%s）" % [
					names.get(e["target"], "?"), float(e["delta"]), str(e["source"])])
			"stunned":
				print("  %s 被眩晕，跳过行动" % names.get(e["actor"], "?"))
			"pass":
				print("  %s 无处可施，空过" % names.get(e["actor"], "?"))
			"death":
				print("  ☠ %s 阵亡" % names.get(e["actor"], "?"))


func _short(u: Combatant) -> String:
	if u.is_hero:
		return u.def_id
	return u.def_id.replace("_A", "").replace("_B", "").replace("_C", "")

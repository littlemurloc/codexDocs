class_name TestSkills
extends RefCounted
## 全技能出手机制（M167）。
##
## 用户在两次对话里都提到「有些恢复性的技能是不是被做成了伤害类」。
## 单测原来只测规则层的公式，**没有任何一条**在验证
## 「点这个技能之后，到底产生了 heal 还是 attack」。
##
## 这一层走的是玩家真实路径：`Battle.submit_choice()` ——
## 界面点技能、点目标之后调的就是它（不是内部的 `_apply_choice`）。
## 所以它验证的是「玩家按下这个按钮，游戏会发生什么」。

const MONSTERS: Array = ["cultist_brawler_A", "cultist_brawler_A", "cultist_witch_A"]
const FILLERS: Array = ["vestal", "crusader", "highwayman"]


static func run(t: TestLib, db: DdDb) -> void:
	t.section("全技能：提交后产生的事件类型")
	var checked: int = 0
	var wrong: Array = []
	var skipped: Array = []

	for hid in db.heroes.keys():
		var h: Dictionary = db.heroes[str(hid)]
		for s in (h.get("skills", []) as Array):
			if not (s is Dictionary):
				continue
			var sid: String = str((s as Dictionary).get("id", ""))
			if sid.is_empty():
				continue
			# 坑：GDScript 的 `a or b` **返回 bool**，不是「a 为空就用 b」。
			# 写成 `(lv or [{}])[0]` 会得到 `(bool)[0]` —— 报
			# 「Invalid access to property or key '0' on a base object of type 'bool'」。
			var lv_list: Array = (s as Dictionary).get("levels", [])
			var lv: Dictionary = lv_list[0] if not lv_list.is_empty() else {}
			# 治疗的字段是**数组** `[2,3]`（回血量区间），不是数字。
			# 第一版直接用 `_num()` 取，Array 一律变 0 —— 于是
			# 「battle_heal 数据没标治疗」这种误报出现了十几次。
			var heal_raw: Variant = lv.get("heal", 0.0)
			var heal_v: float = 0.0
			if heal_raw is Array:
				heal_v = 1.0 if (heal_raw as Array).size() >= 1 else 0.0
			else:
				heal_v = _num(heal_raw)

			var b := Battle.new()
			var heroes: Array = [str(hid)]
			for f in FILLERS:
				if str(f) != str(hid):
					heroes.append(str(f))
			if not b.setup(heroes, MONSTERS, 7711):
				skipped.append("%s：装配失败" % hid)
				continue

			# **必须给一个 decision_provider**（M167）：`step_turn` 里
			# `if actor.is_hero and decision_provider.is_valid() and not awaiting_input`
			# 才把回合交给玩家。没有它，英雄会走 AI 的 `_take_action` 自己出招，
			# `awaiting_input` 永远是 null —— 第一版 105 个技能全被跳过就是这个原因。
			b.decision_provider = func(_bb: Battle, _aa: Combatant) -> Dictionary: return {}
			var actor: Combatant = b.party[0]
			var act: Dictionary = {}
			for a in actor.actions:
				if str((a as Dictionary).get("id", "")) == sid:
					act = a
					break
			if act.is_empty():
				skipped.append("%s/%s：没装进技能列表" % [hid, sid])
				continue

			# 推进到「轮到这个人」。注意：轮到**别的英雄**时不能直接 `step_turn()`
			# 把它跳过去 —— 那样他自己的回合会被当成 pass 空过，
			# 行动序一轮只走一遍，于是永远轮不到 actor（第一版 105 个全被跳过）。
			# 正确做法：别人轮到时替他提交一个合法技能，把这一轮推过去。
			b.begin_round()
			var guard: int = 0
			while not b.is_over() and guard < 80:
				if b.awaiting_input == actor:
					break
				if b.awaiting_input != null:
					var other: Combatant = b.awaiting_input
					var opts_o: Array = b.player_options(other)
					if opts_o.is_empty():
						b.submit_choice({}, [])
					else:
						var o0: Dictionary = opts_o[0]
						b.submit_choice(o0["action"], o0["targets"])
				else:
					b.step_turn()
				guard += 1
			if b.awaiting_input != actor:
				skipped.append("%s/%s：轮不到他出手" % [hid, sid])
				continue

			# 目标**用引擎给的合法列表**，不要自己猜 `enemies[0]`（M167 第二版）。
			# 猜错的表现是「提交后什么事件都没有」——因为非法目标会被 `_apply_choice` 丢弃。
			var opts_a: Array = b.player_options(actor)
			var chosen: Dictionary = {}
			for oa in opts_a:
				if str((oa["action"] as Dictionary).get("id", "")) == sid:
					chosen = oa
					break
			if chosen.is_empty():
				skipped.append("%s/%s：不在可选项里（站位不符或目标为空）" % [hid, sid])
				continue
			# 挑**活着的**目标（M167 第三版）：前面的英雄可能已经把 1 号怪打死了，
			# 这时 `targets[0]` 是尸体，提交后会走 `_strike_corpse` → 只有 `corpse_hit`，
			# 看起来像「技能没生效」。`miss` 同理，是正常没打中。
			var tgs: Array = []
			for ct in (chosen["targets"] as Array):
				var cm: Combatant = ct
				if not cm.dead:
					tgs = [cm]
					break
			if tgs.is_empty():
				skipped.append("%s/%s：目标全是尸体" % [hid, sid])
				continue
			if tgs.is_empty():
				skipped.append("%s/%s：没有合法目标" % [hid, sid])
				continue
			var before: int = b.events.size()
			b.submit_choice(chosen["action"], tgs)

			var got_heal: bool = false
			var got_atk: bool = false
			var got_any: bool = false
			for i in range(before, b.events.size()):
				var e: Dictionary = b.events[i]
				var et: String = str(e.get("t", ""))
				if et == "heal":
					got_heal = true
					got_any = true
				elif et == "attack":
					got_atk = true
					got_any = true
				elif et in ["effect", "buff", "miss", "corpse_hit", "dot", "stress"]:
					got_any = true

			checked += 1
			# ① 标成治疗技能，必须出 heal 事件
			if heal_v > 0.0 and not got_heal:
				wrong.append("%s/%s：数据标了治疗(%.0f)，但提交后没有 heal 事件%s" % [
					hid, sid, heal_v, "" if got_atk else "（连 attack 也没有）"])
			# ② 没标治疗的，不该出 heal 事件
			if heal_v <= 0.0 and got_heal:
				wrong.append("%s/%s：数据没标治疗，却产生了 heal 事件" % [hid, sid])
			# ③ 不检查「有没有事件」——攻击技能的落地事件名不止 `attack`
			# （命中/未命中/位移各有各的），按名字白名单查会误报一片。
			# 这条判据留作参考：任何一个技能提交后**一条事件都没有**才算异常。
			if not got_any and sid != "transform":
				var dump: Array = []
				for ii in range(maxi(0, before - 3), b.events.size()):
					dump.append(str((b.events[ii] as Dictionary).get("t", "?")))
				print("  [SKILL] %s/%s 零事件 · awaiting=%s · act=%s · 尾部事件=%s" % [
					hid, sid, str(b.awaiting_input), str(act.get("id", "")), str(dump)])

	# 40 个左右会因为「这个英雄站在 1 号位用不了这个技能」被跳过，属于正常；
	# 门槛定在 60 是「至少覆盖六成」的意思。
	t.ok(checked >= 60, "覆盖到 %d 个技能（至少应有 60 个）" % checked)
	if not skipped.is_empty():
		print("  （跳过 %d 个：%s）" % [skipped.size(), ", ".join(skipped.slice(0, 5))])
	for w in wrong:
		t.ok(false, str(w))
	t.ok(wrong.is_empty(), "技能分类与事件类型一致（检查 %d 个）" % checked)


static func _num(v: Variant) -> float:
	if v is int or v is float:
		return float(v)
	return 0.0

extends Control
## M1 战斗垂直切片的表现层。
##
## 刻意只用色块和文字：这一版的目的是验证规则，不是验证美术。
## 一旦用上真实美术，人会被「像不像」骗过去，而规则可能已经歪了。
##
## 操作：空格 = 推进一轮；A = 开关自动；R = 换种子重开

const AUTO_INTERVAL: float = 1.4
const SLOT_W: float = 152.0
const SLOT_H: float = 128.0
const GAP: float = 20.0

const C_BG := Color("#14161a")
const C_PANEL := Color("#1b1e24")
const C_PANEL_EDGE := Color("#2c313a")
const C_TEXT := Color("#d9d4c7")
const C_DIM := Color("#8b8a84")
const C_PARTY := Color("#3e5c76")
const C_ENEMY := Color("#7a3b34")
const C_HP := Color("#a8322d")
const C_HP_TRACK := Color("#241c1c")
const C_STRESS := Color("#c08a2e")
const C_STRESS_TRACK := Color("#241f16")
const C_CRIT := Color("#f0c040")
const C_HEAL := Color("#6fbf73")
const C_HARM := Color("#e8e2d4")
const C_STAT := Color("#9d7bd8")

var battle: Battle
var seed_value: int = 20261102
var auto_play: bool = true

var _timer: float = 0.0
var _names: Dictionary = {}
var _log: Array = []
var _floaters: Array = []
var _font: Font
var _banner: String = ""
var _banner_life: float = 0.0

var _capture_path: String = ""
var _capture_at: float = 3.4
var _elapsed: float = 0.0

const HEROES: Array = ["crusader", "highwayman", "vestal", "plague_doctor"]
const MONSTERS: Array = ["cultist_brawler_A", "cultist_brawler_A", "cultist_witch_A"]


func _ready() -> void:
	_font = ThemeDB.fallback_font
	for a in OS.get_cmdline_user_args():
		if a.begins_with("--shot="):
			_capture_path = a.substr(7)
			# 截图时把窗口拉到设计尺寸，避免被任务栏/DPI 挤小导致排版走样
			DisplayServer.window_set_size(Vector2i(1280, 760))
	_restart()
	set_process(true)


func _restart() -> void:
	battle = Battle.new()
	if not battle.setup(HEROES, MONSTERS, seed_value):
		push_error("战斗装配失败")
		return
	_names.clear()
	for u in battle.all_units():
		_names[u.uid] = _pretty(u.def_id)
	_log.clear()
	_floaters.clear()
	_timer = 0.0
	_banner = "种子 %d · 第 1 轮" % seed_value
	_banner_life = 1.8
	queue_redraw()


# ============================================================
# 循环
# ============================================================

func _process(delta: float) -> void:
	_banner_life = maxf(0.0, _banner_life - delta)

	if not _capture_path.is_empty():
		_elapsed += delta
		if _elapsed >= _capture_at:
			var img: Image = get_viewport().get_texture().get_image()
			img.save_png(_capture_path)
			print("截图已保存：", _capture_path)
			get_tree().quit()
			return

	var i: int = 0
	while i < _floaters.size():
		_floaters[i].life -= delta
		_floaters[i].pos.y -= 24.0 * delta
		if _floaters[i].life <= 0.0:
			_floaters.remove_at(i)
		else:
			i += 1

	if auto_play and not battle.is_over():
		_timer += delta
		if _timer >= AUTO_INTERVAL:
			_timer = 0.0
			step_round()

	queue_redraw()


func _input(event: InputEvent) -> void:
	if event is InputEventKey and event.pressed and not event.echo:
		match event.keycode:
			KEY_SPACE:
				if not battle.is_over():
					step_round()
			KEY_A:
				auto_play = not auto_play
			KEY_R:
				seed_value += 1
				_restart()


func step_round() -> void:
	if battle.is_over():
		return
	for e in battle.run_round():
		_consume(e)
	if battle.is_over():
		_banner = "战斗结束 · %s胜 · %d 轮" % [
			"我方" if battle.winner() == "party" else "敌方", battle.round_index]
		_banner_life = 8.0


func _consume(e: Dictionary) -> void:
	match str(e["t"]):
		"round_start":
			_log.append("── 第 %d 轮 ──" % int(e["round"]))
			_banner = "第 %d 轮" % int(e["round"])
			_banner_life = 0.9
		"attack":
			var crit: bool = bool(e["crit"])
			_log.append("%s → %s   %d%s" % [
				_names.get(e["actor"], "?"), _names.get(e["target"], "?"),
				int(e["damage"]), "   暴击" if crit else ""])
			_spawn_float(e["target"], str(int(e["damage"])), C_CRIT if crit else C_HARM, crit)
			if bool(e["died"]):
				_log.append("    · %s 阵亡" % _names.get(e["target"], "?"))
			elif bool(e["deaths_door"]):
				_log.append("    %s 进入死门" % _names.get(e["target"], "?"))
		"miss":
			_log.append("%s → %s   未命中（%.0f%%）" % [
				_names.get(e["actor"], "?"), _names.get(e["target"], "?"),
				float(e["chance"]) * 100.0])
			_spawn_float(e["target"], "MISS", C_DIM, false)
		"heal":
			if int(e["amount"]) > 0:
				_log.append("%s 治疗 %s  +%d" % [
					_names.get(e["actor"], "?"), _names.get(e["target"], "?"), int(e["amount"])])
				_spawn_float(e["target"], "+%d" % int(e["amount"]), C_HEAL, false)
		"effect":
			if e.has("stress") and absf(float(e["stress"])) >= 1.0:
				var d: float = float(e["stress"])
				_spawn_float(e["target"], "%+.0f 压力" % d, C_STAT, false)
			if e.has("dot"):
				_log.append("    %s 陷入%s %d 层" % [
					_names.get(e["target"], "?"), "流血" if str(e["dot"]) == "bleed" else "中毒",
					int(e["amount"])])
		"dot":
			_spawn_float(e["target"], "-%d" % int(e["amount"]), C_HP, false)
		"stress":
			_spawn_float(e["target"], "%+.0f" % float(e["delta"]), C_STAT, false)
		"stunned":
			_log.append("    %s 被眩晕，跳过" % _names.get(e["actor"], "?"))
		"pass":
			_log.append("    %s 无行动" % _names.get(e["actor"], "?"))
		"death":
			_log.append("    · %s 倒下" % _names.get(e["actor"], "?"))
		# —— M3：压力阈值与惊袭 ——
		"affliction":
			_log.append("  ✖ %s 崩溃（%s）" % [
				_names.get(e["target"], "?"), str(e.get("kind", ""))])
			_banner = "崩溃！"
			_banner_life = 1.6
		"virtue":
			_log.append("  ✦ %s 觉醒（%s）" % [
				_names.get(e["target"], "?"), str(e.get("kind", ""))])
			_banner = "美德觉醒"
			_banner_life = 1.6
		"heart_attack":
			_log.append("  ✖✖ %s 心脏骤停" % _names.get(e["target"], "?"))
			_banner = "心脏骤停！"
			_banner_life = 1.8
		"act_out":
			_log.append("    %s 崩溃发作，本回合不行动" % _names.get(e["actor"], "?"))
		"recovered":
			_log.append("    %s 被从死门拉回" % _names.get(e["actor"], "?"))
		"deaths_door":
			_log.append("    %s 进入死门" % _names.get(e["actor"], "?"))
		"surprised":
			_log.append("    %s 被惊袭，本轮不动" % _names.get(e["actor"], "?"))

	if _log.size() > 240:
		_log = _log.slice(_log.size() - 240)


# ============================================================
# 布局
# ============================================================

func _enemy_top() -> float:
	return 74.0


func _party_top() -> float:
	return size.y - 188.0


func _log_rect() -> Rect2:
	var top: float = _enemy_top() + SLOT_H + 16.0
	var bottom: float = _party_top() - 16.0
	return Rect2(40, top, size.x - 80, maxf(96.0, bottom - top))


func _slot_rect(count: int, index: int, top: float) -> Rect2:
	var total: float = count * SLOT_W + (count - 1) * GAP
	var left: float = (size.x - total) * 0.5
	return Rect2(left + index * (SLOT_W + GAP), top, SLOT_W, SLOT_H)


func _anchor_for(uid: int) -> Vector2:
	for i in battle.enemies.size():
		if battle.enemies[i].uid == uid:
			var r: Rect2 = _slot_rect(battle.enemies.size(), i, _enemy_top())
			return Vector2(r.position.x + r.size.x * 0.5, r.position.y + r.size.y * 0.42)
	for i in battle.party.size():
		if battle.party[i].uid == uid:
			var r2: Rect2 = _slot_rect(battle.party.size(), i, _party_top())
			return Vector2(r2.position.x + r2.size.x * 0.5, r2.position.y + r2.size.y * 0.42)
	return Vector2(-1, -1)


func _spawn_float(uid: Variant, text: String, color: Color, big: bool) -> void:
	var pos: Vector2 = _anchor_for(int(uid))
	if pos == Vector2(-1, -1):
		return
	_floaters.append({
		"pos": pos + Vector2(randf_range(-14.0, 14.0), 0.0),
		"text": text, "color": color, "life": 1.15, "big": big,
	})


# ============================================================
# 绘制
# ============================================================

func _draw() -> void:
	draw_rect(Rect2(Vector2.ZERO, size), C_BG)
	draw_string(_font, Vector2(40, 34), "DARKEST LIKE · 战斗核心切片 M1",
		HORIZONTAL_ALIGNMENT_LEFT, -1, 17, C_TEXT)
	draw_string(_font, Vector2(size.x - 330, 34),
		"空格 推进一轮    自动 %s    换种子 R" % ("开" if auto_play else "关"),
		HORIZONTAL_ALIGNMENT_LEFT, -1, 12, C_DIM)

	for i in battle.enemies.size():
		_draw_unit(battle.enemies[i], _slot_rect(battle.enemies.size(), i, _enemy_top()), true)
	for i in battle.party.size():
		_draw_unit(battle.party[i], _slot_rect(battle.party.size(), i, _party_top()), false)

	_draw_log()
	_draw_floaters()

	if _banner_life > 0.0:
		var a: float = clampf(_banner_life, 0.0, 1.0)
		draw_string(_font, Vector2(0, 54), _banner,
			HORIZONTAL_ALIGNMENT_CENTER, size.x, 15,
			Color(C_CRIT.r, C_CRIT.g, C_CRIT.b, a * 0.9))


func _draw_unit(u: Combatant, r: Rect2, is_enemy: bool) -> void:
	var accent: Color = C_ENEMY if is_enemy else C_PARTY
	if u.dead:
		accent = Color("#3a3a3a")

	draw_rect(r, C_PANEL)
	draw_rect(Rect2(r.position, Vector2(r.size.x, 3)), accent)
	draw_rect(r, C_PANEL_EDGE, false, 1.0)

	var text_col: Color = C_DIM if u.dead else C_TEXT
	draw_string(_font, Vector2(r.position.x + 10, r.position.y + 24),
		_pretty(u.def_id), HORIZONTAL_ALIGNMENT_LEFT, int(r.size.x - 20), 12, text_col)
	if u.dead:
		# 阵亡只用一道删除线 + 角标，别用大叉盖住血量数字
		var w: float = minf(_font.get_string_size(_pretty(u.def_id), HORIZONTAL_ALIGNMENT_LEFT, -1, 12).x,
			r.size.x - 20.0)
		draw_line(Vector2(r.position.x + 10, r.position.y + 20),
			Vector2(r.position.x + 10 + w, r.position.y + 20),
			Color(C_DIM.r, C_DIM.g, C_DIM.b, 0.7), 1.0)
		draw_string(_font, Vector2(r.position.x, r.position.y + 18), "×",
			HORIZONTAL_ALIGNMENT_RIGHT, r.size.x - 10, 12, C_HP.lightened(0.1))
	draw_string(_font, Vector2(r.position.x + 10, r.position.y + 40),
		"位 %d" % (u.rank + 1), HORIZONTAL_ALIGNMENT_LEFT, -1, 10, C_DIM)

	var bar_x: float = r.position.x + 10
	var bar_w: float = r.size.x - 20
	var hp_y: float = r.position.y + 50

	draw_rect(Rect2(bar_x, hp_y, bar_w, 12), C_HP_TRACK)
	var ratio: float = clampf(u.hp_ratio(), 0.0, 1.0)
	if ratio > 0.0:
		draw_rect(Rect2(bar_x, hp_y, bar_w * ratio, 12), C_HP)
	draw_string(_font, Vector2(bar_x, hp_y + 10), "%d / %d" % [u.hp, u.base_hp],
		HORIZONTAL_ALIGNMENT_CENTER, bar_w, 9, Color("#f2eee2"))

	if u.is_hero:
		var st_y: float = hp_y + 16
		draw_rect(Rect2(bar_x, st_y, bar_w, 4), C_STRESS_TRACK)
		var sr: float = clampf(u.stress / 100.0, 0.0, 1.0)
		if sr > 0.0:
			draw_rect(Rect2(bar_x, st_y, bar_w * sr, 4), C_STRESS)
		draw_string(_font, Vector2(bar_x, st_y + 14), "压力 %.0f" % u.stress,
			HORIZONTAL_ALIGNMENT_LEFT, bar_w, 9, C_STRESS if u.stress > 50.0 else C_DIM)

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
		if u.buffs.size() > 0:
			marks.append("BUF×%d" % u.buffs.size())
		for key in u.statuses.keys():
			marks.append(str(key))
	if not marks.is_empty():
		draw_string(_font, Vector2(bar_x, r.position.y + r.size.y - 9),
			" ".join(marks), HORIZONTAL_ALIGNMENT_LEFT, int(bar_w), 9,
			C_HP.lightened(0.2) if u.dead else (C_CRIT if u.at_deaths_door else C_STAT))


func _draw_log() -> void:
	var rect: Rect2 = _log_rect()
	draw_rect(rect, C_PANEL)
	draw_rect(rect, C_PANEL_EDGE, false, 1.0)

	var line_h: float = 16.0
	var max_lines: int = int((rect.size.y - 18.0) / line_h)
	var start: int = maxi(0, _log.size() - max_lines)
	var y: float = rect.position.y + 20.0
	for i in range(start, _log.size()):
		var line: String = str(_log[i])
		var col: Color = C_DIM if line.begins_with("──") else C_TEXT
		if line.contains("阵亡") or line.contains("倒下"):
			col = Color("#c8695f")
		elif line.contains("暴击"):
			col = C_CRIT
		draw_string(_font, Vector2(rect.position.x + 14, y), line,
			HORIZONTAL_ALIGNMENT_LEFT, int(rect.size.x - 28), 12, col)
		y += line_h


func _draw_floaters() -> void:
	for f in _floaters:
		var col: Color = f.color
		col.a = clampf(f.life, 0.0, 1.0)
		var fs: int = 21 if f.big else 15
		draw_string(_font, f.pos - Vector2(80, 0), str(f.text),
			HORIZONTAL_ALIGNMENT_CENTER, 160, fs, col)


func _pretty(id: String) -> String:
	var parts: Array = []
	for p in id.replace("_A", "").replace("_B", "").replace("_C", "").replace("_D", "").split("_"):
		var s: String = str(p)
		if s.length() > 0:
			parts.append(s.substr(0, 1).to_upper() + s.substr(1))
	return " ".join(parts)

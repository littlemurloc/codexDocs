extends Control

const I18n = preload("res://scripts/i18n.gd")
## 数羊舞台：夜晚牧场 / 羊圈 / 栅栏 / 木牌 / 牧羊人，全部 _draw 现画（零美术资源）
##
## 主题映射（和技术概念一一对应）：
##   INBOX  → 左边羊圈里待数的羊
##   OUTBOX → 右边栅栏，羊跳过去 = 数过一只
##   手     → 怀里抱着的那只羊，编号浮在头顶
##   地板格 → 插在草地上的木牌，牌子上写数字
##   出错   → 羊被栅栏绊倒，四脚朝天

const C_TEXT := Color("ffffff")
const C_MUTED := Color("cfe8f7")
const C_ACCENT := Color("ffdc30")
const C_OK := Color("3ebc1a")
const C_ERR := Color("e8553f")

# 天空 / 远景（白天：上蓝下浅，远山偏黄绿，近山偏翠）
const C_SKY_TOP := Color("69c6ea")
const C_SKY_BOT := Color("c9ecf9")
const C_HILL_FAR := Color("a8d97a")
const C_HILL_NEAR := Color("82c95c")
# 草地
const C_GRASS := Color("63b93f")
const C_GRASS_D := Color("4f9c33")
# 木料（卡通木：暖橙棕，能压住绿色草地）
const C_WOOD := Color("c08a4e")
const C_WOOD_L := Color("dcaa6c")
const C_WOOD_D := Color("8a5c2e")
# 木牌上的编号格：奶白底 + 深棕字。深底浅字在棕色木料上会糊，必须反过来。
const TAG_FACE := Color("f2e3c8")
const TAG_INK := Color("4a3418")
# 羊
const C_WOOL := Color("fffdf6")
const C_WOOL_D := Color("e2dac8")
const C_FACE := Color("3a2e22")
# 牧羊人（工装）
const C_PJ := Color("3f7fbf")
const C_PJ2 := Color("5a97d0")
const C_SKIN := Color("f0c9a0")

const HOP_TIME := 0.44
const HOP_H := 70.0
const PEN_X := 132.0
const WORKER_SCALE := 1.22
const PEN_SHOW := 3          # 羊圈里同时展示几只羊（每只身上都写着编号）

var slot_count: int = 2
var mem: Array = []
var hand: int = 0
var hand_full: bool = false
var inbox_left: Array = []
## 这一关开局羊圈就是空的（题目不从 INBOX 拿数）。configure 时定一次，
## 画「空羊圈」的说明文字时靠它区分「这关本来就没有羊」和「已经数完了」。
var pen_starts_empty: bool = false
var outbox: Array = []
var expected_count: int = 0

var highlight_slot: int = -1
## 编辑期联动：当前选中行如果带「跳转目标（木牌/格子编号）」，这里放那个编号。
## 与 highlight_slot（运行时正在操作哪块）分开 —— 一个是「正在算哪块」，一个是「这行指着哪块」。
var linked_slot: int = -1
var last_op: String = ""
var status: String = "idle"  # idle / done / error
## 通关庆祝的计时器（秒）。只有 status == "done" 时才走。
## 单独计时而不是复用 phase：庆祝动画的开头必须是一个确定的 0，
## 否则什么时候通关就决定了玩家看到的是彩纸刚喷出来还是已经落地了。
var win_t: float = 0.0

var worker_x: float = -1.0
var target_key: String = "center"
var phase: float = 0.0
var moving: bool = false
var bump: float = 0.0
var facing: float = 1.0

var hop_t: float = -1.0     # 0..1 跳跃进度，<0 表示没有羊在飞
var pose_lock: float = -1.0 # 调试：把跳跃动画钉在某一帧，_process 不再推进
var hop_val: int = 0
var hop_from: float = 0.0
var fail_t: float = 0.0
var stars: Array = []       # 星星：{x, y, r, a}（相对比例）

# ---- 任务牌 ----------------------------------------------------------------
# 目标 / 数据流 / 提示，原先住在抬头那一条里。
# 抬头是「宽富余、高紧张」的地方，字只能压到 12–13px；而玩家的眼睛九成时间
# 停在牧场上，于是「这一关要干什么」成了全屏最小、离视线最远的一行字。
# 现在它挂到舞台顶上，当成一块**木牌**（物体，不是一行字），17px 加粗。
# 高度按内容算，但只允许 1–2 行：同一关里永远是同一个高度，不会自己长高。
var goal_text: String = ""
var stream_a: String = ""    # INBOX 那一串
var stream_b: String = ""    # OUTBOX 那一串
var hint_text: String = ""   # 玩家点了「看提示」才有，空 = 不画

## 播放节奏（1.0 = 正常，最小约 0.29 = 最快）。
## 由 main 按 combo 设进来：**舞台上的动作必须跟着加速** ——
## 音效快到 75ms 一步、羊还在按 0.44s 一跳，看起来就是羊在抽搐，那正是 COMBO 的反效果。
var pace: float = 1.0


var _sign_bold: Font = null     # 加粗版字体（FontVariation），懒建、只建一次
var _sign_lines: int = 1        # 目标实际排了几行（1 或 2）
# 提示纸条最后一次画出来的矩形。留在成员里不是为了复用，是为了**能被量**：
# 「纸条下沿不许压到地面木牌」这类断言，只有拿得到矩形才写得出来（见 tests/test_ui.gd）。
var _hint_rect := Rect2()

var _rng := RandomNumberGenerator.new()


func _ready() -> void:
	mouse_filter = Control.MOUSE_FILTER_IGNORE
	_rng.seed = 20261029
	stars.clear()
	for i in 30:
		stars.append({
			"x": _rng.randf_range(0.02, 0.98),
			"y": _rng.randf_range(0.04, 0.62),
			"r": _rng.randf_range(0.7, 1.8),
			"a": _rng.randf_range(0.25, 0.85),
		})
	resized.connect(func() -> void:
		worker_x = -1.0
		queue_redraw()
	)


func configure(level: Dictionary) -> void:
	slot_count = int(level.get("mem_size", 2))
	mem = []
	for i in slot_count:
		mem.append(0)
	hand = 0
	hand_full = false
	inbox_left = []
	for v in level.get("inbox", []):
		inbox_left.append(int(v))
	# 有些关（第 3 关「照抄一块」）根本不从 INBOX 拿数，羊圈开局就是空的。
	# 这和「跑完数空了」是两件事，玩家看到的时候要说清楚是哪一种 —— 不然像坏了。
	pen_starts_empty = inbox_left.is_empty()
	outbox = []
	expected_count = (level.get("outbox", []) as Array).size()
	highlight_slot = -1
	linked_slot = -1
	last_op = ""
	status = "idle"
	win_t = 0.0
	worker_x = -1.0
	target_key = "center"
	hop_t = -1.0
	fail_t = 0.0
	queue_redraw()


## 换关时把任务牌的三段内容一起塞进来。空字符串 = 那一行不画。
func set_task(goal: String, p_a: String, p_b: String) -> void:
	goal_text = goal
	stream_a = p_a
	stream_b = p_b
	hint_text = ""
	_sign_lines = 1
	queue_redraw()


## 玩家点了「看提示」才有。传空串收起。
func set_hint(t: String) -> void:
	hint_text = t
	queue_redraw()


## 编辑期联动：告诉舞台「当前选中的这行指着哪块木牌」。
## 传 -1（或越界值）表示这行不引用木牌 —— INBOX / OUTBOX 这类没有参数的行。
## 只在与上次不同时才重绘，避免每帧刷新白烧。
func link_slot(i: int) -> void:
	var v: int = i if (i >= 0 and i < slot_count) else -1
	if v == linked_slot:
		return
	linked_slot = v
	queue_redraw()


func sync_from_vm(vm) -> void:
	mem = vm.mem.duplicate()
	hand = vm.hand
	hand_full = vm.hand_full
	inbox_left = vm.inbox.duplicate()
	outbox = vm.outbox.duplicate()
	if vm.finished:
		if status != "done":
			win_t = 0.0      # 从「没通关」翻到「通关」的这一帧，庆祝动画从头开始
		status = "done"
	elif vm.failed:
		status = "error"
		if fail_t <= 0.0:
			fail_t = 0.001


func act(op: String, arg: Variant) -> void:
	last_op = op
	highlight_slot = -1
	match op:
		"INBOX":
			target_key = "pen"
		"OUTBOX":
			target_key = "fence"
			# 此刻 stage.hand 还是「推过去之前」的值，正好拿来当这只羊的编号
			hop_val = hand
			hop_from = worker_x if worker_x >= 0.0 else _key_x("fence")
			hop_t = 0.0
		"COPYFROM", "MOVETO", "ADD", "SUB", "BUMPUP", "BUMPDN":
			var i: int = int(arg) if arg != null else 0
			highlight_slot = i
			target_key = "slot:%d" % i
		_:
			pass
	if worker_x < 0.0:
		worker_x = _key_x(target_key)
	bump = 1.0


func _key_x(k: String) -> float:
	if k == "pen":
		return _pen_door_x()
	if k == "fence":
		return _fence_x() - 80.0
	if k.begins_with("slot:"):
		return _slot_center(int(k.substr(5)))
	return _center_x()


func _process(delta: float) -> void:
	# 所有动作共用这一个「节奏」：加速时羊走得更快、蹦得更急、木牌弹得更短。
	# 一个乘数管全部，比给每个动画各写一个速度要可靠 —— 加新动画时不会忘。
	var step: float = delta / clampf(pace, 0.26, 1.0)
	var target_x: float = _key_x(target_key)
	if worker_x < 0.0:
		worker_x = target_x
	var dx: float = target_x - worker_x
	moving = absf(dx) > 1.5
	if moving:
		facing = 1.0 if dx > 0.0 else -1.0
		worker_x = lerpf(worker_x, target_x, clampf(step * 8.5, 0.0, 1.0))
		phase += step * 12.0
	else:
		phase = 0.0
	bump = maxf(0.0, bump - step * 2.5)
	if hop_t >= 0.0 and pose_lock < 0.0:
		hop_t += step / HOP_TIME
		if hop_t >= 1.0:
			hop_t = -1.0
	if status == "error":
		fail_t += delta
	if status == "done":
		win_t += delta
	queue_redraw()


# ---------------------------------------------------------------- 坐标

func _floor_y() -> float:
	# 62 → 96：原来的地平线太高，天空占了舞台的 2/3、草地只有薄薄一条，
	# 羊像是走在栏杆上。舞台加高以后这个比例更明显，所以把地平线压下去。
	# 底部那条 16px 的 HUD 条已经删掉（信息全在栅栏挂牌和程序行上），
	# 所以 78 现在全是草皮 —— 比原来厚了 16px，羊和栅栏站得更稳。
	#
	# 窄屏改回 60：竖屏的草皮是「羊脚下的地面」，不是背景 ——
	# 78 在 268 高的舞台上等于 29% 的画幅全给了空草地，而上面编辑区正缺这 18px。
	return size.y - (78.0 if not _narrow() else 60.0)


func _center_x() -> float:
	return size.x * 0.5


# ---------------------------------------------------------------- 窄屏
#
# 桌面这条舞台是按 1252 宽画的：羊圈 26～180、木牌带 258～(w-258)、栅栏贴右 100。
# 竖屏只有 374 宽，照抄等于「羊圈吃掉一半、木牌带剩 8px」——
# 7 块木牌挤进 8px，多边形直接退化成一条线（Godot 报 triangulation failed）。
#
# 窄屏不是把桌面等比缩小（缩到 0.3 时 11px 的字就没了），而是**重新分配横向**：
# 羊圈只留 2 只羊（其余用 +N 表示），栅栏压到 88 宽，中间全给木牌。
const NARROW_W := 620.0


func _narrow() -> bool:
	return size.x < NARROW_W


func _pen_step() -> float:
	return 64.0 if not _narrow() else 26.0


func _pen_scale() -> float:
	return 1.72 if not _narrow() else 1.0


func _pen_show() -> int:
	# 窄屏只摆两只：羊是「还剩几只」的示意，不是队列长度 ——
	# 真正的数量在栅栏挂牌和面包屑上，多画 4 只只会把木牌挤没。
	return PEN_SHOW if not _narrow() else 2


func _pen_left() -> float:
	return 26.0 if not _narrow() else 8.0


func _pen_right() -> float:
	if not _narrow():
		return PEN_X + 48.0
	return _pen_left() + 14.0 + float(_pen_show()) * _pen_step() + 14.0


func _fence_left() -> float:
	return size.x - 192.0 if not _narrow() else size.x - 96.0


func _fence_right() -> float:
	return size.x - 92.0 if not _narrow() else size.x - 8.0


func _pen_door_x() -> float:
	# 站位要落在最后一只羊右边，否则牧羊人会挡住羊身上的编号
	return PEN_X + 70.0 if not _narrow() else _pen_right()


func _fence_x() -> float:
	return _fence_left() + 34.0


func _slot_area() -> Vector2:
	if not _narrow():
		return Vector2(258.0, size.x - 258.0)
	var x0: float = _pen_right() + 6.0
	var x1: float = _fence_left() - 6.0
	return Vector2(x0, maxf(x0 + 30.0, x1))


func _slot_w() -> float:
	var a: Vector2 = _slot_area()
	var n: int = maxi(1, slot_count)
	return minf(72.0, (a.y - a.x) / float(n))


func _slot_center(i: int) -> float:
	var a: Vector2 = _slot_area()
	var w: float = _slot_w()
	var total: float = w * float(slot_count)
	var start: float = (a.x + a.y) * 0.5 - total * 0.5
	return start + w * (float(i) + 0.5)


# ---------------------------------------------------------------- 绘制入口

func _draw() -> void:
	var w: float = size.x
	var h: float = size.y
	var fy: float = _floor_y()

	_draw_sky(w, fy)
	_draw_ground(w, fy, h)
	_draw_deco(w, fy)
	_draw_light_pool(w, fy)
	_draw_slots(fy)
	_draw_pen(fy)
	_draw_fence(fy)
	_draw_counted(fy)
	_draw_hop(fy)
	_draw_fireflies(w, fy)
	_draw_shepherd(fy)
	_draw_link_callout()
	# 任务牌排在最后：它是「提示层」，不该被任何一个场景物件盖住
	# （v13 那条教训 —— 木牌 N 对照牌被牧羊人盖过）。
	_draw_task_sign(w)
	if status == "done":
		_draw_win_fx(w, h, fy)


# ---------------------------------------------------------------- 场景

func _draw_sky(w: float, fy: float) -> void:
	# 渐变夜空：分段插值，避免依赖贴图
	var bands: int = 26
	for i in bands:
		var t: float = float(i) / float(bands - 1)
		var col: Color = C_SKY_TOP.lerp(C_SKY_BOT, t)
		draw_rect(Rect2(0, fy * t, w, fy / float(bands) + 1.0), col, true)

	# 白天了。星星这一层直接不要 —— 亮天空里画星星只会变成一片脏点。
	# 太阳：一圈圈向外递减的光晕 + 实心球。光晕依然要分层，
	# 单个半透明大圆会读成「贴了一张光盘」，这是夜景那版就验证过的教训。
	# 太阳往右上挪：任务牌占了 sky 的左上大半（width 的 0..0.775、y 4..66），
	# 原来 0.70 的位置正好被牌子盖住。现在它躲在牌子右边、栅栏挂牌上方那条空里。
	var sun := Vector2(w * 0.80, fy * 0.20)
	var glow: float = 0.22 if status != "done" else 0.34
	for i in 9:
		var gr: float = 17.0 + float(i) * 13.0
		var ga: float = glow * 0.26 * (1.0 - float(i) / 9.0)
		draw_circle(sun, gr, Color(1.0, 0.97, 0.72, ga))
	draw_circle(sun, 20.0, Color(1.0, 0.94, 0.55, glow * 0.55))
	draw_circle(sun, 15.0, Color("ffd94a") if status != "done" else Color("ffe98a"))
	draw_circle(sun + Vector2(-4, -4), 4.2, Color(1, 1, 0.86, 0.75))

	# 远山两层
	var far := PackedVector2Array([
		Vector2(0, fy), Vector2(0, fy - 34), Vector2(w * 0.13, fy - 56),
		Vector2(w * 0.26, fy - 30), Vector2(w * 0.40, fy - 50),
		Vector2(w * 0.55, fy - 26), Vector2(w * 0.70, fy - 46),
		Vector2(w * 0.85, fy - 22), Vector2(w, fy - 40), Vector2(w, fy),
	])
	draw_colored_polygon(far, C_HILL_FAR)
	var near := PackedVector2Array([
		Vector2(0, fy), Vector2(0, fy - 16), Vector2(w * 0.18, fy - 30),
		Vector2(w * 0.34, fy - 12), Vector2(w * 0.52, fy - 26),
		Vector2(w * 0.68, fy - 10), Vector2(w * 0.84, fy - 24),
		Vector2(w, fy - 12), Vector2(w, fy),
	])
	draw_colored_polygon(near, C_HILL_NEAR)

	# 云：白天要白，而且要有一点厚度（先垫一层淡蓝的底，再压一层白）
	# 云也压到任务牌下面那道缝里（牌底 66 → 山脊）。原来「天空很高」的构图
	# 是给抬头没任务说明时留的；现在天空的上半截是牌子，云只能贴在山脊上方。
	_cloud(Vector2(w * 0.30, fy * 0.62), 0.9)
	_cloud(Vector2(w * 0.60, fy * 0.56), 0.7)


func _cloud(c: Vector2, s: float) -> void:
	var shade := Color(0.80, 0.90, 0.98, 0.55)
	var white := Color(1.0, 1.0, 1.0, 0.92)
	for i in 4:
		draw_circle(c + Vector2(float(i) * 16.0 * s - 24.0 * s, -2.0 * s * float(i % 2) + 3.0 * s), 13.0 * s, shade)
	draw_circle(c + Vector2(0, 7), 15.0 * s, shade)
	for i in 4:
		draw_circle(c + Vector2(float(i) * 16.0 * s - 24.0 * s, -2.0 * s * float(i % 2)), 12.0 * s, white)
	draw_circle(c + Vector2(0, 4), 14.0 * s, white)


func _draw_ground(w: float, fy: float, h: float) -> void:
	# 草地分几段往下压暗：脚边亮、镜头前暗，画面立刻有了「纵深」，不再是一块色板
	var bands: int = 7
	for i in bands:
		var t: float = float(i) / float(bands - 1)
		var col: Color = C_GRASS.lerp(C_GRASS_D, t)
		draw_rect(Rect2(0, fy + (h - fy) * t, w, (h - fy) / float(bands) + 1.0), col, true)
	draw_rect(Rect2(0, fy, w, 3.0), Color("3f8a2b"), true)
	# 踩出来的一条小路：羊每天从羊圈被抱到栅栏，路是走出来的（顺带把中间的空草填掉）
	_ellipse(Vector2(w * 0.5, fy + 9.0), w * 0.44, 6.0, Color(0.86, 0.72, 0.42, 0.55))
	_ellipse(Vector2(w * 0.5, fy + 8.0), w * 0.30, 3.0, Color(0.93, 0.82, 0.55, 0.55))
	# 草丛
	var gx: float = 6.0
	var k: int = 0
	while gx < w:
		var hgt: float = 4.0 + float((k * 7) % 5)
		draw_line(Vector2(gx, fy + 6), Vector2(gx + 1.5, fy + 6 - hgt), C_GRASS_D, 1.0)
		draw_line(Vector2(gx + 3, fy + 8), Vector2(gx + 4.5, fy + 8 - hgt * 0.8), C_GRASS_D, 1.0)
		gx += 26.0
		k += 1


## 场景装饰：树、灌木、小花。
## 原来的舞台只有「天 + 山 + 草」三层，干净但空 —— 卡通场景的空气感是靠一堆小圆填出来的，
## 不是靠加细节线。这里全部用圆和矩形，零美术资源。
func _draw_deco(w: float, fy: float) -> void:
	# 树：树干 + 两团深绿 + 两团亮绿（亮绿往左上偏，读作受光）
	var trees := [[0.045, 1.15], [0.115, 0.85], [0.545, 0.95], [0.635, 0.72], [0.955, 1.05]]
	for t in trees:
		var bx: float = float(t[0]) * w
		var s: float = float(t[1])
		var by: float = fy - 2.0
		draw_rect(Rect2(bx - 3.0 * s, by - 18.0 * s, 6.0 * s, 20.0 * s), C_WOOD_D, true)
		draw_circle(Vector2(bx, by - 30.0 * s), 13.0 * s, Color("3f8a2b"))
		draw_circle(Vector2(bx - 9.0 * s, by - 22.0 * s), 9.0 * s, Color("3f8a2b"))
		draw_circle(Vector2(bx + 9.0 * s, by - 23.0 * s), 9.0 * s, Color("3f8a2b"))
		draw_circle(Vector2(bx - 3.0 * s, by - 33.0 * s), 10.0 * s, C_GRASS)
		draw_circle(Vector2(bx + 6.0 * s, by - 27.0 * s), 7.5 * s, C_GRASS)

	# 灌木：贴着地平线的一排半圆，把天和草的交界咬住
	var k := 0
	while k < 9:
		var bx: float = w * (0.06 + 0.112 * float(k))
		var r: float = 6.0 + float((k * 5) % 4)
		draw_circle(Vector2(bx, fy + 3.0), r, C_GRASS_D)
		draw_circle(Vector2(bx + r * 0.9, fy + 4.0), r * 0.72, C_GRASS_D)
		k += 1

	# 小花：白 / 黄小点，稀疏撒在草上
	var f := 0
	while f < 16:
		var fx: float = w * (0.03 + 0.061 * float(f))
		var fy2: float = fy + 16.0 + float((f * 13) % 24)
		var col := Color("fff0a0") if f % 2 == 0 else Color("ffffff")
		draw_circle(Vector2(fx, fy2), 1.7, col)
		draw_circle(Vector2(fx, fy2), 0.7, Color("e8a33c"))
		f += 1


## 光池：白天不需要「光落在哪里」的戏剧感，改成太阳在地上的两片柔光 +
## 牧羊人脚下的一圈接地影 —— 让角色和地面咬住，不要像贴纸浮在草地上。
func _draw_light_pool(w: float, fy: float) -> void:
	# 日光照在草地上的一片亮斑
	var mx: float = w * 0.70
	_ellipse(Vector2(mx, fy + 14.0), w * 0.22, 13.0, Color(1.0, 0.98, 0.80, 0.16))
	_ellipse(Vector2(mx, fy + 11.0), w * 0.13, 8.0, Color(1.0, 1.0, 0.88, 0.18))
	# 接地影：牧羊人脚下的一小片深绿，读作「站住了」
	var lx: float = worker_x if worker_x >= 0.0 else _center_x()
	for i in 4:
		var r: float = 14.0 + float(i) * 7.0
		_ellipse(Vector2(lx, fy + 5.0), r * 1.6, r * 0.30,
			Color(0.16, 0.34, 0.12, 0.13 * (1.0 - float(i) / 4.0)))


func _draw_slots(fy: float) -> void:
	var font: Font = get_theme_default_font()
	var sw: float = _slot_w()
	var pw: float = minf(sw * 0.94, 76.0)
	if pw < 8.0:
		# 宽度退化时一块都不画。宁可空着，也不要一个三角化失败的警告刷满控制台 ——
		# 那种错误不崩，但会把别的真错误淹掉。
		return
	var ph: float = 24.0 if not _narrow() else 22.0
	# 编号格跟着牌宽走：桌面固定 20 是因为牌有 60～72 宽，
	# 窄屏 7 块牌只剩 25 宽，还留 20 给编号，值就只剩 5px。
	var tag_w: float = minf(20.0, pw * 0.45)
	for i in slot_count:
		var cx: float = _slot_center(i)
		var on: bool = (i == highlight_slot)
		var linked: bool = (i == linked_slot) and not on
		# 被引用 / 正在用时整块牌子抬起来一点，是「它被点名了」最便宜的表达
		var lift: float = 3.0 if (on or linked) else 0.0
		var top: float = fy + 4.0 - lift
		var plate := Rect2(cx - pw * 0.5, top, pw, ph)
		# 牌子落在草地上（透视：略微下宽上窄）
		var pts := PackedVector2Array([
			Vector2(plate.position.x + 2.0, plate.position.y),
			Vector2(plate.end.x - 2.0, plate.position.y),
			Vector2(plate.end.x, plate.end.y),
			Vector2(plate.position.x, plate.end.y),
		])
		var fill: Color = C_WOOD
		if on:
			fill = C_WOOD.lerp(C_ACCENT, 0.5)
		# linked 不换底色：C_WOOD_L 会把奶油色数字压得看不清。
		# 「被引用」靠抬牌 + 白描边 + 头顶的「木牌 N」小牌来说，不靠改明度。
		draw_colored_polygon(pts, fill)
		pts.append(pts[0])
		var line: Color = C_WOOD_D
		var lw: float = 1.2
		if on:
			line = C_ACCENT
			lw = 2.0
		elif linked:
			line = Color("ffffff")
			lw = 2.6
		draw_polyline(pts, line, lw)

		# 左侧编号格：和「值」用不同的底分开。
		# 之前编号是飘在牌子左边的一枚 9px 灰字，结果玩家只看到值，看不到编号 ——
		# 参数的「木牌 4」对不上任何东西。现在编号是牌子上的一块，读作「第 4 块」。
		#
		# 第二轮反馈：「编号非常能识别，但和参数对不上」。所以编号格改成高对比的
		# 奶白底 + 深棕字（普通）／琥珀底 + 深棕字（被引用），
		# 不再用深底浅字 —— 深底在棕色木牌上会糊成一片。
		var tag_col: Color = TAG_FACE
		if on:
			tag_col = Color("fff0bd")
		elif linked:
			tag_col = C_ACCENT
		var tag_pts := PackedVector2Array([
			Vector2(plate.position.x + 2.0, plate.position.y),
			Vector2(plate.position.x + tag_w, plate.position.y),
			Vector2(plate.position.x + tag_w, plate.end.y),
			Vector2(plate.position.x, plate.end.y),
		])
		draw_colored_polygon(tag_pts, tag_col)
		draw_line(Vector2(plate.position.x + tag_w, plate.position.y + 1.0),
			Vector2(plate.position.x + tag_w, plate.end.y - 1.0), C_WOOD_D, 1.0)
		draw_string(font, Vector2(plate.position.x, plate.position.y + ph * 0.72),
			str(i), HORIZONTAL_ALIGNMENT_CENTER, tag_w, 13 if not _narrow() else 10, TAG_INK)

		# 值
		var v: int = int(mem[i]) if i < mem.size() else 0
		draw_string(font, Vector2(plate.position.x + tag_w, plate.position.y + ph * 0.76),
			str(v), HORIZONTAL_ALIGNMENT_CENTER, pw - tag_w, 15 if not _narrow() else 12,
			Color("3a2c14") if on else Color("fdf6e6"))

		# 关联提示（「木牌 N」小牌 + 三角）不在这里画 —— 见 _draw_link_callout()
		# 运行时高亮光晕
		if on:
			draw_rect(plate.grow(2.0), Color(C_ACCENT, 0.35 + bump * 0.4), false, 2.0)


## 编辑期联动提示：被选中行引用到的那块木牌，头顶挂一枚「木牌 N」小牌 + 指向三角。
## 只有白框 + 抬牌是不够的 —— 玩家看不出「它为什么抬起来」。
## 为什么要单独一趟、而且排在牧羊人之后：木牌在草地层，牧羊人站在牌子前面，
## 提示牌要是跟着木牌一起画，正中那块牌会被牧羊人的身子整个盖掉（截图里撞见过）。
func _draw_link_callout() -> void:
	if linked_slot < 0 or linked_slot >= slot_count:
		return
	var font: Font = get_theme_default_font()
	var cx: float = _slot_center(linked_slot)
	# linked 时整牌抬了 3px，提示牌跟着一起抬，否则三角会插进牌子里
	var ay: float = _floor_y() + 4.0 - 3.0 - 8.0
	var a: float = 0.70 + 0.30 * bump
	draw_colored_polygon(PackedVector2Array([
		Vector2(cx - 6.0, ay), Vector2(cx + 6.0, ay), Vector2(cx, ay + 7.0)]),
		Color(1, 1, 1, a))
	var txt: String = I18n.tf("木牌 %d", [linked_slot])
	var tw: float = font.get_string_size(txt, HORIZONTAL_ALIGNMENT_LEFT, -1, 11).x
	var pill := Rect2(cx - tw * 0.5 - 6.0, ay - 19.0, tw + 12.0, 16.0)
	draw_rect(pill, C_ACCENT, true)
	draw_rect(pill, TAG_INK, false, 1.0)
	draw_string(font, Vector2(pill.position.x, pill.position.y + 12.0), txt,
		HORIZONTAL_ALIGNMENT_CENTER, pill.size.x, 11, TAG_INK)


## 左边羊圈：待数的羊排成一队，编号直接刷在羊毛上
## 这里故意不画栏杆 —— 栏杆属于前景，会把羊身上的编号挡掉
func _draw_pen(fy: float) -> void:
	var font: Font = get_theme_default_font()
	var left: float = _pen_left()
	var right: float = _pen_right()
	var step: float = _pen_step()
	var s: float = _pen_scale()
	var show: int = mini(_pen_show(), inbox_left.size())

	# 圈地：只画一块被踩实的土，留出干净背景给编号
	_ellipse(Vector2((left + right) * 0.5, fy + 5.0),
		(right - left) * 0.60, 8.0, Color(0.90, 0.80, 0.58, 0.10))

	# 羊（每只身上写着它的编号）；间距给足，别让后一只的头挡住前一只的编号
	for k in show:
		var sx: float = left + 14.0 + float(k) * step
		var sy: float = fy - 24.0 - float(k % 2) * 3.0
		_draw_sheep_rot(Vector2(sx, sy), s, 1.0, 1.0, int(inbox_left[k]))

	# 标题 + 剩余。压在浅蓝天上，纯浅色字会消失，所以统一加深色描边。
	# 位置必须在羊头顶之上（羊是 fy-24 起、高约 52，头顶落在 fy-76）——
	# 原来写 fy-54，正好压在羊脸上，地平线下移以后更明显。
	#
	# 窄屏反过来：天空那一截已经被任务牌占满（3 行目标 = 99 高），
	# 标签再往头顶挂就压到牌子上了。所以窄屏把它挪到**羊脚下的草地上**——
	# 草地上除了草没有别的东西，是竖屏里唯一稳定的空白带。
	var lab_y: float = fy - 90.0 if not _narrow() else fy + 14.0
	var lab_fs: int = 11 if not _narrow() else 10
	draw_string_outline(font, Vector2(left, lab_y), I18n.t("羊圈 INBOX"),
		HORIZONTAL_ALIGNMENT_LEFT, 120, lab_fs, 3, Color(0.03, 0.18, 0.31, 0.85))
	draw_string(font, Vector2(left, lab_y), I18n.t("羊圈 INBOX"),
		HORIZONTAL_ALIGNMENT_LEFT, 120, lab_fs, C_TEXT)
	if inbox_left.is_empty():
		# 空羊圈要说清是哪一种空：题目本来就不给羊（第 3 关只搬木牌），还是刚数完了。
		# 第一版写的是 12px 无描边的「空了」，压在深绿草地上几乎看不见 ——
		# 达叔以为羊圈是坏的。字要跟「羊圈 INBOX」标题同一套处理：深色描边才浮得出来。
		var msg: String = I18n.t("这关不用数羊") if pen_starts_empty else I18n.t("羊都数完啦")
		draw_string_outline(font, Vector2(left, fy - 32.0), msg,
			HORIZONTAL_ALIGNMENT_LEFT, 220, 13, 3, Color(0.03, 0.18, 0.31, 0.85))
		draw_string(font, Vector2(left, fy - 32.0), msg,
			HORIZONTAL_ALIGNMENT_LEFT, 220, 13, Color(C_TEXT, 0.95))
	elif inbox_left.size() > _pen_show():
		draw_string(font, Vector2(right - 34, fy - 90.0), "+%d" % (inbox_left.size() - _pen_show()),
			HORIZONTAL_ALIGNMENT_RIGHT, 34, 12, C_ACCENT)


## 右边栅栏：羊要跳过去，旁边挂计数牌
func _draw_fence(fy: float) -> void:
	var font: Font = get_theme_default_font()
	var left: float = _fence_left()
	var right: float = _fence_right()
	# 栅栏高度必须跟着舞台高度走：原来写死 84，挂牌再往上挂 64，
	# 合计在 fy 之上 148px。舞台一旦低于这个高度，挂牌就会画到面板外面去
	# （2026-10-30 撞见过一次：牌子飘在编辑区上面）。
	# 66 是「fy 上方放得下挂牌 + 栅栏本身」的上限，挂牌改成压在栅栏顶内侧。
	# 窄屏栅栏矮一截：挂牌挂在栅栏顶上，而栅栏顶 + 挂牌 一共要在 fy 之上占 102。
	# 竖屏舞台只有 244 高，任务牌 103 + 这 102 就顶到天花板了 ——
	# 实测牌子被任务牌压掉一半（竖屏第一版，只剩「0 of 3」的下半行）。
	var fence_h: float = 66.0 if not _narrow() else 46.0
	var top: float = fy - fence_h

	# 挂牌：标题 + 计数合在一块，避免两块标牌叠字
	var done: int = outbox.size()
	var pw_plate: float = minf(88.0, right - left - 6.0)
	var plate := Rect2((left + right) * 0.5 - pw_plate * 0.5, top - 36.0, pw_plate, 34.0)
	draw_rect(plate, C_WOOD_D, true)
	draw_rect(plate, C_WOOD_L, false, 1.0)
	draw_string(font, Vector2(plate.position.x, plate.position.y + 12),
		I18n.t("栅栏 OUTBOX"), HORIZONTAL_ALIGNMENT_CENTER, plate.size.x, 9, C_MUTED)
	# 挂牌承担「已数多少 / 一共多少」。这两个数字原来在舞台底部的 HUD 条上，
	# 而那条 HUD 的另一半（「当前指令 X」）和程序行的绿边呼吸是同一件事 ——
	# 一条 16px 高的常驻横条，两条信息，一条重复一条搬得走。所以整条删掉了，
	# 计数搬到这里，舞台多出 16px 净空。
	draw_string(font, Vector2(plate.position.x, plate.position.y + 28),
		I18n.tf("已数 %d / %d", [done, expected_count]), HORIZONTAL_ALIGNMENT_CENTER, plate.size.x, 12,
		C_OK if done >= expected_count and expected_count > 0 else Color("f2e5c8"))
	# 两根吊线往下接到栅栏横杆上（牌子挂在栅栏外侧，不是飘在半空）
	draw_line(Vector2(plate.position.x + 10, plate.end.y), Vector2(plate.position.x + 10, top + 6.0),
		C_WOOD_L, 1.5)
	draw_line(Vector2(plate.end.x - 10, plate.end.y), Vector2(plate.end.x - 10, top + 6.0),
		C_WOOD_L, 1.5)

	# 横杆
	draw_line(Vector2(left, top), Vector2(right, top), C_WOOD, 3.5)
	draw_line(Vector2(left, fy - 30.0), Vector2(right, fy - 30.0), C_WOOD, 3.0)
	# 立柱
	var px: float = left
	while px <= right + 1.0:
		draw_line(Vector2(px, top - 6.0), Vector2(px, fy + 2.0), C_WOOD_L, 4.5)
		px += 26.0
	draw_line(Vector2(right, top - 6.0), Vector2(right, fy + 2.0), C_WOOD_L, 4.5)



## 已经数过的羊：站在栅栏另一边，是「数羊」这件事的成果展示
func _draw_counted(fy: float) -> void:
	var n: int = outbox.size()
	if n <= 0:
		return
	var font: Font = get_theme_default_font()
	var base_x: float = (size.x - 84.0) if not _narrow() else (_fence_left() + 4.0)
	var step: float = 24.0 if not _narrow() else 18.0
	var show: int = mini(3, n)
	for k in show:
		var sx: float = base_x + float(k) * step
		# 通关后栅栏里的羊一起蹦。相位按 k 错开 —— 三只同相就是一块板子在上下弹。
		var hop: float = 0.0
		if status == "done":
			hop = -absf(sin(win_t * 5.2 + float(k) * 0.95)) * 7.0
		_draw_sheep(Vector2(sx, fy - 16.0 - float(k % 2) * 4.0 + hop), 1.0, -1.0)
	if n > 3:
		draw_string(font, Vector2(base_x - 12, fy - 34),
			"+%d" % (n - 3), HORIZONTAL_ALIGNMENT_CENTER, 40, 10, C_OK)


## 萤火虫：整块画面里唯一会动的东西，负责「这是活着的夜晚」
## 白天不画萤火虫，改成几只飘过的蝴蝶 —— 会动的小东西是「场景活着」最便宜的证明，
## 白天用蝴蝶，晚上才用萤火虫。
func _draw_fireflies(w: float, fy: float) -> void:
	var t: float = Time.get_ticks_msec() / 1000.0
	var cols := [Color("fff3a8"), Color("ffffff"), Color("ffd2e8")]
	for i in 3:
		var fi: float = float(i)
		var x: float = fmod(w * (0.20 + fi * 0.26) + sin(t * 0.55 + fi * 2.1) * 34.0, w)
		var y: float = fy - 34.0 - 16.0 * float(i) - sin(t * 1.3 + fi) * 10.0
		var flap: float = absf(sin(t * 7.0 + fi * 2.0))
		var c: Color = cols[i % cols.size()]
		draw_circle(Vector2(x - 2.2, y), 2.4 * flap + 0.6, c)
		draw_circle(Vector2(x + 2.2, y), 2.4 * flap + 0.6, c)
		draw_circle(Vector2(x, y), 1.1, Color("4a3a22"))


## 跳跃中的羊：一条抛物线飞过栅栏
func _draw_hop(fy: float) -> void:
	if hop_t < 0.0:
		return
	var t: float = clampf(hop_t, 0.0, 1.0)
	var from_x: float = hop_from
	var to_x: float = _fence_x() + 40.0
	var x: float = lerpf(from_x, to_x, t)
	var y: float = fy - 4.0 * HOP_H * t * (1.0 - t) - 26.0
	var s: float = lerpf(0.95, 0.72, t)
	var tilt: float = lerpf(-0.35, 0.35, t)
	_draw_sheep_rot(Vector2(x, y), s, 1.0, 1.0 + tilt, hop_val)


# ---------------------------------------------------------------- 羊 / 牧羊人

func _ellipse(c: Vector2, rx: float, ry: float, col: Color) -> void:
	var pts := PackedVector2Array()
	for i in 18:
		var a: float = TAU * float(i) / 18.0
		pts.append(c + Vector2(cos(a) * rx, sin(a) * ry))
	draw_colored_polygon(pts, col)


func _draw_sheep(c: Vector2, s: float, dir: float = 1.0, rot: float = 0.0, num: Variant = null) -> void:
	_draw_sheep_rot(c, s, dir, rot, num)


## rot = 1.0 表示正常，>1 表示头朝下（绊倒）；num 非空时把编号直接刷在羊毛上
func _draw_sheep_rot(c: Vector2, s: float, dir: float, _rot: float, num: Variant = null) -> void:
	# 小尺寸下细节会糊，所以只保留「白身体 + 黑脸 + 四腿」这三样最强的识别特征
	# 影子
	var ground_y: float = c.y + 13.0 * s
	_ellipse(Vector2(c.x, ground_y), 11.0 * s, 3.0 * s, Color(0, 0, 0, 0.18))
	# 腿（加粗加长，才有「站着」的感觉）
	for i in 2:
		var lx: float = c.x + (float(i) * 2.0 - 1.0) * 5.5 * s
		draw_line(Vector2(lx, c.y + 2.0 * s), Vector2(lx, c.y + 12.5 * s), C_FACE, 2.8 * s)
	# 身体：扁而宽，深色描边 + 白色填充
	_ellipse(c + Vector2(0, -1) * s, 12.6 * s, 7.4 * s, C_FACE)
	_ellipse(c + Vector2(0, -1) * s, 11.4 * s, 6.2 * s, C_WOOL)
	# 羊毛起伏（三个凸包，制造云朵感）
	draw_circle(c + Vector2(-6.0, -6.0) * s, 4.4 * s, C_WOOL)
	draw_circle(c + Vector2(0.0, -8.0) * s, 4.8 * s, C_WOOL)
	draw_circle(c + Vector2(6.0, -6.0) * s, 4.4 * s, C_WOOL)
	# 尾巴
	_ellipse(c + Vector2(-12.5 * dir, -3.0) * s, 3.0 * s, 3.4 * s, C_FACE)
	# 头：比原来更大、更靠前下方，是识别「羊」的关键
	var head: Vector2 = c + Vector2(11.5 * dir, -1.5) * s
	_ellipse(head, 6.6 * s, 7.4 * s, C_FACE)
	# 耳朵：向两侧横出
	_ellipse(head + Vector2(-3.5 * dir, -4.8) * s, 4.6 * s, 2.4 * s, C_FACE)
	# 眼睛（先画头，再在头顶压一小团羊毛 —— 没有这团毛，黑脸大圆会读成熊猫）
	draw_circle(head + Vector2(2.6 * dir, -2.2) * s, 1.7 * s, C_WOOL)
	# 鼻头
	_ellipse(head + Vector2(4.4 * dir, 2.6) * s, 1.8 * s, 1.3 * s, Color("221f1b"))
	draw_circle(head + Vector2(-1.0 * dir, -6.2) * s, 3.4 * s, C_WOOL)
	draw_circle(head + Vector2(2.6 * dir, -6.6) * s, 2.6 * s, C_WOOL)

	if num != null:
		_draw_sheep_number(c, s, str(num))


## 编号写在羊毛中央：羊毛是浅色，深字直接可读，比挂在头顶的牌子清楚。
## 描边只能 1px —— 之前给到 2px，浅色描边在小字号下把字几乎吃掉了，远看就是一团白。
func _draw_sheep_number(c: Vector2, s: float, txt: String) -> void:
	var font: Font = get_theme_default_font()
	var fs: int = int(clampf(13.0 * s, 11.0, 20.0))
	if txt.length() > 2:
		fs = maxi(10, int(float(fs) * 0.78))
	var w: float = 18.0 * s
	var ctr := Vector2(c.x - 3.0 * s, c.y - 2.0 * s)
	var p := Vector2(ctr.x - w * 0.5, ctr.y + float(fs) * 0.36)
	draw_string_outline(font, p, txt, HORIZONTAL_ALIGNMENT_CENTER, w, fs, 1, Color(1, 1, 1, 0.85))
	draw_string(font, p, txt, HORIZONTAL_ALIGNMENT_CENTER, w, fs, Color("2a2118"))


## 牧羊人：睡衣 + 抱着羊 + 头顶号码
func _draw_shepherd(fy: float) -> void:
	var font: Font = get_theme_default_font()
	var x: float = worker_x
	var y: float = fy + 2.0
	var s: float = WORKER_SCALE
	var swing: float = sin(phase) * 4.5
	var bob: float = -absf(sin(phase)) * 2.0

	# 影子
	_ellipse(Vector2(x, y + 1), 14.0 * s, 4.0 * s, Color(0, 0, 0, 0.25))

	# 腿
	draw_rect(Rect2(x - 8.0 * s + swing * 0.5, y - 14.0 * s, 5.5 * s, 14.0 * s), C_PJ.darkened(0.15), true)
	draw_rect(Rect2(x + 2.5 * s - swing * 0.5, y - 14.0 * s, 5.5 * s, 14.0 * s), C_PJ.darkened(0.15), true)

	# 身体（睡衣）
	var body := Rect2(x - 10.0 * s, y - 33.0 * s + bob, 20.0 * s, 20.0 * s)
	draw_rect(body, C_PJ, true)
	# 睡衣条纹
	for i in 3:
		var ly: float = body.position.y + 4.5 * s + float(i) * 5.0 * s
		draw_line(Vector2(body.position.x + 1, ly), Vector2(body.end.x - 1, ly), C_PJ2, 1.6 * s)

	# 头
	var head := Vector2(x, y - 41.0 * s + bob)
	draw_circle(head, 8.0 * s, C_SKIN)
	# 头发（乱糟糟的睡相）
	draw_rect(Rect2(head.x - 8.0 * s, head.y - 8.5 * s, 16.0 * s, 4.0 * s), Color("3b2f26"), true)
	draw_circle(Vector2(head.x - 5 * s, head.y - 9 * s), 2.6 * s, Color("3b2f26"))
	draw_circle(Vector2(head.x + 4 * s, head.y - 10 * s), 2.2 * s, Color("3b2f26"))
	# 眼睛（困）
	draw_circle(Vector2(head.x - 2.8 * s + facing * 1.2 * s, head.y + 1.2 * s), 1.2 * s, Color("2a2a2a"))
	draw_circle(Vector2(head.x + 2.8 * s + facing * 1.2 * s, head.y + 1.2 * s), 1.2 * s, Color("2a2a2a"))

	# 怀里抱着的羊
	if hand_full:
		_draw_sheep(Vector2(x + facing * 2.0 * s, y - 19.0 * s + bob), 1.16, facing, 1.0, hand)

	# 头顶号码：手上有值时才显示，字号够大才看得清
	if hand_full:
		var plate := Rect2(x - 13.0 * s, y - 67.0 * s + bob, 26.0 * s, 15.0 * s)
		draw_rect(plate, Color("2a2216"), true)
		draw_rect(plate, C_ACCENT, false, 1.2)
		draw_string(font, Vector2(plate.position.x, plate.position.y + 11),
			str(hand), HORIZONTAL_ALIGNMENT_CENTER, plate.size.x, 10, C_ACCENT)

	# 状态
	if status == "done":
		# 睡着了：三个 z 从头顶飘起来
		var tt: float = Time.get_ticks_msec() / 1000.0
		for i in 3:
			var zt: float = fmod(tt * 0.5 + float(i) * 0.33, 1.0)
			draw_string(font, Vector2(x + 12.0 + zt * 16.0, y - 58.0 * s - zt * 34.0),
				"z", HORIZONTAL_ALIGNMENT_LEFT, 24, 11 + i * 3,
				Color(0.85, 0.92, 1.0, 1.0 - zt))
	elif status == "error":
		# 绊倒的羊：贴在栅栏边，四脚朝天
		var fx: float = _fence_x() - 6.0
		var fy2: float = fy - 10.0
		draw_set_transform(Vector2(fx, fy2), PI * 0.72, Vector2.ONE)
		_draw_sheep(Vector2.ZERO, 0.8, 1.0)
		draw_set_transform(Vector2.ZERO, 0.0, Vector2.ONE)
		# 头上的星星
		for i in 3:
			var a: float = phase * 2.0 + TAU * float(i) / 3.0
			draw_circle(Vector2(fx, fy2 - 16.0) + Vector2(cos(a), sin(a) * 0.5) * 13.0,
				1.8, C_ACCENT)
		var pr2 := Rect2(x - 31.0, y - 72.0 * s + bob, 62.0, 20.0)
		draw_rect(pr2, C_ERR.darkened(0.62), true)
		draw_rect(pr2, C_ERR, false, 1.0)
		draw_string(font, Vector2(pr2.position.x, pr2.position.y + 15),
			I18n.t("绊倒了"), HORIZONTAL_ALIGNMENT_CENTER, pr2.size.x, 11, C_ERR)


# ---------------------------------------------------------------- 通关庆祝

## 确定性伪随机：同一个 i 永远得到同一个 [0,1) 值。
##
## 为什么不用 randf()：_draw 每帧都跑，randf() 每帧给一个新数，
## 彩纸就会在屏幕上原地乱抖（看起来像信号干扰，不像纸片在飞）。
## 彩纸的「随机」必须是——同一片纸永远走同一条抛物线。
func _hash01(i: int) -> float:
	var x: float = sin(float(i) * 12.9898) * 43758.5453
	return x - floor(x)


## 通关庆祝：两处炮口喷彩纸 + 栅栏顶炸一枚星爆。
##
## 设计上的三个决定：
## 1. **不用 Particle 节点**，全部 _draw 现算：和场景其它部分走同一条渲染路径，
##    截图脚本才能稳定拍到（粒子系统有时候要等一帧才吐第一帧，截图会拍到空画面）。
## 2. **彩纸落地不消失**，留在草地上。通关后玩家可能盯着结算卡发呆好几秒，
##    画面应该是「庆祝正在进行」，而不是「庆祝已经结束，只剩一地冷清」。
## 3. **炮口有两个**（栅栏顶 + 羊圈顶），不是全屏乱喷。全屏喷是「放烟花」，
##    两个炮口是「两个环节一起完成了」—— 把庆祝绑在场景里的物件上，别绑在屏幕上。
func _draw_win_fx(w: float, h: float, fy: float) -> void:
	const N := 64
	const G := 900.0
	var cols := [Color("ff5a5a"), Color("ffd93d"), Color("4ecdc4"),
		Color("7ad1ff"), Color("ffffff"), Color("ff9de2")]
	for i in N:
		var r1: float = _hash01(i * 7 + 1)
		var r2: float = _hash01(i * 7 + 2)
		var r3: float = _hash01(i * 7 + 3)
		var from_fence: bool = r1 < 0.62
		var p0 := Vector2((_fence_x() + 44.0) if from_fence else (PEN_X + 34.0), fy - 34.0)
		var ang: float = -PI * 0.5 + (r2 - 0.5) * 2.3
		var spd: float = 250.0 + r3 * 360.0
		var vel := Vector2(cos(ang), sin(ang)) * spd
		# 每片纸错开一点点出发，才像「一喷」而不是「一面墙」
		var t: float = maxf(0.0, win_t - r2 * 0.22)
		var y_free: float = p0.y + vel.y * t + 0.5 * G * t * t
		var floor_y: float = fy - 3.0 - (1.0 - r3) * 3.0
		var pp: Vector2
		var tl: float
		if y_free >= floor_y:
			# 求落地时刻，之后原地趴着
			tl = (-vel.y + sqrt(maxf(0.0, vel.y * vel.y + 2.0 * G * (floor_y - p0.y)))) / G
			pp = Vector2(p0.x + vel.x * tl, floor_y)
		else:
			tl = t
			pp = Vector2(p0.x + vel.x * t, y_free)
		var rot: float = (r3 - 0.5) * 9.0 * tl
		var cw: float = 3.4
		var ch: float = 6.2
		var cs: float = cos(rot)
		var sn: float = sin(rot)
		draw_colored_polygon(PackedVector2Array([
			pp + Vector2(-cw * cs + ch * sn, -cw * sn - ch * cs),
			pp + Vector2(cw * cs + ch * sn, cw * sn - ch * cs),
			pp + Vector2(cw * cs - ch * sn, cw * sn + ch * cs),
			pp + Vector2(-cw * cs - ch * sn, -cw * sn + ch * cs),
		]), cols[i % cols.size()])

	# 星爆：只在头 0.8 秒。它是「刚刚发生了什么」的惊叹号，
	# 不是背景装饰 —— 过了那一瞬就该退场，否则会一直抢彩纸的戏。
	if win_t < 0.95:
		var k: float = clampf(win_t / 0.8, 0.0, 1.0)
		var c := Vector2(_fence_x() + 26.0, fy - 48.0)
		for i in 14:
			var a: float = TAU * float(i) / 14.0
			var rr: float = 16.0 + k * 64.0
			var fade: float = 1.0 - k
			draw_circle(c + Vector2(cos(a), sin(a) * 0.85) * rr,
				3.2 * fade + 0.7, Color(1.0, 0.88, 0.3, fade))


# ---------------------------------------------------------------- 任务牌
#
# 一块挂在舞台顶上的木牌，写「这一关要干什么」和「进什么 → 出什么」。
#
# 为什么从抬头搬下来：抬头那一条只有 56 高，字只能压到 12–13px，而且它离
# 玩家的视线中心（牧场）最远。最该第一时间读到的一句话，是全屏最小最远的一行字——
# 这跟「游戏用物体组织信息」正好相反。搬下来以后它是**一块牌子**：有厚边、
# 有钉子、有影子，17px 加粗，眼睛先看到「有个东西」，再读上面的字。

const SIGN_X0 := 12.0
const SIGN_W_RATIO := 0.775     # 占舞台宽的比例，右边留给太阳和栅栏挂牌
const SIGN_TOP := 4.0
const SIGN_PAD := 20.0
const SIGN_BOLD_FUDGE := 1.09   # 加粗字实际画出来比量出来宽约 8%（见 _draw_task_sign）
const SIGN_LH := 21.0           # 目标行高
const SIGN_GOAL_SIZE := 17
const SIGN_INK := Color("42301a")
const SIGN_SUB := Color("8a7350")
const SIGN_IN := Color("a8640f")     # 数字要压深一档，否则浅纸上黄字读不出来
const SIGN_OUT := Color("2c7610")
const NOTE_TEXT_X := 50.0       # 纸条正文起点：左边要让给那枚「提示」小黄签
const NOTE_MAX_LINES := 5       # 5 而不是 4：第 6 关英文提示按 4 行排会被截掉关键那句
const NOTE_GAP := 10.0          # 纸条下沿与地面那排木牌的最小间距
const NOTE_TOP_GAP := 8.0       # 纸条上沿离任务牌下沿


func _draw_task_sign(w: float) -> void:
	if goal_text == "":
		return
	var font: Font = get_theme_default_font()
	if _sign_bold == null:
		# 项目没有粗体字重，用 FontVariation 现场加粗。
		# 9 级灰的正文用不着粗体，但「本关目标」是全局唯一必须抢眼的一行字。
		var fv := FontVariation.new()
		fv.base_font = font
		fv.variation_embolden = 0.55
		_sign_bold = fv

	# 牌子宽度按内容量出来，不写死。写死的宽牌子上，短目标会变成
	# 「一大片奶油色中间嵌着一行小字」—— 空的地方比字还显眼。
	# 量的时候按最大可用宽折行，再取最长那一行 + 左右留白，最后夹在 [560, 上限] 里。
	# 折行和量宽一律用**基础字体**，不用加粗的那一版：
	# FontVariation 的 embolden 只加在笔画上、不进 advance，于是
	# 「量出来 660、画出来 682」—— 按它量出来的宽度做牌子，字就贴着边。
	# 差的这部分按 9% 补（实测 8% 上下），画的时候照旧用加粗版。
	var lines: Array = goal_lines(font, w, goal_text)
	_sign_lines = maxi(1, lines.size())
	var ph: float = sign_h(_sign_lines)
	var max_w: float = _sign_max_w(w)
	var fs: int = _goal_fs()

	var widest: float = 0.0
	for ln in lines:
		widest = maxf(widest, font.get_string_size(
			String(ln), HORIZONTAL_ALIGNMENT_LEFT, -1, fs).x)
	widest = maxf(widest, _segs_width(font, _stream_segs()))
	# ⚠ 下界也要跟着 max_w 走。原来写死 560 当下界，窄屏时 max_w=350，
	# clampf(v, 560, 350) 是一个**下界大于上界**的区间 —— Godot 的实现会返回下界 560，
	# 于是牌子比舞台还宽，整块从右边溢出屏幕（竖屏第一版就撞在这儿）。
	var pw: float = clampf(widest * SIGN_BOLD_FUDGE + SIGN_PAD * 2.0, minf(560.0, max_w), max_w)

	var r := Rect2(SIGN_X0, SIGN_TOP, pw, ph)
	# 硬投影：牌子要「钉在」天空上，不能像一张贴纸浮着
	var sh := StyleBoxFlat.new()
	sh.bg_color = Color(0.16, 0.12, 0.05, 0.22)
	sh.set_corner_radius_all(9)
	sh.anti_aliasing = true
	draw_style_box(sh, Rect2(r.position + Vector2(0.0, 3.0), r.size))

	var sb := StyleBoxFlat.new()
	sb.bg_color = TAG_FACE
	sb.border_color = C_WOOD_D
	sb.set_border_width_all(2)
	sb.set_corner_radius_all(9)
	sb.anti_aliasing = true
	draw_style_box(sb, r)

	# 两枚钉子：把「这是一块挂上去的板子」说清楚，比加任何装饰都便宜
	for nx in [r.position.x + 13.0, r.end.x - 13.0]:
		draw_circle(Vector2(nx, r.position.y + 11.0), 3.0, C_WOOD_D)
		draw_circle(Vector2(nx - 0.8, r.position.y + 10.2), 1.1, Color(1, 1, 1, 0.6))

	# 目标：居中、深墨、加粗。这是全屏唯一一处「必须第一眼读到」的字
	var by: float = r.position.y + 9.0 + 16.0
	for i in lines.size():
		draw_string(_sign_bold, Vector2(r.position.x, by + SIGN_LH * float(i)),
			String(lines[i]), HORIZONTAL_ALIGNMENT_CENTER, r.size.x,
			fs, SIGN_INK)

	# 数据流：进什么 → 出什么，压在同一块牌子的第二行
	var sy: float = r.position.y + 9.0 + SIGN_LH * float(_sign_lines) + 13.0
	var segs: Array = _stream_segs()
	if not segs.is_empty():
		_draw_centered_segs(font, segs, r.position.x + SIGN_PAD, pw - SIGN_PAD * 2.0, sy, 0.0)

	if hint_text != "":
		_draw_hint_note(font, w, r.end.y + NOTE_TOP_GAP)


## 目标字号：窄屏降一档。牌子宽度只有 350 的时候，17px 加粗的中文只要 9 个字就满行，
## 英文目标句子得折成 4 行 —— 而舞台高度是有限的那一项，宁可字小一点也要少一行。
func _goal_fs() -> int:
	return SIGN_GOAL_SIZE if not _narrow() else 14


## 任务牌的目标折行。抽成静态纯函数：牌子的高度和纸条的起点都由它决定，
## 而「纸条有没有压到地面木牌」这件事得能在**没有渲染帧**的时候量出来（单测用它）。
static func goal_lines(font: Font, w: float, goal: String) -> Array:
	var narrow: bool = w < NARROW_W
	var fs: int = SIGN_GOAL_SIZE if not narrow else 14
	var inner: float = (_sign_max_w(w) - SIGN_PAD * 2.0) / SIGN_BOLD_FUDGE
	# 窄屏放开到 3 行：2 行 + 省略号会把「进什么出什么」那半句吃掉
	return _wrap_chars(font, goal, fs, inner, 2 if not narrow else 3)


## 牌子宽度上限：右边要留给太阳和栅栏挂牌，但窗口太窄时得整个人占满。
static func _sign_max_w(w: float) -> float:
	var m: float = w * SIGN_W_RATIO - SIGN_X0
	if m < 300.0:
		m = maxf(240.0, w - 2.0 * SIGN_X0)
	return m


## 牌子高度 = 上留白 9 + 目标行 + 数据流行 18 + 下留白 9。
## 一行时 57、两行时 78 —— 由折行结果唯一决定，同一关里永远同一个高度。
static func sign_h(n_lines: int) -> float:
	return 9.0 + SIGN_LH * float(maxi(1, n_lines)) + 18.0 + 9.0


## 纸条起点：任务牌下沿往下 8。
static func note_top(font: Font, w: float, goal: String) -> float:
	return SIGN_TOP + sign_h(goal_lines(font, w, goal).size()) + NOTE_TOP_GAP


## 数据流压成一行：「INBOX 4  →  OUTBOX 4, 3, 2, 1, 10」。
## 标签小、数字大而且上色 —— 颜色 + 位置双通道，不只靠颜色。
func _stream_segs() -> Array:
	var segs: Array = []
	if stream_a != "":
		segs.append(["INBOX", 10, SIGN_SUB])
		segs.append(["  " + stream_a, 13, SIGN_IN])
	if stream_a != "" and stream_b != "":
		segs.append(["    →    ", 12, SIGN_SUB])
	if stream_b != "":
		segs.append(["OUTBOX", 10, SIGN_SUB])
		segs.append(["  " + stream_b, 13, SIGN_OUT])
	return segs


func _segs_width(font: Font, segs: Array) -> float:
	var total: float = 0.0
	for s in segs:
		total += font.get_string_size(String(s[0]), HORIZONTAL_ALIGNMENT_LEFT, -1, int(s[1])).x
	return total


## 一串「大小/颜色各不相同」的片段，整体居中画在一行上。
## 数据流就是这样：标签要小、数字要大而且要上色 —— 用 RichTextLabel 干这活
## 就得往场景里塞一个控件，而这里只是一行字。
func _draw_centered_segs(font: Font, segs: Array, x0: float, width: float, baseline: float, gap: float) -> void:
	var total: float = 0.0
	for s in segs:
		total += font.get_string_size(String(s[0]), HORIZONTAL_ALIGNMENT_LEFT, -1, int(s[1])).x
	total += gap * float(maxi(0, segs.size() - 1))
	var x: float = x0 + (width - total) * 0.5
	for s in segs:
		var t: String = String(s[0])
		var fs: int = int(s[1])
		draw_string(font, Vector2(x, baseline), t, HORIZONTAL_ALIGNMENT_LEFT, -1, fs, s[2])
		x += font.get_string_size(t, HORIZONTAL_ALIGNMENT_LEFT, -1, fs).x + gap


## 提示纸条：只在玩家点了「看提示」之后挂出来，贴在任务牌下沿。
## 它不进布局，所以不会把任何东西顶走 —— 这是「玩家自己叫出来的东西」该有的样子。
func _draw_hint_note(font: Font, w: float, top: float) -> void:
	var g: Dictionary = hint_layout(font, w, _floor_y(), top, hint_text)
	var r: Rect2 = g["rect"]
	var lines: Array = g["lines"]
	_hint_rect = r
	var sb := StyleBoxFlat.new()
	sb.bg_color = Color("fdf3dc")
	sb.border_color = Color("c99a52")
	sb.set_border_width_all(1)
	sb.set_corner_radius_all(7)
	sb.anti_aliasing = true
	draw_style_box(sb, r)
	# 左上角一枚小黄签，标出「这是提示，不是任务」
	# 小黄签和第一行文字**同一条基线**：它说明的是「这一整块是提示」，
	# 不是「下面那一行是提示」，所以不该自己占一行。
	var chip := Rect2(r.position.x + 10.0, r.position.y + 11.0, 32.0, 15.0)
	draw_rect(chip, C_ACCENT, true)
	draw_rect(chip, Color("b8862d"), false, 1.0)
	draw_string(font, Vector2(chip.position.x, chip.position.y + 12.0), I18n.t("提示"),
		HORIZONTAL_ALIGNMENT_CENTER, chip.size.x, 10, TAG_INK)
	for i in lines.size():
		draw_string(font, Vector2(r.position.x + NOTE_TEXT_X, r.position.y + 24.0 + 19.0 * float(i)),
			String(lines[i]), HORIZONTAL_ALIGNMENT_LEFT, float(g["text_w"]), 13, Color("5e451f"))


## 纸条的几何：宽度阶梯 → 折行 → 最终矩形。**不画，只算。**
## 抽成静态纯函数有两个理由：
## ① 单测要在没有渲染帧的情况下量它（「下沿压没压到木牌」只能靠量，截图看不出那几像素）；
## ② 高度必须可预测，否则纸条一抖，下面整片场景跟着抖。
##
## 纸条放不放得下，取决于两件互不相干的事：高度由「折成几行」决定，
## 而往下能用到哪里由**窗口高度**决定（fy = size.y - 78）。
## 第一版把宽度写死 700：1280×800 上正好只剩 5px 缝，窗口一矮就直接压在木牌上
## —— 又一处「写死常量 vs 会变的舞台高度」。
## 解法不是把纸条往上挤（上面就是任务牌），而是**横着长**：宽度按阶梯往上试，
## 取第一个竖着放得下的。天空比地面富余得多，「更宽」永远比「更高」便宜。
static func hint_layout(font: Font, w: float, fy: float, top: float, text: String) -> Dictionary:
	var room: float = fy - NOTE_GAP - top
	var limit_w: float = w - SIGN_X0 - 30.0
	var nw: float = limit_w
	var lines: Array = []
	for cand in [minf(w * 0.56, 700.0), minf(w * 0.72, 880.0), limit_w]:
		nw = minf(cand, limit_w)
		lines = _wrap_chars(font, text, 13, maxf(120.0, nw - NOTE_TEXT_X - 16.0), NOTE_MAX_LINES)
		if _note_h(lines.size()) <= room:
			break
	return {
		"rect": Rect2(SIGN_X0 + 6.0, top, nw, _note_h(lines.size())),
		"lines": lines,
		"text_w": maxf(120.0, nw - NOTE_TEXT_X - 16.0),
	}


## 纸条高度 = 上留白 9 + 行高 19 × 行数 + 下留白 9。
## 由折行结果唯一决定 —— 与任务牌同一个道理：高度必须是可预测的，否则整片场景跟着抖。
static func _note_h(n: int) -> float:
	return 9.0 + 19.0 * float(maxi(1, n)) + 9.0


## 折行。中文一个字一个字排；**英文按词排** ——
## 按字排会把「accumulator」切成「accumulat / or.」，中文读者看不出来，
## 英文读者一眼就知道这游戏没做过英文。
## 超过 max_lines 就截断加省略号。
## 抽成静态纯函数是因为「目标牌的高度必须可预测」——高度完全由这里返回几行决定。
static func _wrap_chars(font: Font, text: String, fs: int, max_w: float, max_lines: int) -> Array:
	var lines: Array = []
	var cur: String = ""
	var truncated: bool = false
	var i: int = 0
	var n: int = text.length()
	while i < n:
		var ch: String = text[i]
		if ch == "\n":
			i += 1
			lines.append(cur)
			cur = ""
			if lines.size() >= max_lines:
				truncated = i < n
				break
			continue
		# 一个「排版单位」：拉丁字母/数字整个词算一格（连它后面的空格），
		# 其余（汉字、标点）一个字算一格。
		var piece: String = ""
		if _is_word_char(ch):
			while i < n and _is_word_char(text[i]):
				piece += text[i]
				i += 1
			while i < n and text[i] == " ":
				piece += text[i]
				i += 1
		else:
			piece = ch
			i += 1
		if cur.strip_edges() != "" and _width(font, cur + piece, fs) > max_w:
			lines.append(cur.strip_edges(false, true))     # 行尾空格不算进版面
			cur = piece.strip_edges(true, false)           # 行首也不留空格
			if lines.size() >= max_lines:
				truncated = true
				cur = ""
				break
		else:
			cur += piece
	if cur != "" and lines.size() < max_lines:
		lines.append(cur)
	if truncated and not lines.is_empty():
		lines[lines.size() - 1] = String(lines[lines.size() - 1]).strip_edges(false, true) + "…"
	return lines


static func _width(font: Font, s: String, fs: int) -> float:
	return font.get_string_size(s, HORIZONTAL_ALIGNMENT_LEFT, -1, fs).x


## 什么算「词里的字」：字母、数字、词内撇号。汉字不算（要逐字排）。
## 撇号要算进词里，否则 "don't" 会被断成 "don" + "'t"。
static func _is_word_char(ch: String) -> bool:
	if ch.is_empty():
		return false
	var c: int = ch.unicode_at(0)
	if (c >= 65 and c <= 90) or (c >= 97 and c <= 122) or (c >= 48 and c <= 57):
		return true
	return c == 0x27 or c == 0x2019

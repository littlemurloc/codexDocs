extends SceneTree

const I18n = preload("res://scripts/i18n.gd")

## 竖屏指令条的「两步确认」验收（必须带 390×844 窗口跑，headless 测不了 GUI）：
##   godot --path . --resolution 390x844 --script res://tools/probe_palette.gd
##
## 验四件事，全用**真触摸事件**灌进去（不直接调内部函数 —— 那样只能证明函数写得对，
## 证明不了「手指落下去的时候它真的收到这些事件」）：
##   1) 从牌子上横滑：条子要滚，程序不能多出行，牌不能被选中
##   2) 点一下：牌选中，程序还是不能多行
##   3) 再点同一张：这才追加一行
##   4) 追加后牌不该还亮着
## 第 1 条就是原来那个 bug：滑一下条子，松手白放一张牌。


func _init() -> void:
	# 断言里写的是源码里的中文，语言必须钉死 —— 否则系统是英文时「再点一次」永远对不上。
	I18n.auto_detect = false
	I18n.locale = "zh_Hans"
	I18n.settings_path = "user://probe_palette.cfg"
	var main = load("res://main.tscn").instantiate()
	get_root().add_child(main)
	await process_frame
	await process_frame
	# 第 1 关只有 2 块牌，总宽正好装得下 —— 量出来「滚不动」是内容的问题，不是手势的问题。
	main.load_level(16)
	for _i in 3:
		await process_frame

	print("窗口 %dx%d · 布局 %s · 牌 %d 块" % [
		int(main.size.x), int(main.size.y),
		"竖屏" if main._tall else "横屏",
		main.palette_nodes.size()])
	if not main._tall:
		print("**这个探针专测竖屏，请加 --resolution 390x844**")
		quit()
		return

	var op: String = String(main.palette_nodes.keys()[0])
	var card: Control = main.palette_nodes[op]
	var c: Vector2 = card.get_global_rect().get_center()
	var pal: Control = main.scroll_pal
	var bar: HScrollBar = pal.get_h_scroll_bar()
	print("第一块牌 %s · 中心 (%.0f, %.0f) · 可滚 max=%.0f page=%.0f" % [
		op, c.x, c.y, bar.max_value, bar.page])

	# ---- 1. 从牌子上横滑
	var rows0: int = main.program.size()
	var s0: int = pal.scroll_horizontal
	_touch(c, true)
	await process_frame
	var x: float = c.x
	for _i in 5:
		x -= 16.0
		_drag(Vector2(x, c.y), Vector2(-16.0, 0.0))
		await process_frame
	_touch(Vector2(x, c.y), false)
	await process_frame
	await process_frame
	_ok(pal.scroll_horizontal > s0,
		"从牌子上横滑应滚条子（%d → %d）" % [s0, pal.scroll_horizontal])
	_ok(main.program.size() == rows0,
		"横滑不该追加指令（%d → %d）" % [rows0, main.program.size()])
	_ok(main._pal_sel == "", "横滑不该选中牌（实际「%s」）" % main._pal_sel)

	# 滑完之后第一块牌可能已经移出视口，下面点「新的」第一块可见牌
	var vis: Control = null
	for k in main.palette_nodes.keys():
		var cc: Control = main.palette_nodes[k]
		if cc != null and pal.get_global_rect().has_point(cc.get_global_rect().get_center()):
			vis = cc
			op = String(k)
			break
	_ok(vis != null, "横滑后应至少有一块牌完整落在条子里")
	if vis == null:
		quit()
		return
	c = vis.get_global_rect().get_center()

	# ---- 2. 点一下：只选中
	rows0 = main.program.size()
	_touch(c, true)
	await process_frame
	_touch(c, false)
	await process_frame
	await process_frame
	_ok(main._pal_sel == op, "点一下应选中「%s」，实际「%s」" % [op, main._pal_sel])
	_ok(main.program.size() == rows0, "第一下不该追加（%d → %d）" % [rows0, main.program.size()])
	_ok(main.lbl_insert_hint.text.contains("再点一次"),
		"选中后应提示再点一次，实际「%s」" % main.lbl_insert_hint.text)
	# 这个环境（Windows + OpenGL + --script）下 get_image() 拿到的是「最后一次 present
	# 的帧」，不是此刻这一帧 —— 所以截图只能放在流程末尾：带 --shot 时跑到这就收工。
	var sp: String = _shot_path()
	if sp != "":
		await _save_shot(sp, main)
		quit()
		return

	# ---- 3. 再点同一张：追加
	_touch(c, true)
	await process_frame
	_touch(c, false)
	await process_frame
	await process_frame
	_ok(main.program.size() == rows0 + 1,
		"第二下应追加一行（%d → %d）" % [rows0, main.program.size()])
	_ok(main._pal_sel == "", "追加后牌不该还亮着（实际「%s」）" % main._pal_sel)

	# ---- 4. 从牌上纵向拖到程序列表里：拖拽本身就是确认，不用先点一下
	rows0 = main.program.size()
	var drop: Vector2 = main.scroll_rows.get_global_rect().get_center()
	print("程序列表中心 (%.0f, %.0f)" % [drop.x, drop.y])
	_touch(c, true)
	await process_frame
	var steps: int = 6
	for i in steps:
		var t: float = float(i + 1) / float(steps)
		var p: Vector2 = c.lerp(drop, t)
		_drag(p, p - (_last if i > 0 else c))
		_last = p
		await process_frame
	_touch(drop, false)
	await process_frame
	await process_frame
	_ok(main.program.size() == rows0 + 1,
		"从牌上纵向拖进列表应插入一行（%d → %d）" % [rows0, main.program.size()])

	# ---- 4b. 在牌条内纵向轻拖一下就松手（没拖到列表）：幽灵卡必须消失
	#        达叔在手机上看到的就是这个：松手位置还在卡片区，一张半透明卡片留在屏幕上。
	rows0 = main.program.size()
	var before_kids: int = main.get_child_count()
	var start: Vector2 = main.palette_nodes[op].get_global_rect().get_center() \
		if main.palette_nodes.has(op) else c
	_touch(start, true)
	await process_frame
	var up_at: Vector2 = start
	for _i in 3:
		up_at.y -= 9.0
		_drag(up_at, Vector2(0.0, -9.0))
		await process_frame
	_ok(main._drag_on, "纵向拖 27px 应进入拖牌态（否则这条用例没测到残留）")
	_touch(up_at, false)
	await process_frame
	await process_frame
	await process_frame
	_ok(not main._drag_on, "牌条内松手后拖牌态应结束")
	_ok(main._ghost == null and not is_instance_valid(main._ghost),
		"牌条内松手后不该留着幽灵卡（_ghost 未清）")
	_ok(main.get_child_count() == before_kids,
		"牌条内松手后不该多出残留节点（%d → %d）" % [before_kids, main.get_child_count()])
	_ok(main.program.size() == rows0,
		"牌条内松手不该追加指令（%d → %d）" % [rows0, main.program.size()])

	# ---- 4c. 按下去先往上抖一下（已进拖牌态、幽灵卡已建），再横着划，最后在牌条里松手
	#        这就是达叔在手机上看到的「图片残留」路径：松手位置还在卡片区。
	rows0 = main.program.size()
	var kids0: int = main.get_child_count()
	var p0: Vector2 = main.palette_nodes[op].get_global_rect().get_center() \
		if main.palette_nodes.has(op) else c
	_touch(p0, true)
	await process_frame
	_drag(p0 + Vector2(0.0, -7.0), Vector2(0.0, -7.0))
	await process_frame
	_ok(main._drag_on, "先上抖 7px 应进入拖牌态（否则这条用例没测到残留）")
	var hx: float = p0.x
	for _i in 4:
		hx -= 12.0
		_drag(Vector2(hx, p0.y - 7.0), Vector2(-12.0, 0.0))
		await process_frame
	_touch(Vector2(hx, p0.y - 7.0), false)
	await process_frame
	await process_frame
	await process_frame
	_ok(not main._drag_on and main._ghost == null,
		"在牌条里松手必须把幽灵卡收干净（_drag_on=%s）" % str(main._drag_on))
	_ok(main.get_child_count() == kids0,
		"松手后不该多出残留节点（%d → %d）" % [kids0, main.get_child_count()])
	_ok(main.program.size() == rows0,
		"在牌条里松手不该追加指令（%d → %d）" % [rows0, main.program.size()])

	# ---- 5. 鼠标（桌面/调试窗）在红框这条上横向拖：也应该是「滚条子」，不是拖牌
	#      触摸有 ScreenDrag，鼠标只有 MouseMotion —— 两条通道都得走同一条语义。
	#      **步长必须按真实手速来**：一次 20px 的大跳会绕过「5px 就起拖」那个坑，
	#      而真人拖动是每帧 2~4px —— 达叔报「左右滑不动」就是被大步长探针掩盖的。
	for step in [2.0, 20.0]:
		rows0 = main.program.size()
		s0 = pal.scroll_horizontal
		main._set_pal_sel("")
		var px: float = pal.get_global_rect().get_center().x
		var py: float = c.y
		_mouse_down(Vector2(px, py))
		await process_frame
		var moved: float = 0.0
		while moved < 60.0:
			px -= step
			moved += step
			_mouse_move(Vector2(px, py), Vector2(-step, 0.0))
			await process_frame
		_mouse_up(Vector2(px, py))
		await process_frame
		await process_frame
		_ok(pal.scroll_horizontal > s0,
			"鼠标横拖（每帧 %.0fpx）应滚条子（%d → %d）" % [step, s0, pal.scroll_horizontal])
		_ok(not main._drag_on, "鼠标横拖（%.0fpx/帧）不该变成拖牌" % step)
		_ok(main.program.size() == rows0,
			"鼠标横拖（%.0fpx/帧）不该追加指令（%d → %d）" % [step, rows0, main.program.size()])

	print("=== 两步确认：%d 项检查，%d 项失败 ===" % [_n, _bad])
	quit()


var _n: int = 0
var _bad: int = 0
var _last: Vector2 = Vector2.ZERO


func _ok(cond: bool, msg: String) -> void:
	_n += 1
	if not cond:
		_bad += 1
		print("FAIL  %s" % msg)
	else:
		print("PASS  %s" % msg)


func _touch_at(pos: Vector2, pressed: bool, idx: int) -> void:
	var t := InputEventScreenTouch.new()
	t.index = idx
	t.position = pos
	t.pressed = pressed
	get_root().push_input(t)


func _touch(pos: Vector2, pressed: bool) -> void:
	var t := InputEventScreenTouch.new()
	t.index = 0
	t.position = pos
	t.pressed = pressed
	get_root().push_input(t)


## 选中态是「看一眼才知道对不对」的东西，所以探针顺手能截一张：
##   godot --path . --resolution 390x844 --script res://tools/probe_palette.gd -- --shot=D:/x.png
## 必须等 frame_post_draw：只等 process_frame 会截到上一帧（数字变了图没变）。
func _shot_path() -> String:
	for a in OS.get_cmdline_user_args():
		if a.begins_with("--shot="):
			return a.substr(7)
	return ""


func _save_shot(want: String, main) -> void:
	await RenderingServer.frame_post_draw
	print("截图时刻：hint=「%s」 sel=「%s」 gap=%s rows=%d" % [
		main.lbl_insert_hint.text, main._pal_sel, str(main._gap), main.program.size()])
	var img: Image = get_root().get_texture().get_image()
	img.save_png(want)
	print("截图 → %s" % want)


func _mouse_down(pos: Vector2) -> void:
	var b := InputEventMouseButton.new()
	b.button_index = MOUSE_BUTTON_LEFT
	b.pressed = true
	b.position = pos
	b.global_position = pos
	get_root().push_input(b)


func _mouse_move(pos: Vector2, rel: Vector2) -> void:
	var m := InputEventMouseMotion.new()
	m.position = pos
	m.global_position = pos
	m.relative = rel
	get_root().push_input(m)


func _mouse_up(pos: Vector2) -> void:
	var b := InputEventMouseButton.new()
	b.button_index = MOUSE_BUTTON_LEFT
	b.pressed = false
	b.position = pos
	b.global_position = pos
	get_root().push_input(b)


func _drag(pos: Vector2, rel: Vector2) -> void:
	var d := InputEventScreenDrag.new()
	d.index = 0
	d.position = pos
	d.relative = rel
	get_root().push_input(d)

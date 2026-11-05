extends SceneTree
## 探针：程序列表在「增删行」时到底哪一帧在动。
##
## 达叔反馈：列表长度一变，界面就在跳。先分清是哪种跳：
##   A) scroll_vertical 被夹回 0（容器中途塌陷到高度 0，clamp 到顶）
##   B) 内容高度逐帧变化（行里某个控件第一帧测出的高度和第二帧不一样）
##   C) 列表外的某个控件高度变化，把列表整体顶上去/拉下来
##
## 跑法：godot --path . -s tools/probe_scroll.gd   （必须带窗口，headless 没有真实布局）

const VM = preload("res://scripts/hrm_vm.gd")

var main: Node
var _done: bool = false


func _initialize() -> void:
	var ps: PackedScene = load("res://main.tscn")
	main = ps.instantiate()
	main.save_path = "user://probe_scroll.json"
	root.add_child(main)


func _process(_d: float) -> bool:
	if _done:
		return false
	_done = true
	_run()
	return false


func _snap(tag: String) -> void:
	print("  [%s] 内容高=%3d 视口高=%3d scroll=%3d 面板高=%3d" % [
		tag,
		int(main.box_rows.size.y), int(main.scroll_rows.size.y),
		main.scroll_rows.scroll_vertical, int(main.panel_prog.size.y)])


func _watch(tag: String) -> void:
	for k in 5:
		await process_frame
		_snap("%s f%d" % [tag, k + 1])


func _run() -> void:
	await process_frame
	await process_frame

	print("=== 铺 20 行 ADD ===")
	main.program.clear()
	for i in 20:
		main.program.append(VM.make_ins("ADD", 0))
	main._after_edit()
	await _watch("铺完")

	print("--- 滚到 200，追加一行 ---")
	main.scroll_rows.scroll_vertical = 200
	await process_frame
	_snap("追加前")
	main._append("ADD")
	await _watch("追加后")

	print("--- 滚到 200，删第 4 行 ---")
	main.scroll_rows.scroll_vertical = 200
	await process_frame
	_snap("删除前")
	main._delete_row(3)
	await _watch("删除后")

	print("=== 五条不同指令的行高（不一致 → 重建后总高会变） ===")
	main.program.clear()
	for op in ["INBOX", "MOVETO", "JUMPZ", "OUTBOX", "ADD"]:
		main.program.append(VM.make_ins(op, 0 if op != "JUMPZ" else "a"))
	main._after_edit()
	await _watch("混合")
	var hs: Array = []
	for r in main.row_nodes:
		hs.append(int(r.size.y))
	print("  行高 = %s" % [hs])

	print("=== 列表外的控件高度（会不会把列表顶动） ===")
	print("  说明条 lbl_op_help 高=%d  文字长度=%d" % [
		int(main.lbl_op_help.size.y), main.lbl_op_help.text.length()])
	main._show_op_help("JUMPZ")
	await process_frame
	await process_frame
	print("  换成 JUMPZ 解释后 高=%d  长度=%d  %s" % [
		int(main.lbl_op_help.size.y), main.lbl_op_help.text.length(),
		"❌ 高度变了" if int(main.lbl_op_help.size.y) != 58 else "✓ 没变"])

	print("=== 按住空白往下拖，列表该跟着走 ===")
	main.program.clear()
	for i in 30:
		main.program.append(VM.make_ins("ADD", 0))
	main._after_edit()
	await process_frame
	await process_frame
	main.scroll_rows.scroll_vertical = 300
	await process_frame
	var s0: int = main.scroll_rows.scroll_vertical
	# 按下 → 往上拖 120px（内容跟随手指往下走，scroll 增大）
	main._begin_press("scroll", "", -1, Vector2(600, 400))
	var m1 := InputEventMouseMotion.new()
	m1.global_position = Vector2(600, 340)
	main._input(m1)
	await process_frame
	var s1: int = main.scroll_rows.scroll_vertical
	print("  按下在 y=400，拖到 y=340（往上 60）→ scroll %d → %d  %s" % [
		s0, s1, "✓ 跟手" if s1 > s0 else "❌ 没动"])
	var rel := InputEventMouseButton.new()
	rel.button_index = MOUSE_BUTTON_LEFT
	rel.pressed = false
	rel.global_position = Vector2(600, 340)
	main._input(rel)
	await process_frame
	print("  松手后 _scroll_drag = %s  _press_on = %s  %s" % [
		main._scroll_drag, main._press_on,
		"✓ 状态已复位" if (not main._scroll_drag and not main._press_on) else "❌ 卡住了"])

	print("=== 真实事件链：按在行尾空档上拖，走完整 GUI 分发 ===")
	main.scroll_rows.scroll_vertical = 0
	await process_frame
	var sp: Control = null
	for r in main.row_nodes:
		for c in r.get_child(0).get_children():
			if c.has_meta("scroll_pad"):
				sp = c
				break
		if sp != null:
			break
	if sp == null:
		print("  ❌ 没找到行尾空档控件")
	else:
		var p0: int = main.scroll_rows.scroll_vertical
		var gp: Vector2 = sp.get_global_rect().get_center()
		var down := InputEventMouseButton.new()
		down.button_index = MOUSE_BUTTON_LEFT
		down.pressed = true
		down.position = gp
		down.global_position = gp
		root.push_input(down)
		var mv := InputEventMouseMotion.new()
		mv.position = gp + Vector2(0, -70)
		mv.global_position = gp + Vector2(0, -70)
		root.push_input(mv)
		await process_frame
		var p1: int = main.scroll_rows.scroll_vertical
		print("  按下在空档 (%.0f,%.0f) 上拖 70 → scroll %d → %d  %s" % [
			gp.x, gp.y, p0, p1, "✓ 能滚" if p1 > p0 else "❌ 事件没到"])
		var up := InputEventMouseButton.new()
		up.button_index = MOUSE_BUTTON_LEFT
		up.pressed = false
		up.position = gp + Vector2(0, -70)
		up.global_position = gp + Vector2(0, -70)
		root.push_input(up)
		await process_frame

	print("=== 按在行卡上，不该被当成拖空白 ===")
	main.on_row_press(2, Vector2(600, 400))
	main._begin_press("scroll", "", -1, Vector2(600, 400))
	print("  press_kind = %s  %s" % [
		main._press_kind, "✓ 仍是 row" if main._press_kind == "row" else "❌ 被容器抢走了"])
	main._press_on = false

	quit()

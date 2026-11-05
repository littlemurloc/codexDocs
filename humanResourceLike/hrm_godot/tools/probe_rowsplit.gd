extends SceneTree
## 竖屏行卡左右分区：
##   左半边 = 握把（拖这一行排序）
##   右半边 = 滚动区（拖着滚列表，不碰行序）
## 这两条必须真的分开测 —— 手感上它们用的是同一根手指、
## 同一块矩形，只有按下位置不同，靠肉眼看截图看不出来。

const I18n = preload("res://scripts/i18n.gd")


func st(main) -> String:
	return "press_on=%s kind=%s drag_on=%s scroll_drag=%s" % [
		main._press_on, main._press_kind, main._drag_on, main._scroll_drag]


func drag(root: Window, main, from: Vector2, to: Vector2) -> void:
	var down := InputEventMouseButton.new()
	down.button_index = MOUSE_BUTTON_LEFT
	down.pressed = true
	down.position = from
	down.global_position = from
	root.push_input(down)
	await process_frame
	print("    按下后：", st(main))

	var steps: int = 12
	for k in steps:
		var p: Vector2 = from.lerp(to, float(k + 1) / float(steps))
		var mv := InputEventMouseMotion.new()
		mv.position = p
		mv.global_position = p
		mv.relative = (to - from) / float(steps)
		root.push_input(mv)
		await process_frame
		if k == 2:
			print("    移动 3 步后：", st(main), " scroll=", main.scroll_rows.scroll_vertical)

	var up := InputEventMouseButton.new()
	up.button_index = MOUSE_BUTTON_LEFT
	up.pressed = false
	up.position = to
	up.global_position = to
	root.push_input(up)
	print("    松手瞬间：scroll=", main.scroll_rows.scroll_vertical, " keep=", main._scroll_keep, "  ", st(main))
	await process_frame
	print("    松手 1 帧后：scroll=", main.scroll_rows.scroll_vertical, " keep=", main._scroll_keep)
	await process_frame


func ops(main) -> String:
	var out: PackedStringArray = []
	for ins in main.program:
		out.append(String(ins.get("op", "")))
	return ",".join(out)


func make_main():
	var m = load("res://main.tscn").instantiate()
	get_root().add_child(m)
	await process_frame
	await process_frame
	m.load_level(16)
	for k in 4:
		await process_frame
	return m


func _init() -> void:
	I18n.settings_path = "user://probe_rowsplit.cfg"

	# --- 左半边：握把 ---
	var main = await make_main()
	print("tall=%s  程序 %d 行" % ["是" if main._tall else "否", main.program.size()])
	var r0: Rect2 = (main.row_nodes[0] as Control).get_global_rect()
	print("第 1 行矩形 x %.0f..%.0f y %.0f..%.0f" % [r0.position.x, r0.end.x, r0.position.y, r0.end.y])
	var before: String = ops(main)
	var left_pt: Vector2 = Vector2(r0.position.x + 12.0, r0.get_center().y)
	await drag(get_root(), main, left_pt, left_pt + Vector2(0, 150))
	var after_left: String = ops(main)
	print("左半边拖动 → 顺序 %s" % ("变了（对）" if after_left != before else "**没变（错）**"))
	print("  前 %s" % before)
	print("  后 %s" % after_left)
	main.queue_free()
	await process_frame

	# --- 右半边：滚动区（换一个干净实例，避免上一次的顺序污染落点）---
	var main2 = await make_main()
	var before2: String = ops(main2)
	var scroll0: int = main2.scroll_rows.scroll_vertical
	# 落在「弹性空白」上 —— 那才是右半边真正的滚动区。
	# 参数框和 × 是能点的控件，它们吃掉手势是应该的（点在可点的东西上就点它）。
	var pad: Control = null
	for c in (main2.row_nodes[0] as Control).get_children():
		for cc in c.get_children():
			if cc.has_meta("scroll_pad"):
				pad = cc
	if pad == null:
		print("没找到滚动空白区")
		quit()
		return
	var pr: Rect2 = pad.get_global_rect()
	print("滚动空白区 x %.0f..%.0f y %.0f..%.0f" % [pr.position.x, pr.end.x, pr.position.y, pr.end.y])
	var right_pt: Vector2 = pr.get_center()
	await drag(get_root(), main2, right_pt, right_pt + Vector2(0, -220))
	await process_frame
	await process_frame
	await process_frame
	var after_right: String = ops(main2)
	var scroll1: int = main2.scroll_rows.scroll_vertical
	print("右半边拖动 → 滚动 %d → %d（%s），顺序 %s" % [
		scroll0, scroll1,
		"滚了（对）" if scroll1 != scroll0 else "**没滚（错）**",
		"没变（对）" if after_right == before2 else "**变了（错）**"])
	quit()

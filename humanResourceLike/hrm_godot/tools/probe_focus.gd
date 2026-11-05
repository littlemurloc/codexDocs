extends SceneTree

const HrmVM = preload("res://scripts/hrm_vm.gd")
const I18n = preload("res://scripts/i18n.gd")
## 「专注编写」探针：量切换前后编辑器到底多了多少行。
##
## 要它是因为这件事**截图看不出倍数**——截图上 3 行和 8 行都只是一张图，
## 而「多出来的高度被谁拿走了」必须看数字。顺带确认切换不重建界面
## （重建会丢滚动位置和选中行，而玩家按这个键的瞬间正在看某一行）。

func _init() -> void:
	# 设置写到临时文件：探针会真的点一下「专注」，而它会落盘。
	# 让探针写进真 settings.cfg 的后果是——下一次打开游戏直接是专注模式，
	# 而玩家（达叔）会以为舞台坏了。探针不该改变被测程序的状态。
	I18n.settings_path = "user://probe_focus.cfg"
	var main = load("res://main.tscn").instantiate()
	root.add_child(main)
	await process_frame
	await process_frame
	await process_frame
	print("viewport %s   模式 %s" % [str(root.get_visible_rect().size),
		"竖屏" if main._tall else "横屏"])
	main.load_level(12)
	await process_frame
	await process_frame
	# 造一段带循环跳转的程序：只有 JUMP 才会让跳转线车道有宽度，
	# 全是 INBOX/OUTBOX 的话车道恒为 0，等于没验「专注态放宽车道」这一条。
	var loop: Array = []
	for _k in 3:
		loop.append({"op": "INBOX", "arg": null, "label": ""})
		loop.append({"op": "OUTBOX", "arg": null, "label": ""})
	loop.append({"op": "BUMPUP", "arg": 0, "label": ""})
	loop.append({"op": "MOVETO", "arg": 0, "label": ""})
	loop.append({"op": "JUMP", "arg": "a", "label": ""})
	loop[0]["label"] = "a"
	main.program = loop
	main.sel = 13
	main._after_edit()
	await process_frame
	await process_frame

	var before_rows: int = main.row_nodes.size()
	var before_scroll: float = main.scroll_rows.scroll_vertical

	_dump(main, "普通")

	# 记住节点身份：真重建的话这个实例会失效
	var keep: Node = main.scroll_rows
	main._toggle_focus()
	await process_frame
	await process_frame
	await process_frame

	_dump(main, "专注")
	print("\n切换方式：%s" % ("原地改可见性（节点还在）"
		if is_instance_valid(keep) and main.scroll_rows == keep else "重建了（节点已换）"))
	print("行数没变：%s（%d → %d）" % [
		"是" if before_rows == main.row_nodes.size() else "否",
		before_rows, main.row_nodes.size()])
	if main.lbl_focus_goal != null:
		print("目标行 visible=%s  文字=%s  高=%.0f" % [
			main.lbl_focus_goal.visible, main.lbl_focus_goal.text,
			main.lbl_focus_goal.size.y])
	else:
		print("目标行节点为 null（没建出来）")
	print("舞台可见：%s   按钮文案：%s" % [
		"是" if main.panel_stage.visible else "否",
		main.btn_focus.text if main.btn_focus != null else "（无）"])
	print("切之前滚动位置 %.0f，现在 %.0f（选中行 %d 应被滚进视野）" % [
		before_scroll, main.scroll_rows.scroll_vertical, main.sel])

	# 等真正画完一帧：只 await process_frame 会截到「假装横屏」那一帧的画面，
	# 而数字（8.1 行）已经是新的 —— 图和数对不上，最容易被误判成「代码没生效」。
	await RenderingServer.frame_post_draw
	await RenderingServer.frame_post_draw
	var img: Image = root.get_texture().get_image()
	if img != null:
		img.save_png(OS.get_environment("FOCUS_SHOT"))
		print("截图 %s" % OS.get_environment("FOCUS_SHOT"))

	# 横屏必须把舞台还回来：横屏没有这个按钮，藏了就等于永久黑掉一半屏幕。
	main._tall = false
	main._apply_focus()
	await process_frame
	print("假装横屏：舞台可见=%s（必须是 true）  目标行可见=%s（必须 false）" % [
		"是" if main.panel_stage.visible else "否",
		"是" if (main.lbl_focus_goal != null and main.lbl_focus_goal.visible) else "否"])
	main._tall = true
	main._apply_focus()
	await process_frame
	quit()


func _main_make(op: String):
	# 直接用 VM 的工厂，避免探针自己拼字典拼错字段
	return HrmVM.make_ins(op)


func _rows_fit(main) -> float:
	if main.row_nodes.size() == 0 or main.scroll_rows == null:
		return 0.0
	var h: float = main.row_nodes[0].size.y
	if h <= 0.0:
		return 0.0
	var sep: float = main.box_rows.get_theme_constant("separation")
	return (main.scroll_rows.size.y + sep) / (h + sep)


func _dump(main, tag: String) -> void:
	print("\n==== %s ====" % tag)
	print("  舞台面板 h %.0f（可见 %s）" % [
		main.panel_stage.size.y, "是" if main.panel_stage.visible else "否"])
	print("  编辑器面板 h %.0f" % main.panel_prog.size.y)
	print("  行区 scroll_rows h %.0f" % main.scroll_rows.size.y)
	print("  单行 h %.0f" % (main.row_nodes[0].size.y if main.row_nodes.size() > 0 else 0.0))
	print("  一屏可见 %.1f 行" % _rows_fit(main))
	var widest: float = 0.0
	for rr in main.box_rows.get_children():
		widest = maxf(widest, (rr as Control).get_combined_minimum_size().x)
	print("  最宽行 %.0f / 行区宽 %.0f（超了就是横向溢出）" % [widest, main.scroll_rows.size.x])
	print("  跳转线车道宽 %.0f" % main.row_gutter.get_theme_constant("margin_left"))
	print("  指令面板 h %.0f   操作台 h %.0f" % [
		main.scroll_pal.get_parent().get_parent().size.y,
		main.root_box.get_child(main.root_box.get_child_count() - 1).size.y])

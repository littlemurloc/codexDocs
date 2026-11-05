extends SceneTree
## 跳转线探针：把 lanes / gutter / 每条线的目标标签和车道打出来。
##
## 为什么要有它：线画出来「看着差不多」是最容易骗自己的验收方式。
## 颜色对不对、几条车道、行卡让了多宽，这些都得是**数**，不是感觉。

func _init() -> void:
	var main = load("res://main.tscn").instantiate()
	root.add_child(main)
	await process_frame
	await process_frame
	await process_frame
	main.load_level(16)          # 第 17 关：多层跳转，最能挤
	for _i in 6:
		await process_frame
	var ja = main.jump_arcs
	print("\n==== Lv17 ====")
	print("程序 %d 行，跳转 %d 条" % [main.program.size(), ja.links(main.program).size()])
	print("lanes = %d   gutter = %.0f   margin_left = %d   head_pad = %.0f" % [
		ja.lanes, ja.gutter_width(),
		main.row_gutter.get_theme_constant("margin_left"),
		main.head_pad.custom_minimum_size.x])
	for p in ja.links(main.program):
		var lab: String = String(p[2])
		print("  行 %02d → 行 %02d   标签 %s   颜色 %s" % [
			int(p[0]) + 1, int(p[1]) + 1, lab, str(Kit_tint(lab).to_html(false))])
	# 行卡左边和表头 # 的位置，用来核对「有没有对齐」
	var r0: Rect2 = main.row_nodes[0].get_global_rect()
	print("行 01 左边缘 x = %.0f，行卡宽度 %.0f" % [r0.position.x, r0.size.x])
	# 表头「#」：colhead 的第 2 个孩子（第 1 个是垫片）
	var colhead: Control = main.head_pad.get_parent()
	var h1: Control = colhead.get_child(1)
	print("表头 # 的 x = %.0f   期望 = %.0f（行卡文字左沿）" % [
		h1.get_global_rect().position.x, r0.position.x + 13.0])
	print("scroll_rows 视口高 %.0f" % main.scroll_rows.size.y)
	quit()


func Kit_tint(lab: String) -> Color:
	return load("res://scripts/ui_kit.gd").label_tint(lab)

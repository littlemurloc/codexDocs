extends SceneTree
## 布局探针：把抬头 / 工作台 / 指令面板 / 舞台的实际矩形打出来。
##
## 为什么要有这个：v18 把左栏地图和右栏任务卡都搬走以后，
## 「最小高度」从 749 掉到 603，但屏幕上工作台反而更矮了 ——
## 因为最小高度变小不等于它会变高，**多出来的空间是按 stretch_ratio 分的**。
## 这类问题看截图只能看出「矮了」，看不出「矮了多少、被谁拿走了」。
##
## v24 起它还要能看竖屏：横竖两套布局的 root_box 孩子顺序不同，
## 所以这里不按下标认名字，直接遍历打印 —— 按下标认名字的探针，
## 换个布局就会开始骗人（比不打印更糟）。

func _init() -> void:
	var main = load("res://main.tscn").instantiate()
	root.add_child(main)
	await process_frame
	await process_frame
	await process_frame
	print("viewport %s   main %s   模式 %s" % [
		str(root.get_visible_rect().size), str(main.size),
		"竖屏" if main._tall else "横屏"])
	main.load_level(16)
	await process_frame
	_main_dump(main, "Lv17")
	quit()


func _rect(c: Control) -> String:
	if c == null:
		return "null"
	var r: Rect2 = c.get_global_rect()
	return "y %.0f..%.0f h %.0f | x %.0f..%.0f w %.0f" % [
		r.position.y, r.position.y + r.size.y, r.size.y,
		r.position.x, r.position.x + r.size.x, r.size.x]


func _main_dump(main, tag: String) -> void:
	print("\n==== %s ====" % tag)
	print("root_box 最小高 %.0f / 最小宽 %.0f" % [
		main.root_box.get_combined_minimum_size().y,
		main.root_box.get_combined_minimum_size().x])
	for c in main.root_box.get_children():
		var cc: Control = c
		print("  [%s] %s   最小 %s   ratio %.2f  vflags %d" % [
			cc.get_class(), _rect(cc), str(cc.get_combined_minimum_size()),
			cc.size_flags_stretch_ratio, cc.size_flags_vertical])
		for g in cc.get_children():
			var gg: Control = g
			print("      └ [%s] %s" % [gg.get_class(), _rect(gg)])
	print("  scroll_rows %s" % _rect(main.scroll_rows))
	print("  row_wrap %s   box_rows %s   gutter %s" % [
		_rect(main.scroll_rows.get_parent()), _rect(main.box_rows), _rect(main.row_gutter)])
	if main.scroll_rows != null and main.scroll_rows.get_child_count() > 0:
		print("  scroll_rows 内容高 %.0f" % main.scroll_rows.get_child(0).get_combined_minimum_size().y)
	print("  scroll_pal  %s" % _rect(main.scroll_pal))
	# 横向滑动是否真的能滑：HBox 若被拉成滚动区那么宽，max 会等于 0，
	# 牌子再多也只是被挤窄，手指滑不出任何东西（而且不报错）。
	var vb: HScrollBar = main.scroll_pal.get_h_scroll_bar()
	print("  scroll_pal 横向 max=%.0f page=%.0f（max>page 才滑得动；牌总宽 %.0f）" % [
		vb.max_value, vb.page, main.box_palette.get_combined_minimum_size().x])
	print("  box_palette %s 最小宽 %.0f（滚动区宽 %.0f，超了才滑得动）" % [
		main.box_palette.get_class(), main.box_palette.get_combined_minimum_size().x,
		main.scroll_pal.size.x])
	var widest: float = 0.0
	var widest_i: int = -1
	for rr in main.box_rows.get_children():
		var r2: Control = rr
		if r2.get_combined_minimum_size().x > widest:
			widest = r2.get_combined_minimum_size().x
			widest_i = r2.get_index()
	print("  最宽行 #%d = %.0f  （超过 scroll_rows 宽就是要横向溢出）" % [widest_i, widest])
	if main.box_rows.get_child_count() > 0:
		var row: Control = main.box_rows.get_child(0)
		print("  行卡最小宽 %.0f" % row.get_combined_minimum_size().x)
		var hb: Control = null
		for k in row.get_children():
			if k is HBoxContainer:
				hb = k
		if hb != null:
			for k in hb.get_children():
				print("    %-14s 最小宽 %.0f" % [k.get_class(), k.get_combined_minimum_size().x])


func kid_min(main, i: int) -> float:
	var c: Control = main.root_box.get_child(i)
	return c.get_combined_minimum_size().y

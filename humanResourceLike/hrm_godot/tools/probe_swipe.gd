extends SceneTree

const I18n = preload("res://scripts/i18n.gd")
## 指令条是「一排横向滑动」——这条只有真手指能验，鼠标验不了
## （ScrollContainer 的鼠标拖动默认不开，触摸拖动才走 InputEventScreenDrag）。
## 所以这里直接往视口灌触摸事件，看两件事：
##   1) 划一下，指令条真的滚了吗
##   2) 划完程序还是空的吗 —— 拖动若被当成「点牌追加」，滑一次就多一行指令，
##      而玩家会以为是自己手抖


func _init() -> void:
	I18n.settings_path = "user://probe_swipe.cfg"
	var main = load("res://main.tscn").instantiate()
	get_root().add_child(main)
	await process_frame
	await process_frame
	# 第 1 关只有 2 块牌，总宽正好等于滚动区 —— 没有可滚的东西，
	# 量出来「滚不动」是内容的问题，不是手势的问题。换成有 8 块牌的第 17 关。
	main.load_level(16)
	await process_frame
	await process_frame
	await process_frame

	var pal: Control = main.scroll_pal
	var bar: HScrollBar = pal.get_h_scroll_bar()
	print("指令条 y %.0f~%.0f  x %.0f~%.0f   可滚范围 max=%.0f page=%.0f" % [
		pal.global_position.y, pal.global_position.y + pal.size.y,
		pal.global_position.x, pal.global_position.x + pal.size.x,
		bar.max_value, bar.page])
	print("牌子 %d 块，总宽 %.0f" % [
		main.box_palette.get_child_count(),
		main.box_palette.get_combined_minimum_size().x])

	var before_rows: int = main.program.size()
	var before_scroll: int = pal.scroll_horizontal
	var cy: float = pal.global_position.y + pal.size.y * 0.5
	var x0: float = pal.global_position.x + pal.size.x - 20.0

	# 手指按下
	var t := InputEventScreenTouch.new()
	t.index = 0
	t.position = Vector2(x0, cy)
	t.pressed = true
	get_root().push_input(t)
	await process_frame

	# 向左划（内容往左走 = 看后面的牌）
	var x: float = x0
	while x > pal.global_position.x + 40.0:
		x -= 16.0
		var d := InputEventScreenDrag.new()
		d.index = 0
		d.position = Vector2(x, cy)
		d.relative = Vector2(-16.0, 0.0)
		get_root().push_input(d)
		await process_frame

	var up := InputEventScreenTouch.new()
	up.index = 0
	up.position = Vector2(x, cy)
	up.pressed = false
	get_root().push_input(up)
	await process_frame
	await process_frame

	print("划之前 scroll=%d → 划之后 scroll=%d  （>0 才算滑动了 %.0f px）" % [
		before_scroll, pal.scroll_horizontal, pal.scroll_horizontal - before_scroll])
	print("程序行数 %d → %d  （必须相等；多了就是拖动被当成了点牌）" % [
		before_rows, main.program.size()])
	print("结论：横向滑动%s，误触追加%s" % [
		"可用" if pal.scroll_horizontal > before_scroll else "**没反应**",
		"有（BUG）" if main.program.size() != before_rows else "无"])
	quit()

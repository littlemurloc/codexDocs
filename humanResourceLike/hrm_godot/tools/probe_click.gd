extends SceneTree
## 设置浮层里的按钮到底能不能点中。
## 上一轮在浏览器里点了三次都没反应 —— 要么坐标不对，要么这一层根本收不到输入。
## 这里直接往视口灌鼠标事件，绕开浏览器那一层，先确定是「代码」还是「环境」。

const I18n = preload("res://scripts/i18n.gd")

func click(x: float, y: float) -> void:
	for pressed in [true, false]:
		var ev := InputEventMouseButton.new()
		ev.button_index = MOUSE_BUTTON_LEFT
		ev.pressed = pressed
		ev.position = Vector2(x, y)
		ev.global_position = ev.position
		get_root().push_input(ev)
		await process_frame


func _init() -> void:
	I18n.settings_path = "user://probe_click.cfg"
	var main = load("res://main.tscn").instantiate()
	get_root().add_child(main)
	await process_frame
	await process_frame
	main._toggle_settings()
	await process_frame
	await process_frame

	for k in main._orient_btns.keys():
		var b: Control = main._orient_btns[k]
		var r: Rect2 = b.get_global_rect()
		print("按钮 %-9s 矩形 x %.0f..%.0f y %.0f..%.0f  可见=%s  禁用=%s" % [
			k, r.position.x, r.end.x, r.position.y, r.end.y,
			"是" if b.is_visible_in_tree() else "否",
			"是" if (b as Button).disabled else "否"])

	# 点「横版」正中心
	var target: Control = main._orient_btns["landscape"]
	var tr: Rect2 = target.get_global_rect()
	print("点 (%.0f, %.0f)：" % [tr.get_center().x, tr.get_center().y])
	await click(tr.get_center().x, tr.get_center().y)
	await process_frame
	await process_frame
	await process_frame
	print("  点完 orient=%s  _tall=%s" % [main._orient_mode, "是" if main._tall else "否"])

	# 再点「完成」，看浮层关不关
	print("点「完成」：")
	var done: Button = _find_btn(main.set_layer, "完成")
	if done != null:
		var dr: Rect2 = done.get_global_rect()
		print("  矩形 x %.0f..%.0f y %.0f..%.0f" % [dr.position.x, dr.end.x, dr.position.y, dr.end.y])
		await click(dr.get_center().x, dr.get_center().y)
		await process_frame
		print("  浮层可见=%s" % ("是" if (main.set_layer != null and main.set_layer.visible) else "否"))
	else:
		print("  没找到「完成」按钮")
	quit()


func _find_btn(n: Node, word: String) -> Button:
	if n is Button and (n as Button).text.contains(word):
		return n
	for c in n.get_children():
		var r: Button = _find_btn(c, word)
		if r != null:
			return r
	return null

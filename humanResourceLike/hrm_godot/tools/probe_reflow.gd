extends SceneTree
## 横竖屏切换探针：把一个已经建好的界面从横屏改成竖屏、再改回来，
## 看它是不是能自己重建、有没有崩、重建完布局是不是真的换了。
##
## 为什么要单独立一个：这条路径**只有拖动窗口 / 手机转屏**才会走到，
## 而它和「换语言」共用 _relocalize（整屏拆了重建）。
## 拆的时候漏了谁、重建的时候读了旧的 _tall，都不报错 —— 只是界面停在上一套。

var main = null


func _init() -> void:
	main = load("res://main.tscn").instantiate()
	root.add_child(main)
	await process_frame
	await process_frame
	print("初始：viewport %s  _tall=%s  root_min_w=%.0f" % [
		str(root.get_visible_rect().size), str(main._tall),
		main.root_box.get_combined_minimum_size().x])
	main.load_level(12)

	await _resize(Vector2i(390, 844))
	print("→ 竖屏：viewport %s  _tall=%s  root_min_w=%.0f  scroll_rows 宽 %.0f" % [
		str(root.get_visible_rect().size), str(main._tall),
		main.root_box.get_combined_minimum_size().x,
		main.scroll_rows.get_global_rect().size.x])
	await _resize(Vector2i(1280, 800))
	print("→ 横屏：viewport %s  _tall=%s  root_min_w=%.0f  scroll_rows 宽 %.0f" % [
		str(root.get_visible_rect().size), str(main._tall),
		main.root_box.get_combined_minimum_size().x,
		main.scroll_rows.get_global_rect().size.x])
	await _resize(Vector2i(390, 844))
	print("→ 再竖：viewport %s  _tall=%s" % [
		str(root.get_visible_rect().size), str(main._tall)])

	print("sfx 还活着：%s" % str(main.sfx != null and is_instance_valid(main.sfx)))
	print("关卡名标签：%s" % str(main.lbl_level_name != null and main.lbl_level_name.text != ""))
	quit()


func _resize(sz: Vector2i) -> void:
	DisplayServer.window_set_size(sz)
	for _i in 6:
		await process_frame

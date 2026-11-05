extends SceneTree
## 画面方向开关：三档都要能真的换布局，而且换完设定浮层不能自己消失
## （浮层是在 _relocalize 的拆除范围里的，这是这条链路最容易漏的地方）。

const I18n = preload("res://scripts/i18n.gd")


func _init() -> void:
	I18n.settings_path = "user://probe_orient.cfg"
	var main = load("res://main.tscn").instantiate()
	get_root().add_child(main)
	await process_frame
	await process_frame
	print("启动：_tall=%s  orient=%s" % ["是" if main._tall else "否", main._orient_mode])

	main._toggle_settings()
	await process_frame
	print("打开设定：可见=%s  按钮数=%d" % [
		"是" if main.set_layer.visible else "否", main._orient_btns.size()])
	for k in main._orient_btns.keys():
		var b: Control = main._orient_btns[k]
		var r: Rect2 = b.get_global_rect()
		print("  按钮 %-9s x %.0f..%.0f  y %.0f..%.0f  文字 %s" % [
			k, r.position.x, r.end.x, r.position.y, r.end.y, (b as Button).text])

	for mode in ["portrait", "landscape", "auto"]:
		main._set_orient(mode)
		await process_frame
		await process_frame
		await process_frame
		var base: Vector2i = main.get_window().content_scale_size
		print("切到 %-9s → _tall=%s  base=%s  设定还开着=%s  （期望竖版 390x844 / 横版 1280x800）" % [
			mode, "是" if main._tall else "否", str(base),
			"是" if (main.set_layer != null and main.set_layer.visible) else "否"])

	print("settings.cfg 里的值：%s" % main._read_orient())
	quit()

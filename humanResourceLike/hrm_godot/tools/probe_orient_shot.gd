extends SceneTree
## 在给定窗口尺寸下强制某个方向再截图 —— 用来确认「横窗口里选竖版」到底长什么样。
const I18n = preload("res://scripts/i18n.gd")

func _init() -> void:
	I18n.settings_path = "user://probe_orient_shot.cfg"
	var main = load("res://main.tscn").instantiate()
	get_root().add_child(main)
	await process_frame
	await process_frame
	main._set_orient(OS.get_environment("ORIENT_MODE"))
	for i in 6:
		await process_frame
	await RenderingServer.frame_post_draw
	await RenderingServer.frame_post_draw
	var img: Image = get_root().get_texture().get_image()
	if img != null:
		img.save_png(OS.get_environment("ORIENT_SHOT"))
		print("截图 ", OS.get_environment("ORIENT_SHOT"), "  _tall=", main._tall)
	quit()

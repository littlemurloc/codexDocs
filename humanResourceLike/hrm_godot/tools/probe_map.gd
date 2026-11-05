extends SceneTree

const I18n = preload("res://scripts/i18n.gd")

func _init() -> void:
	I18n.settings_path = "user://probe_map.cfg"
	var main = load("res://main.tscn").instantiate()
	get_root().add_child(main)
	await process_frame
	await process_frame
	main._toggle_level_map()
	await process_frame
	await process_frame
	if main.btn_map_go != null:
		var r: Rect2 = (main.btn_map_go as Control).get_global_rect()
		print("btn_map_go  rect x %.0f..%.0f  y %.0f..%.0f  文字 %s" % [
			r.position.x, r.end.x, r.position.y, r.end.y, main.btn_map_go.text])
	var mp = main.map_pop
	if mp != null:
		var cc: Control = mp.get_child(1)
		var box: Control = cc.get_child(0)
		print("box 宽 %.0f 最小 %.0f | cc 宽 %.0f" % [
			box.size.x, box.get_combined_minimum_size().x, cc.size.x])
		var vv: Control = box.get_child(0)
		for kid in vv.get_children():
			print("    %-18s 最小宽 %.0f" % [kid.get_class(), kid.get_combined_minimum_size().x])
	if main.map_levels != null:
		var mr: Rect2 = (main.map_levels as Control).get_global_rect()
		print("map 浮层    x %.0f..%.0f  y %.0f..%.0f" % [
			mr.position.x, mr.end.x, mr.position.y, mr.end.y])
	quit()

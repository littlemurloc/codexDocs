extends SceneTree
## 依次解锁：地图上要能一眼分出「能进 / 进不去」，点锁住的砖不能预选。
const I18n = preload("res://scripts/i18n.gd")

func _init() -> void:
	I18n.settings_path = "user://probe_unlock.cfg"
	var main = load("res://main.tscn").instantiate()
	get_root().add_child(main)
	await process_frame
	await process_frame

	# 造一个「只过了前 5 关」的存档
	main.progress.clear()
	main.saved_programs.clear()
	for i in 5:
		var id: String = str(int(main.levels[i].get("id", i + 1)))
		main.progress[id] = {"cleared": true, "stars": 2, "size": 10, "speed": 1.0}
		main.saved_programs[id] = [{"op": "INBOX", "arg": null, "label": ""}]
	main._refresh_level_buttons()
	print("解锁到第 %d 关（1 基）" % (main._unlocked_max() + 1))

	main._toggle_level_map()
	await process_frame
	await process_frame
	await process_frame

	# 点第 12 关（索引 11）—— 应该被拒
	main._on_map_picked(11)
	await process_frame
	print("点第 12 关后 pending=%d（应为 -1）" % main.map_levels.pending)
	print("顶部提示：%s" % main.lbl_levels_title.text)

	# 点第 4 关 —— 应该被接受
	main._on_map_picked(3)
	await process_frame
	print("点第 4 关后 pending=%d（应为 3）" % main.map_levels.pending)

	var img: Image = get_root().get_texture().get_image()
	if img != null:
		img.save_png(OS.get_environment("UNLOCK_SHOT"))
		print("截图 ", OS.get_environment("UNLOCK_SHOT"))
	quit()

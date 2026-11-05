extends SceneTree
## 探针：验证「鼠标移到行内 × 上，× 不会消失」。
##
## 为什么必须带窗口跑：headless 没有真实光标，Input.warp_mouse 不起作用，
## 也就触发不了 mouse_entered / mouse_exited。跑法：
##   godot --path . --resolution 1280x800 --script tools/probe_hover.gd
##
## 判据：把光标依次挪到 ① 行中央 ② 行内 × 按钮上 ③ 行外空白处，
## 每一步等两帧（= _leave_row_deferred 的延迟窗口），读 × 的 modulate.a。
## 期望：①1  ②1（关键 —— 修复前这里是 0，就是玩家说的「想点它它跑了」）③0

func _initialize() -> void:
	var ps: PackedScene = load("res://main.tscn")
	if ps == null:
		print("FAIL: main.tscn 加载失败")
		quit(1)
		return
	var main: Node = ps.instantiate()
	main.save_path = "user://probe_hover_progress.json"
	root.add_child(main)
	_run.call_deferred(main)


func _alpha_of(main: Node) -> float:
	# 程序区第一行的 × 按钮：行容器里最后一个 Button
	if main.box_rows == null or main.box_rows.get_child_count() == 0:
		return -1.0
	var row: Control = main.box_rows.get_child(0)
	for c in row.get_children():
		if c is HBoxContainer:
			var kids: Array = c.get_children()
			for i in range(kids.size() - 1, -1, -1):
				if kids[i] is Button:
					return (kids[i] as Button).modulate.a
	return -1.0


func _del_button(main: Node) -> Button:
	if main.box_rows == null or main.box_rows.get_child_count() == 0:
		return null
	var row: Control = main.box_rows.get_child(0)
	for c in row.get_children():
		if c is HBoxContainer:
			var kids: Array = c.get_children()
			for i in range(kids.size() - 1, -1, -1):
				if kids[i] is Button:
					return kids[i] as Button
	return null


func _run(main: Node) -> void:
	for _i in 12:
		await process_frame
	# 没有行就没有 ×，先塞两条指令造出可测的行
	main._append("INBOX")
	main._append("OUTBOX")
	for _i in 4:
		await process_frame
	if main.box_rows == null or main.box_rows.get_child_count() == 0:
		print("FAIL: 程序区没有行")
		quit(1)
		return

	var row: Control = main.box_rows.get_child(0)
	var del: Button = _del_button(main)
	if del == null:
		print("FAIL: 没找到行内 × 按钮")
		quit(1)
		return

	var ok := true
	var exited := [0]
	var entered := [0]
	row.mouse_exited.connect(func() -> void: exited[0] += 1)
	row.mouse_entered.connect(func() -> void: entered[0] += 1)

	# ① 行中央（行内但不在 × 上）
	var rc: Vector2 = row.get_global_rect().get_center()
	Input.warp_mouse(rc)
	for _i in 4:
		await process_frame
	var a1: float = del.modulate.a
	print("① 停在行中央      alpha=%.2f  期望 1.00" % a1)
	if a1 < 0.99:
		ok = false

	# ② 行内 × 按钮上（这就是原来会消失的那一步）
	var dc: Vector2 = del.get_global_rect().get_center()
	Input.warp_mouse(dc)
	for _i in 4:
		await process_frame
	var a2: float = del.modulate.a
	print("② 停在 × 按钮上   alpha=%.2f  期望 1.00  ← 关键" % a2)
	if a2 < 0.99:
		ok = false

	# ③ 挪到行外（舞台中央）
	var sr: Vector2 = main.stage.get_global_rect().get_center()
	Input.warp_mouse(sr)
	for _i in 6:
		await process_frame
	var a3: float = del.modulate.a
	print("③ 停在行外        alpha=%.2f  期望 0.00" % a3)
	print("   目标点=%s  实际鼠标=%s  行矩形=%s" % [
		str(sr), str(main.get_global_mouse_position()), str(row.get_global_rect())])
	# 顺手记一笔信号计数：如果这里不是 1/1，说明引擎的 entered/exited 行为变了，
	# 那条「改用鼠标坐标裁决」的理由需要重新验证。
	print("   (entered=%d exited=%d)" % [entered[0], exited[0]])
	if a3 > 0.01:
		ok = false

	print("=== %s ===" % ("PASS：× 不再被自己吓跑" if ok else "FAIL：hover 行为不对"))
	quit(0 if ok else 1)

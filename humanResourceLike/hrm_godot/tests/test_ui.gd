extends SceneTree
## 界面层冒烟测试（headless）：关卡数据、空白开局、程序存盘、三级提示、拖放、撤销重做
## 跑法：godot --headless --path . --script res://tests/test_ui.gd
## 注意：测试把存档改指到 user://test_progress.json，跑完删除，不会动玩家真实进度

const VM = preload("res://scripts/hrm_vm.gd")
const I18n = preload("res://scripts/i18n.gd")
const Stage = preload("res://scripts/stage.gd")
const TEST_SAVE := "user://test_progress.json"
const TEST_SETTINGS := "user://test_settings.cfg"

var fails: Array[String] = []
var n_check: int = 0
var main: Node
var _done: bool = false


func _initialize() -> void:
	# 多语言：测试钉在「原文语」上 —— 下面的断言写的就是源码里的中文，
	# 不受繁简转换和英文表影响；同时关掉 IP 探测、不碰玩家真实的语言设置。
	I18n.auto_detect = false
	I18n.locale = "zh_Hans"
	I18n.settings_path = TEST_SETTINGS
	var ps: PackedScene = load("res://main.tscn")
	if ps == null:
		fails.append("main.tscn 加载失败")
		return
	# 必须在 add_child 之前改路径：_ready 里的 _load_progress 会用到
	var abs_path: String = ProjectSettings.globalize_path(TEST_SAVE)
	if FileAccess.file_exists(TEST_SAVE):
		DirAccess.remove_absolute(abs_path)
	var abs_set: String = ProjectSettings.globalize_path(TEST_SETTINGS)
	if FileAccess.file_exists(TEST_SETTINGS):
		DirAccess.remove_absolute(abs_set)
	main = ps.instantiate()
	main.save_path = TEST_SAVE
	root.add_child(main)
	# 注意：此刻树尚未 ready，main 的 _ready 会被推迟到首帧，断言不能放这里


func _process(_delta: float) -> bool:
	if _done:
		return false
	_done = true
	_run_checks()      # 协程：里面会 await 帧，等容器排版完再断言
	return false


func _fill_ref() -> void:
	main.program = VM.parse_program(main.level.get("ref", []))
	main._after_edit()


func _run_checks() -> void:
	if main == null:
		_finish()
		return

	_check(main.levels.size() == 40, "关卡数应为 40，实际 %d" % main.levels.size())
	_check(main.li == 0, "初始关卡索引应为 0，实际 %d" % main.li)
	_check(int(main.level.get("id", 0)) == 1, "初始关 id 应为 1")
	_check(main.target_size > 0, "目标 SIZE 应大于 0")
	_check(main.lbl_status != null, "状态栏控件应已构建")

	# ---- 空白开局：新存档进关不该预填参考解
	_check(main.program.is_empty(), "新存档进关应为空白，实际 %d 条" % main.program.size())
	_check(main.row_nodes.is_empty(), "空白开局不应有程序行")

	# ---- 新手引导：一关都没写过程序的人，面板上方那行字要先说「该干什么」
	_check(main._is_new_hand(), "刚开新档进第 1 关应判定为新手")
	_check(main.lbl_insert_hint.text.contains("点一下"),
		"新手引导应指向指令牌，实际「%s」" % main.lbl_insert_hint.text)
	_check(main._guide_btn != null and main._guide_tween != null,
		"新手引导应让第一块指令牌呼吸")
	# 呼吸是动画，静止的截图里看不出来 —— 所以还得有一条常驻的描边告诉人「看这块」
	var gsb: StyleBoxFlat = main._guide_btn.get_meta("sb", null)
	_check(gsb != null and gsb.border_color == preload("res://scripts/ui_kit.gd").AMBER
		and gsb.border_width_top == 2,
		"新手时第一块指令牌应有一圈琥珀描边（截图/静态也认得出）")
	main._append("INBOX")
	main._refresh_guide()
	_check(gsb != null and gsb.border_width_top == 1,
		"不再是新手之后，那圈描边要收回去")
	_check(not main._is_new_hand(), "写过一行之后就不该再算新手")
	_check(not main.lbl_insert_hint.text.contains("点一下"),
		"动过手之后引导文字要换回「插到第几行」，实际「%s」" % main.lbl_insert_hint.text)
	main.program = []
	main.sel = -1
	main._after_edit()
	main._refresh_guide()

	# ---- 提示：冷却期内不松口，满 60 秒后逐级展开
	main.stuck_time = 0.0
	main.hint_stage = 0
	main._on_hint()
	_check(main.hint_stage == 0, "卡住不满 60 秒不应给提示，实际 %d" % main.hint_stage)
	_check(main.stage != null and main.stage.hint_text == "", "冷却期内提示纸条不应挂出来")

	main.stuck_time = 999.0
	main._on_hint()
	_check(main.hint_stage == 1, "第一级应是思路，实际 %d" % main.hint_stage)
	_check(main.stage.hint_text.contains("思路"), "第一级要显示思路")
	main._on_hint()
	_check(main.hint_stage == 2, "第二级应是具体做法，实际 %d" % main.hint_stage)
	_check(main.stage.hint_text.contains("关键做法"), "第二级要显示关键做法")
	main._on_hint()
	_check(main.hint_stage == 3, "第三级应给参考解，实际 %d" % main.hint_stage)
	_check(main.program.size() > 0, "第三级应把参考解填进编辑器")
	# 给过参考解之后按钮是「回看」而不是死的：玩家常常只要那句思路，
	# 而记录（hint_stage）不该因为回看被改回去 —— 只增不减。
	_check(not main.btn_hint.disabled, "给出参考解后按钮应仍可点（回看）")
	main._on_hint()
	_check(main.hint_view == 2, "回看应贴回第 2 级那张纸条，实际 %d" % main.hint_view)
	_check(main.hint_stage == 3, "回看不能把成绩记录改回去，实际 %d" % main.hint_stage)
	_check(main.stage.hint_text.contains("关键做法"), "回看要能看到关键做法")
	main._on_hint()
	_check(main.hint_view == 3, "再点一次应回到参考解说明，实际 %d" % main.hint_view)

	# ---- 用了参考解过关，成绩要打上「参考答案」标记
	main._on_reset()
	for _i in range(400):
		if main.vm.finished or main.vm.failed:
			break
		main._on_step()
	_check(main.vm.finished, "第 1 关参考解应能跑通")
	var rec: Dictionary = main.progress.get("1", {})
	_check(rec.get("hint", false), "用过参考解的关卡应记 hint=true")
	_check(main._best_text(1).contains("☆"), "提示过关应显示 ☆，实际 %s" % main._best_text(1))

	# ---- 程序存盘 / 恢复：自己写的程序要能带回来
	main.load_level(1)                       # 第 2 关，空白
	_check(main.program.is_empty(), "第 2 关首次进入也应是空白")
	main.program = [VM.make_ins("INBOX"), VM.make_ins("OUTBOX")]
	main._after_edit()
	main._save_progress()
	main.load_level(0)                       # 切走再切回
	main.load_level(1)
	_check(main.program.size() == 2, "切回第 2 关应恢复自己写的 2 行，实际 %d" % main.program.size())
	_check(String(main.program[0].get("op", "")) == "INBOX", "恢复的第一行应是 INBOX")

	# ---- 存档格式：应当是新结构 ver/levels/programs
	var f: FileAccess = FileAccess.open(TEST_SAVE, FileAccess.READ)
	_check(f != null, "存档文件应存在")
	if f != null:
		var d: Variant = JSON.parse_string(f.get_as_text())
		f.close()
		_check(typeof(d) == TYPE_DICTIONARY and d.has("levels") and d.has("programs"),
			"存档应是 {ver,levels,programs} 结构")

	# ---- 切到第 10 关，再热重载数据，索引与目标值要保住
	main.load_level(9)
	_check(main.li == 9, "切换后索引应为 9")
	var speed_before: float = main.target_speed
	main._reload_level_data()
	_check(main.levels.size() == 40, "热重载后关卡数应仍为 40")
	_check(main.li == 9, "热重载后应停在第 10 关，实际 %d" % main.li)
	_check(is_equal_approx(main.target_speed, speed_before), "热重载后目标 SPEED 应不变")

	# 越界保护
	main.load_level(999)
	_check(main.li == 39, "越界索引应被夹到末关，实际 %d" % main.li)

	# ---- 指令语义：JUMPZ 就是「比较」，面板上必须看得出来
	main.load_level(5)                       # 第 6 关，第一次给 JUMPZ
	await process_frame
	await process_frame
	_check(main.palette_nodes.has("JUMPZ"), "第 6 关指令面板应有 JUMPZ")
	_check(VM.op_short("JUMPZ").contains("0"), "JUMPZ 白话应点明条件，实际「%s」" % VM.op_short("JUMPZ"))
	_check(VM.op_help("JUMPZ").contains("比较"), "JUMPZ 解释应说明它就是比较")
	_check(VM.op_help("JUMPN").contains("比较"), "JUMPN 解释应说明它就是比较")
	# MOVETO 的坑：玩家会当「粘贴」用，可粘贴不会清空剪贴板，这里写完手就空了
	_check(VM.op_help("MOVETO").contains("粘贴"), "MOVETO 解释应点明它不是粘贴")
	_check(VM.op_help("MOVETO").contains("空"), "MOVETO 解释应说清写完手会空")
	_check(VM.op_help("COPYFROM").contains("复制"), "COPYFROM 解释应说清这一步才是复制")
	# 改名后的旧存档兼容：老程序里存的是 COPYTO，加载时必须收敛成 MOVETO
	_check(VM.canon_op("COPYTO") == "MOVETO", "旧名 COPYTO 应被收敛成 MOVETO")
	_check(VM.make_ins("COPYTO", 0).get("op", "") == "MOVETO", "make_ins 也应收敛旧名")
	_check(VM.parse_program(["COPYTO 1"])[0].get("op", "") == "MOVETO", "解析旧数据也应收敛")
	main.saved_programs["99"] = [{"op": "COPYTO", "arg": 0, "label": ""}]
	var migrated: Array = main._program_from_save("99")
	_check(String(migrated[0].get("op", "")) == "MOVETO", "旧存档加载后应变成 MOVETO")
	main.saved_programs.erase("99")
	var card: Control = main.palette_nodes.get("JUMPZ", null)
	var card_text: String = _collect_labels(card)
	_check(card_text.contains("JUMPZ"), "指令牌上应有指令名，实际「%s」" % card_text)
	_check(card_text.contains("0"), "指令牌上应有白话说明，实际「%s」" % card_text)
	_check(main.lbl_op_help != null and main.lbl_op_help.text.contains("比较"),
		"面板底部应默认说明「没有比较牌」，实际「%s」" % main.lbl_op_help.text)
	main._show_op_help("JUMPZ")
	_check(main.lbl_op_help.text.contains("比较"), "悬停 JUMPZ 时解释条应换成它的说明")
	main._refresh_op_help_default()

	# 程序行右侧也要有白话：读程序不必再默译英文
	#
	# ⚠ 竖屏反过来：带参数的行**故意不画**白话 —— 374 宽里那句解释和数字框
	# 抢的是同一块地盘，抢不过就不抢（见 _make_row 里的分支）。
	# 这不是放宽标准，是这条规则本来就只对「一行放得下」的布局成立。
	if main._tall:
		main.program = [VM.make_ins("INBOX"), VM.make_ins("JUMPZ", "b"), VM.make_ins("OUTBOX")]
		main._after_edit()
		await process_frame
		_check(not _collect_labels(main.row_nodes[1]).contains(VM.op_tag("JUMPZ")),
			"竖屏下带参数的行不应再画白话（宽度不够），实际「%s」" % _collect_labels(main.row_nodes[1]))
	else:
		main.program = [VM.make_ins("INBOX"), VM.make_ins("JUMPZ", "b"), VM.make_ins("OUTBOX")]
		main._after_edit()
		await process_frame
		_check(_collect_labels(main.row_nodes[1]).contains(VM.op_tag("JUMPZ")),
			"JUMPZ 行右侧应有白话说明，实际「%s」" % _collect_labels(main.row_nodes[1]))

	# ---- 说明书弹窗：本关能用的每一张牌都要讲一遍
	main.load_level(5)                       # 第 6 关
	await process_frame
	_check(main.btn_doc != null, "指令面板应有说明书按钮")
	if main.btn_doc != null:
		main.btn_doc.pressed.emit()          # 等于点了按钮
	_check(main.doc_layer != null, "点说明书应弹出窗口")
	var allowed6: Array = main.level.get("allowed", [])
	_check(main.doc_entries.size() == allowed6.size(),
		"说明书应覆盖本关全部 %d 张牌，实际 %d" % [allowed6.size(), main.doc_entries.size()])
	for op6 in allowed6:
		_check(main.doc_entries.has(op6), "说明书缺少 %s" % op6)
	var doc_text: String = _collect_labels(main.doc_layer)
	_check(doc_text.contains(VM.op_help("JUMPZ")), "说明书里应有 JUMPZ 的完整解释")
	_check(doc_text.contains("这就是比较"), "条件跳转牌上要有「这就是比较」徽章")
	_check(doc_text.contains("第 6 关"), "说明书标题要标出当前关卡")
	main._close_doc()
	await process_frame
	_check(main.doc_layer == null, "关闭后弹窗应销毁")
	main._open_doc()
	_check(main.doc_layer != null, "说明书应能再次打开")
	main.load_level(0)                       # 切关应自动收掉，别讲上一关的牌
	_check(main.doc_layer == null, "切关后说明书应自动关闭")

	# ---- 跳转线：「哪一行跳到哪一行」是业务逻辑，不能靠眼睛验
	var lp: Array = VM.parse_program(["a:INBOX", "JUMPZ b", "OUTBOX", "JUMP a", "b:MOVETO 0"])
	var links: Array = main.JumpArcs.links(lp)
	_check(links.size() == 2, "应算出 2 条跳转，实际 %d" % links.size())
	if links.size() == 2:
		_check(int(links[0][0]) == 1 and int(links[0][1]) == 4,
			"JUMPZ b（第 2 行）应跳到 b 所在的第 5 行，实际 %s" % [links[0]])
		_check(int(links[1][0]) == 3 and int(links[1][1]) == 0,
			"JUMP a（第 4 行）应跳回 a 所在的第 1 行，实际 %s" % [links[1]])
	# 标签还没落地时不该画线（玩家常先写 JUMP 再标目标）
	_check(main.JumpArcs.links(VM.parse_program(["JUMP zz"])).is_empty(),
		"目标标签不存在时不该有线")
	# 同一标签写两次：取最后一次（和 VM 的寻址行为一致）
	var dup: Array = main.JumpArcs.links(VM.parse_program(["JUMP a", "a:INBOX", "a:OUTBOX"]))
	_check(dup.size() == 1 and int(dup[0][1]) == 2, "重复标签应跳到最后一次标记的那行")
	# 搭在真实控件上也别崩：行节点和程序对不上时直接跳过
	main.program = lp
	main._after_edit()
	await process_frame
	_check(main.jump_arcs != null and main.jump_arcs.program.size() == lp.size(),
		"跳转线层应拿到和程序等长的数据")

	# ---- 标签上色：线跟着「要落到的那一行」的标签走
	# 第三个返回值就是目标标签。没有它，线只能一种颜色 —— 一堆同色平行线，
	# 玩家还是得逐条去追，那画线就白画了。
	_check(String(links[0][2]) == "b", "第 2 行的 JUMPZ 目标标签应是 b，实际 %s" % links[0][2])
	_check(String(links[1][2]) == "a", "第 4 行的 JUMP 目标标签应是 a，实际 %s" % links[1][2])
	var Kit = main.Kit
	var tints: Array = []
	for lab in ["a", "b", "c", "d"]:
		tints.append(Kit.label_tint(lab))
	for x in tints.size():
		for y in range(x + 1, tints.size()):
			_check(tints[x] != tints[y],
				"标签 %s 和 %s 不该是同一个颜色（同色 = 没染）" % ["abcd"[x], "abcd"[y]])
	_check(Kit.label_tint("a") == Kit.LBL_A, "label_tint 应取到和 LBL_A 同一份颜色")

	# ---- 缩进：线有几条车道，行卡就整体让多宽
	# 判据是「有没有」，不是「多宽」—— 宽度是设计值，会随视觉调；0 和非 0 是功能。
	main.program = [VM.make_ins("INBOX"), VM.make_ins("OUTBOX")]
	main._after_edit()
	await process_frame
	await process_frame
	_check(int(main.row_gutter.get_theme_constant("margin_left")) == 0,
		"没有跳转线的程序不该为不存在的线留白（当前 %d）" %
			main.row_gutter.get_theme_constant("margin_left"))
	main.program = VM.parse_program(["a:INBOX", "JUMP a"])
	main._after_edit()
	await process_frame
	await process_frame
	await process_frame
	var gut: int = int(main.row_gutter.get_theme_constant("margin_left"))
	_check(gut > 0, "有跳转线时行卡应整体右移让出车道，实际 %d" % gut)
	# 表头必须跟着让，否则整排列名比数据左偏一格
	_check(is_equal_approx(main.head_pad.custom_minimum_size.x,
			float(gut + main.ROW_TEXT_INSET - main.COLHEAD_SEP)),
		"表头垫片应 = 空栏 + 13 - 8，实际 %.0f（空栏 %d）" % [
			main.head_pad.custom_minimum_size.x, gut])

	# ---- 末尾追加只动一行：全表重建会让 20 行在屏幕上闪一下
	main.program = [VM.make_ins("INBOX")]
	main._after_edit()
	await process_frame
	var first_row: Control = main.row_nodes[0]
	main.sel = -1                    # 不选中 → 追加到末尾，走增量路径
	main._append("OUTBOX")
	await process_frame
	_check(main.row_nodes.size() == 2, "追加后应有 2 行，实际 %d" % main.row_nodes.size())
	_check(main.row_nodes[0] == first_row, "追加到末尾不该重建已有行（旧节点应原地保留）")

	# ---- 牧场地图：20 块地砖，但不再常驻 —— 收在抬头的关号徽章里
	main.load_level(0)
	await process_frame
	_check(main.map_levels == null, "地图不该常驻（没点开时 map_levels 应为空）")
	_check(main.btn_level != null, "抬头应有一枚可点的关号码牌")
	# 「标签改成按钮」不能只是长相变了：得真接上开合动作，否则玩家点它什么都不会发生
	_check(main.btn_level.pressed.get_connections().size() > 0,
		"关号码牌必须接上开合地图的动作")
	main._toggle_level_map()
	await process_frame
	_check(main.map_pop != null and main.map_levels != null, "点关号徽章应展开牧场地图")
	_check(main.lbl_hud_total.text.ends_with("▲"), "展开时徽章小字应显示收起箭头")
	# 浮层不进根 VBox：它一旦进门，就会把那 776 的预算算进去
	_check(not main.root_box.is_ancestor_of(main.map_pop),
		"地图浮层不该挂在根布局里（会吃掉 776 预算）")
	# 点空白处收起
	main._close_level_map()
	await process_frame
	_check(main.map_pop == null, "收起后浮层节点应被释放")
	main._toggle_level_map()
	await process_frame
	var tiles: Array = main.map_levels.tiles
	_check(tiles.size() == main.levels.size(),
		"地图应有 %d 块地砖，实际 %d" % [main.levels.size(), tiles.size()])
	# 星数必须「按关卡算」。老实现拿当前关的 target 去比所有关，
	# 列表时代看不出（只显示当前关的尾巴），地图时代 20 块砖全错。
	main.progress.clear()
	var tg0: Dictionary = main._target_of(0)
	main.progress["1"] = {
		"cleared": true, "size": int(tg0.get("size", 0)),
		"speed": float(tg0.get("speed", 0.0)), "hint": false,
	}
	main.load_level(6)                 # 切到第 7 关：当前关目标与第 1 关完全不同
	main._refresh_level_buttons()
	var t1: Dictionary = main.map_levels.tiles[0]
	_check(bool(t1.get("clear", false)), "第 1 关通关后地砖应标为已通关")
	_check(int(t1.get("stars", 0)) == 3, "打平参考解应是 3 星，实际 %d" % int(t1.get("stars", 0)))
	_check(main._stars(1) == 3, "_stars(id) 应与地图一致（判据只有一份）")
	_check(not bool(main.map_levels.tiles[1].get("clear", false)), "没通关的砖不该标成已通关")
	_check(int(main.map_levels.tiles[1].get("stars", 0)) == 0, "没通关的地砖应是 0 星")
	# ---- 点砖只是「预选」：换关会存盘、会换掉编辑区，这种擦不掉的动作用不该由一次误触决定
	# 前提：第 10 关得是解锁状态 —— 关卡是依次解锁的，这里先把前 10 关标成「玩过」，
	# 否则点砖会被拦（那条拦截是另一条断言要验的事，不该在这里拦）。测完恢复。
	var keep_prog: Dictionary = main.progress.duplicate(true)
	var keep_saved: Dictionary = main.saved_programs.duplicate(true)
	for i in 10:
		main.progress[str(int(main.levels[i].get("id", i + 1)))] = {"cleared": true}
	var before: int = main.li
	main._on_map_picked(9)
	await process_frame
	_check(main.li == before, "点地砖不该直接切关（要走确认），实际切到了 %d" % main.li)
	_check(int(main.map_levels.pending) == 9, "点地砖应把它设成预选")
	_check(main.map_pop != null, "预选之后浮层还得留着，等玩家按确认")
	_check(main.btn_map_go != null and main.btn_map_go.text.contains("10"),
		"确认按钮应写明要进第几关，实际「%s」" % (main.btn_map_go.text if main.btn_map_go else "（无）"))
	main._confirm_map_pick()
	await process_frame
	_check(main.li == 9, "确认后应进第 10 关，实际 %d" % main.li)
	_check(main.map_pop == null and main.map_levels == null, "确认后地图应自动收起")
	_check(main.lbl_hud_total.text.ends_with("▼"), "收起后徽章小字应显示展开箭头")
	# 预选到「当前关」时，按钮要说清楚「你就在这儿」
	main._toggle_level_map()
	await process_frame
	_check(int(main.map_levels.pending) == main.li, "打开地图应把当前关预选上")
	_check(main.btn_map_go.text.contains("这儿"), "预选当前关时按钮应说明不用换关")
	main._close_level_map()
	await process_frame
	main.progress = keep_prog
	main.saved_programs = keep_saved
	main.load_level(0)

	# ---- 分页：40 关不能硬塞进一屏
	# 塞得下（8 列 5 行），但砖会瘦成 94 宽的「表格单元格」，
	# 地砖那种「一块地」的感觉就没了 —— 宁可多一次翻页。
	main._toggle_level_map()
	await process_frame
	_check(main.map_levels.page_count() == 2,
		"40 关应分 2 页，实际 %d 页" % main.map_levels.page_count())
	_check(main.map_levels.page == 0, "第 1 关应落在第 1 页")
	_check(main.map_levels.page_len() == 20, "第 1 页应有 20 块砖，实际 %d" % main.map_levels.page_len())
	main._turn_map_page(1)
	await process_frame
	_check(main.map_levels.page == 1, "应能翻到第 2 页")
	_check(main.map_levels.page_start() == 20, "第 2 页应从第 21 关开始")
	_check(main.lbl_map_page.text == "2 / 2", "页码应显示 2 / 2，实际「%s」" % main.lbl_map_page.text)
	main._turn_map_page(1)
	await process_frame
	_check(main.map_levels.page == 1, "已经在最后一页，再往后翻应当无效")
	main._close_level_map()
	await process_frame
	main.load_level(25)
	main._toggle_level_map()
	await process_frame
	_check(main.map_levels.page == 1, "打开地图应自动翻到当前关所在的页（第 26 关在第 2 页）")
	main._close_level_map()
	await process_frame
	main.load_level(0)

	# ---- 布局不许把控制栏挤出画布：每一关的最小高度都要装得下
	#      根因记录：指令牌曾把右侧面板撑高，总最小高度 842 > 776，底部的
	#      运行/单步/重置整排被推到画布外（玩家看到的就是「按钮不见了」）
	var canvas_h: float = float(root.get_visible_rect().size.y)
	var avail: float = canvas_h - 24.0            # 上下各 12 的页边距
	var worst: float = 0.0
	var worst_lv: int = 0
	# 抬头现在住着任务说明 —— 一个「文字长度不受控」的东西。
	# 目标一行还是两行、数据流多长，都不许改变抬头高度：
	# 一旦允许它自己长高，每换一关下面的编辑器就跟着挪一次，
	# 玩家会以为程序行在跳（v16 那条「界面自己动」的翻版）。
	var hud_h: float = -1.0
	for lv in range(main.levels.size()):
		main.load_level(lv)
		await process_frame
		await process_frame
		var h: float = main.root_box.get_child(0).get_combined_minimum_size().y
		if hud_h < 0.0:
			hud_h = h
		elif absf(h - hud_h) > 0.5:
			_check(false, "第 %d 关的抬头高度 %.0f 和第 1 关的 %.0f 不一致（目标文案不该改变抬头高度）" % [
				lv + 1, h, hud_h])
		var need: float = main.root_box.get_combined_minimum_size().y
		if need > worst:
			worst = need
			worst_lv = lv + 1
		if need > avail:
			_check(false, "第 %d 关最小高度 %.0f 超过可用 %.0f，控制栏会被挤掉" % [lv + 1, need, avail])
	_check(worst <= avail, "最挤的一关是第 %d 关（%.0f / 可用 %.0f）" % [worst_lv, worst, avail])
	print("布局余量：最挤的是第 %d 关，最小高度 %.0f / 可用 %.0f（留白 %.0f）；抬头高 %.0f" % [
		worst_lv, worst, avail, avail - worst, hud_h])

	# 控制栏本身：存在、有运行按钮、底边在画布内
	var ctrl: Control = main.root_box.get_child(main.root_box.get_child_count() - 1)
	var n_btn: int = _count_buttons(ctrl)
	_check(n_btn >= 4, "最底一栏应是控制栏（运行/单步/重置/清空），实际 %d 个按钮" % n_btn)
	# 别认「第一个按钮」：竖屏控制栏是左中右三列（重置/清空在左、运行在中），
	# 桌面是两行（运行在第一行）。顺序是设计决定，会变；「有没有地方按到它」不会。
	var run_btn: Button = _find_button(ctrl, "运行")
	_check(run_btn != null and run_btn.visible,
		"控制栏里应有一个可见的「运行」按钮，实际 %s" % (run_btn.text if run_btn != null else "（无）"))
	_check(ctrl.get_global_rect().end.y <= canvas_h + 0.5,
		"控制栏底边 %.1f 应在画布 %.0f 之内" % [ctrl.get_global_rect().end.y, canvas_h])

	# ---- 拖放链路（自建拖拽）：整块列表都是投放区，不用精确对位
	main.load_level(9)
	_fill_ref()
	await process_frame
	await process_frame
	var n_drag: int = main.program.size()
	var r1 = main.row_nodes[1]
	var sr: Rect2 = main.scroll_rows.get_global_rect()

	# 2. 鼠标落在行与行之间的缝里（内建 DnD 会漏掉的位置）→ 依旧命中
	var seam_y: float = sr.position.y + r1.position.y + r1.size.y + 1.0
	_check(main._index_at(Vector2(sr.position.x + 30, seam_y)) == 2,
		"落在行间缝隙应命中第 3 位，实际 %d" % main._index_at(Vector2(sr.position.x + 30, seam_y)))

	# 3. 直接放在列表底部空白 → 追加到末尾（程序短、下方有大片空白的常见情况）
	main.program = [VM.make_ins("INBOX"), VM.make_ins("OUTBOX")]
	main._after_edit()
	await process_frame
	await process_frame
	main.scroll_rows.scroll_vertical = 0
	var bottom_pt := Vector2(sr.position.x + 30, sr.end.y - 6)
	_check(main._index_at(bottom_pt) == 2, "落在列表底部空白应追加到末尾，实际 %d" % main._index_at(bottom_pt))
	_fill_ref()
	await process_frame
	await process_frame
	r1 = main.row_nodes[1]
	n_drag = main.program.size()

	# 4. 拖到编辑器外面 → 不投放（松手等于取消）
	_check(main._index_at(Vector2(-400, -400)) == -1, "拖出编辑器应不投放")

	# 5. 空隙是真实插进容器里的：它会撑高、把下面的行挤下去
	main._begin_press("new", "SUB", -1, Vector2.ZERO)
	main._start_drag()
	main._show_gap(2)
	for _f in range(12):
		await process_frame
	_check(main._gap != null and main._gap.get_index() == 2, "空隙节点应插在第 3 位之前")
	var shift: float = main.row_nodes[2].position.y - main.row_nodes[1].position.y
	_check(shift >= main.ROW_H + main.ROW_SEP + main.ROW_H * 0.8,
		"空隙应真的把下面的行挤开，实际间距 %.1f" % shift)

	# 6. 松手落子
	main._drag_idx = 2
	main._end_drag(true)
	_check(main.program.size() == n_drag + 1, "拖放后应 +1，实际 %d" % main.program.size())
	_check(String(main.program[2].get("op", "")) == "SUB", "应插到第 3 位，实际 %s" % main.program[2].get("op", ""))
	_check(main._gap == null, "松手后空隙节点应清掉")

	# 7. 拖已有行：把第 1 行拖到末尾
	main.program = [VM.make_ins("INBOX"), VM.make_ins("OUTBOX"), VM.make_ins("COMMENT")]
	main._after_edit()
	main.on_row_drop({"kind": "row", "index": 0}, 3)
	_check(String(main.program[2].get("op", "")) == "INBOX", "行拖到末尾后应落到最后")

	# 8. 全链路：真的按一下指令面板按钮 → 拖到两行之间 → 松手
	#    headless 下没有窗口，GUI 命中测试跑不起来，这部分只在带窗口时验证
	main.program = [VM.make_ins("INBOX"), VM.make_ins("OUTBOX"), VM.make_ins("MOVETO", 0)]
	main._after_edit()
	await process_frame
	await process_frame
	if DisplayServer.get_name() == "headless":
		print("（headless：跳过真实鼠标链路，请用 --path . --script tests/test_ui.gd 带窗口跑）")
	else:
		var pbtn: Control = null
		var pop: String = ""
		for k in main.palette_nodes.keys():
			if main.palette_nodes[k] is Control:
				pbtn = main.palette_nodes[k]
				pop = String(k)
				break
		_check(pbtn != null, "指令面板应有指令牌")
		_check(main.palette_nodes.size() > 0, "指令牌应按可用指令生成，实际 %d 张" % main.palette_nodes.size())
		if pbtn != null:
			var bp: Vector2 = pbtn.get_global_rect().get_center()
			var r2: Control = main.row_nodes[1]
			var rr: Rect2 = r2.get_global_rect()
			var drop_pt := Vector2(rr.position.x + 60.0, rr.end.y + 1.0)
			_mouse_move(bp)
			_mouse_btn(bp, true)
			_check(main._press_on, "按下指令面板按钮应进入待拖拽状态")
			_mouse_move(bp + Vector2(0, 7))
			_check(main._drag_on, "移动超过阈值应开始拖拽")
			_mouse_move(drop_pt)
			_mouse_btn(drop_pt, false)
			await process_frame
			_check(not main._drag_on, "松手后拖拽状态应结束")
			_check(main.program.size() == 4, "全链路拖放后应 4 行，实际 %d" % main.program.size())
			if main.program.size() == 4:
				_check(String(main.program[2].get("op", "")) == pop,
					"应插到第 3 位，实际 %s（期望 %s）" % [main.program[2].get("op", ""), pop])

		# 9. 全链路：按住第 1 行把它拖到最后
		main.program = [VM.make_ins("INBOX"), VM.make_ins("OUTBOX"), VM.make_ins("COMMENT")]
		main._after_edit()
		await process_frame
		await process_frame
		var ra: Control = main.row_nodes[0]
		var rb: Control = main.row_nodes[2]
		var pa := Vector2(ra.get_global_rect().position.x + 24.0, ra.get_global_rect().get_center().y)
		var pb := Vector2(pa.x, rb.get_global_rect().end.y + 2.0)
		_mouse_move(pa)
		_mouse_btn(pa, true)
		_mouse_move(pa + Vector2(0, 9))
		_mouse_move(pb)
		_mouse_btn(pb, false)
		await process_frame
		_check(String(main.program[0].get("op", "")) == "OUTBOX", "按住首行拖到末尾后，首行应变成原第 2 行")
		_check(String(main.program[2].get("op", "")) == "INBOX", "原首行应落到最后")

	# ---- 编辑操作：插入 / 撤销 / 重做
	main.program = []
	main._after_edit()
	var n0: int = main.program.size()
	main._append("INBOX")
	_check(main.program.size() == n0 + 1, "追加后应 +1，实际 %d" % main.program.size())
	main._undo()
	_check(main.program.size() == n0, "撤销后应回到 %d，实际 %d" % [n0, main.program.size()])
	main._redo()
	_check(main.program.size() == n0 + 1, "重做后应 +1，实际 %d" % main.program.size())

	# ---- 行重排：Alt+上下
	main.program = [VM.make_ins("INBOX"), VM.make_ins("OUTBOX")]
	main._after_edit()
	var first_op: String = String(main.program[0].get("op", ""))
	main._move_row(0, 1)
	_check(String(main.program[1].get("op", "")) == first_op, "下移后原首行应在第 2 位")
	main._move_row(1, -1)
	_check(String(main.program[0].get("op", "")) == first_op, "上移后应回到首位")

	# ---- 空程序占位：第一条指令能直接拖进去
	main.program = []
	main._after_edit()
	_check(main.row_nodes.is_empty(), "空程序时不应有程序行节点")
	main.on_row_drop({"kind": "new", "op": "INBOX"}, 0)
	_check(main.program.size() == 1, "空程序应能直接拖入第一条，实际 %d" % main.program.size())

	# ---- 执行定位：last_pc / fail_pc
	main.program = [VM.make_ins("INBOX"), VM.make_ins("OUTBOX")]
	main._after_edit()
	main._on_step()
	_check(main.vm.last_pc == 0, "单步后 last_pc 应为 0，实际 %d" % main.vm.last_pc)

	main.program = [VM.make_ins("OUTBOX")]
	main._after_edit()
	main._on_step()
	_check(main.vm.failed, "手里没东西就 OUTBOX 应失败")
	_check(main.vm.fail_pc == 0, "失败应定位到第 1 行，实际 %d" % main.vm.fail_pc)

	# ---- SPEED 公式可见
	main._on_reset()
	_check(main.lbl_cycles.text.contains("÷"), "周期标签应摊开成 周期 ÷ 件数")

	# ---- 任务说明搬到舞台顶上那块木牌里了。
	# 之前它是抬头里的一行 13px 小字 —— 全屏最小、离视线最远的地方，
	# 放着「这一关到底要干什么」。现在它是舞台上最大的一行字（17px 加粗）。
	main.load_level(16)
	await process_frame
	_check(main.stage != null, "应有舞台")
	_check(main.stage.goal_text == String(main.level.get("goal", "")),
		"任务牌应拿到本关目标原文")
	_check(main.stage.stream_a == "5, 3, 3, 5, 4, 4",
		"任务牌应写进 INBOX 数据流，实际「%s」" % main.stage.stream_a)
	_check(main.stage.stream_b == "1, -1, 0",
		"任务牌应写进 OUTBOX 数据流，实际「%s」" % main.stage.stream_b)
	_check(main.stage.hint_text == "", "换关后提示纸条应清空（它得玩家自己叫）")
	_check(main.root_box.get_child(0).get_combined_minimum_size().y <= 52.0,
		"任务说明搬走后抬头应回到 48 上下，实际 %.0f" %
		main.root_box.get_child(0).get_combined_minimum_size().y)
	# 牌子高度完全由折行结果决定，所以折行必须是可预测的纯函数：
	# 短句一行、超长句截到两行加省略号。这条错了，换关时下面的场景就跟着抖。
	var sf: Font = main.stage.get_theme_default_font()
	_check(main.Stage._wrap_chars(sf, "短句", 17, 600.0, 2).size() == 1,
		"短目标应排一行")
	var long_txt: String = "很长".repeat(200)
	var wl: Array = main.Stage._wrap_chars(sf, long_txt, 17, 600.0, 2)
	_check(wl.size() == 2, "超长目标最多排两行，实际 %d" % wl.size())
	_check(String(wl[1]).ends_with("…"), "被截断时末行要带省略号")

	# ---- 运行手感：音效 / 渐进加速 / 执行行拖尾 / 第二通道 ---------------
	_check(main.sfx != null, "音效节点应在开机时就建好（合成要 90ms，不能等第一声才做）")
	for k in ["click", "wood", "out", "err", "win", "ding"]:
		var wav: AudioStreamWAV = main.sfx._stream(String(k))
		_check(wav != null and wav.data.size() > 200,
			"音效 %s 应能合成出波形，实际 %s 字节" % [k, 0 if wav == null else wav.data.size()])
		# 首尾样本必须是 0：直接从满幅开始会「啪」一声，那是爆音不是音效
		if wav != null and wav.data.size() >= 4:
			_check(absi(wav.data.decode_s16(0)) < 300, "音效 %s 的起音不该是爆音" % k)
			_check(absi(wav.data.decode_s16(wav.data.size() - 2)) < 300, "音效 %s 的收尾要归零" % k)

	# 加速：不做手动倍率，靠 combo 收缩间隔，而且有下限
	main.combo = 0
	var t_slow: float = main._cur_tick()
	main.combo = 6
	var t_mid: float = main._cur_tick()
	main.combo = 60
	var t_fast: float = main._cur_tick()
	_check(t_slow > t_mid and t_mid > t_fast,
		"跑得越顺间隔越短（%.3f → %.3f → %.3f）" % [t_slow, t_mid, t_fast])
	_check(t_fast <= main.STEP_FAST + 0.001,
		"加速有下限，不能一路加到看不清（实际 %.3f，下限 %.3f）" % [t_fast, main.STEP_FAST])
	main.combo = 0

	# 拖尾：最近三行、去重。原地打转的循环只该亮一行，不该把整列染绿
	main._trail.clear()
	for i in [3, 4, 4, 5, 6]:
		main._push_trail(int(i))
	_check(main._trail.size() == 3, "拖尾最多记 3 行，实际 %d" % main._trail.size())
	_check(int(main._trail[0]) == 6 and int(main._trail[2]) == 4,
		"拖尾应是最近三行且去重，实际 %s" % str(main._trail))

	# 第二通道：正在执行 / 出错的行，行号要换成形状，不能只靠红绿
	_fill_ref()
	main._on_reset()
	main._on_step()
	await process_frame
	main._refresh_runtime()
	var pc_i: int = main.vm.last_pc
	if pc_i >= 0 and pc_i < main.row_nodes.size():
		var nr = main.row_nodes[pc_i].num_lbl
		_check(nr != null and nr.text == "▶",
			"正在执行的行号应换成 ▶（色盲不看颜色也能认），实际「%s」" % ("" if nr == null else nr.text))
	else:
		_check(false, "第 1 关走一步后应有一个「正在执行」的行")

	# 全三星：判据现算，只认一次
	main.progress.clear()
	main.allstar_ack = false
	_check(not main._all_stars(), "没成绩不能算全三星")
	for i in main.levels.size():
		main.progress[str(int(main.levels[i].get("id", i + 1)))] = {
			"cleared": true, "size": true, "speed": true, "hint": false}
	_check(main._all_stars(), "四十关三项全达标应算全三星")
	_check(main._star_total() == main.levels.size() * 3,
		"总星数应为 %d，实际 %d" % [main.levels.size() * 3, main._star_total()])
	_check(main._claim_allstar(), "首次达成应认一次（弹那张卡）")
	_check(not main._claim_allstar(), "同一份成绩不该认第二次 —— 庆祝只能有一次")

	# 设置：音量能存能读，且**不能把语言设置冲掉**（两边共用一个 settings.cfg）
	main._save_audio(0.35)
	_check(is_equal_approx(main._read_audio(), 0.35),
		"音量应能存盘再读回，实际 %.2f" % main._read_audio())
	main.sfx.set_master_volume(0.35)
	_check(is_equal_approx(main.sfx.master_volume, 0.35), "音量应送达音效层")
	I18n.save_locale("en", true)
	_check(is_equal_approx(main._read_audio(), 0.35), "写语言不该冲掉音量")
	main._save_audio(0.8)

	# --fill：把参考解铺进「我的解」（验关用，打开就是现成答案）。
	# 范围两端、单关、all 三种写法都要对；铺的是 parse 后的结构，跟玩家手写的一个样。
	var sp_before: int = main.saved_programs.size()
	main._fill_programs("20-22", false)
	for fid in [20, 21, 22]:
		_check(main.saved_programs.has(str(fid)), "--fill 后第 %d 关应有铺好的程序" % fid)
	var p20: Array = main.saved_programs.get("20", [])
	_check(p20.size() == VM.parse_program(main.levels[19].get("ref", [])).size(),
		"铺进去的行数应与参考解一致，实际 %d" % p20.size())
	_check(main.saved_programs.size() >= sp_before + 3, "不应动范围外的关")
	main._fill_programs("35", false)
	_check(main.saved_programs.has("35"), "单关写法也要生效")
	main._fill_programs("all", false)
	_check(main.saved_programs.size() >= main.levels.size(), "all 应至少铺满 40 关")

	# ---- 多语言 ---------------------------------------------------------
	# 默认语言靠 IP 归属判，所以「区域 → 语言」这条规则必须能被单独钉死：
	# 它错了，整个区域的人都会看到听不懂的那门语言，而玩家只会以为「这游戏没做中文」。
	for cc in ["CN", "TW", "HK", "MO", "tw"]:
		_check(I18n.locale_for_country(cc) == "zh_Hant", "%s 应判为中文区" % cc)
	for cc in ["US", "JP", "DE", "GB", "KR", "SG", ""]:
		_check(I18n.locale_for_country(cc) == "en",
			"%s 应判为英文区（实际 %s）" % [cc, I18n.locale_for_country(cc)])

	# 繁体不是另写一份，是运行时转的 —— 转错的地方只能靠这类定点断言抓。
	I18n.locale = "zh_Hant"
	_check(I18n.t("数完啦！") == "數完啦！", "繁体：数完啦")
	_check(I18n.t("程序是空的") == "程式是空的", "繁体：程序 → 程式（台湾叫法）")
	_check(I18n.t("周期÷件") == "週期÷件", "繁体：周期 → 週期")
	_check(I18n.t("只把非 0 的数放进 OUTBOX") == "只把非 0 的數放進 OUTBOX",
		"繁体：不是量词的「只」不能换成「隻」，实际「%s」" % I18n.t("只把非 0 的数放进 OUTBOX"))
	_check(I18n.t("一只羊") == "一隻羊", "繁体：量词的「只」要换成「隻」")
	I18n.locale = "zh_Hans"
	_check(I18n.t("数完啦！") == "数完啦！", "原文语应恒等（测试与开发都靠它）")

	# 英文：表里有的必须查得到，查不到的会原样返回中文（静默漏翻，最坏的那种）
	I18n.locale = "en"
	_check(I18n.t("数完啦！") == "Counted!", "英文：数完啦，实际「%s」" % I18n.t("数完啦！"))
	_check(I18n.tf("第 %d 关 · %s", [3, "x"]) == "Level 3 · x",
		"英文：带参数的模板要先翻再填，实际「%s」" % I18n.tf("第 %d 关 · %s", [3, "x"]))
	_check(I18n.table_size() > 250, "英文表应有 250 条以上，实际 %d" % I18n.table_size())
	I18n.locale = "zh_Hans"

	# 切一次语言：程序要留下、界面要重建、英文界面里**不许残留中文**。
	# 最后这条是整套 i18n 的兜底：漏包一个 t() 不会有任何报错，
	# 只会在英文界面里混一句中文 —— 只有扫一遍控件树才抓得住。
	main.load_level(0)
	main.program = [VM.make_ins("INBOX"), VM.make_ins("OUTBOX")]
	main._after_edit()
	await process_frame
	var n_before: int = main.program.size()
	var vol_before: float = main.sfx.master_volume
	main._apply_locale("en", true)
	await process_frame
	_check(I18n.locale == "en", "应切到英文，实际 %s" % I18n.locale)
	_check(main.program.size() == n_before, "换语言不该动程序，实际 %d 行" % main.program.size())
	_check(main.row_nodes.size() == n_before,
		"换语言后程序行应重建出来，实际 %d 行" % main.row_nodes.size())
	# 按钮上写**当前**语言（不是「点了会变成什么」）。原来写目标语言时，
	# 中文界面显示 EN、英文界面显示繁中 —— 看起来像整块翻译反了，达叔就是这么被坑的。
	_check(main.btn_lang.text == I18n.locale_label(I18n.locale),
		"语言按钮的字应是「当前语言」，实际「%s」" % main.btn_lang.text)
	var left_cn: String = _collect_text(main, true)
	_check(left_cn == "", "英文界面里不该残留中文：" + left_cn.substr(0, 160))
	_check(String(I18n.read_saved().get("lang", "")) == "en", "手切语言应落盘（下次开机不再探 IP）")
	# 切语言会整屏重建（拆掉 main 的全部子节点）。音效层要是跟着被拆，
	# 8 路 player 池就没了 —— 表现是「切完语言全程静音」，真踩过。
	_check(main.sfx != null and is_instance_valid(main.sfx), "整屏重建后音效节点必须还活着")
	_check(main.sfx._pool.size() == 8, "重建后 8 路 player 池应完好，实际 %d" % main.sfx._pool.size())
	var sfx_ok: bool = true
	for p in main.sfx._pool:
		if not is_instance_valid(p):
			sfx_ok = false
	_check(sfx_ok, "池里每个 player 都必须有效（有一个被 free 就会漏拍）")
	_check(is_equal_approx(main.sfx.master_volume, vol_before),
		"重建不该把音量重置，实际 %f / 之前 %f" % [main.sfx.master_volume, vol_before])

	# 切回繁体：同一个程序、同一关，界面整片换成繁体
	main._apply_locale("zh_Hant", true)
	await process_frame
	_check(I18n.locale == "zh_Hant", "应切回繁体，实际 %s" % I18n.locale)
	_check(_collect_text(main, false).contains("關"), "繁体界面里应出现「關」")
	_check(main.program.size() == n_before, "切回去也不该动程序")
	I18n.locale = "zh_Hans"       # 之后没有别的断言了，恢复原文语收尾

	# 字体覆盖：界面上的每一个字都必须有字形，否则就是一个方框。
	#
	# 这条针对的是「改了文案忘记重跑 tools/make_font_subset.py」——
	# 桌面版靠系统字体还能蒙混过去，网页版会直接满屏豆腐块（v23.2 真踩过）。
	# 检查范围取「会被画出来的字符串」：i18n 的原文键 + 它的繁体转换结果 + 英文值，
	# 外加关卡数据。**不查简繁字典**，那 3881 个罕用字只在查表时用，永远不上屏。
	var font: Font = main.theme.default_font
	_check(font != null, "主题必须有默认字体")
	var bad: Array = []
	if font != null:
		var checked := {}
		var raw: String = FileAccess.get_file_as_string("res://data/i18n.json")
		var dict: Dictionary = JSON.parse_string(raw)
		for k in Dictionary(dict.get("en", {})).keys():
			var forms: Array = [String(k), I18n.to_hant(String(k)), String(dict["en"][k])]
			for form in forms:
				for i in String(form).length():
					var cp: int = String(form).unicode_at(i)
					if cp < 128 or checked.has(cp):
						continue
					checked[cp] = true
					if not font.has_char(cp):
						bad.append(String(form)[i])
		var lv_raw: String = FileAccess.get_file_as_string("res://data/levels.json")
		for i in lv_raw.length():
			var cp2: int = lv_raw.unicode_at(i)
			if cp2 < 128 or checked.has(cp2):
				continue
			checked[cp2] = true
			if not font.has_char(cp2):
				bad.append(lv_raw[i])
		_check(checked.size() > 300, "覆盖面应包含全部界面用字，实际只查到 %d 个" % checked.size())
	_check(bad.is_empty(),
		"界面用字必须都有字形（缺字会显示成方框，重跑 tools/make_font_subset.py）：%s"
			% "".join(bad).substr(0, 40))

	# CanvasLayer 浮层必须显式挂 theme。
	# CanvasLayer 不是 Control，theme 的继承链到它那儿就断了 —— 结算卡和设置浮层
	# 里的字会退回引擎默认字体（无中文、无符号）。网页版上表现是：主界面正常，
	# 一过关结算卡满屏方框。这个坑只在「浮层」出现，所以断言要盯着浮层的根节点。
	_check(main.win_layer != null and main.win_layer.get_child_count() > 0,
		"结算卡浮层应已建好")
	if main.win_layer != null and main.win_layer.get_child_count() > 0:
		# 结算卡也从 CanvasLayer 改成了普通 Control（Web 导出里那一层的按钮点不动），
		# Control 会自己继承 theme，root.theme 本来就是 null。判据改成它真正保证的东西。
		_check(main.win_layer.get_child(0).get_theme_font("font") != null,
			"结算卡里的字必须拿得到主题字体（拿不到就会满屏方框）")
	# ---- 关卡依次解锁
	# 判据是「上一关玩过」（通关或写过程序），不是「点过的关」。后者能靠乱点解锁。
	var keep_prog_u: Dictionary = main.progress.duplicate(true)
	var keep_saved_u: Dictionary = main.saved_programs.duplicate(true)
	main.progress.clear()
	main.saved_programs.clear()
	_check(main._unlocked_max() == 0, "空存档应该只解锁第 1 关，实际 %d" % (main._unlocked_max() + 1))
	var id1: String = str(int(main.levels[0].get("id", 1)))
	main.progress[id1] = {"cleared": true}
	_check(main._unlocked_max() == 1, "过了第 1 关应解锁到第 2 关，实际第 %d 关" % (main._unlocked_max() + 1))
	# 只写过程序、没记通关，也算「到过」—— 老存档全靠这一条才不被锁回去
	main.progress.clear()
	main.saved_programs[id1] = [{"op": "INBOX", "arg": null, "label": ""}]
	_check(main._unlocked_max() == 1, "第 1 关写过程序也应解锁第 2 关，实际第 %d 关" % (main._unlocked_max() + 1))
	main.progress = keep_prog_u
	main.saved_programs = keep_saved_u

	if main.set_layer != null and main.set_layer.get_child_count() > 0:
		# 设置浮层已经从 CanvasLayer 改成普通 Control（Web 导出里那一层的按钮
		# 一个都点不动，实测）。Control 会自己继承 theme，root.theme 本来就是 null，
		# 所以「theme 非空」不再是判据 —— 判据改回它真正要保证的东西：字能画出来。
		var sroot: Control = main.set_layer.get_child(0)
		_check(sroot.get_theme_font("font") != null,
			"设置浮层里的字必须拿得到主题字体（拿不到就会满屏方框）")

	# 提示纸条不许压到地面上那排数字木牌。
	# 这是 v22 的一处真实事故：纸条宽度写死 700，1280×800 上只剩 5px 缝 ——
	# 看全屏截图觉得「贴着」，放大才知道是「差点叠上」，而且窗口一矮就真的叠上了。
	# 纸条高度由折行决定、可用空间由窗口高度决定，两者没有任何关系，
	# 所以这里对**每一条提示 × 每门语言**都量一遍（几何是纯函数，不用等渲染帧）。
	#
	# 舞台高 265 是 1280×800 下探针量到的真实值（fy = 265-78 = 187）；
	# 再补一个矮舞台（高 250），确认「窗口一矮」时纸条会横着长而不是压下去。
	for loc in ["zh_Hans", "zh_Hant", "en"]:
		I18n.locale = loc
		var min_gap: float = 1e9
		var min_at: String = ""
		for sh in [265.0, 250.0]:
			for i in main.levels.size():
				var lv: Dictionary = main.levels[i]
				var h1: String = String(lv.get("hint", ""))
				var h2: String = String(lv.get("hint2", ""))
				if h1 == "":
					continue
				var body: String = I18n.tf("思路：%s\n关键做法：%s", [I18n.t(h1), I18n.t(h2)])
				var goal: String = I18n.t(String(lv.get("goal", "")))
				var fnt: Font = main.stage.get_theme_default_font()
				var top: float = Stage.note_top(fnt, 1264.0, goal)
				var g: Dictionary = Stage.hint_layout(fnt, 1264.0, sh - 78.0, top, body)
				var gap: float = (sh - 78.0) - float((g["rect"] as Rect2).end.y)
				if gap < min_gap:
					min_gap = gap
					min_at = "第 %d 关" % (i + 1)
		_check(min_gap >= 8.0,
			"%s：提示纸条压到地面木牌了（最小间距 %.1fpx，%s）" % [loc, min_gap, min_at])
	I18n.locale = "zh_Hans"

	_finish()


## 把界面上的字收集起来：Label / Button 的文字 + 所有控件的 tooltip。
## only_cjk=true 时只收「含中日韩汉字」的那些 —— 用来检英文界面有没有漏翻。
func _collect_text(n: Node, only_cjk: bool) -> String:
	var out: String = ""
	var txt: String = ""
	if n is Label:
		txt = (n as Label).text
	elif n is Button:
		txt = (n as Button).text
	if txt != "" and (not only_cjk or _has_cjk(_cjk_residue(txt))):
		out += txt + " | "
	if n is Control:
		var tip: String = (n as Control).tooltip_text
		if tip != "" and (not only_cjk or _has_cjk(_cjk_residue(tip))):
			out += "[tip]" + tip + " | "
	for c in n.get_children():
		out += _collect_text(c, only_cjk)
	return out


## 语言名永远用「它自己的语言」写（繁體中文 / English），所以中文界面、英文界面里
## 都会合法地出现这几个词 —— 它们不是漏翻，是必须长这样的那种字。
func _cjk_residue(s: String) -> String:
	for w in ["繁體中文", "简体中文", "繁中", "简中"]:
		s = s.replace(w, "")
	return s


func _has_cjk(s: String) -> bool:
	for i in s.length():
		var c: int = s.unicode_at(i)
		if (c >= 0x4e00 and c <= 0x9fff) or (c >= 0x3400 and c <= 0x4dbf):
			return true
	return false


func _check(ok: bool, msg: String) -> void:
	n_check += 1
	if not ok:
		fails.append(msg)


## 递归找第一个按钮 / 数按钮个数：控制栏外面包了一层停靠条，不能再按下标取
func _find_button(n: Node, word: String) -> Button:
	if n is Button and (n as Button).text.contains(word):
		return n
	for c in n.get_children():
		var r: Button = _find_button(c, word)
		if r != null:
			return r
	return null


func _first_button(n: Node) -> Button:
	if n is Button:
		return n
	for c in n.get_children():
		var r: Button = _first_button(c)
		if r != null:
			return r
	return null


func _count_buttons(n: Node) -> int:
	var k: int = 1 if n is Button else 0
	for c in n.get_children():
		k += _count_buttons(c)
	return k


## 把一个控件子树里所有 Label 的文字拼起来，用来断言「牌面上写了什么」
func _collect_labels(n: Node) -> String:
	if n == null:
		return ""
	var out: String = ""
	if n is Label:
		out += String((n as Label).text) + " "
	for c in n.get_children():
		out += _collect_labels(c)
	return out


func _mouse_btn(pos: Vector2, pressed: bool) -> void:
	var e := InputEventMouseButton.new()
	e.button_index = MOUSE_BUTTON_LEFT
	e.pressed = pressed
	e.position = pos
	e.global_position = pos
	root.push_input(e)


func _mouse_move(pos: Vector2) -> void:
	var e := InputEventMouseMotion.new()
	e.position = pos
	e.global_position = pos
	e.relative = pos
	root.push_input(e)


func _finish() -> void:
	var abs_path: String = ProjectSettings.globalize_path(TEST_SAVE)
	if FileAccess.file_exists(TEST_SAVE):
		DirAccess.remove_absolute(abs_path)
	if fails.is_empty():
		print("=== UI 冒烟测试：%d 项检查，全部通过 ===" % n_check)
		quit(0)
	else:
		for f in fails:
			printerr("FAIL  " + f)
		print("=== UI 冒烟测试：%d 项检查，%d 项失败 ===" % [n_check, fails.size()])
		quit(1)

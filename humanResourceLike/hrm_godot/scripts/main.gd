extends Control
## HRM 复刻原型主界面（UI 全代码搭建，方便脚本化改造）
## 布局：顶栏 / 关卡·程序·指令三栏 / 办公室舞台 / 控制栏

const HrmVM = preload("res://scripts/hrm_vm.gd")
const ProgRow = preload("res://scripts/prog_row.gd")
const Stage = preload("res://scripts/stage.gd")
const DragGap = preload("res://scripts/drag_gap.gd")
const LevelMap = preload("res://scripts/level_map.gd")
const JumpArcs = preload("res://scripts/jump_arcs.gd")

## 说明书按「想干什么」分组，而不是按指令集顺序：
## 玩家脑子里是「我怎么把一个 0 扔掉」，不是「J 开头的那几条」。
const OP_GROUPS: Array = [
	{"title": "搬运：羊圈 ↔ 手 ↔ 栅栏", "ops": ["INBOX", "OUTBOX"]},
	{"title": "木牌：唯一能把值存下来的地方（copy 的源还在，move 的源没了 —— 和 cp / mv 一样）", "ops": ["COPYFROM", "MOVETO"]},
	{"title": "算术：只在手上算，结果留在手上", "ops": ["ADD", "SUB", "BUMPUP", "BUMPDN"]},
	{"title": "跳转 —— 比较就藏在这一类里（没有单独的「比较」牌）", "ops": ["JUMP", "JUMPZ", "JUMPN"]},
	{"title": "其他", "ops": ["COMMENT"]},
]

# 行高统一到 44。实测：带参数的行（SpinBox / OptionButton）被内容撑到 44，
# 不带的只有 34 —— 一列下来参差不齐，而且加一条带参数的指令，整表高度会跳一下。
# 让每一行都占同样的格子，长度变化才是「匀速」的。
const ROW_H := 44.0
const ROW_SEP := 4.0
const DRAG_START_PX := 5.0      # 移动超过这个距离才算拖拽，否则算点击
const EDGE_SCROLL_PX := 30.0    # 拖到列表上下边缘这么近就自动滚

const SAVE_PATH := "user://progress.json"
var save_path: String = SAVE_PATH   # 测试可改指到别的文件，避免污染真实进度

# 表头对齐用的两个数（见 _build_body 与 _on_lanes_changed）
const COLHEAD_SEP := 8          # 表头各列名的间距
const ROW_TEXT_INSET := 13      # 行卡内文字左沿 = border 2 + padding 11

## 基调：明亮卡通牧场。所有材质都在 ui_kit 里，这里只写角色名。
const Kit = preload("res://scripts/ui_kit.gd")
## 贴图皮肤（Crisp Kit Free）。没下/没导入时自动回退到上面那套手搓样式。
const SkinCrisp = preload("res://scripts/skin_crisp.gd")
## 多语言：所有界面文案在**建控件的那一刻**翻一次。
## 汇聚在这里而不是每个调用点各写一遍，是因为「漏翻」在游戏里是不报错的 ——
## 少包一个就只有一句中文混在英文界面里，测试和截图都看不出来。
## 所以宁可让 _label / _button 统一过一道 t()（非中文原样返回）。
const I18n = preload("res://scripts/i18n.gd")
const GeoLang = preload("res://scripts/geo_lang.gd")
const Sfx = preload("res://scripts/sfx.gd")

const C_BG := Kit.BG
const C_PANEL := Kit.WOOD
const C_PANEL2 := Kit.WOOD_3
const C_LINE := Kit.EDGE
const C_ACCENT := Kit.AMBER
const C_TEXT := Kit.TEXT
const C_MUTED := Kit.MUTED
const C_OK := Kit.GREEN
const C_ERR := Kit.RED

# 标签色板已经从「全界面唯一暖色」升级成 a/b/c/d 四色，
# 唯一真源搬到 Kit.label_tint（跳转线也要用同一份）。见 ui_kit.gd。

var levels: Array = []
var li: int = 0
var level: Dictionary = {}
var program: Array = []
var vm = null
var playing: bool = false
var acc: float = 0.0

# 运行节奏：**不做手动倍率**，而是「这一趟跑得越顺，播放越快」。
# 起点 0.26s/步（看得清羊走位、听得清节拍），最快 0.075s/步（约 13 步/秒 ——
# 再快行高亮和音效就糊成一片，那不是刺激，是噪声）。
# 玩家能感到的是「同一段程序，第二遍跑起来像上发条」，
# 而不是「把倍率调到 4×」这种设置项 —— 后者是播放器，前者才是游戏。
const STEP_SLOW := 0.26
const STEP_FAST := 0.075
const STEP_DECAY := 0.86        # 每多跑一步，富余的那段等待砍掉 14%
var tick: float = STEP_SLOW     # 当前实际间隔（由 combo 算出）
var combo: int = 0              # 本次运行连续成功步数；出错 / 重置 / 切关归零
## 最近执行过的行号（新的在前，最多 3 个）。用来给「刚跑过的行」留一点绿 ——
## 这就是加速在画面上的形式：起步时一行亮，全速时三四行一起亮，整列像一道扫描线。
var _trail: Array = []
var sfx: Node = null            # 程序化音效（见 sfx.gd）
var sel: int = -1
var target_size: int = 0
var target_speed: float = 0.0
var progress: Dictionary = {}          # 关卡成绩 {"1": {cleared,size,speed,hint}}
var allstar_ack: bool = false          # 「四十关全三星」这张卡只弹一次（落盘）
var saved_programs: Dictionary = {}    # 玩家自己写的程序 {"1": [ {op,arg,label} ]}
var demo_mode: bool = false            # CLI 截图/演示：自动填参考解，且不写存档
var _dirty: bool = false
var _save_cd: float = 0.0
var stuck_time: float = 0.0            # 本关停留时长，用来决定「提示」何时出现
var hint_stage: int = 0                # 记录：0 未看 / 1 看过思路 / 2 看过指令 / 3 已填入参考解
var hint_view: int = 0                 # 当前贴在舞台上的那一张（回看不改 hint_stage）
const STUCK_SEC := 60.0                # 卡多久才给提示
var _hint_left: int = -1

# 通关结算卡。挂在 CanvasLayer 上而不是塞进根 VBox ——
# 根布局有 776 的高度硬预算，结算卡是「事件」不是「常驻模块」，
# 让它浮在所有东西上面才是最省的，也才符合「通关是一个时刻」这件事。
var win_layer: Control        # 普通 Control（CanvasLayer 在 Web 上点不动，见 _build_win_card）
var win_card: PanelContainer
var win_title: Label
var win_sub: Label
var win_badge: Label
var win_stars: Array = []
var win_rows: VBoxContainer
var win_next_btn: Button
var _win_token: int = 0                # 防止延迟弹出的卡片盖到下一关
const WIN_DELAY := 0.85                # 先让玩家看彩纸，再出卡片

# 设置浮层（音量）。和结算卡同一个道理：事件用浮层，常驻才进 VBox。
var btn_set: Button = null
var set_layer: Control = null       # 普通 Control，不是 CanvasLayer（原因见 _build_settings）
var sld_vol: HSlider = null
var lbl_vol: Label = null
const AUDIO_VOL := 0.8                 # 默认音量：不炸耳，也不至于听不见节拍
## 当前被鼠标压着的那一行程序。显隐 × 的唯一真相来源（见 _update_row_hover）。
var _hover_row: Control = null
## 重建后要重判一次 hover（下一帧，等行排版完），否则 × 会闪一下
var _hover_dirty: bool = false

var stage = null
var lbl_level_name: Label
var lbl_size: Label
var lbl_speed: Label
var lbl_cycles: Label
var lbl_best: Label
var lbl_status: Label
var box_rows: VBoxContainer
var scroll_rows: ScrollContainer
## 跳转线层：盖在行卡之上，只画线不接事件
var jump_arcs: Control = null
var row_gutter: MarginContainer = null   # 行列表左侧那条给跳转线走的空栏（宽度随车道数变）
var head_pad: Control = null             # 表头左侧的伸缩垫片，跟着空栏一起变宽
var row_nodes: Array = []
var _last_pc_shown: int = -1
var undo_stack: Array = []
var redo_stack: Array = []
const UNDO_MAX := 100
var box_palette: Container
var scroll_pal: ScrollContainer
var root_box: VBoxContainer
var lbl_insert_hint: Label
var lbl_op_help: Label
var palette_nodes: Dictionary = {}
## 关卡选择从「20 行清单」换成「20 块地砖」以后，选中/进度不再由 Button 承担，
## 而是这张自绘地图；main 只负责把「过没过、几颗星」算好塞进去。
## 地图本身不常驻：它是「想去别关」时才需要的东西，收在抬头的关号徽章里（见 _toggle_level_map）。
## 所以这几个节点平时都是 null —— 和 doc_layer 一个路子。
var map_levels: Control = null
var map_pop: Control = null        # 地图浮层（null = 收着）
var lbl_levels_title: Label = null
var lbl_stars_total: Label = null
var lbl_map_page: Label = null     # 「第 1 / 2 页」
var btn_map_go: Button = null      # 「进入第 N 关 ›」——点砖只改它的字，不会直接走人
## 每关参考解的成绩（指令数 / 周期），第一次问时现算并缓存。
## 有了它，「这一关几颗星」才与「当前打开的是哪一关」无关 ——
## 原来 _stars() 拿当前关的 target 去比别的关，地图一铺开就全错。
var level_targets: Dictionary = {}
# HUD 抬头（顶部那一条）：关号徽章 + 星级。它们只读当前关，跟着 load_level 走。
var btn_level: Button            # 关号码牌：本身是打开牧场地图的按钮
var btn_lang: Button             # 语言切换（字面是「切过去的那门语言」）
var lbl_hud_no: Label
var lbl_hud_total: Label
var star_nodes: Array = []
var btn_run: Button
var btn_next: Button
var btn_hint: Button
var btn_doc: Button
var doc_layer: Control = null       # 指令说明书弹窗（null = 没开）
var doc_entries: Array = []         # 弹窗里画了哪几张牌，测试与调试用

## 新手引导的呼吸对象（指令面板第一块牌）和它的 tween。
## 只点一块：把整片面板都点亮等于没点亮。
var _guide_btn: Control = null
var _guide_tween: Tween = null

# ---- 自建拖拽（内建 DnD 的命中太苛刻：行间缝隙、行内按钮都会漏）
var panel_prog: Control = null
var _press_on: bool = false          # 鼠标按下中（还没判定是点击还是拖拽）
## 竖屏行卡左边缘多宽算「握把」。左边按下去 = 拖这一行，右边 = 滚列表。
## 用位置分区而不是长按计时：等待是不可见的，玩家永远要试两次才知道要等多久；
## 而「手指在左还是在右」是能看出来的，也能在界面上画出来。
const ROW_HANDLE_W := 58.0
var _pal_drag: bool = false          # 手指/鼠标正按在指令条上
var _press_kind: String = ""         # "row" 拖已有行 / "new" 拖新指令 / "scroll" 拖空白滚列表
var _press_op: String = ""
var _press_from: int = -1
var _press_pos: Vector2 = Vector2.ZERO
var _drag_on: bool = false
var _drag_pos: Vector2 = Vector2.ZERO
var _drag_idx: int = -1              # 当前插入位（程序下标，-1 = 不在投放区）
var _ghost: Control = null
var _gap = null                      # DragGap 节点
var _gap_idx: int = -1
# 「按住往下拖」滚列表 —— 和「按住行拖动」是两个动作：
# 一个是在看，一个是在改。挂在同一个手势上必然有一个不可预期，
# 所以按位置分工：行卡上拖 = 挪动这一行，行尾空档上拖 = 滚列表。
var _scroll_drag: bool = false
var _scroll_from: float = 0.0        # 按下时的 scroll_vertical
var _scroll_y0: float = 0.0          # 按下时的鼠标 y
var _scroll_keep: int = 0            # 这次拖动滚到的位置（松手后要补回去）


var _bg_tex: GradientTexture2D = null
var _vig_tex: GradientTexture2D = null
var _grain: NoiseTexture2D = null


## 背景：夜色竖向渐变 + 远景 + 径向暗角。两个渐变纹理只建一次，之后整帧拉伸绘制。
func _draw() -> void:
	if _bg_tex == null:
		_make_backdrop()
	draw_texture_rect(_bg_tex, Rect2(Vector2.ZERO, size), false)
	_draw_scenery()
	draw_texture_rect(_vig_tex, Rect2(Vector2.ZERO, size), false)
	# 全屏颗粒：极轻的一层，把所有色块「压」在同一张材质上。
	# 明快卡通不需要旧版那么重，0.02 只够消掉大色块的塑料平整感。
	if _grain != null:
		draw_texture_rect(_grain, Rect2(Vector2.ZERO, size), true, Color(1, 1, 1, 0.02))


## 远景：雾里的山脊 + 一轮低月亮 + 几点星。
##
## 这一层解决的是一个具体问题 —— 「这屏像软件」。
## 面板之间会露出 8~10px 的缝，缝里如果只是纯色渐变，整屏读起来就是
## 「几个带边框的区域拼在一起」，那是窗格；缝里能看见山、看见月亮，
## 读起来才是「一张画，UI 压在上面」。
##
## 所以强度必须刻意压到很低：这层的任务不是被看见，而是**在缝里被察觉到**。
## 一旦它开始抢眼，就变成壁纸了，壁纸比窗格更糟。
func _draw_scenery() -> void:
	var w: float = size.x
	var h: float = size.y
	if w < 10.0 or h < 10.0:
		return

	# 月亮：右上角一轮，外面两圈极淡的光晕。不画满月细节 —— 细节会抢面板的对比度
	var mp := Vector2(w * 0.885, h * 0.155)
	draw_circle(mp, 96.0, Color(0.78, 0.92, 1.0, 0.010))
	draw_circle(mp, 68.0, Color(0.78, 0.92, 1.0, 0.016))
	draw_circle(mp, 44.0, Color(0.86, 0.95, 1.0, 0.045))

	# 星：几个散点，位置写死（随机数会让每次启动都不一样，截图比对就没法做了）
	var stars := [
		Vector2(0.14, 0.10), Vector2(0.22, 0.22), Vector2(0.31, 0.07),
		Vector2(0.47, 0.15), Vector2(0.63, 0.06), Vector2(0.72, 0.24),
		Vector2(0.90, 0.34), Vector2(0.06, 0.30), Vector2(0.55, 0.31),
	]
	for i in stars.size():
		var p: Vector2 = stars[i]
		var r: float = 1.4 + float(i % 3) * 0.5
		draw_circle(Vector2(p.x * w, p.y * h), r, Color(0.85, 0.94, 1.0, 0.22))

	# 山脊：三层，越靠下越深（远处被雾吃掉，近处压成剪影）。
	# 用正弦拼折线而不是手写点，是为了换成任意窗口尺寸都不出错。
	var bands := [
		[0.66, 0.030, 0.0, 0.055],
		[0.76, 0.042, 1.7, 0.085],
		[0.88, 0.055, 3.4, 0.125],
	]
	for b in bands:
		var base: float = h * float(b[0])
		var amp: float = h * float(b[1])
		var phase: float = float(b[2])
		var alpha: float = float(b[3])
		var pts := PackedVector2Array()
		pts.append(Vector2(-12.0, h + 12.0))
		var x: float = -12.0
		while x <= w + 12.0:
			var t: float = x / w
			var y: float = base - amp * (0.60 + 0.40 * sin(t * 7.4 + phase)) \
				- amp * 0.35 * sin(t * 17.0 + phase * 2.1)
			pts.append(Vector2(x, y))
			x += 16.0
		pts.append(Vector2(w + 12.0, h + 12.0))
		# 山用「比底色更深」的冷蓝，不是更亮：亮色会浮起来，深色才会退到后面
		draw_colored_polygon(pts, Color(0.004, 0.045, 0.085, 0.16 + alpha * 0.55))


func _make_backdrop() -> void:
	var g := Gradient.new()
	g.offsets = PackedFloat32Array([0.0, 0.55, 1.0])
	g.colors = PackedColorArray([Color("0a3f6c"), Color("06294a"), Color("041c33")])
	_bg_tex = GradientTexture2D.new()
	_bg_tex.gradient = g
	_bg_tex.fill_from = Vector2(0.0, 0.0)
	_bg_tex.fill_to = Vector2(0.0, 1.0)
	_bg_tex.width = 8
	_bg_tex.height = 256

	var v := Gradient.new()
	v.offsets = PackedFloat32Array([0.0, 0.62, 1.0])
	# 卡通底色不需要压角：深色暗角会立刻把画面拉回「深夜」。只留极轻的一层，
	# 让面板边缘的硬影和底色能咬住，不至于完全平。
	v.colors = PackedColorArray([Color(0, 0, 0, 0.0), Color(0, 0, 0, 0.03), Color(0, 0, 0, 0.16)])
	_vig_tex = GradientTexture2D.new()
	_vig_tex.gradient = v
	_vig_tex.fill = GradientTexture2D.FILL_RADIAL
	_vig_tex.fill_from = Vector2(0.5, 0.42)
	_vig_tex.fill_to = Vector2(0.5, 1.05)
	_vig_tex.width = 256
	_vig_tex.height = 256

	var n := FastNoiseLite.new()
	n.noise_type = FastNoiseLite.TYPE_SIMPLEX
	n.frequency = 0.62
	n.fractal_octaves = 2
	_grain = NoiseTexture2D.new()
	_grain.noise = n
	_grain.width = 128
	_grain.height = 128
	_grain.seamless = true


func _ready() -> void:
	texture_repeat = CanvasItem.TEXTURE_REPEAT_ENABLED
	_apply_font()
	# 偏好要在定布局**之前**读：方向决定用哪套布局，专注决定舞台在不在。
	# 读晚了就得「先建错一次再重建」—— 开机时那一下闪烁就是这么来的。
	_orient_mode = _read_orient()
	_focus = _read_focus()
	# 横竖屏要在建界面之前定下来：两套布局的元素不一样，建成再换就是整屏重建。
	_apply_base_size()
	if not get_window().size_changed.is_connected(_on_window_resized):
		get_window().size_changed.connect(_on_window_resized)
	# 音效要早于界面：音色是合成出来的，第一次播放时才合成会在开局卡一下。
	sfx = Sfx.new()
	add_child(sfx)
	sfx.set_master_volume(_read_audio())
	# 语言必须定在 _build_ui 之前：界面文案是在「建控件那一刻」翻好的，
	# 建完再改就得整屏重建一遍（那是换语言的动作，不该发生在开机时）。
	_boot_locale()
	_load_progress()
	levels = _load_levels()
	_build_ui()
	_build_win_card()
	_build_settings()
	if levels.size() > 0:
		load_level(0)
	_handle_cli()


## 自建拖拽的中枢。放在 _input（早于 GUI），所以不管是拖到行、行间缝隙、按钮上还是空白处，
## 都在同一处算插入位 —— 不存在「必须对准」这回事。
func _input(event: InputEvent) -> void:
	# 说明书弹窗开着时，只认 Esc —— 不能让空格/方向键在背后驱动游戏
	if doc_layer != null:
		if event is InputEventKey and event.pressed and event.keycode == KEY_ESCAPE:
			_close_doc()
			get_viewport().set_input_as_handled()
		return
	# 结算卡开着时，Esc 收掉卡片回去看彩纸（不舍得关的人可以留着看成绩）
	if win_layer != null and win_layer.visible:
		if event is InputEventKey and event.pressed and event.keycode == KEY_ESCAPE:
			_hide_win_card()
			get_viewport().set_input_as_handled()
			return
	# 指令条的横向拖动：自己算，不接 ScrollContainer 的触摸滚动 ——
	# 它内部把「能不能拖」绑在 is_touchscreen_available() 上，Web 导出拿不到真值，
	# 表现是「手指划过去，条子一动不动」，而且不报错。
	# 也不接子控件的信号：牌子是 MOUSE_FILTER_STOP，ScreenDrag 冒不上来。
	# 按坐标判断「手指在不在指令条矩形里」最稳，代价只是几行几何。
	if _tall and scroll_pal != null:
		if event is InputEventScreenTouch:
			var st := event as InputEventScreenTouch
			_pal_drag = st.pressed and scroll_pal.get_global_rect().has_point(st.position)
		elif event is InputEventScreenDrag:
			if _pal_drag:
				scroll_pal.scroll_horizontal -= int(round((event as InputEventScreenDrag).relative.x))
				get_viewport().set_input_as_handled()
				return

	# 程序行的悬停状态由「鼠标位置」统一裁决，不依赖各行的 mouse_entered/exited。
	# 原因见 _update_row_hover 的注释 —— 那个信号在这件事上是靠不住的。
	if event is InputEventMouseMotion:
		_update_row_hover((event as InputEventMouseMotion).global_position)
	if not _press_on:
		return
	if event is InputEventMouseMotion:
		_drag_pos = event.global_position
		# 拖空白滚列表：跟手，不判距离阈值 —— 拖滚动本来就是个「立刻响应」的动作
		if _scroll_drag:
			_scroll_keep = int(_scroll_from - (_drag_pos.y - _scroll_y0))
			scroll_rows.scroll_vertical = _scroll_keep
			get_viewport().set_input_as_handled()
			return
		if not _drag_on and _drag_pos.distance_to(_press_pos) > DRAG_START_PX:
			_start_drag()
		if _drag_on:
			_refresh_drag_target()
			get_viewport().set_input_as_handled()
	elif event is InputEventMouseButton and event.button_index == MOUSE_BUTTON_LEFT and not event.pressed:
		if _scroll_drag:
			_scroll_drag = false
			_press_on = false
			_restore_scroll(_scroll_keep)
			get_viewport().set_input_as_handled()
		elif _drag_on:
			_end_drag(true)
			get_viewport().set_input_as_handled()
		else:
			# 没挪动 = 点击：新指令点一下就追加（拖拽成功时走上面那条）
			var was_new: bool = _press_kind == "new"
			var op: String = _press_op
			_press_on = false
			if was_new:
				_append(op)
	elif event is InputEventKey and event.pressed and event.keycode == KEY_ESCAPE:
		if _drag_on:
			_end_drag(false)
			get_viewport().set_input_as_handled()


func _unhandled_input(event: InputEvent) -> void:
	if event is InputEventKey and event.pressed and not event.echo:
		if event.keycode == KEY_F1:
			if doc_layer == null:
				_open_doc()
			else:
				_close_doc()
			get_viewport().set_input_as_handled()
			return
	if doc_layer != null:
		return
	if event is InputEventKey and event.pressed and not event.echo:
		match event.keycode:
			KEY_SPACE:
				_on_run()
				get_viewport().set_input_as_handled()
			KEY_RIGHT:
				_on_step()
				get_viewport().set_input_as_handled()
			KEY_R:
				_on_reset()
				get_viewport().set_input_as_handled()
			KEY_L:
				_reload_level_data()
				get_viewport().set_input_as_handled()
			KEY_UP:
				if event.alt_pressed and sel >= 0:
					_move_row(sel, -1)
					get_viewport().set_input_as_handled()
			KEY_DOWN:
				if event.alt_pressed and sel >= 0:
					_move_row(sel, 1)
					get_viewport().set_input_as_handled()
			KEY_Z:
				if event.ctrl_pressed:
					if event.shift_pressed:
						_redo()
					else:
						_undo()
					get_viewport().set_input_as_handled()
			KEY_Y:
				if event.ctrl_pressed:
					_redo()
					get_viewport().set_input_as_handled()
			KEY_D:
				if event.ctrl_pressed and sel >= 0:
					_duplicate_row(sel)
					get_viewport().set_input_as_handled()


func _process(delta: float) -> void:
	if _hover_dirty:
		_hover_dirty = false
		_update_row_hover(get_global_mouse_position())
	if _drag_on:
		_edge_scroll(delta)
	if playing:
		acc += delta
		# 用 while 而不是 if：加速到 0.075s 时一帧可能跨过不止一个间隔，
		# 用 if 会把多出来的时间攒在 acc 里，表现出来就是「越跑越滞后、然后突然连跳两步」。
		var guard: int = 0
		while playing and acc >= tick and guard < 8:
			acc -= tick
			_step_once()
			guard += 1
	# 只要还没通关就算「卡住」，失败也算——失败往往更需要提示
	if vm != null and not vm.finished and not demo_mode:
		stuck_time += delta
		_update_hint_hint()
	# 编辑后延迟落盘，避免每敲一下都写文件
	if _dirty:
		_save_cd -= delta
		if _save_cd <= 0.0:
			_dirty = false
			_save_progress()


# ---------------------------------------------------------------- 数据 / 存档

func _load_levels() -> Array:
	var f: FileAccess = FileAccess.open("res://data/levels.json", FileAccess.READ)
	if f == null:
		push_error("读不到 levels.json")
		return []
	var data: Variant = JSON.parse_string(f.get_as_text())
	if typeof(data) != TYPE_ARRAY:
		push_error("levels.json 解析失败")
		return []
	return data


## 开发期热重载：改完 data/levels.json 按 L，不重启、不重导出。
## 导出后 res:// 是打包内容，读到的仍是导出时的快照——只对直接跑工程有效。
func _reload_level_data() -> void:
	var keep: int = li
	var fresh: Array = _load_levels()
	if fresh.size() == 0:
		if lbl_status != null:
			lbl_status.text = I18n.t("levels.json 读取失败，保留原数据")
		return
	levels = fresh
	level_targets.clear()      # 关卡数据换了，参考解缓存必须作废，否则星数照旧
	load_level(clampi(keep, 0, levels.size() - 1))
	if lbl_status != null:
		lbl_status.text = I18n.tf("已重新载入 %d 关 · 进度保留", [levels.size()])


## 工程改名会换掉 user:// 目录，这里把旧目录的存档搬过来，避免进度丢失
func _migrate_legacy_save() -> void:
	if save_path != SAVE_PATH:
		return
	var legacy: String = OS.get_user_data_dir().get_base_dir() \
		.path_join("HRM Clone Prototype").path_join("progress.json")
	if not FileAccess.file_exists(legacy):
		return
	var f: FileAccess = FileAccess.open(legacy, FileAccess.READ)
	if f == null:
		return
	var txt: String = f.get_as_text()
	f.close()
	var w: FileAccess = FileAccess.open(save_path, FileAccess.WRITE)
	if w != null:
		w.store_string(txt)
		w.close()


func _load_progress() -> void:
	progress = {}
	saved_programs = {}
	allstar_ack = false
	if not FileAccess.file_exists(save_path):
		_migrate_legacy_save()
	if not FileAccess.file_exists(save_path):
		return
	var f: FileAccess = FileAccess.open(save_path, FileAccess.READ)
	if f == null:
		return
	var d: Variant = JSON.parse_string(f.get_as_text())
	if typeof(d) != TYPE_DICTIONARY:
		return
	if d.has("levels"):
		progress = d.get("levels", {})
		saved_programs = d.get("programs", {})
		allstar_ack = bool(d.get("allstar", false))
	else:
		# 旧存档：顶层直接就是 {"1": {cleared,size,speed}}，原地接过来
		progress = d
		saved_programs = {}


func _save_progress() -> void:
	var f: FileAccess = FileAccess.open(save_path, FileAccess.WRITE)
	if f == null:
		return
	f.store_string(JSON.stringify({"ver": 2, "levels": progress, "programs": saved_programs,
		"allstar": allstar_ack}, "  "))
	f.close()


## 把当前程序写进「我的解」。空程序视为清空，避免删光后还留着旧解。
func _stash_program() -> void:
	if demo_mode:
		return
	var key: String = str(int(level.get("id", 0)))
	if key == "0":
		return
	if program.is_empty():
		saved_programs.erase(key)
	else:
		var arr: Array = []
		for ins in program:
			arr.append({
				"op": String(ins.get("op", "")),
				"arg": ins.get("arg", null),
				"label": String(ins.get("label", "")),
			})
		saved_programs[key] = arr
	_dirty = true
	_save_cd = 0.5


## 验关用：把参考解铺进「我的解」。spec 支持「20-40」范围 /「21」单关 /「all」。
## 写的是玩家程序的位置 —— 会覆盖这些关里自己写的程序，所以只做在命令行开关里。
## demo_mode（--shot）下只填内存不写盘：截图不该改玩家存档。
## persist=false 时只改内存、不落盘。
## 回归测试要验「铺进去的结构对不对」，但它跑在玩家的真实存档目录上 ——
## 默认落盘的话，每跑一次 test_ui 就把 40 关参考答案重新写回玩家存档，
## 而达叔要的恰恰是「打开就是空白」。这类污染不报错，只表现为「答案怎么又回来了」。
func _fill_programs(spec: String, persist: bool = true) -> void:
	var lo: int = 0
	var hi: int = levels.size() - 1
	if spec != "all":
		var parts: PackedStringArray = spec.split("-")
		lo = clampi(int(parts[0]) - 1, 0, levels.size() - 1)
		hi = clampi(int(parts[parts.size() - 1]) - 1, lo, levels.size() - 1)
	var n_filled: int = 0
	for i in range(lo, hi + 1):
		var ref: Array = levels[i].get("ref", [])
		if ref.is_empty():
			continue
		saved_programs[str(int(levels[i].get("id", i + 1)))] = HrmVM.parse_program(ref)
		n_filled += 1
	_dirty = true
	if persist and not demo_mode:
		_save_progress()     # 立刻落盘：这不是随手一改，是专门要留着用的
	# 开发者日志用英文：i18n 的「原文即 key」只收玩家看得到的文案，
	# 调试输出混进去只会让体检报一条假漏翻。
	# 落没落盘必须说清楚：回归测试用 persist=false 调它，
	# 输出里还写「overwritten」会让人以为玩家的存档又被冲了一遍（我自己就被骗过一次）。
	if persist and not demo_mode:
		print("[fill] filled %d levels (%d-%d), saved to disk." % [n_filled, lo + 1, hi + 1])
	else:
		print("[fill] filled %d levels (%d-%d) in memory only, nothing written." % [n_filled, lo + 1, hi + 1])


## 取出玩家上次写的程序；没有就返回空数组（空白开局）
func _program_from_save(key: String) -> Array:
	if not saved_programs.has(key):
		return []
	var raw: Variant = saved_programs[key]
	if typeof(raw) != TYPE_ARRAY:
		return []
	var out: Array = []
	for e in raw:
		if typeof(e) != TYPE_DICTIONARY:
			continue
		out.append({
			"op": HrmVM.canon_op(String(e.get("op", ""))),
			"arg": e.get("arg", null),
			"label": String(e.get("label", "")),
		})
	return out


## 记录成绩。返回值喂给通关结算卡：
##   first        —— 这张图第一次通过（决定标题写「数完啦」还是「又数完啦」）
##   size_better  —— 指令数刷了自己的最好成绩（**首次通关不算，否则两个标签会一起冒出来**）
##   speed_better —— 速度刷了自己的最好成绩
func _record_win(size_now: int, speed_now: float) -> Dictionary:
	var out := {"first": false, "size_better": false, "speed_better": false, "hint": hint_stage >= 3}
	var key: String = str(int(level.get("id", 0)))
	var rec: Dictionary = progress.get(key, {})
	if hint_stage >= 3:
		rec["hint"] = true      # 看过完整解法：成绩保留，但不再算「自己想出来的」
	var changed: bool = false
	if not rec.has("cleared"):
		rec["cleared"] = true
		out["first"] = true
		changed = true
	if size_now < int(rec.get("size", 999999)):
		rec["size"] = int(size_now)
		if not out["first"]:
			out["size_better"] = true
		changed = true
	if speed_now < float(rec.get("speed", 1.0e9)):
		rec["speed"] = snappedf(speed_now, 0.01)
		if not out["first"]:
			out["speed_better"] = true
		changed = true
	progress[key] = rec
	if changed:
		# 演示/截图模式下**仍然更新内存里的成绩**（否则星级永远算成 0 星，截出来的
		# 结算卡是「三颗灰星」，看不出效果），但**绝不落盘** ——
		# 一次截图就污染真实存档，是比截图不好看严重得多的 bug。
		if not demo_mode:
			_save_progress()
		_refresh_level_buttons()
		_refresh_hud()
	return out


func _best_text(id: int) -> String:
	var key: String = str(id)
	if not progress.has(key):
		return ""
	var rec: Dictionary = progress[key]
	if not rec.get("cleared", false):
		return ""
	# ★ 自己写的解；☆ 看过参考解才过的关。区别保留，但都算通关。
	var mark: String = "☆" if rec.get("hint", false) else "★"
	return "%s %d·%.1f" % [mark, int(rec.get("size", 0)), float(rec.get("speed", 0.0))]


func load_level(i: int) -> void:
	# 切关前先把上一关的程序落盘，别丢
	if not demo_mode and not level.is_empty():
		_stash_program()
	# 说明书讲的是上一关的牌，切关就收掉
	_close_doc()
	# 拖拽中切关：行节点要重建，先把拖拽状态收掉，避免悬空引用
	if _drag_on:
		_clear_drag_nodes()
		_drag_on = false
		_press_on = false
	li = clampi(i, 0, levels.size() - 1)
	level = levels[li]
	var key: String = str(int(level.get("id", 0)))
	program = _program_from_save(key)     # 空白开局：只有你自己写过才有内容
	hint_stage = 0
	hint_view = 0
	stuck_time = 0.0
	sel = -1
	_refresh_targets()
	_reset_run()
	_refresh_static()
	_rebuild()
	_rebuild_palette()
	_refresh_level_buttons()
	_refresh_hud()
	_refresh_hint_ui()
	if not demo_mode:
		_save_progress()


## 当前关的两个目标值。现在从 _target_of 取，判据只有一份 ——
## 原来这里和 _stars 各算一遍参考解，两边一改就容易走岔。
func _refresh_targets() -> void:
	var t: Dictionary = _target_of(li)
	target_size = int(t.get("size", 0))
	target_speed = float(t.get("speed", 0.0))


# ---------------------------------------------------------------- 运行控制

func _reset_run() -> void:
	_hide_win_card()
	vm = HrmVM.new()
	vm.setup(level, program)
	playing = false
	acc = 0.0
	combo = 0
	_trail.clear()
	tick = _cur_tick()
	if stage != null:
		stage.configure(level)
		stage.pace = 1.0
		stage.sync_from_vm(vm)
	_refresh_runtime()


## 当前间隔：越跑越快，但有下限。指数收缩，前几步掉得最快 —— 起速感来自头三下。
func _cur_tick() -> float:
	return STEP_FAST + (STEP_SLOW - STEP_FAST) * pow(STEP_DECAY, float(combo))


## 记一行「刚跑过」。重复的不记：原地打转的循环只该亮一行，不该把整列都染绿。
func _push_trail(pc: int) -> void:
	if pc < 0:
		return
	if not _trail.is_empty() and int(_trail[0]) == pc:
		return
	_trail.push_front(pc)
	if _trail.size() > 3:
		_trail.resize(3)


func _trail_level(i: int) -> int:
	for k in _trail.size():
		if int(_trail[k]) == i:
			return k + 1
	return 0


## 每一步的声音分工：click 是节拍器（每步都响、很轻、随 combo 升调），
## out / wood 是重音（只在真动到东西的那一步叠上去）。
## 高速度时就是「底鼓 + 军鼓」，而不是十几个声音一起糊成噪声。
##
## out 的音高跟的是「今天第几只」而不是 combo —— 数满一关就是一段上行音阶，
## 玩家不用看仪表也能听出「快数完了」。
func _sfx_step(op: String, semi: float) -> void:
	if sfx == null:
		return
	sfx.play("click", semi)
	match op:
		"OUTBOX":
			sfx.play("out", float(mini(vm.outbox.size(), 12)) if vm != null else 0.0)
		"COPYFROM", "MOVETO", "BUMPUP", "BUMPDN":
			sfx.play("wood", semi * 0.5)


func _step_once() -> void:
	if vm == null:
		return
	vm.step()
	_push_trail(vm.last_pc)
	if vm.failed:
		combo = 0
		if sfx != null:
			sfx.play("err")
	else:
		combo += 1
		if vm.last_op != "" and vm.last_op != "COMMENT":
			_sfx_step(vm.last_op, minf(float(combo), 12.0))
	if stage != null:
		if vm.last_op != "" and vm.last_op != "COMMENT":
			stage.act(vm.last_op, vm.last_arg)
		stage.sync_from_vm(vm)
	_refresh_runtime()
	tick = _cur_tick()
	if stage != null:
		stage.pace = tick / STEP_SLOW
	if vm.finished:
		playing = false
		var info: Dictionary = _record_win(HrmVM.program_size(program), vm.speed())
		var finals: bool = _claim_allstar()
		_play_win(info)
		_update_buttons()
		_show_win_card(info, finals)
	elif vm.failed:
		playing = false
		_update_buttons()


## 四十关全三星。**判据现算，不靠累加的计数器** —— 玩家删档、改判据、
## 或者我以后调了星的标准，都不会留下一个「说过全三星」的假状态。
func _all_stars() -> bool:
	if levels.is_empty():
		return false
	for i in levels.size():
		if _stars_of_idx(i) < 3:
			return false
	return true


## 拿到的星一共几颗。全三星卡上要写出来 —— 「120 / 120」比「100%」有分量。
func _star_total() -> int:
	var n: int = 0
	for i in levels.size():
		n += _stars_of_idx(i)
	return n


## 首次达成时返回 true 并记下来；之后永远返回 false（这张卡只该看一次）。
## demo_mode 下不落盘也不弹 —— 截图不该改玩家进度。
func _claim_allstar() -> bool:
	if allstar_ack or demo_mode:
		return false
	if not _all_stars():
		return false
	allstar_ack = true
	_dirty = true
	return true


## 过关音：三个音上行。**刷了自己的 SPEED 才多一声「叮」**，
## 让「我这次更快」有它自己的声音，而不是靠结算卡上一个小标签。
func _play_win(info: Dictionary) -> void:
	if sfx == null:
		return
	sfx.play("win")
	if not bool(info.get("speed_better", false)):
		return
	var tree: SceneTree = get_tree()
	if tree == null:
		return
	# 不能用 await：_step_once 在 while 循环里被调用，让出一次就乱序了
	tree.create_timer(0.34).timeout.connect(func() -> void:
		if is_instance_valid(sfx):
			sfx.play("ding"))


func _on_run() -> void:
	if vm.finished or vm.failed:
		_reset_run()
	playing = not playing
	acc = 0.0
	tick = _cur_tick()
	_update_buttons()


## 手动单步：**不涨 combo**。combo 描述的是「连续自动运行」，
## 单步是玩家自己在推 —— 让它也涨的话，一步步点 20 次再按运行就直接全速了，
## 那就成了可以提前预支的加速，不是跟着手感长出来的加速。
## 但声音照给：单步同样需要「这一步做对了」的确认。
func _on_step() -> void:
	playing = false
	if vm.finished or vm.failed:
		_reset_run()
	vm.step()
	_push_trail(vm.last_pc)
	if vm.failed:
		if sfx != null:
			sfx.play("err")
	elif vm.last_op != "" and vm.last_op != "COMMENT":
		_sfx_step(vm.last_op, minf(float(combo), 12.0))
	if stage != null:
		if vm.last_op != "" and vm.last_op != "COMMENT":
			stage.act(vm.last_op, vm.last_arg)
		stage.sync_from_vm(vm)
	if vm.finished:
		var info2: Dictionary = _record_win(HrmVM.program_size(program), vm.speed())
		var finals2: bool = _claim_allstar()
		_play_win(info2)
		_show_win_card(info2, finals2)
	_refresh_runtime()
	_update_buttons()


func _on_reset() -> void:
	_reset_run()
	_update_buttons()


# ---------------------------------------------------------------- 程序编辑

func _default_arg(op: String) -> Variant:
	if HrmVM.MEM_OPS.has(op):
		return 0
	if HrmVM.JUMP_OPS.has(op):
		return "a"
	return null


func _append(op: String) -> void:
	var at: int = program.size()
	if sel >= 0:
		at = sel + 1
	at = clampi(at, 0, program.size())
	_push_undo()
	program.insert(at, HrmVM.make_ins(op, _default_arg(op)))
	sel = at
	# 追加到末尾 = 只在尾巴上加一个节点，别把整张表拆了重搭。
	# 点指令牌是最频繁的操作，而每次全量重建都是「20 行全部销毁、全部新建」——
	# 屏幕上看到的就是列表闪一下，滚到哪都跟着抖一下。增行只动一行，才是稳的。
	if at == program.size() - 1 and program.size() > 1 and row_nodes.size() == program.size() - 1:
		_reset_run()
		var row = _make_row(at)
		box_rows.add_child(row)
		row_nodes.append(row)
		_refresh_row_highlight()
		_update_insert_hint()
		_hover_dirty = true
		_sync_jump_arcs()
		_stash_program()
		_sync_stage_link()
		return
	_after_edit()


func _after_edit() -> void:
	_reset_run()
	_rebuild()
	_stash_program()
	_sync_stage_link()


# ---------------------------------------------------------------- 撤销 / 重做

func _push_undo() -> void:
	undo_stack.append(program.duplicate(true))
	if undo_stack.size() > UNDO_MAX:
		undo_stack.pop_front()
	redo_stack.clear()


func _undo() -> void:
	if undo_stack.is_empty():
		lbl_status.text = I18n.t("没有可撤销的操作")
		lbl_status.add_theme_color_override("font_color", C_MUTED)
		return
	redo_stack.append(program.duplicate(true))
	program = undo_stack.pop_back()
	sel = mini(sel, program.size() - 1)
	_after_edit()


func _redo() -> void:
	if redo_stack.is_empty():
		return
	undo_stack.append(program.duplicate(true))
	program = redo_stack.pop_back()
	sel = mini(sel, program.size() - 1)
	_after_edit()


## Alt+↑ / Alt+↓：比拖拽更精确的行重排
func _move_row(i: int, delta: int) -> void:
	var j: int = i + delta
	if i < 0 or i >= program.size() or j < 0 or j >= program.size():
		return
	_push_undo()
	var ins: Dictionary = program[i]
	program.remove_at(i)
	program.insert(j, ins)
	sel = j
	_after_edit()


## Ctrl+D：复制当前行到它下面
func _duplicate_row(i: int) -> void:
	if i < 0 or i >= program.size():
		return
	_push_undo()
	program.insert(i + 1, program[i].duplicate(true))
	sel = i + 1
	_after_edit()


func _delete_row(i: int) -> void:
	if i < 0 or i >= program.size():
		return
	_push_undo()
	program.remove_at(i)
	sel = clampi(i - 1, -1, program.size() - 1)
	_after_edit()


func _set_arg(i: int, v: Variant) -> void:
	if i < 0 or i >= program.size():
		return
	program[i]["arg"] = v
	_reset_run()
	_stash_program()
	_sync_stage_link()


## 编辑期联动：把「选中行引用的木牌编号」告诉舞台。
## MOVETO 2 / ADD 3 / BUMPUP 1 这类带跳转目标的指令，舞台会把那块牌子抬起来 + 挂三角，
## 让「参数 2」和「草地上第 2 块牌」一眼能对上。
## 没有参数的行（INBOX / OUTBOX）传 -1，舞台那边不做任何提示。
func _sync_stage_link() -> void:
	if stage == null:
		return
	var link: int = -1
	if sel >= 0 and sel < program.size():
		var ins: Dictionary = program[sel]
		if HrmVM.MEM_OPS.has(String(ins.get("op", ""))):
			var a: Variant = ins.get("arg", null)
			if a != null:
				link = int(a)
	stage.link_slot(link)


func _cycle_label(i: int) -> void:
	if i < 0 or i >= program.size():
		return
	var order: Array = ["", "a", "b", "c", "d"]
	var cur: String = String(program[i].get("label", ""))
	var k: int = order.find(cur)
	_push_undo()
	program[i]["label"] = order[(k + 1) % order.size()]
	sel = i
	_after_edit()


func _select(i: int) -> void:
	if sel == i:
		return
	sel = i
	# 只改两行配色，不重建列表：重建会销毁正在拖拽的行节点，拖拽因此断掉
	_refresh_row_highlight()
	_update_insert_hint()
	_sync_stage_link()


func on_row_drop(data: Dictionary, target: int) -> void:
	var kind: String = String(data.get("kind", ""))
	if kind == "row":
		var from: int = int(data.get("index", target))
		if from == target or from == target - 1:
			return
		_push_undo()
		var ins: Dictionary = program.pop_at(from)
		var to: int = target
		if from < target:
			to -= 1
		to = clampi(to, 0, program.size())
		program.insert(to, ins)
		sel = to
	elif kind == "new":
		var op: String = String(data.get("op", "INBOX"))
		_push_undo()
		var at: int = clampi(target, 0, program.size())
		program.insert(at, HrmVM.make_ins(op, _default_arg(op)))
		sel = at
	_after_edit()


# ---------------------------------------------------------------- 拖拽（自建）

## 行内按下：先选中，再按「按在左还是右」决定这次手势的归属。
##   x <= ROW_HANDLE_W  → 握把：可以拖这一行（移动几像素就拿起）
##   x >  ROW_HANDLE_W  → 滚动区：这一次按下不认领行，交给列表去滚
## 两侧的「点一下」都等于选中 —— 手感上不该因为你点偏了就不理你。
func on_row_press(i: int, gpos: Vector2, local_x: float = -1.0) -> void:
	_select(i)
	# 用**全局坐标**自己算这一下落在行内哪个位置，不信传进来的 e.position：
	# 事件可能是行卡的子控件转上来的，那时 e.position 是相对那个子控件的，
	# 拿它跟 ROW_HANDLE_W 比会得出完全错误的结论（实测：右半边被判成握把）。
	var lx: float = local_x
	if i >= 0 and i < row_nodes.size() and row_nodes[i] != null:
		lx = gpos.x - (row_nodes[i] as Control).get_global_rect().position.x
	if _tall and lx > ROW_HANDLE_W:
		_begin_press("scroll", "", -1, gpos)
		return
	_begin_press("row", "", i, gpos)


func _begin_press(kind: String, op: String, from: int, gpos: Vector2) -> void:
	# 行卡和列表容器都会收到同一次按下（行先，容器后 —— 事件是往上冒的）。
	# 行已经认领了这次按下，容器就别再抢，否则每一次点行都会被当成「拖空白」。
	if kind == "scroll" and _press_on and _press_kind != "scroll":
		return
	if vm != null and playing:
		playing = false
	_press_on = true
	_press_kind = kind
	_press_op = op
	_press_from = from
	_press_pos = gpos
	_drag_pos = gpos


## 松手后把滚动位置补回去。
## ScrollContainer 在松手那一刻会把它自己记的位置写回来，覆盖掉手动滚的值
## （实测：拖动过程中 scroll=55，松手瞬间变 0 —— 手感就是「一松手弹回顶部」）。
## 等它写完这一帧，再补一次。竖屏没有滚轮，这个位置只有我们在管，补回去不会打架。
func _restore_scroll(v: int) -> void:
	# 连写三帧：ScrollContainer 要等它自己重排完（内容高度算出来）才认这个值，
	# 只写一次很可能落在「内容高度还是 0」的那一帧上，被 clamp 回 0。
	for _k in 3:
		await get_tree().process_frame
		if scroll_rows != null:
			scroll_rows.scroll_vertical = v


func _start_drag() -> void:
	# 拖空白 = 滚列表。不建 ghost、不算插入位，只记下起点。
	if _press_kind == "scroll":
		_scroll_drag = true
		_scroll_from = float(scroll_rows.scroll_vertical)
		_scroll_y0 = _press_pos.y
		# 立刻跟上这一帧的位移：只置标志、等下一次移动才滚，会慢半拍，
		# 手感上就是「拖了但它没动，再拖一下才动」。
		_scroll_keep = int(_scroll_from - (_drag_pos.y - _scroll_y0))
		scroll_rows.scroll_vertical = _scroll_keep
		return
	_drag_on = true
	_drag_idx = -1
	_ghost = _make_ghost()
	if _ghost != null:
		add_child(_ghost)
		_ghost.global_position = _drag_pos + Vector2(18, 12)
	if lbl_insert_hint != null:
		lbl_insert_hint.text = I18n.t("拖到列表任意位置放下 —— 会自动让出空隙")


func _make_ghost() -> Control:
	var pc := PanelContainer.new()
	pc.mouse_filter = Control.MOUSE_FILTER_IGNORE
	var s := StyleBoxFlat.new()
	s.bg_color = Kit.WOOD_3
	s.set_corner_radius_all(5)
	s.border_color = C_ACCENT
	s.set_border_width_all(1)
	s.content_margin_left = 10
	s.content_margin_right = 10
	s.content_margin_top = 4
	s.content_margin_bottom = 4
	pc.add_theme_stylebox_override("panel", s)
	var l := _label("", 13, C_ACCENT)
	if _press_kind == "row":
		l.text = I18n.tf("第 %d 行", [_press_from + 1])
	else:
		l.text = _press_op
	pc.add_child(l)
	return pc


## 把鼠标位置换算成「插入到第几行」。行坐标先按「没有空隙」还原，
## 这样空隙动画把行挤下去的过程中，判定点不会跟着跳，手感才稳。
func _index_at(gpos: Vector2) -> int:
	if panel_prog == null:
		return -1
	if not panel_prog.get_global_rect().grow(40.0).has_point(gpos):
		return -1
	if program.is_empty():
		return 0
	var sr: Rect2 = scroll_rows.get_global_rect()
	var y: float = gpos.y - sr.position.y + float(scroll_rows.scroll_vertical)
	var shift: float = 0.0
	if _gap != null and _gap_idx >= 0:
		shift = float(_gap.custom_minimum_size.y) + ROW_SEP
	for i in row_nodes.size():
		var r: Control = row_nodes[i]
		if r == null:
			continue
		var top: float = r.position.y - (shift if i >= _gap_idx and shift > 0.0 else 0.0)
		if y < top + r.size.y * 0.5:
			return i
	return row_nodes.size()


func _refresh_drag_target() -> void:
	if _ghost != null:
		_ghost.global_position = _drag_pos + Vector2(18, 12)
	var idx: int = _index_at(_drag_pos)
	if idx == _drag_idx:
		return
	_drag_idx = idx
	_show_gap(idx)


## 空隙节点真插进 VBox 里：它一长高，后面的行就被挤下去，玩家看到的「位置」是真让出来的
func _show_gap(idx: int) -> void:
	if idx < 0:
		_gap_idx = -1
		if _gap != null:
			_gap.target_h = 0.0
		if lbl_insert_hint != null:
			lbl_insert_hint.text = I18n.t("拖到列表里放下（Esc 取消）")
		return
	if _gap == null or not is_instance_valid(_gap):
		_gap = DragGap.new()
		box_rows.add_child(_gap)
	_gap_idx = idx
	box_rows.move_child(_gap, clampi(idx, 0, box_rows.get_child_count() - 1))
	_gap.target_h = ROW_H
	_gap.label = I18n.t("放这里")
	if lbl_insert_hint != null:
		lbl_insert_hint.text = I18n.tf("松手 → 插到第 %d 行", [idx + 1])


func _end_drag(commit: bool) -> void:
	var idx: int = _drag_idx
	var data: Dictionary = {}
	if _press_kind == "row":
		data = {"kind": "row", "index": _press_from}
	else:
		data = {"kind": "new", "op": _press_op}
	_clear_drag_nodes()
	_press_on = false
	_drag_on = false
	if commit and idx >= 0:
		on_row_drop(data, clampi(idx, 0, program.size()))
	else:
		_update_insert_hint()


func _clear_drag_nodes() -> void:
	if _ghost != null and is_instance_valid(_ghost):
		_ghost.queue_free()
	_ghost = null
	if _gap != null and is_instance_valid(_gap):
		_gap.queue_free()
	_gap = null
	_gap_idx = -1
	_drag_idx = -1


## 拖到列表上下边缘时自动滚动，长程序也能一路拖到底
func _edge_scroll(delta: float) -> void:
	if not _drag_on or scroll_rows == null:
		return
	var sr: Rect2 = scroll_rows.get_global_rect()
	var y: float = _drag_pos.y
	var step: float = 420.0 * delta
	if y < sr.position.y + EDGE_SCROLL_PX:
		scroll_rows.scroll_vertical -= int(step)
		_refresh_drag_target()
	elif y > sr.end.y - EDGE_SCROLL_PX:
		scroll_rows.scroll_vertical += int(step)
		_refresh_drag_target()


# ---------------------------------------------------------------- 样式工具

func _apply_font() -> void:
	# 先用打包进游戏的子集字体（tools/make_font_subset.py 从思源黑体裁的，含全部
	# 界面用字）。Web 版拿不到 C:/Windows/Fonts，没有它整屏中文都是豆腐块 ——
	# 这不是「顺手带上」，是 Web 版能读字的前提。系统字体只做桌面端的兜底。
	# 必须走 load()：导出包里字体是「导入产物」，res:// 原文件根本不在包里，
	# 直接 load_dynamic_font() 读原始路径在导出版必失败（真踩过）。
	var f: FontFile = load("res://assets/fonts/app.otf")
	if f != null:
		# 界面里用的符号必须**主字体自己有**，不许依赖 FontFile.fallbacks。
		# 试过了，不work：Theme.default_font 取到的是另一个字体实例，
		# fallbacks 在控件那儿是空的（`t.default_font.fallbacks.size()` 还是 2，
		# 但 `label.get_theme_font("font").fallbacks.size()` 就是 0）。
		# 只有 add_theme_font_override 能带过去，但那是逐控件的事，几百个控件不现实。
		# 所以策略改成：符号只用思源黑体自带的。原来那个空心小三角、重勾、斜叉、
		# 齿轮图标都换成了实心小三角、对勾、乘号、省略号（视觉差别极小）。
		# tools/make_font_subset.py 会校验「每个界面字符都有字形」，加了新符号会当场报错。
		var t := Theme.new()
		t.default_font = f
		t.default_font_size = 15
		Kit.skin(t)
		SkinCrisp.skin_scroll(t)
		theme = t
		return
	# 兜底：桌面直跑时万一字体文件丢了，退回系统字体（Web 上此路必败，但无害）
	var paths: Array = [
		"C:/Windows/Fonts/msyh.ttc",
		"C:/Windows/Fonts/msyhl.ttc",
		"C:/Windows/Fonts/simhei.ttf",
		"C:/Windows/Fonts/Deng.ttf",
	]
	for p in paths:
		if FileAccess.file_exists(p):
			var g := FontFile.new()
			if g.load_dynamic_font(p) == OK:
				var t2 := Theme.new()
				t2.default_font = g
				t2.default_font_size = 15
				Kit.skin(t2)
				# 滚动条优先用贴图；没有素材时 skin_scroll 返回 false，保留上面那套手搓细条
				SkinCrisp.skin_scroll(t2)
				theme = t2
			return


## 程序行里的参数控件换皮。
##
## 两条路：
##   有 Crisp Kit 贴图  -> 用贴图（白色输入框 + 白色步进键，控件立刻有厚度）
##   没有               -> 回退到手搓（比卡深两档的蓝槽 + 顶边暗线）
## 两条路都给控件上深色字：白底上写白字等于没写。
func _paper_input(c: Control) -> void:
	if SkinCrisp.skin_input(c):
		if c is SpinBox:
			SkinCrisp.skin_stepper(c)
			var le1: LineEdit = (c as SpinBox).get_line_edit()
			if le1 != null:
				le1.add_theme_color_override("font_color", SkinCrisp.INK)
				le1.add_theme_color_override("font_selected_color", SkinCrisp.INK)
				le1.add_theme_color_override("caret_color", SkinCrisp.INK)
		if c is OptionButton:
			c.add_theme_icon_override("arrow", Kit.glyph_chev(SkinCrisp.INK, 11, 6, 2.2))
		return

	var w := Kit.well_paper()
	for k in ["normal", "hover", "pressed", "focus"]:
		c.add_theme_stylebox_override(String(k), w)
	for k in ["font_color", "font_hover_color", "font_pressed_color",
			"font_focus_color", "font_placeholder_color"]:
		c.add_theme_color_override(k, Kit.INK_1)
	if c is OptionButton:
		c.add_theme_color_override("font_hover_color", Kit.AMBER)
		c.add_theme_icon_override("arrow", Kit.glyph_chev(Color("ffffff")))
	if c is SpinBox:
		# 上下步进键：自绘刻痕三角 + 凸起木片。引擎默认的浅灰三角落在浅纸上，
		# 之前只能靠调 modulate 压暗，压完还是一枚塑料贴纸。
		c.add_theme_icon_override("up", Kit.glyph_tri(Kit.INK_1, true, 9, 5))
		c.add_theme_icon_override("down", Kit.glyph_tri(Kit.INK_1, false, 9, 5))
		for k in ["up_icon_modulate", "down_icon_modulate"]:
			c.add_theme_color_override(k, Color(1, 1, 1))
		var c_n := Kit.chip(Color("1470b4"))
		var c_h := Kit.chip(Color("1c86cf"))
		var c_p := Kit.chip(Color("0d5387"))
		for k in ["up_background", "down_background"]:
			c.add_theme_stylebox_override(k, c_n)
			c.add_theme_stylebox_override(k + "_hovered", c_h)
			c.add_theme_stylebox_override(k + "_pressed", c_p)
			c.add_theme_stylebox_override(k + "_disabled", c_p)
		var le: LineEdit = (c as SpinBox).get_line_edit()
		if le != null:
			le.add_theme_stylebox_override("normal", w)
			le.add_theme_stylebox_override("focus", w)
			for k in ["font_color", "font_selected_color"]:
				le.add_theme_color_override(k, Kit.INK_1)
			le.add_theme_color_override("caret_color", Kit.INK_1)


## 程序区底部的渐暗层：纯数据实现（GradientTexture2D），不需要额外脚本。
## 上半截完全透明，下半截慢慢压暗 —— 空出来的桌角就有了纵深，而不是一块平色。
func _bottom_shade() -> Control:
	var g := Gradient.new()
	g.set_color(0, Color(0, 0, 0, 0.0))
	g.set_color(1, Color(0, 0, 0, 0.16))
	g.add_point(0.5, Color(0, 0, 0, 0.0))
	var tex := GradientTexture2D.new()
	tex.gradient = g
	tex.width = 4
	tex.height = 256
	tex.fill_from = Vector2(0, 0)
	tex.fill_to = Vector2(0, 1)
	var t := TextureRect.new()
	t.texture = tex
	t.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	t.stretch_mode = TextureRect.STRETCH_SCALE
	t.mouse_filter = Control.MOUSE_FILTER_IGNORE
	return t


## 浮层（设置 / 结算卡 / 说明书）的宽度。
## 这三块一直是「写死宽 + 居中」，桌面够用；竖屏 390 宽时 700 的说明书
## 和 392 的设置卡都比屏幕宽，左右各切掉一截，而且不报错、只是看不见。
func _overlay_w(base: float) -> float:
	var vw: float = get_viewport().get_visible_rect().size.x
	return minf(base, maxf(240.0, vw - 24.0))


func _panel(bg: Color, radius: int = 8, border: Color = C_LINE, pad: int = 10) -> PanelContainer:
	var p := PanelContainer.new()
	p.add_theme_stylebox_override("panel", Kit.board(bg, mini(radius, Kit.R), pad, border, 3, 8))
	return p


## 区块标题：一块钉在板子上的铭牌（深底 + 琥珀竖条 + 文字）。
## 旧版只有一根裸竖条漂在面板上 —— 那是「文档小节标题」的写法。
## 套上一层底，它才变成一件**摆在那儿的东西**，这是游戏 UI 和排版最省事的分界。
func _section(text: String) -> Control:
	var p := PanelContainer.new()
	p.add_theme_stylebox_override("panel", Kit.strip(Color(0, 0, 0, 0.20), C_ACCENT, 3, 6, 0))
	p.size_flags_horizontal = Control.SIZE_SHRINK_BEGIN
	p.add_child(_label(text, 13, C_ACCENT))
	return p


func _label(text: String, size: int = 14, color: Color = C_TEXT) -> Label:
	var l := Label.new()
	l.text = I18n.t(text)
	l.add_theme_font_size_override("font_size", size)
	l.add_theme_color_override("font_color", color)
	# 浅色字一律加深色描边 —— 这是卡通游戏最省事也最见效的一条：
	# 白字压在任意亮底（金、绿、天蓝）上都读得清，不用为每种底色单独挑字色。
	if color.get_luminance() > 0.62:
		l.add_theme_color_override("font_outline_color", Kit.INK)
		l.add_theme_constant_override("outline_size", 4 if size >= 16 else 3)
	return l


func _button(text: String, cb: Callable, bg: Color = C_PANEL2, kind: String = "") -> Button:
	var b := Button.new()
	b.text = I18n.t(text)
	b.focus_mode = Control.FOCUS_NONE
	b.add_theme_font_size_override("font_size", 14)
	# 卡通的按钮统一白字 + 深描边，不按底色的明暗换字色：
	# 参考图里金按钮、绿按钮、蓝按钮上的字，全是同一套白字加深描边。
	var fg: Color = C_TEXT
	for k in ["font_color", "font_hover_color", "font_pressed_color"]:
		b.add_theme_color_override(k, fg)
	b.add_theme_color_override("font_disabled_color", Color(fg, 0.45))
	b.add_theme_color_override("font_outline_color", Kit.INK)
	b.add_theme_constant_override("outline_size", 4)
	# 优先用素材贴图（kind 非空），没素材就回退到手搓 StyleBox
	var boxes: Dictionary = SkinCrisp.button(kind) if kind != "" else {}
	if boxes.is_empty():
		boxes = Kit.button_boxes(bg, 5)
	for k in boxes.keys():
		b.add_theme_stylebox_override(String(k), boxes[k])
	if cb.is_valid():
		b.pressed.connect(cb)
	return b


# ---------------------------------------------------------------- 横竖屏
#
# 一套代码、两套布局，运行时按「窗口宽高比」切换。
#
# 为什么不干脆把桌面那套等比缩到竖屏：竖屏不是「窄一点的横屏」。
# 桌面是三栏（编辑区 + 右栏指令面板），竖屏一窄就只剩一栏宽度，而高度翻倍——
# 元素该**换行**（指令面板从右栏搬到下方），不是该**缩小**。
#
# 两套设计基准：
#   横 1280×800（老布局，一个字没改动）
#   竖  390×844（手机 CSS 像素量级：这样桌面那套「44 行高 / 50 按钮 / 14 字号」
#                换算成物理尺寸正好是手指和眼睛要的，不用另设一套尺寸表）
# 用 EXPAND 而不是 KEEP：手机比例千奇百怪（19.5:9、4:3 平板），
# KEEP 会留黑边，而 Playables / itch 都明确要求「不许有黑边」。
const BASE_WIDE := Vector2i(1280, 800)
const BASE_TALL := Vector2i(390, 844)
const TALL_RATIO := 0.95          # 宽高比低于它算竖屏；4:3 平板(1.33)仍走横屏
var _tall: bool = false
## 专注编写（只在竖屏有意义）：把舞台整块收起来，高度全给编辑器。
## 舞台 244 占竖屏的 29%，而程序最长 36 行 —— 玩家改一段复杂逻辑时，
## 「一屏能看几行」比「羊现在走没走到」重要得多。这是可逆的视图状态，不是功能开关。
var _focus: bool = false
## 画面方向：auto 跟着窗口走，portrait / landscape 强制。
## 为什么要它：手机浏览器有的不跟着转（页面被嵌在壳里、或系统锁了方向），
## 玩家拧了手机却什么都没发生。给一个显式的开关，比让他猜「是不是不支持」好。
var _orient_mode: String = "auto"
var _orient_lock: bool = false
var _orient_btns: Dictionary = {}
var _orient_note: Label = null
var _map_title_token: int = 0
var panel_stage: Control = null
var btn_focus: Button = null
var lbl_focus_goal: Label = null
var _reflow_lock: bool = false    # 换基准尺寸会再触发一次 size_changed，防递归


func _is_tall_screen() -> bool:
	var sz: Vector2i = DisplayServer.window_get_size()
	if sz.x <= 0 or sz.y <= 0:
		var vr: Vector2 = get_viewport().get_visible_rect().size
		return vr.x / maxf(1.0, vr.y) < TALL_RATIO
	return float(sz.x) / maxf(1.0, float(sz.y)) < TALL_RATIO


## 该用竖版吗。强制档优先，auto 才看窗口形状。
## 这个窗口够不够大，大到「强制换一套布局」不会把它拉得没法看。
## 手机竖着选横版（390×844）时，强制横版会被展开成 1300×2800 —— 那不是预览，是事故；
## 桌面窗口（1280×800）强制竖版只是把内容横向摊开一点，能用，而且正是「预览手机版」想要的。
## 手机/平板：屏幕方向是**系统管的**，我们只能请求，不能假装它转了。
func _is_mobile() -> bool:
	return OS.has_feature("android") or OS.has_feature("ios")


func _can_force_layout() -> bool:
	var sz: Vector2i = DisplayServer.window_get_size()
	if sz.x <= 0 or sz.y <= 0:
		var vr: Vector2 = get_viewport().get_visible_rect().size
		return minf(vr.x, vr.y) >= 480.0
	return mini(sz.x, sz.y) >= 480


func _want_tall() -> bool:
	if _orient_mode == "auto":
		return _is_tall_screen()
	# 手机上布局**只跟着窗口走**：竖着拿就是竖版，横着拿就是横版。
	# 这里不强制 —— 方向是让人去转设备的，不是让我们把 1280×800 塞进 390×844。
	if _is_mobile():
		return _is_tall_screen()
	# 小屏只信窗口：转不转是浏览器的权限，我们不能假装它转了。
	if not _can_force_layout():
		return _is_tall_screen()
	return _orient_mode == "portrait"


func _apply_base_size() -> void:
	_tall = _want_tall()
	var base: Vector2i = BASE_TALL if _tall else BASE_WIDE
	var w := get_window()
	_reflow_lock = true
	if w.content_scale_aspect != Window.CONTENT_SCALE_ASPECT_EXPAND:
		w.content_scale_aspect = Window.CONTENT_SCALE_ASPECT_EXPAND
	if w.content_scale_size != base:
		w.content_scale_size = base
	_reflow_lock = false


## 用户把窗口拖成另一个形状了。只在「横 ↔ 竖」真的翻转时才重建——
## 尺寸每变一点就重建整屏，拖动窗口时界面会在抖。
func _on_window_resized() -> void:
	if _reflow_lock:
		return
	if _orient_lock:
		return
	if _want_tall() == _tall:
		return
	_apply_base_size()
	if box_rows == null:
		return
	_relocalize()             # 拆了按新布局重建，和换语言走同一条路


# ---------------------------------------------------------------- UI

func _build_ui() -> void:
	# 背景不再是纯色块：夜色渐变 + 四周压暗，让木牌像真的摆在桌面上
	queue_redraw()

	var pad: int = 8 if _tall else 14
	var margin := MarginContainer.new()
	margin.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	margin.add_theme_constant_override("margin_left", pad)
	margin.add_theme_constant_override("margin_right", pad)
	margin.add_theme_constant_override("margin_top", pad if _tall else 12)
	margin.add_theme_constant_override("margin_bottom", pad if _tall else 12)
	add_child(margin)

	var root := VBoxContainer.new()
	root.add_theme_constant_override("separation", 8 if _tall else 10)
	margin.add_child(root)
	root_box = root

	if _tall:
		# 竖屏：抬头 → 舞台 → 编辑器 → 指令面板 → 操作台
		# 舞台搬到编辑器**上面**：竖屏视线是自上而下的，先看见羊在干什么，
		# 再低头看代码——这和桌面「三个东西并排、眼睛左右扫」是两种读法。
		_build_header_tall(root)
		# 244 是算出来的，不是拍的：任务牌 3 行 = 99，羊头顶 fy-76，草皮 60，
		# 相加 235，再留 9 的缝。舞台再矮就一定会出现「牌子压羊头」。
		# 「一屏想看更多行」不再是压这块地方的理由 —— 那是标题行那颗「专注」的活。
		# 常驻布局不替玩家做这个决定：日常玩的时候，看羊和看代码一样重要。
		_build_stage(root, 244.0)
		_build_body_tall(root)
		_build_controlbar_tall(root)
		# 重建（换语言 / 转屏）之后要把专注态贴回去，否则舞台又冒出来
		_apply_focus()
	else:
		_build_header(root)
		_build_body(root)
		_build_stage(root)
		_build_controlbar(root)


# ---------------------------------------------------------------- 设置浮层

## 目前只有一项（音量），但它必须是**能改的**而不是写死的：
## 这游戏的音效是每步一声、一秒最多十几声，音量大一点就变成机器噪音 ——
## 别人在安静的房间或深夜玩，第一件想做的事就是把它调小。
func _build_settings() -> void:
	# 用普通 Control 而不是 CanvasLayer。理由是实测出来的：
	# 挂在 CanvasLayer 上的这一层，在 Web 导出里**一个按钮都点不动**
	# （本地窗口里正常，浏览器里全套鼠标事件都进不来，而同一份代码的
	# 地图浮层是普通 Control，点得动）。与其去猜 CanvasLayer 的输入排队，
	# 不如用已经证明能工作的那条路 —— 它挂在最后，天然就在最上层，
	# 还顺带自动继承 theme（不用再手工 root.theme = theme）。
	set_layer = Control.new()
	set_layer.name = "SettingsLayer"
	set_layer.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	set_layer.mouse_filter = Control.MOUSE_FILTER_STOP
	set_layer.visible = false
	add_child(set_layer)

	var root := Control.new()
	root.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	root.mouse_filter = Control.MOUSE_FILTER_STOP
	set_layer.add_child(root)

	# 点背景就关：设置是个「顺手改一下」的地方，不该逼玩家去找关闭按钮
	var dim := ColorRect.new()
	dim.color = Color(0.02, 0.09, 0.17, 0.55)
	dim.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	dim.gui_input.connect(func(e: InputEvent) -> void:
		if e is InputEventMouseButton and e.pressed:
			_hide_settings())
	root.add_child(dim)

	var center := CenterContainer.new()
	center.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	center.mouse_filter = Control.MOUSE_FILTER_IGNORE
	root.add_child(center)

	var card := PanelContainer.new()
	var sb: StyleBoxFlat = Kit.board(Kit.WOOD, 12, 4, Kit.EDGE, 3, 14)
	sb.content_margin_left = 26
	sb.content_margin_right = 26
	sb.content_margin_top = 18
	sb.content_margin_bottom = 18
	card.add_theme_stylebox_override("panel", sb)
	# 392 是按「繁中最长的那句说明要一行放得下」反推的：繁中比简中长约 8%，
	# 按简中量出来的 300 会让繁体那句只剩两个字掉到第二行（截图里见过）。
	card.custom_minimum_size = Vector2(_overlay_w(392.0), 0)
	center.add_child(card)

	var v := VBoxContainer.new()
	v.add_theme_constant_override("separation", 12)
	card.add_child(v)

	var title := _label("设置", 20, Kit.AMBER)
	title.add_theme_color_override("font_outline_color", Kit.INK)
	title.add_theme_constant_override("outline_size", 5)
	v.add_child(title)

	var row := HBoxContainer.new()
	row.add_theme_constant_override("separation", 10)
	v.add_child(row)
	var tl := _label("音量", 14, Kit.TEXT)
	tl.custom_minimum_size.x = 62
	tl.size_flags_vertical = Control.SIZE_SHRINK_CENTER
	row.add_child(tl)
	sld_vol = HSlider.new()
	sld_vol.min_value = 0
	sld_vol.max_value = 100
	sld_vol.step = 5
	sld_vol.value = 80
	sld_vol.custom_minimum_size = Vector2(180, 22)
	sld_vol.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	sld_vol.size_flags_vertical = Control.SIZE_SHRINK_CENTER
	sld_vol.mouse_default_cursor_shape = Control.CURSOR_POINTING_HAND
	# 滑轨用凹槽（well）+ 已走过的一段用金色填充：默认的白轨白点在深蓝面板上
	# 读起来像一枚「进度条控件」，不像能拖的东西。凹槽 + 填色才是游戏里的滑块。
	sld_vol.add_theme_stylebox_override("slider", Kit.well(Color("062c4b"), 5))
	sld_vol.add_theme_stylebox_override("grabber_area", Kit.well(Kit.AMBER, 5))
	sld_vol.add_theme_stylebox_override("grabber_area_highlight", Kit.well(Kit.AMBER, 5))
	sld_vol.value_changed.connect(_on_volume_changed)
	row.add_child(sld_vol)
	lbl_vol = _label("80%", 13, Kit.MUTED)
	lbl_vol.custom_minimum_size.x = 42
	lbl_vol.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT
	lbl_vol.size_flags_vertical = Control.SIZE_SHRINK_CENTER
	row.add_child(lbl_vol)

	# 画面方向：三档并排。手机浏览器有的不跟着转，得给玩家一个显式开关。
	var orow := HBoxContainer.new()
	orow.add_theme_constant_override("separation", 10)
	v.add_child(orow)
	var ol := _label("画面", 14, Kit.TEXT)
	ol.custom_minimum_size.x = 62
	ol.size_flags_vertical = Control.SIZE_SHRINK_CENTER
	orow.add_child(ol)
	var obox := HBoxContainer.new()
	obox.add_theme_constant_override("separation", 6)
	obox.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	orow.add_child(obox)
	var modes := ["auto", "portrait", "landscape"]
	var names := ["自动", "竖版", "横版"]
	for i in modes.size():
		var m: String = modes[i]
		var b := _button(I18n.t(names[i]), _set_orient.bind(m), Kit.WOOD_3, "secondary")
		b.custom_minimum_size = Vector2(0, 30)
		b.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		b.add_theme_font_size_override("font_size", 12)
		obox.add_child(b)
		_orient_btns[m] = b

	var onote := _label("选「横版」后手机会转成横屏并占满屏幕；看不惯可以切回来。", 10, Kit.MUTED)
	onote.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	_orient_note = onote
	v.add_child(onote)

	# 顺手解释一句「为什么没有音频文件」——不然没人会注意到音效是合成的
	var note := _label("音效全部由代码现场合成，没有音频文件，也没有背景音乐。", 11, Kit.MUTED)
	note.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	note.custom_minimum_size.x = 340
	v.add_child(note)

	var done := _button("完成", _hide_settings, Kit.WOOD_2, "secondary")
	done.custom_minimum_size = Vector2(0, 34)
	v.add_child(done)


## 换方向。走的是「改基准尺寸 + 整屏重建」这条路，和转屏 / 换语言同一条。
## 浮层会被 _relocalize 一起拆掉，所以记下它原来开着，重建完再撑起来 ——
## 不然玩家点一下「横版」，设定卡自己消失了，会以为点错了。
func _set_orient(mode: String) -> void:
	if mode == _orient_mode:
		return
	_orient_mode = mode
	_save_orient(mode)
	_sync_orient_buttons()
	_request_screen_orient(mode)
	if _is_mobile() or (OS.has_feature("web") and not _can_force_layout()):
		# 小屏（手机）：只请求转屏。等它转 —— 成功了窗口自己会变，界面跟着重排；
		# 没成功就直说，让玩家自己动手，这比给他一张拉长的界面诚实得多。
		await get_tree().create_timer(0.9).timeout
		if _orient_note != null and mode != "auto":
			var want_tall: bool = (mode == "portrait")
			if _is_tall_screen() != want_tall:
				_orient_note.text = I18n.t("这台设备不让页面自己转向，请手动把手机转过来。")
			else:
				_orient_note.text = I18n.t("选「横版」后手机会转成横屏并占满屏幕；看不惯可以切回来。")
		return
	# 大窗口 / 桌面：按钮就是「换个布局看看」，直接重建。
	var was_open: bool = set_layer != null and set_layer.visible
	_orient_lock = true
	_apply_base_size()
	await get_tree().process_frame
	_orient_lock = false
	if box_rows == null:
		return
	_relocalize()
	if was_open:
		_toggle_settings()


## 三档里当前那一档染成琥珀色。只换颜色不换形状 —— 和全局的「选中就换描边/字色」一致。
func _sync_orient_buttons() -> void:
	for k in _orient_btns.keys():
		var b: Button = _orient_btns[k]
		if b == null or not is_instance_valid(b):
			continue
		var on: bool = (String(k) == _orient_mode)
		var col: Color = C_ACCENT if on else C_MUTED
		# 四个状态一起改：只改 font_color 的话，手指还停在按钮上时用的是
		# font_hover_color —— 高度看起来「没反应」（第一版就是这样）。
		for st in ["font_color", "font_hover_color", "font_pressed_color", "font_focus_color"]:
			b.add_theme_color_override(st, col)


## 手机上让浏览器真的转过去。全屏 + 锁方向只在有的浏览器里可用
## （iOS Safari 两个都不支持），所以**全部 try 包住**：失败就当没发生，
## 布局那一步照旧执行 —— 至少把手机横过来时画面是对的。
func _request_screen_orient(mode: String) -> void:
	# 原生端：系统真的会把屏幕转过去（manifest 里已经是 fullSensor，允许竖横）。
	# 这比网页那套可靠得多 —— 网页要靠 requestFullscreen + orientation.lock，
	# iOS 两个都不支持，Android Chrome 也不一定给。
	if _is_mobile():
		var o: int = DisplayServer.SCREEN_SENSOR
		if mode == "portrait":
			o = DisplayServer.SCREEN_PORTRAIT
		elif mode == "landscape":
			o = DisplayServer.SCREEN_LANDSCAPE
		DisplayServer.screen_set_orientation(o)
		return
	if not OS.has_feature("web"):
		return
	var js: String
	if mode == "auto":
		js = "try{if(document.fullscreenElement&&document.exitFullscreen)document.exitFullscreen();}catch(e){}try{if(screen.orientation&&screen.orientation.unlock)screen.orientation.unlock();}catch(e){}"
	else:
		var target: String = "landscape" if mode == "landscape" else "portrait"
		js = ("try{var el=document.documentElement;"
			+ "var go=function(){try{if(screen.orientation&&screen.orientation.lock)screen.orientation.lock('" + target + "');}catch(e){}};"
			+ "if(!document.fullscreenElement&&el.requestFullscreen){el.requestFullscreen().then(go).catch(go);}else{go();}}catch(e){}")
	if JavaScriptBridge != null:
		JavaScriptBridge.eval(js, true)


func _toggle_settings() -> void:
	if set_layer == null:
		return
	if set_layer.visible:
		_hide_settings()
		return
	sld_vol.set_value_no_signal(_read_audio() * 100.0)
	_update_vol_label()
	_sync_orient_buttons()
	set_layer.visible = true


func _hide_settings() -> void:
	if set_layer != null:
		set_layer.visible = false


func _update_vol_label() -> void:
	if lbl_vol != null:
		lbl_vol.text = "%d%%" % int(round(sld_vol.value))


func _on_volume_changed(v: float) -> void:
	_update_vol_label()
	if sfx != null:
		sfx.set_master_volume(v / 100.0)
		# 拉的时候就给一声，让玩家直接听到「现在多大」—— 凭数字判断音量是做不到的
		if int(v) % 20 == 0:
			sfx.play("out", 4.0)
	_save_audio(v / 100.0)


## 音频设置和语言设置共用同一个 settings.cfg，各占一个 section。
## 写之前先 load —— i18n.save_locale 也是这么做的，两边都改文件才不会互相冲掉。
func _read_audio() -> float:
	var cf := ConfigFile.new()
	if cf.load(I18n.settings_path) != OK:
		return AUDIO_VOL
	return clampf(float(cf.get_value("audio", "volume", AUDIO_VOL)), 0.0, 1.0)


## 专注编写是「视图偏好」，不是关卡进度 —— 所以进 settings.cfg 而不是 progress.json。
## 删档重来不该把「我习惯怎么看代码」一起清掉。
## 共用同一个文件，所以写前必须 load：直接 save 会把 audio / language 两节冲掉。
## 画面方向也进 settings.cfg 的 [view]：它是「我习惯怎么看」，不是关卡进度。
func _read_orient() -> String:
	var cf := ConfigFile.new()
	if cf.load(I18n.settings_path) != OK:
		return "auto"
	var v: String = str(cf.get_value("view", "orient", "auto"))
	return v if v in ["auto", "portrait", "landscape"] else "auto"


func _save_orient(v: String) -> void:
	var cf := ConfigFile.new()
	cf.load(I18n.settings_path)
	cf.set_value("view", "orient", v)
	cf.save(I18n.settings_path)


func _read_focus() -> bool:
	var cf := ConfigFile.new()
	if cf.load(I18n.settings_path) != OK:
		return false
	return bool(cf.get_value("view", "focus", false))


func _save_focus(v: bool) -> void:
	var cf := ConfigFile.new()
	cf.load(I18n.settings_path)
	cf.set_value("view", "focus", v)
	cf.save(I18n.settings_path)


func _save_audio(v: float) -> void:
	var cf := ConfigFile.new()
	cf.load(I18n.settings_path)
	cf.set_value("audio", "volume", clampf(v, 0.0, 1.0))
	cf.save(I18n.settings_path)


# ---------------------------------------------------------------- 通关结算卡

## 为什么通关必须有一张卡，而不是只把底部按钮点亮：
## 通关是整局唯一一次「有结果」的时刻，而原来的做法只是把「下一关」按钮显示出来、
## 把状态文字改成「● 任务完成」—— 玩家可能正在看自己写的程序，根本没注意到。
## 一个事件如果没有**占据画面**，在玩家眼里就等于没发生。
func _build_win_card() -> void:
	# 普通 Control，不是 CanvasLayer —— 和设置浮层同一个理由（见 _build_settings）：
	# CanvasLayer 上的按钮在 Web 导出里收不到鼠标/触摸，本地窗口却一切正常。
	# 这一层是结算卡，卡上的「下一关」点不动 = 玩家卡在过关那一刻，比界面难看严重得多。
	# 换成 Control 之后顺带自动继承 theme（不用再手工挂，也不会满屏方框）。
	win_layer = Control.new()
	win_layer.name = "WinLayer"
	win_layer.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	win_layer.mouse_filter = Control.MOUSE_FILTER_STOP
	win_layer.visible = false
	add_child(win_layer)

	var root := Control.new()
	root.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	root.mouse_filter = Control.MOUSE_FILTER_STOP     # 挡住卡片背后的点击，避免误触编辑器
	win_layer.add_child(root)

	var dim := ColorRect.new()
	dim.color = Color(0.02, 0.09, 0.17, 0.0)
	dim.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	dim.mouse_filter = Control.MOUSE_FILTER_IGNORE
	root.add_child(dim)

	var center := CenterContainer.new()
	center.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	center.mouse_filter = Control.MOUSE_FILTER_IGNORE
	root.add_child(center)

	win_card = PanelContainer.new()
	# 金边 + 大投影：这是全屏唯一的「奖励卡」，必须一眼看出它不是普通面板
	var sb: StyleBoxFlat = Kit.board(Color("0f4d80"), 14, 5, Kit.AMBER, 3, 16)
	sb.content_margin_left = 30
	sb.content_margin_right = 30
	sb.content_margin_top = 18
	sb.content_margin_bottom = 18
	win_card.add_theme_stylebox_override("panel", sb)
	win_card.custom_minimum_size = Vector2(_overlay_w(340.0), 0)
	center.add_child(win_card)

	var v := VBoxContainer.new()
	v.add_theme_constant_override("separation", 10)
	win_card.add_child(v)

	win_title = _label("数完啦！", 26, Kit.AMBER)
	win_title.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	win_title.add_theme_color_override("font_outline_color", Kit.INK)
	win_title.add_theme_constant_override("outline_size", 6)
	v.add_child(win_title)

	win_sub = _label("", 12, Kit.INK_2)
	win_sub.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	v.add_child(win_sub)

	# 三颗星单独一行，逐颗弹出 —— 星星是「这次到底多好」的全部信息，
	# 一次性全亮就变成了装饰，一颗一颗亮才是一次宣布。
	var srow := HBoxContainer.new()
	srow.alignment = BoxContainer.ALIGNMENT_CENTER
	srow.add_theme_constant_override("separation", 8)
	v.add_child(srow)
	win_stars = []
	for i in 3:
		var st := _label("★", 34, Color(Kit.INK_3, 0.35))
		win_stars.append(st)
		srow.add_child(st)

	v.add_child(_label("", 6, Color(0, 0, 0, 0)))     # 细间隔

	win_rows = VBoxContainer.new()
	win_rows.add_theme_constant_override("separation", 4)
	v.add_child(win_rows)

	win_badge = _label("", 13, Kit.AMBER)
	win_badge.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	win_badge.add_theme_color_override("font_outline_color", Kit.INK)
	win_badge.add_theme_constant_override("outline_size", 3)
	v.add_child(win_badge)

	var brow := HBoxContainer.new()
	brow.alignment = BoxContainer.ALIGNMENT_CENTER
	brow.add_theme_constant_override("separation", 10)
	v.add_child(brow)

	var b_next := _button("下一关  →", _win_next, Kit.GREEN, "primary")
	b_next.custom_minimum_size = Vector2(138, 40)
	b_next.add_theme_font_size_override("font_size", 16)
	brow.add_child(b_next)
	win_next_btn = b_next

	brow.add_child(_button("再玩一次", func(): _hide_win_card(); _on_reset(), Kit.WOOD_2, "secondary"))


## 「下一关」在最后一关不能什么都不做 —— 点了没反应，玩家会当成按钮坏了。
## 最后一关时文案改成「回到第 1 关」，行为也跟着改。
func _win_next() -> void:
	_hide_win_card()
	if li + 1 >= levels.size():
		load_level(0)
	else:
		load_level(li + 1)


## 一行「指标 / 本次 / 目标 / 达标否」。
## 刻意做成居中紧凑的一条，而不是三列对齐的表格 ——
## 结算卡是奖状，不是报表；左边标签右边结果那种排版会立刻把它读成数据面板。
func _win_row(label: String, now: String, goal: String, hit: bool) -> Control:
	var r := HBoxContainer.new()
	r.alignment = BoxContainer.ALIGNMENT_CENTER
	r.add_theme_constant_override("separation", 6)
	var l := _label(label, 12, Kit.INK_3)
	l.custom_minimum_size.x = 40
	r.add_child(l)
	var a := _label(now, 17, Kit.INK_1 if hit else Color(Kit.INK_1, 0.72))
	a.custom_minimum_size.x = 64
	r.add_child(a)
	r.add_child(_label("/ " + goal, 12, Kit.INK_3))
	# 达标给绿勾，没达标给灰叉：两态**都有形状**，玩家才知道「这一项存在且没拿到」。
	# 只在达标时显示勾，没达标就空着 —— 空着看起来像这行本来就没有这一栏。
	r.add_child(_label("✓" if hit else "×", 15, Kit.GREEN if hit else Color(Kit.INK_3, 0.55)))
	return r


func _show_win_card(info: Dictionary, finals: bool = false) -> void:
	if win_layer == null:
		return
	_win_token += 1
	var token: int = _win_token
	# 先让彩纸飞 0.85 秒：庆祝是「先有画面，后有文字」。
	# 卡片立刻盖上来，玩家就只看到一张表，看不到舞台上发生了什么。
	# 截图时不等（demo_mode），不然命令行要额外空转半秒才能拍到卡片。
	var delay: float = 0.0 if demo_mode else WIN_DELAY
	if delay > 0.0:
		await get_tree().create_timer(delay).timeout
		if token != _win_token or vm == null or not vm.finished:
			return

	if finals:
		# 四十关全三星：这是整局唯一一次「没有下一关」的时刻，
		# 所以卡片说的不是这一关，而是这四十夜。
		win_title.text = I18n.t("四十关 · 全三星")
		win_sub.text = I18n.t("每一关都用最少的指令、最快的周期数完 —— 这些羊认得你了。")
	else:
		win_title.text = I18n.t("数完啦！") if bool(info.get("first", false)) else I18n.t("又数完啦")
		win_sub.text = I18n.tf("第 %d 关 · %s", [int(level.get("id", 0)), I18n.level_name(level)])

	var n: int = _stars(int(level.get("id", 0)))
	for i in win_stars.size():
		var st: Label = win_stars[i]
		st.add_theme_color_override("font_color", Kit.AMBER if i < n else Color(Kit.INK_3, 0.35))
		st.add_theme_color_override("font_outline_color", Kit.INK if i < n else Color(0, 0, 0, 0))
		st.add_theme_constant_override("outline_size", 4 if i < n else 0)

	for c in win_rows.get_children():
		win_rows.remove_child(c)
		c.queue_free()
	if finals:
		# 全三星时**不能**照搬单关那两行：它会拿第 40 关的速度去比 30.75 的目标，
		# 打出一个红叉 —— 在一张「你全做完了」的卡上出现一个叉，是最伤人的那种错。
		var tot: int = levels.size() * 3
		win_rows.add_child(_win_row("星数", "%d" % _star_total(), "%d" % tot, _star_total() >= tot))
		win_rows.add_child(_win_row("关卡", "%d" % levels.size(), "%d" % levels.size(), true))
	else:
		var size_now: int = HrmVM.program_size(program)
		var speed_now: float = vm.speed()
		win_rows.add_child(_win_row("指令", str(size_now), str(target_size), size_now <= target_size))
		win_rows.add_child(_win_row("速度", "%.2f" % speed_now, "%.2f" % target_speed, speed_now <= target_speed + 0.001))

	# 徽章只挂一枚。同时刷两项就只写「新纪录」，不然三行字挤在一张卡里没人读。
	var badge: String = ""
	if finals:
		badge = ""      # 标题已经说了「四十关 · 全三星」，再挂一枚同样的徽章是废话
	elif bool(info.get("first", false)):
		badge = I18n.t("★  首次通关")
	elif bool(info.get("size_better", false)) and bool(info.get("speed_better", false)):
		badge = I18n.t("★  新纪录：指令更快")
	elif bool(info.get("size_better", false)):
		badge = I18n.t("★  指令数破纪录")
	elif bool(info.get("speed_better", false)):
		badge = I18n.t("★  速度破纪录")
	elif bool(info.get("hint", false)):
		badge = I18n.t("看过解法 · 成绩不计入手写榜")
	win_badge.text = badge
	win_badge.visible = badge != ""
	win_next_btn.text = I18n.t("回到第 1 关") if li + 1 >= levels.size() else I18n.t("下一关  →")

	win_layer.visible = true
	_hide_win_card_force_dim(0.5)
	# 入场：卡片从 86% 弹到 100%（TRANS_BACK 会冲过头再回来，这是「砸下来」的手感）
	await get_tree().process_frame
	win_card.pivot_offset = win_card.size * 0.5
	win_card.scale = Vector2(0.86, 0.86)
	win_card.modulate = Color(1, 1, 1, 0)
	var tw := create_tween()
	tw.set_parallel(true)
	tw.tween_property(win_card, "scale", Vector2.ONE, 0.36)\
		.set_trans(Tween.TRANS_BACK).set_ease(Tween.EASE_OUT)
	tw.tween_property(win_card, "modulate", Color(1, 1, 1, 1), 0.22)

	# 星星逐颗弹出：延迟 0.18 起，每颗间隔 0.14。拿到几颗就弹几颗，
	# 没拿到的保持暗色 —— 缺的那几颗必须是安静的，玩家才知道差在哪。
	for i in win_stars.size():
		var st: Label = win_stars[i]
		if i >= n:
			continue
		st.pivot_offset = st.size * 0.5
		st.scale = Vector2(0.2, 0.2)
		var t2 := create_tween()
		t2.tween_interval(0.18 + 0.14 * float(i))
		t2.tween_property(st, "scale", Vector2.ONE, 0.28)\
			.set_trans(Tween.TRANS_BACK).set_ease(Tween.EASE_OUT)


func _hide_win_card_force_dim(a: float) -> void:
	var c := win_layer.get_child(0) as Control
	if c == null or c.get_child_count() == 0:
		return
	var dim := c.get_child(0) as ColorRect
	if dim != null:
		create_tween().tween_property(dim, "color:a", a, 0.25)


func _hide_win_card() -> void:
	_win_token += 1                      # 让还没弹出来的那张作废
	if win_layer != null:
		win_layer.visible = false


func _build_header(root: VBoxContainer) -> void:
	# 顶部是「游戏抬头」，不是软件标题栏。
	# 现在它还兼一个活：**任务说明**搬到这儿了。
	# 原来任务卡占着右栏一整块（约 160 高），可右栏本来就该只放「能拖的东西」——
	# 一块只读的说明书塞在手边，等于把抽屉里塞了一张 A4。
	# 抬头这一条本来就有大半是空的（产品名 + 关号 + 星 + 翻页），任务正好住进去。
	var head := HBoxContainer.new()
	head.add_theme_constant_override("separation", 10)
	# 抬头高度钉死。任务说明搬走以后它只剩定宽的东西，但下面还挂着
	# 玩家点出来的提示 —— 那条一显形就会把抬头顶高，所以照旧钉死。
	head.custom_minimum_size.y = 48
	root.add_child(head)

	var logo := _label("SHEEP COUNTER", 18, C_ACCENT)
	logo.add_theme_color_override("font_shadow_color", Color(0, 0, 0, 0.6))
	logo.add_theme_constant_override("shadow_offset_y", 2)
	logo.size_flags_vertical = Control.SIZE_SHRINK_CENTER
	head.add_child(logo)
	var cn := _label("数羊", 12, C_MUTED)
	cn.size_flags_vertical = Control.SIZE_SHRINK_CENTER
	head.add_child(cn)

	head.add_child(_vline())

	# 关号码牌 = 一枚按钮。大号关号 + 一小行「/ 总数」，
	# 点它才展开牧场地图 —— 地图是「想去别关」时才需要的，不该常年占掉五分之一屏宽。
	btn_level = Button.new()
	btn_level.focus_mode = Control.FOCUS_NONE
	btn_level.custom_minimum_size = Vector2(62, 42)
	btn_level.size_flags_vertical = Control.SIZE_SHRINK_CENTER
	btn_level.tooltip_text = I18n.t("牧场地图：点开选关")
	var lboxes: Dictionary = Kit.button_boxes(Kit.WOOD_2, 9)
	for k in lboxes.keys():
		btn_level.add_theme_stylebox_override(String(k), lboxes[k])
	btn_level.pressed.connect(_toggle_level_map)
	head.add_child(btn_level)
	var bv := VBoxContainer.new()
	bv.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	bv.alignment = BoxContainer.ALIGNMENT_CENTER
	bv.add_theme_constant_override("separation", -6)
	bv.mouse_filter = Control.MOUSE_FILTER_IGNORE     # 按钮才是接事件的那一层
	btn_level.add_child(bv)
	lbl_hud_no = _label("01", 17, Kit.TEXT)
	lbl_hud_no.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	lbl_hud_no.mouse_filter = Control.MOUSE_FILTER_IGNORE
	bv.add_child(lbl_hud_no)
	# 小字是这枚按钮的「功能说明」，必须读得出来。
	# 原来用 9px + INK_3（给白底配的深灰）压在亮蓝上，等于没写。
	lbl_hud_total = _label("/ 20 ▼", 10, Color(Kit.TEXT, 0.82))
	lbl_hud_total.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	lbl_hud_total.mouse_filter = Control.MOUSE_FILTER_IGNORE
	bv.add_child(lbl_hud_total)

	# 星级：三枚固定的星位，拿到的亮、没拿到的暗。
	# 不用空心星（☆）是有意的 —— 同一套字形只换颜色，不换符号，缺一颗时形状完全不变，
	# 玩家扫一眼就能数出「差一颗」。
	var stars := HBoxContainer.new()
	stars.add_theme_constant_override("separation", 1)
	stars.size_flags_vertical = Control.SIZE_SHRINK_CENTER
	stars.tooltip_text = I18n.t("过关得一颗；指令数与周期各达标再各得一颗")
	star_nodes.clear()
	for _k in 3:
		var st := _label("★", 15, Color(Kit.INK_3, 0.45))
		st.size_flags_vertical = Control.SIZE_SHRINK_CENTER
		stars.add_child(st)
		star_nodes.append(st)
	head.add_child(stars)

	head.add_child(_vline())

	# 提示按钮。任务说明已经搬到舞台顶上那块木牌里了 —— 抬头现在只剩
	# 「身份 / 关卡 / 星 / 翻页」和这一个动作。抬头因此从 56 掉回 48，
	# 多出来的 8px 全给了编辑区（抬头是唯一「宽富余、高紧张」的一条，
	# 任何住进去的东西都在偷编辑区的高度）。
	var push := Control.new()
	push.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	push.mouse_filter = Control.MOUSE_FILTER_IGNORE
	head.add_child(push)

	# 提示区分三级：思路 → 具体指令 → 完整解。越往后越「不算自己想的」
	btn_hint = _button("卡住了？看提示", _on_hint, Kit.WOOD_2, "secondary")
	btn_hint.add_theme_font_size_override("font_size", 12)
	btn_hint.custom_minimum_size = Vector2(104, 30)
	btn_hint.size_flags_vertical = Control.SIZE_SHRINK_CENTER
	head.add_child(_vline())
	head.add_child(btn_hint)

	head.add_child(_orb("‹", func(): load_level(li - 1), Kit.WOOD_2, 30))
	head.add_child(_orb("›", func(): load_level(li + 1), Kit.WOOD_2, 30))

	# 语言按钮：字写的是「按了会变成的那门语言」。
	# 写当前语言的话，它看起来像一枚状态灯（玩家不会去按）；写目标语言，它才是一个动作。
	head.add_child(_vline())
	# 显示**当前**语言，不是「点了会变成什么」。
	# 原来写的是目标语言：中文界面上按钮写着 EN、英文界面上写着繁中 ——
	# 达叔看到的就是「中文版里那一块是英文、英文版里是中文」，以为是翻译错了。
	# 按钮的第一职责是说明「你现在在什么状态」，下一步会发生什么交给 tooltip。
	btn_lang = _button(I18n.locale_label(I18n.locale), _toggle_lang, Kit.WOOD_2, "secondary")
	btn_lang.add_theme_font_size_override("font_size", 12)
	btn_lang.custom_minimum_size = Vector2(46, 30)
	btn_lang.size_flags_vertical = Control.SIZE_SHRINK_CENTER
	btn_lang.mouse_default_cursor_shape = Control.CURSOR_POINTING_HAND
	btn_lang.tooltip_text = "%s → %s" % [
		I18n.locale_full_name(I18n.locale), I18n.locale_full_name(I18n.other_locale())]
	head.add_child(btn_lang)

	# 设置：一枚圆钮。抬头是全屏唯一「宽富余」的一条，但也不能随便加东西 ——
	# 所以只放一个入口，真正的设置在浮层里（浮层不进根 VBox，不占 776 的预算）。
	head.add_child(_vline())
	btn_set = _orb("⋯", _toggle_settings, Kit.WOOD_2, 30)
	btn_set.tooltip_text = I18n.t("设置：音量")
	head.add_child(btn_set)


## 抬头里的一条细竖分隔。比 spacer 廉价，比留白明确。
func _vline() -> Control:
	var l := ColorRect.new()
	l.color = Color(Kit.EDGE, 0.55)
	l.custom_minimum_size = Vector2(2, 22)
	l.size_flags_vertical = Control.SIZE_SHRINK_CENTER
	l.mouse_filter = Control.MOUSE_FILTER_IGNORE
	return l


# ---------------------------------------------------------------- 语言

## 开机定语言。优先级：命令行 > 玩家自己选过的 > 系统语言 >（稍后）IP 归属。
##
## 界面先按系统语言出来、IP 结果晚到再换，是有意的：查 IP 要走网络，
## 网慢的时候玩家已经在按第一关了。宁可先给一个「大概对」的语言，也别空着等。
## 而**玩家自己选过就是终局** —— 自动探测再准，也准不过他按的那一下。
func _boot_locale() -> void:
	var forced: String = _cli_flag("--lang=")
	if forced != "":
		I18n.set_locale(_lang_code(forced))
		return
	if not I18n.auto_detect:
		return
	# 伪造地区：核对「哪些区域默认中文」时用，不联网、也不看存档 —— 这类核对
	# 要能一条命令复现，混进玩家存档就复现不出来了。
	var country: String = _cli_flag("--country=")
	if country != "":
		I18n.set_locale(I18n.locale_for_country(country))
		return
	var saved: String = String(I18n.read_saved().get("lang", ""))
	if saved != "":
		I18n.set_locale(saved)
		return                      # 存档里只有「玩家选的」才写，所以看到它就不用探了
	I18n.set_locale(I18n.locale_for_os())
	if demo_mode or _cli_flag("--shot=") != "":
		return                      # 截图不等网络：语言由 --lang 钉死
	var geo = GeoLang.new()
	geo.name = "GeoLang"
	add_child(geo)
	geo.located.connect(_on_country_located)
	geo.probe()


## IP 归属回来了。只在「玩家没自己选过」时才会走到这儿（见 _boot_locale）。
func _on_country_located(country: String) -> void:
	if country == "":
		return                      # 三条线都不通：保持系统语言，不打扰玩家
	# 探测是异步的（四个源轮流试，最坏 12 秒）。玩家完全可能在这之前就手选了语言 ——
	# 这时候「IP 说是中文」再把他改回中文，等于他按的那一下白按了。
	# _boot_locale 只在启动那一刻查过存档，这里必须再查一次。
	if bool(I18n.read_saved().get("manual", false)):
		return
	var want: String = I18n.locale_for_country(country)
	if want == I18n.locale:
		return                      # 猜对了就什么也别动 —— 重建一次屏幕是有代价的
	_apply_locale(want, false)


func _toggle_lang() -> void:
	_apply_locale(I18n.other_locale(), true)


func _apply_locale(l: String, manual: bool) -> void:
	if not I18n.set_locale(l):
		return
	if manual:
		I18n.save_locale(l, true)   # 只记玩家选的，自动探测不落盘
	_relocalize()


## 换语言 = 整屏重建。
##
## 为什么不「逐个控件回填新字」：文案散在几百个控件和十几处格式化里，
## 逐个回填一定会漏，而漏了**不报错** —— 英文界面里混一句中文，截图都看不出来。
## 重建的代价是几十毫秒，而换语言本来就是一次性的动作。
## 程序、选中行、提示阶段、进度一概不动：换的是语言，不是存档。
func _relocalize() -> void:
	if box_rows == null:
		return                      # 界面还没建起来，没什么可换
	if _drag_on:
		_clear_drag_nodes()
	_drag_on = false
	_press_on = false
	_scroll_drag = false
	_close_doc()
	_close_level_map()
	if win_layer != null:
		win_layer.visible = false
	_win_token += 1                 # 让还没弹出来的结算卡作废
	# 拆之前先把「指向旧节点」的引用清干净：留着它们，下一次刷新会往
	# 已经销毁的节点上写字 —— 不报错，只是什么都没发生。
	_hover_row = null
	_gap = null
	_gap_idx = -1
	_last_pc_shown = -1
	row_nodes.clear()
	star_nodes.clear()
	palette_nodes.clear()
	win_stars.clear()
	for c in get_children():
		if c == sfx:
			continue          # 音效层不重建：它持有 8 路 player 池和主音量，
			                  # 拆一次就等于拔了音箱 —— 切完语言全程静音（真踩过）
		remove_child(c)
		c.queue_free()
	box_rows = null
	scroll_rows = null
	box_palette = null
	scroll_pal = null
	jump_arcs = null
	row_gutter = null
	head_pad = null
	stage = null
	win_layer = null
	win_card = null
	win_title = null
	win_sub = null
	win_badge = null
	win_rows = null
	win_next_btn = null
	btn_run = null
	btn_next = null
	btn_hint = null
	btn_doc = null
	btn_set = null
	set_layer = null
	sld_vol = null
	lbl_vol = null
	_orient_btns.clear()
	_orient_note = null
	_guide_btn = null
	btn_level = null
	btn_lang = null
	lbl_level_name = null
	lbl_size = null
	lbl_speed = null
	lbl_cycles = null
	lbl_best = null
	lbl_status = null
	lbl_insert_hint = null
	lbl_op_help = null
	lbl_hud_no = null
	lbl_hud_total = null
	_build_ui()
	_build_win_card()
	_build_settings()
	_reset_run()                    # 重开一轮：vm/stage 里也存着上一门语言的字
	_refresh_static()
	_rebuild()
	_rebuild_palette()
	_refresh_hud()
	_refresh_hint_ui()
	_update_buttons()


## 从命令行取一个 `--key=值`。Godot 4 把 `--` 之后的参数放在 user_args 里，
## 两处都要扫 —— 只扫一处会静默拿不到（截图参数踩过这个坑）。
func _cli_flag(prefix: String) -> String:
	var argv: Array = []
	argv.append_array(OS.get_cmdline_args())
	argv.append_array(OS.get_cmdline_user_args())
	for a in argv:
		var s: String = String(a)
		if s.begins_with(prefix):
			return s.substr(prefix.length())
	return ""


## 命令行上的语言别名。写 `--lang=tw` 和 `--lang=zh_Hant` 都对，
## 因为截图脚本里的人不会记得内部代号。
static func _lang_code(v: String) -> String:
	match v.to_lower():
		"en", "english":
			return "en"
		"hant", "tw", "hk", "zh_hant", "zh-tw", "zh-hk":
			return "zh_Hant"
		_:
			return "zh_Hans"


## 圆钮：只有字形，没有文字。直径 d 决定圆角半径，否则永远不是正圆。
func _orb(sym: String, cb: Callable, bg: Color, d: int = 30) -> Button:
	var b := Button.new()
	b.text = sym
	b.focus_mode = Control.FOCUS_NONE
	b.custom_minimum_size = Vector2(d, d)
	b.size_flags_vertical = Control.SIZE_SHRINK_CENTER
	b.add_theme_font_size_override("font_size", int(d * 0.62))
	for k in ["font_color", "font_hover_color", "font_pressed_color"]:
		b.add_theme_color_override(k, Kit.TEXT)
	b.add_theme_color_override("font_outline_color", Kit.INK)
	b.add_theme_constant_override("outline_size", 3)
	var boxes: Dictionary = Kit.orb(bg, d)
	for k in boxes.keys():
		b.add_theme_stylebox_override(String(k), boxes[k])
	if cb.is_valid():
		b.pressed.connect(cb)
	return b


## 抬头刷新：关号 / 总数 / 三星。load_level 与通关记录变化后都要调。
func _refresh_hud() -> void:
	if lbl_hud_no == null:
		return
	lbl_hud_no.text = "%02d" % int(level.get("id", 0))
	# 小字带一枚箭头：它是这个按钮唯一的功能说明 ——
	# 没有箭头，玩家会以为「17 / 20」是一行只读的进度。
	lbl_hud_total.text = "/ %d %s" % [levels.size(), "▲" if map_pop != null else "▼"]
	var n: int = _stars(int(level.get("id", 0)))
	for i in star_nodes.size():
		var st: Label = star_nodes[i]
		var on: bool = i < n
		st.add_theme_color_override("font_color",
			Kit.AMBER if on else Color(Kit.INK_3, 0.45))
		# 拿到的星给深描边，暗星不给 —— 描边会让暗星也有「形状」，就数不出缺几颗了
		if on:
			st.add_theme_color_override("font_outline_color", Kit.INK)
			st.add_theme_constant_override("outline_size", 3)
		else:
			st.add_theme_constant_override("outline_size", 0)


## 三星：过关一颗；指令数 ≤ 参考解、周期 ≤ 参考解，各再一颗。
## 和 HRM 的判法一致 —— 星不是「玩得开心」，是「还有没有更好的写法」。
##
## ⚠ 这里按「关卡下标」算，不按 id 算。
## 原来的 _stars(id) 拿成员变量 target_size/target_speed（= 当前打开的这关的目标）
## 去跟任意一关的成绩比 —— 只有当前关是对的。列表时代看不出来（只显示当前关的尾巴），
## 地图时代 20 块砖同时显示星数，它会满屏错。
func _stars_of_idx(idx: int) -> int:
	if idx < 0 or idx >= levels.size():
		return 0
	var id: int = int(levels[idx].get("id", idx + 1))
	var rec: Dictionary = progress.get(str(id), {})
	if not bool(rec.get("cleared", false)):
		return 0
	var t: Dictionary = _target_of(idx)
	var n: int = 1
	if int(rec.get("size", 9999)) <= int(t.get("size", 9999)):
		n += 1
	if float(rec.get("speed", 1.0e9)) <= float(t.get("speed", 0.0)) + 0.001:
		n += 1
	return n


func _stars(id: int) -> int:
	for i in levels.size():
		if int(levels[i].get("id", i + 1)) == id:
			return _stars_of_idx(i)
	return 0


## 某一关参考解的成绩。第一次问时现算，之后走缓存 ——
## 20 关全部跑一遍也就几十毫秒，但没有必要时每次刷新都跑。
func _target_of(idx: int) -> Dictionary:
	if level_targets.has(idx):
		return level_targets[idx]
	if idx < 0 or idx >= levels.size():
		return {"size": 9999, "speed": 1.0e9}
	var lv: Dictionary = levels[idx]
	var ref: Array = HrmVM.parse_program(lv.get("ref", []))
	var v = HrmVM.new()
	v.setup(lv, ref)
	var out := {
		"size": HrmVM.program_size(ref),
		"speed": v.speed() if v.run() else 0.0,
	}
	level_targets[idx] = out
	return out


func _build_body(root: VBoxContainer) -> void:
	var body := HBoxContainer.new()
	body.add_theme_constant_override("separation", 10)
	body.size_flags_vertical = Control.SIZE_EXPAND_FILL
	# v18 之前工作台「看着够高」是假象：它的最小高度被左栏地图（288）和右栏任务卡撑着，
	# 那块高度不是它自己挣来的。两样东西一搬走，最小高度从 410 掉到 264，
	# 而富余高度全按 stage 的 1.8 比例给了舞台 —— 编辑器只剩 4 行。
	#
	# ⚠ VBoxContainer 分配 EXPAND 孩子的规则**不是**「按 ratio 分富余」，
	# 是「按 ratio 分扣掉固定项之后的全部高度，但谁也不许低于自己的最小高度」。
	# 探针实测：1:1 时两块都是 319（= 638/2），不是 358/280。
	# 所以这里的 1.8 是一个「总量占比」，直接用屏占比反推：
	# 638 里舞台要 ~230（800 的 29%），1.8 : 1 正好给出 410 / 228。
	body.size_flags_stretch_ratio = 1.45
	root.add_child(body)

	# ---- 中：程序编辑器
	# 中间的「工作台」压暗一档，纸条才会浮起来（规则 09：用明度差区分层级，不画线）
	var center := _panel(Kit.WOOD.darkened(0.28))
	center.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	body.add_child(center)
	panel_prog = center
	# 空桌角的暗角：指令少的时候下半截是一片平色，看着像「没写完的页面」。
	# 这一层从下往上渐暗，空的地方就变成「桌面退进阴影」。（先加 = 画在纸条下面）
	center.add_child(_bottom_shade())
	var cv := VBoxContainer.new()
	cv.add_theme_constant_override("separation", 6)
	center.add_child(cv)
	lbl_level_name = _label("—", 16, C_ACCENT)
	cv.add_child(lbl_level_name)
	# 表头：故意做得很轻（10px、55% 透明）。
	# 它是「表格」的最后一点残留 —— 但完全删掉，玩家就不知道右边那列数字是木牌编号。
	# 所以留着，只是不许它和纸条抢视线：表头是给第一次看的人的解释，不是给每次看的噪音。
	var head_ink := Color(C_MUTED, 0.55)
	var colhead := HBoxContainer.new()
	colhead.add_theme_constant_override("separation", COLHEAD_SEP)
	cv.add_child(colhead)
	# 行列表为了让跳转线走，左边会动态让出一条空栏（row_gutter）；表头不跟着让，
	# 列名就会整排比数据左偏一格 —— 这是「表格」最不能忍的错位。
	# 空栏宽度是变的（几条线让多宽），所以这里也得跟着变，见 _on_lanes_changed。
	head_pad = Control.new()
	head_pad.custom_minimum_size.x = 13
	head_pad.mouse_filter = Control.MOUSE_FILTER_IGNORE
	colhead.add_child(head_pad)
	var h1 := _label("#", 10, head_ink)
	h1.custom_minimum_size.x = 26
	colhead.add_child(h1)
	var h2 := _label("标签", 10, head_ink)
	h2.custom_minimum_size.x = 26
	colhead.add_child(h2)
	var h3 := _label("指令", 10, head_ink)
	h3.custom_minimum_size.x = 96
	colhead.add_child(h3)
	# 表头直说这一列填的是什么：「木牌编号」比「参数」具体，
	# 玩家一眼就能把这一列的数字和草地上那块牌的编号对上。
	colhead.add_child(_label("木牌编号 / 标签", 10, head_ink))
	# 列表外面套一层「夹子」：里面是滚动列表 + 一层跳转线。
	# 这一层必须有，因为跳转线要盖在行卡之上又要跟着列表滚 ——
	# 直接塞进 ScrollContainer 会被它的布局当成第二个内容块，塞进 VBox 会被当一行。
	var row_wrap := Control.new()
	row_wrap.size_flags_vertical = Control.SIZE_EXPAND_FILL
	row_wrap.clip_contents = true          # 滚出去的行和线一起裁掉，别画到表头上
	cv.add_child(row_wrap)

	scroll_rows = ScrollContainer.new()
	scroll_rows.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	scroll_rows.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	# 行数少的时候，列表下面是一大片空白。按在那儿往下拖也该能滚 ——
	# 不然「这块区域不会动」的印象就还在，玩家还是得去够右边那根细条。
	scroll_rows.gui_input.connect(func(e: InputEvent) -> void:
		if e is InputEventMouseButton and e.pressed and e.button_index == MOUSE_BUTTON_LEFT:
			_begin_press("scroll", "", -1, (e as InputEventMouseButton).global_position)
	)
	row_wrap.add_child(scroll_rows)

	jump_arcs = JumpArcs.new()
	jump_arcs.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	jump_arcs.offset_right = -14.0         # 右边让开滚动条，线别压在条上
	jump_arcs.bind(scroll_rows)
	# 线有几列，行卡就让多宽 —— 「要几列」只能由跳转线自己算（列分配要看每行的 y），
	# 所以它说了算，main 只管照做。见 _on_lanes_changed。
	jump_arcs.lanes_changed.connect(_on_lanes_changed)
	row_wrap.add_child(jump_arcs)

	# 行列表左边那条空栏，专门给跳转线走。
	# 不留这一条，线只能挤进行卡内部 11px 的 padding 里 —— 画出来正好压在行号上。
	# 这也让跳转线变成了「代码块外面的括号」，而不是「卡片上的一道划痕」。
	#
	# 宽度**不是常数**：0 条跳转线时就是 0（行卡贴左，白来的宽度全给内容），
	# 每多一条车道就整体右移 12px。程序里有几个循环，界面就该让多宽 ——
	# 这跟代码缩进是同一件事，只不过缩的是行卡而不是文字。
	row_gutter = MarginContainer.new()
	row_gutter.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	row_gutter.add_theme_constant_override("margin_left", 0)
	scroll_rows.add_child(row_gutter)

	box_rows = VBoxContainer.new()
	box_rows.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	box_rows.add_theme_constant_override("separation", 4)
	row_gutter.add_child(box_rows)

	# ---- 右：函数卡片（指令面板）
	# 抬头把任务说明接走以后，这一栏只剩「能拖的东西」——
	# 一块只读的说明书天天待在鼠标旁边，玩家根本不会看，却整整占掉 160 高。
	# 原来这一栏被任务卡压下去的那 160，现在还给了指令牌本身。
	var p_pal := _panel(C_PANEL)
	p_pal.size_flags_vertical = Control.SIZE_EXPAND_FILL
	# 宽度给死，让牌子和中栏的宽度分配稳定：两列牌最舒服是 320～360。
	# 用 custom_minimum_size 而不是 size_flags_stretch_ratio，
	# 是因为后者会让「窗口一宽，牌子就长得又胖又空」。
	p_pal.custom_minimum_size = Vector2(336, 0)
	body.add_child(p_pal)
	var pv := VBoxContainer.new()
	pv.add_theme_constant_override("separation", 6)
	p_pal.add_child(pv)
	var phead := HBoxContainer.new()
	phead.add_theme_constant_override("separation", 6)
	pv.add_child(phead)
	phead.add_child(_section("指令面板"))
	var ph_sp := Control.new()
	ph_sp.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	ph_sp.mouse_filter = Control.MOUSE_FILTER_IGNORE
	phead.add_child(ph_sp)
	btn_doc = _button("说明书", _open_doc, Kit.WOOD_4, "secondary")
	btn_doc.add_theme_font_size_override("font_size", 12)
	btn_doc.custom_minimum_size = Vector2(66, 24)
	btn_doc.tooltip_text = I18n.t("把本关能用的指令牌逐个讲一遍（F1）")
	phead.add_child(btn_doc)
	lbl_insert_hint = _label("未选中行 · 指令会追加到末尾", 12, C_ACCENT)
	pv.add_child(lbl_insert_hint)
	# 指令牌必须能滚动：关卡越靠后可用指令越多，如果牌子把面板「撑高」，
	# 整页最小高度就会超过画布，最底下的控制栏（运行/单步/重置）会被挤出屏幕。
	# 这一条是 2026-10-29 达叔报「运行按钮不见了」的根因。
	scroll_pal = ScrollContainer.new()
	scroll_pal.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	scroll_pal.size_flags_vertical = Control.SIZE_EXPAND_FILL
	# 实测一排牌 ~34 高、间距 6，三排 = 114。原来写 144 是按 40 高估出来的，
	# 白占了 30px 的整屏高度 —— 那 30px 现在是舞台的。
	scroll_pal.custom_minimum_size = Vector2(0, 118)
	pv.add_child(scroll_pal)
	var grid := GridContainer.new()
	grid.columns = 2
	grid.add_theme_constant_override("h_separation", 6)
	grid.add_theme_constant_override("v_separation", 6)
	grid.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	scroll_pal.add_child(grid)
	box_palette = grid

	# 这里原来有一个 EXPAND 的空挡（pad），本意是「把解释条顶到底部」。
	# 但两个 EXPAND 是平分富余的：右栏从 260 高长到 410 以后，
	# 多出来的 150 有一半喂给了这块空气，指令牌只多拿到一排便到底了。
	# v18 起由 scroll_pal 独占富余 —— 牌子列表本来就该把整只手伸到底。
	# 解释条的高度必须固定。原来是「最小 26 + autowrap」，看起来没问题，
	# 可一旦文字换行它就长到 57 —— 鼠标扫过一排指令牌，每换一条解释，
	# 上面的牌整片上下挪一次。这种跳动跟玩家操作无关，纯粹是界面自己动，
	# 是最烦的一种。装进一个固定高、能裁切的盒子里，文字长短就只影响看得见多少。
	var help_box := Control.new()
	help_box.custom_minimum_size = Vector2(0, 58)
	help_box.size_flags_vertical = Control.SIZE_SHRINK_CENTER
	help_box.clip_contents = true
	help_box.mouse_filter = Control.MOUSE_FILTER_IGNORE
	pv.add_child(help_box)
	lbl_op_help = _label("", 12, C_MUTED)
	lbl_op_help.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	lbl_op_help.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	# 最多三行，超了给省略号 —— 直接裁掉会断在半句上（「…写进」），
	# 省略号至少告诉玩家「还有，但放不下」，而不是以为句子就这么结束了。
	lbl_op_help.max_lines_visible = 3
	lbl_op_help.text_overrun_behavior = TextServer.OVERRUN_TRIM_ELLIPSIS
	lbl_op_help.vertical_alignment = VERTICAL_ALIGNMENT_TOP
	lbl_op_help.mouse_filter = Control.MOUSE_FILTER_IGNORE
	help_box.add_child(lbl_op_help)


func _build_stage(root: Control, min_h: float = 186.0) -> void:
	var p_stage := _panel(Kit.BG_DEEP, 8, C_LINE, 2)
	panel_stage = p_stage
	# 窗口不够高时先缩舞台，别缩掉底部的控制栏（2026-10-29 那条 bug 的教训）
	p_stage.custom_minimum_size = Vector2(0, min_h)
	p_stage.size_flags_vertical = Control.SIZE_EXPAND_FILL
	# 富余高度按「工作台 1.45 : 舞台 1」分（工作台那 1.45 写在 _build_body 里）。
	# 这个比值的唯一判据是屏幕占比：舞台要一直待在 29% 上下 ——
	# 低于 25% 会被读成「带预览窗的软件」，超过 45% 又会把编辑器压成一条缝。
	# 原来那版 stage 1.8 / body 1 是给「最小高度已被左栏撑满」的旧布局调的，
	# v18 把左栏搬走后它就反过来了：舞台拿走 74%，编辑器只剩 4 行。
	p_stage.size_flags_stretch_ratio = 1.0
	root.add_child(p_stage)
	stage = Stage.new()
	stage.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	stage.size_flags_vertical = Control.SIZE_EXPAND_FILL
	p_stage.add_child(stage)


func _build_controlbar(root: VBoxContainer) -> void:
	# 底部是「操作台」：一整排动作 + 一排读数表。
	# 旧版这里是「按钮 + 一行小字」，那一行小字正是 VS Code 状态栏的写法 ——
	# SIZE 20/20 SPEED 0.00/11.33 0 周期 · 3 件 就绪，一眼就是 IDE。
	# 游戏不会把数字平铺成一句话：它给每个数字一个**格子**，让你能盯着其中一个看。
	var dock := _panel(Kit.WOOD, 8, Kit.EDGE, 6)
	root.add_child(dock)
	var ctrl := HBoxContainer.new()
	ctrl.add_theme_constant_override("separation", 8)
	dock.add_child(ctrl)
	# 一屏只有一个主操作 —— 运行用素材原色的绿按钮，其余走染色白按钮
	btn_run = _button("▶  运行", _on_run, Kit.GREEN, "primary")
	btn_run.custom_minimum_size = Vector2(120, 40)
	btn_run.add_theme_font_size_override("font_size", 16)
	ctrl.add_child(btn_run)
	var b_step := _button("单步 →", _on_step, C_PANEL2, "secondary")
	b_step.custom_minimum_size = Vector2(0, 36)
	ctrl.add_child(b_step)
	var b_reset := _button("重置", _on_reset, C_PANEL2, "secondary")
	b_reset.custom_minimum_size = Vector2(0, 36)
	ctrl.add_child(b_reset)
	var b_clear := _button("清空", func():
		program.clear()
		sel = -1
		_after_edit()
	, C_PANEL2, "secondary")
	b_clear.custom_minimum_size = Vector2(0, 36)
	b_clear.tooltip_text = I18n.t("清空整段程序（可 Ctrl+Z 撤销）")
	ctrl.add_child(b_clear)
	btn_next = _button("下一关 →", func(): load_level(li + 1), Kit.AMBER, "primary")
	btn_next.custom_minimum_size = Vector2(0, 36)
	btn_next.visible = false
	ctrl.add_child(btn_next)

	var sp := Control.new()
	sp.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	ctrl.add_child(sp)

	# 三只读数表：指令 / 速度 / 周期。
	# 用中文单字当表头是有意的 —— 「指令 20/20」玩家立刻知道在数什么，
	# 「SIZE 20/20」得先在脑子里翻译一次。翻译这一步就是「软件感」的来源。
	var g_size := _gauge("指令", 78)
	lbl_size = g_size[1]
	ctrl.add_child(g_size[0])
	var g_speed := _gauge("速度", 108)
	lbl_speed = g_speed[1]
	ctrl.add_child(g_speed[0])
	var g_cyc := _gauge("周期÷件", 74)
	lbl_cycles = g_cyc[1]
	ctrl.add_child(g_cyc[0])

	lbl_best = _label("", 11, C_MUTED)
	lbl_best.size_flags_vertical = Control.SIZE_SHRINK_CENTER
	lbl_best.tooltip_text = I18n.t("你在本关的最好成绩")
	ctrl.add_child(lbl_best)
	lbl_status = _label("", 12, C_MUTED)
	lbl_status.custom_minimum_size = Vector2(220, 0)
	lbl_status.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT
	lbl_status.size_flags_vertical = Control.SIZE_SHRINK_CENTER
	lbl_status.clip_text = true
	ctrl.add_child(lbl_status)


# ---------------------------------------------------------------- 竖屏布局
#
# 竖屏不是「横屏缩小版」，每一块都重新分过工：
#   抬头    去掉品牌字和 ‹ › 翻页（翻页交给地图；抬头一窄就放不下这些）
#   舞台    从「编辑器下面」搬到「编辑器上面」——竖屏是从上往下读的，
#           先看羊在干什么，再低头看代码；桌面是并排、眼睛左右扫，两种读法
#   编辑器  占满宽度，不再和指令面板分左右
#   指令面板 改成编辑器下方的一条（三列两行），横向不再吃宽度
#   操作台  拆成三行：主操作 / 次操作＋状态 / 三只读数表
#
# 文案一律复用桌面已有的那几句：新增文案要过四门语言的翻译表，
# 而「为了竖屏多造一句同义词」是最不划算的一笔账（见 scan_strings.py）。

func _build_header_tall(root: VBoxContainer) -> void:
	var head := HBoxContainer.new()
	head.add_theme_constant_override("separation", 8)
	head.custom_minimum_size.y = 52
	root.add_child(head)

	# 关号码牌：竖屏里它兼「打开牧场地图」的入口，比桌面更需要被看见
	btn_level = Button.new()
	btn_level.focus_mode = Control.FOCUS_NONE
	btn_level.custom_minimum_size = Vector2(64, 44)
	btn_level.size_flags_vertical = Control.SIZE_SHRINK_CENTER
	btn_level.tooltip_text = I18n.t("牧场地图：点开选关")
	var lboxes: Dictionary = Kit.button_boxes(Kit.WOOD_2, 9)
	for k in lboxes.keys():
		btn_level.add_theme_stylebox_override(String(k), lboxes[k])
	btn_level.pressed.connect(_toggle_level_map)
	head.add_child(btn_level)
	var bv := VBoxContainer.new()
	bv.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	bv.alignment = BoxContainer.ALIGNMENT_CENTER
	bv.add_theme_constant_override("separation", -6)
	bv.mouse_filter = Control.MOUSE_FILTER_IGNORE
	btn_level.add_child(bv)
	lbl_hud_no = _label("01", 17, Kit.TEXT)
	lbl_hud_no.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	lbl_hud_no.mouse_filter = Control.MOUSE_FILTER_IGNORE
	bv.add_child(lbl_hud_no)
	lbl_hud_total = _label("/ 20 ▼", 10, Color(Kit.TEXT, 0.82))
	lbl_hud_total.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	lbl_hud_total.mouse_filter = Control.MOUSE_FILTER_IGNORE
	bv.add_child(lbl_hud_total)

	var stars := HBoxContainer.new()
	stars.add_theme_constant_override("separation", 1)
	stars.size_flags_vertical = Control.SIZE_SHRINK_CENTER
	stars.tooltip_text = I18n.t("过关得一颗；指令数与周期各达标再各得一颗")
	star_nodes.clear()
	for _k in 3:
		var st := _label("★", 15, Color(Kit.INK_3, 0.45))
		st.size_flags_vertical = Control.SIZE_SHRINK_CENTER
		stars.add_child(st)
		star_nodes.append(st)
	head.add_child(stars)

	var push := Control.new()
	push.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	push.mouse_filter = Control.MOUSE_FILTER_IGNORE
	head.add_child(push)

	btn_hint = _button("卡住了？看提示", _on_hint, Kit.WOOD_2, "secondary")
	btn_hint.add_theme_font_size_override("font_size", 11)
	btn_hint.custom_minimum_size = Vector2(96, 32)
	btn_hint.size_flags_vertical = Control.SIZE_SHRINK_CENTER
	head.add_child(btn_hint)

	# 显示**当前**语言，不是「点了会变成什么」。
	# 原来写的是目标语言：中文界面上按钮写着 EN、英文界面上写着繁中 ——
	# 达叔看到的就是「中文版里那一块是英文、英文版里是中文」，以为是翻译错了。
	# 按钮的第一职责是说明「你现在在什么状态」，下一步会发生什么交给 tooltip。
	btn_lang = _button(I18n.locale_label(I18n.locale), _toggle_lang, Kit.WOOD_2, "secondary")
	btn_lang.add_theme_font_size_override("font_size", 11)
	btn_lang.custom_minimum_size = Vector2(44, 32)
	btn_lang.size_flags_vertical = Control.SIZE_SHRINK_CENTER
	btn_lang.mouse_default_cursor_shape = Control.CURSOR_POINTING_HAND
	btn_lang.tooltip_text = "%s → %s" % [
		I18n.locale_full_name(I18n.locale), I18n.locale_full_name(I18n.other_locale())]
	head.add_child(btn_lang)

	btn_set = _orb("⋯", _toggle_settings, Kit.WOOD_2, 32)
	btn_set.tooltip_text = I18n.t("设置：音量")
	head.add_child(btn_set)

	# 读数表住在抬头底下这一条。它们原来是操作台的第三行 ——
	# 占掉 40 高 + 6 间距，而操作台那块地方该留给「能按的东西」，
	# 读数只是「看的东西」：短、一直在看、不该占主视野。
	# 30 是压出来的：表头 9 + 数字 13 两行，间距 -5 才塞得进。
	var gauges := HBoxContainer.new()
	gauges.add_theme_constant_override("separation", 6)
	root.add_child(gauges)
	var g_size := _gauge("指令", 0, 30)
	lbl_size = g_size[1]
	g_size[0].size_flags_horizontal = Control.SIZE_EXPAND_FILL
	gauges.add_child(g_size[0])
	var g_speed := _gauge("速度", 0, 30)
	lbl_speed = g_speed[1]
	g_speed[0].size_flags_horizontal = Control.SIZE_EXPAND_FILL
	gauges.add_child(g_speed[0])
	var g_cyc := _gauge("周期÷件", 0, 30)
	lbl_cycles = g_cyc[1]
	g_cyc[0].size_flags_horizontal = Control.SIZE_EXPAND_FILL
	gauges.add_child(g_cyc[0])
	# 状态（● 就绪 / ▶ 运行中 / × 出错）原来贴在操作台第二行右端。
	# 它和读数一样是「读」的东西，不是「按」的东西，所以一起搬。
	lbl_status = _label("", 10, C_MUTED)
	lbl_status.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT
	lbl_status.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	lbl_status.clip_text = true
	lbl_status.custom_minimum_size.x = 76
	gauges.add_child(lbl_status)


func _build_body_tall(root: Control) -> void:
	var work := VBoxContainer.new()
	work.add_theme_constant_override("separation", 6)
	work.size_flags_vertical = Control.SIZE_EXPAND_FILL
	# 竖屏的富余高度几乎全该给编辑器：舞台的高度是「看羊」用的，
	# 而编辑器的高度直接等于「一屏能看到几行代码」。1.6 是实测出来的——
	# 再往上加，舞台就压到只剩一条，任务牌和羊都塞不进去。
	work.size_flags_stretch_ratio = 1.6
	root.add_child(work)

	# ---- 上：程序编辑器（占满宽度）
	var center := _panel(Kit.WOOD.darkened(0.28))
	center.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	center.size_flags_vertical = Control.SIZE_EXPAND_FILL
	work.add_child(center)
	panel_prog = center
	center.add_child(_bottom_shade())
	var cv := VBoxContainer.new()
	cv.add_theme_constant_override("separation", 4)
	center.add_child(cv)
	var title_row := HBoxContainer.new()
	title_row.add_theme_constant_override("separation", 6)
	cv.add_child(title_row)
	lbl_level_name = _label("—", 15, C_ACCENT)
	lbl_level_name.clip_text = true
	lbl_level_name.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	title_row.add_child(lbl_level_name)
	# 专注：把舞台收起来，编辑器吃掉那 244。放在标题行是因为它紧挨着「能看几行」
	# 这件事本身 —— 玩家觉得挤的时候，眼睛正看着这里。
	btn_focus = _button("专注", _toggle_focus, Kit.WOOD_4, "secondary")
	btn_focus.add_theme_font_size_override("font_size", 11)
	# 琥珀字 + 宽 60：它和右边的「说明书」长得一样时，没人会去点
	# （达叔连着两次没看见它，宁可让我把舞台压扁）。**能改变界面的入口，
	# 就得和「只是查一下」的入口长得不一样。** 只改颜色不改形状，不破坏按钮语言。
	btn_focus.add_theme_color_override("font_color", C_ACCENT)
	btn_focus.custom_minimum_size = Vector2(60, 24)
	btn_focus.tooltip_text = I18n.t("收起舞台，让编辑器多显示一倍的行")
	title_row.add_child(btn_focus)

	# 说明书挂在这儿：它讲的是「这些牌子分别干什么」，紧挨着代码比贴着牌子更近。
	btn_doc = _button("说明书", _open_doc, Kit.WOOD_4, "secondary")
	btn_doc.add_theme_font_size_override("font_size", 11)
	btn_doc.custom_minimum_size = Vector2(62, 24)
	btn_doc.tooltip_text = I18n.t("把本关能用的指令牌逐个讲一遍（F1）")
	title_row.add_child(btn_doc)

	# 专注态专用的一行：舞台收起来，目标牌也跟着不见了 ——
	# 而写复杂逻辑时最需要抬头就能看见「这关要做什么」。
	# 一行小字（16px）换这个信息，值。普通模式下它不占位。
	lbl_focus_goal = _label("", 12, C_ACCENT)
	lbl_focus_goal.clip_text = true
	lbl_focus_goal.text_overrun_behavior = TextServer.OVERRUN_TRIM_ELLIPSIS
	lbl_focus_goal.visible = false
	cv.add_child(lbl_focus_goal)

	var head_ink := Color(C_MUTED, 0.55)
	var colhead := HBoxContainer.new()
	colhead.add_theme_constant_override("separation", COLHEAD_SEP)
	cv.add_child(colhead)
	head_pad = Control.new()
	head_pad.custom_minimum_size.x = 11
	head_pad.mouse_filter = Control.MOUSE_FILTER_IGNORE
	colhead.add_child(head_pad)
	var h1 := _label("#", 10, head_ink)
	h1.custom_minimum_size.x = 22
	colhead.add_child(h1)
	var h2 := _label("标签", 10, head_ink)
	h2.custom_minimum_size.x = 22
	colhead.add_child(h2)
	var h3 := _label("指令", 10, head_ink)
	h3.custom_minimum_size.x = 70
	colhead.add_child(h3)
	colhead.add_child(_label("木牌编号 / 标签", 10, head_ink))

	var row_wrap := Control.new()
	row_wrap.size_flags_vertical = Control.SIZE_EXPAND_FILL
	row_wrap.clip_contents = true
	cv.add_child(row_wrap)

	scroll_rows = ScrollContainer.new()
	scroll_rows.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	scroll_rows.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	scroll_rows.gui_input.connect(func(e: InputEvent) -> void:
		if e is InputEventMouseButton and e.pressed and e.button_index == MOUSE_BUTTON_LEFT:
			_begin_press("scroll", "", -1, (e as InputEventMouseButton).global_position)
	)
	row_wrap.add_child(scroll_rows)

	jump_arcs = JumpArcs.new()
	jump_arcs.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	jump_arcs.offset_right = -10.0
	jump_arcs.bind(scroll_rows)
	jump_arcs.lanes_changed.connect(_on_lanes_changed)
	row_wrap.add_child(jump_arcs)

	row_gutter = MarginContainer.new()
	row_gutter.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	row_gutter.add_theme_constant_override("margin_left", 0)
	# 右边让出滚动条的宽：滚动条是**盖在**内容上画的，
	# 不留这一条，每行末尾那枚 × 会被它遮掉一半（竖屏第一次跑就是这样）。
	row_gutter.add_theme_constant_override("margin_right", 14)
	scroll_rows.add_child(row_gutter)

	box_rows = VBoxContainer.new()
	box_rows.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	box_rows.add_theme_constant_override("separation", 4)
	row_gutter.add_child(box_rows)

	# ---- 下：指令面板（一条，两列）
	# 竖屏里这条只留「牌子 + 一句话」，标题和说明书都搬走了 ——
	# 屏幕高度是这场比赛里最稀缺的变量：每排牌子占 44，省下的一行就多看得见一条指令。
	var p_pal := _panel(C_PANEL, 8, C_LINE, 8)
	p_pal.size_flags_vertical = Control.SIZE_SHRINK_END
	p_pal.custom_minimum_size = Vector2(0, 92)
	work.add_child(p_pal)
	var pv := VBoxContainer.new()
	pv.add_theme_constant_override("separation", 4)
	p_pal.add_child(pv)

	scroll_pal = ScrollContainer.new()
	# 一排，左右滑。竖屏的高度是这场比赛里最稀缺的东西，
	# 而「这关能用哪些指令」天然是一条横向清单 ——
	# 让它在横轴展开，比让它吃掉两排 94 高的纵向空间划算得多
	# （两排变一排，直接还给编辑器 35px）。
	scroll_pal.vertical_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	scroll_pal.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_AUTO
	scroll_pal.size_flags_vertical = Control.SIZE_SHRINK_CENTER
	# 44 的牌 + 12 的横向滚动条
	scroll_pal.custom_minimum_size = Vector2(0, 56)
	pv.add_child(scroll_pal)
	var strip := HBoxContainer.new()
	strip.add_theme_constant_override("separation", 6)
	# SHRINK_BEGIN 是关键：设成 EXPAND/FILL，HBox 的宽会被拉成滚动区那么宽，
	# 内容永远「正好装得下」，横向滚动条就再也不会出现 ——
	# 牌子再多也只是挤窄，不是滑出来。
	strip.size_flags_horizontal = Control.SIZE_SHRINK_BEGIN
	scroll_pal.add_child(strip)
	box_palette = strip

	# 说明放哪儿：它本来跟着「指令面板」这块面板走，竖屏里挂到编辑器的标题行上，
	# 反而更近 —— 玩家看一眼代码、顺手就知道去哪查指令。
	lbl_insert_hint = _label("未选中行 · 指令会追加到末尾", 11, C_ACCENT)
	lbl_insert_hint.clip_text = true
	lbl_insert_hint.text_overrun_behavior = TextServer.OVERRUN_TRIM_ELLIPSIS
	pv.add_child(lbl_insert_hint)

	# 解释条不进竖屏：手指没有 hover，它永远不会被换字，只剩一句默认的废话占 58 高。
	# 但成员变量仍要存在——_refresh_op_help_default / _show_op_help 会往上写。
	help_box_tall_placeholder()


## 切换专注编写。只改可见性，不重建界面 ——
## 重建会丢滚动位置和选中行，而玩家按这个键的瞬间正是「我正在看第 20 行」。
func _toggle_focus() -> void:
	_focus = not _focus
	_save_focus(_focus)
	_apply_focus()
	# 舞台收起来以后，编辑器会立刻重排；把当前选中行滚回来，
	# 否则玩家会以为自己刚才看的代码被删了。
	if _focus:
		_scroll_to_sel()


func _apply_focus() -> void:
	# 只在竖屏生效：横屏的舞台是常驻的，把 _focus 带过去会直接黑掉半边屏幕，
	# 而玩家在横屏根本看不到这个按钮（它在竖屏的编辑器标题行里），也关不掉。
	var on: bool = _focus and _tall
	if panel_stage != null:
		panel_stage.visible = not on
	if btn_focus != null:
		btn_focus.text = I18n.t("还原" if on else "专注")
	if lbl_focus_goal != null:
		lbl_focus_goal.visible = on
		_sync_focus_goal()
	# 车道宽度跟着模式走：不重算的话，线还按 24 宽挤在左边，
	# 而玩家刚点开「专注」，看到的却是和刚才一样挤的跳转线。
	_on_lanes_changed(0)


## 把舞台顶上那块任务牌的文字复述到编辑器标题行下。
## 不复制一份到成员变量里：目标牌是唯一真源，两处各存一份就一定会出现
## 「换了语言/换了关，一处变了另一处没变」。
func _sync_focus_goal() -> void:
	if lbl_focus_goal == null:
		return
	var g: String = stage.goal_text if stage != null else ""
	lbl_focus_goal.text = I18n.tf("目标：%s", [g]) if g != "" else ""


## 把选中行滚进视野。选中行不存在时不动。
func _scroll_to_sel() -> void:
	if scroll_rows == null or sel < 0 or sel >= row_nodes.size():
		return
	var row: Control = row_nodes[sel]
	if row == null or not is_instance_valid(row):
		return
	# 刚切完可见性，容器还没算完尺寸 —— 这一帧滚会滚到旧位置。
	await get_tree().process_frame
	if scroll_rows != null and is_instance_valid(row):
		scroll_rows.ensure_control_visible(row)


## 竖屏里没有「鼠标扫过某张牌」这回事，解释条只剩默认那句话。
## 不建出来又会在 _show_op_help 里碰到空引用，所以建一个不进树的哑节点，
## 由 _relocalize 统一回收（它挂在 panel_prog 下，会跟着一起 free）。
func help_box_tall_placeholder() -> void:
	lbl_op_help = _label("", 11, C_MUTED)
	lbl_op_help.visible = false
	panel_prog.add_child(lbl_op_help)


func _build_controlbar_tall(root: VBoxContainer) -> void:
	var dock := _panel(Kit.WOOD, 8, Kit.EDGE, 6)
	root.add_child(dock)
	# 三**列**，不是三行。手指的落点只有「左中右」三块，
	# 纵向多一行就多一次瞄准；而运行按钮在中间，是唯一有颜色的一块。
	# 原来的三行（运行+单步 / 重置+清空+状态 / 三只读数）现在只剩这一行 74 高，
	# 省下的 58 全部还给上面的编辑器。
	var cols := HBoxContainer.new()
	cols.add_theme_constant_override("separation", 8)
	dock.add_child(cols)

	# 左列：重置 / 清空。两个都会抹掉当前进度，压在远端，不容易顺手按到。
	var left := VBoxContainer.new()
	left.add_theme_constant_override("separation", 6)
	left.custom_minimum_size.x = 82
	cols.add_child(left)
	var b_reset := _button("重置", _on_reset, C_PANEL2, "secondary")
	b_reset.custom_minimum_size = Vector2(0, 34)
	left.add_child(b_reset)
	var b_clear := _button("清空", func():
		program.clear()
		sel = -1
		_after_edit()
	, C_PANEL2, "secondary")
	b_clear.custom_minimum_size = Vector2(0, 34)
	b_clear.tooltip_text = I18n.t("清空整段程序（可 Ctrl+Z 撤销）")
	left.add_child(b_clear)

	# 中列：运行。跨满两行高（34+6+34=74），主操作就该比别的大一号。
	btn_run = _button("▶  运行", _on_run, Kit.GREEN, "primary")
	btn_run.custom_minimum_size = Vector2(0, 74)
	btn_run.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	btn_run.add_theme_font_size_override("font_size", 18)
	cols.add_child(btn_run)

	# 右列：单步 / 下一关。下一关平时不出现，出现时正好补齐 74 ——
	# 所以运行按钮不会因为「通关了多一个按钮」而改高度、
	# 把上面整片布局推一遍（那种跳动比多个按钮更烦）。
	var right := VBoxContainer.new()
	right.add_theme_constant_override("separation", 6)
	right.alignment = BoxContainer.ALIGNMENT_CENTER
	right.custom_minimum_size.x = 88
	cols.add_child(right)
	var b_step := _button("单步 →", _on_step, C_PANEL2, "secondary")
	b_step.custom_minimum_size = Vector2(0, 34)
	right.add_child(b_step)
	btn_next = _button("下一关 →", func(): load_level(li + 1), Kit.AMBER, "primary")
	btn_next.custom_minimum_size = Vector2(0, 34)
	btn_next.visible = false
	right.add_child(btn_next)

	# 最好成绩：竖屏读数行被三只表和状态占满，没它的位置。
	# 但节点必须存在 —— _refresh_gauges 会往上写，空引用会直接炸。
	lbl_best = _label("", 10, C_MUTED)
	lbl_best.visible = false
	right.add_child(lbl_best)

## 一只读数表：上小字（在数什么）+ 下大字（数到几）。返回 [容器, 值标签]。
## 为什么不做成一个 Label 写「指令 20/20」：那样两个信息共用一条基线，
## 眼睛只能整块读。拆成上下两行，表头退成灰、数字顶上去，才能在余光里一眼扫到变化。
func _gauge(caption: String, w: int, h: int = 40) -> Array:
	var p := PanelContainer.new()
	p.add_theme_stylebox_override("panel", Kit.gauge())
	p.custom_minimum_size = Vector2(w, h)
	p.size_flags_vertical = Control.SIZE_SHRINK_CENTER
	p.tooltip_text = I18n.t(caption)
	var v := VBoxContainer.new()
	v.alignment = BoxContainer.ALIGNMENT_CENTER
	v.add_theme_constant_override("separation", -5)
	p.add_child(v)
	var c := _label(caption, 9, Kit.INK_3)
	c.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	v.add_child(c)
	var val := _label("—", 13, Kit.TEXT)
	val.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	v.add_child(val)
	return [p, val]


## 地图上点了一块地 —— 这只是「预选」。
## 一按就走的话，想看看第 27 关拿了几颗星的人会顺手把自己切走；
## 换关是个擦不掉的动作用（程序会存档、当前编辑区会被换掉），
## 擦不掉的动作用不该由一次误触决定。
## 注意这里不能顺手 _stash_program()：load_level 自己会存上一关的程序，
## 两处都存会把「刚切走那一关」的旧内容写回去。
## 「先过第 N 关」只在玩家点的这一下有用，2 秒后把那行字还给「通关 x/y」——
## 不能因为一次误触，让地图顶上长期挂着一句和当前状态无关的话。
func _restore_map_title_later() -> void:
	_map_title_token += 1
	var token: int = _map_title_token
	await get_tree().create_timer(2.0).timeout
	if token == _map_title_token and map_levels != null:
		_refresh_level_buttons()


func _on_map_picked(i: int) -> void:
	if map_levels == null:
		return
	if i > _unlocked_max() and i != li:
		# 锁住的砖点不动。不要沉默 —— 沉默会被读成「这块砖坏了」。
		# 说清楚是哪一关挡着，玩家才知道下一步该干什么。
		if lbl_levels_title != null:
			lbl_levels_title.text = I18n.tf("先过第 %d 关", [maxi(1, i)])
		# 把预选清掉：留着上一个预选，玩家会以为「刚点的那一关被选中了」，
		# 一按确认反而进了另一关 —— 那种「点了 A 进了 B」是最难自查的错。
		map_levels.pending = -1
		_sync_map_footer()
		if sfx != null:
			sfx.play("err")
		_restore_map_title_later()
		return
	map_levels.pending = i
	_sync_map_footer()


## 真的进去。只认地图上那个绿框的预选，不认鼠标最后停在哪。
func _confirm_map_pick() -> void:
	if map_levels == null or map_levels.pending < 0:
		return
	var i: int = map_levels.pending
	_close_level_map()
	if i == li:
		return
	load_level(i)


# ---------------------------------------------------------------- 牧场地图浮层

## 关卡地图是「关卡选择」，不是「导航栏」。
## 常驻它 = 把目录印在每一页的边上：20 块地砖吃掉五分之一屏宽，
## 而玩家真正在里面做事的九成时间，看的是中间那段程序。
## 所以收进抬头的关号徽章里 —— 点开才铺开，铺开时放大到 84px 一块。
##
## 浮层挂在本节点、不进根 VBox：根布局有 776 的硬预算，
## 常驻模块才该受那个预算约束，浮层是「事件」不是「模块」。
func _toggle_level_map() -> void:
	if map_pop != null:
		_close_level_map()
		return
	if _drag_on:
		_end_drag(false)
	map_pop = Control.new()
	map_pop.name = "LevelMapPop"
	map_pop.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	map_pop.mouse_filter = Control.MOUSE_FILTER_STOP
	# 点空白处 = 收起（关掉浮层的最低礼貌，不然它就成了「只能按 × 的广告」）
	map_pop.gui_input.connect(func(e: InputEvent) -> void:
		if e is InputEventMouseButton and e.pressed and e.button_index == MOUSE_BUTTON_LEFT:
			_close_level_map()
	)
	add_child(map_pop)

	var dim := ColorRect.new()
	dim.color = Color(0.02, 0.09, 0.17, 0.74)
	dim.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	dim.mouse_filter = Control.MOUSE_FILTER_IGNORE
	map_pop.add_child(dim)

	var cc := CenterContainer.new()
	cc.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	cc.mouse_filter = Control.MOUSE_FILTER_IGNORE
	map_pop.add_child(cc)

	# 面板底色比常驻面板亮一档：浮起来的东西要在明度上压住底下的页面
	var box := _panel(Kit.WOOD.lightened(0.06), 9, C_ACCENT, 14)
	box.mouse_filter = Control.MOUSE_FILTER_STOP
	cc.add_child(box)
	var v := VBoxContainer.new()
	v.add_theme_constant_override("separation", 8)
	box.add_child(v)

	var hd := HBoxContainer.new()
	hd.add_theme_constant_override("separation", 10)
	v.add_child(hd)
	hd.add_child(_label("牧场地图", 17, C_ACCENT))
	lbl_levels_title = _label("—", 12, C_MUTED)
	lbl_levels_title.size_flags_vertical = Control.SIZE_SHRINK_CENTER
	# 这一段长度会变（"已清 12 / 40"），放开就等于让标题行按它定宽；
	# clip 之后它退让，标题和按钮才保得住。
	lbl_levels_title.clip_text = true
	hd.add_child(lbl_levels_title)
	var hsp := Control.new()
	hsp.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	hsp.mouse_filter = Control.MOUSE_FILTER_IGNORE
	hd.add_child(hsp)
	lbl_stars_total = _label("—", 13, C_ACCENT)
	lbl_stars_total.size_flags_vertical = Control.SIZE_SHRINK_CENTER
	hd.add_child(lbl_stars_total)
	var cb := _button("收起 ×", _close_level_map, Kit.WOOD_2)
	cb.add_theme_font_size_override("font_size", 12)
	cb.custom_minimum_size = Vector2(76, 26)
	hd.add_child(cb)

	# 84 = 52 的 1.6 倍：大不是目的，让「星」和「关号」在同一块砖上互不挤才是目的。
	# 4 列 × 5 行 = 374 × 462，加标题和底下那条操作栏，正好在 1280×800 里居中留白。
	map_levels = LevelMap.new()
	map_levels.tile_max = 84.0
	# 竖屏 390 的屏上，374 的砖区 + 面板内边距 = 402，比屏幕还宽 12 ——
	# 居中的结果是左右各切掉 6px（右边那列砖看起来贴着屏幕边）。
	# 这里按可用宽度收一档：1280 时仍是 374，390 时收到 358，四列 84 的砖正好放得下。
	map_levels.custom_minimum_size = Vector2(
		minf(374.0, get_viewport().get_visible_rect().size.x - 32.0), 462)
	map_levels.picked.connect(_on_map_picked)
	v.add_child(map_levels)

	# 图例：三种框各自是什么意思，得写在界面上。
	# 只靠玩家自己发现「绿框是待确认」，那这一版就白改了。
	var legend := _label("绿框＝选中待确认 · 白框＝当前关 · ★＝这一关拿到的", 11, C_MUTED)
	legend.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	# 竖屏：这句英译 11px 有 382 宽，加面板内边距把浮层撑到 410 ——
	# 比 390 的屏还宽，居中的结果是右边那列砖贴着屏幕边（左右各切 6px）。
	# 折行比截断好：它是图例，截掉一半等于没写。
	legend.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	v.add_child(legend)

	# 翻页条：40 关分两页。40 块砖一次铺满是能做到，但那要 8 列，
	# 砖会瘦成 94 宽的「表格单元格」，地砖的「一块地」感就没了。
	# 圆钮只给翻页用 —— 圆在这套界面语言里专门表示「方向」。
	var pager := HBoxContainer.new()
	pager.add_theme_constant_override("separation", 10)
	pager.alignment = BoxContainer.ALIGNMENT_CENTER
	v.add_child(pager)
	var prev_b := _orb("‹", func(): _turn_map_page(-1), Kit.WOOD_2, 28)
	var next_b := _orb("›", func(): _turn_map_page(1), Kit.WOOD_2, 28)
	pager.add_child(prev_b)
	lbl_map_page = _label("1 / 2", 12, C_MUTED)
	lbl_map_page.custom_minimum_size = Vector2(74, 0)
	lbl_map_page.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	lbl_map_page.size_flags_vertical = Control.SIZE_SHRINK_CENTER
	pager.add_child(lbl_map_page)
	pager.add_child(next_b)

	# 确认条。点砖只改这一行按钮上的字，不会真的走人 ——
	# 换关会存盘、会把编辑区换掉，这种擦不掉的动作值得多按一下。
	btn_map_go = _button("进入第 27 关 ›", _confirm_map_pick, Kit.GREEN)
	btn_map_go.add_theme_font_size_override("font_size", 14)
	btn_map_go.custom_minimum_size = Vector2(0, 40)
	btn_map_go.mouse_default_cursor_shape = Control.CURSOR_POINTING_HAND
	v.add_child(btn_map_go)

	# 先 set_tiles 再定位页码：反过来时 tiles 还是空的，page_count() 算出来是 1，
	# 「翻到当前关那页」会被夹回第 0 页 —— 而且不报错。
	_refresh_level_buttons()
	map_levels.show_page_of(li)
	map_levels.pending = li
	_sync_map_footer()
	_refresh_hud()          # 徽章小字上的箭头要翻成实心朝上那个


## 翻页。翻完要把「第 x / y 页」和确认按钮一起重刷 ——
## 页码变了，确认按钮上那句「进入第 N 关」指的就不再是刚才那一页的砖。
func _turn_map_page(delta: int) -> void:
	if map_levels == null:
		return
	if map_levels.turn_page(delta):
		_sync_map_footer()


## 底部那条：页码 + 确认按钮的文字和可用态。
## 三个名字（第几页 / 选的是哪关 / 现在在哪关）来自同一处状态，所以只有这一个刷新入口。
func _sync_map_footer() -> void:
	if map_levels == null:
		return
	if lbl_map_page != null:
		lbl_map_page.text = "%d / %d" % [map_levels.page + 1, map_levels.page_count()]
	if btn_map_go == null:
		return
	var p: int = map_levels.pending
	if p < 0:
		btn_map_go.text = I18n.t("先点一块地")
		btn_map_go.disabled = true
		return
	btn_map_go.disabled = false
	var no: int = int(levels[p].get("id", p + 1)) if p < levels.size() else (p + 1)
	if p == li:
		btn_map_go.text = I18n.tf("第 %d 关就是这儿 · 收起", [no])
	else:
		btn_map_go.text = I18n.tf("进入第 %d 关 ›", [no])


func _close_level_map() -> void:
	if map_pop == null:
		return
	map_pop.queue_free()
	map_pop = null
	# 地图和它的统计标签都是浮层里的节点，一起置空 ——
	# _refresh_level_buttons 见 null 就跳过，不会往已释放的节点写东西。
	map_levels = null
	lbl_levels_title = null
	lbl_stars_total = null
	lbl_map_page = null
	btn_map_go = null
	_refresh_hud()


## 已解锁到哪一关（0 基索引）。第 1 关永远开，之后每一关要求**上一关已经玩过**。
##
## 「玩过」= 通关，或者写过程序。为什么把「写过程序」也算进来：
## 加这条规则之前，存档里 1-19 关都有玩家自己写的程序、但 cleared 全是空的
## （他手动调出来看的）。只认 cleared 的话，这次更新会把他一把锁回第 1 关 ——
## 加新规则把人挡在门外，是最糟的一种「修复」。
func _unlocked_max() -> int:
	var m: int = 0
	for i in range(1, levels.size()):
		var pid: String = str(int(levels[i - 1].get("id", i)))
		var played: bool = bool(progress.get(pid, {}).get("cleared", false)) \
			or saved_programs.has(pid)
		if not played:
			break
		m = i
	return clampi(m, 0, maxi(0, levels.size() - 1))


func _refresh_level_buttons() -> void:
	if map_levels == null:
		return
	var tiles: Array = []
	var n_clear: int = 0
	var n_stars: int = 0
	var unlocked: int = _unlocked_max()
	for i in levels.size():
		var id: int = int(levels[i].get("id", i + 1))
		var cleared: bool = bool(progress.get(str(id), {}).get("cleared", false))
		var s: int = _stars_of_idx(i)
		if cleared:
			n_clear += 1
		n_stars += s
		tiles.append({"id": id, "clear": cleared, "stars": s, "unlocked": i <= unlocked})
	map_levels.set_tiles(tiles, li)
	# 「12 / 20」自己读不出是什么 —— 一个没标签的分数在游戏里只可能是两种东西之一。
	# 既然旁边还有第二个分数，两个都得自报家门，否则玩家得先猜再对。
	if lbl_levels_title != null:
		lbl_levels_title.text = I18n.tf("通关 %d / %d", [n_clear, levels.size()])
	if lbl_stars_total != null:
		lbl_stars_total.text = "★ %d / %d" % [n_stars, levels.size() * 3]


func _refresh_static() -> void:
	# 关号只在抬头出现一次就够了。工作台顶上再写一遍「#17」，
	# 等于每屏告诉玩家两次「你在第几关」—— 这是导航栏的做法，不是 HUD 的做法。
	# 英文版关名本来就叫 First Sheep，后面再挂一个中文括号是废话 —— 只给一个。
	var nm: String = String(level.get("name", ""))
	lbl_level_name.text = nm if I18n.locale == "en" else "%s  ·  %s" % [nm, I18n.level_name(level)]
	# 任务说明不归抬头管了：它是舞台顶上那块木牌（17px 加粗，全屏最抢眼的一行字）。
	if stage != null:
		stage.set_task(I18n.t(String(level.get("goal", ""))),
			_ints(level.get("inbox", [])), _ints(level.get("outbox", [])))
		_sync_focus_goal()          # 换关后那行复述要跟着换


func _ints(a: Array) -> String:
	var parts: PackedStringArray = []
	for v in a:
		parts.append(str(int(v)))
	if parts.size() == 0:
		return I18n.t("（无）")
	return ", ".join(parts)


# ---------------------------------------------------------------- 提示

## 三级提示。第一级只在卡满 STUCK_SEC 之后才给，避免把「想」这一步跳过。
##
## hint_stage 是**记录**（玩家最多看过第几级，决定星数），hint_view 是**当前贴在舞台上的那一张**。
## 两者分开是因为：给过参考解之后玩家仍想回头看一眼那句思路（那往往才是他真正需要的），
## 而回看不该把「这关是参考答案过的」这件事改回去 —— 记录只增不减。
func _on_hint() -> void:
	if hint_stage >= 3:
		hint_view = 2 if hint_view == 3 else 3
		_refresh_hint_ui()
		return
	if hint_stage == 0 and stuck_time < STUCK_SEC:
		var left: int = ceili(STUCK_SEC - stuck_time)
		lbl_status.text = I18n.tf("再想 %d 秒，实在卡住再点我", [left])
		lbl_status.add_theme_color_override("font_color", C_ACCENT)
		return
	hint_stage = mini(hint_stage + 1, 3)
	hint_view = hint_stage
	if hint_stage == 3:
		_push_undo()
		program = HrmVM.parse_program(level.get("ref", []))
		sel = -1
		_after_edit()
		lbl_status.text = I18n.t("已填入参考解 · 这关记为「参考答案」")
		lbl_status.add_theme_color_override("font_color", C_MUTED)
	_refresh_hint_ui()


func _refresh_hint_ui() -> void:
	if btn_hint == null:
		return
	# 提示文字不写进任何控件：它挂在舞台任务牌的下面，当成一张「纸条」画出来。
	# 这么做的好处是它完全不参与布局 —— 玩家点出来的东西，不该把任何东西顶走。
	var txt: String = ""
	match hint_view:
		0:
			btn_hint.text = I18n.t("卡住了？看提示")
			btn_hint.disabled = false
			_hint_left = -1
		1:
			var h1: String = String(level.get("hint", ""))
			txt = I18n.t("思路：") + (I18n.t(h1) if h1 != "" else I18n.t("（这关没有写提示）"))
			btn_hint.text = I18n.t("还是不懂 · 再具体点")
			btn_hint.disabled = false
		2:
			txt = I18n.tf("思路：%s\n关键做法：%s", [
				I18n.t(String(level.get("hint", ""))), I18n.t(String(level.get("hint2", "")))
			])
			btn_hint.text = I18n.t("看参考解说明 · 回看" if hint_stage >= 3 else "直接看参考解")
			btn_hint.disabled = false
		3:
			txt = I18n.t("已填入参考解。看每行右边那行小字——那就是它在干什么；鼠标停在任意一行上，下面的说明条会讲清这一句。")
			btn_hint.text = I18n.t("回看思路" if hint_stage >= 3 else "已给出参考解")
			# 给过参考解之后按钮不再禁用：它是「回看」，不是「再做一次」
			btn_hint.disabled = hint_stage < 3
	if stage != null:
		stage.set_hint(txt)
	btn_hint.modulate = Color(1, 1, 1, 1) if hint_stage > 0 else btn_hint.modulate


## 按钮在冷却期半透明，并把剩余秒数放进 tooltip——告诉玩家「有提示，但现在先自己想」
func _update_hint_hint() -> void:
	if btn_hint == null or hint_stage > 0:
		return
	var left: int = ceili(maxf(0.0, STUCK_SEC - stuck_time))
	if left == _hint_left:
		return
	_hint_left = left
	if left > 0:
		btn_hint.tooltip_text = I18n.tf("先自己想 %d 秒，实在卡住再点", [left])
		btn_hint.modulate = Color(1, 1, 1, 0.5)
	else:
		btn_hint.tooltip_text = I18n.t("现在可以看了")
		btn_hint.modulate = Color(1, 1, 1, 1)


func _rebuild_palette() -> void:
	for c in box_palette.get_children():
		box_palette.remove_child(c)
		c.queue_free()
	palette_nodes.clear()
	_guide_btn = null
	var allowed: Array = level.get("allowed", [])
	for op in HrmVM.ALL_OPS:
		if not allowed.has(op):
			continue
		var card: Control = _make_palette_card(String(op))
		box_palette.add_child(card)
		palette_nodes[String(op)] = card
		if _guide_btn == null:
			_guide_btn = card
	_refresh_op_help_default()
	_refresh_guide()


## 新手引导：只有「一关都没动过手」的人才看得到 —— 判据是「一关都没写过程序」，
## 所以不需要额外的存档字段，也不会在玩家删光程序时又跳出来烦他（那时他已经会了）。
func _is_new_hand() -> bool:
	return li == 0 and program.is_empty() and saved_programs.is_empty()


## 给指令面板的第一块牌做一次呼吸。**只点一块**：把整片面板都点亮等于没点亮。
## 呼吸本身靠 modulate（只在动起来时才看得见），所以额外钉一圈琥珀描边：
## 「哪一块在呼吸」这件事必须在一张**静止的截图**上也看得出来，否则等于没做
## —— 第一版只有 modulate，截图里两块牌长得一样，验收时根本指不出在哪。
func _refresh_guide() -> void:
	if _guide_tween != null and _guide_tween.is_valid():
		_guide_tween.kill()
	_guide_tween = null
	var on: bool = _is_new_hand()
	_mark_guide(on)
	if not on or _guide_btn == null:
		return
	_update_insert_hint()
	_guide_tween = create_tween().set_loops()
	_guide_tween.tween_property(_guide_btn, "modulate", Color(1.35, 1.3, 1.1, 1.0), 0.62)\
		.set_trans(Tween.TRANS_SINE)
	_guide_tween.tween_property(_guide_btn, "modulate", Color(1, 1, 1, 1), 0.62)\
		.set_trans(Tween.TRANS_SINE)


## 把「这块是被指着的那块」标出来 / 收回去。改描边不改形状 —— 呼吸是暂时的，
## 描边是常驻的，两者叠在一起才知道该看哪。
func _mark_guide(on: bool) -> void:
	if _guide_btn == null:
		return
	_guide_btn.modulate = Color(1, 1, 1, 1)
	var sb: StyleBoxFlat = _guide_btn.get_meta("sb", null)
	if sb == null:
		return
	sb.border_color = Kit.AMBER if on else Kit.EDGE_HI
	sb.set_border_width_all(2 if on else 1)


## 一张「指令牌」：上面是英文指令名，下面一行白话。
## 之前在面板上只有 JUMPZ 这三个字母，玩家根本看不出「它就是比较」。
func _make_palette_card(op: String) -> Control:
	var card := PanelContainer.new()
	card.custom_minimum_size = Vector2(145, 44)
	# 指令牌 = 一块小木片：暖褐底、浅木边、底部 3px 厚影（有厚度才不会像网页按钮）
	var sb := StyleBoxFlat.new()
	sb.bg_color = Kit.WOOD_3
	sb.set_corner_radius_all(5)
	sb.border_color = Kit.EDGE_HI
	sb.set_border_width_all(1)
	sb.content_margin_left = 8
	sb.content_margin_right = 8
	sb.content_margin_top = 3
	sb.content_margin_bottom = 3
	sb.shadow_color = Color(0, 0, 0, 0.5)
	sb.shadow_size = 3
	sb.shadow_offset = Vector2(0, 3)
	sb.anti_aliasing = true
	card.add_theme_stylebox_override("panel", sb)
	# 存一份引用：新手引导要改它的描边（见 _mark_guide）
	card.set_meta("sb", sb)
	card.mouse_filter = Control.MOUSE_FILTER_STOP
	card.mouse_default_cursor_shape = Control.CURSOR_POINTING_HAND
	card.tooltip_text = I18n.tf("%s · %s\n点一下追加到末尾 / 按住拖到任意行之间", [op, HrmVM.op_help(op)])

	var v := VBoxContainer.new()
	v.add_theme_constant_override("separation", 0)
	v.mouse_filter = Control.MOUSE_FILTER_IGNORE
	card.add_child(v)
	# 指令名用暖黄：这是「能拿起来的东西」，整块面板里只有它该发亮
	var top := _label(op, 14, C_ACCENT)
	top.mouse_filter = Control.MOUSE_FILTER_IGNORE
	v.add_child(top)
	var bot := _label(HrmVM.op_short(op), 11, Color(C_MUTED, 0.92))
	bot.mouse_filter = Control.MOUSE_FILTER_IGNORE
	bot.autowrap_mode = TextServer.AUTOWRAP_OFF
	bot.clip_text = true
	v.add_child(bot)

	card.gui_input.connect(func(e: InputEvent) -> void:
		if e is InputEventMouseButton and e.pressed and e.button_index == MOUSE_BUTTON_LEFT:
			_begin_press("new", op, -1, e.global_position)
	)
	card.mouse_entered.connect(func() -> void:
		sb.bg_color = Kit.WOOD_4
		sb.border_color = C_ACCENT
		sb.shadow_size = 6             # 悬停时「抬起来一点」，鼠标才有反馈
		_show_op_help(op)
	)
	card.mouse_exited.connect(func() -> void:
		sb.bg_color = Kit.WOOD_3
		sb.border_color = Kit.EDGE_HI
		sb.shadow_size = 3
		_refresh_op_help_default()
	)
	return card


## 指令面板底部的解释条：默认给一句「这游戏没有比较牌」的定心丸，
## 鼠标停在指令牌或程序行上就换成那条指令的完整说明。
func _show_op_help(op: String) -> void:
	if lbl_op_help == null:
		return
	lbl_op_help.text = "%s —— %s" % [op, HrmVM.op_help(op)]
	lbl_op_help.add_theme_color_override("font_color", C_TEXT)


func _refresh_op_help_default() -> void:
	if lbl_op_help == null:
		return
	var allowed: Array = level.get("allowed", [])
	if allowed.has("JUMPZ") or allowed.has("JUMPN"):
		lbl_op_help.text = I18n.t("没有单独的「比较」牌：JUMPZ / JUMPN 就是比较 —— 看一眼手上的数，成立就跳。")
	else:
		lbl_op_help.text = I18n.t("鼠标停在指令牌或程序行上，这里会解释它做什么。")
	lbl_op_help.add_theme_color_override("font_color", C_MUTED)


# ---------------------------------------------------------------- 指令说明书弹窗

## 面板上只有几个字母，玩家不知道 JUMPZ 是「比较」。说明书把这关**能用的每一张牌**
## 按用途分组讲一遍，比 tooltip 强在：不用先猜该把鼠标放到哪儿。
func _open_doc() -> void:
	if doc_layer != null:
		_close_doc()
		return
	if _drag_on:
		_end_drag(false)
	doc_entries.clear()
	doc_layer = Control.new()
	doc_layer.name = "DocLayer"
	doc_layer.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	doc_layer.mouse_filter = Control.MOUSE_FILTER_STOP
	doc_layer.gui_input.connect(func(e: InputEvent) -> void:
		if e is InputEventMouseButton and e.pressed and e.button_index == MOUSE_BUTTON_LEFT:
			_close_doc()
	)
	add_child(doc_layer)

	var dim := ColorRect.new()
	dim.color = Color(0.03, 0.02, 0.02, 0.76)
	dim.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	dim.mouse_filter = Control.MOUSE_FILTER_IGNORE
	doc_layer.add_child(dim)

	var cc := CenterContainer.new()
	cc.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	cc.mouse_filter = Control.MOUSE_FILTER_IGNORE
	doc_layer.add_child(cc)

	var box := _panel(Kit.WOOD.darkened(0.12), 8, C_ACCENT, 16)
	box.custom_minimum_size = Vector2(_overlay_w(700.0), 0)
	box.mouse_filter = Control.MOUSE_FILTER_STOP
	cc.add_child(box)
	var v := VBoxContainer.new()
	v.add_theme_constant_override("separation", 10)
	box.add_child(v)

	var head := HBoxContainer.new()
	head.add_theme_constant_override("separation", 10)
	v.add_child(head)
	head.add_child(_label("指令说明书", 17, C_ACCENT))
	# 关号这一条必须能缩：它是 head 里唯一长度不定的东西，
	# 放开它 → 右上角那枚「关闭」被挤出屏幕（竖屏第一版，关都关不掉）。
	var lv_lbl := _label(I18n.tf("第 %d 关 · %s", [int(level.get("id", 0)), I18n.level_name(level)]),
		13, C_MUTED)
	lv_lbl.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	lv_lbl.clip_text = true
	lv_lbl.text_overrun_behavior = TextServer.OVERRUN_TRIM_ELLIPSIS
	head.add_child(lv_lbl)
	var close_btn := _button("关闭 ×", _close_doc, Kit.WOOD_2)
	close_btn.custom_minimum_size = Vector2(64 if _tall else 78, 26)
	close_btn.add_theme_font_size_override("font_size", 12)
	head.add_child(close_btn)

	var allowed: Array = level.get("allowed", [])
	if allowed.has("JUMPZ") or allowed.has("JUMPN"):
		var tip := _label("这游戏没有单独的「比较」牌 —— 比较长在 JUMPZ / JUMPN 身上：它们看一眼手上的数，条件成立就跳走。", 13, C_MUTED)
		tip.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
		v.add_child(tip)

	var sc := ScrollContainer.new()
	sc.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	sc.custom_minimum_size = Vector2(0, minf(460.0, get_viewport().get_visible_rect().size.y - 250.0))
	v.add_child(sc)
	var list := VBoxContainer.new()
	list.add_theme_constant_override("separation", 8)
	list.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	sc.add_child(list)

	for g in OP_GROUPS:
		var ops: Array = []
		for op in g.get("ops", []):
			if allowed.has(op):
				ops.append(String(op))
		if ops.is_empty():
			continue
		var sec := _label(String(g.get("title", "")), 12, C_ACCENT)
		sec.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
		list.add_child(sec)
		for op in ops:
			list.add_child(_make_doc_entry(String(op)))
			doc_entries.append(String(op))

	var foot := _label("Esc / 点空白处 关闭 · 面板上悬停任意一行，底部也会给出同一句解释", 11, C_MUTED)
	v.add_child(foot)


## 说明书里的一张牌：指令名 + 白话 + 完整解释；条件跳转再挂一个「比较」徽章
## 用纸条而不是深色卡片：整块弹窗是「在桌上摊开的说明」，纸才是内容该有的样子
func _make_doc_entry(op: String) -> Control:
	var card := PanelContainer.new()
	var sb: StyleBoxFlat = Kit.strip(Kit.SLIP, Color("9a7326"), 3, 5, 3)
	sb.content_margin_left = 12
	sb.content_margin_right = 12
	sb.content_margin_top = 8
	sb.content_margin_bottom = 8
	card.add_theme_stylebox_override("panel", sb)

	var v := VBoxContainer.new()
	v.add_theme_constant_override("separation", 3)
	card.add_child(v)

	var head := HBoxContainer.new()
	head.add_theme_constant_override("separation", 8)
	v.add_child(head)
	head.add_child(_label(op, 15, Kit.INK_1))
	head.add_child(_label(HrmVM.op_short(op), 12, Kit.INK_3))
	if op == "JUMPZ" or op == "JUMPN":
		head.add_child(_badge("这就是比较", Color("c39a4e")))

	var d := _label(HrmVM.op_help(op), 13, Kit.INK_2)
	d.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	d.mouse_filter = Control.MOUSE_FILTER_IGNORE
	v.add_child(d)
	return card


## 小徽章：深底浅字在深色 UI 里看不清，所以反过来用亮底深字
func _badge(text: String, bg: Color) -> Control:
	var p := PanelContainer.new()
	var sb := StyleBoxFlat.new()
	sb.bg_color = bg
	sb.set_corner_radius_all(3)
	sb.content_margin_left = 6
	sb.content_margin_right = 6
	sb.content_margin_top = 1
	sb.content_margin_bottom = 1
	p.add_theme_stylebox_override("panel", sb)
	p.size_flags_vertical = Control.SIZE_SHRINK_CENTER
	p.add_child(_label(text, 11, Color("191c22")))
	return p


func _close_doc() -> void:
	if doc_layer != null and is_instance_valid(doc_layer):
		doc_layer.queue_free()
	doc_layer = null



func _rebuild() -> void:
	if box_rows == null:
		return
	# 重建会连带清掉拖拽用的空隙节点，引用一起清掉，避免悬空
	_gap = null
	_gap_idx = -1
	# 旧的行马上要被销毁，hover 记录也必须一起清 —— 留着它，
	# 下一次移动会去摸一个已经 queue_free 的节点。
	_hover_row = null
	for c in box_rows.get_children():
		box_rows.remove_child(c)
		c.queue_free()
	row_nodes.clear()
	if program.is_empty():
		box_rows.add_child(_make_placeholder())
		_update_insert_hint()
		_sync_jump_arcs()
		return
	for i in program.size():
		var row = _make_row(i)
		box_rows.add_child(row)
		row_nodes.append(row)
	_refresh_row_highlight()
	_update_insert_hint()
	# 重建以后鼠标可能正停在某一行的空档上：这时 × 还没被判成「该显示」，
	# 会先消失，等鼠标再动一下才冒出来 —— 改一次参数，列表就闪一下。
	# 重建完标记一下，下一帧按真实鼠标位置重判一次（本帧行还没排版，量不到矩形）。
	_hover_dirty = true
	_sync_jump_arcs()


## 把「行节点 + 程序 + 当前选中」交给跳转线层。
## 它自己不算任何东西：哪行跳到哪行由 op/arg 决定，标签落点由人写。
func _sync_jump_arcs() -> void:
	if jump_arcs == null:
		return
	jump_arcs.set_data(row_nodes, program, sel)


## 跳转线的车道数变了：行卡整体让位，表头跟着让，两者不能各走各的。
##
## 为什么不是「固定留 14px」：第 1 关那种一条跳转都没有的程序，
## 也该为不存在的线留白吗？让位应该跟「这段代码有几个块」走 ——
## 这就是缩进的本意：**结构越深，右边的空间越少**，玩家不用读代码也能看出层次。
##
## 上限在 JumpArcs.MAX_LANE 那边（5 列 / 60px），再宽下去行卡里的参数控件就该挤了。
func _on_lanes_changed(n: int) -> void:
	if row_gutter == null or jump_arcs == null:
		return
	var g: int = int(round(jump_arcs.gutter_width()))
	# 竖屏把这条空栏压到 24 以内：5 条车道 = 60px，在 374 的屏宽上是 16% 的净宽，
	# 而这一栏只走几根 2.5px 的线。宁可让线在极端关卡里挤一点，也不能让它吃行卡。
	# 专注态放宽到 64：那时玩家要的正是「看清结构」，而舞台收起来后
	# 左边多出来的那块地方没别的东西要用。
	if _tall:
		g = mini(g, 64 if (_focus and _tall) else 24)
	row_gutter.add_theme_constant_override("margin_left", g)
	# 表头：「#」要压在行号左沿上。行卡内文字在「空栏 + 13」，
	# 而表头这一格后面还跟着一个 separation 的间隔 —— 所以垫片要先扣掉它，
	# 否则整排表头会一直偏右一个格距（8px，眼睛看得出来，但很难指出是哪儿）。
	if head_pad != null:
		head_pad.custom_minimum_size.x = maxf(0.0, float(g + ROW_TEXT_INSET - COLHEAD_SEP))


## 明确告诉玩家"下一笔会插到哪"，这是原来最含糊的地方
func _update_insert_hint() -> void:
	if lbl_insert_hint == null:
		return
	# 第一次进来：这行字是全屏唯一在说「接下来该干什么」的地方，
	# 所以先说这一步，别急着讲「插到第几行」—— 那是第二步的事。
	if _is_new_hand():
		# 牌子在桌面靠右、在竖屏靠**下**，方向词必须跟着布局走。
		# 写死「右边」时，竖屏玩家会往屏幕右边找 —— 那里什么都没有。
		lbl_insert_hint.text = I18n.t(
			"点一下下面任意一块指令牌，它就会变成一行代码" if _tall
			else "点一下右边任意一块指令牌，它就会变成一行代码")
		lbl_insert_hint.add_theme_color_override("font_color", C_ACCENT)
		return
	if sel < 0 or program.is_empty():
		lbl_insert_hint.text = I18n.t("未选中行 · 指令会追加到末尾")
		lbl_insert_hint.add_theme_color_override("font_color", C_MUTED)
	else:
		lbl_insert_hint.text = I18n.tf("已选第 %d 行 · 新指令插到第 %d 行", [sel + 1, sel + 2])
		lbl_insert_hint.add_theme_color_override("font_color", C_ACCENT)


## 空程序的占位行：拖拽时它会被空隙挤下去，第一条指令直接落在它上面
func _make_placeholder() -> Control:
	var row = ProgRow.new()
	row.index = 0
	row.custom_minimum_size = Vector2(0, 46)
	var sb := StyleBoxFlat.new()
	sb.bg_color = C_PANEL2
	sb.set_corner_radius_all(6)
	sb.set_border_width_all(1)
	sb.border_color = C_LINE
	sb.content_margin_left = 10
	sb.content_margin_right = 10
	row.add_theme_stylebox_override("panel", sb)
	row.sb = sb
	# 方向词按布局分支：桌面牌子在右栏，竖屏牌子在下面。
	# 一直写「右边」的话，竖屏玩家会往屏幕右边找 —— 那里什么都没有。
	var ph_txt: String = ("程序是空的 —— 把下面的指令牌拖到这里，或点一下追加到末尾"
		if _tall else "程序是空的 —— 把右边的指令牌拖到这里，或点一下追加到末尾")
	var ph_lbl := _label(ph_txt, 13, C_MUTED)
	if _tall:
		# 这句 13px 有 440 宽。空程序时它一个人把列表撑到 440，
		# 于是每行右边那枚删除键都留在屏幕外（竖屏第一版全屏看不见 ×）。
		# 靠折行解决：行高 46 放两行正好。
		ph_lbl.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
		ph_lbl.max_lines_visible = 2
	row.add_child(ph_lbl)
	return row


## 每帧刷新时只改行配色，不重建节点（重建会打断拖拽和输入焦点）
func _refresh_row_highlight() -> void:
	if vm == null or row_nodes.is_empty():
		return
	for i in mini(row_nodes.size(), program.size()):
		var r = row_nodes[i] if i < row_nodes.size() else null
		if r == null:
			break
		var is_err: bool = vm.failed and vm.fail_pc == i
		var is_pc: bool = not vm.failed and vm.last_pc == i
		r.set_state(i == sel, is_pc, is_err, _trail_level(i))
		_second_channel(r, i, is_pc, is_err)

	# 程序变长以后 PC 会跑出可视区，跟着滚，否则看不到它在干什么
	var focus_row: int = vm.fail_pc if vm.failed else vm.last_pc
	if focus_row != _last_pc_shown:
		_last_pc_shown = focus_row
		if scroll_rows != null and focus_row >= 0 and focus_row < row_nodes.size():
			scroll_rows.ensure_control_visible(row_nodes[focus_row])
	# 选中的行相关的跳转线加亮 —— 「我这个 JUMP 跳到哪」在点中它的时候最该看清楚
	_sync_jump_arcs()


## 色盲第二通道：把行首那个「01」换成 ▶（正在跑）/ ×（这行出错）。
##
## 为什么必须加：红绿型色盲看「执行绿」和「出错红」是两个相近的黄褐，
## 而这两个状态恰恰是运行时**唯一要紧**的信息。四态里出错还带羊绊倒和一行字兜底，
## 正在执行那一行却只有颜色 —— 所以颜色之外得再给一个**形状**。
##
## 用行号位置而不是另开一栏：加一栏要把表头、缩进、跳转线车道全部跟着挪，
## 为了一枚 12px 的箭头不值当；而行号在运行时是最不重要的字，正好让位。
func _second_channel(r: Control, i: int, is_pc: bool, is_err: bool) -> void:
	var lbl: Label = r.get("num_lbl")
	if lbl == null:
		return
	var want: String = "%02d" % (i + 1)
	var col: Color = Kit.INK_3
	if is_err:
		want = "×"
		col = Kit.RED
	elif is_pc:
		want = "▶"
		col = Kit.GREEN
	if lbl.text != want:
		lbl.text = want
	if lbl.get_theme_color("font_color") != col:
		lbl.add_theme_color_override("font_color", col)


## 标签小贴纸（JUMP 的落点名）。
## 旧版空标签是一枚透明度 55% 的「·」，看着像标点符号，没有一个人知道那能点。
## 现在做成两个明确的态：
##   空  → 深色凹槽 + 琥珀色「+」＝ 这里还空着，可以往里写
##   填了 → 该标签**自己的颜色**当贴纸底 + 深蓝字 ＝ 已经写了
## 再配手型光标和悬浮说明，鼠标扫过一次就懂。
##
## 每种标签一个颜色，是因为 a/b/c/d 四个单字母在余光里长得一模一样 ——
## 不染色的话，玩家判断「这两行是不是同一个块」只能逐字读。
## 颜色取自 Kit.label_tint，和跳转线共用一份：黄色线一定连着黄色牌子。
func _label_chip(lab: String, cb: Callable) -> Button:
	var on: bool = lab != ""
	var b := Button.new()
	b.text = lab if on else "+"
	b.focus_mode = Control.FOCUS_NONE
	b.custom_minimum_size = Vector2(26, 24)
	b.mouse_default_cursor_shape = Control.CURSOR_POINTING_HAND
	b.tooltip_text = I18n.t("标签：点一下循环切换  无 → a → b → c → d\nJUMP a / JUMP b 就是跳到标签为 a / b 的那一行")
	b.add_theme_font_size_override("font_size", 14 if on else 16)
	if on:
		var tint: Color = Kit.label_tint(lab)
		for k in ["normal", "hover", "pressed"]:
			var bg: Color = tint
			if k == "hover":
				bg = tint.lightened(0.20)
			elif k == "pressed":
				bg = tint.darkened(0.14)
			b.add_theme_stylebox_override(String(k), Kit.card(bg, Kit.EDGE, 2, 6, 0, 0, 0))
		# 四个色都是亮色，统一压深蓝字 —— 不为每种底色单独挑字色，
		# 否则以后加第五个颜色就得重新挑一次，而挑错是看不见的（字照样显示，只是糊）。
		for k in ["font_color", "font_hover_color", "font_pressed_color"]:
			b.add_theme_color_override(String(k), Kit.INK)
	else:
		# 凹槽：比行卡更暗的底 + 一条细浅边，读作「挖出来的一格」
		b.add_theme_stylebox_override("normal",
			Kit.card(Color(0.01, 0.13, 0.24, 0.55), Color(1, 1, 1, 0.32), 1, 6, 0, 0, 0))
		# 悬停：边框转琥珀、底提亮 —— 「鼠标一上来它就活了」
		b.add_theme_stylebox_override("hover",
			Kit.card(Color(0.05, 0.28, 0.44, 0.88), Kit.AMBER, 2, 6, 0, 0, 0))
		b.add_theme_stylebox_override("pressed",
			Kit.card(Color(0.02, 0.18, 0.31, 0.80), Kit.AMBER_DEEP, 2, 6, 0, 0, 0))
		for k in ["font_color", "font_hover_color", "font_pressed_color"]:
			b.add_theme_color_override(String(k), Kit.AMBER)
	if cb.is_valid():
		b.pressed.connect(cb)
	return b


func _make_row(i: int) -> PanelContainer:
	var ins: Dictionary = program[i]
	var row := ProgRow.new()
	row.main = self
	row.index = i
	row.custom_minimum_size = Vector2(0, ROW_H)
	# 纸条：没有外框，只有左侧一条 3px 色带（选中黄 / 执行绿 / 出错红）+ 一层薄影
	# 行卡：圆角 + 整圈描边（状态由 prog_row.set_state 换描边颜色）
	# 竖屏左边距 18 而不是 11：左边要留出一条握把（三道横线），
	# 11 的时候那三道线紧贴着行号「01」，看起来像数字前面的横杠 —— 放大截图才看出来。
	var sb: StyleBoxFlat = Kit.card(Kit.SLIP, Kit.EDGE, 2, 9, 18 if _tall else 11, 9, 3)
	row.add_theme_stylebox_override("panel", sb)
	row.sb = sb

	var h := HBoxContainer.new()
	# 窄屏把每条缝和每格都收一档：桌面行宽 476，塞进 374 的屏宽必须让出 100，
	# 否则 ScrollContainer 会把宽高算成 476 —— 右边那枚删除键整截留在屏幕外（竖屏第一版）。
	h.add_theme_constant_override("separation", 6 if _tall else 8)
	h.mouse_filter = Control.MOUSE_FILTER_PASS
	row.add_child(h)

	# 纸上写字：行号最弱、指令名最重、白话居中 —— 一列扫下去先看到「做什么」
	var li_lbl := _label("%02d" % (i + 1), 13, Kit.INK_3)
	li_lbl.custom_minimum_size.x = 26
	h.add_child(li_lbl)
	row.num_lbl = li_lbl

	var op: String = String(ins.get("op", ""))
	var lab: String = String(ins.get("label", ""))
	h.add_child(_label_chip(lab, func(): _cycle_label(i)))

	var olbl := _label(op, 14, Kit.INK_1 if op != "COMMENT" else Kit.INK_3)
	olbl.custom_minimum_size.x = 80 if _tall else 96
	h.add_child(olbl)

	if HrmVM.MEM_OPS.has(op):
		var sp := SpinBox.new()
		sp.min_value = 0
		sp.max_value = maxi(0, int(level.get("mem_size", 8)) - 1)
		var arg: Variant = ins.get("arg", null)
		sp.value = int(arg) if arg != null else 0
		# 22 高而不是 24：行卡内高只有 ~22，24 会顶出卡片上下各 1px，
		# 白输入框在深蓝行上多出两个白角，非常显眼。
		sp.custom_minimum_size = Vector2(74 if _tall else 100, 22)
		_paper_input(sp)
		if _tall:
			# SpinBox 的最小宽是「LineEdit 最小宽 + 上下两枚小箭头」，
			# 给 SpinBox 设 custom_minimum_size 只是设下限的**下限**，
			# 里面那根输入框默认还要一百多 —— 不钻进去改它，整行就被它一个人撑破。
			sp.get_line_edit().custom_minimum_size.x = 26
			sp.get_line_edit().alignment = HORIZONTAL_ALIGNMENT_CENTER
		sp.value_changed.connect(func(v: float): _set_arg(i, int(v)))
		h.add_child(sp)
	elif HrmVM.JUMP_OPS.has(op):
		var ob := OptionButton.new()
		var names: Array = ["a", "b", "c", "d"]
		for n in names:
			ob.add_item(String(n))
		# 用 str() 不用 String()：老存档 / 手改的 levels.json 里 arg 可能是数字，
		# String(int) 会直接抛「Invalid call String constructor」把整行炸掉。
		var cur: String = "a" if ins.get("arg") == null else str(ins.get("arg"))
		ob.selected = maxi(0, names.find(cur))
		ob.custom_minimum_size = Vector2(64 if _tall else 86, 0)
		_paper_input(ob)
		ob.item_selected.connect(func(k: int): _set_arg(i, names[k]))
		h.add_child(ob)
	# 无需参数的指令不再画「—」占位：那个空占位是最典型的表单味

	# 白话紧跟在参数后面，像汇编里的行尾注释；不再右对齐成一列「说明字段」
	# 注意不能开 clip_text——一开，最小宽度就变 0，会被 spacer 挤成看不见的一条线
	# 竖屏：带参数的行不画白话。参数本身就是这一行的信息，
	# 而「一句话解释」在 374 宽里和数字框抢的是同一块地盘 —— 抢不过就不抢。
	# ⚠ 只是**不画这一格**，不能 return：后面还有行尾空档和那枚 ×，
	# 少了它们这一行既删不掉、也拖不动（而且不报错）。
	if not (_tall and (HrmVM.MEM_OPS.has(op) or HrmVM.JUMP_OPS.has(op))):
		var sem := _label("   " + HrmVM.op_tag(op), 11, Kit.INK_2)
		sem.mouse_filter = Control.MOUSE_FILTER_IGNORE
		if _tall:
			# 窄屏反过来：这里必须钉死一个最小宽再开裁切，否则它按整句白话撑宽行卡。
			sem.custom_minimum_size.x = 46
			sem.clip_text = true
			sem.text_overrun_behavior = TextServer.OVERRUN_TRIM_ELLIPSIS
		h.add_child(sem)

	# 行尾的空档：原来的注释写着「空档区域也要能按住行来拖」——
	# 现在它多了一个活儿：按住这里往下拖 = 滚列表。
	# 一个行卡上只有这里既不属于「读」也不属于「改」，用它做滚动最不抢戏：
	# 玩家想挪这一行，按在内容上拖；想把列表往下看，按在右边空档拖。
	var spacer := Control.new()
	spacer.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	spacer.mouse_filter = Control.MOUSE_FILTER_STOP
	spacer.mouse_default_cursor_shape = Control.CURSOR_DRAG
	spacer.tooltip_text = I18n.t("按住拖动 = 滚动")
	spacer.set_meta("scroll_pad", true)      # 给探针用的记号
	spacer.gui_input.connect(func(e: InputEvent) -> void:
		if e is InputEventMouseButton and e.pressed and e.button_index == MOUSE_BUTTON_LEFT:
			_begin_press("scroll", "", -1, (e as InputEventMouseButton).global_position)
	)
	h.add_child(spacer)

	var del := _button("×", func(): _delete_row(i), Kit.WOOD_2)
	# 桌面靠悬停浮出（一列 × 常驻会立刻变成「表单」），
	# 但手指没有悬停 —— 竖屏里它必须**一直可见**，否则整行删不掉，
	# 而且不是「不好用」，是「根本没有这个功能」。
	del.custom_minimum_size = Vector2(30, 30) if _tall else Vector2(24, 24)
	del.add_theme_font_size_override("font_size", 15 if _tall else 13)
	del.modulate = Color(1, 1, 1, 1.0) if _tall else Color(1, 1, 1, 0.0)
	h.add_child(del)
	# 把 × 和指令名挂在行节点上，给 _update_row_hover() 用 ——
	# 它只拿得到「行」，需要知道这一行的 × 是哪个、讲什么。
	row.set_meta("del", del)
	row.set_meta("op", op)

	# 悬停才浮出删除键（游戏 UI 常见做法：动作跟着注意力走）。
	#
	# 这里的数据流是：**鼠标位置说了算**，不是行的 mouse_entered/exited。
	# 实测过那条路走不通：鼠标从行内移到行内的子控件（× 自己、数字框、跳转下拉）上时，
	# Godot 会给整行发一次 mouse_exited（因为子控件接管了鼠标），而之后从子控件
	# 直接移出行外时**不会再发第二次** —— 状态已经停在「exit」上了。
	# 于是：靠 entered/exited 控制显隐，结果必然是
	#   旧版：移到 × 上就消失（exit 触发），再移开也不回来；
	#   加延迟判定：移到 × 上倒是保住了，但移出行外也永远不收起。
	# 两头都不对。所以改成 _input 里统一按鼠标坐标算「现在压在哪一行」，
	# 见 _update_row_hover()。这里的 entered 只负责「立刻亮起来」，不等下一帧。
	row.mouse_entered.connect(func() -> void:
		_show_op_help(op)
		del.modulate = Color(1, 1, 1, 1)
	)
	return row


## 按鼠标坐标刷新「哪一行被压着」：命中行亮出 ×，其余行收起。
##
## 为什么每帧扫一遍行矩形也不怕：只在 MouseMotion 里调用（鼠标不动就不算），
## 而且行数最多几十个，矩形判断是纯算术。这点代价换来的是**可预测**——
## 显隐只由「鼠标在不在这个矩形里」决定，不受子控件抢事件的影响。
func _update_row_hover(p: Vector2) -> void:
	var hit: Control = null
	if box_rows != null:
		for c in box_rows.get_children():
			var rc := c as Control
			if rc != null and rc.visible and rc.get_global_rect().has_point(p):
				hit = rc
				break
	if hit == _hover_row:
		return
	if _hover_row != null and is_instance_valid(_hover_row):
		var d0 = _hover_row.get_meta("del", null)
		if d0 != null and is_instance_valid(d0):
			(d0 as Button).modulate = Color(1, 1, 1, 0.0)
	_hover_row = hit
	if _hover_row == null:
		_refresh_op_help_default()
		return
	var d1 = _hover_row.get_meta("del", null)
	if d1 != null and is_instance_valid(d1):
		(d1 as Button).modulate = Color(1, 1, 1, 1)
	var op1 = _hover_row.get_meta("op", "")
	if String(op1) != "":
		_show_op_help(String(op1))


func _refresh_runtime() -> void:
	if vm == null:
		return
	var size_now: int = HrmVM.program_size(program)
	var speed_now: float = vm.speed()
	lbl_size.text = "%d/%d" % [size_now, target_size]
	lbl_speed.text = "%.2f/%.2f" % [speed_now, target_speed]
	# 周期必须跟着件数一起读：「34」本身没有好坏，「34÷17」才知道该往哪儿优化。
	# 表头写「周期÷件」，值写「34÷17」—— 一行里同时给出总数和摊分，不用玩家自己除。
	var n_items: int = vm.item_count()
	if n_items > 0:
		lbl_cycles.text = "%d÷%d" % [vm.cycles, n_items]
		lbl_cycles.tooltip_text = I18n.tf("%d 个周期处理 %d 件，摊到每件 %.2f 周期", [
			vm.cycles, n_items, float(vm.cycles) / float(n_items)])
	else:
		lbl_cycles.text = "%d" % vm.cycles
		lbl_cycles.tooltip_text = I18n.t("还没有处理过任何一件")
	_refresh_row_highlight()

	var best_key: String = str(int(level.get("id", 0)))
	if progress.has(best_key) and progress[best_key].get("cleared", false):
		var rec: Dictionary = progress[best_key]
		lbl_best.text = I18n.tf("最佳 %d · %.1f", [int(rec.get("size", 0)), float(rec.get("speed", 0.0))])
	else:
		lbl_best.text = ""

	# 状态一律带一枚圆点。圆点是游戏里「当前状态」的通用符号（灯亮着 / 灭了），
	# 纯文字「就绪」看着像一句日志，加了灯才像仪表。
	if vm.finished:
		lbl_size.add_theme_color_override("font_color", C_OK)
		lbl_speed.add_theme_color_override("font_color", C_OK)
		lbl_status.text = I18n.t("● 任务完成")
		lbl_status.add_theme_color_override("font_color", C_OK)
		btn_next.visible = true
	elif vm.failed:
		lbl_size.add_theme_color_override("font_color", C_TEXT)
		lbl_speed.add_theme_color_override("font_color", C_TEXT)
		lbl_status.text = "● " + vm.message
		lbl_status.add_theme_color_override("font_color", C_ERR)
		btn_next.visible = false
	else:
		lbl_size.add_theme_color_override("font_color", C_TEXT)
		lbl_speed.add_theme_color_override("font_color", C_TEXT)
		lbl_status.text = I18n.t("● 运行中…") if playing else I18n.t("● 就绪")
		lbl_status.add_theme_color_override("font_color", C_MUTED)
		btn_next.visible = false
	_update_buttons()


func _update_buttons() -> void:
	if btn_run != null:
		btn_run.text = I18n.t("■  暂停") if playing else I18n.t("▶  运行")


# ---------------------------------------------------------------- 截图 / 演示参数

func _handle_cli() -> void:
	var shot: String = ""
	var want_level: int = -1
	var want_steps: int = 0
	var bad: int = 0
	var _pose_hop: float = -1.0
	var gap_at: int = -1
	var help_op: String = ""
	var want_doc: bool = false
	var want_sel: int = -1
	var want_win: bool = false
	var want_settings: bool = false
	var want_allstar: bool = false      # 调试：直接弹「全三星」那张卡
	var want_cleared: int = -1      # -1 = 不动真实进度；0 = 清空，看全新开局长什么样
	var fill_spec: String = ""      # 调试/验关：把参考解铺进存档（--fill=20-40 / --fill=21 / --fill=all）
	var want_map: bool = false
	var want_pick: int = -1        # 打开地图后预先选中的关（0 起），截图核对「预选态」用
	var want_hint: int = 0         # 预先展开到第 N 级提示，截图核对舞台上的提示纸条
	# Godot 4 把 `--` 之后的参数单独收在 get_cmdline_user_args() 里，
	# 只扫 get_cmdline_args() 会拿不到 --shot/--level，截图会静默跳过。
	var argv: Array = []
	argv.append_array(OS.get_cmdline_args())
	argv.append_array(OS.get_cmdline_user_args())
	for a in argv:
		var s: String = String(a)
		if s.begins_with("--shot="):
			shot = s.substr(7)
		elif s.begins_with("--level="):
			want_level = int(s.substr(8))
		elif s.begins_with("--run="):
			want_steps = int(s.substr(6))
		elif s.begins_with("--bad="):
			bad = int(s.substr(6))
		elif s.begins_with("--gap="):
			gap_at = int(s.substr(6))
		elif s.begins_with("--op="):
			help_op = s.substr(5).to_upper()
		elif s == "--doc":
			want_doc = true
		elif s.begins_with("--sel="):
			want_sel = int(s.substr(6))
		elif s == "--win":
			want_win = true
		elif s == "--set":
			want_settings = true
		elif s == "--allstar":
			want_allstar = true
		elif s.begins_with("--cleared="):
			want_cleared = int(s.substr(10))
		elif s.begins_with("--fill="):
			fill_spec = s.substr(7)
		elif s == "--map":
			want_map = true
		elif s.begins_with("--pick="):
			want_pick = int(s.substr(7))
		elif s.begins_with("--hint="):
			want_hint = clampi(int(s.substr(7)), 0, 3)
		elif s.begins_with("--hop="):
			_pose_hop = float(s.substr(6))
	if shot != "":
		demo_mode = true          # 截图/演示：填参考解、不写存档
	# 调试用：造一批假成绩，用来核对地图上「已通关 / 星数」两套状态。
	# 星数按 3、2、1 循环发，一屏就能同时看到三种砖长什么样。
	# 先清空：截图要看的是「我刚说的这几个状态」，混进真实存档就什么都对不上了。
	if want_cleared >= 0:
		progress.clear()
		for i in mini(want_cleared, levels.size()):
			var cid: int = int(levels[i].get("id", i + 1))
			var ct: Dictionary = _target_of(i)
			var cs: int = 3 - (i % 3)
			progress[str(cid)] = {
				"cleared": true,
				"size": int(ct.get("size", 0)) + (0 if cs >= 2 else 3),
				"speed": float(ct.get("speed", 0.0)) + (0.0 if cs >= 3 else 1.0),
				"hint": false,
			}
		_refresh_level_buttons()   # 假成绩是改在 load_level 之后的，地图得手动重刷一次
	# 验关用：把参考解直接铺进「我的解」，打开那些关就是现成的答案，按运行就能看过程。
	# 写的是玩家程序的位置 —— 会覆盖这些关里你自己写的程序，所以只做在命令行开关里。
	# 必须在 load_level 之前做：load_level 才会把铺好的程序搬进编辑器。
	if fill_spec != "":
		_fill_programs(fill_spec)
		get_tree().quit()     # 铺完就走：这是批处理动作，不是开游戏（不开窗口干等）
	# 先切关再开地图：反过来的话地图是按旧关铺的，页码和预选都会指错
	if want_level > 0:
		load_level(want_level - 1)
	# 伪造「玩家已经卡了很久」，好把提示纸条直接展开到指定级别
	if want_hint > 0:
		stuck_time = STUCK_SEC + 1.0
		for _i in range(want_hint):
			_on_hint()
	# 调试用：开局就把牧场地图铺开，方便截图核对浮层尺寸与地砖的几种状态
	if want_map:
		_toggle_level_map()
		if want_pick >= 0 and map_levels != null:
			map_levels.pending = want_pick
			map_levels.show_page_of(want_pick)
			_sync_map_footer()
	if demo_mode and want_level > 0 and bad == 0:
		program = HrmVM.parse_program(level.get("ref", []))
		sel = -1
		_after_edit()
	# 调试用：故意塞一条会报错的程序，方便截图检查"出错行标红"
	if bad > 0:
		program = [HrmVM.make_ins("OUTBOX")]
		_after_edit()
	for _k in range(want_steps):
		if vm == null or vm.finished or vm.failed:
			break
		vm.step()
		_push_trail(vm.last_pc)
		if vm.last_op != "" and vm.last_op != "COMMENT":
			stage.act(vm.last_op, vm.last_arg)
	if want_steps > 0:
		if vm.finished:
			_record_win(HrmVM.program_size(program), vm.speed())
			# 调试用：`--win` 才把结算卡弹出来（延迟压到 0，不然命令行得额外空转）。
			# 默认不弹，这样才能单拍到「彩纸已经飞起来、卡片还没盖上来」的那一帧。
			if want_win:
				_show_win_card({"first": false, "size_better": true, "speed_better": false})
		stage.sync_from_vm(vm)
		_refresh_runtime()
		stage.worker_x = stage._key_x(stage.target_key)
	# 调试用：把跳跃动画钉在某一帧，方便截图核对抛物线
	if _pose_hop >= 0.0:
		stage.hop_t = _pose_hop
		stage.pose_lock = _pose_hop
		stage.hop_from = stage._key_x("fence")
		stage.queue_redraw()
	# 调试用：选中某一行，方便截图核对「参数编号 ↔ 草地木牌」的联动提示
	if want_sel >= 0 and want_sel < program.size():
		sel = want_sel
		_refresh_row_highlight()
		_sync_stage_link()
	if shot == "":
		return
	for _i in range(20):
		await get_tree().process_frame
	# 调试用：把某条指令的解释条定格，方便截图核对「悬停会讲什么」
	if help_op != "":
		_show_op_help(help_op)
		for _i in range(4):
			await get_tree().process_frame
	# 调试用：直接弹「四十关全三星」那张卡
	if want_allstar:
		# 造一份真的全三星成绩：不然卡上会是「81 / 120」还打绿勾 —— 那是我自己造出来的谎
		progress.clear()
		for i in levels.size():
			progress[str(int(levels[i].get("id", i + 1)))] = {
				"cleared": true, "size": true, "speed": true, "hint": false}
		_show_win_card({"first": false, "size_better": false, "speed_better": false}, true)
		# 入场动画 0.36s，等够再拍 —— 拍到半透明的那一帧，卡片看起来像坏了
		await get_tree().create_timer(0.55).timeout
	# 调试用：把设置浮层打开后再截图
	if want_settings:
		_toggle_settings()
		for _i in range(4):
			await get_tree().process_frame
	# 调试用：把说明书弹窗打开后再截图
	if want_doc:
		_open_doc()
		for _i in range(6):
			await get_tree().process_frame
	# 调试用：把拖拽时的「空隙 + 幽灵卡片」定格，方便截图核对
	if gap_at >= 0:
		_press_kind = "new"
		_press_op = "BUMPUP"
		_start_drag()
		_drag_pos = scroll_rows.get_global_rect().position + Vector2(120, 40 + 34 * gap_at)
		if _ghost != null:
			_ghost.global_position = _drag_pos + Vector2(18, 12)
		_show_gap(gap_at)
		for _i in range(16):
			await get_tree().process_frame
	if _pose_hop >= 0.0:
		# 注意：_ready 阶段 stage.size 还是 0，所有坐标都得在这时候按真实尺寸重算
		stage.hop_t = _pose_hop
		stage.hop_from = stage._key_x("fence")
		stage.worker_x = stage._key_x(stage.target_key)
		stage.fail_t = 1.0
		stage.queue_redraw()
		await RenderingServer.frame_post_draw
	await RenderingServer.frame_post_draw
	var img: Image = get_viewport().get_texture().get_image()
	img.save_png(shot)
	print("screenshot saved: " + shot)
	get_tree().quit()

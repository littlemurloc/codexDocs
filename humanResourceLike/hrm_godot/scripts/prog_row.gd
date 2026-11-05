extends PanelContainer
## 程序行 = 一张纸条：左侧一条色带表示状态，正在执行的那行色带会轻轻呼吸。
##
## 之前是「整块换底色」，整列看下来像表格；改成只给左边一条竖条之后，
## 状态依然一眼可见，但视线不会来回跳（《UI 设计军规》规则 16：最小代价换焦点）。
##
## 拖拽仍不走 Godot 内建 DnD：按下只上报坐标，命中判定与插入动画全由 main 算。

const KIT = preload("res://scripts/ui_kit.gd")

var main: Control = null
var index: int = 0
var sb: StyleBoxFlat = null
## 行首那个「01 / 02」的 Label。main 在运行时要把它换成 ▶ 或乘号 ——
## 见 main._refresh_row_highlight 里关于「第二通道」的注释。
var num_lbl: Label = null

## 程序行 = 一张蓝色圆角卡片。状态靠「描边」而不是左色带：
## 卡通游戏里选中某一张卡，做法是给它一圈白色高亮框（LayerLab 的背包格就是这个手法），
## 比一条 3px 竖条更符合这套语系，也更容易在蓝色底上被一眼看到。
const BG_NORM := KIT.SLIP   # 045e9d 中蓝
const BG_SEL := KIT.SLIP_SEL
const BG_PC := KIT.SLIP_PC
const BG_ERR := KIT.SLIP_ERR

# 执行中 / 出错的左缘色带
const BAR_PC := KIT.GREEN
const BAR_ERR := KIT.RED
const RING := Color("ffffff")

## 拖尾三档亮度（1 = 最近一行）。**必须是一档比一档淡**：第一版写成
## 「0.55 / 0.55 / 0.30」，最近的两行一样亮，看上去就只是「有两行变绿了」，
## 而不是「一道往下走的痕迹」。上限不许到 1.0 —— 那是「正在执行」的纯绿。
const TRAIL_K := [0.62, 0.42, 0.24]

var _pc: bool = false
var _t: float = 0.0
var _hover: bool = false


func _ready() -> void:
	# 行本身要能收到按下（PASS 会继续冒泡给列表，滚轮照样能滚）
	mouse_filter = Control.MOUSE_FILTER_PASS
	set_process(false)
	# 握把那三道线要跟着尺寸和悬停重画
	resized.connect(queue_redraw)
	mouse_entered.connect(func() -> void:
		_hover = true
		queue_redraw())
	mouse_exited.connect(func() -> void:
		_hover = false
		queue_redraw())


func _gui_input(e: InputEvent) -> void:
	if main == null:
		return
	if e is InputEventMouseButton and e.pressed and e.button_index == MOUSE_BUTTON_LEFT:
		# 把「按在行内哪个位置」一起传出去：左边是握把（拖这一行），
		# 右边是滚动区（拖着滚列表）。见 main.ROW_HANDLE_W。
		main.on_row_press(index, e.global_position, e.position.x)


## 光标也分区：压在左半边是「可以拿起来」，右半边是普通箭头。
## 这是鼠标上唯一能表达「这里有握把」的地方 —— 手指没有光标，
## 所以握把本身还得有静态可见的记号（见 _draw 里那三道横线）。
func _get_cursor_shape(at_position: Vector2) -> int:
	if main != null and main._tall and at_position.x <= main.ROW_HANDLE_W:
		return CURSOR_DRAG
	return CURSOR_ARROW


## 左侧握把的三道横线。**必须画出来**：手指没有光标，如果握把只在
## 「按下去之后会发生什么」里存在，玩家在按之前根本不知道那儿能按。
## 只在竖屏画 —— 桌面有滚轮，行卡整块都能拖，不需要这条边界。
func _draw() -> void:
	if main == null or not main._tall:
		return
	# 一条淡色竖槽 + 中间三道横线。只画线试过：2px 的线压在深蓝上，
	# 缩略图里像一粒灰，玩家根本不会注意到 —— 「有边界」这件事得靠**面**说，
	# 不能只靠线说。
	var hw: float = main.ROW_HANDLE_W
	var slot: Color = Color(1, 1, 1, 0.085 if not _hover else 0.14)
	draw_rect(Rect2(1.0, 2.0, hw - 8.0, size.y - 4.0), slot, true)

	var c: Color = Color(1, 1, 1, 0.62 if not _hover else 0.95)
	var w: float = 7.0
	var bar: float = 2.0
	var gap: float = 3.0
	var x: float = 4.0
	var y0: float = (size.y - (bar * 3.0 + gap * 2.0)) * 0.5
	for k in 3:
		draw_rect(Rect2(x, y0 + float(k) * (bar + gap), w, bar), c, true)


## 由 main 在每次刷新时调用，决定这一行长什么样。
## 四态共用同一套结构：圆角卡 + 2px 描边，只换描边颜色 ——
## 形状不变、只变色，整列扫下来才有节奏；形状也跟着变就会像表格换行。
##
## trail：刚执行过的行（1 = 上一行，越大越旧）。它是「加速」的可视化 ——
## 起步时只有一行亮，跑到 13 步/秒时是三四行一起亮，整列像一道下滑的扫描线。
## 不给拖尾的话，高速运行在玩家眼里就只剩「画面在抖」。
func set_state(is_sel: bool, is_pc: bool, is_err: bool, trail: int = 0) -> void:
	if sb == null:
		return
	var bg: Color = BG_NORM
	var line: Color = KIT.EDGE
	if is_err:
		bg = BG_ERR
		line = KIT.RED
	elif is_pc:
		bg = BG_PC
		line = KIT.GREEN
	elif is_sel:
		bg = BG_SEL
		line = RING
	elif trail > 0:
		# 拖尾不让它亮到和「正在执行」抢戏：只掺一点绿，一级比一级淡
		var k: float = TRAIL_K[clampi(trail - 1, 0, TRAIL_K.size() - 1)]
		bg = BG_NORM.lerp(BG_PC, k)
		line = KIT.EDGE.lerp(KIT.GREEN, k * 0.8)
	sb.bg_color = bg
	sb.border_color = line
	sb.set_border_width_all(2)
	# 只有「正在执行」那一行呼吸，别的行完全静止 —— 动效要稀缺才有效（规则 25）
	var want: bool = is_pc and not is_err
	if want != _pc:
		_pc = want
		set_process(want)
		_t = 0.0


func _process(delta: float) -> void:
	if not _pc:
		return
	_t += delta
	# 呼吸做在描边上：卡片是不透明的，透明度变化看不出来
	var k: float = 0.5 + 0.5 * sin(_t * 4.2)
	sb.border_color = BAR_PC.lerp(Color("d6ffb8"), k)

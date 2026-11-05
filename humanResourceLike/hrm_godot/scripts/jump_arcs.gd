extends Control
## 跳转线：JUMP / JUMPZ / JUMPN 和它的落点之间，画一条跨行的线。
##
## 为什么非要画这条线：
## 「JUMPZ b」和下面某行的「b」之间是什么关系，光看两个字母是看不出来的 ——
## 玩家得在脑子里做一次「往下找 b」，而程序一超过一屏，这次搜索就直接失败。
## 这条线把那次搜索画了出来，于是「这几行是一个循环体」变成了看得见的东西。
##
## 线一律走行卡左边那条 14px 空白栏（`row_gutter`），不分左右：
## 分左右会让同一段代码的两头各挂一串线，反而更乱。都走左边，
## 一列线竖下来就是「这段被谁从外面拉着」—— 这就是包裹感。
## 方向自己会说明语义：线在行下面收口 = 往回跳 = 循环；在上面收口 = 往前跳 = 分支。

const Kit = preload("res://scripts/ui_kit.gd")
const HrmVM = preload("res://scripts/hrm_vm.gd")

## 车道变了（0 = 没有跳转线）。main 拿它决定行卡整体右移多少 ——
## 「线有几列」这件事只能在这里算（列分配要看每行的 y），所以由这里说了算。
signal lanes_changed(n: int)

const LINE_W := 2.5
const LINE_W_HOT := 3.4
const LANE_PAD := 6.0        # 最左/最右车道离空栏边缘的余量（断口横杠 ±5，得装得下）
const LANE_STEP := 12.0      # 相邻两条车道的间距：2.5px 的线，间隔 12 才真正分得开
const MAX_LANE := 6          # 最多 6 条车道（缩进 72）。再多的程序已经读不动了，回绕共用
const IN_X := 2.0            # 线拐进行内的深度：行号从 13px 才开始，2 离字还远

var rows: Array = []         # 行节点，和 program 一一对应
var program: Array = []
var sel: int = -1            # 选中行：和它有关的线加亮

var lanes: int = 0           # 当前需要几条纵向车道
var _last_lanes: int = -1
var _scroll: ScrollContainer = null


func bind(p_scroll: ScrollContainer) -> void:
	_scroll = p_scroll


func set_data(p_rows: Array, p_program: Array, p_sel: int = -1) -> void:
	rows = p_rows
	program = p_program
	sel = p_sel
	queue_redraw()


## 行卡左边要让出多宽。0 条线 = 0，行卡贴左 —— 没跳转的程序不该为不存在的东西留白。
func gutter_width() -> float:
	if lanes <= 0:
		return 0.0
	return LANE_PAD * 2.0 + float(lanes - 1) * LANE_STEP


func _ready() -> void:
	# 纯装饰层：盖在行卡上面，但绝不能吃掉点击（行卡才是接事件的）
	mouse_filter = Control.MOUSE_FILTER_IGNORE
	set_process(true)


func _process(_d: float) -> void:
	# 每帧重画。想省可以只比 scroll_vertical，但行位置还会因为「上面插了一行」、
	# 「参数控件刚量出高度」而变，只盯滚动量就会把线画到旧位置上去。
	# 这张图最多几条折线，比修一次位置不同步便宜太多。
	queue_redraw()


## 算出所有「第 i 行跳到第 j 行」。抽成静态纯函数是为了能单测 ——
## 线怎么画可以凭眼睛验，但「哪一行跳到哪一行」不能靠眼睛。
## 返回 `[from, to, 目标标签]`：第三个值给颜色用，线跟着它要落的那一行的标签走。
## 标签重复时取最后一次（和 VM 的寻址行为一致）；目标标签不存在则不算一条。
static func links(program: Array) -> Array:
	var at := {}
	for i in program.size():
		var lab: String = String(program[i].get("label", ""))
		if lab != "":
			at[lab] = i
	var out: Array = []
	for i in program.size():
		var op: String = String(program[i].get("op", ""))
		if not HrmVM.JUMP_OPS.has(op):
			continue
		var target: String = String(program[i].get("arg", ""))
		if not at.has(target):
			continue                 # 标签还没落地（写了 JUMP 还没标目标）
		var j: int = int(at[target])
		if j != i:
			out.append([i, j, target])
	return out


func _draw() -> void:
	if rows.is_empty() or program.is_empty():
		_lanes_changed(0)
		return
	var origin: Vector2 = get_global_rect().position
	# 先收集：[i, j, 标签, y0, y1]
	var items: Array = []
	for pair in links(program):
		var i: int = int(pair[0])
		var j: int = int(pair[1])
		if i >= rows.size() or j >= rows.size():
			continue
		var ra: Rect2 = rows[i].get_global_rect()
		var rb: Rect2 = rows[j].get_global_rect()
		if ra.size.y <= 0.0 or rb.size.y <= 0.0:
			continue
		items.append([i, j, String(pair[2]),
			ra.position.y - origin.y + ra.size.y * 0.5,
			rb.position.y - origin.y + rb.size.y * 0.5])
	# **跨度大的先分列** —— 括号是层层套的：贯穿整个程序的大循环走外圈，
	# 只包住三行的分支走内圈。反过来（按出现顺序）会让第 3 行那个短跳转
	# 占掉最外面一列，视觉上像是它包住了整个函数。
	items.sort_custom(func(a, b) -> bool:
		return absf(float(a[4]) - float(a[3])) > absf(float(b[4]) - float(b[3])))
	var cols: Array = []             # 每列已占用的纵向区间
	var plan: Array = []             # [i, j, label, col]
	for it in items:
		plan.append([int(it[0]), int(it[1]), String(it[2]),
			_pick_col(cols, float(it[3]), float(it[4]))])
	_lanes_changed(cols.size())
	for it in plan:
		_draw_one(int(it[0]), int(it[1]), String(it[2]), int(it[3]),
			int(it[0]) == sel or int(it[1]) == sel, origin)


## 车道数变了才发信号 —— 每帧发会让 main 每帧改一次布局。
func _lanes_changed(n: int) -> void:
	lanes = n
	if n == _last_lanes:
		return
	_last_lanes = n
	# _draw 里改别人的 size/margin 是不合法的（正在刷新绘制），推迟一帧。
	lanes_changed.emit.call_deferred(n)


## 一段「出 → 拐 → 竖 → 拐 → 入」的折线，加起点圆点和终点箭头。
func _draw_one(i: int, j: int, lab: String, col_idx: int, hot: bool,
		origin: Vector2) -> void:
	var ra: Rect2 = rows[i].get_global_rect()
	var rb: Rect2 = rows[j].get_global_rect()
	ra.position -= origin
	rb.position -= origin
	if ra.size.y <= 0.0 or rb.size.y <= 0.0:
		return

	var y0: float = ra.position.y + ra.size.y * 0.5
	var y1: float = rb.position.y + rb.size.y * 0.5
	# 车道从「空栏左边缘」往右排：第 0 列最靠外，越大越靠里。
	var lane_x0: float = ra.position.x - gutter_width() + LANE_PAD
	var col: float = lane_x0 + float(col_idx) * LANE_STEP
	var inx: float = ra.position.x + IN_X

	# 颜色跟着「这条线要落到的那一行」的标签走：玩家看到黄色线，就知道它连的是那个黄牌子。
	var base: Color = Kit.label_tint(lab)
	var c_line: Color = Color(base, 1.0) if hot else Color(base, 0.78)
	var c_dot: Color = Color(base, 1.0) if hot else Color(base, 0.95)
	var w: float = LINE_W_HOT if hot else LINE_W

	# 端点跑到视口外时把线夹在边界上，并在断口画一道小横杠。
	# 不夹的话线会直接画出裁剪区，玩家看到的是「线没了」，而不是「还连着」。
	var a_out: bool = y0 < 1.0 or y0 > size.y - 1.0
	var b_out: bool = y1 < 1.0 or y1 > size.y - 1.0
	var y0v: float = clampf(y0, 1.0, size.y - 1.0)
	var y1v: float = clampf(y1, 1.0, size.y - 1.0)

	draw_polyline(PackedVector2Array([
		Vector2(inx, y0v), Vector2(col, y0v), Vector2(col, y1v), Vector2(inx, y1v),
	]), c_line, w, true)

	if a_out:
		_cut_mark(col, 1.0 if y0 < 1.0 else size.y - 1.0, c_dot)
	else:
		# 起点：小圆点 —— 「这条线是从这行出发的」
		draw_circle(Vector2(inx, y0v), 3.0, c_dot)

	if b_out:
		_cut_mark(col, 1.0 if y1 < 1.0 else size.y - 1.0, c_dot)
	else:
		# 终点：箭头指回行内 = 落在这一行
		draw_colored_polygon(PackedVector2Array([
			Vector2(inx + 8.0, y1v),
			Vector2(inx - 1.0, y1v - 5.5),
			Vector2(inx - 1.0, y1v + 5.5),
		]), c_dot)


## 断口：一道短横杠，表示「这条线还接着往上/往下走，只是看不见」
func _cut_mark(col: float, y: float, c: Color) -> void:
	draw_line(Vector2(col - 5.0, y), Vector2(col + 5.0, y), c, 2.5, true)


## 贪心分列：找第一条「纵向不冲突」的列，都冲突才新开一列。
## 不这么做的话，相隔很远的两个循环也会被挤到不同列上，栏里就全是平行线。
func _pick_col(cols: Array, y0: float, y1: float) -> int:
	var lo: float = minf(y0, y1) - 3.0
	var hi: float = maxf(y0, y1) + 3.0
	for c in cols.size():
		var free: bool = true
		for span in cols[c]:
			if not (hi < span.x or lo > span.y):
				free = false
				break
		if free:
			cols[c].append(Vector2(lo, hi))
			return c
	if cols.size() < MAX_LANE:
		cols.append([Vector2(lo, hi)])
		return cols.size() - 1
	cols[0].append(Vector2(lo, hi))
	return 0

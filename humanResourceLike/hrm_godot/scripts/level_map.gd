extends Control
## 牧场地图：20 个关卡 = 20 块地砖，而不是 20 行字。
##
## 为什么要自绘而不是用 GridContainer + Button：
## 用 Button 拼出来的是「一排按钮」，框是方的、间距是均匀的、字是横排的 ——
## 那还是列表，只是换了排法。地砖要有投影（浮起来）、有厚边、有星点（收集物），
## 这三样东西各画各的才控制得住，交给容器布局反而互相打架。
##
## 判据回到那句话：软件用位置组织信息，游戏用物体组织信息。
## 一行「[01] First Sheep    3星」是位置（第 3 行第 2 列）；
## 一块「01 ★★★」是物体（一块地，地上有庄稼）。
##
## 本类是纯渲染器：过关与否、几颗星都由 main 算好塞进 tiles，
## 判据只有一份（main._stars_of_idx），这里不重复算。

## 点一块砖 = 「预选」，不是「进入」。真进去要再按一下浮层底部的确认。
## 一按就走的话，想看第 27 关拿了几颗星的人会顺手把自己切走 —— 那是个不可撤销的操作，
## 配一个不可撤销的操作，代价是玩家以后不敢点地图了。
signal picked(index: int)

const Kit = preload("res://scripts/ui_kit.gd")

# 4 列 × 5 行：一页 20 关正好铺满，一眼看全，不用滚。
# 5 列会更「横」，但砖一挤就只有 40px 出头，数字和星点会挤在一起 ——
# 宁可多一行，也要让每块砖大到像个「东西」。
# 40 关之后靠翻页：8 列 × 5 行也能塞下，但砖会瘦成 94 宽的「表格单元格」，
# 地砖的那种「一块地」的感觉就没了。
const COLS := 4
const PER_PAGE := 20
const GAP := 7.0
var tile_max: float = 52.0       # 地砖上限：左栏里 52，弹出的大地图里可以放到 80+

var tiles: Array = []            # [{id:int, clear:bool, stars:int}, ...]
var cur: int = 0                 # 当前所在的关
var pending: int = -1            # 被点中、等着确认的那一关（-1 = 没选）
var page: int = 0                # 第几页（0 起）
var hover: int = -1

var _t: float = 0.0
var _boxes: Dictionary = {}      # 三种状态各一套 StyleBoxFlat，别每帧新建

# 三态：只换底色与描边，形状一律不动 —— 和程序行的四态是同一套语言
const C_TILE_CLEAR := Kit.AMBER
const C_TILE_CUR := Kit.SLIP_SEL
const C_TILE_LOCK := Color("083a63")      # 已解锁、还没通关
const C_TILE_SEALED := Color("042238")    # 还没解锁：比「未通关」再暗一档
# 预选砖的底色。为什么不只是加个绿框：
# 绿框在深蓝砖上根本跳不出来（2px 的绿线压 84px 的深蓝面，眼睛先看到的是面）。
# 预选是个「马上就要走」的短暂状态，这一瞬间玩家不需要知道「这块通没通关」，
# 所以底色可以先让位给状态 —— 星点还留着，信息没丢。
const C_TILE_PEND := Color("1a6f47")


func _ready() -> void:
	mouse_filter = Control.MOUSE_FILTER_STOP
	# 自绘控件不会自动给「可点」的光标。少了这只手，玩家会以为地图是张图。
	mouse_default_cursor_shape = Control.CURSOR_POINTING_HAND
	set_process(true)


func set_tiles(p_tiles: Array, p_cur: int) -> void:
	tiles = p_tiles
	cur = p_cur
	if hover >= tiles.size():
		hover = -1
	if pending >= tiles.size():
		pending = -1
	page = clampi(page, 0, maxi(0, page_count() - 1))
	queue_redraw()


func page_count() -> int:
	if tiles.is_empty():
		return 1
	return int(ceil(float(tiles.size()) / float(PER_PAGE)))


func page_start() -> int:
	return page * PER_PAGE


## 本页有几块砖。最后一页可能不满（比如 30 关时第二页只有 10 块）。
func page_len() -> int:
	return clampi(tiles.size() - page_start(), 0, PER_PAGE)


## 翻页。返回 true 表示真的翻了 —— 调用方要据此重刷「第 x / y 页」那行字。
func turn_page(delta: int) -> bool:
	var p: int = clampi(page + delta, 0, maxi(0, page_count() - 1))
	if p == page:
		return false
	page = p
	hover = -1
	queue_redraw()
	return true


## 把某一关翻到可见的那一页（打开地图时用：玩家想看的多半是自己现在这页）。
func show_page_of(index: int) -> void:
	page = clampi(int(floor(float(index) / float(PER_PAGE))), 0, maxi(0, page_count() - 1))
	queue_redraw()


func _process(delta: float) -> void:
	# 只有「当前关」和「预选」需要呼吸。没有它们就不用每帧重绘，省得 20 块地砖白刷。
	if not _need_pulse():
		return
	_t += delta
	queue_redraw()


func _need_pulse() -> bool:
	return (cur >= 0 and cur < tiles.size()) or (pending >= 0 and pending < tiles.size())


# ---------------------------------------------------------------- 几何

func _rows() -> int:
	return int(ceil(float(page_len()) / float(COLS)))


func _tile_size() -> float:
	var rows: int = _rows()
	if rows <= 0:
		return 0.0
	var w: float = (size.x - GAP * float(COLS - 1)) / float(COLS)
	var h: float = (size.y - GAP * float(rows - 1)) / float(rows)
	return minf(minf(w, h), tile_max)


## k 是「本页第几块」，不是全局关号 —— 分页以后这两者不再相等。
func _tile_rect(k: int) -> Rect2:
	var d: float = _tile_size()
	var rows: int = _rows()
	var gw: float = d * float(COLS) + GAP * float(COLS - 1)
	var gh: float = d * float(rows) + GAP * float(rows - 1)
	var ox: float = (size.x - gw) * 0.5
	var oy: float = (size.y - gh) * 0.5
	var c: int = k % COLS
	var r: int = int(floor(float(k) / float(COLS)))
	return Rect2(Vector2(ox + float(c) * (d + GAP), oy + float(r) * (d + GAP)), Vector2(d, d))


func _index_at(p: Vector2) -> int:
	for k in page_len():
		if _tile_rect(k).grow(1.0).has_point(p):
			return page_start() + k
	return -1


# ---------------------------------------------------------------- 画

func _box_for(kind: String, d: float) -> StyleBoxFlat:
	var key: String = "%s_%d" % [kind, int(d)]
	if _boxes.has(key):
		return _boxes[key]
	var bg: Color = C_TILE_LOCK
	var line: Color = Kit.EDGE
	var lw: int = 2
	match kind:
		"clear":
			bg = C_TILE_CLEAR
			line = Kit.EDGE
		"cur":
			bg = C_TILE_CUR
			line = Kit.PAPER
			lw = 3
		"pend":
			bg = C_TILE_PEND
			line = Kit.GREEN
			lw = 3
		"sealed":
			# 锁住的砖：底色再压暗一档、描边也退掉一半。
			# 光是「暗一点」不够 —— 它和「已解锁未通关」只差一次明度的话，
			# 玩家会以为自己看错了。差一档 + 一把锁，两个通道同时说。
			bg = C_TILE_SEALED
			line = Color(Kit.EDGE, 0.45)
	var sb := StyleBoxFlat.new()
	sb.bg_color = bg
	sb.set_corner_radius_all(int(minf(9.0, d * 0.22)))
	sb.border_color = line
	sb.set_border_width_all(lw)
	# 硬影：地砖要「从草地上浮起来」。偏移 3、几乎不模糊 —— 模糊一大就变网页卡片
	sb.shadow_color = Color(0, 0, 0, 0.34)
	sb.shadow_size = 2
	sb.shadow_offset = Vector2(0, 3)
	sb.anti_aliasing = true
	_boxes[key] = sb
	return sb


func _draw() -> void:
	if tiles.is_empty():
		return
	var d: float = _tile_size()
	if d < 12.0:
		return
	_draw_ground()
	var font: Font = get_theme_font("font", "Label")
	if font == null:
		font = ThemeDB.fallback_font
	var base: int = page_start()
	for k in page_len():
		var i: int = base + k
		var r: Rect2 = _tile_rect(k)
		var clear: bool = bool(tiles[i].get("clear", false))
		var is_cur: bool = (i == cur)
		var is_pend: bool = (i == pending)
		# 预选用绿框：和「当前关的白框」形状完全一样、只换颜色 ——
		# 形状在这个界面里等于状态，多一种形状就等于多一种「东西」。
		var unlocked: bool = bool(tiles[i].get("unlocked", true))
		var kind: String = "cur" if is_cur and not is_pend else ("clear" if clear else ("lock" if unlocked else "sealed"))
		if is_pend:
			kind = "pend"
		if i == hover and not is_cur and not is_pend and unlocked:
			# 悬停只提亮底色，不换形状
			var hb: StyleBoxFlat = (_box_for(kind, d).duplicate() as StyleBoxFlat)
			hb.bg_color = hb.bg_color.lightened(0.14)
			draw_style_box(hb, r)
		else:
			draw_style_box(_box_for(kind, d), r)

		var id: int = int(tiles[i].get("id", i + 1))
		var ink: Color = Kit.INK if clear and not is_cur else (Kit.TEXT if is_cur else Kit.INK_3)
		if not unlocked:
			ink = Color(Kit.INK_3, 0.5)
		if is_pend:
			ink = Kit.TEXT
		var fs: int = clampi(int(d * 0.40), 10, 17)
		# 有星点的砖，数字往上抬一点，给三颗星腾地方
		var lift: float = -d * 0.10 if clear else 0.0
		var baseline_y: float = r.position.y + r.size.y * 0.5 + float(fs) * 0.36 + lift
		draw_string(font, Vector2(r.position.x, baseline_y), "%02d" % id,
				HORIZONTAL_ALIGNMENT_CENTER, r.size.x, fs, ink)

		if clear:
			_draw_stars(r, int(tiles[i].get("stars", 0)))

		if not unlocked:
			_draw_lock(r, d, Color(Kit.TEXT, 0.42))

		if is_pend:
			_ring(r, d, Kit.GREEN, 0.45 + 0.35 * sin(_t * 3.4), true)
		elif is_cur:
			# 当前关：一圈随呼吸变亮的外光环。用「光环」而不是改底色，
			# 因为底色已经用来表示「过没过」，一个像素不能同时说两件事。
			_ring(r, d, Kit.AMBER, 0.35 + 0.35 * sin(_t * 2.6), false)


## 一把小锁，画在地砖右上角。
## **用几何画，不用字符**：思源黑体里没有锁字形，写「🔒」会变成方框
## （之前符号那轮已经踩过一次，FontFile 的 fallback 在主题上不生效）。
func _draw_lock(r: Rect2, d: float, c: Color) -> void:
	var s: float = d * 0.24
	var cx: float = r.position.x + r.size.x - s * 0.95
	var cy: float = r.position.y + s * 0.95
	# 锁体
	draw_rect(Rect2(cx - s * 0.5, cy, s, s * 0.62), c, true)
	# 锁梁：上半圈
	draw_arc(Vector2(cx, cy), s * 0.30, PI, TAU, 12, c, maxf(1.3, d * 0.035))


## 状态环：一圈外扩的光环 + 一圈贴边的描边。
## 预选（绿）和当前关（黄）共用这一份画法 —— 只换颜色，形状一律不动。
func _ring(r: Rect2, d: float, c: Color, a: float, thick: bool) -> void:
	var gb := StyleBoxFlat.new()
	gb.bg_color = Color(0, 0, 0, 0)
	gb.set_corner_radius_all(int(minf(9.0, d * 0.22)) + 3)
	gb.border_color = Color(c, a)
	gb.set_border_width_all(2)
	gb.anti_aliasing = true
	draw_style_box(gb, r.grow(4.0))
	if thick:
		var sb := StyleBoxFlat.new()
		sb.bg_color = Color(0, 0, 0, 0)
		sb.set_corner_radius_all(int(minf(9.0, d * 0.22)))
		sb.border_color = c
		sb.set_border_width_all(3)
		sb.anti_aliasing = true
		draw_style_box(sb, r)


## 草皮：地图不是一块玻璃，是片地。散几撮草，留白才读成「草地边缘」而不是「没排满」。
## 位置必须是确定性的（_hash01），否则每帧乱跳 —— 和通关彩纸同一个坑。
func _draw_ground() -> void:
	var grass := Color(1, 1, 1, 0.06)
	for i in 14:
		var px: float = _hash01(i * 3 + 1) * size.x
		var py: float = _hash01(i * 3 + 2) * size.y
		# 草长在砖上会像污点（砖本身有投影，压过去更脏），跳过砖区
		if _index_at(Vector2(px, py)) >= 0:
			continue
		var h: float = 3.0 + _hash01(i * 3 + 3) * 3.0
		draw_line(Vector2(px, py), Vector2(px - 1.5, py - h), grass, 1.5)
		draw_line(Vector2(px, py), Vector2(px + 1.5, py - h * 0.85), grass, 1.5)


## 三颗星：同一字形只换颜色。缺一颗时形状不变，才数得出来缺几颗。
## 空心/实心混用会让「2 星」和「3 星」看起来是两种东西。
## 形状必须是真星形 —— 三个圆点读出来是「弹孔」或「三个小孔」，
## 只有五角星能跟抬头那三颗★对上话（一个界面里同一种东西只许有一种画法）。
func _draw_stars(r: Rect2, n: int) -> void:
	var d: float = r.size.x
	var ro: float = maxf(3.2, d * 0.108)
	var step: float = ro * 2.35
	var cy: float = r.position.y + r.size.y - maxf(7.5, d * 0.155)
	var cx: float = r.position.x + r.size.x * 0.5 - step
	for k in 3:
		var c: Color = Color(Kit.INK, 1.0) if k < n else Color(Kit.INK, 0.22)
		draw_colored_polygon(_star_pts(Vector2(cx + step * float(k), cy), ro), c)


static func _star_pts(c: Vector2, ro: float) -> PackedVector2Array:
	var pts := PackedVector2Array()
	var ri: float = ro * 0.44
	for i in 10:
		var rr: float = ro if (i % 2) == 0 else ri
		var a: float = -PI * 0.5 + PI * float(i) / 5.0
		pts.append(c + Vector2(cos(a), sin(a)) * rr)
	return pts


static func _hash01(n: int) -> float:
	var x: float = sin(float(n) * 12.9898) * 43758.5453
	return x - floor(x)


# ---------------------------------------------------------------- 输入

func _gui_input(event: InputEvent) -> void:
	if event is InputEventMouseMotion:
		var i: int = _index_at(event.position)
		if i != hover:
			hover = i
			queue_redraw()
		return
	if event is InputEventMouseButton and event.pressed \
			and event.button_index == MOUSE_BUTTON_LEFT:
		var i: int = _index_at(event.position)
		if i >= 0:
			emit_signal("picked", i)
		accept_event()


func _notification(what: int) -> void:
	if what == NOTIFICATION_MOUSE_EXIT:
		if hover != -1:
			hover = -1
			queue_redraw()

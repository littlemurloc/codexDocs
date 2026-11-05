extends Control
## 拖拽时的「插入位」：一个从 0 长到整行高的虚线格子。
##
## 它是真的插进 VBoxContainer 里的一个节点，所以长高的过程就是把下面的行往下挤 ——
## 玩家看到的是「位置自己挪出来了」，而不是一条要精确对准的细线。

const ROW_H := 44.0

var h: float = 0.0
var target_h: float = ROW_H
var accent: Color = Color("ffdc30")
var label: String = ""


func _ready() -> void:
	mouse_filter = Control.MOUSE_FILTER_IGNORE
	custom_minimum_size = Vector2(0, 0)


func _process(delta: float) -> void:
	var k: float = clampf(delta * 22.0, 0.0, 1.0)
	h = lerpf(h, target_h, k)
	if absf(h - target_h) < 0.6:
		h = target_h
	if not is_equal_approx(custom_minimum_size.y, h):
		custom_minimum_size = Vector2(0, h)
	queue_redraw()


func _draw() -> void:
	if size.y < 2.0 or size.x < 4.0:
		return
	var r := Rect2(1.0, 1.0, size.x - 2.0, size.y - 2.0)
	draw_rect(r, Color(accent, 0.18), true)

	var dash := 7.0
	var skip := 5.0
	var x: float = r.position.x
	while x < r.end.x:
		var x2: float = minf(x + dash, r.end.x)
		draw_line(Vector2(x, r.position.y), Vector2(x2, r.position.y), Color(accent, 0.95), 2.0)
		draw_line(Vector2(x, r.end.y), Vector2(x2, r.end.y), Color(accent, 0.95), 2.0)
		x += dash + skip
	var y: float = r.position.y
	while y < r.end.y:
		var y2: float = minf(y + dash, r.end.y)
		draw_line(Vector2(r.position.x, y), Vector2(r.position.x, y2), Color(accent, 0.75), 2.0)
		draw_line(Vector2(r.end.x, y), Vector2(r.end.x, y2), Color(accent, 0.75), 2.0)
		y += dash + skip

	# 高度够了才写字，避免动画前半段糊成一团
	if label != "" and size.y >= 18.0:
		var font: Font = get_theme_default_font()
		var fs: int = 11
		var tw: float = font.get_string_size(label, HORIZONTAL_ALIGNMENT_LEFT, -1, fs).x
		var p := Vector2((size.x - tw) * 0.5, size.y * 0.5 + fs * 0.36)
		draw_string(font, p, label, HORIZONTAL_ALIGNMENT_LEFT, -1, fs, Color(accent, 0.9))

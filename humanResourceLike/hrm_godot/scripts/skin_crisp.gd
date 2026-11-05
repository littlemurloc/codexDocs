extends RefCounted
## Crisp Kit 贴图皮肤接入层。
##
## 为什么单独一层：贴图皮肤和「手搓 StyleBox」是两套完全不同的东西 ——
## 前者靠 assets 里的 PNG + 九宫格边距，后者靠代码里的颜色和圆角。
## 分成两层之后，素材没下、没导入、路径写错，游戏照样能跑（自动回退到手搓），
## 只是长得朴素一点。这比「素材缺失就报错」或「静默少一块」都好排查。
##
## 素材：Crisp Kit Free（Anipixels），免费可商用、免署名。
## 切图由 tools/import_crisp_skin.py 完成，边距数据在 crisp_slices.json 里。

const DIR := "res://assets/ui/crisp/"
const SLICES := DIR + "crisp_slices.json"

## 贴图上的字要用深色（白底），不能用全局白字
const INK := Color("16324a")

static var _meta: Dictionary = {}
static var _loaded: bool = false


static func _ensure() -> void:
	if _loaded:
		return
	_loaded = true
	if not FileAccess.file_exists(SLICES):
		return
	var f := FileAccess.open(SLICES, FileAccess.READ)
	if f == null:
		return
	var parsed: Variant = JSON.parse_string(f.get_as_text())
	if parsed is Dictionary:
		_meta = parsed


## 有没有可用的贴图皮肤（决定走贴图还是回退到手搓）
static func ok() -> bool:
	_ensure()
	return not _meta.is_empty()


static func has(name: String) -> bool:
	_ensure()
	return _meta.has(name)


## 取一个可拉伸的贴图样式块。名字不在表里、或图片没导入，都返回 null。
static func box(name: String, tint: Color = Color(1, 1, 1, 1)) -> StyleBoxTexture:
	_ensure()
	if not _meta.has(name):
		return null
	var t: Texture2D = load(DIR + name + ".png")
	if t == null:
		return null
	var m: Dictionary = _meta[name]
	var sb := StyleBoxTexture.new()
	sb.texture = t
	sb.texture_margin_left = float(m.get("l", 0))
	sb.texture_margin_top = float(m.get("t", 0))
	sb.texture_margin_right = float(m.get("r", 0))
	sb.texture_margin_bottom = float(m.get("b", 0))
	sb.modulate_color = tint
	return sb


## 单个控件（OptionButton / LineEdit / SpinBox）套上贴图输入框皮肤。
## 返回 true 表示套上了；false 表示没素材，调用方该回退。
##
## 注意 SpinBox：它本身没有 normal 这个主题项，真正画出来的是里面那个 LineEdit。
## 直接给 SpinBox 设 normal 不会报错，只是什么都没有 —— 这里替调用方拆开处理。
static func skin_input(c: Control) -> bool:
	if not ok() or not has("input_normal"):
		return false
	var target: Control = c
	if c is SpinBox:
		target = (c as SpinBox).get_line_edit()
		if target == null:
			return false
	var n := box("input_normal")
	if n == null:
		return false
	var hover := box("input_normal", Color(0.97, 0.99, 1.0, 1.0))
	var down := box("input_normal", Color(0.88, 0.92, 0.96, 1.0))
	for k in ["normal", "focus"]:
		target.add_theme_stylebox_override(String(k), n)
	target.add_theme_stylebox_override("hover", hover)
	target.add_theme_stylebox_override("pressed", down)
	for k in ["font_color", "font_hover_color", "font_pressed_color",
			"font_focus_color", "font_placeholder_color", "font_selected_color"]:
		target.add_theme_color_override(k, INK)
	target.add_theme_color_override("caret_color", INK)
	return true


## 数字框的两个步进键。
##
## 这里没用素材 —— button_flat_normal 自带一圈薄荷绿描边，染成蓝色后那道绿边还在，
## 挤在白输入框右边非常刺眼。
##
## 踩过的坑（记下来免得再走一遍）：一度想「自绘深墨三角盖掉引擎的浅灰箭头」，
## 结果无论三角画成 9×5、11×9 还是 16×8，落到这个只有十几像素高的键里都糊成一撮灰毛，
## 换纯红色块测试也一样淡 —— 图标在这么小的键里根本放不出细节。
## 结论：别跟图标较劲，**把底做深**。深蓝底 + 引擎自带浅灰箭头，
## 对比度天然够，箭头形状也还是引擎调好的那个。
static func skin_stepper(c: SpinBox) -> bool:
	if not ok():
		return false
	var n := _chip(Color("16324a"), Color("0a2033"))
	var h := _chip(Color("1f4a6b"), Color("4a90c2"))
	var d := _chip(Color("0f2438"), Color("08192a"))
	for k in ["up_background", "down_background"]:
		c.add_theme_stylebox_override(k, n)
		c.add_theme_stylebox_override(k + "_hovered", h)
		c.add_theme_stylebox_override(k + "_pressed", d)
		c.add_theme_stylebox_override(k + "_disabled", d)
	for k in ["up_icon_modulate", "down_icon_modulate"]:
		c.add_theme_color_override(k, Color(1, 1, 1))
	return true


static func _chip(bg: Color, line: Color) -> StyleBoxFlat:
	var sb := StyleBoxFlat.new()
	sb.bg_color = bg
	sb.set_corner_radius_all(3)
	sb.border_color = line
	sb.set_border_width_all(1)
	sb.content_margin_left = 2
	sb.content_margin_right = 2
	sb.content_margin_top = 2
	sb.content_margin_bottom = 2
	sb.anti_aliasing = true
	return sb


## 滚动条：轨道 + 滑块
static func skin_scroll(theme: Theme) -> bool:
	if not ok() or not has("progress_track") or not has("progress_fill"):
		return false
	var track := box("progress_track", Color(1, 1, 1, 0.22))
	var grab := box("progress_fill")
	var grab_hi := box("progress_fill", Color(1.15, 1.15, 1.15, 1.0))
	var grab_dn := box("progress_fill", Color(0.85, 0.88, 0.92, 1.0))
	if track == null or grab == null:
		return false
	for t in ["VScrollBar", "HScrollBar"]:
		theme.set_stylebox("scroll", t, track)
		theme.set_stylebox("scroll_focus", t, track)
		theme.set_stylebox("grabber", t, grab)
		theme.set_stylebox("grabber_highlight", t, grab_hi)
		theme.set_stylebox("grabber_pressed", t, grab_dn)
	return true


## 按钮三态。两种口径：
##   "primary"   —— 用素材原色的绿按钮（主操作，一屏只该有一个）
##   "secondary" —— 用素材里的白色按钮**染色**（素材是白的，modulate 乘什么色就是什么色）
## 之所以能这样：white × color = color，所以一套白按钮能变出整套配色，不用为每个颜色单独找素材。
static func button(kind: String) -> Dictionary:
	if not ok():
		return {}
	if kind == "primary":
		var a := box("button_medium_normal")
		var b := box("button_medium_hover")
		var c := box("button_medium_pressed")
		var d := box("button_medium_disabled")
		if a == null:
			return {}
		return _finish({"normal": a, "hover": b if b else a,
				"pressed": c if c else a, "disabled": d if d else a}, 12, 6, 12, 8)
	if kind == "secondary":
		var tint := Color("1d86d0")
		var a := box("button_flat_normal", tint)
		var b := box("button_flat_normal", tint.lightened(0.16))
		var c := box("button_flat_normal", tint.darkened(0.14))
		var d := box("button_flat_normal", tint.darkened(0.30))
		if a == null:
			return {}
		return _finish({"normal": a, "hover": b, "pressed": c, "disabled": d}, 11, 4, 11, 6)
	return {}


static func _finish(d: Dictionary, l: float, t: float, r: float, b: float) -> Dictionary:
	for k in d.keys():
		var sb: StyleBoxTexture = d[k]
		sb.content_margin_left = l
		sb.content_margin_top = t
		sb.content_margin_right = r
		sb.content_margin_bottom = b
	d["focus"] = StyleBoxEmpty.new()
	return d

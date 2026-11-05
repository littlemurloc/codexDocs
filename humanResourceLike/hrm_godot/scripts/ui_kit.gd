extends RefCounted
## 视觉工具箱：把「深夜牧场」这套材质做成可复用的 StyleBox
##
## 为什么要单独一层：原来所有面板都是一样的灰底 + 1px 细边，这正是「软件感」的来源
## （《UI 设计军规》规则 19：别急着画 1px 灰线，先用色差、留白、阴影分区）。
## 现在把「木牌」「纸条」「浮雕按钮」各自的边、影、圆角收在这里，
## UI 代码只说「这里是一块木牌」，不再手搓颜色。

# ============================================================================
# 基调卡：明亮卡通牧场（Casual Farm）
#
# 2026-10-30 达叔定了方向：要 Township / Coin Master / LayerLab「GUI Pro - Casual
# Game」那一挂的明亮卡通休闲游戏感，不要上一版的「深夜牧场·木牌与牛皮纸」。
#
# 那一挂的共同语言只有五条，照着做就有味：
#   1) 粗描边   —— 外圈一条深色实边（2~3px），像贴纸，不是 1px 灰线
#   2) 大圆角   —— 10~16px，块头越大圆角越大
#   3) 竖向渐变 —— 上亮下暗，读作「受光」
#   4) 硬投影   —— 偏移 3~5px 的实影（几乎不模糊），像从桌面上浮起来
#   5) 白字描边 —— 白字 + 深蓝描边，在任意亮底上都读得清
#
# 下面所有常量名都沿用旧名（WOOD / SLIP / INK…），因为 main.gd 有近百处引用，
# 改名字等于把整个工程翻一遍；名字先留着，值全部换成新语系。
# ============================================================================

# ---- 天（页面底）—— 整屏最深的一层，所有面板靠「比底更亮」站起来
const BG_DEEP := Color("05223f")
const BG := Color("083458")
const NIGHT := Color("0a3e68")

# ---- 面板（旧名 WOOD = 木牌，现在是面板/卡片）
const WOOD := Color("0e5a96")       # 一级面板：侧栏、底栏
const WOOD_2 := Color("1276bd")     # 二级：行卡、列表项
const WOOD_3 := Color("1d86d0")     # 按钮 / 突出的片
const WOOD_4 := Color("3cb3ff")     # 悬停高亮
const EDGE := Color("03192d")       # 外描边：比面板深三档，才读得成「一条粗边」
const EDGE_HI := Color("5fc8ff")    # 内侧高光边

# ---- 卡片（旧名 PAPER = 纸，现在是卡片）
const PAPER := Color("ffffff")
const PAPER_DIM := Color("0b4f88")

# ---- 卡片四态：底色只微调，状态主要靠「描边颜色」——
# 卡通游戏里选中一张卡是给它一圈亮框，不是换一块底色。
const SLIP := Color("1470b4")
const SLIP_SEL := Color("1c86cf")
const SLIP_PC := Color("1a7f52")
const SLIP_ERR := Color("a8372c")

# ---- 卡片上的字（旧名 INK = 墨，现在是白字，描边在控件上单独设）
const INK_1 := Color("ffffff")      # 指令名，最亮
const INK_2 := Color("cdeaff")      # 白话注释
const INK_3 := Color("8fc2e6")      # 行号等最弱信息

# ---- 文字
const TEXT := Color("ffffff")
const MUTED := Color("bcdcf5")
const FAINT := Color("8bb8d8")

# ---- 强调与状态（金 = 强调，绿 = 主操作/执行中，红 = 出错）
const AMBER := Color("ffdc30")
const AMBER_DEEP := Color("e0a81c")
const GREEN := Color("3ebc1a")
const RED := Color("e8553f")
const INK := Color("0a2a46")        # 白字描边色 / 亮底上的深字

# ---- 标签色板 a/b/c/d
# 为什么标签要上色：程序里最多同时有四个标签，字面上都是「a」「b」「c」「d」——
# 四个单字母在余光里长得一模一样。有了颜色，玩家不用读字就知道「这两行是同一个块」。
# 这是「颜色 + 位置双通道」那条规则的又一次应用：颜色不是装饰，是让位置关系长出来。
#
# 四个色相必须拉开（黄 / 绿 / 珊瑚 / 紫），而且都要亮到能当 2.5px 细线压在深蓝上。
# 深一点的色（比如藏青）做底色好看，做线就没了 —— 线的可辨识度优先于色板的和谐。
const LBL_A := Color("ffdc30")
const LBL_B := Color("4fd9a4")
const LBL_C := Color("ff8f6b")
const LBL_D := Color("b49bff")


## 标签 → 颜色。**标签贴纸和跳转线共用这一份** —— 同一个标签在两处是两个颜色，
## 等于让玩家记两套，那还不如不染色。
static func label_tint(lab: String) -> Color:
	match lab:
		"a":
			return LBL_A
		"b":
			return LBL_B
		"c":
			return LBL_C
		"d":
			return LBL_D
	return AMBER

const R := 10                       # 统一圆角：卡通要大圆角，小圆角读作「软件」


## 木牌：暖褐底 + 2px 木边 + 底部投影。投影是「离开桌面」的关键，没有它就是一张贴纸。
static func board(bg: Color = WOOD, radius: int = R, pad: int = 10,
		border: Color = EDGE, bw: int = 2, shadow: int = 8) -> StyleBoxFlat:
	var sb := StyleBoxFlat.new()
	sb.bg_color = bg
	sb.set_corner_radius_all(radius)
	sb.border_color = border
	sb.set_border_width_all(bw)
	sb.content_margin_left = pad
	sb.content_margin_right = pad
	sb.content_margin_top = pad
	sb.content_margin_bottom = pad
	if shadow > 0:
		# 硬影：卡通面板靠「几乎不模糊的投影」浮起来；模糊半径一大就变网页卡片
		sb.shadow_color = Color(0, 0, 0, 0.38)
		sb.shadow_size = 4
		sb.shadow_offset = Vector2(0, 5)
	sb.anti_aliasing = true
	return sb


## 纸条：没有外框，只有一条左侧竖条（强调色），用来做程序行 / 列表项。
## StyleBoxFlat 的边框颜色是全局的，但宽度可以分边设置 —— 只给左边宽度，就成了一条竖条。
static func strip(bg: Color, bar: Color = Color(0, 0, 0, 0), bar_w: int = 3, radius: int = 4,
		shadow: int = 0) -> StyleBoxFlat:
	var sb := StyleBoxFlat.new()
	sb.bg_color = bg
	sb.set_corner_radius_all(radius)
	if bar.a > 0.0:
		sb.border_color = bar
		sb.set_border_width(SIDE_LEFT, bar_w)
	sb.content_margin_left = 8 + bar_w
	sb.content_margin_right = 8
	sb.content_margin_top = 3
	sb.content_margin_bottom = 3
	# 亮面必须有影，否则纸条就是「填了色的格子」——
	# 投影是判断「这东西躺在桌面上」的唯一线索（军规 19：用影分区，别画线）
	if shadow > 0:
		sb.shadow_color = Color(0, 0, 0, 0.38)
		sb.shadow_size = shadow
		sb.shadow_offset = Vector2(0, maxi(1, shadow / 2))
	sb.anti_aliasing = true
	return sb


## 卡片：圆角 + 整圈描边。和 strip() 的分工是 ——
## strip 只画左边那一条色带（旧版的状态语言），card 画整圈（新版的选中语言）。
static func card(bg: Color, line: Color = Color(0, 0, 0, 0), lw: int = 0, radius: int = R,
		pad_l: int = 10, pad_r: int = 10, pad_y: int = 3) -> StyleBoxFlat:
	var sb := StyleBoxFlat.new()
	sb.bg_color = bg
	sb.set_corner_radius_all(radius)
	if lw > 0 and line.a > 0.0:
		sb.border_color = line
		sb.set_border_width_all(lw)
	sb.content_margin_left = pad_l
	sb.content_margin_right = pad_r
	sb.content_margin_top = pad_y
	sb.content_margin_bottom = pad_y
	sb.anti_aliasing = true
	return sb


## 按钮三态。卡通游戏的按钮读起来像「贴在屏幕上的一块塑料片」：
## 外圈一条深描边（不是 1px 灰线）、下方一道几乎不模糊的硬影、按下时整体下沉。
static func button_boxes(bg: Color, radius: int = R) -> Dictionary:
	var mk := func(b: Color, drop: bool, down: int) -> StyleBoxFlat:
		var sb := StyleBoxFlat.new()
		sb.bg_color = b
		sb.set_corner_radius_all(radius)
		sb.border_color = EDGE
		sb.set_border_width_all(2)
		sb.content_margin_left = 14
		sb.content_margin_right = 14
		sb.content_margin_top = 5 + down
		sb.content_margin_bottom = 5 + down
		if drop:
			# 硬影：偏移 4、模糊 2 —— 模糊一大就成「柔和阴影」，塑料感立刻塌掉
			sb.shadow_color = Color(0, 0, 0, 0.34)
			sb.shadow_size = 2
			sb.shadow_offset = Vector2(0, 4)
		else:
			sb.shadow_color = Color(0, 0, 0, 0.22)
			sb.shadow_size = 1
			sb.shadow_offset = Vector2(0, 1)
		sb.anti_aliasing = true
		return sb
	return {
		"normal": mk.call(bg, true, 0),
		"hover": mk.call(bg.lightened(0.14), true, 0),
		"pressed": mk.call(bg.darkened(0.12), false, 1),
		"disabled": mk.call(bg.darkened(0.22), false, 0),
		"focus": StyleBoxEmpty.new(),
	}


## 输入类控件（SpinBox 的输入框 / OptionButton / LineEdit）：
## 凹进去的槽，和按钮的「凸出来」形成对比，控件才不像网页表单。
static func well(bg: Color = Color("08345a"), radius: int = 4) -> StyleBoxFlat:
	var sb := StyleBoxFlat.new()
	sb.bg_color = bg
	sb.set_corner_radius_all(radius)
	sb.border_color = Color(0, 0, 0, 0.45)
	sb.set_border_width_all(1)
	sb.content_margin_left = 8
	sb.content_margin_right = 4
	sb.content_margin_top = 3
	sb.content_margin_bottom = 3
	sb.anti_aliasing = true
	return sb


## 卡片上的输入槽：卡是亮的，槽要「压下去」。
## 用比卡深两档的同色蓝 + 顶边一道更深的线 —— 光从上方来，凹槽顶沿一定最暗。
static func well_paper() -> StyleBoxFlat:
	var sb := StyleBoxFlat.new()
	sb.bg_color = Color("0a4a7c")
	sb.set_corner_radius_all(5)
	sb.border_color = Color("04223c")
	sb.set_border_width(SIDE_TOP, 2)
	sb.content_margin_left = 7
	sb.content_margin_right = 3
	sb.content_margin_top = 1
	sb.content_margin_bottom = 1
	sb.anti_aliasing = true
	return sb


## 步进键：一块凸出的小木片。顶边与左边提亮 —— 光从左上来，这样才像「能按下去的东西」。
## 不能加投影：两个键竖着叠在纸条里，投影会越过纸条下沿，看着像被裁掉一半。
static func chip(bg: Color = WOOD_3, radius: int = 2) -> StyleBoxFlat:
	var sb := StyleBoxFlat.new()
	sb.bg_color = bg
	sb.set_corner_radius_all(radius)
	sb.border_color = bg.lightened(0.22)
	sb.set_border_width(SIDE_TOP, 1)
	sb.set_border_width(SIDE_LEFT, 1)
	sb.content_margin_left = 3
	sb.content_margin_right = 3
	sb.content_margin_top = 0
	sb.content_margin_bottom = 0
	sb.anti_aliasing = true
	return sb


## 凹槽（读数窗）：计数器、数值胶囊用它，模拟「数字是嵌在板子里的一块表」。
## 和 chip() 的分工是一条通用规矩：**凸出来的是能按的，凹下去的是只读的**。
static func gauge(bg: Color = Color("08345a"), radius: int = 7) -> StyleBoxFlat:
	var sb := StyleBoxFlat.new()
	sb.bg_color = bg
	sb.set_corner_radius_all(radius)
	sb.border_color = EDGE
	sb.set_border_width_all(2)
	sb.content_margin_left = 8
	sb.content_margin_right = 8
	sb.content_margin_top = 1
	sb.content_margin_bottom = 2
	sb.anti_aliasing = true
	return sb


## 圆钮：正圆 + 深描边 + 硬影。只用在没有文字的动作上（翻页、步进、播放）。
## 圆形在这个界面里是一种语法，不是装饰：圆 = 方向 / 切换，圆角块 = 执行 / 命令。
## 散着用会让整屏看起来像一排棋子，所以只有「翻向另一关」这一件事允许用圆。
static func orb(bg: Color, d: int = 32) -> Dictionary:
	var r: int = int(round(d * 0.5))
	var mk := func(c: Color, dy: int) -> StyleBoxFlat:
		var sb := StyleBoxFlat.new()
		sb.bg_color = c
		sb.set_corner_radius_all(r)
		sb.border_color = EDGE
		sb.set_border_width_all(2)
		sb.content_margin_left = 0
		sb.content_margin_right = 0
		sb.content_margin_top = 0
		sb.content_margin_bottom = 0
		sb.shadow_color = Color(0, 0, 0, 0.36)
		sb.shadow_size = 2
		sb.shadow_offset = Vector2(0, dy)
		sb.anti_aliasing = true
		return sb
	return {
		"normal": mk.call(bg, 3),
		"hover": mk.call(bg.lightened(0.14), 3),
		"pressed": mk.call(bg.darkened(0.14), 1),
		"disabled": mk.call(bg.darkened(0.32), 1),
	}


# ---- 自绘图标 ------------------------------------------------------------
# 为什么不直接用引擎图标：默认主题给的是浅灰实心三角，落在牛皮纸上像贴了张塑料贴纸，
# 落在深木上又灰得发白。游戏里的步进键是「刻在木头上的一道痕」，所以这枚三角得自己画。
# 画法：4x4 超采样算像素覆盖率当 alpha，得到平直但不锯齿的边缘 —— 不引外部图，也不糊。

## 三角在 (fx, fy) 这一点是否被覆盖；fx/fy 都是 0..1 的归一化坐标
static func _tri_hit(fx: float, fy: float, up: bool) -> bool:
	var k := fy if up else 1.0 - fy
	return absf(fx - 0.5) <= 0.5 * k


static func _seg_dist(p: Vector2, a: Vector2, b: Vector2) -> float:
	var ab := b - a
	var t := clampf((p - a).dot(ab) / maxf(ab.length_squared(), 0.0001), 0.0, 1.0)
	return (p - (a + ab * t)).length()


static func glyph_tri(ink: Color, up: bool = true, w: int = 10, h: int = 7) -> ImageTexture:
	var img := Image.create(w, h, false, Image.FORMAT_RGBA8)
	img.fill(Color(0, 0, 0, 0))
	var ss := 4
	var inv := 1.0 / float(ss * ss)
	for py in range(h):
		for px in range(w):
			var cov := 0
			for sy in range(ss):
				for sx in range(ss):
					var fx := (float(px) + (float(sx) + 0.5) / float(ss)) / float(w)
					var fy := (float(py) + (float(sy) + 0.5) / float(ss)) / float(h)
					if _tri_hit(fx, fy, up):
						cov += 1
			if cov > 0:
				img.set_pixel(px, py, Color(ink.r, ink.g, ink.b, ink.a * float(cov) * inv))
	return ImageTexture.create_from_image(img)


## 下拉箭头：画成「V」而不是实心三角 —— 一道折痕比一块色块更像木片刻出来的
static func glyph_chev(ink: Color, w: int = 12, h: int = 7, thick: float = 1.8) -> ImageTexture:
	var img := Image.create(w, h, false, Image.FORMAT_RGBA8)
	img.fill(Color(0, 0, 0, 0))
	var ss := 4
	var inv := 1.0 / float(ss * ss)
	var a := Vector2(float(w) * 0.14, float(h) * 0.28)
	var m := Vector2(float(w) * 0.5, float(h) * 0.74)
	var b := Vector2(float(w) * 0.86, float(h) * 0.28)
	var half := thick * 0.5
	for py in range(h):
		for px in range(w):
			var cov := 0
			for sy in range(ss):
				for sx in range(ss):
					var p := Vector2(float(px) + (float(sx) + 0.5) / float(ss),
							float(py) + (float(sy) + 0.5) / float(ss))
					if minf(_seg_dist(p, a, m), _seg_dist(p, m, b)) <= half:
						cov += 1
			if cov > 0:
				img.set_pixel(px, py, Color(ink.r, ink.g, ink.b, ink.a * float(cov) * inv))
	return ImageTexture.create_from_image(img)


## 滚动条：细、圆、暖色，别抢视线
static func scroll_bar() -> Dictionary:
	var track := StyleBoxFlat.new()
	track.bg_color = Color(0, 0, 0, 0.22)
	track.set_corner_radius_all(3)
	track.content_margin_left = 2
	track.content_margin_right = 2
	var grab := StyleBoxFlat.new()
	grab.bg_color = Color(0.42, 0.34, 0.24, 0.85)
	grab.set_corner_radius_all(3)
	var grab_hi := grab.duplicate() as StyleBoxFlat
	grab_hi.bg_color = Color(0.56, 0.45, 0.30, 0.95)
	var grab_dn := grab.duplicate() as StyleBoxFlat
	grab_dn.bg_color = Color(0.34, 0.27, 0.19, 0.95)
	return {"track": track, "grab": grab, "grab_hi": grab_hi, "grab_dn": grab_dn}


## 把整套控件皮肤挂到任意 Control 的 Theme 上（滚动条 / 输入框 / 下拉 / 弹窗）
static func skin(theme: Theme) -> void:
	var sb := scroll_bar()
	theme.set_stylebox("scroll", "VScrollBar", sb["track"])
	theme.set_stylebox("grabber", "VScrollBar", sb["grab"])
	theme.set_stylebox("grabber_highlight", "VScrollBar", sb["grab_hi"])
	theme.set_stylebox("grabber_pressed", "VScrollBar", sb["grab_dn"])
	theme.set_stylebox("scroll", "HScrollBar", sb["track"])
	theme.set_stylebox("grabber", "HScrollBar", sb["grab"])
	theme.set_stylebox("grabber_highlight", "HScrollBar", sb["grab_hi"])
	theme.set_stylebox("grabber_pressed", "HScrollBar", sb["grab_dn"])

	theme.set_stylebox("normal", "OptionButton", well())
	theme.set_stylebox("hover", "OptionButton", well(Color(0.14, 0.11, 0.08)))
	theme.set_stylebox("pressed", "OptionButton", well(Color(0.08, 0.06, 0.04)))
	theme.set_stylebox("focus", "OptionButton", StyleBoxEmpty.new())
	theme.set_color("font_color", "OptionButton", TEXT)
	theme.set_color("font_hover_color", "OptionButton", AMBER)
	theme.set_icon("arrow", "OptionButton", glyph_chev(AMBER))

	theme.set_stylebox("normal", "LineEdit", well())
	theme.set_stylebox("focus", "LineEdit", well(Color(0.13, 0.10, 0.07)))
	theme.set_color("font_color", "LineEdit", TEXT)
	theme.set_color("caret_color", "LineEdit", AMBER)

	# 步进键：主题项真名是 up_background / down_background，图标是 up / down。
	# 之前写成 up_button / up_icon，名字不对不会报错，只静默失效 —— 所以那对箭头一直是引擎默认的灰三角。
	theme.set_icon("up", "SpinBox", glyph_tri(AMBER, true))
	theme.set_icon("down", "SpinBox", glyph_tri(AMBER, false))
	var c_n := chip(WOOD_3)
	var c_h := chip(WOOD_4)
	var c_p := chip(WOOD_2)
	for k in ["up_background", "down_background"]:
		theme.set_stylebox(k, "SpinBox", c_n)
		theme.set_stylebox(k + "_hovered", "SpinBox", c_h)
		theme.set_stylebox(k + "_pressed", "SpinBox", c_p)
		theme.set_stylebox(k + "_disabled", "SpinBox", c_p)
	theme.set_stylebox("field_and_buttons_separator", "SpinBox", StyleBoxEmpty.new())
	theme.set_stylebox("up_down_buttons_separator", "SpinBox", StyleBoxEmpty.new())
	for k in ["up_icon_modulate", "down_icon_modulate"]:
		theme.set_color(k, "SpinBox", Color(1, 1, 1))

	var pop := board(WOOD_2, 6, 4, EDGE, 1, 10)
	theme.set_stylebox("panel", "PopupMenu", pop)
	theme.set_stylebox("hover", "PopupMenu", strip(AMBER, AMBER, 0, 4))
	theme.set_color("font_color", "PopupMenu", TEXT)
	theme.set_color("font_hover_color", "PopupMenu", INK)
	theme.set_color("font_separator_color", "PopupMenu", MUTED)
	theme.set_constant("v_separation", "PopupMenu", 4)

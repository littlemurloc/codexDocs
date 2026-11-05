extends SceneTree

func _mk_fb() -> Array[Font]:
	var fb: Array[Font] = []
	for p in ["res://assets/fonts/sym2.otf", "res://assets/fonts/sym1.otf"]:
		fb.append(load(p))
	return fb

func _init():
	var f: FontFile = load("res://assets/fonts/app.otf")
	var fb := _mk_fb()

	# 方案 A：先设 theme，再改 theme.default_font 上的 fallbacks
	var t := Theme.new()
	t.default_font = f
	print("A: theme.default_font 是同一个实例吗? ", t.default_font == f)
	t.default_font.fallbacks = fb
	print("A: t.default_font.fallbacks=", t.default_font.fallbacks.size())
	var l := Label.new(); l.theme = t
	var lf: Font = l.get_theme_font("font")
	print("A: Label has ▾? ", lf.has_char(0x25BE), " fallbacks=", (lf.fallbacks.size() if lf is FontFile else -1))

	# 方案 B：FontVariation 包一层
	var f2: FontFile = load("res://assets/fonts/app.otf")
	var fv := FontVariation.new()
	fv.base_font = f2
	fv.fallbacks = fb
	var t2 := Theme.new()
	t2.default_font = fv
	print("B: theme.default_font 是同一个实例吗? ", t2.default_font == fv)
	var l2 := Label.new(); l2.theme = t2
	var lf2: Font = l2.get_theme_font("font")
	print("B: Label has ▾? ", lf2.has_char(0x25BE), " 类=", lf2.get_class())

	# 方案 C：直接把 fallbacks 写死到 Label 的 font override
	var t3 := Theme.new()
	var f3: FontFile = load("res://assets/fonts/app.otf")
	f3.fallbacks = _mk_fb()
	t3.default_font = f3
	var l3 := Label.new(); l3.theme = t3
	l3.add_theme_font_override("font", f3)
	print("C: override 后 has ▾? ", l3.get_theme_font("font").has_char(0x25BE))
	quit()

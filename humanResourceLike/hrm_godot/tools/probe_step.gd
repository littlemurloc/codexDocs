extends SceneTree
## 探针：确认 SpinBox 的 up/down 图标最终取到的是我们自绘的三角，还是引擎默认图标。
## 跑法：godot --headless --path . --script tools/probe_step.gd

func _init() -> void:
	var Skin = load("res://scripts/skin_crisp.gd")
	print("SkinCrisp.ok() = ", Skin.ok())

	var sb := SpinBox.new()
	print("覆盖前 up = ", sb.get_theme_icon("up").get_size() if sb.get_theme_icon("up") else "null")
	var got: bool = Skin.skin_stepper(sb)
	print("skin_stepper -> ", got)

	for n in ["up", "down"]:
		var ic: Texture2D = sb.get_theme_icon(n)
		if ic == null:
			print(n, " = null")
			continue
		var im: Image = ic.get_image()
		print(n, " size=", ic.get_size(), " fmt=", im.get_format())
		for y in range(im.get_height()):
			var row := ""
			for x in range(im.get_width()):
				row += "#" if im.get_pixel(x, y).a > 0.5 else "."
			print("   ", row)
	print("up_icon_modulate = ", sb.get_theme_color("up_icon_modulate"))
	quit()

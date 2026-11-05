extends SceneTree
const I18n = preload("res://scripts/i18n.gd")

func _init() -> void:
	# _load 是内部函数，直接调 t() 就会触发加载
	for lg in ["zh", "zh_Hant", "en"]:
		I18n.locale = lg
		print("locale=%-8s 设置=%s 音量=%s 画面=%s 自动=%s 竖版=%s 横版=%s 完成=%s" % [
			lg, I18n.t("设置"), I18n.t("音量"), I18n.t("画面"),
			I18n.t("自动"), I18n.t("竖版"), I18n.t("横版"), I18n.t("完成")])
	quit()

extends SceneTree
## 英雄与怪物的动作帧隔离（M217）
func _init() -> void:
	var db: DdDb = DdDb.shared("res://data")
	var art := UnitArt.new()
	art.placeholder_id = "skeleton_militia"
	print("英雄 crusader 有 windup 帧吗:", art.has_frame("crusader", "attack_windup"),
		"→ 两段式", "开" if art.has_frame("crusader", "attack_windup") else "关")
	print("怪物 skeleton_militia_A 有 windup 帧吗:", art.has_frame("skeleton_militia_A", "attack_windup"),
		"→ 两段式", "开" if art.has_frame("skeleton_militia_A", "attack_windup") else "关")
	var h: Texture2D = art.frame("crusader", "attack_windup", false)
	print("英雄 attack_windup(禁占位) =", "有" if h != null else "缺", h.get_size() if h else "")
	print("英雄 attack_sword  =", str(art.frame("crusader", "attack_sword", false).get_size()))
	quit()

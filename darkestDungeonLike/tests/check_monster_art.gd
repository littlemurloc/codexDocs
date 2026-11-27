extends SceneTree
## 一次性自检（M210）：怪物能不能拿到动作帧。
##
## 专门验三件事，都是「不跑起来看不出来」的：
##   1. `build_attack_map` 有没有把 `monsters.json` 也索引进去；
##   2. `skeleton_militia_A` 这个带变体后缀的 id 能不能找到 `skeleton_militia_*` 的图；
##   3. 三个关键帧（combat / attack_melee / dead）是不是都真的存在。

func _init() -> void:
	var db: DdDb = DdDb.shared("res://data")
	var art := UnitArt.new()
	art.build_attack_map(db)
	var anim: String = art.anim_for_skill("skeleton_militia_A", "sword_strike")
	print("anim_for_skill = '%s'" % anim)
	for a in ["combat", "attack_windup", "attack_melee", "dead"]:
		var t: Texture2D = art.frame("skeleton_militia_A", a)
		print("frame(%s) = %s" % [a, "有" if t != null else "缺"])
	# 占位资源（M213）：没做过的怪在任何动作下都该有图，不能掉回剪影
	art.placeholder_id = "skeleton_militia"
	for pair in [["fungal_bloat_A", "combat"], ["fungal_bloat_A", "attack_ranged"],
			["cultist_witch_A", "attack_spell"], ["brigand_cutthroat_A", "dead"]]:
		var t2: Texture2D = art.frame(str(pair[0]), str(pair[1]))
		print("占位 %s / %s = %s" % [pair[0], pair[1], "有" if t2 != null else "缺"])
	quit()

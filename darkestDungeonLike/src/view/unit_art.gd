class_name UnitArt
extends RefCounted
## 单位贴图（M36）。
##
## 只做一件事：**按 id 找图，找不到就说没有**。
## 怎么画、画多大、缺图时用什么占位，全在界面层——
## 因为「没有图」是正常状态（怪物现在一张静态图都没有），不是错误。
##
## ## 槽位约定（换美术时只换文件，不改代码）
##
## ```
## res://assets/art/units/<unit_id>.png
## ```
##
## - `<unit_id>` = `heroes.json` / `monsters.json` 里的 id，两边共用一套目录；
## - 任意尺寸的正方形，透明背景，**内容居中**；
## - 绘制端按「等比缩放到目标显示边长」处理，所以 85×85 和 256×256 都能直接用。
##
## 这就是「将来换同批规格的美术资源零障碍」的全部约定——
## 没有 manifest、没有注册表、没有尺寸表要同步。文件名对上就行。

const DIR: String = "res://assets/art/units/"

## 槽位与绘制约定（M38）：
##
## - `<id>.png`           方形头像（UI 用）
## - `<id>_<anim>.png`    动作帧：`combat` / `dead` / `defend` / `attack_*`
##
## **所有动作帧按同一缩放比导出**（以 `combat` 的画布高 400 为基准），
## 所以绘制端只用一个全局 scale，脚底统一压在地面线上。
## 不同帧画布大小不同（冲锋 837×461、死亡 368×508），但缩放比一致，
## 看起来就是同一个人的不同姿势，而不是忽大忽小。

## id -> Texture2D（缺图也缓存成 null，避免每帧重试一次 IO）
var _cache: Dictionary = {}

## "def_id|skill_id" -> 动作名（`art.anim`）。M38 从 heroes.json 建一次。
var _attack: Dictionary = {}


func texture_of(id: String) -> Texture2D:
	return _load("p:" + str(id), str(id))


## 某个动作的帧。没有这张图返回 null，由绘制端决定画什么占位。
func frame(id: String, anim: String) -> Texture2D:
	var a: String = anim if not anim.is_empty() else "combat"
	return _load("f:%s_%s" % [str(id), a], "%s_%s" % [str(id), a])


func _load(key: String, file_base: String) -> Texture2D:
	if _cache.has(key):
		return _cache[key]
	var tex: Texture2D = null
	var path: String = DIR + file_base + ".png"
	# exists() 对没导入的文件返回 false——资源放进目录后要跑一次 `--import`，
	# 否则这里会一直认为「没有图」，而画面只是安静地退回占位，不报错。
	if ResourceLoader.exists(path):
		tex = ResourceLoader.load(path) as Texture2D
	_cache[key] = tex
	return tex


func has_art(id: String) -> bool:
	return texture_of(id) != null


## 建「技能 → 动作帧」映射（M38）。
##
## 数据里现成的：`heroes.json` 每个技能带 `art.anim`（如 `attack_sword`），
## 而素材包里正好有 `<hero>.sprite.attack_sword.png`。两边不用人为对齐。
func build_attack_map(db: DdDb) -> void:
	_attack.clear()
	if db == null:
		return
	for hid in db.heroes.keys():
		var h: Dictionary = db.heroes[hid]
		for s in (h.get("skills", []) as Array):
			if not (s is Dictionary):
				continue
			var art: Dictionary = (s as Dictionary).get("art", {})
			var anim: String = str((art as Dictionary).get("anim", ""))
			if anim.is_empty():
				continue
			var sid: String = str((s as Dictionary).get("id", ""))
			_attack["%s|%s" % [str(hid), sid]] = anim


func anim_for_skill(def_id: String, skill_id: String) -> String:
	return str(_attack.get("%s|%s" % [def_id, skill_id], ""))


## 当前资源层的覆盖率（自检 / 诊断用）。返回 {have, total, missing}
func coverage(ids: Array) -> Dictionary:
	var missing: Array = []
	for id in ids:
		if not has_art(str(id)):
			missing.append(str(id))
	return {"have": ids.size() - missing.size(), "total": ids.size(), "missing": missing}

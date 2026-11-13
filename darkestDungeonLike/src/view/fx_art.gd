class_name FxArt
extends RefCounted

## 技能特效资源层（M57）。
##
## 素材来源：DD1 的 `heroes/<id>/fx/*.skel` / `monsters/<id>/fx/*.skel`，
## 由 `.tmp/spine/fxrender.py` 离线导成 `assets/art/fx/<名字>/000.webp` 帧序列，
## 并写一份 `manifest.json` 描述每个特效的帧数、fps、画布尺寸和锚点。
##
## 与 `unit_art.gd` 同一套哲学：**换美术零改代码**。
##   - 帧文件放进去就能播，代码不登记、不写死名字；
##   - 缺某个特效不报错，只是不播（「没有」是正常状态）；
##   - 数据里的映射（`skills[].art.fx`）是唯一来源，两边不用人工对齐。
##
## 锚点为什么重要：同一特效的每一帧都画在同一块**固定画布**上，
## 画布的哪里对应「角色脚底」由 `manifest.anchor` 给出。
## 画的时候 `位置 = 脚底 - 锚点 * 缩放`，各帧才会稳定落在一处，不会左右跳。

const DIR: String = "res://assets/art/fx/"
const MANIFEST: String = "res://assets/art/fx/manifest.json"

## fx 名 -> {frames, fps, w, h, anchor:[x,y], scale, dur}
var defs: Dictionary = {}
## "def_id|skill_id" -> {performer, target}
var _map: Dictionary = {}
## "名字/帧号" -> Texture2D。同一个特效常被几十个技能共用，必须缓存。
var _cache: Dictionary = {}


func load_manifest() -> bool:
	defs.clear()
	if not FileAccess.file_exists(MANIFEST):
		return false
	var txt: String = FileAccess.get_file_as_string(MANIFEST)
	var parsed: Variant = JSON.parse_string(txt)
	if parsed is Dictionary:
		defs = parsed
	return not defs.is_empty()


## 建「技能 → 特效名」映射。英雄和怪物一起建（两边字段同名）。
##
## 一个技能通常挂两条：`fx` 跟出手者、`targchestfx` 跟目标。
## 其余 `targfx` / `targheadfx` / `targlowfx` / `performerfx` 同样收着，
## 但当前战斗屏只用到前两条——多收不会错，将来要用不必再改这里。
func build_map(db: DdDb) -> void:
	_map.clear()
	if db == null:
		return
	for group in [db.heroes, db.monsters]:
		for did in group.keys():
			var row: Dictionary = group[did]
			for s in (row.get("skills", []) as Array):
				if not (s is Dictionary):
					continue
				var art: Dictionary = (s as Dictionary).get("art", {})
				if art.is_empty():
					continue
				var sid: String = str((s as Dictionary).get("id", ""))
				if sid.is_empty():
					continue
				var perf: String = str(art.get("fx", ""))
				if perf.is_empty():
					perf = str(art.get("performerfx", ""))
				# 目标特效的**落点**由字段名决定，不是猜的：
				# `targchestfx` 打胸口、`targheadfx` 打头、`targlowfx` 打脚下。
				# 资源本身的原点就在命中点（不是角色脚底），所以落点错了整块会飘到地上。
				var target: String = ""
				var t_anch: String = ""
				for pair in [["targchestfx", "chest"], ["targheadfx", "head"], ["targlowfx", "low"]]:
					if not str(art.get(pair[0], "")).is_empty():
						target = str(art.get(pair[0]))
						t_anch = str(pair[1])
						break
				if target.is_empty() and not str(art.get("targfx", "")).is_empty():
					target = str(art.get("targfx"))
					t_anch = "chest"
				_map["%s|%s" % [str(did), sid]] = {
					"performer": perf, "target": target, "target_anchor": t_anch}


## 某个单位的某个技能要播什么。返回 {performer, target}，缺就是空串。
func fx_for(def_id: String, skill_id: String) -> Dictionary:
	return _map.get("%s|%s" % [def_id, skill_id], {})


func has(name: String) -> bool:
	return defs.has(name)


func def_of(name: String) -> Dictionary:
	return defs.get(name, {})


## 取第 idx 帧。越界自动夹到范围内（时间累计多一点不会黑屏）。
func frame(name: String, idx: int) -> Texture2D:
	var d: Dictionary = defs.get(name, {})
	if d.is_empty():
		return null
	var n: int = int(d.get("frames", 0))
	if n <= 0:
		return null
	var i: int = clampi(idx, 0, n - 1)
	var key: String = "%s/%d" % [name, i]
	if _cache.has(key):
		return _cache[key]
	var path: String = "%s%s/%03d.webp" % [DIR, name, i]
	var tex: Texture2D = null
	if ResourceLoader.exists(path):
		tex = load(path) as Texture2D
	_cache[key] = tex
	return tex


## 覆盖率（自检用）：数据里被引用、但资源目录没有的特效名。
func missing(ids: Array) -> Array:
	var out: Array = []
	for nm in ids:
		if not defs.has(str(nm)):
			out.append(str(nm))
	return out

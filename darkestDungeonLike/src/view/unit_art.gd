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

## 暂代资源（M213）：任何单位找不到自己的图时，退到这一套 id 的图。
##
## 现在是开发期用**骷髅兵**顶掉全部怪物的黑色剪影，先验证「战斗画面全是立绘」
## 到底是什么样。**量产时要把它清空**：那时缺图回到剪影，剪影代表
## 「这只还没做」，是正常状态而不是 bug；留着占位会让缺图变得看不出来。
var placeholder_id: String = ""

## "def_id|skill_id" -> 动作名（`art.anim`）。M38 从 heroes.json 建一次。
var _attack: Dictionary = {}


func texture_of(id: String) -> Texture2D:
	var tex: Texture2D = _load("p:" + str(id), str(id))
	if tex == null:
		# 家族兜底（M210）：怪物是 `skeleton_militia_A`，图按 `skeleton_militia` 存
		var fam: String = family_of(str(id))
		if fam != str(id):
			tex = _load("p:" + fam, fam)
	return tex


## 某个动作的帧。没有这张图返回 null，由绘制端决定画什么占位。
##
## 查找顺序（M210 / M213）：
##   1. `<def_id>_<anim>`        —— 单独的变体给了专属图
##   2. `<family>_<anim>`        —— 家族图，一张覆盖 A/B/C/D 四个变体
##   3. `<placeholder>_<anim>`   —— 暂代资源（开发期才有）
##   4. `<placeholder>` 的起手帧 / 站姿 —— 占位单位没有这个动作时（比如法术）
##   5. null                     —— 交给绘制端画剪影
## `allow_placeholder`：怪物传 true，英雄传 false（M217）。
## 占位资源是**怪物的暂代**，英雄哪怕一张图都没有，也该是黑剪影，而不是别人。
func frame(id: String, anim: String, allow_placeholder: bool = true) -> Texture2D:
	var a: String = anim if not anim.is_empty() else "combat"
	var fam: String = family_of(str(id))
	var tex: Texture2D = _frame_of(str(id), a)
	if tex == null and fam != str(id):
		tex = _frame_of(fam, a)
	# 缺这个动作 → 退到**自己的站姿**（M217）。
	#
	# 英雄素材包的动作不全：`crusader` 有 banner / charge / heal / scroll / stun，
	# 唯独没有 `attack_sword`，而 `smite` 技能的 anim 正是它。
	# 没有这一步，英雄一出手就会跳过所有自己的图、掉进下面的怪物占位 ——
	# 表现是「我方放技能的一瞬间变成骷髅」（用户看到的就是这个）。
	if tex == null and a != "combat":
		tex = _frame_of(str(id), "combat")
		if tex == null and fam != str(id):
			tex = _frame_of(fam, "combat")
	if tex == null and allow_placeholder and not placeholder_id.is_empty():
		tex = _frame_of(placeholder_id, a)
		if tex == null:
			# 占位单位没有这个动作：攻击类用它自己的起手帧（至少有"在出手"的意思），
			# 其余退回站姿。不这么做的话，法术怪会突然变回黑剪影 ——
			# 而这一轮的目的恰恰是「让所有怪物都有立绘」。
			tex = _frame_of(placeholder_id, "attack_windup" if a.begins_with("attack_") else "combat")
	return tex


## **真的存在**这张图吗（M217）。不走任何 fallback。
##
## 两段式攻击的判据必须用它，不能用 `frame() != null`：
## `frame()` 现在有"缺动作 → 退自己的站姿"这一步，于是任何有立绘的单位
## 都会返回非 null，判据永远为真 —— 结果所有英雄都会先"站着不动 0.2 秒"
## 再切攻击帧，动作被拉长又发飘。
func has_frame(id: String, anim: String) -> bool:
	if _frame_of(str(id), anim) != null:
		return true
	var fam: String = family_of(str(id))
	return fam != str(id) and _frame_of(fam, anim) != null


func _frame_of(uid: String, anim: String) -> Texture2D:
	return _load("f:%s_%s" % [uid, anim], "%s_%s" % [uid, anim])


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
##
## **怪物也要建**（M210）：`monsters.json` 的技能同样带 `art.anim`
## （骷髅兵的 `sword_strike` 是 `attack_melee`）。原来只遍历 `db.heroes`，
## 于是怪物永远拿不到 anim、攻击时只能复用站姿 —— 就算把动作帧放进去也不会被用。
func build_attack_map(db: DdDb) -> void:
	_attack.clear()
	if db == null:
		return
	for hid in db.heroes.keys():
		_index_skills(str(hid), (db.heroes[hid] as Dictionary))
	for mid in db.monsters.keys():
		_index_skills(str(mid), (db.monsters[mid] as Dictionary))


func _index_skills(uid: String, def: Dictionary) -> void:
	for s in (def.get("skills", []) as Array):
		if not (s is Dictionary):
			continue
		var art: Dictionary = (s as Dictionary).get("art", {})
		var anim: String = str((art as Dictionary).get("anim", ""))
		if anim.is_empty():
			continue
		var sid: String = str((s as Dictionary).get("id", ""))
		_attack["%s|%s" % [uid, sid]] = anim


## `skeleton_militia_A` → `skeleton_militia`（M210）。
##
## 怪物数据有 A/B/C/D 四个变体，但**美术是同一套**（原版就是一套骨架换色）。
## 贴图按家族命名，一张覆盖四个变体；加载时先按 def_id 找，找不到再退回家族。
## 界面上要区分变体时再上换色，不必备四份图。
static func family_of(id: String) -> String:
	if id.length() > 2 and id[id.length() - 2] == "_":
		var tail: String = id.substr(id.length() - 1)
		if tail >= "A" and tail <= "D":
			return id.substr(0, id.length() - 2)
	return id


func anim_for_skill(def_id: String, skill_id: String) -> String:
	return str(_attack.get("%s|%s" % [def_id, skill_id], ""))


## 当前资源层的覆盖率（自检 / 诊断用）。返回 {have, total, missing}
func coverage(ids: Array) -> Dictionary:
	var missing: Array = []
	for id in ids:
		if not has_art(str(id)):
			missing.append(str(id))
	return {"have": ids.size() - missing.size(), "total": ids.size(), "missing": missing}

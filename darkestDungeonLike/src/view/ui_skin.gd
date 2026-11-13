class_name UiSkin
extends RefCounted
## 界面贴图槽位（M40）。
##
## 只解决一件事：**「这张图从哪来、没有图怎么办」收敛到一个地方**。
## 不负责排版——排版仍然在各屏的绘制函数里。抽太厚会变成另一套要和
## 现有 100 处绘制调用对齐的框架，收益抵不过风险。
##
## ## 槽位约定
##
## ```
## res://assets/art/ui/<kind>/<id>.png
## ```
##
## - `buildings/<building_id>.png` —— 城镇建筑（实际是「谁在这栋建筑里」的半身像）
## - 将来 `panels/` `icons/` 也走同一套，只要加一个方法
##
## 缺图返回 null，绘制端退回自绘。和 `UnitArt` 同一条原则：
## **「没有图」是正常状态，不是错误。**
##
## ## 开关
##
## `--no-skin` 会把 `enabled` 设成 false，全部退回自绘。
## 注意它只管**界面贴图**：单位立绘（`UnitArt`）不受影响，
## 那是战斗层的资源，和界面皮肤是两件事。
## 这不是可选装饰——它是验证「退化路径还能不能看」的唯一办法，
## 也是将来换成原创美术时逐个槽位替换的退路。

const DIR: String = "res://assets/art/ui/"

var enabled: bool = true

var _cache: Dictionary = {}


func texture(kind: String, id: String) -> Texture2D:
	if not enabled:
		return null
	var key: String = "%s/%s" % [kind, str(id)]
	if _cache.has(key):
		return _cache[key]
	var tex: Texture2D = null
	var path: String = DIR + key + ".png"
	# 资源放进目录后要跑一次 `--import`，否则 exists() 恒为 false，
	# 画面只是安静地退回自绘，不报错——排查时容易误判成「代码没接上」。
	if ResourceLoader.exists(path):
		tex = ResourceLoader.load(path) as Texture2D
	_cache[key] = tex
	return tex


## 城镇建筑。本作的 id 与 DD1 目录名不同（`coach` 对 `stage_coach`），
## 映射在导入时就展开成了文件名，这里不用再查表。
func building(id: String) -> Texture2D:
	return texture("buildings", id)


## 区域横幅（M42）：出发区背后的那张地貌图。
func region(id: String) -> Texture2D:
	return texture("regions", id)


## 一张都没加载到时返回 true，自检/诊断用。
func is_empty() -> bool:
	for k in _cache.keys():
		if _cache[k] != null:
			return false
	return true

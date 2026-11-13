class_name BattleBg
extends RefCounted

## 战斗背景（M45）。
##
## 素材是 DD1 的 `dungeons/<region>/<region>.room_wall.*.png`（1920×720，每区域 7–8 张）。
## 那批图的**底边往下 12% 是石板地面**，地面线在 y≈632/720（87.8%）。
## 提取时按 1280:422 的比例裁到地面线为止，于是：
##
##   「图的底边」= 「原图的地面线」
##
## 绘制端只做「铺满 + 底边对齐」，地面就自动接上我方地面线，不需要逐张调偏移。
## 这一步是必须的：如果直接把原图缩放到绘制区，地面线会落在不同高度，
## 每换一张背景角色就"换了身高"。
##
## 文件名约定 `<region>_<n>.png`，n 从 0 连续。缺号即视为到末尾——
## 不建 manifest，因为「有几个文件」就是唯一需要的信息。

const DIR: String = "res://assets/art/battle/bg/"
## 探测上限：超过这个数还找不到就停（防止死循环）。
const MAX_FRAMES: int = 32

var _cache: Dictionary = {}
var _count: Dictionary = {}


## 该区域有几张背景。缓存结果，避免每帧探测 IO。
func count_of(region: String) -> int:
	if _count.has(region):
		return int(_count[region])
	var n: int = 0
	while n < MAX_FRAMES and ResourceLoader.exists(DIR + "%s_%d.png" % [region, n]):
		n += 1
	_count[region] = n
	return n


## 取背景纹理。room_index < 0（不在房间里）时用第 0 张。
##
## 用**房间号**挑图而不是随机数：同一趟远征里回到同一个房间，背景应该还是那一张；
## 而且这条不消耗 `rng`，不会像 M15 那样把 bench 数字带偏。
func texture(region: String, room_index: int) -> Texture2D:
	var n: int = count_of(region)
	if n <= 0:
		return null
	var idx: int = 0
	if room_index >= 0:
		idx = room_index % n
	var key: String = "%s_%d" % [region, idx]
	if _cache.has(key):
		return _cache[key]
	var tex: Texture2D = ResourceLoader.load(DIR + key + ".png") as Texture2D
	_cache[key] = tex
	return tex


func has_any() -> bool:
	for r in ["weald", "crypts", "warrens", "cove"]:
		if count_of(r) > 0:
			return true
	return false

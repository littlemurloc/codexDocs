class_name LightLayer
extends RefCounted

## 光照的视觉层（M44）。
##
## 规则层早就有光照：`exp.light` 是 0–100，四档（明亮/微光/昏暗/漆黑），
## 影响怪物伤害、我方受压、侦察概率、被偷袭概率。但画面上**一点表现都没有**——
## 顶栏写着「光照 100（明亮）」，图和不写这个数时一模一样。
##
## 这一层只做一件事：把 light 变成一个**可见范围**。
##
## 做法是两张程序化径向渐变纹理，而不是 shader 或 mask：
##   `vignette` 中心透明 → 边缘不透明黑。铺成比屏幕大一圈、中心对准光源，
##              于是「洞里亮、洞外黑」。之所以能这么干，是因为 CanvasItem
##              没有擦除能力——只能往上盖东西，不能挖洞。
##              把「洞」做成纹理的透明部分、把纹理画得比屏幕大，等价于挖洞。
##   `warm`     中心暖黄 → 边缘透明，alpha 很低。只负责让光看起来像火把，
##              而不是一盏白炽灯。没有它，暗角会显得像「屏幕脏了一块」。
##
## 两张图都是代码生成的，不入库，也没有版权问题。

const VIG_SIZE: int = 256
const WARM_SIZE: int = 192

var _vig: GradientTexture2D = null
var _warm: GradientTexture2D = null


## 暗角纹理：中心透明，到边缘变成不透光的黑。
##
## 中间那段（0.34→0.55）刻意放缓：如果从中心就开始线性变暗，
## 光圈内的立绘也会被压灰，等于「光照低 = 整张图变暗」，
## 而不是「光照低 = 能看见的地方变小」。这两件事的观感完全不同。
func vignette() -> Texture2D:
	if _vig != null:
		return _vig
	var g := Gradient.new()
	g.offsets = PackedFloat32Array([0.0, 0.34, 0.55, 0.78, 1.0])
	g.colors = PackedColorArray([
		Color(0.015, 0.013, 0.012, 0.0),
		Color(0.015, 0.013, 0.012, 0.0),
		Color(0.015, 0.013, 0.012, 0.34),
		Color(0.012, 0.011, 0.010, 0.74),
		Color(0.010, 0.009, 0.009, 0.94),
	])
	var t := GradientTexture2D.new()
	t.gradient = g
	t.width = VIG_SIZE
	t.height = VIG_SIZE
	t.fill = GradientTexture2D.FILL_RADIAL
	t.fill_from = Vector2(0.5, 0.5)
	t.fill_to = Vector2(1.0, 0.5)
	_vig = t
	return _vig


## 暖光：中心一层很淡的橙色。alpha 上限只有 0.18——
## 再高就会把立绘的颜色吃掉，人物会变成一片橘子色。
func warm() -> Texture2D:
	if _warm != null:
		return _warm
	var g := Gradient.new()
	g.offsets = PackedFloat32Array([0.0, 0.26, 0.55, 1.0])
	# 纹理本身是**纯白**，颜色由绘制时的 modulate 决定（见 params 的 warm_tint）。
	# 如果这里写死橙色，就没法让「低光照偏冷」——乘一层冷色只会把橙色变浊。
	g.colors = PackedColorArray([
		Color(1.0, 1.0, 1.0, 0.17),
		Color(1.0, 1.0, 1.0, 0.095),
		Color(1.0, 1.0, 1.0, 0.022),
		Color(1.0, 1.0, 1.0, 0.0),
	])
	var t := GradientTexture2D.new()
	t.gradient = g
	t.width = WARM_SIZE
	t.height = WARM_SIZE
	t.fill = GradientTexture2D.FILL_RADIAL
	t.fill_from = Vector2(0.5, 0.5)
	t.fill_to = Vector2(1.0, 0.5)
	_warm = t
	return _warm


## 光照值 → 三个绘制参数。纯函数，不碰纹理，方便单测与对照。
##
##   radius_k  覆盖半径 / 屏幕宽。亮时 1.42（光圈远大于屏幕，四角只是略暗），
##             暗时 1.02（光圈缩进屏幕内，四角全黑）。
##   vignette  暗角的整体强度倍率。
##   warm      暖光强度倍率。
##   warm_tint 暖光的颜色。明亮偏暖黄，漆黑偏冷青——DD1 的招牌。
##             只靠亮度区分档位不够用：55 和 100 的明暗差肉眼很难分辨，
##             但「暖橙 → 冷青」一眼就分得开，而且比单纯变暗更不像故障。
##   dim       全屏压暗（0..1）。光照低时整屏变暗，**不只是**边缘。
##             为什么要这一项：界面基色本身已经接近黑（BG 约 20,22,26），
##             靠暗角「再压暗」压不下去——100 和 15 两档的观感差别太小。
##             整屏压一层才是「火把快烧完了」最直接的表达。
##
## 为什么「暗」不只是把强度调高：如果只调 alpha，四角变黑但**可见范围没变**，
## 玩家读到的还是「屏幕变暗了」。半径跟着缩，才是「看得见的地方变少了」。
static func params(light: float) -> Dictionary:
	var t: float = clampf(light / 100.0, 0.0, 1.0)
	var warm_col: Color = Color(1.0, 0.72, 0.42).lerp(Color(0.70, 0.78, 0.92), 1.0 - t)
	return {
		"radius_k": 1.02 + 0.40 * t,
		"vignette": 0.30 + 0.56 * (1.0 - t),
		"warm": 0.20 + 0.80 * t,
		"warm_tint": warm_col,
		"dim": 0.22 * (1.0 - t),
	}

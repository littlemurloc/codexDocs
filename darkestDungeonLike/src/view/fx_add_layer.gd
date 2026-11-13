class_name FxAddLayer
extends Node2D

## 加法混合的特效层（M57 修）。
##
## 为什么单独一层：DD1 的特效走自己的 particle shader——
## `tex0.rgb *= tex0.a` 之后按 additive 输出。我们原来的实现用普通 alpha 合成，
## 结果刀光变成一块灰色贴纸（`smite` 的贴图平均 RGB 只有 60/64/65，
## 而 alpha 高达 186：它是「暗灰的高透明度」，只有在加法混合下才读成光）。
##
## Control 的 `_draw()` 不能逐项换混合模式，所以加法的那部分必须画在
## 一个带 `CanvasItemMaterial(BLEND_MODE_ADD)` 的子节点上。
## 子节点画在父 Control 之后，所以它会盖在 UI 之上——特效本身都在
## 人物区域（y 250~500），碰不到底部面板，暂时接受。
##
## `modulate` 给 2.2 倍：素材平均亮度只有 0.25 左右，直接加法还是灰的；
## 放大 2.2 倍才是截图里那种白色刀光（A/B 见图 `shots/m57_add_ab.png`）。

const GAIN: float = 2.2

## 回调宿主（`expedition_scene`），由它提供要画哪些。
var host: Node = null


func _ready() -> void:
	var mat := CanvasItemMaterial.new()
	mat.blend_mode = CanvasItemMaterial.BLEND_MODE_ADD
	material = mat
	modulate = Color(GAIN, GAIN, GAIN, 1.0)


func _draw() -> void:
	if host != null and host.has_method("draw_fx_additive"):
		host.draw_fx_additive(self)

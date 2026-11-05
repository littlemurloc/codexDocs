class_name DdTheme
extends RefCounted
## 表现层的视觉令牌：颜色、字号、间距、按钮四态。
##
## M31 把 700 多名行的名字表搬去了 `dd_names.gd`，这里只剩「长什么样」。
## 下面 §2 是这一期新加的字号/间距刻度——之前每个调用点自己写 9/10/11/13/15，
## 同一个层级在不同屏幕上差 1px，是「看起来像草台班子」的主要来源之一。

const BG := Color("#14161a")
const PANEL := Color("#1b1e24")
const PANEL_DEEP := Color("#161920")
const PANEL_EDGE := Color("#2c313a")
const PANEL_HI := Color("#23272f")

const TEXT := Color("#d9d4c7")
const DIM := Color("#8b8a84")
const FAINT := Color("#5d5f5c")

const PARTY := Color("#3e5c76")
const ENEMY := Color("#7a3b34")

const HP := Color("#a8322d")
const HP_TRACK := Color("#241c1c")
const STRESS := Color("#c08a2e")
const STRESS_TRACK := Color("#241f16")

const CRIT := Color("#f0c040")
const HEAL := Color("#6fbf73")
const HARM := Color("#e8e2d4")
const STAT := Color("#9d7bd8")

const LIGHT := Color("#e0b24a")
const FOOD := Color("#8fae6a")
const OK := Color("#6fbf73")
const WARN := Color("#c8695f")

const BTN := Color("#23272f")
const BTN_HOVER := Color("#2f3540")
const BTN_OFF := Color("#191c21")
const BTN_ACTIVE := Color("#3a4453")



## 带省略号的截断。自绘 UI 没有自动换行，宁可按字符截断也不要让文字压到别的元素上。
static func ellipsis(text: String, font: Font, max_w: float, fs: int) -> String:
	if font.get_string_size(text, HORIZONTAL_ALIGNMENT_LEFT, -1, fs).x <= max_w:
		return text
	var out: String = text
	while out.length() > 1 and font.get_string_size(out + "…", HORIZONTAL_ALIGNMENT_LEFT, -1, fs).x > max_w:
		out = out.substr(0, out.length() - 1)
	return out + "…"


## 百分比 / 小数的统一写法。别在每处调用点各写一种。
static func pct(v: float, digits: int = 0) -> String:
	return ("%." + str(digits) + "f%%") % (v * 100.0)


# ============================================================
# §2 字号与间距刻度（M31）
# ============================================================
#
# 之前字号是散落的字面量：城镇 13/11/10、准备屏 15/11/9、战斗 13/12/9 ——
# 没有统一的层级，所以「次要信息」在有些屏比「主要信息」还大。
# 现在固定六档，新代码只准用这些名字：
#
#   FONT_TAG   9   角标、状态小字（不该抢注意力）
#   FONT_SM    10  辅助说明、行内单位
#   FONT_MD    11  正文默认
#   FONT_BD    13  强调（按钮文字、条目名）
#   FONT_LG    15  段落标题
#   FONT_H1    16  屏幕内的大标题
#   FONT_HERO  20  战斗中唯一的超大数字（伤害飘字）
const FONT_TAG: int = 9
const FONT_SM: int = 10
const FONT_MD: int = 11
const FONT_BD: int = 13
const FONT_LG: int = 15
const FONT_H1: int = 16
const FONT_HERO: int = 20
## 结算屏那种「一屏只有一个」的大标题
const FONT_DISPLAY: int = 30

# 间距只用 4 的倍数：4 / 8 / 12 / 16 / 24 / 32。
# 之前 3、5、6、7、10、14 都有，凑出来的空隙看起来处处不一样。
const GAP_XS: int = 4
const GAP_SM: int = 8
const GAP_MD: int = 12
const GAP_LG: int = 16
const GAP_XL: int = 24

## 屏幕四周统一留白。三块主屏（城镇/地图/战斗）都从这条线起。
const MARGIN: int = 28
## 顶栏高度：标题 + 一行副标题。所有屏的表头都占这么高，内容从 MARGIN+HEADER_H 起。
const HEADER_H: int = 56

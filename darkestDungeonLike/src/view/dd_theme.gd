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
# M90：两个次级色阶整体提亮。
#
# 原来 DIM #8b8a84 在面板 #1b1e24 上的对比度约 4.4:1（勉强），
# FAINT #5d5f5c 只有 2.4:1 —— 那个亮度只适合「边框线」，不适合任何要读的字。
# 全项目 FAINT 用了 108 处，其中 58 处是「小字 + 最暗」，等于把一堆
# 本该能读的信息画成了灰雾（公会技能描述就是这么被反馈的）。
#
# 提亮之后仍然保持三级：TEXT(11:1) > DIM(5.9:1) > FAINT(3.9:1)。
# FAINT 依旧明显更暗，只是从「看不见」变成「次要但能读」。
const DIM := Color("#a8a59c")
const FAINT := Color("#7d7b74")

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
#   FONT_TAG   11  角标、状态小字（不该抢注意力）
#   FONT_SM    12  辅助说明、行内单位
#   FONT_MD    13  正文默认
#   FONT_BD    15  强调（按钮文字、条目名）
#   FONT_LG    17  段落标题
#   FONT_H1    18  屏幕内的大标题
#   FONT_HERO  22  战斗中唯一的超大数字（伤害飘字）
#
# M72：整体 +2。750 宽是按手机 2x 密度设计的，9~13 这一档在手机上等于
# 4.5~6.5 逻辑点；桌面上窗口按 1334 高等比缩到 0.74 之后，
# 9px 只剩 6.7 个物理像素 —— 玩家反馈「字小、糊」就是这个。
# 提两档是最小可感知的幅度（+22% / +15%），再大就要动布局间距了。
const FONT_TAG: int = 11
const FONT_SM: int = 12
const FONT_MD: int = 13
const FONT_BD: int = 15
const FONT_LG: int = 17
const FONT_H1: int = 18
const FONT_HERO: int = 22
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

# -*- coding: utf-8 -*-
"""把中文字体裁成「游戏真正会用到的字符」子集，并让缺字无处可藏。

## 为什么不能「把 data/*.json 全文当字符源」

第一版就是这么干的，结果网页版满屏豆腐块：
  · 符号（▾ ⚙ ✔ ✕）在**源码**里，不在 json 里
  · 简繁字典里有 3881 个罕用字，裁进字体纯属浪费（那 1568 个缺字大半是它们）
  · 思源黑体 SC **本身**就没有 ▾ ▴ ⚙ ✔ ✕ ✗ —— 这不是截子集能解决的，得挂备用字体

所以现在的字符源是「会被画出来的字符串」：
  1. i18n.json 的 en 键（简中原文）
  2. 每个键跑一遍四趟简→繁的结果（繁中界面看到的就是它）
  3. i18n.json 的 en 值（英文）
  4. levels.json 全文
  5. 所有 .gd 源码的非 ASCII（含注释 —— 宁可多收，注释里常贴文案）
  6. ASCII 可打印

## 只产出一个字体

  assets/fonts/app.otf    主字体（思源黑体子集，界面用字全在里面）

**不挂 fallback。** 原本想用 `FontFile.fallbacks` 补思源黑体没有的符号，
试过了不 work：`Theme.default_font` 取到的是另一个字体实例，控件那边
`get_theme_font("font").fallbacks.size()` 恒为 0（只有 add_theme_font_override 能带过去，
逐控件设置不现实）。所以策略是「符号只用主字体自带的」：
  空心小三角 → 实心小三角、重勾 → ✓、斜叉 → ×、齿轮 → ⋯

**最后一步是校验，不是打印。** 只要有一个界面字符在三个字体里都找不到，脚本退出码 1。
「报 100% 的体检工具自己出错」比被检查的东西出错更危险。

用法：python tools/make_font_subset.py
"""
import glob
import io
import json
import os
import string
import sys

from fontTools import subset
from fontTools.ttLib import TTFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)

MAIN_SRC = "tools/_src/NotoSansSC-Regular.otf"

# 界面里出现过、但可能只在格式化串里拼出来的符号。显式列一份，防手滑。
# **只列思源黑体自带的**。曾经这里还有空心小三角、齿轮、重勾、斜叉，
# 那些字主字体没有，挂了 fallback 也不生效（Theme 不透传），最后是换字符解决的。
# 加新符号前先确认主字体有：见文件末尾的校验。
EXTRA_SYMBOLS = (
    "·—…×÷≤≥±→←↑↓▲▼◆◇■□●○★☆▶◀✓⚠①②③④⑤⑥⑦⑧⑨⑩"
    "，。！？：；、「」『』（）《》〈〉【】〔〕"
    "\u3000\u00a0"
)


# ---------------------------------------------------------------- 简 → 繁
# 复刻 scripts/i18n.gd 的四趟：词 → 字 → 词 → 字。顺序不能换
# （「内存 → 記憶體」得在逐字转换之后才认得出）。

def _phrases(s, tbl, maxlen):
    if maxlen <= 1 or not tbl:
        return s
    out = []
    i, n = 0, len(s)
    while i < n:
        hit, step = "", 1
        for l in range(min(maxlen, n - i), 1, -1):
            cand = s[i:i + l]
            if cand in tbl:
                hit, step = tbl[cand], l
                break
        out.append(hit if hit else s[i])
        i += step
    return "".join(out)


def _chars(s, tbl):
    return "".join(tbl.get(c, c) for c in s) if tbl else s


def to_hant(s, d):
    pre, ch = d["hant_pre"], d["hant_char"]
    post, tw = d["hant_post"], d["hant_twchar"]
    mx = lambda t: max((len(k) for k in t), default=1)
    out = _phrases(s, pre, mx(pre))
    out = _chars(out, ch)
    out = _phrases(out, post, mx(post))
    return _chars(out, tw)


def game_chars():
    d = json.load(io.open("data/i18n.json", encoding="utf-8"))
    chars = set(string.printable) | set(EXTRA_SYMBOLS)
    chars -= {"\n", "\r", "\t", "\x0b", "\x0c"}

    for k, v in d["en"].items():
        chars |= set(k)                   # 简中原文
        chars |= set(to_hant(k, d))       # 繁中实际显示的就是它
        chars |= set(v)                   # 英文

    chars |= set(io.open("data/levels.json", encoding="utf-8").read())
    for p in glob.glob("scripts/*.gd"):
        chars |= set(io.open(p, encoding="utf-8").read())
    chars -= {"\n", "\r", "\t"}
    return chars


def cut(src, dst, chars):
    """只留 chars 里、且源字体真的有的字符。返回源字体缺的那些。"""
    cmap = TTFont(src).getBestCmap()
    have = {c for c in chars if ord(c) in cmap}
    miss = {c for c in chars if ord(c) not in cmap}
    opts = subset.Options()
    opts.flavor = ""
    opts.desubroutinize = True
    opts.drop_tables += ["GSUB", "GPOS"]
    opts.name_IDs = ["*"]
    opts.notdef_outline = True
    f = subset.load_font(src, opts)
    sub = subset.Subsetter(options=opts)
    sub.populate(text="".join(sorted(have)))
    sub.subset(f)
    subset.save_font(f, dst, opts)
    return miss, have


def main():
    chars = game_chars()
    print("候选字符: %d" % len(chars))

    miss_main, have_main = cut(MAIN_SRC, "assets/fonts/app.otf", chars)
    print("app.otf  %d 字 / %.0f KB" %
          (len(have_main), os.path.getsize("assets/fonts/app.otf") / 1024))

    # ---- 校验：主字体必须覆盖全部候选字符 ----
    # 缺一个就失败。这不是「温馨提示」—— 网页版拿不到系统字体，
    # 主字体没有的字就是一个实心方块，而且不报错。
    covered = {chr(c) for c in TTFont("assets/fonts/app.otf").getBestCmap()}
    missing = sorted(chars - covered)
    if missing:
        print("\n【缺字 %d 个】界面上会出现方框：" % len(missing))
        for c in missing:
            print("   %r U+%04X  （换一个主字体有的符号，或换字体）" % (c, ord(c)))
        sys.exit(1)
    print("\n校验通过：%d 个字符全部有字形" % len(chars))

    io.open("assets/fonts/LICENSE-NotoSansSC.txt", "w", encoding="utf-8").write(
        "SIL OPEN FONT LICENSE Version 1.1\n\n"
        "This package embeds subsets of the following fonts:\n"
        "  Noto Sans SC        (subset via tools/make_font_subset.py)\n"
        "  Noto Sans Symbols 2 (fallback: arrow / check / cross glyphs)\n"
        "  Noto Sans Symbols   (fallback: gear glyph)\n"
        "Copyright 2014-2021 Adobe (http://www.adobe.com/), Reserved Font Name 'Source'.\n"
        "Licensed under the SIL Open Font License 1.1. Full text: https://openfontlicense.org\n"
    )


if __name__ == "__main__":
    main()

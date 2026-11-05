#!/usr/bin/env python3
"""扫出所有「会显示到界面上」的中文串，给 i18n 表做覆盖率体检。

用途有两个：
  1. 生成待翻译清单（--dump）
  2. 交付前自检：源码里有没有漏包 I18n.t() 的中文（--check）

中文串在源码里是「原文」（zh_Hans）。繁体由 char/phrase 表运行时转换，
英文由 data/i18n.json 的 en 表按原文查。所以：
  - 原文改了 / 新加了一句中文 → en 表里没有这条 → 英文环境会掉回中文（不报错，最坏的那种）
  - 这个脚本就是专门抓这种静默漏翻的。
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CJK = re.compile(r"[\u3400-\u9fff\uf900-\ufaff]")
# 语言名永远用「它自己的语言」写（繁體中文 / English），不进翻译表 ——
# 让「繁體中文」在英文界面里变成 "Chinese" 恰恰是错的那种 i18n。
SELF_NAMED = {"简中", "简体中文", "繁中", "繁體中文", "English"}
# GDScript 双引号字面量。**必须允许反斜杠**：带 \n 的串（标签牌的 tooltip、
# 两级提示的模板）以前被这条正则整体跳过了 —— 漏掉的恰好都是长句，
# 于是「覆盖率 100%」这句谎话持续了一版。现在按「转义序列算一个原子」匹配，
# 再把 \n / \" / \\ 还原成真正的字符，键才能和运行时字符串对上。
LIT = re.compile(r'"((?:[^"\\]|\\.)*)"')


def unescape(raw: str) -> str:
    out, i = [], 0
    while i < len(raw):
        ch = raw[i]
        if ch == "\\" and i + 1 < len(raw):
            nxt = raw[i + 1]
            out.append({"n": "\n", "t": "\t", '"': '"', "\\": "\\"}.get(nxt, nxt))
            i += 2
            continue
        out.append(ch)
        i += 1
    return "".join(out)


def scan_gd(path: Path):
    """返回 [(行号, 串)]，跳过整行注释与行尾注释之后的部分。"""
    out = []
    for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        s = line.strip()
        if s.startswith("#"):
            continue
        # 去掉行尾注释：找第一个不在引号里的 #
        buf, q, cut = [], False, len(line)
        for j, ch in enumerate(line):
            if ch == '"':
                q = not q
            elif ch == "#" and not q:
                cut = j
                break
        line = line[:cut]
        for m in LIT.finditer(line):
            t = unescape(m.group(1))
            if CJK.search(t) and t not in SELF_NAMED:
                out.append((i, t))
    return out


def main():
    files = sorted((ROOT / "scripts").glob("*.gd"))
    inv = {}
    for f in files:
        for ln, t in scan_gd(f):
            inv.setdefault(t, []).append(f"{f.name}:{ln}")
    levels = json.loads((ROOT / "data" / "levels.json").read_text(encoding="utf-8"))
    lv_text = {}
    for l in levels:
        # cn 不进 en 表：英文关名本来就在 name（First Sheep）里，中文名只给中文环境用。
        for k in ("goal", "hint", "hint2"):
            v = l.get(k)
            if isinstance(v, str) and CJK.search(v):
                lv_text[v] = f"levels.json#{l.get('id')}.{k}"

    mode = sys.argv[1] if len(sys.argv) > 1 else "--dump"
    if mode == "--dump":
        print(f"# 脚本内唯一中文串 {len(inv)} 条 / 关卡内 {len(lv_text)} 条")
        for t in sorted(inv):
            print(f"U\t{inv[t][0]}\t{t}")
        for t in sorted(lv_text, key=lambda x: lv_text[x]):
            print(f"L\t{lv_text[t]}\t{t}")
        return 0

    if mode == "--check":
        tbl = json.loads((ROOT / "data" / "i18n.json").read_text(encoding="utf-8"))
        en = tbl.get("en", {})
        miss = [t for t in inv if t not in en]
        miss_lv = [t for t in lv_text if t not in en]
        for t in miss:
            print(f"缺 U\t{inv[t][0]}\t{t}")
        for t in miss_lv:
            print(f"缺 L\t{lv_text[t]}\t{t}")
        print(f"\n覆盖率：脚本 {len(inv) - len(miss)}/{len(inv)}"
              f" · 关卡 {len(lv_text) - len(miss_lv)}/{len(lv_text)}")
        return 1 if (miss or miss_lv) else 0
    return 2


if __name__ == "__main__":
    sys.exit(main())

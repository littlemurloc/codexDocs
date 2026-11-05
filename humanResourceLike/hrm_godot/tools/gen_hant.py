#!/usr/bin/env python3
"""把 OpenCC 的 s2twp（简 → 繁 台湾正体＋惯用词）烘焙成游戏里能查的小表。

游戏运行时不想联网、也不想背 1MB 的 STPhrases，所以只留三样：
  hant_pre   简→繁 多字词（只留「光靠单字表转不对」的那些）
  hant_char  简→繁 单字表
  hant_post  繁→台 多字词（TWPhrases 全表，852 条，留给以后的文案）
  hant_twchar 台湾字形（TWVariants，41 条，最后一道）

生成后逐条比对完整 s2twp 流水线的结果：对不上就把该串里能修的 STPhrases 词补进
hant_pre，直到 0 差异 —— 保证游戏里看到的繁体就是 OpenCC 的答案。

字典从 OpenCC 仓库取来放进 tools/opencc/（只取需要的四个文件）：
  STCharacters.txt STPhrases.txt TWPhrases.txt TWVariants.txt
用法：
  python tools/gen_hant.py            # 体检
  python tools/gen_hant.py --write    # 写回 data/i18n.json
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DICT = ROOT / "tools" / "opencc"
CJK = re.compile(r"[\u3400-\u9fff\uf900-\ufaff]")

## OpenCC 的 TWPhrases 收的是 IT 词库（U盘→隨身碟、主板→主機板），
## 但游戏里的白话词它不管：程序 它不会变成 程式，循环 不会变成 迴圈。
## 下面这些是「按台湾玩家的读法」人工定的，宁可少改也不要改错 ——
## 只放确认无害的（同一个词在两岸指的是同一件事，只是叫法不同）。
MANUAL = {
    "程序": "程式",
    "循环": "迴圈",
    "数据": "資料",
    "鼠标": "滑鼠",
    "设置": "設定",
    "运行": "執行",
    "重置": "重設",
}


def load(name):
    out = {}
    for line in (DICT / f"{name}.txt").read_text(encoding="utf-8").splitlines():
        if not line or line.startswith("#"):
            continue
        parts = line.split("\t")
        if len(parts) < 2:
            continue
        k, v = parts[0], parts[1].split(" ")[0]
        if k != v:
            out[k] = v
    return out


class Conv:
    def __init__(self, pre=None):
        self.st_ch = load("STCharacters")
        self.st_ph = load("STPhrases")
        self.tw_ph = load("TWPhrases")
        self.tw_ch = load("TWVariants")
        self.pre = dict(pre or {})
        self._m = {k: max((len(x) for x in d), default=1) for k, d in
                   (("st", self.st_ph), ("tw", self.tw_ph), ("pre", self.pre))}

    @staticmethod
    def phrases(s, table, maxlen):
        if maxlen <= 1 or not table:
            return s
        out, i, n = [], 0, len(s)
        while i < n:
            hit, step = None, 1
            for l in range(min(maxlen, n - i), 1, -1):
                cand = s[i:i + l]
                if cand in table:
                    hit, step = table[cand], l
                    break
            out.append(hit if hit else s[i])
            i += step
        return "".join(out)

    @staticmethod
    def chars(s, table):
        return "".join(table.get(c, c) for c in s)

    def runtime(self, s):
        """游戏里 i18n.gd 走的同一条流水线。"""
        s = self.phrases(s, self.pre, self._m["pre"])
        s = self.chars(s, self.st_ch)
        s = self.phrases(s, self.tw_ph, self._m["tw"])
        return self.chars(s, self.tw_ch)

    def reference(self, s):
        """OpenCC s2twp 的完整流水线（含 STPhrases）。

        人工词表（MANUAL）两边都先过一遍：它是**有意的偏离**，不该被当成差异
        反复「修」，也不该被漏掉 —— 所以放在比对之前，让两边站在同一起点。
        """
        s = self.phrases(s, self.pre, self._m["pre"])
        s = self.phrases(s, self.st_ph, self._m["st"])
        s = self.chars(s, self.st_ch)
        s = self.phrases(s, self.tw_ph, self._m["tw"])
        return self.chars(s, self.tw_ch)


def corpus():
    tbl = json.loads((ROOT / "data" / "i18n.json").read_text(encoding="utf-8"))
    keys = [k for k in tbl.get("en", {}) if CJK.search(k)]
    lv = json.loads((ROOT / "data" / "levels.json").read_text(encoding="utf-8"))
    for l in lv:
        for k in ("cn", "goal", "hint", "hint2"):
            v = l.get(k)
            if isinstance(v, str) and CJK.search(v):
                keys.append(v)
    return sorted(set(keys))


def main():
    tbl = json.loads((ROOT / "data" / "i18n.json").read_text(encoding="utf-8"))
    strings = corpus()
    pre = dict(MANUAL)
    pre.update(tbl.get("hant_pre", {}))      # 上次生成的补词继续有效
    c = Conv(pre)
    diffs = [s for s in strings if c.runtime(s) != c.reference(s)]

    # 逐条修：在这串里找一个 STPhrases 词补进 pre，补到这条对得上为止
    for s in diffs:
        cands = []
        for l in range(2, len(s) + 1):
            for i in range(len(s) - l + 1):
                frag = s[i:i + l]
                if frag in c.st_ph:
                    cands.append((l, frag))
        for _l, frag in sorted(cands, reverse=True):
            trial = dict(pre)
            trial[frag] = c.st_ph[frag]
            cc = Conv(trial)
            if cc.runtime(s) == cc.reference(s):
                pre = trial
                c = cc
                break
        else:
            print("  修不了（STPhrases 里没有能补的词）：", s)

    # 精简：逐个试删。删完所有文案还能对得上，说明这个词本来就没起作用
    # （「输出」这种单字就能转对的，进去只是给字典添噪音）。
    # 只留「真的改了结果」的词，字典才读得懂 —— 下次加文案也才知道该往哪儿加。
    for w in list(pre.keys()):
        if w in MANUAL:                      # 人工词表不参与精简
            continue
        trial = dict(pre)
        del trial[w]
        cc = Conv(trial)
        if all(cc.runtime(s) == cc.reference(s) for s in strings):
            pre, c = trial, cc

    left = [s for s in strings if c.runtime(s) != c.reference(s)]
    print(f"文案 {len(strings)} 条 · 需要补词 {len(pre)} 个 · 仍不一致 {len(left)} 条")
    for s in left[:10]:
        print(f"   源 {s}\n   得到 {c.runtime(s)}\n   应为 {c.reference(s)}")

    out = dict(tbl)
    out["hant_pre"] = dict(sorted(pre.items(), key=lambda kv: (-len(kv[0]), kv[0])))
    out["hant_char"] = dict(sorted(c.st_ch.items()))
    out["hant_post"] = dict(sorted(c.tw_ph.items(), key=lambda kv: (-len(kv[0]), kv[0])))
    out["hant_twchar"] = dict(sorted(c.tw_ch.items()))

    if "--write" in sys.argv:
        (ROOT / "data" / "i18n.json").write_text(
            json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        print(f"已写回：pre {len(out['hant_pre'])} · char {len(out['hant_char'])}"
              f" · post {len(out['hant_post'])} · twchar {len(out['hant_twchar'])}")
        print(f"文件 {(ROOT / 'data' / 'i18n.json').stat().st_size // 1024} KB")
    else:
        print("（未写回，加 --write 才落盘）")
    return 0 if not left else 1


if __name__ == "__main__":
    sys.exit(main())

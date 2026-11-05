#!/usr/bin/env python3
"""CODEX.md -> CODEX.html

只做一件事：把 CODEX.md 排成和图册（ATLAS.html）同一套视觉的阅读版。
不是通用 Markdown 转换器，只认这本图鉴里实际用到的语法：

    # 卷一 · 城的地面          -> 卷首（大图/无图）
    ## 1.2 逐处                -> 节，进侧栏
    ### 一 · 井口台（...）      -> 小节，进侧栏
    | a | b |                  -> 表（第二行必须是分隔行）
    > 引文                     -> 引文块（多行合成一块）
    - / 1.                     -> 列表
    ---                        -> 分隔线
    ![[file.png|图注]]          -> 图版

用法：
    python tools/gen_codex.py            # 写 CODEX.html
    python tools/gen_codex.py --check    # 只校验，不写文件（CI 用）

约定：图版路径相对项目根，文件不存在时脚本会报错并列出缺失项——
图册最怕的是"图裂了但没人发现"。
"""

from __future__ import annotations

import html
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "CODEX.md"
OUT = ROOT / "CODEX.html"
IMG_DIR = "shots/concept"  # 图版都在这；md 里只写文件名


def img_path(name: str) -> str:
    """md 里写的裸文件名 -> 页面里用的相对路径"""
    return name if "/" in name else f"{IMG_DIR}/{name}"


# ---------------------------------------------------------------- 块级解析


def parse_blocks(lines: list[str]) -> list[dict]:
    blocks: list[dict] = []
    i, n = 0, len(lines)

    while i < n:
        raw = lines[i]
        line = raw.rstrip()

        if not line.strip():
            i += 1
            continue

        m = re.match(r"^(#{1,3})\s+(.*)$", line)
        if m:
            blocks.append({"t": "h", "lvl": len(m.group(1)), "text": m.group(2).strip()})
            i += 1
            continue

        m = re.match(r"^!\[\[(.+?)\|(.+?)\]\]\s*$", line)
        if m:
            blocks.append({"t": "img", "src": m.group(1).strip(), "cap": m.group(2).strip()})
            i += 1
            continue

        if re.match(r"^-{3,}\s*$", line):
            # 卷首前的那条 --- 不画线，卷首自己就是分隔
            j = i + 1
            while j < n and not lines[j].strip():
                j += 1
            if not (j < n and lines[j].lstrip().startswith("#")):
                blocks.append({"t": "hr"})
            i += 1
            continue

        if line.lstrip().startswith("|"):
            rows = []
            while i < n and lines[i].lstrip().startswith("|"):
                rows.append(lines[i].strip())
                i += 1
            blocks.append(_table(rows))
            continue

        if line.lstrip().startswith(">"):
            buf = []
            while i < n and lines[i].lstrip().startswith(">"):
                buf.append(re.sub(r"^\s*>\s?", "", lines[i].rstrip()))
                i += 1
            blocks.append({"t": "quote", "lines": [b for b in buf]})
            continue

        if re.match(r"^\s*-\s+", line):
            items = []
            while i < n and re.match(r"^\s*-\s+", lines[i]):
                items.append(re.sub(r"^\s*-\s+", "", lines[i].rstrip()))
                i += 1
            blocks.append({"t": "ul", "items": items})
            continue

        if re.match(r"^\s*\d+\.\s+", line):
            items = []
            while i < n and re.match(r"^\s*\d+\.\s+", lines[i]):
                items.append(re.sub(r"^\s*\d+\.\s+", "", lines[i].rstrip()))
                i += 1
            blocks.append({"t": "ol", "items": items})
            continue

        buf = [line.strip()]
        i += 1
        while i < n:
            nxt = lines[i]
            if (not nxt.strip()
                    or nxt.lstrip().startswith(("#", "|", ">", "- ", "![["))
                    or re.match(r"^\s*\d+\.\s+", nxt)
                    or re.match(r"^-{3,}\s*$", nxt)):
                break
            buf.append(nxt.strip())
            i += 1
        blocks.append({"t": "p", "text": " ".join(buf)})

    return blocks


def _table(rows: list[str]) -> dict:
    def cells(r: str) -> list[str]:
        r = r.strip()
        if r.startswith("|"):
            r = r[1:]
        if r.endswith("|"):
            r = r[:-1]
        return [c.strip() for c in r.split("|")]

    head = cells(rows[0])
    body = [cells(r) for r in rows[2:]] if len(rows) > 2 else []
    return {"t": "table", "head": head, "body": body}


# ---------------------------------------------------------------- 行内


def inline(text: str) -> str:
    t = html.escape(text, quote=False)
    t = re.sub(r"`([^`]+)`", r"<code>\1</code>", t)
    t = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", t)
    t = re.sub(r"(?<![\*\w])\*([^*]+)\*(?!\*)", r"<em>\1</em>", t)
    t = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', t)
    return t


# ---------------------------------------------------------------- 渲染


def vol_label(title: str) -> tuple[str, str]:
    """'卷一 · 城的地面' -> ('卷一', '城的地面')"""
    if "·" in title:
        a, b = title.split("·", 1)
        return a.strip(), b.strip()
    return "", title.strip()


def render(blocks: list[dict]) -> tuple[str, list[dict], str]:
    body: list[str] = []
    toc: list[dict] = []
    mast = ""
    sec = 0
    cur_vol: dict | None = None

    for idx, b in enumerate(blocks):
        t = b["t"]

        if t == "h":
            lvl, text = b["lvl"], b["text"]

            if lvl == 1 and not mast:
                mast = text
                body.append(_mast(text))
                body.append('<div class="wrap"><section class="intro" id="intro">')
                continue

            if lvl == 1:
                sec += 1
                sid = f"s{sec}"
                label, rest = vol_label(text)
                nxt = blocks[idx + 1] if idx + 1 < len(blocks) else None
                img = nxt if (nxt and nxt["t"] == "img") else None
                b["_used_img"] = bool(img)

                cls = "vol"
                if not img and "磨心" in text:
                    cls += " vol--mill"

                bg = ""
                if img:
                    bg = (f'<div class="vol-bg"><img src="{html.escape(img_path(img["src"]))}" '
                          f'alt="{html.escape(img["cap"])}"></div>')

                # 卷首横幅通栏，正文另起一个 wrap
                body.append("</section></div>")
                body.append(
                    f'<section class="{cls}" id="{sid}">{bg}'
                    f'<div class="vol-in">'
                    f'<div class="vol-kicker">{html.escape(label) if label else "附录"}</div>'
                    f'<h1>{inline(rest)}</h1>'
                    f'{_sub(rest)}'
                    f'</div></section>'
                )
                body.append('<div class="wrap">')
                cur_vol = {"id": sid, "label": label or rest, "title": rest, "items": []}
                toc.append(cur_vol)
                continue

            sec += 1
            sid = f"s{sec}"
            if lvl == 2:
                body.append(f'<h2 id="{sid}">{inline(text)}</h2>')
                if cur_vol is not None:
                    cur_vol["items"].append({"id": sid, "text": text, "lvl": 2})
                else:
                    toc.append({"id": sid, "label": text, "title": "", "items": []})
                    cur_vol = toc[-1]
            else:
                body.append(f'<h3 id="{sid}">{inline(text)}</h3>')
                if cur_vol is not None:
                    cur_vol["items"].append({"id": sid, "text": text, "lvl": 3})
            continue

        if t == "img":
            if b.get("_used_img") or (idx > 0 and blocks[idx - 1].get("_used_img")):
                continue
            body.append(_figure(b["src"], b["cap"]))
            continue

        if t == "p":
            body.append(f"<p>{inline(b['text'])}</p>")
        elif t == "quote":
            inner = "<br>".join(inline(x) for x in b["lines"] if x.strip())
            body.append(f"<blockquote>{inner}</blockquote>")
        elif t == "hr":
            body.append("<hr>")
        elif t == "ul":
            body.append("<ul>" + "".join(f"<li>{inline(x)}</li>" for x in b["items"]) + "</ul>")
        elif t == "ol":
            body.append("<ol>" + "".join(f"<li>{inline(x)}</li>" for x in b["items"]) + "</ol>")
        elif t == "table":
            body.append(_table_html(b))

    body.append("</section></div>")
    return "\n".join(body), toc, mast


def _mast(title: str) -> str:
    prose = re.sub(r"（[^）]*）|\([^)]*\)", "", title).strip()
    return (
        '<header class="mast">'
        '<div class="mast-eyebrow">The Codex of the Hollow</div>'
        f"<h1>{html.escape(prose)}</h1>"
        '<div class="mast-sub">四卷：城的地面 · 人 · 地下 · 磨心　　附：术语 · 接口 · 未定</div>'
        '<div class="mast-meta"><span>与 WORLD.md 同级</span>'
        '<span><a href="ATLAS.html">图册 ATLAS.html →</a></span><span>2026-11-03</span></div>'
        "</header>"
    )


def _sub(title: str) -> str:
    """卷首副题。一句话，说明这一卷装的是什么。"""
    subs = {
        "城的地面": "绞盘渡 · 十一个地方 · 围着一口井长出来",
        "人": "六个种 · 十三行 · 一个班站四个位",
        "地下": "四层 · 三段咽 · 十八个原住民",
        "磨心": "第四层 · 所有向下的通道汇成一处",
        "术语对照": "做本地化、写注释、对美术稿时用这一张",
        "与工程的接口汇总": "本文不改数值，只标该往哪儿挂",
        "还没定的": "这些是参数，不是设定",
    }
    key = re.sub(r"（.*?）|\(.*?\)", "", title).strip()
    s = subs.get(key) or subs.get(key.split("·")[-1].strip())
    return f'<div class="vol-sub">{html.escape(s)}</div>' if s else ""


def _figure(src: str, cap: str) -> str:
    return (f'<figure><img src="{html.escape(img_path(src))}" alt="{html.escape(cap)}" loading="lazy">'
            f"<figcaption>{inline(cap)}</figcaption></figure>")


def _table_html(b: dict) -> str:
    head = "".join(f"<th>{inline(c)}</th>" for c in b["head"])
    rows = []
    for r in b["body"]:
        if len(r) < len(b["head"]):
            r = r + [""] * (len(b["head"]) - len(r))
        cells = "".join(f"<td>{inline(c)}</td>" for c in r)
        rows.append(f"<tr>{cells}</tr>")
    return (f'<div class="tw"><table><thead><tr>{head}</tr></thead>'
            f"<tbody>{''.join(rows)}</tbody></table></div>")


def build_nav(toc: list[dict]) -> str:
    out = ['<nav class="toc">', '<div class="toc-kicker">目录</div>']
    for v in toc:
        out.append(f'<div class="toc-grp"><a class="toc-v" href="#{v["id"]}">{html.escape(v["label"])}'
                   f'{" " if v["title"] else ""}{html.escape(v["title"])}</a>')
        if v["items"]:
            out.append('<div class="toc-items">')
            for it in v["items"]:
                cls = "toc-i" + (" toc-i3" if it["lvl"] == 3 else "")
                out.append(f'<a class="{cls}" href="#{it["id"]}">{html.escape(it["text"])}</a>')
            out.append("</div>")
        out.append("</div>")
    out.append("</nav>")
    return "\n".join(out)


# ---------------------------------------------------------------- 模板

CSS = """
:root{
  --ink:#14161a; --ink-2:#1a1d22; --line:rgba(216,212,200,.1);
  --bone:#d8d4c8; --bone-dim:#9a978d; --bone-soft:#b6b1a6;
  --rust:#c08a2e; --rust-dim:#7a5c22; --teal:#4a5a6a;
}
*{margin:0;padding:0;box-sizing:border-box;}
html{scroll-behavior:smooth;scroll-padding-top:24px;}
body{
  background:var(--ink); color:var(--bone);
  font-family:"Songti SC","SimSun","Noto Serif CJK SC",Georgia,serif;
  font-size:16px; line-height:1.95; -webkit-font-smoothing:antialiased;
}
a{color:#c9a05a;text-decoration:none;border-bottom:1px solid rgba(192,138,46,.25);}
a:hover{color:#e0b76e;border-bottom-color:rgba(192,138,46,.6);}

/* 进度条 */
.bar{position:fixed;top:0;left:0;height:2px;width:0;background:var(--rust);z-index:60;transition:width .1s linear;}

/* 布局 */
.layout{display:grid;grid-template-columns:272px minmax(0,1fr);}
aside{
  position:sticky;top:0;height:100vh;overflow-y:auto;
  border-right:1px solid var(--line);padding:40px 22px 60px 28px;
  scrollbar-width:thin;
}
aside::-webkit-scrollbar{width:5px;}
aside::-webkit-scrollbar-thumb{background:rgba(216,212,200,.15);}
.toc-kicker{
  font-family:"Helvetica Neue",Arial,"PingFang SC",sans-serif;
  font-size:10px;letter-spacing:.34em;color:var(--rust);margin-bottom:22px;
}
.toc-grp{margin-bottom:18px;}
.toc-v{
  display:block;font-size:13.5px;color:#ded9cc;letter-spacing:.06em;
  border:0;padding:3px 0;
}
.toc-v:hover{color:#fff;}
.toc-items{margin:6px 0 0 1px;border-left:1px solid rgba(216,212,200,.12);padding-left:12px;}
.toc-i{
  display:block;font-size:12px;line-height:1.7;color:#8a8d95;border:0;
  padding:2px 0;
}
.toc-i3{padding-left:10px;font-size:11.5px;color:#75787f;}
.toc-i:hover,.toc-i3:hover{color:#c9c4b6;}
.toc-i.on,.toc-i3.on{color:var(--rust);margin-left:-13px;padding-left:12px;
  border-left:1px solid var(--rust);}

main{min-width:0;padding:0 0 120px;}
.wrap{max-width:920px;margin:0 auto;padding:0 38px;}

/* 扉页 */
.mast{max-width:920px;margin:0 auto;padding:88px 38px 44px;border-bottom:1px solid var(--line);}
.mast-eyebrow{font-family:"Helvetica Neue",Arial,"PingFang SC",sans-serif;
  font-size:10.5px;letter-spacing:.42em;color:var(--rust);text-transform:uppercase;margin-bottom:22px;}
.mast h1{font-size:clamp(34px,4.6vw,54px);font-weight:400;letter-spacing:.16em;color:#efece3;line-height:1.15;}
.mast-sub{font-size:14px;color:#9d998f;letter-spacing:.1em;margin-top:18px;}
.mast-meta{display:flex;gap:30px;flex-wrap:wrap;margin-top:26px;padding-top:16px;
  border-top:1px solid var(--line);font-family:"Helvetica Neue",Arial,"PingFang SC",sans-serif;
  font-size:10.5px;letter-spacing:.24em;color:#6f7278;}

/* 卷首 */
.vol{position:relative;min-height:340px;display:flex;align-items:flex-end;
  margin:16px 0 8px;overflow:hidden;border-top:1px solid var(--line);
  border-bottom:1px solid var(--line);}
.vol-bg{position:absolute;inset:0;}
.vol-bg img{width:100%;height:100%;object-fit:cover;object-position:center 42%;
  filter:brightness(.52) contrast(1.02);}
.vol-bg::after{content:"";position:absolute;inset:0;
  background:linear-gradient(to top,rgba(20,22,26,1) 2%,rgba(20,22,26,.55) 45%,rgba(20,22,26,.82) 100%);}
.vol-in{position:relative;z-index:2;padding:70px 38px 34px;max-width:920px;margin:0 auto;width:100%;}
.vol-kicker{
  font-family:"Helvetica Neue",Arial,"PingFang SC",sans-serif;
  font-size:11px;letter-spacing:.42em;color:var(--rust);margin-bottom:14px;
}
.vol h1{font-size:clamp(30px,4.2vw,46px);font-weight:400;letter-spacing:.14em;color:#efece3;}
.vol-sub{margin-top:16px;font-size:13.5px;letter-spacing:.12em;color:#9a9689;}
/* 卷四：磨心。没有图，用同心环做"磨眼" */
.vol--mill{background:
  radial-gradient(circle at 76% 44%, #05070a 0 3.4%, rgba(5,7,10,0) 4.2%),
  repeating-radial-gradient(circle at 76% 44%, rgba(192,138,46,.11) 0 1px, transparent 1px 27px),
  radial-gradient(circle at 76% 44%, rgba(74,90,106,.30) 0%, rgba(16,18,22,0) 60%),
  #0f1114;}
.vol--mill .vol-bg{display:none;}

/* 正文 */
.intro{padding-top:34px;}
.intro p{font-size:16.5px;color:#c2beb2;margin-bottom:1.35em;text-align:justify;}
h2{
  font-size:clamp(20px,2.5vw,27px);font-weight:400;letter-spacing:.08em;color:#e6e1d4;
  margin:64px 0 20px;padding-bottom:12px;border-bottom:1px solid var(--line);
}
h3{
  font-size:18.5px;font-weight:400;letter-spacing:.06em;color:#ded9cc;
  margin:44px 0 14px;
}
h3::before{content:"";display:block;width:26px;height:1px;background:var(--rust);margin-bottom:14px;opacity:.7;}
p{font-size:15.5px;color:var(--bone-soft);margin-bottom:1.15em;text-align:justify;}
strong{color:#eae5d8;font-weight:600;}
em{font-style:normal;color:#d3cdbc;border-bottom:1px solid rgba(192,138,46,.32);}
code{
  font-family:"JetBrains Mono",Consolas,monospace;font-size:.86em;
  background:rgba(216,212,200,.07);border:1px solid rgba(216,212,200,.06);
  padding:1px 5px;border-radius:2px;color:#cfc7b4;
}
blockquote{
  margin:26px 0;padding:4px 0 4px 20px;border-left:2px solid rgba(192,138,46,.45);
  color:#cfc9bb;font-size:15.5px;
}
blockquote br{content:"";display:block;margin-bottom:.45em;}
blockquote strong{color:#f0e9da;}
blockquote code{background:rgba(192,138,46,.1);}
hr{border:0;height:1px;background:var(--line);margin:58px 0;}
ul,ol{margin:0 0 1.3em 1.4em;}
li{font-size:15.5px;color:var(--bone-soft);margin-bottom:.45em;text-align:justify;}
li strong{color:#eae5d8;}

/* 图版：做成装裱的版面，不让铜版画的褐纸在冷底色上"跳"出来 */
figure{margin:44px 0 48px;background:#100e0c;border:1px solid rgba(192,138,46,.13);
  padding:12px 12px 0;box-shadow:0 20px 50px -30px #000;}
figure img{display:block;width:100%;height:auto;border:0;background:#0d0f12;}
figcaption{
  margin:0;padding:12px 3px 14px;font-size:12px;letter-spacing:.12em;color:#7f828a;
}
figcaption::before{content:"图版 ";color:var(--rust-dim);}

/* 表 */
.tw{overflow-x:auto;margin:24px 0 34px;}
table{width:100%;border-collapse:collapse;font-size:13px;}
thead th{
  text-align:left;font-weight:400;color:#cfa963;letter-spacing:.08em;
  background:rgba(192,138,46,.07);border-bottom:1px solid rgba(192,138,46,.28);
  padding:8px 10px;
}
tbody td{
  padding:8px 10px;border-bottom:1px solid rgba(216,212,200,.07);
  color:#aca79c;line-height:1.72;vertical-align:top;
}
tbody tr:hover td{background:rgba(216,212,200,.022);}
tbody td:first-child{color:#d6d0c2;white-space:nowrap;}
tbody th{white-space:nowrap;}
tbody td strong{color:#e8e2d4;}
td code,th code{font-size:.85em;}

/* 页脚 */
.foot{max-width:880px;margin:80px auto 0;padding:34px;border-top:1px solid var(--line);}
.foot p{font-size:12.5px;color:#5c5a54;letter-spacing:.1em;text-align:left;}

@media (max-width:1080px){
  .layout{grid-template-columns:1fr;}
  aside{display:none;}
  .wrap{padding:0 22px;}
  .mast{padding:56px 22px 32px;}
  .vol-in{padding:48px 22px 24px;}
  body{font-size:15.5px;}
  table{font-size:12.5px;}
}
@media print{
  aside,.bar{display:none;}
  body{background:#fff;color:#111;}
}
"""

JS = """
const bar=document.createElement('div');bar.className='bar';document.body.appendChild(bar);
addEventListener('scroll',()=>{
  const h=document.documentElement;
  bar.style.width=(h.scrollTop/(h.scrollHeight-h.clientHeight)*100)+'%';
},{passive:true});

const links=[...document.querySelectorAll('.toc-i,.toc-i3')];
const map=new Map(links.map(a=>[a.getAttribute('href').slice(1),a]));
const obs=new IntersectionObserver(es=>{
  es.forEach(e=>{
    if(!e.isIntersecting)return;
    links.forEach(l=>l.classList.remove('on'));
    const a=map.get(e.target.id); if(a)a.classList.add('on');
  });
},{rootMargin:'-10% 0px -80% 0px'});
document.querySelectorAll('h2[id],h3[id]').forEach(h=>obs.observe(h));
"""

HTML = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title} · 图鉴</title>
<style>{css}</style>
</head>
<body>
<div class="layout">
<aside>{nav}</aside>
<main>
{body}
<div class="foot">
  <p>空腔 · 图鉴　|　与《WORLD.md》同级，为其下卷　|　图版见 shots/concept/</p>
  <p style="margin-top:8px;">本文由 <code>tools/gen_codex.py</code> 从 <code>CODEX.md</code> 生成，不要直接改本文件。</p>
</div>
</main>
</div>
<script>{js}</script>
</body>
</html>
"""


def main() -> int:
    if not SRC.exists():
        print(f"[gen_codex] 找不到 {SRC}")
        return 1

    raw = SRC.read_text(encoding="utf-8")
    blocks = parse_blocks(raw.splitlines())

    missing = [b["src"] for b in blocks if b["t"] == "img" and not (ROOT / img_path(b["src"])).exists()]
    if missing:
        print("[gen_codex] 以下图版文件不存在：")
        for m in missing:
            print("   -", m)
        return 2

    body, toc, mast = render(blocks)
    nav = build_nav(toc)
    out = HTML.format(title=html.escape(mast or "空腔"), css=CSS, nav=nav, body=body, js=JS)

    n_tbl = sum(1 for b in blocks if b["t"] == "table")
    n_img = sum(1 for b in blocks if b["t"] == "img")
    n_words = len(re.sub(r"\s", "", raw))

    if "--check" in sys.argv:
        print(f"[gen_codex] check ok: {n_words} 字 / {n_tbl} 表 / {n_img} 图 / {len(toc)} 卷")
        return 0

    OUT.write_text(out, encoding="utf-8")
    print(f"[gen_codex] {OUT.name} 已生成：{n_words} 字 / {n_tbl} 表 / {n_img} 图 / {len(toc)} 卷 "
          f"/ {len(out)/1024:.1f} KB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

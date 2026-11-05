"""`.darkest` DSL 解析器。

DD1 的规则文件是一种极简的行式 DSL，形态为：

    <行类型>: .<字段> <值>... .<字段> <值>...
    combat_skill: .id "smite" .level 0 .atk 85% .target 12

约定：
  * 一行一条记录；行首 `类型:` 开启新记录。
  * 以 `.字段` 开头的行是上一条记录的续写（layout 文件大量使用）。
  * `//` 开始为注释；作者也误用过单斜杠 `/------`，一并按注释跳过。
  * 字段值可以是多个（`.effect "A" "B" "C"`）也可以为空（`.target  .is_crit_valid True`）。
  * 值类型：引号字符串 / true|false / 百分数 / 整数 / 浮点 / 裸标识符。

解析结果是 Record 列表，每条记录保留来源文件与行号，便于回溯校验。
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

# 行类型：允许行首缩进（部分 layout 文件有制表符/空格缩进）
_RE_RECORD = re.compile(r"^\s*([A-Za-z_][A-Za-z_0-9]*)\s*:")
# 字段名：`.xxx`
_RE_FIELD = re.compile(r"^\.([A-Za-z_][A-Za-z_0-9]*)$")
# 分词：优先匹配双引号字符串，其次非空白串
_RE_TOKEN = re.compile(r'"([^"]*)"|(\S+)')
# 百分数
_RE_PCT = re.compile(r"^(-?\d+(?:\.\d+)?)%$")
_RE_INT = re.compile(r"^-?\d+$")
_RE_FLOAT = re.compile(r"^-?\d*\.\d+$")


@dataclass
class Record:
    """一条 DSL 记录。"""

    type: str
    fields: dict[str, list[str]] = field(default_factory=dict)
    src: str = ""
    line: int = 0

    def raw(self, key: str, default=None):
        """取原始字符串值（单值时返回 str，多值返回 list）。"""
        vals = self.fields.get(key)
        if vals is None:
            return default
        if len(vals) == 0:
            return default
        if len(vals) == 1:
            return vals[0]
        return list(vals)

    def raw_list(self, key: str) -> list[str]:
        return list(self.fields.get(key, []))

    def __repr__(self) -> str:  # pragma: no cover - 调试用
        return f"<{self.type} {self.fields.get('id') or self.fields.get('name') or ''} @{self.src}:{self.line}>"


class ParseStats:
    """解析统计，用于发现语法漏网之鱼。"""

    def __init__(self) -> None:
        self.files = 0
        self.records = 0
        self.comment_lines = 0
        self.blank_lines = 0
        self.orphan_lines: list[tuple[str, int, str]] = []
        self.unknown_types: dict[str, int] = {}

    def as_dict(self) -> dict:
        return {
            "files": self.files,
            "records": self.records,
            "comment_lines": self.comment_lines,
            "blank_lines": self.blank_lines,
            "orphan_line_count": len(self.orphan_lines),
            "orphan_line_samples": [
                {"file": f, "line": n, "text": t} for f, n, t in self.orphan_lines[:20]
            ],
        }


def strip_comment(line: str) -> str:
    """去掉行内注释，但保护引号内的 `//`。"""
    in_quote = False
    for i, ch in enumerate(line):
        if ch == '"':
            in_quote = not in_quote
        elif not in_quote and line.startswith("//", i):
            return line[:i]
    return line


def tokenize(text: str) -> list[str]:
    """按引号规则切分，引号内容去除包裹引号。"""
    return [m.group(1) if m.group(1) is not None else m.group(2) for m in _RE_TOKEN.finditer(text)]


def parse_text(text: str, src: str = "<string>", stats: ParseStats | None = None) -> list[Record]:
    """解析单个文件的文本内容。"""
    records: list[Record] = []
    current: Record | None = None
    pending_field: str | None = None

    for lineno, raw_line in enumerate(text.splitlines(), start=1):
        line = strip_comment(raw_line).strip()
        if not line:
            if stats:
                stats.blank_lines += 1
            continue

        # 作者的笔误注释：`/------` 之类，无冒号、单斜杠开头
        if line.startswith("/") and ":" not in line:
            if stats:
                stats.comment_lines += 1
            continue

        m = _RE_RECORD.match(line)
        if m:
            # 新记录
            current = Record(type=m.group(1), src=src, line=lineno)
            records.append(current)
            pending_field = None
            rest = line[m.end():]
            _consume(rest, current, None)
            continue

        if line.startswith("."):
            if current is None:
                if stats:
                    stats.orphan_lines.append((src, lineno, line))
                continue
            pending_field = _consume(line, current, None)
            continue

        if current is None:
            if stats:
                stats.orphan_lines.append((src, lineno, line))
            continue

        # 既不是记录头也不是字段：视为上一字段的续值
        if pending_field:
            current.fields[pending_field].extend(tokenize(line))

    if stats:
        stats.files += 1
        stats.records += len(records)
        for r in records:
            stats.unknown_types[r.type] = stats.unknown_types.get(r.type, 0) + 1
    return records


def _consume(text: str, rec: Record, _unused) -> str | None:
    """把 `text` 里的 `.字段 值...` 序列吃进记录，返回最后一个字段名（供续行用）。"""
    tokens = tokenize(text)
    last_field: str | None = None
    for tok in tokens:
        m = _RE_FIELD.match(tok)
        if m:
            last_field = m.group(1)
            rec.fields.setdefault(last_field, [])
        elif last_field is not None:
            rec.fields[last_field].append(tok)
    return last_field


def parse_file(path: Path, stats: ParseStats | None = None, root: Path | None = None) -> list[Record]:
    """解析单个文件。`root` 用于把路径裁剪成相对路径，便于阅读。"""
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []
    src = str(path.relative_to(root)).replace("\\", "/") if root else path.name
    return parse_text(text, src=src, stats=stats)


def parse_files(paths, root: Path | None = None, stats: ParseStats | None = None) -> list[Record]:
    out: list[Record] = []
    for p in paths:
        out.extend(parse_file(Path(p), stats=stats, root=root))
    return out


def find_darkest_files(root: Path, exclude_dirs: tuple[str, ...] = ()) -> list[Path]:
    """收集所有 .darkest 文件，可排除指定子串目录（如 dlc/arena）。"""
    files = []
    for p in root.rglob("*.darkest"):
        rel = str(p.relative_to(root)).replace("\\", "/")
        if any(x in rel for x in exclude_dirs):
            continue
        files.append(p)
    return sorted(files)


# ---------------------------------------------------------------- 值类型转换

def to_number(tok: str):
    """把裸 token 转成数字：百分数 -> 小数比例，整数 -> int，其余 -> float 或原样返回。"""
    m = _RE_PCT.match(tok)
    if m:
        return round(float(m.group(1)) / 100.0, 6)
    if _RE_INT.match(tok):
        return int(tok)
    if _RE_FLOAT.match(tok):
        return float(tok)
    return tok


def to_bool(tok: str):
    low = str(tok).strip().lower()
    if low in ("true", "false"):
        return low == "true"
    return None


def typed(rec: Record, key: str, default=None):
    """取字段并做类型转换。多值时返回 list，单值返回标量。"""
    vals = rec.fields.get(key)
    if not vals:
        return default
    conv = []
    for v in vals:
        b = to_bool(v)
        if b is not None:
            conv.append(b)
        else:
            conv.append(to_number(v))
    return conv[0] if len(conv) == 1 else conv


def typed_list(rec: Record, key: str) -> list:
    vals = rec.fields.get(key) or []
    out = []
    for v in vals:
        b = to_bool(v)
        out.append(b if b is not None else to_number(v))
    return out


def mask(tok) -> str:
    """站位掩码统一成字符串（`.target 12` 会被转成 int 12，这里还原）。"""
    if tok is None:
        return ""
    return str(tok)


def dump_records(records: list[Record], keep_empty: bool = False) -> list[dict]:
    """记录列表转可 JSON 序列化的字典列表。"""
    out = []
    for r in records:
        d = {"_type": r.type, "_src": r.src, "_line": r.line}
        for k, v in r.fields.items():
            if not v and not keep_empty:
                continue
            conv = []
            for item in v:
                b = to_bool(item)
                conv.append(b if b is not None else to_number(item))
            d[k] = conv[0] if len(conv) == 1 else conv
        out.append(d)
    return out

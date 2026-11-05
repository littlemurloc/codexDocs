# -*- coding: utf-8 -*-
"""hrm_vm.gd 的 Python 复刻 —— 只为设计新关卡时能秒级试错。

它不参与游戏运行，也不该被当成第二份真理：
真正的判据永远是 tests/test_levels.gd（跑的是真 VM）。
这个脚本的价值是「写关卡时先在终端里跑通」，改完仍然要让 Godot 再验一遍。

用法：python tools/vm_py.py            # 校验 data/levels.json 里所有关
"""

MEM_OPS = ["COPYFROM", "MOVETO", "ADD", "SUB", "BUMPUP", "BUMPDN"]
JUMP_OPS = ["JUMP", "JUMPZ", "JUMPN"]
ARG_OPS = MEM_OPS + JUMP_OPS


class VM:
    def __init__(self, level, lines, free=False):
        self.free = free
        self.prog = parse(lines)
        ms = int(level.get("mem_size", 8))
        self.mem = [0] * ms
        for i, v in enumerate(level.get("mem_init", [])):
            if i < ms:
                self.mem[i] = int(v)
        self.inbox = [int(v) for v in level.get("inbox", [])]
        self.expected = [int(v) for v in level.get("outbox", [])]
        self.outbox = []
        self.hand = 0
        self.full = False
        self.pc = 0
        self.cycles = 0
        self.finished = False
        self.failed = False
        self.msg = ""
        self.max_open = 0

    def label_at(self, name):
        # 重复标签取最后一次（和 VM 一致）
        found = -1
        for i, ins in enumerate(self.prog):
            if ins.get("label") == name:
                found = i
        return found

    def complete(self):
        # free 模式（设计关卡时用）不按 outbox 判定，只靠「程序走到底」结束：
        # 否则读完最后一个数就停下，尾部那些汇总输出永远跑不到。
        if self.free:
            return False
        return len(self.outbox) == len(self.expected) and not self.inbox

    def run(self, limit=200000):
        for _ in range(limit):
            if self.finished or self.failed:
                break
            if not self.step():
                break
        else:
            self.failed = True
            self.msg = "疑似死循环"
        return self.finished

    def step(self):
        if self.finished or self.failed:
            return False
        if not self.prog:
            self.fail("程序是空的")
            return False
        while True:
            if self.pc < 0 or self.pc >= len(self.prog):
                if self.free or self.complete():
                    self.finished = True
                else:
                    self.fail("程序走到底了，可羊还没数完")
                return False
            if self.prog[self.pc]["op"] == "COMMENT":
                self.pc += 1
                continue
            break

        ins = self.prog[self.pc]
        op = ins["op"]
        arg = ins.get("arg")
        self.pc += 1
        self.cycles += 1

        if op == "INBOX":
            if self.full:
                return self.fail("INBOX 要求手空")
            if not self.inbox:
                if self.free:
                    self.finished = True
                    return False
                return self.fail("羊圈空了")
            self.hand = self.inbox.pop(0)
            self.full = True
        elif op == "OUTBOX":
            if not self.full:
                return self.fail("OUTBOX 要求手非空")
            if not self.free:
                if len(self.outbox) >= len(self.expected):
                    return self.fail("输出多了")
                want = self.expected[len(self.outbox)]
                if self.hand != want:
                    return self.fail("第 %d 个应为 %d，实际 %d"
                                     % (len(self.outbox) + 1, want, self.hand))
            self.outbox.append(self.hand)
            self.full = False
        elif op == "COPYFROM":
            if not self.valid(arg, op):
                return False
            if self.full:
                return self.fail("COPYFROM 要求手空")
            self.hand = self.mem[arg]
            self.full = True
        elif op == "MOVETO":
            if not self.valid(arg, op):
                return False
            if not self.full:
                return self.fail("MOVETO 要求手非空")
            self.mem[arg] = self.hand
            self.full = False
        elif op == "ADD":
            if not self.valid(arg, op):
                return False
            if not self.full:
                return self.fail("ADD 要求手非空")
            self.hand += self.mem[arg]
        elif op == "SUB":
            if not self.valid(arg, op):
                return False
            if not self.full:
                return self.fail("SUB 要求手非空")
            self.hand -= self.mem[arg]
        elif op == "BUMPUP":
            if not self.valid(arg, op):
                return False
            if self.full:
                return self.fail("BUMPUP 要求手空")
            self.mem[arg] += 1
            self.hand = self.mem[arg]
            self.full = True
        elif op == "BUMPDN":
            if not self.valid(arg, op):
                return False
            if self.full:
                return self.fail("BUMPDN 要求手空")
            self.mem[arg] -= 1
            self.hand = self.mem[arg]
            self.full = True
        elif op == "JUMP":
            t = self.label_at(arg)
            if t < 0:
                return self.fail("找不到标签 %s" % arg)
            self.pc = t
        elif op == "JUMPZ":
            if not self.full:
                return self.fail("JUMPZ 要求手非空")
            if self.hand == 0:
                t = self.label_at(arg)
                if t < 0:
                    return self.fail("找不到标签 %s" % arg)
                self.pc = t
        elif op == "JUMPN":
            if not self.full:
                return self.fail("JUMPN 要求手非空")
            if self.hand < 0:
                t = self.label_at(arg)
                if t < 0:
                    return self.fail("找不到标签 %s" % arg)
                self.pc = t
        else:
            return self.fail("未知指令 " + op)

        if not self.free and self.complete():
            self.finished = True
        return True

    def valid(self, arg, op):
        if arg is None:
            return self.fail("%s 缺参数" % op)
        if arg < 0 or arg >= len(self.mem):
            return self.fail("%s 越界" % op)
        return True

    def fail(self, msg):
        self.failed = True
        self.msg = msg
        return False


def parse(lines):
    out = []
    for raw in lines:
        s = str(raw).strip()
        if not s:
            continue
        label = ""
        if ":" in s:
            head, rest = s.split(":", 1)
            if " " not in head.strip():
                label = head.strip()
                s = rest.strip()
        if not s:
            out.append({"op": "COMMENT", "arg": None, "label": label})
            continue
        toks = s.split()
        op = toks[0].upper()
        arg = None
        if len(toks) > 1:
            arg = toks[1] if op in JUMP_OPS else int(toks[1])
        out.append({"op": op, "arg": arg, "label": label})
    return out


def program_size(prog):
    return sum(1 for ins in prog if ins["op"] != "COMMENT")


def links(prog):
    at = {}
    for i, ins in enumerate(prog):
        if ins.get("label"):
            at[ins["label"]] = i
    out = []
    for i, ins in enumerate(prog):
        if ins["op"] not in JUMP_OPS:
            continue
        t = ins.get("arg")
        if t in at and at[t] != i:
            out.append((i, at[t]))
    return out


def max_nest(prog):
    """同时在「开着」的跳转区间数 = 玩家心里的嵌套层数"""
    spans = sorted([(min(a, b), max(a, b)) for a, b in links(prog)])
    best = 0
    for i, (s, e) in enumerate(spans):
        depth = 1
        for j, (s2, e2) in enumerate(spans):
            if i == j:
                continue
            if s2 <= s and e <= e2 and (s2 < s or e < e2):
                depth += 1
        best = max(best, depth)
    return best


def score_plain(level, prog):
    """不含「新概念」项的纯解题难度：工作量 + 状态量 + 控制流嵌套 + 可选空间。

    排序 21 关往后只用这一项 —— 那一段里所有指令都已经出现过，novel 恒为 0。
    """
    ops = set(i["op"] for i in prog if i["op"] != "COMMENT")
    return (program_size(prog) * 1.0
            + len(level.get("allowed", [])) * 1.5
            + int(level.get("mem_size", 0)) * 2.0
            + max_nest(prog) * 4.0)


def score(level, prog, seen_ops):
    """难度分：工作量 + 可选空间 + 状态量 + 控制流嵌套 + 新概念

    刻意让「复刻关」拿不到分：novel=0 的关只能靠 size 堆，堆不过真正的新概念关。
    """
    ops = set(i["op"] for i in prog if i["op"] != "COMMENT")
    novel = len(ops - seen_ops)
    size = program_size(prog)
    return (size * 1.0
            + len(level.get("allowed", [])) * 1.5
            + int(level.get("mem_size", 0)) * 2.0
            + max_nest(prog) * 4.0
            + novel * 6.0)


def main():
    import io
    import json
    import sys
    path = "data/levels.json"
    if len(sys.argv) > 1 and not sys.argv[1].startswith("--"):
        path = sys.argv[1]
    levels = json.load(io.open(path, encoding="utf-8"))
    seen = set()
    fails = 0
    as_json = "--json" in sys.argv
    bag = []
    if "--json" not in sys.argv:
        print("%-4s %-22s %5s %5s %4s %4s %5s %6s" %
              ("id", "name", "size", "speed", "ops", "mem", "nest", "score"))
    prev = None
    for lv in levels:
        prog = parse(lv.get("ref", []))
        vm = VM(lv, lv.get("ref", []))
        ok = vm.run()
        ops = set(i["op"] for i in prog if i["op"] != "COMMENT")
        bad = ops - set(lv.get("allowed", []))
        sp = vm.cycles / max(1, len(lv.get("outbox", [])))
        sc = score(lv, prog, seen)
        seen |= ops
        flag = ""
        if not ok:
            flag = "  FAIL " + vm.msg
            fails += 1
        if bad:
            flag += "  未开放:" + ",".join(sorted(bad))
            fails += 1
        if prev is not None and int(lv["id"]) > 20 and sc < prev:
            flag += "  ↓回落"
        prev = sc
        bag.append({"id": lv["id"], "name": lv.get("name", ""),
                    "size": program_size(prog), "nest": max_nest(prog),
                    "mem": lv.get("mem_size", 0), "score": sc})
        if not as_json:
            print("%-4d %-22s %5d %5.2f %4d %4d %5d %6.1f%s" %
                  (lv["id"], lv.get("name", ""), program_size(prog), sp,
                   len(ops), lv.get("mem_size", 0), max_nest(prog), sc, flag))
    if as_json:
        print(json.dumps(bag))
        return 0
    print("\n%d 关，%d 处失败" % (len(levels), fails))
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main())

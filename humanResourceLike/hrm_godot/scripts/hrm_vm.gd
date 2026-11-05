extends RefCounted

const I18n = preload("res://scripts/i18n.gd")
## HRM 风格虚拟机：手（寄存器）+ 地板（内存）+ 收件箱/发件箱 + 跳转标签。
## 语义完全按《Human Resource Machine》的 11 条指令 + COMMENT 复刻。

const MEM_OPS: Array = ["COPYFROM", "MOVETO", "ADD", "SUB", "BUMPUP", "BUMPDN"]
const JUMP_OPS: Array = ["JUMP", "JUMPZ", "JUMPN"]
const ARG_OPS: Array = ["COPYFROM", "MOVETO", "ADD", "SUB", "BUMPUP", "BUMPDN", "JUMP", "JUMPZ", "JUMPN"]
const ALL_OPS: Array = ["INBOX", "OUTBOX", "COPYFROM", "MOVETO", "ADD", "SUB", "BUMPUP", "BUMPDN", "JUMP", "JUMPZ", "JUMPN", "COMMENT"]

## 指令牌上的一行白话（挂在指令名下面，玩家不用猜英文缩写）
const OP_SHORT: Dictionary = {
	"INBOX": "取一只",
	"OUTBOX": "送出",
	"COPYFROM": "读木牌",
	"MOVETO": "搬进木牌 · 手变空",
	"ADD": "加上木牌",
	"SUB": "减去木牌",
	"BUMPUP": "木牌 +1",
	"BUMPDN": "木牌 -1",
	"JUMP": "跳到标签",
	"JUMPZ": "是 0 就跳（比较）",
	"JUMPN": "是负数就跳（比较）",
	"COMMENT": "注释，不执行",
}

## 程序行右侧用的极短标签：一行要挤下序号/标签/指令/参数，只能给几个字
const OP_TAG: Dictionary = {
	"INBOX": "取一只",
	"OUTBOX": "送出",
	"COPYFROM": "读木牌",
	"MOVETO": "搬进木牌",
	"ADD": "加",
	"SUB": "减",
	"BUMPUP": "+1",
	"BUMPDN": "-1",
	"JUMP": "跳",
	"JUMPZ": "是0就跳",
	"JUMPN": "是负就跳",
	"COMMENT": "注释",
}

## 悬停时给出的完整解释：做什么、手会不会空、能不能当比较用
const OP_HELP: Dictionary = {
	"INBOX": "从羊圈牵一只到手上。手上有东西时再 INBOX 会报错。",
	"OUTBOX": "把手上这只送到栅栏外的羊圈，手随之清空。送错一只，整关就废。",
	"COPYFROM": "把木牌 N 上的数抄到手上 —— 这一步才是真正的「复制」：木牌里那份抄完还在。手要先是空的。",
	"MOVETO": "把手上的数搬进木牌 N —— 是 move，不是 copy：搬完手上就空了，木牌里那份是唯一的一份（也不是「粘贴」，粘贴完剪贴板里还留着一份）。写进一块用不着的木牌，等于把手里这只扔掉。",
	"ADD": "手上 += 木牌 N，结果留在手上（木牌不变）。手不会空。",
	"SUB": "手上 -= 木牌 N，结果留在手上，可以是负数。手不会空。",
	"BUMPUP": "木牌 N 自己 +1，新值同时拿到手上。",
	"BUMPDN": "木牌 N 自己 -1，新值同时拿到手上。",
	"JUMP": "无条件跳到标签处。",
	"JUMPZ": "这游戏没有单独的「比较」牌 —— 比较就长在条件跳转里：看一眼手上的数，等于 0 就跳到标签，否则往下走。手上的值不会被吃掉。",
	"JUMPN": "同样是比较，只是条件换成「小于 0」：看一眼手上的数，是负数就跳到标签，否则往下走。手上的值不会被吃掉。",
	"COMMENT": "只写给人看的注释，不执行，也不算进 SIZE。",
}

var program: Array = []
var mem: Array = []
var inbox: Array = []
var outbox: Array = []
var expected: Array = []

var hand: int = 0
var hand_full: bool = false
var pc: int = 0
var cycles: int = 0
var finished: bool = false
var failed: bool = false
var message: String = ""
var last_op: String = ""
var last_arg: Variant = null
## 刚执行完的指令下标（-1 = 还没跑过），UI 用它做"当前行"高亮
var last_pc: int = -1
## 出错时定格在那一行（-1 = 没出错），UI 用它标红
var fail_pc: int = -1


# ---------------------------------------------------------------- 工具函数

## 旧名字 → 新名字。第六版把 COPYTO 改名 MOVETO（它不是 copy，是搬运），
## 但玩家存档里的程序、老关卡数据里都还写着 COPYTO，所以入口处统一收敛一次。
const OP_ALIAS: Dictionary = {
	"COPYTO": "MOVETO",
}

static func canon_op(op: String) -> String:
	var u: String = op.to_upper()
	return String(OP_ALIAS.get(u, u))


## 把 ["a:INBOX", "MOVETO 0", ...] 解析成 [{op, arg, label}]
static func parse_program(lines: Array) -> Array:
	var prog: Array = []
	for raw in lines:
		var s: String = str(raw).strip_edges()
		if s == "":
			continue
		var label: String = ""
		if s.contains(":"):
			var parts: PackedStringArray = s.split(":", true, 1)
			label = parts[0].strip_edges()
			s = parts[1].strip_edges()
		var toks: PackedStringArray = s.split(" ", false)
		if toks.size() == 0:
			continue
		var op: String = canon_op(String(toks[0]))
		var arg: Variant = null
		if toks.size() > 1:
			if JUMP_OPS.has(op):
				arg = String(toks[1])
			elif MEM_OPS.has(op):
				arg = int(toks[1])
			else:
				arg = String(toks[1])
		prog.append({"op": op, "arg": arg, "label": label})
	return prog


## 程序尺寸 = 非 COMMENT 指令条数（原版同样是注释不计入）
static func program_size(prog: Array) -> int:
	var n: int = 0
	for ins in prog:
		if ins.get("op", "") != "COMMENT":
			n += 1
	return n


static func make_ins(op: String, arg: Variant = null) -> Dictionary:
	return {"op": canon_op(op), "arg": arg, "label": ""}


## 指令名下面那行白话；没写过的指令就返回空串
static func op_short(op: String) -> String:
	return I18n.t(String(OP_SHORT.get(op, "")))


## 程序行右侧的极短标签
static func op_tag(op: String) -> String:
	return I18n.t(String(OP_TAG.get(op, "")))


## 悬停解释；没写过就退回白话
static func op_help(op: String) -> String:
	return I18n.t(String(OP_HELP.get(op, OP_SHORT.get(op, ""))))


# ---------------------------------------------------------------- 运行

func setup(level: Dictionary, prog: Array) -> void:
	program = prog
	mem = []
	var ms: int = int(level.get("mem_size", 8))
	for _i in ms:
		mem.append(0)
	var init: Array = level.get("mem_init", [])
	for i in init.size():
		if i < ms:
			mem[i] = int(init[i])
	inbox = []
	for v in level.get("inbox", []):
		inbox.append(int(v))
	expected = []
	for v in level.get("outbox", []):
		expected.append(int(v))
	outbox = []
	hand = 0
	hand_full = false
	pc = 0
	cycles = 0
	finished = false
	failed = false
	message = ""
	last_op = ""
	last_pc = -1
	fail_pc = -1


func item_count() -> int:
	return expected.size()


func speed() -> float:
	if item_count() == 0:
		return 0.0
	return float(cycles) / float(item_count())


func step() -> bool:
	if finished or failed:
		return false
	if program.is_empty():
		_fail(I18n.t("还没给牧羊人下指令（程序是空的）"))
		return false

	# 跳过 COMMENT（不消耗周期）
	var guard: int = 0
	while true:
		guard += 1
		if guard > 1000:
			_fail(I18n.t("程序里只有注释，什么也没发生"))
			return false
		if pc < 0 or pc >= program.size():
			if _is_complete():
				finished = true
			else:
				_fail(I18n.t("程序走到底了，可羊还没数完"))
			return false
		var ins0: Dictionary = program[pc]
		if String(ins0.get("op", "")) == "COMMENT":
			pc += 1
			continue
		break

	var ins: Dictionary = program[pc]
	# 老存档里的 COPYTO 在这里被收敛成 MOVETO —— 执行侧永远只认新名字
	var op: String = canon_op(String(ins.get("op", "")))
	var arg: Variant = ins.get("arg", null)
	last_pc = pc
	pc += 1
	cycles += 1
	last_op = op
	last_arg = arg

	match op:
		"INBOX":
			if hand_full:
				_fail(I18n.t("怀里还抱着一只羊，腾不出手去羊圈牵（INBOX 要求手空）"))
				return false
			if inbox.is_empty():
				_fail(I18n.t("羊圈已经空了（INBOX 没有数据了）"))
				return false
			hand = int(inbox.pop_front())
			hand_full = true

		"OUTBOX":
			if not hand_full:
				_fail(I18n.t("怀里空着，没有羊可以推过栅栏（OUTBOX 要求手非空）"))
				return false
			if outbox.size() >= expected.size():
				_fail(I18n.tf("推过去的羊多了：这关不需要编号 %d", [hand]))
				return false
			var want: int = int(expected[outbox.size()])
			if hand != want:
				_fail(I18n.tf("第 %d 只羊的编号应该是 %d，你推过去的是 %d", [outbox.size() + 1, want, hand]))
				return false
			outbox.append(hand)
			hand_full = false

		"COPYFROM":
			if not _valid_mem(arg, op):
				return false
			if hand_full:
				_fail(I18n.t("怀里还抱着羊，捡不了木牌（COPYFROM 要求手空）"))
				return false
			hand = int(mem[int(arg)])
			hand_full = true

		"MOVETO":
			if not _valid_mem(arg, op):
				return false
			if not hand_full:
				_fail(I18n.t("怀里空着，没东西可以记到木牌上（MOVETO 要求手非空）"))
				return false
			mem[int(arg)] = hand
			hand_full = false

		"ADD":
			if not _valid_mem(arg, op):
				return false
			if not hand_full:
				_fail(I18n.t("怀里空着，加不了（ADD 要求手非空）"))
				return false
			hand = hand + int(mem[int(arg)])

		"SUB":
			if not _valid_mem(arg, op):
				return false
			if not hand_full:
				_fail(I18n.t("怀里空着，减不了（SUB 要求手非空）"))
				return false
			hand = hand - int(mem[int(arg)])

		"BUMPUP":
			if not _valid_mem(arg, op):
				return false
			if hand_full:
				_fail(I18n.t("怀里还抱着羊，动不了木牌（BUMPUP 要求手空）"))
				return false
			mem[int(arg)] = int(mem[int(arg)]) + 1
			hand = int(mem[int(arg)])
			hand_full = true

		"BUMPDN":
			if not _valid_mem(arg, op):
				return false
			if hand_full:
				_fail(I18n.t("怀里还抱着羊，动不了木牌（BUMPDN 要求手空）"))
				return false
			mem[int(arg)] = int(mem[int(arg)]) - 1
			hand = int(mem[int(arg)])
			hand_full = true

		"JUMP":
			var t: int = _find_label(arg)
			if t < 0:
				return false
			pc = t

		"JUMPZ":
			if not hand_full:
				_fail(I18n.t("怀里空着，没有数值可以判断（JUMPZ 要求手非空）"))
				return false
			if hand == 0:
				var t: int = _find_label(arg)
				if t < 0:
					return false
				pc = t

		"JUMPN":
			if not hand_full:
				_fail(I18n.t("怀里空着，没有数值可以判断（JUMPN 要求手非空）"))
				return false
			if hand < 0:
				var t: int = _find_label(arg)
				if t < 0:
					return false
				pc = t

		_:
			_fail(I18n.tf("未知指令：%s", [op]))
			return false

	if _is_complete():
		finished = true
	return true


func run(max_steps: int = 200000) -> bool:
	var n: int = 0
	while not finished and not failed:
		if n >= max_steps:
			_fail(I18n.tf("疑似死循环（超过 %d 步）", [max_steps]))
			break
		n += 1
		if not step():
			break
	return finished


# ---------------------------------------------------------------- 内部

func _is_complete() -> bool:
	return outbox.size() == expected.size() and inbox.is_empty()


func _fail(msg: String) -> void:
	failed = true
	message = msg
	if fail_pc < 0:
		fail_pc = last_pc if last_pc >= 0 else 0


func _valid_mem(arg: Variant, op: String) -> bool:
	if arg == null:
		_fail(I18n.tf("%s 后面得填一个木牌编号", [op]))
		return false
	var i: int = int(arg)
	if i < 0 or i >= mem.size():
		_fail(I18n.tf("%s 的木牌编号 %d 越界（这关只有 %d 块木牌）", [op, i, mem.size()]))
		return false
	return true


func _find_label(arg: Variant) -> int:
	for i in program.size():
		if String(program[i].get("label", "")) == String(arg):
			return i
	_fail(I18n.tf("找不到标签 %s（第 1~4 行右侧可以设置 a/b/c/d）", [str(arg)]))
	return -1

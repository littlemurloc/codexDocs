extends SceneTree
## 无头回归测试：godot --headless --path . --script res://tests/test_levels.gd

const VM_PATH := "res://scripts/hrm_vm.gd"
const LEVELS_PATH := "res://data/levels.json"

var fails: int = 0
var checks: int = 0


func _init() -> void:
	var VM = load(VM_PATH)
	var levels: Array = _load_json(LEVELS_PATH)

	print("=== 关卡参考解校验（共 %d 关） ===" % levels.size())
	for lv in levels:
		var prog: Array = VM.parse_program(lv.get("ref", []))
		var vm = VM.new()
		vm.setup(lv, prog)
		var ok: bool = vm.run()
		var size: int = VM.program_size(prog)
		var line: String = "#%02d %-28s size=%-3d speed=%.2f  cycles=%-3d" % [
			int(lv.get("id", 0)), String(lv.get("name", "")), size, vm.speed(), vm.cycles
		]
		if ok:
			print("PASS  " + line)
		else:
			print("FAIL  " + line + "  -> " + vm.message)
			fails += 1
		checks += 1

		# 数据自检：参考解只能使用本关允许的指令
		var allowed: Array = lv.get("allowed", [])
		for ins in prog:
			var op: String = String(ins.get("op", ""))
			if op == "COMMENT":
				continue
			if not allowed.has(op):
				print("FAIL  关卡 #%d 的参考解用了未开放的指令 %s" % [int(lv.get("id", 0)), op])
				fails += 1
		checks += 1

		# 越界自检：内存编号不能超过 mem_size
		for ins in prog:
			var op2: String = String(ins.get("op", ""))
			if VM.MEM_OPS.has(op2) and ins.get("arg", null) != null:
				if int(ins["arg"]) >= int(lv.get("mem_size", 0)):
					print("FAIL  关卡 #%d 的 %s %d 超出 mem_size" % [int(lv.get("id", 0)), op2, int(ins["arg"])])
					fails += 1
		checks += 1

	print("\n=== 负向用例 ===")
	_test_negative(VM, levels)

	print("\n=== 结果：%d 项检查，%d 项失败 ===" % [checks, fails])
	quit(1 if fails > 0 else 0)


func _test_negative(VM, levels: Array) -> void:
	var lv: Dictionary = levels[0]

	# 1. 少一个 OUTBOX 就不该过关
	var prog: Array = VM.parse_program(["INBOX", "OUTBOX", "INBOX"])
	var vm = VM.new()
	vm.setup(lv, prog)
	_expect(vm.run() == false, "不完整的程序不应过关")

	# 2. 手是空的时候 OUTBOX 应报错
	prog = VM.parse_program(["OUTBOX"])
	vm = VM.new()
	vm.setup(lv, prog)
	vm.run()
	_expect(vm.failed and vm.message.contains("空"), "空手 OUTBOX 应失败：%s" % vm.message)

	# 3. 地板编号越界应报错
	prog = VM.parse_program(["INBOX", "MOVETO 9"])
	vm = VM.new()
	vm.setup(lv, prog)
	vm.run()
	_expect(vm.failed and vm.message.contains("越界"), "越界内存应失败：%s" % vm.message)

	# 4. 输出顺序错误应失败
	prog = VM.parse_program(["INBOX", "MOVETO 0", "INBOX", "OUTBOX", "COPYFROM 0", "OUTBOX",
		"INBOX", "MOVETO 0", "INBOX", "COPYFROM 0", "OUTBOX", "INBOX", "OUTBOX"])
	vm = VM.new()
	vm.setup({"inbox": [1, 2, 3, 4], "outbox": [1, 2, 3, 4], "mem_size": 1}, prog)
	vm.run()
	_expect(vm.failed, "顺序错误应被判错")


func _expect(cond: bool, msg: String) -> void:
	checks += 1
	if cond:
		print("PASS  " + msg)
	else:
		print("FAIL  " + msg)
		fails += 1


func _load_json(path: String) -> Array:
	var f: FileAccess = FileAccess.open(path, FileAccess.READ)
	if f == null:
		print("无法打开 " + path)
		return []
	var txt: String = f.get_as_text()
	var data: Variant = JSON.parse_string(txt)
	if data == null or typeof(data) != TYPE_ARRAY:
		print("JSON 解析失败：" + path)
		return []
	return data

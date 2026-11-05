extends SceneTree
## 设计验证：把"想做的关卡方向"先在 VM 里跑通，确认这套 11 指令语义撑得住。
## 跑法：godot --headless --path . --script res://tests/test_ideas.gd
## 说明：这里只是设计探针，不进正式关卡表；验证通过后再搬进 data/levels.json。

const VM_PATH := "res://scripts/hrm_vm.gd"

var fails: int = 0


func _init() -> void:
	var VM = load(VM_PATH)
	var ideas: Array = [
		{
			"name": "过滤 · 只留正数（丢弃要付 MOVETO 的代价）",
			"mem_size": 2, "mem_init": [0, 0],
			"inbox": [3, -1, 4, -2, 5], "outbox": [3, 4, 5],
			"allowed": ["INBOX", "OUTBOX", "MOVETO", "JUMP", "JUMPN"],
			"ref": ["a:INBOX", "JUMPN b", "OUTBOX", "JUMP a", "b:MOVETO 0", "JUMP a"],
		},
		{
			"name": "压缩 · 连续去重（必须先清手才能捡值）",
			"mem_size": 3, "mem_init": [-999, 0, 0],
			"inbox": [1, 1, 2, 2, 3], "outbox": [1, 2, 3],
			"allowed": ["INBOX", "OUTBOX", "COPYFROM", "MOVETO", "SUB", "JUMP", "JUMPZ"],
			"ref": ["a:INBOX", "MOVETO 1", "COPYFROM 0", "SUB 1", "JUMPZ b",
					"MOVETO 2", "COPYFROM 1", "OUTBOX", "COPYFROM 1", "MOVETO 0", "JUMP a",
					"b:MOVETO 2", "JUMP a"],
		},
		{
			"name": "展开 · n 变 n 个 1（输出比输入多）",
			"mem_size": 3, "mem_init": [0, 1, 0],
			"inbox": [3, 2], "outbox": [1, 1, 1, 1, 1],
			"allowed": ["INBOX", "OUTBOX", "COPYFROM", "MOVETO", "BUMPDN", "JUMP", "JUMPZ"],
			"ref": ["a:INBOX", "MOVETO 0", "b:COPYFROM 1", "OUTBOX", "BUMPDN 0",
					"JUMPZ c", "MOVETO 2", "JUMP b", "c:MOVETO 2", "JUMP a"],
		},
		{
			"name": "滑窗 · 相邻两数求和（输出比输入少一个）",
			"mem_size": 2, "mem_init": [0, 0],
			"inbox": [1, 2, 3, 4], "outbox": [3, 5, 7],
			"allowed": ["INBOX", "OUTBOX", "COPYFROM", "MOVETO", "ADD", "JUMP"],
			"ref": ["a:INBOX", "MOVETO 0", "b:INBOX", "MOVETO 1",
					"COPYFROM 0", "ADD 1", "OUTBOX", "COPYFROM 1", "MOVETO 0", "JUMP b"],
		},
	]

	for lv in ideas:
		var prog: Array = VM.parse_program(lv.get("ref", []))
		var vm = VM.new()
		vm.setup(lv, prog)
		var ok: bool = vm.run()
		var size: int = VM.program_size(prog)
		if ok:
			print("PASS  %-40s size=%-3d cycles=%-4d speed=%.2f" % [
				String(lv["name"]), size, vm.cycles, vm.speed()])
		else:
			print("FAIL  %-40s -> %s" % [String(lv["name"]), vm.message])
			fails += 1

	# 关键约束验证：跑到 INBOX 已空时会怎样（决定"哨兵值提前终止"能不能做）
	print("\n=== 语义边界探针 ===")
	var probe: Dictionary = {
		"name": "哨兵关（0 在中间，后面还有数据要忽略）",
		"mem_size": 2, "mem_init": [],
		"inbox": [3, 0, 9], "outbox": [3],
		"ref": ["a:INBOX", "JUMPZ z", "OUTBOX", "JUMP a", "z:MOVETO 0"],
	}
	var pvm = VM.new()
	pvm.setup(probe, VM.parse_program(probe["ref"]))
	var pok: bool = pvm.run()
	print("哨兵提前终止 -> %s  |  %s" % ["可完成" if pok else "失败", pvm.message])
	print("（若为失败，说明 _is_complete 要求 inbox 必须读空，'读到哨兵就收工'这类关卡得先改引擎）")

	print("\n=== 结果：%d 项验证，%d 项失败 ===" % [ideas.size() + 1, fails])
	quit(1 if fails > 0 else 0)

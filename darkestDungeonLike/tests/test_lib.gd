class_name TestLib
extends RefCounted
## 极简断言库。不引入第三方框架，是因为这个项目的测试会持续被当作
## 「数值回归基准」使用，越少依赖越好。

var passed: int = 0
var failed: int = 0
var failures: Array = []
var _section: String = ""


func section(name: String) -> void:
	_section = name
	print("\n── %s ──" % name)


func ok(cond: bool, msg: String) -> bool:
	if cond:
		passed += 1
		return true
	failed += 1
	failures.append("[%s] %s" % [_section, msg])
	print("  FAIL  %s" % msg)
	return false


func eq(actual: Variant, expected: Variant, msg: String) -> bool:
	if actual == expected:
		passed += 1
		return true
	failed += 1
	failures.append("[%s] %s  期望=%s 实际=%s" % [_section, msg, str(expected), str(actual)])
	print("  FAIL  %s  期望=%s 实际=%s" % [msg, str(expected), str(actual)])
	return false


func near(actual: float, expected: float, eps: float, msg: String) -> bool:
	if absf(actual - expected) <= eps:
		passed += 1
		return true
	failed += 1
	failures.append("[%s] %s  期望≈%s 实际=%s" % [_section, msg, str(expected), str(actual)])
	print("  FAIL  %s  期望≈%s 实际=%s" % [msg, str(expected), str(actual)])
	return false


func between(value: float, lo: float, hi: float, msg: String) -> bool:
	return ok(value >= lo and value <= hi, "%s  实际=%s 区间[%s,%s]" % [msg, str(value), str(lo), str(hi)])


func summary() -> int:
	print("\n" + "=".repeat(52))
	if failed == 0:
		print("全部通过：%d 项断言" % passed)
		return 0
	print("失败 %d / 共 %d 项" % [failed, passed + failed])
	for f in failures:
		print("  · " + str(f))
	return 1

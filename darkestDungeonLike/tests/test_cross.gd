class_name TestCross
extends RefCounted
## 与 Python 参考实现的逐条对账。
##
## 这是整个测试体系里最有价值的一层：两份独立编写的实现，喂同一批输入
## （含同一串随机数），必须给出同一个 hit/crit/damage。
## 只要有一处系数写错、一处顺序颠倒、一处随机数转录错误，这里立刻红。

const FIXTURE: String = "res://tests/fixtures/cross_validation.json"


static func run(t: TestLib) -> void:
	t.section("交叉验证（GDScript vs Python）")
	var text: String = FileAccess.get_file_as_string(FIXTURE)
	var data: Variant = JSON.parse_string(text)
	if data == null:
		t.ok(false, "交叉验证用例解析失败")
		return

	var scenarios: Array = data.get("scenarios", [])
	t.ok(scenarios.size() > 0, "用例数 %d" % scenarios.size())

	var mismatches: Array = []
	var hit_count: int = 0
	var crit_count: int = 0
	var damage_total: float = 0.0

	for s in scenarios:
		var seed_value: int = int(s["seed"])
		var spec: Dictionary = s["spec"]
		var expected: Dictionary = s["expected"]

		var rng := DdRng.new(seed_value)
		var got: Dictionary = DamageFormula.resolve_attack(spec, rng)

		if bool(got["hit"]) != bool(expected["hit"]):
			mismatches.append("用例 %s 命中不一致：期望 %s 实际 %s" % [
				str(s["index"]), str(expected["hit"]), str(got["hit"])])
			continue
		if bool(got["crit"]) != bool(expected["crit"]):
			mismatches.append("用例 %s 暴击不一致" % str(s["index"]))
			continue
		if int(got["damage"]) != int(expected["damage"]):
			mismatches.append("用例 %s 伤害不一致：期望 %d 实际 %d" % [
				str(s["index"]), int(expected["damage"]), int(got["damage"])])
			continue
		if absf(float(got["raw"]) - float(expected["raw"])) > 1e-9:
			mismatches.append("用例 %s 原始伤害浮点不一致" % str(s["index"]))
			continue
		if absf(float(got["mult"]) - float(expected["mult"])) > 1e-9:
			mismatches.append("用例 %s 修正倍率不一致" % str(s["index"]))
			continue

		if bool(got["hit"]):
			hit_count += 1
			damage_total += float(got["damage"])
		if bool(got["crit"]):
			crit_count += 1

	t.eq(mismatches.size(), 0, "全部 %d 条用例与 Python 实现一致" % scenarios.size())
	for m in mismatches.slice(0, 8):
		print("    " + str(m))

	# 用例覆盖面自检：如果全是命中或全是不暴击，这组用例其实没测到分支
	t.ok(hit_count > 40, "命中分支样本充足（%d 条）" % hit_count)
	t.ok(hit_count < scenarios.size() - 5, "未命中分支也被覆盖（%d 条）" % (scenarios.size() - hit_count))
	t.ok(crit_count > 3, "暴击分支被覆盖（%d 条）" % crit_count)
	t.ok(damage_total > 0.0, "伤害总额为正")

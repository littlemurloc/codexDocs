class_name TestDamage
extends RefCounted
## 伤害/命中公式单测。
##
## 这里的基准值全部来自 DD1 的原始配置，不是我自己编的：
## 十字军 L0 武器 6-12、惩击命中 85%、暴击 3%、基础闪避 5%，
## 惩击 L0 的 effect「Unholy Killer 1」给 +15% 对邪物伤害。
## 所以「打邪物 = 7..14」这一条，是能拿游戏本体对照的硬断言。

const SEED_A: int = 20261102


static func run(t: TestLib) -> void:
	_hit_chance(t)
	_crit(t)
	_damage_range(t)
	_conditional_mods(t)
	_protection(t)
	_rng_determinism(t)


static func _hit_chance(t: TestLib) -> void:
	t.section("命中率")
	t.near(DamageFormula.hit_chance(0.85, 0.05), 0.80, 1e-9, "惩击 85% 命中 vs 5% 闪避 = 80%")
	t.near(DamageFormula.hit_chance(1.20, 0.0), 0.95, 1e-9, "命中上限固定 95%")
	t.near(DamageFormula.hit_chance(1.50, 0.0), 0.95, 1e-9, "再高也是 95%")
	t.near(DamageFormula.hit_chance(0.30, 0.40), 0.0, 1e-9, "命中可被压到 0，不设下限")
	t.near(DamageFormula.hit_chance(0.85, 0.05, 0.0, 1.0), 0.80, 1e-9, "覆盖上限参数生效")


static func _crit(t: TestLib) -> void:
	t.section("暴击")
	var rng := DdRng.new(SEED_A)
	var high: Dictionary = DamageFormula.resolve_attack({
		"base_low": 10, "base_high": 10, "acc": 1.0, "dodge": 0.0,
		"crit": 1.0, "crit_mult": 1.5, "crit_valid": true, "cutoff_hit": 1.0,
	}, rng)
	t.eq(high["hit"], true, "必中")
	t.eq(high["crit"], true, "暴击率 100% 必暴")
	t.eq(high["damage"], 15, "暴击 10 × 1.5 = 15")

	var rng2 := DdRng.new(SEED_A)
	var no_crit_valid: Dictionary = DamageFormula.resolve_attack({
		"base_low": 10, "base_high": 10, "acc": 1.0, "dodge": 0.0,
		"crit": 1.0, "crit_mult": 1.5, "crit_valid": false, "cutoff_hit": 1.0,
	}, rng2)
	t.eq(no_crit_valid["crit"], false, "技能标记不可暴击时，暴击率再高也不暴")
	t.eq(no_crit_valid["damage"], 10, "不可暴击则不乘倍率")


static func _damage_range(t: TestLib) -> void:
	t.section("基础伤害区间（十字军惩击 L0）")
	var seen: Dictionary = {}
	var rng := DdRng.new(SEED_A)
	for i in 3000:
		var r: Dictionary = DamageFormula.resolve_attack({
			"base_low": 6, "base_high": 12, "acc": 1.0, "dodge": 0.0,
			"crit": 0.0, "crit_valid": false, "cutoff_hit": 1.0,
		}, rng)
		seen[int(r["damage"])] = true
	t.eq(seen.size(), 7, "6-12 应恰好出现 7 种伤害值")
	t.eq(seen.has(6), true, "最小伤害 6 出现过")
	t.eq(seen.has(12), true, "最大伤害 12 出现过")
	t.eq(seen.has(5), false, "不应出现 5")


static func _conditional_mods(t: TestLib) -> void:
	t.section("条件伤害修正（加算）")
	# 对邪物 +15%：6*1.15=6.9→7，12*1.15=13.8→14
	var seen: Dictionary = {}
	var rng := DdRng.new(SEED_A + 1)
	for i in 4000:
		var r: Dictionary = DamageFormula.resolve_attack({
			"base_low": 6, "base_high": 12, "acc": 1.0, "dodge": 0.0,
			"crit": 0.0, "crit_valid": false, "mods": [0.15], "cutoff_hit": 1.0,
		}, rng)
		seen[int(r["damage"])] = true
	t.eq(seen.keys().min(), 7, "对邪物最低伤害 6→7")
	t.eq(seen.keys().max(), 14, "对邪物最高伤害 12→14")

	# 加算验证：+15% 与 +50% 同时生效应为 ×1.65，而不是 ×1.725
	var rng2 := DdRng.new(SEED_A + 2)
	var r: Dictionary = DamageFormula.resolve_attack({
		"base_low": 10, "base_high": 10, "acc": 1.0, "dodge": 0.0,
		"crit": 0.0, "crit_valid": false, "mods": [0.15, 0.5], "cutoff_hit": 1.0,
	}, rng2)
	t.near(float(r["mult"]), 1.65, 1e-9, "修正倍率应为加算 1.65（连乘会是 1.725）")
	t.eq(int(r["damage"]), 17, "10 × 1.65 = 16.5 → 17")

	# 用 20 点基础伤害才能把加算与连乘区分开：加算 33，连乘 34.5→35
	var rng3 := DdRng.new(SEED_A + 3)
	var r2: Dictionary = DamageFormula.resolve_attack({
		"base_low": 20, "base_high": 20, "acc": 1.0, "dodge": 0.0,
		"crit": 0.0, "crit_valid": false, "mods": [0.15, 0.5], "cutoff_hit": 1.0,
	}, rng3)
	t.eq(int(r2["damage"]), 33, "20 × 1.65 = 33（若误写成连乘会得 35）")


static func _protection(t: TestLib) -> void:
	t.section("防护与受伤修正")
	var rng := DdRng.new(SEED_A + 10)
	var r: Dictionary = DamageFormula.resolve_attack({
		"base_low": 10, "base_high": 10, "acc": 1.0, "dodge": 0.0,
		"crit": 0.0, "crit_valid": false, "prot": 0.2, "cutoff_hit": 1.0,
	}, rng)
	t.eq(int(r["damage"]), 8, "10 伤害 × (1-0.2) = 8")

	var rng2 := DdRng.new(SEED_A + 11)
	var r2: Dictionary = DamageFormula.resolve_attack({
		"base_low": 10, "base_high": 10, "acc": 1.0, "dodge": 0.0,
		"crit": 0.0, "crit_valid": false, "prot": 0.2, "ignore_prot": true, "cutoff_hit": 1.0,
	}, rng2)
	t.eq(int(r2["damage"]), 10, "无视防护时不吃减伤")

	var rng3 := DdRng.new(SEED_A + 12)
	var r3: Dictionary = DamageFormula.resolve_attack({
		"base_low": 10, "base_high": 10, "acc": 1.0, "dodge": 0.0,
		"crit": 0.0, "crit_valid": false, "dmg_taken_mod": 0.25, "cutoff_hit": 1.0,
	}, rng3)
	t.eq(int(r3["damage"]), 13, "受伤 +25%：10 × 1.25 = 12.5 → 13")

	# 全防护也不该出现 0 以下的负数
	var rng4 := DdRng.new(SEED_A + 13)
	var r4: Dictionary = DamageFormula.resolve_attack({
		"base_low": 5, "base_high": 5, "acc": 1.0, "dodge": 0.0,
		"crit": 0.0, "crit_valid": false, "prot": 0.99, "cutoff_hit": 1.0,
	}, rng4)
	t.ok(int(r4["damage"]) >= 0, "伤害永不为负")


static func _rng_determinism(t: TestLib) -> void:
	t.section("随机数确定性")
	var a := DdRng.new(12345)
	var b := DdRng.new(12345)
	var same: bool = true
	for i in 500:
		if a.next_u32() != b.next_u32():
			same = false
			break
	t.ok(same, "同种子 500 次抽样完全一致")

	var c := DdRng.new(12345)
	var d := DdRng.new(12346)
	var diff: bool = false
	for i in 20:
		if c.next_u32() != d.next_u32():
			diff = true
			break
	t.ok(diff, "不同种子序列不同")

	# 均匀性粗检：4 个桶各应有约 25%
	var e := DdRng.new(777)
	var buckets: Array = [0, 0, 0, 0]
	for i in 40000:
		buckets[e.next_int(4)] += 1
	for i in 4:
		var ratio: float = float(buckets[i]) / 40000.0
		t.between(ratio, 0.235, 0.265, "桶 %d 占比应接近 25%%" % i)

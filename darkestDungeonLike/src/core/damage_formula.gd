class_name DamageFormula
extends RefCounted
## 伤害与命中公式。全部是静态纯函数：给定输入必得同一输出，不碰节点、不碰状态。
##
## 公式来源：shared/rules.json + 英雄/怪物配置。运算顺序是项目里最需要
## 固定下来的一件事——顺序不同，结果就不同，而且不会报错，只会「手感不对」。
##
##   1. 命中判定   hit = clamp(ACC - DODGE, 0, 0.95)          （rules.cutoffAlwaysHit）
##   2. 暴击判定   crit = rng() < CRIT
##   3. 基础伤害   raw = lerp(dmg_low, dmg_high, rng())
##   4. 加成累加   mult = 1 + Σ(修正)   ← 加算，不是连乘
##   5. 暴击倍率   dmg = raw * mult * crit_mult
##   6. 减伤       dmg *= (1 - PROT) * (1 + 受伤加成)
##   7. 取整       floor(dmg + 0.5)
##
## 第 4 步用加算是从数据反推出来的：十字军「惩击」基础修正 0%，对邪物 +15%，
## 打邪物时应为 ×1.15 而非 ×1.0×1.15——两者数值相同，但当两个条件同时命中
## （如 +15% vs 邪物 与 +50% vs 标记）时，加算得 ×1.65、连乘得 ×1.725。
## DD1 的面板显示的正是加算结果。此结论标注为「高置信推断」，非源码确认。


## 命中率。DD1 的命中上限固定 95%，无下限（可以低到 0 甚至负数被夹到 0）。
static func hit_chance(acc: float, dodge: float, cutoff_miss: float = 0.0, cutoff_hit: float = 0.95) -> float:
	return clampf(acc - dodge, cutoff_miss, cutoff_hit)


## 暴击倍率表。表结构 [{chance, value}]，chance 为累积权重。
## DD1 当前只有一条 {1, 1.5}，写成查表是为了后续换自研数值时不用改代码。
static func pick_crit_mult(table: Array, rng: DdRng) -> float:
	if table.is_empty():
		return 1.5
	var roll: float = rng.next_float()
	var acc: float = 0.0
	for entry in table:
		acc += float(entry.get("chance", 0.0))
		if roll < acc:
			return float(entry.get("value", 1.5))
	return float(table[-1].get("value", 1.5))


## 一次攻击的完整结算。返回字典而非改状态，便于单测与回放。
##
## spec 字段：
##   base_low / base_high  float  基础伤害区间（英雄取武器，怪物取技能）
##   acc / dodge           float  命中与闪避（0-1）
##   crit                  float  暴击率（0-1）
##   crit_mult             float  暴击倍率
##   crit_valid            bool   该技能是否可暴击
##   prot                  float  目标防护（0-1）
##   mods                  Array  伤害修正，加算
##   dmg_mult_buffs        float  持久伤害倍率（相乘）
##   dmg_taken_mod         float  目标受伤加成（如 +25% 则传 0.25）
##   ignore_prot           bool
##   cutoff_hit / cutoff_miss  float  可选，覆盖规则
static func resolve_attack(spec: Dictionary, rng: DdRng) -> Dictionary:
	var acc: float = float(spec.get("acc", 0.85))
	var dodge: float = float(spec.get("dodge", 0.0))
	var cutoff_hit: float = float(spec.get("cutoff_hit", 0.95))
	var cutoff_miss: float = float(spec.get("cutoff_miss", 0.0))

	var chance: float = hit_chance(acc, dodge, cutoff_miss, cutoff_hit)
	if not (rng.next_float() < chance):
		return {
			"hit": false, "crit": false, "damage": 0,
			"raw": 0.0, "mult": 1.0, "hit_chance": chance,
		}

	var crit_valid: bool = bool(spec.get("crit_valid", true))
	var crit_rate: float = clampf(float(spec.get("crit", 0.0)), 0.0, 1.0)
	var crit: bool = crit_valid and rng.next_float() < crit_rate

	var base_low: float = float(spec.get("base_low", 0.0))
	var base_high: float = float(spec.get("base_high", base_low))
	var t: float = rng.next_float()
	var raw: float = base_low + (base_high - base_low) * t

	# 4. 修正加算
	var extra: float = 0.0
	for m in spec.get("mods", []):
		extra += float(m)
	var mult: float = 1.0 + extra

	var dmg: float = raw * mult
	if mult < 0.0:
		mult = 0.0
		dmg = 0.0

	# 5. 持久伤害倍率（buff 类，连乘）
	var buff_mult: float = float(spec.get("dmg_mult_buffs", 1.0))
	if buff_mult != 1.0:
		dmg *= buff_mult

	# 6. 暴击
	var crit_mult: float = float(spec.get("crit_mult", 1.5))
	if crit:
		dmg *= crit_mult

	# 7. 减伤
	if not bool(spec.get("ignore_prot", false)):
		var prot: float = clampf(float(spec.get("prot", 0.0)), 0.0, 1.0)
		dmg *= (1.0 - prot)
	dmg *= (1.0 + float(spec.get("dmg_taken_mod", 0.0)))

	# 8. 取整。用 floor(x+0.5) 而不是 round()，因为 Python 的 round() 是
	#    银行家舍入，两边行为必须显式对齐。
	var final_damage: int = int(floor(dmg + 0.5)) if dmg > 0.0 else 0

	return {
		"hit": true, "crit": crit, "damage": final_damage,
		"raw": raw, "mult": mult, "hit_chance": chance,
	}


## 期望伤害（不考虑命中，用于 AI 评分与平衡分析）
static func expected_damage(spec: Dictionary) -> float:
	var base_low: float = float(spec.get("base_low", 0.0))
	var base_high: float = float(spec.get("base_high", base_low))
	var extra: float = 0.0
	for m in spec.get("mods", []):
		extra += float(m)
	var dmg: float = (base_low + base_high) * 0.5 * maxf(1.0 + extra, 0.0)
	dmg *= float(spec.get("dmg_mult_buffs", 1.0))
	var crit_rate: float = clampf(float(spec.get("crit", 0.0)), 0.0, 1.0)
	dmg *= 1.0 + crit_rate * (float(spec.get("crit_mult", 1.5)) - 1.0)
	if not bool(spec.get("ignore_prot", false)):
		dmg *= 1.0 - clampf(float(spec.get("prot", 0.0)), 0.0, 1.0)
	return dmg

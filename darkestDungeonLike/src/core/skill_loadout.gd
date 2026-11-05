class_name SkillLoadout
extends RefCounted
## 技能组规则（M19）：每个英雄从全部技能里挑 N 个装备。
##
## 抽成共用件的理由和 M15 的 `BuffRules` 一样：**同一套判定有两个调用方**
## ——元层（Campaign 存/读档）和 bench（对照组）。
## 两边各写一份，迟早会在某个边界上分叉，然后 bench 数字和游戏内表现对不上，
## 而这种不一致最难查：两边都不报错，只是答案不同。
##
## 数据来源：`heroes.json` 的 `skill_selection` 段
## （`can_select_combat_skills` / `number_of_selected_combat_skills_max`）。
## 这段数据 M0 就抽出来了，M19 之前一直没人读。

## 默认组：`campaign.json` 的 `default_skills` 优先，没配就用技能表前 N 个。
##
## 原版没有「默认装哪 4 个」这张表（硬编码在游戏逻辑里，抽不出来），
## 所以配置里那套是本项目补的，见 M19 文档。
static func default_for(table: Dictionary, cfg: Dictionary, hid: String) -> Array:
	var rule: Dictionary = table.get(hid, {})
	# 不可选职业 / 没这张表 → 空数组 = 战斗层全装（M18 及以前的行为）
	if rule.is_empty() or rule.get("can_select", false) != true:
		return []
	var allowed: Array = rule.get("ids", [])
	var max_n: int = int(rule.get("max", 0))
	if max_n <= 0:
		return []
	var preset: Array = (cfg.get("default_skills", {}) as Dictionary).get(hid, [])
	var out: Array = []
	for sid in preset:
		var s: String = str(sid)
		if allowed.has(s) and not out.has(s):
			out.append(s)
	if out.is_empty():
		return allowed.slice(0, mini(max_n, allowed.size()))
	return out.slice(0, max_n)


## 读档时的清洗：只留合法的、去重、超上限截断；清洗完是空的就回默认。
##
## 「空」必须回默认而不是原样返回——空数组在战斗层表示「全装」，
## 老存档（没有 skills 字段）会因此变成 7 个技能，和新档不一致。
static func sanitize(table: Dictionary, cfg: Dictionary, hid: String, raw: Variant) -> Array:
	var rule: Dictionary = table.get(hid, {})
	var allowed: Array = rule.get("ids", [])
	var got: Array = []
	if raw is Array:
		for sid in (raw as Array):
			var s: String = str(sid)
			if allowed.has(s) and not got.has(s):
				got.append(s)
	var max_n: int = int(rule.get("max", 0))
	if max_n > 0 and got.size() > max_n:
		got = got.slice(0, max_n)
	if got.is_empty():
		return default_for(table, cfg, hid)
	return got


## 技能栏有几格。不可选职业返回它自己的技能总数（憎恶是 7）。
static func max_slots(table: Dictionary, hid: String) -> int:
	var rule: Dictionary = table.get(hid, {})
	if rule.get("can_select", false) != true:
		return (rule.get("ids", []) as Array).size()
	return int(rule.get("max", 4))

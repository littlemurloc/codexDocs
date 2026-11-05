class_name TurnScheduler
extends RefCounted
## 行动序。
##
## DD1 的回合制是「每轮重排」：所有单位各自掷一次先攻，按先攻从高到低行动，
## 一轮结束后全部重掷。所以速度不是「谁永远先手」，而是「谁更常先手」——
## 速度 8 的盗墓贼也会有被速度 1 的十字军抢先的回合。这是它和很多回合制
## 游戏的关键差别，做成固定速度排序会立刻丢掉这个手感。
##
## 先攻 = 速度 + rand(0, initiative_base)，initiative_base 取自 rules.json = 8。
## 「0 到 8」含两端这一点无法从数据确认，标注为推断（中置信）。
##
## 同先攻的 tie-break 规则在 exe 里，不可见。此处采用：
##   先攻相同 → 速度高者优先 → 双方轮流 → 站位靠前优先
## 这是与 DD1 观感一致的近似，不是源码还原。

## 返回 [{actor, initiative, order}]，已按行动顺序排列
static func build_order(actors: Array, rng: DdRng, initiative_base: int) -> Array:
	var entries: Array = []
	var index: int = 0
	for a in actors:
		if not a.is_alive():
			continue
		var init_value: float = a.speed() + a.initiative_bonus + float(rng.next_int_range(0, initiative_base))
		entries.append({"actor": a, "initiative": init_value, "index": index})
		index += 1

	entries.sort_custom(func(x, y):
		if x.initiative != y.initiative:
			return x.initiative > y.initiative
		var sx: float = x.actor.speed()
		var sy: float = y.actor.speed()
		if sx != sy:
			return sx > sy
		# 双方轮流，避免某一方永远占便宜
		if x.actor.side != y.actor.side:
			return x.actor.side == Combatant.SIDE_PARTY
		return x.index < y.index
	)
	return entries

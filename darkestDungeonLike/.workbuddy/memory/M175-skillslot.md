# 「技能 4/4 但战斗里只有 2 个」排查记录（M175）

## 数据

`plague_doctor` 的 `launch`（位次掩码，1 = 1 号位）：

| 技能 | launch |
|---|---|
| noxious_blast（毒气喷发） | `432` |
| plague_grenade（瘟疫手雷） | `43` |
| blinding_gas（致盲瓦斯） | `43` |
| battlefield_medicine（战地医术） | `43` |
| incision | `321` |
| emboldening_vapours | `4321` |
| disorienting_blast | `432` |

用户截图里瘟疫医生在 **4 号位**，装的正是前四个 ——
**按 launch 算，四个都能在 4 号位放**。

## 所以「只显示 2 个」不是位次问题

`Battle.player_options()` 过滤条件有两条：
1. `_can_use()` —— 位次掩码 + 每场次数（`per_battle_limit`）
2. `_legal_targets()` 非空

四个技能的 launch 都含 4，那么剩下的可能：
- **`per_battle_limit` 用完**（某些技能每场只能放 N 次）
- **没有合法目标**（比如只剩后排敌人、技能要求近战位目标）
- **战斗中实际站位已经不是 4 号位**（被打退/换位）

## 界面已改

队伍屏技能区现在会写：

```
技能　4 / 4　·　4 位于可用 2 个
· 毒气喷发        · 瘟疫手雷
· 致盲瓦斯        · 战地医术
```

不可用的那几项**灰掉并在名字后面标「（此位不可用）」**。
判据和战斗里 `Battle._can_use()` 用的是同一个 `launch_mask`。

## 待确认

用户报的现象（4 号位只出 2 个）**和 launch 数据不符**，
需要在实际战斗里看是哪两个、以及当时的站位和 `per_battle_limit`。

## 坑

`campaign.db` **不存在**（Campaign 上没有这个字段），
要用视图层的 `db`。写成 `campaign.db.heroes` 会运行时报
「Invalid access to property or key 'db' on Campaign」。

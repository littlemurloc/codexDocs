# M52 怪物攻击声

> M51 之后怪物会「叫」了，但**出手还是通用打击声**（`imp_general`）——
> 骷髅挥棒、猪人挥刀、鱼人戳叉，听起来是同一记闷响。
> 这一期把每只怪自己的攻击声接上。**规则层一行未改**，1310 项断言全绿。

---

## 1. 素材是按「技能」录的，但我们拿不到技能级映射

DD1 的怪物攻击音命名是：

```
char_en_<前缀>_<动作>          char_en_sklcom_cudgel
                              char_en_swinereav_butcher
                              char_en_fishcrab_pincer
```

看起来「技能 id 直接对上动作名」就能精确匹配。实测**不行**：

| 尝试 | 结果 |
|---|---|
| 技能 id 精确等于动作名 | **39 / 552**（7%） |

失败的原因是缩写：本作技能 id 是 `cudgel`、`crossbowshot`，而音效名里
分组前缀把怪物名压成了 `sklcom`、`sklar`，动作那一段也常是缩写或干脆叫 `attack`。

## 2. 退一步：每个怪物组取最多 3 个「像打人」的动作

不判断「哪个才是它的主攻击」，而是**从这组的全部动作里挑 3 个能当攻击的**，随机播：

```
atk/<family>_1.ogg   atk/<family>_2.ogg   atk/<family>_3.ogg
```

挑选规则：

1. 排除明显不是攻击的动作：`miss` / `heal` / `buff` / `mark` / `summon` /
   `howl` / `guard` / `shuffle` / `back` / `fwd`（`back`/`fwd` 是步法，
   第一版把蹒跚者挑成了「后退的脚步声」）
2. 命中关键词的优先：`stab` `slice` `claw` `bite` `spear` `hook` `pincer` `smash` …
3. **同名动作只留第一个 take**（第一版没去重，导出成 `cudgel, cudgel, cudgel`——
   三个变体是同一段录音的三次采样，随机播等于没随机）

结果：**89 个组 / 169 个文件 / 2.9 MB**，其中 22 组有 3 个变体、36 组 2 个、31 组 1 个。

## 3. 两个名字体系要分开

这里有个容易搞混的地方，写进代码注释了：

| | 语音（M51） | 攻击声（M52） |
|---|---|---|
| 槽位 | `voice/<group>_<kind>_<n>` | `atk/<family>_<n>` |
| 键 | DD1 的**语音分组**（`skel` / `swine_1` / `brig_2`） | 本作的 **family**（`skeleton_common` / `swine_reaver`） |
| 为什么 | 语音是按「怪物家族」录的，一个组可能覆盖好几只 | 攻击声是按**具体怪物**录的，分组比 family 粗就对不上 |

语音那边 `skel` 一个组给七种骷髅共用是合理的（都是骨头架子），
但攻击声要是也共用，长枪兵和重盾兵的挥击就一样了——所以走 family。

## 4. 播放与兜底

```gdscript
if 是怪物:
    played = play_variant("atk/" + family, 3, ±5% 音高, -1dB)
if not played:                    # 这组没录过攻击声
    走 M51 的武器音链：imp_<kind> → imp_general → hit
```

**254 个怪物里 221 个有攻击声，33 个没有**——没有的全是道具与尸体：
`cauldron_*`（大锅）、`brigand_barrel`（炸药桶）、`corpse_*`（尸体）、
`pew_*`（长椅）、`ancestor_nebula`。这些不特判，靠 `play_variant` 返回 false 自然走兜底。

> 兜底链保持三级不变，是因为**静音会被读成「音效坏了」**，而不是「这只怪没录」。

## 5. 试听模式

`--sfx-demo` 现在 40 项，末尾 6 项是怪物攻击声：

```
atk/skeleton_common   atk/swine_reaver     atk/fishman_harpoon
atk/brigand_cutthroat atk/cultist_witch    atk/hag
```

攻击声是 3 份变体、语音是 2 份，所以试听播放时要**按前缀选份数**——
拿 2 去探 `atk/*` 会漏掉第 3 份。

---

## 6. 已知限制

1. **不是技能级映射。** 同一只怪的三个变体是「它会的三招」里挑的，不是「这一招配这一声」。
   要做到技能级，得先解决缩写（`sklcom` ← `skeleton_common`）那一层，
   而技能名和动作名仍然是两套命名，收益不值。
2. **`templar` 的 4 个 family 共用一个前缀**（`templar_melee` / `_ranged` / `_mb` 变体），
   它们本来就长得一样、招式名也一样，共用没有副作用。
3. **`shuffler` / `cell_white` / `swine_prince` 挑到的不是纯攻击**（`shuffle`、
   `reconstruct`、`blind`/`enrage`）——这些怪在 DD1 里就没有「挥一下」的动作音。
   听感上仍是「它动了」，比通用闷响准。
4. **没有做「打空的攻击声」**（`_miss` 那一批）。本作有未命中事件，
   但目前未命中的处理是 `miss` 音效 + 无伤害飘字，够用。

---

## 7. 验证

| 项 | 结果 |
|---|---|
| 单测 | **1310 项全绿** |
| 自检 | `SELFTEST PASS`（结束原因 wipe 也算 PASS：判据是「有没有走完流程」，不是「有没有赢」） |
| 覆盖 | 254 怪 → **221 有攻击声 / 33 无**（全是道具与尸体） |
| 实跑 crypts | `[sfx] atk/skeleton_courtier`、`atk/skeleton_defender`，英雄侧仍是 `imp_sword` / `imp_gas` / `imp_staff` |
| 试听 | `shots/m52_sfx_demo.png`（40 项 / 两列 / 无溢出） |
| 文件 | 169 个 / 2.9 MB，`.gitignore` 已加 `assets/audio/atk/*.ogg` |

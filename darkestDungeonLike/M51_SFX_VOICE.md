# M51 分类命中音与敌人语音

> M50 之后剩下的两件事：命中音还是「一把剑打所有东西」，怪物一声不吭。
> 这一期把「按武器分类的打击声」和「每只怪自己的叫声」接上了。
> **规则层一行未改**，1310 项断言全绿。

---

## 1. 分类命中：武器名就在数据里

M50 把 `hit` 从合成音换成了 `char_share_imp_sword`——**所有攻击都是挥剑**。
瘟疫医生扔炸弹、赏金猎人开枪、修女抡钉锤，听起来都是同一把剑。

修法不需要新表。`data/heroes.json` 里每个技能的 `art.anim` 本来就是武器名：

```
{"id": "smite",  "art": {"anim": "attack_sword"}}
{"id": "blast",  "art": {"anim": "attack_blast"}}
{"id": "pistol", "art": {"anim": "attack_pistol"}}
```

素材包里正好有 13 个 impact：

| 槽位 | 原样本 | 谁在用 |
|---|---|---|
| `imp_sword` | `char_share_imp_sword` | 十字军、麻风病人（`chop`/`hew`）、赏金猎人（`axe`）、强盗（`slice`） |
| `imp_knife` | `imp_knife` | 盗墓贼、瘟疫医生（`dagger`）、小丑（`dirk`/`sickle`）、`pick` |
| `imp_spear` | `imp_spear` | 恶女（`high`/`low`/`leap`）、`charge`/`lunge` |
| `imp_arrow` | `imp_arrow` | 弩手（`artillery`）、小丑（`bow`）、强盗（`hipshot`） |
| `imp_gun` | `imp_gun` | 强盗（`pistol`） |
| `imp_shield` | `imp_shield` | 老兵（`shield`/`guard`） |
| `imp_whip` | `imp_whip` | 憎恶（`chain`）、赏金猎人（`hook`） |
| `imp_staff` | `imp_staff` | 修女（`lectionary`/`miracle`）、十字军（`scroll`）、古董商（`censer`） |
| `imp_magic_dark` | `imp_magic_dark` | 神秘学家（`skull`） |
| `imp_gas` | `imp_gas` | 瘟疫医生（`blast`/`grenade`）、憎恶（`barf`） |
| `imp_liquid` | `imp_liquid` | 盗墓贼（`potion`） |
| `imp_slime` | `imp_slime` | 目前没有技能用到，留着给怪物 |
| `imp_general` | `imp_general` | 钝击（`club`/`mace`/`punch`/`stun`/`claw`）+ **所有没登记的动作的兜底** |

**DD1 只有这 13 种**，没有「斧」「锤」「爪」的细分。所以 `chop`、`axe` 归到 `sword`，
`hook`、`chain` 归到 `whip`。归类依据是「谁在用什么」写的注释，不是随便配的。

### 兜底链是三级的

```
anim → imp_<kind>  →（缺文件）imp_general →（还缺）hit →（再缺）静音
```

第二级是必须的：**素材不全时不能静音**。一次攻击没声音，玩家的第一反应是
「音效坏了」，而不是「这个武器没录」。宁可听一声闷响。

---

## 2. 敌人语音：一张推出来的表

### 为什么只能推

DD1 的语音样本按**它自己的分组名**命名：

```
char_en_vo_skel_hurt_01     ← 分组 skel
char_en_vo_swine_2_death_03 ← 分组 swine_2
```

本作的单位 id 是目录名（`skeleton_common_A`）。两边对不上，而且**没有可读的映射**：

- `.darkest` / `.fx.darkest` 里搜 `voice` / `sound` / `bank` / `event:/` → **零命中**
- DD1 走 FMOD event，样本名只在 bank 内部使用

所以表是**按名字语义 + 所在区域的 bank** 推出来的。推不出来的**留空**：

> 骷髅发出猪叫，比没有声音糟得多。

### 结果

**254 个怪物，219 个有语音，35 个静音。** 静音的 35 个全部是道具与终局部件：

`cauldron_*`（大锅）、`pew_*`（长椅）、`cell_*`（牢笼）、`cyst_D`、`totem_*`、
`brigand_barrel_D`、`ancestor_*`（只有部分叫声录了）。**这些本来就不该叫。**

### 槽位

```
assets/audio/voice/<group>_<kind>_<n>.ogg
```

- `kind` ∈ `aggro` / `hurt` / `crit` / `death`
- `n` = 1..2，每种叫声各留 2 份录音，播放时随机挑一份
  （只有一份的话，同一只怪连挨两下听起来像卡带）
- 共 **353 个 / 5.7 MB**（单声道 22.05k，q3，统一截到 2 秒）

### 什么时候出声

| 时机 | 种类 | 音量 |
|---|---|---|
| 敌人第一次出手 | `aggro` | −7 dB |
| 敌人挨打 | `hurt` | −3 dB |
| 敌人被暴击 | `crit` | −3 dB |
| 敌人阵亡 | `death` | −1 dB |

**咆哮一场只来一次**。第一版是「每次出手都吼」，结果同一只猪连着三次出手吼了三声，
听起来像音效卡在循环里。咆哮是登场台词，不是每回合的台词。

两条限流是必须的，因为语音素材每个 1–2 秒、而命中事件密集得多：

- 同一只怪 `hurt` 间隔 ≥ 260 ms（持续伤害一跳一跳地来，否则会连成一片）
- 全局 `aggro` 间隔 ≥ 800 ms（四只怪同一轮登场时不要叠成合唱）

### 有些分组只录了部分叫声

`cultist_orgiastic` 只有 `aggro`、`viragoshroom` 只有 `hurt`、
`brigcannon` 也只有 `hurt`。这类分组缺某种时退到 `FALLBACK` 表里的补位组
（`cultist_orgiastic → cultist_m`、`viragoshroom → virago`、`brigcannon → brig_2`）。

不补位的话表现是「被打时不吭声、死时却叫」，读起来像 bug。

---

## 3. 两个新文件

| 文件 | 职责 |
|---|---|
| `src/view/enemy_voice.gd` | `family_of()` / `group_of()` / `slot()` / `fallback_slot()`。纯数据 + 纯函数，不碰播放 |
| `src/view/sfx.gd` 扩写 | 新增 `ANIM_IMPACT` 表、`impact_slot()`、`play_variant()`、`has_slot()` |

`enemy_voice.gd` 是 `class_name`，**新增后要重建类缓存**，否则报
`Identifier "EnemyVoice" not declared`——这条 MEMORY.md 里记着，照做即可。

### `family_of` 不能用「去掉最后一段」

```gdscript
s.rfind("_")  → 切掉末段
```

`skeleton_common_A` 这样切是对的，但 `carrion_eater_big_A` 会被削成 `carrion_eater`，
大小腐肉就共用一个组了。所以判据是**末段必须是一个大写字母**（`_A`–`_E`）。

---

## 4. 试听模式扩了

`--sfx-demo` 现在一屏 34 项，两列：

- 左：界面音 10 + 分类命中 13
- 右：敌人语音 12（8 个 hurt + 2 个 death + 1 crit + 1 aggro）

带 `/` 的是变体槽位，播放要走 `play_variant`——直接 `play("voice/skel_hurt")`
会去找一个不存在的文件然后静音。

---

## 5. 已知限制

1. **分组是推的，不是读的。** `jellyfish` / `octotank` / `snail_urchin` 都归到了
   `bug_2`（海湾里那几个「虫」），`fungal_*` 归到了 `slime_*`。这两组是**猜的**，
   如果听出来不对，改 `FAMILY_GROUP` 一行即可——播放端不用动。
2. **怪物没有「攻击声」。** 素材里其实有 `char_en_<group>_attack`
   （`char_en_formmelee_attack`、`char_en_jelly_sting`、`char_en_fishcrab_pincer`），
   那是另一张映射表，这一期没做。敌人出手目前只有 `aggro` 发声。
3. **英雄没有语音。** `voiceover.bank` 有 166 MB 的英雄台词（按职业分），
   但那是「台词」不是「反馈音」，要先决定什么时候播（暴击？死门？城镇对话？）。
4. **`imp_slime` 目前无人使用**。留着给怪物，将来怪物的攻击分类可以用它。
5. **`.gitignore` 漏过一层。** `assets/audio/*.ogg` 的 `*` 不跨 `/`，
   所以 `assets/audio/voice/*.ogg` 必须单列一条——不然 353 个版权文件会进仓库。

---

## 6. 验证

| 项 | 结果 |
|---|---|
| 单测 | **1310 项全绿**（只改 view 层，规则层未动） |
| 自检 | `SELFTEST PASS` |
| 语音覆盖 | 254 个怪物 → 219 有语音 / 35 静音（全是道具与终局部件） |
| 分组抽查 | `skeleton_common_A→skel`、`swine_wretch_B→swine_1`、`fishman_harpoon_C→fish_1`、`cultist_witch_A→cultist_f` |
| 实际播放 | crypts：`imp_sword`/`imp_gas`/`imp_gun` 各自命中，`skel_hurt`/`skel_crit`/`skel_aggro` 都出 |
| 死亡 | warrens：`swine_drummer_A death → voice/swine_2_death`、`spider_spitter_A death → voice/bug_1_death` |
| 试听 | `shots/m51_sfx_demo.png`（34 项 / 两列 / 无溢出） |

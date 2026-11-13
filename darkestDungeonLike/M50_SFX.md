# M50 · 真实音效

> M43 那 10 个程序化合成的占位音，换掉 8 个。

## 1. 先纠正 M43 的三个误判

### 1.1 FSB5 头是 6 个 uint32，我读少了一个

已经写在 M49，这里再记一次，因为它是后面一切的根：

```
"FSB5" | version | numSamples | hdrSize | nameSize | dataSize | mode
```

从 `+4` 读 5 个的话，`dataSize` 会被当成 `mode`，于是得出「1 个样本、1892 字节」这种荒谬值，
然后判断「字段顺序没对上」。**读 6 个**，`60 + hdr + names + data == 文件大小` 才算读对。

### 1.2 「数据是裸 MPEG 流」是错的

M43 我看到 `en_cove.bank` 里有 23 万个 `0xFF 0xFB`，就断定是 MPEG 帧。
vgmstream 给出的是：

```
encoding: Custom Vorbis
```

**是 Vorbis**（FMOD 自己的封装，不带 Ogg 容器）。`0xFF 0xFB` 是 Vorbis 压缩数据里的偶然字节——
在 146 MB 里出现 23 万次，比随机期望高，但远不足以构成「帧」。

这个误判的代价很实际：按 MPEG 帧切会切出噪音，而按 Vorbis 头解又缺 header。

### 1.3 两个 codec 值，两种编码

同一批 bank 里混着两种编码，靠 `mode` 字段区分：

| mode | 编码 | 哪些 bank | 内容 |
|---|---|---|---|
| `0xF`（15） | **Custom Vorbis** | `en_*.bank`、`general.bank`、`hero_*.bank` | 音效、语音 |
| `0x10`（16） | **FMOD FADPCM 4-bit** | `music.bank`、`ambience.bank` | 音乐、环境音 |

`fsb5` 这个 Python 库的枚举只到 15，遇到 16 直接抛异常——这就是 M49 卡住的地方。
而 15 它是认识的，所以**音效本来可以直接用那个库解**（只要有 header 表）。

## 2. 工具链（和音乐同一条）

```
bank（RIFF/FEV）
  → 切出 FSB5 块（60 + hdr + names + data 字节）
  → vgmstream-cli -s <subsong> -o x.wav
  → ffmpeg（截断 + 淡出 + 单声道 22.05k）
```

vgmstream 是这条链上唯一一个「两种编码都认」的工具。直接用 fsb5 库解 Vorbis 也能行，
但它需要一份内置的 crc32 → setup header 表，覆盖率不确定；vgmstream 没有这个问题。

## 3. 换了哪 8 个

选音效有两个硬约束：

1. **不要人声**。库里大量 `char_en_vo_*`（敌人喊叫）、`char_al_*`（英雄台词），
   拿去做通用反馈的话，每次攻击都是同一个角色的嗓子，很怪。所以优先选 `*_imp_*`（impact）和 `gen_*`。
2. **必须截断**。原版这些音是「完整动作音」（挥动 + 撞击 + 收势），2–6 秒。
   而本作的出手表现是 0.42 秒（`POSE_TIME`），照搬会拖过下一个动作。
   统一截到 0.85–2.5 秒，末尾 120ms 淡出——**不能硬切在响的地方，那会「啪」一声**。

| 槽位 | 原曲目 | subsong | 截到 |
|---|---|---|---|
| `hit` | `char_share_imp_sword` | en_shared#227 | 0.85s |
| `crit` | `char_share_crit_hero` | general#100 | 1.20s |
| `death` | `gen_char_death_enemy` | general#159 | 1.30s |
| `stress` | `gen_status_stress_up_comp` | general#115 | 1.20s |
| `heal` | `gen_status_heal_ally` | general#142 | 1.00s |
| `door` | `gen_map_door_open_weald` | general#129 | 1.00s |
| `torch` | `gen_map_torchout` | general#50 | 1.00s |
| `victory` | `Combat_Level2_Victory` | general#65 | 2.50s |

输出：单声道 22.05kHz Vorbis q5，8 个共 **85 KB**。

> 单声道 + 22.05k 是有意的：音效不需要立体声定位，也不需要 16kHz 以上的频段。
> 换来的体积差是 4 倍，而且这些音本来就很短，加载更快。

## 4. 没换的两个

| 槽位 | 为什么保留合成音 |
|---|---|
| `click` | 全部 41 个 bank 里**没有 UI 点击音**。`ui_` 开头只有 `ui_shr_mailinglist`（邮件列表，3.5 秒）。DD1 的界面音多半是 FMOD event 里的程序化音，不在这批 sample 里 |
| `miss` | 库里有 `*_miss` 的都是**挥空 + 人声抱怨**（`char_al_cru_smite_miss` 1.6 秒，带台词）。合成的那个是 0.18 秒的高频噪声，反而更像「擦过去了」 |

## 5. 两级素材：原版优先，占位兜底

同一个槽位可以同时有两种文件：

```
assets/audio/hit.ogg     原版（DD1，不进版本库）
assets/audio/hit.wav     M43 合成占位（原创，入库）
assets/audio/miss.wav    只有占位
```

`Sfx.stream()` 的查找顺序改成 **`.ogg` 优先**：

```gdscript
for ext in [".ogg", ".wav", ".mp3"]:
```

这个顺序不是随手定的。反过来（`.wav` 优先）的话，本地放着原版也永远用不上，
因为占位 wav 一直在。而现在：

- 有原版的机器 → 听到原版
- 没有原版的机器（clone 下来只有 wav）→ 退回占位，**照样有声音，不报错**

对应 `.gitignore`：

```
assets/audio/music/*.ogg
assets/audio/*.ogg
```

`*.wav` 不忽略——那是原创的。两条规则不能合并，因为它们是**同一槽位的两级素材**。

## 6. 验证

- 10 个槽位的实际来源（`.tmp/chk_sfx2.gd`）：

```
OK   hit      AudioStreamOggVorbis  0.85 秒  来自 .ogg
OK   crit     AudioStreamOggVorbis  1.20 秒  来自 .ogg
OK   miss     AudioStreamWAV        0.18 秒  来自 .wav   ← 回退正确
OK   death    AudioStreamOggVorbis  1.30 秒  来自 .ogg
OK   stress   AudioStreamOggVorbis  1.20 秒  来自 .ogg
OK   heal     AudioStreamOggVorbis  1.00 秒  来自 .ogg
OK   door     AudioStreamOggVorbis  1.00 秒  来自 .ogg
OK   torch    AudioStreamOggVorbis  1.00 秒  来自 .ogg
OK   click    AudioStreamWAV        0.05 秒  来自 .wav   ← 回退正确
OK   victory  AudioStreamOggVorbis  2.50 秒  来自 .ogg
--   nope（无文件，返回 null 不报错）
```

- 实际运行（`--dev`，一趟 crypts 中途）：`25 次 hit`、`2 次 crit`，音乐切换正常
- **1310 项断言全绿**，自检 PASS

## 7. 还没做的

1. **分类音效**。原版每个职业有自己的攻击音（`char_al_cru_smite`、
   `char_share_imp_axe/shield/knife/spear/gun/staff`），现在所有人都用同一把剑。
   接的话要按技能的 `art.anim` 或武器类型分派，是 view 层的事。
2. **敌人语音**。`en_shared.bank` 有 335 个样本，几乎全是各怪物的 aggro/hurt/crit/death 喊叫。
   接进去会让战斗热闹很多，但要改 `Battle` 的事件带怪物 id——不是纯 view 改动。
3. **环境音**。`ambience.bank` 149 MB / 564 个 FADPCM 样本，是各区域的环境底噪。
   和音乐同一套解，但体积大，要挑。

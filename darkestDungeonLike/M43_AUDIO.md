# M43 · 音效层（程序化占位）

> 一句话：**先把「事件 → 槽位 → 播放」这条链接通**，音效是真是假不影响这条链。
> 真音效将来只是替换文件。

---

## 1. 为什么没有直接用 DD1 的音效

DD1 的音频在 `audio/secondary_banks/*.bank`（41 个，610 MB）。
侦察结果（详细见 §6）：

- `.bank` 是 **RIFF/FEV** 容器，内部包着 **FSB5** 音频块（每个 bank 一个）
- 样本**名字能读出来**：`char_en_vo_bug_2_death_01`、`char_en_vo_zombie_2_death_04` 这类
- 样本数据是**裸 MPEG 帧**（`0xFFFB` 大量出现），没有 Ogg 容器
- 但 **FSB5 样本表的字段顺序我没对上**：按 `(version, numSamples, headerSize, nameSize, dataSize)`
  读能凑出一组自洽的数（164 个样本、7584 字节表头、5028 名字、11.49 MB 数据），
  可名字实际出现在表头之后第 0 字节处，和「名字在最后」的布局差约 4.5 KB

这和 `.skel` 那次是同一类问题：**格式能摸到边，但要花一整期才能确认**。

所以换路子：**用合成音把链路先跑通**。

## 2. 十个人工合成的占位音

Python 直接生成 22.05 kHz / 16bit 单声道 WAV（噪声 + 正弦 + 指数包络），共 188 KB：

| 名字 | 时长 | 做法 | 用在 |
|---|---|---|---|
| `hit` | 0.16s | 低频噪声 + 95Hz 衰减音 | 普通命中 |
| `crit` | 0.34s | 高通噪声 + 上扫音 180→780Hz | 暴击 |
| `miss` | 0.18s | 高通噪声短扫 | 未命中 |
| `death` | 0.70s | 160→48Hz 下滑 + 低频噪声 | 阵亡 |
| `stress` | 0.45s | 146Hz + 155Hz 双音拍频（不协和） | 加压 |
| `heal` | 0.45s | 520→840Hz 上滑 + 二次谐波 | 治疗 / 休整 |
| `door` | 0.50s | 极低通噪声 + 7Hz 颤动 | 撤退 / 门 |
| `torch` | 0.30s | 高通噪声爆 | 点火把 |
| `click` | 0.05s | 1400Hz 短促 | 界面点击 |
| `victory` | 0.80s | 392/494/587/784 四音上行 | 离开地牢 |

**这些是原创的，可以进版本库**（和 DD1 美术不同，那些必须 `.gitignore`）。

## 3. 播放层

```gdscript
class_name Sfx extends Node
func play(name, pitch_scale := 1.0, db_offset := 0.0)
func stream(name) -> AudioStream          # 缺文件返回 null
```

- **槽位**：`res://assets/audio/<name>.wav`（也试 `.ogg` / `.mp3`，将来换格式不改代码）
- **缺文件 = 静音**，不报错——和 `UnitArt` / `UiSkin` 同一条原则
- **8 个声道轮转**：一轮里可能同时有攻击、受击、死亡三个音，2 个声道会互相掐掉
- **随机音高 ±6%**：同一种声音连响时不至于像机关枪
- `--mute` 全程静音

## 4. 接线点

| 事件 | 音 |
|---|---|
| `attack`（暴击 / 普通） | `crit` / `hit` |
| `miss` | `miss` |
| `heal`（amount > 0） | `heal` |
| `stress`（|delta| ≥ 1） | `stress` |
| `death` | `death` |
| `affliction` | `stress`（音高 ×0.7、+2dB） |
| `virtue` | `heal`（音高 ×1.25、+2dB） |
| 点火把 / 休整 / 撤退 / 离开 | `torch` / `heal` / `door` / `victory` |
| 界面点击 | `click`（−12dB） |

点击音**跳过 `skill:` 和 `goto:`**：点技能再点目标本来就要连响两次，
再叠 tick 会显得吵。

## 5. 验证

- `--dev` 下每次播放打印 `[sfx] hit`：一次自动战斗里 4 次攻击 4 条，接线通
- 载入检查脚本 `.tmp/chk_sfx.gd`：**10/10 全部载入**（`AudioStreamWAV`，时长正确），
  不存在的名字返回 null 而不报错
- 1310 项断言全绿；自检 PASS

## 6. 附：FSB5 的探查记录（留给下一期）

```
offset 149728（en_cove.bank，11.4 MB）
+0     "FSB5"
+4     01 00 00 00       ← 假设是 version
+8     a4 00 00 00       ← 164，假设 numSamples
+12    a0 1d 00 00       ← 7584，假设 sampleHeadersSize
+16    a4 13 00 00       ← 5028，假设 nameTableSize
+20    20 5e af 00       ← 11492896，假设 dataSize（≈ 文件长 11655296 − 162400）
+24    0f 00 00 00 01 00 00 00 + 12 字节 0
+40    16 字节 hash
+48    名字表开始（`char_en_vo_*`），实测 169 个可读串
第一个 MP3 帧头在 +17165
```

**矛盾点**：名字在 +48 出现，但按 `headerSize + nameSize` 算，名字该在 +7632。
差 4505 字节，说明要么字段顺序不同，要么中间还有一层。

下一步该做的：拿 `fsb5` 的公开解析器（vgmstream 的 `fsb5.c`）对一遍字段，
而不是继续猜——猜格式的代价已经付过两次（`.skel`、这一次）。

---

**未 commit、未 push。**

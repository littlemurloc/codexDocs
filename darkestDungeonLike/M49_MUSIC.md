# M49 · 背景音乐

> 64 首曲子，5 首接进了游戏。

## 1. 之前为什么没做

M43 探查音频时判断「FSB5 样本表字段顺序没对上」，就转去做程序化占位音效了。

那次判断有一半是错的。

## 2. 这次摸清的三件事

### 2.1 字段顺序：我少读了一个字段

FSB5 头是 **6 个 uint32**：

```
"FSB5" | version | numSamples | sampleHeadersSize | nameTableSize | dataSize | mode
```

M43 我从 `+4` 读了 5 个，把 `dataSize` 当成了 `mode`，于是 `numSamples=1`、
`dataSize=1892` 这种荒谬值。正确读法是读 6 个：

```python
version, num, hdr, names, data, mode = struct.unpack_from('<6I', b, o+4)
```

music.bank 的值是 `num=64 hdr=1024 names=1892 data=153779872 mode=0x10`，
而 `60 + hdr + names + data == 文件大小` **完全吻合**——这一条才是「读对了」的证据。

### 2.2 `mode=0x10` 不是 Vorbis，也不是 Opus

FMOD 的 codec 枚举到 15（Vorbis）为止，16 没有标准定义。
`fsb5` 这个 Python 库直接把 mode 当 codec，遇到 16 会抛
`ValueError: 16 is not a valid SoundFormat`。

我试过把它强行改成 15（Vorbis）让库接受，结果样本表能解、名字和时长全对，
但解码时抛「缺少 VORBISDATA chunk」——**说明它根本不是 Vorbis**。

vgmstream 一句话给出答案：

```
encoding: FMOD FADPCM 4-bit ADPCM
layout: interleave
interleave: 0x8c bytes
```

**是 FADPCM**（FMOD 自家的 4-bit ADPCM）。所以：
- 按 MPEG 帧扫 → 扫不到（不是 MPEG）
- 按 Vorbis 头解 → 解不出（不是 Vorbis）

两个方向都试过，都在错误的假设上。

### 2.3 bank 是 RIFF/FEV，FSB 只是其中一段

`music.bank` 146.7 MB，开头是 `RIFF...FEV `，音频在偏移 92192 处的一个 FSB5 块里。

vgmstream **直接吃整个 bank 会失败**（`failed opening music.fsb`），
必须先把 FSB5 块切出来：

```python
raw = 60 + hdr + names + data
open('music.fsb','wb').write(b[o:o+raw])
```

## 3. 曲库

64 首，44.1kHz 立体声。名字本身说明了用途：

| 类别 | 例子 | 数量 |
|---|---|---|
| 主题 | `mus_theme_intro_v2` / `mus_theme_loop` / `mus_theme_outro_loop` | 3 |
| 城镇 | `Town_Stereo_Mix_LOOP_1/2` / `mus_town_stemmed` | 4 |
| 战斗 | `Combat_Level1_Loop1/2` / `mus_combat_*`（各区域） | ~25 |
| 探索 | `Explore_Vaults_Level_1..4_Loop` / `Mournweald_LEVEL1_LOOP1_V11` | ~6 |
| 扎营 | `Camping_Stereo_Mix_LOOP_1/2` | 3 |
| 短过场 | 各种 `*_INTRO` / `*_OUTRO`（2–19 秒） | ~15 |

## 4. 接了哪 5 首

| 键 | 曲目 | 时长 | 用在哪 |
|---|---|---|---|
| `menu` | `mus_theme_loop` | 12.2s | 主菜单、设置、胜利屏 |
| `town` | `Town_Stereo_Mix_LOOP_1` | 84.7s | 城镇 + 六栋建筑 + 准备 + 结算 |
| `combat` | `Combat_Level1_Loop1` | 51.2s | 战斗 |
| `weald` | `Mournweald_LEVEL1_LOOP1_V11` | 69.7s | 荒野地图 |
| `depths` | `Explore_Vaults_Level_1_Loop` | 128.0s | 其余三个区域的地图 |

`camp`（扎营曲）也导了，但**还没接**——本作的扎营在 map 屏内一步完成，
没有一个"正在扎营"的持续状态，挂不上去。文件先留着。

曲目和界面是**多对一**的：经营相关的六屏共用城镇曲。
不这么做的话，每次点进商店/公会都要换歌，反而更吵。

## 5. 播放层

`src/view/music.gd`（`class_name BgMusic`）：

- **单通道**：同一时刻只有一首。和 `Sfx` 的 8 声道轮转是两个东西，所以分成两个类
- **0.8 秒淡入淡出**：切屏时不会"啪"地换歌
- **循环在运行时设**：`AudioStreamOggVorbis.loop = true`。
  写在导入设置里的话，这几首就被锁成"只能循环"，别处想用它做一次性过场就不行了
- **缺曲目 = 安静**，不报错（和 `UnitArt` / `Sfx` 同一条原则）
- **比音效低 5dB**：两者同音量的话，战斗里听不清"打中了没有"

## 6. 切歌是「状态变了才切」

```gdscript
if _music != null:
    var want := _music_for_state()
    if want != _music_want:
        _music_want = want
        _music.play(want)
```

界面状态有 12 个，逐个在切换点挂钩一定会漏。而曲目本来就只由当前状态决定，
放在 `_process` 里比对一次最省事，也保证"不管从哪条路径进到这个屏，曲子都对"。

`--dev` 打印切换序列，这是唯一能确认它的方式（截图看不见、耳朵也只能听出有没有）：

```
[music] -> depths      ← 地图（cove）
[music] -> combat      ← 进战斗
[music] -> depths      ← 打完回地图
...
[music] -> town        ← 结算
```

## 7. 工具链（这段值得记）

| 步骤 | 工具 | 坑 |
|---|---|---|
| 切出 FSB5 | 手写 12 行 | 整个 bank 喂给 vgmstream 会失败 |
| FSB5 → wav | vgmstream-cli | 只有它认得 FADPCM；`fsb5` 库不认 |
| wav → ogg | ffmpeg（`imageio-ffmpeg` 自带） | 见下 |

**`soundfile` 在这个环境不可用**：
- `sf.read()` 直接让进程消失（exit 127，无任何输出）
- `sf.info()` 正常、`sf.SoundFile(...).read()` 也正常
- 写 OGG（`format='OGG'`）同样崩

崩的是 libsndfile 的便捷入口，不是 Python 本身。换成 `imageio-ffmpeg` 的二进制一次通过。

> 这类"无输出的 exit 127"最难查：没有 traceback、没有 stderr。
> 判断方法只有缩小范围（import 正常 → info 正常 → read 崩），
> 一旦定位到某个具体调用就直接换工具，不要试着修它。

## 8. 体积

`assets/audio/music/*.ogg`：5 首 / **5.9 MB**（libvorbis q4，约 110 kbps）。

已加进 `.gitignore`。注意 `assets/audio/*.wav`（M43 的原创占位音效）**要入库**，
两条规则不能混。

## 9. 验证

- **1310 项断言全绿**，自检 PASS
- 6 个 ogg 全部 `AudioStreamOggVorbis` 载入成功、时长正确、`loop` 可设
- 实际运行切歌序列正确（weald 用 weald 曲、cove 用 depths 曲、战斗来回切）

## 10. 还没做的

1. **每个区域的专属探索曲**。原版 weald/crypts/warrens/cove 各有一首，
   现在只有 weald 有，其余共用 `Explore_Vaults_Level_1_Loop`。
   曲库里有 `Explore_Vaults_Level_2..4`，但那是"地牢等级"不是"区域"，不能直接对应。
2. **战斗分档**。原版有 Level1/Level2、区域专属、走廊/房间之分；现在只有一首。
3. **扎营曲**。见 §4。
4. **音效仍是程序化合成的**（M43）。真音效在 `en_*.bank` 里，codec 是 0x0F——
   按这次的经验，那多半也是 FADPCM，用同一条流水线就能解，是下一件顺手的事。

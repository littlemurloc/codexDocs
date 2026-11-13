# M57 —— 技能特效接进战斗屏

> 上一期（M56）解决了「能不能解出来」，这一期解决「播在哪儿、播多久」。
> 结论：英雄/怪物技能的施法与命中特效已经能跟着出手者和目标播，
> 映射全部来自数据，`--no-fx` 可整层关掉。

---

## 1. 资源落到哪

`.tmp/spine/fxrender.py --batch` 输出到 `assets/art/fx/`：

```
assets/art/fx/manifest.json        # 描述文件（入库）
assets/art/fx/<特效名>/000.webp    # 帧序列（不入库，.gitignore 已排除）
```

参数：`fps=20`、`scale=0.6`、`webp q=78`。

| 项 | 数值 |
|---|---|
| 特效数 | **125 / 136**（缺的 6 个是 skinnedmesh 读不通 + 5 个数据里没引用） |
| 帧数 | 3111 |
| 体积 | **17.7 MB**（PNG 要约 60 MB，WebP 省 70%） |
| 平均 | 5.8 KB/帧 |

`manifest.json` 每一项：

```json
"smite": {"frames": 17, "fps": 20, "w": 187, "h": 63, "anchor": [93.2, 41.1],
          "scale": 0.6, "dur": 0.83}
```

`anchor` 是**spine 原点（角色脚底）在画布里的像素坐标**。同一特效的每一帧
都画在同一块固定画布上（所有帧内容的并集），所以帧尺寸恒定、播放不会左右跳。

---

## 2. 运行时的三层

| 文件 | 职责 |
|---|---|
| `src/view/fx_art.gd` | 读 manifest、建「技能 → 特效名」映射、按需加载帧纹理（带缓存） |
| `src/view/expedition_scene.gd` 的 `_fx_*` | 播放队列、计时、绘制 |
| `_consume_battle_event("attack")` | 出招时触发：出手特效 + 命中特效（延迟 0.12s） |

映射仍然不手工维护：`fx_art.gd` 遍历 `db.heroes` / `db.monsters` 的
`skills[].art`，把 `fx` 收成出手特效、`targchestfx` / `targheadfx` / `targlowfx`
收成命中特效。

---

## 3. 落点：三种锚点，不是一律画在脚底

第一版把命中特效也画在脚底，结果**溅血落在地上**。原因是 DD1 的目标特效
原点就在「被打的地方」，不是角色脚底。

现在按字段名决定落点：

| 字段 | 锚点 | 用途 |
|---|---|---|
| `fx` | `feet`（脚底） | 挥击、施法弧光 |
| `targchestfx` | `chest`（身体 60%） | 绝大多数命中 |
| `targheadfx` | `head`（84%） | 眩晕星星这类 |
| `targlowfx` | `low`（12%） | 地面效果 |

缩放公式：`k = SPRITE_H / BASE_H / manifest.scale`
= `180 / 400 / 0.6 ≈ 0.75`。改导出比例不用改代码，manifest 里记着。

验证图 `shots/m57_fx_mock.png` 是**离线按同一套公式合成**的（不是引擎截图，
原因见 §5）：弧光在剑身、眩晕在面部、血迹在躯干。

---

## 4. 几个刻意的选择

- **画在光照层之前**：特效会被暗处压暗，读起来是「同一盏灯下」。
  放到光照之后会变成自发光，在至暗难度里亮得很假。
- **命中特效延迟 0.12 秒**：同一帧出会让「挥」和「中」压成一个动作。
- **不报错**：`_fx.has()` 为假就静默跳过（那 49 个 skinnedmesh 本来就没有）。
- **整层可关**：`--no-fx`。关掉之后战斗逻辑、数值、随机序列一个字节都不变。
- **纹理按需加载**：3111 帧不会一次性进内存，用到哪帧读哪帧，读过的缓存。

---

## 5. 验收

### 5.1 无头查表（`--fx-check`，两秒）

```
FX_CHECK PASS
  资源 125 个｜技能引用 1140 处｜命中 469 处
  英雄：引用 182，命中 171
  怪物：引用 958，命中 298
  缺资源 191 个（唯一名）：transform / festering_vapours_target / flashpowder / sniper_mark …
  帧读不到 0；锚点缺字段 0
```

- **英雄 171/182 = 94%**：差的是那 6 个 skinnedmesh 导不出来的
  （`command`、`inspiring_tune`、`festering_vapours_target` 等）。
- **怪物 298/958 = 31%**：这期只导了英雄侧，怪物只命中与英雄共用的
  （`blood_splatter` / `mark_target` 之类）。
- 判 PASS 的口径是「有资源的都能加载出帧、锚点字段齐全」，
  不把「怪物还没导」算成失败——那是进度不是缺陷。

结果同时写 `user://fx_check.log`（Windows 上脚本的 `print` 抓不到，只能看文件）。

### 5.2 画面（引擎内截图）

```
godot --path . -- --start --battle --fx-preview=smite --fx-anchor=feet --fx-t=0.35
              --shot=shots/m57_smite.png --shot-at=2.0
```

| 截图 | 结论 |
|---|---|
| `shots/m57_dbg.png` | 红框=贴图矩形、绿点=锚点。框落在胸口高度，弧光在框内，绿点正好在脚底 → **锚点公式对** |
| `shots/m57_smite.png` | 挥砍弧光横在胸前，方向合理 |
| `shots/m57_blood.png` | 血迹落在胸/arm 高度 |
| `shots/m57_stun.png` | 爆闪正好在头盔位置 |
| `shots/m57_1080.png` | 1080 宽下重跑：红框仍在胸口（x 445–597 / y 293–347）、锚点仍在脚底（539,469），布局无重叠 |

> **踩坑**：Godot 4 的 `OS.get_cmdline_user_args()` **只返回 `--` 之后的参数**。
> 不写 `--` 的话 `--shot=` / `--battle` / `--fx-check` 全部无效，
> 表现是「窗口开出来、停在那儿、什么都不发生」，而且不报错。
> 本仓库旧文档里的命令都省了 `--`，照抄会浪费时间。


---

## 6. 补充：屏幕溅血（受击反馈）

**原版没有受击/硬直动作**。扫了全部 1369 个 `.skel`，动画名里没有
`hit` / `hurt` / `stagger` / `flinch` / `recoil`（只有 `attack_overlay` 的插槽叫 hit、
两个 `snipe_target` 里有 impact 字样）。英雄每职业固定 8 个通用动作
（`idle` / `combat` / `walk` / `investigate` / `camp` / `heroic` / `afflicted` / `defend`），
怪物只有 4 个（`combat` / `attack_melee` / `defend` / `dead`）。
数据里也没有 `.hitfx` 字段（全部特效字段只有 fx / targfx / targchestfx / targheadfx /
misstargfx / deathfx / spawnfx）。

所以挨打时角色**继续播 `combat` 帧**，不换姿势。打击感来自四层叠加：

| 层 | 来源 | 状态 |
|---|---|---|
| 屏幕溅血 | `fx/attack_overlay`（hit / crit / miss，0.79s，`.attack_overlay_pos 960 360`） | **本期接上** |
| 命中点血溅 | `fx/blood_splatter` | 已有 |
| 伤害数字 / 血条 | 代码绘制 | 已有 |
| 音效 / 敌人痛叫 | `assets/audio` | 已有 |

实现：

- 导出 `attack_overlay_hit` / `attack_overlay_crit` 到 `assets/art/fx/`，
  12 fps、scale 0.7、q50 → 两个共 **1.6 MB**（20 帧）。
  `miss` 没导：它的时间轴 alpha 全是 0（原版就是不溅血），导出来是空的。
- `_fx_overlay_play(kind, flip)`：按高度贴合（`k = size.y / manifest.h`），
  水平居中；`flip` 把整块画布镜像，血就溅到另一侧。
- **翻面用 `draw_set_transform` 负缩放**，画完立刻复位——`draw_texture_rect`
  只有 5 个参数，没有 `flip_h`，而且复位漏了会把后面的日志/技能面板一起镜像。
- 同一时刻只留一层：范围技打四个目标会叠四张，屏幕直接糊成红布。
- 画在光照之后、UI 面板之前：要压住场景，但不能盖住技能按钮。
- 验收开关：`--fx-overlay=hit|crit[:flip]` 钉在屏幕上不动，方便截图。

截图：`shots/m57_overlay.png`（右侧/敌方位）、`shots/m57_overlay_flip.png`（左侧/我方位，
UI 未受影响）、`shots/m57_overlay_battle.png`（自动战斗里真实触发）。

> `defend` 不是受击动作：它是主动防御姿态。我们的数据里 9 个技能把它当技能姿势用
> （`antiquarian/cower`、`leper/withstand` + 7 个怪物技能），所以会显示。
> 真正没做的是 DD1 那个无条件「防御」按钮。

---

## 6.5 修正：特效「像贴纸」的三个真原因（M57 修）

截图看着特效不贴，量过之后发现**缩放其实是对的**（刀光宽 337 / 人物本体 411 = 0.82，
屏幕上 151/180 = 0.84，一致），真正的问题有三个：

1. **预览截图的姿势不对**：`--fx-preview` 只钉特效，角色还是 `combat` 站姿，
   刀光横在脸前当然像贴纸。新增 `--fx-pose=attack_sword` 把角色钉在最大前冲点，
   一眼就能看出刀光其实贴着剑走。
2. **出招位移没同步**（真 bug）：`_draw_unit` 画的是 `cx + mo.x`，角色前冲 42px，
   而 `_fx_pos_of` 只取 `_anim_x`，特效留在原地 → 打起来错开半格。
   现在把 `_pose_motion` 的位移和缩放都算进去。
3. **混合模式错了**（最要命）：`smite` 的贴图平均 RGB 只有 (60,64,65)，
   alpha 却高达 186——它是「暗灰 + 高透明」，**只有加法混合才读成光**。
   我们原来用普通 alpha，画出来就是一块灰贴纸。
   原版 `shaders/particle.glsl` 做的正是 `tex0.rgb *= tex0.a` 后加法输出。

实现：`src/view/fx_add_layer.gd`，一个带 `CanvasItemMaterial(BLEND_MODE_ADD)` 的
`Node2D` 子节点，`modulate` 给 **2.2 倍**（素材平均亮度只有 0.25，直接加法还是灰）。
层内标注由 manifest 的 `add` 字段决定：**色度 < 30 的 44 个**走加法
（刀光、火花、光晕、金色爆闪），红色血迹/烟雾/尘土保持普通 alpha。
A/B 对比见 `shots/m57_add_ab.png`（左=普通、中=加法×2.2、右=加法×3.6）。

顺手改的：屏幕溅血从「按高度贴合」改成**按宽度贴合**——
原版资产 1921 宽对 1920 舞台，本来就是铺满宽；按高度贴只能铺到 79%，两边留空。

---

## 7. 还没做

1. **怪物侧特效**：958 处引用只命中 298。导一遍 254 个怪物的 fx 大约 +25 MB，
   等 M40 怪物立绘定了再一起做——现在怪物是剪影，特效再准也对不上身体。
2. **命中/受击之外的时机**：治疗、加护、压力、召唤都还没接特效，
   事件里已经有 `heal` / `stress` / `summon` 分支，接上去只是几行。
3. **加法混合**：帧图是按普通 alpha 合的（DD1 的 additive 在 Unity shader 里，
   文件里没有标记）。想更亮得在 Godot 端给特效单独一层 `BLEND_MODE_ADD` 试。
4. **APK 体积**：帧图约 19 MB（含溅血层 1.6 MB），57 MB 的包会涨到 ~77 MB。
   要压的话优先降 `scale` 到 0.5 或 `fps` 到 15——但血迹类会开始看出跳帧。
5. **49 个 skinnedmesh**：仍然读不通，英雄侧缺 6 个特效
   （`command`、`inspiring_tune`、`festering_vapours_target` 等）。
6. **受击位移**：原版被打会整体后退一点；我们只有 3.2px 抖动。

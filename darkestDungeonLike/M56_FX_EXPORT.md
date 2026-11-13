# M56 —— 战斗特效资源：解包与导帧

> 目标：把 DD1 每个技能的施法/命中特效变成**能播的帧序列**，接进现有战斗屏。
> 关键结论：**资源完整、映射免费（数据里已有）、只差导帧器**。导帧器这一期做完了。

---

## 1. 资源在哪、有多少

源：`D:\Program Files (x86)\Steam\steamapps\common\DarkestDungeon`（app 262060）

| 目录 | skel | 说明 |
|---|---|---|
| `heroes/<id>/fx/` | 136 | 每个英雄技能一条：`crusader.sprite.smite.skel` |
| `monsters/<id>/fx/` | 257 | 每个怪物技能一条：`skeleton_common.sprite.cudgel.skel` |
| `fx/<名字>/` | 120 | 通用：`blood_splatter`、`death_large`、`mark_target`、`torch_flame`、`scout_room`… |
| 合计 | **513** | 三件套恒为 `.skel + .atlas + .png`，贴图共 135 MB |

**映射不用自己建**：`data/heroes.json` / `data/monsters.json` 的 `skills[].art` 里早就有
`fx` / `targfx` / `targchestfx` / `targheadfx` / `targlowfx` / `performerfx`，是从
`<id>.art.darkest` 解析出来的。实测：

- 英雄 105 个技能 → **105 个有 fx，105 个命中 skel（100%）**
- 怪物 552 个技能 → 546 个有 fx，**546 个命中（100%）**
  （剩下 34 个单位是 corpse / cauldron / pew / nest 这类道具，本来就没有技能）

典型一个技能挂两条：`.fx` 跟出手者（挥击/施法），`.targchestfx` 跟目标胸口（基本是 `blood_splatter`）。

---

## 2. 文件格式：Spine 2.1.27 二进制

`.skel` 是 Spine 的二进制骨架，**不是帧图**。一份文件里是
「骨骼 + 插槽 + 图集附件 + 时间轴」。实测：

- 附件构成：**mesh 1155 个 / region 1466 个** —— 一半以上是网格（三角形 + UV），
  只会画 region 的渲染器会丢掉一半图层。
- `additive` 标记 **3520 个插槽里 0 个为真**：DD1 不用 Spine 的加法混合字段，
  发光是 Unity 端 shader 做的。→ 离线导帧按普通 alpha 合成是对的，
  要「亮」的效果得在**运行时**用加法材质。
- FFD（网格顶点变形）**全部为空**，动起来靠骨骼时间轴 + 颜色时间轴：
  - 真运动型：`death_large` 15 条骨骼时间轴，`monster_spawn` 44 条；
  - 纯淡入淡出型：`crusader.smite` 只有 1 条 COLOR 时间轴（弧光是静态图，原地亮灭）。
- 时长普遍被规范化到 1.87s，但**有效动作集中在 0～1.0s**，尾巴是透明保持帧。
  导帧按「最后一条有效关键帧」截断，帧数直接少一半（1.87s→0.83s，56 帧→24 帧）。

---

## 3. 解析器修了两个真 bug

`.tmp/spine/spinerender.py`：

1. **`R.shorts()` 读完不推进指针**（返回列表但 `self.i` 不动）。
   凡是含 mesh 附件的文件，从这里开始整体错位，表现成 M39 里记的
   「区域附件差 1 字节 / `unknown attachment type 8<xx>`」。
   修法：记起始偏移，`self.i += 2*n` 之后再解包。
   > 修正 M39 §6 的结论：region 段落本来就是 name → type → path → 7 floats → color，
   > 一个字节都不差；真正的锅是 mesh 分支里的 `shorts()`。
2. **附件 `path` 为 null 时没回退到附件名** → 图集键变成空串，什么都取不到。
   修法：`read_skin` 里 `if not att['path']: att['path'] = 附件名的键`。

修完解析成功率 **464/513**；剩 49 个含 `skinnedmesh`（蒙皮网格）的还读不通。

---

## 4. 导帧器：`.tmp/spine/fxrender.py`

```bash
python .tmp/spine/fxrender.py <skel> <atlas> <png> <输出目录> [fps] [动画名] [--skip=层名,层名]
```

实现要点：

- **mesh 通路**：按三角形做 仿射 + 遮罩 逐片贴图（PIL `Image.AFFINE` + 多边形蒙版），
  UV 从 `att['uvs']` 取、索引从 `att['tris']` 取；
- **region 通路**：复用原来的四角映射，含 `rotate: true` 的图集还原；
- **采样**：骨骼 rotate/translate/scale 线性插值；插槽 COLOR 线性取 alpha；
  插槽 ATTACHMENT 取「最后一个 ≤ t 的帧」（离散切换，不能插值）；
- **y 轴**：Spine 是 y 向上，画布 y 向下 → 世界点统一 `-(y)` 翻转；
- **截断**：`effective_end()` 取最后一条有效颜色/骨骼关键帧，丢掉尾部透明帧；
- **画布自适应**：每帧按当帧内容 tight-crop，所以帧尺寸会变，
  运行时定位要用「锚点 + 缩放」而不是固定帧尺寸。

### 插槽过滤（必须做）

很多技能特效把**角色本体剪影一起烘进 skel 当遮罩**（`inspiring_cry` 里那具灰白人体），
直接用会多出一个人。插槽名统计（349 个文件）：

```
rim_light 126   shadow 91   defend 61   attack_melee 34   glow 32
smoke 32   aura 28   attack_ranged 26   attack_heal 16   blood 16   ring 15
```

`rim_light` / `shadow` / `defend` / `attack_*` / `combat` 这类都是「角色本体层」，
**导帧黑名单起步就用这几个**；`glow` / `ray*` / `smoke*` / `blood` / `ring` / `spike*` /
`trail` / `aura` / `dust` / `rubble` 才是特效本体。

示例（十字军鼓舞，跳过三层后干净了）：

```bash
python .tmp/spine/fxrender.py .../crusader.sprite.inspiring_cry.{skel,atlas,png} \
    .tmp/fx/cry 30 "" --skip=arm_glow,rim_light,inner_glow
```

---

## 5. 验证（5 个效果，全过）

| 特效 | 特征 | 结果 | 截图 |
|---|---|---|---|
| `fx/blood_splatter` | 2 mesh + 6 骨骼 TL + 颜色 | 溅射形状清晰、随时间扩散淡出 | `shots/m56_fx_blood.png` |
| `crusader.smite` | 1 mesh + 纯 alpha | 弧光形状对，0.1s 亮起、0.83s 灭 | `shots/m56_fx_smite.png` |
| `crusader.stunning_blow_target` | 4 mesh + 6 region + 12 骨骼 TL | 金色爆闪 + 星星逐个浮现 | `shots/m56_fx_stun.png` |
| `crusader.inspiring_cry` | 7 mesh + 1 region，含人体遮罩 | 跳过 3 层后只剩盾牌/火炬徽记 + 光晕 | `shots/m56_fx_cry.png` |
| `skeleton_common.cudgel` | 怪物挥击轨迹 | 弧形挥击轨迹连贯 | `shots/m56_fx_cudgel.png` |

---

## 6. 还没做的

1. **skinnedmesh**：49/513 读不通（`int(r.flt())` 读到 NaN）。先当「该技能没有特效」跳过。
2. **drawOrder 时间轴**：目前按插槽顺序画。DD1 里大概率无所谓，但没验证过。
3. **加法混合**：资源里没有标记，运行时想还原「发光」要用 Godot 的
   `CanvasItemMaterial.BLEND_MODE_ADD` 试出来，不能指望帧图自带宽高。
4. **批量导出**：513 个全导估计 1.5 万帧、几百 MB，得先定「只导英雄 105 条」
   还是「英雄 + 常用怪物」，再决定压不压。
5. **接入**：`expedition_scene.gd` 里 `grep 'targchestfx|"fx"'` 目前 **0 命中**，
   表现层完全没读这些字段。要加的是「一次性特效节点 + 锚点对齐 + 播完销毁」。

---

## 7. 下一步建议

按性价比排：

1. 先接通**英雄 105 条**（体积小、玩家看得最多），`smite` / `blood_splatter` 做样板；
2. 特效节点挂在出手者/目标身上，锚点用「脚底中心」，缩放按 `SPRITE_H / 400`；
3. 命中特效（`blood_splatter`）单独一层，跟伤害数字同时出现；
4. 怪物特效等 M40 的怪物立绘定了再一起做，否则锚点对不上。

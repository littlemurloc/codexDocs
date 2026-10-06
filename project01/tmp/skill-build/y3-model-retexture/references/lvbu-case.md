# 官方吕布案例（2026-10-05）

## 来源与编号

当时当前项目为 `D:\littl\testTempFile\ProjectMonster02`，地图 `map3`；这些路径仅是历史线索，使用时重新查当前项目。

| 对象 | 当时编号 |
| --- | --- |
| 吕布单位物编 | 134235305 |
| 官方吕布模型资源 | 200802 |
| 引擎内部模型 | 504061 |

本机缓存候选安装根曾有 `D:\CliCli\games\2.0\game` 和 `D:\Program Files\y3\games\2.0\game`。身体颜色图在两处的内容一致；不能推断其他资源也一样。

## 原材质引用

`504061_MatInstance` 的 GUID 为 `2baa7546-56cc-ac44-2c7d-bffcefd58b5b`，解码后有两组 `M_UDK_Phone0 / Sanguo` 材质：

| 顺序 | 用途 | 颜色图名称 / GUID | 缓存尺寸 |
| --- | --- | --- | --- |
| 1 | 身体、甲胄、布料 | `504061_d` / `0124172b-8d30-d76d-66b1-fa59578a7ad4` | 512×512 |
| 2 | 方天画戟 | `504061_001_d` / `aff15f17-7d43-e2bb-7110-9ff1e79a9e52` | 256×512 |

两张缓存图均为 `.6` 纹理容器，最高 mip 为 BC1/DXT1；解码后 RGBA Alpha 范围 255–255。

身体法线：`7484a16d-aa2d-6cf2-6edc-15351eedad48`；高光：`cf675d5f-161c-7154-14cf-0b6034d8a755`。
武器法线：`c0b3fc27-b22f-843a-267d-f41667f66c61`；高光：`f89e5034-22ed-bf35-030f-73c48094dc51`。

左上脸、右上布料、中下甲胄等是原展开图视觉识别，未逐岛与网格 UV 验证。材质 2 对应武器按材质实例顺序判断，未在游戏中确认。

## 实际替换动作

单位对象嵌入 ECA 位于当时 `maps/map3/unit/134235305.json`。这类 ECA 不在 `y3_eca` 的 standalone 全局触发器索引范围，搜索吕布返回空结果不能证明动作不存在。

动作 `CHANGE_MODEL_TEXTURE` 的参数顺序为：

1. `CUR_UNIT`，参数类型 `100006`。
2. `UNIT_MODEL(CUR_UNIT)`，类型 `100122`。
3. 字面整数 `1`，类型 `100002`，截图界面对应材质序号。
4. 字面整数 `1`，类型 `100002`，截图界面对应“颜色贴图”。
5. 图片资源，类型 `100115`；当时值 `120767` 是用户测试选用的装备图标，不是原吕布贴图编号。

动作放在 `UNIT_BORN`（创建）事件。身体可保留材质 1，武器拟用材质 2；类型 1 的含义来自当时 JSON 与截图对照，不把它推广为其他版本所有模型的枚举保证。

## 重绘提示词的关键内容

这次用户选择银白甲胄与冰蓝布料，不把它设为后续任务默认风格。

```text
Use case: precise-object-edit.
Asset: basecolor UV texture atlas for an existing Y3 model.
Edit target: the supplied original atlas; preserve its exact aspect ratio.
Change only existing gold/bronze armor into cold silver-white steel,
and red cloth/insets into ice blue. Preserve skin, eyes, hair and original shading.
Keep every UV island, outline, seam, engraving and landmark at exactly the
same normalized XY coordinates. No repacking, cropping, rotating, mirroring,
new shapes, margins, labels, wire overlays, character render or perspective.
Output only a flat opaque texture atlas.
```

生成母版的实测尺寸为身体 1254×1254、武器 887×1774，比例正确；最终以 Lanczos 缩小至原尺寸，保存不透明 RGB PNG。生成提示词要求原尺寸并不保证工具实际按该尺寸输出，必须读文件元数据。

## 项目内已交付资源

从项目根解析：`assets/art/characters/lvbu/y3-texture-silver-ice-v01/`。其中 `README.md`、`original-texture-metadata.json`、`final-texture-metadata.json`、`generation-prompts.json` 记录原始来源、规范化结果和完整生成提示词。最终 ZIP：`deliverables/lvbu-silver-ice-textures-v01.zip`。

当时完成了原图解码、尺寸/模式检查和逐图视觉检查；没有做 Y3 导入或游戏内接缝测试。后续不能继承为“实机验证通过”。

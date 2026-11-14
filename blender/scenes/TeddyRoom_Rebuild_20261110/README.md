# 熊娃娃房间：从空场景重新制作

日期：2026-11-10。入口 [三图与工序预览](index.html)。

本次从 Blender `--factory-startup` 开始，先删除默认对象，再用新脚本建立白模、模型、材质和灯光。**没有加载、追加或修改上一版 3D 场景。** 上一版只读取其最终 PNG 作为对比。已有脚本仅在开工学习时阅读，没有执行旧搭建脚本。

## 三张对比图

1. `comparison/01_reference.png`：用户原始参考图，原样复制。
2. `comparison/02_previous.png`：上一版的最终 Blender 渲染，原样复制。
3. `comparison/03_rebuild.png`：本次 `scene_cycles.blend` 实际输出的最终主镜头，原样复制自 `renders/05_final.png`。

三者均为 3:2，全图展示，不裁切旧版以制造对齐。新版主镜头按原图桌面、主熊、吊灯、地毯等位置匹配；相机位置不是从单图恢复出的唯一真实参数。见 `camera_alignment.json`。

## 新增规范落实

- [需求与物件清单](scene_brief.md)：15 组可见物件的外观、内容与位置约束。
- [实际视觉评审](visual_review.md)：逐阶段问题、修正和未完全保留的细节。
- [工作状态](work_state.md)：学习记录、检查点和接续说明。
- 原图案直接映射到独立纸片 UV，不再把墙画改成随机涂鸦。原图纹理仅用在纸画/桌面画纸，没有整场照片背景板；主体、家具和房间是三维模型。
- 主熊、凳子、玩具和角色均重新建模；构图、图案保留与资产可见性分别检查。

## 工程与阶段

| 文件 | 内容 |
|---|---|
| `01_blockout.blend` | 真正仅大体块的空场景白模检查点 |
| `02_assets.blend` | 新建模型、纸画与程序材质、中性照明 |
| `03_lighting.blend` | 第一轮氛围灯光 |
| `04_review.blend` | 几轮物件/灯光纠偏后的新工程 |
| `scene_cycles.blend` | 最终离线成片，主相机 Hero，1440×960、128 采样 |
| `scene_realtime.blend` | EEVEE 浏览版本，关闭叠加和 Gizmos，隐藏视口雾及侧光遮挡片，侧光能量另作调整 |

实时版与离线版的阴影、反射、体积和曝光观感有差异；实时版未做性能测试。八个相机用于诊断，不代表完整可探索关卡。俯视、反向、凳子和墙面诊断图暂时隐藏顶棚/雾/侧光遮挡片并加检查灯；拍完恢复。

## 从零复现

在此目录的 PowerShell 执行；仅在本任务的新后台进程使用 `base`。`assets`、`refine` 是顺序追加，必须从指定前一检查点运行，不能在成品重复追加。

```powershell
$blenderExe = 'D:\Program Files\Blender Foundation\Blender 4.2\blender.exe'
& $blenderExe --background --factory-startup --python-exit-code 1 --python source/rebuild.py -- base
& $blenderExe --background 01_blockout.blend --python-exit-code 1 --python source/rebuild.py -- assets
& $blenderExe --background 02_assets.blend --python-exit-code 1 --python source/rebuild.py -- lighting
& $blenderExe --background 03_lighting.blend --python-exit-code 1 --python source/refine.py
& $blenderExe --background 04_review.blend --python-exit-code 1 --python source/deliver.py -- final
& $blenderExe --background scene_cycles.blend --python-exit-code 1 --python source/deliver.py -- views
& $blenderExe --background scene_cycles.blend --python-exit-code 1 --python source/deliver.py -- realtime
& $blenderExe --background scene_cycles.blend --python-exit-code 1 --python source/deliver.py -- verify
& $blenderExe --background scene_realtime.blend --python-exit-code 1 --python source/check_realtime.py
```

Blender 4.2.3 LTS / RTX 4060 Laptop OptiX；脚本内对 GPU 初始化不可用提供 CPU 默认回退。贴图随工程打包，路径按脚本目录推导；从零需要本目录的 `reference.png`。

`prepare_preview.cjs` 是本机对照页与基线哈希校验辅助工具，另外读取 `D:/codex/blender` 中的旧案例和迁移清单；搬到另一台机器时需要调整这部分基线路径。它不参与三维搭建或渲染。项目归档脚本是一次性工具，不要在已存在的目标目录重复执行。

## 限制与来源

米制尺寸、隐藏结构与侧窗为设计补全。角色精细造型、家具磨损、散物与布料仍有明显差异，逐项详见评审。原图画纸保留源照明信息，不是无光照扫描材质。没有进行游戏引擎、碰撞、导航或 FPS 验收。

参考图权利归原权利人。本次未使用图像生成服务产出最终图或三维模型，所有新版场景预览来自 Blender 实际渲染。原参考图用于本地复刻实验，未声称获得其商业使用权。

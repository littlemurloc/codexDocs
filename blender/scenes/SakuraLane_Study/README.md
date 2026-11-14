# 雨后樱花街：单张氛围图到三维场景

日期：2026-11-09。输入为用户提供的一张室外参考图。本项目用可编辑的三维场景展示制作工序，所有阶段预览均由 Blender 实际渲染。

## 查看入口

- `index.html`：原图、布局、白模、立面、湿地面、最终主镜头和多视角的本地预览页；点击图片可以放大。
- `scene_cycles.blend`：Cycles 成片工程。
- `scene_realtime.blend`：EEVEE 浏览工程，关闭辅助叠加与 Gizmos，隐藏视口中的远处体积雾。
- `source/build_lane.py`：可复现制作脚本。
- `scene_spec.json`：设计尺度与高度假设。
- `validation.json`：从独立加载的工程中读取的检查结果。

这是根据参考图提出的一套空间解释。参考图没有提供的建筑背面、远端街口、庭院与树木根部均为设计补全，未声称精确重建。

## 各阶段的目的与实际修正

| 阶段 | 内容 | 观察与修正 |
|---|---|---|
| 1 分析 | 偏右消失方向、低机位、左高右低建筑与湿街面 | 地面、路缘、门前台阶和浅水分开描述 |
| 2 白模 | 街宽、建筑体块、挑檐、架空通道和主镜头 | 先看空间，不用材质掩盖轮廓问题 |
| 3 立面 | 木梁、门板、窗格、阳台、屋檐和瓦片 | 样板检查与沿街模块扩展；远端原本过空，后续增加转向街口的遮挡建筑 |
| 4 地面与布景 | 石板、路缘、排水格栅、浅水、招牌、灯笼、木桶、凸面镜、樱花与落瓣 | 初版石板缝过宽、水像银色薄片、樱花被屋顶遮挡；修正缝隙、高差、水材质和树冠位置 |
| 5 氛围 | 柔和日光、天空、暖灯笼与远处薄雾 | 日光沿街照入，前景保持清楚，远处以体积效果建立层次 |
| 6 多视角 | 主镜头、立面、地面、反向、高位、中段、右店铺、俯视 | 发现远端地面未延伸和模块透光缝，补齐支撑地面、接缝与完整坡屋面后重新输出；俯视关闭远处薄雾 |
| 7 验证 | 在独立 Blender 进程中重开，并输出小图 | 检查相机、打包图像和缺失依赖，不把技术检查当成美术质量证明 |

本项目没有录制逐对象建模过程。阶段图是制作检查点，不是连续建模录像。

## 高度与材质如何表达

- 米制尺度是设计选择，不能据此推导真实街道尺寸。
- 基础街面总体平缓，石板只加入少量局部高差。
- 路缘顶约 0.27 米，路边步行面与门前台阶独立建模。
- 积水是贴近石板表面的独立浅水面，另有连续湿润粗糙度变化；没有把原图暗斑全部当作凹坑。
- 建筑约 5–7 米高，架空通道桥面约 3.95 米。
- 木材、灰泥、屋面和石材使用生成底色图集；并非实测或扫描 PBR 材质。

## 资产与工具

本机 Blender 4.2.3 LTS；Cycles 使用可用的 RTX 4060 Laptop GPU / OptiX，脚本包含 CPU 回退。没有安装软件，没有调用外部付费建模服务，也没有要求用户打开软件。

几何、招牌文字、灯具、树枝、花瓣、石板和道具由脚本生成。招牌使用本机字体并随工程打包。底色图集通过内置 image_gen 工具生成，完整提示词见 `assets/generation_prompt.md`，项目内保存于 `assets/material_atlas.png`。本示例未使用图片模型生成最终场景渲染。

用户原图保存在 `reference.png` 作为本地参考。参考作品的权利属于其权利人。

## 从零复现

在此目录打开 PowerShell，按顺序执行。`base` 会清空所在 Blender 进程的场景，因此必须在新的后台进程里运行，不要在用户其他工程中执行。

```powershell
$blenderExe = 'D:\Program Files\Blender Foundation\Blender 4.2\blender.exe'
& $blenderExe --background --factory-startup --python-exit-code 1 --python source/build_lane.py -- base
& $blenderExe --background 02_blockout.blend --python-exit-code 1 --python source/build_lane.py -- facade
& $blenderExe --background 03_facades.blend --python-exit-code 1 --python source/build_lane.py -- dress
& $blenderExe --background 04_dressed.blend --python-exit-code 1 --python source/build_lane.py -- lighting
& $blenderExe --background scene_cycles.blend --python-exit-code 1 --python source/build_lane.py -- integration
& $blenderExe --background scene_cycles.blend --python-exit-code 1 --python source/build_lane.py -- views
& $blenderExe --background scene_cycles.blend --python-exit-code 1 --python source/build_lane.py -- verify
& $blenderExe --background scene_cycles.blend --python-exit-code 1 --python source/build_lane.py -- realtime
```

各阶段是顺序搭建脚本，不应在已完成工程上重复执行 `facade` 或 `dress`，否则会产生重复资产。恢复时加载前一检查点。

## 当前用途边界

本项目是沿街单镜头与多视角检查用原型。与参考图相比，建筑重复性、屋面形状、树冠自然度、细部磨损、天空及光影仍需继续美术精修。

俯视图会显示设计中的建筑体块与有限深度；房屋内部和背面没有作为完整可探索建筑交付。街道远端是设计的转向遮挡区域，不代表原地点真实布局。

EEVEE 与 Cycles 的间接光、反射和体积表现不同。实时版本用于检查空间和浏览，不保证与 Cycles 成片逐像素一致；尚未进行目标游戏引擎导入、碰撞、导航或性能测试。未报告参考图相似度百分比或游戏 FPS。

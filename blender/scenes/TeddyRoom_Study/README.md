# 单图到三维：玩偶房间工序学习原型

本项目以用户提供的一张氛围图为依据，演示空间解释、白模检查、材质检查、灯光迭代、多视角和重新加载验证。

## 当前保存的两个版本

- `scene_realtime.blend`：用户浏览后的当前场景，使用 EEVEE、关闭辅助叠加与 Gizmos、临时隐藏视口薄雾，并保留当前查看角度与最大化视口。
- `scene.blend`：此前生成的 Cycles 渲染工程，保留原照明和薄雾配置。

两种版本均已保存到本目录。项目 `learning/packages/` 中重新生成的当前完整包包含实时版本；`learning/packages/original/` 保留早于该版本的历史包。此文不表示当前桌面正在打开哪个文件。

## 先看什么

打开 `index.html`。页面包含原图、初始布局、各阶段预览及八视角。所有场景图均为 Blender 实际渲染；本项目没有使用图像生成来替代三维结果，也没有进行摄影测量。

## 运行方式

- 已在本机 Blender 4.2.3 LTS 后台执行，使用 RTX 4060 Laptop GPU 的 Cycles/OptiX 路径。
- 搭建与阶段渲染通过本地后台进程完成；后续通过 Blender GUI 调整并保存实时浏览版本。未依赖 MCP 连接。
- `source/build_scene.py` 是可重建的制作脚本；它只应在新的空白后台进程中执行 `blockout`，该模式会清空该进程中的当前场景。
- 初始布局记录在 `scene_spec.json`。这是设计假设，不是从照片测量出的坐标。
- 构图修正后，脚本和 `scene.blend` 表达最终实现；`scene_as_built.json` 记录从最终工程读取的部分对象边界。初始草案与最终实现有明确差异。

在本目录下的 PowerShell 中执行，按需替换 Blender 路径：

```powershell
$blenderExe = 'D:\Program Files\Blender Foundation\Blender 4.2\blender.exe'
& $blenderExe --background --factory-startup --python-exit-code 1 --python source/build_scene.py -- blockout
& $blenderExe --background scene.blend --python-exit-code 1 --python source/build_scene.py -- materials
& $blenderExe --background scene.blend --python-exit-code 1 --python source/build_scene.py -- final
& $blenderExe --background scene.blend --python-exit-code 1 --python source/build_scene.py -- views
& $blenderExe --background scene.blend --python-exit-code 1 --python source/build_scene.py -- verify
```

脚本模式是顺序制作步骤。`materials` 只保存材质检查点；`final` 保存最终主工程；`views` 添加渲染结果并保存主相机。不要在用户正在编辑的文件里随意重复运行完整搭建模式。

## 阶段与观察

| 阶段 | 实际检查 | 修正或结果 |
|---|---|---|
| 1 原图分析 | 桌面、地毯、柜体、玩偶、光源与遮挡 | 明确平地假设，隐藏区域合理设计 |
| 2 布局 | 俯视关系与支撑高度 | 采用米制设计尺度，桌面顶约 0.94 米 |
| 3 白模 | 实际打开主镜头渲染 | 初版柜体偏向中央、吊灯偏低；第二版将柜体向外移、吊灯上移 |
| 4 材质与模型 | 均匀照明下检查 | 家具、玩偶组合、纸张曲线涂鸦、地毯和程序材质形成可编辑模型 |
| 5 灯光 | 比较三个版本的渲染 | 第一版侧光过强，第二版整体过暗，第三版增强中心光池与局部斜光 |
| 6 多视角 | 主镜头、左右、反向、俯视、桌面细节及两个角落 | 通过不同视角展示三维一致性，也暴露隐藏区域为设计补全 |
| 7 重开验证 | 独立 Blender 进程加载并重新渲染 | 详见 validation.json 和 renders/07_reopen_check.png |

制作脚本在初始搭建时已经创建了部分细节与材质；阶段图是对白模、材质和照明的分项检查，不是逐对象建模过程的录像。

## 多视角说明

- `view_hero.png`：主镜头。
- `view_left.png`、`view_right.png`：左右偏移，检验遮挡和物件纵深。
- `view_reverse.png`：反向视角。镜头后方原本是开放拍摄面，因此视图可能看到外部背景；它不是已补齐的封闭可玩关卡。
- `view_overhead.png`：俯视诊断视图，隐藏顶棚、吊灯遮挡与薄雾，并增加检查照明。它不是原照明下的最终效果图。
- `view_table_detail.png`：桌面与主熊细节。
- `view_left_corner.png`、`view_right_corner.png`：角落观察。

八视角不是围绕一个不可见目标重新生成八次图像，而是从同一个可编辑工程中渲染。

## 当前视觉差异与用途边界

这是学习工序用的三维解释原型，未达到原画精细复刻质量：

- 玩偶和前景角色是简单程序化组合，轮廓、表情、衣料与原图有明显差异。
- 家具更规整，缺少原图的形变、精细磨损和复杂结构。
- 涂鸦为原创曲线示意，未复制原图笔迹。
- 右侧窗洞是对光源的设计解释，并非原图明确提供的建筑事实。
- 斜光、薄雾与后期暗角建立了明暗层次，但光影位置、材质表现和构图仍与原图不同。
- 地板采用程序化板材表达；不能从原图确认真实材质。
- 原图未提供的背面与空间只完成了支撑本学习示例的设计，没有将其验证为可漫游关卡。
- 没有进行游戏引擎导入、碰撞、导航或帧率测试。
- 未计算或声称参考图相似度百分比。

## 资产与依赖

用户原图只作为本地参考保留于 `reference.png`。几何与材质由脚本构建，墙上图画是可编辑曲线。工程无需下载素材或调用付费模型。原图所示作品的权利属于其权利人，本学习示例不赋予商业使用许可。

进一步提高相似度，应优先精修主熊与前景角色轮廓，调整柜体与座具结构，再对主镜头做更精确的边缘对照；随后补充布料、木材和墙面的真实表面细节。

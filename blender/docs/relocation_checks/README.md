# 迁移后工程检查

这里的报告来自新项目路径下的独立 Blender 进程，不覆盖案例原有的历史验证。

| 工程 | 报告 | 检查范围 |
|---|---|---|
| 室内 Cycles | [teddy_cycles.json](teddy_cycles.json) · [小图](teddy_cycles.png) | 加载、图像/字体/链接库依赖、相机、低采样实际渲染 |
| 室内 EEVEE | [teddy_realtime.json](teddy_realtime.json) | 加载、依赖、相机与引擎，未自动做实时性能测试 |
| 室外 Cycles | [sakura_cycles.json](sakura_cycles.json) · [小图](sakura_cycles.png) | 加载、图像/字体/链接库依赖、相机、低采样实际渲染 |
| 室外 EEVEE | [sakura_realtime.json](sakura_realtime.json) | 加载、依赖、相机与引擎，未自动做实时性能测试 |

`*.json.log` 是本次独立进程日志。运行 `tools/check_relocated_blends.ps1` 可重做；检查不保存 `.blend`。它会降低输出尺寸和采样，不重置曝光、灯光、雾与合成器。

这些诊断证明迁移后的文件可用，不等于视觉还原评估或游戏性能验收。实际图像观察结果在 [visual_review.md](visual_review.md) 中记录。

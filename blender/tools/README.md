# 项目工具

所有工具从自身路径找到项目根目录；不依赖原工作区。以下命令在项目根目录的 PowerShell 执行。

| 工具 | 用途 | 是否修改场景 |
|---|---|---|
| `build_learning_packages.ps1` | 从当前两套场景生成当前 ZIP 和包清单；替换当前包，保留 original 历史包 | 否 |
| `verify_project.ps1` | 检查 96 个迁入文件、允许的文档更新、必需文件、多视角、每个 ZIP 条目哈希、本地链接和迁移检查；输出 JSON | 否 |
| `check_relocated_blends.ps1` | 四个独立 Blender 进程检查迁移后最终工程；两份 Cycles 工程渲染小图 | 否，只输出诊断文件 |
| `verify_blender_relocation.py` | 上述工具调用的 Blender Python；检查图像/字体/链接库与相机，保留艺术参数，只降低诊断分辨率/采样 | 不保存 blend |
| `copy_legacy_resources.ps1` | 本次一次性复制与 SHA256 校验的历史脚本；有旧路径，目标存在即中止 | 不要重复执行 |
| `finish_legacy_move.ps1` | 本次一次性清理：核对源未变更、目标最终哈希及明确目录边界后移除旧来源；需要旧路径写权限 | 不改场景，但会删除已迁入的旧来源 |

迁移后工程检查：

```powershell
.\tools\check_relocated_blends.ps1
.\tools\build_learning_packages.ps1
.\tools\verify_project.ps1
```

若 Blender 安装位置不同，对首条命令加 `-BlenderExe '实际路径'`。验证过程不保存工程，既有 `scene_spec`、艺术设置和原始渲染不被覆盖。低采样小图仅检验可重开渲染，可能与原成片有噪点/分辨率差异。检查完仍须实际看图；脚本不判断美术相似度。

阶段搭建命令另见各场景 README，不在这里合并为一个无条件执行的“全跑”按钮。新增场景应配置自己的检查项，不把本工具固定的案例名和八相机数量当作所有项目的通用约束。

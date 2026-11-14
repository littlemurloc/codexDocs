# 资源迁入记录

迁入项目：`D:\codex\blender`。操作开始于 2026-11-09，文档与校验整理于 2026-11-10。

**已完成移动。** 2026-11-10 获得旧路径写权限后，再次核对源文件未变更、目标最终哈希与目录边界，移除了上表对应的七个旧来源目标。96 个文件的 `source_removed` 均为 `true`，两套场景现在以本项目为工作位置。

## 范围

原位置：`C:\Users\littl\Documents\Codex\2026-11-05\z`。

| 旧目录下的位置 | 新项目位置 |
|---|---|
| `outputs/TeddyRoom_Study/` | `scenes/TeddyRoom_Study/` |
| `outputs/SakuraLane_Study/` | `scenes/SakuraLane_Study/` |
| `outputs/*_完整学习包.zip`（两份） | `learning/packages/original/` |
| `outputs/Blender_Agent_场景制作与视觉验收指南.md` | `learning/materials/` |
| `work/teddy_scene/` | `archive/run_logs/teddy_scene/` |
| `work/sakura_scene/` | `archive/run_logs/sakura_scene/` |

总计 96 个原始文件、509,298,563 字节，复制时逐文件核对 SHA256。详见 [migration_manifest.json](migration_manifest.json)。本次也保留了自动备份与失败日志。工具供应商默认缓存中的生成图副本、Blender 安装和系统字体不属于这两套场景的源目录；纹理项目副本、提示词和工程内打包依赖已随场景迁入。

## 版本与改动

- 两份原 ZIP 原样保留在 `original/`，用于溯源。
- 当前 ZIP 从 `scenes/` 重新生成，补入实时工程，排除 `*.blend1` 自动备份，记录在 `learning/packages/package_manifest.json`。
- 修改室内 README 中过时的“当前窗口”与历史 ZIP 描述，说明实际 GUI 浏览版本；未改模型几何、材质、源码或历史渲染。
- 新增根目录规范、Pipeline、经验总结、任务模板与验证工具。

清单的 `original_sha256` 与 `copied_sha256` 证明迁入时原样复制；`final_sha256` 表示整理后文件，修改过的文件另外标注。不能将文档整理后的哈希变化误当作原始复制失败。

## 校验与源文件清理状态

先完成复制校验、项目整理和迁移后 Blender 重开检查，再清理旧来源。当前状态以机器记录为准：

- [迁移清单](migration_manifest.json)：`status` 和各文件 `source_removed`，完成移动应为全部已删除来源。
- [项目校验](project_verification.json)：当前目录结构、学习包及原始资源保留检查。
- [迁移后工程检查](relocation_checks/README.md)：四份最终工程的独立进程加载结果与两套小图。

清理仅针对上表列出的旧位置；不得删除整个旧工作区。删除前再次比较源哈希，检测文件是否在迁入后被修改。旧来源目录当前不在项目可写沙箱内，需要运行环境授予该具体路径写权限，才能完成移除；若权限未获准，必须明确报告“已复制，旧来源仍保留”。

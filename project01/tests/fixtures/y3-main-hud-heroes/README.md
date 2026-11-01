# 主HUD固定回归与局部回退样本

2026-11-01清理后，测试不依赖tmp或运行中的编辑器。压缩JSON是工程样本，不含玩家存档，不是完整地图包。完整哈希见[样本清单](../../../deliverables/evidence/main-hud-work-cleanup-20261101/fixture-manifest.json)，测试对实际消费的样本核对固定SHA256。

| 样本 | 来源与用途 |
| --- | --- |
| source.json.gz | 改造前GameHUD、universe01、动态创建函数、镜像06绑定、两份目录索引及函数模板；保留原版HUD及相关ECA，可作人工局部回退比较 |
| published-v1.json.gz | 首次发布的刷新函数、公共触发器与GameHUD，重现未注册监听和非法空UI引用 |
| published-repair01.json.gz | 第一轮修订后仍不能点击的触发器和GameHUD，保留失败历史 |
| published-repair02.json.gz | 第二轮仍未收到点击的触发器，保留错误四项注册引用实际样本 |
| accepted-hud.json.gz | 后续已发布、获代表试玩确认的GameHUD、公共触发器、刷新函数及universe01；来自动态登记候选只读支持与战斗显隐候选，含无诊断、左侧边界、聚焦和显隐版本 |
| dynamic-registration.json.gz | 动态英雄登记修复前／后创建函数及实际受测HUD、触发器、刷新函数、镜像06只读支持 |

运行：

```powershell
python -B tools/test_y3_main_hud_hero_layout.py
python -B tools/test_y3_dynamic_hero_manual_cards.py
```

HUD回归先从source执行纯历史构建，再由accepted-hud覆盖上述4份资源，以检查实际发布的交互／显隐版本。创建和镜像绑定的原动作保留检查仍针对历史HUD构建，动态登记增量由第二套回归单独验证；前者不作为含后续全部扩展的可发布包。--candidate-dir仍可只读覆盖未来候选，不写地图。

动态回归直接执行实际发布登记块，并要求纯补丁从before重建的结果与固定after完整相同；测试现有自动施法处理器对新行的更新。原生表首次字段写入建行按同图开局模式模拟，缺失字段读取仍失败。

模型只按已核对的整数配置节点建立本根监听，拒绝将四项动作引用当注册；事件必须来自实际声明控件，非法空资源不能自动当None。历史23项及首次修订通过次数保留当时模型限制。当前34项HUD与9项登记回归的单位、UI、绑定与表API是有界替身，不替代引擎创建、命中、渲染、抽牌、施法和多人验证。

本轮所有一次性stage／publish／rebase入口已删除。保留的两个维护模块只提供纯构建／补丁辅助函数，直接运行退出提示，不能重跑历史全量迁移。

原版source可提取旧HUD及相关ECA作逐项比较，不提供一键回滚；新增资源、目录登记和后续有效修改须一并审查。各轮tmp整图过程备份已按授权删除，历史路径不再可回退。正式记录与原生失败／成功证据见[清理记录](../../../deliverables/主HUD工作规范落档与过程清理-2026-11-01.md)。

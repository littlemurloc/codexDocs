# 2026-10-29／30 回归输入

按负责人要求清理过程文件时，从当时的已验证候选中提取；仅用于离线回归，不是完整地图备份、编辑器导入包或待发布候选。gzip只用于压缩JSON，加载时校验manifest登记的SHA256，不解包回tmp，也不写入历史验收回执。

| 文件 | 用途 |
| --- | --- |
| damage-context.json.gz | 第01步伤害上下文的原ECA／改后ECA与逆变换记录 |
| combat-batch02.json.gz | 兵种克制原／改后函数、180资源精确日志开关对照 |
| combat-batch03.json.gz | 能量显示、重建与26核心Buff、47条旧诊断的原／改后输入 |
| forge.json.gz | 锻造最终配置、ECA及共享函数原分支；保留最小路线筛选函数作为有明确断言消费的历史反例 |
| card-ui.json.gz | 库存角标与同步演出改动、必要原UI动作及只读辅助函数样本 |

维护入口为`tools/y3_recent_work_fixtures.py`。五份压缩样本合计945,655字节，代替对586份临时文件的测试依赖。保留当前变换／构建辅助函数和精确追踪开关；初次全量部署入口及一次性锻造／重复函数清理发布脚本已退役，不通过这些输入重建或发布旧地图。

回归命令：

```powershell
python -B tools/test_y3_damage_context_optimization.py
python -B tools/test_y3_combat_optimization_batch02.py
python -B tools/test_y3_combat_optimization_batch03.py
python -B tools/test_y3_forge_command_cards.py
python -B tools/test_y3_card_ui_polish.py
```

五组分别为11／11／24／17／7项，共70项。部分既有军略解释器和原生结构校验仍使用本机Y3工具／工程，不宣称是独立引擎。样本固定到明确版本；未来玩法调整时应说明如何更新用例，不能自动覆盖历史反例让测试通过。

验收摘要、迁移来源与清理回执见[保留证据](../../../deliverables/evidence/y3-recent-work-cleanup-20261030/README.md)。

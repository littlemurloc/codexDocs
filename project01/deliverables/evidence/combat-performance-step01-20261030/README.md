# 自动战斗性能优化第01步：证据

- `littlemurloc_2026_10_30_00_58_45.log`：负责人重开并进入战斗后的代表局完整日志，从Y3轮转history归档。
- `step01-runtime-observation.json`：日志计数、原文件哈希、当前磁盘候选哈希及验证边界。
- `before-optimization-profiler.png`：负责人提供的改前火焰图截图原文件；仅作基线线索，前后场景与统计范围还没有对齐。
- `after-optimization-profiler-01.png`、`after-profiler-observation-01.json`：后续改后截图与只读数值记录；可见最高78.88 ms，表中统计范围约8 ms，未与改前统一。

目前确认代表局存在正常施法、伤害及Buff执行记录且没有Error/Fatal，并收到一份改后火焰图。前后场景和统计范围未对齐，未证明性能改善比例；没有公共触发器内存导出，未把磁盘哈希标为加载回读通过。

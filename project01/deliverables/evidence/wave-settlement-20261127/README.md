# 波次奖励与战报交付证据

- `release-receipts/`：各阶段正式写入的历史回执，含目标路径和前后哈希。旧回执中的 `formal_y3_runtime_verified=false` 表示当时发布窗口未验证；不覆盖后来用户对最终波次卷轴的反馈。首次卡住的结算回执与最终写入回执分开。
- `settlement-local-rollback.zip`：最终结算发布前的 3 个既有文件及工程头快照。只用于人工比对和局部回退；不能整包覆盖正式工程，不应恢复未被修改的工程头。若要回退，先通过最终回执校验当前 5 路径，关闭编辑器，再分别恢复 3 个旧文件及移除 2 个新元件。它不是整图备份，不包含波次模块回退。
- `formal-path-hashes.json`：本次清理的正式范围和清理前后字节校验；历史发布过程与 Y3 实机验收不以此替代。
- `verification.json`：隔离副本的两条结算日志摘录、Error／Fatal 计数和清理前模型复测数量。
- `cleanup-summary.json`：清理目录、文件数量和容量。隔离副本 `CodexSettlementUI`、废弃候选、旧发布入口及网页过渡稿不再保留；保留最终布局参考和本目录证据。

固定验收边界：历史 7 项波次模型、5 项生成 ECA 模型在清理前重跑通过；正式战报曾在隔离副本得到用户正常反馈，两次结算日志无 Error／Fatal。清理后用[只读检查器](../../../tools/audit_y3_wave_settlement.py)核对当前正式文件，正式战报的重新加载和实机仍待用户反馈。

```powershell
python tools/audit_y3_wave_settlement.py D:/littl/testTempFile/ProjectMonster02
```

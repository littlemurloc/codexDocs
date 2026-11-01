# 本次HUD工作清理证据

- `delete-manifest.json`：限于本次工作区过程目录／废弃工具的删除清单，每文件大小与SHA256；不包含正式地图删除。
- `fixture-manifest.json`：保留的6份压缩工程样本哈希。新迁移2份，原版及3份失败历史样本保持。
- `historical-receipts/`：删除过程目录前保留、此前正式证据目录未已有相同内容的小型回执。56份与现有证据字节相同的新复制件已去重，原证据引用见`deduplicated-receipts.json`。历史published／editor_verified字段不改写，旧tmp备份路径清理后失效。
- `selected-skin-reference/`：选定B方案参考与资源映射。只采用左侧，右侧预览未采用；重排草图与其他合成过程删除。
- `map-protection-before.json`、`header-protection-before.json`：本轮工作区清理前对正式工程只读取哈希，供清理后核对不曾写回。

`delete-receipt.json`记录实际删除160份过程文件；`cleanup-regression.json`和两份测试log记录删除后34＋9项回归、样本／入口退役与正式地图5429文件及header未变检查。原始失败和成功日志仍在各任务原证据目录，不重复搬入本目录。维护入口、回退范围及完整结论见[正式清理记录](../../主HUD工作规范落档与过程清理-2026-11-01.md)。

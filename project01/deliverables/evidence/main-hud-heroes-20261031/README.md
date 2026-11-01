# 主HUD改造发布证据

2026-10-31保存关闭后定向发布9份文件。这里保留候选哈希、23项离线检查和输出、发布回执、磁盘写后检查及MCP有限引用验证；不包含玩家存档或完整地图备份。

`manifest.json`是发布前候选清单，其未发布标记保留历史语义；实际写入事实见`published.json`。`checks.json`是离线验证，`post-publish-check.json`是实际磁盘内容和静态事件配对，`mcp-post-publish-validation.json`是插件结构和有限引用检查。它们均不替代编辑器内存、原生UI或试玩验收。

2026-11-01负责人授权清理后，各轮tmp整图过程备份及旧发布工具已撤除，历史路径不再可回退。原版HUD及相关ECA仍保存在`tests/fixtures/y3-main-hud-heroes/source.json.gz`，当前HUD及动态登记测试输入也已固定，不依赖tmp；这是局部工程样本，不是整图备份。范围和清理后检查见[本次清理记录](../../主HUD工作规范落档与过程清理-2026-11-01.md)。

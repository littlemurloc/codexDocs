# 安全区UI固定回归样本

本目录是2026-11-19收尾保留的测试输入，**不是可导入或可重新发布的地图资源包**。

- `fixtures.zip`：约3.84MiB，包含五个已发布阶段的必要输入／输出和只读依赖。
- `manifest.json`：归档哈希、每项文件哈希、来源阶段及覆盖用途。
- `tools/safezone_ui_fixtures.py`按需解包到系统临时目录，进程退出自动移除；原始夹具不改写。测试不读取已删除的工程历史tmp，也不要求本机存在正式Y3工程。
- 函数／触发器身份检查使用当日冻结的命名空间目录；当前正式工程的新变化需另用Y3索引工具检查，不能用冻结目录冒充实时扫描。

五组样本：`skin`八皮肤、`inner`兵种网格revision-03、`detail`详情还原最终关闭修复、`skills`六技能空类型修复、`attributes`高星级属性最终修复。旧阶段断言用于保护当时改动，不能把各阶段叠加视作一个当前全量游戏模拟。

运行以下脚本，使用本机Python即可；当前Codex Python路径见收尾记录：

```text
tools/test_y3_safezone_skin_switch.py
tools/test_y3_safezone_inner_pages.py
tools/test_y3_hero_detail_restore.py
tools/test_y3_hero_skill_overview.py
tools/test_y3_hero_attribute_display_guard.py
tools/test_safezone_cleanup_integrity.py
```

报告写入`deliverables/evidence/safezone-closeout-20261119/regression/`。旧工具的stage、publish及一次性repair入口永久退役，清掉历史发布标记也不能重新启用；纯构建函数和只读原生保存检查仍保留供后续维护参考。

现有夹具仅含相关UI、配置／物编元数据和局部ECA样本，不包含完整地图、地形和玩家存档；不能保证整图回退。正式资源仍位于原Y3工程和`assets/art/`。

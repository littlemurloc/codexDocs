# UI Asset Manifest

2026-11-19安全区收尾：正式美术库与确认参考图全部保留，仅清理实装过程tmp、废弃迁移脚本和对应缓存。完整当前状态、高星级修复验收及清理边界见[收尾复盘](../../../deliverables/安全区界面实装复盘与清理-2026-11-19.md)；下表阶段记录不替代该最新结论。

当前 UI 资源索引只记录资源状态，不改变玩法规则。旧版三选一、装备页签、羁绊页签只作为历史视觉参考。

安全区英雄详情最新状态：立绘扩大至300×420，新增完整六技能及核心机制入口，继续沿用青玉素材；负责人反馈展示和点击正常，完整跨英雄和交易覆盖仍待专项验收。见[最新记录](../../../deliverables/英雄详情立绘与六技能展示更新-2026-11-19.md)。下表早期内页记录保留为历史阶段。

| 资源 | 状态 | 当前用途 |
| --- | --- | --- |
| [胜利战报](../../../assets/art/ui/preview/wave-settlement-20261127/victory.png)、[失败战报](../../../assets/art/ui/preview/wave-settlement-20261127/failure.png) | 布局参考，原生版已写回 | 原生战报保留现有青玉、军帐和任务逻辑；卷轴沿用抽取演出。参考图不是实机截图，首通以回营领取口径为准。见[实装复盘](../../../deliverables/波次奖励与关卡结算实装复盘-2026-11-27.md)。 |
| [安全区阵容／兵种内页青玉参考](../../../assets/art/ui/preview/safezone-inner-pages-20261119/README.md) | 已写回，英雄详情布局／入口反馈正常 | 原英雄详情偏差已定向修正6文件，收尾29项离线检查通过；负责人确认布局和入口显示正常，最终关闭修复及交易仍待专项复测，兵种网格仍保留独立复测边界。见[还原实装记录](../../../deliverables/英雄详情确认稿还原实装记录-2026-11-19.md)、[差异清单](../../../deliverables/英雄详情界面与确认稿差异对照-2026-11-19.md)及[前轮记录](../../../deliverables/安全区阵容详情与兵种养成内页实装记录-2026-11-19.md)。 |
| [安全区界面风格菜单与确认框](../../../assets/art/ui/preview/safezone-skin-switch-20261118/README.md) | 已实装，代表试玩反馈正常 | 八套外层模板、菜单／确认与个人偏好已写回；26 项离线及6份新增ECA结构检查通过。负责人11月19日试玩未反馈问题，样本日志0 Error／Fatal；多人、跨次保存与全面视觉边界仍待专项验收，见[实装记录](../../../deliverables/安全区八皮肤换肤实装记录-2026-11-19.md)。 |
| [安全区现有 kit 八套对照](../../../assets/art/ui/preview/safezone-existing-kits-all-20261118/README.md) | 待选择 | 六套基础系列加 kit01、kit02，共八张对照图。青玉沿用上一轮，其余七张本轮生成；已有素材路径、资源 ID、提示词和哈希均归档，未改工程。 |
| [安全区现有 new 青玉皮肤](../../../assets/art/ui/preview/safezone-existing-new-skin-20261118/README.md) | 待确认 | 按用户要求核对 new/kit 中青玉窗口、标题条、按钮及圆形控件的实际资源定义与预览后，用 imagegen 出一张效果参考。资源 ID、源图、提示词和缩略图限制均归档，未实装。 |
| [安全区风格候选 A／B／C](../../../assets/art/ui/preview/safezone-style-exploration-20261118/README.md) | 待选择 | 水墨留白、青瓷素金、朱砂军务三种控件与场景表现。内容／宏观布局相同，外观分别生成；原图、提示词及文件校验已归档，未改正式工程。 |
| [安全区营地总览 v01](../../../assets/art/ui/preview/safezone-overview-20261118/safezone-overview-v01.png) | 旧皮肤不采用，布局参考 | 负责人要求重做外观，后续看 A／B／C 候选。该图保留为内容与布局参考，未实装。 |
| [装备补给与行囊确认稿](../../../assets/art/ui/preview/equipment-ui-20261115/) | 已确认方向 | 既有 Y3 资源拼接的两张设计参考。行囊后续放大并修正排版，最终参数见[实装复盘](../../../deliverables/装备界面更新实装复盘-2026-11-15.md)。 |
| `assets/art/ui/processed/p0_components/` | 已确认 | 首轮 Y3 原型正式拼接资源，优先用于阵容、战斗 HUD、备战、通关奖励和失败结算。 |
| `assets/art/ui/processed/p0/` | 参考 | 快速布局和比例参考。 |
| `assets/art/ui/export/basic-ui-kits-sanguo-v01/extracted-controls-v12-imagegen-reference-redraw/` | 候选 | 基础控件候选资源，下一步做审美、透明边缘和九宫格复核。 |
| `assets/art/ui/command-cards/v01/` | 阶段 B 待产出 | 12 张主动军令已完成无文字透明主图、48px 预览与 alpha 校验；UI/UX 下一任务是补齐 30 张被动军略/自动融合图标，先交效果总览审核，再进行无文字切片与 alpha 校验。 |

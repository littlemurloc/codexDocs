# UI/UX 设计索引

本文档是《三国斗阵》UI/UX 设计工作的入口。后续生成任何新 UI 概念图前，应先读取本文档、[ui-guidelines.md](ui-guidelines.md)、[asset-manifest.md](asset-manifest.md)，再读取与当前界面相邻或已确认的具体说明文档。

## 当前视觉基准

- 参考方向：现代历史策略 UI，接近《三国志14》的清爽战略界面气质。
- 核心关键词：清晰、轻量、克制、战术信息优先、三国历史质感。
- 避免方向：页游大厅、黑金充值感、厚重卷轴、竹简堆叠、重装饰边框、过暗压抑背景、过多商城/活动入口。

## 当前工作状态

- 当前 UI 工作处在“资源整理与首轮 Y3 原型拼接准备”阶段，不是完整 Y3 工程实装阶段。
- `assets/ui/processed/p0_components/` 是首轮原型正式拼接优先资源；`assets/ui/processed/p0/` 只作为快速布局占位和整体比例参考。
- `assets/ui/export/basic-ui-kits-sanguo-v01/` 是基础 UI 控件审美探索；A/C 方向保留为轻量策略 UI 参考，B 方向只用于战斗、确认、奖励等更重控件参考，D 方向暂不作为主方向。
- `assets/ui/export/basic-ui-kits-sanguo-v01/extracted-controls-v12-imagegen-reference-redraw/` 是基础控件候选切片资源，下一步进行审美、透明边缘和九宫格复核；通过前不直接替换 P0 组件。
- 旧的脚本绘制 UI 控件方向已退役。后续脚本只承担切片、对齐、透明清理、预览、manifest 和校验工作。

## 已确认概念图

| 文档 | 对应资源 | 用途 |
| --- | --- | --- |
| [home-map-stage-select-v02.md](home-map-stage-select-v02.md) | `assets/ui/preview/home-map-stage-select-v02.png` | 主界面 / 地图选关入口 |
| [lineup-formation-v01.md](lineup-formation-v01.md) | `assets/ui/preview/lineup-formation-v01.png` | 阵容编成 |
| [lineup-synergy-v01.md](lineup-synergy-v01.md) | `assets/ui/preview/lineup-synergy-v01.png` | 阵容编成 / 羁绊页签 |
| [hero-config-v01.md](hero-config-v01.md) | `assets/ui/preview/hero-config-skill-tab-v01.png`、`assets/ui/preview/hero-config-equipment-tab-v01.png` | 武将配置 / 技能与装备页签 |
| [battle-hud-v07.md](battle-hud-v07.md) | `assets/ui/preview/battle-hud-v07.png` | 战斗 HUD |
| [battle-prep-choice-v04.md](battle-prep-choice-v04.md) | `assets/ui/preview/battle-prep-choice-v04.png` | 波次战备三选一 |
| [difficulty-clear-reward-v01.md](difficulty-clear-reward-v01.md) | `assets/ui/preview/difficulty-clear-reward-v01.png` | 难度通关奖励 3 选 1 |
| [challenge-failure-settlement-v03.md](challenge-failure-settlement-v03.md) | `assets/ui/preview/challenge-failure-settlement-v03.png` | 挑战失败结算 |
| [meta-upgrade-v02.md](meta-upgrade-v02.md) | `assets/ui/preview/meta-upgrade-v02.png` | 兵书成长 |

## 基础文档

| 文档 | 用途 | 负责人 |
| --- | --- | --- |
| [screen-flow.md](screen-flow.md) | 局内外界面流程、状态切换、入口关系 | UI/UX |
| [ui-guidelines.md](ui-guidelines.md) | 全局视觉方向、信息承载原则、规避项 | UI/UX |
| [asset-manifest.md](asset-manifest.md) | UI 图片、导出资源、源文件和评审状态索引 | UI/UX |
| [art-asset-generation-workflow.md](art-asset-generation-workflow.md) | 美术资源出图、清稿、切片和校验流程规则 | UI/UX |

## 后续出图前置规则

生成新 UI 概念图前必须完成：

1. 读取 [art-asset-generation-workflow.md](art-asset-generation-workflow.md)，确认当前处在效果图、清稿或工程切片哪个阶段。
2. 确认当前要做的界面属于哪个流程节点。
3. 读取已确认概念图说明，继承其中已经确定的视觉方向和信息规则。
4. 明确哪些元素是已确定规范，哪些只是当前界面的探索。
5. 避免重新引入已被否定的设计理念，例如页游感、黑暗厚重、横向大卡遮挡战斗、层级式关卡切换。

## 资源目录

| 路径 | 用途 | 默认是否批量浏览 |
| --- | --- | --- |
| `assets/ui/source/` | 源文件、可编辑工程文件、原始图 | 否 |
| `assets/ui/export/` | 正式导出的 UI 图片资源 | 否 |
| `assets/ui/preview/` | 评审用概念图、预览图、关键截图 | 否 |
| `assets/ui/processed/p0/` | 首轮原型快速占位资源 | 否 |
| `assets/ui/processed/p0_components/` | 首轮 Y3 原型正式组件拼接资源 | 否 |

## 回溯规则

- 需要理解某张图的设计意图时，优先读对应 `.md` 说明文档，再看图片。
- 新图引用旧图方向时，应在说明中写明继承了哪张图的哪些规则。
- 若用户确认某张图，需将状态更新为“已确认”，并补充或更新对应说明。
- 若某张图被后续方案替代，应在清单中标为“已废弃”，避免误用。
- 若涉及基础控件资源，优先回看 `asset-manifest.md` 中登记的 basic UI kit 和 v12 候选状态，再决定是否打开图片资源。
- 若涉及 Y3 首轮原型拼接，优先读 `assets/ui/processed/p0_components/README.md`、`p0-ui-acceptance-checklist.md` 和 `y3-ui-implementation-guide.md`。

# UI/UX 设计索引

本文档是《三国斗阵》UI/UX 设计工作的入口。后续生成任何新 UI 概念图前，应先读取本文档、[ui-guidelines.md](ui-guidelines.md)、[asset-manifest.md](asset-manifest.md)，再读取与当前界面相邻或已确认的具体说明文档。

## 当前视觉基准

- 参考方向：现代历史策略 UI，接近《三国志14》的清爽战略界面气质。
- 核心关键词：清晰、轻量、克制、战术信息优先、三国历史质感。
- 避免方向：页游大厅、黑金充值感、厚重卷轴、竹简堆叠、重装饰边框、过暗压抑背景、过多商城/活动入口。

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

## 后续出图前置规则

生成新 UI 概念图前必须完成：

1. 确认当前要做的界面属于哪个流程节点。
2. 读取已确认概念图说明，继承其中已经确定的视觉方向和信息规则。
3. 明确哪些元素是已确定规范，哪些只是当前界面的探索。
4. 避免重新引入已被否定的设计理念，例如页游感、黑暗厚重、横向大卡遮挡战斗、层级式关卡切换。

## 资源目录

| 路径 | 用途 | 默认是否批量浏览 |
| --- | --- | --- |
| `assets/ui/source/` | 源文件、可编辑工程文件、原始图 | 否 |
| `assets/ui/export/` | 正式导出的 UI 图片资源 | 否 |
| `assets/ui/preview/` | 评审用概念图、预览图、关键截图 | 否 |

## 回溯规则

- 需要理解某张图的设计意图时，优先读对应 `.md` 说明文档，再看图片。
- 新图引用旧图方向时，应在说明中写明继承了哪张图的哪些规则。
- 若用户确认某张图，需将状态更新为“已确认”，并补充或更新对应说明。
- 若某张图被后续方案替代，应在清单中标为“已废弃”，避免误用。

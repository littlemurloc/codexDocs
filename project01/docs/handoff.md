# Agent Handoff Guide

本文档用于《三国斗阵》不同角色 agent 之间的工作交接。它不替代 [agents.md](agents.md) 的角色章程；`agents.md` 定义“谁负责什么”，本文档定义“跨角色如何沟通、交接和请求越界”。

## 当前默认角色

当前对话中的默认角色为：主策划。

主策划负责维护玩法目标、系统边界、设计取舍、验收口径和文档结构。主策划不默认浏览 UI 图片资源、导出素材、代码实现、临时文件或音频资源，除非任务明确要求或获得项目负责人许可。

## 总原则

- 每个角色只回溯自己职责范围内的文件。
- 如果任务需要读取或修改职责范围外的文件，必须先向项目负责人说明原因、涉及文件和预期动作，并获得明确许可。
- 任何落档行为，包括新增、修改、整理或同步文档、代码、配置和资源说明，都必须先获得项目负责人明确授权。
- 跨角色交接优先通过本文档模板记录，不直接改写对方细案。
- 如果两个文档口径冲突，优先级为：项目负责人最新明确口径 > `docs/project-context.md` > `docs/game-design.md` > 具体系统细案 > 历史自检文档。

## 角色回溯入口

| 角色 | 默认先读 | 再按任务读取 | 默认不读 |
| --- | --- | --- | --- |
| 主策划 | `docs/project-context.md` | `docs/game-design.md`、任务相关 `docs/design/`、必要的 `tests/` | `assets/ui/` 图片本体、`tools/` 代码、`web-prototype/`、`tmp/` |
| UI/UX | `docs/project-context.md`、`docs/design/ui-ux/ui-index.md` | `docs/design/ui-ux/`、`asset-manifest.md`、任务指定资源 | 玩法细案全文、数值模拟、代码实现 |
| 程序顾问 | `docs/project-context.md`、`docs/y3-implementation-alignment.md` | `docs/y3-design-consistency-review.md`、相关系统细案、`web-prototype/`、`tools/` | UI 图片本体、无关资源包、历史自检全文 |
| 数值/战斗验证 | `docs/project-context.md`、`tests/combat-sim-validation.md` | `docs/design/initial-stat-baseline.md`、战斗相关细案、`tools/combat-sim/` | UI 资源、音频资源、非战斗文档全文 |
| UI 美术资源 | `docs/design/ui-ux/art-asset-generation-workflow.md`、`asset-manifest.md` | `assets/ui/` 指定目录、资源 README/manifest | 核心玩法细案、数值模拟、Web 原型 |
| 测试验收 | `tests/acceptance-checklist.md` | `tests/design-test-record-template.md`、当前测试相关设计文档 | UI 源资源、代码实现细节、临时文件 |
| 音频/BGM | 任务指定说明 | `tools/generate_sanguo_battle_bgm*.py`、`tmp/` 中任务指定音频材料 | 核心玩法全文、UI 图片资源 |

## Handoff 记录模板

跨角色交接时，使用以下结构：

```md
## Handoff: <主题>

- 发起角色：
- 接收角色：
- 日期：
- 当前目标：
- 已确认口径：
- 已改动文件：
- 未完成事项：
- 风险/疑点：
- 需要接收角色处理：
- 越界读取/修改需求：
```

## 交接内容要求

交接记录必须说明：

- 当前任务为什么需要交给另一个角色。
- 接收角色应读取哪些文件，不应读取哪些文件。
- 哪些内容已经获得项目负责人确认。
- 哪些内容只是建议、草案或待审核。
- 如果涉及文件修改，哪些文件已修改、哪些文件只是建议修改。
- 如果涉及资源或代码，资源/代码是否只是参考，不得被误认为最终实装。

## 越界审批格式

角色需要越界时，应先向项目负责人提交：

```md
我需要越界读取/修改以下内容：

- 角色：
- 原职责范围：
- 越界文件/目录：
- 原因：
- 预期动作：
- 不做的事：
```

获得明确许可后，才能继续。

## 当前项目注意事项

- 战斗核心已更新为 3 路 3x3 站位战斗、行优先选敌、站位被动和技能卡牌池。
- 历史文档中出现“唯一主路线”时，除非明确写作历史记录，否则不作为当前规则。
- `assets/ui/export/loading-concepts-v01/`、`assets/ui/export/main-menu-bg-animation-v01/` 等资源目录属于 UI 美术资源范围，主策划不默认打开图片本体。
- `tmp/` 为临时和依赖文件集中区，不作为任何角色默认回溯入口。

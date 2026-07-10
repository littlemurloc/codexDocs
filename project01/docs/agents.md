# Project Agent Rules

本文定义《三国斗阵》项目中不同角色 agent 的工作边界。它不替代 Codex 文件系统权限，只约束项目协作方式。

## 通用规则

- 当前对话默认角色为：主策划。
- 所有角色在工作回溯时，只默认浏览和关注自己职位范围内的文件。
- 如需读取、修改、生成或整理职责范围外的文件，必须先向项目负责人说明原因、涉及文件和预期动作，并获得明确许可。
- 任何落档行为，包括新增、修改、整理文档、代码、配置或资源说明，都必须先获得项目负责人明确授权。
- 若文档口径冲突，优先级为：项目负责人最新明确口径 > `docs/project-context.md` > `docs/game-design.md` > 具体系统细案 > 历史自检文档。

## 角色范围

| 角色 | 默认先读 | 可读/可写范围 | 默认不读/不改 |
| --- | --- | --- | --- |
| 主策划 | `docs/project-context.md` | `README.md`、`docs/game-design.md`、`docs/design/`、`tests/acceptance-checklist.md`、必要索引文档 | UI 图片资源本体、工程代码、音频资源，除非任务明确要求 |
| UI/UX | `docs/project-context.md`、`docs/design/ui-ux/ui-index.md` | `docs/design/ui-ux/`、`docs/design/ui-ux/asset-manifest.md`、任务指定 UI 资源说明 | 核心玩法、数值、关卡、英雄技能细案全文，除非获许可 |
| UI 美术资源 | `docs/design/ui-ux/art-asset-generation-workflow.md`、`docs/design/ui-ux/character-portrait-production-rules.md`、`docs/design/ui-ux/asset-manifest.md` | `assets/ui/`、`assets/characters/` 指定目录、资源 README/manifest | 核心玩法、英雄技能、数值、关卡 |
| 程序顾问 | `docs/project-context.md`、`docs/y3-implementation-alignment.md` | 技术咨询文档、表字段、原型或工具说明 | 擅自决定 Y3 工程架构、擅自改核心玩法 |
| 数值/战斗验证 | `docs/project-context.md`、`tests/combat-sim-validation.md` | 战斗验证记录、模拟器规程、必要战斗细案 | UI 资源、非战斗文档全文 |
| 测试验收 | `tests/acceptance-checklist.md` | `tests/`、任务相关设计文档 | 擅自修改玩法细案、UI 资源、工程代码 |

## 当前主策划重点文档

- `docs/design/first-batch-8-heroes-latest-skills.md`：当前第一批 8 英雄技能主源。
- `docs/design/hero-skill-template-guideline.md`：新增英雄、复盘英雄和审查技能稿的模板规范。
- `docs/design/first-batch-8-heroes-skill-implementation-audit.md`：技能落表审查。
- `docs/design/first-batch-8-heroes-y3-skill-table-v0.md`：Y3 技能落表草案。
- `docs/design/general-rules.md`：当前核心规则。
- `tests/acceptance-checklist.md`：当前验收口径。

## 当前废弃/暂缓文件

以下文档保留入口但不作为当前设计依据：

- 旧版第二批/第三批英雄设计。
- 旧版英雄读性和旧数值基线。
- 旧版装备设计和装备压力反查。
- 旧版战备 3 选 1 和战备能力池。
- 旧版羁绊设计。
- 旧版设计自检和最终审查。

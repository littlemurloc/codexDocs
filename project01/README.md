# 三国斗阵 Project01

当前主项目是《三国斗阵》Y3 单人 PVE 自动战斗设计案。当前优先目标是新版第一版 8 英雄技能定型、3x3 站位、小队规则、技能卡牌池和首轮 Y3 原型准备。

## 当前核心入口

- `docs/project-context.md`：项目回溯入口。
- `docs/game-design.md`：当前设计总览。
- `docs/design/general-rules.md`：核心规则。
- `docs/design/hero-skill-design.md`：英雄与技能系统入口。
- `docs/design/first-batch-8-heroes-latest-skills.md`：当前第一版 8 英雄技能主源。
- `docs/design/first-batch-8-heroes-skill-implementation-audit.md`：8 英雄技能落表审查。
- `docs/design/first-batch-8-heroes-y3-skill-table-v0.md`：48 技能 Y3 落表草案。
- `docs/design/y3-table-field-design.md`：Y3 表字段建议。
- `tests/acceptance-checklist.md`：首轮原型验收清单。

## 当前第一版 8 英雄

- 吕布
- 张飞
- 吕蒙
- 黄忠
- 诸葛亮
- 赵云
- 刘备
- 夏侯惇

## 当前明确废弃或暂缓

- 旧版 6 选 4 技能装配废弃。
- 旧版 24 人武将池和旧批次英雄文档不作为当前依据。
- 旧版装备系统废弃，待新版 8 英雄技能定型后重做。
- 旧版战备 3 选 1 废弃，待新版技能定型后重做。
- 阵营分布和羁绊暂不考虑，后续扩充时再设计。

## UI 资源当前状态

- `assets/ui/processed/p0_components/`：首轮 Y3 原型拼接主资源。
- `assets/ui/processed/p0/`：快速布局和比例参考。
- `assets/ui/export/basic-ui-kits-sanguo-v01/extracted-controls-v12-imagegen-reference-redraw/`：基础控件候选资源，下一步只做审美、透明边缘和九宫格复核，不直接替换 P0 组件。

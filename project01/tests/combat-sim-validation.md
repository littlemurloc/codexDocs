# Combat Simulation Validation Guide

本文档定义《三国斗阵》迷你战斗模拟器的使用边界、触发条件和记录方式。它是设计验证工具规程，不是 Y3 实装方案，也不是每次设计回溯都必须读取的常驻文档。

## 定位

`tools/combat-sim/combat_sim.py` 是用于策划验证的抽象战斗沙盘，主要检查角色定位、技能闭环、装备放大、敌人压力和战备能力方向是否成立。

它不验证：

- Y3 路径寻路、碰撞、同步、特效和性能。
- 最终数值平衡。
- UI 操作体验。
- 玩家真实理解成本。

它验证：

- 某个角色技能设定是否能在目标流派中发挥作用。
- 装备是否确实放大对应关键词，而不是变成泛用最优。
- 敌人波次是否能提供预期压力。
- 战备能力是否会破坏核心流派、跳过关键决策或造成无脑通关。

## 默认回溯规则

主策划、UI/UX 或其他 agent 在普通设计讨论、文档索引、UI 讨论、商业化讨论、读取项目上下文时，默认不读取本文件，也不运行 `combat_sim.py`。

只有当任务涉及下列变更之一时，才需要读取本文件并运行对应模拟验证：

1. 新增英雄角色，包含新增角色技能设定。
2. 修改现有英雄的技能设计。
3. 新增装备或道具。
4. 修改现有装备设计。
5. 新增关卡波次怪物。
6. 修改现有关卡波次怪物设计。
7. 新增战备能力。
8. 修改现有战备能力设计。

## 验证触发说明

| 触发类型 | 主要验证目标 | 推荐命令 |
| --- | --- | --- |
| 新英雄/英雄技能变更 | 检查定位、输出、承伤、关键词贡献和 2 人组合闭环 | `python -S tools\combat-sim\combat_sim.py --diagnose --team 角色名` |
| 新装备/装备变更 | 检查装备是否显著放大目标流派，且不成为万能最优 | `python -S tools\combat-sim\combat_sim.py --compare-items` |
| 新敌人/波次变更 | 检查波次压力是否符合测试目的，是否导致无解或过易 | `python -S tools\combat-sim\combat_sim.py --diagnose --scenario 场景名` |
| 新战备能力/战备变更 | 检查能力对流派闭环、节奏和极端组合的影响 | 先补入模拟参数，再跑 `--diagnose`、`--compare-items` 与 `--compare-preps` |

基础运行方式：

```powershell
cd D:\Codex\project01
python -S tools\combat-sim\combat_sim.py
```

常用命令：

```powershell
python -S tools\combat-sim\combat_sim.py --team 关羽 --scenario 高甲
python -S tools\combat-sim\combat_sim.py --team 关羽 --scenario 高甲 --no-items
python -S tools\combat-sim\combat_sim.py --compare-items
python -S tools\combat-sim\combat_sim.py --compare-preps
python -S tools\combat-sim\combat_sim.py --diagnose
python -S tools\combat-sim\combat_sim.py --diagnose --scenario Boss
```

## 通过标准

一次设计变更不要求所有组合都变强，但至少应满足以下标准：

- 新内容能在预期流派中产生可读贡献。
- 新内容不会让某个单一技能、装备或战备能力碾压全部测试场景。
- 至少 3 条核心流派仍保留各自优势场景和压力场景：流血斩杀、灼烧扩散、护盾反击。
- 默认 2 人参战条件下仍存在基础通关路径。
- 付费 4 人参战只扩大组合空间，不改变奖励池和稀有度规则。
- Boss 或高压波次可以失败，但失败原因必须可解释，例如缺续航、缺破甲、缺前排或缺后排处理。

## 记录要求

触发模拟验证后，应把结果简要记录在对应设计任务或测试记录中。记录不需要粘贴完整终端输出，保留策划判断即可。

建议记录字段：

| 字段 | 说明 |
| --- | --- |
| 变更内容 | 新增或修改了什么设计。 |
| 验证命令 | 本次运行的命令。 |
| 关键结果 | 胜负、耗时、余血、阵亡数、关键词贡献。 |
| 设计判断 | 通过、需微调、需重做或暂缓。 |
| 后续动作 | 是否同步修改角色、装备、敌人、战备或关卡文档。 |

## 当前首轮结论

首轮验证已经证明三条核心流派具备初步区分度：

- 流血斩杀：对高甲和 Boss 有持续压血能力，但需要前排或控制节奏保护输出位。
- 灼烧扩散：清杂和群体压力强，但无前排组合在高压与 Boss 场景风险较高。
- 护盾反击：需要承伤、辅助和装备共同闭环；双前排稳定但容易拖慢战斗。

这些结论只作为后续设计调整的基线。新增内容如果改变了上述结论，需要重新跑相关模拟并更新本文件或对应设计细案。

当前模拟器已额外支持 12 件正式首发装备名对照和 6 个高影响战备代理对照。装备校准与战备校准的当前结论以 `docs/design/initial-stat-baseline.md` 为准。

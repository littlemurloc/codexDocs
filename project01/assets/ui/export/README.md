# UI Export Slice Manifest

本目录保存从 `assets/ui/preview/` 已确认界面示意图中裁切出的第一轮 UI 拼接参考资源。

## 使用边界

- 当前切片来自平面预览图，主要用于 Y3 落地时对照控件结构、尺寸比例、视觉语言和拼接层级。
- 当前切片不是最终无字版、透明版或九宫格工程资源；若后续需要正式控件资源，应在此基础上继续制作去文字、透明底、九宫格和多状态版本。
- `skill-loadout-v04.png` 已废弃，本轮没有纳入正式裁切。
- 已有 24 个武将头像占位素材位于 `assets/ui/icon/skill-select-v02/`，本目录不重复导出。

## 目录说明

| 目录 | 内容 |
| --- | --- |
| `common/` | 顶部栏、按钮、页签、底部信息条等跨界面通用件。 |
| `home/` | 主界面、地图选关、关卡节点、关卡信息面板和阵容摘要。 |
| `lineup/` | 阵容编成、2+2 出战槽、武将列表、羁绊页签和羁绊摘要。 |
| `hero-config/` | 武将配置、头像格、技能槽、装备槽、技能/装备详情面板。 |
| `battle/` | 战斗 HUD、角色竖卡、战备三选一、下一波预览和本局战备摘要。 |
| `settlement/` | 通关奖励、失败结算、奖励卡、失败建议和结算按钮。 |
| `meta/` | 兵书成长路线、节点、节点详情和升级按钮。 |

## 第一轮导出清单

### common

- `top-bar-dark.png`
- `top-bar-light.png`
- `button-red-large.png`
- `button-red-wide.png`
- `button-gold-wide.png`
- `button-light-back.png`
- `tabs-three-dark-active.png`
- `tabs-skill-equipment.png`
- `bottom-info-bar-dark.png`

### home

- `map-background-left.png`
- `stage-card-selected.png`
- `stage-card-normal.png`
- `stage-card-locked.png`
- `stage-card-locked-large.png`
- `party-summary-panel.png`
- `stage-info-panel.png`
- `bottom-report-bar.png`
- `nav-buttons-row.png`

### lineup

- `role-detail-panel.png`
- `formation-slot-filled-1.png`
- `formation-slot-filled-2.png`
- `formation-slot-empty-1.png`
- `formation-slot-empty-2.png`
- `hero-list-panel.png`
- `bottom-synergy-bar.png`
- `save-lineup-button.png`
- `synergy-list-panel.png`
- `synergy-row-active.png`
- `synergy-detail-block.png`
- `synergy-bottom-tokens.png`

### hero-config

- `left-hero-grid-panel.png`
- `hero-tile-selected.png`
- `hero-tile-normal.png`
- `right-config-panel-skill.png`
- `character-summary.png`
- `skill-slot-card.png`
- `skill-candidate-row.png`
- `skill-detail-panel.png`
- `equipment-slot-card-1.png`
- `equipment-slot-card-2.png`
- `equipment-group-panel-1.png`
- `equipment-group-panel-2.png`
- `equipment-group-panel-3.png`
- `equipment-detail-panel.png`

### battle

- `battle-top-bar.png`
- `unit-card-active-1.png`
- `unit-card-active-2.png`
- `unit-card-empty.png`
- `threat-panel.png`
- `battle-bottom-status-bar.png`
- `prep-left-preview-panel.png`
- `prep-card-normal.png`
- `prep-card-selected.png`
- `prep-card-rare.png`
- `prep-right-summary-panel.png`
- `prep-confirm-button.png`

### settlement

- `reward-summary-panel.png`
- `reward-card-selected.png`
- `reward-card-normal-1.png`
- `reward-card-normal-2.png`
- `fixed-reward-panel.png`
- `first-clear-unlock-panel.png`
- `confirm-reward-button.png`
- `record-button.png`
- `failure-summary-panel.png`
- `defeat-illustration-panel.png`
- `failure-gain-panel.png`
- `failure-suggestion-panel.png`
- `retry-button.png`
- `adjust-lineup-button.png`

### meta

- `meta-routes-panel.png`
- `route-card-common.png`
- `route-card-prep.png`
- `route-card-reward.png`
- `route-card-faction.png`
- `node-selected.png`
- `node-normal.png`
- `node-locked.png`
- `node-detail-panel.png`
- `meta-warning-bar.png`
- `upgrade-button.png`

## 后续加工建议

1. 从 `common/` 中挑选按钮、页签和面板做无字版。
2. 将高复用面板整理为九宫格资源，避免 Y3 内缩放时边框变形。
3. 为按钮和卡片补齐普通、悬停、选中、禁用状态。
4. 对奖励卡、战备卡、角色卡、兵书节点做透明底独立控件。
5. 将图标类资源单独整理到 `assets/ui/icon/`，不要混入面板切片目录。

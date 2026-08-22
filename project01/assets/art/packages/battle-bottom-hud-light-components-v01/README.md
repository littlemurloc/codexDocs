# battle-bottom-hud-light-components-v01

这是一套基于已确认轻量战斗 HUD 方案拆分的可实装控件资源。

## 内容

- `transparent/base/`：HUD 总底、队伍区底、详情区底、空立绘水墨背板。
- `transparent/overlays/`：姓名牌、栏目条等固定叠加件。
- `transparent/controls/`：圆头像框、方形技能/装备槽、攻防信息底、血条框和血条填充。
- `reference/`：1920x1080 空控件拼装参考，以及完整视觉对照图。
- `preview/`：资源总览、alpha 检查、9 宫拉伸检查。

## 实装说明

- 不包含人物立绘和头像；程序运行时把角色半身像、头像、技能 ICON、装备 ICON 贴入对应空槽。
- 需要拉伸的资源使用 manifest 中的 `nine_slice` 参数。
- 圆头像框、技能槽、装备槽按固定比例使用，不建议 9 宫拉伸。
- 技能和装备槽保持正方形，以兼容当前项目已有 ICON。
- `reference/battle_bottom_hud_full_visual_reference.png` 含示意人物、头像和 ICON，只用于实装拼接时对照布局和氛围，不作为切片来源。

## QA

- 外围为透明 PNG，不保留截图背景。
- 没有人物像素残留。
- 已输出 `preview_alpha_check.png` 和 `preview_9slice_stretch.png` 供检查。

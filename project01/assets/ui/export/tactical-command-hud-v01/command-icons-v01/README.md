# 通用军令图标 v01

这组资源对应战斗 HUD 的三张固定通用军令卡，基于已确认的技能卡结构语言绘制。

## 文件

- `transparent/command_emblem_ling.png`：圆形“令”军令章，用于三张军令卡的顶部印记位。
- `transparent/command_icon_huzhen.png`：护阵令图标，青绿防护阵势。
- `transparent/command_icon_yazhen.png`：压阵令图标，朱红压制军旗。
- `transparent/command_icon_poshi.png`：破势令图标，金色破阵枪锋。

## 使用规则

- 全部为 `512x512`、RGBA PNG，四边保留透明安全区。
- 军令章作为圆形前景装饰，叠在卡牌顶部印记位置。
- 三张技能图标只包含中央图标画面与其细金属内描边；不含完整卡牌底板、标题文字、描述文字或状态高亮。
- 可用、禁用、已使用、目标选择等状态由程序或后续状态层叠加，不烘焙进本组图标。

## 检查

`preview_alpha_checker.png` 用于核对透明区域与裁切边缘，不作为运行时资源。

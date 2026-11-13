把美术交付的底部导航图标放在这个目录，文件名必须严格是：

    icon_town.png    512×512  城镇
    icon_gate.png    512×512  出征（中间那颗主按钮）
    icon_shop.png    512×512  商店

放好之后重开一次 Godot 编辑器（让它导入新图），
游戏会自动优先用这里的图；没有的话退回图集里那三张 40px 的旧图。

代码在 `src/view/expedition_scene.gd` 的 `_dock_icon()`，不需要改任何东西。

需求文档：`docs/DOCK_ICONS_BRIEF.md`

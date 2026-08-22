# Battle UI Ink Warfield Components v02

本包按可实装 UI 控件重新拆分，不再使用整张局内效果图硬裁。

## 内容

- `source/`：无文字控件清稿表。
- `transparent/`：按控件拆出的透明 PNG。
- `transparent/start_challenge_text.png`、`transparent/duel_text.png`：单独生成的艺术字贴图。
- `manifest.json`：控件职责、尺寸、来源坐标、九宫格建议和用途说明。
- `preview_components.jpg`：控件总览。
- `preview_alpha_check.jpg`：透明背景检查。

- `preview_text_on_controls.jpg`：艺术字贴到目标控件上的合成检查。

## 实装原则

- 血条、面板、卡牌、资源栏都按 `base + overlay + engine text/icon` 使用。
- 带徽章、头像框、按钮图标等具象装饰不参与九宫格拉伸。
- 顶部 HUD、资源条、双方血条、布阵大面板、属性条提供九宫格候选参数。
- 圆形按钮、头像框、开战印章、技能槽、卡牌框、小地图框建议固定尺寸或等比缩放。

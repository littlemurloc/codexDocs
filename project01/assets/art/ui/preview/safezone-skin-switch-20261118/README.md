# 安全区界面风格选择：交互效果参考

日期：2026-11-18。状态：待视觉确认，未实装。使用内置 imagegen，以现有青玉效果图及实际控件素材为参考生成，非网页、非引擎截图。

## 两个交互状态

| 图片 | 内容 |
| --- | --- |
| [01 菜单展开](01-style-menu-open.png) | 设置旁增加“界面风格”；下拉列出八套名称，青玉璧环标记“使用中”。 |
| [02 切换确认](02-style-switch-confirm.png) | 菜单收起，居中确认“青玉璧环 → 墨金战阵”；取消／确认切换层级区分，底下仍为青玉界面。 |

当前青玉、目标墨金战阵仅用于演示流程，不代表已确定正式默认皮肤。选择其他项后先确认，确认后才应用外观；取消、关闭不改外观或存档。

菜单的小色块仅作风格辨识，不作为新增的正式资源。确认框采用浅纸细金边的固定中性外观，不随确认过程切换。场景、人物与章节数据是既有概念图样例，不规定真实阵容或章节配置。

这两张图用于确认新控件的位置、尺寸层级、文字和交互状态；生成模型仍可能重绘局部人物、底图及原有标题，不能用其局部变化取代原有正式界面定义。实装时仅按已确认范围添加和绑定控件，不据此改写业务内容。未执行新 UI 导入、ECA 修改、存档设置或默认皮肤变更。

## 原始输入

- 01 编辑目标：`../safezone-existing-new-skin-20261118/safezone-existing-jade-kit-v01.png`。
- 01 控件参考：`assets/art/packages/ui-control-kit-implementation-v01/06_jade_bi/window/base_9slice.png`、`06_jade_bi/button_rect_normal/base_9slice.png`。
- 02 编辑目标：本目录 `01-style-menu-open.png`。
- 02 目标皮肤参考：`../safezone-existing-kits-all-20261118/08-kit02-warfield.png`；仅用于目标标记风格，不先替换底下的青玉界面。
- 02 弹窗参考：`assets/art/packages/ui-control-kit-implementation-v01/01_porcelain_map/window/base_9slice.png`。

实际提交提示词见 [prompts.md](prompts.md)，图片尺寸、哈希及视觉检查见 [verification.json](verification.json)。完整功能架构见[落地方案](../../../../../deliverables/安全区八皮肤动态切换落地方案-2026-11-18.md)。

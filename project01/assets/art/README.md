# Art Asset Root

本目录是项目正式美术资源的统一入口。后续进入工程、原型或资源索引的美术文件，都应优先归入 `assets/art/` 下，避免散落在项目根目录、`tmp/`、`deliverables/` 或独立的旧资源目录中。

## Directory Map

| 目录 | 用途 |
| --- | --- |
| `characters/` | 武将头像、半身像、立绘和角色相关 manifest。 |
| `ui/` | UI 控件、HUD、图标、卡牌、按钮、特效序列帧、预览和源图。 |
| `ui-concepts/` | 已保留但尚未作为正式切片使用的 UI 概念图。 |
| `packages/` | 阶段性 UI 资源包、可实装控件包、效果图包和样板包。 |

## Rules

- 正式资源路径以 `assets/art/...` 开头。
- `tmp/`、`.tmp/` 只用于过程文件和一次性预览，不登记为正式资源。
- `deliverables/` 用于对外交付文档；美术资源包统一放入 `assets/art/packages/`。
- UI 控件若需要实装，应同时包含源图、透明切片、预览图、manifest 和 README。
- 移动资源时必须同步更新文档、manifest、工具脚本和原型页面里的路径引用。

# UI 控件分层清稿样板 v01

本目录用于重新建立“三国项目 UI 控件资源”的正确生产链路。

## 推荐样板

- `porcelain_map_clean_layers_v02_recommended.png`

这是当前推荐的“清瓷地图框”分层清稿样板。它的目标不是最终切片，而是确认资源生产方式：

1. 第一排为 base assets，只保留可 9 宫格拉伸的主体框、边、角、底纹。
2. 第二排为 overlay ornaments，玉扣、结饰、花枝、连接件等都单独摆放。
3. 第三排为 recomposition preview，只用于看组合效果，不应直接切进工程。

## 对比稿

- `porcelain_map_clean_layers_v01.png`

v01 保留作对比。它已经比旧的扁平总览图更合理，但部分花纹与装饰关系不够严格，因此不作为推荐标准。

## 本轮已产出风格

| 文件 | 风格 | 当前判断 |
| --- | --- | --- |
| `porcelain_map_clean_layers_v02_recommended.png` | 清瓷地图框 | 推荐作为主标准样板 |
| `cinnabar_seal_clean_layers_v01.png` | 朱印令牌框 | 可作为分层样板，装饰与 base 分离较清楚 |
| `ink_brush_clean_layers_v01.png` | 墨刷浮层框 | 可作为风格样板；红色刷痕需确认是 base 材质还是 overlay |
| `bronze_armor_clean_layers_v01.png` | 玄铁铜铆框 | 可作为分层样板，盾徽、龙纹、铆钉件清晰 |
| `dossier_paper_clean_layers_v01.png` | 军务档案夹 | 可作为分层样板，纸夹、印章、折角适合 overlay |
| `jade_bi_clean_layers_v01.png` | 青玉璧环框 | 可作为风格样板；组合预览里部分云纹需后续保持 overlay 化 |

## 后续切片原则

- base 必须是原生无装饰底图，不能从合成图里修补抠掉装饰。
- overlay 必须是纯装饰件，不能带矩形底板残片。
- 带徽章、玉扣、纸夹、印章、兽头、龙纹、盾徽的控件，一律用 base + overlay 叠加。
- 9 宫格只拉伸主体框体，装饰件固定尺寸并按锚点叠加。
- 每套风格应先通过一张清稿样板确认，再进入批量切片。

## 下一步建议

先从 `porcelain_map_clean_layers_v02_recommended.png` 和 `cinnabar_seal_clean_layers_v01.png` 各切一套工程样例，验证：

1. 9 宫格边界是否能稳定拉伸。
2. overlay 锚点是否能在不同尺寸下保持正确位置。
3. normal / disabled 按钮是否能形成统一交互状态。
4. 组合预览是否能由 base + overlay 还原，而不是依赖整张合成图。

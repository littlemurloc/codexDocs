# 现有 kit 对照出图提示词

生成工具为内置 imagegen。01–05、07 的实际提交文本为公共提示词加对应补充段；08 首次请求主机超时、核查未找到结果后重试，最终成功请求全文单独保存在 [prompt-08-retry.txt](prompt-08-retry.txt)。06 青玉沿用上一轮原图及提示词，不重复生成。

输入参考顺序为布局、窗口、标题条、主按钮、圆形控件（07 改为次按钮）。布局参考为 `../safezone-existing-new-skin-20261118/safezone-existing-jade-kit-v01.png`，其余输入路径见资源清单。

## 公共提示词

```text
Use case: ui-mockup, material-constrained existing Y3 game kit comparison.
Make ONE complete landscape 16:9 2D camp-overview screenshot for 三国斗阵, at approximately 1920x1080 composition. No browser, no presentation board, no watermark, no comparison sheet.
Image 1 is the layout/content reference ONLY. Its JADE SKIN must be replaced with this call's REQUIRED existing asset skin. Image 2 is the actual window material/construction, Image 3 the actual header/title strip, Image 4 the actual primary button (or seal), Image 5 the actual portrait/round control or secondary button. Faithfully retain these existing textures, corner motifs, colors and edge construction. This is a reuse proposal, not a new freely invented skin. Do not just recolor the jade image, and don't replace the supplied materials with generic minimal UI. Use sensible nine-slice proportions, fixed-size corners and restrained decoration; no distortion of meaningful ornaments.
Keep identical functional content and comparable macro layout:
- Slim header with 三国斗阵 at left, 设置 and 退出 at far right.
- Upper-left 营地总览 and small subtitle 整备队伍，再赴战场.
- Historical Three Kingdoms camp, flags, distant ancient Chinese fortress and mountains visible in the same middle background composition; keep the same scene and camera across kit comparisons. Allow subtle tonal support for the selected skin, no entirely different environment.
- Lower-left wide party region headed 当前出战阵容. FIVE compact CIRCULAR historical Chinese general bust portraits in ONE row, names 黄忠、张飞、赵云、刘备、韩当. Portraits small and elegant, no card borders, no rarity stars, no 5/5 count, no full-body hero. Five is sample content only.
- Below portraits exactly one secondary button 武将阵容, plus plain descriptive text 布阵 · 武将升星 · 兵种养成. These words are not extra buttons.
- Right narrower challenge region: 当前挑战, 第1章, modest horizontal fortress/army image, one clean detail row 已选章节 and 难度 1, short helper 进入后确认挑战难度, then ONE primary button or seal 开始挑战. Main challenge action most important; roster secondary.
- Quiet small lower-left 在线补给 and small text 在线累计 · 材料补给.
- Clean alignments, generous space, readable Chinese headings and functional body text with no thick outlines. Choose dark ink text on light source materials and warm ivory text on dark source materials. Typography must remain readable at gameplay scale.
No new controls, no UI currencies or invented rewards. No 成就、天赋、月卡、商城、充值、签到、主角兑换、特殊能力、装备商店. Announcement/chat, old 敬请期待 chapter-map placeholders and developer tools remain unchanged in their existing separate screens/hidden states, do not reveal or redesign them. No debug annotation or resource IDs on the screenshot.
This must be a high-quality game screenshot showing the SPECIFIC existing component family in this call, not a web dashboard. No big additional decorative animals/medallions not present in these source assets.

```

## 01 清瓷地图

```text
REQUIRED SKIN: 清瓷地图. Off-white porcelain/pale map paper, fine continuous warm gold line, very small compact geometric Chinese corner details. The source button is pale ivory, NOT red or jade. Keep the headbar equally pale. A delicate classic Chinese menu skin, source-accurate thin borders and a bright quiet surface. Use dark charcoal/green text. Avoid inventing giant green title plaques; title goes on the supplied light title strip.
```

## 02 朱印令牌

```text
REQUIRED SKIN: 朱印令牌. The source window is warm cream map paper bounded by a narrow RED LACQUER frame and fixed Chinese gold geometric corners. The supplied headbar has red ends and light center. The source primary button is deep vermilion lacquer with gold corners; secondary may use same family at smaller scale. Capture real red lacquer/cream construction, not recolored jade or a flat red modern poster. Keep the border slender by correct nine-slice stretching. Dark brown text on cream, pale text on red.
```

## 03 墨刷浮层

```text
REQUIRED SKIN: 墨刷浮层. Real source is a DARK charcoal-black rough ink/stone floating panel with irregular scraped edges, thin sharp silver metal edge accents and sparse dark red battle scratch marks. It is NOT a white ink-wash layout. Headbar and rectangular button must use the same jagged dark black/silver/red source material, with readable warm ivory characters. Keep irregular corners fixed and red scratch decor local rather than stretching it over text. Background remains visible; use light typography and good spacing, avoid muddy black-on-black or giant red glows.
```

## 04 玄铁铜铆

```text
REQUIRED SKIN: 玄铁铜铆. Blackened iron/leather textured panel with angular BRONZE STRAP corners and visible small circular RIVETS. The actual window, header, button and round bezel must retain that armor construction, not ink brush, not gold scrollwork. Correct thin-bronze-edge scale, dark iron centers, small rivet heads at true corners. Warm ivory text, small aged-bronze accents. Do not add dragon heads, huge shields or extra studs beyond the supplied elements. Make the existing rugged military kit look well-composed and readable.
```

## 05 军务档案

```text
REQUIRED SKIN: 军务档案. Source is pale warm-beige military dossier paper with a subtle column/grid watermark, faint distant landscape and double very fine grey-brown rules. Light folded/clipped corners, NO gold-metal corners or red lacquer. Button and headbar are softly raised ivory paper labels with the supplied fine linear edge. This is a quiet functional paper kit, with dark ink typography and no added paperclips, ropes, stamps, fake office props or big scroll rolls. Match the actual source shapes instead of inventing a contemporary editorial red/black poster.
```

## 07 kit01 基础金边

```text
REQUIRED SKIN: actual new/kit/kit01 classic set. Window has light paper with fine landscape/cloud imagery, a blackened dark outer rim and gold geometric corner patterns, plus an INTEGRATED DARK JADE title cartouche at its top. Put 当前出战阵容/当前挑战 into that integrated title position; don't stack another identical title above it. The supplied standalone headbar and PRIMARY button are deep jade with distinctive gold diamond ends and raised gold trim. Use source-accurate green primary and the supplied smaller pale ivory secondary button for roster. Keep dark jade/gold mostly on edge strips and action areas, the main readable interiors pale. Do not copy the all-pale jade family from Image1. Reuse its real classic patterns without inventing more dragons or heavy crown decorations.
```


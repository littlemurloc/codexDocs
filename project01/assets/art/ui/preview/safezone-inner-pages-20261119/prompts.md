# 安全区内部界面参考图提示词

## 02 主项材料数量颜色定点修正

```text
Use case: precise-object-edit.
Make ONLY ONE very small color correction to this provided screenshot.
Find the main cultivation line in the upper-middle panel: the text "刀兵材料 2 / 1" directly below "3星 → 4星" and to the left of the upper "升星" button.
Its numeral 2 is STILL RED. It is located approximately at x=40.4% of image width, y=53.8% of image height (about x674,y506 in a 1672x941 image). This is NOT the lower capability-row material counter.
Change that single red numeral 2 to dark charcoal ink matching the neighboring / 1 and 刀兵材料. The ENTIRE upper line "刀兵材料 2 / 1" must now be dark ink, with NO red anywhere in that upper line.
Preserve the lower-row insufficient "0 / 1" red 0 and the red hint "还差1份材料". The lower sufficient 2 / 1 is already correct and must remain dark.
Preserve every other pixel appearance as closely as possible: all shapes, text content, values, positions, buttons, icons, background, panel scale and typography. Do not redraw or redesign unrelated content. Output the corrected full image only.
```

## 02 材料提示颜色修正

```text
Use case: precise-object-edit / ui-mockup.
Edit the provided troop-cultivation game screen with ONLY one targeted correction: material-availability text colors.
The numeral 2 in "刀兵材料 2 / 1" (main cultivation area, upper middle) and the numeral 2 in "材料 2 / 1" (first capability row 刀法研习) currently appear red despite sufficient materials. Change ONLY these TWO numeral glyphs from red to the same normal dark ink color as their surrounding material text. Keep the sufficient "1 / 1" third row normal dark ink.
Keep "材料 0 / 1" in the middle disabled row with its 0 red, and keep the shortage hint "还差1份材料" red. Do not alter any number, wording, button availability, icons, portraits, layout, header, panel, font size, texture or scene. Do not make extra changes or redesign the screen. Preserve exact 16:9 composition and all existing content. Output the corrected full-screen image only, no annotations.
```

生成工具：内置 imagegen。两张图均使用既有青玉效果图与06青玉原始窗口／标题／按钮作参考。

## 01 武将阵容与详情

```text
Use case: ui-mockup. Create ONE polished 16:9 landscape 2D Chinese Three Kingdoms game UI reference screen, with composition designed for 1920x1080. No browser, HTML, slideshow, comparison board, watermark, resource IDs or developer annotations.
Input image1 is the previously approved jade camp scene and visual family ONLY, not the old content layout to copy. Input image2 is the actual existing jade window material, image3 actual jade title strip, image4 actual jade rectangular button. Reuse their pale celadon paper, very fine warm gold lines, small clipped corners and shallow relief; retain source material identity with sensible nine-slice proportions and fixed small corners. Do not invent heavy dragons, thick metal frames, crowns, gigantic gold medallions or a dark muddy skin.
Keep the same historical camp/fortress background, softly defocused with restrained dimming, and a slim top bar: 三国斗阵 at left, 返回营地 / 界面风格 / 设置 / 退出 at right. Below it show ONE generous inset game-management panel around x80 y145 width1760 height830 (1920x1080 proportions), with clean pale jade surfaces, excellent readable dark ink Chinese typography, compact headings, generous spacing and fine separators. Do not fill text with thick strokes or glows. Main body labels should feel at least 22px at design size. This is a safe-zone management page, not the combat HUD.
Only portray actual existing management functions specified below. Preserve square skill/material icons in square frames and use small circular portrait busts for roster rows. No rarity letters R/SSR, no talent, achievement, recharge/shop, new currency, new stats formulas or invented guaranteed-drop rules. No full-body hero, no huge collectible card frames. All figures and balances specified here are deliberate layout examples, not factual player-save values. Do not print that explanation in the image.
SCREEN: 武将阵容, with selected hero detail and deployment simultaneously visible. Refined editorial hierarchy and compact functional grouping, faithful to the existing jade kit.
Panel top: title "武将阵容", subtitle "选择武将，查看详情与出战阵位".
Three aligned columns beneath the title, separated by breathing room:
LEFT approx 390px: heading "武将列表". FIVE compact horizontal rows, each with a small circular illustrated Chinese general head portrait, a clearly readable name, text star level and a quiet deployment status. In order 黄忠 / 张飞 / 赵云 / 刘备 / 韩当. Third row 赵云 is selected using a thin gold/jade outline, NO checkmark button. All five can say 已上阵, with sample star levels 2星 / 3星 / 3星 / 2星 / 1星. Use restrained scroll affordance for a longer list, no 5/5 capacity claim, no extra filter tabs or search.
CENTER approx 720px: heading "武将详情". Top compact identity area with a small half-bust of 赵云, recognizably Chinese general with dark tied hair, silver/white armor and blue accents; NOT red-haired 马超. Alongside: large "赵云", smaller "3星", status "已上阵". A small secondary "下阵" button at the right.
Below this top area put three spacious readable skill rows, each with one SQUARE illustrated icon and label, exactly "主动技能", "被动技能", "普通攻击". Each row has short auxiliary text "查看完整说明" and a subtle right chevron. Avoid inventing skill names, cooldown values, new powers or the obsolete five-star random-pool claim. No skill glyph cropped to circles.
At bottom of center a neatly bounded upgrade area: heading "武将升星"; "当前 3星 → 下一级 4星"; one material line "赵云材料  2 / 3"; a muted disabled button "升星"; a clearly legible small warm-red hint "材料不足，还差1份". No claimed numeric attack/HP gains, no 主角属性加成.
RIGHT approx 490px: heading "出战阵位". Show an elegant 3 by 3 formation grid of nine square placements with thin borders. Five occupied cells have SMALL head portraits matching the five named heroes, four cells have a quiet plus marker. The Zhao Yun cell uses the same selection outline as his roster row. Small labels clarify "前排" / "中排" / "后排". Under grid, clear helper text "点选武将后，再点阵位调整". No new max-count claim, no battle map or battle units.
Panel bottom spanning full width: a shallow separate recruitment strip with heading "武将招募", one unobtrusive material balance "招募材料 120", and two moderate buttons "招募一次" and "招募十次", each with a readable cost line "消耗 10" and "消耗 100". Keep this secondary to the main detail; no free-draw badge or summon lottery machine.
Render the complete screenshot only. Make the hierarchy attractive, light and useful rather than a stack of ornate boxes.
```

## 02 兵种养成

```text
Use case: ui-mockup. Create ONE polished 16:9 landscape 2D Chinese Three Kingdoms game UI reference screen, with composition designed for 1920x1080. No browser, HTML, slideshow, comparison board, watermark, resource IDs or developer annotations.
Input image1 is the previously approved jade camp scene and visual family ONLY, not the old content layout to copy. Input image2 is the actual existing jade window material, image3 actual jade title strip, image4 actual jade rectangular button. Reuse their pale celadon paper, very fine warm gold lines, small clipped corners and shallow relief; retain source material identity with sensible nine-slice proportions and fixed small corners. Do not invent heavy dragons, thick metal frames, crowns, gigantic gold medallions or a dark muddy skin.
Keep the same historical camp/fortress background, softly defocused with restrained dimming, and a slim top bar: 三国斗阵 at left, 返回营地 / 界面风格 / 设置 / 退出 at right. Below it show ONE generous inset game-management panel around x80 y145 width1760 height830 (1920x1080 proportions), with clean pale jade surfaces, excellent readable dark ink Chinese typography, compact headings, generous spacing and fine separators. Do not fill text with thick strokes or glows. Main body labels should feel at least 22px at design size. This is a safe-zone management page, not the combat HUD.
Only portray actual existing management functions specified below. Preserve square skill/material icons in square frames and use small circular portrait busts for roster rows. No rarity letters R/SSR, no talent, achievement, recharge/shop, new currency, new stats formulas or invented guaranteed-drop rules. No full-body hero, no huge collectible card frames. All figures and balances specified here are deliberate layout examples, not factual player-save values. Do not print that explanation in the image.
SCREEN: 兵种养成. The same panel shell and same visual scale as the roster screenshot, with a coherent three-column layout that makes progress, material requirements and actions easy to understand.
Panel top title "兵种养成", subtitle "培养兵种，查看成长与所需材料".
LEFT approx 340px, heading "兵种列表": FIVE compact selectable rows with SMALL SQUARE painted military icons and exact names in order "刀兵", "弓兵", "枪兵", "盾兵", "骑兵". Show sample levels 3星 / 2星 / 1星 / 0星 / 0星. Third and later rows do NOT look disabled merely because unselected. 刀兵 is selected by a thin gold/jade outline. 盾兵 and 骑兵 may have quiet "未激活" labels, others 已激活. No fake species names and no huge troop cards.
CENTER approx 850px, heading "刀兵培养": a compact top identity area with one small square swordsman icon, name "刀兵", "当前 3星", a short description "近战兵种", no full-body large character art. Then a roomy section "主项培养" with "3星 → 4星", line "刀兵材料  2 / 1", one enabled understated button "升星". Nearby a clearly named "培养效果" field with brief natural text "物理攻击提升" and a secondary line "提升效果随星级成长". Do not claim this is a whole-team bonus and do not invent numeric attribute gains.
Below, heading "兵种能力培养". THREE full-width horizontal capability rows with square icons, readable display names and separate material/progress/action columns:
row1 "刀法研习" small subtype "攻击成长", material "材料 2 / 1", normal button "升星";
row2 "体魄锤炼" small subtype "生命成长", material "材料 0 / 1", muted disabled "升星" plus a visible hint "还差1份材料";
row3 "刀术精进" small subtype "攻击成长", material "材料 1 / 1", normal button "激活".
These are friendly display-name proposals for existing 刀兵能力01/02/03, not new abilities. Do not print internal identifiers, data-table language or arbitrary specific combat effects. Keep at least 22px readable text and tidy row alignment.
RIGHT approx 470px: a quiet dedicated panel headed "练兵补给". One modest balance line "练兵材料 120". A small row of THREE SQUARE material icons (swordsman training token, archery training token, military training booklet) under label "补给内容", short text "兵种培养材料 · 能力材料". No claw machine, capsule machine, modern mechanical props, giant box art, wheel of fortune or premium gacha framing.
Below put two full-width source-shaped buttons vertically: "补给一次" with cost "消耗 10", "补给十次" with cost "消耗 100". Clear material icon next to cost so the resource being spent is understandable. One small explanatory line "获得材料直接入库". No new pity number, probabilities, free-draw promise, history panel or invented conversion.
Show the complete screenshot only. Keep generous breathing room, fine separators, readable unselected and disabled states, and source-accurate jade/gold aesthetics.
Image5 is the just-created roster concept. Match its outer panel bounds, top bar, light jade material, fine borders, dark typography and overall UI scale so these are two coherent sibling pages. Replace its roster content with the troop-cultivation layout specified above.
```


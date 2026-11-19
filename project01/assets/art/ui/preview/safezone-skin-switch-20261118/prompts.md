# 界面风格交互参考图提示词

## 02 切换确认

```text
Use case: ui-mockup / precise-object-edit.
Create ONE complete landscape 16:9 2D game screen for 1920x1080 composition: the confirmation-dialog state immediately after choosing 墨金战阵 from the interface-style dropdown.
Input image 1 is the edit target, the MENU-OPEN jade camp screenshot. Preserve its scenery, camera, existing jade outer interface, troop portraits and all content positions. Input image 2 is ONLY the target-skin reference: black-bronze angular frame and tan ink paper of 墨金战阵. Input image 3 is the actual pale porcelain window material for the neutral confirmation dialog. Keep its fine gold edge and small geometric corners, use sensible nine-slice proportions and fixed-size corners. Do not invent a different skin.
Required changes:
- CLOSE the eight-row dropdown completely. Keep top-right header entries 界面风格 with a down chevron, 设置, 退出 in place.
- Add a subtle uniform dark translucent backdrop over the entire original screen (about 35% black). The original underlying interface MUST STILL BE JADE because the new skin is not applied before confirmation.
- In the screen center place ONE refined compact confirmation dialog, roughly 740x380 pixels in 1920x1080 proportions, comfortably padded. Opaque warm ivory paper, thin restrained gold line and small Chinese geometric corners, dark readable typography. No gigantic title plaque, no dragon head, no thick bevel, no modern browser chrome.
- Exact centered heading: "切换界面风格？"
- Below it, one comparison row: small pale jade material chip and "青玉璧环", then a simple right arrow, then small black-bronze/tan paper chip and "墨金战阵". These are small material chips, not nested screenshot cards. Names must be entirely visible.
- Below row, two short centered helper lines, exactly:
"仅调整安全区外层界面"
"可随时再次切换"
- Bottom action row: equal-size buttons "取消" at left, "确认切换" at right. Cancel pale paper with fine muted gold edge; confirm same restrained construction with stronger dark jade fill and warm ivory text. Strong clear hierarchy without thick 3D ornamentation. Keep reasonable button spacing.
- A small simple close X in the top-right of the dialog, inside the panel with padding.
No dropdown remains visible; no success toast; no image showing the already-switched skin underneath. This is a pending confirmation state. No changes to battle HUD, no new gameplay features, no extra actions. The goal is a polished readable authentic Chinese strategy game dialog integrated with existing resources. Output only the full completed game screen, no external annotations, labels, resource IDs or watermarks.
```

工具：内置 imagegen；用途：2D 视觉确认，不是引擎截图。当前青玉、目标墨金战阵仅为演示，不确定正式默认项。

## 01 菜单展开

```text
Use case: ui-mockup / precise-object-edit.
Create ONE complete 16:9 landscape 2D game interface reference image, composition for 1920x1080. This is the MENU-OPEN state of an existing Three Kingdoms game safe-zone screen, not a website or a comparison board.
Reference image 1 is the exact edit target: preserve its camp scenery, camera, visible mountains, flag, header, jade material, lower-left party portraits/names, online supplies and right challenge panel in place. Reference image 2 is the actual jade nine-slice panel material. Reference image 3 is the actual jade rectangular button material. Reuse the supplied jade surface, delicate gold edge and compact clipped corners. Do not freely redesign the skin. No watermark, no IDs, no annotations.
Change only the following:
1. In the top-right header, make room for three adjacent compact entries in this exact left-to-right order: "界面风格" with small down chevron, "设置", "退出". A small restrained appearance icon may accompany 界面风格. Keep header title 三国斗阵 at left.
2. Open a compact dropdown directly below 界面风格. Anchor its top at about x=1250 y=80 in a 1920x1080 composition, width about 400px and height about 530px; keep entire panel on screen. It overlays the right challenge panel, rather than moving any underlying content. Opaque pale jade paper with thin gold trim, fixed small corners, subtle shadow. It should read as a list menu, not a full-page modal or an oversized card.
3. Inside this menu, heading "界面风格", then EIGHT uniform selectable text rows in this exact order with NO numbered prefixes:
"清瓷地图"
"朱印令牌"
"墨刷浮层"
"玄铁铜铆"
"军务档案"
"青玉璧环"
"基础金边"
"墨金战阵"
Use dark ink Chinese text, clean and readable at gameplay scale, aligned left. Each row may have one tiny material-color chip at left, not whole skin screenshots. The SIXTH row 青玉璧环 has a subtle warm jade selection band, one small check, and the right-aligned label "使用中". All other rows unselected, no hover on another row, no second check.
4. Small footer "选择后确认切换". Do not add Apply or Cancel buttons inside the dropdown: clicking a different row will open a separate confirmation state in another image.
Keep all original main content legible and unchanged where not covered. Keep 当前出战阵容, 黄忠, 张飞, 赵云, 刘备, 韩当, 武将阵容, 布阵 · 武将升星 · 兵种养成, 在线补给, 在线累计 · 材料补给, 当前挑战, 第1章, 已选章节, 难度 1, 进入后确认挑战难度, 开始挑战. Do not add achievement/talent/shop/bag systems. No backdrop dimming in this menu-open state. Refined restrained contemporary game UI readability, no heavy text outlines or thick 3D bevels. Output only the completed full-screen reference image.
```


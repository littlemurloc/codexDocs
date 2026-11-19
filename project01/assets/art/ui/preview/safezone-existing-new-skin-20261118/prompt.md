# 现有 new 青玉皮肤效果图提示词

工具为内置 imagegen（image2 工作流），以布局参考和四张已有控件参考分别指定角色。以下为实际成功提交的完整提示词。

```text
Use case: ui-mockup using existing game assets.
Create ONE beautiful, believable 16:9 landscape 2D screenshot reference of the 三国斗阵 safe-zone/camp overview. This is a material-CONSTRAINED skin proposal using the actual project's existing imported new/kit resources, not another free-style skin invention.
INPUT IMAGE ROLES IN EXACT ORDER:
1. Previous camp overview image: use ONLY functional content, five hero identities, camp setting and macro composition. Its ivory antique-gold plaques and red button were rejected. Do not copy that skin.
2. Existing 青玉璧环 window source from the local imported kit family, 513x318: THIS IS THE REQUIRED WINDOW SKIN. Preserve the pale muted mint/jade material, subtle smoky texture, fine pale gold edge lines, clipped corners and the tiny angular corner fittings. This is not white parchment, turquoise glass or black metal.
3. Existing imported normal rectangular button resource 134273889: THIS IS THE REQUIRED BUTTON SKIN. Preserve its actual pale jade inset, bevel construction, small clipped corners and slim gold edge. Both 开始挑战 and 武将阵容 must use this same family and retain the same corner shape. Differentiate priority using size, spacing and typography, NOT by inventing a red, dark-green or glowing button.
4. Actual imported title/headbar resource 134237694 (CDN preview): required slim mint title strip, shaped ends and fine edge. Stretch only its middle region, retain ends and border proportions.
5. Actual imported round blank button resource 134271555: small round utility/portrait frame treatment with pale green center, fine gold rings and clipped fitting detail. Use sparingly at native-like scale.
Faithful material constraint: design using THESE existing component silhouettes, textures and border details as if assembled with proper nine-slice stretching and separate fixed overlays in Y3. Keep edge/corner thickness constant while stretching middles. Do NOT redraw it as the previous experimental contemporary blue-green chopped-corner sheet skin. Do NOT change materials into flat graphic posters or ink brush fields. The user explicitly wants something achievable with existing assets in 美术资源/图标/玩家自定义/new.
FRESHNESS THROUGH LAYOUT SCALE: tiny corner ornaments, thin original edges, unframed breathing space, a compact header instead of a tall embossed plaque, avoid too many nested windows. No dragons, lion heads, chains, giant round seals, new embossed patterns or new decorative banners. Most refinement comes from spacing, subdued typography, one muted jade surface family and a quiet camp background.
COMPOSITION:
- One full game screenshot, landscape ratio approximately 1920x1080. Not a website, no browser chrome, no multi-screen sheet or labels outside the UI.
- Thin header across top with understated 三国斗阵 at left and small 设置 / 退出 at far right, using small same-family round utility bases or quiet text. No large black/red logo seal.
- Small upper-left page title 营地总览, subtitle 整备队伍，再赴战场.
- Backdrop: refined gently lit historical Chinese military camp, distant mountains and a fortified city in pale muted green-grey morning light; comfortably less saturated and less detailed behind controls. Illustrated setting and characters are layout atmosphere, not a new game system. No giant full-body heroes.
- Lower-left main region approximately x70–1080,y530–930: a wide but COMPACT existing pale jade window, REQUIRED source material from image2, constant slim gold frame. Simple CURRENT PARTY header on source headbar image4 reading 当前出战阵容. Five genuinely SMALL round upper-body portraits of 黄忠、张飞、赵云、刘备、韩当 in one row, readable names below. Portrait rings borrow image5's narrow gold-ring treatment, no cards, no rarity stars, no slot limit counter 5/5. Let the interior breathe; portraits must not dominate the whole screen.
- Below portraits, exactly one medium secondary button 武将阵容 using image3's exact pale jade button skin. Next to it in simple smaller body type: 布阵 · 武将升星 · 兵种养成. These are descriptive words, not three new action buttons.
- Right challenge region approximately x1210–1840,y240–930: a second source-image2 pale jade panel, SAME skin and border thickness as left, header 当前挑战 on the actual narrow headbar. Elegant title 第1章. A modest rectangular fortress-and-army image with a thin source-family edge, not a second elaborate nested window. Clean short detail line 已选章节 and 难度 1. Small helper 进入后确认挑战难度.
- Bottom of right region exactly one primary button 开始挑战, using the EXISTING PALE JADE normal button skin image3 stretched horizontally; make it visibly larger than 武将阵容, use legible dark pine-green or near-black lettering. No red button, no orange glow, no recolored dark-green button that does not exist.
- Small tertiary 在线补给 at bottom-left margin with helper 在线累计 · 材料补给, a compact version of same-family source strip; keep it less prominent.
- Typography: refined restrained Chinese Song-style headings and highly legible simple functional body type. No strong black outlines, no exaggerated calligraphy. Use dark pine-green/charcoal ink text, limited pale gold only where existing source art contains it. Headings moderate in size, button hierarchy obvious.
STRICT FUNCTIONAL CONTENT:
Only 三国斗阵, 营地总览, 整备队伍，再赴战场, 当前出战阵容, 黄忠, 张飞, 赵云, 刘备, 韩当, 武将阵容, 布阵 · 武将升星 · 兵种养成, 当前挑战, 第1章, 已选章节, 难度 1, 进入后确认挑战难度, 开始挑战, 在线补给, 在线累计 · 材料补给, 设置, 退出.
Do not add 成就, 天赋, 月卡, 充值, 商城, 主角兑换, 特殊能力, 装备商店, 签到, new resources, currency amounts or fabricated rewards. Announcement/chat, existing 敬请期待 map placeholders and developer tools remain unchanged in existing screens/hidden states; they are outside this overview, do not reveal or redesign them here.
No asset IDs or arrows annotating the screenshot. No debug text or watermark. Keep the visual identity specifically anchored in the actual uploaded existing jade kit, not vaguely inspired by it. Render a polished implementable game layout reference.
```

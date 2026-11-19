# 安全区三种风格的实际提示词

工具为内置 imagegen（image2 工作流），三张图分别调用生成。每张实际提示词为下方公共部分加对应风格部分，均以营地总览 v01 作为内容与宏观布局参考。

## 公共部分

```text
Use case: ui-mockup / style exploration.
Create ONE full-screen 16:9 landscape high-fidelity 2D reference screenshot for 三国斗阵, the Chinese Three Kingdoms PC strategy/auto-battle game. Not a website or browser, no presentation board or device frame.
The provided image is a CONTENT AND MACRO-LAYOUT reference ONLY. The user rejected its dated, ornate skin. RADICALLY redesign the appearance: framing geometry, typography hierarchy, surface material, button construction, background art rendering, icon treatment, negative space. This is not a hue shift, recolor or filter. Remove its continuous antique-gold outlines, embossed corner motifs, imitation antique plaques, bulky title badges, grainy yellow parchment and giant isolated bordered boxes.
Keep the SAME functional scope and macro zones so the three variants are comparable:
- Top slim header: 三国斗阵 at left, small 设置 and 退出 at far right.
- Upper-left small page identity 营地总览 and subtitle 整备队伍，再赴战场.
- Lower-left area current party summary labelled 当前出战阵容, FIVE small round Chinese historical general bust portraits in one row: 黄忠、张飞、赵云、刘备、韩当, each name below. Busts show upper-body only. No card-frame silhouettes, card rarity, star ratings, huge hero illustrations or roster maximum 5/5. Five is only a sample party.
- In the party region one secondary button 武将阵容 and descriptive plain text 布阵 · 武将升星 · 兵种养成. This line is not additional buttons.
- Right-hand challenge region labelled 当前挑战 with 第1章, a modest fortress-and-army chapter image, short readable fields 已选章节 and 难度 1, helper 进入后确认挑战难度, then ONE primary button 开始挑战. Do not add a second challenge button anywhere.
- Small tertiary 在线补给 and helper 在线累计 · 材料补给 at lower-left edge.
- Large quiet camp scenery/negative space connects these regions. The characters, camp, distant ancient Chinese city, flags and mountains remain recognizably Three Kingdoms.
Function priority: 开始挑战 strongest, 武将阵容 secondary, 在线补给 quiet, settings/exit smallest. Consistent 1920x1080 layout proportions and comfortably legible Chinese text. Align carefully, functional body text without thick outlines. Avoid clutter.
DO NOT include 成就, 天赋, 月卡, 特殊能力, 主角选择, 商城, 充值, 签到, 装备商店, power score, currencies or fake rewards/tasks. The original coming-soon map placeholders, announcement/chat and developer tools remain in their original screens/hidden states and are outside this overview design; don't add/remove/reveal/redesign their controls here.
No explanatory design annotations, no giant A/B/C labels on the game screen, no watermark, no debug overlay. Render all important Chinese labels correctly.

```

## A 水墨留白

```text
STYLE A — contemporary Chinese ink-and-wash negative space.
Treat this as an art-directed premium historical strategy game interface grounded in ink painting, with dramatically lighter framing than the reference. Composition like a refined modern Chinese ink album: luminous warm-white negative space, flowing mist, soft grey mountains and an ancient camp drawn with fine charcoal architecture and sparse black brush textures. Tiny controlled vermilion accents. No yellow aged-paper effect.
The UI should feel integrated into the ink landscape: mostly borderless clean off-white semi-opaque paper fields, no closed ornamental rectangles, a single restrained rule or dry-brush edge to separate each functional region. Header is a quiet thin rule, not a giant banner. Party portraits are compact ink-painted color busts emerging from fine unornamented circles, much smaller than the rejected reference, with generous spacing.
Challenge presentation on the right has an elegant large serif 第1章 with a tiny vermilion square seal, floating chapter image with ink-diffused edges, and crisp compact detail lines. Only two or three artistic brush marks in the whole interface, never obscuring information. Primary button is a modern rectangular vermilion ink field with one natural imperfect edge and clean white 开始挑战; secondary action is a simple dark-ink word button and a small arrow, no gold plaque. Typography mixes beautiful precise modern Song headings with highly legible functional Chinese body type; avoid nostalgic restaurant-menu calligraphy.
Make this genuinely spacious and visually sophisticated, restrained, crisp, tactile, confidently minimal, and recognizably a game UI rather than a corporate dashboard. Background and UI both use the same contemporary ink language. Keep almost all gold out.
```

## B 青瓷素金

```text
STYLE B — refined celadon porcelain, satin silk and brushed pale bronze.
This must look fundamentally different from Style A's ink brush and from the reference's antique plaque UI. A cool luminous celadon-and-ivory art direction with desaturated pine-green shadows, a pale silver-copper accent and exceptionally clean construction. Backdrop is an elegant finely painted early-morning ancient Chinese camp in mist, layered blue-green mountains and pearl sky, tasteful atmospheric painterly realism, not distressed ink splatter.
UI surfaces are very thin smooth porcelain-white enamel/slightly translucent jade-silk sheets with almost imperceptible celadon edge tint and sharp short diagonal-cut corners. No continuous gold frames, no ornamental corners, no gold relief, no round pill dashboard cards. Use large unbroken clean surfaces and slim edge tabs. A tiny geometric inlay at one junction is enough. Thin bronze dividers are sparse, not a frame around every element. Portrait frames use smooth narrow matte celadon rings, no medallion caps.
Challenge title and layout use precision modern Chinese Song lettering, calm spacing, a thin celadon vertical spine or side tab. Fortress image sits flush within the sheet with a minimal crop, no ornamental inset frame. Primary button is a flat deep jade enamel rectangle with white text and one subtle satin highlight; use restrained dark jade for all actions, not a red/gold imitation of the reference. Secondary action is a light porcelain outline/cut-corner tab. Small utility icons are spare line symbols in desaturated bronze.
This should feel luxurious through proportions, material subtlety and precision, never through heavy ornament. Airy bright game UI, thin depth and almost no cast shadows. No sci-fi blue glow or glassmorphism widgets.
```

## C 朱砂军务

```text
STYLE C — contemporary military dispatch print design, cinnabar seal and black silk.
Make a distinctly bold yet elegant Chinese historical command interface, a complete redesign rather than recoloring A or B. Inspired by clean Chinese printed military dispatches and fine-woven banner strips, without antique scrolls, fake aged textures or bureaucratic office props. Graphic ivory, charcoal-black ink, warm light-grey and controlled rich cinnabar red, with no gold. Background is a restrained cinematic camp/fortress illustration rendered with high-contrast fine screenprint engraving and muted color, softened where text overlays it. All historical elements remain Han/Three Kingdoms.
UI construction: asymmetrical open white planes, clear black typography, a few very fine charcoal rules, narrow vertical red tab strips and selective cut-corner construction. The party field is a compact horizontal open strip without an enclosing beveled window, its portraits linked by alignment and a fine baseline. Portraits are hand-painted colored military busts in thin dark rings, not cards. Secondary button uses an ivory outlined straight-edged label with a restrained small red square corner marker.
Right challenge field reads like a sophisticated command dispatch: small black 当前挑战 above an assertive typographic 第1章, fortress image integrated as a horizontal print block, compact information arranged on a clean baseline, a small red seal as accent, then a sharply cut large cinnabar rectangular 开始挑战 button with crisp white lettering. Avoid a giant red title plaque. No ropes, clips, tassels, paper torn on every edge or dense stamps. The header is a clean light horizontal band with a narrow dark edge, not a gold-bordered antique panel.
The look must be much fresher, more graphic, typographically disciplined and dynamic than the rejected reference while retaining readability and practical game controls. True differences in silhouettes, construction and illustration medium; do not just change the hue of the original skin.
```


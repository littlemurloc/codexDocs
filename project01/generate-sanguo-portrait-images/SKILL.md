---
name: generate-sanguo-portrait-images
description: Generate Three Kingdoms character portrait images or image-generation prompts in a consistent Chinese historical fantasy, anime, semi-realistic style. Use when the user asks for 三国/Sanguo character standing art, character portraits, direct image generation, role-based visual design, or prompts for 武将、智将、敏将、辅将 characters with randomized costume, armor, hair, color, and lighting details. Prefer the available image-generation workflow, including gpt-image-2/image_gen when active, unless the user asks for prompt text only.
---

# 三国人物立绘图片生成

## Workflow

Collect or infer these inputs before composing the image prompt:

- `角色名`: required.
- `职业类型`: required; choose one of `武将`, `智将`, `敏将`, `辅将`.
- `姿势`: optional; infer a subtle head-and-shoulders pose when absent.
- `武器/道具`: optional; omit this phrase cleanly when absent.
- `表情/气质`: required.
- `构图范围`: optional; default to `头肩特写`. Do not use full-body standing art.

If required inputs are missing, infer reasonable defaults from the character, role, or user request when possible. Ask a concise question only when the missing detail would materially change the image.

Use the fixed visual direction:

- Style: `国风`, `二次元`, `半写实`.
- Background: fully transparent cutout background with alpha channel, described as `透明背景/镂空背景`. Do not use a visible solid-color backdrop.
- Rendering: details rich, strong layering, lighting that emphasizes metal or fabric texture.
- Palette pool: `深红`, `金色`, `暗灰`, `青色`.
- Composition: always `头肩特写`, showing only head, neck, and shoulders. Prioritize the face, eyes, and expression.
- Camera/view angle: vary by character and request; choose from `正脸`, `左侧脸`, `右侧脸`, `轻微俯视`, `轻微仰视`, `三分之二侧脸`. Do not default every portrait to side-facing or top-down.
- Expression: match the character's personality, reputation, and role. Use calm, stern, heroic, fierce, confident, cunning, gentle, mysterious, or dignified expressions as appropriate instead of using the same expression for every character.
- Weapons/props: optional. If shown, the weapon must be held naturally by a visible hand with anatomically plausible grip. If a normal grip is unnecessary or would crowd the portrait, omit the weapon entirely.

## Output Mode

Default to direct image generation.

1. Compose a polished Chinese image prompt using the template below.
2. Use the available image-generation workflow to create the image. Prefer the built-in `image_gen` path / gpt-image-2 behavior when available.
3. Return the generated image and the final prompt used. The image should be a transparent-background portrait whenever the available image-generation workflow supports it.

If the user asks for `只要提示词`, `prompt only`, or asks to revise prompt text without drawing, return only the polished prompt.

If the image-generation workflow is unavailable, return the polished prompt and briefly say that the prompt is ready for image generation.

## Random Elements

Select one value from each category. For职业关联 categories, select from the matching `职业类型`.

| Category | 武将 | 智将 | 敏将 | 辅将 |
| --- | --- | --- | --- | --- |
| 披风/披肩 | 红色厚重披风, 暗红长披风 | 青灰长袍披肩, 深蓝长袍飘带 | 暗红轻便披风, 深蓝轻披风 | 明亮轻飘披风, 华丽轻披风 |
| 头饰/发饰 | 战盔, 羽毛冠 | 法冠, 流苏头饰 | 轻盔, 无饰头盔 | 发簪头饰, 神秘头饰 |
| 服装/甲胄 | 龙鳞胸甲配战袍, 虎纹肩甲配劲装, 轻型锁子甲, 武将披挂战袍, 皮革护肩与束袖战衣, 金属护心镜配锦袍 | 绣花长袍, 锦缎法袍, 羽纹宽袖谋士袍, 青灰文士长衫, 轻薄披肩礼服, 暗纹丝绸官服 | 轻甲皮革, 护腕装甲, 短打劲装配软甲, 贴身骑射战衣, 暗纹披肩轻甲, 便捷束腰战袍 | 饰纹丰富布料, 轻甲绣饰, 华丽礼袍配护肩, 柔软丝绸披挂, 神秘纹样长袍, 辅臣锦衣配轻护甲 |
| 色彩点缀 | 金色盔甲边缘, 宝石红披风 | 青灰丝绸装饰, 暗灰腰带 | 深色披风点缀, 暗红腰带 | 明亮丝绸点缀, 柔和装饰色 |

Select one from each global category:

- 发型/头发流动: `长发飘动`, `短发整齐`, `辫发`, `飘散刘海`.
- 光影特效: `暗光`, `柔光`, `背光`, `微光反射`.
- 镜头/视角: `正脸`, `左侧脸`, `右侧脸`, `轻微俯视`, `轻微仰视`, `三分之二侧脸`.

## Image Prompt Template

Compose a polished prompt in Chinese. Keep the order close to:

```text
{角色名}，头肩特写立绘，{姿势}，{镜头/视角}，重点展示面部、眼神和表情，{职业类型}，国风、二次元、半写实风格，{符合人物性格的表情/气质}，{武器/道具展示规则}，{随机披风}，{随机头饰}，{随机服装/甲胄}，{随机发型}，{随机色彩点缀}，{随机光影特效}，透明背景/镂空背景，参考光荣三国志10美术风格
```

For `武器/道具展示规则`, use one of:

- If the weapon should be visible: `{武器/道具}由画面内可见的手自然握持，手指结构正确，握持姿势合理`.
- If the weapon is not necessary for the portrait: `不展示武器，避免武器遮挡面部和表情`.
- If `武器/道具` is missing, remove that segment and its extra comma.

Append these generation constraints when creating an image:

```text
高质量角色头像设定图，画面只包含头部至肩部，人物面部完整清晰，眼神和表情明确，服饰层次丰富，金属、皮革、丝绸或布料质感明确，透明背景，alpha通道，镂空背景，无任何可见背景色、底色、渐变、阴影底板、场景或边框，无文字，无水印，不要全身，不要半身到腰，不要现代服饰，不要照片写实脸。若展示武器，必须出现正常握持武器的手；否则不要展示武器。
```

Do not expose the random selection process unless the user asks for variants or the selected elements.

## Variants

When the user asks for multiple versions, vary the random elements while keeping the same core style. For each variant, include a compact label such as `版本A` and then the prompt.

For multiple generated images, create one prompt per version and run one image-generation call per version. Keep character identity and core request stable; vary costume, hair, colors, and lighting.

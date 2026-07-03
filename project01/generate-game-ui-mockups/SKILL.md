---
name: generate-game-ui-mockups
description: Generate game UI mockup images and visual design drafts with the available image-generation workflow, preferably image_gen/gpt-image-2 when active. Use when the user asks for game UI screens, interface concepts, UX mockups, menus, HUDs, panels, dashboards, layout drafts, visual style exploration, or iterative UI revisions for games such as PVE auto-battlers, roguelike runs, RPG character management, stage selection, skill/equipment screens, battle preparation, rewards, and settlement screens. Return an image mockup for review unless the user asks for prompt text only.
---

# Game UI Mockup Image Generation

## Workflow

Generate visual UI mockups, not only text descriptions.

1. Identify the UI screen type and player task.
2. Before composing any prompt for the `D:\Codex\project01` Three Kingdoms project, read the UI documentation entrypoints:
   - `docs/design/ui-ux/ui-index.md`
   - `docs/design/ui-ux/ui-guidelines.md`
   - `docs/design/ui-ux/asset-manifest.md`
3. If the target screen is related to an existing confirmed screen, also read the corresponding design note, such as:
   - `docs/design/ui-ux/home-map-stage-select-v02.md`
   - `docs/design/ui-ux/battle-hud-v07.md`
   - `docs/design/ui-ux/battle-prep-choice-v04.md`
4. Compose a concise UI image prompt using the template below, explicitly preserving confirmed design rules from the relevant notes.
5. Use the available image-generation workflow to create the mockup. Prefer built-in `image_gen` / gpt-image-2 behavior when available.
6. Return the generated image and the final prompt used.
7. If the user gives feedback, revise the prompt with only the requested changes and generate a new mockup.

If the user asks for `只要方案`, `只要提示词`, `prompt only`, or pure UX analysis, return text only.

## Required Inputs

Infer reasonable defaults when possible. Ask only when a missing input would materially change the screen.

- `游戏类型`: required; infer from project context when available.
- `界面名称`: required, such as `主界面`, `战斗HUD`, `阵容编成`, `技能装配`, `装备配置`, `关卡选择`, `战备3选1`, `结算`.
- `核心玩家任务`: required; what the player must do on this screen.
- `视觉风格`: optional; infer from project context.
- `画幅`: optional; default to `16:9 横屏游戏界面`.
- `必须出现的信息`: optional.
- `不应出现的信息`: optional.

## UI Design Rules

- Produce a real game UI mockup, not a landing page, poster, splash art, or pure background illustration.
- Prioritize readability: clear hierarchy, legible labels, obvious primary action, and sufficient contrast.
- Keep UI dense enough for repeated gameplay, but avoid clutter that hides the main task.
- Use game-native panels, buttons, tabs, lists, cards, HUD elements, icons, meters, badges, and resource bars.
- Use Chinese UI text when the project/user is Chinese. Keep labels short and legible.
- Do not place long explanatory paragraphs inside the UI.
- Do not use tiny unreadable text, fake lorem ipsum, watermarks, browser chrome, phone mockup frames, or developer annotations.
- Use consistent visual language across related screens.
- For historical Three Kingdoms strategy projects, prefer a modern grand-strategy interface inspired by Koei Romance of the Three Kingdoms 14: clean strategic map texture, modern flat information panels, ink/stone/porcelain color blocks, restrained vermilion and aged-gold accents, thin borders, readable Chinese UI typography, and clear tactical data hierarchy.
- Avoid overusing old-fashioned scrolls, bamboo slips, parchment sheets, heavy carved frames, and prop-like historical decorations. Use them only as subtle accents when they improve theme without making the UI look dated.
- Avoid webgame-like dark fantasy lobbies, black-gold heavy monetization styling, neon glow, oversized glossy buttons, cluttered reward popups, and oppressive dark backgrounds unless explicitly requested.
- Preserve confirmed project constraints: default 2 active characters, maximum 4 character slots, same-layer map-based stage switching, lightweight battle HUD, bottom-centered vertical character cards for battle, and Roguelike three-choice battle preparation. Do not reintroduce discarded ideas from prior iterations.

## Screen-Specific Guidance

For `主界面`:
- Show the game title, a dominant primary action, major system entries, current progression, resources, and a restrained background that supports UI readability.
- The first screen should feel like an actionable game lobby, not a marketing hero.
- For Three Kingdoms projects, use a modern strategic mainland map or clean war-room command view rather than a dark battle poster or old scroll lobby.
- If the project has multiple PVE stages, prefer same-layer map-based stage switching on the main screen: show a Three Kingdoms mainland map with stage nodes placed on the map. Clicking a stage node should reveal that stage's information panel. Avoid hiding stage switching behind a dropdown or deep menu unless explicitly requested.

For `战斗HUD`:
- Show player/enemy status, wave progress, skill readiness, speed/pause controls, and combat readability indicators.
- Leave enough central space for battle action.

For `阵容编成`:
- Show selected lineup, bench/roster list, role tags, faction/profession synergy, and a clear confirm/start action.

For `技能装配`:
- Show a character portrait, six candidate skills, four equipped slots, keyword tags, and skill detail comparison.

For `装备配置`:
- Show equipment slots, inventory/grid, keyword synergy, and stat/flow impact.

For `关卡/难度选择`:
- Show stage cards or map nodes, difficulty ladder, unlock state, recommended build tags, and rewards.

For `战备3选1`:
- Show next-wave enemy preview, three ability choices, current run bonuses, and a clear confirm action.

For `结算`:
- Show victory/failure state, rewards, unlocked content, run summary, and next action.

## Prompt Template

Compose prompts close to this structure:

```text
生成一张{画幅}游戏UI示意图，界面为{界面名称}。
游戏类型：{游戏类型}。
核心玩家任务：{核心玩家任务}。
视觉风格：{视觉风格}。
布局要求：{主要区域、信息层级、按钮/面板/列表/HUD元素}。
必须出现：{必须出现的信息}。
避免出现：{不应出现的信息}。
要求：高可读性，中文界面文字清晰，主操作按钮突出，信息层级明确，游戏内真实UI截图风格，不是网页落地页，不是纯插画，无水印，无浏览器窗口，无手机边框。
```

## Iteration Rules

- For first drafts, generate one strong direction unless the user asks for multiple variants.
- For revisions, keep the approved structure and style stable; change only the requested details.
- If the user says a mockup is confirmed, do not keep redesigning that screen. Move to the next requested screen.
- When the user asks for multiple options, label them as `方案A`, `方案B`, `方案C` and generate one image per option.

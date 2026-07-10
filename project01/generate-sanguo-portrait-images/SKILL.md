---
name: generate-sanguo-portrait-images
description: Generate production-ready Three Kingdoms character half-body illustrations and avatar icons from one full-body 45-degree game-model reference. Use for batch character art, half-body portraits, square avatars, or circular avatars in this project. Enforce the required approval gate: generate no downstream avatar assets until the user explicitly approves the character's half-body illustration.
---

# Three Kingdoms Character Asset Pipeline

Create reusable character UI assets from a single full-body 45-degree model screenshot.

## Non-Negotiable Rules

- Accept one full-body 45-degree model image as the required visual source. Do not require face close-ups or upper-body source images.
- Do not generate or deliver full-body illustrations. The approved character illustration format is upper body only.
- Preserve the approved project direction: dark Chinese historical-fantasy game art; concise angular brushwork; controlled ink texture; readable red, black, and antique-gold accents; no glossy 3D-render look.
- Create the half-body illustration first. Stop and request explicit user approval.
- Do not generate square or circular avatars until the user explicitly approves that half-body illustration. Treat revisions as still pending approval.
- Use the approved half-body illustration as the visual source for every downstream avatar. Do not ask for additional face reference images.
- Save final assets as transparent PNG files. Do not include text, frames, watermarks, scenery, floor planes, cast shadows, or visible background color.
- Do not default to a centered front-facing, level-shouldered, stern passport-photo pose. Use that composition only when the character direction explicitly calls for formal authority or implacable restraint.

## Required Output Set

| Asset | Size | Composition |
| --- | --- | --- |
| Half-body illustration | 512 x 1156 | Crown/head, face, shoulders, chest, and upper abdomen. Narrow portrait composition. |
| Square avatar | 256 x 256 | Large face. Eyes near the image center. Crown and shoulders support recognition without empty space. |
| Circular avatar | 256 x 256 | Derived from the approved avatar composition. Keep face and recognition features inside the circle-safe area. Pixels outside the circle are transparent. |

Do not add full-body art to the standard set. Produce legacy 128 x 128 or 32 x 32 avatar variants only when the user explicitly requests them.

## Workflow

### 1. Intake

Collect:

- Character id and display name.
- One full-body 45-degree model screenshot.
- Optional personality, mood, or pose note.

Infer face, costume, hair, weapon, palette, silhouette, and iconic accessories from the model reference. Vary the half-body pose to fit the character's personality, but retain all visible identity anchors.

### Character Direction Brief

Before every half-body prompt, derive a compact direction brief from the character's historical reputation, combat identity, model silhouette, and any user note:

- `temperament`: for example, arrogant, calculating, reckless, composed, veteran, watchful, benevolent, or severe.
- `pose`: choose a three-quarter turn, shoulder lead, forward lean, relaxed backward tilt, guarded half-turn, weapon-led diagonal, or other personality-appropriate upper-body action.
- `eye line`: choose direct challenge, sidelong appraisal, lowered concentration, upward resolve, or a controlled off-camera look.
- `expression`: choose a specific emotional read rather than generic severity: restrained confidence, predatory focus, contempt, calm calculation, battle joy, wary patience, or quiet fatigue.

Keep the action inside the narrow upper-body crop. Use head yaw, torso angle, shoulder height, cloak/weapon direction, and eye line to create energy; do not solve pose variety by adding a full body or random effects.

Use these direction families as starting points, not rigid character classes:

| Character read | Suitable pose and expression direction |
| --- | --- |
| Proud warlord | Forward three-quarter lean, lifted chin, direct challenge or a restrained smirk. |
| Cunning strategist | Controlled half-turn, one shoulder leading, sidelong appraisal, quiet calculation. |
| Veteran general | Grounded asymmetric shoulders, calm direct gaze, seasoned patience rather than blank seriousness. |
| Agile fighter or assassin | Guarded twist, lowered center through shoulder angle, watchful eyes, poised tension. |
| Noble commander | Relaxed upright posture, slightly raised chin, composed authority. |
| Fierce berserker | Weapon-led diagonal, compressed brow, visible aggression or battle joy. |

For characters produced in the same batch, change at least two of these axes between adjacent characters: head yaw, shoulder line, torso inclination, eye line, weapon/cloak direction, and expression. Do not reveal this selection process unless the user asks.

### 2. Half-Body Approval Gate

Generate only the half-body illustration. Compose it for a 140:316-like narrow portrait, then export it at 512 x 1156.

Show the result and ask for approval. Mark the asset state as `half_body_pending` until the user explicitly says it is approved.

When the user asks for a revision, revise only the half-body illustration and return to `half_body_pending`. Do not create avatars.

Only after explicit approval, mark the state as `half_body_approved` and continue.

### 3. Avatar Production

Use the approved half-body image as an identity and style reference.

- Generate a close face-and-shoulders avatar master with the face large enough to remain readable at 256 px.
- Export the square avatar at 256 x 256.
- Create the circular avatar at 256 x 256 from the same approved avatar composition. Use a circular alpha mask; do not bake a circular frame or background.

### 4. Transparency and QA

Use a flat #00ff00 chroma-key background during image generation. Explicitly remove #00ff00 afterwards; do not rely on automatic border-color selection when the subject touches the edge.

Validate every final asset:

- Exact required pixel dimensions.
- RGBA alpha channel present.
- Transparent outer corners for the circular avatar.
- No visible green key-color fringe, especially around hair, plumes, sharp armor, and gold highlights.
- No clipped face, crown, or primary shoulder identifier.
- No accidental text, UI, weapon fragments, or background.
- Pose and expression communicate the direction brief; the result does not read as a generic ID-photo stance.

Use a temporary preview only for QA. Do not combine final deliverables into a contact sheet.

## Storage

Store final files together at:

`assets/characters/{character_id}/vNN-halfbody-avatar-256/`

Use these filenames:

- `{character_id}-upperbody-512x1156.png`
- `{character_id}-avatar-square-256.png`
- `{character_id}-avatar-circle-256.png`

Keep a short `manifest.json` in the same version folder with the model source path, the approved half-body source path, output dimensions, `approval_state`, and the selected `character_direction` brief.

## Prompt Constraints

For half-body art, specify a narrow vertical crop, the selected direction brief, large shoulder identifiers, chest and upper abdomen, and no legs or full-body pose. Center the face only when the pose direction calls for it; otherwise preserve a deliberate three-quarter or asymmetrical composition.

For avatars, specify a large face, eyes near center, minimal empty space, and a circle-safe margin. Preserve the approved half-body's emotional read instead of reverting to a neutral expression. Never simply shrink a distant full-body illustration into an icon.

State the identity anchors from the model reference in every prompt. Use the approved half-body asset as the strongest style and facial reference after approval.

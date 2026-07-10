# Character Portrait Production Rules

This document defines the production contract for Three Kingdoms character illustrations and avatars.

## Source Requirement

- Accept one full-body 45-degree game-model screenshot as the only required visual source.
- Do not request upper-body or face close-up reference images.
- Infer the face, costume, hair, accessories, silhouette, and weapon from the supplied model.

## Locked Art Direction

- Use the latest approved dark Three Kingdoms character-art direction: angular brushwork, restrained ink texture, clear silhouette, and controlled red, black, and antique-gold accents.
- Retain model identity anchors while allowing personality-driven half-body poses.
- Deliver transparent PNG assets without text, UI frames, scenery, shadows, or visible background color.

## Character Pose and Expression

- Before each half-body illustration, define a direction brief from the character's reputation, combat identity, model silhouette, and any supplied personality note: temperament, upper-body pose, eye line, and expression.
- Do not default to a centered, level-shouldered, stern front view. Treat it as a deliberate choice for characters whose identity genuinely calls for formal authority or immovable restraint.
- Create energy through a three-quarter turn, shoulder lead, torso tilt, head yaw, eye direction, cloak/weapon direction, and a specific expression. Keep the action inside the narrow half-body crop.
- Use distinctive reads such as arrogant challenge, quiet calculation, veteran patience, wary focus, predatory concentration, battle joy, or composed authority. Do not reduce every character to the same serious stare.
- In a batch, change at least two of head yaw, shoulder line, torso inclination, eye line, weapon/cloak direction, and expression between adjacent characters.
- The square and circular avatars must preserve the approved half-body illustration's emotional read rather than reverting to a neutral ID-photo crop.

## Mandatory Approval Gate

1. Generate the 512 x 1156 half-body illustration first.
2. Stop and wait for explicit user approval.
3. Generate the 256 x 256 square and circular avatars only after that approval.
4. Any requested half-body revision resets the work to pending approval.

No full-body illustration belongs to the standard production set.

## Standard Deliverables

| Asset | Size | Notes |
| --- | --- | --- |
| Half-body illustration | 512 x 1156 | Narrow portrait showing crown/head, face, shoulders, chest, and upper abdomen. |
| Square avatar | 256 x 256 | Large face, eyes near center, minimal empty space. |
| Circular avatar | 256 x 256 | Face and identity features stay inside circular safe area; outer corners are transparent. |

Create 128 x 128 or 32 x 32 variants only when explicitly requested.

## Export and QA

- Use a #00ff00 chroma-key background during generation, then remove that exact key color.
- Verify RGBA alpha, dimensions, unclipped facial identifiers, transparent circular corners, and absence of green edge spill.
- Store final deliverables at `assets/characters/{character_id}/vNN-halfbody-avatar-256/`.
- Include a `manifest.json` recording the model source, approved half-body source, output dimensions, approval state, and character direction brief.

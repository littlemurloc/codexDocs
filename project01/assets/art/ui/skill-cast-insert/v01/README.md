# Skill Cast Insert Shared Layers

This directory contains only newly created shared artwork for the left-middle skill cast insert.

## Deliverables

- Five transparent ink brush themes in `transparent/`.
- One shared bamboo scroll for all military strategy skills.
- One transparent sheet of optional antique-gold trim fragments.
- A checkerboard alpha preview in `preview/shared-layer-alpha-checker.png`.

## Reuse Instead Of Duplicating

- Use existing hero upper-body portraits.
- Use existing square ability and strategy-card icons.
- Use the existing ability icon frame and ability-name slot.
- Implement battlefield dimming, the short energy sweep, and reveal motion in the runtime material/animation system.

## Assembly Order

1. Apply runtime battlefield dimming.
2. Place one themed ink brush at left-middle.
3. Add a hero portrait or `strategy-scroll-base`.
4. Add the existing square icon frame and selected skill icon.
5. Add the existing short ability-name slot.
6. Optionally scatter a few isolated gold fragments.
7. Animate the ink reveal and short colored sweep, keeping the entire group within 30 percent screen width and 35 percent screen height.

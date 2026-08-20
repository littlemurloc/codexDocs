# dialogue-sanguo-v01

Three Kingdoms dialogue UI templates with an empty portrait slot.

## Files

- `raw-generated/`: original generated preview images with dark backing.
- `transparent/`: early transparent test exports. Do not use for production.
- `transparent-clean-alpha/`: production candidates rebuilt from the clean raw sources. Use these.
- `transparent-fixed/`: rejected repair attempt if present. Do not use.
- `_deprecated-transparent-fixed-do-not-use/`: rejected repair attempt if present. Do not use.
- `preview/dialogue-frame-empty-portrait-transparent-contact-sheet-v01.png`: checkerboard preview of the transparent exports.
- `preview/dialogue-frame-empty-portrait-fixed-white-bg-preview-v01.png`: white-background check for the fixed exports.

## Production Transparent Exports

Use these files:

- `dialogue-frame-empty-portrait-blue-transparent-clean-alpha-v01.png`
- `dialogue-frame-empty-portrait-red-transparent-clean-alpha-v01.png`
- `dialogue-frame-empty-portrait-green-transparent-clean-alpha-v01.png`
- `dialogue-frame-empty-portrait-gold-transparent-clean-alpha-v01.png`

## Early Transparent Exports

- `dialogue-frame-empty-portrait-blue-transparent-v01.png`
- `dialogue-frame-empty-portrait-red-transparent-v01.png`
- `dialogue-frame-empty-portrait-green-transparent-v01.png`
- `dialogue-frame-empty-portrait-gold-transparent-v01.png`

## Usage Notes

These assets keep the left portrait frame empty so character art can be placed above the colored portrait backplate.

For variable-width dialogue boxes, avoid nine-slicing the full image because it will distort the portrait frame. Use one of these approaches instead:

1. Use the full PNG at fixed width.
2. Split implementation into layers: fixed left portrait frame + stretchable right dialogue panel.
3. If using a single sprite, keep the left portrait area and right decorative end caps fixed, and only stretch the central parchment area of the dialogue panel.

Suggested stretch region:

- Do not stretch the left portrait frame.
- Do not stretch the right pointed end cap.
- Do not stretch the lower speech tail.
- Stretch only the clean central parchment band between the name plate area and the right end ornament.

All text areas are intentionally empty: portrait, name, and dialogue copy should be added in engine.

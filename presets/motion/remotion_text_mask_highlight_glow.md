# Remotion Text Mask Highlight Glow

Use this preset for programmatic CapCut-style highlight wipes, split-mask
gradients, and glow sweeps in Remotion.

## Pattern

`base text -> absolute duplicate styled text -> animated clip-path/mask -> optional masked glow duplicate -> hold`

## Settings

- Timing: start after the word is readable; finish before the next reading task.
- Mask: travel from fully off-word to fully off-word.
- Glow: keep inside the same masked group as the sharp duplicate.
- Text: duplicate layer must match font, size, tracking, line breaks, and position.

## QC

- No pre-glow, tail glow, or leftover mask sliver.
- Styled and plain text states remain readable at phone size.
- Captions are suppressed or repositioned if the styled text carries the spoken phrase.

## Related Cards

- `technique_cards/typography_programmatic_text_mask_highlight_glow_001.json`
- `technique_cards/typography_remotion_sequence_local_kinetic_presets_001.json`


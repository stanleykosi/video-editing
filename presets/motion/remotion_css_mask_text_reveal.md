# Remotion CSS Mask Text Reveal Preset

## Use When

- Building split-color text, highlight wipes, glow reveals, or soft masked title
  effects in Remotion.

## Layer Pattern

`base_text -> duplicate_styled_text -> CSS mask or SVG mask -> optional masked glow duplicate -> readable hold`

## Starting Values

- Fast short-form reveal: 6-15 frames at 30 fps.
- Calmer title/lower-third reveal: 12-24 frames at 30 fps.
- Mask travel: start fully off-word and end fully off-word.
- Soft edge: keep feather narrow enough that letters stay crisp.

## Implementation Notes

- Use CSS masks for soft opacity gradients.
- Use `clip-path` for hard rectangular reveals.
- Use alpha mask mode when opacity should drive visibility.
- Use luminance mask mode only when grayscale brightness should drive visibility.

## QC

- Base and duplicate text align at start, midpoint, hold, and clear frames.
- No pre-glow, tail glow, or mask sliver.
- Ordinary captions are suppressed or repositioned when the masked text carries
  the spoken phrase.

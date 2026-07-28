# Programmatic Typography QC

Use this checklist before approving Remotion or FFmpeg-generated title,
caption-emphasis, highlight, glow, glitch, or word-by-word typography.

## Source And Reproducibility

- Remotion text effects use Sequence-local frame logic, not hard-coded global
  timeline starts.
- Remotion glitch, scramble, jitter, or particle-like text uses deterministic
  seeded randomness.
- Remotion transparent overlay renders have no painted root background and show
  checkerboard in empty canvas areas before export.
- FFmpeg text renders use explicit `fontfile` paths or a documented fallback.
- Generated FFmpeg filter graphs are logged or reproducible from structured data.
- Alpha overlay metadata records codec, pixel format, fps, duration, resolution,
  and source recipe.

## Timing

- Text appears no earlier than its intended phrase, beat, or visual reference.
- Entrance, pop, wipe, or glitch settles before the viewer needs to read the word.
- Mask/glow reveals start off-word and end off-word with no sliver or glow leak.
- Word-by-word windows match transcript timing or beat timing within the intended tolerance.
- Final readable states hold long enough to read before clearing.

## Layout

- Base and duplicate text layers align exactly through the whole mask/glow pass.
- Text remains inside safe areas at the smallest and largest animated states.
- Text does not cover faces, proof, UI, products, maps, captions, or action.
- Captions are visible, repositioned, or explicitly approved for suppression when designed text carries the same words.

## Rendering

- Contact sheets cover reveal start, midpoint, final hold, and clear frame.
- Bright, dark, and busy representative frames preserve text contrast.
- Glow, blur, RGB split, and blend modes preserve crisp readable edges.
- FFmpeg drawtext chains are split or pre-rendered before they become brittle.
- Remotion transparent overlay renders match the final video resolution, fps, and duration.
- Reusable transparent overlays use alpha-capable output such as ProRes 4444 or
  PNG sequences, not ordinary MP4.
- Empty overlay areas are transparent, not black.
- FFmpeg `alphamerge` foreground and mask streams match width, height, fps,
  duration, and timing.
- Grayscale masks are previewed before final compositing, with correct polarity:
  white reveals and black hides.
- Alpha edges are checked over bright and dark backgrounds for halos,
  premultiply issues, and glow contamination.

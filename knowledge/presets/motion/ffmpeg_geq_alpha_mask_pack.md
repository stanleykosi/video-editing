# FFmpeg GEQ Alpha Mask Pack Preset

## Use When

- Generating procedural alpha masks for text highlights, radial reveals, soft
  spotlights, wave shimmers, or mask debugging.

## Mask Types

- Linear X/Y gradient: highlight bars, left/right or top/bottom reveals.
- Radial distance mask: spotlight, aura, pulse, or center reveal.
- Gaussian-style mask: soft focus reveal.
- Checker mask: debugging alpha pipeline and polarity.
- Wave mask: liquid, shimmer, scanline, or stylized energy pass.

## Workflow

1. Generate and preview the grayscale mask.
2. Pre-render the mask if it is expensive or reused.
3. Attach it to the foreground with `alphamerge`.
4. Composite or export with an alpha-capable format.

## QC

- Mask preview confirms direction, polarity, and softness.
- Wave masks do not reduce text readability.
- Heavy `geq` masks are pre-rendered when repeated.
- No semi-transparent tail remains after the reveal should be complete.

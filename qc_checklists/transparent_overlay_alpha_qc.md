# Transparent Overlay Alpha QC

Use this checklist before approving Remotion or FFmpeg-generated transparent
overlays, alpha masks, text reveal assets, lower thirds, glow sweeps, or reusable
motion-graphic intermediates.

## Source And Render Setup

- Transparent Remotion compositions show checkerboard in empty areas before render.
- No root wrapper, CSS reset, background card, or full-frame container paints an
  opaque background unless the render is intentionally opaque.
- Reusable editor overlays use an alpha-capable output such as ProRes 4444 or a
  PNG image sequence.
- Browser-targeted WebM alpha files have documented target browser/platform
  support and an opaque fallback when needed.
- Imported alpha videos in Remotion use transparent mode only when the source
  actually contains alpha.

## FFmpeg Alpha Graph

- `alphaextract` is used to inspect or reuse existing alpha when debugging.
- `alphamerge` is used only after foreground and mask streams match width, height,
  fps, duration, and timing.
- Mask polarity is correct: white/high values reveal and black/low values hide.
- `overlay` is not expected to create transparency by itself.
- Final pixel format/container preserves alpha until the workflow intentionally
  composites into an opaque delivery file.

## Visual Review

- Empty overlay areas are transparent, not black, in sampled frames.
- Contact sheets include reveal start, midpoint, final hold, and clear frame.
- The same overlay is checked over bright and dark backgrounds.
- Soft text, glow, blur, and antialiasing edges have no black/white halo.
- No pre-glow, tail glow, leftover mask sliver, or unintended semi-transparent
  tail remains.
- Caption, face, proof, UI, product, map, chart, and action safe areas remain clear.

## Performance And Maintainability

- Heavy procedural `geq` masks are pre-rendered when reused.
- Generated masks are previewed as grayscale before final compositing.
- Overlay filename or metadata records effect name, resolution, fps, duration,
  alpha status, and source recipe.
- The project stores enough graph/component metadata to regenerate the overlay.

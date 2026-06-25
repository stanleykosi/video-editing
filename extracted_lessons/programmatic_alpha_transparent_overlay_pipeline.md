# Lesson: Programmatic Alpha And Transparent Overlay Pipeline

## Source

- Tutorials/docs:
  - `transcripts/remotion_transparent_videos_source_notes.md`
  - `transcripts/remotion_creating_overlays_source_notes.md`
  - `transcripts/remotion_offthreadvideo_transparent_source_notes.md`
  - `transcripts/curio_ffmpeg_alpha_masking_source_notes.md`
  - `transcripts/hhsprings_ffmpeg_alphamerge_alphaextract_source_notes.md`
  - `transcripts/hhsprings_ffmpeg_alphamerge_alphaextract_more_source_notes.md`
  - `transcripts/ffmpeg_filters_alpha_masking_official_source_notes.md`
  - `transcripts/ffmpeg_wipe_reveal_alpha_mask_source_notes.md`
  - `transcripts/mdn_css_masking_source_notes.md`
- Related cards:
  - `technique_cards/programmatic_remotion_prores4444_alpha_overlay_export_001.json`
  - `technique_cards/programmatic_remotion_webm_alpha_overlay_export_001.json`
  - `technique_cards/programmatic_remotion_offthreadvideo_alpha_import_001.json`
  - `technique_cards/programmatic_remotion_css_mask_text_reveal_001.json`
  - `technique_cards/programmatic_ffmpeg_alphamerge_alpha_mask_pipeline_001.json`
  - `technique_cards/programmatic_ffmpeg_alphaextract_mask_reuse_001.json`
  - `technique_cards/programmatic_ffmpeg_geq_procedural_alpha_masks_001.json`
  - `technique_cards/programmatic_ffmpeg_in_place_wipe_reveal_alpha_001.json`

## What The Sources Teach

This source pack turns prior CapCut text-mask knowledge into a reproducible
programmatic pipeline. Remotion should handle text layout, CSS masks, spring or
frame-exact motion, and transparent overlay export. FFmpeg should handle alpha
inspection, alpha-mask attachment, procedural mask generation, final compositing,
and export verification.

The main distinction is intent:

- Use Remotion when text layout, responsive typography, component reuse, CSS
  masking, and editor-friendly transparent overlay export matter.
- Use FFmpeg when the agent is compositing video streams, attaching grayscale
  masks as alpha, pre-rendering heavy procedural masks, or validating final files.
- Use CapCut/Premiere/Resolve equivalents only as editable NLE analogues; do not
  use chroma key as a workaround when true alpha is available.

## Agent Decision Rules

- Prefer ProRes 4444 transparent `.mov` or PNG sequences for editor/compositing
  handoff. Use WebM alpha only for browser-targeted output with documented support.
- A transparent overlay must have no painted composition background and must use
  an alpha-capable frame format, codec, and pixel format.
- Use `<OffthreadVideo transparent />` only for imported source videos that truly
  contain alpha. Do not enable it for opaque footage.
- Use CSS `mask-image`/SVG masks in Remotion when text reveals need soft
  opacity gradients; use `clip-path` for hard rectangular/path reveals.
- Use FFmpeg `alphamerge` when attaching a grayscale mask to a foreground layer.
- Use FFmpeg `alphaextract` when an existing alpha plane needs inspection, reuse,
  modification, or round-trip debugging.
- Use `maskedmerge` when directly blending two opaque images through a mask; use
  `alphamerge` when the goal is a reusable transparent foreground.
- Use `overlay` only after alpha has been created or confirmed. A plain overlay
  does not create a reveal by itself.
- Pre-render expensive `geq` masks when reused or when iteration becomes slow.
- If black rectangles or dark edge fringes appear, verify codec, pixel format,
  premultiply/unpremultiply behavior, and alpha preservation before redesigning
  the effect.

## Timeline Patterns

### Remotion to editor overlay

`transparent_remotion_component -> no_background_preflight -> png_frames -> prores_4444_yuva444p10le -> import_above_footage -> edge_qc`

Use for reusable lower thirds, title glows, text highlight sweeps, split-color
type, and transition overlays.

### Remotion CSS mask text reveal

`base_text -> duplicate_styled_text -> CSS_mask_or_clip -> optional_masked_glow -> local_frame_progress -> transparent_export_or_final_composite`

Use when the type is generated in Remotion and needs responsive positioning,
duplicate-layer alignment, and soft mask control.

### FFmpeg alpha-mask composite

`foreground_or_text_render -> grayscale_mask -> alphamerge -> overlay_over_background -> probe_and_contact_sheet_qc`

Use when the foreground is already rendered or the final composite happens in
FFmpeg.

### FFmpeg in-place wipe reveal

`black_source + white_source -> xfade_wipe_mask -> alphamerge_on_foreground -> overlay_over_background`

Use when a foreground must reveal in place rather than slide. This is safer than
direct `xfade` when the top layer has transparency.

## Timing Rules

- Short-form text wipes often work in 6-15 frames at 30 fps.
- Lower thirds and calmer title overlays can use 12-24 frames when the phrase
  remains readable.
- Reveal masks should finish before the viewer needs to read the full phrase.
- A glow/highlight layer should not appear before the base letter is visible and
  should not remain after the reveal clears.
- Transparent overlay duration, fps, and frame count must match the edit window
  or the mask pass will drift.

## Implementation Notes

### Remotion

- Keep reusable text effects Sequence-local.
- Do not set a root background for transparent overlays.
- Export editor overlays with PNG frame extraction, ProRes 4444, and
  `yuva444p10le`.
- Export browser overlays with PNG frame extraction, VP8/VP9, and `yuva420p`,
  only when WebM alpha support fits the delivery target.
- Use CSS masks for opacity gradients and `clip-path` for hard reveals.
- Import existing alpha clips with `<OffthreadVideo transparent />` and trim them
  to the visible range.

### FFmpeg

- Use `alphaextract` to inspect or reuse existing alpha.
- Use `alphamerge` to attach grayscale masks to foreground streams.
- Use `geq` to generate linear, radial, Gaussian, checker, or wave masks.
- Use `xfade` cautiously as a mask generator; keep input dimensions, fps, pixel
  format, duration, and timebase compatible.
- End in an alpha-capable output format if the result remains a reusable overlay.
- End in an opaque delivery format only after final background compositing.

### CapCut/Premiere/Resolve Equivalent

- CapCut: duplicate text, compound only the layer that needs masking, keyframe
  Split/Film Strip masks, and use true alpha assets when importing external
  overlays instead of chroma-keying.
- Premiere: duplicate Essential Graphics, use track mattes/Linear Wipe/masks,
  import ProRes 4444 overlays above footage, and inspect for black rectangles.
- Resolve: use Fusion masks/merge nodes or imported ProRes 4444 overlays; check
  alpha interpretation and node order.

## Mistakes And QC

- Mistake: calling an overlay transparent before checking alpha with `ffprobe` or
  a checkerboard preview.
- Mistake: exporting Remotion transparent overlays as ordinary MP4.
- Mistake: using `overlay` alone while expecting a masked reveal.
- Mistake: using `xfade` directly on a transparent top layer and accepting black
  where alpha should be empty.
- Mistake: generating a procedural mask without previewing polarity and edge
  softness.
- Mistake: stripping alpha with a final pixel format conversion.
- Mistake: using a wave/liquid mask on readable captions until the phrase becomes
  harder to parse.

Actionable checks:

- `ffprobe` confirms an alpha-capable codec/pixel format for reusable overlays.
- A sampled empty area of the overlay is transparent, not black.
- Mask preview shows correct polarity: white reveals, black hides.
- Foreground and mask dimensions, fps, duration, and timebase match before
  `alphamerge`.
- Contact sheets include reveal start, midpoint, final hold, and clear frame.
- The overlay is tested over both bright and dark backgrounds.
- Edge fringes are checked before approving glow, blur, and antialiased text.

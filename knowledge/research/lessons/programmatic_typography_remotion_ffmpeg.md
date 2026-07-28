# Lesson: Programmatic Typography With Remotion And FFmpeg

## Source

- Tutorial: Remotion Lab Kinetic Typography Presets
- Notes: `knowledge/research/source_notes/remotion_lab_kinetic_typography_presets_source_notes.md`
- Tutorial: FFmpeg Drawtext Animations
- Notes: `knowledge/research/source_notes/brayden_ffmpeg_drawtext_animations_source_notes.md`
- Related cards:
  - `knowledge/techniques/typography/typography_programmatic_text_mask_highlight_glow_001.json`
  - `knowledge/techniques/typography/typography_remotion_sequence_local_kinetic_presets_001.json`
  - `knowledge/techniques/typography/typography_remotion_seeded_scramble_glitch_001.json`
  - `knowledge/techniques/typography/typography_remotion_stagger_spring_text_motion_001.json`
  - `knowledge/techniques/typography/typography_remotion_blur_scale_morph_001.json`
  - `knowledge/techniques/typography/typography_ffmpeg_drawtext_timed_overlay_001.json`
  - `knowledge/techniques/typography/typography_ffmpeg_fade_pop_envelope_001.json`
  - `knowledge/techniques/captions/typography_ffmpeg_sequential_word_drawtext_001.json`

## What The Tutorial Teaches

These sources convert CapCut-style text effects into reusable programmatic
patterns. Remotion is the better path for complex typography because it can use
React components, frame-local timing, CSS masks, deterministic random values,
springs, and layered text. FFmpeg `drawtext` is useful for simple timed text,
fade envelopes, font-size pops, and generated word-by-word overlays, but complex
mask/glow work should usually be pre-rendered as transparent overlays or built
in Remotion before final compositing.

## Agent Decision Rules

- Use Remotion when the effect needs reusable components, per-word or
  per-character timing, CSS `clip-path`, spring motion, seeded glitch, or
  transparent overlay renders.
- Use FFmpeg `drawtext` when the text is simple, timing is known, and the effect
  can be expressed as text placement, visibility windows, alpha, font size,
  shadow, border, or box styling.
- Do not force dense kinetic typography into one huge FFmpeg filter graph. If
  the graph becomes hard to read, pre-render the text pass or switch to Remotion.
- Treat CapCut text-mask, highlight, gradient, and glow effects as layer graphs:
  base text, duplicate styled text, animated reveal mask, optional glow/blur
  duplicate, and phone-size QC.
- Use deterministic randomness for Remotion glitch/scramble work. Direct random
  calls can create preview/render mismatch and flicker.
- Use `interpolate()` for exact timed reveals; use `spring()` for weight, pop,
  bounce, and staggered motion.
- Use explicit `fontfile` paths in FFmpeg when reproducible rendering matters.

## Timeline Patterns

### Programmatic highlight/glow text mask

`base_video -> base_text -> duplicate_text_or_highlight_group -> animated_mask -> optional_blur_or_glow_duplicate -> composite -> contact_sheet_qc`

- Base and duplicate text layers must align exactly.
- The mask starts off-word and ends off-word.
- The glow layer should be revealed by the same timing as the sharp text layer so
  there is no pre-glow or tail glow.

### Remotion reusable typography preset

`parent_timeline -> Sequence(from, duration) -> local_useCurrentFrame -> progress_or_spring -> transform/opacity/mask -> hold/readability_qc`

- Components assume their first local frame is 0.
- Parent sequences decide placement against narration, beats, or edit sections.
- Long text uses phrase or word animation; character effects are reserved for
  short words.

### FFmpeg drawtext overlay

`input_video -> drawtext_with_fontfile -> enable_window -> alpha_or_fontsize_expression -> optional_shadow_border_box -> output_or_next_label`

- Use `text_w` and `text_h` to keep centered text stable while font size changes.
- Chain overlays with labels only while the graph stays debuggable.
- For long word-level captions, prefer generated ASS or Remotion.

## Implementation Notes

### Remotion

- Store typography as components with props for text, start frame, duration,
  phrase lines, impact words, safe region, font role, motion mode, caption
  suppression, and QC status.
- Use `<Sequence>` to make each text effect reusable at any timeline position.
- Drive exact wipes with `interpolate()` and clamp the result.
- Drive elastic or weighted entrances with `spring()` and delay each word or
  character with `frame - index * delay`.
- Use CSS `clip-path: inset(...)` for straight highlight wipes and duplicate
  text masks.
- Use stacked colored text layers plus deterministic jitter for RGB/glitch text.
- Keep large blur values limited and preview at target delivery resolution.

### FFmpeg

- Use `drawtext` for programmatic text when placement, timing, alpha, size,
  shadow, border, and simple windows are enough.
- Prefer explicit `fontfile` paths over system font names in agent workflows.
- Generate complex filter graphs from structured data rather than hand-writing
  long command strings.
- Use `enable` windows for text layer timing.
- Use `alpha` envelopes for fade-in/hold/fade-out.
- Use animated `fontsize` for simple pop and bounce approximations.
- Use labeled filter chains for sequential word overlays, then switch to
  pre-rendered passes when the chain becomes too long.
- For true split-mask/glow reveals, pre-render or generate the styled text layer
  and composite it with an animated alpha mask rather than relying on raw
  `drawtext` alone.

### CapCut And Premiere Equivalents

- CapCut: duplicate text, compound only the layer that needs a mask/effect, apply
  Split or Film Strip masks, animate the mask off-word to off-word, and review
  glow/gradient edges.
- Premiere: duplicate Essential Graphics text, use nests or masks for reveals,
  use Transform scale for pop, and use Linear Wipe/track matte approaches for
  simple highlight passes.

## Mistakes And QC

- Do not copy decorative CapCut effects into code before base typography is
  readable.
- Do not use direct non-deterministic randomness in Remotion render logic.
- Do not let a glow layer appear before the reveal band reaches the word.
- Do not animate FFmpeg font size without checking centered placement and safe
  margins.
- Do not build a word-by-word `drawtext` chain so long that it cannot be debugged
  or regenerated.
- Check final output frames, not only component previews.
- Verify text layer alignment, mask start/end states, font availability, caption
  collisions, and delivery-size readability.


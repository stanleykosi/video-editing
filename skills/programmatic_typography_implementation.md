# Programmatic Typography Implementation

## Purpose

Guide the agent when recreating CapCut-style text masks, highlight wipes, glow
sweeps, glitch text, word staggers, pop captions, title cards, hook cards, lower
thirds, and timed overlays with HyperFrames, Remotion, ASS, or FFmpeg instead of
inside CapCut.

## When To Use This Skill

- Reproducing CapCut text-mask, glow, highlight, gradient, or pop effects outside
  CapCut.
- Building reusable Remotion typography components for titles, hooks, captions,
  or explainer graphics.
- Building HyperFrames title cards, hook cards, chapter cards, stat cards, lower
  thirds, and transparent HTML/CSS typography overlays.
- Generating FFmpeg text overlays, fade/pop envelopes, or short word-by-word
  sequences from structured timing data.
- Deciding whether an effect belongs in FFmpeg `drawtext`, Remotion, Premiere,
  CapCut, or a pre-rendered overlay pass.
- QCing programmatic typography before the final edit is called finished.

## Core Principles

- Programmatic typography is still typography first: message, hierarchy, line
  break, contrast, and safe placement come before motion.
- CapCut-style premium text effects are layer graphs: base text, duplicate styled
  text, mask or matte, optional glow/blur duplicate, and final readability QC.
- True alpha is the preferred handoff for reusable glow, highlight, lower-third,
  mask-wipe, and title overlays; do not use chroma key or black backgrounds when
  ProRes 4444, PNG sequences, or alpha-preserving compositing is available.
- Remotion is preferred for complex kinetic type because components can use local
  frame timing, CSS masks, springs, deterministic randomness, and clean props.
- HyperFrames is preferred for title cards, hook cards, chapter cards, stat
  cards, lower thirds, and HTML/CSS/GSAP typography layouts that need approval
  frames and deterministic browser rendering.
- FFmpeg `drawtext` is preferred for simple timed overlays, labels, fades, basic
  font-size pops, and generated proof-of-concept captions, but not for final
  professional title systems when HyperFrames or Remotion fits.
- FFmpeg alpha workflows should be explicit: inspect or reuse existing alpha with
  `alphaextract`, attach grayscale masks with `alphamerge`, blend opaque sources
  with `maskedmerge`, and composite confirmed-alpha foregrounds with `overlay`.
- Do not force dense kinetic typography into a fragile FFmpeg filter graph. Use
  ASS, HyperFrames, Remotion, or pre-rendered transparent overlays when the graph
  gets long.
- All generated text renders should be reproducible: known fonts, logged filter
  graphs, deterministic random seeds, and explicit frame/timing metadata.
- Pillow/PIL is not a final typography engine. Use it only for diagnostics,
  masks, contact sheets, rough placeholders, or non-typographic helper assets.
- New or materially changed title/hook/lower-third graphics require approval
  frames/contact sheets and user approval before final compositing.

## Techniques

- `technique_cards/typography_programmatic_text_mask_highlight_glow_001.json`
- `technique_cards/typography_remotion_sequence_local_kinetic_presets_001.json`
- `technique_cards/typography_remotion_seeded_scramble_glitch_001.json`
- `technique_cards/typography_remotion_stagger_spring_text_motion_001.json`
- `technique_cards/typography_remotion_blur_scale_morph_001.json`
- `technique_cards/typography_ffmpeg_drawtext_timed_overlay_001.json`
- `technique_cards/typography_ffmpeg_fade_pop_envelope_001.json`
- `technique_cards/typography_ffmpeg_sequential_word_drawtext_001.json`
- `technique_cards/programmatic_remotion_prores4444_alpha_overlay_export_001.json`
- `technique_cards/programmatic_remotion_webm_alpha_overlay_export_001.json`
- `technique_cards/programmatic_remotion_offthreadvideo_alpha_import_001.json`
- `technique_cards/programmatic_remotion_css_mask_text_reveal_001.json`
- `technique_cards/programmatic_ffmpeg_alphamerge_alpha_mask_pipeline_001.json`
- `technique_cards/programmatic_ffmpeg_alphaextract_mask_reuse_001.json`
- `technique_cards/programmatic_ffmpeg_geq_procedural_alpha_masks_001.json`
- `technique_cards/programmatic_ffmpeg_in_place_wipe_reveal_alpha_001.json`
- `technique_cards/typography_capcut_color_change_highlight_wipe_001.json`
- `technique_cards/typography_capcut_film_strip_glow_reveal_001.json`
- `technique_cards/typography_capcut_staggered_blur_glitch_reveal_001.json`
- `technique_cards/typography_capcut_split_mask_gradient_type_001.json`

## Timing Rules

- Remotion text components should calculate motion from Sequence-local frames so
  they can be placed anywhere in the edit.
- Use exact progress/interpolation for mask wipes, highlight reveals, fades, and
  other effects that must land on a timed frame.
- Use springs for word lift, elastic pop, bounce, and other physical entrances.
- FFmpeg `enable` windows should come from transcript, beat, or scene timing
  rather than rough guesses.
- Text entrances should settle before the viewer needs to read the phrase.
- Word-level caption windows should match transcript timing or switch to
  phrase-level chunks when one-word timing harms comprehension.
- Mask and glow effects should start and end off-word with a readable hold after
  the reveal.
- Short-form alpha text wipes can start around 6-15 frames at 30 fps; calmer
  title or lower-third reveals can use about 12-24 frames when readability holds.
- Transparent overlay renders must match the final edit window's fps, duration,
  and frame count or the alpha pass will drift.

## Motion Rules

- Animate transform, opacity, clip masks, and text-layer effects rather than
  layout properties when possible.
- Use character-level effects only on short words; use word, phrase, or line
  animation for longer text.
- Keep glitch, scramble, wave, and morph effects short and resolved to stable
  readable text before the next claim.
- Use deterministic seeded randomness for Remotion scramble, RGB glitch, jitter,
  or particle-like typography.
- For FFmpeg pop effects, re-center using rendered text dimensions while font
  size changes.
- For programmatic highlight/glow, reveal the sharp styled layer and glow layer
  with the same timing so glow does not leak before or after the sweep.
- Use CSS masks or SVG masks in Remotion for soft opacity gradients; use
  `clip-path` only when a hard-edged reveal is intentional.
- In FFmpeg, generate and preview grayscale masks before `alphamerge`; white
  reveals, black hides, and gray creates partial transparency.
- Use in-place wipe masks when a foreground should reveal without sliding; the
  mask moves while the foreground position remains fixed.

## Sound Rules

- Most programmatic typography does not need SFX.
- If text has a real beat job, a pop, tick, glitch, or shimmer may land on the
  visible entrance, reveal, or resolve frame.
- Text SFX should stay below speech and end with the visual motion.
- Do not use SFX to make weak hierarchy or late timing feel energetic.

## Caption Rules

- Correct transcript wording, timing, line breaks, and phrase grouping before
  adding programmatic caption motion.
- Use ASS subtitles from the repo caption preset system for final captioned
  renders.
- Use Remotion for reusable animated caption groups and FFmpeg for short tests or
  simple timed overlays.
- Use ASS, HyperFrames, or Remotion instead of long `drawtext` chains when
  subtitle layout, accessibility, title cards, or many words matter.
- Keep ordinary captions visible or repositioned when designed text carries the
  same spoken phrase. Suppression requires explicit user approval.
- Never use scramble, glitch, morph, or glow as the only accessibility layer for
  important speech.

## Color Rules

- Highlight, glow, gradient, RGB split, and shadow treatments must preserve crisp
  letter edges at delivery size.
- Compare stylized text against a plain high-contrast fallback before approving
  a programmatic effect.
- Use accent color only where it marks priority, meaning, brand, comparison, or
  a deliberate digital/glitch tone.
- Test bright, dark, and busy representative frames before saving a typography
  component as reusable.
- Check alpha edges over both light and dark backgrounds because glow, blur, and
  antialiasing can reveal black/white fringe or premultiply issues.
- Use luminance masks only when brightness should drive visibility; use alpha
  masks when opacity should drive visibility.

## Tool Implementation Notes

- HyperFrames: store title/card projects in the animation slot, render approval
  contact sheets, run lint/validate/render checks when practical, then export the
  approved final overlay.
- Remotion: store text components with `text`, `phraseLines`, `impactWords`,
  `startFrame`, `durationInFrames`, `safeRegion`, `fontRole`, `motionMode`,
  `captionContinuityPolicy`, any user-approved suppression exception, and
  `qcStatus`.
- Remotion masks: duplicate text inside an absolute container and animate
  `clip-path` or a mask position from off-word to off-word.
- Remotion alpha export: for editor handoff, render PNG frames into ProRes 4444
  with `yuva444p10le`; for web alpha, use VP8/VP9 with `yuva420p` only after
  documenting browser support and fallback needs.
- Remotion alpha import: use `<OffthreadVideo transparent />` only for source
  videos that really contain alpha, and trim those sources to their visible range.
- Remotion CSS masks: store `maskMode`, `maskSource`, `maskPosition`,
  `maskSize`, reveal frames, and duplicate-layer alignment status.
- Remotion glitch: use seeded random values tied to frame/index; avoid direct
  random values in render logic.
- FFmpeg: use explicit `fontfile`, `enable` windows, `alpha` envelopes, and
  `fontsize` expressions for simple text motion.
- FFmpeg masks/glow: use pre-rendered text/glow overlays or animated alpha masks
  rather than expecting raw `drawtext` to handle premium mask sweeps alone.
- FFmpeg alpha graph: use `alphaextract` for existing alpha, `alphamerge` for
  attaching grayscale masks, `maskedmerge` for direct masked blends, `overlay`
  for confirmed-alpha foregrounds, and `geq` for procedural mask generation.
- FFmpeg alpha export: use ProRes 4444 or PNG sequences for editor/compositor
  handoff; use opaque final formats only after the overlay is composited.
- ASS: keep the final caption layer in ASS and apply it after all overlays.
- Pillow/PIL: do not use for final title or caption typography.
- CapCut: duplicate and compound only the layer that needs masking/effects, then
  verify duplicate alignment and mask start/end states.
- Premiere: use Essential Graphics duplicates, nests, Transform scale, Linear
  Wipe, masks, or track mattes; move complex repeatable motion to Remotion or AE.

## Common Mistakes

- Copying a CapCut effect visually while skipping the base text readability pass.
- Hard-coding Remotion component timing to global frames instead of local frames.
- Using non-deterministic random values in Remotion glitch or scramble text.
- Building giant FFmpeg `drawtext` chains that cannot be debugged or regenerated.
- Rendering final title cards, hook cards, lower thirds, or captions with
  Pillow/PIL.
- Compositing title graphics before user approval of still frames/contact sheets.
- Suppressing captions under designed text without explicit user approval.
- Relying on system font lookup in FFmpeg when a render agent may not have the
  same fonts installed.
- Letting glow appear before the sweep reaches the word or remain after it exits.
- Using font-size animation on text that rewraps, drifts, crops, or collides.
- Applying character-level effects to long captions that need phrase readability.
- Exporting a reusable transparent overlay as MP4 and losing alpha.
- Expecting FFmpeg `overlay` alone to create a masked reveal.
- Reusing procedural masks before previewing polarity, softness, and aspect-ratio
  behavior.
- Enabling transparent video extraction in Remotion for opaque footage and
  slowing renders unnecessarily.
- Accepting black rectangles or dark text halos before checking codec, pixel
  format, premultiply behavior, and alpha preservation.

## QC Checklist

- Remotion component starts correctly when placed at different Sequence positions.
- HyperFrames title/card overlays have approval frames/contact sheets and the
  user's approval before final compositing.
- ASS is used for final captions.
- No final title/caption typography uses Pillow/PIL.
- Seeded glitch/scramble renders the same frame consistently across repeated exports.
- FFmpeg filter graph is logged or generated from structured data.
- Fontfile resolves and the rendered font matches the intended style.
- Base and duplicate text layers align exactly through the mask/glow pass.
- Mask/glow starts and ends off-word with no sliver, pre-glow, tail glow, or
  lingering blur.
- Transparent overlay exports have verified alpha, no painted background, and no
  black rectangle in empty areas.
- FFmpeg foreground and mask streams match width, height, fps, duration, and
  timing before `alphamerge`.
- Generated grayscale masks are previewed before final compositing.
- Alpha overlays are checked over bright and dark backgrounds for fringe, halo,
  and premultiply artifacts.
- Text remains readable at phone size through smallest, largest, blurred,
  glitched, highlighted, and final hold states.
- Captions, faces, products, proof, UI, maps, and action stay clear.
- Any SFX lands on the final visible motion and stays below speech.

## Source Lessons Added

- 2026-06-01: `Remotion Lab Kinetic Typography Presets`
- 2026-06-01: `FFmpeg Drawtext Animations`
- 2026-06-01: `Remotion Transparent Videos`
- 2026-06-01: `Remotion Creating Overlays`
- 2026-06-01: `Remotion OffthreadVideo Transparent`
- 2026-06-01: `Curio Museum FFmpeg Alpha Masking`
- 2026-06-01: `hhsprings FFmpeg Alphamerge Alphaextract`
- 2026-06-01: `hhsprings FFmpeg Alphamerge Alphaextract More`
- 2026-06-01: `FFmpeg Filters Alpha Masking Official`
- 2026-06-01: `FFmpeg Wipe Reveal With Alpha Mask`
- 2026-06-01: `MDN CSS Masking Introduction`

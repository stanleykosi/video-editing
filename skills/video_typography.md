# Video Typography

## Purpose

Guide font selection, hierarchy, line breaks, spacing, live-action text placement,
and readability for video titles, captions, hooks, ads, explainers, and cinematic
text.

## When To Use This Skill

- Choosing fonts or type families for a video edit.
- Designing hook text, title cards, B-roll text, lower thirds, or graphic labels.
- Turning captions into more intentional typography without losing readability.
- Integrating text into live-action footage, cinematic shots, or negative space.
- Creating text-behind-subject composites, chroma-key video-in-text portals, and
  full-screen chapter cards when typography is part of a CapCut effect.
- Matching a client reference or industry style while keeping the text useful.
- Reviewing whether typography supports story, brand, retention, and accessibility.
- Designing title graphics that require HyperFrames/Remotion approval frames before
  final compositing.
- Choosing documentary-style title and label fonts for archival, editorial,
  research, or parallax collage scenes.
- Building CapCut social text effects such as adaptive caption texture, Player 3
  smooth caption compounds, smooth slide-up text, axis stretch, flicker, number
  counters, perspective freeze words, color-change highlight wipes, staggered
  blur reveals, gradient type, foreground-lift reveals, outline reveals,
  film-strip glow reveals, and video-in-text.
- Reproducing those text masks, highlights, glow sweeps, glitch effects, and
  pop captions programmatically with Remotion or FFmpeg.

## Core Principles

- Typography is part of storytelling, communication, branding, and attention.
- Start with the message, then choose the type style.
- Font family should match the project's role: serif for editorial/history gravity,
  sans serif for clean modern clarity, script for handwritten expression, and
  display for bold headline energy.
- Use expressive fonts as accents; use readable fonts for continuous captions and
  information-heavy screens.
- Build contrast through weight, color, case, and size, then combine only what the
  line needs.
- Highlight the word that changes the impact of the line, not filler words.
- One text moment should have one primary hierarchy.
- Line breaks should follow phrase logic, like short readable thoughts, not random
  auto-wrapped words.
- Microspacing can make type feel premium only after readability is already solved.
- Live-action typography should use negative space, matching color temperature, and
  theme-appropriate font choices so it feels integrated.
- For performance ads, clean readable text usually beats fancy typography.
- Video-in-text reveals need short, bold words; text behind people needs clean
  foreground separation and enough visible letter area to read.
- Trendy text effects are useful only when they have a role: readability,
  emphasis, proof, depth, scene integration, or beat-synced accent.
- Compound text templates should preserve editable source words while letting the
  agent duplicate, reposition, freeze, or animate the wrapper.
- Premium-looking text effects usually come from controlled layer construction:
  duplicate text, compound clips, masks, clean contrast, and one readable path.
- Programmatic premium text effects should follow the same layer logic: base
  text, duplicate styled text, animated mask or matte, optional glow/blur pass,
  and delivery-size readability checks.
- When text effects are handed between tools, true alpha is part of typography
  quality: soft glow, blur, antialiasing, and masked edges must survive without
  black boxes, chroma-key fringes, or muddy halos.
- Documentary typography can use editorial serif, typewriter/display, clean sans,
  or condensed headline roles, but each font must have a readable job rather than
  copying a publisher reference.

## Professional Render Rules

- Use `skills/professional_title_graphics_pipeline.md` for title cards, hook
  cards, chapter cards, stat cards, lower thirds, and major motion typography.
- Final continuous captions must be ASS captions from the repo caption style
  system.
- ASS hard line breaks must be written as a single `\N` control sequence in the
  final `.ass` file. Do not double-escape line breaks into `\\N` or ship any
  burned caption that shows visible slash/backslash artifacts.
- HyperFrames is the default engine for title cards, hook cards, chapter cards,
  stat cards, lower thirds, HTML/CSS typography systems, and transparent overlay
  cards.
- Remotion is the default engine for polished animated typography, reusable
  components, data-driven graphics, and frame-precise social motion.
- Do not use Pillow/PIL for final title, caption, lower-third, hook-card, or
  chapter-card typography. Use it only for diagnostics, masks, contact sheets,
  placeholders, or non-typographic helper assets.
- New or materially changed title designs need approval frames/contact sheets and
  user approval before final compositing.
- Captions should continue through title overlays by default. Reposition or
  restyle captions before considering suppression, and suppress only with explicit
  user approval.

## Techniques

- `technique_cards/typography_font_family_role_selection_001.json`
- `technique_cards/typography_contrast_hierarchy_stack_001.json`
- `technique_cards/typography_sentence_structure_line_breaks_001.json`
- `technique_cards/typography_live_action_whitespace_integration_001.json`
- `technique_cards/typography_tracking_kerning_line_spacing_qc_001.json`
- `technique_cards/typography_roi_readability_ad_text_001.json`
- `technique_cards/retention_hook_text_design_sequence_001.json`
- `technique_cards/captions_two_word_social_subtitles_001.json`
- `technique_cards/captions_premiere_one_word_pop_fade_001.json`
- `technique_cards/motion_overlay_readability_focus_stack_001.json`
- `technique_cards/motion_broll_text_readability_sequence_001.json`
- `technique_cards/motion_typographic_explainer_intro_collage_001.json`
- `technique_cards/davinci_textplus_premium_caption_stack_001.json`
- `technique_cards/captions_capcut_adaptive_texture_animation_001.json`
- `technique_cards/captions_capcut_player3_smooth_caption_compounds_001.json`
- `technique_cards/typography_capcut_apple_slide_up_text_001.json`
- `technique_cards/typography_capcut_axis_stretch_emphasis_001.json`
- `technique_cards/typography_capcut_opacity_flicker_tick_001.json`
- `technique_cards/typography_capcut_srt_number_countup_001.json`
- `technique_cards/typography_capcut_perspective_freeze_text_001.json`
- `technique_cards/typography_capcut_color_change_highlight_wipe_001.json`
- `technique_cards/typography_capcut_staggered_blur_glitch_reveal_001.json`
- `technique_cards/typography_capcut_split_mask_gradient_type_001.json`
- `technique_cards/typography_capcut_font_shift_loop_001.json`
- `technique_cards/typography_capcut_outline_reveal_chroma_001.json`
- `technique_cards/typography_capcut_film_strip_glow_reveal_001.json`
- `technique_cards/compositing_capcut_subject_sandwich_cutout_001.json`
- `technique_cards/typography_capcut_chroma_video_text_portal_001.json`
- `technique_cards/motion_capcut_chapter_card_slide_interrupt_001.json`
- `technique_cards/typography_programmatic_text_mask_highlight_glow_001.json`
- `technique_cards/typography_remotion_sequence_local_kinetic_presets_001.json`
- `technique_cards/typography_remotion_seeded_scramble_glitch_001.json`
- `technique_cards/typography_remotion_stagger_spring_text_motion_001.json`
- `technique_cards/typography_remotion_blur_scale_morph_001.json`
- `technique_cards/typography_ffmpeg_drawtext_timed_overlay_001.json`
- `technique_cards/typography_ffmpeg_fade_pop_envelope_001.json`
- `technique_cards/typography_ffmpeg_sequential_word_drawtext_001.json`
- `technique_cards/programmatic_remotion_css_mask_text_reveal_001.json`
- `technique_cards/programmatic_remotion_prores4444_alpha_overlay_export_001.json`
- `technique_cards/programmatic_ffmpeg_alphamerge_alpha_mask_pipeline_001.json`
- `technique_cards/programmatic_ffmpeg_in_place_wipe_reveal_alpha_001.json`

## Timing Rules

- The viewer should understand the main text priority before the shot changes.
- Hook typography should establish its key word or phrase inside the first five
  seconds of a feed-first short.
- Caption line breaks and emphasis must be corrected before text is animated.
- Display, script, gradient, or composite-mode text needs extra read time because
  it is harder to parse than plain sans text.
- Text animation should settle before the phrase needs to be read.
- Live-action scene text should hold long enough for the viewer to read it without
  leaving the emotional shot too late.
- Chroma-key video-in-text should zoom through a letter only after the word has
  been read.
- Chapter cards should hold briefly for the section label, then clear before the
  next body line or caption appears.
- Documentary title animations can start around 1.5-2 seconds when the scene is
  calmer; cinematic open-style text can start around 1.3 seconds, then tune by
  word length and narration pace.
- Apple-style CapCut slide-up text can start around 22 frames from hidden to
  landed text, then be shortened or widened based on phrase length.
- Fast flicker text can use one-frame opacity changes, but the final frame should
  return to full readability.
- Number counters should slow or hold on the final value so the result registers.
- Font-shift loops and perspective-freeze text must resolve before the next
  reading task begins.
- Highlight wipes should let the phrase establish, then finish before the next
  caption, proof, or CTA competes.
- Staggered blur/glitch reveals should resolve to stable text quickly; the glitch
  cue should not outlast the final word reveal.
- Film-strip glow sweeps should start off the word, cross once, and exit off the
  word before the next reading task.
- Remotion typography components should use Sequence-local frame timing so the
  same effect can be placed at any timeline position.
- FFmpeg `drawtext` overlays should use explicit enable windows, and word-level
  chains should switch to ASS or Remotion when they become hard to debug.
- Alpha-mask text reveals should complete before the viewer needs to read the full
  word; fast short-form wipes can be 6-15 frames at 30 fps and calmer title/lower
  third wipes can use about 12-24 frames.

## Motion Rules

- Animate hierarchy, not every word.
- Use short pop, slide, wipe, or fade moves only when they reinforce the text's job.
- Scene-attached text should be tracked or positioned so it respects the shot's
  perspective, negative space, and subject movement.
- Do not combine heavy tracking, zoom, caption pop, glow, and busy background motion
  unless the style intentionally demands chaos.
- Text must not cover the subject, product, proof, map, chart, face, or object that
  gives the line meaning.
- For text-behind-subject effects, place the text in the prepared base and use a
  foreground cutout only after text timing and placement are stable.
- In parallax collages, text can sit behind or between cutouts only while the
  covered letters remain readable.
- Axis stretch should affect one impact word and one axis at a time unless a
  deliberate distortion still reads.
- Perspective freeze text should fit scene geometry or negative space, not just
  show off an angle.
- Outline reveal and text-behind-object effects need foreground cutout edge QC
  through motion, not only on a paused frame.
- Foreground-lift text should move from behind a clean masked foreground edge and
  remain readable after it clears the object.
- Split-mask and film-strip text effects must keep mask boundaries, feather, and
  glow secondary to the word shape.
- Programmatic highlight, gradient, and glow effects should align duplicate text
  layers exactly and reveal sharp text plus glow with the same mask timing.
- Character-level scramble, glitch, wave, or morph effects should be reserved for
  short words and should resolve to a stable readable state.
- Use CSS masks or SVG masks for soft Remotion text reveals; use `clip-path` only
  when a hard reveal edge is the intended design.
- FFmpeg text reveal masks should be previewed as grayscale before final
  compositing so polarity, softness, and edge position are not guessed.

## Sound Rules

- Typography usually does not need sound unless text enters as a real beat.
- Hits, ticks, typewriter cues, or whooshes should land on meaningful text entrances
  and stay below dialogue.
- Ticking SFX for flicker or font-shift text should end with the visual change.
- Glitch or shimmer cues for staggered reveals and glow sweeps should be trimmed
  to the exact visual span and kept below speech.
- Do not use SFX to make weak typography feel energetic; fix hierarchy and timing
  first.
- A video-in-text zoom can use a soft whoosh only when it supports the portal move
  and does not mask speech.
- Documentary title SFX should be restrained and should land only on meaningful
  title entrances, not every text layer.

## Caption Rules

- Continuous captions should prioritize readability over expressive font choices.
- Use one- or two-word chunks only when they improve pace and remain understandable.
- Keep captions visible through title/card overlays by default, repositioning or
  restyling them when the frame is dense.
- Captions, title text, lower thirds, and proof labels should be planned as one
  layout system.
- Sentence case, mixed case, all caps, and size changes should be chosen by meaning,
  not by habit.
- Suppress ordinary captions during video-in-text portals or chapter cards only
  when the user approved the suppression and the designed text carries the spoken
  phrase clearly.
- Reposition ordinary captions during adaptive caption texture,
  Player 3 smooth captions, flicker, font shift, outline reveal, number counters,
  highlight wipes, glow reveals, or perspective text when designed text owns the
  same screen region.
- During dense documentary title/cutout scenes, keep captions readable by moving,
  shrinking, or restyling them. Suppress only after explicit approval.

## Color Rules

- Text color must remain readable over the actual background, not just the design
  canvas.
- Limit accent colors; use neutrals for support text unless comparison logic needs
  positive/negative color.
- Match live-action text temperature to the frame unless contrast is the point.
- Gradients and blend/composite modes can feel premium only when they preserve
  edge contrast.
- Drop shadow is acceptable as a functional readability aid; avoid heavy default
  shadows when contrast already works.
- Chroma-key text mattes must leave no colored fringe or edge specks over the
  destination footage.
- Blend modes such as Overlay, Linear Burn, and Screen must preserve letter-edge
  contrast and the footage inside video-in-text.
- Highlight bars, split-mask gradients, and glow sweeps are approved only when
  both the styled and plain text states remain crisp at delivery size.
- Transparent text overlays must be checked over bright and dark backgrounds
  because antialiasing, glow, and mask feathers can reveal alpha-edge problems
  that are invisible on one background.

## Tool Implementation Notes

- HyperFrames: use for final title cards, hook cards, chapter cards, stat cards,
  lower thirds, transparent HTML/CSS overlays, and approval-frame contact sheets.
- Remotion: use for final polished motion typography, reusable components,
  animated data/text systems, and frame-precise social graphics.
- ASS captions: use the repo caption style presets for final captioned renders;
  do not replace the caption layer with graphic text unless explicitly approved.
- Pillow/PIL: do not use for final title or caption typography. Limit it to
  diagnostics, masks, contact sheets, placeholders, or non-typographic helper
  assets.
- ffmpeg: use `drawtext` with explicit fontfile, size, line spacing, color,
  shadow, box, alpha/fontsize expressions, and enable timing; review
  delivery-size contact sheets and log generated filter graphs.
- Remotion: store type as structured tokens for family role, hierarchy level, line
  breaks, impact words, tracking, line height, case, color, safe region, Sequence
  timing, motion mode, caption continuity policy, and any user-approved caption
  suppression exception.
- Programmatic typography: use `skills/programmatic_typography_implementation.md`
  when converting CapCut text masks, highlights, glow sweeps, seeded glitch,
  pop/stagger captions, or drawtext overlays into reusable code.
- Programmatic alpha typography: export reusable Remotion overlays as ProRes 4444
  or PNG sequences for editor handoff, use CSS masks for soft text reveals, and
  use FFmpeg `alphamerge` when attaching a grayscale reveal mask to rendered text.
- Blender: use text objects and camera tracking for cinematic scene-attached text.
- CapCut: use templates as editable drafts; manually check family, line breaks,
  tracking, placement, and readability.
- CapCut social text effects: correct captions first, use Character spacing
  lightly, compound reusable text templates, duplicate compounds only after the
  source text remains editable, and review every blend/key/cutout at phone size.
- CapCut premium text masks: for highlight wipes, gradient type, and glow reveals,
  duplicate the text precisely, compound only the layer that needs masking, and
  keep mask starts/ends outside the readable word.
- CapCut documentary titles: test editorial serif, typewriter/display, clean sans,
  or condensed headline roles, set animation duration around 1.5-2 seconds as a
  starting point, and check that text settles before it must be read.
- CapCut video-in-text: create a colored bold text matte on black, export it,
  overlay on destination footage, key the text color, tune intensity, and animate
  a zoom through a readable letter.
- CapCut animated video-in-text: compound black background plus editable text,
  place the fill video with a tested blend mode, compound again, set the wrapper
  to Screen, and reopen the internal text layer for text animations.
- Premiere: use Essential Graphics, Track Styles, rulers/guides, and caption-to-
  graphic conversion only after wording and timing are corrected.
- After Effects: save text animation presets by behavior and test them on long,
  short, bright-background, and dark-background phrases before reuse.

## Common Mistakes

- Selecting fonts because they look fancy instead of because they fit the story.
- Using script or display fonts for dense captions.
- Emphasizing filler words instead of the word that carries impact.
- Mixing too many font families in one short.
- Breaking lines randomly and making viewers reassemble the sentence.
- Tightening tracking until letters collide or small captions shimmer.
- Placing text over the exact visual detail the viewer needs to inspect.
- Over-styling ad text until the product promise or CTA is slower to understand.
- Using long phrases or thin fonts for video-in-text, leaving too little footage
  visible inside the letters.
- Applying viral text effects to every line until no word has priority.
- Using flicker, font shift, or axis stretch on continuous accessibility captions.
- Using Player 3, highlight wipes, gradient text, glow sweeps, or staggered blur
  reveals before the base text, line breaks, and contrast are already strong.
- Trusting a CapCut blend mode, chroma key, or cutout without playback QC.
- Generating number counters without checking the final value, unit, or hold.
- Leaving duplicate captions under a full-screen chapter card or portal title.
- Using documentary font examples as fixed rules instead of matching the current
  project tone and source context.
- Letting parallax cutouts cover title letters until the word can no longer be read.
- Using non-deterministic random values in Remotion glitch/scramble text.
- Building a long FFmpeg word-by-word `drawtext` chain when Remotion, ASS, or a
  pre-rendered overlay would be safer.
- Rendering final title cards, captions, lower thirds, or hook cards with
  Pillow/PIL.
- Double-escaping ASS caption line breaks so `\\N` or slash/backslash artifacts
  appear in the rendered video.
- Adding title graphics to a final render before the user approves approval
  frames/contact sheets.
- Suppressing captions under title cards by default instead of repositioning or
  restyling them.
- Trusting system font lookup in FFmpeg when a reproducible agent render needs an
  explicit fontfile.
- Exporting masked or glowing text as an opaque file and then trying to remove
  black with chroma key.
- Using the wrong mask mode so luminance/alpha behavior reverses the intended
  text reveal.

## QC Checklist

- Typography has one clear primary focus per text moment.
- Final title cards, hook cards, chapter cards, stat cards, and lower thirds were
  rendered with HyperFrames or Remotion.
- New title/motion graphics have user-approved approval frames/contact sheets.
- Final captions are ASS captions from the repo caption style system.
- ASS Dialogue text has no double-escaped line-break markers; hard breaks are
  single `\N`, and rendered captions show no slash/backslash artifacts.
- No final title/caption typography was rendered with Pillow/PIL.
- Font family matches the video tone, industry, and reference.
- Text is readable at phone size and final delivery resolution.
- Line breaks form readable phrases.
- Tracking, kerning, and line spacing do not create collisions or awkward gaps.
- Captions, title text, lower thirds, and proof labels do not collide.
- Captions continue through title overlays or have a documented user-approved
  suppression exception.
- Text does not cover faces, products, UI, maps, charts, documents, or emotional
  reactions.
- Accent color, gradient, blend mode, or shadow improves readability or hierarchy.
- For ads, the product/result/CTA is readable faster than the style is noticeable.
- Video-in-text mattes key cleanly without colored fringe, and the zoom lands on a
  readable part of the destination footage.
- Text-behind-subject effects remain readable after the foreground cutout passes.
- Flicker and font-shift accents resolve to a readable final word.
- Number counters show a verified final value and hold long enough to read.
- Perspective and outline effects preserve one clear reading order.
- Highlight wipes, gradient text, and glow sweeps preserve crisp letter edges
  before, during, and after the effect.
- Foreground-lift text uses a clean cutout edge and does not hide the word behind
  the foreground for too long.
- Documentary title animations settle before the viewer needs the word, source
  label, or claim.
- Remotion text effects render consistently with Sequence-local timing and
  deterministic seeds.
- FFmpeg text overlays use available fonts, logged filter graphs, and readable
  enable windows.
- Programmatic mask/glow text has no duplicate-layer drift, pre-glow, tail glow,
  or leftover mask sliver.
- Transparent text overlays have verified alpha and no black rectangle behind
  empty areas.
- Masked text is tested over both bright and dark representative frames.

## Source Lessons Added

- 2026-05-29: `Typography`
- 2026-05-29: `Make Pro Media`
- 2026-05-29: `Documentary Edits`
- 2026-05-29: `Viral Text Effects`
- 2026-06-01: `Premium CapCut Text Effect`
- 2026-06-01: `Remotion Lab Kinetic Typography Presets`
- 2026-06-01: `FFmpeg Drawtext Animations`
- 2026-06-01: `Programmatic Alpha Masking And Transparent Overlay Source Pack`

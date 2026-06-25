# Lesson: CapCut Documentary Editing Effects

## Source

- Tutorial: `Documentary Edits`
- Notes: `transcripts/documentary edits.txt`
- Date processed: 2026-05-29
- Related cards:
  - `technique_cards/motion_capcut_switch_focus_depth_blur_001.json`
  - `technique_cards/motion_documentary_research_overlay_timelapse_001.json`
  - `technique_cards/color_archival_film_frame_treatment_001.json`
  - `technique_cards/motion_capcut_documentary_parallax_collage_001.json`
  - `technique_cards/motion_screen_blend_texture_overlay_001.json`
  - `technique_cards/typography_font_family_role_selection_001.json`
  - `technique_cards/motion_capcut_graph_curve_easing_001.json`
  - `technique_cards/motion_capcut_pendulum_transition_movement_001.json`
  - `technique_cards/nle_capcut_compound_graphics_workflow_001.json`
  - `technique_cards/sound_infographic_motion_sfx_sync_001.json`

## What The Tutorial Teaches

This tutorial turns CapCut into a documentary graphics tool: layered cutouts,
compound clips, eased scale/position moves, cross-rack blur, texture overlays,
archival film framing, restrained typography, and subtle ambient motion are used
to make still images, screen recordings, documents, and historical material feel
designed rather than flat.

The reusable lesson is not to copy Johnny Harris, Vox, or any publisher identity.
The agent should extract the grammar: evidence-led motion, a single focal point,
depth through foreground/background separation, documentary type choices,
source-safe assets, and texture that supports credibility without hurting
readability.

## Agent Decision Rules

- Use switch-focus depth blur when two visual ideas need contrast, comparison, or
  a handoff in attention.
- Use on-screen research overlays when the story needs to show investigation,
  process, or discovery without turning the section into raw screen recording.
- Use archival film framing only when the footage/photo is meant to read as old,
  historical, found, or memory-like; avoid it on current proof that needs neutral
  trust.
- Use glass or filmed-screen texture when a screen recording should feel captured
  by a camera, but reduce opacity if it hides UI, source text, or captions.
- Use multi-layer parallax collage when cutout images and text need depth, not
  when a simple map, document, or chart would explain the claim faster.
- Treat AI-generated or downloaded documentary images, textures, fonts, SFX, and
  music as rights-managed assets before a publishable export.

## Timeline Patterns

- Switch focus:
  `background -> cutout_a -> cutout_b -> compound_cutouts -> transform_keyframes -> cross_blur_a_b -> background_countermove -> subtle_fps_lag_pendulum -> qc`
- Research overlay:
  `process_recording -> document_or_screen_overlays -> blend_mode -> optional_speedup -> riser -> proof_context_hold`
- Archival treatment:
  `current_or_source_clip -> film_frame -> desaturate -> contrast -> particles/fade -> text/caption_readability_qc`
- Filmed screen:
  `screen_recording -> glass_texture_overlay -> color_burn_or_blend -> opacity_reduce -> ui_readability_qc`
- Parallax collage:
  `background_mist_rain -> cutout_sequence -> fade_overlaps -> compound_images -> eased_scale_xy -> background_subtle_countermove -> text_behind_cutouts -> global_grade_texture`

## Implementation Notes

- ffmpeg: model cutouts, blur ramps, glass textures, film frames, fades, and
  color/noise passes as explicit timed layers; render contact sheets for focus
  handoffs and UI/source-text readability.
- Remotion: create components for SwitchFocusDepthBlur, ResearchOverlayTimelapse,
  ArchivalFilmFrameTreatment, FilmedScreenTexture, and DocumentaryParallaxCollage
  with source/license metadata.
- CapCut: use Remove Background, rectangle masks with feather, Enhance Quality
  only when needed, compound clips, transform keyframes, Graphs/Ease or Cubic
  Ease, blur keyframes, blend modes, animation duration around 1.5-2 seconds for
  documentary text, film frame effects, particles/fade, FPS Lag, and low-strength
  Play Pendulum.
- Premiere/After Effects: use nests/precomps, opacity masks, Gaussian Blur,
  adjustment layers, Posterize Time, text styles, Lumetri/noise/film overlays,
  blend modes, and eased Motion or Graph Editor curves.

## Mistakes And QC

- Do not let texture, glass overlays, film frames, or FPS lag hide evidence.
- Do not use documentary fonts or overlays without assigning roles: title,
  source, label, quote, or emphasis.
- Do not let cross-blur make both subjects unfocused at the same time.
- Do not paste identical motion onto foreground and background layers; parallax
  needs a subtler background move.
- Do not use AI-generated or downloaded images as documentary evidence unless
  they are clearly illustrative, licensed, attributed, and ethically labeled.
- Check every effect at delivery size with captions, source text, asset rights,
  and SFX/music levels restored.

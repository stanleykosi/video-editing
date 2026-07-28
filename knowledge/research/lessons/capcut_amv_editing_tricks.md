# Lesson: CapCut AMV Editing Tricks

## Source

- Tutorial: `Editing Tricks`
- Notes: `knowledge/research/transcripts/editing tricks.txt`
- Date processed: 2026-05-29
- Related cards:
  - `knowledge/techniques/beat_sync/beat_sync_capcut_speed_match_twixtor_001.json`
  - `knowledge/techniques/motion/motion_capcut_character_mask_shadow_glow_001.json`
  - `knowledge/techniques/nle_workflow/nle_capcut_heavy_overlay_prerender_workflow_001.json`
  - `knowledge/techniques/transition/transition_capcut_turbulent_wide_angle_shake_001.json`
  - `knowledge/techniques/sound_design/sound_anime_edit_sfx_voice_line_spotting_001.json`
  - `knowledge/techniques/motion/motion_capcut_effect_tail_extension_001.json`

## What The Tutorial Teaches

This tutorial turns a dense CapCut AMV workflow into repeatable agent knowledge:
sync action clips to music by adjusting speed, design character-focused effects
with duplicate layers and masks, keep heavy overlay edits responsive by working
clip-by-clip, build transitions as their own pass, and finish with frame-placed
SFX and voice lines.

The strongest lesson is workflow order. Lock clip timing to the beat first, then
design each clip, then replace heavy edited clips into the main timeline, then
add transition effects and transition-specific shakes, and only then spot SFX.

## Agent Decision Rules

- Use speed matching when an action peak, transformation, impact, or pose needs
  to land on a song beat.
- Use character-isolated masks when the effect should touch only the subject,
  eyes, hair, weapon, or body edge rather than the whole frame.
- Use the heavy-overlay pre-render workflow when CapCut playback lag prevents
  clean timing review.
- Add transition shakes after turbulent, wide-angle, or zoom transition effects
  are visible, because shake strength depends on the final transition flow.
- Add voice lines only when they anchor identity, emotion, or impact; do not use
  them as filler over every clip.
- Use black matte or duplicated effect layers only when an effect fades before
  the intended visual beat is finished.

## Timeline Patterns

- Beat speed match:
  `music_track -> beat_markers -> action_clip -> speed_adjust -> preview_on_beat -> repeat_sequence`
- Character mask design:
  `base_clip -> duplicate_or_cutout -> mask_subject_or_body_part -> glow_or_shadow -> flicker_graph -> edge_review`
- Lag-safe clip design:
  `main_timeline_placeholder -> clip_subproject -> overlays/effects -> pre-render_or_export -> replace_placeholder`
- Transition pass:
  `split_locked_clips -> turbulent_effect -> wide_angle_zoom -> transition_shake -> SFX_hit -> preview`
- AMV sound spotting:
  `locked_visual_hit -> licensed_sfx_import -> whoosh/hit/elemental_cue -> identity_voice_line -> full_mix_review`
- Effect-tail extension:
  `short_effect_tail -> black_matte_or_backing -> duplicate_effect_layers -> fast_background_slices -> color_match -> tail_qc`

## Implementation Notes

- ffmpeg: represent speed changes with `setpts` or timeline metadata, isolate
  subject layers with alpha mattes where available, pre-render dense sections,
  and align SFX using frame offsets plus `adelay`, `amix`, and short fades.
- Remotion: store beat frames, clip speed, effect layers, subject masks,
  transition shake frames, SFX frames, and pre-render boundaries as explicit data.
- CapCut: use beat markers, Speed, Duplicate, Mask, Remove Background/quick
  brush, overlays, blend modes, effect stacks, separate projects or compound
  sections, and Sounds > Device imports.
- Premiere: use Speed/Duration or Time Remapping, duplicated masked layers,
  nested sequences or Render and Replace, Turbulent Displace/Lens Distortion or
  Transform shake equivalents, and marker-based SFX spotting.

## Mistakes And QC

- Do not pick one universal speed value; adjust per clip until the action beat
  lands cleanly.
- Do not overtrim subproject clips before pre-rendering; keep enough handles for
  replacement and transition work.
- Do not apply transition shakes before the transition effect stack is visible.
- Do not let masks create halo edges, rough cutouts, or glow spilling over the
  wrong subject.
- Do not let SFX, voice lines, or music licensing assumptions enter a publishable
  edit without rights review.
- Check that turbulent, wide-angle, glow, flicker, and black-matte extensions
  still preserve action readability at phone size.

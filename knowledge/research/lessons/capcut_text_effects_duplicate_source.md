# Lesson: CapCut Text Effects Duplicate Source

## Source

- Tutorial: `CapCut Text Effects`
- Notes: `knowledge/research/transcripts/capcut text effects.txt`
- Date processed: 2026-05-29
- Duplicate source check: byte-for-byte identical to `knowledge/research/transcripts/powerful capcut edits.txt`
- Related cards:
  - `knowledge/techniques/compositing/compositing_capcut_eye_power_overlay_001.json`
  - `knowledge/techniques/motion/motion_capcut_pendulum_transition_movement_001.json`
  - `knowledge/techniques/beat_sync/beat_sync_capcut_speed_match_twixtor_001.json`
  - `knowledge/techniques/nle_workflow/nle_capcut_heavy_overlay_prerender_workflow_001.json`
  - `knowledge/techniques/transition/transition_capcut_turbulent_wide_angle_shake_001.json`
  - `knowledge/techniques/sound_design/sound_anime_edit_sfx_voice_line_spotting_001.json`

## What The Tutorial Teaches

The saved file name suggests a CapCut text-effects tutorial, but the transcript
content matches the already-processed CapCut AMV/power-edit workflow from
`Powerful CapCut Edits`. It teaches speed-matched action clips, eye/power overlay
alignment, lag-safe export/re-import replacement, pendulum movement, turbulent
wide-angle transition polish, and event-matched SFX/voice-line spotting.

No new text-effect-specific technique was extracted from this source. The only
text-related material is a brief font-selection mention, which is not enough to
create a reliable typography or kinetic-caption rule.

## Agent Decision Rules

- Treat this transcript as an additional source reference for the existing
  CapCut AMV/power-edit technique cards.
- Do not create a new text-effects skill, preset, or card from this file unless a
  different source provides actual text animation, masking, caption, typography,
  or kinetic-type instruction.
- Reuse the existing CapCut AMV cards when the requested edit needs speed-matched
  action, eye/power overlays, pre-render replacement, pendulum movement,
  turbulent wide-angle transitions, or event-matched SFX.

## Timeline Patterns

- Reused pattern:
  `beat_match_clips -> align_power_overlay -> pre_render_heavy_layers -> replace_with_duration_check -> pendulum_movement -> turbulent_wide_angle_transition -> event_matched_sfx`

## Implementation Notes

- ffmpeg: no new implementation path; use the existing card notes for `setpts`,
  `overlay`, intermediate renders, and frame-based SFX alignment.
- Remotion: no new component model; reuse beat/action metadata, overlay feature
  positions, replacement duration checks, transition peak frames, and SFX cue
  frames.
- CapCut: no new text-effect workflow was present; use the existing Speed,
  overlay, export/re-import, Pendulum, turbulent/wide-angle, and SoundFX notes.
- Premiere: no new text-effect workflow was present; use existing Time Remapping,
  masked overlays, Render and Replace, adjustment-layer transitions, and marker
  based SFX notes.

## Mistakes And QC

- Do not file this source under typography knowledge only because the filename
  says text effects.
- Do not duplicate existing technique cards when a transcript repeats the same
  material.
- Existing CapCut AMV QC rules already cover the actionable checks from this
  source: beat sync, overlay alignment, replacement duration, pendulum
  readability, transition distortion, SFX sync, and source/license status.

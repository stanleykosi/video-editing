# Lesson: Powerful CapCut Edits

## Source

- Tutorial: `Powerful CapCut Edits`
- Notes: `knowledge/research/transcripts/powerful capcut edits.txt`
- Date processed: 2026-05-29
- Related cards:
  - `knowledge/techniques/compositing/compositing_capcut_eye_power_overlay_001.json`
  - `knowledge/techniques/motion/motion_capcut_pendulum_transition_movement_001.json`
  - `knowledge/techniques/beat_sync/beat_sync_capcut_speed_match_twixtor_001.json`
  - `knowledge/techniques/nle_workflow/nle_capcut_heavy_overlay_prerender_workflow_001.json`
  - `knowledge/techniques/transition/transition_capcut_turbulent_wide_angle_shake_001.json`
  - `knowledge/techniques/sound_design/sound_anime_edit_sfx_voice_line_spotting_001.json`

## What The Tutorial Teaches

This tutorial extends the existing CapCut AMV workflow with two practical
CapCut-specific moves: align a character eye or power overlay by slowing the
clip before the effect pass, and add a pendulum movement pass when a clip needs
stronger swing before the transition pass.

The workflow is still order-dependent: speed-match action to the beat, build
heavy overlays in short isolated passes, export and replace only after duration
is stable, preserve timing with a placeholder or black spacer when removing
temporary layers, add motion/transition polish, then spot SFX against the final
visual events.

## Agent Decision Rules

- Use eye/power overlays when a close-up detail needs a readable transformation
  that is tied to a character moment, not as a generic decoration.
- Slow or speed-adjust the source only enough to align the overlay and beat; do
  not apply a Twixtor-style slow effect directly and then edit blindly.
- Use export/re-import only after overlay timing is stable, and preserve the
  original duration with a spacer or placeholder so replacement does not shift
  the main timeline.
- Use one pendulum pass for added movement, two when the style needs strong
  swing, and a third only when readability still survives.
- Reverse or extend a short effect clip only when it smooths a visible loop,
  covers the required beat, and does not create a stutter.
- Spot SFX after visuals are locked: clip starts, power alignments, lightning
  entrances, glass-break overlays, and voice-line identity beats each need their
  own cue frame.

## Timeline Patterns

- Eye power overlay:
  `beat_marker -> slow_or_speed_adjust_eye_clip -> place_eye_overlay -> mask/scale/position -> reverse_or_extend_if_needed -> pre-render -> replace_main_clip -> transformation_sfx`
- Lag-safe replacement:
  `main_placeholder -> isolated_project -> overlays/effects -> export -> black_spacer_or_placeholder -> replace_original -> duration_check`
- Pendulum movement pass:
  `locked_clip -> apply_pendulum -> preview_swing -> optional_second_or_third_pass -> export/reimport -> transition_pass`
- Final sound pass:
  `locked_visual -> preview_sfx -> place_on_clip_start_or_event -> trim_tail -> add_voice_line_if_identity_job -> full_mix_review`

## Implementation Notes

- ffmpeg: store the target beat frame, source action frame, eye overlay position,
  playback rate, and SFX cue frames; use `setpts`, `overlay`, alpha masks, and
  `adelay`/`amix` for automated recreations.
- Remotion: model the edit as beat/action metadata plus components for eye
  overlay, pendulum transform, pre-render boundaries, replacement duration, and
  SFX frames.
- CapCut: use Speed before heavy effects, isolate dense overlays in separate
  projects, export/re-import only after timing review, preserve duration with a
  temporary spacer, apply Pendulum effects by intensity, then use Sounds or
  device imports for frame-placed cues.
- Premiere: use Time Remapping, nests or Render and Replace, transform/shake or
  lens distortion effects, masked overlays for power details, and markers for
  SFX/voice-line placement.

## Mistakes And QC

- Do not let the pre-render replacement shorten or lengthen the clip by accident.
- Do not stack pendulum, turbulent distortion, wide angle, and shake until the
  character pose becomes unreadable.
- Do not let an eye overlay drift, cover the expression, or survive after the
  transformation beat has ended.
- Do not place SFX by vibe alone; place them on the visible clip start, impact,
  overlay event, or character voice beat.
- Check all downloaded/app-library overlays, sounds, music, and character audio
  for license/platform status before any publishable use.

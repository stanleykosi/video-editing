# Lesson: Keyframe Pro Edits CapCut Property Keyframes

## Source

- Tutorial: `Keyframe Pro Edits`
- Notes: `knowledge/research/transcripts/keyframe pro edits.txt`
- Related cards:
  - `knowledge/techniques/nle_workflow/nle_capcut_keyframe_spacing_control_001.json`
  - `knowledge/techniques/motion/motion_keyframe_focus_zoom_hold_001.json`
  - `knowledge/techniques/motion/motion_capcut_overlay_path_keyframes_001.json`
  - `knowledge/techniques/color/color_keyframed_saturation_shift_001.json`
  - `knowledge/techniques/sound_design/sound_music_ducking_volume_keyframes_001.json`
  - `knowledge/techniques/nle_workflow/nle_capcut_compound_graphics_workflow_001.json`
  - `knowledge/techniques/nle_workflow/nle_capcut_compound_clip_animation_unlock_001.json`
  - `knowledge/techniques/color/color_filter_strength_music_reveal_001.json`

## What The Tutorial Teaches

Keyframes are reusable control points for changing one property over time:
scale, position, saturation, filter strength, volume, rotation, or overlay
placement. The strongest lesson is that keyframes should be treated as
property-specific. If the editor keyframes saturation, later saturation changes
should not silently become hue, brightness, or exposure changes.

The tutorial reinforces CapCut fundamentals: close keyframes create fast changes,
farther keyframes create slower movement, and a first keyframe lets later property
changes generate the next keyframe. It applies the same logic to visual emphasis,
black-and-white shifts, sticker paths, music ducking, and filter-strength reveals.

## Agent Decision Rules

- Use manual keyframes when the edit needs exact path, level, timing, or focus.
- Use built-in animations only when they already land cleanly and do not need a
  custom route or beat.
- For face zooms, animate scale and position together so the eyes or named focus
  stay in the same screen area.
- For quick attention zooms, use only a few frames between keyframes when the
  jolt is intentional.
- For slow engagement zooms, widen the keyframe spacing and keep the crop safe.
- For saturation shifts, keyframe only saturation unless another color property
  has a named story job.
- For music ducking, lower music before speech starts and restore after the
  phrase clears.
- For filter reveals, keyframe filter strength from neutral to the approved look
  in sync with music returning after speech.
- Use a compound clip wrapper when a text/sticker layer needs animation controls
  that are only available on video-like clips.

## Timeline Patterns

- Property keyframe: `select_property -> starting_keyframe -> move_playhead -> change_same_property -> preview -> adjust_spacing`.
- Slow zoom: `scale_position_start -> later_scale_position_change -> eye/focus_stable_hold`.
- Quick zoom: `scale_position_start -> about_4_frames_later_scale_position_change -> short_hold`.
- Sticker path: `set_size_flip_rotation -> position_start -> position_destination_or_offscreen_exit`.
- Saturation shift: `normal_saturation -> desaturated_keyframe -> hold_or_restore`.
- Music duck: `music_full -> pre_speech_duck -> low_under_speech -> post_phrase_restore`.
- Filter reveal: `filter_strength_0 -> music_restore -> filter_strength_full -> montage_or_mood_hold`.
- Animation unlock: `sticker_or_text -> create_compound_clip -> apply_video_style_animation -> reopen_if_source_changes`.

## Implementation Notes

- ffmpeg: represent property keyframes as timestamped values. For color or filter
  reveals, interpolate effect parameters or crossfade neutral/treated layers;
  pair with audio gain envelopes.
- Remotion: store keyframes as frame/value arrays per property. Keep filter
  strength and music gain on the same frame range when the reveal should feel
  unified.
- Blender: keyframe transform/material/compositor values and audio-strip volume
  separately; parent graphics to an empty when wrapper animation is needed.
- CapCut: add the first keyframe on the target clip/overlay/audio, move the
  playhead, change the same property, then preview spacing. Use compound clips
  for text/sticker layers only when the wrapper unlocks needed animation options.
- Premiere: use Effect Controls for Motion, Lumetri/effect amount, and nested
  sequences; use clip-volume rubber-band keyframes for manual ducking.

## Mistakes And QC

- Do not change multiple properties accidentally after creating only one intended
  property keyframe.
- Do not use one volume number for every track; music under speech must be judged
  against the actual voice and song.
- Do not restore music under the last word of a phrase.
- Do not use a filter-strength reveal if the look hides proof, captions, faces,
  or product detail.
- Do not leave a sticker, object, or compound animation onscreen after its concept
  has passed.
- Check that quick zooms land on the intended moment and slow zooms do not make
  the focus drift.
- Confirm every compound wrapper still leaves the original sticker/text editable.

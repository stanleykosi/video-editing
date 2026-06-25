# Lesson: CapCut Keyframes For Motion, Audio, And Color

## Source

- Tutorial: `transcripts/capcut keyframes.txt`
- Related cards:
  - `technique_cards/nle_capcut_keyframe_spacing_control_001.json`
  - `technique_cards/motion_capcut_overlay_path_keyframes_001.json`
  - `technique_cards/motion_keyframed_tilt_tension_001.json`
  - `technique_cards/motion_capcut_cutout_character_walk_001.json`
  - `technique_cards/color_keyframed_saturation_shift_001.json`
  - `technique_cards/sound_music_ducking_volume_keyframes_001.json`

## What The Tutorial Teaches

Keyframes are timeline points that store clip or layer settings such as scale,
position, rotation, color adjustment, and volume. CapCut interpolates between
those points, so the same value change can feel fast or slow depending on how
close the keyframes are.

The tutorial demonstrates a practical ladder:

1. Scale/position zooms for engagement or emphasis.
2. Saturation keyframes for a color-to-black-and-white shift.
3. Volume keyframes for music that rises under montage and ducks under speech.
4. Overlay keyframes for stickers, photos, text, or video sliding in and out.
5. Rotation/tilt keyframes for eerie or disorienting tension.
6. Overlay path keyframes for travel-map or cutout character animation.
7. Manual tracking keyframes to keep a moving subject centered.

## Agent Decision Rules

- Use keyframes when the motion, volume, color, or overlay path needs custom
  timing that a built-in animation or transition cannot provide.
- Use built-in CapCut animations for simple slide-on/slide-off behavior when the
  default timing already works and the effect does not need custom path control.
- Put keyframes closer together for fast jolts, snaps, or dramatic shifts; put
  them farther apart for slow zooms, gradual fades, or smooth mood changes.
- For zooms and tracking, animate scale and position together so the intended
  subject stays in frame.
- For rotation tilts, zoom in before rotating so black corners do not appear.
- For music ducking, place level keyframes before the speech begins so the music
  is already lower when the line starts.
- For color shifts, use the effect as a motivated mood, flashback, reveal, or
  emphasis beat rather than a random filter change.

## Timeline Patterns

- Zoom: `start_full_frame -> end_scale_position -> hold_or_cut`.
- Color shift: `normal_color_keyframe -> saturation_shift_keyframe -> hold_or_restore`.
- Music ducking: `music_full -> pre_duck_keyframe -> low_under_speech -> restore_keyframe -> music_full`.
- Overlay slide: `offscreen_start -> onscreen_focus -> hold -> offscreen_exit`.
- Tilt tension: `zoom_safe_start -> rotate_keyframe -> hold_tension -> reset_or_cut`.
- Cutout animation: `clean_cutout -> first_pose -> small_position_steps -> optional voice/SFX -> clear`.
- Manual tracking: `normal_context -> punch_in -> repeated_subject_center_keyframes -> hold_or_return`.

## Implementation Notes

- CapCut: select the clip or overlay, add a starting keyframe, move the playhead,
  change scale/position/rotation/adjustment/volume, and let CapCut create or
  update the next keyframe. Delete or move bad keyframes instead of stacking
  accidental points.
- ffmpeg: represent visual keyframes as timed crop/scale/overlay/rotate/color
  expressions and audio keyframes as volume envelopes.
- Remotion: store keyframe arrays for scale, x/y, rotation, saturation, and
  audio gain; interpolate them with explicit easing and hold frames.
- Premiere/DaVinci: use Effect Controls or Inspector keyframes for simple moves,
  nested/compound clips for grouped overlays, and audio volume automation for
  music ducking.
- Asset note: map images, stock cutouts, icons, and music used in real projects
  need source/license records before publishing.

## Mistakes And QC

- Do not add movement just because keyframes are available.
- Do not place keyframes so close that the move jolts unintentionally.
- Do not leave a zoom, pan, or tracked crop drifting after the viewer needs to
  read the subject.
- Do not rotate footage without zooming enough to hide black corners.
- Do not let overlays slide over faces, captions, UI, products, map labels, or
  proof details.
- Do not let music stay loud under dialogue because the duck keyframe starts too
  late.
- QC by watching the rendered motion at phone size and muting decorative effects
  mentally: the keyframe should still have a clear focus, story, or clarity job.

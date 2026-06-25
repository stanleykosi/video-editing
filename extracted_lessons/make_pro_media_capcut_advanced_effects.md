# Lesson: Make Pro Media CapCut Advanced Effects

## Source

- Tutorial: `Make Pro Media`
- Notes: `transcripts/make pro media.txt`
- Date processed: 2026-05-29
- Related cards:
  - `technique_cards/compositing_capcut_subject_sandwich_cutout_001.json`
  - `technique_cards/typography_capcut_chroma_video_text_portal_001.json`
  - `technique_cards/motion_capcut_auto_subject_sticker_tracking_001.json`
  - `technique_cards/motion_capcut_slide_on_photo_stack_001.json`
  - `technique_cards/motion_capcut_chapter_card_slide_interrupt_001.json`
  - `technique_cards/compositing_capcut_pip_border_chroma_shape_001.json`
  - `technique_cards/compositing_locked_camera_split_mask_illusion_001.json`
  - `technique_cards/compositing_capcut_green_screen_vfx_insert_001.json`

## What The Tutorial Teaches

This tutorial is a CapCut advanced-effects collection. The reusable lesson is how
to build professional-looking composites with simple mobile tools: export a
prepared layer, re-import it, sandwich foreground cutouts above text or VFX, use
chroma key as a matte, use tracking when the subject stays readable, and use
split masks only when the footage was filmed for the trick.

It also reinforces two production rules: plan space while filming when graphics
will be added later, and treat music, SFX, stock clips, stickers, and green-screen
assets as rights-managed assets rather than assuming app availability means safe
delivery.

## Agent Decision Rules

- Use subject-sandwich compositing when text, stickers, or VFX should appear
  behind a person without leaving CapCut.
- Use video-in-text only with very short words, bold fonts, and clean chroma
  removal; long phrases make the underlying video unreadable.
- Use CapCut automatic tracking for face/body/hand or sticker follows only when
  the tracked feature stays visible.
- Use slide-on photo stacks when the speaker was framed to one side and there is
  planned negative space.
- Use full-screen chapter cards as pattern interrupts when a numbered tip,
  section reset, or essay beat benefits from a scene change.
- Use split-mask illusions and clones only when exposure, focus, camera position,
  and background stay locked between takes.
- Use green-screen VFX inserts only when the asset is rights-safe and the effect
  is placed, color-adjusted, and layered behind the subject intentionally.

## Timeline Patterns

- Subject sandwich:
  `base_clip_with_text_or_vfx -> export -> new_project -> reimport_prepared_base -> original_clean_clip_as_overlay -> remove_background -> align_duration -> qc_edges`
- Video-in-text portal:
  `black_clip -> bold_yellow_text -> export_matte -> overlay_on_video -> chroma_key_text_color -> keyframe_zoom_through_letter -> final_scene`
- Tracked sticker:
  `place_sticker -> set_final_visual_position -> tracking_circle_on_feature -> start_tracking -> preview_drift -> adjust_or_reject`
- Slide photo stack:
  `speaker_off_to_side -> photo_overlay_1_slide_in -> photo_overlay_2_offset -> hold -> slide_out -> caption_safe_review`
- Split-mask illusion:
  `locked_plate -> action_take -> overlay_action_take -> split_mask_on_object_edge -> align_timing -> preview_boundary -> add_foley_if_needed`

## Implementation Notes

- ffmpeg: treat these as layer graphs: base video, prepared text/VFX render,
  chroma-keyed matte layers, foreground cutout alpha, split masks, and cue-aligned
  audio. Use contact sheets for mask edges and caption collisions.
- Remotion: model each trick as explicit layer metadata: render pass, matte color,
  chroma tolerance, foreground segmentation, tracking target, split-mask line, and
  asset license status.
- Blender: use compositor masks, alpha cutouts, green-screen keying, and locked
  camera planes for higher-control versions of the same layer logic.
- CapCut: use export/re-import passes only when the effect requires a prepared
  base; otherwise prefer editable overlays, masks, chroma key, tracking, and
  simple in/out animations.
- Premiere: use nests, Ultra Key, opacity masks, track mattes, Essential Graphics,
  and duplicated foreground layers with rotoscoping or mask tracking when the
  CapCut method needs a professional NLE equivalent.

## Mistakes And QC

- Do not trust Remove Background, Tracking, Chroma Key, or Mask until the full
  affected range has been previewed.
- Do not film split-mask or clone tricks with auto exposure, auto focus, or camera
  movement if the composite must look seamless.
- Do not add photo stacks over a centered speaker unless the crop has safe
  negative space.
- Do not use long phrases for video-in-text reveals; the video needs large letter
  windows.
- Do not use YouTube-ripped, downloaded, app-library, sticker, music, or SFX
  assets in deliverables without license/platform safety notes.

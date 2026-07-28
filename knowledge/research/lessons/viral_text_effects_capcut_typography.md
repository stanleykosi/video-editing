# Lesson: Viral Text Effects CapCut Typography

## Source

- Tutorial: `Viral Text Effects`
- Notes: `knowledge/research/transcripts/viral text effects.txt`
- Related cards:
  - `knowledge/techniques/captions/captions_capcut_adaptive_texture_animation_001.json`
  - `knowledge/techniques/typography/typography_capcut_apple_slide_up_text_001.json`
  - `knowledge/techniques/typography/typography_capcut_axis_stretch_emphasis_001.json`
  - `knowledge/techniques/typography/typography_capcut_opacity_flicker_tick_001.json`
  - `knowledge/techniques/typography/typography_capcut_srt_number_countup_001.json`
  - `knowledge/techniques/typography/typography_capcut_perspective_freeze_text_001.json`
  - `knowledge/techniques/typography/typography_capcut_font_shift_loop_001.json`
  - `knowledge/techniques/typography/typography_capcut_outline_reveal_chroma_001.json`
  - `knowledge/techniques/typography/typography_capcut_chroma_video_text_portal_001.json`
  - `knowledge/techniques/compositing/compositing_capcut_subject_sandwich_cutout_001.json`

## What The Tutorial Teaches

This tutorial is a pack of CapCut social typography effects. The reusable lesson
is not "use every trend"; it is that each text effect needs a role: caption
readability, premium presentation polish, word emphasis, number proof, depth,
environment integration, or a beat-synced accent.

The transcript also demonstrates how many CapCut text effects rely on compound
clips. Compounds can preserve editable source text while letting the agent
duplicate a finished motion template, freeze a chosen perspective frame, or
unlock animation/blend workflows.

Sponsor and asset-document promotion segments were ignored.

## Agent Decision Rules

- Use adaptive caption texture only after auto captions are corrected and tested
  against bright, dark, busy, and face-heavy frames.
- Use Apple-style slide-up text for clean premium emphasis, not dense subtitles.
- Use width/height stretch on one impact word only.
- Use opacity flicker and font-shift loops as short accents; return to readable
  stable text before the viewer needs the word.
- Use SRT number counters only when the final value and units are verified.
- Use perspective freeze text when angled words fit the scene geometry or
  thumbnail/title design.
- Use text-behind-object and outline reveal effects only when cutout edges remain
  clean through playback.
- Use video-in-text direct masks for speed; use the compound/blend method when
  editable text animations are required.
- Add tick/click SFX only when the sound lands on visible text changes and stays
  below speech.

## Timeline Patterns

- Adaptive captions:
  `auto_captions -> apply_style_to_all -> font_spacing -> caption_animation_preset -> reposition -> qc`.
- Apple slide-up:
  `text -> transform/blend keyframes -> 22-frame landing -> opacity_0_start -> Y_offset_start -> cubic_ease -> compound_template -> duplicate/edit`.
- Axis stretch:
  `text -> disable_uniform_scale -> width_or_height_start -> width_or_height_end -> hold_or_restore`.
- Flicker:
  `six_opacity_keyframes -> opacity_sequence -> optional_tick_sfx -> full_mix_qc`.
- Number counter:
  `number_srt -> import -> apply_style -> compound -> speed_curve -> final_hold`.
- Perspective freeze:
  `compound_text -> perspective_animation -> choose_frame -> freeze -> stagger_words -> group_transform`.
- Text behind object:
  `base_video -> duplicate_top_cutout -> text_between_layers -> edge_qc`.
- Outline reveal:
  `base_video -> subject_cutout -> fill/outline_text -> key_color_matte -> compound -> chroma_key -> edge_qc`.
- Video-in-text:
  `video_text_mask` for fast static text, or
  `black_background_text_compound -> fill_video_blend -> wrapper_screen -> internal_text_animation`.

## Implementation Notes

- ffmpeg: use drawtext/ASS for captions and counters, pre-render text overlays for
  non-uniform stretch or perspective, and use chromakey/alpha masks for text
  portals and outline reveals.
- Remotion: model each effect as a reusable component with text role, frame range,
  safe region, easing, blend mode, SFX frame, and caption-suppression metadata.
- Blender: use text objects, alpha/material animation, camera perspective, and
  foreground masks for higher-control composites.
- CapCut: correct captions before styling, use Character spacing lightly, create
  compounds for reusable text templates, use Custom Removal/Remove Background
  only after playback edge review, and keep final captions/SFX editable where
  possible.
- Premiere: use Essential Graphics, nests, opacity/position keyframes, Ultra
  Key/Track Matte Key, and Roto Brush/AE for more precise subject separation.

## Mistakes And QC

- Do not let trendy text effects replace readability.
- Do not leave ordinary captions duplicated under designed text that already
  carries the phrase.
- Do not trust CapCut cutout, chroma key, blend mode, or font animation without
  phone-size playback review.
- Do not use generated number counters until the final value and units are
  verified.
- Do not let tick/click SFX continue after the flicker or font shift ends.
- Check that text effects avoid faces, product UI, proof, captions, and action.
- Confirm every highly stylized text moment has one primary reading path.

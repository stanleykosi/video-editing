# Lesson: Ultimate Guide To Shortform Premiere Reels

## Source

- Tutorial: `Ultimate Guide To Shortform`
- Notes: `knowledge/research/transcripts/ultimate guide to shortform.txt`
- Related cards:
  - `knowledge/techniques/nle_workflow/nle_j_l_cut_dialogue_smoothing_001.json`
  - `knowledge/techniques/captions/captions_two_word_social_subtitles_001.json`
  - `knowledge/techniques/captions/captions_premiere_one_word_pop_fade_001.json`
  - `knowledge/techniques/retention/retention_hook_text_design_sequence_001.json`
  - `knowledge/techniques/motion/motion_filler_background_text_animation_001.json`
  - `knowledge/techniques/motion/motion_broll_text_readability_sequence_001.json`
  - `knowledge/techniques/motion/motion_full_screen_object_animation_001.json`
  - `knowledge/techniques/motion/motion_adjustment_zoom_blur_flow_001.json`
  - `knowledge/techniques/sound_design/sound_music_audition_story_fit_001.json`

## What The Tutorial Teaches

This tutorial teaches a practical Premiere Pro short-form workflow: cut the talking-head base first, smooth dialogue with J-cuts, generate short subtitles, convert selected caption layers into animated graphics, build a stronger hook with text design, keep the body visually active with filler cards, B-roll text sequences, and full-screen object animations, then finish with adjustment-layer zooms and music that fits the tone.

The strongest extraction is not a single effect. It is the order of operations: clean pacing first, readable captions second, visual hierarchy third, polish and music last.

## Agent Decision Rules

- Build the clean A-roll timeline before adding hook graphics, filler visuals, B-roll, or music.
- Use one-word captions only for high-energy social pacing; use longer subtitle chunks when comprehension or accessibility matters more.
- Convert captions to graphics only after transcript timing, wording, and placement are corrected.
- Use hook text design for the first major claim or curiosity line, not every sentence.
- Use filler background text when the talking head needs a quick visual reset and the concept can be represented with text alone.
- Use B-roll text sequences when the spoken line names an experience, object, status, proof point, or emotional contrast that can be shown.
- Use full-screen animation for high-value abstract ideas or brand/tool moments; avoid spending that effort on throwaway lines.
- Use adjustment-layer zooms and blur only where they improve flow or emphasize a section change.
- Audition music by fit and license safety; do not let a trendy track hide weak pacing or mask speech.

## Timeline Patterns

- `rough_cut -> silence_removal -> J_cut_smoothing -> caption_generation -> caption_style -> caption_animation -> hook_text_design -> body_visuals -> post_zoom -> music_fit`
- `hook_line -> stacked_text_design -> emphasized_keyword -> glow_or_accent -> body_rest_or_visual_support`
- `spoken_body_concept -> filler_background_or_broll_or_fullscreen_animation -> readable_text -> return_to_speaker_or_next_concept`
- `section_start -> adjustment_layer_zoom_out_blur -> clean_hold_or_zoom_in -> duplicate_only_where_needed`

## Implementation Notes

- Premiere: use the razor tool or equivalent trims for silences, then Alt-select video independently to overlap picture and sound for J-cuts.
- Premiere captions: use text transcription and short caption settings as a draft; one-word social captions can start around 7 characters, 2 seconds max duration, and one line.
- Premiere graphics: use a clean sans font, lower-third placement, phone-readable size, saved caption style, and upgrade captions to graphics only before animation.
- Premiere motion: use Transform effect keyframes for opacity, position, scale, and rotation; use easing so moves start quickly and settle smoothly.
- B-roll readability: place text above B-roll, then put an adjustment layer between text and video to darken and desaturate the background.
- Full-screen animation: build from background, main object/PNG, design elements, and text; animate the object with scale/rotation and animate support circles from scale 0.
- Adjustment zoom: a strong starting point is scale 130 to 100 with blur 3 to 0 for a zoom-out reveal, then optional scale 100 to 115 for a controlled zoom-in.
- Remotion: represent each phase as named sequences with caption style IDs, hook text layers, visual support layers, adjustment zoom ranges, and music candidates.
- ffmpeg: approximate with trims, concat, subtitles, drawtext, overlays, scale/crop/zoompan, background dim/desaturation, and short phone-size preview renders.

## Mistakes And QC

- Do not paste auto captions into the final without reviewing wording, timing, chunk length, and placement.
- Do not stack captions, hook text, B-roll text, and full-screen labels in the same frame unless the hierarchy is obvious.
- Do not use body visuals as filler when they do not match the spoken concept.
- Do not convert every moment into a full-screen animation; reserve it for high-value ideas.
- Do not duplicate adjustment zooms so often that the edit feels mechanically preset-driven.
- Check that music is licensed or platform-safe, speech remains intelligible, and the selected track actually improves tone.

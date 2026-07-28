# Lesson: Short-Form Editing - Viral Hook And Visual Stack

## Source

- Tutorial: `Short-Form Editing`
- Notes: `knowledge/research/transcripts/short-form editing.txt`
- Date processed: 2026-05-28
- Related cards:
  - `knowledge/techniques/retention/retention_shortform_claim_hook_001.json`
  - `knowledge/techniques/retention/retention_high_energy_hook_rest_001.json`
  - `knowledge/techniques/motion/motion_subject_tracking_statement_zoom_001.json`
  - `knowledge/techniques/motion/motion_show_dont_tell_visual_stack_001.json`
  - `knowledge/techniques/captions/captions_two_word_social_subtitles_001.json`

## What The Tutorial Teaches

This tutorial teaches a high-energy short-form workflow where the idea, script, edit, sound, and captions all serve fast viewer comprehension. The main pattern is: research a strong short-form idea, extract a claim with immediate attraction, deliver it with energy in the first five seconds, remove wasted time, center-track the subject, turn spoken concepts into visual evidence, sync SFX to every meaningful movement, and finish with tight social subtitles.

## Agent Decision Rules

- Start from the idea before the edit: trend research, niche-specific AI prompts, and "sounds too good to be true" curiosity can generate short-form concepts worth testing.
- The first five seconds need a strong claim, usually built from desire, social proof, controversy, surprise, or disbelief.
- Keep sentences short and remove setup that does not help the viewer understand the claim or payoff.
- Film or crop with enough room around the body for zoom-ins, zoom-outs, and subject tracking.
- Use zooms to emphasize important statements and tracking to follow movement.
- Show the idea visually whenever possible: text, icons, stock footage, screenshots, GIFs, masks, glows, and animated callouts should replace unnecessary verbal explanation.
- After an intense hook, give the viewer brief rest sections so the edit does not become exhausting.
- Match whooshes, hits, reverse hits, and transitions to real motion, text pops, and anticipation beats.
- Keep background music low enough that speech remains the anchor.
- Use short social subtitles, often one or two words per card, but remove captions where they clutter the screen or duplicate stronger visual storytelling.

## Timeline Patterns

- Viral short setup: `trend_or_niche_research -> strong_claim -> five_second_hook -> fast_value_delivery -> visualized_proof -> payoff`.
- High-energy edit rhythm: `intense_hook -> show_dont_tell_intro -> calmer_rest_beat -> important_statement_zoom -> visual_stack -> sound_design -> subtitles`.
- Subject tracking: `wide_body_room -> center_guides -> scale_position_keyframes -> statement_zoom -> re-center_on_motion`.
- Show-don't-tell visual stack: `spoken_concept -> timed_text_or_icon -> supporting_stock_or_GIF -> mask_or_background -> transition_to_next_concept`.
- Sound design: `movement_or_text_pop -> whoosh_or_hit -> reversed_hit_before_question_or_reveal -> low_music_bed`.
- Subtitle pass: `transcribe -> short_caption_chunks -> style_preset -> remove_unneeded_captions -> convert_to_graphics_if_animating -> phone_size_qc`.

## Implementation Notes

- ffmpeg: use `silencedetect`, `trim`, `crop`, `scale`, `overlay`, `drawtext`, `zoompan`, `afade`, `areverse`, and contact sheets to review hook, captions, overlays, and SFX alignment.
- Remotion: store short-form beats as data with `claimType`, `hookFrames`, `focusBox`, `subjectCenter`, `visualStack`, `captionWords`, `sfxFrame`, and `restBeat` fields.
- Blender: use camera or object keyframes for icon/text pop-ups, masks, and stylized visual stack elements when 3D staging is needed.
- CapCut: use keyframes, tracking/crop, text templates, stock overlays, masked visuals, SFX tracks, and manual captions as editable drafts.
- Premiere: use sequence markers, rulers/guides, Effect Controls position/scale keyframes, Essential Graphics styles, text-to-captions, upgraded caption graphics, clip gain, and SFX markers.

## Mistakes And QC

- Using generic AI prompts instead of niche-specific idea prompts.
- Opening with a weak claim or a long setup before the viewer knows why to care.
- Moving at maximum intensity for the whole short with no rest beat.
- Cropping too tightly during filming so later zooms cut off body, hands, or captions.
- Using zooms constantly instead of on important statements.
- Showing every spoken word as text when an icon, stock shot, or simple visual would communicate faster.
- Leaving whooshes too loud or unsynced from movement.
- Captioning sections where the visual stack already carries the idea and the captions only clutter the frame.

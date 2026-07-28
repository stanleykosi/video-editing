# Slow Human Retention Editing

## Purpose

Guide slower, human short-form edits where connection, proof, warmth, and
intentional imperfection carry retention more than constant hyper-editing.

## When To Use This Skill

- Editing a Reel, TikTok, Short, or creator story that should feel personal,
  warm, and human.
- Deciding whether to keep an imperfect unscripted moment instead of cutting it
  for technical polish.
- Building a slower short where the first seconds still need a clear hook.
- Using proof artifacts, simple dynamic zooms, realistic foley, and warm color to
  make a story feel believable.
- Comparing short-form timeline versions to find a balanced cut instead of the
  absolute shortest cut.

## Core Principles

- Slow does not mean loose; every pause, hold, drop, and imperfection needs a job.
- Hook the viewer early, then earn slower pacing through human connection and
  story clarity.
- Imperfection can create trust when it reveals warmth, vulnerability, humor, or
  character.
- Show proof or lived context when a line names a result, memory, obstacle,
  place, or status change.
- Use the least editing that still guides the viewer's eye, ear, and emotion.
- Hyper-editing is not always better; the right density depends on the audience,
  tone, and story.
- Sound and cuts can create contrast just as strongly as color.
- Organic captions and warm grading should support the human feeling without
  becoming template-like or hard to read.

## Techniques

- `knowledge/techniques/retention/retention_first_three_second_dynamic_zoom_hook_001.json`
- `knowledge/techniques/retention/retention_human_imperfection_pattern_interrupt_001.json`
- `knowledge/techniques/story_pacing/story_contrast_intensity_drop_001.json`
- `knowledge/techniques/sound_design/sound_realistic_foley_cutaway_001.json`
- `knowledge/techniques/color/color_warm_nostalgic_hope_grade_001.json`
- `knowledge/techniques/nle_workflow/nle_stacked_timeline_versioning_001.json`
- `knowledge/techniques/captions/captions_organic_low_focus_social_subtitles_001.json`
- `knowledge/techniques/motion/motion_keyframe_focus_zoom_hold_001.json`
- `knowledge/techniques/motion/motion_show_dont_tell_visual_stack_001.json`
- `knowledge/techniques/transition/eye_trace_continuity_cut.json`
- `knowledge/techniques/retention/retention_overediting_value_supplement_001.json`

## Timing Rules

- In feed-first shorts, the first 3-5 seconds should contain motion, proof, face,
  or a clear reason to continue.
- Use a dynamic zoom, image stack, or proof frame early only when it clarifies the
  hook.
- Keep short-form black/drop gaps below one second unless a longer cinematic
  pause has a named purpose.
- Hold human interruptions only until the connection beat lands, then return to
  the main story.
- A long simple dynamic zoom can carry a 20-30 second emotional section when the
  story and face remain compelling.
- Compare original, shorter, and balanced versions before locking the final cut.

## Motion Rules

- Keep faces, eyes, and proof artifacts guided through early cuts and zooms.
- Use center guides, eyeline, or rule-of-thirds targets to make match cuts feel
  smooth.
- Do not add new effects to a long section simply because time has passed.
- Crop or punch in on a human reaction only when the reaction is the point.
- Hold after zooms so the viewer can read the face, proof, or emotional cue.

## Sound Rules

- Add foley only for visible or strongly implied physical movement.
- Keep foley, whooshes, risers, and reverb below dialogue.
- Use layered sound to build intensity only when a drop, reset, or calmer section
  receives the contrast.
- Preserve natural voice, breath, room tone, and small movement sounds when they
  make the moment more believable.
- Fade edges around micro drops and foley so the edit does not click or feel
  broken.

## Caption Rules

- Captions support comprehension; they should not become the most digital-looking
  part of a warm human reel.
- Keep captions away from faces, proof artifacts, hands, and emotional reactions.
- Use restrained static captions or soft fades when kinetic captions would fight
  the tone.
- Remove duplicate captions when proof text, hook text, or visual text already
  carries the same idea unless accessibility requires both.

## Color Rules

- Use warm looks only when warmth supports hope, memory, gratitude, or emotional
  closure.
- Preserve skin, proof, and caption contrast before adding glow, grain, radial
  blur, or vignette.
- Reduce harsh digital feeling without making the image muddy, orange, or soft.
- Keep the look consistent enough that the warm section feels designed, not
  randomly filtered.

## Tool Implementation Notes

- DaVinci Resolve: use stacked timelines for original, shorter, and balanced
  versions; use Dynamic Zoom for simple social movement and Fusion only when the
  move needs manual control.
- Premiere: duplicate sequences for major pacing variants, use guides for face
  continuity, keep foley on separate tracks, and apply warm looks on adjustment
  layers after the chosen cut is stable.
- CapCut: duplicate projects for timing experiments, add simple keyframe zooms,
  use restrained captions, and manually lower foley/music under speech.
- ffmpeg: store the locked cut as an EDL/concat list, then add zoom/crop, black
  micro-drop inserts, foley mix, subtitle burn-in, and warm look filters.
- Remotion: model hook, interrupt, contrast drop, foley cues, caption style, and
  color look as named components with explicit frame data.

## Common Mistakes

- Calling an untrimmed edit "slow" when the pauses have no story purpose.
- Cutting out the most relatable human moment because it is technically imperfect.
- Keeping every mistake instead of only the ones that deepen connection.
- Using dynamic zoom as a formula while ignoring hook quality and payoff.
- Making the black/drop reset look like an accidental render gap.
- Adding foley that is louder or more dramatic than the visible action.
- Making warm color so heavy that captions, proof, and skin stop reading cleanly.

## QC Checklist

- First 3-5 seconds contain motion, proof, face, or a clear retention reason.
- The final version was chosen after comparing named timeline variants.
- Every slow hold, pause, or gap has a named story, emotion, proof, or
  comprehension purpose.
- Human imperfections kept in the cut build connection and create no consent,
  privacy, or dignity issue.
- Any short-form black/drop gap is under one second unless intentionally
  cinematic.
- Dynamic zooms preserve faces, proof, captions, and emotional reactions.
- Foley matches visible movement and stays below dialogue.
- Captions are readable but visually restrained.
- Warm grade preserves skin, proof, caption contrast, and compression cleanliness.

## Source Lessons Added

- 2026-05-29: `Slow Editing`

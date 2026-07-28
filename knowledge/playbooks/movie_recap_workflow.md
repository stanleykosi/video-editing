# Movie Recap Workflow

## Purpose

Guide movie recap, movie explainer, anime recap, episode recap, and scene
commentary videos that use fresh narration over transformed movie visuals.

This skill is intentionally practical: it captures the working method from
`knowledge/research/transcripts/movie recap.txt` so agents do not default to long raw scene runs or
generic montage when the user asks for a movie recap.

## Use When

- The user asks for a movie recap, movie explainer, anime recap, series recap, or
  story recap using a movie/video as source.
- The final should be narration-led with the original movie audio muted.
- The source movie is longer than the intended short output.
- The edit should work as short social clips, especially TikTok, Reels, Shorts,
  or compact YouTube recap units.
- The agent needs to select gripping scenes and match them tightly to narration.

## Avoid When

- The user wants a review, essay, or opinion video with little or no movie
  footage.
- The user asks for an unedited continuous scene.
- The source visuals cannot be inspected.
- The user explicitly asks for a full long recap instead of short paragraph
  units.

## Core Rules

- Work narration first. The recap script determines the visual sections, not the
  movie's linear order.
- Recap narration must go through `knowledge/workflows/content_creation/script_subagent_review_loop.md`:
  a writer subagent drafts the paragraph script and an independent harsh critic
  subagent rejects generic, AI-sounding, inaccurate, unvisual, or weakly hooked
  lines until the draft passes.
- Include the release year when identifying or discussing a movie title so the
  correct film/version is used.
- Generate or write compact, high-tension narration around the most engaging
  sections, not a full plot dump.
- Break the narration into paragraphs. Each paragraph needs a source scene hint,
  a verified scene range, and a visual job.
- Default to one paragraph per exported short. Do not stitch three paragraphs
  into one longer recap unless the user asks for it.
- Mute the original movie audio by default. Narration is the main audio.
- Do not use long unbroken movie excerpts. Transform source visuals into short
  fragments.
- Use AI-proposed timestamps only as hints. Verify the actual source frames
  before cutting.
- Apply the repo's narration/visual alignment rules: named characters, places,
  objects, and events must be visible when narration refers to them.

## Technique Cards

- `knowledge/techniques/genre_workflow/movie_recap_paragraph_scene_workflow_001.json`
- `knowledge/techniques/nle_workflow/movie_recap_chop_delete_flip_speed_transform_001.json`
- `knowledge/techniques/qc/qc_narration_visual_character_alignment_001.json`
- `knowledge/techniques/story_pacing/motivated_broll_story_sequence_001.json`
- `knowledge/techniques/retention/retention_shortform_claim_hook_001.json`
- `knowledge/techniques/sound_design/documentary_audio_intelligibility_001.json`

## Workflow

1. **Movie and section selection.**
   Use the user's movie if provided. If not, ask for or propose a title. Include
   the release year. Identify the most gripping section or sections rather than
   summarizing the entire movie.

2. **Paragraph script.**
   Use the writer/critic subagent loop before accepting the narration. Write a
   short, energetic narration in compact paragraphs. Each paragraph should
   describe one scene-driven beat and contain enough detail for fans to feel the
   stakes. The critic must reject generic recap filler, fake cliffhangers, and
   model-script patterns such as "what happens next changes everything" or "it's
   not X, it's Y".

3. **Scene range planning.**
   For each paragraph, write a scene hint and approximate source timestamp range.
   Treat AI scene timestamps as rough leads. Find and verify the actual scene by
   visual inspection.

4. **Voiceover.**
   Generate or use narration per paragraph. A fast, energetic recap voice can
   work well, but clarity is more important than raw speed.

5. **Visual assembly per paragraph.**
   Import the matching movie source range, mute its audio, and build a transformed
   visual sequence against the paragraph voiceover.

6. **Transform pattern.**
   Chop the verified source scene into roughly 2-3 second fragments, delete
   alternating fragments to compress the source, mirror alternating retained
   fragments when it does not harm clarity, and use optional speed changes to fit
   the narration.

7. **Format pass.**
   Choose 16:9, 9:16, or another requested aspect ratio. Apply vertical crop,
   blurred background, or reframing after the fragment pattern is locked.

8. **QC and export.**
   Check rendered contact sheets for scene match, source-audio mute, no long raw
   source run, no confusing mirror, no narration/visual mismatch, and the final
   requested runtime/format.

## Implementation Notes

- In EDLs, add paragraph metadata:
  - `paragraph_id`
  - `voiceover_window`
  - `source_scene_hint`
  - `verified_source_range`
  - `fragment_pattern`
  - `mirror`
  - `playback_rate`
- If the source scene range is much longer than the voiceover, do not simply
  pick the beginning. Watch/sketch the range and retain the fragments that best
  match each sentence.
- The transcript's deletion pattern removes every other chopped segment. Use that
  as a default compression method, but override it when the sentence needs a
  specific action or reaction.
- Mirroring is a transformation option, not an obligation. Skip it on shots with
  readable text, recognizable directional movement, asymmetric weapons/props, or
  continuity that becomes confusing when flipped.
- Speed changes should fit the narration and preserve the action. Slow down a
  key shot if the viewer needs to register it; speed up transitional fragments if
  the paragraph needs to close.
- For private tests, this skill can be applied directly. For public-facing work,
  the same creative workflow still needs the project's normal source/asset notes.

## QC Rules

- The final is paragraph-sized unless the user requested a longer recap.
- Original movie audio is muted.
- The voiceover is intelligible and dominant.
- Every paragraph has a matching verified source scene range.
- No generated timestamp was accepted without visual checking.
- No retained source run feels like an unedited movie excerpt.
- Chopped fragments still make story sense after deletion.
- Mirrored fragments do not contain text or confusing direction changes.
- Speed changes do not destroy action readability.
- Each named character, place, object, and event appears at the viewer-facing
  narration timestamp.
- Aspect ratio treatment is consistent after chopping.
- Rendered preview and final spot sheets were reviewed before delivery.

## Common Mistakes

- Making a full multi-minute recap when the stronger method is short paragraph
  units.
- Trusting an AI timestamp and cutting the wrong scene.
- Leaving source audio audible under narration.
- Using a cool action shot that does not match the current paragraph.
- Applying the chop/delete pattern before finding the correct source scene.
- Mirroring every retained shot.
- Stretching a raw source clip by dragging handles instead of using intentional
  speed changes.
- Applying vertical blur/canvas treatment before the edit is chopped and locked.

## Source Lessons Added

- 2026-06-24: `Movie Recap`

# Lesson: Movie Recap Short Transformed Scene Workflow

## Source

- Tutorial transcript: `transcripts/movie recap.txt`
- Date added: 2026-06-24
- Related skill: `skills/movie_recap_workflow.md`
- Related cards:
  - `technique_cards/movie_recap_paragraph_scene_workflow_001.json`
  - `technique_cards/movie_recap_chop_delete_flip_speed_transform_001.json`

## What The Tutorial Teaches

Movie recap shorts should be built from narration-first paragraphs, not from a
full linear retelling. The workflow is:

1. Pick a movie and include the release year when prompting for the story.
2. Generate a short, engaging narration focused on the most gripping parts.
3. Break the narration into paragraphs, with each paragraph mapped to a matching
   movie scene or time range.
4. Turn each paragraph into its own voiceover segment.
5. Build each paragraph as its own short recap unit instead of forcing the full
   three-paragraph script into one long video.
6. For each paragraph, find the matching source scene range in the movie, mute
   the original movie audio, then cut only the visuals against the narration.
7. Transform the source visuals with short cuts, deletion, mirror/flip on
   alternating retained shots, and optional speed changes.
8. Export for the intended aspect ratio after the transformed scene sequence is
   locked.

The strongest practical point in the tutorial is: keep recap exports short. The
creator tests a longer version against a much shorter one and concludes that
one-paragraph shorts are the safer and more repeatable format for this workflow.

## Agent Decision Rules

- Treat a movie recap as a narration-led edit, not a source-audio edit.
- Use the user's movie if provided. If the user asks for suggestions, provide
  candidates and ask which one to use.
- When prompting or researching the movie internally, include the release year so
  the scenes and plot points refer to the correct title.
- Script in compact paragraphs. Each paragraph must have a scene target, visual
  purpose, and approximate source range.
- Prefer one paragraph per final short unless the user explicitly asks for a
  longer recap.
- Source audio from the movie is muted by default. Use generated or recorded
  narration as the main audio.
- Do not use raw continuous movie scenes. Build a transformed visual sequence
  from short fragments.
- Apply the chop/delete/flip/speed workflow only after the matching scene range
  is found and verified visually.
- If AI-proposed timestamps are wrong, search around them and use the agent's
  own visual inspection to find the real matching scene.
- Match visuals to narration tightly; use the repo's narration/visual alignment
  QC card for named characters, locations, events, and objects.

## Timeline Patterns

### One-Paragraph Recap Short

```
movie_selection -> paragraph_narration -> scene_range_lookup ->
source_audio_muted_visuals -> 2-3s fragments -> delete alternate fragments ->
mirror alternating retained fragments -> optional speed adjust -> narration sync ->
short export
```

### Multi-Paragraph Source Project

```
paragraph_1_short -> paragraph_2_short -> paragraph_3_short
```

Do not default to stitching all paragraphs into one long recap. Treat each
paragraph as a reusable episode unless the user asks for a combined version.

## Implementation Notes

- In ffmpeg/EDL terms, represent each paragraph as a group with:
  - `paragraph_id`
  - `voiceover_text`
  - `voiceover_audio`
  - `source_scene_hint`
  - `verified_source_ranges`
  - `transform_pattern`
  - `output_duration`
- The tutorial uses three-second chunks, but the agent should treat this as a
  target pattern rather than an absolute rule. A practical range is 2-3 seconds
  per fragment, adjusted for action readability and narration sync.
- The deletion step keeps every other fragment after chopping the source scene.
  The result should feel compressed and transformed, not like a continuous scene.
- The flip/mirror step applies to alternating retained fragments, not every shot.
  Avoid flipping text-heavy shots, recognizable asymmetric story details, or
  direction-critical action when it harms clarity.
- Speed changes are optional and should solve timing: slow a shot when the visual
  needs more hold time, or speed up when the narration needs the beat to clear.
- For vertical output, use a 9:16 crop/reframe or blurred background treatment
  only after the chop pattern is locked, so the visual treatment is applied
  consistently to all retained fragments.

## Mistakes And QC

- Do not build a long full-movie recap by default when the intended method is
  short one-paragraph exports.
- Do not leave movie source audio under the narration.
- Do not trust AI-proposed scene timestamps without visual verification.
- Do not stretch a raw movie scene to fit narration; transform it with short
  fragments and scene selection.
- Do not flip shots where mirrored direction or text makes the scene confusing.
- Do not let the recap become random action montage. Each retained fragment must
  match the paragraph narration.
- Before final export, run rendered-output contact sheet checks for:
  - scene-to-paragraph match
  - named character/event alignment
  - no long continuous source run
  - muted source audio
  - short runtime target
  - aspect ratio and crop safety

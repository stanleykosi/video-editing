# Movie Recap QC

Use this checklist before showing or finalizing any movie recap, movie
explainer, anime recap, episode recap, or narration-over-source scene recap.

## Script And Structure

- The recap is narration-led, not a raw scene export.
- The movie title/version is clear enough to avoid mixing up remakes, sequels, or
  same-title films.
- The script focuses on gripping sections instead of trying to summarize the
  entire movie by default.
- The narration is broken into compact paragraphs with one clear scene job each.
- Each paragraph is treated as its own potential short unless the user requested
  a combined longer video.
- The final runtime matches the intended paragraph/short format.

## Scene Matching

- Every paragraph has a source scene hint and a visually verified source range.
- AI-generated scene timestamps were treated as hints, not accepted blindly.
- The selected fragments match the current narration sentence or paragraph.
- Named characters, places, objects, and events appear at the viewer-facing
  narration timestamp.
- Timestamped contact sheets from the rendered preview/final were reviewed around
  sensitive handoffs.

## Source Audio And Voiceover

- Original movie audio is muted unless the user explicitly asked for a source
  audio moment.
- Narration is the dominant audio.
- Music and SFX, if used, stay below narration.
- The voiceover does not cut off at paragraph boundaries.
- The final audio has no accidental movie dialogue, score, or effects bleeding
  under the narration.

## Visual Transformation

- The edit does not contain long unbroken source movie runs.
- Verified source scenes were chopped into short fragments before final assembly.
- Alternate deletion/compression still leaves the scene understandable.
- Mirrored/flipped fragments do not include readable text, confusing direction
  changes, or continuity-breaking details.
- Speed changes preserve action readability and match narration pacing.
- The final visual order feels intentionally compressed, not random.

## Format And Render

- Aspect ratio matches the requested platform: 16:9, 9:16, square, or other.
- Vertical crops, blurred backgrounds, or canvas treatments are consistent after
  chopping.
- Captions, if present, caption the recap narration and do not cover key action.
- The final render has no black gaps, accidental overlays, offline media, missing
  fonts, or unwanted source subtitles.
- The promoted `final.mp4`, not only the preview, passes spot checks for scene
  match, mute, runtime, and transform pattern.

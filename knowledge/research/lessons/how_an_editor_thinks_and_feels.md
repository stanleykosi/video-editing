# Lesson: How An Editor Thinks And Feels

## Source

- Tutorial: Every Frame a Painting-style lesson on how editors think and feel.
- Local notes: `knowledge/research/transcripts/how an editor think.txt`
- Related cards:
  - `knowledge/techniques/story_pacing/eyes_decision_reaction_cut.json`
  - `knowledge/techniques/story_pacing/emotional_hold_time.json`
  - `knowledge/techniques/story_pacing/build_peak_release_duration_arc.json`
  - `knowledge/techniques/story_pacing/natural_rhythm_cut.json`
  - `knowledge/techniques/story_pacing/justified_jarring_cut.json`

## What The Tutorial Teaches

Editing judgment is driven by emotion and rhythm more than by mechanical rules.
The strongest cut point is often visible in a face, especially the eyes, when a
person decides, reacts, withholds speech, or changes emotion. A cut should either
follow the natural rhythm of the shot so it feels invisible, or deliberately break
that rhythm to create discomfort, agitation, or emphasis.

The tutorial also stresses that emotions need screen time. A scene can fail if the
edit asks the viewer to believe an emotion without giving enough time to enter,
recognize, and leave it. Climactic moments often benefit from a duration arc: shots
compress toward the peak, then expand after the peak so the audience can feel the
consequence.

## Techniques Taught

### Eyes Decision Reaction Cut

Use a close look, eye movement, facial shift, or withheld line as the emotional
source of a cut. Cutting from the eyes to the object, person, or consequence tells
the audience what the character is thinking without exposition.

### Emotional Hold Time

Hold before and after speech or action when the point is emotional belief. The
viewer needs time to connect to the face, register the change, and feel the result.

### Build Peak Release Duration Arc

Compress shot durations toward a peak, then lengthen shots after the peak. The
release can be longer than the build when the audience needs to process failure,
loss, awe, or disappointment.

### Natural Rhythm Cut

Watch the shot repeatedly until the movement, performance, or environmental rhythm
reveals the cut point. This supports invisible editing, especially with physical
actions, walking patterns, busy spaces, and dialogue flow.

### Justified Jarring Cut

Hold slightly too long or cut unusually when the desired reaction is discomfort,
agitation, unease, or friction. The unusual cut must be justified by the emotional
intent.

## Agent Decision Rules

- Read the edit for emotion first: what should the viewer feel at this point?
- Look for visible decision points in eyes, face, body, and breath.
- Do not trim emotional beats only because silence is present.
- If a scene feels unbelievable, test whether the edit stole time from the emotional turn.
- Use invisible rhythm cuts for clarity and flow.
- Use jarring cuts only when the discomfort is the point.
- Shape climaxes as arcs, not isolated moments.
- When overwhelmed, solve one shot and one cut at a time.

## Timeline Patterns

- Eye thought pattern: face/eyes hold -> object or target -> reaction/consequence.
- Emotion hold pattern: pre-speech face hold -> line/action -> post-line reaction hold.
- Climax arc: medium/longer shots -> progressively shorter shots -> peak -> longer release shots.
- Natural rhythm pattern: cut on completed gesture, glance, breath, step, or environmental cycle.
- Jarring pattern: hold past expected rhythm -> cut when tension becomes intentional.

## Timing Rules

- Four seconds can materially change perceived emotion; test alternate holds instead of assuming.
- Avoid reducing major emotional failure or realization to a few frames.
- For build/release arcs, release time may need to be equal to or longer than the buildup.
- Let viewer comprehension decide timing: fast for action clarity, slower for emotional belief.
- Use repeated viewing to find natural cut rhythm, then watch once cold to confirm it still feels right.

## Motion, Sound, Captions, And Color

- Motion: avoid decorative motion over subtle facial decisions; if motion is used, keep it secondary.
- Sound: avoid burying breaths, pauses, or room tone that carry emotional rhythm.
- Captions: do not cover eyes or facial micro-reactions; avoid animated captions during quiet emotional holds.
- Color: preserve eye detail, skin tone, and facial contrast; do not grade away the emotion source.

## Implementation Notes

### ffmpeg

- Generate review windows around candidate cut points with contact sheets and waveforms.
- Compare alternate holds by rendering short A/B clips with different in/out times.
- Use `select`, `trim`, `setpts`, and concat workflows to test duration arcs quickly.
- For QC, create contact sheets around emotional beats and verify the face/eyes remain readable.

### Remotion

- Represent each shot as a sequence with explicit frame durations.
- Build duration arcs as arrays of shot frame counts so compression and release are inspectable.
- Use markers or metadata for emotional beats: `decision`, `peak`, `release`, `jarring_hold`.

### CapCut Equivalent

- Use split edits and manual clip duration adjustments rather than effect presets.
- For emotional holds, extend the clip before or after speech and remove distracting overlays.
- For jarring cuts, hold a reaction slightly longer than expected, then cut sharply.

### Premiere Equivalent

- Use markers for decision points, emotional peaks, and release beats.
- Create duplicate sequence versions for A/B timing tests.
- Use J/L cuts only when they support the intended emotional rhythm.

## Common Mistakes

- Cutting away before the viewer sees the emotional change.
- Treating all silence as dead space.
- Compressing emotional failure, disappointment, or realization until it feels unearned.
- Applying motion/captions over the face when the eyes are the storytelling source.
- Making a jarring cut without a clear emotional reason.
- Focusing on software operations before deciding the viewer reaction.

## QC Checklist

- Can the viewer identify the emotional turn without extra explanation?
- Are the eyes or reaction visible long enough to read?
- Does the scene give enough time before and after major speech/action?
- Does the climax have a clear build, peak, and release?
- Do rhythm cuts feel natural when watched cold?
- Are jarring cuts intentional and emotionally justified?
- Do captions, motion, sound, and grade preserve the key face/reaction?

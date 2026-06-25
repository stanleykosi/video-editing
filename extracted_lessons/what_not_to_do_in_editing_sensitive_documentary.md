# Lesson: What Not To Do In Sensitive Documentary Editing

## Source

- Tutorial notes: `transcripts/what not to do in editing.txt`
- Date processed: 2026-05-27
- Related cards:
  - `technique_cards/documentary_sensitive_tone_alignment_001.json`
  - `technique_cards/motivated_broll_story_sequence_001.json`
  - `technique_cards/movement_continuity_broll_001.json`
  - `technique_cards/longform_confident_pacing_001.json`
  - `technique_cards/meaningful_match_cut_001.json`
  - `technique_cards/documentary_audio_intelligibility_001.json`
  - `technique_cards/ethical_poetic_reordering_001.json`
  - `technique_cards/emotional_hold_time.json`
  - `technique_cards/eye_trace_continuity_cut.json`
  - `technique_cards/licensed_needle_drop_retention.json`
  - `technique_cards/artful_practical_audience_balance.json`
  - `technique_cards/scripted_montage_blueprint.json`

## What The Tutorial Teaches

The tutorial is a critique of a long-form Ukraine travel/documentary edit whose
footage had strong human drama, but whose edit often used the language of a fast,
happy travel vlog. The core lesson is that serious documentary material needs
intention, empathy, motivated B-roll, readable pacing, strong sound, and tone-aware
graphics. Editing quickly for retention can become insecure when the subject and
audience actually need confidence and observation.

## Techniques Taught

### Subject-First Sensitive Opening

For war, crisis, grief, and testimony, open on the subject, evidence, and local
voices before centering the creator. This makes the creator's later perspective feel
more vulnerable and less self-promotional.

### Confident Long-Form Pacing

Once the viewer has committed to a long-form documentary, the edit can slow down.
Hold dense destruction, maps, faces, and emotional beats long enough to scan. Silence,
ambience, and music can carry meaning without constant dialogue.

### Motivated B-Roll

B-roll should not be thrown in as filler. Each shot should visualize the current line,
create contrast, deepen a story beat, or connect a person to place. Related shots
should be grouped into beats instead of scattered.

### Movement Continuity

Smooth documentary sequences benefit from consistent camera or subject movement:
left-to-right with left-to-right, push with push, pull with pull. This keeps the
viewer oriented and helps location sequences feel connected.

### Wide-To-Close Contrast

Use wide-to-close pairs to connect epic scale with human detail: destroyed city wide,
personal detail close; safe place wide, human detail close. This creates rhythm and
meaning instead of generic coverage.

### Tone-Aware Graphics

Graphics should match the subject. Goofy lower thirds, trendy wipes, and old channel
templates can cheapen mature material. Simple maps, restrained titles, and readable
subtitles usually serve sensitive documentaries better.

### Audio Intelligibility

Bad sound can make viewers leave faster than bad visuals. If a story-critical line is
hard to hear, prioritize cleanup or subtitles over decorative graphics. Related B-roll
should have a consistent ambience rule.

### Meaningful Match Cuts

A match cut is not just a cool transition. It creates a relationship between images.
If that relationship is accidental, the cut can imply something false or offensive.

### Ethical Poetic Reordering

Moving interview lines or events can clarify a truthful arc, but it must not change
meaning, causality, speaker intent, or chronology in a materially misleading way.
Sensitive reorders should be flagged for review.

## Agent Decision Rules

- Match edit tone to subject matter before applying the creator's default style.
- For sensitive topics, prefer empathy and subject truth over manipulative retention hacks.
- Confirm title/thumbnail promise early, but do it through subject-first evidence when the topic is serious.
- Slow down when the viewer needs to study dense visual information.
- Do not cut B-roll just because the talking head has been visible for a while.
- Group related shots into story beats and use contrast deliberately.
- Use title cards differently by format: often wasteful in short videos, but potentially confidence-building in long-form after a strong opening.
- Treat captions as story tools; if the audience cannot hear a line, subtitles beat lower thirds.
- Treat every clever transition as a statement. If it has no meaning, simplify it.
- Reorder documentary material only when the truth and speaker intent survive the change.

## Timing Rules

- Sensitive emotional reactions often need a 2-5 second test hold before cutting away.
- Long-form documentary B-roll often needs 1.5-3 seconds per meaningful shot, longer for maps, destruction, signs, or dense details.
- Avoid constant fast cutting after a viewer has committed to an hour-long video.
- Hold maps or route graphics until the viewer understands the full route or distance.
- Let observational destruction or city atmosphere play under music/ambience without forcing dialogue at all times.

## Motion, Sound, Captions, And Color

- Motion: match movement direction in smooth B-roll strings; avoid screen wipes unless the tone supports them.
- Sound: bad dialogue needs repair, subtitles, or removal; music and SFX must duck under testimony.
- Captions: subtitles for hard-to-hear story lines take priority over lower-thirds and decorative labels.
- Color: preserve faces, destruction, evidence, and mature documentary tone; avoid glossy travel-vlog treatment for serious material.

## Implementation Notes

### ffmpeg

- Use contact sheets to check focal points, repeated shots, movement direction, and hold time.
- Use EDL beat labels for subject-first opening, scale, human detail, danger, normal life, and consequence.
- Use `hflip` only when correcting movement direction does not reverse meaningful text, geography, or truth.
- Use audio cleanup and loudness checks before relying on subtitles.
- Keep source timestamps for any reordered documentary lines or events.

### Remotion

- Store B-roll beat metadata: story purpose, focal point, movement direction, hold duration, audio rule.
- Model serious documentary graphics as restrained components with slower reveals and stable text.
- Mark ethical reorders with original source order, edited order, and reason.

### CapCut / Premiere Equivalent

- Remove trendy wipes and old channel templates when they clash with subject tone.
- Use markers or notes for B-roll motivation, title-card placement, and commitment point.
- Assemble related shots into beats; avoid random B-roll filler.
- Use subtitles or caption tracks for hard-to-hear story lines before adding lower thirds.

## Common Mistakes

- Treating war or crisis footage like a happy travel vlog.
- Opening on the creator when the subject should lead.
- Cutting too fast for viewers to scan maps, destruction, faces, or focal points.
- Using B-roll as filler rather than evidence.
- Repeating shots because the edit schedule is rushed.
- Using goofy graphics, screen wipes, or cliche stock music over serious material.
- Letting bad sound or missing subtitles make important lines unintelligible.
- Making match cuts that accidentally imply false relationships.
- Reordering documentary events without checking truth and chronology.

## Contradictions And Applicability Notes

- Short-form retention rules still apply to feed-first clips, hooks, and under-90-second deliverables. This tutorial argues against applying those same fast-cut habits to sensitive long-form documentary once the viewer has committed.
- Title cards can waste time in short videos, but in a long-form documentary after a strong opening, a title card can signal confidence and give the audience a clean entry point.
- Reordering material can improve story clarity, but strict chronology should be preferred when factual order, consent, journalism, or participant trust would be compromised.

## QC Checklist

- Does the opening center the subject before the creator when the topic is serious?
- Can a first-time viewer understand why the video is worth a long commitment?
- Are dense shots held long enough to study?
- Does every B-roll shot serve a story beat?
- Are movement direction and focal point continuity intentional?
- Are graphics mature enough for the subject?
- Is critical dialogue intelligible or subtitled?
- Is music appropriate, licensed/platform-safe, and not overpowering testimony?
- Do match cuts create only intended meanings?
- Are reordered lines/events truthful and traceable to source timestamps?

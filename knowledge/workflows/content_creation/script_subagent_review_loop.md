# Script Subagent Review Loop

Use this for any video task that requires a new or substantially rewritten
script, voiceover, narration, recap paragraph, ad read, explainer, hook, or
storyboard script.

## Non-Negotiable Rule

Do not accept a script produced only by the main agent. Spawn two independent
subagents whenever subagents are available:

1. **Scriptwriter subagent** - writes the draft using the task brief and relevant
   skills.
2. **Script critic subagent** - judges the draft harshly against the task,
   audience, platform, source material, and human writing standards.

The script is not final until the critic returns `PASS`. If subagents are not
available, emulate the two roles in separate isolated passes, document that
limitation in `script_revision_log.md`, and do not call the result equivalent to
the full subagent workflow.

## Required Artifacts

Store the loop inside the project folder:

- `script_brief.md` - task, platform, duration, audience, source constraints,
  style/tone, required knowledge files, and success criteria.
- `script_drafts/round_01.md`, `round_02.md`, etc. - writer drafts.
- `script_critique.md` - critic pass/fail history and required fixes.
- `script_revision_log.md` - what changed each round and why.
- `script.md` - only the critic-approved final script.

Use these templates when creating artifacts:

- `knowledge/workflows/content_creation/templates/script_brief_template.md`
- `knowledge/workflows/content_creation/templates/script_critique_template.md`
- `knowledge/workflows/content_creation/templates/script_revision_log_template.md`

For existing-footage recap/commentary projects, keep these artifacts in the edit
project folder next to the EDL and visual plan.

## Writer Subagent Brief

Give the writer only the task brief, required source notes, and relevant skill
paths. The writer should use:

- `knowledge/playbooks/scriptwriting.md`
- `knowledge/workflows/content_creation/scriptwriter.md`
- `knowledge/playbooks/editing_taste_story_pacing.md`
- `knowledge/playbooks/short_form_retention.md` when retention matters
- `knowledge/workflows/content_creation/youtube_storytelling_workflow.md` for story-led videos
- `knowledge/playbooks/movie_recap_workflow.md` for movie/anime/episode recaps
- any project-specific research notes, transcripts, scene notes, or style packs

Writer output must include:

- final candidate script or recap paragraphs
- hook options when the format benefits from them
- beat table with timing estimates
- visual/source notes per beat
- pronunciation notes for names or invented terms
- lines intentionally avoided or changed because they sounded generic

## Critic Subagent Brief

The critic should be independent. Give it the task brief, the candidate script,
and relevant judging knowledge. Do not give it the writer's private rationale.

The critic must be harsh and specific. It should return:

- `PASS` or `FAIL` as the first line
- one-sentence reason for the decision
- issue list ordered by severity
- exact lines that feel weak, generic, inaccurate, or unhuman
- required revision instructions
- optional examples for one or two fixes, not a full rewrite

The critic must screen for:

- weak hook, delayed promise, or no reason to keep watching
- generic recap summary instead of scene-driven tension
- abstract claims without concrete images
- fake urgency, fake mystery, or overpromising
- plot confusion, wrong chronology, unsupported facts, or poor source alignment
- monotone sentence length or essay rhythm
- dialogue/voiceover that sounds written for a model instead of spoken by a
  human narrator
- filler lines that only sound clever
- any line that cannot be represented visually
- weak transitions between beats
- ending that fades out instead of landing a payoff

## AI-Slop Phrase Checks

Reject or rewrite lines that lean on recognizable model-script patterns unless
there is a deliberate, context-specific reason. Watch especially for:

- "It's not about X, it's about Y"
- "If not X, then Y"
- "But what happens next..."
- "What happens next changes everything"
- "Little did he know..."
- "This is where things get interesting"
- "And that's when everything changed"
- "In a world where..."
- "One thing is clear"
- "Needless to say"
- "The shocking truth is..."
- "You won't believe..."
- "At the end of the day"
- "More than just..."
- "The rest is history"
- "Only time will tell"
- "A journey of..."
- "A testament to..."

The critic should also flag softer versions of those patterns, not only exact
matches.

## Human Writing Standard

The final script should feel like a skilled human narrator wrote it:

- concrete before abstract
- image before explanation
- causal logic before punchline
- specific verbs instead of broad adjectives
- short spoken sentences with varied rhythm
- emotional stakes attached to people, choices, objects, or consequences
- no filler throat-clearing
- no generic moral unless the footage earns it
- every beat gives the editor a visual job

## Loop Rules

1. Writer drafts `script_drafts/round_01.md`.
2. Critic reviews and writes `script_critique.md`.
3. If critic says `FAIL`, writer receives the critique and writes the next round.
4. Repeat until the critic says `PASS`.
5. Main agent copies only the approved version into `script.md`.
6. If the critic blocks three rounds for the same unresolved issue, stop and ask
   the user instead of quietly lowering the standard.

Do not let the critic become the writer. The critic can give examples, but the
writer must perform the rewrite.

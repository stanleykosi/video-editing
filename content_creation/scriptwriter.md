# Scriptwriter

Use this when creating a video from scratch. The script is the spine of the edit:
every visual, caption, sound cue, chart, and asset request should attach to a
specific script beat.

## Inputs

- Topic or working title.
- `knowledge_plan.md` for the selected project route.
- Target platform and aspect ratio.
- Target duration.
- Audience knowledge level.
- Style pack, if any.
- Required facts, claims, examples, CTA, or constraints.
- Source notes or research links when factual accuracy matters.

## Output

Create `script.md` in the project folder using
`content_creation/templates/script_template.md`.

Do not write `script.md` directly from a single main-agent pass. First run the
subagent writer/critic workflow in `content_creation/script_subagent_review_loop.md`.
Only copy the critic-approved version into `script.md`.

## Script Rules

- Start with the viewer problem, curiosity gap, contradiction, or promise.
- Use one main idea per beat.
- Make every claim visualizable.
- Prefer concrete nouns and verbs over abstract summary.
- Keep sentences short enough to caption cleanly.
- Write for voiceover rhythm, not essay rhythm.
- Mark factual claims that require citations before visuals are sourced.
- Mark any generated or illustrative scene so it is not presented as real evidence.
- Avoid AI-sounding contrast formulas and fake-cliffhanger phrases unless the
  project has an explicit parody or trope reason. The critic must reject generic
  lines such as "it's not X, it's Y", "if not X then Y", "what happens next
  changes everything", and similar model-script patterns.

## Short-Form Structure

Use this default unless a style pack says otherwise:

1. Hook: 0-3 seconds.
2. Context or stakes: 3-8 seconds.
3. Evidence or example sequence.
4. Turn, twist, or explanation.
5. Payoff or takeaway.
6. CTA only if it serves the format.

## Long-Form Or Documentary Structure

Use this default:

1. Cold open with a question, contradiction, sensory detail, or story beat.
2. Promise and framing.
3. Evidence blocks.
4. Counterpoint or complication.
5. Synthesis.
6. Human or practical takeaway.

## Knowledge To Use

Start with the selected script/story route in `knowledge_plan.md`, then load the
relevant files below when present:

- `skills/scriptwriting.md`
- `content_creation/script_subagent_review_loop.md`
- `skills/editing_taste_story_pacing.md`
- `skills/short_form_retention.md`
- `skills/documentary_explainer.md`
- `skills/viral_youtube_editing_workflow.md`
- `skills/editor_qc.md`

## QC

- The first line creates a clear reason to keep watching.
- Every beat can be represented visually.
- Claims are source-ready and not overstated.
- No line exists only because it sounds clever.
- No line survives if the critic flags it as generic, AI-sounding, unvisual, or
  disconnected from the task.
- The script fits the target duration at the expected words per minute.

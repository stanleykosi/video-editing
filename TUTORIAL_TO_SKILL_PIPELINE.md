# Tutorial To Skill Pipeline

Use this pipeline to convert tutorials into agent-ready editing knowledge.

## 1. Source Intake

Add the tutorial to `sources/youtube_tutorial_list.md` with:

- URL
- creator/channel
- topic
- target skill files
- priority
- current status

Do not treat a tutorial as knowledge just because it was saved. It becomes knowledge
after extraction.

## 2. Notes Or Transcript

Place cleaned notes in `transcripts/`.

Preferred format:

```md
# Tutorial Title

- Source:
- Creator:
- Date added:
- Target skills:

## Timeline Notes

- `00:00-00:18` Hook or promise.
- `00:18-01:05` Technique explanation.

## Raw Claims Worth Testing

- Claim:
- Context:
- Needs validation:
```

Keep enough timestamps to trace the lesson back, but remove filler.

## 3. Extract Lessons

Create a lesson file in `extracted_lessons/`.

Use this structure:

```md
# Lesson: Short Name

## Source

- Tutorial:
- Notes:
- Related cards:

## What The Tutorial Teaches

## Agent Decision Rules

## Timeline Patterns

## Implementation Notes

## Mistakes And QC
```

## 4. Create Technique Cards

Copy `technique_cards/_template.json` and fill every relevant field.

One tutorial can produce multiple cards. Keep each card atomic enough that an agent
can choose it deliberately.

## 5. Update Skills

Patch the relevant files in `skills/`.

Use stable sections:

- `Use When`
- `Avoid When`
- `Decision Rules`
- `Technique Cards`
- `Implementation Notes`
- `QC Rules`

Do not paste raw transcript into skill files.

## 6. Add Presets

If the lesson implies repeatable settings, add a preset suggestion under `presets/`.

Examples:

- caption style
- transition timing
- sound-design chain
- color look
- motion timing curve

## 7. Add QC Checks

If the tutorial warns about a failure mode, add it to `qc_checklists/`.

Good QC rules are observable:

- captions do not cover faces or product UI
- hit sounds peak below delivery ceiling
- beat cuts land within an intentional tolerance
- color grade preserves skin tone and detail
- motion does not distract from the spoken point

## 8. Validate

For high-value techniques, create a small test in `test_projects/`.

The test should prove that the agent can apply the lesson without re-reading the
original tutorial.

# AI Video Editing Agent Knowledge System

This repo is the local home for a video-editing agent and its editing knowledge base.

The goal is not to store raw tutorial dumps. The goal is to convert editing tutorials,
reference edits, official docs, and real project lessons into structured knowledge that
an AI agent can use when cutting, pacing, captioning, grading, animating, and checking
videos.

It also supports from-scratch faceless video creation: topic research, scriptwriting,
voiceover planning, visual planning, asset planning, timeline construction, preview
rendering, QC, and final export.

## Layout

- `sources/` - source lists, official docs, and reference edits to study.
- `transcripts/` - cleaned tutorial notes or transcripts with timestamps.
- `extracted_lessons/` - distilled lessons from tutorials and projects.
- `technique_cards/` - reusable JSON technique cards.
- `skills/` - agent-readable editing skills grouped by domain.
- `content_creation/` - from-scratch video creation workflows and templates.
- `style_packs/` - reusable style grammar and edit-language files.
- `presets/` - caption, motion, transition, sound, and color preset suggestions.
- `qc_checklists/` - checks the agent should run before calling an edit finished.
- `test_projects/` - small test edits for validating techniques.
- `tools/video-use/` - the local video editing engine and helper scripts.

## Operating Rule

Each tutorial or reference should eventually become:

1. A concise lesson summary.
2. One or more JSON technique cards.
3. Updates to the relevant skill files.
4. Preset suggestions when the technique can be reused.
5. QC checklist rules that catch common failures.

Keep the knowledge practical. Prefer timelines, decision rules, examples, and failure
modes over vague taste notes.

For from-scratch projects, the required production artifacts are:

1. `script.md`
2. `visual_plan.md`
3. `asset_list.md`
4. `edit_decision_list.json`
5. `preview.mp4`
6. `qc_report.md`
7. `final.mp4`

The callable helper layer for that workflow lives in `tools/video-use/helpers/`:
`knowledge_router.py`, `freesound_oauth.py`, `research_checker.py`,
`stock_footage_planner.py`, `voiceover_generator.py`, `caption_engine.py`,
`timeline_builder.py`, `sound_design_engine.py`, `motion_graphics_generator.py`,
`faceless_renderer.py`, and `qc_check.py`.

For from-scratch projects, run `knowledge_router.py` early so the agent scans
the repo's skills, extracted lessons, technique cards, presets, style packs,
source docs, and QC checklists before writing project artifacts.

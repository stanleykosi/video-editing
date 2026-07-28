# Universal Video Editing Engine

This repository contains a programmable nonlinear video-editing engine, its
installed agent workflow, and a structured editorial knowledge base.

The goal is not to store raw tutorial dumps. The goal is to convert editing tutorials,
reference edits, official docs, and real project lessons into structured knowledge that
an AI agent can use when cutting, pacing, captioning, grading, animating, and checking
videos.

It also supports from-scratch faceless video creation: topic research, scriptwriting,
voiceover planning, visual planning, asset planning, timeline construction, preview
rendering, QC, and final export.

## Repository Map

- `src/video_engine/` - canonical engine, public API, CLI, media services,
  operations, render backends, audio, captions, graphics, color, QC, and storage.
- `knowledge/` - the single editorial knowledge namespace. Start with
  `knowledge/README.md`.
- `tools/video-use/` - installed agent workflow, preparation helpers, and thin
  compatibility entrypoints. It is not a second engine.
- `docs/engine/` - architecture, public API, rendering, audio, migration, and
  testing documentation.
- `scripts/` - release-evidence and golden-baseline utilities.
- `testdata/engine/` - compact baseline, golden, and review-collapsed test evidence.
- `tests/` - local regression suite; currently excluded from Git by repository
  policy.
- `.github/` and root manifests - CI and exact Python/Node toolchain authority.

## Knowledge Map

- `knowledge/playbooks/` - curated editorial skills and domain playbooks.
- `knowledge/workflows/content_creation/` - from-scratch creation workflows and templates.
- `knowledge/research/catalogs/` - source catalogs, official references, and asset guidance.
- `knowledge/research/lessons/` - distilled tutorial and project lessons.
- `knowledge/research/source_notes/` - local curated source notes; ignored.
- `knowledge/research/transcripts/` - local raw transcripts; ignored.
- `knowledge/techniques/<category>/` - reusable typed technique cards.
- `knowledge/presets/` - caption, color, motion, sound, and transition suggestions.
- `knowledge/styles/` - reusable editorial style grammars.
- `knowledge/quality/editorial_checklists/` - editorial and accessibility review rules.

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

The canonical execution layer is the installable `video_engine` package and its
`video-engine` CLI. Workflow preparation helpers still live in
`tools/video-use/helpers/`:
`knowledge_router.py`, `freesound_oauth.py`, `research_checker.py`,
`stock_footage_planner.py`, `voiceover_generator.py`, `caption_engine.py`,
`timeline_builder.py`, `sound_design_engine.py`, `motion_graphics_generator.py`,
`video_engine.py` (location-independent CLI launcher), and `qc_check.py`.

For from-scratch projects, run `knowledge_router.py` early so the agent scans
the repository's playbooks, lessons, technique cards, presets, styles, source
catalogs, and editorial checklists before writing project artifacts.

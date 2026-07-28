# Faceless Video Workflow

Use this for the request pattern:

> Create a faceless educational short about `<topic>`.

## Required Project Outputs

Every from-scratch faceless project must produce:

- `script.md`
- `visual_plan.md`
- `asset_list.md`
- `edit_decision_list.json`
- `preview.mp4`
- `qc_report.md`
- `final.mp4`

Supporting outputs should include:

- `knowledge_plan.md` and `knowledge_plan.json` after routing repo knowledge.
- `research_notes.md` when facts are researched.
- `asset_manifest.json` for every external/generated/data-derived asset.
- `voiceover_plan.md` or a voiceover section in `visual_plan.md`.
- `project.md` as the running production log.

## Workflow

1. Receive or choose topic.
2. Choose style pack and target platform.
3. Run `knowledge_router.py` to create `knowledge_plan.md/json`.
4. Research facts if needed.
5. Write `script.md`.
6. Build voiceover plan.
7. Build `visual_plan.md`.
8. Build `asset_list.md`.
9. Source, request, generate, render, or placeholder assets.
10. Build `edit_decision_list.json`.
11. Render `preview.mp4`.
12. Self-QC and write `qc_report.md`.
13. Fix issues.
14. Render `final.mp4`.

## Default Project Layout

```text
<project_dir>/
├── project.md
├── knowledge_plan.md
├── knowledge_plan.json
├── research_notes.md
├── script.md
├── voiceover_plan.md
├── visual_plan.md
├── asset_list.md
├── asset_manifest.json
├── edit_decision_list.json
├── assets/
│   ├── footage/
│   ├── images/
│   ├── generated/
│   ├── audio/
│   ├── maps/
│   └── charts/
├── animations/
├── captions/
├── renders/
├── preview.mp4
├── qc_report.md
└── final.mp4
```

## Editing Knowledge To Apply

Start from `knowledge_plan.md`. It is generated from:

- Story: `knowledge/playbooks/editing_taste_story_pacing.md`
- Retention: `knowledge/playbooks/short_form_retention.md`
- Visuals: `knowledge/playbooks/motion_graphics.md`
- Typography/captions: `knowledge/playbooks/video_typography.md`,
  `knowledge/playbooks/kinetic_captions.md`
- Sound: `knowledge/playbooks/sound_design.md`, `knowledge/playbooks/beat_sync.md`
- Color: `knowledge/playbooks/color_grading.md`
- QC: `knowledge/playbooks/editor_qc.md`
- Assets: `knowledge/research/catalogs/asset_resource_platforms.md`,
  `knowledge/quality/editorial_checklists/asset_manifest_qc.md`
- Matching extracted lessons, technique cards, presets, style packs, and QC
  checklists selected for the topic.

## Mode Rules

- If the user gives a topic and asks to create, treat that as permission to make
  a first complete draft unless external spend, paid assets, voice cloning, or
  factual/legal uncertainty requires confirmation.
- Use placeholders only when final rights-safe assets are unavailable; mark them
  in `asset_list.md` and `qc_report.md`.
- For factual videos, research before scripting.
- For opinion or fictional videos, label assumptions and creative invention.
- Render preview before final.

## QC

- The video can stand alone without existing footage.
- Every visual beat maps to a script beat.
- Every asset is sourced, generated, or requested with manifest status.
- Captions do not cover key visuals.
- Music/SFX do not mask voiceover.
- Final render has correct aspect, duration, fps, captions, mix, and rights notes.

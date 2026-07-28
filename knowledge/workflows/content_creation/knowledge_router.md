# Knowledge Router

## Purpose

Use this workflow before creating a faceless video from scratch. The repo has
many skills, technique cards, presets, style packs, source docs, lesson
summaries, and QC checklists. The agent should not rely on memory or manually
guess which files matter.

The knowledge router scans the reusable knowledge layers and creates a
project-local route:

- `knowledge_plan.md`
- `knowledge_plan.json`

These files tell every sub-agent which repo files to read for the current
topic, style, and format.

## When To Run

Run the router immediately after project setup and style-pack selection, before
scriptwriting or visual planning:

```bash
python tools/video-use/helpers/knowledge_router.py \
  --project-dir <project_dir> \
  --brief "Create a faceless educational short about <topic>" \
  --video-type faceless_educational_short
```

Run it again if the project changes direction, such as switching from a viral
short to a documentary explainer, adding a sports topic, changing the target
platform, or discovering the video needs a more factual research workflow.

After routing, immediately run the knowledge compiler:

```bash
python tools/video-use/helpers/knowledge_compiler.py \
  --project-dir <project_dir>
```

The compiler writes `creative_directive.md/json`. That directive is the bridge
between the knowledge base and the render system: it converts selected skills,
technique cards, presets, and QC rules into concrete caption, motion, sound,
color, transition, layout-safety, and timeline-layer requirements. Rich layers
must be safe to render: semantic caption chunks, bounded emphasis text,
caption suppression or repositioning over text-heavy scenes, and checks against
obscuring proof, diagrams, products, faces, or UI.

## What It Scans

The router scans these repo layers:

- `knowledge/workflows/content_creation/`
- `knowledge/research/catalogs/`
- `knowledge/research/lessons/`
- `knowledge/styles/`
- `knowledge/playbooks/`
- `knowledge/techniques/`
- `knowledge/presets/`
- `knowledge/quality/editorial_checklists/`

Raw transcripts are intentionally excluded. Use distilled lessons, structured
cards, presets, and checklists in final project work.

## Routing Layers

Every from-scratch video should load:

- Universal content creation docs.
- `knowledge/research/catalogs/asset_resource_platforms.md` before sourcing or generating assets.
- The selected or inferred style pack.
- Core editing skills for pacing, retention, captions, sound, motion, color,
  and QC.
- Genre-specific skills required by the style pack.
- Matching technique cards.
- Matching presets for captions, motion, transitions, sound, and color.
- Matching QC checklists.
- Relevant extracted lesson summaries when the topic or style overlaps.

## Sub-Agent Use

Every sub-agent should read `knowledge_plan.md` first, then load only the
selected files needed for its module:

- Research and script agents use the content creation docs, style pack, source
  docs, story/retention skills, and relevant lessons.
- Visual and asset agents use the style pack, asset guidance, visual planning
  docs, motion skills, technique cards, and presets.
- Caption agents use caption and typography skills/cards/presets.
- Sound agents use sound and beat-sync skills/cards/presets.
- Timeline and renderer agents use technique cards as implementation hints for
  layer timing, motion, captions, sound, and tool equivalents.
- QC agents use `qc_check.py`, selected QC checklists, and card-level `qc`
  rules.

Agents must not treat a project as complete just because `knowledge_plan.md`
exists. The selected knowledge must appear downstream in
`creative_directive.json`, `edit_decision_list.json` beat layers,
`captions/captions.json`, `sound_design_plan.json`, and `qc_report.json`.

Project artifacts should cite the most important knowledge files that shaped
them, especially when a style choice, asset rule, caption rule, or QC rule comes
from a specific skill, card, preset, or checklist.

## Output Contract

`knowledge_plan.md` is for agents to read quickly.

`knowledge_plan.json` is for tools and sub-agents that need structured routing.
It includes:

- The brief.
- The selected style pack.
- Detected domains.
- Inventory counts for every scanned knowledge layer.
- Selected files grouped by layer.
- A full inventory list of scanned files so the agent can verify coverage.

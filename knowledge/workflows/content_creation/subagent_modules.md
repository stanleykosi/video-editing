# Sub-Agent Module Map

These modules can be run as dedicated sub-agents. The important rule is that
each sub-agent must read and write project artifacts, not private memory.

## Why Sub-Agents Work Here

- Each module has a clear input file and output file.
- Asset and rights state lives in `asset_manifest.json`.
- Timeline state lives in `edit_decision_list.json`.
- The renderer and QC checker can validate work after other modules finish.

## Coordination Rules

- One sub-agent owns one module at a time.
- Sub-agents must not overwrite another module's artifact without reading it.
- If a helper writes JSON, keep IDs stable so later modules can reference them.
- The main agent should run the final render and QC gate, or explicitly assign
  those to one renderer/QC sub-agent after all upstream modules finish.

## Module Contracts

| Module | Primary Inputs | Primary Outputs | Helper |
| --- | --- | --- | --- |
| Knowledge router | brief, style pack, project docs | `knowledge_plan.md`, `knowledge_plan.json` | `knowledge_router.py` |
| Knowledge compiler / creative director | `knowledge_plan.json`, style pack, selected skills/cards/knowledge/presets/QC | `creative_directive.md`, `creative_directive.json` with caption/motion/sound/color/layout contracts | `knowledge_compiler.py` |
| Scriptwriter | `script_brief.md`, topic, style pack, research notes, relevant skills | `script_drafts/round_XX.md` | Dedicated writer subagent using `knowledge/playbooks/scriptwriting.md`, `knowledge/workflows/content_creation/scriptwriter.md`, and task-specific knowledge |
| Script critic | `script_brief.md`, current draft, relevant QC/story knowledge | `script_critique.md` with `PASS` or `FAIL` | Independent harsh critic subagent using `knowledge/workflows/content_creation/script_subagent_review_loop.md` |
| Research checker | `script.md`, `research_notes.md` | `research_check_report.md`, `.json` | `research_checker.py` |
| Voiceover generator | `script.md`, `.env` Deepgram key | `voiceover_plan.md`, `assets/audio/voiceover.mp3` | `voiceover_generator.py` |
| Asset finder/manager | `asset_list.md`, `stock_footage_plan.md` | downloaded/generated assets, `asset_manifest.json` | `find_assets.py`, `asset_manifest.py`, `generate_asset.py` |
| Stock footage planner | `visual_plan.md` | `stock_footage_plan.md`, `stock_footage_queries.json` | `stock_footage_planner.py` |
| Image generator/selector | `asset_list.md`, prompts, source plan | image assets, manifest entries | `generate_asset.py`, `find_assets.py` |
| Motion graphics generator | `edit_decision_list.json` | motion cards or rendered animation slots | `motion_graphics_generator.py`, Remotion/HyperFrames/Manim |
| Caption engine | `script.md`, later aligned VO timing | semantic phrase captions in `captions/master.srt`, rich render metadata in `captions/captions.json` | `caption_engine.py` |
| Sound design engine | `edit_decision_list.json` | `sound_design_plan.md`, `.json` | `sound_design_engine.py` |
| Timeline builder | `script.md`, `visual_plan.md`, manifest, `creative_directive.json` | compiled `edit_decision_list.json` with renderable layers | `timeline_builder.py` |
| Video renderer | canonical `project.json`, assets, rich captions, VO | `preview.mp4`, render manifest, `final.mp4` | `video-engine migrate faceless`, `video-engine render` |
| QC checker | all project artifacts | `qc_report.md`, `qc_report.json` | `qc_check.py` |

## Practical Sub-Agent Split

- Knowledge router agent: scans the repo's reusable knowledge and writes
  `knowledge_plan.md/json` before other modules begin.
- Knowledge compiler agent: turns selected knowledge into concrete caption,
  motion, sound, color, transition, layout-safety, and QC systems in
  `creative_directive.md/json`.
- Research agent: gathers sources, writes `research_notes.md`, runs
  `research_checker.py`.
- Script writer agent: writes draft rounds from the brief, research, and
  relevant script/story/recap skills.
- Script critic agent: independently reviews each draft, rejects weak hooks,
  generic summary, AI-sounding phrasing, unvisual lines, source mismatch, and
  poor rhythm; no script becomes `script.md` until the critic returns `PASS`.
- Visual/asset agent: writes `visual_plan.md`, `asset_list.md`, and runs
  `stock_footage_planner.py`.
- Asset agent: downloads/generates/registers assets.
- Audio agent: runs `voiceover_generator.py` and `sound_design_engine.py`.
- Caption agent: runs `caption_engine.py`, keeps captions as semantic phrase
  chunks, avoids dangling fragments, and later improves timing from VO.
- Timeline/motion agent: runs `timeline_builder.py` only after
  `creative_directive.json` exists; verifies every beat has compiled
  `camera_motion`, `caption_kinetic`, `emphasis_text`, `visual_motion_overlay`,
  `color_grade`, and `sound_cue` layers.
- Renderer/QC agent: migrates `edit_decision_list.json` with `video-engine
  migrate faceless`, renders a canonical preview, runs `video-engine qc`,
  verifies the generated contact sheet and rich-layer bounds, records the
  reviewed approval artifact, fixes failures, and renders final with
  `video-engine render final --approval`.

No module needs to be a single monolith. The only reason to keep a step in the
main agent is if it requires a taste decision, paid asset approval, credentials,
or final delivery judgment.

Every sub-agent should read `knowledge_plan.md` first and cite the most relevant
knowledge files it used in the artifact it writes.

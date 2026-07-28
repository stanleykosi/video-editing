# AGENTS.md

This file gives fresh agent instances the working context for `/home/stanley/video-editing`.

## What This Repo Is

This repo is a local AI video-editing agent system. It contains:

- A structured knowledge base for editing taste, techniques, presets, and QC.
- The canonical `video_engine` package in `src/video_engine/` and the
  `video-use` workflow/compatibility layer in `tools/video-use/`.
- Root Python/Node tooling for agent-driven video editing work.

The old `/home/stanley/Developer/video-use` path is kept as a symlink to
`/home/stanley/video-editing/tools/video-use` so existing skill references still work.

## Knowledge Base Layout

- `knowledge/README.md` - canonical knowledge map and routing index.
- `knowledge/research/catalogs/` - source lists, official docs, and asset guidance.
- `knowledge/research/transcripts/` - ignored local raw transcripts.
- `knowledge/research/source_notes/` - ignored local curated source notes.
- `knowledge/research/lessons/` - distilled lessons from tutorials and projects.
- `knowledge/techniques/` - reusable JSON technique cards grouped by category.
- `knowledge/playbooks/` - agent-readable editing playbooks grouped by domain.
- `knowledge/workflows/content_creation/` - from-scratch faceless video workflows and templates.
- `knowledge/styles/` - reusable style grammar and edit-language files.
- `knowledge/presets/` - caption, motion, transition, sound, and color preset suggestions.
- `knowledge/quality/editorial_checklists/` - checks the agent should run before calling an edit finished.
- `testdata/engine/` - compact immutable engine baseline and golden evidence.
- `src/video_engine/` - canonical editing engine, API, CLI, render backends, and QC.
- `tools/video-use/` - workflow helpers, compatibility delegates, and skill docs.

## Purpose

Convert video-editing tutorials and reference edits into structured AI-agent knowledge,
not raw transcript dumps.

Each tutorial should eventually become:

1. A lesson summary.
2. JSON technique cards.
3. Updates to skill files.
4. Preset suggestions.
5. QC checklist rules.

For from-scratch video creation, use `tools/video-use/SKILL.md`,
`knowledge/workflows/content_creation/`, `knowledge/styles/`, `knowledge/research/catalogs/asset_resource_platforms.md`, and
the relevant editing skills together. A complete from-scratch project must
produce `script.md`, `visual_plan.md`, `asset_list.md`,
`edit_decision_list.json`, `preview.mp4`, `qc_report.md`, and `final.mp4`.
The production helpers in `tools/video-use/helpers/` can be run by dedicated
sub-agents as long as they communicate through those project artifacts.
Run `tools/video-use/helpers/knowledge_router.py` early in from-scratch projects
to create `knowledge_plan.md/json` from the repository's playbooks, lessons,
techniques, presets, styles, source catalogs, and editorial checklists.

## Asset Resource Guidance

Asset sourcing guidance lives in:

- `knowledge/research/catalogs/asset_resource_platforms.md`

Fresh agents must read that source file before searching, generating,
downloading, or rendering stock footage/images, generated images, icons, maps,
charts, music, SFX, style packs, templates, or motion graphics. Do not duplicate
or summarize the platform list here.

API credentials, when available, live in the root `.env`. If a needed API key is
missing or blank, fall back to the no-key/direct public options listed in
`knowledge/research/catalogs/asset_resource_platforms.md`. Every external/generated/data asset used
in a project still needs a manifest entry with source URL, rights/license,
creator/attribution, download/generation date, and local path. Do not bypass
paywalls, login walls, watermarks, rate limits, or license restrictions.

Use the asset helpers in `tools/video-use/helpers/` for this workflow:
`find_assets.py`, `generate_asset.py`, `render_map.py`, `render_chart.py`, and
`asset_manifest.py`. For helpers that render image files, maps, or charts,
prefer `tools/video-use/.venv/bin/python` unless the root `.venv` has been synced
with the repo dependencies.

## Local Transcription Setup

This repo is moving to Deepgram for transcription. Do not download local
`faster-whisper` or OpenAI Whisper model checkpoints unless the user explicitly
asks for a local fallback.

Deepgram guidance:

- Prefer Deepgram for long audio/video files, especially multi-hour jobs where
  local CPU transcription would take too long.
- Keep outputs in the same two-file shape used by the local helper when
  possible: `<source_stem>.txt` and `<source_stem>.segments.txt`.
- After transcription, clean obvious ASR hallucinations, lyric/music blocks,
  bad proper nouns, and repeated filler before using the text as knowledge-base
  material.

Local fallback:

- The helper still exists at `tools/video-use/helpers/transcribe_local.py`, but
  the faster-whisper model cache was intentionally removed on 2026-05-28.
- If local transcription is explicitly requested again, using the helper will
  redownload model files under `.whisper-models/faster/`.
- OpenAI Whisper CLI/model checkpoints were removed; do not reinstall or use
  `whisper` unless the user explicitly asks.

## Default Posture

- Be proactive and practical.
- Inspect the workspace before acting.
- Preserve existing virtual environments and tooling files unless the user explicitly asks to change them.
- Keep raw tutorials, notes, lesson extraction, skill updates, presets, and QC checks in separate layers.
- Prefer structured, reusable agent knowledge over long unprocessed notes.
- Avoid adding media files, renders, caches, or generated edit artifacts unless a future task requires them.

## Professional Video Typography Defaults

- For captioned final renders, use ASS captions from the repo caption style system.
- ASS caption line breaks must be encoded correctly: the rendered `.ass` file should contain a single `\N` control sequence for a hard line break, never a double-escaped `\\N` or any visible slash/backslash marker in the burned video. Before final delivery, scan the ASS dialogue text and contact sheets for literal escape artifacts.
- For title cards, hook cards, chapter cards, stat cards, lower thirds, and major motion typography, use HyperFrames and/or Remotion. Do not use Pillow/PIL for final typography.
- Before compositing new or materially changed title/motion graphics into a final render, create approval frames/contact sheets and get user approval.
- Do not suppress captions under titles by default. Reposition or restyle captions first; suppression requires explicit user approval.
- For any title-heavy or caption-heavy edit, read `knowledge/playbooks/professional_title_graphics_pipeline.md`, `knowledge/playbooks/video_typography.md`, `knowledge/playbooks/kinetic_captions.md`, and `knowledge/quality/editorial_checklists/video_typography_qc.md`.

## Recap And Commentary Alignment Defaults

- For narration-driven recap/commentary edits, when the narration names a character, person, place, object, product, UI element, proof point, or event, the rendered picture must already show the matching subject at the viewer-facing timestamp.
- Do not rely only on exact EDL boundaries. If a player shows `0:42`, inspect what the viewer sees at `0:42`, not only what starts at a later sub-second boundary such as `42.765s`.
- Use a small early visual handoff buffer for important named subjects, verify source ranges by looking at frames, and create timestamped contact sheets from the rendered preview/final around sensitive handoffs.
- If the user reports a timestamp, inspect at least 0.5s before through 1.0s after the reported window, then verify the promoted `final.mp4`, not only the preview.
- Read `knowledge/techniques/qc/qc_narration_visual_character_alignment_001.json`, `knowledge/playbooks/editor_qc.md`, and `knowledge/quality/editorial_checklists/story_retention_accessibility_qc.md` for this failure mode.

## Movie Recap Defaults

- Any request for a movie recap, movie explainer, anime recap, episode recap, or narration-over-movie-source edit must load `knowledge/playbooks/movie_recap_workflow.md`, `knowledge/quality/editorial_checklists/movie_recap_qc.md`, `knowledge/research/lessons/movie_recap_short_transformed_scene_workflow.md`, and the movie recap technique cards before planning.
- Default to narration-first, paragraph-sized recap shorts. Each paragraph gets a matching source scene hint, visually verified source range, muted movie audio, and its own export unless the user asks for a longer combined video.
- Do not use long continuous movie excerpts by default. Transform verified scene ranges with short fragments, alternate deletion/compression, optional alternating mirror/flip where it stays readable, and speed changes only when needed to fit narration.
- Treat generated scene timestamps as hints only. Find and verify the actual movie frames before cutting.
- Always run rendered-output spot checks for scene-to-narration match, source-audio mute, fragment transformation, aspect ratio, and the promoted final file.

## Scriptwriting Subagent Defaults

- Any task that creates or substantially rewrites a script, voiceover, narration, recap paragraph, explainer, ad read, hook, or storyboard script must use `knowledge/workflows/content_creation/script_subagent_review_loop.md`.
- Spawn an independent scriptwriter subagent and a separate harsh script critic subagent whenever subagents are available. The writer drafts from the task brief and relevant skills; the critic judges the draft independently against the task, source material, audience, platform, and human writing standards.
- The script is not final until the critic returns `PASS`. If the critic returns `FAIL`, the writer revises from the critique and the loop repeats. If the same issue blocks three rounds, stop and ask the user instead of lowering the standard.
- The critic must screen for weak hooks, generic summary, plot/source mismatch, lines that cannot be visualized, poor rhythm, and AI-sounding patterns such as "it's not X, it's Y", "if not X then Y", "what happens next changes everything", "this is where things get interesting", and similar model-script phrasing.
- Store the loop artifacts in the project folder: `script_brief.md`, `script_drafts/`, `script_critique.md`, `script_revision_log.md`, and the critic-approved `script.md`.

## First Steps In A New Session

1. Read this `AGENTS.md`.
2. Inspect the workspace with `rg --files -uu`, `find`, or `ls`.
3. Determine whether the task is knowledge-base maintenance or actual video editing work.
4. If the task is tutorial ingestion, follow `knowledge/CONTRIBUTING.md`.
5. If the task is editing existing footage, use Mode 1 in `tools/video-use/SKILL.md`.
6. If the task is creating a faceless video from a topic or brief, use Mode 2 in `tools/video-use/SKILL.md` and the docs in `knowledge/workflows/content_creation/`.
7. For from-scratch work, run or follow `knowledge/workflows/content_creation/knowledge_router.md` before scriptwriting so the project has a current `knowledge_plan.md/json`.
8. For any script creation/rewrite, run `knowledge/workflows/content_creation/script_subagent_review_loop.md` before accepting `script.md`.
9. Keep outputs in a clearly named project folder.
10. Verify changes before reporting completion.

## Skills Available To Future Agents

Use skills when the task matches their purpose. Read the skill file before using it.

- `video-use`
  Path: `/home/stanley/video-editing/tools/video-use/SKILL.md`
  Use for video editing, faceless video creation from scratch, transcription, script-to-timeline planning, asset sourcing/generation, cutting, montage building, grading, subtitles, overlays, preview/final rendering, QC, and project logs.

- `still_image_cinematic_compositing`
  Path: `/home/stanley/video-editing/knowledge/playbooks/still_image_cinematic_compositing.md`
  Use for turning still images into cinematic moving scenes with motivated overlays, masks, local light, blend modes, and unified grading.

- `capcut_pro_compositing_effects`
  Path: `/home/stanley/video-editing/knowledge/playbooks/capcut_pro_compositing_effects.md`
  Use for CapCut subject sandwiches, chroma-key text portals, tracked stickers, slide-on photo stacks, chapter cards, PiP borders, split-mask illusions, clone effects, and green-screen VFX.

- `movie_recap_workflow`
  Path: `/home/stanley/video-editing/knowledge/playbooks/movie_recap_workflow.md`
  Use for movie recaps, movie explainers, anime recaps, episode recaps, narration-led scene summaries, paragraph-based recap shorts, muted-source movie edits, and transformed movie scene fragments.

- `scriptwriting`
  Path: `/home/stanley/video-editing/knowledge/playbooks/scriptwriting.md`
  Use for improving scripts, voiceover narration, storyboards, hooks, structure, tone, visual notes, motion notes, and duration planning. For movie recaps, combine this with `movie_recap_workflow` and the repo storytelling knowledge; do not force product-video CTAs into recap scripts unless the user asks for them.

- `professional_title_graphics_pipeline`
  Path: `/home/stanley/video-editing/knowledge/playbooks/professional_title_graphics_pipeline.md`
  Use for title cards, hook cards, lower thirds, stat cards, motion-typography approval frames, ASS caption continuity, and enforcing HyperFrames/Remotion instead of Pillow/PIL for final typography.

- `manim-video`
  Path: `/home/stanley/video-editing/tools/video-use/vendor/manim-video/SKILL.md`
  Use for mathematical or technical animations.

- `imagegen`
  Path: `/home/stanley/.codex/skills/.system/imagegen/SKILL.md`
  Use for generated or edited raster images.

- `openai-docs`
  Path: `/home/stanley/.codex/skills/.system/openai-docs/SKILL.md`
  Use for current OpenAI API/product docs and cite official sources.

- `skill-creator`
  Path: `/home/stanley/.codex/skills/.system/skill-creator/SKILL.md`
  Use to create or update Codex skills.

- `skill-installer`
  Path: `/home/stanley/.codex/skills/.system/skill-installer/SKILL.md`
  Use to install Codex skills.

- `plugin-creator`
  Path: `/home/stanley/.codex/skills/.system/plugin-creator/SKILL.md`
  Use to create local Codex plugins.

- Vercel plugin skills
  Use only for Vercel, Next.js, AI SDK, deployment, auth, storage, or related web-app tasks.

## File Rules

- Use `rg` or `rg --files` for search.
- Use `apply_patch` for manual file edits.
- Do not modify `.venv/` or `tools/video-use/.venv/` unless explicitly asked.
- Do not rely on `.git/` unless confirmed working; this workspace may not behave like a normal repository.
- Preserve user-created changes.

## Response Style

While working, provide short progress updates. At the end, report:

- What changed.
- Which files or folders were produced.
- What verification was run.
- Any remaining limitation or risk.

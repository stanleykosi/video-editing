---
name: video-use
description: Edit existing footage or create faceless videos from scratch by conversation. Transcribe, cut, write scripts, plan visuals, source/generate assets, create voiceover plans, build timelines, animate overlays, burn subtitles, QC, and render previews/finals. Production-correctness and asset-rights rules are hard; everything else is artistic freedom.
---

# Video Use

## Principle

1. **LLM reasons from raw transcript + on-demand visuals.** The only derived artifact that earns its keep is a packed phrase-level transcript (`takes_packed.md`). Everything else — filler tagging, retake detection, shot classification, emphasis scoring — you derive at decision time.
2. **Audio is primary, visuals follow.** Cut candidates come from speech boundaries and silence gaps. Drill into visuals only at decision points.
3. **Ask → confirm → execute → iterate → persist.** Never touch the cut until the user has confirmed the strategy in plain English.
4. **Generalize.** Do not assume what kind of video this is. Look at the material, ask the user, then edit.
5. **Artistic freedom is the default.** Every specific value, preset, font, color, duration, pitch structure, and technique in this document is a *worked example* from one proven video — not a mandate. Read them to understand what's possible and why each worked. Then make your own taste calls based on what the material actually is and what the user actually wants. **The only things you MUST do are in the Hard Rules section below.** Everything else is yours.
6. **Invent freely, using the professional render path.** If the material calls for a technique not described here — split-screen, picture-in-picture, lower-third identity cards, reaction cuts, speed ramps, freeze frames, crossfades, match cuts, L-cuts, J-cuts, speed ramps over breath, whatever — build it. Final captions use ASS subtitles. Final title cards, hook cards, chapter cards, lower thirds, and designed text overlays use HyperFrames and/or Remotion. Pillow/PIL is only acceptable for diagnostics, masks, temporary placeholders, contact sheets, or non-typographic utility images; it is not an acceptable final typography engine unless the user explicitly approves that exception.
7. **Verify your own output before showing it to the user.** If you wouldn't ship it, don't present it.
8. **Two production modes are supported.**
   - **Mode 1: Edit existing footage.** Transcribe source footage, build an EDL, render an edited video.
   - **Mode 2: Create from scratch.** Start from a topic or brief, research if needed, write the script, plan voiceover, plan/source/generate assets, build the timeline, animate, caption, sound-design, render, QC, and final.
9. **Root knowledge must guide the edit.** Use the repo root knowledge base, not only this skill. For existing-footage clipping, load the relevant root `skills/`, `technique_cards/`, `presets/`, `style_packs/`, and `qc_checklists/` before proposing the edit strategy. For from-scratch work, use root `style_packs/*.json` and `content_creation/*.md`, then apply the editing knowledge in root `skills/`, `technique_cards/`, `presets/`, and `qc_checklists/`.
10. **Knowledge must compile into the edit.** For from-scratch videos, routed knowledge is not enough. Every relevant selected skill, technique card, preset, and QC rule must be converted into `creative_directive.json`, then into concrete timeline layers, caption metadata, sound cues, color rules, transitions, and render/QC checks. If a selected technique is not applicable, record why instead of silently ignoring it.

## Hard Rules (production correctness — non-negotiable)

These are the things where deviation produces silent failures or broken output. They are not taste, they are correctness. Memorize them.

1. **Subtitles are applied LAST in the filter chain**, after every overlay. Otherwise overlays hide captions. Silent failure.
2. **Per-segment extract → lossless `-c copy` concat**, not single-pass filtergraph. Otherwise you double-encode every segment when overlays are added.
3. **30ms audio fades at every segment boundary** (`afade=t=in:st=0:d=0.03,afade=t=out:st={dur-0.03}:d=0.03`). Otherwise audible pops at every cut.
4. **Overlays use `setpts=PTS-STARTPTS+T/TB`** to shift the overlay's frame 0 to its window start. Otherwise you see the middle of the animation during the overlay window.
5. **Master SRT uses output-timeline offsets**: `output_time = word.start - segment_start + segment_offset`. Otherwise captions misalign after segment concat.
6. **Never cut inside a word.** Snap every cut edge to a word boundary from the Scribe transcript.
7. **Pad every cut edge.** Working window: 30–200ms. Scribe timestamps drift 50–100ms — padding absorbs the drift. Tighter for fast-paced, looser for cinematic.
8. **Word-level verbatim ASR only.** Never SRT/phrase mode (loses sub-second gap data). Never normalized fillers (loses editorial signal).
9. **Cache transcripts per source.** Never re-transcribe unless the source file itself changed.
10. **Parallel sub-agents for multiple animations.** Never sequential. Spawn N at once via the `Agent` tool; total wall time ≈ slowest one.
11. **Strategy confirmation before editing existing footage.** Never touch the cut until the user has approved the plain-English plan.
12. **For create-from-scratch requests, the user's "create/make/build this video" request counts as approval for a first complete draft** unless the plan requires paid assets, unclear rights, voice cloning/impersonation, external spend, sensitive factual claims, or a major creative ambiguity. In those cases, ask before proceeding.
13. **All existing-footage session outputs go in `<videos_dir>/edit/`.** Never write inside the `video-use/` project directory.
14. **All create-from-scratch session outputs go in a dedicated project folder.** Never scatter generated assets, renders, manifests, or timelines across the repo root.
15. **Every from-scratch video must produce the required artifact set:** `script.md`, `visual_plan.md`, `asset_list.md`, `edit_decision_list.json`, `preview.mp4`, `qc_report.md`, and `final.mp4`.
16. **Every external, generated, rendered, map, chart, music, SFX, font, or template asset used in a from-scratch project must be logged in `asset_manifest.json`.** Do not use watermarked previews in final exports.
17. **No thin from-scratch renders.** A create-from-scratch project must include `knowledge_plan.json`, `creative_directive.json`, rich `captions/captions.json`, and a timeline where every beat has compiled `camera_motion`, `caption_kinetic`, `emphasis_text`, `visual_motion_overlay`, `color_grade`, and `sound_cue` layers. QC fails if the output is only stitched clips plus plain subtitles.
18. **Rich layers must still be controlled.** Caption and emphasis text must be semantic phrase chunks, fitted to vertical safe-width boxes, and repositioned when scene text competes with them. Never ship giant cropped text, dangling two-word fragments, or effect layers that obscure the proof/diagram/product.
19. **Existing-footage final renders require visual QC.** For clipping/edited-source work, render a preview, run `visual_qc.py --video <edit>/preview.mp4 --edl <edit>/edl.json`, view every generated contact sheet, fix/reclip/reframe/mask any visual blockers, then mark the report with `visual_qc.py --mark-reviewed ... --status pass`. `render.py` blocks normal final renders until `<edit>/visual_qc/visual_qc_report.json` is agent-reviewed and passed. Use `--skip-visual-qc` only for diagnostics, never for delivery.
20. **ASS captions are mandatory for captioned final renders.** Build captions through the ASS caption system and caption presets, not image-text overlays. Do not hardcode one font or one style; choose or adapt a style from the repo's caption presets and the active creative brief. ASS text escaping is part of caption correctness: a hard line break in the written `.ass` file is a single `\N` control sequence. If the file contains double-escaped `\\N` in Dialogue text, or if the burned video shows slash/backslash artifacts, fix captions and rerender before delivery.
21. **HyperFrames and Remotion are the default title/motion tools.** Use HyperFrames for title cards, hook cards, chapter cards, stat cards, and lower thirds. Use Remotion for polished motion graphics, animated typography, reusable components, and graphics that need precise timing. Do not use Pillow/PIL for final title or caption design.
22. **Title designs require approval before final compositing.** For any newly designed or materially changed title card, hook card, chapter card, stat card, lower third, or major motion graphic, render still approval frames/contact sheets first and get the user's approval before continuing to final render.
23. **Do not blanket-suppress captions under titles.** Captions should continue through title overlays by default, repositioning or restyling when needed. Only suppress captions for a title section when the user approves it and the title itself preserves the spoken meaning clearly.
24. **Existing-footage clipping requires a root-knowledge pass.** Before strategy for a nontrivial clip, read or route the relevant root knowledge layers: editing taste, short-form retention, typography/captions, motion graphics, sound design, color, platform QC, caption presets, motion/transition presets, and applicable technique cards. Record what was used in `<edit>/project.md` or `<edit>/knowledge_notes.md`.
25. **Narration-to-visual alignment is mandatory for recap/commentary edits.** When narration names a person, character, place, object, product, UI element, proof point, or scene event, the matching visual must already be visible at the viewer-facing timestamp. Do not rely only on exact sub-second EDL boundaries; if a player shows `0:42`, inspect what the viewer sees at `0:42`, not only what starts at `42.765s`. Use a small early visual handoff buffer for important named entities, and prove the result with timestamped contact sheets from the rendered preview/final.
26. **Movie recap requests must load the movie recap workflow.** For any movie recap, movie explainer, anime recap, episode recap, or narration-over-movie-source edit, read `skills/movie_recap_workflow.md`, `extracted_lessons/movie_recap_short_transformed_scene_workflow.md`, `technique_cards/movie_recap_paragraph_scene_workflow_001.json`, `technique_cards/movie_recap_chop_delete_flip_speed_transform_001.json`, and `qc_checklists/movie_recap_qc.md` before planning. Default to paragraph-sized narration-led shorts with muted source audio, visually verified scene ranges, transformed short fragments, and rendered-output spot checks.
27. **Scripts require independent writer/critic subagents.** For any new or substantially rewritten script, narration, recap paragraph, hook, ad read, explainer, or storyboard script, run `content_creation/script_subagent_review_loop.md`: spawn a dedicated scriptwriter subagent and a separate harsh critic subagent. The script is not accepted until the critic returns `PASS`; writer revises on `FAIL`.

Everything else in this document is a worked example. Deviate whenever the material calls for it.

## Directory layout

The skill lives in `video-use/`. User footage lives wherever they put it.
Existing-footage outputs go into `<videos_dir>/edit/`.

```
<videos_dir>/
├── <source files, untouched>
└── edit/
    ├── project.md               ← memory; appended every session
    ├── takes_packed.md          ← phrase-level transcripts, the LLM's primary reading view
    ├── edl.json                 ← cut decisions
    ├── transcripts/<name>.json  ← cached raw Scribe JSON
    ├── animations/slot_<id>/    ← per-animation source + render + reasoning
    ├── clips_graded/            ← per-segment extracts with grade + fades
    ├── master.srt               ← output-timeline subtitles
    ├── downloads/               ← yt-dlp outputs
    ├── verify/                  ← debug frames / timeline PNGs
    ├── visual_qc/               ← contact sheets, OCR report, blocked ranges
    ├── preview.mp4
    └── final.mp4
```

From-scratch outputs go into a dedicated project folder, either user-specified or
created by the agent with a clear slug.

```
<project_dir>/
├── project.md
├── knowledge_plan.md              ← selected repo knowledge for this project
├── knowledge_plan.json            ← structured route for helpers/sub-agents
├── research_notes.md              ← when factual research is needed
├── script.md                      ← required
├── voiceover_plan.md              ← optional if included in visual_plan.md
├── visual_plan.md                 ← required
├── asset_list.md                  ← required
├── asset_manifest.json            ← required when assets are used
├── edit_decision_list.json        ← required
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
├── preview.mp4                    ← required
├── qc_report.md                   ← required
└── final.mp4                      ← required
```

## Setup

First-time install lives in `install.md` (clone, deps, ffmpeg, skill registration, API key). Don't re-run it every session; on cold start just verify:

- `DEEPGRAM_API_KEY` resolves when generating from-scratch voiceover. It can live in the root repo `.env` or the process environment. `voiceover_generator.py` uses Deepgram's REST Speak API with `DEEPGRAM_TTS_MODEL` defaulting to `aura-2-thalia-en`.
- `ELEVENLABS_API_KEY` may still be needed by the older existing-footage transcription helper until transcription is fully migrated.
- `ffmpeg` + `ffprobe` on PATH.
- Python deps installed (`uv sync` or `pip install -e .` inside the repo).
- Node.js + npm available if the session needs HyperFrames or Remotion slots. HyperFrames currently requires Node.js 22+.
- `tesseract-ocr` on PATH for OCR-assisted visual QC; Python deps include `pytesseract`.
- `yt-dlp` for source ingestion. Prefer the root env package via `uv run yt-dlp` or `.venv/bin/yt-dlp` when the system CLI is older.
- HyperFrames, Remotion, Manim installed only on first use.
- First-use animation setup happens inside the slot directory, never at the video-use repo root. HyperFrames can be invoked with `npx --yes hyperframes ...`; Remotion can be scaffolded with `npx create-video@latest` or installed as a project-local dependency before using its `remotion render` command.
- Before designing title cards or polished motion graphics, verify HyperFrames and/or Remotion are available. If they are missing, install or request installation instead of falling back to Pillow/PIL for final design.
- This skill vendors `skills/manim-video/`. Read its SKILL.md when building a Manim slot.

Helpers (`helpers/transcribe.py`, `helpers/render.py`, etc.) live alongside this SKILL.md. Resolve their paths relative to the directory containing this file — the skill is typically symlinked at `~/.claude/skills/video-use/` or `~/.codex/skills/video-use/`.

## Helpers

- **`transcribe.py <video>`** — single-file Scribe call. `--num-speakers N` optional. Cached.
- **`transcribe_batch.py <videos_dir>`** — 4-worker parallel transcription. Use for multi-take.
- **`pack_transcripts.py --edit-dir <dir>`** — `transcripts/*.json` → `takes_packed.md` (phrase-level, break on silence ≥ 0.5s).
- **`timeline_view.py <video> <start> <end>`** — filmstrip + waveform PNG. On-demand visual drill-down. **Not a scan tool** — use it at decision points, not constantly.
- **`visual_qc.py --edl <edit>/edl.json --source-preflight`** — scan proposed EDL source ranges, generate contact sheets/OCR flags, run lightweight OpenCV face/safe-area checks, and write `source_visual_qc_report.md/json` plus `source_blocked_ranges.json` when source overlays, banners, caption-zone face collisions, or crop-edge risks are detected.
- **`visual_qc.py --video <edit>/preview.mp4 --edl <edit>/edl.json`** — pre-final visual QC gate for rendered previews. The contact sheets draw a caption safe zone and detected face boxes. The agent/LLM must view every contact sheet, then mark the report with `--mark-reviewed <edit>/visual_qc/visual_qc_report.json --status pass|needs_reclip|needs_reframe|needs_mask|blocked`.
- **`render.py <edl.json> -o <out>`** — per-segment extract → concat → overlays (PTS-shifted) → subtitles LAST. Final renders default to the highest source resolution used by the EDL, with anything below 1080p upscaled to a 1080-pixel short edge; `--resolution 3840x2160` can force a delivery target, while `--preview`/`--draft` intentionally render lighter QC copies. `--build-subtitles` generates styled `master.ass` captions inline from `presets/captions/ass_caption_styles.json`; use this ASS path for all captioned final renders.
- **`grade.py <in> -o <out>`** — ffmpeg filter chain grade. Presets + `--filter '<raw>'` for custom.
- **`find_assets.py <query>`** — search/download rights-trackable assets from agent-friendly sources. Use `--project-dir <project_dir>` so downloads enter the project manifest.
- **`freesound_oauth.py auth-url|exchange|refresh`** — create Freesound OAuth access/refresh tokens for original-quality Freesound downloads. Freesound's client secret is also the token-auth API key.
- **`asset_manifest.py init|add|list|check <project_dir>`** — create, update, inspect, and validate `asset_manifest.json`.
- **`generate_asset.py --prompt ... --project-dir <project_dir>`** — create placeholder or AI-generated visual assets and log provenance.
- **`render_map.py ... --project-dir <project_dir>`** — render map plates with attribution and manifest entries.
- **`render_chart.py ... --project-dir <project_dir>`** — render chart plates from CSV/API data and log data provenance.
- **`knowledge_router.py --project-dir <project_dir> --brief ...`** — scan root knowledge layers and write `knowledge_plan.md/json` for the project.
- **`knowledge_compiler.py --project-dir <project_dir>`** — compile routed knowledge into `creative_directive.md/json`, including renderable caption, motion, sound, color, transition, layout, and QC contracts.
- **`research_checker.py --project-dir <project_dir>`** — validate claim/source coverage and optionally check URL reachability.
- **`stock_footage_planner.py --project-dir <project_dir>`** — convert `visual_plan.md` beats into stock-footage/media search queries.
- **`voiceover_generator.py --project-dir <project_dir>`** — generate Deepgram Aura TTS voiceover and register it in the manifest.
- **`caption_engine.py --project-dir <project_dir>`** — create semantic phrase SRT/JSON captions from `script.md`, including animation/source metadata and render-layer layout rules.
- **`timeline_builder.py --project-dir <project_dir>`** — build `edit_decision_list.json` from script, visual plan, style pack, and manifest assets.
- **`sound_design_engine.py --project-dir <project_dir>`** — create `sound_design_plan.md/json` from the timeline.
- **`motion_graphics_generator.py --project-dir <project_dir>`** — legacy/simple local motion-card PNG helper for non-final placeholders or non-typographic plates. Do not use it for final title, caption, hook-card, chapter-card, or lower-third typography; use HyperFrames, Remotion, and ASS instead.
- **`faceless_renderer.py --project-dir <project_dir> --preview`** — render a knowledge-driven from-scratch preview/final from `edit_decision_list.json`, including compiled motion/color treatment and a final rich overlay pass for kinetic captions, emphasis text, glow/highlight effects, progress accents, and diagram callouts.
- **`qc_check.py --project-dir <project_dir>`** — run artifact, timeline, manifest, and media probe checks into `qc_report.md/json`.

For animations, create `<edit>/animations/slot_<id>/` with `Bash` and spawn a sub-agent via the `Agent` tool.

## Mode 1: Edit Existing Footage

1. **Inventory.** `ffprobe` every source. `transcribe_batch.py` on the directory. `pack_transcripts.py` to produce `takes_packed.md`. Sample one or two `timeline_view`s for a visual first impression.
2. **Pre-scan for problems.** One pass over `takes_packed.md` to note verbal slips, obvious mis-speaks, or phrasings to avoid. Plain list, feed into the editor brief.
3. **Root knowledge pass.** Before strategy, search and read the relevant root knowledge layers for the actual job. For short-form clips, this usually includes `skills/editing_taste_story_pacing.md`, `skills/short_form_retention.md`, `skills/kinetic_captions.md`, `skills/video_typography.md`, `skills/professional_title_graphics_pipeline.md`, `skills/motion_graphics.md`, `skills/sound_design.md`, `skills/beat_sync.md`, `skills/color_grading.md`, `skills/editor_qc.md`, caption/motion/transition presets, matching technique cards, and relevant QC checklists. For movie recap/explainer work, also load `skills/movie_recap_workflow.md`, `qc_checklists/movie_recap_qc.md`, and the movie recap technique cards before strategy. Use `knowledge_router.py --project-dir <edit> --brief "<clip brief>" --video-type existing-footage-short` when practical; otherwise create a concise `<edit>/knowledge_notes.md` listing selected root skills/cards/presets/QC and how they will affect the edit.
4. **Converse.** Describe what you see in plain English. Ask questions *shaped by the material*. Collect: content type, target length/aspect, aesthetic/brand direction, pacing feel, must-preserve moments, must-cut moments, animation and grade preferences, subtitle needs. Do not use a fixed checklist — the right questions are different every time.
5. **Propose strategy.** 4–8 sentences: shape, take choices, cut direction, root knowledge/preset choices, animation plan, title/motion graphics tool path, grade direction, ASS caption style, length estimate. **Wait for confirmation.**
6. **Execute.** Produce `edl.json` via the editor sub-agent brief. Drill into `timeline_view` at ambiguous moments. For recap/commentary edits, label named-entity narration beats in the EDL `reason` or `voiceover_window` fields and verify source ranges visually before assigning them. Important named-character/person/object handoffs should start slightly before the viewer-facing timestamp so a rounded player time does not show the previous subject. Run `visual_qc.py --edl <edit>/edl.json --source-preflight`, view the generated contact sheets, and remove/reclip/reframe any source ranges with description overlays, lower-thirds, social UI, watermarks, wrong-character/wrong-subject carryover, or other visual blockers before rendering. Build title cards and lower thirds with HyperFrames, polished motion graphics with Remotion, and captions with ASS. Render title/motion approval frames before compositing; wait for user approval when designs are new or materially changed. Apply grade per-segment. Compose via `render.py`.
7. **Preview.** `render.py --preview`.
8. **Visual QC gate (before showing the user or rendering final).** Run `visual_qc.py --video <edit>/preview.mp4 --edl <edit>/edl.json`. By default it uses CPU-only OpenCV Haar detection to draw face boxes and flag lower-caption safe-zone collisions or crop-edge faces; use `--caption-zone center` for centered caption designs or `--caption-zone none` only when a user-approved no-caption/suppression window exists. The agent/LLM must view every PNG listed under `<edit>/visual_qc/contact_sheets/` and check for source overlays, description text, caption collisions, bad crops, blocked faces/products/proof, jump frames, flashes, unreadable cut moments, unapproved title frames, caption/title conflicts, and narration/visual mismatches. For recap/commentary edits, create or inspect timestamped spot sheets around each sensitive named-entity handoff and around any user-reported timestamp; include at least 0.5s before through 1.0s after the window so rounded playback seconds are checked. If anything fails: fix the EDL/crop/captions/overlays → re-render preview → rerun visual QC. After a clean review, mark the report:

   ```
   python helpers/visual_qc.py --mark-reviewed <edit>/visual_qc/visual_qc_report.json --status pass --notes "reviewed contact sheets"
   ```

9. **Self-eval closeups.** Use `timeline_view` on the **rendered output** (not the sources) at every cut boundary (±1.5s window) when the contact sheet suggests a cut needs closer inspection. Check each image for:
   - Visual discontinuity / flash / jump at the cut
   - Waveform spike at the boundary (audio pop that slipped past the 30ms fade)
   - Subtitle hidden behind an overlay (Rule 1 violation)
   - Overlay misaligned or showing wrong frames (Rule 4 violation)

   Also sample first 2s, last 2s, and 2–3 mid-points when the contact sheets are not enough — check grade consistency, subtitle readability, overall coherence. Run `ffprobe` on the output to verify duration matches the EDL expectation.

   For narration-driven recap/commentary edits, add a dedicated **character/narration alignment pass**: list every named person, character, place, object, product, UI element, or proof point; sample the rendered output at the spoken-name timestamp and the rounded viewer-facing second; confirm the correct visual is already present. If the user reports `0:42-0:51`, inspect at least `0:41.5-0:52` and verify the promoted `final.mp4`, not only the preview.

   If anything fails: fix → re-render → re-eval. **Cap at 3 self-eval passes** — if issues remain after 3, flag them to the user rather than looping forever. Only present the preview once the self-eval passes.
10. **Iterate + persist.** Natural-language feedback, re-plan, re-render. Never re-transcribe. Final render only after `visual_qc_report.json` is passed. Append selected root knowledge, technique cards, presets, QC outcomes, and final decisions to `project.md`.

## Mode 2: Create From Scratch

Use this when the user says something like:

> Create a faceless educational short about `<topic>`.

The agent owns the full production path from topic to final render.

### Knowledge To Load

Before planning, read the relevant root knowledge:

- `content_creation/knowledge_router.md`, then create or refresh
  `<project_dir>/knowledge_plan.md` with `knowledge_router.py`
- `content_creation/faceless_video_workflow.md`
- `content_creation/scriptwriter.md`
- `content_creation/script_subagent_review_loop.md`
- `content_creation/research_to_script.md` when facts are needed
- `content_creation/visual_planner.md`
- `content_creation/asset_planner.md`
- `content_creation/voiceover_planner.md`
- `content_creation/youtube_storytelling_workflow.md` for story-led formats
- `sources/asset_resource_platforms.md`
- Relevant style pack from root `style_packs/*.json`
- Relevant skills, extracted lessons, technique cards, presets, and QC
  checklists selected by `knowledge_plan.md`, especially:
  - `editing_taste_story_pacing.md`
  - `short_form_retention.md`
  - `kinetic_captions.md`
  - `video_typography.md`
  - `sound_design.md`
  - `beat_sync.md`
  - `motion_graphics.md`
  - `color_grading.md`
  - `editor_qc.md`
  - `movie_recap_workflow.md` and `movie_recap_qc.md` whenever the brief is a
    movie recap, movie explainer, anime recap, episode recap, or
    narration-over-movie-source video

### From-Scratch Process

1. **Project setup.** Create or use a dedicated `<project_dir>`. Start
   `project.md`, initialize `asset_manifest.json`, and choose the style pack.
2. **Knowledge route.** Run `knowledge_router.py --project-dir <project_dir>
   --brief "<user brief>" --video-type <style_or_format>` to create
   `knowledge_plan.md/json`. Sub-agents read this before their module-specific
   files so skills, technique cards, presets, lessons, and QC rules are not
   missed.
3. **Knowledge compiler.** Run `knowledge_compiler.py --project-dir
   <project_dir>` immediately after routing. This creates
   `creative_directive.md/json`, the contract that turns the selected knowledge
   into renderable caption, motion, sound, color, transition, and QC systems.
   Do not proceed to timeline/render without this artifact.
4. **Topic and promise.** If the user gave only a topic, infer a focused promise,
   audience, duration, aspect ratio, and platform from the chosen style pack.
5. **Research if needed.** For factual videos, create `research_notes.md`, track
   claims and source URLs, avoid unsupported certainty, then run
   `research_checker.py --project-dir <project_dir>`.
6. **Write script through writer/critic subagents.** Follow
   `content_creation/script_subagent_review_loop.md`. Create `script_brief.md`,
   spawn a dedicated writer subagent for drafts, spawn a separate harsh critic
   subagent for pass/fail review, iterate until critic `PASS`, then copy only
   the approved script into `script.md` from
   `content_creation/templates/script_template.md`. The final script must be
   voiceover-ready and beat-tagged.
7. **Voiceover plan.** Create `voiceover_plan.md` or a voiceover section in
   `visual_plan.md`: tone, WPM, emphasis, pauses, pronunciation, and cue words.
8. **Visual plan.** Create `visual_plan.md` from
   `content_creation/templates/visual_plan_template.md`. Every script beat gets
   a visual job, primary visual, motion treatment, caption treatment, and QC risk.
9. **Asset plan.** Create `asset_list.md` from
   `content_creation/templates/asset_list_template.md`. Decide what to source,
   generate, render, or request from the user. Run
   `stock_footage_planner.py --project-dir <project_dir>` when stock footage or
   public media is needed.
10. **Source/generate/render assets.** Use the asset helpers and manifest every
   final asset. Use placeholders only when necessary and mark them clearly.
11. **Build compiled timeline.** Run `timeline_builder.py --project-dir
   <project_dir>` after `creative_directive.json` exists. The resulting
   `edit_decision_list.json` must include script beats, assets, voiceover,
   kinetic caption layers, emphasis text, camera motion, visual overlays, color,
   SFX, transitions, source technique references, and render settings.
12. **Generate voiceover and captions.** Use `voiceover_generator.py` for
    Deepgram Aura narration and `caption_engine.py` for draft captions. For
    final captions, replace draft timing with aligned/transcribed timing when
    available. `caption_engine.py` must output rich `captions/captions.json`,
    not only `master.srt`.
13. **Sound and motion passes.** Use `sound_design_engine.py` for cue planning.
    Use HyperFrames for title cards, hook cards, chapter cards, stat cards, lower
    thirds, and designed text systems. Use Remotion for polished motion graphics,
    animated typography, reusable components, and graphics that need precise
    timing. Use Manim for technical animation. Do not use Pillow/PIL for final
    title or caption typography. Render approval frames/contact sheets for new
    title cards, hook cards, chapter cards, lower thirds, and major motion
    graphics before final compositing.
14. **Render preview.** Build `preview.mp4` with `faceless_renderer.py`,
    ffmpeg/Remotion/Manim/HyperFrames as appropriate. ASS subtitles still apply
    last.
15. **Self-QC.** Run `qc_check.py`; check story, facts, assets/rights, captions,
    visual collisions, sound mix, motion timing, and technical export.
16. **Fix and final.** Correct failures, then render `final.mp4`.

### Required Artifact Contract

Do not call a from-scratch project complete unless these exist:

- `script.md`
- `visual_plan.md`
- `asset_list.md`
- `creative_directive.json`
- `edit_decision_list.json`
- `preview.mp4`
- `qc_report.md`
- `final.mp4`

### From-Scratch EDL Rules

`edit_decision_list.json` is the creation timeline. It may later be translated
into helper-specific EDLs, Remotion compositions, ffmpeg filter graphs, Manim
scenes, or HyperFrames projects. It must include:

- Project settings: resolution, fps, duration, aspect ratio.
- Beat IDs matching `script.md` and `visual_plan.md`.
- Voiceover segments or generated audio references.
- Asset IDs that match `asset_manifest.json`.
- Layer start/end times.
- Caption continuity/repositioning rules, plus any explicit user-approved suppression exceptions.
- Motion/overlay instructions.
- Music/SFX cues and mix levels.
- QC flags and unresolved placeholders.

### Asset Rules For From-Scratch Work

- Read `sources/asset_resource_platforms.md` before searching, downloading,
  generating, or rendering assets.
- Prefer no-key/direct public and user-provided assets first.
- Use API-key sources only if credentials exist in root `.env` or the user
  provides them.
- Use paid/manual sources only after user approval.
- Never bypass paywalls, watermarks, login walls, rate limits, or license
  restrictions.
- Every asset used in the timeline must have a manifest entry.
- Generated visuals must record prompt/model/provider/date and must not be
  presented as factual evidence.
- Maps need attribution; charts need data source and query/file reference.

### From-Scratch Self-QC

Before showing `preview.mp4`:

- The hook creates a reason to keep watching.
- The script has no unsupported factual claims.
- Every beat has a planned visual and every visual has a timeline role.
- `asset_manifest.json` passes `asset_manifest.py check` or remaining warnings
  are explained in `qc_report.md`.
- Captions are readable and do not cover faces, products, proof, maps, charts,
  UI, or important action.
- Music and SFX stay below narration.
- Motion and transitions land on meaningful beats.
- Generated visuals are not presented as real evidence.
- The render matches target aspect ratio, resolution, fps, duration, and audio.

## Cut craft (techniques)

- **Audio-first.** Candidate cuts from word boundaries and silence gaps.
- **Preserve peaks.** Laughs, punchlines, emphasis beats. Extend past punchlines to include reactions — the laugh IS the beat.
- **Speaker handoffs** benefit from air between utterances. Common values: 400–600ms. Less for fast-paced, more for cinematic. Taste call.
- **Audio events as signals.** `(laughs)`, `(sighs)`, `(applause)` mark beats. Extend past them.
- **Silence gaps are cut candidates.** Silences ≥400ms are usually the cleanest. 150–400ms phrase boundaries are usable with a visual check. <150ms is unsafe (mid-phrase).
- **Example cut padding** (the launch video shipped with this): 50ms before the first kept word, 80ms after the last. Tighter for montage energy, looser for documentary. Stay in the 30–200ms working window (Hard Rule 7).
- **Never reason audio and video independently.** Every cut must work on both tracks.

## The packed transcript (primary reading view)

`pack_transcripts.py` reads all `transcripts/*.json` and produces one markdown file where each take is a list of phrase-level lines, each prefixed with its `[start-end]` time range. Phrases break on any silence ≥ 0.5s OR speaker change. This is the artifact the editor sub-agent reads to pick cuts — it gives word-boundary precision from text alone at 1/10 the tokens of raw JSON.

Example line:
```
## C0103  (duration: 43.0s, 8 phrases)
  [002.52-005.36] S0 Ninety percent of what a web agent does is completely wasted.
  [006.08-006.74] S0 We fixed this.
```

## Editor sub-agent brief (for multi-take selection)

When the task is "pick the best take of each beat across many clips," spawn a dedicated sub-agent with a brief shaped like this. The structure is load-bearing; the pitch-shape example is not.

```
You are editing a <type> video. Pick the best take of each beat and 
assemble them chronologically by beat, not by source clip order.

INPUTS:
  - takes_packed.md (time-annotated phrase-level transcripts of all takes)
  - Product/narrative context: <2 sentences from the user>
  - Speaker(s): <name, role, delivery style note>
  - Expected structure: <pick an archetype or invent one>
  - Verbal slips to avoid: <list from the pre-scan pass>
  - Target runtime: <seconds>

Common structural archetypes (pick, adapt, or invent):
  - Tech launch / demo:   HOOK → PROBLEM → SOLUTION → BENEFIT → EXAMPLE → CTA
  - Tutorial:             INTRO → SETUP → STEPS → GOTCHAS → RECAP
  - Interview:            (QUESTION → ANSWER → FOLLOWUP) repeat
  - Travel / event:       ARRIVAL → HIGHLIGHTS → QUIET MOMENTS → DEPARTURE
  - Documentary:          THESIS → EVIDENCE → COUNTERPOINT → CONCLUSION
  - Music / performance:  INTRO → VERSE → CHORUS → BRIDGE → OUTRO
  - Or invent your own.

RULES:
  - Start/end times must fall on word boundaries from the transcript.
  - Pad cut boundaries (working window 30–200ms).
  - Prefer silences ≥ 400ms as cut targets.
  - Unavoidable slips are kept if no better take exists. Note them in "reason".
  - If over budget, revise: drop a beat or trim tails. Report total and self-correct.

OUTPUT (JSON array, no prose):
  [{"source": "C0103", "start": 2.42, "end": 6.85, "beat": "HOOK",
    "quote": "...", "reason": "..."}, ...]

Return the final EDL and a one-line total runtime check.
```

## Color grade (when requested)

Your job is to **reason about the image**, not apply a preset. Look at a frame (via `timeline_view`), decide what's wrong, adjust one thing, look again.

Mental model is ASC CDL. Per channel: `out = (in * slope + offset) ** power`, then global saturation. `slope` → highlights, `offset` → shadows, `power` → midtones.

**Example filter chains** (`grade.py` has `--list-presets`; use them as starting points or mix your own):

- **`warm_cinematic`** — retro/technical, subtle teal/orange split, desaturated. Shipped in a real launch video. Safe for talking heads.
- **`neutral_punch`** — minimal corrective: contrast bump + gentle S-curve. No hue shifts.
- **`none`** — straight copy. Default when the user hasn't asked.

For anything else — portraiture, nature, product, music video, documentary — invent your own chain. `grade.py --filter '<raw ffmpeg>'` accepts any filter string.

Hard rules: apply **per-segment during extraction** (not post-concat, which re-encodes twice). Never go aggressive without testing skin tones.

## Subtitles (when requested)

Subtitles have three dimensions worth reasoning about: **chunking** (1/2/3/sentence per line), **case** (UPPER/Title/Natural), and **placement** (margin from bottom). The right combo depends on content.

For any captioned final render, captions must be ASS captions generated through the repo's caption style system. Do not burn final captions as Pillow/PIL image text or as a hardcoded single-font overlay. Choose, adapt, or create an ASS style from `presets/captions/ass_caption_styles.json`, the active style pack, and the creative brief.

When writing ASS dialogue text, escape only what ASS requires. Use `\N` in the final `.ass` file for an intentional hard line break; do not accidentally write `\\N`, because that can burn visible slash/backslash markers instead of a clean line break. Before final render, inspect the `.ass` Dialogue lines for literal escape artifacts and verify at least one caption contact sheet after burn-in.

**Worked styles** — pick, adapt, or invent:

**`bold-overlay`** — short-form tech launch, fast-paced social. 2-word chunks, UPPERCASE, break on punctuation, bold sans, white-on-outline, low safe margin. `render.py --build-subtitles` now resolves dynamic ASS caption styles from `presets/captions/ass_caption_styles.json`.

```
FontName=<resolved font role from ass_caption_styles.json>,FontSize=<style size>,Bold=1,
PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,BackColour=&H00000000,
BorderStyle=1,Outline=2,Shadow=0,
Alignment=2,MarginV=<style safe margin>
```

**`natural-sentence`** (if you invent this mode) — narrative, documentary, education. 4–7 word chunks, sentence case, break on natural pauses, `MarginV=60–80`, larger font for readability, slightly wider max-width. No shipped force_style — design one if you need it.

Invent a third style if neither fits. Hard rules: subtitles LAST (Rule 1), output-timeline offsets (Rule 5).

Title cards and motion graphics do not replace the caption layer by default. Keep captions visible, reposition them, or restyle them under title overlays unless the user explicitly approves a suppression/no-caption window.

## Animations (when requested)

Animations match the content and the brand. **Get the palette, font, and visual language from the conversation** — never assume a default. If the user hasn't told you, propose a palette in the strategy phase and wait for confirmation before building anything.

**Tool options:**

Pick the engine per animation slot, but keep the professional default: HyperFrames for designed title/card/lower-third systems and Remotion for polished motion graphics. Do not fall back to Pillow/PIL for final typography.

- **HyperFrames** — default for title cards, hook cards, chapter cards, stat cards, lower thirds, typographic layouts, browser-native HTML/CSS/GSAP video compositions, product UI motion, website-to-video or mockup-to-video captures, kinetic typography, landing-page/storyboard promos, data-driven UI states, transparent WebM overlays, and clips that need deterministic frame capture plus HyperFrames lint/validate/render checks. Best when the animation should be authored and verified like a web composition instead of a React component tree.
- **Remotion** — default for polished social motion graphics, animated typography, reusable React primitives, component state, data viz, or an existing Remotion brand system. Best when reusable component logic or React composition is the simpler authoring model.
- **Manim** — formal diagrams, state machines, equation derivations, graph morphs. Read `skills/manim-video/SKILL.md` and its references for depth.
- **Pillow/PIL** — diagnostics, rough placeholders, masks, contact-sheet utilities, or non-final helper assets only. Do not use it for final title cards, captions, lower thirds, hook cards, chapter cards, or designed typography.

For HyperFrames slots, scaffold the slot inside `edit/animations/slot_<id>/` with `npx --yes hyperframes init . --example blank --non-interactive --skip-skills`, build the HTML composition there, run the HyperFrames checks that fit the slot (`lint`, `validate`, and a draft render when practical), then produce the final overlay video with `npx --yes hyperframes render . -o render.mp4` or `--format webm -o render.webm` when alpha is required. Point the EDL overlay `file` at the actual rendered path.

For Remotion slots, keep the Remotion project isolated inside the same slot directory, scaffold with `npx create-video@latest` or install Remotion locally there, render the composition to `render.mp4` with the project-local `remotion render` command, and verify duration and dimensions with `ffprobe`.

For title cards, hook cards, chapter cards, lower thirds, stat cards, and major motion graphics, render still approval frames/contact sheets before compositing. Get user approval before continuing to final render.

Invent hybrids if useful, but final typography must come from ASS, HyperFrames, Remotion, or another explicitly approved professional typography engine.

**Duration rules of thumb, context-dependent:**

- **Sync-to-narration explanations.** A viewer needs to parse the content at 1×. Rough floor 3s, typical 5–7s for simple cards, 8–14s for complex diagrams. The launch video shipped at 5–7s per simple card.
- **Beat-synced accents** (music video, fast montage). 0.5–2s is fine — they're visual accents, not information. The "readable at 1×" rule becomes *"recognizable at 1×"*, not *"fully parseable."*
- **Hold the final frame ≥ 1s** before the cut (universal).
- **Over voiceover:** total duration ≥ `narration_length + 1s` (universal).
- **Never parallel-reveal independent elements** — the eye can't track two new things at once. One thing, pause, next thing.

**Animation payoff timing (rule for sync-to-narration):** get the payoff word's timestamp. Start the overlay `reveal_duration` seconds earlier so the landing frame coincides with the spoken payoff word. Without this sync the animation feels disconnected.

**Easing** (universal — never `linear`, it looks robotic):

```python
def ease_out_cubic(t):    return 1 - (1 - t) ** 3
def ease_in_out_cubic(t):
    if t < 0.5: return 4 * t ** 3
    return 1 - (-2 * t + 2) ** 3 / 2
```

`ease_out_cubic` for single reveals (slow landing). `ease_in_out_cubic` for continuous draws.

**Typing text anchor trick:** center on the FULL string's width, not the partial-string width — otherwise text slides left during reveal.

**Example palette** (the launch video — one aesthetic among infinite):
- Background `(10, 10, 10)` near-black
- Accent `#FF5A00` / `(255, 90, 0)` orange
- Labels `(110, 110, 110)` dim gray
- Font: Menlo Bold at `/System/Library/Fonts/Menlo.ttc` (index 1)
- ≤ 2 accent colors, ~40% empty space, minimal chrome
- Result: terminal / retro tech feel

This is one style. If the brand is warm and serif, use that. If it's colorful and playful, use that. If the user handed you a style guide, follow it. If they didn't, propose one and confirm.

**Parallel sub-agent brief** — each animation is one sub-agent spawned via the `Agent` tool. Each prompt is self-contained (sub-agents have no parent context). Include:

1. One-sentence goal: *"Build ONE animation: [spec]. Nothing else."*
2. Absolute output path (`<edit>/animations/slot_<id>/render.mp4`)
3. Exact technical spec: resolution, fps, codec, pix_fmt, CRF, duration
4. Style palette as concrete values (RGB tuples, hex, or reference to a design system)
5. Font path with index
6. Frame-by-frame timeline (what happens when, with easing)
7. Anti-list ("no chrome, no extras, no titles unless specified")
8. Code pattern reference (copy helpers inline, don't import across slots)
9. Deliverable checklist (script, render, verify duration via ffprobe, report)
10. **"Do not ask questions. If anything is ambiguous, pick the most obvious interpretation and proceed."**

One sub-agent = one file (unique filenames, parallel agents don't overwrite each other).

## Output spec

Match the source unless the user asked for something specific. Common targets: `1920×1080@24` cinematic, `1920×1080@30` screen content, `1080×1920@30` vertical social, `3840×2160@24` 4K cinema, `1080×1080@30` square. `render.py` final exports default to the highest-resolution source used by the EDL, but sources below 1080p are upscaled to a 1080-pixel short edge, so 720p landscape becomes `1920×1080`, 720×1280 vertical becomes `1080×1920`, and 4K stays 4K. Use `--resolution <WxH>` or EDL fields like `"resolution": "3840x2160"` only when a specific delivery target is needed. Worth asking the user which delivery format matters.

## EDL format

```json
{
  "version": 1,
  "sources": {"C0103": "/abs/path/C0103.MP4", "C0108": "/abs/path/C0108.MP4"},
  "ranges": [
    {"source": "C0103", "start": 2.42, "end": 6.85,
     "beat": "HOOK", "quote": "...", "reason": "Cleanest delivery, stops before slip at 38.46."},
    {"source": "C0108", "start": 14.30, "end": 28.90,
     "beat": "SOLUTION", "quote": "...", "reason": "Only take without the false start."}
  ],
  "grade": "warm_cinematic",
  "overlays": [
    {"file": "edit/animations/slot_1/render.mp4", "start_in_output": 0.0, "duration": 5.0}
  ],
  "subtitles": "edit/master.srt",
  "total_duration_s": 87.4
}
```

`grade` is a preset name or raw ffmpeg filter. `overlays` are rendered animation clips. `subtitles` is optional and applied LAST.

## Memory — `project.md`

Append one section per session at `<edit>/project.md`:

```markdown
## Session N — YYYY-MM-DD

**Strategy:** one paragraph describing the approach
**Decisions:** take choices, cuts, grades, animations + why
**Reasoning log:** one-line rationale for non-obvious decisions
**Outstanding:** deferred items
```

On startup, read `project.md` if it exists and summarize the last session in one sentence before asking whether to continue.

## Anti-patterns

Things that consistently fail regardless of style:

- **Hierarchical pre-computed codec formats** with USABILITY / tone tags / shot layers. Over-engineering. Derive from the transcript at decision time.
- **Hand-tuned moment-scoring functions.** The LLM picks better than any heuristic you'll write.
- **Whisper SRT / phrase-level output.** Loses sub-second gap data. Always word-level verbatim.
- **Running Whisper locally on CPU.** Slow and it normalizes fillers. Use hosted Scribe.
- **Burning subtitles into base before compositing overlays.** Overlays hide them. (Hard Rule 1.)
- **Double-escaping ASS line breaks.** A final `.ass` file should use `\N` for a hard line break, not `\\N`; visible slash/backslash caption artifacts require caption regeneration and rerender.
- **Single-pass filtergraph when you have overlays.** Double re-encodes. Use per-segment extract → concat.
- **Linear animation easing.** Looks robotic. Always cubic.
- **Hard audio cuts at segment boundaries.** Audible pops. (Hard Rule 3.)
- **Typing text centered on the partial string.** Text slides left as it grows.
- **Sequential sub-agents for multiple animations.** Always parallel.
- **Editing before confirming the strategy.** Never.
- **Re-transcribing cached sources.** Immutable outputs of immutable inputs.
- **Assuming what kind of video it is.** Look first, ask second, edit last.

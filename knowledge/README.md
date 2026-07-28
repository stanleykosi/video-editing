# Editorial Knowledge Base

This is the only canonical namespace for editorial knowledge. Engine behavior
lives in `src/video_engine/`; workflow executables live in `tools/video-use/`.
Knowledge describes decisions and constraints but does not execute edits.

## Structure

- `playbooks/` - curated skills by editing domain and format.
- `workflows/content_creation/` - artifact-driven creation workflows and templates.
- `research/catalogs/` - official references, source queues, and asset guidance.
- `research/lessons/` - distilled lessons derived from research and projects.
- `research/source_notes/` - ignored local paraphrased research notes.
- `research/transcripts/` - ignored local raw ASR/tutorial transcripts.
- `techniques/<category>/` - JSON technique cards grouped by declared category.
- `presets/` - reusable parameter and style suggestions.
- `styles/` - higher-level editorial grammars.
- `quality/editorial_checklists/` - human-facing editorial and accessibility QC.
- `CONTRIBUTING.md` - tutorial-to-knowledge ingestion process.

## Core Skills

- `knowledge/playbooks/editing_taste_story_pacing.md` - story shape, rhythm, scene selection, and cut judgment.
- `knowledge/playbooks/scriptwriting.md` - video scriptwriting systems for hooks, structure, voiceover/dialogue, visual notes, storyboard planning, tone, duration, and script iteration.
- `knowledge/playbooks/short_form_retention.md` - hooks, retention beats, pattern breaks, and payoff density.
- `knowledge/playbooks/slow_human_retention_editing.md` - slower human short-form style built on proof, warmth, intentional imperfection, and restrained polish.
- `knowledge/playbooks/viral_youtube_editing_workflow.md` - viral-style YouTube workflow from idea/script fit to publish threshold.
- `knowledge/playbooks/capcut_motion_language.md` - mobile/social motion patterns and CapCut-style edit grammar.
- `knowledge/playbooks/capcut_pro_compositing_effects.md` - CapCut subject sandwiches, chroma-key portals, tracking stickers, photo stacks, PiP borders, split masks, clones, and green-screen VFX.
- `knowledge/playbooks/vox_style_documentary_graphics.md` - Vox-inspired editorial explainer graphics, maps, charts, document highlights, and paper-texture motion.
- `knowledge/playbooks/video_typography.md` - font roles, typographic hierarchy, line breaks, spacing, live-action text placement, and ad/readability typography.
- `knowledge/playbooks/programmatic_typography_implementation.md` - Remotion/FFmpeg reproduction of text masks, highlight wipes, glow sweeps, glitch text, pop captions, and timed overlays.
- `knowledge/playbooks/davinci_resolve_short_form_workflow.md` - Resolve vertical shorts, Fusion motion, Text+, Power Bins, and shortcut workflow.
- `knowledge/playbooks/davinci_resolve_full_workflow.md` - full Resolve workflow from project/media organization through Edit/Cut, Fusion, Color, Fairlight, and Deliver.
- `knowledge/playbooks/premiere_professional_editing.md` - professional timeline organization and NLE equivalents.
- `knowledge/playbooks/after_effects_reel_animation.md` - After Effects-heavy Reel animation, segment scenes, presets, and Premiere roundtrips.
- `knowledge/playbooks/kinetic_captions.md` - caption chunking, emphasis, animation, and readability.
- `knowledge/playbooks/sound_design.md` - impact hits, risers, ambience, transitions, and mix polish.
- `knowledge/playbooks/beat_sync.md` - music mapping, beat-aware cuts, ramps, and accents.
- `knowledge/playbooks/color_grading.md` - correction, look design, consistency, and delivery safety.
- `knowledge/playbooks/motion_graphics.md` - overlays, layouts, graphs, callouts, and animated explainers.
- `knowledge/playbooks/still_image_cinematic_compositing.md` - image-to-video scene composites with motivated overlays, masks, local light, and unified grade.
- `knowledge/playbooks/podcast_to_shorts.md` - long-form conversation to short-form clips.
- `knowledge/playbooks/movie_recap_workflow.md` - movie recaps, movie explainers, anime recaps, episode recaps, narration-led scene matching, muted-source movie edits, and transformed short fragments.
- `knowledge/playbooks/sports_highlights.md` - highlight selection, momentum, replay, and commentary sync.
- `knowledge/playbooks/anime_edits.md` - anime/action montage grammar and source-audio handling.
- `knowledge/playbooks/documentary_explainer.md` - evidence-led narrative, archival flow, and visual explanation.
- `knowledge/playbooks/ugc_ad_editing.md` - direct-response ad structure, proof, objections, and CTA pacing.
- `knowledge/playbooks/editor_qc.md` - final review rules before preview or delivery.

## Knowledge Flow

1. Add candidate tutorials to `knowledge/research/catalogs/youtube_tutorial_list.md`.
2. Add official tool references to `knowledge/research/catalogs/official_docs.md`.
3. Store raw notes in `knowledge/research/transcripts/` and curated source notes
   in `knowledge/research/source_notes/`.
4. Distill lessons in `knowledge/research/lessons/`.
5. Create categorized JSON cards in `knowledge/techniques/`.
6. Update playbooks in `knowledge/playbooks/`.
7. Add reusable presets in `knowledge/presets/`.
8. Add failure checks in `knowledge/quality/editorial_checklists/`.
9. Validate important techniques with small projects in `test_projects/`.

## From-Scratch Creation

- `knowledge/workflows/content_creation/knowledge_router.md` - scans the repo and creates project-specific `knowledge_plan.md/json` routes.
- `knowledge/workflows/content_creation/script_subagent_review_loop.md` - mandatory writer subagent plus independent harsh critic loop for any new or substantially rewritten video script, narration, hook, recap paragraph, ad read, or storyboard script.
- `knowledge/workflows/content_creation/scriptwriter.md` - converts a topic or brief into a beat-tagged, voiceover-ready script.
- `knowledge/workflows/content_creation/research_to_script.md` - turns source research into claim-safe script material.
- `knowledge/workflows/content_creation/visual_planner.md` - maps every script beat to visuals, motion, captions, sound, and QC risks.
- `knowledge/workflows/content_creation/asset_planner.md` - plans source, generated, rendered, and user-provided assets with manifest requirements.
- `knowledge/workflows/content_creation/voiceover_planner.md` - defines narration pace, tone, pauses, emphasis, and pronunciation.
- `knowledge/workflows/content_creation/faceless_video_workflow.md` - end-to-end artifact contract for faceless videos.
- `knowledge/workflows/content_creation/youtube_storytelling_workflow.md` - story structures for retention-led explainers and shorts.
- `knowledge/workflows/content_creation/templates/` - reusable starters for `script.md`, `visual_plan.md`, `asset_list.md`, and `edit_decision_list.json`.
- `knowledge/workflows/content_creation/subagent_modules.md` - sub-agent boundaries, artifact contracts, and which helpers each module should call.
- `knowledge/styles/faceless_educational_short.json` - clean educational vertical short style.
- `knowledge/styles/documentary_explainer.json` - evidence-led documentary explainer style.
- `knowledge/styles/viral_storytelling_short.json` - fast curiosity-and-payoff short style.
- `knowledge/styles/business_history_short.json` - business/history short narrative style.
- `knowledge/styles/football_analysis_short.json` - tactical football analysis short style.

## Card Categories

- `story_pacing`
- `retention`
- `captions`
- `motion`
- `compositing`
- `transition`
- `sound_design`
- `beat_sync`
- `color`
- `typography`
- `nle_workflow`
- `genre_workflow`
- `qc`

## Quality Bar

A knowledge item is ready when an agent can answer:

- When should I use this?
- When should I avoid this?
- What does the timeline pattern look like?
- How do I implement it in ffmpeg, Remotion, Blender, CapCut, or Premiere?
- What mistakes should I check for before delivery?

## High-Risk Recap And Commentary Checks

- `knowledge/techniques/qc/qc_narration_visual_character_alignment_001.json` - use for recap, commentary, documentary, anime, product, UI, or proof-led edits where narration names a subject that must be visible at the viewer-facing timestamp. This card exists because exact EDL boundaries can still fail the viewer experience when a rounded playback second shows the previous subject.
- `knowledge/playbooks/movie_recap_workflow.md` - always load for movie recap, movie explainer, anime recap, episode recap, or narration-over-movie-source edits.
- `knowledge/techniques/genre_workflow/movie_recap_paragraph_scene_workflow_001.json` - use to script paragraph-sized recap shorts and map each narration paragraph to a visually verified source scene range.
- `knowledge/techniques/nle_workflow/movie_recap_chop_delete_flip_speed_transform_001.json` - use to transform verified movie scene ranges with short fragments, alternate deletion/compression, optional mirror/flip, speed fitting, and muted source audio.
- `knowledge/quality/editorial_checklists/movie_recap_qc.md` - use before showing or finalizing any movie recap output.

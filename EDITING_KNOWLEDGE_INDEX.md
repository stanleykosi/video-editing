# Editing Knowledge Index

Use this file as the routing map for agent knowledge.

## Core Skills

- `skills/editing_taste_story_pacing.md` - story shape, rhythm, scene selection, and cut judgment.
- `skills/scriptwriting.md` - video scriptwriting systems for hooks, structure, voiceover/dialogue, visual notes, storyboard planning, tone, duration, and script iteration.
- `skills/short_form_retention.md` - hooks, retention beats, pattern breaks, and payoff density.
- `skills/slow_human_retention_editing.md` - slower human short-form style built on proof, warmth, intentional imperfection, and restrained polish.
- `skills/viral_youtube_editing_workflow.md` - viral-style YouTube workflow from idea/script fit to publish threshold.
- `skills/capcut_motion_language.md` - mobile/social motion patterns and CapCut-style edit grammar.
- `skills/capcut_pro_compositing_effects.md` - CapCut subject sandwiches, chroma-key portals, tracking stickers, photo stacks, PiP borders, split masks, clones, and green-screen VFX.
- `skills/vox_style_documentary_graphics.md` - Vox-inspired editorial explainer graphics, maps, charts, document highlights, and paper-texture motion.
- `skills/video_typography.md` - font roles, typographic hierarchy, line breaks, spacing, live-action text placement, and ad/readability typography.
- `skills/programmatic_typography_implementation.md` - Remotion/FFmpeg reproduction of text masks, highlight wipes, glow sweeps, glitch text, pop captions, and timed overlays.
- `skills/davinci_resolve_short_form_workflow.md` - Resolve vertical shorts, Fusion motion, Text+, Power Bins, and shortcut workflow.
- `skills/davinci_resolve_full_workflow.md` - full Resolve workflow from project/media organization through Edit/Cut, Fusion, Color, Fairlight, and Deliver.
- `skills/premiere_professional_editing.md` - professional timeline organization and NLE equivalents.
- `skills/after_effects_reel_animation.md` - After Effects-heavy Reel animation, segment scenes, presets, and Premiere roundtrips.
- `skills/kinetic_captions.md` - caption chunking, emphasis, animation, and readability.
- `skills/sound_design.md` - impact hits, risers, ambience, transitions, and mix polish.
- `skills/beat_sync.md` - music mapping, beat-aware cuts, ramps, and accents.
- `skills/color_grading.md` - correction, look design, consistency, and delivery safety.
- `skills/motion_graphics.md` - overlays, layouts, graphs, callouts, and animated explainers.
- `skills/still_image_cinematic_compositing.md` - image-to-video scene composites with motivated overlays, masks, local light, and unified grade.
- `skills/podcast_to_shorts.md` - long-form conversation to short-form clips.
- `skills/movie_recap_workflow.md` - movie recaps, movie explainers, anime recaps, episode recaps, narration-led scene matching, muted-source movie edits, and transformed short fragments.
- `skills/sports_highlights.md` - highlight selection, momentum, replay, and commentary sync.
- `skills/anime_edits.md` - anime/action montage grammar and source-audio handling.
- `skills/documentary_explainer.md` - evidence-led narrative, archival flow, and visual explanation.
- `skills/ugc_ad_editing.md` - direct-response ad structure, proof, objections, and CTA pacing.
- `skills/editor_qc.md` - final review rules before preview or delivery.

## Knowledge Flow

1. Add candidate tutorials to `sources/youtube_tutorial_list.md`.
2. Add official tool references to `sources/official_docs.md`.
3. Store cleaned notes in `transcripts/`.
4. Distill lessons in `extracted_lessons/`.
5. Create JSON technique cards in `technique_cards/`.
6. Update skills in `skills/`.
7. Add reusable presets in `presets/`.
8. Add failure checks in `qc_checklists/`.
9. Validate important techniques with small projects in `test_projects/`.

## From-Scratch Creation

- `content_creation/knowledge_router.md` - scans the repo and creates project-specific `knowledge_plan.md/json` routes.
- `content_creation/script_subagent_review_loop.md` - mandatory writer subagent plus independent harsh critic loop for any new or substantially rewritten video script, narration, hook, recap paragraph, ad read, or storyboard script.
- `content_creation/scriptwriter.md` - converts a topic or brief into a beat-tagged, voiceover-ready script.
- `content_creation/research_to_script.md` - turns source research into claim-safe script material.
- `content_creation/visual_planner.md` - maps every script beat to visuals, motion, captions, sound, and QC risks.
- `content_creation/asset_planner.md` - plans source, generated, rendered, and user-provided assets with manifest requirements.
- `content_creation/voiceover_planner.md` - defines narration pace, tone, pauses, emphasis, and pronunciation.
- `content_creation/faceless_video_workflow.md` - end-to-end artifact contract for faceless videos.
- `content_creation/youtube_storytelling_workflow.md` - story structures for retention-led explainers and shorts.
- `content_creation/templates/` - reusable starters for `script.md`, `visual_plan.md`, `asset_list.md`, and `edit_decision_list.json`.
- `content_creation/subagent_modules.md` - sub-agent boundaries, artifact contracts, and which helpers each module should call.
- `style_packs/faceless_educational_short.json` - clean educational vertical short style.
- `style_packs/documentary_explainer.json` - evidence-led documentary explainer style.
- `style_packs/viral_storytelling_short.json` - fast curiosity-and-payoff short style.
- `style_packs/business_history_short.json` - business/history short narrative style.
- `style_packs/football_analysis_short.json` - tactical football analysis short style.

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

- `technique_cards/qc_narration_visual_character_alignment_001.json` - use for recap, commentary, documentary, anime, product, UI, or proof-led edits where narration names a subject that must be visible at the viewer-facing timestamp. This card exists because exact EDL boundaries can still fail the viewer experience when a rounded playback second shows the previous subject.
- `skills/movie_recap_workflow.md` - always load for movie recap, movie explainer, anime recap, episode recap, or narration-over-movie-source edits.
- `technique_cards/movie_recap_paragraph_scene_workflow_001.json` - use to script paragraph-sized recap shorts and map each narration paragraph to a visually verified source scene range.
- `technique_cards/movie_recap_chop_delete_flip_speed_transform_001.json` - use to transform verified movie scene ranges with short fragments, alternate deletion/compression, optional mirror/flip, speed fitting, and muted source audio.
- `qc_checklists/movie_recap_qc.md` - use before showing or finalizing any movie recap output.

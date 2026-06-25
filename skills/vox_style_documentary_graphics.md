# Vox-Style Documentary Graphics

## Purpose

Guide editorial documentary explainer graphics inspired by Vox-like motion design:
warm paper texture, maps, charts, document highlights, screenshot focus, cutout
collages, restrained SFX, and low-FPS handmade motion.

## When To Use This Skill

- Building a documentary explainer, educational breakdown, or editorial sequence
  that needs maps, charts, source documents, and visual evidence.
- Translating a CapCut-style graphics tutorial into reusable ffmpeg, Remotion,
  Premiere, or After Effects instructions.
- Creating a 16:9 infographic sequence with paper texture, serif typography,
  arrows, masks, and compound/nested scenes.
- Designing a Vox-inspired style without copying protected logos, marks, or exact
  publisher identity.
- Refining editorial typography roles, hierarchy, line breaks, and spacing inside
  maps, charts, document highlights, and title-card scenes.
- Building CapCut documentary effects with cutout depth, switch-focus blur,
  filmed-screen texture, archival frame treatment, and parallax collage motion.

## Core Principles

- Use the editorial grammar, not another brand's identity.
- Every graphic should support a claim, statistic, location, source detail, or
  transition.
- Build from a consistent background, type, palette, and motion cadence.
- Keep maps, charts, documents, and source screenshots readable before adding
  texture or low-FPS effects.
- Compound or nest dense graphic sections so the main timeline remains readable.
- Add SFX only after motion timing is locked and only for meaningful reveals.
- Music should feel documentary/editorial and stay below narration.
- Use font families by role: editorial serif for gravity, clean sans for utility
  labels, and display type only for short dominant title words.
- Typography hierarchy should point to the claim, source word, map label, or data
  value the viewer needs first.
- Depth, blur, texture, and archival styling must make source type and focus
  clearer rather than making evidence harder to trust.

## Techniques

- `technique_cards/motion_vox_paper_grid_background_001.json`
- `technique_cards/motion_typographic_explainer_intro_collage_001.json`
- `technique_cards/motion_map_trace_route_pan_001.json`
- `technique_cards/motion_animated_bar_chart_wipe_001.json`
- `technique_cards/motion_document_highlight_focus_pan_001.json`
- `technique_cards/motion_word_focus_screenshot_sequence_001.json`
- `technique_cards/motion_layered_cutout_infographic_scene_001.json`
- `technique_cards/motion_stop_motion_fps_lag_texture_001.json`
- `technique_cards/sound_infographic_motion_sfx_sync_001.json`
- `technique_cards/nle_capcut_compound_graphics_workflow_001.json`
- `technique_cards/motion_overlay_readability_focus_stack_001.json`
- `technique_cards/motion_capcut_switch_focus_depth_blur_001.json`
- `technique_cards/motion_documentary_research_overlay_timelapse_001.json`
- `technique_cards/color_archival_film_frame_treatment_001.json`
- `technique_cards/motion_capcut_documentary_parallax_collage_001.json`
- `technique_cards/motion_screen_blend_texture_overlay_001.json`
- `technique_cards/motion_sketch_to_animation_ladder_001.json`
- `technique_cards/nle_shortform_project_asset_template_system_001.json`
- `technique_cards/typography_font_family_role_selection_001.json`
- `technique_cards/typography_contrast_hierarchy_stack_001.json`
- `technique_cards/typography_sentence_structure_line_breaks_001.json`
- `technique_cards/typography_tracking_kerning_line_spacing_qc_001.json`

## Timing Rules

- Build uncertain intro or graphic scenes longer than needed, then trim the
  compound/nest to the finished animation.
- Map route reveals can start around 2 seconds; shorten for simple routes and
  lengthen only when geography needs more scan time.
- Bar chart wipes can start around 1 second per bar and stagger by narration
  order.
- Document highlights should hold until the highlighted words are readable.
- Word-focus screenshot sequences can shorten each successive source, but must
  end with enough context to avoid cherry-picking.
- Apply FPS lag/posterize texture after motion timing is locked.
- Hold typographic title, label, or source-text moments long enough to read at
  final documentary delivery size.
- Switch-focus moves can use a roughly 1s to 3s handoff when the comparison
  remains readable.
- Documentary text animations can start around 1.5-2 seconds, then shorten only
  if the title still reads.

## Motion Rules

- Warm paper/grid background motion stays subordinate to foreground evidence.
- Use wipes for arrows, routes, bars, and highlights when a draw-on feeling helps
  the explanation.
- Use eased/cubic curves for map pans, document zooms, compound zooms, and final
  collage moves.
- Avoid low-FPS texture on dense labels if it damages readability.
- Do not let cutouts, arrows, captions, or labels cover the exact evidence being
  explained.
- Use line breaks and spacing that preserve source context and title hierarchy.
- Use blur ramps, background counter-movement, and reduced copied transforms to
  create depth while keeping one primary focus.
- Use archival frames, filmed-screen textures, and glass overlays as source-type
  signals, not as constant decoration.

## Sound Rules

- Use whooshes for major entrances/routes, ticks for highlights, and
  shutter-like cues for screenshot swaps only when they clarify hierarchy.
- Keep SFX below narration and avoid cueing every small layer.
- Choose music by documentary tone, not trend energy.
- Trim music to a natural phrase ending and crossfade exits.
- Recheck SFX sync after applying FPS lag or posterize-time effects.
- One restrained riser can support a research overlay timelapse when it resolves
  into a real discovery or claim.

## Caption Rules

- Keep captions visible, repositioned, or simplified where graphic text already
  carries the spoken idea. Suppress only with explicit user approval.
- Captions should not cover map labels, chart bars, source documents, or
  highlighted screenshots.
- If narration is essential, place captions in a dedicated safe region away from
  the evidence area.
- Decide whether source text, labels, or subtitles are primary before placing all
  three on the same frame.

## Color Rules

- Use warm off-white, charcoal/gray, yellow, red, and muted accents as a starting
  editorial palette.
- Warmth should make the graphic feel analog without lowering text/data contrast.
- Route colors, highlights, and chart bars need enough contrast against the paper
  background and source material.
- Texture, grid, and low-FPS effects should not create dirty compression.
- Accent color should identify evidence priority, category, or contrast, not random
  decoration.
- Archival particles/fade, glass texture, vignette, and HSL unification must not
  lower text/data contrast or hide source labels.

## Tool Implementation Notes

- CapCut: use ratio settings, chroma key, auto removal, masks, blend modes, text
  layers, animation presets, compound clips, keyframes, variable-speed/ease curves,
  separate SFX tracks, and FPS Lag after timing lock.
- ffmpeg: build each scene as layered composition data with background, overlays,
  masks, text, route/chart/highlight timing, and audio cue frames.
- Remotion: create reusable components for paper background, typographic intro,
  route map, bar chart, document highlight, word focus, cutout scene, and FPS
  texture.
- Premiere/After Effects: use nested sequences/precomps, Essential Graphics,
  masks, track mattes, Linear Wipe/Trim Paths equivalents, Posterize Time, eased
  Motion keyframes, and separate SFX/music tracks.
- Asset workflow: every map, screenshot, paper texture, photo, logo, and SFX used
  in a real project needs a source/license/attribution manifest entry.
- Typography workflow: store title font, label font, impact words, line breaks,
  tracking, line height, accent colors, and caption-safe areas with each scene.
- CapCut depth workflow: store cutout source, mask feather, focus blur values,
  compound name, Cubic Ease state, background motion reduction, texture opacity,
  and rights/license status.

## Common Mistakes

- Copying another publisher's protected logo or exact identity.
- Treating texture as style while the map, chart, or source text becomes hard to
  read.
- Building dense graphics without named compounds/nests.
- Applying FPS lag before the animation is timed.
- Using charts without source values or labels.
- Highlighting source text so aggressively that the wording is hidden or
  misleading.
- Adding SFX to every layer until the documentary feels unserious.
- Mixing serif, sans, script, and display fonts without clear editorial roles.
- Tightening tracking or line spacing until labels and source words become harder
  to read.
- Using aged film treatment on current proof footage and confusing source type.
- Pasting the same foreground motion onto the background without reducing it.
- Letting glass texture, blur, or particles hide source text, UI, or captions.

## QC Checklist

- Style is project-specific and does not use unlicensed logos or protected
  identity.
- Every graphic supports a claim, source, data point, map relation, or transition.
- Background, grid, and paper texture stay subordinate to foreground evidence.
- Maps, routes, markers, chart labels, document highlights, and screenshot words
  are readable at final size.
- Compounds/nests are named and internally editable.
- SFX cues land on meaningful visible events and stay below narration.
- Music is licensed/platform-safe or marked temp-only.
- FPS lag/posterize texture does not damage text, map, or chart readability.
- External/generated assets have manifest-ready source and rights notes.
- Typography has one clear primary focus per scene and remains readable after
  paper texture, warmth, blend modes, and low-FPS effects.
- Switch-focus and parallax scenes preserve one readable subject or title at all
  times.
- Archival, AI-generated, downloaded, or reconstructed images have clear source
  and rights notes before delivery.

## Source Lessons Added

- 2026-05-29: `Vox Style Documentary`
- 2026-05-29: `Typography`
- 2026-05-29: `Documentary Edits`

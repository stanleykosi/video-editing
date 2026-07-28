# Editor QC

## Purpose

Collect final checks the agent should run before showing a preview or final export.

## When To Use This Skill

- Before sending any preview.
- Before calling a video final.
- After major changes to captions, audio, color, motion, timing, story structure, or tone.
- When a tutorial lesson introduces a new failure mode.
- When story edits depend on protagonist perspective, open loops, pickups, or learning arcs.
- When a long-form intro delays the explicit promise to build world, trust, or curiosity.
- When music choice, licensing, cue timing, or tonal contrast drives the edit.
- When exporting YouTube tutorials, talking-head videos, or AI-generated short-form clips.
- When exporting high-energy short-form edits with visual stacks, fast captions, subject tracking, and motion-synced SFX.
- When exporting DaVinci Resolve vertical shorts with Fusion effects, Text+, Power Bins, or shortcut-heavy timeline edits.
- When exporting Premiere-built Reels with one-word captions, hook text, B-roll text, full-screen object animation, adjustment zooms, and music auditions.
- When exporting Premiere/After Effects Reels with prepared renders, AE motion passes, final SFX, music, captions, and roundtrip checks.
- When exporting or publishing a scripted viral-style YouTube edit with audience/style, script, assets, music, animation, SFX, and publish-threshold checks.
- When exporting slower human short-form edits where imperfection, proof, foley, warmth, and restrained captions are intentional.
- When exporting editorial documentary graphics with maps, charts, source documents, screenshots, cutouts, and low-FPS motion texture.
- When exporting typography-heavy edits with titles, captions, lower thirds, ad text, scene text, or font/style presets.
- When exporting Remotion or FFmpeg-generated typography, including drawtext
  overlays, word chains, seeded glitch, masks, highlights, and glow sweeps.
- When exporting transparent overlay assets, alpha-mask reveals, ProRes/WebM
  alpha files, or FFmpeg `alphamerge` composites.
- When exporting viral CapCut text effects, number counters, text-behind-object
  composites, outline reveals, or video-in-text.
- When exporting complete DaVinci Resolve projects that use Media Pool
  organization, Edit/Cut assembly, Fusion, Color, Fairlight, and Deliver.
- When approving a formal intro bumper, branded show open, podcast intro, course opener, or repeatable social-series intro.
- When exporting CapCut-style keyframed motion, overlay paths, cutouts, color shifts, tracking, or music ducking.
- When exporting CapCut property-specific keyframes, compound-wrapper sticker/text
  animations, or filter-strength reveals synced to music.
- When exporting high-energy CapCut/anime/action edits with beat-matched speed, character masks, turbulent/wide-angle transitions, heavy overlay pre-renders, SFX, or voice lines.
- When exporting CapCut graph-shaped keyframes, intense zoom stacks, or motion-blur zoom effects.
- When exporting still-image cinematic composites with stock/library overlays,
  Screen blend modes, masks, local flicker, and unified grading.
- When exporting CapCut pro compositing effects such as subject sandwiches,
  chroma-key text portals, tracked stickers, photo stacks, chapter cards, PiP
  borders, split-mask illusions, clone effects, or green-screen VFX.
- When exporting CapCut documentary effects with switch-focus blur, research
  overlays, archival film frames, filmed-screen texture, or parallax cutout
  collages.

## Core Principles

- Check the rendered output, not just the source timeline.
- Inspect the first seconds, last seconds, major transitions, dense effects, and emotional beats.
- Verify audio loudness, clipping, resolution, frame rate, and duration.
- Check for accidental text, watermarks, credits, broken captions, black frames, and style mismatches.
- QC should be observable and actionable.
- A story edit should be checked for both moment-level clarity and macro arc completion.
- Narration-driven edits must be checked for subject alignment: when the narration names a person, character, place, object, product, UI element, proof point, or event, the rendered frame at the viewer-facing timestamp should already show the matching subject unless an intentional mismatch is documented.
- Movie recap edits need paragraph-sized structure, muted source audio, visually verified scene ranges, transformed short fragments, and a final check that no long raw source run slipped through.
- Delayed intros need loop, trust, proof, and promise-delivery checks rather than only first-seconds speed checks.
- Music-led edits need story-fit, license, cue timing, intelligibility, and ethical-tone checks.
- A final QC pass should verify the rendered output against the title/thumbnail promise, first 30 seconds, audio mix, captions, layout, and export settings.
- Auto-generated clips, captions, reframes, and templates must be manually approved before delivery.
- Short-form QC must check the first five seconds, claim support, visual density, subject crop, caption chunks, and SFX sync.
- Resolve QC must check vertical project settings, Fusion easing, adjustment-clip range, Power Bin preset readiness, Text+/auto-caption collisions, and B-roll audio.
- Premiere Reel QC must check caption correction before graphic conversion, duplicate text continuity, any user-approved suppression exception, adjustment-layer ranges, B-roll readability treatment, and music license/platform status.
- AE Reel QC must check the prepared render, segment plan, motion sync, enabled effects, duplicate audio, caption continuity, any user-approved suppression exception, SFX sync, and unmuted final tracks.
- Viral YouTube workflow QC must separate idea/script blockers from optional polish so the edit can improve without becoming endless.
- Slow human short-form QC must distinguish purposeful breathing room from unshaped dead air.
- Vox-inspired documentary graphics need rights, evidence readability, source context, SFX sync, and low-FPS readability checks.
- Typography QC must verify font role, hierarchy, phrase line breaks, spacing, contrast, safe placement, and duplicate caption policy.
- Programmatic typography QC must also verify reproducible fonts, logged filter
  graphs, Sequence-local timing, deterministic randomness, and rendered mask/glow
  states.
- Transparent overlay QC must verify alpha-preserving codec/pixel format,
  transparent empty pixels, mask polarity, matching stream properties, and edge
  behavior over contrasting backgrounds.
- Viral text QC must verify readability after animation, correct final counter
  values, clean cutout/chroma/blend edges, synced SFX, caption continuity, and any user-approved suppression exception.
- Premium CapCut text QC must verify compound editability, duplicate text
  alignment, mask start/end states, glow/gradient readability, and trimmed reveal
  SFX.
- Full Resolve QC must verify project/media organization, synced audio, page
  handoffs, Fusion node order, color management, Fairlight routing, and Deliver settings.
- Formal intro QC must verify the format gate, duration cap, brand/proof/outcome clarity, text hierarchy, caption continuity, any user-approved suppression exception, and frame-locked SFX handoff.
- CapCut keyframe QC must verify keyframe intent, spacing, holds, caption safety, black-corner safety, music duck timing, and asset rights.
- CapCut property-keyframe QC must verify that only the intended property changes
  and that each changing property has its own start/end keyframe.
- CapCut AMV/action QC must verify beat sync, mask edges, heavy-overlay replacement handles, transition readability, SFX sync, and source/license status.
- CapCut anime power-effect QC must verify eye-overlay alignment, placeholder-safe replacement duration, Pendulum readability, and event-matched SFX.
- CapCut graph QC must verify curve intent, subject centering, export-stack quality, motion blur readability, and caption/proof safety.
- Still-image composite QC must verify overlay motivation, mask edges, local light
  plausibility, asset rights, grade unification, and delivery-size readability.
- CapCut pro compositing QC must verify layer order, baked render alignment,
  cutout/key/mask edges, tracking stability, locked-camera capture, audio sync,
  and asset rights.
- CapCut documentary depth QC must verify source type, cutout edges, blur
  handoffs, parallax depth, archival truthfulness, filmed-screen readability, and
  asset rights.

## Techniques

- `knowledge/techniques/story_pacing/eyes_decision_reaction_cut.json`
- `knowledge/techniques/story_pacing/emotional_hold_time.json`
- `knowledge/techniques/story_pacing/build_peak_release_duration_arc.json`
- `knowledge/techniques/story_pacing/natural_rhythm_cut.json`
- `knowledge/techniques/story_pacing/justified_jarring_cut.json`
- `knowledge/techniques/story_pacing/scripted_montage_blueprint.json`
- `knowledge/techniques/story_pacing/character_pov_action_sequence.json`
- `knowledge/techniques/transition/eye_trace_continuity_cut.json`
- `knowledge/techniques/sound_design/licensed_needle_drop_retention.json`
- `knowledge/techniques/retention/artful_practical_audience_balance.json`
- `knowledge/techniques/genre_workflow/documentary_sensitive_tone_alignment_001.json`
- `knowledge/techniques/story_pacing/motivated_broll_story_sequence_001.json`
- `knowledge/techniques/qc/qc_narration_visual_character_alignment_001.json`
- `knowledge/techniques/genre_workflow/movie_recap_paragraph_scene_workflow_001.json`
- `knowledge/techniques/nle_workflow/movie_recap_chop_delete_flip_speed_transform_001.json`
- `knowledge/techniques/transition/movement_continuity_broll_001.json`
- `knowledge/techniques/retention/longform_confident_pacing_001.json`
- `knowledge/techniques/transition/meaningful_match_cut_001.json`
- `knowledge/techniques/sound_design/documentary_audio_intelligibility_001.json`
- `knowledge/techniques/genre_workflow/ethical_poetic_reordering_001.json`
- `knowledge/techniques/story_pacing/story_perspective_editing_protagonist_pov_001.json`
- `knowledge/techniques/story_pacing/story_dunning_kruger_narrative_arc_001.json`
- `knowledge/techniques/retention/retention_goal_gap_open_loop_001.json`
- `knowledge/techniques/story_pacing/story_expert_pedestal_intro_001.json`
- `knowledge/techniques/story_pacing/story_pickup_insert_for_perspective_001.json`
- `knowledge/techniques/sound_design/sound_music_characterization_001.json`
- `knowledge/techniques/story_pacing/story_repetition_scale_accumulation_001.json`
- `knowledge/techniques/retention/retention_invitation_intro_question_loops_001.json`
- `knowledge/techniques/story_pacing/story_worldbuilding_before_promise_001.json`
- `knowledge/techniques/sound_design/sound_sensory_world_characterization_001.json`
- `knowledge/techniques/motion/motion_reality_fantasy_visual_treatment_001.json`
- `knowledge/techniques/sound_design/sound_music_audition_story_fit_001.json`
- `knowledge/techniques/beat_sync/beat_sync_needle_drop_action_cue_001.json`
- `knowledge/techniques/sound_design/sound_diegetic_music_bridge_001.json`
- `knowledge/techniques/sound_design/sound_beauty_horror_tonal_contrast_001.json`
- `knowledge/techniques/nle_workflow/nle_rough_cut_second_pass_workflow_001.json`
- `knowledge/techniques/nle_workflow/nle_j_l_cut_dialogue_smoothing_001.json`
- `knowledge/techniques/motion/motion_keyframe_focus_zoom_hold_001.json`
- `knowledge/techniques/motion/motion_overlay_readability_focus_stack_001.json`
- `knowledge/techniques/sound_design/sound_audio_leveling_track_hygiene_001.json`
- `knowledge/techniques/sound_design/sound_sfx_variation_exaggeration_001.json`
- `knowledge/techniques/retention/retention_frontload_first_30_seconds_001.json`
- `knowledge/techniques/retention/retention_intro_packaging_alignment_001.json`
- `knowledge/techniques/retention/retention_overediting_value_supplement_001.json`
- `knowledge/techniques/genre_workflow/podcast_ai_shorts_review_refine_001.json`
- `knowledge/techniques/retention/retention_shortform_claim_hook_001.json`
- `knowledge/techniques/retention/retention_high_energy_hook_rest_001.json`
- `knowledge/techniques/motion/motion_subject_tracking_statement_zoom_001.json`
- `knowledge/techniques/motion/motion_show_dont_tell_visual_stack_001.json`
- `knowledge/techniques/captions/captions_two_word_social_subtitles_001.json`
- `knowledge/techniques/captions/captions_premiere_one_word_pop_fade_001.json`
- `knowledge/techniques/retention/retention_hook_text_design_sequence_001.json`
- `knowledge/techniques/motion/motion_filler_background_text_animation_001.json`
- `knowledge/techniques/motion/motion_broll_text_readability_sequence_001.json`
- `knowledge/techniques/motion/motion_full_screen_object_animation_001.json`
- `knowledge/techniques/motion/motion_adjustment_zoom_blur_flow_001.json`
- `knowledge/techniques/nle_workflow/davinci_vertical_short_project_setup_001.json`
- `knowledge/techniques/motion/davinci_fusion_spline_zoom_animation_001.json`
- `knowledge/techniques/captions/davinci_textplus_premium_caption_stack_001.json`
- `knowledge/techniques/transition/davinci_white_flash_transition_001.json`
- `knowledge/techniques/nle_workflow/davinci_power_bins_preset_workflow_001.json`
- `knowledge/techniques/nle_workflow/davinci_timeline_shortcuts_efficiency_001.json`
- `knowledge/techniques/nle_workflow/nle_shortform_project_asset_template_system_001.json`
- `knowledge/techniques/story_pacing/story_reel_segment_ideation_board_001.json`
- `knowledge/techniques/nle_workflow/nle_fourk_to_1080_reel_prep_001.json`
- `knowledge/techniques/motion/aftereffects_eye_locked_zoom_text_parenting_001.json`
- `knowledge/techniques/motion/aftereffects_text_animation_preset_stack_001.json`
- `knowledge/techniques/motion/aftereffects_track_matte_texture_cutout_001.json`
- `knowledge/techniques/motion/aftereffects_null_camera_scene_motion_001.json`
- `knowledge/techniques/motion/aftereffects_path_counter_motion_001.json`
- `knowledge/techniques/motion/aftereffects_branded_background_texture_system_001.json`
- `knowledge/techniques/nle_workflow/premiere_aftereffects_render_finish_roundtrip_001.json`
- `knowledge/techniques/retention/retention_audience_style_idea_gate_001.json`
- `knowledge/techniques/story_pacing/story_secondary_story_script_layer_001.json`
- `knowledge/techniques/nle_workflow/nle_script_color_code_asset_map_001.json`
- `knowledge/techniques/nle_workflow/nle_music_first_voiceover_assembly_001.json`
- `knowledge/techniques/motion/motion_sketch_to_animation_ladder_001.json`
- `knowledge/techniques/motion/motion_premiere_text_pop_scale_preset_001.json`
- `knowledge/techniques/motion/motion_screen_blend_texture_overlay_001.json`
- `knowledge/techniques/motion/motion_capcut_switch_focus_depth_blur_001.json`
- `knowledge/techniques/motion/motion_documentary_research_overlay_timelapse_001.json`
- `knowledge/techniques/color/color_archival_film_frame_treatment_001.json`
- `knowledge/techniques/motion/motion_capcut_documentary_parallax_collage_001.json`
- `knowledge/techniques/sound_design/sound_isolated_sfx_design_pass_001.json`
- `knowledge/techniques/qc/qc_publish_threshold_creative_iteration_001.json`
- `knowledge/techniques/retention/retention_first_three_second_dynamic_zoom_hook_001.json`
- `knowledge/techniques/retention/retention_human_imperfection_pattern_interrupt_001.json`
- `knowledge/techniques/story_pacing/story_contrast_intensity_drop_001.json`
- `knowledge/techniques/sound_design/sound_realistic_foley_cutaway_001.json`
- `knowledge/techniques/color/color_warm_nostalgic_hope_grade_001.json`
- `knowledge/techniques/nle_workflow/nle_stacked_timeline_versioning_001.json`
- `knowledge/techniques/captions/captions_organic_low_focus_social_subtitles_001.json`
- `knowledge/techniques/motion/motion_vox_paper_grid_background_001.json`
- `knowledge/techniques/motion/motion_typographic_explainer_intro_collage_001.json`
- `knowledge/techniques/motion/motion_map_trace_route_pan_001.json`
- `knowledge/techniques/motion/motion_animated_bar_chart_wipe_001.json`
- `knowledge/techniques/motion/motion_document_highlight_focus_pan_001.json`
- `knowledge/techniques/motion/motion_word_focus_screenshot_sequence_001.json`
- `knowledge/techniques/motion/motion_layered_cutout_infographic_scene_001.json`
- `knowledge/techniques/motion/motion_stop_motion_fps_lag_texture_001.json`
- `knowledge/techniques/sound_design/sound_infographic_motion_sfx_sync_001.json`
- `knowledge/techniques/nle_workflow/nle_capcut_compound_graphics_workflow_001.json`
- `knowledge/techniques/typography/typography_font_family_role_selection_001.json`
- `knowledge/techniques/typography/typography_contrast_hierarchy_stack_001.json`
- `knowledge/techniques/typography/typography_sentence_structure_line_breaks_001.json`
- `knowledge/techniques/typography/typography_live_action_whitespace_integration_001.json`
- `knowledge/techniques/typography/typography_tracking_kerning_line_spacing_qc_001.json`
- `knowledge/techniques/typography/typography_roi_readability_ad_text_001.json`
- `knowledge/techniques/captions/captions_capcut_adaptive_texture_animation_001.json`
- `knowledge/techniques/captions/captions_capcut_player3_smooth_caption_compounds_001.json`
- `knowledge/techniques/typography/typography_capcut_apple_slide_up_text_001.json`
- `knowledge/techniques/typography/typography_capcut_axis_stretch_emphasis_001.json`
- `knowledge/techniques/typography/typography_capcut_opacity_flicker_tick_001.json`
- `knowledge/techniques/typography/typography_capcut_srt_number_countup_001.json`
- `knowledge/techniques/typography/typography_capcut_perspective_freeze_text_001.json`
- `knowledge/techniques/typography/typography_capcut_color_change_highlight_wipe_001.json`
- `knowledge/techniques/typography/typography_capcut_staggered_blur_glitch_reveal_001.json`
- `knowledge/techniques/typography/typography_capcut_split_mask_gradient_type_001.json`
- `knowledge/techniques/typography/typography_capcut_font_shift_loop_001.json`
- `knowledge/techniques/typography/typography_capcut_outline_reveal_chroma_001.json`
- `knowledge/techniques/typography/typography_capcut_film_strip_glow_reveal_001.json`
- `knowledge/techniques/typography/typography_programmatic_text_mask_highlight_glow_001.json`
- `knowledge/techniques/typography/typography_remotion_sequence_local_kinetic_presets_001.json`
- `knowledge/techniques/typography/typography_remotion_seeded_scramble_glitch_001.json`
- `knowledge/techniques/typography/typography_remotion_stagger_spring_text_motion_001.json`
- `knowledge/techniques/typography/typography_remotion_blur_scale_morph_001.json`
- `knowledge/techniques/typography/typography_ffmpeg_drawtext_timed_overlay_001.json`
- `knowledge/techniques/typography/typography_ffmpeg_fade_pop_envelope_001.json`
- `knowledge/techniques/captions/typography_ffmpeg_sequential_word_drawtext_001.json`
- `knowledge/techniques/typography/programmatic_remotion_prores4444_alpha_overlay_export_001.json`
- `knowledge/techniques/typography/programmatic_remotion_webm_alpha_overlay_export_001.json`
- `knowledge/techniques/motion/programmatic_remotion_offthreadvideo_alpha_import_001.json`
- `knowledge/techniques/typography/programmatic_remotion_css_mask_text_reveal_001.json`
- `knowledge/techniques/motion/programmatic_ffmpeg_alphamerge_alpha_mask_pipeline_001.json`
- `knowledge/techniques/motion/programmatic_ffmpeg_alphaextract_mask_reuse_001.json`
- `knowledge/techniques/motion/programmatic_ffmpeg_geq_procedural_alpha_masks_001.json`
- `knowledge/techniques/motion/programmatic_ffmpeg_in_place_wipe_reveal_alpha_001.json`
- `knowledge/techniques/nle_workflow/davinci_project_library_media_pool_setup_001.json`
- `knowledge/techniques/sound_design/davinci_waveform_audio_sync_media_pool_001.json`
- `knowledge/techniques/nle_workflow/davinci_edit_page_in_out_story_assembly_001.json`
- `knowledge/techniques/story_pacing/davinci_anchor_shot_action_cutting_001.json`
- `knowledge/techniques/motion/davinci_fusion_node_compositing_basics_001.json`
- `knowledge/techniques/color/davinci_color_management_primary_look_001.json`
- `knowledge/techniques/sound_design/davinci_fairlight_dialogue_ambience_bus_mix_001.json`
- `knowledge/techniques/nle_workflow/davinci_deliver_codec_render_queue_archive_001.json`
- `knowledge/techniques/retention/retention_intro_format_gate_001.json`
- `knowledge/techniques/retention/retention_brand_authority_outcome_intro_001.json`
- `knowledge/techniques/motion/motion_premium_intro_text_logo_flicker_001.json`
- `knowledge/techniques/sound_design/sound_frame_locked_intro_sfx_drums_001.json`
- `knowledge/techniques/nle_workflow/nle_capcut_keyframe_spacing_control_001.json`
- `knowledge/techniques/nle_workflow/nle_capcut_compound_clip_animation_unlock_001.json`
- `knowledge/techniques/motion/motion_capcut_graph_curve_easing_001.json`
- `knowledge/techniques/motion/motion_capcut_graph_zoom_stack_001.json`
- `knowledge/techniques/compositing/motion_still_image_environment_composite_001.json`
- `knowledge/techniques/compositing/motion_masked_firelight_strobe_reflection_001.json`
- `knowledge/techniques/color/color_low_key_firelight_scene_unification_001.json`
- `knowledge/techniques/compositing/compositing_capcut_subject_sandwich_cutout_001.json`
- `knowledge/techniques/typography/typography_capcut_chroma_video_text_portal_001.json`
- `knowledge/techniques/motion/motion_capcut_auto_subject_sticker_tracking_001.json`
- `knowledge/techniques/motion/motion_capcut_slide_on_photo_stack_001.json`
- `knowledge/techniques/retention/motion_capcut_chapter_card_slide_interrupt_001.json`
- `knowledge/techniques/compositing/compositing_capcut_pip_border_chroma_shape_001.json`
- `knowledge/techniques/compositing/compositing_locked_camera_split_mask_illusion_001.json`
- `knowledge/techniques/compositing/compositing_capcut_green_screen_vfx_insert_001.json`
- `knowledge/techniques/motion/motion_capcut_overlay_path_keyframes_001.json`
- `knowledge/techniques/motion/motion_keyframed_tilt_tension_001.json`
- `knowledge/techniques/motion/motion_capcut_cutout_character_walk_001.json`
- `knowledge/techniques/color/color_keyframed_saturation_shift_001.json`
- `knowledge/techniques/sound_design/sound_music_ducking_volume_keyframes_001.json`
- `knowledge/techniques/color/color_filter_strength_music_reveal_001.json`
- `knowledge/techniques/beat_sync/beat_sync_capcut_speed_match_twixtor_001.json`
- `knowledge/techniques/motion/motion_capcut_character_mask_shadow_glow_001.json`
- `knowledge/techniques/nle_workflow/nle_capcut_heavy_overlay_prerender_workflow_001.json`
- `knowledge/techniques/transition/transition_capcut_turbulent_wide_angle_shake_001.json`
- `knowledge/techniques/sound_design/sound_anime_edit_sfx_voice_line_spotting_001.json`
- `knowledge/techniques/motion/motion_capcut_effect_tail_extension_001.json`
- `knowledge/techniques/compositing/compositing_capcut_eye_power_overlay_001.json`
- `knowledge/techniques/motion/motion_capcut_pendulum_transition_movement_001.json`

## Timing Rules

- Emotional holds are long enough to register but not so long they become empty.
- Dense shots, maps, signs, documents, or destruction have enough scan time.
- Fast cuts are justified by story, format, or energy rather than insecurity.
- Jarring cuts have a named emotional purpose.
- Goal-gap openings do not fully satisfy the promise too early.
- Pickup inserts are long enough to read and not so long they stall the pace.
- Delayed long-form intros close at least one early question loop before adding more mystery.
- Pause beats are long enough to land but short enough to avoid dead air.
- High-energy music cues land within 1-2 frames of the intended visual turn.
- Music-led sections have a planned duck, filter, or exit before story-critical dialogue.
- No accidental opening dead air, breath, or hesitation remains unless intentionally kept.
- Short-form dead air over 300 ms is removed unless it has a named purpose.
- J/L cuts and audio crossfades sound natural and do not mislead.
- AI short start and end trims contain a complete premise and payoff.
- Named-person, character, place, object, product, UI, proof, or event handoffs start early enough that the rounded player timestamp already shows the matching visual.
- Feed-first shorts establish a clear claim, result, question, or proof within five seconds.
- Dense high-energy hooks include a readable rest beat when the explanation needs it.
- Resolve vertical shorts have project settings and crop checked before captions are approved.
- Premiere generated captions are corrected before being upgraded to graphics.
- Caption pop motion completes before the word needs to be read.
- Adjustment zoom-blur effects settle before the viewer needs to inspect text, UI, product, or proof.
- Prepared AE renders are exported only after the vertical sequence, sync, rough cut, and basic correction are checked.
- Final SFX, music, and captions are checked after the AE animation render is aligned.
- Voiceover-led music-first assemblies are rechecked after final visuals and SFX are added.
- Meaningful pauses are preserved only when they have a named story, joke, tension, emotion, or comprehension job.
- Slow human shorts still establish motion, proof, face, or a clear reason to continue in the first 3-5 seconds.
- Short-form black/drop gaps stay under one second unless intentionally cinematic.
- Human pattern interrupts exit before they become unshaped dead air.
- Map routes, chart bars, document highlights, and screenshot focus beats hold long enough to read.
- Low-FPS/posterize texture is applied after timing lock and checked for readability.
- Typography hierarchy appears early enough that the impact word or phrase is understood before the text clears.
- Text animation settles before the viewer needs to read the phrase.
- Remotion text components use Sequence-local timing and hold the readable final
  state after masks, springs, glitches, or morphs.
- FFmpeg drawtext overlays use explicit enable windows; word chains are split or
  moved to ASS/Remotion before they become brittle.
- Viral text effects resolve to a readable state before the next phrase, caption,
  proof, or CTA competes.
- Player 3 caption compounds, highlight wipes, gradient text, staggered reveals,
  foreground-lift text, and glow sweeps are readable at phone size before the next
  phrase competes.
- Number counters slow or hold on the verified final value.
- Full Resolve timelines have no accidental leading black, gaps, wrong source
  ranges, or unreviewed Smart Insert/Sync Bin placements.
- Formal social intros stay around 3-5 seconds, and show/podcast/course intros stay around 10-15 seconds maximum unless the brief explicitly says otherwise.
- Formal intros deliver brand, proof, and outcome before bodyStartFrame; logo-only time does not count as viewer value.
- CapCut-style keyframe spacing creates the intended speed: close for intentional snaps, wider for slow movement, and held when the final state must be read.
- Music ducking keyframes lower music before speech begins and restore only after the phrase clears.
- Music-linked filter reveals start after speech clears unless the overlap has a
  named creative reason and speech remains intelligible.
- Speed-matched action peaks land within the intended beat tolerance and remain readable.
- Eye/power-overlay reveal frames land on the intended beat after speed adjustment and replacement.
- Transition shakes are tuned after turbulent/wide-angle effects and settle before the next action pose.
- Pendulum movement is checked with the final transition stack, not only in isolation.
- Effect-tail extensions clear before the next main beat.
- Graph curves create the intended start speed, acceleration/deceleration, and ending feel.
- Motion blur is added only after graph timing, scale, and position are approved.
- Still-image overlays cover the intended beat without visible loops, hard starts,
  or tail gaps.
- Local flicker starts and ends with the visible or implied source light.
- Export/re-import subject-sandwich effects are baked only after the behind-layer
  timing is stable.
- Chapter cards, photo stacks, and tracked stickers clear before the next focal
  beat or caption region competes.
- Switch-focus blur leaves at least one subject readable during the handoff.
- Documentary title animations settle before the word, source label, or claim
  needs to be read.
- Research timelapses and filmed-screen sections hold proof frames long enough
  for source context to register.

## Motion Rules

- Movement continuity is intentional in smooth B-roll strings.
- Motion graphics and transitions match the subject tone.
- Match cuts imply only the intended relationship.
- Effects do not make action geography unreadable.
- Small-object action stays center-frame or clearly guided.
- Reality/fantasy visual treatments are consistent and exceptions are intentional.
- Movement-direction breaks have a story reason, striking-image reason, or sound beat.
- Focus zooms land near the spoken reference or beat and hold long enough to read.
- Keyframed focus moves do not drift after they should be steady.
- Overlays, captions, lower thirds, and title text do not compete for primary focus.
- Speaker tracking preserves face, hands, captions, and proof in the final crop.
- Visual stack layers are synced to the spoken concept and clear before the next idea.
- Fusion effects use intentional Spline easing and affect only the intended clip range.
- White flash transitions are brief and do not hide captions or key action.
- Hook text has one clear hierarchy and does not duplicate ordinary captions.
- Filler cards, B-roll text, and full-screen object animations are chosen by line importance.
- Adjustment layers affect only the intended clips and do not crop caption-safe areas.
- Speaker eyes remain stable through AE zooms.
- Original footage and any rotoscope/cutout duplicates share intended transform motion.
- Camera/null moves do not reveal empty background edges.
- Dense AE elements clear with out animations or motivated transitions.
- Focus points stay stable across zooms and cuts using guides, center, eyeline, or rule-of-thirds targets.
- Screen-blend texture overlays have a named highlight, transition, or mood job and remain readable.
- Text pop presets settle before the phrase needs to be read.
- Dynamic zoom hooks preserve the first focal point and do not crop proof, face, or captions.
- Human interrupt crops or zooms make the reaction readable without making it feel staged.
- Infographic compounds/nests are named, editable, and do not crop maps, charts, labels, or cutouts.
- Route arrows, highlight masks, and chart wipes reveal rather than hide evidence.
- Live-action text sits in negative space or tracks cleanly without covering the subject, product, UI, or evidence.
- CapCut text-behind-object, outline reveal, and video-in-text effects preserve
  readable text edges and clean foreground/key/blend edges.
- Premium text mask effects start and end outside the word when the effect is a
  wipe or shine, with no pre-glow, tail glow, or lingering blur.
- Programmatic text mask effects align base and duplicate text layers exactly,
  reveal sharp and glow layers together, and render contact sheets for start,
  midpoint, hold, and clear frames.
- Font, line break, spacing, and hierarchy are checked before approving motion presets.
- Fusion node order, trackers, masks, Magic Mask edges, and Edit page keyframes
  are checked across the full affected range.
- Intro motion has one primary focus at a time: brand or show identity, external proof or authority, then viewer outcome.
- Intro flicker, font changes, motion blur, and 3D camera movement preserve phone-size readability.
- CapCut overlay paths, cutout walks, zooms, tilts, and manual tracking preserve captions, faces, proof, UI, products, map labels, and action.
- Every CapCut property keyframe changes only the intended property unless a
  multi-property move is explicitly named.
- Keyframed tilt/rotation moves reveal no black corners or unintended frame edges.
- Character masks, glow, shadow, and flicker preserve clean edges through the full affected range.
- Heavy overlay pre-renders or replacements preserve handles, duration, and a revision path.
- Temporary black spacers or placeholders used during CapCut replacement are removed before final export.
- Turbulent/wide-angle distortion does not bend subjects, captions, products, or proof beyond recognition.
- Eye/power overlays stay aligned through playback and do not hide expression.
- Graph-shaped zooms keep the focus subject centered and readable through the full curve.
- Extreme stacked zooms preserve enough source detail for delivery.
- Still-image environmental overlays align with plausible source regions and do
  not create unmotivated motion.
- Screen/Add overlays remove black backgrounds cleanly and masks remain invisible
  at full playback speed.
- Local strobe/flicker affects only the reflected region, not the whole frame,
  unless full-scene lighting is intentionally motivated.
- Subject-sandwich composites use the correct layer order and frame alignment.
- Chroma-key text portals, PiP borders, and green-screen VFX have clean keys with
  no spill, specks, or erased detail.
- Split-mask and clone effects were filmed from locked camera settings and masks
  align to believable object edges.
- Switch-focus blur ramps, parallax moves, and copied background transforms keep
  one clear focus and do not move the entire scene as a flat layer.
- Filmed-screen texture preserves UI, cursor action, source text, and captions.
- Archival frames and particles do not hide faces, dates, source labels, or proof.

## Sound Rules

- Decode pass completes without errors.
- Audio has no clipping, harsh pops, or unintelligible speech.
- Music/SFX duck under important dialogue and testimony.
- Music rights and platform safety are documented where relevant.
- Related B-roll ambience is consistent.
- Music tone matches the character state or narrative phase.
- Sensory SFX cues have named story jobs and do not mask VO re-entry.
- Abrupt silence resets land on grounded images or natural sound rather than feeling like an audio error.
- Important music tracks are licensed, platform-safe, or clearly marked temp-only.
- Diegetic music bridges have plausible source sound before opening to full mix.
- Sensitive music contrast creates critique, grief, or discomfort rather than glamour.
- Dialogue, music, SFX, and ambience remain controllable in the timeline or render plan.
- Quiet story-critical words are repaired without causing clipped peaks.
- Repeated SFX cues use variation and land on real impacts or motion.
- Music fits the scene pace and tone rather than hiding a cut that should be tighter.
- Whooshes, hits, and reverse hits land within 1-2 frames of intended motion or reveal when sync matters.
- Background music stays low enough that speech remains intelligible without captions.
- B-roll source audio is muted or intentionally mixed under A-roll.
- In-app Resolve voiceover recordings are checked for level, noise, and timing.
- Short-form music candidates are checked for tone fit, speech clarity, and license/platform safety.
- AE-roundtrip SFX land on visible motion frames and required dialogue, music, and SFX tracks are unmuted before export.
- Isolated SFX spotting is followed by a full-mix check with dialogue and music restored.
- Foley for human cutaways matches visible movement and stays below dialogue.
- Contrast drops follow a clear build and re-enter speech or ambience cleanly.
- Infographic SFX land on meaningful visible events and stay below narration.
- Viral text ticks/clicks land on visible flicker, font-shift, counter, or reveal
  frames and end with the text animation.
- Glitch or shimmer cues for staggered, highlight, or glow text reveals end with
  the visible effect and stay below speech.
- Documentary graphics music is licensed/platform-safe or marked temp-only and exits cleanly.
- Fairlight tracks and buses route to the main output; dialogue, ambience, music,
  and SFX are balanced in the full mix, not only while soloed.
- Intro SFX land on visible logo, text, flicker, underline, cut, camera, or transition events.
- Intro music/SFX duck, fade, or resolve before proof quotes or the first body line become hard to understand.
- Music remains intelligible-safe under CapCut-style ducking and license/platform status is documented.
- Music-duck values fit the actual song and voice; captions are not rescuing a
  buried mix.
- AMV/action SFX and voice lines land on visible jobs, stay mix-safe, and have license/platform status.
- Eye, lightning, glass, entrance, and voice-line cues use event-appropriate sounds and land on their visible frames.
- Environmental ambience, such as fire or wind, stays below speech and has
  license/source status when used.
- CapCut pro-effect SFX land on visible events and imported/app-library audio is
  licensed, platform-safe, or marked temp-only.
- Research risers build to a visible discovery or claim and stay below narration.
- Archival/projector/screen texture sounds remain subtle and licensed or
  platform-safe.

## Caption Rules

- Captions are readable and correctly timed.
- Captions do not cover important faces, UI, products, maps, evidence, or action.
- Hard-to-hear story-critical lines are subtitled.
- Lower thirds do not block needed subtitles.
- Captions do not cover protagonist reactions, object inserts, or small-action demonstrations.
- Captions do not cover opening clues, proof screenshots, treatment boundaries, or body language that closes a loop.
- Captions support music-heavy dialogue but do not excuse a buried mix.
- Captions do not cover the visual turn receiving a music drop.
- AI-generated captions are corrected for wording, timing, emphasis, line breaks, and filler clutter.
- Captions remain readable over both bright and dark footage at delivery size.
- Captions do not cover title text, proof cards, speaker faces, UI, products, or the action being discussed.
- One- or two-word caption chunks are used only where they improve pace and readability.
- Duplicate captions remain visible, repositioned, simplified, or have a documented user-approved suppression exception where visual text already carries the idea.
- Resolve auto captions and Text+ premium captions do not collide or duplicate unintentionally.
- Premiere one-word captions are readable at phone size and do not collide with hook text, B-roll text, or full-screen hierarchy text.
- Duplicate captions remain visible, repositioned, simplified, or have a documented user-approved suppression exception when another text layer already carries the idea.
- Captions are visible, repositioned, faded, or explicitly approved for suppression over dense AE text, counters, paths, icons, and CTA elements.
- Organic low-focus captions remain readable while letting faces, proof, and human reactions stay primary.
- Captions do not cover map labels, chart data, source documents, screenshot highlights, or title hierarchy.
- Caption and typography line breaks form readable phrases and do not isolate filler words as emphasis.
- Adaptive caption animations are applied only after auto-caption wording, timing,
  and line breaks are corrected.
- Designed text and ordinary captions do not duplicate unless accessibility requires both.
- Ordinary captions are visible, repositioned, or explicitly approved for suppression during designed intro text when both layers cannot coexist cleanly.
- Captions avoid flickering reflections, fire, and moving sky regions when those
  areas change contrast frame to frame.
- Captions avoid foreground cutout edges, PiP regions, tracked stickers, split
  mask boundaries, chroma-key portals, and VFX impact frames.
- Captions avoid switch-focus targets, research documents, filmed-screen UI,
  archival frame borders, and dense parallax title/cutout intersections.

## Color Rules

- Color preserves skin tone, eye detail, evidence, product/brand color, maps, and readable detail.
- Grade does not clash with subject tone or hide important information.
- Reality/fantasy grades or treatments preserve evidence readability and facial/body-language cues.
- Beauty-over-horror music is not paired with a grade that glamorizes harm or hides evidence.
- Premiere color correction for AE prep preserves skin, detail, and caption/overlay readability before the animation pass.
- Viral-style correction preserves faces, proof, text, overlays, and compression cleanliness.
- Warm nostalgic grades preserve skin, proof, caption contrast, and clean compression before glow, grain, blur, or vignette are approved.
- Warm paper/grid palettes preserve map, chart, document, and screenshot readability.
- Text color, gradient, shadow, stroke, and blend mode preserve crisp readable edges on the final grade.
- Highlight bars, feathered split masks, and Glow effects preserve crisp letter
  edges and do not create muddy compression.
- Live-action typography color matches scene temperature only as far as readability allows.
- Resolve color management, scopes, hero stills, shot matching, timeline looks,
  and secondaries preserve faces, proof, captions, and compression cleanliness.
- Keyframed saturation shifts have a named purpose and preserve faces, proof, products, brand colors, and caption contrast.
- Filter-strength reveals preserve captions, faces, proof, UI, products, and
  brand colors at full strength.
- Low-key still-image composites preserve shadow detail, control bright overlays,
  and keep captions readable on both the darkest and brightest frames.
- Archival film treatments, glass textures, particles, fade, vignette, and HSL
  unification preserve source text, dates, faces, captions, and labels.

## Tool Implementation Notes

- `ffprobe` should confirm expected duration, streams, resolution, and frame rate.
- Run a decode pass on final outputs.
- Use contact sheets around openings, emotional beats, dense B-roll, transitions, maps, and ending.
- Use waveform/loudness checks after audio, music, or SFX changes.
- Track source timestamps for documentary reorders.
- Track open loops and verify each has closure or reframing.
- Check pickup inserts against adjacent shots for truth, continuity, color, and sound bed.
- For invitation intros, mark first-frame question, early closure, worldbuilding, proof, call to adventure, and promise delivery.
- Review treatment-heavy sequences for black edges, lost evidence, caption collisions, and accidental grammar breaks.
- For music-led sections, review license status, cue markers, waveform peaks, duck points, and rejected track notes.
- Compare stylized sensitive-music versions against a restrained version before approval.
- Render first-30-second and vertical-short previews at delivery size before final batch export.
- Use waveform/loudness review after local dialogue keyframes, music ducking, or SFX changes.
- Review AI-generated short candidates cold and mark approved/rejected before export or scheduling.
- Confirm export range, resolution, aspect ratio, frame rate, and filename before rendering.
- For visual-stack shorts, render phone-size hook and full-short previews before final export.
- Check first five seconds, claim support, rest beat, subject tracking, captions, SFX sync, and final layout.
- For Resolve projects, check vertical settings, Fusion Spline, Text+, Power Bin presets, shortcut move sync, B-roll audio, and render output.
- For Premiere Reel workflows, review rough cut, J-cuts, caption graphics, hook text, body visuals, adjustment-layer ranges, music candidates, and final vertical render.
- For AE Reel workflows, review the prepared render, segment ideation board, AE render duration/resolution/frame rate, enabled effects, duplicate render audio, final caption continuity, any user-approved suppression exception, SFX sync, and unmuted export tracks.
- For viral YouTube workflows, review target audience, idea gate, script structure, secondary story, script asset tags, music license, animation sketches, SFX full mix, color readability, and publish blockers.
- For slow human shorts, review first-seconds hook, timeline version choice, human-interrupt purpose, micro-drop duration, foley cue frames, restrained captions, and warm grade readability.
- For Vox-inspired graphics, review asset rights, source context, map truth, chart values, document highlight legibility, compound names, SFX cue sync, music license, and low-FPS bypasses.
- For typography-heavy scenes, review font family role, impact word, line breaks, tracking/kerning/line spacing, negative-space placement, contrast, and ad/CTA readability.
- For programmatic typography, review fontfile availability, generated filter
  graph or component metadata, Sequence-local timing, deterministic seed policy,
  duplicate-layer alignment, mask/glow bounds, caption continuity, any user-approved suppression exception, and
  contact-sheet frames.
- For transparent overlays, review alphaFormat, codec, pixelFormat, resolution,
  fps, durationFrames, no-background preflight, mask polarity, `ffprobe` output,
  bright/dark edge checks, and import behavior in the receiving tool.
- For FFmpeg alpha composites, preview the grayscale mask before compositing and
  verify `alphaextract`/`alphamerge`/`maskedmerge`/`overlay` filter choice against
  the intended operation.
- For premium CapCut text scenes, review compound editability, duplicate text
  alignment, mask keyframes, feather/glow values, foreground cutout edges, SFX
  cue range, caption continuity, and any user-approved suppression exception.
- For Resolve full-workflow projects, review Media Pool imports, bins/keywords,
  audio sync/channel mapping, Edit/Cut placement, Fusion node order, Color
  management/stills/scopes, Fairlight routing, Deliver profile, and watched export.
- For formal intro approval, mark introAllowed, format, durationCap, brandBeat, proofBeat, outcomeBeat, textLayer roles, SFX event frames, and bodyStartFrame.
- For CapCut keyframe approval, mark property keyframes, focus target, hold frames, cleanup frame, caption safe areas, music duck ranges, color-shift purpose, and asset/license notes.
- For CapCut AMV/action approval, mark beatFrame, actionPeakFrame, clipSpeed, maskLayer, preRenderRange, transitionPeakFrame, SFX cueFrame, voiceLineStartFrame, and source/license status.
- For CapCut graph zoom approval, mark curveIntent, graphShape, firstPassScale, secondPassScale, subjectCentering, motionBlur, blend, renderPasses, and qualityRisk.
- For still-image composite approval, mark baseStill, overlayAssets, blend modes,
  mask/feather regions, local light source, final grade, brightest/darkest review
  frames, and asset license notes.
- For CapCut pro compositing approval, mark layerOrder, preparedRenderRef,
  foregroundSourceRef, chromaKeyColor, trackingTarget, splitMaskLine, impactFrame,
  edgeReviewFrames, captionSafeRegions, and source/license status.
- For CapCut documentary effects, mark sourceType, cutoutSourceRefs, maskFeather,
  focusBlurRamps, parallaxTargets, backgroundMotionReduction, textureOpacity,
  archivalValues, titleRoles, captionSafeRegions, and source/license status.

## Common Mistakes

- Checking only source timelines instead of rendered output.
- Missing caption collisions because the preview was not checked at delivery size.
- Accepting bad sound because the image looks good.
- Letting repeated B-roll and weak focal points slip through a rushed edit.
- Ignoring the meaning created by adjacent shots or match cuts.
- Applying short-form QC assumptions to long-form documentary.
- Missing the protagonist perspective because the edit only shows impressive visuals.
- Opening a goal loop without closing it.
- Using a pickup that fabricates rather than clarifies.
- Delaying the promise without enough trust closure or worldbuilding value.
- Treating confusion as a hook when no specific question is opened.
- Applying visual treatment so inconsistently that reality and fantasy become unclear.
- Accepting a music choice because it is famous or exciting while the story tone gets worse.
- Letting music bury dialogue and assuming captions solve it.
- Keeping a sensitive music contrast after it feels too far for the subject.
- Checking the timeline but not the exported file.
- Trusting an exact sub-second EDL boundary while the viewer-facing rounded timestamp still shows the previous character, product, object, or proof point.
- Forgetting to review the first 30 seconds after polishing later sections.
- Publishing AI clips without verifying context, captions, layout, and start/end trims.
- Letting captions and overlays cover the proof point they were meant to explain.
- Exporting a selected range accidentally instead of the full intended sequence.
- Accepting a viral-sounding hook that the short does not support.
- Forgetting to add a rest beat after a visually overloaded hook.
- Letting one- or two-word captions cover visual text or proof.
- Using preset whooshes and hits that are louder than the speaker.
- Saving an unchecked Resolve effect into Power Bins.
- Leaving Fusion motion linear or crop-unsafe.
- Forgetting that shortcut-based timeline moves can desync captions or SFX.
- Leaving unwanted B-roll audio under the talking head.
- Converting captions to graphics before correcting auto-caption errors.
- Leaving duplicate captions under designed hook or B-roll text.
- Reusing adjustment zoom layers without checking the affected range.
- Selecting music because it is trendy while the tone, dialogue clarity, or license status is wrong.
- Forgetting to re-enable heavy AE effects before render.
- Exporting a prepared or final Premiere render with required audio tracks muted.
- Leaving duplicate audio from the imported AE render under the original dialogue.
- Checking the AE comp but not watching the imported render inside the final Premiere timeline.
- Publishing a viral-style edit without checking whether the target audience and idea promise are clear.
- Treating optional polish ideas as blockers after core QC passes.
- Doing an isolated SFX pass and forgetting to restore the full mix.
- Exporting simple animations too soft for timeline zooms.
- Calling a loose cut "slow editing" when the pauses have no named purpose.
- Leaving a black/drop gap that looks like a broken export.
- Letting warm color, captions, or foley overpower the human moment.
- Copying a protected publisher identity or using unlicensed logos/assets.
- Exporting low-FPS graphic texture that makes text or data unreadable.
- Using charts or map routes without source/truth checks.
- Approving typography that looks stylish in the editor but fails at phone size.
- Approving viral text effects because they are trendy while the word, number, or
  cutout is unreadable.
- Approving premium text effects while duplicate text is misaligned, the glow
  leaks before the word, or the foreground-lift mask chatters in motion.
- Using a generated number counter without verifying the final value and units.
- Leaving tick SFX after the visible text change has ended.
- Using heavy shadow, gradient, blend mode, or tight tracking that makes text harder to read.
- Approving Remotion glitch or scramble text that uses non-deterministic random
  values and changes between preview and render.
- Approving FFmpeg generated text without checking fontfile availability,
  generated filter graph reproducibility, and representative contact sheets.
- Letting a programmatic glow layer leak before the mask reaches the word or
  remain after the sweep exits.
- Approving transparent overlays without verifying alpha, causing black boxes,
  keyed fringes, or haloed glow edges in the final composite.
- Using FFmpeg `overlay` or `xfade` as if it automatically creates an in-place
  alpha reveal.
- Trusting Resolve timeline playback without watching the delivered file for wrong
  range, codec/playback problems, black frames, clipping, or caption collisions.
- Letting CTA, captions, title text, and proof labels compete without hierarchy.
- Approving a premium-looking intro that fails the format gate or delays the promised value.
- Letting intro SFX, music, or motion hide the proof quote, outcome text, or first body line.
- Approving CapCut keyframes without checking the rendered phone-size preview.
- Leaving accidental keyframes that create drift, pops, late ducks, or lingering overlays.
- Leaving accidental cross-property keyframes that change hue, brightness, scale,
  position, or volume after only one property was meant to move.
- Raising music and filter strength together before the final spoken word clears.
- Using unlicensed maps, music, stock cutouts, stickers, or icons in a publishable edit.
- Speeding action clips before marking the beat and action peak.
- Slowing a clip for an overlay and failing to recheck beat sync after the effect pass.
- Accepting rough mask edges, glow spill, or unreadable transition shake because the edit feels energetic.
- Baking captions or final SFX into heavy pre-renders that still need top-level adjustment.
- Leaving a temporary black spacer in the final render after replacing a heavy CapCut effect.
- Stacking Pendulum movement with turbulence and shake until the next pose cannot be read.
- Using downloaded voice lines, songs, SFX, or source clips without license or temp status.
- Leaving graph motion linear when the move needs a designed ease.
- Adding motion blur before checking the graph curve and subject centering.
- Stacking export/re-import zoom passes when the quality loss outweighs the style gain.
- Approving a still-image composite while masks look clean paused but reveal hard
  edges in motion.
- Using stock fire, sky, glow, or atmosphere without checking perspective, light,
  source alignment, and license status.
- Letting a warm/glow grade hide overlay mismatch or crush important scene detail.
- Trusting CapCut Remove Background, Chroma Key, Tracking, or Split masks without
  watching the full affected range.
- Approving clone or split-mask footage that was filmed with auto exposure/focus
  changes or camera movement.
- Using app-library, downloaded, screen-recorded, sticker, music, or SFX assets
  without source/license status.
- Using archival styling on current proof footage and confusing source age.
- Letting both switch-focus subjects become unreadable during a blur handoff.
- Treating AI-generated or downloaded documentary images as evidence without
  labels, source notes, or rights status.

## QC Checklist

- Final output matches the user-requested format.
- The opening confirms the promise and matches subject tone.
- Montage intent is written and visible in the edit.
- Character action stays anchored to perspective, stakes, and reaction.
- Every B-roll shot serves a story point.
- In narration-driven edits, every named character, person, place, object, product, UI element, proof point, or event is visually matched in the rendered output at the spoken-name timestamp and rounded viewer-facing second.
- Movie recap edits are built as narration-led paragraph units unless the user requested a longer combined recap.
- Movie recap source audio is muted, scene ranges are visually verified, and retained fragments are transformed rather than left as long continuous source runs.
- Eye-trace and movement continuity reduce viewer search time after cuts.
- Music is licensed/platform-safe and does not bury important audio.
- Artful choices match the target audience and do not hide the premise.
- Sensitive documentary edits preserve dignity, truth, and chronology unless a reorder is explicitly justified.
- No dead air remains in short-form unless it has clear tension, humor, or emotional purpose.
- The protagonist's goal, obstacle, learning path, and payoff are visible.
- Expert introductions prove credibility before the expert changes the story.
- Repetition for scale stops once the pattern is clear.
- Invitation intros close an early loop and eventually deliver the promised story.
- The first frame creates a specific question, tension, or sensory contradiction.
- Proof barrages include at least one readable trust-building beat.
- Pause beats carry meaning through image and sound rather than becoming dead air.
- Reality/fantasy treatment has a clear rule and intentional exceptions.
- Music-led sections have documented intended tone and license status.
- Main music cues land on meaningful visual or story turns.
- Dialogue is intelligible before and after music cue-heavy moments.
- Diegetic music bridges are truthful and source-motivated.
- Sensitive tonal contrast preserves subject dignity.
- First frame and first 30 seconds match the title/thumbnail promise.
- No accidental opening silence, breath, or hesitation remains unless intentional.
- No short-form dead air longer than 300 ms remains unless it has a named purpose.
- J/L cuts and punch-ins feel natural and do not mislead.
- Focus zooms hold steady and do not crop needed faces, captions, UI, or proof.
- Repeated whooshes or hits use variation and stay below dialogue.
- AI-generated shorts are approved for standalone context, layout, caption accuracy, and truthful trims.
- Export range, resolution, aspect ratio, frame rate, and filename match the delivery target.
- Timestamped rendered-output spot sheets have been reviewed around sensitive narration/visual handoffs and any user-reported timestamp, including at least 0.5s before through 1.0s after the window.
- The first five seconds contain a clear and supported short-form claim.
- Visual density drops or rests when the hook would otherwise become hard to process.
- Subject tracking keeps the speaker centered and caption-safe.
- One- or two-word subtitles are readable and not duplicated by visual text.
- Motion-synced SFX land on actual text pops, zooms, impacts, or reveals.
- Resolve project is vertical and captions are safe before export.
- Fusion effects render with intended easing, crop, and range.
- Power Bin presets used in the edit are named and phone-size checked.
- B-roll audio, Text+ stacks, and auto captions are clean in the final render.
- Premiere caption graphics were created after correction and checked after preset application.
- Hook text, captions, B-roll text, and full-screen text do not duplicate or collide.
- B-roll text readability treatment preserves the proof or action underneath.
- Adjustment zooms are range-safe and crop-safe.
- Short-form music is tone-fit, speech-safe, and licensed/platform-safe or marked temp-only.
- Prepared render is synced, trimmed, corrected, 1080x1920, and reviewed before AE animation starts.
- Every AE segment has a visual job and its layers are trimmed to that segment.
- Heavy AE effects are enabled before render.
- AE render matches the Premiere timeline duration, resolution, and frame rate.
- Duplicate AE render audio is removed or intentionally muted.
- Final captions, overlays, SFX, music, and dialogue are visible/audible in the intended export range.
- Target audience, idea promise, and style lane are written.
- Script beats are tagged and timeline assets match those tags.
- Animations have sketches or written plans before build.
- Isolated SFX pass was followed by full-mix review.
- Remaining improvements are optional and publish/hold decision is explicit.
- Slow human sections have named connection, proof, emotion, or comprehension purposes.
- Kept imperfections are free of consent, privacy, dignity, or brand risk.
- Warm grade, foley, micro drop, and low-focus captions pass final phone-size review.
- Editorial graphics pass rights, readability, source-context, SFX-sync, and low-FPS checks.
- Maps, charts, documents, screenshots, and cutouts have manifest-ready source/license notes.
- Typography has one primary focus per text moment.
- Viral text effects have one named job and one primary reading path.
- Font family, weight, case, size, and color match the project tone and meaning.
- Line breaks form readable phrases, and spacing survives motion at delivery size.
- Flicker, font-shift, stretch, and slide-up text resolve to readable final states.
- Player 3 captions, highlight wipes, gradient type, staggered blur reveals,
  foreground-lift text, and glow sweeps preserve readable final states.
- Remotion text effects render consistently with Sequence-local timing and
  deterministic seeds.
- FFmpeg text overlays have available fonts, logged filter graphs, readable enable
  windows, and contact-sheet review.
- Programmatic mask/glow text has no duplicate-layer drift, pre-glow, tail glow,
  or leftover mask sliver.
- Transparent overlay exports have verified alpha, no opaque background in empty
  areas, and no black rectangle when placed over footage.
- FFmpeg alpha masks have correct polarity and matching foreground/mask width,
  height, fps, duration, and timing before `alphamerge`.
- Number counters show a verified final value and hold long enough to read.
- Live-action text is placed in negative space or tracks cleanly without covering key visuals.
- For ads, the product/result/offer/CTA is readable faster than the text styling is noticed.
- Full Resolve export uses the intended timeline/range, container, codec, audio,
  filename, output folder, and caption mode, and the rendered file has been watched.
- Formal intro has a named purpose: brand identity, series identity, social proof, authority, or perceived outcome.
- Formal intro format is appropriate; ordinary mid-length YouTube/tutorial content starts with value unless the bumper materially increases trust.
- Brand/show identity is readable before dense motion begins.
- Social proof or authority is truthful, relevant, and preferably external to the creator.
- Viewer outcome or perceived value is clear before the intro ends.
- Intro text layers have assigned roles and one phrase owns hierarchy at each moment.
- Intro SFX land on visible events within the intended tolerance and do not overpower proof or body speech.
- If the intro is removed, the edit loses package/trust value rather than simply becoming faster.
- Every CapCut keyframed property has a named job and wrong keyframes are removed.
- Each changing CapCut property has its own intended start and end keyframe.
- Keyframe spacing creates the intended speed and the final state holds long enough to read or hear.
- Quick zooms keep the eyes or named focus target stable when the second
  scale/position keyframe lands.
- Zooms, tracking, tilts, overlays, and cutout paths preserve captions, faces, proof, UI, products, map labels, and action.
- Rotation/tilt moves reveal no black corners.
- Music ducking begins before speech and restores only after speech clears.
- Music duck level is checked against the actual track and voice, not copied from
  a preset.
- Saturation shifts preserve readability and are restored or held intentionally.
- Filter-strength reveals align with the music lift and keep captions, faces,
  proof, UI, products, and brand colors readable.
- External maps, music, stock images, stickers, icons, and cutouts have source/license notes when used in a real project.
- Beat-matched action clips land on the intended beat and remain readable at phone size.
- Eye/power overlays reveal on beat, remain aligned through playback, and keep facial expression readable.
- Character masks/glow/shadow have clean edges and avoid caption/action overlap.
- Heavy overlay replacements keep handles and leave final captions/SFX editable.
- Temporary placeholders/spacers used during replacement are removed or replaced before delivery.
- Pendulum movement preserves the action pose, caption safety, and next transition readability.
- Turbulent/wide-angle transitions peak on the cut or beat and settle before the next readable pose.
- SFX and voice lines have visible jobs, synced cue frames, and license/platform status.
- SFX cue families match the visible event type rather than using one generic impact for every moment.
- Graph-shaped motion has a named curve intent and avoids accidental robotic movement.
- Stacked graph zooms keep the subject centered and avoid excessive softness.
- Motion blur does not smear captions, faces, proof, UI, products, or action.
- Still-image composites use only motivated moving overlays and preserve the
  original focal point.
- Fire, sky, reflection, and base image layers match closely enough in exposure,
  temperature, contrast, and highlight detail.
- Local flicker remains weaker than or consistent with its light source and does
  not cover captions, faces, proof, UI, products, or key action.
- All external still-image composite assets are manifest-ready for source,
  license, creator/attribution, date, and local path.
- Subject-sandwich, chroma-key, tracking, PiP, split-mask, clone, and green-screen
  effects preserve captions, faces, UI, products, proof, and active action.
- Text-behind-object, outline reveal, and video-in-text effects have clean cutout,
  key, blend, and letter edges at phone size.
- Highlight wipes and glow sweeps start/end off-word without pre-glow, tail glow,
  or lingering blur.
- Pro-effect music, SFX, stickers, photos, and VFX assets are licensed,
  platform-safe, or marked temp-only before delivery.
- Switch-focus scenes keep one subject readable and maintain clean cutout edges.
- Research overlays reveal enough context to avoid misleading source use.
- Archival treatments truthfully signal source type and do not disguise generated
  or illustrative media as historical proof.
- Filmed-screen texture keeps UI, source text, cursor action, and captions readable.
- Parallax collage foreground, background, and text move with intentional depth
  and do not crop important labels or cutouts.
- Transparent overlay empty regions are transparent, not black, and edge softness
  remains clean over bright and dark backgrounds.
- Generated alpha masks are previewed alone before controlling a foreground layer.
- The promoted final file, not only the preview or EDL, passes any required narration/visual alignment spot checks.

## Source Lessons Added

- 2026-05-27: `How an Editor Thinks and Feels`
- 2026-05-27: `Editing Secrets`
- 2026-05-27: `What Not To Do In Editing`
- 2026-05-27: `Editing That Makes Your Story 10x`
- 2026-05-27: `The 5-Second Intro Is Dead: Here's Why`
- 2026-05-28: `Saving Bad Videos With Only Music`
- 2026-05-28: `Editing Full Course`
- 2026-05-28: `Short-Form Editing`
- 2026-05-28: `DaVinci Resolve Short Form Editing`
- 2026-05-28: `Ultimate Guide To Shortform`
- 2026-05-28: `Edit High Quality Reel`
- 2026-05-29: `Editing Viral Videos`
- 2026-06-23: `Bleach Women Recap Character Alignment Correction`
- 2026-06-24: `Movie Recap`
- 2026-05-29: `Slow Editing`
- 2026-05-29: `Vox Style Documentary`
- 2026-05-29: `Typography`
- 2026-05-29: `DaVinci Resolve Full Tutorial`
- 2026-05-29: `Killer Intros`
- 2026-05-29: `CapCut Keyframes`
- 2026-05-29: `Editing Tricks`
- 2026-05-29: `Keyframe Graph Tutorial`
- 2026-05-29: `Still Image To Media`
- 2026-05-29: `Make Pro Media`
- 2026-05-29: `Powerful CapCut Edits`
- 2026-05-29: `CapCut Text Effects`
- 2026-05-29: `Documentary Edits`
- 2026-05-29: `Keyframe Pro Edits`
- 2026-05-29: `Viral Text Effects`
- 2026-06-01: `Premium CapCut Text Effect`
- 2026-06-01: `Remotion Lab Kinetic Typography Presets`
- 2026-06-01: `FFmpeg Drawtext Animations`
- 2026-06-01: `Programmatic Alpha Masking And Transparent Overlay Source Pack`

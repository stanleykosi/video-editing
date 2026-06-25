# CapCut Motion Language

## Purpose

Capture mobile-first social editing patterns often built in CapCut and translate them
into reusable agent instructions for ffmpeg, Remotion, Premiere, and DaVinci.

## When To Use This Skill

- Recreating social edit grammar outside CapCut.
- Matching TikTok, Reels, or Shorts motion language.
- Translating CapCut-style keyframes, shakes, captions, templates, and auto-clips into agent workflows.
- Reviewing AI/CapCut-like outputs for readability, focus, and caption safety.
- Building high-energy short-form talking-head edits with tracking, zooms, visual text, icons, and motion-synced SFX.
- Building CapCut editorial explainer graphics with compound clips, masks, maps, charts, document highlights, and FPS lag texture.
- Translating CapCut typography templates into reusable font, hierarchy, line-break, and placement rules.
- Building viral CapCut text effects such as adaptive captions, slide-up text,
  Player 3 smooth captions, slide-up text, flicker, counters, perspective words,
  color-change highlight wipes, staggered blur reveals, gradient type, font-shift
  loops, outline reveals, foreground-lift text, and film-strip glow reveals.
- Building custom CapCut keyframes for scale, position, rotation, overlay paths, color shifts, and music volume automation.
- Building property-specific CapCut keyframes for saturation, filter strength,
  scale/position, sticker paths, and music volume without accidental cross-property changes.
- Building high-energy AMV/action edits with beat-matched speed, subject masks, glow, heavy overlays, turbulent transitions, and frame-placed SFX.
- Building CapCut anime power edits with eye overlays, pendulum movement, export/re-import replacement, and event-matched SFX.
- Shaping CapCut graph curves for smoother keyframe zooms, moves, rotations, overlays, and stylized zoom stacks.
- Turning a still image into a moving CapCut composite with library overlays,
  Screen blend, feathered masks, local flicker, and adjustment-layer grading.
- Building pro-style CapCut composites with subject sandwiches, chroma-key text,
  auto tracking, slide-on photo stacks, PiP borders, split masks, clone effects,
  and green-screen VFX.
- Building documentary-style CapCut scenes with switch-focus blur, research
  overlays, archival film frames, filmed-screen texture, and parallax cutout
  collage motion.

## Core Principles

- Use motion to emphasize beats, not to decorate every cut.
- Prefer short, readable moves for captions and subject emphasis.
- Match zooms, shakes, flashes, and blurs to audio accents or meaning shifts.
- A motion effect needs a job: focus, impact, concealment, transition, comedy, or proof.
- One primary focus should dominate each moment.
- Templates are drafts until the agent checks timing, captions, layout, and tone.
- Use zooms to highlight important statements and tracking to follow subject movement.
- Visualize what the speaker says when a text/icon/stock/GIF stack communicates faster than more talking head.
- Dense hooks should settle into a readable rest beat before the next heavy motion stack.
- Compound clips should organize dense graphic scenes without hiding unreadable internal timing.
- CapCut templates, stickers, logos, and publisher-style layouts need rights and identity review before reuse.
- Text templates are drafts until font role, impact word, line breaks, tracking, and negative-space placement are checked.
- Viral text effects must be assigned a job before use: caption readability,
  premium presentation, impact-word emphasis, proof counter, depth, or beat accent.
- Premium CapCut text effects should be built as controlled compounds, masks, and
  duplicate layers, then judged by readability rather than trend value.
- Keyframes are for custom behavior: if a preset animation already lands cleanly, use it; if the path, timing, or level must be exact, keyframe it.
- Treat CapCut keyframes as property-specific: changing saturation, filter
  strength, position, scale, or volume should not silently move unrelated
  properties.
- Keyframe spacing controls perceived speed: closer points snap or jolt, farther points drift or ease slowly.
- CapCut can create a later keyframe automatically after the first keyframe exists and the editor changes a property at a new playhead position.
- Compound clips can unlock video-style animation options for stickers or text,
  but use the wrapper only when manual keyframes or native animations cannot land
  the behavior cleanly.
- For dense AMV-style edits, lock clip speed to beats before building masks, glow, transition shake, or SFX.
- When CapCut lags under many overlays, isolate and pre-render heavy clips while keeping final captions, SFX, and transitions editable in the main project.
- Preserve duration with a spacer or placeholder while replacing exported overlay clips so the main timeline does not drift.
- Pendulum movement is an energy layer, not a default; add it only after the clip timing is beat-locked and still readable.
- Graphs control speed flow between keyframes: keyframes set the values, graphs decide whether the move starts slow, starts fast, accelerates, decelerates, or settles gently.
- Motion blur belongs after graph timing, scale, position, and crop safety are locked.
- Still-image composites work best when CapCut effects are treated as motivated
  scene layers: fire belongs on the fire source, sky belongs behind the horizon,
  and flicker belongs only on surfaces that would catch the light.
- Advanced CapCut effects should be planned like simple compositing: lock the
  shot, choose layer order, keep revision-sensitive layers editable, and check
  cutout/key/mask edges across the full range.
- Documentary-style CapCut effects need restrained depth: one primary focus,
  readable evidence, clear source type, and source/license notes.

## Techniques

- `technique_cards/nle_capcut_keyframe_spacing_control_001.json`
- `technique_cards/motion_capcut_graph_curve_easing_001.json`
- `technique_cards/motion_capcut_graph_zoom_stack_001.json`
- `technique_cards/motion_still_image_environment_composite_001.json`
- `technique_cards/motion_masked_firelight_strobe_reflection_001.json`
- `technique_cards/color_low_key_firelight_scene_unification_001.json`
- `technique_cards/compositing_capcut_subject_sandwich_cutout_001.json`
- `technique_cards/typography_capcut_chroma_video_text_portal_001.json`
- `technique_cards/motion_capcut_auto_subject_sticker_tracking_001.json`
- `technique_cards/motion_capcut_slide_on_photo_stack_001.json`
- `technique_cards/motion_capcut_chapter_card_slide_interrupt_001.json`
- `technique_cards/compositing_capcut_pip_border_chroma_shape_001.json`
- `technique_cards/compositing_locked_camera_split_mask_illusion_001.json`
- `technique_cards/compositing_capcut_green_screen_vfx_insert_001.json`
- `technique_cards/motion_keyframe_focus_zoom_hold_001.json`
- `technique_cards/motion_overlay_readability_focus_stack_001.json`
- `technique_cards/motion_capcut_switch_focus_depth_blur_001.json`
- `technique_cards/motion_documentary_research_overlay_timelapse_001.json`
- `technique_cards/color_archival_film_frame_treatment_001.json`
- `technique_cards/motion_capcut_documentary_parallax_collage_001.json`
- `technique_cards/motion_screen_blend_texture_overlay_001.json`
- `technique_cards/motion_capcut_overlay_path_keyframes_001.json`
- `technique_cards/motion_keyframed_tilt_tension_001.json`
- `technique_cards/motion_capcut_cutout_character_walk_001.json`
- `technique_cards/color_keyframed_saturation_shift_001.json`
- `technique_cards/sound_music_ducking_volume_keyframes_001.json`
- `technique_cards/color_filter_strength_music_reveal_001.json`
- `technique_cards/nle_capcut_compound_clip_animation_unlock_001.json`
- `technique_cards/captions_capcut_adaptive_texture_animation_001.json`
- `technique_cards/captions_capcut_player3_smooth_caption_compounds_001.json`
- `technique_cards/typography_capcut_apple_slide_up_text_001.json`
- `technique_cards/typography_capcut_axis_stretch_emphasis_001.json`
- `technique_cards/typography_capcut_opacity_flicker_tick_001.json`
- `technique_cards/typography_capcut_srt_number_countup_001.json`
- `technique_cards/typography_capcut_perspective_freeze_text_001.json`
- `technique_cards/typography_capcut_color_change_highlight_wipe_001.json`
- `technique_cards/typography_capcut_staggered_blur_glitch_reveal_001.json`
- `technique_cards/typography_capcut_split_mask_gradient_type_001.json`
- `technique_cards/typography_capcut_font_shift_loop_001.json`
- `technique_cards/typography_capcut_outline_reveal_chroma_001.json`
- `technique_cards/typography_capcut_film_strip_glow_reveal_001.json`
- `technique_cards/beat_sync_capcut_speed_match_twixtor_001.json`
- `technique_cards/motion_capcut_character_mask_shadow_glow_001.json`
- `technique_cards/nle_capcut_heavy_overlay_prerender_workflow_001.json`
- `technique_cards/transition_capcut_turbulent_wide_angle_shake_001.json`
- `technique_cards/motion_capcut_effect_tail_extension_001.json`
- `technique_cards/sound_anime_edit_sfx_voice_line_spotting_001.json`
- `technique_cards/compositing_capcut_eye_power_overlay_001.json`
- `technique_cards/motion_capcut_pendulum_transition_movement_001.json`
- `technique_cards/sound_sfx_variation_exaggeration_001.json`
- `technique_cards/retention_overediting_value_supplement_001.json`
- `technique_cards/podcast_ai_shorts_review_refine_001.json`
- `technique_cards/retention_high_energy_hook_rest_001.json`
- `technique_cards/motion_subject_tracking_statement_zoom_001.json`
- `technique_cards/motion_show_dont_tell_visual_stack_001.json`
- `technique_cards/captions_two_word_social_subtitles_001.json`
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
- `technique_cards/typography_font_family_role_selection_001.json`
- `technique_cards/typography_contrast_hierarchy_stack_001.json`
- `technique_cards/typography_sentence_structure_line_breaks_001.json`
- `technique_cards/typography_live_action_whitespace_integration_001.json`
- Add future cards for velocity ramps, blur transitions, flash hits, and pop-in text.

## Timing Rules

- Punch zooms, shakes, or hits should land within 1-2 frames of the beat or visual impact when sync matters.
- Caption motion should finish before the word needs to be read.
- Focus moves should hold long enough for the target to register.
- Do not add fixed-interval pattern breaks when attention is not actually dipping.
- For fast social text/icon pops, use roughly 4-8 frame entrances when readable.
- Hold statement zooms 8-18 frames after landing so emphasis registers.
- Map route wipes can start around 2 seconds and adjust to the geography/narration.
- Chart bar wipes can start around 1 second per reveal when labels remain readable.
- Apply FPS Lag only after graphic timing is locked.
- CapCut text presets should be timed only after the line break and impact word are corrected.
- Apple-style text slides can start around 22 frames and should settle before the
  phrase needs to be read.
- One-frame flicker keyframes are acceptable only when the word remains readable
  and resolves to full opacity.
- Number counters need a final-value hold; do not let speed curves skip the proof.
- Player 3 caption compounds should be trimmed to the phrase and checked after
  pasted attributes.
- Highlight wipes and film-strip glow reveals should start/end off the word and
  clear before the next reading task.
- Staggered blur/glitch reveals should resolve to stable readable text before the
  next caption, proof, or CTA competes.
- Close keyframes create dramatic zooms, fast overlay entrances, or sudden color/volume shifts; widen the spacing for slow engagement zooms and gradual mood changes.
- Quick CapCut focus zooms can use about 4 frames between scale/position
  keyframes when the jolt is intentional and the focus remains stable.
- Add hold keyframes after zooms, overlay arrivals, route destinations, or tracking moves when the viewer needs time to read the target.
- Switch-focus depth blur can start with a 1s to 3s handoff and opposite blur
  ramps, but the viewer should never lose both subjects.
- Documentary text animations around 1.5-2 seconds can feel polished when they
  settle before the title or source label must be read.
- Archival frame treatments and filmed-screen textures should be applied after
  the proof/source timing is known.
- Start music ducking before speech begins and restore it only after the phrase or talking section clears.
- Align a filter-strength reveal with music restoring after speech only when the
  look and audio lift serve the same montage or mood beat.
- Add beat markers before speed-matching multiple action clips.
- Tune clip speed per action peak; there is no single CapCut speed value that fits every beat.
- Slow or speed-adjust a character detail only enough to align the overlay and beat; recheck sync after the effect pass.
- Transition shakes should be applied after turbulent and wide-angle effects so intensity can be judged from the final transition flow.
- Pendulum movement should be judged with the following transition because swing plus turbulence can quickly hide the next readable pose.
- Short effect-tail extensions should clear before the next main beat.
- A lower left-side graph curve creates a slower start; a higher left-side curve creates a faster start.
- A lower right-side graph curve creates a gentler ending; a higher right-side curve creates a sharper stop.
- Use smooth graph curves for polished zooms unless the edit intentionally needs a snap or hard stop.
- For stacked CapCut graph zooms, approve the first pass before exporting/re-importing for the second pass.
- Still-image overlays should cover the full still-image beat without visible
  looping pops or tail gaps.
- Local reflection flicker should begin and end with the visible or implied light
  source rather than continuing as an unrelated effect.
- Export/re-import subject-sandwich effects only after the baked text, sticker,
  or VFX timing is stable.
- Photo stacks and chapter cards should settle long enough to read, then clear
  before the next body line or visual focus.

## Motion Rules

- Use scale and position keyframes together so the target remains readable.
- For slow face zooms, adjust position while scaling so the eyes or named focus
  target stays in the same screen area.
- Add hold keyframes after focus moves.
- Use shake for aggression, surprise, or comedy; avoid it for mature or sensitive material.
- Use background dim, blur, stroke, or shadow to make overlays readable.
- Avoid stacking shake, zoom, caption pop, whoosh, and meme overlay at the same moment unless the style demands chaos.
- Keep the speaker near center guide during manual tracking unless text or proof needs intentional space.
- Preserve face, hands, captions, and proof during zooms.
- Use masks, feathered stock footage, glow, and background texture only when they clarify the spoken concept.
- Use chroma key, auto removal, split masks, blend modes, and compound clips as editable construction tools, not final quality guarantees.
- Eased/cubic keyframes should control map pans, document zooms, and compound scene transforms.
- Place text in negative space before adding shadows, backgrounds, or blend modes to rescue readability.
- For overlay paths, start offscreen or at origin, land on the focus point, hold, then exit before the next concept competes.
- For sticker/object paths, set size, flip, and rotation before position
  keyframes, then preview the path through the full spoken concept.
- For tilt tension, zoom in before rotation so black corners do not appear.
- For manual subject tracking, add enough position keyframes to prevent drift but not so many that the crop jitters.
- For cutout character/object movement, use small position steps when a playful walk is intended; use one smooth path only when the object should glide.
- For character masks, isolate only the subject or body part that needs glow, shadow, or flicker, then review edges through the whole motion range.
- Use separate clip projects or compounds for overlay-heavy shots when playback lag prevents accurate timing review.
- Keep a black screen, placeholder, or spacer only as a temporary duration guard while replacing an exported effect clip; remove it before final export.
- Turbulent and wide-angle transition effects should peak around the cut/beat and settle before the next action pose needs to be read.
- For eye or power overlays, speed-adjust first, align the overlay through playback, then export/re-import only after the feature does not drift.
- Start with one Pendulum pass, use two for strong AMV swing, and reserve three for extreme style that still passes phone-size readability.
- Black matte/backing and duplicated effect layers can extend a fading effect only when the extension has a named visual job.
- Shape graphs after scale and position keyframes are set so the movement speed matches the focus job.
- For intense graph zoom stacks, animate scale and position together in both passes so the subject stays centered.
- Heavy zoom values such as 300% first-pass scale and 150% second-pass scale require source-quality and crop-safety checks.
- For CapCut still-image composites, place library or imported overlays above the
  still, set black-background fire/glow clips to Screen, resize them to the
  source object, and use Mask plus high Feather for sky or reflection regions.
- If using a Strobe/Flicker effect for reflected light, isolate it with a small
  feathered mask before blending so the entire frame does not blink.
- For behind-subject effects, place text/VFX in the prepared base, then align the
  original clean clip above it and use Remove Background for the foreground.
- For direct text-behind-object effects, duplicate the video, remove the subject
  or object on the top layer, and place text between the video layers only after
  edge QC passes.
- For perspective text, freeze the best readable angle and remove unused animated
  tails before final export.
- For foreground-lift text, brush or cut out the foreground object on the top
  duplicate, then keyframe the text upward from behind it only if the edge holds.
- For axis-stretch text, disable uniform scale and animate only the intended width
  or height property on the impact word.
- For split-mask gradient and glow text, duplicate text layers exactly before
  compounding, then keep the mask feather, strip width, and glow below the point
  where edges become muddy.
- For split-mask illusions or clones, film with locked camera, focus, exposure,
  and white balance, then align the Split mask to a real object edge.
- Use CapCut tracking only while the target remains visible; shorten or keyframe
  around drift, occlusion, and face turns.
- For switch-focus scenes, compound the foreground cutouts separately from the
  background, ease scale/X/Y, and use opposite blur ramps to hand off attention.
- For parallax collages, copy location/size attributes only as a starting point;
  reduce background motion so it does not match the foreground exactly.
- Low-strength Pendulum can be used as documentary texture only after titles,
  captions, source text, and cutouts pass readability checks.

## Sound Rules

- Match SFX to the motion start, impact, or reveal frame.
- Rotate whoosh and hit variants instead of repeating the exact same file.
- Lower or remove SFX that compete with speech.
- Avoid default whooshes in serious sections.
- Use reversed hits before real questions, reveals, or transitions when anticipation helps.
- Start whooshes low under dialogue and adjust by ear.
- Infographic SFX should cue major text, map, chart, highlight, or screenshot events, not every small layer.
- Ticks for flicker, font-shift, and number-counter text should land on actual
  visible changes and end with the animation.
- Glitch, shimmer, or tick cues for staggered reveals, highlight wipes, and glow
  sweeps should be trimmed to the visible change and reviewed in the full mix.
- Volume keyframes should make music loud under visual-only sections and low under speech; if captions are needed to understand normal dialogue, the music is still too loud.
- Music ducking under speech can start around -15 dB to -20 dB, or around -14 dB
  for a softer bed, but the actual voice/song mix decides the final value.
- Imported music must be licensed, platform-safe, or marked temp-only before delivery.
- AMV/action SFX should be spotted after visual timing is locked enough for hits to land on real motion frames.
- Match cue families to visible jobs: lightning, glass, eye transformation, entrance, and identity voice beats should not all use the same generic hit.
- Short identity voice lines belong only where they clarify character, emotion, or impact.
- Environmental composites usually need low ambience, such as fire crackle or
  wind, only after the visual source exists and only below speech.
- CapCut/app-library music, downloaded SFX, and screen-recorded green-screen
  effects still need license or platform-safety notes before delivery.
- Footsteps, door sounds, or impact hits can sell clone and VFX tricks only after
  the visual timing is locked.
- Research-overlay risers should stay restrained and resolve into a visible
  discovery; avoid trailer-style build under ordinary browsing.

## Caption Rules

- Captions remain readable through motion.
- Captions do not cover the face, title, product, proof, or action being emphasized.
- Auto-captions need manual correction for wording, line breaks, emphasis, and filler words.
- Keep captions inside safe margins for vertical layouts.
- One- or two-word subtitle chunks can fit high-energy style, but keep duplicate captions visible, repositioned, or simplified unless the user explicitly approves suppression.
- Break captions and text templates by phrase meaning; do not rely on auto-wrap.
- Check captions after every keyframed zoom, tilt, tracking move, overlay path, or cutout animation.
- Keep captions away from high-contrast flicker, fire, or moving sky regions when
  those areas change brightness frame to frame.
- Keep captions away from foreground cutout edges, tracked stickers, PiP regions,
  split-mask boundaries, and VFX impact frames.
- Keep captions off the face or eye during a power-overlay transformation by
  moving or restyling them; suppress only with explicit user approval.
- Keep duplicate captions visible or repositioned during chapter cards,
  video-in-text portals, or designed full-screen text when the visual text
  already carries the line; suppress only with explicit user approval.
- Keep duplicate captions visible or repositioned during slide-up, flicker,
  font-shift, outline, counter, highlight, glow, or perspective text when the
  designed text carries the same words; suppress only with explicit user approval.
- Keep captions away from the subject receiving switch focus, dense research
  documents, film-frame borders, filmed-screen UI, and parallax title layers.

## Color Rules

- Motion effects, flashes, and blur should not hide faces, action, or proof.
- Template colors must stay readable over both bright and dark footage.
- Warm paper/grid palettes must keep map labels, chart bars, and source text readable.
- Gradients, composite modes, and drop shadows are approved only if they improve readability at phone size.
- Blend modes and chroma-keyed text effects must preserve crisp letter edges and
  avoid color specks or muddy video-in-text fills.
- Keyframed saturation shifts should have a mood, memory, reveal, or contrast purpose and preserve skin, proof, product, and caption readability.
- Filter-strength ramps should start from neutral, rise only after speech clears
  when paired with music, and preserve faces, proof, products, and captions at
  full strength.
- Glow, flicker, wide-angle distortion, and effect-tail color correction should preserve subject silhouette and avoid compression dirt.
- Gradient, highlight, and glow text must preserve crisp letter edges before,
  during, and after the mask or shine move.
- For still-image composites, lower exposure or shadows only enough for the
  moving light source to stand out, then use tint/contrast/highlights/glow to
  unify layers without crushing detail.
- Match foreground cutouts, keyed VFX, and baked base renders so export/re-import
  passes do not reveal color or compression mismatch.
- Match eye/power overlays for brightness, glow, and contrast so the face remains readable.
- Archival particles/fade and film frame effects should sell old media without
  hiding source labels, dates, captions, or faces.
- Glass texture and Color Burn-style blends over screen recordings should be
  lowered until UI and source text remain readable.

## Tool Implementation Notes

- CapCut: use keyframes, canvas blur/dim, text stroke/shadow, manual captions, SFX tracks, and template toggles as editable drafts.
- CapCut keyframes: select the target clip/overlay/audio, add a starting keyframe, move the playhead, change scale/position/rotation/adjustment/volume, preview, then adjust spacing or delete bad points.
- CapCut property keyframes: if the intended move is saturation, filter strength,
  or volume, change only that property at the later playhead position and confirm
  no unrelated keyframes were created.
- CapCut compound animation unlock: create a compound from a sticker/text layer
  only when the needed video-style animation is unavailable on the original
  layer, then reopen the compound for source revisions.
- CapCut graphs: after property keyframes exist, open Graphs on the selected keyframe, choose or shape the curve, preview the actual motion, and recheck captions/crop.
- CapCut graph zoom stack: set first-pass end scale around 300 with subject centered, apply graph easing, export/re-import, split, add a second pass around 150, export again, then apply Motion Blur around Blur 10 and Blend 10 as a starting point.
- CapCut still-image composite: add the still to the timeline, place matching
  moving clips above it, set black-backed clips to Screen, use Mask and Feather
  for partial replacements, add localized strobe/flicker on a masked duplicate or
  adjustment layer, then apply an Adjustment layer or glow/warm filter for final
  unification.
- CapCut pro compositing: use overlays, Cutout/Remove Background, Chroma Key,
  Mask/Split, Camera Tracking, sticker Tracking, simple in/out animations, and
  export/re-import only when layer order requires a prepared base.
- CapCut graphics: use ratio, chroma key, auto cutout, masks, blend modes, compound clips, W trims, variable-speed/ease controls, and FPS Lag after timing review.
- CapCut viral text: correct captions before applying animation presets, use
  Character spacing lightly, compound reusable text templates, freeze perspective
  frames only after choosing the readable angle, and keep source text editable.
- CapCut premium text: for Player 3 captions, compound corrected caption groups;
  for highlight/gradient/glow text, duplicate text precisely, compound only the
  layer that needs masking, and paste attributes only after one reference layer
  passes QC.
- CapCut AMV workflow: mark beats, speed-match each action clip, design heavy masked overlays in isolated clip projects or compounds, replace into the main timeline, then add transition effects, transition shakes, and final SFX.
- CapCut eye overlay workflow: speed-adjust the close-up, add/position/mask the eye or power overlay, preview for drift, export/re-import after duration approval, then place the transformation SFX.
- ffmpeg: use crop/scale/overlay/drawtext/fades and audio cue alignment from frame data.
- Remotion: drive zooms, captions, SFX, overlays, color shifts, and volume ducks from shared beat/focus metadata.
- Premiere/DaVinci: use Effect Controls or Inspector keyframes, Essential Graphics/text settings, linked/unlinked audio, and marker-based sync checks.
- Premiere: use rulers/guides for center tracking, Essential Graphics for visual text, masks with feather for stock inserts, and caption-to-graphics only after timing is correct.
- Store CapCut-style text templates by role: title, caption, proof label, CTA, impact word, and scene-attached text.
- CapCut documentary scene metadata should include cutout source, mask feather,
  blur ramps, scale/X/Y keyframes, graph/ease state, archival treatment values,
  texture opacity, and asset/license status.

## Common Mistakes

- Using motion because the template offers it, not because the beat needs it.
- Making captions unreadable during zooms, shakes, or flashes.
- Repeating the same whoosh on every movement.
- Covering the exact detail the motion was meant to emphasize.
- Accepting an AI-generated vertical layout without checking face and proof visibility.
- Zooming every line instead of important statements.
- Forgetting to leave crop room for body movement before adding zooms.
- Using visual stacks that duplicate captions instead of clarifying the idea.
- Letting hook-level effects continue until the explanation becomes tiring.
- Creating compounds with vague names or inaccessible internal timing.
- Letting FPS Lag make text, maps, or charts unreadable.
- Copying a publisher-style logo/layout without rights or project-specific adaptation.
- Trusting a text template before checking impact word, line break, font family, and placement.
- Applying viral text effects to every line instead of using them as selected
  emphasis or proof moments.
- Letting generated number counters, font shifts, or flickers overstay without a
  readable final state.
- Letting Player 3, highlight wipes, glow sweeps, gradient masks, or staggered
  blur reveals make text harder to read than the plain version.
- Leaving accidental keyframes that cause drift after the move should stop.
- Changing an unrelated property after adding a keyframe and creating accidental
  hue, brightness, scale, position, or volume movement.
- Rotating footage without zooming enough to hide black corners.
- Starting a music duck after speech begins.
- Copying one music-duck value across every song instead of checking speech
  intelligibility on the actual track.
- Using a filter-strength reveal to add energy while speech still needs to be
  understood.
- Using a rough cutout or unlicensed asset where the project needs clean, publishable polish.
- Adding glow, turbulent effects, shake, and SFX before the clip is speed-matched to the beat.
- Overtrimming isolated CapCut clip projects so the main timeline has no transition handles.
- Letting exported overlay replacements change the timeline duration because no temporary spacer or placeholder was used.
- Stacking Pendulum passes with turbulent/wide-angle transitions until the action pose is unreadable.
- Judging an eye overlay on a paused frame instead of checking drift through playback.
- Applying transition shake before the turbulent/wide-angle transition can be judged.
- Using voice lines or intense SFX on every clip until the edit loses contrast.
- Leaving graph-shaped motion linear when the move should accelerate or settle.
- Copying a graph preset across clips without previewing each subject's motion.
- Adding motion blur before checking graph timing, subject centering, and caption safety.
- Stacking export/re-import zoom passes when one clean keyframed zoom would be enough.
- Applying Strobe/Flicker to the whole still-image composite instead of masking a
  local light reflection.
- Adding a library fire, sky, or atmosphere clip that does not match the still
  image's perspective, light, or mood.
- Filming split-mask or clone tricks with auto exposure, auto focus, or camera
  movement.
- Using long phrases or thin fonts for video-in-text reveals.
- Trusting auto tracking, Remove Background, Chroma Key, or Split masks without
  full-range review.
- Using identical foreground and background motion in a parallax scene.
- Adding film frames, glass texture, FPS lag, or Pendulum before source text and
  captions are readable.
- Using generated or downloaded documentary imagery without source/license notes
  or labels.

## QC Checklist

- Motion does not make captions unreadable.
- Effects land on intentional beats.
- Focus moves hold long enough to read the target.
- Only one primary focus dominates each moment.
- SFX do not overpower speech.
- Auto-generated layouts and captions have been manually reviewed.
- Avoid stacking multiple attention effects unless the style demands chaos.
- Speaker remains centered during tracking.
- Statement zooms preserve face, hands, captions, and proof.
- Visual stack elements sync to the spoken concept and clear before the next idea.
- Whooshes and hits stay below dialogue and land on actual motion.
- Graphic compounds are named, readable, and internally editable.
- Map, chart, document, and screenshot graphics remain readable after masks, blends, and FPS Lag.
- All external assets used in a real project have source/license notes.
- Text templates have one clear hierarchy and do not cover the subject, proof, product, or CTA.
- Viral text effects have one named role and one primary reading path.
- Keyframe spacing creates the intended speed and wrong keyframes are removed.
- Each changing property has its own intended start and end keyframe.
- Zooms, tracking, tilts, overlays, and cutout paths preserve captions, faces, proof, UI, products, and action.
- Rotation/tilt moves reveal no black corners.
- Music ducks before speech and restores only after speech clears.
- Music duck values fit the actual voice/song and do not rely on a copied preset.
- Saturation shifts preserve faces, proof, products, and caption contrast.
- Filter-strength reveals sync with the music lift and preserve captions, faces,
  proof, UI, products, and brand colors.
- Speed-matched action remains readable and lands within the intended beat tolerance.
- Eye/power overlays stay aligned through playback and land on the intended transformation beat.
- Masked character glow/shadow has clean edges and does not cover captions or action.
- Heavy overlay replacements keep enough handles and leave final captions/SFX editable.
- Temporary spacers/placeholders used during replacement are removed before final export.
- Pendulum movement preserves the action pose, captions, and next transition readability.
- Turbulent/wide-angle transition shakes settle before the next action pose.
- AMV SFX and voice lines land on visible jobs, stay mix-safe, and have license/temp status.
- Graph curves create the intended start speed, acceleration/deceleration, and ending feel.
- Intense graph zooms keep the subject centered and preserve source detail.
- Motion blur does not smear captions, faces, proof, UI, products, or action.
- Screen-blended overlays remove black backgrounds cleanly and line up with the
  source object or region.
- Still-image masks are feathered enough to hide sky, reflection, or atmosphere
  boundaries at full playback speed.
- Firelight flicker remains local, readable, and weaker than or consistent with
  its source light.
- Subject-sandwich layers are frame-aligned and foreground cutout edges remain
  clean through hair, hands, motion blur, and turns.
- Chroma-key text, PiP borders, and green-screen VFX have clean edges with no key
  color specks or spill.
- Adaptive captions, flicker, font-shift, counters, and perspective text stay
  readable at phone size and do not duplicate ordinary captions.
- Highlight wipes, gradient type, foreground-lift text, outline reveals, and glow
  sweeps preserve clean masks, readable edges, and one clear reading path.
- Split-mask and clone effects match exposure, focus, white balance, and camera
  position across takes.
- Switch-focus blur keeps one subject readable and cutout edges clean.
- Research overlays, archival treatments, filmed-screen textures, and parallax
  collages preserve source context, captions, and asset rights.

## Source Lessons Added

- 2026-05-28: `Editing Full Course`
- 2026-05-28: `Short-Form Editing`
- 2026-05-29: `Vox Style Documentary`
- 2026-05-29: `Typography`
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

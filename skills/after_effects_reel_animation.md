# After Effects Reel Animation

## Purpose

Guide high-quality vertical Reel animation in After Effects, especially for
Premiere-prepared talking-head shorts that need branded motion, text systems,
icons, paths, counters, nulls, cameras, and reusable presets.

## When To Use This Skill

- Animating a prepared short-form cut in After Effects.
- Building branded motion systems for creators, clients, coaches, or educators.
- Creating reusable text, background, camera, path, icon, matte, and transition presets.
- Translating After Effects-heavy tutorials into agent-ready motion rules.
- Deciding when a segment deserves full-screen animation versus simple captions or text.
- Rendering an After Effects animation pass for Premiere finishing.
- Turning sketched YouTube animation ideas into text, shape, pen, typewriter, Trim Paths, and glow motion.

## Core Principles

- Animate only after the rough cut and segment ideation are stable.
- Every element on screen needs a message job: hook, proof, focus, transition, emotion, CTA, or hierarchy.
- Keep one visual style system across fonts, colors, icons, textures, shadows, and backgrounds.
- Reuse presets to move faster, but check every preset at phone size in the actual segment.
- Keyframes should be shaped, not merely placed; Easy Ease and speed graph work are part of the edit.
- Motion should already feel alive when a segment begins when static starts would feel dead.
- Parent layers deliberately: use parenting for shared scale/position, but remember opacity does not automatically follow child layers.
- Keep dense animation readable by repositioning/restyling duplicate captions and clearing old elements before the next idea. Suppress captions only with explicit user approval.
- Heavy effects can be disabled during editing for speed, but must be enabled before render.
- Start from a sketch or written animation plan; After Effects should execute the idea, not invent it from scratch.
- Use simpler tools or Premiere graphics when the beat does not justify AE complexity.

## Techniques

- `technique_cards/nle_shortform_project_asset_template_system_001.json`
- `technique_cards/story_reel_segment_ideation_board_001.json`
- `technique_cards/nle_fourk_to_1080_reel_prep_001.json`
- `technique_cards/aftereffects_eye_locked_zoom_text_parenting_001.json`
- `technique_cards/aftereffects_text_animation_preset_stack_001.json`
- `technique_cards/aftereffects_track_matte_texture_cutout_001.json`
- `technique_cards/aftereffects_null_camera_scene_motion_001.json`
- `technique_cards/aftereffects_path_counter_motion_001.json`
- `technique_cards/aftereffects_branded_background_texture_system_001.json`
- `technique_cards/premiere_aftereffects_render_finish_roundtrip_001.json`
- `technique_cards/motion_keyframe_focus_zoom_hold_001.json`
- `technique_cards/motion_show_dont_tell_visual_stack_001.json`
- `technique_cards/motion_overlay_readability_focus_stack_001.json`
- `technique_cards/sound_sfx_variation_exaggeration_001.json`
- `technique_cards/motion_sketch_to_animation_ladder_001.json`
- `technique_cards/motion_premiere_text_pop_scale_preset_001.json`

## Timing Rules

- Hook motion should support a clear first-five-second claim, not delay it.
- Text entrances should start on or just before the spoken word they represent.
- Position+opacity entrances often feel cleaner when opacity starts slightly before the position settle.
- Path/counter animations should reach the final path point or value while the spoken concept is still active.
- Camera/null moves can begin a few frames before the visible beat so the scene does not start dead.
- Out animations or overlay transitions are required when elements would otherwise disappear harshly.
- Render the AE animation pass before final captions so caption collisions can be judged in context.
- Animation reveal order should follow the voiceover explanation and not lag behind it.

## Motion Rules

- Keep speaker eyes aligned during zooms by using a guide and animating scale plus position together.
- Parent hook text to the video only when it should scale as if attached to the shot.
- Apply the same motion to original footage and rotoscope/cutout duplicates.
- Use Shy layers to focus on the current segment in crowded compositions.
- Use null objects to group scene motion when direct keyframes would conflict with other movements.
- Use camera plus orbit null for real 3D scene moves; keep simpler scenes 2D.
- Convert only the layers that need camera response to 3D.
- Use Trim Paths for highlights, lines, and route drawing.
- Copy shape paths into Position only after the visible path has its final size and shape.
- Use track mattes with duplicate cutouts so textures do not erase the original image.
- Use turbulent displacement, glow, shadow, vignette, grid, noise, and texture subtly.
- Use text, shape, and pen tools to build the base design before adding typewriter, Trim Paths, glow, or camera polish.

## Sound Rules

- SFX should be added after visual motion is locked enough to mark exact frames.
- Whooshes, hits, typewriter sounds, and reward cues should land on real text, icon, zoom, path, or reveal beats.
- Keep SFX and music below dialogue; captions should not rescue a bad mix.
- Music should be aligned to the final animated edit, then ducked or split around dialogue-heavy sections.

## Caption Rules

- Keep captions visible or repositioned where hook text, animated text, path labels, or CTA text already carries the line. Suppress only with explicit user approval.
- Fade captions out before a dense animation rather than cutting them off harshly.
- Caption style should be applied after transcript cleanup and checked over the AE render.
- Captions should not cover counters, path endpoints, icons, faces, or CTA words.

## Color Rules

- Use brand/client colors consistently across backgrounds, icons, text, glows, and overlays.
- Subtle Lumetri correction should preserve skin and detail before the AE pass.
- Textures should add depth without creating dirty compression, banding, or low contrast.
- Avoid random colors that break the editing signature.

## Tool Implementation Notes

- Premiere: prepare synced and trimmed 1080x1920 footage, export a prepared render, then import AE animation render for finishing.
- After Effects: create a vertical comp, trim layers by segment, use Shy layers, save animation presets, and render a checked animation pass.
- Remotion: model this as segment data with style tokens, parent IDs, 3D/camera metadata, caption continuity policy, any user-approved suppression exception, and SFX frame markers.
- ffmpeg: use for conforming, downscaling, contact sheets, audio checks, and final probes; complex AE motion should be pre-rendered or rebuilt in Remotion.
- CapCut: simplify AE-heavy concepts into grouped keyframes, text animation presets, overlays, caption continuity checks, and any user-approved suppression exception.
- Simple-tool animation equivalent: export at high enough resolution if the edit will zoom into the render.

## Common Mistakes

- Animating before the message and rough cut are clear.
- Letting every segment become equally complex.
- Using assets that do not match the brand/style system.
- Forgetting to center anchor points before scaling/animating text or icons.
- Leaving layers untrimmed across unrelated segments.
- Making camera moves that reveal background edges.
- Forgetting that opacity does not automatically follow a parent layer.
- Letting elements vanish without an out animation or overlay transition.
- Forgetting to enable disabled effects before render.
- Exporting from Premiere with a muted music, SFX, or dialogue track.
- Building an AE scene before sketching the boxes, arrows, labels, reveal order, or focus path.
- Spending AE time on a line that only needed a simple text card.

## QC Checklist

- Each animated segment has a written visual job.
- All layers are trimmed to their intended segment.
- Hook text is readable and clear within the first five seconds.
- Speaker eyes remain stable through zooms.
- Original and rotoscope/cutout layers share intended motion.
- Text, icons, paths, counters, and camera moves are synced to spoken concepts.
- Heavy effects are enabled before render.
- Captions are visible, repositioned, faded, or explicitly approved for suppression where dense animation carries the same idea.
- AE render duration, resolution, frame rate, and color match the Premiere timeline.
- Final Premiere export has no muted required tracks, duplicate render audio, caption collisions, or accidental overlays.
- The animation plan exists before the AE build begins.
- The chosen animation tool is justified by the line's importance.

## Source Lessons Added

- 2026-05-28: `Edit High Quality Reel`
- 2026-05-29: `Editing Viral Videos`

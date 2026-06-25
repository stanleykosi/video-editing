# Lesson: Edit High Quality Reel With Premiere And After Effects

## Source

- Tutorial: `Edit High Quality Reel`
- Notes: `transcripts/edit high quality reel.txt`
- Related cards:
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

## What The Tutorial Teaches

This tutorial teaches a full high-quality short-form production pipeline: organize client/self/assets folders, define an editing signature, build Premiere and After Effects templates, prepare 4K footage for 1080x1920 delivery, storyboard each spoken segment before animating, build After Effects scenes with keyframes, text animators, mattes, nulls, 3D cameras, path motion, and reusable presets, then return to Premiere for overlays, SFX, music, captions, and export QC.

The useful agent knowledge is the layered workflow: style and project systems first, clean footage prep second, segment ideation third, After Effects animation fourth, Premiere finishing last.

## Agent Decision Rules

- Build folder, project, template, asset, and render structure before editing a batch of reels.
- Define a style foundation from the brand, audience, fonts, colors, icons, backgrounds, and market research; let it evolve, but keep each reel visually coherent.
- Prepare the footage in Premiere before animation: sync audio, downscale to the target delivery size when needed, trim to the strongest short-form cut, and apply subtle correction.
- Ideate each timeline segment before opening After Effects. Decide whether the segment needs only captions, speaker plus text, a full-screen animation, B-roll/images, icons, or no added visual.
- Use After Effects only after the rough cut and segment plan are stable enough to avoid rebuilding animations.
- Keep the speaker's eyes locked during zooms so the subject does not jump around the frame.
- Parent text or duplicate rotoscope layers to the same video movement when they should feel attached to the speaker or background.
- Use nulls, camera orbit nulls, and 3D layers when a scene needs spatial movement; use simpler position/opacity keyframes when a flat layout communicates better.
- Add out animations or a motivated overlay/transition so elements do not vanish on hard cuts.
- Finish in Premiere with overlays, SFX, music, captions, and final export checks after the animation render has been watched.

## Timeline Patterns

- `folder_style_template -> Premiere_sync_and_prep -> rough_cut -> subtle_color -> prepared_render -> After_Effects_segment_animation -> AE_render -> Premiere_finish -> captions -> export_qc`
- `spoken_segment -> ideation_note -> required_assets -> AE_scene_build -> animate_hierarchy -> effects_off_if_lag -> effects_on_before_render -> review_render`
- `hook_claim -> eye_locked_zoom -> text_slide_or_typewriter -> highlight_trim_path -> parent_text_to_video -> SFX_marker`
- `abstract_result -> branded_background -> icons_or_cutouts -> path/counter/camera_motion -> captions_suppressed -> next_segment_transition`

## Implementation Notes

- Premiere: keep one project per client or channel/output type when editing batches, with bins for each reel and template bins/timelines for overlays, SFX, and music.
- Premiere prep: sync external mic audio, delete unwanted camera audio, export 1080x1920 from 4K source when the target platform is HD vertical, reimport that prepared file, trim the short-form cut, apply subtle Lumetri correction on an adjustment layer, and export the prepared edit for After Effects.
- After Effects: build a 1080x1920 composition from the prepared render, add only the needed segment assets, keep layers trimmed to each segment, and use Shy layers to focus on the active scene.
- After Effects text: create reusable presets for slide up/down, smooth typewriter, glow/drop shadow, turbulent displace, and text fades. Name presets by behavior, not by project.
- After Effects motion: use Easy Ease and the speed graph; keyframes can start before the visible segment so motion is already alive when the beat begins.
- After Effects camera: create a camera plus orbit null, convert intended layers to 3D, and trim each camera/null pair to the exact scene range.
- After Effects path/counter: copy a shape path into an object's Position property for path-follow motion; use Slider Control plus a source-text expression for number counters.
- After Effects backgrounds: use solids, gradient ramp, vignette, noise alpha, grids, or Venetian Blinds, but keep the palette consistent with the brand/style.
- Premiere finishing: import the AE render, unlink and remove its audio if the original mix is kept, add overlays, SFX, music, and captions, then export only after all tracks are unmuted and checked.
- Remotion equivalent: represent this as a data-driven pipeline with project metadata, style tokens, segment plans, asset manifests, animation components, caption suppression flags, and final mix metadata.
- ffmpeg equivalent: keep the NLE/AE steps as EDL-like metadata where possible; use ffmpeg for conforming, downscaling, preliminary trims, subtitle burn-ins, contact sheets, loudness checks, and final QC probes.

## Mistakes And QC

- Do not start After Effects animation before the short-form edit and segment plan are stable.
- Do not download or import assets without organizing them into the project folder and preserving source/license notes.
- Do not over-correct color; subtle adjustment-layer correction is safer for brand reels.
- Do not let animation elements disappear on a hard cut unless a transition overlay or hard-cut style intentionally covers it.
- Do not leave heavy effects disabled before render.
- Do not forget the rotoscope duplicate when applying zooms or parented motion.
- Do not trust the final export if any music, SFX, or voice tracks were muted during checking.
- Do not leave captions over major animations that already communicate the same idea.

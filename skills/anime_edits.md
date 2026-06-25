# Anime Edits

## Purpose

Guide anime montage, character edits, action sync, source-audio moments, stylized
effects, and music-led pacing without turning the timeline into unreadable noise.

## When to use this skill

- Editing anime power edits, character tributes, action montages, or beat-synced clips.
- Combining music with selected dialogue, voice lines, impacts, whooshes, glitches, or texture SFX.
- Designing CapCut-style AMV edits with speed matching, masks, glow, shadow, flicker, turbulent transitions, and wide-angle shakes.
- Designing CapCut anime power edits with eye overlays, pendulum movement passes, and character-specific SFX.
- Using graph-shaped CapCut zooms and motion blur for stylized anime/action impact moments.
- Reviewing anime/action edits for accidental source subtitles, credits, watermarks, unreadable action, or unsafe audio/source usage.

## Core principles

- Sync action peaks, transformations, reveals, and impacts to musical structure.
- Use source dialogue or voice lines only when they anchor identity, emotion, or intensity.
- Design the clean action beat before adding glow, turbulent effects, shake, or SFX.
- Shape zoom graphs after the action beat is readable; smooth motion cannot rescue unclear framing.
- Align small power details through playback before baking them; a cool eye overlay fails if it drifts or hides expression.
- Keep one primary focus per moment: character, impact, transition, or text.
- Use repeated shots only when repetition is a deliberate motif.
- Preserve rights awareness: anime clips, voice lines, music, SFX, overlays, and cutouts need clearance or temp labels for real projects.

## Techniques

- `technique_cards/beat_sync_capcut_speed_match_twixtor_001.json`
- `technique_cards/motion_capcut_character_mask_shadow_glow_001.json`
- `technique_cards/nle_capcut_heavy_overlay_prerender_workflow_001.json`
- `technique_cards/transition_capcut_turbulent_wide_angle_shake_001.json`
- `technique_cards/sound_anime_edit_sfx_voice_line_spotting_001.json`
- `technique_cards/motion_capcut_effect_tail_extension_001.json`
- `technique_cards/compositing_capcut_eye_power_overlay_001.json`
- `technique_cards/motion_capcut_pendulum_transition_movement_001.json`
- `technique_cards/motion_capcut_graph_curve_easing_001.json`
- `technique_cards/motion_capcut_graph_zoom_stack_001.json`
- `technique_cards/beat_sync_needle_drop_action_cue_001.json`
- `technique_cards/sound_sfx_variation_exaggeration_001.json`
- `technique_cards/qc_narration_visual_character_alignment_001.json`

Future gaps to card when a strong source appears: dialogue-to-drop, transformation build, impact flash, color callback, and character identity stamp.

## Timing rules

- Action peaks should land within 1-2 frames of the intended beat when high-energy sync matters.
- Use beat markers before speed-matching multiple clips.
- Adjust clip speed per action beat; do not reuse one universal value across every clip.
- Add transition shakes after turbulent, wide-angle, and zoom effects are visible.
- Add pendulum movement only after speed matching, then judge it with the transition pass.
- Eye/power overlays should reveal or lock within the intended beat tolerance when they are the transformation moment.
- Keep effect-tail extensions only as long as the intended beat needs them.
- Let voice lines start at or just before the clip beat only when they anchor identity or emotion.
- Graph zooms should land and settle on readable character poses or impacts.
- In narrated anime recaps or commentary edits, named-character visuals should arrive slightly before the viewer-facing spoken-name timestamp. If the narrator says the character name around `0:42`, the frame a viewer sees at `0:42` should already be that character, not a carryover from the prior beat.

## Motion rules

- Speed changes must preserve the readable pose, impact, or motion direction.
- Character glow, shadow, and flicker should be isolated to the subject or body part that carries the beat.
- Mask edges must stay clean through motion, shake, and flicker.
- Turbulent and wide-angle transitions should peak on the cut or beat and settle before the next action pose.
- Heavy overlay clips can be built in isolated projects or compounds, then replaced into the main timeline for smoother transition work.
- Eye overlays, symbols, and power details should track the visible feature through playback and clear before drift is obvious.
- One Pendulum pass adds movement; two creates strong swing; three is extreme and needs phone-size readability approval.
- Intense zoom stacks need scale and position keyframes together so the character remains centered.
- Motion blur should support the zoom energy without smearing the character pose.

## Sound rules

- Every SFX cue needs a visible job: whoosh, hit, texture, glitch, transition, reveal, or character identity.
- Match SFX to the specific event family: entrance, lightning, glass, eye transformation, or identity voice line.
- Voice lines should clarify the clip instead of filling every gap.
- SFX tails should fade or trim before the next beat or voice line.
- Review the full mix with music, SFX, and voice lines active before export.
- Treat downloaded music, voice lines, and SFX as temp until rights or platform safety are confirmed.
- When source audio is muted under narration, scene choice follows the narration identity and meaning, not the source sequence order or music energy.

## Caption rules

- Avoid accidental source subtitles, credits, watermarks, and title-card flashes.
- Captions should not cover action peaks, character glow, transition impact, or readable poses.
- Caption voice lines only when they are story-critical or hard to understand.
- Move, restyle, or explicitly approve suppression for captions over the most chaotic transition frames.

## Color rules

- Glow, flicker, flashes, and color correction should preserve character silhouette and action readability.
- Background slices or effect tails should match the palette enough that they do not steal focus.
- Avoid noisy duplicate layers that create banding, mud, or compression dirt.

## Tool implementation notes

- CapCut: use beat markers, Speed, Duplicate, Mask, Remove Background/quick brush, overlays, effect layers, separate projects/compounds, and Sounds > Device imports.
- ffmpeg: use `setpts` for speed-matched visuals, alpha mattes or cutouts for isolated glow, pre-rendered intermediates for dense sections, and `adelay`/`amix` for frame-placed SFX.
- Remotion: store beat frames, action peak frames, playbackRate, subject masks, transition shake ranges, SFX frames, and license/temp status in structured metadata.
- Premiere: use Speed/Duration or Time Remapping, masked duplicate layers, nested sequences or Render and Replace, Turbulent Displace/Lens Distortion/Transform shake, and marker-based SFX spotting.

## Common mistakes

- Adding effects before the action and beat timing are clean.
- Speeding clips until the action becomes unreadable.
- Leaving rough masks, halo edges, or glow spilling over the wrong subject.
- Applying the same shake, hit, or voice-line pattern to every clip.
- Baking captions or final SFX into pre-rendered clips that still need top-level edits.
- Using unlicensed music, character footage, voice lines, or SFX in a publishable edit.
- Scaling or blurring the character until the action pose becomes unreadable.
- Letting a previous character's shot remain visible during the next character's narrated section because the exact EDL cut happens later inside the same rounded playback second.

## QC checklist

- No unintended source subtitles, credits, UI overlays, or watermarks.
- Action remains readable after speed changes, effects, masks, and transitions.
- Beat-synced peaks land within the intended tolerance.
- Eye/power overlays stay aligned and do not cover the character expression.
- Pendulum movement does not hide the action pose or next transition.
- Character masks/glow/shadow preserve clean edges and do not cover captions.
- Turbulent/wide-angle transitions settle before the next action must be read.
- Music, voice lines, and SFX do not fight each other or clip.
- Audio/source rights are licensed, platform-safe, or marked temp-only.
- Graph zooms and motion blur preserve readable character action at phone size.
- Narrated character handoffs have timestamped rendered-output spot checks; every spoken character name shows the matching character at the viewer-facing timestamp and in the promoted final.

## Source lessons added

- 2026-05-29: `Editing Tricks`
- 2026-05-29: `Keyframe Graph Tutorial`
- 2026-05-29: `Powerful CapCut Edits`
- 2026-05-29: `CapCut Text Effects`
- 2026-06-23: `Bleach Women Recap Character Alignment Correction`

# DaVinci Resolve Short-Form Workflow

## Purpose

Guide DaVinci Resolve-specific short-form editing workflows, including vertical
project setup, clean A-roll/B-roll assembly, Fusion motion, Text+ captions,
Power Bins, transitions, and efficiency shortcuts.

## When To Use This Skill

- Editing Reels, TikToks, Shorts, or vertical talking-head clips in DaVinci Resolve.
- Translating Resolve tutorials into agent-ready workflow steps.
- Pulling short-form pieces from a larger Resolve project that already has media,
  synced audio, color, Fairlight, or Deliver requirements.
- Building Fusion-based short-form zooms, punch-ins, text stacks, overlays, and flashes.
- Creating reusable Resolve presets with Power Bins.
- Checking whether a Resolve edit is simple, postable, polished, or preset-ready.
- Comparing stacked timeline versions to choose a balanced short-form cut before polish.
- Building premium Resolve/Fusion intros with brand, proof, outcome text, logo movement, flicker, and frame-locked SFX.

## Core Principles

- Set the project to vertical resolution before judging layout, captions, or overlays.
- Build the simple edit first: clean A-roll cuts, motivated B-roll, muted B-roll audio, and readable captions.
- Use the Edit page for assembly and the Fusion page for custom motion/text effects.
- Keep the Effects Library and Inspector available during short-form editing.
- Prefer `Text+` when the caption or title needs Fusion-level styling or motion.
- Use adjustment clips for reusable Fusion motion that should affect a clip range.
- Smooth Fusion animation with Spline easing; do not leave important motion accidentally linear.
- Save checked effects into Power Bins only after phone-size QC.
- Efficiency is part of pro editing: shortcuts, presets, and reusable style systems matter more than rebuilding every effect.
- More effects are not automatically better; preset speed should serve clarity, consistency, and output volume.
- Use stacked timelines or named timeline duplicates to compare original, shorter, and balanced versions before committing Fusion, captions, or color.
- Dynamic Zoom is valid for slow human shorts when a simple move carries the hook or emotional section without extra Fusion complexity.
- Use `knowledge/playbooks/davinci_resolve_full_workflow.md` when the task expands beyond a
  vertical short into Media page organization, Cut page multicam, Color, Fairlight,
  or Deliver decisions.
- Use Fusion for a premium intro only when Text+, Transform, MultiMerge, masks, motion blur, or 3D/camera-style movement improves brand/proof/outcome clarity.

## Techniques

- `knowledge/techniques/nle_workflow/davinci_vertical_short_project_setup_001.json`
- `knowledge/techniques/motion/davinci_fusion_spline_zoom_animation_001.json`
- `knowledge/techniques/captions/davinci_textplus_premium_caption_stack_001.json`
- `knowledge/techniques/transition/davinci_white_flash_transition_001.json`
- `knowledge/techniques/nle_workflow/davinci_power_bins_preset_workflow_001.json`
- `knowledge/techniques/nle_workflow/davinci_timeline_shortcuts_efficiency_001.json`
- `knowledge/techniques/nle_workflow/davinci_project_library_media_pool_setup_001.json`
- `knowledge/techniques/sound_design/davinci_waveform_audio_sync_media_pool_001.json`
- `knowledge/techniques/nle_workflow/davinci_edit_page_in_out_story_assembly_001.json`
- `knowledge/techniques/nle_workflow/davinci_deliver_codec_render_queue_archive_001.json`
- `knowledge/techniques/nle_workflow/nle_rough_cut_second_pass_workflow_001.json`
- `knowledge/techniques/story_pacing/motivated_broll_story_sequence_001.json`
- `knowledge/techniques/captions/captions_two_word_social_subtitles_001.json`
- `knowledge/techniques/motion/motion_subject_tracking_statement_zoom_001.json`
- `knowledge/techniques/motion/motion_show_dont_tell_visual_stack_001.json`
- `knowledge/techniques/retention/retention_first_three_second_dynamic_zoom_hook_001.json`
- `knowledge/techniques/nle_workflow/nle_stacked_timeline_versioning_001.json`
- `knowledge/techniques/retention/retention_human_imperfection_pattern_interrupt_001.json`
- `knowledge/techniques/retention/retention_intro_format_gate_001.json`
- `knowledge/techniques/retention/retention_brand_authority_outcome_intro_001.json`
- `knowledge/techniques/motion/motion_premium_intro_text_logo_flicker_001.json`
- `knowledge/techniques/sound_design/sound_frame_locked_intro_sfx_drums_001.json`

## Timing Rules

- Remove accidental dead air over 300 ms in short-form A-roll unless it has a clear purpose.
- Place B-roll on key lines, not at random intervals.
- Manual white flashes should peak around the cut and fade down within a few frames.
- Text+ stack clips can be very short for fast emphasis, but must remain readable at phone size.
- Fusion motion should land on the spoken reference, cut, beat, or B-roll entry it supports.
- Compare major duration versions before Text+, Fusion, SFX, and color work create churn.
- For slow human shorts, keep micro black/drop gaps under one second unless the pause is intentionally cinematic.
- For social-series Resolve intros, trim the finished compound/Fusion intro to about 3-5 seconds.
- For show/podcast/course intros built in Resolve, keep the bumper around 10-15 seconds maximum.

## Motion Rules

- Use Fusion Transform nodes for controlled size, x/y position, and angle animation.
- Use Spline `Out Cubic` as a starting point for crisp short-form motion.
- A strong B-roll zoom-out can start around Size `1.95` and animate to `1.0` only if crop remains safe.
- Dynamic Zoom is acceptable for quick in/out moves when manual Fusion control is unnecessary.
- Dynamic Zoom can carry a first 3-5 second hook or longer emotional passage if the face, proof, and captions remain safe.
- Check that adjustment clips affect only their intended range.
- Use viewer background changes to inspect black edges or black-on-black elements, then restore review assumptions.
- For premium intros, assign Text+ layers to brand, proof, outcome, keyword, underline, or transition before animating.
- Flicker, font changes, motion blur, and 3D-style camera moves must preserve phone-size readability.

## Sound Rules

- Delete or mute unwanted B-roll source audio.
- Use audio transitions or fades when audio edges click or feel harsh.
- Keep dialogue dominant under SFX, music, and whooshes.
- Resolve in-app voiceover can be useful, but the recording still needs level, noise, and timing QC.
- Foley or texture added to human cutaways should stay on separate tracks and below dialogue.
- Place intro SFX on visible logo, text, flicker, underline, camera, cut, or transition frames and duck before body speech.

## Caption Rules

- Use Resolve auto captions for simple postable styles when speed matters.
- Use `Text+` for premium animated caption stacks, gradients, glow, glitch, or emphasis text.
- Do not let Text+ stacks duplicate auto captions unless the duplicate is intentional emphasis.
- Gradient, glow, blur, glitch, and Stop Motion treatments must preserve readability.
- Captions and Text+ should avoid face, hands, proof, and title-safe areas.
- For warm human shorts, prefer restrained caption styling when Text+ energy would make the moment feel too digital.
- Keep auto captions visible or repositioned under designed intro Text+ when the designed text already carries brand, proof, or outcome; suppress only with explicit user approval.

## Color Rules

- Do not apply LUTs, film grain, or style looks before vertical crop and caption readability are safe.
- Gradient text colors must remain readable over the actual background.
- Color presets should preserve skin tone and caption contrast before entering Power Bins or style packs.
- Warm hopeful looks should preserve skin, proof, and caption readability before glow, grain, radial blur, or vignette are approved.

## Tool Implementation Notes

- Resolve setup: use `Shift+9` project settings and enable vertical resolution for vertical shorts.
- Resolve assembly: use the Edit page, Effects Library, Inspector, A-roll/B-roll tracks, and caption tools.
- Resolve Fusion: use adjustment clips, `Text+`, Transform nodes, Gaussian Blur, Glow, Stop Motion, Spline curves, and Dynamic Zoom.
- Resolve presets: enable/show Power Bins, create named bins, drag checked effects into them, and rename by job.
- Resolve stacked timelines: compare original, short, and balanced timeline versions before choosing the edit to polish.
- Resolve shortcuts: document local mappings for split, ripple delete, duplicate, select left/right, swap clip, deactivate clip, and open target in Fusion.
- Resolve full-workflow handoff: for larger projects, organize Media Pool bins,
  sync external audio, assemble in Edit/Cut, then use Fusion, Color, Fairlight,
  and Deliver only after the short's story cut is stable.
- Resolve intro workflow: build the brand/proof/outcome beats as a compound/Fusion clip, mark bodyStartFrame, add SFX markers, then trim the compound to the platform duration cap.
- ffmpeg equivalent: use vertical crop/pad, filter-chain templates, drawtext, overlays, opacity envelopes, and JSON/YAML reusable presets.
- Remotion equivalent: create reusable components for Resolve-like motion, captions, flashes, visual stacks, and Power Bin-style presets.
- CapCut/Premiere equivalent: use vertical project settings, text templates, saved presets, adjustment layers, nested sequences, and motion/text styles.

## Common Mistakes

- Adding Fusion polish before the simple edit is clean.
- Forgetting vertical resolution before placing captions and overlays.
- Leaving unwanted B-roll audio under speech.
- Overusing built-in transitions or flashes on every cut.
- Leaving Fusion animation linear or too slow because Spline was not adjusted.
- Saving untested effects into Power Bins.
- Letting Power Bins fill with vague duplicate presets.
- Believing ten hours of effects automatically makes a better short.
- Polishing the first timeline without comparing a shorter and balanced version.
- Opening Fusion for a simple Dynamic Zoom that does not need manual node control.
- Building a Fusion intro before proving that the format needs a bumper.
- Saving premium intro effects to Power Bins before checking brand/proof/outcome readability on a phone preview.

## QC Checklist

- Project is vertical before layout decisions are judged.
- A-roll cuts are tight and no short-form dead air over 300 ms remains without purpose.
- B-roll appears on motivated key lines and unwanted B-roll audio is removed.
- Fusion animation uses intentional easing and preserves face, hands, captions, proof, and action.
- Auto captions and Text+ stacks do not collide or duplicate clutter.
- White flashes are brief, intentional, and render cleanly.
- Power Bin presets were phone-size checked before saving.
- Shortcut-based moves did not desync captions, SFX, or B-roll.
- Final vertical render has readable captions, safe crop, clean audio, and no accidental overlays.
- The exported version matches the intended named timeline.
- Slow human sections have a clear hook, connection purpose, and crop-safe Dynamic Zoom.
- If the short comes from a larger Resolve project, Media Pool organization,
  synced audio, Color/Fairlight changes, and Deliver range/settings are checked.
- Any Resolve intro passes the format gate, duration cap, Text+/caption collision check, and frame-locked SFX review.

## Source Lessons Added

- 2026-05-28: `DaVinci Resolve Short Form Editing`
- 2026-05-29: `Slow Editing`
- 2026-05-29: `DaVinci Resolve Full Tutorial`
- 2026-05-29: `Killer Intros`

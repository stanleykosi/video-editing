# Lesson: DaVinci Resolve Short-Form Workflow

## Source

- Tutorial: `DaVinci Resolve Short Form Editing`
- Notes: `knowledge/research/transcripts/davinci resolve short form editing.txt`
- Date processed: 2026-05-28
- Related cards:
  - `knowledge/techniques/nle_workflow/davinci_vertical_short_project_setup_001.json`
  - `knowledge/techniques/motion/davinci_fusion_spline_zoom_animation_001.json`
  - `knowledge/techniques/captions/davinci_textplus_premium_caption_stack_001.json`
  - `knowledge/techniques/transition/davinci_white_flash_transition_001.json`
  - `knowledge/techniques/nle_workflow/davinci_power_bins_preset_workflow_001.json`
  - `knowledge/techniques/nle_workflow/davinci_timeline_shortcuts_efficiency_001.json`

## What The Tutorial Teaches

This tutorial teaches a three-phase DaVinci Resolve short-form workflow. Phase one is a simple postable reel: vertical project setup, clean A-roll cuts, motivated B-roll, audio removal from B-roll, and auto captions. Phase two adds polish through Fusion: adjustment clips, Transform nodes, Spline easing, dynamic zooms, Text+ caption stacks, overlays, white flashes, gradient/glitch text, and selective B-roll emphasis. Phase three is the pro workflow: build reusable presets in Power Bins, use shortcuts to move faster, and prioritize efficiency over endless effects.

## Agent Decision Rules

- Use Resolve's vertical resolution setting before cutting a short-form project.
- Work mainly in the Edit page for assembly and Fusion page for custom motion/text effects.
- Keep the Effects Library and Inspector available during short-form editing.
- Start with a clean simple edit before adding Fusion polish.
- Use three to four motivated B-roll shots where they support key lines, then delete or mute B-roll source audio unless it is intentionally useful.
- Use Text+ for custom captions and motion text; use basic auto captions only when a simple style is enough.
- Add Fusion animation through adjustment clips or Text+ nodes, then smooth it with Spline easing.
- Use Power Bins for any reusable animation, caption, flash, overlay, or adjustment clip preset that should appear in future projects.
- Prefer reusable presets and keyboard shortcuts over rebuilding the same effect repeatedly.
- Do not mistake time spent or effect count for pro quality; speed, consistency, and a unique reusable style are part of the edit quality.

## Timeline Patterns

- Simple Resolve short: `new_project -> vertical_resolution -> import_a_roll_b_roll -> clean_cuts -> motivated_broll -> remove_broll_audio -> auto_captions -> simple_export_qc`.
- Fusion B-roll polish: `broll_clip -> adjustment_clip -> Fusion Transform -> size/position keyframes -> out_cubic_spline -> dynamic_zoom_or_punch -> return_to_a_roll`.
- Premium Text+ stack: `Text+ -> Fusion nodes -> blur/transform -> gradient_or_glow -> short staggered text layers -> caption_safe_qc`.
- White flash: `solid_color_or_white_flash_transition -> opacity_keyframes_or_builtin_transition -> 2-3_frame_flash_peak -> next_clip`.
- Power Bin workflow: `build_effect -> verify_effect -> drag_to_power_bin -> rename_by_job -> reuse_in_new_project -> customize_text_or_color`.
- Efficiency shortcuts: `split -> ripple_delete -> option_drag_duplicate -> open_target_in_fusion -> select_left_or_right -> swap_clip_left_right`.

## Implementation Notes

- ffmpeg: model vertical setup with `scale`, `crop`, and `pad`; model simple white flashes with a white overlay and opacity envelope; model reusable presets as JSON filter templates.
- Remotion: store Resolve-like presets as components with `vertical`, `effectName`, `powerBinName`, `fusionNodes`, `spline`, `captionStyle`, and `shortcutEquivalent` metadata.
- Blender: use camera/text keyframes for Resolve-style motion when a custom rendered element is needed.
- CapCut: use project aspect ratio, keyframes, text templates, auto captions, saved favorite effects, and template reuse as rough equivalents.
- Premiere: use sequence settings, adjustment layers, Essential Graphics, text styles, nested sequences, Motion presets, keyboard shortcuts, and project bins as rough equivalents.
- DaVinci Resolve: use Shift+9 project settings, Use Vertical Resolution, Edit page Effects Library, Inspector, Text+, adjustment clips, Fusion Transform nodes, Spline easing, Dynamic Zoom, Power Bins, and Resolve shortcuts.

## Mistakes And QC

- Building flashy Fusion effects before the simple cut works.
- Forgetting to switch the project to vertical resolution before layout decisions.
- Leaving unwanted B-roll audio under the talking head.
- Overusing built-in transitions instead of checking whether a simple cut, B-roll insert, or white flash is enough.
- Using Fusion text stacks that collide with auto captions.
- Creating a reusable preset before the effect has been checked at phone size.
- Letting Power Bins become unnamed clutter.
- Spending many hours on one short when a reusable preset system would create more consistent output faster.

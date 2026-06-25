# Lesson: CapCut Keyframe Graph Zoom

## Source

- Tutorial: `Keyframe Graph Tutorial`
- Notes: `transcripts/keyframe graph tutorial.txt`
- Date processed: 2026-05-29
- Related cards:
  - `technique_cards/motion_capcut_graph_curve_easing_001.json`
  - `technique_cards/motion_capcut_graph_zoom_stack_001.json`

## What The Tutorial Teaches

This tutorial explains CapCut graphs as speed-shaping controls between keyframes.
Keyframes define the start and end values for scale, position, rotation, or other
properties. Graphs control how the movement accelerates, holds speed, or eases
into the final frame.

It then applies the graph idea to a stylized zoom workflow: keyframe a first zoom
pass, shape the graph, export, re-import the rendered result, add a second zoom
pass, export again, then apply motion blur.

## Agent Decision Rules

- Use graph curves when a keyframed move feels linear, robotic, abrupt, or cheap.
- Use a slow-start graph when the viewer needs a gentle pickup into motion.
- Use a fast-start graph when the move should snap immediately from the first frame.
- Use a gentle end curve when the final focus needs to settle cleanly.
- Use a sharp end only when the style intentionally wants a hard stop or impact.
- Use stacked export zooms only for stylized, high-energy edits where the crop,
  resolution, and action readability can survive the extra magnification.
- Add motion blur after the zoom timing is locked, not before judging scale,
  position, or graph shape.

## Timeline Patterns

- Graph curve setup:
  `start_keyframe -> end_keyframe -> graph_editor -> start_speed/end_speed_curve -> preview -> adjust`
- CapCut zoom-in stack:
  `clip -> start/end keyframes -> scale_300_center_subject -> graph_curve -> export -> reimport -> split -> scale_150_center_subject -> graph_curve -> export -> motion_blur_10_blend_10`
- Zoom-out variation:
  `zoomed_state -> end_context_state -> graph_curve -> preview_subject_center -> optional_export_stack -> motion_blur_after_timing_lock`

## Implementation Notes

- ffmpeg: store keyframe values plus easing metadata. Approximate graph curves
  with expressions for scale/crop/translate and render short tests around the
  start, peak, and settle frames.
- Remotion: represent curves with easing functions or cubic-bezier control data,
  then interpolate scale and position from the same curve metadata.
- CapCut: create start and end keyframes, select the final keyframe, set Basic
  scale and position, use Graphs to shape speed, export/re-import only when
  stacking zoom passes is intentional, then add Motion Blur after timing is
  locked.
- Premiere: use Effect Controls or Transform keyframes with Bezier/Ease In/Ease
  Out, nest when stacking zoom passes, and use Transform shutter angle or blur
  effects after checking crop and caption safety.

## Mistakes And QC

- Do not treat graph presets as automatically professional; preview the actual
  motion and subject position.
- Do not use a flat or linear graph when the move needs a natural accelerate or
  settle.
- Do not use an extreme sharp curve unless the jolt is intentional.
- Do not scale to 300% or stack exports when the source is too soft, noisy, or
  caption-heavy.
- Check that the subject stays centered during both zoom passes.
- Check that motion blur does not smear faces, captions, proof, or action.

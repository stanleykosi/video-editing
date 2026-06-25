# Lesson: Still Image To Cinematic Media

## Source

- Tutorial: `Still Image To Media`
- Notes: `transcripts/still image to media.txt`
- Date processed: 2026-05-29
- Related cards:
  - `technique_cards/motion_still_image_environment_composite_001.json`
  - `technique_cards/motion_masked_firelight_strobe_reflection_001.json`
  - `technique_cards/color_low_key_firelight_scene_unification_001.json`

## What The Tutorial Teaches

This tutorial shows how to turn a static image into a moving cinematic scene by
layering motivated motion sources over the still image. The main construction is
a night scene with a fire overlay, a moving sky overlay, localized flicker on
nearby surfaces, and a final low-key warm grade that makes the separate layers
feel like one shot.

The important editing idea is not the exact stock clip choice. The reusable
lesson is to add motion only where the still image implies motion already exists:
fire moves at the fire source, sky movement sits behind architecture, and flicker
appears only on nearby surfaces that would plausibly catch light.

## Agent Decision Rules

- Use this workflow when a still image needs believable environmental motion
  rather than full animation.
- Choose overlays that match the base image's perspective, mood, direction, and
  light source.
- Use Screen or Add-style blending for black-background fire, sparks, smoke,
  glow, or atmosphere overlays when the black should disappear.
- Use masks with high feathering when replacing or extending parts of a still
  image, such as sky or localized light.
- Add local flicker only where a visible source would naturally reflect, such as
  a wall, face, object, or ground near a fire.
- Darken or reshape the base image only enough to make the added moving element
  feel motivated.
- Avoid the workflow when the image is documentary evidence that must remain a
  true still, when asset rights are unclear, or when the composite would imply a
  false event.

## Timeline Patterns

- Still image composite:
  `base_still -> fire_or_atmosphere_overlay -> screen_blend -> resize_position -> sky_overlay -> mask_feather -> local_reflection_flicker -> global_adjustment -> glow_or_warm_filter -> export`
- Fire reflection:
  `base_still_duplicate_or_adjustment -> strobe_or_flicker_effect -> circle_mask -> high_feather -> screen_blend_or_opacity -> align_to_visible_fire -> preview_edges`
- Unified grade:
  `base_darkening -> exposure_contrast_tint -> overlay_color_match -> warm_glow_filter -> highlight_check -> caption_and_face_qc`

## Implementation Notes

- ffmpeg: layer the base image as a video stream, loop the still for duration,
  overlay moving assets with Screen/lighten-style blending or pre-keyed alpha,
  apply alpha masks for sky or reflection regions, and finish with eq/curves
  color adjustment.
- Remotion: model the scene as a stack of image and video layers with
  `mixBlendMode`, mask geometry, feather/blur values, transform metadata, and
  global color tokens.
- Blender: place the still and moving overlays as planes or compositor inputs,
  use alpha/masks for sky and reflection zones, then unify the scene with color
  management and glow in the compositor.
- CapCut: place moving clips above the still image, use Screen for black-backed
  overlays, use Mask plus heavy Feather for localized regions, then add an
  Adjustment layer or filter to unify exposure, tint, contrast, and glow.
- Premiere: use higher video tracks with Screen blend mode, opacity masks with
  feather, nested sequences for complex reflection layers, and Lumetri/adjustment
  layers for the final look.

## Mistakes And QC

- Do not add a moving element just because it is available in the library; it
  must have a plausible place in the still image.
- Do not let a full-frame strobe affect the whole shot when only a local
  reflection should flicker.
- Do not leave hard mask edges around sky, fire, or reflection overlays.
- Do not over-darken the base image until faces, architecture, captions, or
  important details disappear.
- Check that every external overlay has source and license notes before a real
  project is delivered.

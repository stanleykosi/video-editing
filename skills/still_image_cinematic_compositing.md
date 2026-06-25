# Still Image Cinematic Compositing

## Purpose

Turn still images, AI images, reference frames, or static plates into believable
moving media by layering motivated environmental motion, soft masks, localized
light, and a unifying grade.

## When To Use This Skill

- A static image needs to feel alive for a cinematic beat, short-form visual, or
  establishing shot.
- The still image already implies motion, such as fire, sky, smoke, water, rain,
  neon, screens, or atmosphere.
- A project needs motion from a still asset without building a full 3D scene or
  complex character animation.
- The edit needs CapCut/Premiere/Remotion instructions for overlays, masks,
  blend modes, and final grade checks.

## Core Principles

- Animate what the image already suggests; do not add unrelated motion.
- Environmental overlays must match the still's perspective, lighting, scale,
  color temperature, and mood.
- Local light sells the composite: fire, neon, screens, or bright practicals
  should affect nearby surfaces, not the whole frame equally.
- Masks should disappear into the image through placement, feathering, opacity,
  and color matching.
- Global filters are the final glue, not a replacement for layer-specific
  matching.
- Every external overlay needs source/license notes before publishable delivery.

## Techniques

- `technique_cards/motion_still_image_environment_composite_001.json`
- `technique_cards/motion_masked_firelight_strobe_reflection_001.json`
- `technique_cards/color_low_key_firelight_scene_unification_001.json`
- `technique_cards/motion_screen_blend_texture_overlay_001.json`

## Timing Rules

- Loop or trim moving overlays so there are no visible start/end pops during the
  still-image beat.
- Local flicker starts and ends with the visible or implied light source.
- Environmental motion should remain subtle enough that the viewer still reads
  the original image.
- Hold the final composite long enough for the viewer to understand the scene,
  especially when the image is an establishing shot or story bridge.

## Motion Rules

- Put the base still on the lowest visual layer and add only motivated moving
  overlays above it.
- Use Screen/Add-style blending for black-background fire, sparks, glow, or
  atmosphere overlays after checking that the black disappears cleanly.
- Use masks with high feathering for sky replacement, reflection zones, or local
  atmosphere.
- Resize and position overlays against real objects in the still image before
  judging the grade.
- Use one or two moving regions first; add more only when each has a clear job.

## Sound Rules

- Add fire crackle, wind, rain, room tone, or low ambience only when it helps the
  scene feel present.
- Keep ambience below dialogue or narration and document music/SFX rights for
  publishable projects.
- Avoid adding a hit or whoosh to every flicker pulse; environmental motion
  usually needs bed sound more than accents.

## Caption Rules

- Captions must stay readable over both the static base and brightest moving
  overlay frames.
- Avoid placing captions on top of flickering reflections, fire, or moving sky if
  the motion changes contrast frame to frame.
- If the composite is only a mood layer behind narration, captions take priority
  over decorative motion.

## Color Rules

- Correct layer mismatch before applying a global filter.
- Darken or warm the base image only enough to motivate the moving light source.
- Match overlays for exposure, contrast, temperature, tint, and highlight detail.
- Use glow or warm filters subtly; they should unify the scene without crushing
  shadows or clipping bright overlays.

## Tool Implementation Notes

- CapCut: place moving clips above the still, set black-background overlays to
  Screen, use Mask plus high Feather for local regions, and finish with an
  Adjustment layer or filter after layer matching.
- Premiere: use higher tracks with Screen/Lighten blend modes, opacity masks with
  feather, nests for multi-layer reflection effects, and Lumetri adjustment
  layers for final unification.
- Remotion: represent the scene with base image, overlay video assets, blend
  mode, transform, mask, feather, loop duration, local light metadata, and grade
  tokens.
- ffmpeg: loop the still, overlay moving assets with alpha or screen/lighten
  approximations, apply soft masks, and render contact frames around the
  brightest and darkest moments.
- Blender: use planes or compositor inputs, soft alpha masks, animated light or
  glow layers, and compositor color management.

## Common Mistakes

- Using a library asset because the keyword matches while the visual fit is poor.
- Letting a sky, fire, smoke, or light mask show a hard edge.
- Applying a strobe or flicker to the whole frame when only a reflected area
  should move.
- Over-darkening the image until the composite feels cinematic but unreadable.
- Forgetting asset rights for stock, generated, or downloaded overlay clips.

## QC Checklist

- Each moving layer has a named reason to exist.
- Overlays match the still image's perspective, scale, brightness, and color.
- Screen/Add overlays remove black backgrounds cleanly.
- Mask edges are invisible at delivery size and full playback speed.
- Local reflections stay weaker than or consistent with their light source.
- Faces, captions, UI, products, proof, and important architecture remain
  readable.
- External overlay assets have manifest-ready source/license notes.

## Source Lessons Added

- 2026-05-29: `Still Image To Media`

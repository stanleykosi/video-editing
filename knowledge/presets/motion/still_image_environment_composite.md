# Still Image Environment Composite

Use when a static image needs believable environmental motion without full
animation.

## Starting Values

- Base layer: still image looped to the target duration.
- Moving overlays: one or two motivated regions first, such as fire, sky, smoke,
  rain, or atmosphere.
- Blend mode: Screen/Add-style for black-background light or fire overlays.
- Mask feather: high enough that sky, reflection, or atmosphere edges disappear.
- Overlay transform: resize and position against real objects in the still.

## Use When

- The image already implies the moving element.
- The overlay matches perspective, brightness, color, and motion direction.

## Avoid When

- The still image is evidence that should not be dramatized.
- The overlay rights are unclear for delivery.
- The moving layer hides captions, faces, products, UI, or proof.

## Related Cards

- `knowledge/techniques/compositing/motion_still_image_environment_composite_001.json`
- `knowledge/techniques/motion/motion_screen_blend_texture_overlay_001.json`

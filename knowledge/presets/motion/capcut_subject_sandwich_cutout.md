# CapCut Subject Sandwich Cutout

Use when text, stickers, graphics, or VFX should appear behind a person inside
CapCut.

## Starting Values

- Bottom layer: exported prepared base with behind-subject element already placed.
- Top layer: original clean clip, full-frame aligned to the prepared base.
- Cutout: Remove Background on the top layer.
- Quick direct method: duplicate the video, remove the subject/object background
  on the top layer, and place text between the video layers.
- Custom Removal starter: Feather `5` and Expansion `5`, then tune by playback.
- Foreground-lift text: place text between video copies, set a Transform keyframe
  while hidden behind the foreground, then raise it on the reveal beat.
- Review: hair, hands, motion blur, turns, and caption collisions.

## Use When

- Timing and behind-element placement are stable enough to bake into a prepared
  render.

## Avoid When

- The subject cutout edge fails or the effect still needs frequent timing changes.
- Trees, water, hair, or hands chatter during a foreground-lift reveal.

## Related Card

- `knowledge/techniques/compositing/compositing_capcut_subject_sandwich_cutout_001.json`

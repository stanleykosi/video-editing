# CapCut Keyframe Motion QC

Use this checklist before approving CapCut-style keyframed motion, color, overlay,
tracking, cutout animation, or music ducking.

## Keyframe Intent

- Each keyframed property has a named job: focus, emphasis, tracking, mood shift, callout, route, comedy, or audio clarity.
- Each changing property has its own start and end keyframe, and unrelated
  properties do not move accidentally.
- Built-in animation was used only where custom keyframes were unnecessary.
- Compound-wrapper animation is used only when it unlocks needed controls for a
  sticker, text layer, or graphic, and the source layer remains editable inside.
- Accidental or duplicate keyframes have been removed.
- Keyframe spacing creates the intended speed, not accidental jolt or drag.
- Graph curves create the intended start speed, acceleration/deceleration, and ending feel.
- Linear graph motion is used only when constant speed is the intended style.

## Motion Safety

- Zooms and tracking preserve faces, hands, captions, proof, UI, products, and action.
- Focus moves hold long enough for the viewer to read the target.
- Scale and position are animated together during zooms so the subject remains centered.
- Quick zooms keep the eyes or named focus target stable when the second
  scale/position keyframe lands.
- Manual subject tracking keeps the chosen subject centered or intentionally offset for text/proof.
- Rotation/tilt effects are zoomed enough to avoid black corners.
- Overlay paths avoid faces, captions, UI, product, proof, and map labels.
- Sticker/object paths have size, flip, and rotation set before position
  keyframes are judged.
- Cutout/object animations have clean enough edges and do not cover the main point.
- Automatic tracking keeps the target visible and does not drift, jitter, or cover
  captions/proof.
- Subject-sandwich foreground layers are frame-aligned and cutout edges remain
  clean through hair, hands, motion blur, and turns.
- Chroma-key, PiP, split-mask, and green-screen layers have clean edges with no
  spill, specks, or visible mask boundary.

## Audio And Color

- Music ducks before speech begins and restores only after speech clears.
- Music duck levels fit the actual song and voice; copied numeric values are
  rejected if speech is not clear.
- Filter-strength reveals rise with music only after speech clears, unless the
  overlap is intentional and the words remain intelligible.
- Music is licensed, platform-safe, or marked temp-only.
- App-library, downloaded, or screen-recorded audio is licensed, platform-safe, or
  marked temp-only.
- Dialogue remains intelligible without captions rescuing the mix.
- Saturation shifts have a named mood or information purpose.
- Faces, products, proof, and captions remain readable through color changes.
- Filter-strength reveals preserve faces, captions, proof, UI, products, and
  brand colors at full strength.

## Asset And Export

- External maps, stock images, icons, stickers, music, and cutouts have source/license notes when used in a real project.
- Green-screen VFX, photo overlays, PiP borders, and sticker assets have
  source/license notes when used in a real project.
- Final preview is checked at phone size.
- No keyframed layer drifts, pops, or remains onscreen after its spoken concept has passed.
- Compound-wrapper animations do not duplicate a source layer animation unless
  the double motion is intentional.
- Motion blur is added only after graph timing is locked.
- Motion blur does not smear captions, faces, proof, UI, products, or action.
- Export/re-import zoom stacks preserve enough source detail for delivery.

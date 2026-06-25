# CapCut Documentary Parallax Collage

Use for historical, editorial, or explainer scenes where cutout images and text
need depth over a stylized background.

## Starting Values

- Build background longer than needed, then trim after the sequence works.
- Use about `5s` per image as a planning placeholder when no VO timing exists.
- Fade image outs around `0.5s`.
- Use short opacity keyframes from `0` to `100%` for manual fade-ins.
- Apply Cubic Ease to scale, X, and Y after keyframe changes.
- Copy foreground motion to background only as a starting point, then reduce
  background scale and position changes.
- Use light mist/rain/particles/vignette only after the motion and text read.

## QC

- Cutouts have source/license status.
- Foreground and background move differently enough to create depth.
- Text behind cutouts is still readable.
- Captions are suppressed or moved during dense collage frames.

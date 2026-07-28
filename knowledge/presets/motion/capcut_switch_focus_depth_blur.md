# CapCut Switch Focus Depth Blur

Use when a documentary or explainer scene needs to hand attention from one cutout
subject to another.

## Starting Values

- Foreground compound move: keyframe around `1s` to `3s`.
- Foreground scale: about `125%` to `135%` if crop remains safe.
- Outgoing subject blur: `0` to `50`.
- Incoming subject blur: `50` to `0`.
- Background scale: about `120%` to `125%`, with subtler position drift.
- Curves: apply Ease or Cubic Ease to scale, X, and Y.
- Optional texture: FPS Lag around `14`; Play Pendulum speed `2`, strength `3`,
  twist `0`, sharpen `0`.

## QC

- One subject is always readable.
- Cutout edges survive blur and scale.
- Background motion is subtler than foreground motion.
- Captions avoid the focused subject.

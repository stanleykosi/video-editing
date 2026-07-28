# FFmpeg Alphamerge Wipe Reveal Preset

## Use When

- A pre-rendered text, glow, lower-third, or graphic foreground needs an in-place
  reveal outside CapCut.

## Graph Pattern

```text
[foreground][mask]alphamerge[foreground_alpha];
[background][foreground_alpha]overlay=format=auto[final]
```

For generated wipe masks:

```text
[black][white]xfade=transition=wiperight:duration=...:offset=...[mask];
[foreground][mask]alphamerge[foreground_alpha];
[background][foreground_alpha]overlay=format=auto[final]
```

## Timing

- Short-form text wipe: 6-15 frames at 30 fps.
- Lower third/title wipe: 12-24 frames at 30 fps.
- Always add a readable hold after reveal.

## QC

- Mask preview polarity is correct: white reveals, black hides.
- Foreground and mask match resolution, fps, duration, and timebase.
- Foreground does not slide unless that is intentional.
- Transparent areas do not render as black.

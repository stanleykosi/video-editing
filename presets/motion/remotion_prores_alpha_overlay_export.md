# Remotion ProRes Alpha Overlay Export Preset

## Use When

- Rendering reusable Remotion text, lower-third, highlight, glow, or transition
  overlays for an editor or FFmpeg composite.
- The overlay needs transparent soft edges.

## Settings

- Composition background: transparent/no painted root background.
- Image format: PNG.
- Codec: ProRes.
- ProRes profile: 4444.
- Pixel format: `yuva444p10le`.
- Filename pattern: `{effect}_{resolution}_{fps}_{duration}_alpha.mov`.

## Command Pattern

```bash
npx remotion render OverlayComposition out/effect_1080x1920_30fps_alpha.mov \
  --image-format=png \
  --codec=prores \
  --prores-profile=4444 \
  --pixel-format=yuva444p10le
```

## QC

- Checkerboard visible before render.
- `ffprobe` confirms alpha-capable format.
- Empty overlay area is transparent, not black.
- Glow/text edges are inspected over bright and dark backgrounds.

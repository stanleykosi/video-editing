# Vox-Style Documentary Graphics In CapCut

Source: `transcripts/vox style documentary.txt`  
Processed: 2026-05-29

## Core Lesson

The tutorial teaches a CapCut workflow for building documentary explainer graphics
that feel like editorial motion design: warm paper texture, subtle grid structure,
serif typography, highlighted documents, animated maps, simple charts, cutout
collages, motion-synced SFX, and a low-FPS stop-motion texture.

The reusable lesson is not to copy another publisher's logo or identity. The
agent should extract the grammar: evidence-led 16:9 explainer scenes, warm analog
texture, restrained palette, clean focus hierarchy, sequential map/chart reveals,
and tidy compound-clip organization.

## Techniques Extracted

- Warm paper-grid background: scale a paper background to fill 16:9, warm it
  slightly, overlay a low-opacity grid, and add subtle paper-edge/hand-drawn
  texture.
- Typographic explainer intro collage: combine serif display text, small labels,
  circles, arrows, and logos/icons with staggered wipes/fades, then compound the
  stack and trim it to the actual animation duration.
- Compound-clip scene workflow: build each infographic section longer than needed,
  group it into a compound clip, retime internally, then move/fade the whole
  section as one object.
- Map trace route animation: remove a map background, draw a route or outline as a
  PNG, reveal the line with a feathered split mask, add markers/arrows, then
  keyframe pan/zoom/rotation to follow the geography.
- Animated bar chart wipe: build axes and bars from simple text/shape layers,
  animate bars with directional wipes, stagger bar timing, then compound and
  slide the chart in/out.
- Document highlight focus: use highlight bars with a darken/multiply-style blend
  so they appear behind text, then pan/zoom between highlighted lines.
- Word-focus screenshot sequence: stack screenshots that share one repeated word
  or phrase, mask a highlight strip over the target, shorten each screenshot over
  time, then zoom out to reveal the full context.
- Layered cutout end graphic: combine keyed/auto-removed cutouts, title text,
  background panels, slide/wipe animations, and a subtle compound zoom/rotation.
- Infographic SFX pass: add whooshes, highlight ticks, camera-shutter-like cues,
  and other small sounds only on actual motion/highlight changes.
- Documentary music bed: choose a restrained piano, classical, or editorial-style
  bed, trim to a musically natural section, and crossfade the exit.
- FPS lag/stop-motion texture: apply a low-FPS or shutter-like effect across the
  sequence to make smooth motion feel slightly handmade and editorial.

## Timing And Motion Rules

- Build intro elements at a safe length, such as 10 seconds, then trim the final
  compound once all entrances finish.
- Screen-wipe arrows and route lines should finish before the viewer needs the
  destination or conclusion.
- Map route arrow duration can start around 2 seconds; adjust between roughly
  1-4 seconds depending on geography and narration speed.
- Fade out outgoing map/chart/document sections instead of letting them vanish.
- Stagger chart bars and word-focus screenshots so the viewer can read the change
  order.
- Use cubic/eased curves on map pans, chart moves, and compound zooms.
- Stop-motion/FPS texture should be applied late and checked after all timing is
  locked.

## Sound Rules

- Use a small whoosh/pop when an important word, label, or cutout appears.
- Use highlight/tick/shutter cues on outlines, text highlights, and screenshot
  swaps.
- Do not add SFX to every small layer; the sound should clarify hierarchy.
- Lower SFX that compete with voiceover.
- Trim music to a musically clean phrase and crossfade exits rather than cutting
  abruptly.

## Caption And Color Rules

- If the explainer graphic already contains text, captions should be suppressed,
  repositioned, or simplified to avoid duplicate reading paths.
- Warm paper texture should not make text, map labels, charts, or source documents
  low contrast.
- Use a limited palette, often warm off-white, charcoal/gray, yellow, red, and
  muted accent colors.
- Any logo, publisher mark, map, screenshot, or photo asset must have rights or
  be replaced with an allowed equivalent.

## Implementation Notes

- ffmpeg: represent each graphic section as a layered composition with background
  image/video, grid alpha overlay, masks, text, shape overlays, route reveals,
  chart wipes, and audio cues. Use contact sheets to verify readability.
- Remotion: build reusable components such as PaperGridBackground, TypeIntro,
  RouteTraceMap, BarChartWipe, DocumentHighlight, WordFocusSequence,
  CutoutInfographicScene, and FpsLagTexture.
- CapCut: use compound clips, chroma key, auto cutout, masks, blend modes,
  animation presets, keyframes, variable-speed/ease curves, separate SFX tracks,
  and FPS Lag only after the graphic sequence is timed.
- Premiere/After Effects equivalent: use nested sequences/precomps, track mattes,
  masks, Essential Graphics/shape layers, linear wipe/trim-path equivalents,
  motion easing, posterize time, and separate SFX/music tracks.

## Common Mistakes

- Copying another brand's logo or exact identity instead of using the visual
  grammar ethically.
- Letting paper texture, grid, or FPS lag reduce map/chart/text readability.
- Building many layers without compounding or naming scenes.
- Leaving a route, chart, or highlight onscreen too briefly to understand.
- Adding SFX to every movement until the voiceover feels noisy.
- Applying low-FPS texture before timing is locked, then missing jitter or unreadable
  reveals.
- Using document/screenshot highlights that cover the exact words the viewer needs
  to inspect.

## QC Checklist

- The style is inspired by editorial documentary graphics without copying protected
  brand identity or unlicensed logos.
- Every graphic section supports a narration claim, map relation, statistic,
  document detail, or transition.
- Background paper/grid texture remains subordinate to foreground text and data.
- Map route, markers, labels, and destination are readable before the scene exits.
- Chart axes, labels, and bars are readable after animation and FPS lag.
- Highlight overlays sit behind text and do not hide source wording.
- Screenshot focus sequence reveals the repeated word/idea and then restores full
  context.
- Compound clips are named and still editable for internal retiming.
- SFX cues land on visible entrances, highlights, swaps, or route movement and stay
  below voiceover.
- Music is licensed/platform-safe or marked temp-only.
- Final low-FPS texture does not create distracting stutter or unreadable text.

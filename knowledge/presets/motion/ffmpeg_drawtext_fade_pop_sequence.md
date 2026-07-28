# FFmpeg Drawtext Fade Pop Sequence

Use this preset for simple generated titles, labels, pop words, and short
word-by-word overlays when Remotion would be heavier than needed.

## Pattern

`drawtext layer -> enable window -> alpha envelope or fontsize pop -> hold -> clear`

## Settings

- Font: use explicit `fontfile` where possible.
- Fade: around 0.3s in/out for calm titles; shorter for fast shorts.
- Pop: start around 70% size and settle at 100%; optional peak around 110%.
- Sequence: use labeled drawtext chains only while the graph stays debuggable.

## QC

- Text stays centered during font-size animation.
- Filter graph is logged or generated from structured data.
- Contact sheets show readable text and no face/proof/UI collisions.

## Related Cards

- `knowledge/techniques/typography/typography_ffmpeg_drawtext_timed_overlay_001.json`
- `knowledge/techniques/typography/typography_ffmpeg_fade_pop_envelope_001.json`
- `knowledge/techniques/captions/typography_ffmpeg_sequential_word_drawtext_001.json`


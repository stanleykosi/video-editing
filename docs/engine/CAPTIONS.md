# Captions

## Canonical Model

Caption tracks contain strict phrase cues and optional absolute rational word
timings. Cues carry language, speaker, style, typed overrides, suppression, and
top/center/bottom/custom position. Styles are project-owned and responsive;
unknown override fields are rejected. Collision regions are caller decisions,
not inferred editorial policy.

Multiple enabled language tracks require an explicit render selection. A render
may select root track IDs or language codes. Language selection propagates into
nested sequences; cue language inherits its track when left `und`.

## Rendering

The compiler validates reading speed, line count, measured width, title-safe
placement, fonts, and declared collision regions. Blocking layout findings stop
compilation. The selected fitted size is carried into the render node rather
than remaining diagnostic-only.

ASS is the baseline burn-in format. It preserves phrase punctuation, explicit
word gaps, word styles/highlights, speaker names, custom coordinates, and one
literal `\N` per hard line break. Range renders retain original caption times
and shift video PTS during libass evaluation, so a partial render has the same
karaoke state as the corresponding full-timeline frame.

Resolved font files are staged into the libass font directory and included by
content hash in caption cache keys. A font-file change therefore invalidates the
caption node without invalidating unrelated media analysis.

## Interchange

`CaptionService.import_file` accepts ASS, SSA, SRT, and WebVTT and returns native
tracks, styles, and structured loss records. `CaptionService.export` emits ASS,
SRT, or WebVTT and returns a `CaptionExportResult`; lossy features are reported
instead of silently discarded. WebVTT speaker labels use native voice spans.

ASS has no portable literal escape for braces or backslashes that precede ASS
special sequences. The engine emits a marked, reversible fullwidth escape for
those characters and restores them on its own re-import. The export result
reports this representation because non-engine ASS consumers render the
lookalike glyphs. SSA v4 output is deliberately rejected; callers should export
ASS v4+.

Designed kinetic typography remains the Remotion subsystem's responsibility.
Pillow is used only for measurement and diagnostics, never final text pixels.

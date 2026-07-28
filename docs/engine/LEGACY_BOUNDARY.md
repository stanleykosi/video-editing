# Legacy And Compatibility Boundary

## Production Authority

`src/video_engine/` is the only production editing engine. Canonical adapters
under `video_engine.adapters` are supported public import services, not archived
legacy implementations. They translate older EDL/interchange documents into the
same strict project and timeline used by every new caller.

## Compatibility Facades

`tools/video-use/compat/` owns the implementation behind historical command
shapes:

- `render.py` translates an existing-footage EDL and delegates render/QC to
  `VideoEngine`.
- `timeline_view.py` delegates to canonical inspection.
- `grade.py` translates historical color presets or requests canonical measured
  analysis; it cannot encode media.
- `caption_styles.py` prepares ASS input for the EDL facade.

The matching files in `tools/video-use/helpers/` are deliberately tiny forwarding
entry points. They preserve external skill links for one deprecation cycle while
new callers move to `video-engine` or `video_engine.api.VideoEngine`.

## Workflow Tools

The other files in `tools/video-use/helpers/` are active preparation and review
tools. They route knowledge, plan assets, transcribe speech, author workflow EDLs,
and review creative artifacts. They stay outside `src/video_engine` because they
make editorial or external-service decisions; the engine only executes structured
decisions.

The repository-root Python and Node manifests are the sole dependency authority.
`tools/video-use/` is not a second installable package.

## Frozen Evidence

Historical executable renderer source is not retained. Immutable decoded outputs,
checksums, probe metadata, contact sheets, and parity reports live in the
deterministic `testdata/engine/baseline.tar.gz` bundle; regression contracts
live in `tests/legacy/` and `tests/golden/`. Git history is the source archive.

The following files are prohibited from returning:

- `faceless_renderer.py`
- `render_vertical_podcast_clips.py`
- `render_variant_caption_styles.py`
- `sfx_renderer.py`

`tests/legacy/test_deprecated_renderer_removed.py` recursively enforces that rule.

## Change Policy

1. Add or change behavior in the canonical engine first.
2. Cover it with behavioral media evidence.
3. Keep a compatibility facade only when a real historical caller needs it.
4. Facades may translate inputs, but may not own FFmpeg/Remotion production
   execution.
5. Remove a forwarding path only after caller searches, documentation migration,
   and an anti-return regression pass.

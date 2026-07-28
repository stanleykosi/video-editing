# Compatibility Facades

This directory contains the implementations behind historical `video-use`
commands. They translate legacy inputs into canonical `video_engine` projects or
delegate to canonical services; they are not an alternative rendering engine.

Supported facades:

- `render.py` imports the historical existing-footage EDL and calls the canonical
  render and QC services.
- `timeline_view.py` delegates historical range/timeline inspection to the
  canonical inspection service.
- `grade.py` translates historical preset names or invokes canonical measured
  color analysis. It cannot render media.
- `caption_styles.py` exists only to prepare ASS data accepted by the EDL facade.

The files under `../helpers/` with matching names are stable forwarding entry
points for existing scripts and installed skills. New automation should use the
`video-engine` CLI or `video_engine.api.VideoEngine` directly.

Removed renderer implementations are not archived here. Their behavior is
frozen as immutable media and parity reports under
`test_projects/engine_baseline/` and guarded by `tests/legacy/`.

# Workflow Helpers

These scripts prepare editorial decisions and project evidence around the
canonical engine. They do not form a second rendering engine.

## Active Workflow Tools

- Knowledge and planning: `knowledge_router.py`, `knowledge_compiler.py`,
  `timeline_builder.py`, `stock_footage_planner.py`, `research_checker.py`
- Assets and provenance: `asset_manifest.py`, `find_assets.py`,
  `generate_asset.py`, `render_map.py`, `render_chart.py`, `freesound_oauth.py`
- Speech and captions: `transcribe*.py`, `pack_transcripts.py`,
  `voiceover_generator.py`, `caption_engine.py`
- Sound and review: `sound_design_engine.py`, `visual_qc.py`, `qc_check.py`
- Planning graphics: `motion_graphics_generator.py` is restricted to diagnostic,
  placeholder, or non-typographic plates. Final typography uses ASS/Remotion.

## Stable Forwarders

`render.py`, `timeline_view.py`, `grade.py`, and `caption_styles.py` retain old
command/import paths while forwarding to implementations in `../compat/`.
`video_engine.py` is a location-independent launcher for the canonical CLI.

New integrations should use `video-engine` or
`video_engine.api.VideoEngine`. Historical renderer source is intentionally not
kept executable; parity evidence lives under `test_projects/engine_baseline/`.

Dependencies are owned only by the repository-root `pyproject.toml` and
`uv.lock`. There is no nested helper environment or second installable package.

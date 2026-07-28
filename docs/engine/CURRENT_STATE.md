# Current Engine State

Last updated: 2026-07-28

## Summary

The repository now has one canonical `video_engine` package, public API, and
`video-engine` CLI. The following table records the entrypoints found at the
start of migration and their current disposition:

| Path | Input model | Primary implementation | Status |
| --- | --- | --- | --- |
| Existing footage | `sources` plus ordered floating-point `ranges` | canonical legacy-EDL adapter; `compat/render.py` owns the facade and `helpers/render.py` only forwards | Migrated |
| From scratch | beat/layer `edit_decision_list.json` | canonical faceless adapter plus FFmpeg/Remotion backends | Migrated; deprecated renderer removed and guarded by regression test |
| Vertical podcasts | script-specific ranges and constants | canonical project/timeline operations and podcast golden | Standalone renderer retired; editorial choices remain caller-owned project data |

There was no repository-owned test suite at the start of the migration. The
baseline command `uv run pytest -q` exited 5 with `no tests ran`. There was no
installable `src` package, console script, CI workflow, pre-commit configuration,
typed timeline, schema migration system, or engine public API.

## Frozen Valuable Existing Behavior

`render.py` provides per-segment extraction, 30 ms audio fades at cuts,
homogeneous concat, HLG/PQ detection and SDR conversion, crop/focus/fit controls,
ASS and SRT caption support, subtitle-last compositing, timed overlays and SFX,
loudness normalization, preview/draft/final profiles, and a visual-QC gate.

The faceless path provides asset-manifest lookup, still-image motion, looping
video, cover crops, simple crossfades, voice-over replacement, generated SFX,
rich caption/emphasis/diagram/progress overlays, and ASS/SRT fallback captions.
Some declared track/layer data is descriptive and is not executed by the legacy
renderer; parity tests must freeze executed behavior rather than documentation.

`caption_styles.py`, `grade.py`, `visual_qc.py`, `timeline_view.py`, and
`asset_manifest.py` contain reusable behavior but expose helper-specific data
contracts and command runners.

The old faceless, vertical-podcast, caption-variant, and standalone SFX render
implementations have now been removed. Their executed media behavior is covered
by immutable legacy baselines, canonical parity fixtures, podcast/caption
goldens, and sample-accurate multitrack SFX tests. `grade.py` remains only as a
non-rendering measured-analysis and typed-preset translation shim.

## Pre-Migration Architectural Problems

- Timeline authority is floating-point seconds with no frame/sample model.
- Existing-footage and faceless timelines are incompatible.
- Rendering, media probing, operations, cache policy, and process execution are
  coupled inside CLI scripts.
- Faceless final typography is rasterized with Pillow, contrary to the current
  ASS/Remotion production policy.
- Audio has no canonical tracks, buses, automation, sample clock, or technical
  QC. Existing loudness is globally fixed at -14 LUFS.
- Faceless cache invalidation ignores much of the render configuration.
- Remotion and HyperFrames are dependencies/documentation only; there is no
  component registry or structured bridge.
- Visual QC is coupled to the legacy range EDL and its approval hash does not
  bind the reviewed preview essence.
- `timeline_builder.py` and the podcast renderer contain editorial rules. Those
  rules may remain in workflow adapters but must not enter engine core.

## Baseline Environment

- FFmpeg/FFprobe: 6.1.1 (Ubuntu build)
- Python target: CPython 3.11
- Node observed: 25.0.0
- npm observed: 11.6.2
- Existing Python tests: none
- Existing JS install: lockfile present, `node_modules` absent
- Existing JS specifiers: nine `latest` entries (lock resolves Remotion 4.0.481,
  React 19.2.7, GSAP 3.15.0)

These problems describe the state captured by the immutable baseline, not the
current canonical engine. Ongoing status belongs in `PROGRESS.md`; shipped
contracts belong in `PUBLIC_API.md`.

## Current Graphics Runtime

The canonical renderer registry now executes five typed backends: FFmpeg,
Remotion, HyperFrames, Manim, and Blender. HyperFrames 0.7.77 and Manim 0.20.1
have real alpha/range render evidence. Blender has complete typed lowering,
registration, cache identity, confinement, and deterministic tests. An official
portable 4.5.12 LTS binary passed its published SHA-256 and version probe, but
did not reach render execution in this environment; no Blender render parity
claim is made. The default extended doctor reports Blender absent unless that
portable path is explicitly configured.

# Implementation Plan

## Milestone 0: Freeze Legacy Behavior

Status: complete.

- Generate synthetic AV, still, overlay, caption, vertical-crop, SFX, and
  HLG/PQ fixtures.
- Render both legacy pathways and record probe metadata, decoded hashes,
  loudness/peak measurements, contact sheets, tool versions, and failure cases.
- Add behavioral regression tests before changing production helpers.

## Milestone 1: Foundation And Canonical Model

Status: complete.

- Make the repository an installable `src` package with pinned dependencies,
  lint/type/test/coverage tooling, pre-commit, CI, structured logs, exceptions,
  configuration, process runner, temporary storage, doctor, and CLI.
- Implement strict rational time, frame/sample clocks, project/timeline/track/
  item/effect/keyframe/marker/delivery schemas and schema migrations.

## Milestone 2: Edit, Media, Render

Status: complete for media, edit, baseline render graph/backend, audio, and captions.

- Implement the content-addressed media registry and derivative generators.
- Implement transactional professional editing operations, audit, inverse,
  undo/redo, invariant checks, and JSON patches.
- Implement render nodes, compiler, registry, optimizer, scheduler, cache,
  partial/range execution, manifests, and typed FFmpeg backend.

## Milestone 3: Production Subsystems

Status: complete for the required baseline engine.

- Implement multitrack audio/buses and sample-accurate processing. Complete.
- Implement native captions, ASS/sidecar output, layout safety, and typography.
  Complete.
- Implement structured Remotion, HyperFrames, Manim, and Blender components and
  adapters. Complete: all four are registered render backends; HyperFrames and
  Manim have real range/alpha render evidence. Blender real-render verification
  remains blocked by the local Blender process failing to reach render execution.
- Implement visual transforms/tracking/reframing, color pipeline, nested
  sequences, long-form resumption, inspection, and technical QC.

## Milestone 4: Migration, Parity, Removal

Status: complete.

- Import existing EDL, faceless EDL, SRT, ASS, WebVTT and optional interchange.
- Update helper compatibility shims, skills, docs, and sample commands.
- Dual-render golden projects, classify parity differences, test performance and
  invalidation, then remove `faceless_renderer.py`. Complete.
- Add an anti-return test covering the file, imports, CLI references, and
  production documentation.

## Quality Gate

Each milestone remains runnable and has unit plus integration evidence. Failed
commands and incomplete requirements are recorded in `PROGRESS.md`; interfaces
without working implementations do not count as complete.

# Engine Architecture

## Principles

1. The canonical project and timeline are backend-neutral, strictly validated,
   versioned data. Rational frame and sample time are authoritative.
2. Editorial decisions enter through typed objects or JSON patches. Core never
   chooses subjects, hooks, emphasis words, retention effects, or creative cuts.
3. Timeline mutations are transactional, invariant-preserving, auditable, and
   undoable where an inverse is well-defined.
4. Rendering compiles a timeline into a validated DAG. Capability planning
   selects a backend per node, allowing one graph to mix Remotion, HyperFrames,
   Manim, or Blender source nodes with FFmpeg processing and delivery while
   retaining backend-specific cache identity and execution records.
5. Media identity derives from source SHA-256. A persistent stat-keyed identity
   store avoids rereading unchanged bytes while still rejecting in-place source
   mutation. Derived assets include source identity, tool capabilities, and
   complete normalized parameters in their keys.
6. Captions, graphics, audio, color, inspection, and QC are first-class tracks
   or subsystems rather than post-render script conventions.
7. Temporal playback is an item-level rational mapping. Visual automation is a
   typed property/time curve, and backend expressions are derived only during
   backend execution.

## Package Boundaries

```text
src/video_engine/
  api/          stable Python facade and client DTO re-exports
  core/         rational time, schemas, migrations, validation, audit
  operations/   transactional timeline commands and JSON patches
  media/        registry, probing, derivatives, relinking
  render/       DAG, compiler, scheduler, manifests, cache contracts
  render/backends/ typed FFmpeg/Remotion/HyperFrames/Manim/Blender backends
  audio/        public audio type re-exports and deterministic SFX synthesis
  captions/     cue import/export, ASS layout and responsive checks
  graphics/     component registry, preparation service and renderer bridges
  visual/       transforms, masks, compositing, reframing, tracking
  color/        interpretation, normalization, grade, output transform
  qc/           ingest/timeline/video/audio/delivery checks and reports
  inspection/   filmstrips, waveforms and timeline/range/cut views
  adapters/     legacy and interchange import/export with loss reports
  storage/      project IO, content cache and temporary workspaces
  cli/          one machine-readable command tree
```

Dependencies point inward toward `core`; the public API may orchestrate all
subsystems. Backends may not leak raw filter strings into canonical effects.
Extension metadata may retain opaque legacy syntax as migration evidence, but it
is never a compilation input. A future backend escape hatch would require its
own explicit trusted adapter and capability contract.

Canonical audio tracks, clips, buses, roles, effects, and loudness profiles are
schema types in `core/` and are re-exported by `video_engine.audio`. Their typed
processor lowering belongs to `render/`; encoded signal validation belongs to
`qc/`. This separation keeps one timeline authority while giving callers a
coherent stable audio import surface.

## Canonical Compilation Flow

```text
Project JSON
  -> schema migration and strict validation
  -> timeline invariant validation
  -> optional transactional patch application
  -> media resolution and source validation
  -> render compiler
  -> backend capability resolution
  -> optimized render DAG
  -> cached/parallel execution
  -> mux and delivery output
  -> technical QC and render manifest
```

Visual items compile as decode, exact source trim, frame conform, technical
colour normalization, fixed-canvas fit, then caller transforms/masks. Track
blend decisions live on composite layers. Track mattes are validated dependency
edges to one hashed asset, same-sequence item, or visual track; recursive and
cyclic references are resolved or rejected before scheduling. Adjustment tracks
apply typed grade or LUT nodes over an explicit render-relative range before
captions.

Tracking backends return source-time observations. A binding service maps them
through exact clip retime and the target frame grid, then emits normal timeline
patch operations plus mapping evidence. This keeps tracking backend-neutral,
undoable, and separate from subject selection or editorial judgment. Projection
is bound to probed source display geometry, sequence canvas and delivery fit;
missing observations use explicit error/hold/interpolate policy and target
boundaries are synthesized on the rational frame grid.

Long renders compile into exact frame/sample-bounded sections. Section roots are
independently content-addressed, concatenated through bounded fan-in nodes, and
recorded in project/revision-scoped durable attempt checkpoints. Corrupt state is
quarantined, concurrent attempt histories merge under a lock, and only cache keys
proven complete by the checkpoint may be reused during a cache-disabled resume.
The public partial-render API executes and persists an explicit node ancestor
closure. Immutable sequence snapshots let a nested clip resolve a historic
revision while current sequences evolve.

The color subsystem exposes one strict pipeline decision spanning input
interpretation, technical normalization, creative grade/LUT, working space, and
delivery output transform. These decisions become canonical effects and profile
settings; FFmpeg expressions remain backend-owned.
Measured correction samples an exact rational source range through FFmpeg
`signalstats`, normalizes against probed storage bit depth, and records source,
toolchain, policy, and measurement evidence in a canonical typed grade effect.
The content-addressed analysis cache is locked and quarantines invalid records;
analysis failure never manufactures neutral measurements.

Technical QC analyzes both the canonical project and final encoded essence. A
successful render manifest is authoritative for delivery profile, range and
checksum expectations; unavailable evidence produces an incomplete result,
never a pass. Inspection is read-only and emits exact rational/frame/sample
evidence without making editorial quality decisions.

Legacy and interchange adapters terminate at this same boundary. Each adapter
creates a normal strict `Project`, validates it, hashes the source and relevant
sidecars, resolves or records relinkable media, and returns a `MigrationReport`.
CMX and FCPXML syntax never becomes a second timeline authority. Unsupported
constructs remain namespaced extension data and a reported disposition.

Designed-graphics definitions carry one of `safe_area`, `edge_accent`, or
`full_frame` bounds policies. Remotion derives alpha bounds for every rendered
frame and stores their union and edge-touch counts in artifact metadata and the
render manifest. Encoded-output QC uses that evidence to distinguish intentional
full-bleed accents from blank or persistently cropped safe-area components.

## Stable Seams For Future Systems

External graphics use the same `GeneratorClip` authority as built-in Remotion
components. `GraphicsService` hashes the authored source and declared assets,
creates confined bindings, and returns a strict clip/reference bundle. The
compiler lowers it to a renderer-tagged `MotionGraphicNode`; backend planning
selects HyperFrames, Manim, or Blender without exposing command lines to the
caller. Each backend normalizes output to exact-frame ProRes 4444 alpha before
ordinary FFmpeg composition, caching, delivery, and QC.

Manim runs in an isolated exact toolchain because Manim 0.20.1 requires NumPy
2.1+ while the canonical media environment is pinned to NumPy 1.26.4. Blender
is executable-isolated. HyperFrames is an exact root Node dependency because
its producer API shares the existing browser graphics runtime.

The future Editorial Brain will produce canonical projects, operation requests,
or JSON patches. The future Editorial Critic will consume inspection artifacts,
render manifests, and QC reports. Neither system needs FFmpeg syntax or helper
implementation knowledge.

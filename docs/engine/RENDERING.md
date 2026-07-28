# Rendering

## Required Pipeline Properties

- Frame-accurate extraction against explicit source timebases.
- Explicit conform policy for mixed frame rates and variable-frame-rate media.
- Typed transforms/effects compiled to backend expressions.
- Subtitles and designed captions composited after visual overlays unless a
  caller explicitly places a graphic above captions.
- Boundary audio smoothing and sample-aligned cue delays.
- Output transforms, color tags, loudness policy, encode, fast-start, and mux
  controlled by a delivery profile.
- Draft, preview, range, and final requests share the same graph compiler; only
  profile parameters and requested range differ.

## Render DAG

Required node families are decode, trim, conform, scale, crop, transform, speed,
speed ramp, reverse, freeze, color conversion, grade, mask, composite, transition, caption,
motion graphic, audio process, audio mix, loudness, output transform, encode,
and mux.

Nodes are immutable and validated. Backends declare capabilities. Compilation
must fail with a structured unsupported-capability error rather than silently
dropping an effect. The optimizer may fuse compatible nodes, eliminate identity
work, and reuse cached nodes without changing timing semantics.

Implemented graph rules include unique IDs, strict input arity and artifact-family
contracts, missing-input and cycle rejection, named outputs, partial ancestor
closure, deterministic topology, and conservative identity pruning. Cache keys
exclude graph IDs and output paths while including semantic parameters, ordered
upstream keys, source and referenced-asset hashes, compiler fingerprint, backend
version, and FFmpeg fingerprint. Cache hits are SHA-256-validated and per-key
cross-process locks serialize calculation and atomic publication.

`execute_partial()` exposes ancestor-closure execution for cacheable targets.
Whole-output renders write fsynced, project/revision-scoped checkpoints. Resume
can use only node keys recorded complete by that checkpoint, including when
ordinary cache reads are disabled. Invalid checkpoint JSON is quarantined and
attempt histories survive concurrent completion.

Backend planning is per node. Structured `MotionGraphicNode` sources execute in
the Remotion backend, and their transparent ProRes 4444 outputs flow into the
same FFmpeg composite/effect/output graph as decoded media. Cache keys retain
component source/version, normalized strict props, logical asset IDs, media
type, staged extension, actual asset bytes, exact frame range, browser hash,
Node/Remotion versions, and the package-lock hash. Every Remotion result is
FFprobed for codec, alpha pixel format, dimensions, rational rate, frame count,
and duration before cache publication.

The trusted bridge hardcodes its entry point, confines job paths, rejects public
symlinks and undeclared assets, verifies source and asset hashes, bounds canvas,
frame, prop and asset resources, and uses a configured/cached Chrome
headless-shell. Inter is exact-pinned and bundled at the used weights. A
Remotion-specific semaphore prevents the general graph worker count from
launching unbounded browsers.

HyperFrames, Manim, and Blender use renderer-specific `MotionGraphicNode`
sources selected by the same backend registry. Their typed properties are the
canonical representation; raw CLI flags or renderer scripts are not effects.
HyperFrames invokes the exact `@hyperframes/producer` API behind a lint gate,
blocks remote assets, and uses the configured local headless browser. Manim
invokes one named scene in its isolated 0.20.1 executable environment. Blender
opens one content-addressed `.blend`, applies only typed scene/camera/engine/
frame settings, and renders a bounded RGBA frame sequence. All outputs are
FFprobed and conformed to exact dimensions, rational frame rate, frame count,
codec, and alpha requirements before entering the shared graph cache.

Browser setup and render calls use the bounded
`EngineConfig.remotion_browser_timeout_seconds` value (environment variable
`VIDEO_ENGINE_REMOTION_BROWSER_TIMEOUT`, default 120 seconds). The bridge passes
the same limit to composition selection and rendering so a cold or resource-
constrained Chromium launch is not constrained by Remotion's shorter default.

## FFmpeg Lowering

The backend executes argument arrays without a shell. Source video and audio are
decoded as separate semantic streams. Exact trim and timestamp reset happen in
filters, adapters may request boundary fades, and audio placement uses sample
counts (`adelay=...S`). Source audio is trimmed at its probed sample rate before
being conformed to the delivery sample clock.

Compiler verification caches source SHA-256 against a strong stat identity and
carries imported stream metadata on decode nodes. An unchanged source is neither
rehash-read nor re-probed while in-place mutation is still detected. Explicit
audio clip and automation boundaries that cannot land exactly on the delivery
sample grid fail before FFmpeg instead of being silently rounded.

Visual layers are independently trim/conform/effect/fit processed, then composed
bottom-to-top over an explicit canvas. Captions compile after that composite.
Lossless intermediates are alpha-capable 10-bit FFV1. Final colour/output
transform, format-appropriate colour tags, per-stream encode, fast-start, and mux
are separate nodes. Delivery loudness targets are optional and profile-specific;
preview uses one-pass and final uses measured two-pass normalization when set.

Source-backed items carry a canonical rational playback rate, reverse flag, and
optional exact hold/linear speed curve. Range compilation integrates that curve
to map the requested timeline interval to the exact source interval. Lowering is
`trim -> reverse -> speed/speed-ramp -> output-rate conform`, which preserves
high-frame-rate source detail for slow motion and defines asymmetric reverse
curves on the viewer-facing clock. Constant and variable temporal nodes enforce
an exact target frame/sample count. Linked audio follows the same map.

A freeze effect selects one item-local presentation frame on the owning
sequence's frame grid, independently of the delivery profile frame rate. The
compiler maps it through the same reverse/retime function to exactly one source
frame, then the backend extends that decoded frame to the clip's exact frame
count. Editing operations materialize that source-frame decision when trimming
or splitting and move it explicitly when slipping, so subsequent edits cannot
silently select a different picture. Full, section, and range graphs therefore
share the selected source identity; invalid duration, off-grid, automated, or
out-of-bounds freezes fail before execution.

Variable-speed audio uses a single stateful FFmpeg Rubber Band filter. Tempo
commands are scheduled from sample-aligned output knots mapped back to exact
source times, and the result is padded/trimmed to an exact output sample count.
Audio ramps therefore do not depend on the project video frame rate. The doctor
requires Rubber Band support; the FFmpeg backend rejects non-finite rates and
rates outside its declared 0.01 through 100 capability. The schema rejects every
source/timeline duration mismatch, including integrated ramp duration.

Position, scale, rotation, anchor, opacity, crop, and corner radius carry typed
rational automation points in the DAG. The FFmpeg backend derives time
expressions for hold, linear, ease-in/out, smooth ease, and tangent-aware Bezier
segments. Range nodes add the original item-local offset, so a range frame
matches the corresponding full-render frame. Fixed-canvas intermediates retain
alpha between sequential effects.

Blend mode and layer opacity are composite-layer properties. Chroma/luma keys,
animated normalized rectangle/ellipse masks, and selective inside/outside blur
are typed nodes with rational automation. Alpha/luma track mattes accept one
content-hashed asset, same-sequence item, or video/graphics track. Referenced
items compile recursively; disabled matte-only tracks composite enabled items
over transparent pixels so gaps remain transparent. Matte-track transitions use
the same canonical transition compiler and dense layers are staged through the
configured maximum input fan-in. Missing/nonvisual targets, normal or transition-
handle range gaps, invalid historical snapshots, self references, and dependency
cycles block compilation. The backend extracts 10-bit matte alpha/luma and
multiplies foreground alpha, preserving prior opacity and mask effects.
Referenced upstream nodes therefore participate in normal graph cache identity
and partial invalidation. Adjustment-track grades carry explicit render-relative
enable ranges.
Grade nodes carry typed exposure, white-balance, contrast, gamma, saturation,
highlight, and shadow values. Measured correction is resolved before graph
compilation, so cache identity contains source-range measurements and policy
rather than an opaque backend filter string.

Materialized tracking effects carry their source/canvas geometry. Reframe focus
is the fraction of available scaled crop overflow used by the FFmpeg scale node,
not a normalized source point. Binding and rendering therefore share one
projection model for cover/contain/stretch, focus and zoom. Target-start samples
are interpolated on the exact output frame grid and incompatible delivery canvas
dimensions block compilation.

Draft, preview, range, and final CLI requests share this compiler. Range
compilation intersects items, advances source ranges, rebases timeline placement
to zero, and changes only affected/downstream cache keys.

Caption nodes retain original timeline cue/word times and carry the render range
start as a rational evaluation offset. The FFmpeg backend shifts timestamps for
libass evaluation and restores zero-based output timestamps afterward. This
preserves word-highlight state between full and range renders. Resolved font
assets are hash-keyed and staged into a deterministic `fontsdir`.

## Baseline Comparison

Legacy parity uses decoded frame/audio essence, timebase-aware duration,
representative perceptual hashes, boundary audio windows, stream metadata, and
contact sheets. Audio windows gate both dominant frequency and RMS delta under a
caller-owned policy; frozen legacy level defects require an explicit documented
tolerance. Container SHA-256 is recorded but is not the sole golden signal
because mux metadata can vary between FFmpeg builds.

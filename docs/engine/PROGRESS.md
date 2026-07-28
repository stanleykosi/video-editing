# Engine Progress

Last updated: 2026-07-28

## Current Phase

Final release verification and repository-boundary cleanup across Phases 0-20.
Phases 11-17 are implemented and
verified: tracking/reframing, numerical colour transforms, bounded sectioned
long-form rendering, durable resumption, technical QC, and general inspection.
Existing-footage, faceless, CMX 3600, hardened FCPXML, and optional OTIO imports
are implemented. Canonical JSON, caption sidecar, CMX, FCPXML and optional OTIO
exports now use one typed loss-reporting service. The existing-footage helper is
now a thin canonical delegate, all production workflow docs use the public CLI,
the twelve-project golden matrix passes, and the deprecated faceless renderer
has been removed behind a production-tree anti-return regression.
The canonical schema is now version 1.2.0 and variable-speed retiming is
implemented end to end. Every declared tracking binding and canonical animated
matte is implemented with decoded render evidence and independent review fixes.
Measured legacy auto-grade migration, exact freeze lowering, horizontal/
vertical/square delivery evidence, section-local caption invalidation, and
toolchain-portable golden schema v3 are complete. The remaining compatibility
renderers have been retired behind a recursive live-tree guard. Package metadata
has been regenerated. The external-graphics expansion is in final verification:
HyperFrames and Manim are implemented with real alpha/range renders, while the
Blender adapter cannot receive real-render evidence because the official
portable process does not reach execution locally. A hosted GitHub Actions result remains external to this
uncommitted workspace.

## Completed Work

- Added strict registered HyperFrames, Manim, and Blender generator components,
  renderer-tagged DAG nodes, backend capability planning, confined asset
  staging, tool fingerprints, exact range conformance, output validation, and
  manifest metadata.
- Added `GraphicsService` and machine-readable `video-engine graphics prepare`
  commands for content-addressed HyperFrames HTML, Manim scene, and Blender
  project bundles. Future agents do not need renderer CLI knowledge.
- Exact-pinned `@hyperframes/producer==0.7.77`. Locked and installed Manim
  0.20.1 in an isolated uv project so its NumPy 2.4 runtime cannot alter the
  engine media environment's NumPy 1.26 contract.
- Extended GitHub Actions now executes real HyperFrames in the browser lane and
  isolated Manim, Manim `MathTex`, and distro Blender in a dedicated graphics
  lane with LaTeX/dvisvgm.

- Consolidated the formerly scattered root knowledge folders into the single
  `knowledge/` namespace, with clear workflow, playbook, research, technique,
  preset, style, and quality boundaries plus a canonical routing index.
- Preserved ignored local transcripts and curated source notes under stable
  `knowledge/research/` paths, with zero tracked files in either private layer.
- Moved bundled workflow documentation/assets under `tools/video-use/docs/` and
  the optional Manim skill under `tools/video-use/vendor/`, while retaining the
  installed `tools/video-use` compatibility boundary.
- Collapsed baseline evidence and the locally ignored test tree into three
  review-friendly files under `testdata/engine/`; CI materializes the exact test
  suite before collection, and the deterministic pack mode keeps it refreshable.
- Added a knowledge validator that checks required directories, retired root
  absence, technique category placement, and internal Markdown/JSON paths.
- Centralized the four supported historical command implementations under
  `tools/video-use/compat/`; the matching helper paths are forwarding entry
  points, not renderer implementations.
- Added an explicit legacy/compatibility/workflow boundary document and
  regression tests that constrain facade ownership and prevent deleted
  renderers from returning.
- Fixed the unanchored root `audio/` ignore rule that could exclude
  `src/video_engine/audio/` from a commit. A source-inventory regression now
  checks every canonical Python source file for Git visibility.
- Removed the duplicate `tools/video-use` Python manifest and lockfile. Root
  `pyproject.toml` and `uv.lock` are the sole Python dependency authority.
- Updated the `video-use` skill/install/readme references to treat Deepgram as
  the preferred hosted transcription path and the older Scribe commands as
  compatibility tools.
- Extended CI and pre-commit static gates to cover the compatibility facade
  implementations. Active workflow helpers remain a separately classified
  preparation/review surface with CLI smoke coverage.
- Read the root instructions and `tools/video-use/SKILL.md`.
- Inventoried repository topology, helper scripts, packaging, dependencies, and
  production documentation callers.
- Audited the existing-footage, faceless, and vertical-podcast render paths.
- Audited caption, graphics, sound, SFX, grade, visual-QC, and workflow-QC
  helpers.
- Established the target architecture, migration policy, and capability matrix.
- Added deterministic FFmpeg fixture generation for existing-footage, faceless,
  caption-only, overlay-only, SFX-only, vertical-crop, HLG, and PQ cases.
- Added black-box legacy regression tests without modifying either renderer.
- Recorded eight rendered baselines with full FFprobe JSON, container SHA-256,
  decoded `framemd5` hash, decoded PCM hash, loudness measurements, tool versions,
  and contact-sheet checksums in the deterministic
  `testdata/engine/baseline.tar.gz` bundle.
- Inspected every generated baseline contact sheet directly.
- Replaced workstation-only metadata with an installable `src/video_engine`
  package and `video-engine` console entry point.
- Added strict configuration, structured logging, typed errors, one command
  runner, managed temporary workspaces, atomic project IO, and environment doctor.
- Implemented rational timeline/frame time, drop-frame timecode, audio sample
  time, the complete strict canonical project/timeline/track/item schema, schema
  migrations, nested-sequence cycle checks, and cross-track invariant reports.
- Added public project create/load/save/validate/doctor APIs and JSON CLI commands
  for `init`, `doctor`, and `project validate`.
- Exact-pinned Python and Node dependencies, refreshed both lockfiles, separated
  dev/legacy/optional groups, and removed every JavaScript `latest` specifier.
- Added Ruff, Black, strict MyPy, Pytest, coverage, local pre-commit hooks, package
  build, and two-job GitHub Actions CI.
- Installed and validated Remotion 4.0.481. Added an exact `fast-uri==3.1.4`
  override to remove the one high-severity transitive npm advisory.
- Implemented a persistent content-addressed media registry using source SHA-256,
  atomic writes, deduplication, validation, hash-safe relinking, and derived asset
  records keyed by source, normalized parameters, FFmpeg fingerprint, and engine
  compiler version.
- Implemented strict FFprobe stream/format extraction, timebase and fractional
  frame-rate parsing, deep FFmpeg `vfrdet`, HDR/colour/rotation/channel metadata,
  and warnings for VFR, missing audio/video, and HDR sources.
- Implemented cached FFmpeg proxies, thumbnails, waveform PNG/JSON, and lossless
  conformed media with optional HDR-to-SDR normalization.
- Added public `VideoEngine.media()` plus JSON CLI commands for media import,
  inspect, proxy, thumbnails, and waveform.
- Implemented the complete transactional editing operation surface: append,
  insert, overwrite, replace, split, trim, ripple trim, roll, slip, slide, lift,
  extract, ripple delete, move, duplicate, toggles, links, groups, nest/unnest,
  transitions, effects, keyframes, markers, J/L cuts, audio crossfades, and
  audio extensions.
- Each operation now executes against a deep candidate project, validates schema
  and timeline invariants before commit, advances project/sequence revisions,
  returns structured audit data and an inverse patch, and participates in
  in-memory undo/redo.
- Added strict public JSON patches with optimistic revision checks and working
  `timeline inspect` and `timeline apply-patch` CLI commands.
- Implemented immutable strict render nodes for every required DAG family,
  deterministic graph hashes, unique/missing/cycle/arity validation, partial
  ancestor closure, stable topological order, unreachable pruning, and
  conservative identity elimination.
- Implemented backend registration and per-node capability planning,
  content-addressed render-node caching with artifact checksum validation, and a
  bounded dependency-aware parallel scheduler with cached/succeeded/failed/
  skipped execution records.
- Implemented strict effect-parameter lowering. Unknown parameters, unsupported
  effects, keyframes without a lowering, and disabled backend overrides fail
  explicitly instead of becoming raw or silently omitted FFmpeg filters.
- Implemented canonical compilation for clip/still/generator video, track
  compositing, embedded and explicit audio, captions-last burn-in, delivery
  transforms, encode/mux, frame-grid enforcement, sample-grid cue placement,
  range intersection/rebasing, source hash validation, and draft profile
  derivation.
- Implemented the typed FFmpeg backend: exact filter trims, 30 ms audio edge
  fades, frame/audio conform, cover/contain/stretch, focus/crop/transform,
  speed/reverse/freeze, HLG/PQ tone mapping, grade/LUT, masks, multi-input
  composition, transitions, ASS burn-in, audio processing/mixing, sample delay,
  configurable one/two-pass loudness, Rec.709 output tags, encoding, fast-start,
  and mux.
- Added atomic delivery publishing and success/failure render manifests plus
  working `render draft|preview|range|final` JSON CLI commands.
- Added recursive nested-sequence compilation, visual transition handle/window
  lowering, and exact-duration transition integration coverage.
- Added media-family and declared-output contracts to graph validation, including
  zero-input motion graphics and strict encoded-stream mux inputs.
- Made render cache keys independent of graph-local IDs and asset locations when
  content hashes are available. Added checksum-safe cache records, permanent
  cross-process `flock` locks, fsynced publication, and path-safe work directories.
- Changed lossless video intermediates to alpha-capable `yuva444p10le`; verified
  opacity compositing by pixel inspection and 10-bit delivery by FFprobe.
- Added source colour interpretation, source-to-working conversion, working-to-
  delivery conversion, HLG/PQ profile validation, and Rec.709/Rec.2020/HLG/PQ
  encoder tag maps.
- Added source-stream probing for incomplete legacy media records, absolute audio
  endpoint sample rounding, explicit output channel/layout enforcement, strict
  bus ancestry, disabled-subtree muting, and track/bus processor lowering.
- Expanded render failure manifests to compilation, capability, preflight,
  scheduling, and publication failures. Outputs now reject source/cache collisions.
- Implemented executable rational gain/pan automation, range/full PCM
  equivalence, exact sample-count audio crossfades, side-chain ducking, strict
  bus ancestry, profile channel layouts, and boundary-only pop prevention.
- Implemented native strict caption styles, typed cue overrides, word timing,
  speaker/language metadata, custom positioning, collision regions, and
  multilingual/nested render selection.
- Added ASS/SRT/WebVTT import and ASS/SRT/WebVTT export with structured loss
  reports, parser round trips, speaker-preserving WebVTT voice spans, reversible
  ASS reserved-character handling, and explicit SSA v4 export rejection.
- Made caption layout a blocking render preflight with font fallback resolution,
  measured responsive fitting, title-safe/collision checks, reading-speed
  warnings, and the fitted size carried into actual ASS rendering.
- Preserved full-timeline caption/karaoke state in range renders through rational
  PTS evaluation offsets. Resolved font files are staged for libass and hashed as
  render cache inputs.
- Implemented a version-preserving registry of 21 strict designed-graphics
  components, structured generator props/assets, exact component source
  digests, and canonical range-to-frame lowering.
- Implemented per-node backend planning and mixed Remotion/FFmpeg scheduling;
  records, manifests and cache keys retain each node's actual backend.
- Added a hardened trusted Remotion runner with confined paths, symlink/hash
  validation, bounded resources, exact browser/tool fingerprints, bundled Inter
  weights, and a strict TypeScript no-emit gate.
- Added Remotion-specific concurrency limiting and FFprobe output-contract
  validation for ProRes, alpha, dimensions, rational rate, frame count and
  duration before cache publication.
- Fixed graphics cache type confusion, duplicate asset-alias staging, component
  version eviction, inconsistent frame durations, and small-canvas text
  clipping. Added optional Blender/Manim backend contracts.
- Decode cache construction now verifies source bytes against declared SHA-256.
  Relative LUTs resolve from project root, and FFmpeg fingerprints include its
  full build/filter/encoder capabilities.
- Added a strict dimensionless `RationalRate` and canonical per-item `Retime`.
  Source duration invariants, partial-range mapping, reverse mapping, linked
  audio retiming, and retime-aware transactional trims preserve exact rational
  timing. Temporal effect dictionaries are rejected in favor of this field.
- Corrected visual ordering so source normalization and canvas fitting precede
  caller transforms. Fixed-canvas scale, rotation, position, anchor, opacity,
  and crop preserve alpha and cannot accidentally resize the composite canvas.
- Added structured visual automation points to render nodes. Position, scale,
  rotation, anchor, opacity, crop, and corner radius lower rational keyframes,
  range offsets, hold/linear/ease/Bezier interpolation, and typed bounds into
  backend expressions without storing FFmpeg strings in canonical objects.
- Added layer-native normal/multiply/screen/overlay/darken/lighten/difference
  blend modes and time-bounded adjustment-track grade/LUT compilation.
- Added typed chroma and luma keys, alpha/luma track mattes, rounded masks, and
  content-hashed two-input matte DAGs with strict graph arity and artifact
  validation.
- Fixed non-normal blend alpha, end-exclusive composite/adjustment ranges, and
  executable hold-keyframed blend-mode automation.
- Added source-time-aware tracking through in-points, rational speed and reverse,
  plus executable contain/center/split-screen fallbacks.
- Verified Rec.709/Rec.2020 to HLG/PQ output conversion with 10-bit pixels and
  correct BT.2020 transfer/primaries tags while preserving HDR-to-SDR goldens.
- Added exact frame/sample-bounded render sections, chapter resolution, bounded
  concat/composite/mix fan-in, shared decodes, and section-local invalidation.
- Added durable fsynced render checkpoints with deterministic identity, attempt
  history, and interrupted/failed/succeeded recovery.
- Added immutable sequence snapshots, historic nested revision resolution, typed
  nested settings overrides, and nested audio routing/gain/pan/mute.
- Added strict ingest/timeline/video/audio/delivery QC with full decode scans,
  signal and metadata analysis, checksums, contact sheets, and atomic JSON plus
  Markdown reports. Missing evidence is incomplete, never passed.
- Added canonical `inspect timeline|range|cut|audio|captions` services and CLI
  with bounded track pages, exact filmstrips, transition/source mappings,
  per-channel peaks, measured silence, caption layout, and hashed artifacts.
- Added strict migration results with source/sidecar SHA-256, stable project
  identity, resolved/offline asset inventories, explicit disposition/severity,
  preserved extension metadata, and post-import canonical validation.
- Migrated existing-footage EDLs into exact 24 fps/48 kHz canonical projects,
  including ordered extraction, source-space crops, cover/contain/stretch,
  nested focus aliases, zero-focus correction, typed grades, independent
  overlays/SFX, ASS/SRT/WebVTT captions, 30 ms cut fades, legacy loudness
  profiles, optional-sidecar behavior, and derived legacy resolution rules.
- Migrated faceless projects into absolute beat ranges, explicit gaps, source
  clips/stills/placeholders, looped conform, native voice-over, deterministic
  sample-accurate SFX stems, master limiting, transitions, typed motion,
  generic Remotion progress/diagram/emphasis/caption components, native
  suppressed caption data, sidecar hashes, and loss reports.
- Fixed render graph optimization so animated transforms cannot be removed as
  static identities and composite/audio input descriptors follow replacements.
- Added per-component graphics bounds policies and frame-by-frame alpha bounds
  telemetry to Remotion artifacts/manifests; QC now blocks blank graphics and
  sustained safe-area edge contact instead of permanently skipping the check.
- Corrected drop-frame parsing/formatting at minute boundaries for 29.97/59.94,
  including illegal label and explicit separator-mode rejection.
- Added native CMX 3600 import with explicit NDF rates, DF defaults, record and
  source timecode rebasing, online/offline reels, black gaps, AV tracks,
  constant retimes, dissolves, comments/M2 preservation, and JSON CLI support.
- Exact-pinned `defusedxml==0.7.1` and added hardened FCPXML file/bundle import
  for formats, assets, lanes, nested media sequences, gaps, captions, markers,
  transforms, opacity, crops, endpoint retimes, dissolves, relinking, and
  unsupported XML preservation. Entity/DTD input is rejected.
- Added the optional exact-pinned OpenTimelineIO bridge behind the interchange
  dependency group with typed missing-dependency behavior and loss reporting.
- Added one typed interchange exporter for canonical JSON, SRT, ASS, WebVTT,
  CMX 3600, FCPXML, and optional OTIO, with atomic output, exact rational
  timecodes, nested-resource graphs, and explicit lossy dispositions.
- Added decoded media parity reports with exact metadata/frame counts,
  perceptual frame hashes, FFT audio-frequency/RMS samples, JSON/Markdown
  evidence, and immutable baseline-manifest enforcement.
- Added hash-bound QC approval artifacts covering project identity/revision,
  sequence, preview output, QC report/status, contact sheet, reviewer and time.
  Final renders reject missing, stale, or tampered evidence and retain approval
  data in the render manifest.
- Replaced the legacy existing-footage renderer implementation with a thin
  compatibility CLI that imports through the canonical adapter, renders through
  the canonical DAG/backends, runs canonical QC, and cannot bypass final
  approval. Added a location-independent canonical CLI launcher.
- Migrated README, skill, install, and sub-agent production instructions away
  from the deprecated faceless executable and onto `video-engine migrate`,
  `render`, and `qc`.
- Hardened derived-media caching with checksum/size evidence, per-key locks,
  corruption rebuilds, atomic publication, and merge-safe registry updates.
- Added a persistent source identity store so unchanged source bytes are not
  repeatedly hashed or probed; stat changes force fresh SHA-256 validation.
- Scoped durable render checkpoints to project/revision, quarantined corruption,
  merged concurrent histories, and exposed typed partial DAG execution.
- Proved cache-disabled recovery against the real FFmpeg backend; the recovered
  output is byte-identical to an uncached clean render.
- Added all twelve required canonical golden projects with decoded frame hashes,
  exact samples, spectral audio expectations, QC findings, chapter rendering,
  HDR/mixed-rate metadata, and Remotion bounds evidence.
- Removed `tools/video-use/helpers/faceless_renderer.py` after parity and caller
  audits passed; added a regression that rejects the file, symbol, or production
  documentation reference.
- Added a public strict color subsystem spanning interpretation, normalization,
  creative grade/LUT, working space, and delivery output transform.
- Replaced the legacy fixed/duplicated auto-grade path with exact-range FFmpeg
  measurements, storage-bit-depth normalization, a strict caller-visible policy,
  typed gamma lowering, locked content-addressed caching, corrupt-record
  quarantine, and source/tool/policy evidence embedded in the canonical effect.
  Existing-footage `auto` migration now measures each clip source range, and the
  compatibility helper delegates to the same service.
- Hardened measured-color analysis to `signalstats-v3`: it snapshots verified
  source bytes before FFprobe/FFmpeg access, fingerprints both tools, enforces a
  strict maximum of 256 requested/decoded samples, preserves exact rational
  range identity, and embeds the complete policy in typed effect evidence.
- Implemented exact freeze compilation as one retime/reverse-aware source-frame
  decision with full, section, and range parity. Invalid duration, frame grid,
  target bounds, automation, and transition-handle assumptions fail explicitly.
- Added decoded delivery evidence for horizontal stretch, vertical cover, and
  square contain profiles, including exact dimensions, 24 fps, square pixels,
  crop pixels, and letterbox pixels.
- Strengthened section-cache evidence so a middle-caption edit invalidates only
  its video section through public partial execution; first/third video roots,
  every audio root, and persisted source identity remain reusable.
- Upgraded all twelve canonical projects to golden schema v3 with complete
  decoded-frame dHash sequences, toolchain-conditioned exact digests,
  cross-toolchain perceptual/signal tolerances, exact pre-encode sample counts,
  temporal audio windows, QC/output binding, and contact-sheet checksums.
- Retired the unreferenced standalone vertical-podcast, caption-variant, and SFX
  renderers after canonical podcast/caption/SFX evidence passed. Converted
  `grade.py` into a non-rendering typed analysis/translation utility and expanded
  the anti-return regression across recursive live source/operator surfaces.
- Added transactional caption-collision-region operations and tracking binding
  materialization for crop/reframe, subject-centering position, graphic
  attachment, animated rectangle/ellipse mask, selective inside/outside blur,
  and caption exclusion. Applications return strict revision-checked timeline
  patches, inverse-compatible editor operations, and per-observation mapping
  evidence.
- Tracking observations map through exact constant, reverse, and hold/linear
  ramp retimes before snapping to the effective sequence frame grid. Ambiguous
  subjects, geometry collisions on one frame, mismatched media/rates,
  nonvisual targets, and missing bounding boxes fail explicitly.
- Tracking geometry is bound to probed display dimensions, sequence canvas,
  delivery fit, and the source clip's static reframe. Crop focus uses the
  backend's crop-overflow coordinate system, target-start samples are
  synthesized on the exact frame grid, confidence gaps have explicit
  error/hold/interpolate policy, and tracked effects/collision regions reject
  incompatible render canvases. Effect/keyframe patch operations honor track
  and item locks.
- Track mattes now accept exactly one content-hashed path, same-sequence item,
  or video/graphics-track reference. Validation rejects missing, ambiguous,
  disabled/nonvisual item targets, uncovered ranges, self references, and
  dependency cycles. Disabled matte-only tracks compile recursively over a
  transparent canvas, preserve gaps and visual transitions, use bounded
  composite fan-in, and participate in upstream cache keys. Item coverage
  includes transition handles and historical sequence snapshots.
- FFmpeg matte lowering multiplies existing foreground alpha by alpha/luma
  matte values at 10-bit precision instead of replacing it. Decoded renders
  verify prior opacity, transparent track gaps, materialized moving masks,
  materialized selective blur, centered crop, and full/range parity. Asset-mask
  and full-frame-blur geometry automation is rejected rather than ignored.

## Tests Run

- Real Manim backend integration: 1 passed in 9.45 s; exact 24-frame 320x180,
  24 fps ProRes alpha output.
- Real HyperFrames producer/browser integration: 1 passed in 54.47 s; linted
  exact 24-frame 320x180, 24 fps ProRes alpha output.
- External-graphics focused unit suite: strict registry/bindings, public
  preparation service, CLI JSON bundle, backend selection, Blender fractional
  frame-rate lowering, and content-addressed asset handling.
- Consolidated focused gate: 63 passed, 3 opt-in integrations skipped, 5
  deselected in 14.65 s. Ruff passed, strict MyPy passed across 89 source files,
  `uv lock --check` passed, and the deterministic test archive was repacked.
- Local no-isolation sdist/wheel build passed and includes the HyperFrames
  runner package data. Standard doctor now passes 15 checks with only optional
  Blender warning when the isolated Manim path is configured.
- Real Manim geometry/alpha and `MathTex`/LaTeX integrations both pass: 2 tests
  in 35.61 s with Manim 0.20.1, pdfTeX 1.40.25, and dvisvgm 3.2.1.

- `uv run pytest -q`: exit 5, no tests collected. The command created the root
  environment and installed the lockfile environment before collection.
- Independent system collection check: exit 5, no tests collected.
- Python AST parse audit: all 30 helper scripts parsed.
- Helper `--help` audit: 25 of 27 passed in the initially empty environment;
  `timeline_view.py` and `transcribe_local.py` lacked optional imports there.
- `uv lock --check`: passed.
- `python -m pytest -q tests/legacy/test_legacy_renderers.py`: 9 passed.
- `scripts/generate_engine_baselines.py`: passed; eight outputs and eight contact
  sheets recorded with FFmpeg/FFprobe 6.1.1.
- `pytest tests/unit tests/legacy`: 28 passed.
- Coverage: 80.54% branch-aware total; configured gate is 80%.
- `ruff check src tests scripts`: passed.
- `black --check src tests scripts`: passed.
- `mypy src/video_engine`: passed, 19 source files.
- Isolated sdist/wheel build: passed.
- `video-engine doctor --json`: healthy; 10 required/available checks passed,
  four optional-tool warnings, zero failures.
- `npm run remotion:version`: all Remotion packages consistently 4.0.481.
- `npm install --package-lock-only`: zero vulnerabilities after override.
- `pytest tests/integration/test_media_service.py`: 4 passed, including real
  proxy/thumbnail/waveform/conform generation and cache reuse.
- MyPy: passed across 24 engine source files after media subsystem addition.
- `pytest tests/unit/test_foundation.py tests/unit/test_operations.py`: 15 passed,
  including property-based append/invariant coverage and CLI patch persistence.
- Ruff, Black, and strict MyPy: passed across 27 engine source files after the
  transactional operation layer.
- Render graph/compiler/backend focused suite: 13 passed, including real FFmpeg
  preview/range renders, CLI execution, parallel branches, corruption detection,
  and second-run cache reuse.
- Canonical render direct inspection: 36 frames, 1.50 s, 320x180, 24/1 fps,
  square pixels, yuv420p Rec.709, AAC stereo at 48 kHz. Contact sheet was viewed;
  responsive ASS sizing fixed an initially clipped small-frame caption.
- Canonical render audio inspection: -21.8 LUFS integrated and -20.7 dBFS true
  peak without an active delivery loudness profile, matching the unnormalised
  synthetic source policy.
- Strict MyPy: passed across 48 engine source files after render implementation.
- Render correctness unit suite: 26 passed after graph contracts, cache locks,
  audio-bus validation, strict profiles, and automation rejection.
- New FFmpeg integration gates passed individually: real alpha composite, 10-bit
  Rec.709 delivery metadata, 44.1 kHz trim with missing stored stream metadata,
  source/output collision protection, and pre-compilation failure manifests.
- Caption unit/compiler suite: 23 passed, covering strict timing, ASS escaping,
  120 fps centisecond boundaries, SRT/VTT round trips, import/export losses,
  layout/collision behavior, font cache invalidation, explicit language
  selection, and nested propagation.
- `pytest tests/unit tests/legacy -q`: 73 passed in 37.47 s.
- `pytest tests/integration -q`: 18 passed in 94.35 s, including native styled
  caption burn-in and decoded-frame full/range parity.
- Ruff and strict MyPy passed across 51 engine source files. Black individually
  verified all files changed by the pinned formatter; its multi-file process
  leaves an open executor session in this local PTY after formatting completes.
- Graphics/compiler/scheduler focused suite: 33 passed after version, alias,
  duration, cache-semantic, source-hash and project-relative LUT fixes.
- `npm run graphics:typecheck` and `npm run remotion:bundle`: passed with exact
  TypeScript 5.9.3, Remotion 4.0.481 and bundled Inter 5.3.0.
- Current real Remotion integration outside the restricted browser sandbox:
  2 passed in 46.98 s. FFprobe verified exact ProRes 4444 alpha/range output;
  decoded-frame inspection confirmed complete small-canvas subtitle text and
  safe edges. Split-screen duplicate aliases rendered and second-run cache hit.
- `pytest tests/unit tests/legacy -q`: 78 passed in 28.85 s before the final
  graphics/source-cache additions; the focused additions pass above.
- `npm audit --audit-level=high`: zero vulnerabilities. Ruff and strict MyPy
  passed across 49 current engine source files.
- Rational retime/compiler/operation focused suite: 57 passed. Real FFmpeg
  forward/reverse full-versus-range frame comparison passed, with exact 48,000
  and 12,000 sample master durations.
- Current unit suite: 86 passed in 14.47 s. Ruff and strict MyPy pass across all
  49 current engine source files.
- Real FFmpeg visual gates passed for fixed-canvas scale/position transparency,
  rational position/opacity animation, screen blending, time-bounded adjustment
  grading, chroma keying, luma track mattes, and rounded alpha masks.
- Long-form performance gate: 2,000 items compiled in 6.53 seconds with three
  bounded sections, one shared decode, maximum fan-in 32, and bounded memory.
- Current unit suite: 117 passed in 19.22 seconds. Ruff and strict MyPy pass
  across all 68 engine source files.
- Technical QC integrations: 3 passed in 17.88 seconds, covering a clean
  manifest-bound render, truncated delivery failure, evidence, and JSON CLI.
- Inspection integrations: 2 passed in 13.29 seconds. All five service and CLI
  modes produced real hashed evidence; range/cut frame and 48 kHz stereo sample
  assertions passed.
- Adapter integration suite: 4 passed in 6.39 seconds. Existing/faceless tracks,
  focus/crop/grade aliases, caption migration, deterministic legacy SFX hash,
  and machine-readable project/report persistence passed.
- Combined QC unit/integration suite: 8 passed in 75.40 seconds, including the
  regression that a durationless PNG is valid when used as a still.
- Interchange unit suite: 7 passed in 5.00 seconds. CMX NDF/DF, illegal labels,
  source/record rebasing, offline relinking, FCPXML bundle/security/nesting,
  effects/captions/markers and JSON CLI behavior passed.
- Interchange import/export unit suite: 11 passed in 2.99 seconds. Canonical
  JSON and WebVTT export, CMX source/record timecode round trip, FCPXML nested
  media-resource/audio/caption round trip, and JSON export CLI passed.
- Drop-frame time suite: 22 passed. Graphics/render/QC focused suite: 25 passed.
- Faceless canonical preview rerender before bounds telemetry: succeeded at
  exactly 2.000 s, 160x284, 24 fps, 48 frames, H.264/AAC, Rec.709, fast-start;
  SHA-256 `833e5a07931e7e95303eec486741d89bb40507338903f3fb76923f89d9e03031`.
  Full QC passed every available check; ingest image-duration failure is fixed.
- Immutable baseline validator: eight legacy outputs, ten inputs, and eight
  contact sheets passed SHA-256 validation without regenerating evidence.
- Canonical existing-footage parity suite: 8 passed, 1 browser-dependent test
  deselected in 52.28 s. Base, captions, overlays, SFX, combined, vertical crop,
  and HDR-to-SDR cases met their exact metadata and decoded frame/audio policy.
- Canonical faceless parity on real Remotion/Chromium: 1 passed in 169.32 s.
  The 48-frame canonical improvement retained expected audio content, matched
  the frozen hash, and passed frame-by-frame graphics-bounds QC.
- Post-telemetry existing and faceless contact sheets were viewed directly;
  current JSON/Markdown QC and parity evidence is stored under
  the archived `engine_baseline/parity/` evidence directory.
- Compatibility and immutable legacy regression gate: 8 passed in 30.40 s,
  including outside-repository launcher use and final-approval bypass rejection.
- Current Ruff gate passed across `src`, `tests`, and `scripts`; strict MyPy
  passed across 79 engine source files.
- Canonical FFmpeg golden lane: 9 passed, 2 expected browser skips in 172.07 s.
- Product-ad and motion-graphics browser goldens: 2 passed in 193.50 s.
- Golden expectation validator: 12 projects, zero failures.
- Render checkpoint suite: 8 passed; real FFmpeg fail-once recovery: 1 passed in
  34.92 s.
- Source identity/decode regression lane: 3 passed in 34.30 s. Derived-media
  corruption/concurrency lane: 2 passed in 11.24 s.
- Removal, archived behavior and non-browser parity lane: 13 passed, 1 expected
  browser skip in 79.78 s.
- Strict MyPy passed across 84 source files after the public color subsystem.
- Added exact rational variable-speed curves with hold/linear interpolation,
  authored-curve context preserved through trim/split/extension, reverse-aware
  source mapping, and schema migration to 1.2.0.
- Temporal compilation now orders trim, reverse, retime, then delivery-rate
  conform so high-frame-rate slow motion retains source frames. Constant and
  variable temporal nodes carry exact target duration, frame rate, and sample rate.
- Variable-speed audio uses a continuous Rubber Band filter instance controlled
  from sample-clock knots, then bounds output with an exact `end_sample`; it no
  longer restarts `atempo` once per video frame. FFmpeg capability checks now
  require the `rubberband` filter and reject rates outside 0.01 through 100.
- Retiming focused verification: 74 unit tests passed. Eight real FFmpeg cases
  passed for forward/reverse ramps, non-frame-aligned 100 ms audio, 60-to-30 fps
  slow motion, exact frame/sample bounds, and 2x, 3/2, 1001/1000, and ramped
  visual transitions/audio crossfades.
- Post-review operation/visual/compiler/schema focused suite: 92 passed. Ruff
  and strict MyPy pass for the changed source tree (83 typed source files).
- Real FFmpeg visual evidence now runs through `TrackingResult -> binding ->
  patch -> editor -> render`: materialized moving mask/selective blur, centered
  tracked crop with range output, and referenced matte alpha/gap/range parity
  all passed (`3 passed in 67.55s`). The path-based luma/rounded-mask regression
  remains green.
- Measured color verification: 46 focused color/compiler unit tests passed;
  Ruff passed for the changed color/helper/test surface; strict MyPy passed over
  83 engine source files; and three real integration cases passed in 13.33 s,
  covering 8/10-bit normalization, rational cache reuse, corrupt-cache recovery,
  out-of-bounds rejection, per-range legacy migration, and decoded typed-gamma
  output.
- Freeze compiler unit lane: 5 passed. Exact real FFmpeg full/section/range
  freeze evidence: 1 passed in 15.65 seconds.
- Horizontal/vertical/square real-delivery lane: 3 passed in 9.24 seconds.
- Caption section-cache locality real-render lane: 1 passed in 7.76 seconds.
- Golden-v2 validator: 12 projects, zero failures. Non-browser canonical lane:
  9 passed, 2 expected browser skips in 180.93 seconds. Real Chromium lane:
  2 passed, 9 deselected in 163.18 seconds. These are retained as the final v2
  measurements; v3 adds portable evidence without weakening semantic checks.
- Compatibility removal and typed-grade focused gate: 6 passed in 4.28 seconds;
  Ruff passed and strict MyPy remains green across 83 source files.
- Independent freeze/golden/cache review found six concrete evidence or edit-
  stability gaps. Sequence-grid freeze selection, edit-stable source-frame
  materialization, real normal/reverse/constant/ramped frame identity, visual
  fit pixels, no-rehash cache locality, and toolchain-portable golden evidence
  are now implemented and covered.
- Golden-v3 expectation generation completed for all ten rendered scenarios,
  including the two real Remotion/Chromium projects; the 12-project validator
  passes. Its first full test run exposed a removed redundant sampled-frame
  threshold key after all-frame comparison had passed. The assertion now uses
  the manifest's single per-frame threshold, validation covers both tolerance
  fields, and a representative rerender passes.
- Package sdist/wheel build passes without setuptools deprecation warnings;
  generated metadata no longer names the retired renderer. Environment doctor
  passes all 11 required checks with only four optional-tool warnings. Python
  and Node lock checks, graphics TypeScript, and Remotion bundle gates pass.
- Corrected complete golden-v3 lane: 11 passed in 285.90 seconds, including the
  manifest declaration, all eight FFmpeg-only scenarios, and both real
  Remotion/Chromium scenarios.
- Superseded pre-audit consolidated Python/coverage gate: 300 passed, five expected skips,
  80.52% branch-aware coverage in 905.91 seconds. Ruff and strict MyPy pass;
  all 121 Python files pass the pinned Black check in bounded single-file mode.
- Online npm audit found one high-severity transitive PostCSS advisory. An exact
  compatible `postcss==8.5.23` override now resolves through Remotion's CSS
  loader; the refreshed lock reports zero vulnerabilities and Node typecheck
  plus bundle remain green. CI now blocks on `npm audit --audit-level=high`.
- Corrected CI so coverage runs against the complete non-browser suite and both
  legacy and interchange extras are installed. Optional OTIO now has a positive
  import/export execution test.
- Added stable public DTO re-exports, complete operation/audio exports,
  machine-readable CLI usage errors, and a canonical inspection delegate for
  the retired standalone timeline viewer.
- Added real draft delivery, all six visual transition variants, all required
  typed audio processors, and hostile ingest/output QC fixtures.
- Expanded `video-engine doctor` to check the exact FFmpeg filter contract for
  captions, HDR, compositing, transitions, loudness, sidechain, EQ, compression,
  limiting, gating, de-essing, denoising, channel mapping, and resampling.
- Legacy parity now gates RMS level and frequency. Frozen existing-footage
  outputs use an explicit 18 dB migration window for their known normalization
  defect; the replacement faceless path is held to 3 dB.
- Current transition matrix: 6 passed in 22.42 seconds. Existing-footage parity:
  7 passed in 31.03 seconds. Current browser lane: 5 passed in 153.26 seconds,
  including both bridge tests, faceless parity, product ad, and motion graphics.
- Final consolidated Python gate: 320 passed, six expected optional/browser
  skips, and 81.37% branch-aware coverage in 483.53 seconds.
- Final release gates pass: Ruff; strict MyPy over 84 source files; 211-package
  lock resolution; wheel and sdist build; TypeScript; Remotion bundle; zero npm
  vulnerabilities; eight immutable baselines; twelve golden declarations;
  doctor with 11 required passes and four optional warnings; clean diff
  whitespace; and retired-renderer/latest-dependency scans.
- The exact optional `opentimelineio==0.18.1` overlay executes its real export/
  import round trip without changing the repository environments: 1 passed in
  6.85 seconds.
- Cleanup boundary gate: 14 passed in 53.24 seconds across compatibility
  entrypoints, canonical color delegation, source inventory, and anti-return
  tests.
- All 22 active workflow helper commands passed their root-environment `--help`
  smoke check.
- Post-cleanup Ruff passed for `src`, `tests`, `scripts`, and
  `tools/video-use/compat`; strict MyPy passed all 84 engine source files.
- Final scoped cleanup verification: four source-inventory, facade-boundary,
  and deprecated-renderer guards passed in 1.76 seconds; all five compatibility
  Python files passed per-file Black checks; `git diff --check` passed.
- The long-form performance test passes standalone in 11.10 seconds. Under the
  unnecessarily broad coverage run it took 22.40 seconds and exceeded its
  20-second timing ceiling; 322 other tests passed, six optional/browser tests
  skipped, and branch coverage passed at 81.40%.
- CI now runs marked performance tests in a distinct non-coverage step while
  retaining their original timing ceilings. The coverage lane excludes only
  that marker, avoiding instrumentation-dependent wall-clock failures.
- Consolidated the 49-file immutable baseline tree into one deterministic
  `testdata/engine/baseline.tar.gz`. Tests and validators materialize it safely under
  `/tmp`; Git now sees only that archive and the golden expectations JSON under
  `testdata/engine/`.
- Post-consolidation validation matched all 10 archived inputs, eight outputs,
  and eight contact sheets; all 12 golden declarations and four frozen legacy
  contract tests pass.
- Repository-layout validation passes with eight canonical knowledge
  directories, 184 category-aligned technique cards, and no stale or missing
  structured paths. A documentary router/compiler smoke selected the new paths
  and emitted a complete creative directive.
- The deterministic test packer produced the same SHA-256 on consecutive runs;
  safe materialization reproduced the ignored local suite exactly after cache
  cleanup. Eleven focused golden, legacy-parity, and compatibility tests pass.
- Current cleanup quality gates pass: Ruff for `src`, `scripts`, and
  `tools/video-use/compat`; strict MyPy across 84 engine source files; workflow
  YAML parsing; all 192 knowledge JSON documents; and `git diff --check`.

## Failures

- Blender real-render verification is externally blocked. System installation
  requires an unavailable sudo password. The official portable 4.5.12 LTS
  archive passed its published SHA-256 and version probe, but did not reach test
  execution under sandboxed or unrestricted runs; the latter was interrupted
  after 13 minutes. No Blender parity claim is made.
- Root `uv lock` refresh reached the PyTorch macOS wheel index and timed out.
  The only root dependency change was removal of legacy Manim; lock metadata was
  updated consistently, the independent Manim 0.20.1 lock resolves, and the
  final `uv lock --check` passes.

- No repository-owned test suite or fixtures existed at baseline.
- `ruff check tools/video-use/helpers`: 10 existing errors.
- `ruff format --check tools/video-use/helpers`: all 30 files would reformat.
- A later direct audit of the expanded active helper set reports 273 Ruff
  findings, predominantly pre-existing line-length/import formatting. This
  workflow-layer debt is not part of the canonical engine or compatibility
  facade quality gate.
- The first two post-telemetry browser launches were not admitted by the
  execution reviewer. A later approved real Remotion run passed in 169.32 s;
  this blocker is resolved.
- `npm ls`: failed because `node_modules` is absent.
- Legacy existing fixture declares 2.4 s but renders 2.5 s.
- Legacy faceless fixture declares 2.0 s but renders 1.92 s.
- Legacy explicit `focus_x=0` resolves to center (`0.5`).
- Initial isolated package build could not reach PyPI inside the sandbox; the
  approved network rerun passed. This is resolved, not an engine limitation.
- Initial doctor Remotion probe used obsolete `--version`; changed to the
  supported `remotion versions` command and the doctor now passes.
- Setuptools 81 rejected the non-SPDX string form of the proprietary license;
  changed it to the standards-compatible PEP 621 text table. Resolved.
- Black 26.3.1 completed formatting but did not close its multi-file PTY session
  locally after worker exit. Per-file `black --check` exits zero; CI retains its
  normal non-PTY quality command.
- A sandboxed `npm ci` lost DNS after clearing `node_modules`; an approved exact-
  lock restore passed with zero vulnerabilities and all Node gates passed after.
- Two main-thread approval reviews timed out before a post-font Chromium launch.
  A focused review agent ran the current two-test browser suite outside the
  restricted sandbox and produced the passing evidence above.
- The first luma-matte integration run used incorrect FFmpeg option punctuation
  for `alphamerge`; the failure manifest captured command and stderr, the typed
  backend was corrected, and the unchanged render fixture passed.
- The first post-golden consolidated run found four old integration fixtures
  assigning `timeline_range` before their matching `source_range`. Strict
  assignment validation correctly rejected the transient invalid clips; the
  fixtures now use atomic model copies and all four renders pass.
- The first sample-clock ramp run called a nonexistent conversion method on
  `AudioSampleTime`; the failure manifest isolated the node, the implementation
  now uses its exact rational `time` property, and both aligned and deliberately
  non-frame-aligned real renders pass.
- The first selective-blur render exposed an invalid four-argument FFmpeg
  `min()` expression. The failure manifest retained the exact command/stderr;
  feather distance now uses nested binary minima and the unchanged decoded
  fixture passes.
- Independent tracking/matte review found crop-coordinate drift, geometry
  ambiguity, silently ignored automation, transition-handle inconsistency,
  omitted matte transitions, and unbounded matte-track fan-in. Each finding was
  reproduced by a focused test and resolved before this milestone closed.
- Initial `signalstats` integration showed `YBITDEPTH=6` for a flat gray 8-bit
  source because that field describes effective signal bits, not pixel storage.
  Analysis now probes the stream pixel format/raw bit depth. Its current
  `signalstats-v3` schema also closes immutable-source, hard-sample-bound, and
  FFprobe-fingerprint review findings; matched 8/10-bit fixtures pass.
- The first golden-v3 full test run read the removed v2 `max_hamming` key after
  its exhaustive all-frame comparison had passed. Sample checks now share the
  declared all-frame ceiling, the validator enforces both v3 tolerance fields,
  and the focused rerender passes. This was a test-schema migration defect, not
  an essence mismatch.
- Sandboxed npm audit initially failed DNS resolution and later returned one
  transient empty registry error. Approved registry retries returned the real
  advisory and then a zero-vulnerability result after the exact override.
- Black 26.3.1 formats the complete tree but its large multi-file process does
  not close under this local execution wrapper after printing completion. The
  formatter changed all 53 reported files, and 121 independent `-W 1` checks
  subsequently exited zero. Normal CI retains the native aggregate command.
- The final aggregate Black recheck again stalled under the local PTY wrapper,
  including with one worker and an isolated cache. The four final Python edits
  were formatted successfully before Ruff, strict MyPy, and the full-suite pass.
  This is a formatter-process shutdown limitation, not a reported source diff.
- The post-cleanup full-suite run was broader than the change warranted and
  took 35 minutes. Its only failure was the 2,000-item compile timing assertion
  at 22.40 seconds under coverage/full-suite load; the same targeted test passed
  in 11.10 seconds immediately afterward. No threshold was weakened and no test
  was disabled.

## Decisions

- Use rational frame/sample time and strict Pydantic schemas.
- Freeze executed legacy behavior before modifying production render helpers.
- Treat known legacy defects as documented canonical improvements.
- Keep editorial selection logic outside the engine package.
- Treat resolved font bytes as render inputs and evaluate range captions on the
  original timeline clock.
- Plan render backends per node and keep graphics props/assets strict at both
  Python and Node process boundaries.
- Bind final delivery to immutable preview/QC/contact-sheet evidence rather than
  treating a mutable status flag as approval.
- Preserve legacy outputs as immutable archives; compatibility tests may read
  them but must not execute a second renderer implementation.
- Define speed curves on the viewer-facing timeline: reverse source bytes before
  applying the local curve, retain authored curve context across reversible edit
  windows, and conform delivery frames only after temporal mapping.
- Materialize tracking as auditable timeline patches, never hidden project
  mutation. Caption tracking creates collision regions and never suppresses cues.
- Treat item/track mattes as validated render-DAG dependencies and multiply them
  with existing alpha; an asset path is the static form of the same typed effect.
- Bind tracking projection to declared source/canvas/fit geometry and preserve
  missing-data policy in the generated patch. A render may not reinterpret
  tracking coordinates under a different profile.
- Treat measured correction as reproducible source evidence plus an explicit
  numerical policy; never conceal editorial taste or fabricate neutral data in
  the analysis service.

## Remaining Tasks

- Execute the Blender real alpha/range integration gate on a host where the
  official process starts normally; this is the only external-graphics runtime
  proof still blocked.
- Commit/push the completed tree and observe the configured GitHub Actions jobs.
- Decide the intended licensing boundary before any public distribution: the
  root package declares `LicenseRef-Proprietary`, while the historical
  `tools/video-use/LICENSE` contains an MIT grant. No legal text was changed by
  this engineering cleanup.

## Known Risks

- Archived legacy timing is float-based and fixed to 24 fps; production imports
  convert it once into rational canonical time.
- Remotion/Chromium graphics goldens are materially slower than FFmpeg-only
  tests and require an execution environment that admits a local browser.
- HyperFrames browser rendering is likewise slower than FFmpeg-only work.
  HyperFrames' producer dependency currently carries three upstream moderate
  `@hono/node-server` advisories; the high-severity npm audit gate passes and
  engine jobs accept only confined local trusted compositions.
- Operation undo/redo is process-local; durable CLI history is represented by
  emitted inverse patches until a persistent project audit store is added.
- ASS has no portable literal brace/backslash escape. Canonical ASS export uses a
  marked reversible lookalike representation and reports that interoperability
  limitation to callers.
- Remotion's internal HTTP server/browser flags require OS/container network
  isolation for hosted multi-user execution; local execution accepts only
  trusted registered code and content-addressed staged assets.
- Approval artifacts prove evidence integrity but cannot technically prove the
  named reviewer visually examined the contact sheet; workflow policy and the
  recorded reviewer identity remain the human-control boundary.
- Boundary-pop analysis is bounded by caller policy on dense timelines; reports
  disclose when the configured maximum was reached.
- Hosted CI has not run on this uncommitted tree. Its commands have passing local
  equivalents except the PTY-specific Black shutdown issue documented above.
- Active workflow helpers are deliberately outside the canonical static gate and
  retain pre-existing style debt. They are smoke-tested command tools, not a
  second engine; behavior should be migrated or tested before broad reformatting.

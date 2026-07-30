# Public API

The installable package is `video_engine`; the console command is `video-engine`.

## Stable Imports

Client code should import the facade and data-transfer contracts from
`video_engine.api`. That module re-exports the canonical time, timeline, patch,
media, render, QC, inspection, migration, and export DTOs used at system
boundaries:

```python
from video_engine.api import (
    VideoEngine,
    Project,
    RationalTime,
    TimeRange,
    TimelinePatch,
    PatchEnvelope,
    RenderRequest,
    RenderResult,
    QCRequest,
    QCResult,
    InspectionRequest,
    MigrationResult,
    PreparedGraphic,
)
```

`video_engine.audio` is the stable convenience surface for `AudioTrack`,
`AudioClip`, `AudioBus`, `AudioRole`, `AudioSampleTime`, `Effect`, `EffectKind`,
and `LoudnessProfile`. Specialized service implementations remain available in
their subsystem packages, but future Editorial Brain integrations should prefer
the facade and DTO surface above.

## Python Facade

Implemented project lifecycle facade:

```python
from pathlib import Path
from video_engine import VideoEngine
from video_engine.core.time import FrameRate

engine = VideoEngine(Path("my-project"))
project = engine.create_project(
    "Example",
    width=1080,
    height=1920,
    frame_rate=FrameRate(numerator=30_000, denominator=1_001),
)
engine.save_project(project)
loaded, migrations = engine.load_project()
report = engine.validate_project(loaded)
doctor = engine.doctor()
```

Implemented methods:

- `VideoEngine.create_project(...) -> Project`
- `VideoEngine.save_project(project, path=None) -> Path`
- `VideoEngine.load_project(path=None) -> tuple[Project, list[str]]`
- `VideoEngine.validate_project(project) -> ValidationReport`
- `VideoEngine.doctor() -> DoctorReport`
- `VideoEngine.media() -> MediaService`
- `VideoEngine.adapters() -> AdapterService`
- `VideoEngine.exporter() -> ExportService`
- `VideoEngine.captions() -> CaptionService`
- `VideoEngine.color() -> ColorService`
- `VideoEngine.graphics() -> GraphicsService`
- `VideoEngine.editor(project) -> TimelineEditor`
- `VideoEngine.renderer(project) -> RenderService`
- `VideoEngine.qc(project) -> QCService`
- `VideoEngine.inspection(project) -> InspectionService`
- `VideoEngine.visual() -> VisualService`
- `VideoEngine.parity() -> MediaParityService`
- `VideoEngine.approvals() -> QCApprovalService`

`CaptionService` imports ASS/SSA/SRT/WebVTT into native tracks, exports
ASS/SRT/WebVTT with typed loss reports, and runs measured layout validation.
`RenderRequest.caption_track_ids` selects root caption tracks;
`RenderRequest.caption_languages` selects a language across nested sequences.
The selectors are mutually exclusive and unknown selections fail compilation.

`GeneratorClip` is the stable designed-graphics input. It carries a registered
component ID/version, strict JSON props, explicit logical asset references,
transparent-output intent, and rational timeline range. The built-in registry
currently exposes `title_card`, `hook_card`, `chapter_card`, `lower_third`,
`quote_card`, `stat_card`, `number_card`, `countdown`, `comparison`,
`product_feature`, `screenshot_frame`, `device_mockup`, `picture_in_picture`,
`split_screen`, `logo_reveal`, `call_to_action`, `end_card`, `progress_accent`,
`diagram_overlay`, `emphasis_text`, and `kinetic_caption`, all at version
`1.0.0`. Unknown props, component versions, or asset references fail before a
browser starts.

External authored graphics use `hyperframes_composition`, `manim_scene`, and
`blender_scene`. Call `engine.graphics().prepare_hyperframes(...)`,
`prepare_manim(...)`, or `prepare_blender(...)` to receive a `PreparedGraphic`
containing a strict `GeneratorClip` and deduplicated content-addressed
`MediaReference` objects. Renderer commands and staging remain backend-private.

```bash
video-engine graphics prepare hyperframes composition.html \
  --clip-id hook --start 0 --duration 3 --asset assets/logo.png=logo.png --json
video-engine graphics prepare manim scene.py \
  --clip-id diagram --start 3 --duration 4 --scene Architecture --json
video-engine graphics prepare blender product.blend \
  --clip-id product-spin --start 7 --duration 5 --camera Camera --json
```

`MediaService` implements content-addressed import/inspect/relink plus cached
proxy, thumbnail, waveform, and conformed-media generation. `TimelineEditor`
implements the professional operation set through `apply_operation`, atomic
multi-operation `apply_patch`, `undo`, and `redo`. Patches may carry an expected
project revision for optimistic concurrency; public patch envelopes reject the
engine-reserved `restore_project` inverse operation.

`AddTrackOperation` is the general revision-checked primitive for adding a
typed video, audio, caption, graphics, or adjustment track to an existing
sequence. Duplicate IDs and invalid insertion positions fail transactionally.
The operation carries no editorial lane-selection policy.

`Clip`, `AudioClip`, and `NestedSequenceClip` expose a canonical `retime` with
an exact rational rate, reverse flag, and audio-pitch policy. Visual `Effect`
objects accept typed position, scale, rotation, anchor, opacity, crop, corner
radius, blend, chroma/luma key, matte, grade, and LUT parameters. Supported
visual keyframes remain rational item-local times and are preserved through
range compilation. Track mattes accept exactly one content-hashed path,
same-sequence visual item, or video/graphics track reference.

Tracking decisions enter through `TrackingBinding`. The service returns an
auditable patch rather than a mutated project:

```python
application = engine.visual().materialize_binding(project, tracking_result, binding)
result = engine.editor(project).apply_patch(application.patch)
```

`TrackingBindingApplication` includes exact frame-quantized mapping evidence,
effect/collision-region IDs, and a strict revision-checked `TimelinePatch`.
Supported drivers are crop, position, graphic attachment, mask, blur, and
caption exclusion. Caption exclusion adds native collision regions; it does not
suppress caption cues and requires hold interpolation. Bindings validate probed
source display dimensions, sequence canvas, profile fit, static source reframe,
target track/type, and lock-safe application. `missing_policy` is `error`,
`hold`, or `interpolate`; optional `maximum_source_gap` places an exact rational
bound on interpolation. Generated effects retain geometry provenance so a render
under an incompatible canvas fails explicitly.

All public results are typed and serializable. Expected failures use typed engine
exceptions with stable machine codes and structured context.

`EngineConfig.remotion_browser_timeout_seconds` defaults to 120 seconds and may
be set with `VIDEO_ENGINE_REMOTION_BROWSER_TIMEOUT` from 7 through 300 seconds.
The value is forwarded to composition selection and media rendering; it is a
browser resilience limit, not an editorial timing decision.

`ColorService.pipeline(...)` returns a strict `ColorPipeline`. Its `effects()`
method materializes canonical input-interpretation, normalization, creative
grade, and LUT effects; `apply_project_settings()` and
`apply_delivery_profile()` bind working and output spaces without backend filter
syntax. `ColorService.analyze(source, source_range=..., sample_count=...)`
returns strict `ColorMeasurements` with exact rational range, SHA-256 source
identity, storage bit depth, FFmpeg and FFprobe fingerprints, analyzer version,
hard-bounded sample count, and cache evidence. Analysis decodes a verified
immutable snapshot so mutation cannot poison source-addressed cache records.
`ColorService.auto_grade(...)` applies a caller-visible
`AutoGradePolicy` and returns `MeasuredAutoGrade`, including a portable typed
contrast/gamma/saturation effect. Invalid or unavailable measurements fail
explicitly; no neutral fallback is fabricated.

`RenderService.execute_partial(request, target_node_ids)` executes only the
validated ancestor closure for explicit cacheable DAG targets and returns typed
artifacts plus node records. `RenderService.render(request)` uses durable,
project-scoped checkpoints for whole-output resumption.

## CLI Contract

The installed command is `video-engine`. Every command supports JSON output,
including argument-validation failures when `--json` is present, and uses
nonzero exit status for blocking errors. Required command groups are:

```text
init
doctor
media import|inspect|proxy|thumbnails|waveform
project validate
timeline inspect|apply-patch
render draft|preview|range|final
qc
inspect timeline|range|cut|audio|captions
migrate legacy-edl|faceless|cmx|fcpxml|otio
export
```

Currently implemented commands:

```bash
video-engine init PROJECT_DIR --name "Example" --json
video-engine doctor --project-root PROJECT_DIR --json
video-engine media import SOURCE... --project-root PROJECT_DIR --json
video-engine media inspect MEDIA_ID --project-root PROJECT_DIR --json
video-engine media proxy MEDIA_ID --project-root PROJECT_DIR --json
video-engine media thumbnails MEDIA_ID --project-root PROJECT_DIR --json
video-engine media waveform MEDIA_ID --project-root PROJECT_DIR --json
video-engine project validate PROJECT_DIR/project.json --json
video-engine timeline inspect PROJECT_DIR/project.json --json
video-engine timeline apply-patch PROJECT_DIR/project.json PATCH.json --json
video-engine render draft PROJECT.json OUTPUT.mp4 --json
video-engine render preview PROJECT.json OUTPUT.mp4 --json
video-engine render range PROJECT.json OUTPUT.mp4 --start 12/24 --duration 24/24 --json
video-engine qc PROJECT.json --output PREVIEW.mp4 --report-dir qc \
  --approve-by REVIEWER --approval-notes "reviewed contact sheet and report" \
  --approval-output qc/approval.json --json
video-engine render final PROJECT.json OUTPUT.mp4 --approval qc/approval.json --json
video-engine inspect timeline PROJECT.json --json
video-engine inspect range PROJECT.json OUTPUT.mp4 --start 0 --duration 10 --json
video-engine inspect cut PROJECT.json OUTPUT.mp4 --at 5 --window 2 --json
video-engine inspect audio PROJECT.json OUTPUT.mp4 --json
video-engine inspect captions PROJECT.json --json
video-engine migrate cmx SOURCE.edl --fps-num 24 --json
video-engine migrate fcpxml SOURCE.fcpxml --json
video-engine export PROJECT.json OUTPUT.edl --format cmx --json
video-engine export PROJECT.json OUTPUT.fcpxml --format fcpxml --json
video-engine export PROJECT.json CAPTIONS.vtt --caption-track captions --json
```

Render commands accept repeatable `--caption-track ID` or
`--caption-language CODE` options.

`QCRequest` carries caller-owned thresholds and scopes. `QCResult` returns a
typed report plus atomic JSON/Markdown paths. Technical warnings remain
non-blocking unless policy promotes them; unavailable evidence is `incomplete`.

`InspectionRequest` selects timeline/range/cut/audio/caption views. Results
contain complete/partial status, exact ranges, paginated or sampled artifacts,
hashes, and JSON/Markdown reports. Compatibility `timeline inspect` delegates
to the canonical timeline inspector.

`VideoEngine.adapters()` now exposes:

```python
result = engine.adapters().import_legacy_edl(path)
result = engine.adapters().import_faceless(project_dir, voiceover=voiceover)
result = engine.adapters().import_cmx(
    path,
    frame_rate=FrameRate(numerator=24),
    media_paths={"AX": source},
    source_timecodes={"AX": "01:00:00:00"},
)
result = engine.adapters().import_fcpxml(path, media_paths={"r2": source})
result = engine.adapters().import_otio(path, frame_rate=FrameRate(numerator=24))
```

Every result contains the canonical `project` and a strict `report`. The report
includes hashes, schema identity, resolved/offline assets and itemized losses.
Caption interchange remains `engine.captions().import_file()` / `.export()`.
The unified `engine.exporter().export(...)` surface additionally writes canonical
project JSON, caption sidecars, CMX 3600, FCPXML and optional OTIO. Every result
contains its destination, format, metadata and itemized preserved,
approximated, or omitted features.

Implemented migration CLI commands are:

```text
video-engine migrate legacy-edl SOURCE
video-engine migrate faceless PROJECT_DIR
video-engine migrate cmx SOURCE --fps-num 24 --media REEL=PATH
video-engine migrate fcpxml SOURCE --media RESOURCE=PATH
video-engine migrate otio SOURCE --fps-num 24
```

No placeholder command is advertised as implemented.

# Migration

The ownership and deprecation rules for historical commands are defined in
[`LEGACY_BOUNDARY.md`](LEGACY_BOUNDARY.md).

## Legacy Existing-Footage EDL

- Ordered `ranges` become linked canonical video/audio clips placed
  sequentially on tracks.
- Source start/end floats are converted with an explicit legacy timescale and a
  migration warning when they cannot land exactly on the project frame grid.
- `fit`, `focus_x`, `focus_y`, and manual crop become typed visual effects.
- Grade presets become typed color effects. Legacy `auto` analyzes each exact
  source range and stores source/tool/policy measurements with the typed effect;
  raw or unknown filter syntax is retained in the original import payload and
  migration report but deliberately produces no executable effect.
- Overlays become graphics clips; SFX become audio clips; transcript-derived or
  sidecar subtitles become caption cues.

## Legacy Faceless EDL

- Beats become clips/stills/generators at their declared absolute ranges.
- Voice-over, music, ambience, SFX, captions, and graphics become actual tracks.
- Executed camera, color, transition, caption, emphasis, diagram, and progress
  behavior is mapped to canonical effects/components.
- Editorial/knowledge fields are preserved in extension metadata and are not
  executed by engine core.
- Declared but previously ignored fields are reported as behavior improvements,
  not silently described as legacy parity.

## Compatibility Sequence

1. Freeze legacy fixtures and failure behavior.
2. Implement adapters and canonical execution.
3. Render equivalent fixtures through legacy and canonical paths.
4. Compare timing, decoded frames, audio windows, metadata, and QC findings.
5. Document intentional improvements such as correct cache invalidation,
   rational timing, focus value zero handling, and non-Pillow typography.
6. Update every production caller and document.
7. Remove the old render implementations only after their executed capabilities
   have canonical regression evidence and caller searches are empty.
8. The faceless, vertical-podcast, caption-variant, and standalone SFX renderers
   are retired. The anti-return regression recursively scans live source,
   helpers, scripts, workflows, skills, presets, and operator documentation;
   immutable baselines and this historical migration record remain read-only
   evidence rather than executable paths.

The historical `timeline_view.py` command remains only as a compatibility
delegate. It constructs or imports a canonical project, calls
`InspectionService`, and publishes the service's hashed contact sheet and
JSON/Markdown reports. It no longer owns raw frame extraction, waveform
analysis, or image composition.

Every adapter returns a structured migration report with warnings, preserved
extensions, dropped fields, approximations, and source schema identity.

## Interchange

- CMX 3600 import requires an explicit frame rate for non-drop files. Drop-frame
  files default to 30000/1001 unless the caller explicitly selects 60000/1001.
  Illegal dropped labels are rejected. Record timecode is rebased to timeline
  zero; source timecode uses caller/media origins or a reported earliest-event
  inference. Cuts, black gaps, video/audio designators, constant retimes and
  adjacent dissolves are canonical; M2, wipes, keys and comments are preserved.
- FCPXML import uses `defusedxml`, accepts a file or confined
  `.fcpxmld/Info.fcpxml`, and rejects entities/DTDs. Exact `N/Ds` timing,
  formats, assets, spines, connected lanes, gaps, nested media sequences,
  captions, markers, transforms, opacity, trim crop, endpoint retime and cross
  dissolve are imported. Network media remains offline/relinkable; unsupported
  child XML is retained and reported.
- OpenTimelineIO is optional behind `uv sync --extra interchange`. Clips, gaps,
  AV tracks, external references, markers and transitions import through the
  same report contract. OTIO effects and overlap-transition timing that do not
  have a backend-neutral equivalent remain explicit losses.
- CMX export emits exact source and record timecodes, black events, AV track
  designators and adjacent dissolve durations. Unsupported canonical tracks,
  items, and retime policy are itemized in the export result.
- FCPXML export emits exact rational formats, assets, spines, connected lanes,
  captions, dissolves and reusable nested sequence media resources. Features
  without a portable FCP representation remain canonical and are reported.
- OTIO export uses the same optional dependency boundary and loss contract.
- ASS/SSA, SRT and WebVTT use `VideoEngine.captions()` and return native caption
  tracks/styles plus structured format losses.

# Testing

## Test Layers

- Unit: rational time, schemas, migrations, operations, graph validation,
  compiler lowering, cache keys, caption layout, audio math, and QC rules.
- Property: timeline operations preserve ordering, nonnegative duration, source
  bounds, and undo/redo round trips.
- Integration: FFprobe registry, derivatives, FFmpeg graphs, ASS burn, Remotion,
  HyperFrames and Manim bridges, inspection, adapters, and reports.
- End to end: required golden projects across formats and production profiles.
- Performance/recovery: thousands of items, range rendering, cache invalidation,
  resumption, worker failure, and memory-conscious compilation.

## Legacy Baseline Fixtures

Synthetic fixtures cover existing footage, faceless beats, captions, timed SFX,
overlays, vertical crops/focus edges, HLG/PQ metadata, silent media, voice-over
duration edges, crossfades, and stale-cache behavior.

Each baseline records tool versions, input/EDL/output SHA-256, decoded video
frame hashes, decoded PCM hashes, probe JSON, duration, dimensions, frame rate,
timebase, pixel/color metadata, sample rate/layout, loudness/true peak, cut/cue
window measurements, representative frames, and contact sheets.

The immutable baseline is committed as
`testdata/engine/baseline.tar.gz`. Tests and release validators safely
materialize it into a process-owned temporary directory and remove that
directory at exit. This keeps 49 binary/evidence files out of ordinary code
reviews without weakening the frozen legacy contract.

## Golden Projects

The canonical suite includes existing footage, faceless vertical, podcast,
interview, product ad, recap, documentary, motion graphics, long-form, HDR-to-SDR,
mixed frame rate, and multitrack audio. Tests assert meaningful behavior rather
than object existence. Golden schema v3 records every decoded-frame perceptual
hash, the full-sequence digest, pre-encode stereo PCM evidence, temporal audio
windows, toleranced loudness/true peak, QC-output binding, contact-sheet
checksum, and scenario-specific metadata/behavior assertions. The manifest
also fingerprints the complete FFmpeg and FFprobe versions: exact decoded
digests are required on a matching toolchain, while bounded perceptual and
signal comparisons remain authoritative across compatible toolchain builds.

## Commands

CI installs locked environments, runs Ruff, Black, MyPy, branch coverage,
package build, Node typecheck/bundle, the complete non-browser integration lane,
all twelve golden declarations, immutable baseline validation, and separate
browser and extended-graphics lanes. The browser lane executes Remotion and
HyperFrames; the extended lane installs the isolated Manim lock and Blender,
then runs both real alpha/range adapters. Wall-clock performance tests run in
their own step without coverage instrumentation.

Static gates cover the canonical package, tests, release scripts, and
`tools/video-use/compat`. The remaining `tools/video-use/helpers` files are
workflow preparation/review commands rather than engine implementations. Their
CLI entry points receive a complete `--help` smoke test; compatibility wrappers
also have structural boundary tests. Existing style debt in the active workflow
scripts is tracked separately so a formatting-only rewrite cannot obscure an
engine change.

Repository policy currently keeps the expanded `tests/` tree ignored to reduce
code-review file noise. The exact suite is committed as the deterministic
`testdata/engine/tests.tar.gz`; `scripts/materialize_tests.py` safely expands it
inside fresh CI runners before collection. Local checkouts may keep the ignored
expanded tree for development.

After changing a local test, refresh the deterministic review archive with:

```bash
uv run python scripts/materialize_tests.py --pack
```

The packer excludes Python caches, normalizes archive ownership and timestamps,
and atomically replaces the archive. Run the materializer against a temporary
directory to verify the committed payload without overwriting local tests.

Current render gate:

```bash
uv run pytest -q tests/unit/test_render_graph.py \
  tests/unit/test_render_compiler.py tests/integration/test_render_engine.py
```

It covers strict/frozen nodes, graph failures, stable partial topology, identity
optimisation, backend capability errors, parallel scheduling, stable cache keys,
corrupt-cache recovery, range/source rebasing, subtitle-last graph order, strict
effect parameters, real FFmpeg metadata/duration/audio/caption output, CLI
delivery, and second-run cache reuse.

Tracking and matte gates additionally execute constant/reverse/ramped source
mapping, subject ambiguity, all six binding drivers, transactional application,
inverse restoration, item/track matte validation and cycles, disabled matte-only
tracks with gaps/transitions/bounded fan-in, transition-handle and snapshot
validation, unsupported automation rejection, confidence-gap policy, geometry
drift, lock enforcement, and target-boundary synthesis. Real tests materialize
moving masks, moving selective blur and crop through the public patch API before
checking prior-alpha multiplication, centered decoded pixels, transparent gaps,
and full/range parity.

Measured color gates compare normalized 8-bit and 10-bit analysis, equivalent
rational cache keys, corrupt-record quarantine, invalid source-range rejection,
legacy per-range migration, policy bounds, and a real FFmpeg render whose typed
gamma correction is verified on decoded pixels. They also mutate the original
after snapshot creation, assert the hard sample bound, and fingerprint both
analysis tools.

Current subsystem gates also include:

```bash
uv run pytest -q tests/unit
uv run pytest -q tests/integration/test_qc.py
uv run pytest -q tests/integration/test_inspection.py
uv run pytest -q tests/performance/test_long_form.py
```

External graphics have focused opt-in real-render gates:

```bash
VIDEO_ENGINE_RUN_HYPERFRAMES_INTEGRATION=1 uv run pytest -q \
  tests/integration/test_hyperframes_graphics.py
VIDEO_ENGINE_RUN_MANIM_INTEGRATION=1 uv run pytest -q \
  tests/integration/test_manim_graphics.py
```

Both assert exact 24-frame, 320x180, 24 fps ProRes alpha output. Blender's
lowering and capability selection are unit-tested. Its opt-in real-render gate
was attempted with checksum-verified Blender 4.5.12 inside and outside the
sandbox; the process did not reach test execution and the unrestricted run was
interrupted after 13 minutes.

The local standard doctor auto-discovers the isolated Manim executable and
passes 15 checks; only optional Blender warns. The extended gate requires the
locked Manim/LaTeX toolchain while Blender remains optional. The real Manim `MathTex` smoke render
passes with the installed pdfTeX/dvisvgm toolchain. Hosted CI repeats that gate
and owns the real distro-Blender lane.

The final post-hardening consolidated Python run passes 320 tests with six
expected optional/browser skips and 81.37% branch-aware coverage in 483.53
seconds. QC executes
real decode, signal, metadata, checksum and report workflows. Inspection tests
all five public modes,
exact frame/cut sampling, per-channel sample counts, artifact hashes, pagination,
and JSON CLI output. The 2,000-item long-form gate compiled in 6.53 seconds with
bounded graph fan-in.

Interchange tests assert exact timeline/source ranges, DF/NDF legality, offline
asset identities, nested sequence references, transitions, typed visual effects,
caption and marker placement, malicious XML rejection, report persistence, and
machine-readable CLI output. Export round trips cover canonical JSON, WebVTT,
CMX source/record origins, and FCPXML nested resources/audio/captions. Adapter
integration also compares the canonical
faceless SFX stem against the frozen legacy byte hash.

Visual-transition integration executes dissolve, dip-to-color, wipe, slide,
push, and zoom through FFmpeg and validates exact frames and duration. Audio
integration executes EQ, compression, limiting, gating, de-essing, noise
reduction, channel mapping, and sample-rate conversion from typed effects. Draft
CLI delivery is decoded at its bounded 1280x720 profile. Hostile QC fixtures
prove twenty encoded-output findings plus corrupt, missing-stream, durationless,
hash-mismatch, missing, and offline ingest findings.

Migration parity compares decoded metadata, sampled frame hashes, dominant audio
frequency, and RMS level. Frozen existing-footage cases use a declared 18 dB RMS
window because the canonical path fixes their loudness-normalization defect;
new faceless parity uses a 3 dB window.

The canonical golden lane records exactly twelve projects. Golden-v3 generation
and structural validation cover all twelve scenarios. The validator requires
valid tool fingerprints, all-frame dHash sequences and tolerances, decoded PCM
evidence, output sample counts, temporal/spectral assertions, QC dispositions,
contact-sheet identity, and immutable baseline parity evidence. The corrected
complete lane passes all 11 declarations in 285.90 seconds: one manifest
declaration plus ten real canonical renders, including both Chromium projects.
The final current-tree browser lane additionally passes five tests in 153.26
seconds: both Remotion bridge integrations, faceless migration parity, product
ad, and motion graphics.

Delivery evidence includes real horizontal `stretch`, vertical `cover`, and
square `contain` renders with exact dimensions and decoded crop/letterbox pixels.
Freeze evidence identifies the exact selected source frame across full,
sectioned and range output under normal, reverse, constant-speed, and ramped
retimes. Transactional trim, split, slip, and replace operations materialize or
move that source decision without violating duration invariants. Caption-locality
evidence changes one middle section through the public partial API and proves
the first/third video roots, every audio root, unchanged visual ancestors, and
persisted source identity remain reusable without hashing source bytes again.

Recovery tests cover corrupt checkpoint quarantine, project/revision identity,
concurrent attempt merging, public partial execution, and cache-disabled resume.
A real fail-once FFmpeg integration recovers completed sections and produces an
MP4 byte-identical to a clean render. Derived-media tests corrupt proxy,
waveform, and conform artifacts and verify locked atomic rebuild/publication.

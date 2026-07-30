# Engineering Decisions

## D001: Rational Time Is Authoritative

Use integer `value/timescale` representations for timeline and sample time.
Floating-point seconds are accepted only at legacy/API boundaries and are
converted explicitly. This prevents cumulative drift and supports 24000/1001,
30000/1001, 60000/1001, and audio sample clocks.

## D002: Pydantic Models With Strict Extra Rejection

Canonical persisted schemas use Pydantic v2 with unknown fields rejected.
Every extensible object has an explicit namespaced `extensions` mapping.

## D003: Python Command Objects, JSON Patch Envelope

Editing operations use typed command objects internally. A stable JSON envelope
serializes commands for agents and automation. Atomic execution records before/
after revisions, audit metadata, validation output, and an inverse when safe.

## D004: Immutable Render DAG

Canonical effects compile to typed immutable nodes. Cache keys include node
type/version, complete normalized parameters, dependency keys, media hashes,
backend/tool versions, and delivery settings.

## D005: FFmpeg Is The Required Baseline Backend

FFmpeg handles decode, conform, transforms, audio, captions, encode, and mux for
the baseline engine. Remotion and HyperFrames are installed designed-graphics
bridges. Blender and Manim are executable-isolated optional renderers;
OpenTimelineIO and ML trackers remain optional plugins.

## D006: Legacy Defects Are Evidence, Not Desired Parity

Regression fixtures freeze legacy execution. Known stale cache reuse, ignored
absolute gaps/overlaps, `focus=0` truthiness, fixed loudness, and Pillow final
typography are documented improvements in the canonical path, not behavior to
reproduce.

## D007: No Editorial Policy In Core

Topic terms, effect rotation, interest scoring, hook selection, and performance
logic stay outside `video_engine`. The engine executes caller-supplied tracks,
effects, keyframes, components, operations, and patches.

## D008: Preserve Requested Rational Timescales

`RationalTime` equality and arithmetic are fraction-based, but instances retain
their requested timescale. Reducing `1602/48000` to `267/8000` loses the audio
sample index even though the duration is equal. Frame and sample clocks therefore
keep their representational timescale while comparisons remain exact.

## D009: Narrow Security Overrides Are Pinned

The exact Remotion 4.0.481 dependency tree initially resolved vulnerable
`fast-uri@3.1.2`. The engine pins the smallest compatible patched release,
`3.1.4`, through an npm override rather than silently accepting the advisory or
moving the full graphics stack.

## D010: Track Order Is Bottom To Top

Canonical visual and graphics tracks are compiled in list order, with later
enabled items above earlier items. Migrated projects place captions after visual
and graphics layers to preserve subtitle-last behavior. A future explicit layer
operation may place graphics above captions; no compiler inference changes the
caller-supplied stack.

## D011: Semantic Nodes Do Not Imply One Permanent Process Model

The graph records backend-neutral meaning. The current executor materializes
cacheable node artifacts; backend planning may later fuse compatible linear
nodes without changing semantic node records, hashes, validation, or manifests.
This keeps correctness and incremental caching independent of subprocess count.

## D012: Reject Unsupported Lowering

Transitions without defined source-handle semantics, unresolved nested
sequences, and keyframed effects without interpolation lowering produce stable
unsupported-capability errors. The engine never claims support by omitting them.
Raw backend overrides are disabled by default and require an explicit adapter.

## D013: Alpha-Capable Ten-Bit Lossless Working Video

FFmpeg materialized video nodes use FFV1 `yuva444p10le` intermediates. This
preserves transparency created by transforms/keys and avoids reducing HDR or
10-bit sources before technical colour conversion. Delivery pixel format is
applied only by the output transform and encoder.

## D014: Cache Identity Is Semantic And Publication Is Serialized

Cache keys exclude node IDs, dependency IDs, and content-addressed asset paths;
ordered upstream cache keys and asset SHA-256 values carry dependency identity.
A permanent per-key `flock` is held across the second lookup, node execution,
fsynced atomic publication, and validation so independent engine processes do not
duplicate or destroy work.

## D015: Disabled Audio Buses Mute Their Subtrees

An enabled child routed through a disabled parent is silent. Disabled never means
implicit bypass because bypass would evade caller-supplied bus gain, processing,
and routing intent. Every non-master bus must have a parent path to master.

## D016: Caption Range Evaluation Uses Original Timeline Time

Caption cues and words remain on their canonical timeline clock inside render
nodes. Range renders carry a rational evaluation offset and shift video PTS only
while libass evaluates subtitles. Clipping/restarting karaoke tags would make a
range frame differ from the same full-render frame and is therefore forbidden.

## D017: Fonts Are Render Inputs

Font-family names alone are not deterministic. Caption layout resolves installed
font files, compilation carries those paths, cache keys hash their bytes, and the
backend stages them for libass. Changing font content must invalidate caption
pixels without invalidating unrelated source-media nodes.

## D018: Backend Planning Is Per Node

A preferred backend is attempted first for every reachable node, then the
registry selects another capable backend when needed. Cache identity, manifests,
and execution records retain the actual backend per node. This permits a
Remotion motion-graphic source to feed FFmpeg composition and delivery without
making either backend understand the other's canonical responsibilities.

## D019: Declared Media Hashes Are Verified, Not Trusted

Content-addressed identity is a claim that must be checked against the current
bytes before cache lookup. Decode cache-key construction hashes an existing
source and fails on a declared SHA mismatch. Relocation may preserve an identity;
mutation at the same path may not reuse stale decoded or downstream artifacts.

## D020: Designed Graphics Use A Trusted, Deterministic Bundle

Graphics accept only registered component IDs/versions, strict props, declared
content-addressed assets, exact frame ranges, and bounded canvases. The bridge
entry and component code are engine-owned. Exact Remotion, React, Zod, TypeScript,
browser and Inter font identities participate in tooling or source fingerprints.
Hosted deployments must still isolate the browser process and its temporary HTTP
server at the OS/container network boundary.

## D021: Retime Is An Item Mapping, Not An Effect String

Every source-backed item declares an exact positive rational playback rate and
reverse flag. Its source duration must equal timeline duration multiplied by
that rate. Range and edit operations preserve this invariant. Legacy speed or
reverse effect dictionaries are rejected because two temporal authorities
would make linked audio, inverse edits, and cache invalidation ambiguous.

## D022: Visual Automation Stays Structured Through The DAG

Canonical nodes carry property-scoped rational-time points, values,
interpolation, tangents, and a range evaluation offset. FFmpeg expressions are
derived only inside the backend. This keeps project patches and cache identity
portable while making a range frame evaluate on the same clock as a full render.

## D023: Mattes Are Graph Inputs

External alpha/luma mattes compile into content-verified decode nodes and a
strict two-input mask node. A path hidden inside a filter parameter would evade
graph validation, source collision checks, and upstream cache identity. Chroma
and luma keys remain one-input mask nodes; graph arity is mode-specific.

## D024: Long Renders Are Exact Independent Sections

Section boundaries land on the delivery frame clock and record their audio
sample boundary. Visual, caption and audio roots cache independently, then join
through bounded concat nodes. Changing one cue does not invalidate unrelated
chapters or source analysis.

## D025: Resume State Is Durable And Separate From Cache Policy

Fsynced checkpoints are keyed by compiler/graph/profile/range/section/backend
identity and exclude destination path. Cache use and resumption are independent.
Attempt history and completed roots make interruption and failure inspectable.

## D026: Sequence Revisions Are Immutable Snapshots

An edit snapshots current sequence content before advancing its revision. Pinned
nested clips resolve that immutable digest; unpinned clips resolve current state.
Historic revisions cannot be silently replaced.

## D027: Time Ranges Are Half-Open Through Backend Lowering

Canonical `[start,end)` semantics lower to greater-than-or-equal/less-than
predicates. Non-normal blends retain upstream alpha before overlay so transparent
top pixels cannot modify base RGB.

## D028: Tracking Results Use Source Time

Tracking observations are source-absolute evidence. Timeline effects apply the
source in-point, exact rational rate and reverse mapping. Multi-subject split
fallback becomes explicit duplicated tracks and panel reframes.

## D029: QC Missing Evidence Is Never A Pass

Technical QC distinguishes passed, warned, failed and incomplete. Final encoded
essence is decoded and measured; a successful manifest supplies delivery
expectations. Checks without sufficient telemetry remain incomplete.

## D030: Inspection Is Exact Evidence, Not Editorial Judgment

Inspection snaps half-open samples to the encoded frame grid, preserves rational
timeline/source mappings and audio sample counts, and emits hashed evidence in
bounded pages. It does not infer whether an edit is creatively good.

## D031: Crop Coordinates Declare Their Space

Canonical crop parameters distinguish source pixels from fitted-canvas pixels.
Legacy manual crops execute before reframing; visual canvas crops execute after
fit. A backend must never infer this ordering from effect names or dimensions.

## D032: Legacy Implicit Decisions Live In Adapters

Historical automatic fades, generated SFX recipes, faceless motion defaults and
caption burn choices are materialized by versioned adapters. The canonical core
executes those objects but does not acquire hidden creative policies.

## D033: Designed Caption Burns Retain Native Caption Data

Faceless rich cues import into suppressed native cues while registered Remotion
components provide the selected burn-in. This avoids double rendering without
discarding text, language, timing or emphasis metadata needed by future systems.

## D034: Automation Is Never A Static Identity

A transform with identity base values cannot be optimized away when it carries
automation. Node replacement must update both graph input tuples and structured
composite/audio input descriptors.

## D035: Migration Reports Are Reproducibility Artifacts

Reports hash the primary source and every consumed sidecar, list resolved and
offline media, preserve unsupported metadata and state each approximation or
improvement. A report marked valid must contain a canonically valid project.

## D036: Still Images Do Not Require Source Duration

Duration is authoritative on `StillImageClip`, not the image container. Ingest
requires positive source duration only for time-based video/audio use.

## D037: Interchange Timing Becomes Canonical Once

CMX timecodes and FCPXML/OTIO rational values are parsed exactly, rebased, and
then stored as canonical rational ranges. Source syntax is retained in extension
metadata and reports; it does not remain a parallel timing authority.

## D038: Graphics Bounds Are Render Evidence

Component definitions declare whether edges are safe-area, intentional accents,
or full-frame. Remotion measures alpha content per frame and manifests the
telemetry. QC may not call graphics uncropped merely because props validated.

## D039: Interchange Loss Is A Typed Result

Export never implies that a target format can carry the full canonical project.
Each export returns preserved, approximated, and omitted features with canonical
paths. CMX, FCPXML, OTIO, caption sidecars, and project JSON share this boundary;
backend syntax never becomes a second canonical timeline.

## D040: Source Identity Is Persisted But Byte Identity Remains Authoritative

The source-identity store keys prior SHA-256 evidence by size, nanosecond mtime
and ctime, device, and inode. Unchanged files avoid a second full read and decode
nodes use compiler-verified stream metadata without another probe. Any stat
identity change forces a fresh content hash; a mismatch with the project media
reference blocks compilation.

## D041: Recovery Reuses Only Checkpoint-Proven Artifacts

General cache policy and recovery evidence are independent. A resumed render may
read completed node keys recorded by its project/revision/backend checkpoint even
when ordinary cache lookup is disabled. It may not adopt an unrelated cache key.
Corrupt checkpoints are quarantined, concurrent completions merge, and a later
failure cannot overwrite an already successful result.

## D042: The Second Renderer Is Removed, Baselines Remain

Executed legacy faceless behavior remains frozen as immutable media, hashes,
contact sheets, and black-box assertions. Production execution imports the
legacy EDL into the canonical timeline and uses the normal render graph. A source
and documentation scan test fails if the retired module or symbol returns.

## D043: Goldens Compare Decoded Behavior

The twelve canonical golden projects assert rational timing, decoded perceptual
frame hashes, exact pre-encode sample counts, output stream metadata, spectral
audio content, expected QC findings, and graphics bounds. The expectation
manifest fingerprints FFmpeg and FFprobe. Exact decoded digests apply when that
toolchain matches; bounded all-frame perceptual distances and audio signal
measurements carry the cross-toolchain contract. Container hashes are evidence
but are not the sole cross-toolchain oracle.

## D044: Speed Curves Live On The Timeline Clock

Retime rates are exact rational derivatives of source time with respect to the
viewer-facing timeline. A reverse item therefore reverses its verified source
window before the local speed curve executes. Temporal mapping precedes final
frame-rate conform, while audio control knots are scheduled on the sample clock
through one stateful Rubber Band processor. Every temporal node declares and
enforces its target frame or sample count. Edit windows retain typed authored-
curve context so trimming and later extension do not flatten discarded slopes.

## D045: Tracking Materializes Auditable Patches

Tracking backends produce canonical source-time observations; they do not mutate
the timeline. A binding resolves one explicit subject and geometry, maps samples
through the source clip's exact retime, quantizes on the target sequence frame
grid, and emits a revision-checked `TimelinePatch` plus mapping evidence. Crop,
position, masks, blur, graphic attachment, and caption collision regions are
ordinary typed operations. Caption tracking never silently suppresses a cue.

## D046: Mattes Are Render Dependencies And Multiply Alpha

A track matte owns exactly one static path, same-sequence item, or visual-track
reference. Item and track references become upstream render nodes, so recursive
effects and cache invalidation follow the DAG rather than a side channel.
Validation rejects ambiguous, missing, disabled, uncovered, self-referential,
and cyclic dependencies. Matte alpha or luma multiplies an item's existing alpha;
it never replaces opacity already authored by another effect. A referenced track
uses a transparent canvas so intentional gaps remain transparent.

## D047: Tracking Coordinates Are Render-Bound Evidence

A tracking binding declares probed source display dimensions, canonical canvas,
fit, focus and zoom. These values must match the sequence, delivery profiles and
the tracked source's static reframe. Subject boxes are converted to backend crop
overflow coordinates once; later renders reject a mismatched canvas rather than
reinterpret pixels. Target boundaries are evaluated on the sequence frame grid,
and confidence/sampling gaps follow caller-owned error, hold or interpolate
policy. Caption exclusions are hold regions until the caption schema gains
animated collision geometry.

## D048: Measured Color Is Evidence, Not Hidden Taste

Automatic correction is an explicit caller-visible numerical policy applied to
measurements from an exact rational source range. Measurement identity includes
source SHA-256, normalized range, sample count, analyzer version, storage bit
depth, and the complete FFmpeg/FFprobe analysis fingerprints. Analysis reads a
verified immutable snapshot, and the requested sample count is a hard bound.
Failures block instead of falling back to invented neutral statistics. The
resulting typed grade embeds semantic measurement and the full policy; transient
cache-hit state is excluded so a warm cache cannot change render identity.
Creative interpretation remains a caller decision outside the engine.

## D049: Compatibility Utilities Cannot Be Second Renderers

Preparation and inspection helpers may translate inputs or emit typed project
decisions, but only the canonical render service may encode production output.
Unreferenced podcast, caption-variant, and SFX renderers were retired after their
valuable behaviors gained canonical decoded regression evidence. The remaining
grade compatibility utility cannot accept a media output or raw backend filter.
Unknown legacy backend syntax remains visible in migration evidence and is never
lowered implicitly.

## D050: Freeze Is A Temporal Source Decision

A freeze selects one item-local presentation frame on the exact owning-sequence
frame grid, maps it through reverse and retime to a single verified source
frame, and extends that frame to the owning clip duration. Delivery frame rate
does not redefine the selection grid. Trim and split materialize the selected
source frame, slip moves it, and duration-changing edits update the freeze
duration atomically. Range and section renders reuse the same mapped source
identity. The effect cannot carry automation or consume transition handles as
moving source media.

## D051: Golden Portability Is Explicit

Golden expectations separate semantic invariants from encoder-build identity.
Dimensions, frame counts, rational rates, sample-grid duration, all-frame
perceptual bounds, signal measurements, QC findings, and temporal audio behavior
must hold across compatible builds. Exact all-frame and PCM digests are an
additional same-toolchain regression oracle, selected by a hash of the complete
FFmpeg and FFprobe version output.

## D052: Migration Audio Parity Measures Level And Content

Legacy migration parity gates dominant frequency and RMS level over exact
rational windows. The frozen existing-footage renderer has known loudness
normalization defects, so its comparisons use an explicit caller-owned 18 dB
RMS tolerance and report the canonical level correction as an improvement.
New faceless migration uses a 3 dB tolerance. Neither threshold is a creative
target; delivery loudness remains owned by the selected delivery profile.

## D053: External Graphics Share One Canonical Clip Contract

Remotion, HyperFrames, Manim, and Blender are renderer implementations, not
parallel timelines. Each consumes a registered strict `GeneratorClip`, declared
content-addressed assets, an exact timeline range, and a renderer tag compiled
into the DAG. Outputs normalize to ProRes 4444 alpha and then use the ordinary
FFmpeg composite, cache, delivery, and QC path. Manim 0.20.1 is locked in an
isolated uv project because its NumPy 2.1+ requirement conflicts with the core
media stack's NumPy 1.26.4 contract.

## D054: Track Creation Is A General Transactional Operation

Revision-checked callers may need to add a typed lane before inserting media.
`AddTrackOperation` adds exactly one canonical track at an explicit or trailing
index, rejects duplicate IDs and invalid positions, and participates in normal
validation, audit, inverse, undo and redo. It contains no editorial rule about
when a lane should exist or what content belongs on it.

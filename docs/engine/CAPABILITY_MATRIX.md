# Capability Matrix

Legend: `legacy` exists in a current helper, `building` is under migration,
`planned` is not implemented, and `verified` has automated behavioral evidence.

| Capability | Existing footage | Faceless | Canonical engine | Evidence/notes |
| --- | --- | --- | --- | --- |
| Ordered cuts | legacy | legacy | verified | Rational frame-grid compiler and render tests |
| Per-segment extraction | legacy | no | verified | Exact source trim nodes and range renders |
| Boundary audio fades | legacy | no | verified | Sample-aligned configurable fades; legacy adapter preserves 30 ms policy |
| Cover/contain/stretch | legacy | cover only | verified | Typed scale/focus lowering and pixel tests |
| Horizontal/vertical/square/custom size | legacy | legacy | verified | Real stretch/cover/contain renders verify exact dimensions, rate, SAR, crop and letterbox pixels |
| HDR-to-SDR | legacy | no | verified | HLG/PQ interpretation and tested Rec.709 output |
| Grade knowledge/presets/auto grade | legacy | simple fixed filters | verified | Exact-range measured correction with typed gamma/policy evidence, content cache, typed grade/LUT, and HDR/SDR goldens |
| Overlay compositing | legacy | legacy | verified | Alpha-capable 10-bit compositing inspected by pixel |
| Blend/adjustment layers | no | raster legacy | verified | Screen blend and range-bounded grade render pixels |
| Keys and mattes | partial chroma | raster masks | verified | Animated shape/selective blur plus path/item/track alpha/luma mattes; cycle, gap, alpha and range render evidence |
| Transitions | limited overlay/cuts | global crossfade | verified | Decoded dissolve, dip, wipe, slide, push, zoom and exact audio crossfade execution |
| ASS captions | legacy | fallback | verified | Native strict cues/styles and parser/render round trips |
| Word/phrase highlights | style-driven ASS | raster overlays | verified | Word timing, punctuation, style changes, range parity |
| Subtitle-last order | legacy | legacy | verified | Compiler-order assertion and end-to-end burn test |
| Voice-over replacement | no | legacy | verified | Explicit audio roles/tracks and embedded replacement |
| Timed SFX | legacy file-based | generated legacy | verified | Sample-count placement through canonical audio tracks |
| Loudness normalization | fixed legacy target | no | verified | Optional profile-owned one/two-pass targets |
| Multitrack audio/buses | no | no | verified | Strict routing, automation, sidechain, mix integrations |
| Audio processors | limited helper filters | limiter only | verified | Real typed EQ, compression, limiter, gate, de-esser, denoise, channel-map and resample renders |
| J/L cuts | implicit ranges only | no | verified | Transactional operations and separate AV ranges |
| Timeline operations/undo | no | no | verified | Atomic patches, audit, inverse, undo/redo tests |
| Nested sequences | no | no | verified | Recursive compile, version/cycle checks, caption selection |
| Proxy/thumbnail/waveform | isolated helpers | no | verified | SHA-addressed derivation cache and real FFmpeg tests |
| Render DAG | no | no | verified | Strict nodes, graph validation, optimizer, scheduler |
| Incremental cache | partial/staging | unsafe mtime cache | verified | Section roots, public partial execution, corruption rebuild, checksums and locks |
| Remotion bridge | no | no | verified | 21 strict components; real alpha/range, alias and cache renders |
| HyperFrames bridge | docs/manual | docs/manual | verified | Exact 0.7.77 producer, lint gate, confined assets, typed variables and real 24-frame alpha/range render |
| Manim adapter | helper/manual | helper/manual | verified optional | Exact isolated 0.20.1 toolchain; typed scene/renderer/seed controls and real 24-frame alpha/range render |
| Blender adapter | helper/manual | helper/manual | implemented, runtime blocked | Typed scene/camera/engine/range controls, confined assets and deterministic lowering; official 4.5.12 process did not reach render execution locally |
| Keyframed visual transforms | partial helper logic | raster legacy | verified | Rational range-aware motion/opacity pixel renders |
| Freeze frames | no | descriptive only | verified | Exact item-local frame selection through retime/reverse; full, section and range decoded parity |
| Tracking/reframing | focus hints | no | verified | Six patch-based drivers, constant/reverse/ramp frame mapping, evidence, caption collision regions and executable split fallback |
| Long-form section rendering | no | no | verified | Chapter/section concat, checkpoints and 2,000-item performance test |
| Technical QC | partial visual gate | workflow QC | verified | Five scopes, encoded analysis, JSON/Markdown and hashed evidence |
| Timeline inspection | delegated compatibility helper | no | verified | Five exact rational views, bounded pages, combined filmstrip/waveform sheets, captions and audio peaks |
| Legacy adapters | N/A | N/A | verified | Existing/faceless fixtures, hashes, aliases and JSON reports |
| SRT/ASS/WebVTT import/export | partial burn only | partial burn only | verified | Native tracks plus structured import/export loss reports |
| OTIO/EDL/FCPXML | no | no | verified/optional | Native CMX/FCPXML import/export round trips; optional OTIO bridge |

The matrix is updated only when implementation and tests change a status.

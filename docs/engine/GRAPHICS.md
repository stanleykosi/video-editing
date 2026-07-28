# Graphics

## Canonical Contract

Designed graphics are `GeneratorClip` timeline items, not pre-render commands or
raw React props. A clip names a registered component/version, supplies strict
properties and logical media asset references, declares transparency, and owns a
rational timeline range. The compiler converts the intersected range to exact
composition/start/duration frame counts and emits a zero-input
`MotionGraphicNode`.

The registry retains definitions by `(component_id, version)`. Component source
files are SHA-256 addressed; adding v2 does not evict projects pinned to v1.
Asset-bearing props must reference declared logical IDs. The compiler validates
the current source bytes and stages each alias under a distinct safe name.

## Remotion Bridge

The trusted TypeScript entry uses Zod to repeat validation at the process
boundary. It supports 17 built-in card, lower-third, comparison, media-frame,
PiP, split-screen, logo and CTA families. Shared canvas metrics and bounded text
fitting keep content inside horizontal, vertical, square and small diagnostic
canvases. Exact Inter font files are bundled rather than resolved from host font
fallbacks.

Remotion renders transparent ProRes 4444. The backend validates codec, alpha,
dimensions, rational frame rate, frame count and duration with FFprobe before
returning an artifact. FFmpeg then composites and delivers it like any other
canonical video layer. Range renders evaluate the original component frame
window instead of restarting animation at zero.

## Security And Caching

The runner hardcodes its entry, confines request/public/output paths to a
temporary job, rejects symlinks, verifies component and asset hashes, disallows
URL-backed media by construction, and enforces request, pixel, frame, asset and
byte limits. Browser launches are separately concurrency-limited. Multi-user or
hosted execution must additionally deny external network and isolate Chromium,
because Remotion owns an internal HTTP server and launches Chrome with its own
sandbox flags.

Render-node cache identity includes component source/version, normalized props,
asset semantics and bytes, exact range/canvas, backend versions, package lock and
browser binary. Tests prove alpha/range output, visible small-canvas typography,
safe edges, duplicate aliases, split-screen media rendering and second-run cache
reuse.

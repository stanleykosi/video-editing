# Video Typography QC

Use this checklist before exporting any edit where titles, captions, lower thirds,
graphic labels, ad text, or scene-attached typography influence comprehension.

## Required Tool Path

- Final captions are ASS subtitles from the repo caption style system.
- ASS Dialogue text uses correct escaping: intentional hard line breaks are
  single `\N` in the final `.ass` file, not double-escaped `\\N`, and no
  slash/backslash markers are visible in burned captions.
- Final title cards, hook cards, chapter cards, stat cards, lower thirds, and
  major motion-typography overlays are rendered with HyperFrames or Remotion.
- Pillow/PIL was not used for final title, caption, lower-third, hook-card, or
  chapter-card typography.
- FFmpeg drawtext is used only where it is intentionally simpler and still
  reproducible; long or premium typography chains move to ASS, HyperFrames, or
  Remotion.
- The chosen font/style is dynamic and justified by the brief, reference, style
  pack, or caption preset, not a hardcoded default.

## Approval Gate

- New or materially changed title cards, hook cards, chapter cards, stat cards,
  lower thirds, and major motion graphics have approval frames/contact sheets.
- Approval frames include reveal start, midpoint, final readable hold, and clear
  or exit state.
- The user approved the title/motion design before final compositing.
- Title copy is human, meaningful, concise, and tied to the actual clip.
- Any proposed caption suppression/no-caption window was explicitly approved by
  the user and logged.

## Font System

- Font family matches the project tone, industry, and client/reference lane.
- Continuous captions use readable type; script or display fonts are reserved for
  short emphasis or title moments.
- One primary font lane and one support/accent lane are used unless a story shift
  deliberately changes the type system.
- Any publisher-inspired typography is adapted to the project and does not copy a
  protected logo or exact identity.

## Hierarchy

- Each text moment has one clear primary word or phrase.
- Weight, color, case, and size changes emphasize impact words, not filler words.
- Support words are readable but lower priority.
- Accent colors are limited and have a meaning, category, brand, or comparison job.
- Drop shadow, stroke, glow, gradient, or blend mode improves readability or
  hierarchy instead of acting as decoration.
- Viral text effects have one named job: caption readability, emphasis, proof
  counter, depth, scene integration, or beat accent.
- Premium text masks, highlights, gradients, and glow sweeps have one readable
  path and are not being used to hide weak base typography.

## Line Structure

- Line breaks form readable phrases or complete thoughts.
- Auto-caption line breaks were manually reviewed.
- ASS line-break markup was inspected before burn-in and verified on contact
  sheets after burn-in.
- No weak filler word is isolated as the largest or final line.
- Text was shortened when line breaks could not be made readable.

## Spacing

- Tracking does not make letters collide, shimmer, or disappear.
- Large title words have no obvious awkward kerning gaps.
- Multi-line text has compact but readable line spacing.
- Spacing was checked after scale, pop, typewriter, tracking, or camera motion.
- Tight CapCut Character values such as `-1` or `-2` were tested at final size
  and not copied to small subtitles by habit.

## Layout

- Text stays inside platform and project safe areas.
- Text does not cover faces, hands, UI, products, maps, charts, source documents,
  proof details, or emotional reactions.
- Live-action text sits in negative space or is intentionally tracked to the scene.
- Captions, title text, lower thirds, proof labels, and CTA text do not collide.
- Captions remain visible through title overlays by default. If they are
  repositioned, restyled, or user-approved for suppression, that decision is
  documented.
- Typography remains readable at phone size and final delivery resolution.
- Flicker, font-shift, stretch, slide-up, perspective, and outline text resolve
  to a readable final state before the next phrase competes.
- Number counters show a verified final value, currency/unit, and final hold.
- Video-in-text, outline reveal, and text-behind-object effects have clean
  cutout, key, blend, and letter edges.
- Player 3 caption compounds remain readable after attributes are pasted across
  caption groups.
- Highlight wipes and glow sweeps start/end outside the word with no pre-glow,
  tail glow, or lingering blur.
- Foreground-lift text clears the masked object long enough to read and the mask
  edge does not chatter.

## Programmatic Typography

- HyperFrames title/card renders pass the practical project checks and point the
  EDL at the rendered output, not a placeholder.
- Remotion text effects use Sequence-local frame timing so reusable components
  start correctly at different timeline positions.
- Remotion glitch, scramble, jitter, or RGB split text uses deterministic seeds
  and renders the same frame consistently.
- FFmpeg text overlays use explicit `fontfile` paths or documented font fallback.
- Generated FFmpeg filter graphs are logged or reproducible from structured data.
- Programmatic highlight, mask, gradient, and glow effects align base and
  duplicate text layers exactly.
- Mask/glow reveals start and end off-word with no leftover sliver, pre-glow,
  tail glow, or lingering blur.
- Contact sheets include the reveal start, midpoint, final hold, and clear frame.
- Transparent text overlays have verified alpha and no black rectangle in empty
  regions.
- CSS/FFmpeg mask polarity is correct, with no unintended alpha/luminance reversal.
- Masked or glowing text edges stay clean over both bright and dark backgrounds.

## Performance And Client Work

- For ads, the product/result/offer/CTA reads faster than the styling is noticed.
- Client references are matched by style lane, not copied blindly.
- If the typography is highly stylized, a cleaner readability-first variant is
  considered for performance-led content.

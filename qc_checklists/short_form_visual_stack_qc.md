# Short-Form Visual Stack QC

Use this checklist before exporting a high-energy Short, Reel, or TikTok-style edit.

## Hook

- Viewer can understand the main claim within the first five seconds.
- First 3-5 seconds contain motion, proof, face, or another clear retention reason.
- Any opening dynamic zoom preserves face, proof, captions, product, and action.
- Hook claim is supported by the payoff or proof later in the short.
- Opening audio starts cleanly and the claim is not masked by music or SFX.
- First caption, text, or proof frame is readable at phone size.
- The hook does not rely on unsupported controversy or exaggerated proof.
- Designed hook text has one clear keyword or phrase priority.
- Ordinary captions are removed or simplified when hook text already carries the same words.

## Pacing

- Sentences are short and setup that does not support the claim is removed.
- Dead air over 300 ms is removed unless it creates tension, humor, or comprehension value.
- High-energy hook is followed by at least one readable rest beat when the intro is visually dense.
- Effects return on important statements rather than every sentence.
- Body visuals are chosen by line importance: simple talking head, filler card, B-roll text, or full-screen animation.
- Full-screen animations are reserved for high-value concepts, transitions, or payoff lines.
- AE-heavy edits have a segment ideation pass before animation begins.
- Scripted edits use visual tags so each asset or animation maps to a spoken beat.
- Pauses are removed only when they are dead air, not when they carry story, joke timing, or comprehension.
- Slow sections have a named connection, proof, emotion, or comprehension purpose.
- Human pattern interrupts exit before the main story loses momentum.
- Short-form black/drop gaps stay under one second unless intentionally cinematic.

## Motion And Visuals

- Speaker stays centered during manual tracking.
- Automatic face/body/hand or sticker tracking stays locked without drift, jitter,
  or caption collisions.
- Statement zooms are used for important lines only.
- Zooms preserve face, hands, captions, and proof visuals.
- Visual stack elements appear in sync with the spoken concept.
- Text, icons, stock footage, captions, and background texture have a clear hierarchy.
- No asset implies something unsupported or off-brand.
- B-roll text treatment preserves visible proof, action, and story detail after dimming or desaturation.
- Adjustment-layer zooms affect only intended sections and keep captions, faces, UI, products, and proof safe.
- Eye-locked AE zooms keep the speaker's eyes stable through scale/position changes.
- Original footage and rotoscope/cutout duplicates share intended motion.
- Camera/null moves do not reveal background edges.
- Path/counter animations reach a readable final value or endpoint before the segment changes.
- Track-matte textures keep the original subject recognizable.
- Elements clear with an out animation or motivated overlay transition.
- Fonts, colors, icons, backgrounds, and textures follow one editing signature.
- Text pop scale overshoots settle before the viewer needs to read the phrase.
- Typography has one clear impact word or phrase per text moment.
- Viral text effects are reserved for selected emphasis, proof, or depth moments,
  not every line.
- Flicker, font-shift, stretch, slide-up, perspective, and outline text resolve
  to readable final states.
- Player 3 caption compounds, highlight wipes, gradient type, staggered blur
  reveals, foreground-lift text, and glow sweeps preserve readable final states.
- Number counters show a verified final value and hold long enough to read.
- Hook, proof, and CTA text use phrase-based line breaks instead of random auto-wrap.
- Live-action or B-roll text sits in negative space and does not cover the subject, product, UI, or proof.
- Subject-sandwich text remains readable after the foreground cutout passes.
- Video-in-text, outline reveal, and text-behind-object effects keep clean
  cutout/key/blend edges at phone size.
- Highlight wipes and glow sweeps start/end off-word with no glow leak or
  lingering blur.
- Programmatic text effects use logged component/filter metadata, available fonts,
  deterministic seeds, and contact sheets around reveal states.
- FFmpeg word-by-word text chains are kept short enough to debug or moved to
  ASS/Remotion before final.
- Transparent text or motion overlays have verified alpha and do not render as
  black rectangles over footage.
- Alpha-mask reveals are previewed at start, midpoint, hold, and clear frames
  before they are used in the final short.
- Slide-on photo stacks use planned negative space and clear before the next beat.
- Chapter cards mark a real section reset and do not slow the next useful line.
- PiP borders and green-screen VFX avoid captions, UI, products, proof, and active
  action.
- Texture overlays have named jobs and remain readable through their brightest frames.
- Long simple dynamic zooms stay crop-safe and do not drift away from the intended human or proof focus.
- Paper/grid backgrounds stay subordinate to foreground text, maps, charts, and evidence.
- Map routes, document highlights, chart bars, and screenshot focus strips finish their reveal before the next claim depends on them.
- Low-FPS or FPS Lag texture is bypassed where it makes labels, captions, charts, or source text unreadable.

## Sound

- Whooshes, hits, and reverse hits land within 1-2 frames of their intended movement or reveal.
- Whooshes start low enough that dialogue remains dominant.
- Repeated SFX use variation.
- Background music supports pace without masking speech.
- Music candidates were auditioned under the finished short and chosen for tone fit, not trend status alone.
- Track license/platform status is documented or marked temp-only.
- App-library, downloaded, or screen-recorded audio is licensed/platform-safe or
  marked temp-only.
- SFX are placed against the final visible motion render, not an earlier animation placeholder.
- Required dialogue, music, and SFX tracks are unmuted in the final export range.
- Isolated SFX passes are followed by restored full-mix checks.
- Foley matches visible or strongly implied movement and stays below dialogue.
- Contrast drops follow a visible or audible build and re-enter dialogue cleanly.
- Infographic SFX cue meaningful reveals, highlights, swaps, or route movement rather than every layer.
- Text ticks/clicks land on visible flicker, font-shift, counter, or reveal
  frames and end with the animation.
- Glitch or shimmer cues for staggered, highlight, or glow text reveals end with
  the visible effect and stay below speech.

## Captions

- Captions are readable at phone size.
- One- or two-word chunks are used only where they improve pace and readability.
- Auto-caption wording, timing, line breaks, and emphasis are corrected.
- Unneeded captions are removed where visual text already explains the idea.
- Captions do not cover faces, hands, visual text, proof, or transition objects.
- Premiere one-word captions were corrected before being upgraded to graphics.
- Pop-fade caption motion finishes before the spoken word needs to be read.
- Captions fade or clear before dense AE text, counters, paths, icons, or CTA words need the same screen space.
- Captions, center text, and scene-attached text do not duplicate each other without a clear hierarchy or accessibility reason.
- Organic low-focus captions remain readable while letting faces, proof, and reactions stay primary.
- Captions avoid map labels, chart values, document highlights, screenshot focus areas, and title hierarchy.
- Caption emphasis lands on meaning-changing words, not filler words isolated by auto-captioning.
- Caption tracking, line spacing, gradients, shadows, and accent colors remain readable at phone size.
- CapCut adaptive caption animations are applied only after auto-caption wording,
  timing, and line breaks are corrected.
- CapCut Player 3 caption compounds are applied only after auto-caption wording,
  timing, line breaks, and phrase grouping are corrected.
- Remotion or FFmpeg animated caption groups are generated from corrected phrase
  timing, not raw auto-caption output.

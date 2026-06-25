# Lesson: Video Typography Core Principles

## Source

- Tutorial: `Typography`
- Notes: `transcripts/typography.txt`
- Related cards:
  - `technique_cards/typography_font_family_role_selection_001.json`
  - `technique_cards/typography_contrast_hierarchy_stack_001.json`
  - `technique_cards/typography_sentence_structure_line_breaks_001.json`
  - `technique_cards/typography_live_action_whitespace_integration_001.json`
  - `technique_cards/typography_tracking_kerning_line_spacing_qc_001.json`
  - `technique_cards/typography_roi_readability_ad_text_001.json`

## What The Tutorial Teaches

Typography is part of the edit's communication system, not decoration added after
the cut. Type choices influence story tone, brand read, attention, and whether the
viewer understands the intended word first.

The core typography decisions are:

- Choose font families by role and tone: serif for historical/editorial/documentary
  gravity, sans serif for clean modern utility, script for handwritten or expressive
  accents, and display for bold headlines or poster-like emphasis.
- Build hierarchy through contrast: weight, color/hue, mixed case, size, and the
  controlled combination of those choices.
- Highlight the word that creates impact in the line, not filler words.
- Break lines by human phrase logic so each line reads like a complete thought.
- Use tracking, kerning, and line spacing as finishing controls after the text is
  already readable.
- Place text in negative space or a tracked scene area so it belongs to the image
  instead of feeling pasted on.
- For ads and performance-led content, clean readable text normally beats fancy
  typography that slows comprehension.

## Agent Decision Rules

- Start from the video's purpose: documentary, tech, ad, cinematic, music video,
  comedy, educational, or social-retention short.
- Pick one primary type family and one support family before designing text motion.
- Give one word or phrase the highest hierarchy per text moment.
- Use size, weight, case, and color only when they communicate priority.
- Keep accent colors limited; use neutral text for support words unless the scene
  has a clear positive/negative or before/after comparison.
- Use script or display fonts sparingly because expressive type often trades away
  readability.
- In live-action scenes, match type color temperature to the frame and place text
  in negative space, not over faces, lamps, products, or evidence.
- Use drop shadow only as a functional readability aid. If contrast already works,
  a heavy default shadow usually makes the design feel cheaper.

## Timeline Patterns

- Font system: `project tone -> choose family role -> choose primary/support font -> apply to title/caption/hook -> phone-size test -> lock style`.
- Hierarchy stack: `spoken line -> choose impact word -> base text -> weight contrast -> optional hue/case/size contrast -> line-break check -> collision check`.
- Caption line structure: `transcript chunk -> phrase break -> one/two-line layout -> safe placement -> timing -> phone-size read`.
- Live-action integration: `shot scan -> find negative space -> choose matching type tone -> match temperature -> optional track -> read hold -> clear`.
- Ad readability: `product/result claim -> reference style -> clean text layout -> CTA/proof priority -> readability and ROI check`.

## Implementation Notes

- ffmpeg: use `drawtext` only after the hierarchy and line breaks are planned. For
  complex font pairing or composite-mode effects, pre-render text assets from a
  design tool, Remotion, AE, or Blender and then overlay them.
- Remotion: store typography as structured style tokens: `fontFamilyRole`,
  `primaryFont`, `supportFont`, `impactWords`, `caseMode`, `tracking`, `lineHeight`,
  `accentColor`, `safeRegion`, and `duplicateCaptionPolicy`.
- Blender: use text objects for scene-attached or cinematic title work, with camera
  and tracking only when the text should belong to the shot's space.
- CapCut: use text styles and templates as drafts, then manually check family,
  hierarchy, tracking, negative-space placement, and collision.
- Premiere/After Effects: use Essential Graphics or AE text animators for style
  systems; save presets only after testing multiple phrase lengths and backgrounds.

## Mistakes And QC

- No hierarchy: every word has the same size, case, weight, and color.
- Random font switching: type families change without a brand, tone, or story reason.
- Low readability: gradients, script fonts, display fonts, shadows, or blend modes
  make the text harder to read than plain type.
- Bad line breaks: words wrap randomly instead of forming readable phrases.
- Poor placement: text covers faces, product, UI, evidence, or the shot's emotional
  focal point.
- Over-styling ads: typography looks creative but slows the product/result claim.
- Missing QC: text was checked in the desktop viewer but not at phone size.

# Color Grading

## Purpose

Guide correction, look design, shot matching, and delivery-safe color choices.

## When To Use This Skill

- Matching shots from different sources.
- Creating a genre look.
- Fixing exposure, contrast, white balance, saturation, or skin tones.
- Preparing talking-head footage before an After Effects Reel animation pass.
- Checking whether color choices keep captions, icons, overlays, and proof readable.
- Applying basic correction after a scripted viral-style edit is structurally stable.
- Creating warm hopeful or nostalgic looks for slower human short-form sections.
- Designing warm paper/editorial palettes for documentary maps, charts, documents, and explainer graphics.
- Checking typography contrast, gradients, shadows, and live-action text temperature.
- Building DaVinci Resolve color-managed primary correction, hero-still shot
  matching, timeline looks, and tracked secondaries.
- Building motivated keyframed saturation shifts such as color-to-black-and-white transitions.
- Building filter-strength reveals that rise with music after speech while
  preserving readability.
- Unifying still-image composites where fire, sky, glow, reflection, and base
  image layers need to feel like one low-key scene.
- Creating archival film-frame treatments and filmed-screen texture looks while
  preserving source evidence.

## Core Principles

- Correct before stylizing.
- Protect faces, product colors, brand colors, and important detail.
- Use a look to support genre and emotion.
- Check grade consistency across the whole sequence, not just one hero frame.
- Keep correction subtle before AE roundtrips so skin, edges, and textures do not become brittle.
- Brand colors can make a Reel feel premium, but they must not reduce text/icon contrast.
- Color polish should support the chosen style lane without hiding the message, proof, or text.
- Warm emotional grades should make a hopeful section feel human without making skin orange, proof muddy, or captions soft.
- Editorial graphics can be warm and analog, but data, maps, source text, and labels remain the priority.
- Typography color is a readability decision before it is a style decision.
- Live-action text should usually match the frame's warm/cool temperature while maintaining contrast.
- In Resolve, use clip nodes for shot-level correction and timeline nodes for
  whole-timeline looks; scopes and stills keep the grade from drifting.
- Keyframed color shifts should have a story, mood, memory, contrast, or reveal purpose; avoid random filter movement.
- Filter-strength keyframes should usually animate one clear amount control
  rather than several unrelated color controls unless each property has a named
  job.
- In composites, match individual layer exposure and color before using a global
  filter or glow to glue the scene together.
- Archival or old-media looks should clarify source type; never use aging to make
  generated, reconstructed, or current footage seem like real historical proof.

## Techniques

- `knowledge/techniques/nle_workflow/nle_fourk_to_1080_reel_prep_001.json`
- `knowledge/techniques/retention/retention_audience_style_idea_gate_001.json`
- `knowledge/techniques/color/color_warm_nostalgic_hope_grade_001.json`
- `knowledge/techniques/motion/motion_vox_paper_grid_background_001.json`
- `knowledge/techniques/typography/typography_contrast_hierarchy_stack_001.json`
- `knowledge/techniques/typography/typography_live_action_whitespace_integration_001.json`
- `knowledge/techniques/color/davinci_color_management_primary_look_001.json`
- `knowledge/techniques/color/davinci_color_hero_still_shot_matching_001.json`
- `knowledge/techniques/color/davinci_color_secondary_windows_qualifier_tracker_001.json`
- `knowledge/techniques/color/color_keyframed_saturation_shift_001.json`
- `knowledge/techniques/color/color_filter_strength_music_reveal_001.json`
- `knowledge/techniques/color/color_low_key_firelight_scene_unification_001.json`
- `knowledge/techniques/color/color_archival_film_frame_treatment_001.json`
- Add future cards for neutral correction, teal-orange split, bleach bypass, anime contrast, and low-key drama.

## Timing Rules

- Apply basic correction after the talking-head rough cut is stable and before exporting a prepared AE render.
- Save heavy look design until the edit timing is stable enough that renders will not churn.
- Check color and contrast again after overlays, captions, backgrounds, and animated textures are visible.
- In scripted YouTube workflows, do basic correction after the rough visual pass is stable enough that repeated clip-level changes will not churn.
- Apply warm nostalgic looks only after the chosen slow-human section timing is stable.
- Apply paper/grid warmth before final graphic QC, then recheck every foreground label and data point.
- Check text color and contrast again after gradients, shadows, blend modes, vignettes, or warmth are applied.
- Use a hero still for scene matching and compare related shots to that constant
  reference instead of drifting from shot to shot.
- For keyframed saturation shifts, choose closer keyframes for sudden impact and wider keyframes for gradual mood change, then hold or restore intentionally.
- For filter-strength music reveals, start neutral, raise the look after speech
  clears, and align or intentionally offset the strength rise from the music
  restore.
- For still-image composites, finish layer placement and mask feathering before
  judging the final low-key warmth or glow.
- Apply archival film frames, particles, fade, and desaturation after the source
  role and caption/source-label placement are clear.

## Motion Rules

- Color has no direct motion rule, but zooms, rotoscoped cutouts, and textured backgrounds must preserve clean edges and readable detail.
- Avoid pairing a saturation shift with extra motion unless both support the same beat.
- Flickering local light should be isolated from the global grade so the whole
  scene does not pulse accidentally.

## Sound Rules

- No direct sound rule.

## Caption Rules

- Caption contrast must hold over both corrected footage and animated backgrounds.
- Do not let glows, gradients, noise, grids, or vignettes make caption edges muddy.
- Typography should be tested on bright, dark, warm, and cool representative frames.
- In firelight composites, captions must be checked on both the darkest base
  frame and the brightest glow frame.

## Color Rules

- No crushed important shadows or clipped highlights unless intentional.
- Skin tones and brand/product colors remain believable.
- The grade does not introduce banding, flicker, or compression ugliness.
- Subtle talking-head correction can start with exposure, contrast, highlights, shadows, whites, and a restrained vignette.
- Compare corrected and uncorrected frames before extending the correction across the prepared sequence.
- In Premiere, clip-level Lumetri for exposure, contrast, and saturation can be enough when the goal is clean viral-style polish rather than a heavy look.
- Warm hopeful looks can use glow, gradient, subtle grain, radial blur, and vignette only after skin, proof, and caption readability are protected.
- Preserve useful cool background context when warming the subject; the whole frame does not need to become orange.
- Editorial warm paper palettes should use restrained off-white/gray/yellow/red accents and avoid muddy low-contrast combinations.
- Accent typography color should mark priority, category, brand, or comparison; avoid color changes without meaning.
- Drop shadows and strokes are acceptable only when they improve readability over the grade.
- Resolve secondaries should start from a corrected primary; windows, qualifiers,
  and tracked masks should remain subtle enough that edges do not reveal themselves.
- A strong creative look can be built before final matching when the look changes
  how shot differences read, but preserve faces, proof, and captions.
- CapCut-style black-and-white shifts can start by keyframing saturation down strongly, then adjusting for skin, product, proof, and caption readability.
- Filter-strength reveals can start at `0` and rise toward the approved final
  amount, often full strength, only if captions, faces, proof, UI, product, and
  brand colors remain readable.
- Low-key firelight composites can lower exposure or shadows and add warm tint,
  contrast, highlight control, and subtle glow only after the overlay layers
  already match the base still.
- Archival treatments can start with moderate desaturation, slight contrast lift,
  film framing, and particles/fade around 50 in CapCut, then reduce until faces,
  dates, source text, and captions remain readable.
- Glass or filmed-screen texture grades should be lowered when UI or source text
  becomes harder to inspect.

## Tool Implementation Notes

- Premiere: use an adjustment layer with Lumetri for basic correction before exporting the prepared AE render.
- After Effects: check that imported prepared footage still matches any backgrounds, icons, and overlays after texture effects are enabled.
- Remotion: store correction and style tokens separately so footage correction does not become mixed with brand background styling.
- ffmpeg: use contact sheets and histograms/scopes where useful to catch clipped highlights, crushed shadows, and banding.
- CapCut: apply correction lightly and preview captions/overlays at phone size after the look is applied.
- Premiere: after text, overlays, and SFX are in place, check that Lumetri correction still leaves captions and texture overlays readable.
- DaVinci/Premiere: compare the warm look against a neutral base frame and check phone-size captions before approving glow, grain, blur, or vignette.
- CapCut/Remotion/Premiere: render stills of maps, charts, documents, and screenshot highlights after warmth/texture is applied.
- For typography-heavy scenes, render stills with text over actual footage and compare plain, shadowed, gradient, and accent-color variants.
- DaVinci Resolve: use color management or explicit input transforms for log or
  wide-gamut footage, parade/vectorscope for objective checks, stills for shot
  matching, and tracked windows/qualifiers for subtle secondaries.
- For keyframed saturation shifts, store startFrame, endFrame, startSaturation, endSaturation, restoreFrame, and readability check frames.
- For filter-strength reveals, store neutralFrame, fullLookFrame, finalStrength,
  musicRestoreFrame, speechClearFrame, and readability check frames.
- For still-image composite grades, store per-layer correction, final adjustment
  values, brightest/darkest review frames, and caption contrast check frames.
- For archival treatments, store sourceType, frameAsset, saturation, contrast,
  particles/noise, fade/vignette, source label, and generated/reconstructed flags.

## Common Mistakes

- Overgrading a talking-head Reel before animation and making skin or cutout edges look harsh.
- Using random background or accent colors that clash with the editing signature.
- Adding vignette, noise, glow, or grid texture until text contrast drops.
- Extending a correction across the sequence without comparing corrected and original frames.
- Correcting color before the rough cut is stable and then redoing work after script/asset changes.
- Making a hopeful section look orange, muddy, or overly digital.
- Adding glow, grain, radial blur, or vignette until proof and captions lose clarity.
- Letting a warm paper palette hide chart values, map labels, route lines, or source text.
- Using accent colors that imply unsupported urgency or hierarchy.
- Matching a live-action text color so closely to the frame temperature that the word disappears.
- Keeping a heavy shadow or gradient because it looks premium while readability drops.
- Matching shots only to the previous shot and letting the scene drift away from
  the intended reference.
- Applying harsh secondaries or qualifiers that create halos, patches, or edge chatter.
- Using a saturation shift because it looks dramatic when no story beat changes.
- Using a filter-strength ramp as energy polish when the edit still lacks a
  clear visual or story reason for the look change.
- Forgetting to restore color after the memory, failure, or contrast beat ends.
- Using a warm/glow filter to hide bad overlay alignment or hard mask edges.
- Crushing shadows in a night composite until architecture, faces, captions, or
  proof disappear.
- Applying archival style to current proof footage and confusing the viewer about
  source age.
- Using particles, fade, or film borders to hide source labels, faces, dates, or
  generated-image status.

## QC Checklist

- Skin, eyes, product colors, and brand colors still look believable.
- Highlights and shadows preserve the detail needed for faces, proof, and cutouts.
- Captions, icons, counters, paths, and overlays remain readable over the final look.
- Texture and vignette effects do not create compression dirt or banding.
- The prepared AE render has the intended correction and does not need emergency color repair after animation.
- Viral-style overlays and text remain readable after exposure, contrast, and saturation changes.
- Warm nostalgic grades preserve believable skin, readable proof, caption contrast, and clean compression.
- Editorial paper palettes preserve foreground text/data contrast and compression cleanliness.
- Typography remains readable on the final graded frame, not only the ungraded source.
- Accent, gradient, shadow, and blend-mode text choices preserve crisp edges at delivery size.
- Resolve color management, hero still matching, timeline look nodes, and tracked
  secondaries preserve faces, proof, captions, and compression cleanliness.
- Keyframed saturation shifts preserve faces, proof, products, brand colors, and captions through the full transition.
- Filter-strength reveals preserve faces, proof, UI, products, brand colors, and
  captions at both neutral and full-look frames.
- Color is restored or held intentionally after the shift.
- Still-image fire/sky/reflection layers match the base in exposure, temperature,
  contrast, and highlight control.
- Low-key composite shadows preserve the details the viewer still needs.
- Archival treatments preserve source context, labels, dates, faces, and caption
  contrast.

## Source Lessons Added

- 2026-05-28: `Edit High Quality Reel`
- 2026-05-29: `Editing Viral Videos`
- 2026-05-29: `Slow Editing`
- 2026-05-29: `Vox Style Documentary`
- 2026-05-29: `Typography`
- 2026-05-29: `DaVinci Resolve Full Tutorial`
- 2026-05-29: `CapCut Keyframes`
- 2026-05-29: `Still Image To Media`
- 2026-05-29: `Documentary Edits`
- 2026-05-29: `Keyframe Pro Edits`

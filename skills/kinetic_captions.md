# Kinetic Captions

## Purpose

Guide caption design, chunking, animation, emphasis, subtitles, and readability.

## When To Use This Skill

- Burning subtitles into short-form or social edits.
- Adding emphasis words, pop captions, karaoke highlights, or animated captions.
- Designing captions for silent autoplay.
- Repairing comprehension when documentary audio is hard to hear.
- Choosing between subtitles, lower thirds, and other on-screen text.
- Reviewing auto-captions from AI short-form or repurposing tools.
- Creating short, high-energy social subtitles from a transcript pass.
- Building Premiere one-word captions and pop-fade caption graphics for Reels.
- Creating Resolve Text+ premium caption stacks and styling Resolve auto captions.
- Finishing captions over an After Effects animation render where some segments already contain animated text.
- Choosing between captions, center/emphasis text, and scene-attached text in scripted YouTube edits.
- Designing restrained captions for warm human shorts where subtitles should not feel overly digital.
- Applying typography hierarchy, font-family, line-break, and spacing rules to captions or emphasis text.
- Designing brand, proof, and outcome intro text that replaces ordinary captions during a formal bumper.
- Creating ASS caption styles that continue cleanly through HyperFrames/Remotion
  title graphics.
- Designing CapCut adaptive caption animations and deciding when viral text
  effects should stay separate from, reposition, or become an explicitly approved
  replacement for ordinary captions.
- Applying CapCut Player 3 to corrected caption compounds for a smoother premium
  caption treatment.
- Building programmatic Remotion or FFmpeg caption-emphasis effects such as
  word staggers, pop words, fade envelopes, and short word-by-word overlays.

## Core Principles

- Chunk captions by meaning and breath, not arbitrary word counts.
- Emphasize the word that changes the meaning of the sentence.
- Story comprehension beats decorative labels.
- If a line is hard to hear and important, subtitle it even if that means dropping a lower third.
- Caption style should match subject tone; serious testimony should not look like a meme caption.
- Place captions around faces, hands, products, maps, evidence, and action.
- Use stroke, drop shadow, backing boxes, or repositioning when footage makes text hard to read.
- Captions should not compete with title text, proof cards, overlays, or the main action.
- Auto-captions need human review for wording, emphasis, line breaks, timing, and filler-word clutter.
- One- or two-word subtitle chunks can increase speed and emphasis in social edits when they remain readable.
- Captioned final renders require an ASS caption layer. Designed visual text can
  add emphasis, but it does not remove captions by default.
- Convert captions to graphics only after timing, wording, and line breaks are correct.
- One-word social captions are a style choice, not a default; use them only when they improve pace and remain readable.
- In Resolve, auto captions are a speed layer; Text+ is the premium emphasis layer for selected moments.
- Text+ gradients, glow, blur, glitch, and Stop Motion must preserve legibility.
- High-quality Reel captions can use slightly fuller single-line chunks around 10-15 characters when one-word chunks would feel too fragmented.
- Captions should be designed after the AE render is visible so dense animation sections can be faded, repositioned, restyled, or explicitly approved for suppression.
- Constant pop text can become irritating; emphasize only the lines that need visual priority.
- Scene-attached text should look anchored to the screen, wall, object, or background it belongs to.
- Organic human shorts can use simple static captions or soft fades when kinetic presets would steal focus from faces and proof.
- Caption typography should highlight the word that changes meaning, not filler words.
- Auto-caption line breaks are drafts; final captions should break by phrase, breath, and screen safety.
- Script and display fonts are accents, not default subtitle fonts.
- Tracking, kerning, and line spacing are finishing controls after readability and placement are already solved.
- Designed intro text can replace ordinary captions when it clearly communicates brand identity, proof or authority, and viewer outcome.
- In intro bumpers, text roles matter more than text quantity: brand, proof, outcome, and accent should not compete equally.
- Adaptive caption texture and viral text effects are not accessibility passes;
  use them only after caption wording, timing, line breaks, and placement are
  correct.
- Compound caption effects should be applied only after the phrase split is
  readable; pasting attributes is a speed step, not a QC substitute.
- Programmatic caption motion should be generated from corrected caption timing
  and phrase data, not from unreviewed auto-caption output.
- If animated caption-emphasis text is exported as a reusable overlay, alpha
  quality becomes part of caption readability: no black boxes, haloed edges, or
  chroma-key cleanup should be needed.

## Professional Caption Rules

- Use ASS subtitles from the repo caption preset system for all captioned final
  renders.
- ASS hard line breaks must be correct in the written file: use a single `\N`
  control sequence, not a double-escaped `\\N`, and never ship visible
  slash/backslash markers in burned captions.
- Do not render final captions with Pillow/PIL image text or a hardcoded one-font
  overlay.
- Caption style must be chosen or adapted dynamically from the active style pack,
  caption presets, reference video, and content tone.
- Keep captions visible through title cards and motion graphics by default.
  Reposition, resize, restyle, or shift safe regions before considering
  suppression.
- Suppress captions only when the user explicitly approves a suppression/no-
  caption window and the designed title text clearly preserves the spoken meaning.
- HyperFrames/Remotion title graphics are not substitutes for the ASS caption
  layer unless the user approves that exact exception.

## Techniques

- `technique_cards/documentary_audio_intelligibility_001.json`
- `technique_cards/motion_overlay_readability_focus_stack_001.json`
- `technique_cards/podcast_ai_shorts_review_refine_001.json`
- `technique_cards/sound_audio_leveling_track_hygiene_001.json`
- `technique_cards/captions_two_word_social_subtitles_001.json`
- `technique_cards/captions_premiere_one_word_pop_fade_001.json`
- `technique_cards/retention_hook_text_design_sequence_001.json`
- `technique_cards/motion_show_dont_tell_visual_stack_001.json`
- `technique_cards/davinci_textplus_premium_caption_stack_001.json`
- `technique_cards/davinci_vertical_short_project_setup_001.json`
- `technique_cards/aftereffects_text_animation_preset_stack_001.json`
- `technique_cards/premiere_aftereffects_render_finish_roundtrip_001.json`
- `technique_cards/motion_premiere_text_pop_scale_preset_001.json`
- `technique_cards/motion_sketch_to_animation_ladder_001.json`
- `technique_cards/captions_organic_low_focus_social_subtitles_001.json`
- `technique_cards/typography_font_family_role_selection_001.json`
- `technique_cards/typography_contrast_hierarchy_stack_001.json`
- `technique_cards/typography_sentence_structure_line_breaks_001.json`
- `technique_cards/typography_tracking_kerning_line_spacing_qc_001.json`
- `technique_cards/retention_brand_authority_outcome_intro_001.json`
- `technique_cards/motion_premium_intro_text_logo_flicker_001.json`
- `technique_cards/captions_capcut_adaptive_texture_animation_001.json`
- `technique_cards/captions_capcut_player3_smooth_caption_compounds_001.json`
- `technique_cards/typography_capcut_apple_slide_up_text_001.json`
- `technique_cards/typography_capcut_opacity_flicker_tick_001.json`
- `technique_cards/typography_capcut_font_shift_loop_001.json`
- `technique_cards/typography_capcut_srt_number_countup_001.json`
- `technique_cards/typography_remotion_stagger_spring_text_motion_001.json`
- `technique_cards/typography_ffmpeg_fade_pop_envelope_001.json`
- `technique_cards/typography_ffmpeg_sequential_word_drawtext_001.json`
- `technique_cards/programmatic_remotion_css_mask_text_reveal_001.json`
- `technique_cards/programmatic_remotion_prores4444_alpha_overlay_export_001.json`
- Add future cards for pop captions, karaoke highlights, bounce emphasis, and two-line social captions.

## Timing Rules

- Caption animation should finish in time for the spoken word, not after it.
- Hard-to-hear documentary lines should appear exactly when the line is needed.
- Do not animate captions during a quiet emotional hold if the text distracts from the face.
- Caption motion should finish before the spoken word needs to be read.
- For shorts, remove filler-word caption emphasis when it distracts from the core point.
- Keep rapid social caption chunks short enough to follow fast speech; around 1-2 words per chunk is useful when the style is energetic.
- Avoid keeping a short caption onscreen past about 2 seconds in rapid social style unless the speech slows down.
- Resolve Text+ staggered stacks can use very short layers for emphasis, but each layer must remain readable.
- Premiere pop-fade captions should complete their entrance before the spoken word needs to be read.
- Use one-word chunks inside rapid social sequences; switch back to longer chunks when meaning becomes too fragmented.
- Fade captions out before dense animation or visual text replaces them; avoid harsh on/off caption cuts.
- Text pop overshoots should settle before the viewer needs to read the phrase.
- Organic low-focus captions can use 3-6 frame fades when hard on/off caption cuts distract from a warm human moment.
- Correct caption line breaks and hierarchy before applying pop, fade, typewriter, or Text+ animation.
- Expressive display/script caption moments need extra read time compared with plain sans captions.
- Intro flicker or font-change accents should stay in short 3-9 frame bursts and leave the final brand/proof/outcome words readable.
- Social intro text should usually complete within 3-5 seconds; long-form/show intro text should usually complete within 10-15 seconds.
- CapCut adaptive caption animation should finish before the spoken word needs to
  be read, and the caption must still read over changing backgrounds.
- Player 3 smooth caption compounds should be trimmed to the spoken phrase and
  reviewed after pasted attributes.
- Flicker and font-shift accents should return to a stable readable word before
  the next caption or phrase competes.
- Number counters should hold their verified final value long enough to read.
- Remotion word staggers and spring pops should settle before the spoken phrase
  needs to be read.
- FFmpeg word-by-word windows should match transcript timing; switch to phrase
  chunks when one-word timing makes comprehension worse.
- Masked caption-emphasis reveals should finish before the viewer needs the full
  phrase; reserve wave/liquid masks for short emphasis words, not accessibility captions.

## Motion Rules

- Keep caption motion short enough that text can still be read.
- Use stable subtitles for sensitive testimony or poor audio.
- Avoid animated captions that compete with movement continuity or focal-point guidance.
- Keep captions stable when overlays, zooms, or reframes are already directing attention.
- Do not animate captions heavily at the same time as a subject-tracking move, icon pop, or transition object unless the style intentionally demands it.
- Keep Text+ motion secondary to the spoken point and caption readability.
- Position-and-opacity caption pops should be short, readable, and less important than the spoken line.
- Hook text design can sit above the ASS caption system during the hook; it should
  not replace captions unless the user approved that exception.
- AE animated text should be treated as a separate visual hierarchy layer, not duplicated by ordinary captions unless accessibility requires it.
- Center/emphasis text should be reserved for ideas captions cannot make prominent enough.
- Keep caption motion minimal when a human reaction, proof artifact, or slow zoom is already the focus.
- Animate the impact word only when the motion helps the viewer understand the line priority.
- Treat intro brand/proof/outcome text as designed graphic text, not automatic transcript captions.
- Treat Apple-style slide-up words, axis stretch, flicker, font shift, counters,
  and video-in-text as designed text layers; keep ordinary captions visible or
  repositioned unless the user approved suppression.
- Treat Player 3 caption compounds as styled caption groups, not raw subtitles;
  fall back to stable captions when motion makes the line harder to read.
- Treat Remotion/FFmpeg animated caption groups as designed text layers that need
  the same duplicate-caption and safe-region decisions as CapCut compounds.
- Treat transparent caption overlays as final render assets: verify alpha,
  duration, fps, safe region, and edge readability before importing them over footage.

## Sound Rules

- Captions supplement audio repair; they do not excuse inaudible dialogue.
- If music/SFX masks speech, fix the mix before relying on captions.
- Repair quiet words before expecting captions to carry the hook or payoff.
- Ticking SFX used with caption-like text effects must stay below speech and end
  with the visual change.

## Caption Rules

- Captions are readable at phone size.
- Captions do not cover important faces, UI, products, maps, evidence, or action.
- Subtitles for critical speech take priority over lower thirds and character intro graphics.
- Caption placement should not pull the viewer away from the next key visual point.
- Captions should not cover title text, cards, speaker faces, product/UI proof, or small action being discussed.
- Captions, lower thirds, and overlays must be checked together as one layout.
- Keep captions through visual text by default; if visual text, icons, or stock
  footage duplicate the spoken concept, reposition or simplify captions before
  requesting an explicit suppression exception.
- Prefer single-line captions when the frame already contains visual-stack text.
- Resolve Text+ stacks should not duplicate the same words as auto captions unless the duplicate is intentional emphasis.
- For Premiere one-word captions, check short line settings, clean sans styling, lower-third placement, and phone-readable size before saving a style.
- Do not remove ordinary captions under hook text, B-roll text, or full-screen
  hierarchy text unless the user approved that suppression and the designed text
  carries the same spoken meaning.
- For high-quality Reels, keep captions single-line when possible and review 10-15 character chunks against animated text, counters, icons, and faces.
- Use captions for comprehension, center text for emphasis, and scene-attached text for integration with the visual world.
- Restrained caption styling still needs phone-size readability, corrected text, and safe placement.
- Use readable serif or sans fonts for continuous subtitles; reserve script/display fonts for short title or emphasis words.
- Break captions into phrase-complete lines so the viewer does not have to rebuild the sentence.
- Sentence case, mixed case, all caps, and size changes should follow meaning and tone.
- Slightly tightened tracking can work on large emphasis words, but subtitle-sized captions should stay near normal spacing unless QC proves otherwise.
- During formal intros, keep captions visible or repositioned when possible. If
  designed brand/proof/outcome text duplicates the line, suppression still
  requires user approval.
- During viral text effects, remove or reposition ordinary captions if they
  duplicate or collide with the designed text only after user approval; otherwise
  reposition or restyle them and restore normal placement after the effect clears.
- Player 3 or other CapCut effects are applied after auto-caption wording, timing,
  line breaks, and phrase groupings are manually corrected.

## Color Rules

- Caption contrast should remain readable over both bright and dark footage.
- Serious documentary captions should use restrained styling unless the project asks for social-caption energy.
- For shorts, test caption color and stroke against at least one bright frame and one dark frame.
- Highlight color should emphasize meaning-changing words, not random words.
- Gradient captions must preserve contrast over both bright and dark footage.
- Low-focus captions should fit the warm palette while remaining readable over both bright and dark frames.
- Drop shadow, stroke, glow, or backing should solve readability; avoid heavy default shadows when plain contrast already works.
- Limit accent colors in one caption system so color means priority, brand, or comparison instead of noise.

## Tool Implementation Notes

- ASS: use the repo caption style presets for final captioned renders and apply
  them last in the render chain. Inspect Dialogue text for double-escaped
  `\\N` before burn-in; the final file should contain single `\N` hard breaks,
  and contact sheets should show clean line breaks with no slash artifacts.
- HyperFrames/Remotion: title, hook, lower-third, and motion graphic overlays must
  declare how captions remain readable through their window.
- Pillow/PIL: do not use for final caption typography; it is allowed only for
  diagnostics, masks, contact sheets, placeholders, or non-typographic helper
  assets.
- For ffmpeg, burn subtitles after overlays and verify placement on contact sheets.
- For Remotion, separate subtitle layers from lower-third components so one can be disabled when they conflict.
- For CapCut/Premiere, manually inspect hard-to-hear lines and remove lower thirds if they block subtitles.
- For AI short workflows, review every generated caption and remove distracting filler emphasis without cutting meaningful audio.
- For Remotion, store caption safe regions separately from overlay and lower-third safe regions.
- For Premiere, use Transcribe Sequence and Create Captions as a draft; apply a style preset, then upgrade to graphics only when animation or detailed styling requires it.
- For Premiere pop-fade captions, style and correct captions first, upgrade to graphics, add Transform position/opacity keyframes, then save the Transform effect as a tested preset.
- For Remotion, store maxWords, maxDurationFrames, styleId, safeRegion, and duplicateVisualText flags.
- For Resolve, use AI subtitle creation for simple captions and Text+ with Fusion nodes for premium animated captions.
- For Premiere finishing after AE, transcribe/correct first, create short captions, style one caption, save a track style, upgrade only when needed, then fade or disable caption graphics over dense animation sections.
- For Premiere text pop, apply Transform scale keyframes around 70%, 110%, then 100%, and save the preset only after testing phrase length and collisions.
- For organic captions, store a low-focus style with safe regions, soft-fade duration, duplicate-visual-text flag, and phone-size readability notes.
- For Remotion, store caption phraseLines, impactWords, fontFamilyRole, lineHeight, tracking, caseMode, safeRegion, and duplicateVisualText flags.
- For Premiere/CapCut/Resolve, manually correct line breaks, impact words, spacing, and placement before saving caption styles or presets.
- For branded intros, store textRole, fontRole, startFrame, endFrame, safeRegion, accentType, and duplicateCaptionPolicy for every text layer.
- For CapCut Player 3 captions, store phraseLines, compoundName, textureValue,
  pastedAttributes, safeRegion, and contrastQcStatus.
- For Remotion caption motion, store phraseLines, word timings, impactWords,
  startFrame, durationInFrames, spring or fade settings, safeRegion, and
  captionContinuityPolicy plus any explicit user-approved suppression exception.
- For Remotion transparent caption overlays, export editor handoffs as ProRes
  4444 or PNG sequences and check the overlay over bright and dark footage before
  approving.
- For FFmpeg word captions, generate `drawtext` windows from corrected word or
  phrase timing, log the filter graph, and move long sequences to ASS or
  Remotion before the graph becomes brittle.

## Common Mistakes

- Prioritizing a name/title card over an important spoken line.
- Covering faces or evidence.
- Using flashy caption animation over serious testimony.
- Letting captions lag behind the spoken line.
- Assuming subtitles compensate for a bad mix.
- Publishing auto-captions without checking line breaks, filler words, or collision with faces and titles.
- Adding caption animation while another overlay or zoom already demands attention.
- Leaving long auto-caption chunks in a high-energy short.
- Captioning every word when visual text already communicates the idea.
- Upgrading captions to graphic layers before the transcript timing is corrected.
- Leaving Resolve auto captions in default styling without font, position, and line-length review.
- Using Text+ gradients, glow, or glitch on too many captions.
- Applying a pop-fade preset to many caption layers without rechecking safe areas.
- Keeping captions under hook text or B-roll text that already communicates the same phrase.
- Suppressing captions under hook/title graphics without explicit user approval.
- Rendering final captions with Pillow/PIL or a hardcoded single-font image layer.
- Double-escaping ASS hard breaks so `\\N` appears in the file or visible slash
  artifacts appear in the burned video.
- Cutting captions off harshly when an opacity fade would avoid a distracting pop.
- Leaving captions over AE text, counters, path endpoints, icons, or CTA words.
- Applying text pop to every sentence until the edit feels visually noisy.
- Letting emphasis text duplicate captions without adding hierarchy or accessibility value.
- Using loud kinetic captions in a human section where the face or proof should stay primary.
- Making captions subtle enough to match the tone but too weak to read on a phone.
- Letting auto-wrap isolate filler words as the largest or most animated caption text.
- Using script/display type for dense subtitles that need accessibility-first readability.
- Tightening tracking or adding gradient/shadow until the caption edge becomes muddy.
- Letting ordinary captions, brand text, proof quote, and outcome text all compete for the same screen region.
- Using many font styles in a fast intro without assigning each one a readable role.
- Pasting Player 3 attributes to every caption compound without checking each
  phrase against its own background.
- Generating animated caption graphics from uncorrected transcript chunks.
- Building long FFmpeg `drawtext` word chains when phrase chunks, ASS, or
  Remotion would be clearer and safer.
- Using seeded glitch, scramble, or morph as the only caption layer for important
  speech.
- Using transparent animated caption overlays without checking alpha, edge
  halos, and collision with the base caption layer.

## QC Checklist

- Captions are readable at delivery size.
- Final captioned renders use ASS captions from the repo caption style system.
- ASS files and rendered contact sheets are checked for line-break escape
  artifacts: no double-escaped `\\N`, no visible slash/backslash marks.
- No final captions were rendered with Pillow/PIL image text.
- Story-critical hard-to-hear lines are subtitled.
- Captions do not cover key visual information.
- Caption animation does not distract from emotional holds.
- Lower thirds never block subtitles needed for comprehension.
- Auto-captions are corrected before export.
- Captions remain readable over bright and dark footage.
- Captions do not collide with title-safe text, proof cards, or overlays.
- One- or two-word chunks are used only where they improve readability and pace.
- Duplicate captions remain visible, repositioned, or have a documented user-
  approved suppression exception when visual text carries the same idea.
- Caption graphics were created only after timing and wording were checked.
- CapCut adaptive caption animations are applied only after auto captions are
  corrected and line breaks are reviewed.
- Resolve auto captions and Text+ stacks are both checked for duplication and collision.
- Premium Text+ moments are tied to key lines, not every sentence.
- Premiere one-word caption chunks are manually corrected and readable at phone size.
- Caption graphic conversion happened after timing and wording review.
- Pop-fade motion does not lag behind the spoken word.
- Caption graphics are faded or disabled where the AE animation already carries the same text.
- Captions do not cover counters, path endpoints, icons, faces, proof, or CTA words.
- Center/emphasis text appears only on lines that deserve extra visual priority.
- Text pop motion settles before the phrase needs to be read.
- Organic caption style remains readable while letting faces, proof, and reactions stay primary.
- Caption line breaks form readable phrases rather than random auto-wrap.
- Word-level emphasis lands on the impact word, not filler words.
- Caption spacing remains readable after scale, pop, fade, or typewriter motion.
- Formal intro text has one primary phrase at a time and ordinary captions are
  visible, repositioned, or explicitly approved for suppression when they
  duplicate it.
- Proof and outcome text remain readable at phone size through flicker, underline, glow, or motion blur.
- Flicker, font-shift, and adaptive caption effects remain readable on both bright
  and dark frames.
- Number counters do not replace required subtitles unless the number is the
  actual spoken content.
- Player 3 caption compounds remain readable on bright, dark, busy, and face-heavy
  frames after attributes are pasted.
- Programmatic caption effects use corrected wording, timing, line breaks, and
  phrase grouping as input.
- FFmpeg word windows match speech timing and are logged for regeneration.
- Remotion caption motion has a readable final hold and does not duplicate
  ordinary captions without a clear accessibility reason.
- Transparent caption overlays have verified alpha and no black rectangle behind
  empty regions.

## Source Lessons Added

- 2026-05-27: `What Not To Do In Editing`
- 2026-05-28: `Editing Full Course`
- 2026-05-28: `Short-Form Editing`
- 2026-06-01: `Premium CapCut Text Effect`
- 2026-05-28: `DaVinci Resolve Short Form Editing`
- 2026-05-28: `Ultimate Guide To Shortform`
- 2026-05-28: `Edit High Quality Reel`
- 2026-05-29: `Editing Viral Videos`
- 2026-05-29: `Slow Editing`
- 2026-05-29: `Typography`
- 2026-05-29: `Killer Intros`
- 2026-05-29: `Viral Text Effects`
- 2026-06-01: `Remotion Lab Kinetic Typography Presets`
- 2026-06-01: `FFmpeg Drawtext Animations`
- 2026-06-01: `Programmatic Alpha Masking And Transparent Overlay Source Pack`

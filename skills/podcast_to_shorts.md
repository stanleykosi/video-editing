# Podcast To Shorts

## Purpose

Guide transformation of long-form conversations, interviews, livestreams, and
talking-head footage into short-form clips that work independently.

## When To Use This Skill

- Cutting podcasts, interviews, livestreams, webinars, or talking-head videos into shorts.
- Selecting moments from long transcripts or AI-generated candidate clips.
- Reframing landscape footage into vertical, square, or social layouts.
- Reviewing AI clipping, auto-caption, auto-reframe, or auto-publish outputs.
- Preventing short clips from misrepresenting the original context.
- Deciding whether a long podcast/show needs a reusable brand intro, and whether a short clip should inherit or skip it.

## Core Principles

- Pick clips with a clear self-contained premise, tension, point, and payoff.
- Remove setup that can be replaced by a short context caption or cold open.
- Preserve reactions when they carry emotion, credibility, or meaning.
- Use jump cuts, J/L cuts, and tiny audio handles so speech remains natural.
- AI clipping tools are first-pass assistants, not final editors.
- The clip must make sense to someone who has not watched the source episode.
- Vertical layouts should keep the active speaker, reaction, and proof visible.
- Captions need manual review even when automatically generated.
- Long podcasts or shows can justify a short brand/proof/outcome intro; extracted short clips usually should start with the standalone premise instead of inheriting a long bumper.
- Podcast intro proof is strongest when external authority, guest credibility, community proof, or outcome value is shown quickly.

## Techniques

- `technique_cards/podcast_ai_shorts_review_refine_001.json`
- `technique_cards/nle_j_l_cut_dialogue_smoothing_001.json`
- `technique_cards/retention_frontload_first_30_seconds_001.json`
- `technique_cards/retention_intro_packaging_alignment_001.json`
- `technique_cards/retention_intro_format_gate_001.json`
- `technique_cards/retention_brand_authority_outcome_intro_001.json`
- `technique_cards/motion_overlay_readability_focus_stack_001.json`
- `technique_cards/sound_audio_leveling_track_hygiene_001.json`
- Add future cards for cold-open claim, question-to-answer clip, reaction tail, context caption, and two-camera pacing.

## Timing Rules

- The first second should contain a claim, question, tension, useful point, or strong reaction.
- Do not start mid-thought unless a context caption makes the premise instantly clear.
- Trim endings only after the payoff, laugh, turn, or useful conclusion lands.
- Preserve small audio handles when a too-tight cut makes speech feel chopped.
- Remove dead air over 300 ms unless it creates tension, humor, or emotional value.
- For full podcast/show packaging, keep reusable intros around 10-15 seconds maximum.
- For podcast-derived shorts, use a 3-5 second series label only if it clarifies the clip faster than a cold open.

## Motion Rules

- Use auto-reframe only as a draft; manually check face tracking, reactions, and proof visuals.
- Choose fill, fit, split, or multi-speaker layouts based on who is speaking and what visual context matters.
- Avoid multi-person layouts that shrink the important speaker too much.
- Use focus zooms or arrows only when the viewer might miss the key action or proof.
- If a podcast intro is reused in vertical clips, trim it to the platform duration cap and keep speaker/proof visibility safe.

## Sound Rules

- Keep speech clean and natural after trims.
- Duck music or SFX under speech; podcast-to-shorts clips usually live or die on intelligibility.
- Do not cut breaths so tightly that the speaker sounds robotic.
- Repair quiet words before adding captions as compensation.
- Intro music and SFX should hand off cleanly to speech; do not bury guest or host credibility proof.

## Caption Rules

- Captions are readable at phone size.
- Remove filler-word captions and bad emphasis when they distract from meaning.
- Captions do not cover faces, title text, proof visuals, or split-screen boundaries.
- Context captions should be short and should not become a second script.
- Caption timing follows the audible speech, not the source transcript timing.
- Designed intro text should not duplicate ordinary captions unless accessibility requires it.

## Color Rules

- Keep the short visually consistent with the source unless a platform-specific style pack is requested.
- Preserve skin tone and face detail in vertical crops.
- Do not let auto-templates add colors that clash with brand or subject tone.

## Tool Implementation Notes

- ffmpeg: use crop/scale/pad for 9:16 versions, burn corrected captions after layout review, and render candidate previews before batching.
- Remotion: store candidates with source start/end, approved status, layout, caption edits, context text, and source-context risk notes.
- CapCut: use auto-captions/templates as a draft, then manually trim, reframe, edit captions, and remove weak layouts.
- Premiere: use Auto Reframe and captions as starting points, then adjust crop, speaker framing, caption breaks, and export presets.
- AI clipping tools: review every candidate for standalone premise, truthful context, start/end timing, layout, and caption accuracy before export or scheduling.
- For podcast/show intros, store introAllowed, showName, proofBeat, outcomeBeat, maxDuration, and whether each derived short should inherit, trim, or skip the bumper.

## Common Mistakes

- Publishing AI-selected clips without watching them cold.
- Starting after the premise has already been said.
- Ending before the payoff or reaction lands.
- Creating a misleading claim by removing surrounding context.
- Letting auto-captions cover faces or visual proof.
- Keeping filler-word caption emphasis that makes the clip feel messy.
- Choosing clips that are merely loud rather than useful, surprising, or complete.
- Carrying a full podcast/show intro into a short clip where it delays the standalone premise.
- Using guest/host self-praise instead of external proof or a clear viewer outcome.

## QC Checklist

- The clip makes sense without the original episode.
- Speaker identity and context are clear enough.
- Start and end trims feel natural and complete.
- Cuts do not create misleading claims.
- Captions are accurate, readable, and collision-free.
- The vertical layout keeps active speaker, reactions, and proof visible.
- No dead air longer than 300 ms remains unless it has a purpose.
- AI-generated candidates have been manually approved before export or scheduling.
- Full-show intros communicate show/brand, credible proof, and outcome within the duration cap.
- Derived shorts skip or shorten any bumper that delays the clip's independent hook.

## Source Lessons Added

- 2026-05-28: `Editing Full Course`
- 2026-05-29: `Killer Intros`

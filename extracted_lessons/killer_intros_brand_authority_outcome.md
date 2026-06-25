# Lesson: Killer Intros For Brand, Authority, And Outcome

## Source

- Tutorial: `transcripts/killer intros.txt`
- Related cards:
  - `technique_cards/retention_intro_format_gate_001.json`
  - `technique_cards/retention_brand_authority_outcome_intro_001.json`
  - `technique_cards/motion_premium_intro_text_logo_flicker_001.json`
  - `technique_cards/sound_frame_locked_intro_sfx_drums_001.json`

## What The Tutorial Teaches

The tutorial treats intros as a packaging tool, not a default opening for every
video. A strong intro can make a channel, course, podcast, or social series feel
premium when it quickly communicates three things:

1. Clear branding: who the creator, show, series, or community is.
2. Social proof and authority: why the viewer should trust this creator or offer.
3. Perceived value and outcome: what the viewer expects to gain by staying.

The tutorial also warns that old-style intro bumpers can feel outdated on normal
8-12 minute YouTube videos. The intro is most useful for long-form podcasts,
repeatable Instagram/social series, creator-brand pages, and premium course or
community packaging where identity and trust are part of the product.

## Agent Decision Rules

- Use an intro bumper only when brand identity, authority, social proof, or a
  repeatable series frame will increase trust faster than jumping straight into
  the content.
- Avoid a formal intro bumper on ordinary mid-length YouTube videos when viewers
  already clicked for a specific promise and expect the content immediately.
- For long-form YouTube or podcast packaging, keep the intro around 10-15 seconds
  maximum unless the audience already expects a show open.
- For Instagram/Reels/social series intros, keep the intro closer to 3-5 seconds
  and make the series promise clear immediately.
- Put the most persuasive third-party proof in the intro when possible. Social
  proof is stronger when someone else says the creator is valuable.
- The intro should not say "I am the best" directly; it should show proof,
  audience/community reaction, known authority, or a quote that implies value.
- Premium intro effort is justified only when the intro will be reused, opens a
  high-value product/community, or materially changes perceived production value.

## Timeline Patterns

- Brand-authority-outcome intro:
  `logo_or_show_name -> authority_or_social_proof -> outcome_quote_or_value_line -> content_start`
- Podcast/show intro:
  `cold_open_or_title -> 10-15s brand/proof/outcome package -> episode body`
- Social series intro:
  `series_name_or_episode_label -> creator/channel promise -> immediate topic/body`
- Premium text/logo motion:
  `logo/brand mark -> fast text stack/flicker -> proof/community shot -> underlined outcome phrase -> transition to content`
- Sound design:
  `music pulse/drum -> frame-locked hit/pop/flicker -> beat-aligned text emphasis -> clean handoff to speech`

## Implementation Notes

- DaVinci Resolve: use Fusion clips, Transform nodes, Text+, MultiMerge, masks,
  motion blur, flicker-style layers, and simple 3D camera/object scenes only
  when the intro needs premium identity. Use Edit page keyframes for simple brand text.
- Text design: keep one clear brand/show name, one social proof beat, and one
  outcome/value line. Multiple text layers can work, but each layer needs a role.
- Typography: use a controlled font mix; five font roles is already enough for a
  dense intro. Use underlines or highlight strokes only on high-value words.
- Sound: every SFX cue should match a visible frame event. If the sound does not
  land on what happens onscreen, remove or retime it.
- Music: fast intros can use a 120 BPM-style pulse or drum pattern, but the beat
  must support the intro hierarchy and not bury spoken proof.
- ffmpeg: build intro bumpers from timed logo/text overlays, short image/video
  proof cuts, drawtext, alpha/fade expressions, frame-accurate SFX placement, and
  a pre-rendered reusable bumper.
- Remotion: model the intro as structured sections with `brandFrame`,
  `proofFrame`, `outcomeFrame`, `textLayers`, `sfxEvents`, `bpm`, and
  `maxDurationFrames`.
- CapCut/Premiere: use nested/compound intro sequences, text layers, logo
  reveals, underlines, beat markers, and SFX tracks; keep the bumper reusable but
  trim it to the target platform.

## Mistakes And QC

- Do not add intro bumpers to videos where they delay the promised value.
- Do not build an intro around the creator's ego instead of viewer value.
- Do not use fake or weak authority. Social proof should be recognizable,
  relevant, or clearly tied to the niche.
- Do not let text layers, captions, title cards, and logo elements compete for
  the same screen region.
- Do not place SFX because they sound cool; each cue must align to a visible
  motion, text, logo, flicker, or transition frame.
- QC the intro by muting decorative layers mentally: the viewer should still know
  who this is, why to trust it, and what value they will get.

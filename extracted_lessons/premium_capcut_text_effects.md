# Lesson: Premium CapCut Text Effects

## Source

- Tutorial: `Premium CapCut Text Effect`
- Notes: `transcripts/premium capcut text effect.txt`
- Related cards:
  - `technique_cards/typography_capcut_perspective_freeze_text_001.json`
  - `technique_cards/captions_capcut_player3_smooth_caption_compounds_001.json`
  - `technique_cards/typography_capcut_color_change_highlight_wipe_001.json`
  - `technique_cards/typography_capcut_staggered_blur_glitch_reveal_001.json`
  - `technique_cards/typography_capcut_split_mask_gradient_type_001.json`
  - `technique_cards/compositing_capcut_subject_sandwich_cutout_001.json`
  - `technique_cards/typography_capcut_outline_reveal_chroma_001.json`
  - `technique_cards/typography_capcut_film_strip_glow_reveal_001.json`

## What The Tutorial Teaches

Premium CapCut text effects are mostly built from simple layer discipline:
duplicate text, compound clips, masks, keyframes, clean typography, restrained
glow, and phone-size QC. The value is not that every line gets a premium effect;
the value is choosing the right text treatment for the text's job.

The reusable techniques are scene-integrated perspective text, compound-caption
effects, color-changing highlight wipes, staggered text reveals with blur and
glitch sound, split-mask gradient type, foreground-lift text reveals, outline
chroma text, and film-strip glow sweeps.

The promotional AI-tool segment was ignored because it does not teach editing
technique.

## Agent Decision Rules

- Use perspective freeze text when angled words can follow real scene geometry,
  such as B-cam negative space, slopes, architecture, or diagonal foregrounds.
- Use Player 3-style smooth captions only after auto captions have been corrected,
  split by phrase, and compounded into manageable caption groups.
- Use color-changing highlight wipes for premium emphasis on a short statement,
  not as an accessibility subtitle replacement.
- Use staggered blur/glitch text when the reveal itself is the style beat; keep
  the reveal short and trim the glitch sound to the visual duration.
- Use split-mask gradient type for large, minimal title words where a subtle
  top/bottom tone shift reads cleaner than heavy shadow.
- Use foreground-lift text reveals only when the brush/cutout edge stays clean
  while the text moves from behind the foreground.
- Use outline reveal chroma text only when the subject cutout and green/key matte
  are clean enough at phone size.
- Use film-strip glow reveals on dark or controlled backgrounds where the shine
  can start off the word, cross it, and leave without pre-glow or tail glow.

## Timeline Patterns

- Perspective scene text:
  `text -> compound -> Flip 6 -> internal_size_adjust -> second_compound -> freeze_frame -> delete_tails -> align_to_scene_geometry`.
- Player 3 smooth captions:
  `auto_captions -> line_splits -> compound_caption_groups -> Player 3 effect -> Texture 0 -> paste_attributes -> qc`.
- Highlight color change:
  `base_text -> duplicate_inverted_text_plus_highlight_bar -> compound -> Split mask 90deg -> left_to_right_keyframes -> easing`.
- Staggered reveal:
  `word_layers -> 2-frame_blade -> pre-reveal_color -> stagger_layers -> compound_each_word -> blur_segments -> glitch_sfx_trim`.
- Gradient type:
  `base_text -> duplicate_lighter_text -> compound -> Split mask -> Feather around 35 -> position_gradient_boundary`.
- Foreground lift:
  `duplicate_video_top -> brush_foreground_cutout -> text_between_layers -> Transform Y keyframes -> edge_qc`.
- Outline reveal:
  `base_video -> foreground_cutout -> duplicate_text -> stroke_plus_key_fill -> compound -> chroma_key -> edge_qc`.
- Glow reveal:
  `base_text -> duplicate_white_text -> compound -> Film Strip mask -> mask_keyframes -> Glow 2 -> off-word start/end qc`.

## Implementation Notes

- ffmpeg: approximate compound text effects with separate drawtext/ASS layers,
  alpha masks, animated crop/wipe mattes, boxblur/gblur for glow, and audio cues
  aligned by frame. Use contact sheets because many CapCut-only effects are not
  one-to-one filters.
- Remotion: model each effect as structured data with source text, effect type,
  layer order, mask geometry, keyframe frames, caption suppression, SFX frame, and
  final readable frame.
- Blender: use text objects, 3D transforms, alpha masks, foreground roto, and
  compositor glow when the scene needs higher-control perspective or cutout work.
- CapCut: keep source text editable inside compounds, paste attributes only after
  one reference layer passes QC, and review Remove Background, Chroma Key, Split
  mask, Film Strip mask, Glow, and Player 3 effects in motion.
- Premiere: use Essential Graphics, nests, masks, Track Matte/Ultra Key, blur,
  glow, and After Effects/Roto Brush for cleaner cutout or matte versions.

## Mistakes And QC

- Do not keep ordinary captions under designed text unless accessibility needs a
  separate subtitle layer.
- Do not let glow, gradient, blur, or mask boundaries make text slower to read
  than a plain title.
- Do not paste Player 3 or other effects to all captions before checking a bright,
  dark, busy, and face-heavy frame.
- Do not use foreground lift or outline reveals when the cutout edge chatters
  around hair, hands, trees, water, or motion blur.
- Do not let a glitch SFX tail continue after the staggered reveal finishes.
- Check that every premium text effect has one readable path, one named job, and a
  clean final state before the next phrase appears.

# CapCut Heavy Overlay Pre-render Workflow

## Use When

- Dense overlays, masks, effects, or duplicate layers make the main project lag.
- Each clip can be polished separately before transitions and sound are finalized.

## Workflow Pattern

`main_clip_placeholder -> clip_subproject -> overlays/effects -> render_or_export -> replace_placeholder -> transition/SFX pass`

## Suggested Rules

- Keep the full clip or enough handles in the subproject.
- Use a temporary black screen, placeholder, or spacer only to preserve duration
  while replacing the rendered clip.
- Keep captions and final SFX editable in the main timeline unless they are part
  of the baked visual design.
- Retain the original source or placeholder for revisions.
- Check the rendered replacement against the previous and next clips before
  deleting or hiding anything.

## QC

- Replacement duration matches the intended range.
- Temporary spacers are removed before final export.
- Main timeline playback is smooth enough to judge timing.
- Captions, final sound, and transitions remain editable.

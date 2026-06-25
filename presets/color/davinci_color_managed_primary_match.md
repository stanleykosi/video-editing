# DaVinci Color Managed Primary Match

Use this preset when a Resolve project needs a clean technical base before a
creative look.

## Setup

- Project color management: use a color-managed Resolve workflow or explicit
  input transforms for log/wide-gamut footage.
- First node pass: exposure, contrast, white balance/tint, saturation, and a
  restrained curve.
- Shot match: select a hero still, compare every related shot to that still, and
  avoid cumulative drift.
- Global look: place whole-timeline style on timeline nodes only after clip-level
  matching is close.

## QC

- Scopes confirm no accidental clipped important highlights or crushed important shadows.
- Skin, proof, captions, and overlays remain readable after the look.
- The look enhances the footage's existing tone instead of fighting the production design.
- Secondaries remain subtle enough that windows, qualifiers, or tracked masks do not reveal themselves.

## Related Cards

- `technique_cards/davinci_color_management_primary_look_001.json`
- `technique_cards/davinci_color_hero_still_shot_matching_001.json`
- `technique_cards/davinci_color_secondary_windows_qualifier_tracker_001.json`


# DaVinci Fusion Basic Node Composite

Use this preset when an effect needs Resolve Fusion instead of simple Edit page
inspector keyframes.

## Node Pattern

- `MediaIn -> source correction or transform -> mask/blur/noise/title branch -> Merge -> MediaOut`
- Use Merge when combining foreground and background sources.
- Put source-specific correction before Merge and whole-result correction after Merge.
- Use Polygon or Ellipse masks with soft edges for local effects.
- Rename nodes once the graph has more than a few branches.

## QC

- Node order affects only the intended source or combined image.
- Mask edge softness hides the composite without erasing important detail.
- Motion or tracker data stays aligned across the whole affected range.
- The effect remains readable in the final timeline context, not only inside Fusion.

## Related Cards

- `technique_cards/davinci_fusion_node_compositing_basics_001.json`
- `technique_cards/davinci_fusion_tracker_magic_mask_graphics_001.json`


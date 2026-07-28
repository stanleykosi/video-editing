# Asset Manifest QC

Use this checklist before marking any edit finished when it uses downloaded,
generated, rendered, or data-derived assets.

## Manifest

- `asset_manifest.json` exists in the project folder.
- Every external stock image, video, music cue, SFX, icon, map, chart, template,
  generated image, or generated data visual used in the timeline has a manifest
  entry.
- Each manifest entry includes source platform, source URL or provider, local
  path, downloaded/generated date, rights/license notes, and intended use.
- Generated assets include prompt, model/provider, generation date, and any input
  references.
- Maps include attribution text and map data/tile provider.
- Charts include data source, query URL or local data path, units/date range when
  relevant, transformations, and chart spec path when available.
- Screenshots, source documents, paper textures, grids, cutouts, logos, and
  editorial graphic templates include source/rights notes and privacy review
  status when applicable.

## Rights And Delivery

- CC/open assets prefer public domain/CC0 first, then CC BY with attribution.
- NC, ND, editorial-only, watermark, or preview-only assets are not used in final
  commercial/monetized/remixed exports unless the intended use is explicitly
  allowed.
- Music and SFX license/platform safety is documented or the track is marked
  temp-only.
- Public OpenStreetMap tiles were used only for light/draft map rendering; heavy
  or production use has a provider, local renderer, or explicit plan.
- Final export does not include unlicensed source files, raw stock loops, or
  template source assets as standalone redistributable material.
- Publisher-inspired styles do not use protected logos, exact trade dress, or
  official marks unless the project has permission.

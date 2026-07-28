# Asset Planner

Use this before sourcing, generating, or rendering assets for a from-scratch
video. Always read `knowledge_plan.md` and
`knowledge/research/catalogs/asset_resource_platforms.md` before asset search or generation.

## Output

Create `asset_list.md` in the project folder using
`knowledge/workflows/content_creation/templates/asset_list_template.md`, then maintain
`asset_manifest.json` with `tools/video-use/helpers/asset_manifest.py`.

## Asset Categories

- Footage.
- Images.
- Generated images.
- Icons.
- Maps.
- Charts/data.
- Music.
- SFX.
- Fonts.
- Motion graphics/templates.
- Transparent overlays.

## Source Priority

1. Existing user-provided assets.
2. No-key/public sources with clear rights.
3. API-key sources available in `.env`.
4. Generated assets with prompt/model provenance.
5. Paid/manual sources only after user confirmation.

## Helper Workflow

- Route project knowledge before planning assets:
  `tools/video-use/helpers/knowledge_router.py`
- Search/download public assets:
  `tools/video-use/helpers/find_assets.py`
- Register downloaded, imported, generated, map, chart, or audio assets:
  `tools/video-use/helpers/asset_manifest.py`
- Generate placeholder or AI visual assets:
  `tools/video-use/helpers/generate_asset.py`
- Render data charts:
  `tools/video-use/helpers/render_chart.py`
- Render maps:
  `tools/video-use/helpers/render_map.py`

## Rules

- Do not bypass paywalls, watermarks, login walls, or license restrictions.
- Do not use watermarked previews in final exports.
- Track every external, generated, and data-derived asset in the manifest.
- For documentary/factual videos, do not let generated visuals appear as proof.
- Prefer charts from data and maps from geodata over screenshots.
- Music and SFX need license/platform status before final export.

## QC

- Every timeline asset has a manifest entry.
- Every manifest entry has source, creator, URL, license/rights, date, local path,
  and timeline use status.
- Generated assets include provider, model, prompt, date, and policy/license notes.
- Maps include attribution.
- Charts include data source and query/file reference.

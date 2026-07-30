# Editorial Brain Progress

Last updated: 2026-07-30

## Current phase

Implementation and all release gates are complete.

## Completed

- Read root instructions and the complete `video-use` and `openai-docs` skills.
- Recorded clean baseline commit
  `54c6dcd1b29be4f6bf653a4ee0ef2691d5400b11`.
- Audited engine docs/public boundaries, media/inspection capabilities,
  helper transcription, tests, fixtures, dependencies and knowledge seams.
- Installed the official OpenAI Developer Docs MCP for future sessions; this
  session used official-domain fallback because newly installed MCP tools are
  not hot-loaded.
- Completed the unmodified engine baseline: 329 passed, 10 skipped.
- Added the smallest required engine seam, a backend-neutral typed
  `AddTrackOperation`, with transactional editor coverage and public docs.
- Implemented the separate `editorial_brain` package: strict models, evidence,
  providers, deterministic media analysis, story/select/cut/continuity/rhythm
  systems, beam and duration search, ten planning passes, reference analysis,
  compilation, caching, observability, benchmarks, and CLI.
- Implemented Deepgram transcription/diarization and current OpenAI Responses
  API structured semantic/vision providers as optional integrations.
- Added dedicated narration-media compilation instead of conflating source
  picture audio with voice-over.
- Added structurally bounded subshot derivation from verified speech, pause,
  and audio-event times.
- Replaced benchmark contract checks with actual deterministic planning,
  repeatability, patch application, and render-DAG compilation for all ten
  required scenarios. Current result: 10/10 pass.
- Passed strict MyPy across 227 source files and Ruff across the repository
  source/test/tool surfaces.
- Passed the current complete Brain suite: 54 passed, 2 optional-provider smoke
  tests skipped, 83.26% branch-aware Brain coverage.
- Passed all 12 golden tests and all ten scenario benchmark runs, including
  deterministic repeatability, patch application, render-DAG compilation, and
  scenario-specific editorial behavior assertions. Current deterministic
  fingerprint: `d0913ccafe6d05c5af41c2e9ab8a36525eb397b73ac9779961fa7bf52a7b48a1`.
- Passed performance gates: four-hour transcript indexing in 1.48s,
  hundreds-of-beats beam search in 3.02s, thousand-document indexing/search in
  0.11s, and 1,000 checksum-validated cache reuses in 0.79s on the final run.
- Passed the bounded real-media analysis -> plan -> patch -> render -> technical
  QC integration test.
- Passed `uv lock --check`, both doctor commands, and isolated sdist/wheel build.
- Passed the pre-knowledge-release combined engine + Brain suite with coverage: 380 passed,
  12 environment-gated skips, 80.98% combined branch-aware coverage in
  1279.91s. Existing engine behavior remains green.
- Added separate baseline, analysis, engine-integration, and credential-gated
  provider-smoke CI lanes without changing the existing engine CI.
- Materialized all ignored engine and Brain tests into the canonical
  `testdata/engine/tests.tar.gz` archive.
- Fixed provider configuration so project-root `.env` keys resolve without
  logging secrets or mutating global environment state. Deepgram is now
  correctly reported as configured from `project_env_file`.
- Replaced duplicated creator-file routing with a checked source-neutral
  knowledge graph: 385 inputs and 9,393 atomic statements consolidate to 2,357
  unique principles, 240 recipes, 1,940 QC gates, 11 resolved contextual
  conflict families, and zero unresolved conflicts. Principle reduction is
  74.91%; total-construct reduction is 51.70%.
- Implemented deterministic per-video TasteProfiles from the brief, workflow,
  source capabilities, explicit style terms, and bounded reference grammar.
  Duplicate tutorial frequency cannot change rankings or weights, and no
  creator/source/path/URL provenance survives into the base, taste, plan, or
  engine operations.
- Removed the legacy public file-route compiler and its policy source-path/hash
  propagation. Added `video-brain knowledge-build`, checked canonical base
  validation, cached loading, API/CLI exposure, and source-neutral artifacts.
- Extended all ten editorial benchmarks with separate consolidation-reduction,
  scenario-relevance, reference-conditioning, source-neutral identity, and
  engine-compilation gates. All pass; current deterministic fingerprint:
  `621831cdc6bc08f21d595762748ded81f983bcb84cf4c651b671d57b923ec683`.
- Added a production environment factory that selects OpenAI when configured or
  launches a fresh authenticated Codex sub-agent when the OpenAI key is absent.
  The fallback is read-only, ephemeral, candidate-ID bounded, strict-schema
  validated, cached through the analysis identity, and live-smoke verified.
- Auto-discovered the repository's isolated Manim 0.20.1 runtime, repaired its
  setup check, made the release doctor validate the exact locked version, and
  retained Blender as optional. Real geometry/alpha and MathTex renders pass.

## Active

- None for this phase. The independent Editorial Critic remains a separate
  future phase.

## External limitations

- Deepgram is configured from the project `.env`; live calls still require
  network access and consume provider quota. OpenAI remains unconfigured and
  optional; the authenticated Codex fallback also requires network access and
  consumes the signed-in account's inference allowance.
- Subjective human editorial quality is intentionally reported as an ungated
  review area; this phase does not implement the independent Editorial Critic.

## 2026-07-30 provider and Manim hardening verification

- Live authenticated Codex fallback: 1 successful semantic request with strict
  candidate-ID output, request provenance and reported token usage.
- Editorial Brain suite: 60 passed, 2 credential-gated provider smokes skipped.
- Engine unit suite: 209 passed, 1 environment-gated skip.
- Focused provider/CLI/external-graphics suite: 22 passed, 2 provider smokes
  skipped; final external-graphics unit gate: 8 passed.
- Real Manim geometry/alpha plus MathTex: 2 passed in 10.79 seconds.
- Ruff lint and format: clean across 249 files. Strict MyPy: clean across 234
  source files. Lock check, deterministic test repack, both doctors, sdist and
  wheel build passed.

## 2026-07-30 knowledge consolidation and taste verification

- Canonical base fingerprint:
  `01c01b594527c33d97bff9a104e4600a8bf4b551fa32d3669fe51db350037c9b`.
- Focused consolidation/taste tests: 8 passed in 46.90s.
- Editorial Brain suite before final consolidation cleanup: 64 passed, 2
  credential-gated skips. Final behavior is covered again by the combined run.
- Golden benchmark: 10/10 scenarios passed with fingerprint
  `621831cdc6bc08f21d595762748ded81f983bcb84cf4c651b671d57b923ec683`.
- Final combined branch-coverage gate: 398 passed, 12 environment-gated skips
  in 1178.89s; 82% branch-aware coverage across 20,307 statements.
- Strict MyPy: 238 source files clean. Ruff: Brain source/tests clean. Engine
  unit regression: 209 passed, 1 environment-gated skip.

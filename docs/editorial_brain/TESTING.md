# Editorial Brain Testing

Tests are split into unit, provider, integration, golden and performance lanes.
The default lane has no network and no heavyweight optional dependency.

Unit coverage includes strict models, evidence/cache identity, transcript and
shot processing, candidate generation, hard constraints, scoring, continuity,
reaction protection, AV relationships, pacing, search, compilation and
serialization. Integration applies compiled patches through `TimelineEditor`,
validates projects, compiles render DAGs and runs bounded render/QC fixtures.

Ten editorial goldens execute plan/variant/compile flows and assert
ranges/windows/relationships and expected behavior, not human-level quality. A
bounded generated-media integration test additionally imports, analyzes,
plans, patches, renders and runs engine technical QC. Provider smoke tests are
opt-in environment gates.
Performance tests cover multi-hour transcript indexes, thousands of shots,
search scaling, cache reuse and memory.

CI is split into Brain baseline, analysis, Brain-to-engine integration, and
manual optional-provider lanes. The bounded integration fixture performs
canonical import, analysis, reference analysis, planning, patch application,
render, and engine technical QC. Existing engine CI remains unchanged.

Final local results on 2026-07-29:

- Current Brain-only: 54 passed, 2 credential-gated skips, 83.26% branch
  coverage.
- Golden: 12 passed.
- Pre-knowledge-release combined engine + Brain baseline: 380 passed, 12
  environment-gated skips, 80.98% branch coverage in 1279.91s. The current
  knowledge update reran the complete Brain and Brain-to-engine compilation
  suites; `video_engine` production code was unchanged.
- Ruff, strict MyPy (227 files), changed-surface Black check, lock check,
  doctors, and isolated sdist/wheel build all passed.
- The ignored tests were packed into `testdata/engine/tests.tar.gz`.

Knowledge tests validate complete catalog ingestion, deterministic semantic
consolidation, source-neutral output, conflict resolution, duplicate-frequency
immunity, reference-conditioned taste, bounded policy effects, opt-out behavior,
engine compilation and CLI exposure. Provider tests verify
project `.env` resolution without leaking or mutating credentials.

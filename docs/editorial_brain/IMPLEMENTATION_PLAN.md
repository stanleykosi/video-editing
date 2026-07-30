# Editorial Brain Implementation Plan

1. Freeze engine/API/test baselines and decisions.
2. Implement strict models, evidence, policies, providers, cache, tracing.
3. Implement deterministic source and transcript analysis plus optional cloud
   adapters.
4. Implement story, requirements, selects, cut generation/scoring, continuity,
   reactions and audio/picture planning.
5. Implement pacing, specialist planning, reference priors, variants and global
   beam/DP optimization through explicit passes.
6. Compile to public engine objects/patches and validate transactionally.
7. Ship facade, CLI, artifacts, benchmarks, ten goldens, performance tests, CI,
   packaging and complete documentation.
8. Run the full release gate and record exact results in `PROGRESS.md`.

Every stage remains executable with deterministic providers and no network.


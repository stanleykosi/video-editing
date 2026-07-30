# Editorial Brain Architecture

```text
brief + canonical Project + optional reference/directives
  -> deterministic/media and provider-backed evidence index
  -> story map and explicit visual/audio requirements
  -> top-K selects and structural cut candidates
  -> hard constraints, visible multidimensional scores
  -> beam/DP candidate-sequence search
  -> fine-cut, AV, B-roll, rhythm and presentation passes
  -> EditorialPlan + DecisionTrace
  -> canonical video_engine Project or revision-checked TimelinePatch
```

Dependency direction is one-way: `editorial_brain -> video_engine.api`.
Providers may classify supplied candidate IDs and evidence, but cannot author
timestamps. Code owns rational time, enumeration, constraints, aggregation,
search, tie-breaking, compilation, and validation.

`editorial_brain.knowledge` sits above policies and below the facade. It loads
the checked source-neutral base, synthesizes a per-video TasteProfile, and compiles bounded
typed directives before selects/search. It never imports or changes engine
internals.

The package is divided into API/core, providers, analysis/understanding, story,
selects/cuts/continuity/rhythm, planning/search/reference, compile, policies,
storage/observability, benchmark, and CLI. Artifacts are project-scoped under
`.editorial-brain/`; source media is referenced by engine media ID and SHA-256,
never copied.

All persisted models reject unknown fields. Evidence distinguishes measured,
observed, model-inferred, user-supplied, and derived claims. Rationale is concise
structured evidence, never hidden chain-of-thought.

# Editorial Brain Public API

For production provider auto-selection, use
`EditorialBrain.from_environment(project_root)`. It configures Deepgram from the
project `.env`, selects OpenAI semantic/vision inference when its key exists,
and otherwise selects the authenticated Codex sub-agent fallback. The plain
constructor remains dependency-injected and network-free by default for tests
and controlled integrations.

The stable import surface is `editorial_brain` and `editorial_brain.api`.

```python
brain = EditorialBrain(project_root)
analysis = brain.analyze(project=project, brief=brief)
base = brain.consolidate_knowledge()  # checked source-neutral knowledge graph
knowledge = brain.knowledge(brief)  # TasteProfile + executable directives
reference = brain.analyze_reference(reference_path)  # optional
plans = brain.plan(
    project=project, brief=brief, analysis=analysis, variants=3, reference=reference
)
compiled = brain.compile(project=project, plan=plans.best)
result = engine.editor(project).apply_patch(compiled.patch)
```

The facade exposes `analyze`, `analyze_reference`, `consolidate_knowledge`, `knowledge`, `build_story`,
`generate_selects`, `generate_variants`, `plan`, `compile`, `explain`, and
`benchmark`. Results are strict serializable models and preserve evidence,
confidence, alternatives, review flags, provider fingerprints, and run traces.

Compilation returns a canonical new `Project`, a revision-checked
`TimelinePatch`, or both when appropriate. It never renders production media.

`analyze` returns a `MediaUnderstandingIndex`; `build_story` returns a
`StoryMap`; `generate_selects` retains top-K alternatives; and `plan`/
`generate_variants` return a ranked `PlanSet`. `compile(mode="patch")` returns
the patch plus the transactionally validated project, while
`compile(mode="project")` returns the resulting canonical project.

`video-brain` provides `doctor`, `knowledge-build`, `knowledge`, `analyze`, `analyze-reference`, `story`,
`selects`, `plan`, `variants`, `compile`, `apply`, `explain`, and `benchmark`.
Every command accepts `--json`; planning also accepts `--reference-profile`.
Production rendering remains a `video-engine` responsibility.

Knowledge routing defaults to `auto`. `EditorialBrief.knowledge_mode` can be
`auto`, `off`, or `explicit`; explicit mode uses canonical principle IDs,
categories, or semantic terms. `reference_influence` is bounded to `0..0.6`.
Plans retain only the canonical base fingerprint, per-video TasteProfile ID,
active principle IDs, resolved axes, and concise reasons. Tutorial/creator
source provenance is intentionally not carried into planning or engine state.

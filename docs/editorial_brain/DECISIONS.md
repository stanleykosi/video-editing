# Editorial Brain Decisions

## EB-D001: Engine time is the only time authority

All persisted timestamps use public engine `RationalTime` and `TimeRange`.
Library/provider float seconds are converted immediately at an explicit
timescale and never used for ordering or final boundaries.

## EB-D002: Models judge supplied candidates

Semantic/vision providers return IDs and structured judgments over verified
candidates. A response containing unknown IDs or timestamps is rejected.

## EB-D003: Evidence precedes optimization

Measured/observed/provider evidence is immutable input to explicit scoring.
Hard constraints reject invalid edits before weighted soft scoring.

## EB-D004: Search is deterministic and global

Beam search and duration DP use stable candidate IDs, explicit seeds, and
lexicographic tie-breaking. Top alternatives remain in the result.

## EB-D005: Silence and discontinuity are intentional possibilities

Pause/reaction protection and motivated discontinuity are modeled explicitly;
speed and density are never universal quality proxies.

## EB-D006: Provider absence is data, not fabricated output

Missing credentials and exhausted retries return typed unavailable/failure
results. Baseline tests use deterministic providers only.

## EB-D007: Brain artifacts are separate from engine state

Analysis/cache/traces live under `.editorial-brain/`. Only final canonical
projects or patches cross into engine state, with namespaced provenance.

## EB-D008: Knowledge is compiled, not prompted

`RepositoryKnowledgeDirectiveProvider` validates a checked source-neutral base
compiled from every playbook, lesson, technique, preset, style and editorial
checklist. Per-video synthesis uses applicability predicates, profile/workflow
relevance, available source capabilities, optional reference grammar, and
deterministic tie-breaking. Selected principles become bounded cut/select
priors, pacing, reaction/breath preservation, music alignment and transition
preferences. Raw prose never becomes an unrestricted timeline or renderer
command.

## EB-D009: Engine changes require proof

The implementation initially targets existing public operations. Any missing
track-management primitive will be added only if compilation tests prove it is
necessary, and will remain general-purpose and backend-neutral.

Audit proved that an arbitrary rough project may lack the separate audio or
upper visual lane required by a valid compiled patch. The engine therefore adds
only `AddTrackOperation`; no remove/reorder operation or Brain policy was added.

## EB-D010: Dialogue, narration and reference timing stay distinct

Source dialogue uses transcript phrase ranges and protected pause beats.
Voice-over compiles as a dedicated canonical audio clip while source picture
audio is disabled. References contribute only measured pacing/music priors.

## EB-D011: Final variants are ranked after all passes

Beam order is provisional. Assemblies are re-ranked after fine-cut, AV,
picture-role, transition and rhythm scoring so `best` reflects the final
objective.

## EB-D012: Tutorial-derived knowledge is a taste prior, not a human-level claim

Tutorial-derived knowledge changes the actual search objective and is covered
by golden consolidation/taste gates. It does not prove universal human taste. Human
preference panels and the independent post-render Editorial Critic remain
separate validation layers.

## EB-D013: Consolidated knowledge is source-neutral

Creator names, URLs, tutorial paths, source IDs and source hashes are ingestion
concerns only and do not exist in the canonical base, TasteProfile, plan, or
engine operations. Repeated tutorial occurrence is diagnostic support count,
never an editorial vote. Legitimate contradictions are preserved as contextual
variants and resolved for the current video.

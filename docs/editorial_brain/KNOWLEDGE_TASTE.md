# Canonical Knowledge And Per-Video Taste

The tutorial-derived repository is compiled once into the checked,
source-neutral base at `knowledge/editorial_base/v1/index.json`. Runtime
planning does not route creator files, count repeated advice as votes, or carry
creator names, URLs, source paths, source IDs, or source hashes.

The compiler separates four things that were previously mixed together:

- canonical principles: editorial judgment that can affect selection, cuts,
  continuity, rhythm, audio/picture, story, or presentation;
- technique recipes: optional execution patterns with applicability,
  prerequisites, exclusions, and bounded steps;
- quality gates: observable blocker or warning assertions;
- contextual conflicts: legal alternatives such as fast compression versus an
  intentional hold, resolved for the current brief instead of globally.

The checked v1 base is built from 385 validated items and 9,393 atomic
statements. It contains 2,357 unique principles, 240 consolidated recipes,
1,940 quality gates, 11 resolved contextual conflict families, and zero
unresolved conflicts. Unique principles are 74.91% smaller than the atomic
input; all retained constructs together are 51.70% smaller. These numbers are
compiler outputs, not popularity weights.

## Taste synthesis

For every video, the Brain creates a strict `TasteProfile`. It considers the
brief, format, audience, script/storyboard terms, source capabilities, explicit
directives, and optional `ReferenceEditProfile`. It then selects legal
principles and recipes, activates relevant QC gates, resolves conflicts, and
produces bounded values for:

`clarity`, `information_density`, `cut_energy`, `breathing_room`,
`reaction_patience`, `visual_proof`, `continuity_strictness`, `musicality`,
`novelty`, `presentation_restraint`, and `camera_motion`.

Those values compile into visible cut/select weights, duration priors,
reaction/breath/hold policy, music alignment, and restrained transition rules.
The profile ID, base fingerprint, active principle IDs, axes, and concise
reasons are retained in the plan. Source provenance is intentionally absent.

## Reference-led uniqueness

A reference contributes measured grammar only: duration distribution,
silence, motion, graphic/caption/SFX density, musical alignment, and
repetition. Its influence is explicitly bounded by
`EditorialBrief.reference_influence` (maximum `0.6`). The reference cannot
provide timestamps, source ranges, frames, or a sequence to copy. Two different
reference grammars produce different deterministic TasteProfiles for the same
brief.

Negative reference examples are not required to use the base. Avoidance rules,
incompatibilities, source-capability checks, and QC gates provide conservative
guardrails. Future positive/negative ranked edits can calibrate preferences,
but they are an enhancement rather than a missing aggregation layer.

Rebuild and validate the checked base with:

```bash
video-brain knowledge-build --json
```

Inspect a video's resolved taste with:

```bash
video-brain knowledge --brief brief.yaml --reference-profile reference.json --json
```
